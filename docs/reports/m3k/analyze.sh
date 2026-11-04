#!/usr/bin/env bash
# M3k analysis: run from the repo root. R = M3j's arm R (reused, not rerun); T and K from this milestone.
# Primary (the only one): T - R on the held-out set. K - R is exploratory. The 86: one run per arm, descriptive.
set -euo pipefail
O=docs/reports/m3k
J=$O/runs
M=docs/reports/m3j/runs
T=$(ls $J/heldout_T[0-9]_*.csv | paste -sd,)
K=$(ls $J/heldout_K[0-9]_*.csv | paste -sd,)
R=$(ls $M/heldout_R[0-9]*_*.csv | paste -sd,)
IDS=tools/m3g_heldout_ids.txt
python3 tools/ablate.py --arm R=$R --arm T=$T --arm K=$K --base R --ids $IDS > $O/heldout_paired.md
python3 tools/m3h_tables.py --arm R=$R --arm T=$T --arm K=$K --ids $IDS > $O/heldout_effort.md
R86=$M/dev86_R_merged.csv; T86=$(ls $J/dev86_T_*.csv); K86=$(ls $J/dev86_K_*.csv)
E=tools/m3b_eval_ids.txt
python3 tools/ablate.py --arm R=$R86 --arm T=$T86 --arm K=$K86 --base R --ids $E > $O/dev86_paired.md
python3 tools/ablate.py --arm R=$R86 --arm T=$T86 --arm K=$K86 --base R --ids $E \
  --exclude tools/benchmark_limited_ids.txt > $O/dev79_paired.md
python3 tools/m3h_tables.py --arm R=$R86 --arm T=$T86 --arm K=$K86 --ids $E > $O/dev86_effort.md
python3 tools/taxonomy.py --arm dev86_R=$R86 --arm dev86_T=$T86 --arm dev86_K=$K86 > $O/taxonomy_dev86.md
python3 tools/taxonomy.py --arm held_R=$R --arm held_T=$T --arm held_K=$K > $O/taxonomy_heldout.md
# the 86 without the two problems that had an llm_error row (not run) in T or K
python3 tools/ablate.py --arm R=$R86 --arm T=$T86 --arm K=$K86 --base R --ids $E --exclude $O/dev86_not_run_ids.txt > $O/dev84_paired.md
