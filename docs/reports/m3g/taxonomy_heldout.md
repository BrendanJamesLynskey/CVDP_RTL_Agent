291 failed (problem, run) rows of 600.

#### Primary label by arm

| Label | heldout_A | heldout_K | All |
|---|---|---|---|
| llm_error | 1 | 0 | 1 |
| stopped_by_cap | 0 | 2 | 2 |
| sim_incomplete | 9 | 10 | 19 |
| compile_fail_hidden | 10 | 10 | 20 |
| signal_missing_hidden | 16 | 16 | 32 |
| tests_failed_selfcheck_passed | 5 | 11 | 16 |
| tests_failed_selfcheck_failed | 3 | 0 | 3 |
| tests_failed_no_selfcheck | 103 | 95 | 198 |
| **All failures** | 147 | 144 | 291 |

#### Primary label by cid

| Label | cid002 | cid003 | cid004 | All |
|---|---|---|---|---|
| llm_error | 0 | 1 | 0 | 1 |
| stopped_by_cap | 1 | 1 | 0 | 2 |
| sim_incomplete | 10 | 6 | 3 | 19 |
| compile_fail_hidden | 14 | 6 | 0 | 20 |
| signal_missing_hidden | 6 | 14 | 12 | 32 |
| tests_failed_selfcheck_passed | 13 | 1 | 2 | 16 |
| tests_failed_selfcheck_failed | 2 | 1 | 0 | 3 |
| tests_failed_no_selfcheck | 103 | 64 | 31 | 198 |
| **All failures** | 149 | 94 | 48 | 291 |

Secondary flags: single_turn 220, tests_failed_selfcheck_failed 2, no_edit 1, compile_fail_own 1

