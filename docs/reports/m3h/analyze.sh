#!/usr/bin/env bash
# M3h analysis, as pre-registered: run from the repo root. Uses only committed light tools. The run CSVs in runs/ are
# already merged (tools/m3h_merge.py: a rate-limited row replaced by its rerun's row); ablate.py leaves out any row
# still rate-limited. Held-out phase only so far; the 86's lines are added when that phase has run.
set -euo pipefail
O=docs/reports/m3h
H=tools/m3g_heldout_ids.txt
HA=$(ls $O/runs/heldout_A[0-9]_*.csv | paste -sd,)
HS1C=$(ls $O/runs/heldout_S1c[0-9]_*.csv | paste -sd,)
HS2C=$(ls $O/runs/heldout_S2c[0-9]_*.csv | paste -sd,)
HS2=$(ls $O/runs/heldout_S2_*.csv | paste -sd,)
# primary: S2c - A on the held-out 100 (and the secondary S1c - A, from the same call)
python3 tools/ablate.py --arm A=$HA --arm S1c=$HS1C --arm S2c=$HS2C --base A --ids $H > $O/heldout_paired.md
# secondary: S2c - S1c on the held-out 100 (v2's ten new skills under the same hint)
python3 tools/ablate.py --arm S1c=$HS1C --arm S2c=$HS2C --base S1c --ids $H > $O/heldout_paired_S2c_S1c.md
python3 tools/taxonomy.py --arm heldout_A=$HA --arm heldout_S1c=$HS1C --arm heldout_S2c=$HS2C --arm heldout_S2=$HS2 \
  > $O/taxonomy_heldout.md
python3 tools/m3h_tables.py --arm A=$HA --arm S1c=$HS1C --arm S2c=$HS2C --arm "S2 (no hint, 1 run)=$HS2" --ids $H \
  > $O/tables_heldout.md
