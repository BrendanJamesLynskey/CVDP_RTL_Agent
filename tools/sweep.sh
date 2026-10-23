#!/usr/bin/env bash
# Run the agent image on a split (or a list of ids) through the CVDP harness, then collect and tabulate.
# Used by .github/workflows/sweep.yml; runs the same way locally.
#
#   bash tools/sweep.sh [all|run|collect]     (default all; the workflow runs `run` and `collect` as separate steps,
#                                              so collection still happens when the run step times out)
#
# SEEDS=n runs the same problem list n times, one after another, each in its own work dir ($WORK/seed<k>) and its
# own harness invocation, with CVDP_SEED=<k> passed to the agent (a label only: sampling is not seeded). One ledger
# ($WORK.ledger) is shared by every seed, so the whole-run spend guard covers the whole job.
#
# Needs: the harness checked out in $CVDP_DIR (with its requirements installed and .env set), the dataset in
# $DATA_DIR, nvidia/cvdp-sim:v1.0.0 and $AGENT_IMAGE in the local Docker.
# The API key, when needed, is read from OPENROUTER_API_KEY and reaches the agent only through CVDP_AGENT_ENV.
set -euo pipefail

PHASE=${1:-all}
SPLIT=${SPLIT:-agentic}
IDS=${IDS:-}
MODEL=${MODEL:-fake}
BUDGET_USD=${BUDGET_USD:-0.10}
RUN_BUDGET_USD=${RUN_BUDGET_USD:-}   # absolute whole-run guard; blank = budget x problems x 1.2
MAX_TURNS=${MAX_TURNS:-10}
SELF_CHECK=${SELF_CHECK:-1}
LINT=${LINT:-1}
REASONING=${REASONING:-low}          # default | low | medium | high | off
SEEDS=${SEEDS:-1}
THREADS=${THREADS:-2}
WORK=${WORK:-work}
CVDP_DIR=${CVDP_DIR:-cvdp}
DATA_DIR=${DATA_DIR:-data}

die() { echo "sweep.sh: $*" >&2; exit 2; }
num() { [[ "$2" =~ ^[0-9]+(\.[0-9]+)?$ ]] || die "$1 must be a non-negative number, got '$2'"; }
int() { [[ "$2" =~ ^[1-9][0-9]*$ ]] || die "$1 must be a positive integer, got '$2'"; }
bit() { [[ "$2" =~ ^[01]$ ]] || die "$1 must be 0 or 1, got '$2'"; }
num BUDGET_USD "$BUDGET_USD"; int MAX_TURNS "$MAX_TURNS"; int THREADS "$THREADS"
bit SELF_CHECK "$SELF_CHECK"; bit LINT "$LINT"; int SEEDS "$SEEDS"
case "$REASONING" in
  default|low|medium|high|off) ;;
  *) die "REASONING must be default, low, medium, high or off, got '$REASONING'" ;;
esac
[ -z "$RUN_BUDGET_USD" ] || num RUN_BUDGET_USD "$RUN_BUDGET_USD"
[[ "$MODEL" =~ ^[A-Za-z0-9._:/-]+$ ]] || die "MODEL has unexpected characters: '$MODEL'"
case "$PHASE" in all|run|collect) ;; *) die "phase must be all, run or collect" ;; esac

repo=$(cd "$(dirname "$0")/.." && pwd)
case "$SPLIT" in
  agentic) src="$DATA_DIR/agentic_code_generation_no_commercial.jsonl" ;;
  heavy) src="$DATA_DIR/agentic_heavy_code_generation_no_commercial.jsonl" ;;
  *) die "unknown split $SPLIT" ;;
esac

run_phase() {
  # A reused work dir is wrong twice over: the old ledger counts against the guard, and the harness reuses an
  # existing raw_result.json instead of running.
  if [ -e "$WORK" ] && [ -n "$(ls -A "$WORK" 2>/dev/null)" ]; then die "WORK=$WORK is not empty; use a new one"; fi
  for x in "$WORK.ledger" "$WORK.problems.jsonl"; do [ ! -e "$x" ] || die "$x exists; use a new WORK"; done
  mkdir -p "$WORK"
  local work subset ledger n guard seed start
  work=$(cd "$WORK" && pwd)
  subset="$work.problems.jsonl"
  ledger="$work.ledger"
  n=$(python3 "$repo/tools/subset.py" "$src" "$IDS" "$subset")
  echo "problems: $n"

  # Whole-run spend guard, across all seeds: each agent adds its cost to the ledger (plus the per-problem budget for
  # any call whose cost was not reported), and an agent that starts once the ledger has passed the guard stops
  # before its first LLM call.
  mkdir -p "$ledger"
  if [ -n "$RUN_BUDGET_USD" ]; then guard=$RUN_BUDGET_USD
  else guard=$(python3 -c "import sys; a = sys.argv; print(round(float(a[1]) * int(a[2]) * int(a[3]) * 1.2, 6))" \
    "$BUDGET_USD" "$n" "$SEEDS"); fi
  printf '{"problems": %s, "seeds": %s, "run_budget_usd": %s, "model": "%s", "reasoning": "%s"}\n' \
    "$n" "$SEEDS" "$guard" "$MODEL" "$REASONING" > "$work.run.json"

  if [ "$MODEL" = fake ]; then export CVDP_PROVIDER=fake; else export CVDP_PROVIDER=openrouter; fi
  export CVDP_MODEL="$MODEL" CVDP_BUDGET_USD="$BUDGET_USD" CVDP_MAX_TURNS="$MAX_TURNS" CVDP_SELF_CHECK="$SELF_CHECK" \
    CVDP_LINT="$LINT" CVDP_LEDGER_DIR=/ledger CVDP_RUN_BUDGET_USD="$guard" CVDP_REASONING="$REASONING"
  export CVDP_AGENT_MOUNTS="$ledger:/ledger"
  export CVDP_AGENT_ENV=CVDP_PROVIDER,CVDP_MODEL,CVDP_BUDGET_USD,CVDP_MAX_TURNS,CVDP_SELF_CHECK,CVDP_LINT,CVDP_LEDGER_DIR,CVDP_RUN_BUDGET_USD,CVDP_REASONING,CVDP_SEED
  if [ "$CVDP_PROVIDER" = openrouter ]; then
    test -n "${OPENROUTER_API_KEY:-}" || die "OPENROUTER_API_KEY is not set"
    export CVDP_AGENT_ENV="OPENROUTER_API_KEY,$CVDP_AGENT_ENV"
  fi
  echo "run budget guard: \$$guard (all $SEEDS seed(s))"

  for seed in $(seq 1 "$SEEDS"); do
    mkdir -p "$work/seed$seed"
    export CVDP_SEED=$seed
    start=$(date +%s)
    (cd "$CVDP_DIR" && ./run_benchmark.py -f "$subset" -l -g "$AGENT_IMAGE" -p "$work/seed$seed" -t "$THREADS") || true
    echo "$(( $(date +%s) - start ))" > "$work/seed$seed.wall_s"
    echo "seed $seed: harness wall time $(cat "$work/seed$seed.wall_s") s"
  done
}

collect_phase() {
  [ -d "$WORK" ] || die "no work dir $WORK"
  local work d seed hdr="" collected=0 missing=""
  work=$(cd "$WORK" && pwd)
  rm -f "$work/results.csv"
  for d in $(ls -d "$work"/seed* 2>/dev/null | grep -E '/seed[0-9]+$' | sort -V); do
    seed=${d##*/seed}
    if [ -f "$d/raw_result.json" ]; then
      python3 "$repo/tools/collect.py" "$d" --dataset "$work.problems.jsonl" --runner "${RUNNER:-local}" \
        --model "$MODEL" --seed "$seed" $hdr >> "$work/results.csv"
      hdr=--no-header
      collected=$((collected + 1))
    else
      missing="$missing $seed"
    fi
  done
  if [ "$collected" -gt 0 ]; then
    if [ "$collected" -gt 1 ]; then python3 "$repo/tools/table.py" --seeds "$work/results.csv" > "$work/table.md"
    else python3 "$repo/tools/table.py" "$work/results.csv" > "$work/table.md"; fi
  else
    : > "$work/table.md"
  fi
  if [ -n "$missing" ]; then
    echo "No raw_result.json for seed(s)$missing: the harness did not finish (timeout?). Agent outputs, if any, are" \
      "still uploaded." >> "$work/table.md"
  fi
  for d in "$work"/seed*.wall_s; do
    [ -f "$d" ] && echo "Harness wall time, $(basename "$d" .wall_s): $(cat "$d") s" >> "$work/table.md"
  done
  python3 - "$work.ledger" "$work.run.json" >> "$work/table.md" <<'EOF'
import glob, json, sys
rep = unrep = charge = 0.0
for f in glob.glob(sys.argv[1] + "/*.json"):
    e = json.load(open(f))
    c = float(e.get("cost_usd") or 0)
    rep += c
    unrep += int(e.get("cost_unreported_calls") or 0)
    charge += float(e.get("guard_charge_usd", c))
try:
    guard = json.load(open(sys.argv[2]))["run_budget_usd"]
except (OSError, ValueError, KeyError):
    guard = "unknown"
print(f"\nRun spend (sum of provider-reported cost): ${rep:.4f}; calls with unreported cost: {int(unrep)}; "
      f"guard charge ${charge:.4f} of ${guard}")
EOF
  for d in $(ls -d "$work"/seed* 2>/dev/null | grep -E '/seed[0-9]+$' | sort -V); do
    echo -e "\n${d##*/}:" >> "$work/table.md"
    python3 "$repo/tools/log_check.py" "$d" >> "$work/table.md"
  done
  cat "$work/table.md"
}

[ "$PHASE" = collect ] || { [ -n "${AGENT_IMAGE:-}" ] || die "set AGENT_IMAGE"; run_phase; }
[ "$PHASE" = run ] || collect_phase
