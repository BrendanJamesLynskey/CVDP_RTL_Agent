174 failed (problem, run) rows of 516.

#### Primary label by arm

| Label | CC+Opus | CC+Sonnet | LG+Opus | LG+luna | All |
|---|---|---|---|---|---|
| llm_error | 0 | 0 | 0 | 2 | 2 |
| stopped_by_cap | 0 | 1 | 0 | 7 | 8 |
| gave_up | 0 | 0 | 1 | 0 | 1 |
| sim_incomplete | 2 | 0 | 0 | 5 | 7 |
| compile_fail_own | 3 | 4 | 0 | 0 | 7 |
| compile_fail_hidden | 0 | 0 | 4 | 10 | 14 |
| signal_missing_hidden | 0 | 2 | 1 | 4 | 7 |
| tests_failed_selfcheck_passed | 0 | 0 | 17 | 16 | 33 |
| tests_failed_selfcheck_failed | 0 | 0 | 1 | 2 | 3 |
| tests_failed_no_selfcheck | 18 | 19 | 0 | 55 | 92 |
| **All failures** | 23 | 26 | 24 | 101 | 174 |

#### Primary label by cid

| Label | cid003 | cid004 | cid005 | cid016 | All |
|---|---|---|---|---|---|
| llm_error | 1 | 0 | 0 | 1 | 2 |
| stopped_by_cap | 2 | 4 | 1 | 1 | 8 |
| gave_up | 0 | 1 | 0 | 0 | 1 |
| sim_incomplete | 0 | 4 | 2 | 1 | 7 |
| compile_fail_own | 6 | 1 | 0 | 0 | 7 |
| compile_fail_hidden | 12 | 1 | 1 | 0 | 14 |
| signal_missing_hidden | 6 | 0 | 1 | 0 | 7 |
| tests_failed_selfcheck_passed | 8 | 9 | 9 | 7 | 33 |
| tests_failed_selfcheck_failed | 0 | 3 | 0 | 0 | 3 |
| tests_failed_no_selfcheck | 26 | 34 | 23 | 9 | 92 |
| **All failures** | 61 | 57 | 37 | 19 | 174 |

Secondary flags: single_turn 53, tests_failed_selfcheck_failed 9, partial_pass 5, tests_failed_no_selfcheck 1, compile_fail_own 1

