#!/usr/bin/env bash
# M3l analysis: run from the repo root. Primary (the only one, amended 2026-11-09): E - R over the 16 problems that get
# an example (3 held-out + 13 dev), 5 runs per arm, against a fresh R. Everything else is descriptive.
set -euo pipefail
O=docs/reports/m3l
J=$O/runs
IDS=$O/ids16.txt
cat tools/m3l_fires_heldout_ids.txt tools/m3l_fires_dev_ids.txt > $IDS
R=$J/dev_R_42545543795.csv,$J/heldout_R_42545563498.csv
E=$J/dev_E_42545534466.csv,$J/heldout_E_42545553518.csv
python3 tools/ablate.py --arm R=$R --arm E=$E --base R --ids $IDS > $O/paired16.md
# sensitivity: without hdbn_codec_0001, where 2 of E's 5 runs ended in llm_error (counted as fails above)
echo cvdp_agentic_hdbn_codec_0001 > $O/llm_error_ids.txt
python3 tools/ablate.py --arm R=$R --arm E=$E --base R --ids $IDS --exclude $O/llm_error_ids.txt > $O/paired15.md
python3 $O/analyze_tables.py $IDS tools/m3l_fires_heldout_ids.txt $E $R > $O/tables16.md
python3 tools/taxonomy.py --arm R16=$R --arm E16=$E > $O/taxonomy16.md
