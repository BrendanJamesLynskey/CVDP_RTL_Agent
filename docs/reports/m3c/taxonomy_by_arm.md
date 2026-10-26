299 failed (problem, run) rows of 774.

#### Primary label by arm

| Label | A | I | M | All |
|---|---|---|---|---|
| llm_error | 1 | 0 | 2 | 3 |
| stopped_by_cap | 4 | 12 | 19 | 35 |
| sim_incomplete | 5 | 5 | 1 | 11 |
| compile_fail_hidden | 11 | 13 | 11 | 35 |
| signal_missing_hidden | 5 | 3 | 4 | 12 |
| tests_failed_selfcheck_passed | 14 | 18 | 50 | 82 |
| tests_failed_selfcheck_failed | 3 | 7 | 10 | 20 |
| tests_failed_no_selfcheck | 56 | 45 | 0 | 101 |
| **All failures** | 99 | 103 | 97 | 299 |

#### Primary label by cid

| Label | cid003 | cid004 | cid005 | cid016 | All |
|---|---|---|---|---|---|
| llm_error | 1 | 1 | 1 | 0 | 3 |
| stopped_by_cap | 16 | 12 | 3 | 4 | 35 |
| sim_incomplete | 0 | 7 | 3 | 1 | 11 |
| compile_fail_hidden | 31 | 0 | 4 | 0 | 35 |
| signal_missing_hidden | 8 | 0 | 4 | 0 | 12 |
| tests_failed_selfcheck_passed | 20 | 20 | 15 | 27 | 82 |
| tests_failed_selfcheck_failed | 4 | 9 | 2 | 5 | 20 |
| tests_failed_no_selfcheck | 32 | 41 | 22 | 6 | 101 |
| **All failures** | 112 | 90 | 54 | 43 | 299 |

Secondary flags: single_turn 92, gate_no_tb 66, tests_failed_selfcheck_failed 30, gate_overridden 25, partial_pass 11, interface_mismatch_unresolved 7, tests_failed_no_selfcheck 4, empty_replies 3, best_edit_restored 2, compile_fail_hidden 2, sim_incomplete 1, signal_missing_hidden 1

