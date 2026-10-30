#!/usr/bin/env bash
# M3e analysis: run from the repo root. Uses only committed light tools.
set -euo pipefail
O=docs/reports/m3e
A=$(ls docs/reports/m3d/runs/A*.csv | paste -sd,)
CCO=docs/reports/claude_code/runs/claude-opus-5-5.csv
CCS=docs/reports/claude_code/runs/claude-sonnet-5-5.csv
LGO=$O/runs/LG_opus_41040802008.csv
arms="--arm LG+luna=$A --arm LG+Opus=$LGO --arm CC+Opus=$CCO --arm CC+Sonnet=$CCS"
# views: attempted67 (primary), attempted minus benchmark-limited (63), full 86 (refused counted as failures)
for v in attempted67 attempted63 full86_refused_as_fail; do
  case $v in
    attempted67) ids=$O/attempted_ids.txt; ex="" ;;
    attempted63) ids=$O/attempted_ids.txt; ex="--exclude tools/benchmark_limited_ids.txt" ;;
    full86_refused_as_fail) ids=tools/m3b_eval_ids.txt; ex="" ;;
  esac
  python3 tools/ablate.py $arms --base LG+luna --ids $ids $ex > $O/vs_luna_$v.md
  python3 tools/ablate.py --arm LG+Opus=$LGO --arm CC+Opus=$CCO --base LG+Opus --ids $ids $ex > $O/harness_opus_$v.md
done
python3 tools/ablate.py --arm LG+luna=$A --arm LG+Opus=$LGO --base LG+luna --ids $O/attempted_ids.txt \
  --pareto-csv $O/pareto.csv --pareto-svg $O/pareto.svg > /dev/null
python3 tools/taxonomy.py $arms > $O/taxonomy_by_arm_all_rows.md
python3 tools/m3d_tables.py $arms --ids $O/attempted_ids.txt | awk '/^#### The verify step/{exit} {print}' > $O/secondary_tables_attempted67.md
# ---- brief 14b: the full 86-problem LG+Opus arm, merged from three dispatches (41040802008's 67 attempted rows,
# 41095517652's 13 attempted rows, 41097171384's 6 rows); the raw CSVs of the two finishing runs are in finish/.
LGO86=$O/full86/LG_opus_41040802008+41095517652+41097171384.csv
arms86="--arm LG+luna=$A --arm LG+Opus=$LGO86 --arm CC+Opus=$CCO --arm CC+Sonnet=$CCS"
for v in eval86 eval79; do
  case $v in
    eval86) ex="" ;;
    eval79) ex="--exclude tools/benchmark_limited_ids.txt" ;;
  esac
  python3 tools/ablate.py $arms86 --base LG+luna --ids tools/m3b_eval_ids.txt $ex > $O/vs_luna_$v.md
  python3 tools/ablate.py --arm LG+Opus=$LGO86 --arm CC+Opus=$CCO --base LG+Opus --ids tools/m3b_eval_ids.txt $ex > $O/harness_opus_$v.md
done
python3 tools/ablate.py --arm LG+luna=$A --arm LG+Opus=$LGO86 --base LG+luna --ids tools/m3b_eval_ids.txt \
  --pareto-csv $O/pareto_eval86.csv --pareto-svg $O/pareto_eval86.svg > /dev/null
python3 tools/taxonomy.py $arms86 > $O/taxonomy_by_arm_eval86.md
python3 tools/m3d_tables.py $arms86 --ids tools/m3b_eval_ids.txt | awk '/^#### The verify step/{exit} {print}' > $O/secondary_tables_eval86.md
