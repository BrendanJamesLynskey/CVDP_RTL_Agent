#!/usr/bin/env bash
# Run the agent image on a split (or a list of ids) through the CVDP harness, then collect and tabulate.
# Used by .github/workflows/sweep.yml; runs the same way locally.
#
# Needs: the harness checked out in $CVDP_DIR (with its requirements installed and .env set), the dataset in
# $DATA_DIR, nvidia/cvdp-sim:v1.0.0 and $AGENT_IMAGE in the local Docker.
# The API key, when needed, is read from OPENROUTER_API_KEY and reaches the agent only through CVDP_AGENT_ENV.
set -euo pipefail

: "${AGENT_IMAGE:?set AGENT_IMAGE}"
SPLIT=${SPLIT:-agentic}
IDS=${IDS:-}
MODEL=${MODEL:-fake}
BUDGET_USD=${BUDGET_USD:-0.10}
MAX_TURNS=${MAX_TURNS:-10}
SELF_CHECK=${SELF_CHECK:-1}
LINT=${LINT:-1}
THREADS=${THREADS:-2}
WORK=${WORK:-work}
CVDP_DIR=${CVDP_DIR:-cvdp}
DATA_DIR=${DATA_DIR:-data}

repo=$(cd "$(dirname "$0")/.." && pwd)
case "$SPLIT" in
  agentic) src="$DATA_DIR/agentic_code_generation_no_commercial.jsonl" ;;
  heavy) src="$DATA_DIR/agentic_heavy_code_generation_no_commercial.jsonl" ;;
  *) echo "unknown split $SPLIT" >&2; exit 2 ;;
esac

mkdir -p "$WORK"
WORK=$(cd "$WORK" && pwd)
subset="$WORK.problems.jsonl"
n=$(python3 "$repo/tools/subset.py" "$src" "$IDS" "$subset")
echo "problems: $n"

# Whole-run spend guard: each agent adds its cost to the ledger, and an agent that starts once the ledger has
# passed budget x problems x 1.2 stops before its first LLM call.
ledger="$WORK.ledger"
mkdir -p "$ledger"

if [ "$MODEL" = fake ]; then export CVDP_PROVIDER=fake; else export CVDP_PROVIDER=openrouter; fi
export CVDP_MODEL="$MODEL" CVDP_BUDGET_USD="$BUDGET_USD" CVDP_MAX_TURNS="$MAX_TURNS" CVDP_SELF_CHECK="$SELF_CHECK" \
  CVDP_LINT="$LINT" CVDP_LEDGER_DIR=/ledger
export CVDP_RUN_BUDGET_USD=$(python3 -c "print(round($BUDGET_USD * $n * 1.2, 6))")
export CVDP_AGENT_MOUNTS="$ledger:/ledger"
export CVDP_AGENT_ENV=CVDP_PROVIDER,CVDP_MODEL,CVDP_BUDGET_USD,CVDP_MAX_TURNS,CVDP_SELF_CHECK,CVDP_LINT,CVDP_LEDGER_DIR,CVDP_RUN_BUDGET_USD
if [ "$CVDP_PROVIDER" = openrouter ]; then
  test -n "${OPENROUTER_API_KEY:-}" || { echo "OPENROUTER_API_KEY is not set" >&2; exit 2; }
  export CVDP_AGENT_ENV="OPENROUTER_API_KEY,$CVDP_AGENT_ENV"
fi
echo "run budget guard: \$$CVDP_RUN_BUDGET_USD"

start=$(date +%s)
(cd "$CVDP_DIR" && ./run_benchmark.py -f "$subset" -l -g "$AGENT_IMAGE" -p "$WORK" -t "$THREADS") || true
echo "harness wall time: $(( $(date +%s) - start )) s"

python3 "$repo/tools/collect.py" "$WORK" --dataset "$subset" --runner "${RUNNER:-local}" > "$WORK/results.csv"
python3 "$repo/tools/table.py" "$WORK/results.csv" > "$WORK/table.md"
python3 -c "
import glob, json
total = sum(float(json.load(open(f)).get('cost_usd') or 0) for f in glob.glob('$ledger/*.json'))
print(f'Run spend (sum of provider-reported cost): \${total:.4f}; guard \$$CVDP_RUN_BUDGET_USD')
" >> "$WORK/table.md"
cat "$WORK/table.md"
