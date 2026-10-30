208 failed (problem, run) rows of 516.

#### Primary label by arm

| Label | dev_A | dev_K | All |
|---|---|---|---|
| llm_error | 2 | 5 | 7 |
| no_edit | 0 | 1 | 1 |
| stopped_by_cap | 7 | 6 | 13 |
| sim_incomplete | 5 | 5 | 10 |
| compile_fail_hidden | 10 | 8 | 18 |
| signal_missing_hidden | 4 | 9 | 13 |
| tests_failed_selfcheck_passed | 16 | 14 | 30 |
| tests_failed_selfcheck_failed | 2 | 7 | 9 |
| tests_failed_no_selfcheck | 55 | 52 | 107 |
| **All failures** | 101 | 107 | 208 |

#### Primary label by cid

| Label | cid003 | cid004 | cid005 | cid016 | All |
|---|---|---|---|---|---|
| llm_error | 4 | 0 | 2 | 1 | 7 |
| no_edit | 0 | 1 | 0 | 0 | 1 |
| stopped_by_cap | 2 | 7 | 2 | 2 | 13 |
| sim_incomplete | 0 | 6 | 3 | 1 | 10 |
| compile_fail_hidden | 16 | 0 | 2 | 0 | 18 |
| signal_missing_hidden | 10 | 0 | 3 | 0 | 13 |
| tests_failed_selfcheck_passed | 5 | 8 | 4 | 13 | 30 |
| tests_failed_selfcheck_failed | 3 | 5 | 0 | 1 | 9 |
| tests_failed_no_selfcheck | 40 | 35 | 23 | 9 | 107 |
| **All failures** | 80 | 62 | 39 | 27 | 208 |

Secondary flags: single_turn 109, tests_failed_selfcheck_failed 12, partial_pass 5, compile_fail_own 4, no_edit 3, tests_failed_no_selfcheck 2, empty_replies 2, signal_missing_hidden 1, tests_failed_selfcheck_passed 1, compile_fail_hidden 1

