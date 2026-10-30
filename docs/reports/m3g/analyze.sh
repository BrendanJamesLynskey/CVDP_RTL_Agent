#!/usr/bin/env bash
# M3g analysis, as pre-registered: run from the repo root. Uses only committed light tools.
set -euo pipefail
O=docs/reports/m3g
HA=$(ls $O/runs/heldout_A*.csv | paste -sd,)
HK=$(ls $O/runs/heldout_K*.csv | paste -sd,)
DA=$(ls docs/reports/m3d/runs/A*.csv | paste -sd,)   # M3d's arm A: the development-set base
DK=$(ls $O/runs/dev_K*.csv | paste -sd,)
# primary: K - A on the held-out 100
python3 tools/ablate.py --arm A=$HA --arm K=$HK --base A --ids tools/m3g_heldout_ids.txt \
  --pareto-csv $O/pareto_heldout.csv --pareto-svg $O/pareto_heldout.svg > $O/heldout_paired.md
# secondary: K - A on the 86 (development set) and the 79-problem view
python3 tools/ablate.py --arm A=$DA --arm K=$DK --base A --ids tools/m3b_eval_ids.txt > $O/dev_paired_eval86.md
python3 tools/ablate.py --arm A=$DA --arm K=$DK --base A --ids tools/m3b_eval_ids.txt \
  --exclude tools/benchmark_limited_ids.txt > $O/dev_paired_eval79.md
python3 tools/taxonomy.py --arm heldout_A=$HA --arm heldout_K=$HK > $O/taxonomy_heldout.md
python3 tools/taxonomy.py --arm dev_A=$DA --arm dev_K=$DK > $O/taxonomy_dev.md
python3 tools/m3g_tables.py --arm A=$HA --arm K=$HK --ids tools/m3g_heldout_ids.txt > $O/tables_heldout.md
python3 tools/m3g_tables.py --arm A=$DA --arm K=$DK --ids tools/m3b_eval_ids.txt > $O/tables_dev.md
