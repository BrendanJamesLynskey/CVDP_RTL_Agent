#!/usr/bin/env bash
# M3j analysis: run from the repo root. PA, B, R from this milestone; P = M3i's plain profile (plan), D = M3i's arm D
# (M3h's arm A, Claude Code as shipped), both reused. Held-out seeds 1-2 and seed 3 are separate dispatches.
# The 86 (one run per arm, descriptive): R's 30 guard-stopped rows (no model call) rerun and merged by m3h_merge.py.
set -euo pipefail
O=docs/reports/m3j
J=$O/runs
I=docs/reports/m3i/runs
H=docs/reports/m3h/runs
PA=$(ls $J/heldout_PA[0-9]*_*.csv | paste -sd,)
B=$(ls $J/heldout_B[0-9]*_*.csv | paste -sd,)
R=$(ls $J/heldout_R[0-9]*_*.csv | paste -sd,)
P=$(ls $I/heldout_P[0-9]_*.csv | paste -sd,)
D=$(ls $H/heldout_A[0-9]_*.csv | paste -sd,)
IDS=tools/m3g_heldout_ids.txt
python3 tools/ablate.py --arm PA=$PA --arm B=$B --arm R=$R --base PA --ids $IDS > $O/heldout_paired.md
python3 tools/ablate.py --arm P=$P --arm PA=$PA --base P --ids $IDS > $O/heldout_PA_vs_P.md
python3 tools/ablate.py --arm D=$D --arm R=$R --base D --ids $IDS > $O/heldout_R_vs_D.md
python3 tools/m3h_merge.py $J/dev86_R_first_*.csv $J/dev86_R_rerun_*.csv > $J/dev86_R_merged.csv
PA86=$(ls $J/dev86_PA_*.csv); B86=$(ls $J/dev86_B_*.csv); R86=$J/dev86_R_merged.csv
P86=$(ls $I/dev86_P_*.csv); D86=$(ls $H/dev86_A_*.csv)
E=tools/m3b_eval_ids.txt
python3 tools/ablate.py --arm PA=$PA86 --arm B=$B86 --arm R=$R86 --arm P=$P86 --arm D=$D86 --base PA --ids $E > $O/dev86_paired.md
python3 tools/ablate.py --arm PA=$PA86 --arm B=$B86 --arm R=$R86 --arm P=$P86 --arm D=$D86 --base PA --ids $E \
  --exclude tools/benchmark_limited_ids.txt > $O/dev79_paired.md
python3 tools/m3h_tables.py --arm PA=$PA86 --arm B=$B86 --arm R=$R86 --ids $E > $O/dev86_effort.md
python3 tools/taxonomy.py --arm dev86_PA=$PA86 --arm dev86_B=$B86 --arm dev86_R=$R86 > $O/taxonomy_dev86.md
