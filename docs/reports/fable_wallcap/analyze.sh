#!/usr/bin/env bash
# Brief 21 / 23 analysis: the Fable wall-cap rerun of the 17 wall-capped ids, EXPLORATORY AND INCOMPLETE. Run from the repo
# root; committed tools only. Two dispatches (1,500 s cap), merged by tools/fable_wallcap.py merge (first valid row per
# problem; a plan-limit or error stop is never an attempt). 12 of 17 have a valid row; 5 do not. No 86 score is computed
# from incomplete data: only bounds.
set -euo pipefail
O=docs/reports/fable_wallcap
L=docs/reports/claude_code/runs/claude-fable-5-1.csv      # the ladder's Fable 5.1 run, 480 s cap on every problem
python3 tools/fable_wallcap.py merge "$O/runs/fable_1500s_merged.csv" "$O"/runs/dispatch1_41224141945.csv \
  "$O"/runs/dispatch2_41369146552.csv | tee "$O/merge.txt"
python3 - "$L" "$O/runs/fable_1500s_merged.csv" tools/fable_wallcap_ids.txt tools/m3b_eval_ids.txt > "$O/bounds.md" <<'EOF'
import csv, sys
ids = lambda p: [l.strip() for l in open(p) if l.strip() and not l.startswith("#")]
L = {r["id"]: r for r in csv.DictReader(open(sys.argv[1]))}
M = {r["id"]: r for r in csv.DictReader(open(sys.argv[2]))}
cap, e86 = ids(sys.argv[3]), ids(sys.argv[4])
meas = [i for i in cap if i in M]
un = [i for i in cap if i not in M]
rest = sum(L[i]["pass"] == "1" for i in e86 if i not in cap)
new = sum(M[i]["pass"] == "1" for i in meas)
print("| Row set | Problems | Ladder (480 s cap) passed | Rerun (1,500 s cap) passed |\n|---|---|---|---|")
print(f"| measured | {len(meas)} | {sum(L[i]['pass'] == '1' for i in meas)} | {new} |")
print(f"| not measured | {len(un)} | {sum(L[i]['pass'] == '1' for i in un)} | – |")
print(f"| the other {len(e86) - len(cap)} of the 86 (unchanged) | {len(e86) - len(cap)} | {rest} | – |\n")
print(f"Bounds on Fable's score on the 86 with the rerun's rows (not a score): {rest + new} to {rest + new + len(un)} of "
      f"{len(e86)} ({100 * (rest + new) / len(e86):.1f}% to {100 * (rest + new + len(un)) / len(e86):.1f}%), "
      f"against the ladder's {sum(L[i]['pass'] == '1' for i in e86)}. The lower bound counts the {len(un)} unmeasured as failed, "
      f"the upper as passed.\n")
print("| Problem | Ladder | Rerun | Stop | Wall s | Dispatch |\n|---|---|---|---|---|---|")
for i in cap:
    if i in M:
        r = M[i]; print(f"| `{i}` | {L[i]['pass']} | {r['pass']} | {r['stop_reason']} | {r['wall_time_s']} | {r['dispatch']} |")
    else:
        print(f"| `{i}` | {L[i]['pass']} | not measured | – | – | – |")
EOF
