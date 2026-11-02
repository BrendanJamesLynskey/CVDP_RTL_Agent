#!/usr/bin/env bash
# M3h analysis, as pre-registered: run from the repo root. Uses only committed light tools. The run CSVs in runs/ are
# already merged (tools/m3h_merge.py: a rate-limited row replaced by its rerun's row); ablate.py leaves out any row
# still rate-limited. Held-out phase first; the 86's lines (dev86_*) come after it.
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
# The 86 (development set; one run per arm, descriptive): paired against A, the 79 view (7 benchmark-limited left out),
# S2c - S1c, the skill tables, the failure taxonomy
E=tools/m3b_eval_ids.txt
DA=$(ls $O/runs/dev86_A_*.csv | paste -sd,)
DS1C=$(ls $O/runs/dev86_S1c_*.csv | paste -sd,)
DS2C=$(ls $O/runs/dev86_S2c_*.csv | paste -sd,)
python3 tools/ablate.py --arm A=$DA --arm S1c=$DS1C --arm S2c=$DS2C --base A --ids $E > $O/dev86_paired.md
python3 tools/ablate.py --arm A=$DA --arm S1c=$DS1C --arm S2c=$DS2C --base A --ids $E \
  --exclude tools/benchmark_limited_ids.txt > $O/dev79_paired.md
python3 tools/ablate.py --arm S1c=$DS1C --arm S2c=$DS2C --base S1c --ids $E > $O/dev86_paired_S2c_S1c.md
python3 tools/taxonomy.py --arm dev86_A=$DA --arm dev86_S1c=$DS1C --arm dev86_S2c=$DS2C > $O/taxonomy_dev86.md
python3 tools/m3h_tables.py --arm A=$DA --arm S1c=$DS1C --arm S2c=$DS2C --ids $E > $O/tables_dev86.md
# The old ladder's Haiku run on the 86, for reference only (not a comparison arm)
python3 tools/ablate.py --arm A=$DA --arm "ladder Haiku=docs/reports/claude_code/runs/claude-haiku-5-5.csv" --base A \
  --ids $E > $O/dev86_vs_ladder.md
# Local only (needs the private pack checkout and the downloaded artifacts; writes names and counts only):
#   python3 tools/m3h_copied.py --pack <v2.0 generic/> --public <dataset dir> \
#     --arm "S1c:300=<S1c artifact dirs>,<withheld_S1c*.csv>" --arm "S2c:300=..." --arm "S2 (no hint):100=..." \
#     --arm "A (no pack installed; control for chance matches):300=<A artifact dirs>"  -> copied_heldout.md
