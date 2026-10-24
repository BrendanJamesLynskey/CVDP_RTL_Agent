#!/usr/bin/env bash
# Run the agent image on a split (or a list of ids) through the CVDP harness, then collect and tabulate.
# Used by .github/workflows/sweep.yml; runs the same way locally.
#
#   bash tools/sweep.sh [all|run|collect]     (default all; the workflow runs `run` and `collect` as separate steps,
#                                              so collection still happens when the run step times out)
#
# SEED_OFFSET=m numbers the seeds m+1 … m+n (CVDP_SEED, work dirs, the seed column), so two dispatches of the same
# settings pool with distinct seeds.
# SEEDS=n runs the same problem list n times, one after another, each in its own work dir ($WORK/seed<k>) and its
# own harness invocation, with CVDP_SEED=<k> passed to the agent (a label only: sampling is not seeded). One ledger
# ($WORK.ledger) is shared by every seed, so the whole-run spend guard covers the whole job.
#
# A seed is started only if the step has time for its worst case (STEP_BUDGET_S, counted from when this script
# starts; blank = no limit): the harness writes raw_result.json only when a run ends, so a seed killed part-way
# loses every problem it finished while its spend stays in the ledger. Worst case = ceil(problems / threads) x
# SEED_PROBLEM_WORST_S (default 660: the harness's 600 s agent timeout plus the tests) + 300 s. A seed not started
# is listed in table.md. Each seed's UTC start and end go into $WORK.run.json and table.md.
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
SEED_OFFSET=${SEED_OFFSET:-0}
PROVIDER_ORDER=${PROVIDER_ORDER:-}   # OpenRouter providers, comma-separated, tried in order with no fallbacks
HARNESS=${HARNESS:-langgraph}        # langgraph (the M1-M3 agent) | deepagents (M3b)
MEMORY=${MEMORY:-}                   # a lessons snapshot in the repo (tools/learn_lessons.py); blank = none
STEP_BUDGET_S=${STEP_BUDGET_S:-}
SEED_PROBLEM_WORST_S=${SEED_PROBLEM_WORST_S:-660}
T0=$(date +%s)
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
[[ "$SEED_OFFSET" =~ ^[0-9]+$ ]] || die "SEED_OFFSET must be a non-negative integer, got '$SEED_OFFSET'"
case "$REASONING" in
  default|low|medium|high|off) ;;
  *) die "REASONING must be default, low, medium, high or off, got '$REASONING'" ;;
esac
[ -z "$RUN_BUDGET_USD" ] || num RUN_BUDGET_USD "$RUN_BUDGET_USD"
[ -z "$STEP_BUDGET_S" ] || int STEP_BUDGET_S "$STEP_BUDGET_S"
int SEED_PROBLEM_WORST_S "$SEED_PROBLEM_WORST_S"
[[ "$PROVIDER_ORDER" =~ ^[A-Za-z0-9\ ._,/-]*$ ]] || die "PROVIDER_ORDER has unexpected characters: '$PROVIDER_ORDER'"
case "$HARNESS" in langgraph|deepagents) ;; *) die "HARNESS must be langgraph or deepagents, got '$HARNESS'" ;; esac
if [ -n "$MEMORY" ]; then
  [[ "$MEMORY" =~ ^[A-Za-z0-9._/-]+\.json$ ]] || die "MEMORY must be a path to a .json snapshot, got '$MEMORY'"
  [ -f "$MEMORY" ] || die "MEMORY: no such file '$MEMORY'"
fi
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
  printf '{"problems": %s, "seeds": %s, "seed_offset": %s, "run_budget_usd": %s, "model": "%s", "reasoning": "%s", "provider_order": "%s"}\n' \
    "$n" "$SEEDS" "$SEED_OFFSET" "$guard" "$MODEL" "$REASONING" "$PROVIDER_ORDER" > "$work.run.json"
  python3 - "$work.run.json" "$HARNESS" "$MEMORY" <<'EOF'
import json, sys
run = json.load(open(sys.argv[1]))
run.update(harness=sys.argv[2], memory=sys.argv[3])
json.dump(run, open(sys.argv[1], "w"))
EOF

  if [ "$MODEL" = fake ]; then export CVDP_PROVIDER=fake; else export CVDP_PROVIDER=openrouter; fi
  export CVDP_MODEL="$MODEL" CVDP_BUDGET_USD="$BUDGET_USD" CVDP_MAX_TURNS="$MAX_TURNS" CVDP_SELF_CHECK="$SELF_CHECK" \
    CVDP_LINT="$LINT" CVDP_LEDGER_DIR=/ledger CVDP_RUN_BUDGET_USD="$guard" CVDP_REASONING="$REASONING" \
    CVDP_PROVIDER_ORDER="$PROVIDER_ORDER" CVDP_HARNESS="$HARNESS"
  export CVDP_AGENT_MOUNTS="$ledger:/ledger"
  if [ -n "$MEMORY" ]; then  # the snapshot, read-only, at /memory/<its name> in the agent's container
    export CVDP_MEMORY="/memory/$(basename "$MEMORY")"
    export CVDP_AGENT_MOUNTS="$CVDP_AGENT_MOUNTS,$(cd "$(dirname "$MEMORY")" && pwd)/$(basename "$MEMORY"):$CVDP_MEMORY:ro"
  fi
  export CVDP_AGENT_ENV=CVDP_PROVIDER,CVDP_MODEL,CVDP_BUDGET_USD,CVDP_MAX_TURNS,CVDP_SELF_CHECK,CVDP_LINT,CVDP_LEDGER_DIR,CVDP_RUN_BUDGET_USD,CVDP_REASONING,CVDP_SEED,CVDP_PROVIDER_ORDER,CVDP_HARNESS,CVDP_MEMORY
  if [ "$CVDP_PROVIDER" = openrouter ]; then
    test -n "${OPENROUTER_API_KEY:-}" || die "OPENROUTER_API_KEY is not set"
    export CVDP_AGENT_ENV="OPENROUTER_API_KEY,$CVDP_AGENT_ENV"
  fi
  echo "run budget guard: \$$guard (all $SEEDS seed(s))"

  local worst left skip=""
  worst=$(( (n + THREADS - 1) / THREADS * SEED_PROBLEM_WORST_S + 300 ))
  for seed in $(seq $((SEED_OFFSET + 1)) $((SEED_OFFSET + SEEDS))); do
    if [ -z "$skip" ] && [ -n "$STEP_BUDGET_S" ]; then
      left=$(( T0 + STEP_BUDGET_S - $(date +%s) ))
      [ "$left" -ge "$worst" ] || skip="the step had ${left} s left, under this seed's worst case of ${worst} s"
    fi
    if [ -n "$skip" ]; then
      echo "$skip" > "$work/seed$seed.skipped"
      echo "seed $seed: not started: $skip"
      continue
    fi
    mkdir -p "$work/seed$seed"
    export CVDP_SEED=$seed
    start=$(date +%s)
    (cd "$CVDP_DIR" && ./run_benchmark.py -f "$subset" -l -g "$AGENT_IMAGE" -p "$work/seed$seed" -t "$THREADS") || true
    python3 - "$work.run.json" "$seed" "$start" "$(date +%s)" <<'EOF'
import datetime, json, sys
path, seed, start, end = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
iso = lambda t: datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
run = json.load(open(path))
run.setdefault("seed_runs", {})[seed] = {"start_utc": iso(start), "end_utc": iso(end), "wall_s": end - start}
json.dump(run, open(path, "w"), indent=1)
print(f"seed {seed}: {iso(start)} to {iso(end)}, harness wall time {end - start} s")
EOF
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
        --model "$MODEL" --seed "$seed" --reasoning "$REASONING" $hdr >> "$work/results.csv"
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
  python3 - "$work.run.json" "$work" >> "$work/table.md" <<'EOF'
import glob, json, os, sys
try:
    run = json.load(open(sys.argv[1]))
except (OSError, ValueError):
    run = {}
for seed, t in sorted(run.get("seed_runs", {}).items(), key=lambda kv: int(kv[0])):
    print(f"\nSeed {seed}: {t['start_utc']} to {t['end_utc']}, harness wall time {t['wall_s']} s")
for f in sorted(glob.glob(os.path.join(sys.argv[2], "seed*.skipped"))):
    print(f"\n**{os.path.basename(f)[:-8].replace('seed', 'Seed ')}: not started**: {open(f).read().strip()}")
if run.get("provider_order"):
    print(f"\nProvider order pinned: {run['provider_order']}")
EOF
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
