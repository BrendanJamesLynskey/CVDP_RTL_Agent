184 failed (problem, run) rows of 516.

#### Primary label by arm

| Label | CC+Opus | CC+Sonnet | LG+Opus | LG+luna | All |
|---|---|---|---|---|---|
| llm_error | 0 | 0 | 0 | 2 | 2 |
| stopped_by_cap | 0 | 1 | 19 | 7 | 27 |
| sim_incomplete | 2 | 0 | 0 | 5 | 7 |
| compile_fail_own | 3 | 4 | 0 | 0 | 7 |
| compile_fail_hidden | 0 | 0 | 3 | 10 | 13 |
| signal_missing_hidden | 0 | 2 | 0 | 4 | 6 |
| tests_failed_selfcheck_passed | 0 | 0 | 11 | 16 | 27 |
| tests_failed_selfcheck_failed | 0 | 0 | 1 | 2 | 3 |
| tests_failed_no_selfcheck | 18 | 19 | 0 | 55 | 92 |
| **All failures** | 23 | 26 | 34 | 101 | 184 |

#### Primary label by cid

| Label | cid003 | cid004 | cid005 | cid016 | All |
|---|---|---|---|---|---|
| llm_error | 1 | 0 | 0 | 1 | 2 |
| stopped_by_cap | 10 | 10 | 6 | 1 | 27 |
| sim_incomplete | 0 | 4 | 2 | 1 | 7 |
| compile_fail_own | 6 | 1 | 0 | 0 | 7 |
| compile_fail_hidden | 11 | 1 | 1 | 0 | 13 |
| signal_missing_hidden | 5 | 0 | 1 | 0 | 6 |
| tests_failed_selfcheck_passed | 6 | 7 | 7 | 7 | 27 |
| tests_failed_selfcheck_failed | 0 | 3 | 0 | 0 | 3 |
| tests_failed_no_selfcheck | 26 | 34 | 23 | 9 | 92 |
| **All failures** | 65 | 60 | 40 | 19 | 184 |

Secondary flags: single_turn 52, run_budget_exhausted 19, compile_fail_own 15, tests_failed_selfcheck_failed 8, partial_pass 5, tests_failed_no_selfcheck 4, signal_missing_hidden 2

