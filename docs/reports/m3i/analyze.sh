#!/usr/bin/env bash
# M3i analysis: run from the repo root. D = M3h's arm A (reused, cc_profile=default), P = the plain profile.
# Held-out: D = M3h's A1-A3. The 86 (development set, one run per arm, descriptive): D = M3h's A run 41507899046.
set -euo pipefail
O=docs/reports/m3i
M=docs/reports/m3h/runs
D=$(ls $M/heldout_A[0-9]_*.csv | paste -sd,)
P=$(ls $O/runs/heldout_P[0-9]_*.csv | paste -sd,)
python3 tools/ablate.py --arm D=$D --arm P=$P --base D --ids tools/m3g_heldout_ids.txt > $O/heldout_paired.md
D86=$(ls $M/dev86_A_*.csv)
P86=$(ls $O/runs/dev86_P_*.csv)
python3 tools/ablate.py --arm D=$D86 --arm P=$P86 --base D --ids tools/m3b_eval_ids.txt > $O/dev86_paired.md
python3 tools/ablate.py --arm D=$D86 --arm P=$P86 --base D --ids tools/m3b_eval_ids.txt \
  --exclude tools/benchmark_limited_ids.txt > $O/dev79_paired.md
python3 tools/m3h_tables.py --arm D=$D86 --arm P=$P86 --ids tools/m3b_eval_ids.txt > $O/dev86_effort.md
python3 tools/taxonomy.py --arm dev86_D=$D86 --arm dev86_P=$P86 > $O/taxonomy_dev86.md
