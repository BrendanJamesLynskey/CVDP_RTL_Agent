# M4: failures by task category

**Status: done (2026-11-09).** Analysis only: no sweep, no model call. Every number is computed by
`docs/reports/m4/categories.py` from the committed run CSVs (rerun it from the repo root). Raw cells are in
`categories_groups.csv`; the site chart reads `categories_data.json`.

## In short

- **No category is uniformly hard for our agents.** On the 86 development problems, every model and agent we ran
  solves between about half and nine in ten of each category. The weakest category changes with the model: bug
  fixing (cid016) for `gpt-6-luna` in the LangGraph agent (50.5%, n = 99) and for Fable in Claude Code (64%),
  RTL modification (cid004) for Haiku and Sonnet in Claude Code (58% each), module reuse (cid005) for Opus in
  Claude Code (61%). Single-run cells hold 11 to 33 problems, so most gaps between categories are inside the
  intervals.
- **On the held-out 100, RTL completion (cid002) is the weakest category** for every arm we ran: 40% to 50%
  against 60% to 72% for spec to RTL (cid003). It also holds the most problems no run solved: 13 of 42.
- **Where the failures are depends on the category.** Bug fixing fails differently: for `gpt-6-luna` in the
  LangGraph agent, the agent's own testbench had passed in 22 of 49 failed bug-fixing rows. In spec to RTL, the
  hidden build failed on an interface mismatch in 28 of 119 failed rows. Everywhere else the biggest label is
  that the agent never ran a testbench.
- **This split cannot test the paper's central category finding.** It has no verification-writing categories
  (testbench stimulus, checkers, assertions: cid012 to cid014). See "What is missing".

## Method

- **Groups.** One group is one milestone's arm, on one problem set, with one model and harness. Seeds of the same
  arm are pooled. Groups are not pooled with each other, because arms differ on purpose. The pass-rate table
  shows every group.
- **Sets stay apart.** dev 86 (`tools/m3b_eval_ids.txt`), held-out 100 (`tools/m3g_heldout_ids.txt`) and the M2 92
  (the 92 agentic problems of M2 and M3). A pass rate is never compared across sets. Rows whose problem is not in
  the group's set are dropped (some M3h and M3i dev files carry the 6 problems outside the 86).
- **Left out.** Pilots (M1's 10, the reasoning pick, M2a), smoke runs, M3b's runs on excluded problems, M3l's
  13-problem and 3-problem subsets, and Fable's wall-cap reruns (a 30-problem top-up of the Claude Code run).
  M3e's Opus run is the merged 86 where the problems the cost guard refused count as failures.
- **Cells.** passed/n = rate [Wilson 95% interval]. n counts problem-runs, so a three-seed group has three times
  the problems. Seeds of one problem are not independent, so the interval for a pooled cell is narrower than the
  truth.
- **Categories in the free split.** cid002 RTL completion (held-out only), cid003 spec to RTL, cid004 RTL
  modification, cid005 spec to RTL with module reuse (agentic only), cid016 bug fixing (agentic only). The
  paper writes these as cid02, cid03 and so on.
- **Labels.** `failure_label` from `tools/taxonomy.py`: deterministic rules on the logs, no model reads anything.
  M2 CSVs predate the labels, so label tables use the groups from M3 on.

## Results

### Pass rate by category: dev 86

| Milestone | Model and harness | Arm | cid003 spec to RTL | cid004 RTL modification | cid005 spec to RTL, module reuse | cid016 bug fixing | All |
|---|---|---|---|---|---|---|---|
| M3b | OpenAI gpt-6-luna, LangGraph agent | A LangGraph, no memory | 178/297 = 59.9% [54.3, 65.3] | 116/216 = 53.7% [47.0, 60.2] | 104/162 = 64.2% [56.6, 71.2] | 50/99 = 50.5% [40.8, 60.1] | 448/774 = 57.9% [54.4, 61.3] |
| M3b | OpenAI gpt-6-luna, Deep Agents harness | B Deep Agents, no memory | 184/297 = 62.0% [56.3, 67.3] | 128/216 = 59.3% [52.6, 65.6] | 111/162 = 68.5% [61.0, 75.2] | 60/99 = 60.6% [50.8, 69.7] | 483/774 = 62.4% [58.9, 65.7] |
| M3b | OpenAI gpt-6-luna, LangGraph agent | C LangGraph, lessons memory | 60/99 = 60.6% [50.8, 69.7] | 41/72 = 56.9% [45.4, 67.7] | 35/54 = 64.8% [51.5, 76.2] | 17/33 = 51.5% [35.2, 67.5] | 153/258 = 59.3% [53.2, 65.1] |
| M3b | OpenAI gpt-6-luna, Deep Agents harness | D Deep Agents, lessons memory | 60/99 = 60.6% [50.8, 69.7] | 46/72 = 63.9% [52.4, 74.0] | 39/54 = 72.2% [59.1, 82.4] | 23/33 = 69.7% [52.7, 82.6] | 168/258 = 65.1% [59.1, 70.7] |
| M3c | OpenAI gpt-6-luna, LangGraph agent | A base | 60/99 = 60.6% [50.8, 69.7] | 42/72 = 58.3% [46.8, 69.0] | 36/54 = 66.7% [53.4, 77.8] | 21/33 = 63.6% [46.6, 77.8] | 159/258 = 61.6% [55.6, 67.4] |
| M3c | OpenAI gpt-6-luna, LangGraph agent | I interface check | 64/99 = 64.6% [54.8, 73.4] | 40/72 = 55.6% [44.1, 66.5] | 34/54 = 63.0% [49.6, 74.6] | 17/33 = 51.5% [35.2, 67.5] | 155/258 = 60.1% [54.0, 65.9] |
| M3c | OpenAI gpt-6-luna, LangGraph agent | M mutation gate | 61/99 = 61.6% [51.8, 70.6] | 44/72 = 61.1% [49.6, 71.5] | 38/54 = 70.4% [57.2, 80.9] | 18/33 = 54.5% [38.0, 70.2] | 161/258 = 62.4% [56.4, 68.1] |
| M3d | OpenAI gpt-6-luna, LangGraph agent | A base | 61/99 = 61.6% [51.8, 70.6] | 41/72 = 56.9% [45.4, 67.7] | 35/54 = 64.8% [51.5, 76.2] | 20/33 = 60.6% [43.7, 75.3] | 157/258 = 60.9% [54.8, 66.6] |
| M3d | OpenAI gpt-6-luna, LangGraph agent | V verify before submit | 58/99 = 58.6% [48.7, 67.8] | 41/72 = 56.9% [45.4, 67.7] | 36/54 = 66.7% [53.4, 77.8] | 17/33 = 51.5% [35.2, 67.5] | 152/258 = 58.9% [52.8, 64.7] |
| M3d | OpenAI gpt-6-luna, LangGraph agent | S verify plus spec cases | 60/99 = 60.6% [50.8, 69.7] | 36/72 = 50.0% [38.7, 61.3] | 33/54 = 61.1% [47.8, 73.0] | 16/33 = 48.5% [32.5, 64.8] | 145/258 = 56.2% [50.1, 62.1] |
| M3e | Anthropic claude-opus-5.5 (low), LangGraph agent | LG, run refused by guard counted as fail | 24/33 = 72.7% [55.8, 84.9] | 16/24 = 66.7% [46.7, 82.0] | 12/18 = 66.7% [43.7, 83.7] | 10/11 = 90.9% [62.3, 98.4] | 62/86 = 72.1% [61.8, 80.5] |
| Claude Code ladder | Anthropic claude-haiku-5-5 (low), Claude Code | plan-signed-in | 20/33 = 60.6% [43.7, 75.3] | 14/24 = 58.3% [38.8, 75.5] | 14/18 = 77.8% [54.8, 91.0] | 9/11 = 81.8% [52.3, 94.9] | 57/86 = 66.3% [55.8, 75.4] |
| Claude Code ladder | Anthropic claude-sonnet-5-5 (low), Claude Code | plan-signed-in | 24/33 = 72.7% [55.8, 84.9] | 14/24 = 58.3% [38.8, 75.5] | 13/18 = 72.2% [49.1, 87.5] | 9/11 = 81.8% [52.3, 94.9] | 60/86 = 69.8% [59.4, 78.5] |
| Claude Code ladder | Anthropic claude-opus-5-5 (low), Claude Code | plan-signed-in | 28/33 = 84.8% [69.1, 93.3] | 16/24 = 66.7% [46.7, 82.0] | 11/18 = 61.1% [38.6, 79.7] | 8/11 = 72.7% [43.4, 90.3] | 63/86 = 73.3% [63.1, 81.5] |
| Claude Code ladder | Anthropic claude-fable-5-1 (low), Claude Code | plan-signed-in | 22/33 = 66.7% [49.6, 80.2] | 16/24 = 66.7% [46.7, 82.0] | 13/18 = 72.2% [49.1, 87.5] | 7/11 = 63.6% [35.4, 84.8] | 58/86 = 67.4% [57.0, 76.4] |
| M3g | OpenAI gpt-6-luna, LangGraph agent | K knowledge pack | 57/99 = 57.6% [47.7, 66.8] | 41/72 = 56.9% [45.4, 67.7] | 34/54 = 63.0% [49.6, 74.6] | 19/33 = 57.6% [40.8, 72.8] | 151/258 = 58.5% [52.4, 64.4] |
| M3h | Anthropic claude-haiku-5-5, Claude Code harness | A base | 21/33 = 63.6% [46.6, 77.8] | 16/24 = 66.7% [46.7, 82.0] | 13/18 = 72.2% [49.1, 87.5] | 8/11 = 72.7% [43.4, 90.3] | 58/86 = 67.4% [57.0, 76.4] |
| M3h | Anthropic claude-haiku-5-5, Claude Code harness | S1c skills v1.0 + hint | 21/33 = 63.6% [46.6, 77.8] | 16/24 = 66.7% [46.7, 82.0] | 13/18 = 72.2% [49.1, 87.5] | 7/11 = 63.6% [35.4, 84.8] | 57/86 = 66.3% [55.8, 75.4] |
| M3h | Anthropic claude-haiku-5-5, Claude Code harness | S2c skills v2.0 + hint | 22/33 = 66.7% [49.6, 80.2] | 15/24 = 62.5% [42.7, 78.8] | 14/18 = 77.8% [54.8, 91.0] | 10/11 = 90.9% [62.3, 98.4] | 61/86 = 70.9% [60.6, 79.5] |
| M3i | Anthropic claude-haiku-5-5, Claude Code harness | P plain profile | 23/33 = 69.7% [52.7, 82.6] | 14/24 = 58.3% [38.8, 75.5] | 14/18 = 77.8% [54.8, 91.0] | 10/11 = 90.9% [62.3, 98.4] | 61/86 = 70.9% [60.6, 79.5] |
| M3j | Anthropic claude-haiku-5-5, Claude Code harness | B | 21/33 = 63.6% [46.6, 77.8] | 14/24 = 58.3% [38.8, 75.5] | 13/18 = 72.2% [49.1, 87.5] | 9/11 = 81.8% [52.3, 94.9] | 57/86 = 66.3% [55.8, 75.4] |
| M3j | Anthropic claude-haiku-5-5, Claude Code harness | PA | 23/33 = 69.7% [52.7, 82.6] | 13/24 = 54.2% [35.1, 72.1] | 13/18 = 72.2% [49.1, 87.5] | 8/11 = 72.7% [43.4, 90.3] | 57/86 = 66.3% [55.8, 75.4] |
| M3j | Anthropic claude-haiku-5-5, Claude Code harness | R (first run plus rerun of not-run problems) | 21/33 = 63.6% [46.6, 77.8] | 16/24 = 66.7% [46.7, 82.0] | 12/18 = 66.7% [43.7, 83.7] | 9/11 = 81.8% [52.3, 94.9] | 58/86 = 67.4% [57.0, 76.4] |
| M3k | Anthropic claude-haiku-5-5, Claude Code harness | T | 20/33 = 60.6% [43.7, 75.3] | 14/24 = 58.3% [38.8, 75.5] | 13/18 = 72.2% [49.1, 87.5] | 10/11 = 90.9% [62.3, 98.4] | 57/86 = 66.3% [55.8, 75.4] |
| M3k | Anthropic claude-haiku-5-5, Claude Code harness | K | 21/33 = 63.6% [46.6, 77.8] | 15/24 = 62.5% [42.7, 78.8] | 14/18 = 77.8% [54.8, 91.0] | 9/11 = 81.8% [52.3, 94.9] | 59/86 = 68.6% [58.2, 77.4] |

### Pass rate by category: held-out 100

| Milestone | Model and harness | Arm | cid002 RTL completion | cid003 spec to RTL | cid004 RTL modification | All |
|---|---|---|---|---|---|---|
| M3g | OpenAI gpt-6-luna, LangGraph agent | A base | 52/126 = 41.3% [33.1, 50.0] | 74/123 = 60.2% [51.3, 68.4] | 27/51 = 52.9% [39.5, 65.9] | 153/300 = 51.0% [45.4, 56.6] |
| M3g | OpenAI gpt-6-luna, LangGraph agent | K knowledge pack | 51/126 = 40.5% [32.3, 49.2] | 78/123 = 63.4% [54.6, 71.4] | 27/51 = 52.9% [39.5, 65.9] | 156/300 = 52.0% [46.4, 57.6] |
| M3h | Anthropic claude-haiku-5-5, Claude Code harness | A base | 61/126 = 48.4% [39.9, 57.1] | 87/123 = 70.7% [62.2, 78.0] | 27/51 = 52.9% [39.5, 65.9] | 175/300 = 58.3% [52.7, 63.8] |
| M3h | Anthropic claude-haiku-5-5, Claude Code harness | S1c skills v1.0 + hint | 63/126 = 50.0% [41.4, 58.6] | 87/123 = 70.7% [62.2, 78.0] | 29/51 = 56.9% [43.3, 69.5] | 179/300 = 59.7% [54.0, 65.1] |
| M3h | Anthropic claude-haiku-5-5, Claude Code harness | S2c skills v2.0 + hint | 58/126 = 46.0% [37.6, 54.7] | 82/123 = 66.7% [57.9, 74.4] | 29/51 = 56.9% [43.3, 69.5] | 169/300 = 56.3% [50.7, 61.8] |
| M3h | Anthropic claude-haiku-5-5, Claude Code harness | S2 skills v2.0, no hint (1 run) | 19/42 = 45.2% [31.2, 60.1] | 29/41 = 70.7% [55.5, 82.4] | 9/17 = 52.9% [31.0, 73.8] | 57/100 = 57.0% [47.2, 66.3] |
| M3i | Anthropic claude-haiku-5-5, Claude Code harness | P plain profile | 58/126 = 46.0% [37.6, 54.7] | 88/123 = 71.5% [63.0, 78.8] | 28/51 = 54.9% [41.4, 67.7] | 174/300 = 58.0% [52.3, 63.4] |
| M3j | Anthropic claude-haiku-5-5, Claude Code harness | B | 60/126 = 47.6% [39.1, 56.3] | 87/123 = 70.7% [62.2, 78.0] | 28/51 = 54.9% [41.4, 67.7] | 175/300 = 58.3% [52.7, 63.8] |
| M3j | Anthropic claude-haiku-5-5, Claude Code harness | PA | 58/126 = 46.0% [37.6, 54.7] | 78/123 = 63.4% [54.6, 71.4] | 28/51 = 54.9% [41.4, 67.7] | 164/300 = 54.7% [49.0, 60.2] |
| M3j | Anthropic claude-haiku-5-5, Claude Code harness | R | 57/126 = 45.2% [36.8, 53.9] | 80/123 = 65.0% [56.3, 72.9] | 27/51 = 52.9% [39.5, 65.9] | 164/300 = 54.7% [49.0, 60.2] |
| M3k | Anthropic claude-haiku-5-5, Claude Code harness | T | 52/126 = 41.3% [33.1, 50.0] | 85/123 = 69.1% [60.5, 76.6] | 28/51 = 54.9% [41.4, 67.7] | 165/300 = 55.0% [49.3, 60.5] |
| M3k | Anthropic claude-haiku-5-5, Claude Code harness | K | 59/126 = 46.8% [38.3, 55.5] | 82/123 = 66.7% [57.9, 74.4] | 27/51 = 52.9% [39.5, 65.9] | 168/300 = 56.0% [50.3, 61.5] |

### Pass rate by category: M2 92

| Milestone | Model and harness | Arm | cid003 spec to RTL | cid004 RTL modification | cid005 spec to RTL, module reuse | cid016 bug fixing | All |
|---|---|---|---|---|---|---|---|
| M2 | Anthropic claude-haiku-5.5 (low), LangGraph agent, x86 | base | 19/34 = 55.9% [39.5, 71.1] | 13/25 = 52.0% [33.5, 70.0] | 13/22 = 59.1% [38.7, 76.7] | 7/11 = 63.6% [35.4, 84.8] | 52/92 = 56.5% [46.3, 66.2] |
| M2 | DeepSeek deepseek-v4.1-flash-1017 (off), LangGraph agent, x86 | base | 19/34 = 55.9% [39.5, 71.1] | 11/25 = 44.0% [26.7, 62.9] | 7/22 = 31.8% [16.4, 52.7] | 6/11 = 54.5% [28.0, 78.7] | 43/92 = 46.7% [36.9, 56.9] |
| M2 | OpenAI gpt-6-luna, LangGraph agent, x86 | base | 20/34 = 58.8% [42.2, 73.6] | 15/25 = 60.0% [40.7, 76.6] | 12/22 = 54.5% [34.7, 73.1] | 5/11 = 45.5% [21.3, 72.0] | 52/92 = 56.5% [46.3, 66.2] |
| M2 | Anthropic claude-haiku-5.5 (low), LangGraph agent, Arm64 | base | 21/34 = 61.8% [45.0, 76.1] | 14/25 = 56.0% [37.1, 73.3] | 12/22 = 54.5% [34.7, 73.1] | 9/11 = 81.8% [52.3, 94.9] | 56/92 = 60.9% [50.7, 70.2] |
| M2 | DeepSeek deepseek-v4.1-flash-1017 (off), LangGraph agent, Arm64 | base | 18/34 = 52.9% [36.7, 68.5] | 10/25 = 40.0% [23.4, 59.3] | 7/22 = 31.8% [16.4, 52.7] | 6/11 = 54.5% [28.0, 78.7] | 41/92 = 44.6% [34.8, 54.7] |
| M2 | OpenAI gpt-6-luna, LangGraph agent, Arm64 | base | 20/34 = 58.8% [42.2, 73.6] | 14/25 = 56.0% [37.1, 73.3] | 13/22 = 59.1% [38.7, 76.7] | 6/11 = 54.5% [28.0, 78.7] | 53/92 = 57.6% [47.4, 67.2] |
| M3 | OpenAI gpt-6-luna, LangGraph agent | A base | 38/68 = 55.9% [44.1, 67.1] | 28/50 = 56.0% [42.3, 68.8] | 25/44 = 56.8% [42.2, 70.3] | 13/22 = 59.1% [38.7, 76.7] | 104/184 = 56.5% [49.3, 63.5] |
| M3 | OpenAI gpt-6-luna, LangGraph agent | B self-check off | 39/68 = 57.4% [45.5, 68.4] | 26/50 = 52.0% [38.5, 65.2] | 26/44 = 59.1% [44.4, 72.3] | 11/22 = 50.0% [30.7, 69.3] | 102/184 = 55.4% [48.2, 62.4] |
| M3 | OpenAI gpt-6-luna, LangGraph agent | C lint off | 39/68 = 57.4% [45.5, 68.4] | 26/50 = 52.0% [38.5, 65.2] | 23/44 = 52.3% [37.9, 66.2] | 13/22 = 59.1% [38.7, 76.7] | 101/184 = 54.9% [47.7, 61.9] |
| M3 | OpenAI gpt-6-luna, LangGraph agent | D self-check and lint off | 38/68 = 55.9% [44.1, 67.1] | 26/50 = 52.0% [38.5, 65.2] | 24/44 = 54.5% [40.1, 68.3] | 13/22 = 59.1% [38.7, 76.7] | 101/184 = 54.9% [47.7, 61.9] |
| M3 | OpenAI gpt-6-luna, LangGraph agent | E 5 turns | 40/68 = 58.8% [47.0, 69.7] | 27/50 = 54.0% [40.4, 67.0] | 25/44 = 56.8% [42.2, 70.3] | 11/22 = 50.0% [30.7, 69.3] | 103/184 = 56.0% [48.8, 63.0] |
| M3 | OpenAI gpt-6-luna, LangGraph agent | F 20 turns | 42/68 = 61.8% [49.9, 72.4] | 30/50 = 60.0% [46.2, 72.4] | 25/44 = 56.8% [42.2, 70.3] | 14/22 = 63.6% [43.0, 80.3] | 111/184 = 60.3% [53.1, 67.1] |
| M3 | OpenAI gpt-6-luna, LangGraph agent | G $0.02 budget | 39/68 = 57.4% [45.5, 68.4] | 27/50 = 54.0% [40.4, 67.0] | 23/44 = 52.3% [37.9, 66.2] | 12/22 = 54.5% [34.7, 73.1] | 101/184 = 54.9% [47.7, 61.9] |

### Failed rows by label and category (reference groups)

**M3b, OpenAI gpt-6-luna, LangGraph agent, A LangGraph, no memory (dev 86)**

| Label | In plain words | cid003 (119 failed of 297) | cid004 (100 failed of 216) | cid005 (58 failed of 162) | cid016 (49 failed of 99) |
|---|---|---|---|---|---|
| `tests_failed_no_selfcheck` | hidden tests failed, agent never ran a testbench | 60 | 61 | 41 | 17 |
| `tests_failed_selfcheck_passed` | hidden tests failed, own testbench passed | 8 | 9 | 9 | 22 |
| `compile_fail_hidden` | hidden build failed (port or interface mismatch), own compile passed | 28 | 1 | 3 | 0 |
| `stopped_by_cap` | stopped by a turn, budget or time cap | 10 | 16 | 2 | 3 |
| `tests_failed_selfcheck_failed` | hidden tests failed, own testbench failed, submitted anyway | 3 | 3 | 0 | 6 |
| `signal_missing_hidden` | hidden test reads a signal or parameter name the design lacks | 10 | 0 | 1 | 0 |
| `sim_incomplete` | hidden simulation never finished | 0 | 7 | 2 | 1 |
| `no_edit` | finished without editing rtl/ | 0 | 3 | 0 | 0 |

**M3b, OpenAI gpt-6-luna, Deep Agents harness, B Deep Agents, no memory (dev 86)**

| Label | In plain words | cid003 (113 failed of 297) | cid004 (88 failed of 216) | cid005 (51 failed of 162) | cid016 (39 failed of 99) |
|---|---|---|---|---|---|
| `tests_failed_no_selfcheck` | hidden tests failed, agent never ran a testbench | 48 | 38 | 14 | 18 |
| `stopped_by_cap` | stopped by a turn, budget or time cap | 34 | 34 | 25 | 0 |
| `compile_fail_hidden` | hidden build failed (port or interface mismatch), own compile passed | 26 | 3 | 4 | 0 |
| `tests_failed_selfcheck_passed` | hidden tests failed, own testbench passed | 1 | 7 | 5 | 20 |
| `signal_missing_hidden` | hidden test reads a signal or parameter name the design lacks | 4 | 0 | 3 | 0 |
| `sim_incomplete` | hidden simulation never finished | 0 | 5 | 0 | 0 |
| `killed` | agent killed, no summary | 0 | 0 | 0 | 1 |
| `llm_error` | provider error or missed call deadline | 0 | 1 | 0 | 0 |

**M3e, Anthropic claude-opus-5.5 (low), LangGraph agent, LG, run refused by guard counted as fail (dev 86)**

| Label | In plain words | cid003 (9 failed of 33) | cid004 (8 failed of 24) | cid005 (6 failed of 18) | cid016 (1 failed of 11) |
|---|---|---|---|---|---|
| `tests_failed_selfcheck_passed` | hidden tests failed, own testbench passed | 5 | 5 | 6 | 1 |
| `compile_fail_hidden` | hidden build failed (port or interface mismatch), own compile passed | 3 | 1 | 0 | 0 |
| `gave_up` | agent gave up | 0 | 1 | 0 | 0 |
| `signal_missing_hidden` | hidden test reads a signal or parameter name the design lacks | 1 | 0 | 0 | 0 |
| `tests_failed_selfcheck_failed` | hidden tests failed, own testbench failed, submitted anyway | 0 | 1 | 0 | 0 |

**Claude Code ladder, Anthropic claude-haiku-5-5 (low), Claude Code, plan-signed-in (dev 86)**

| Label | In plain words | cid003 (13 failed of 33) | cid004 (10 failed of 24) | cid005 (4 failed of 18) | cid016 (2 failed of 11) |
|---|---|---|---|---|---|
| `tests_failed_no_selfcheck` | hidden tests failed, agent never ran a testbench | 5 | 10 | 4 | 2 |
| `compile_fail_own` | hidden build failed, own compile failed too | 6 | 0 | 0 | 0 |
| `signal_missing_hidden` | hidden test reads a signal or parameter name the design lacks | 2 | 0 | 0 | 0 |

**Claude Code ladder, Anthropic claude-sonnet-5-5 (low), Claude Code, plan-signed-in (dev 86)**

| Label | In plain words | cid003 (9 failed of 33) | cid004 (10 failed of 24) | cid005 (5 failed of 18) | cid016 (2 failed of 11) |
|---|---|---|---|---|---|
| `tests_failed_no_selfcheck` | hidden tests failed, agent never ran a testbench | 3 | 10 | 4 | 2 |
| `compile_fail_own` | hidden build failed, own compile failed too | 4 | 0 | 0 | 0 |
| `signal_missing_hidden` | hidden test reads a signal or parameter name the design lacks | 1 | 0 | 1 | 0 |
| `stopped_by_cap` | stopped by a turn, budget or time cap | 1 | 0 | 0 | 0 |

**Claude Code ladder, Anthropic claude-opus-5-5 (low), Claude Code, plan-signed-in (dev 86)**

| Label | In plain words | cid003 (5 failed of 33) | cid004 (8 failed of 24) | cid005 (7 failed of 18) | cid016 (3 failed of 11) |
|---|---|---|---|---|---|
| `tests_failed_no_selfcheck` | hidden tests failed, agent never ran a testbench | 3 | 6 | 6 | 3 |
| `compile_fail_own` | hidden build failed, own compile failed too | 2 | 1 | 0 | 0 |
| `sim_incomplete` | hidden simulation never finished | 0 | 1 | 1 | 0 |

**Claude Code ladder, Anthropic claude-fable-5-1 (low), Claude Code, plan-signed-in (dev 86)**

| Label | In plain words | cid003 (11 failed of 33) | cid004 (8 failed of 24) | cid005 (5 failed of 18) | cid016 (4 failed of 11) |
|---|---|---|---|---|---|
| `tests_failed_no_selfcheck` | hidden tests failed, agent never ran a testbench | 1 | 6 | 1 | 4 |
| `stopped_by_cap` | stopped by a turn, budget or time cap | 6 | 1 | 3 | 0 |
| `compile_fail_own` | hidden build failed, own compile failed too | 3 | 0 | 0 | 0 |
| `signal_missing_hidden` | hidden test reads a signal or parameter name the design lacks | 1 | 0 | 1 | 0 |
| `sim_incomplete` | hidden simulation never finished | 0 | 1 | 0 | 0 |

**M3h, Anthropic claude-haiku-5-5, Claude Code harness, A base (dev 86)**

| Label | In plain words | cid003 (12 failed of 33) | cid004 (8 failed of 24) | cid005 (5 failed of 18) | cid016 (3 failed of 11) |
|---|---|---|---|---|---|
| `tests_failed_no_selfcheck` | hidden tests failed, agent never ran a testbench | 6 | 8 | 5 | 3 |
| `compile_fail_own` | hidden build failed, own compile failed too | 5 | 0 | 0 | 0 |
| `signal_missing_hidden` | hidden test reads a signal or parameter name the design lacks | 1 | 0 | 0 | 0 |

**M3h, Anthropic claude-haiku-5-5, Claude Code harness, A base (held-out 100)**

| Label | In plain words | cid002 (65 failed of 126) | cid003 (36 failed of 123) | cid004 (24 failed of 51) |
|---|---|---|---|---|
| `tests_failed_no_selfcheck` | hidden tests failed, agent never ran a testbench | 50 | 26 | 18 |
| `signal_missing_hidden` | hidden test reads a signal or parameter name the design lacks | 3 | 4 | 6 |
| `compile_fail_own` | hidden build failed, own compile failed too | 8 | 3 | 0 |
| `sim_incomplete` | hidden simulation never finished | 4 | 3 | 0 |

**M3g, OpenAI gpt-6-luna, LangGraph agent, A base (held-out 100)**

| Label | In plain words | cid002 (74 failed of 126) | cid003 (49 failed of 123) | cid004 (24 failed of 51) |
|---|---|---|---|---|
| `tests_failed_no_selfcheck` | hidden tests failed, agent never ran a testbench | 52 | 34 | 17 |
| `signal_missing_hidden` | hidden test reads a signal or parameter name the design lacks | 3 | 7 | 6 |
| `compile_fail_hidden` | hidden build failed (port or interface mismatch), own compile passed | 7 | 3 | 0 |
| `sim_incomplete` | hidden simulation never finished | 5 | 3 | 1 |
| `tests_failed_selfcheck_passed` | hidden tests failed, own testbench passed | 5 | 0 | 0 |
| `tests_failed_selfcheck_failed` | hidden tests failed, own testbench failed, submitted anyway | 2 | 1 | 0 |
| `llm_error` | provider error or missed call deadline | 0 | 1 | 0 |

### Problems that no run solved

**dev 86** (every group on this set counted)

| Category | Problems | Never solved | Of those, benchmark-limited |
|---|---|---|---|
| cid003 spec to RTL | 33 | 2 | 1 |
| cid004 RTL modification | 24 | 4 | 3 |
| cid005 spec to RTL, module reuse | 18 | 3 | 1 |
| cid016 bug fixing | 11 | 0 | 0 |
| **All** | 86 | 9 | 5 |

**held-out 100** (every group on this set counted)

| Category | Problems | Never solved | Of those, benchmark-limited |
|---|---|---|---|
| cid002 RTL completion | 42 | 13 | 0 |
| cid003 spec to RTL | 41 | 6 | 0 |
| cid004 RTL modification | 17 | 6 | 0 |
| **All** | 100 | 25 | 0 |

**M2 92** (every group on this set counted)

| Category | Problems | Never solved | Of those, benchmark-limited |
|---|---|---|---|
| cid003 spec to RTL | 34 | 9 | 2 |
| cid004 RTL modification | 25 | 7 | 3 |
| cid005 spec to RTL, module reuse | 22 | 7 | 1 |
| cid016 bug fixing | 11 | 1 | 0 |
| **All** | 92 | 24 | 6 |

## What is missing

The free split of the benchmark contains **no verification-writing categories**: testbench stimulus generation
(cid012), testbench checker generation (cid013) and assertion generation (cid014) are not in it, nor are code
improvement (cid007), the correspondence tasks or question answering. Our five categories are RTL completion,
spec to RTL, RTL modification, module reuse and bug fixing. So nothing here can confirm or contradict the paper's
finding that verification categories are harder than RTL categories.

## The paper, beside ours

Paper: "Comprehensive Verilog Design Problems: A Next-Generation Benchmark Dataset for Evaluating Large Language
Models and Agents on RTL Design and Verification", arXiv 2506.14074 (v1, 17 June 2025), read through
export.arxiv.org.

- **Verification is harder than RTL, in the paper.** Section 4: "Design verification categories ... exhibit
  substantially lower pass rates compared to other code generation categories." Table 2 (non-agentic, pass@1,
  n = 5): cid12 13% to 25%, cid13 3% to 11%, cid14 5% to 23%, against cid02 to cid04 of 18% to 48%. Table 3 (agentic, converted to single-turn) shows the same split. Section 5
  and Table 5 say the same of the failure clusters. The abstract adds that agentic tasks "involving RTL reuse
  and verification" are particularly difficult. The recollection that verification and testbench categories
  are harder than RTL categories is confirmed by the paper.
- **Where our categories match the paper's** (cid003, cid004, cid005, cid016; cid002 for the held-out set), the paper
  tested older models with single-turn prompts on all of the benchmark's problems for each category: the models
  were Claude 3.7 Sonnet, Claude 3.5 Haiku, GPT 4.1, o1, o4-mini and Llama 3.1. Our models, our agent loop and
  our problem subsets differ, so we do not compare levels. Table 3 gives bug fixing (cid16) the highest
  agentic pass rate for most models (36% to 56%) and module reuse (cid05) among the lowest of the RTL categories
  (18% to 25%). We do not see that order: for gpt-6-luna in the LangGraph agent, bug fixing is the lowest of
  the four (50.5%) and module reuse the highest (64.2%); for the Claude Code models bug fixing is higher
  (64% to 82%) and module reuse mixed (61% to 78%). We read the order as not stable across models and harnesses.
- **Section 5 failure entities** (Table 5) are LLM-clustered text such as "data misalignment" or "bit-slicing
  errors". Ours are rule-based labels from logs. The two sets are not comparable label by label.

## Limits

- Cell sizes are small (11 to 33 problems per category on one run), and the intervals say so.
- Every dev-set result is on problems we developed against. The held-out 100 is the cleaner read, but it has no
  cid005 or cid016.
- "Never solved" counts a problem as solved if any run of any arm passed it. It is a floor on difficulty for these
  agents, not a property of the benchmark; the 11 benchmark-limited problems (`unsolved_analysis.md`) are
  marked.
- Held-out problems are counted here, never named.
