320 failed (problem, run) rows of 774.

#### Primary label by arm

| Label | A | S | V | All |
|---|---|---|---|---|
| llm_error | 2 | 9 | 14 | 25 |
| stopped_by_cap | 7 | 43 | 27 | 77 |
| sim_incomplete | 5 | 1 | 2 | 8 |
| compile_fail_hidden | 10 | 10 | 9 | 29 |
| signal_missing_hidden | 4 | 0 | 3 | 7 |
| tests_failed_selfcheck_passed | 16 | 44 | 48 | 108 |
| tests_failed_selfcheck_failed | 2 | 4 | 3 | 9 |
| tests_failed_no_selfcheck | 55 | 2 | 0 | 57 |
| **All failures** | 101 | 113 | 106 | 320 |

#### Primary label by cid

| Label | cid003 | cid004 | cid005 | cid016 | All |
|---|---|---|---|---|---|
| llm_error | 9 | 11 | 4 | 1 | 25 |
| stopped_by_cap | 30 | 32 | 7 | 8 | 77 |
| sim_incomplete | 0 | 6 | 1 | 1 | 8 |
| compile_fail_hidden | 26 | 0 | 3 | 0 | 29 |
| signal_missing_hidden | 6 | 0 | 1 | 0 | 7 |
| tests_failed_selfcheck_passed | 25 | 26 | 26 | 31 | 108 |
| tests_failed_selfcheck_failed | 2 | 4 | 2 | 1 | 9 |
| tests_failed_no_selfcheck | 20 | 19 | 14 | 4 | 57 |
| **All failures** | 118 | 98 | 58 | 46 | 320 |

Secondary flags: tests_failed_selfcheck_failed 71, single_turn 56, spec_checks_passed 53, spec_checks_failed 27, spec_failed_open 25, verify_let_through 23, empty_replies 10, partial_pass 9, compile_fail_own 9, signal_missing_hidden 8, run_budget_exhausted 8, compile_fail_hidden 6, tests_failed_no_selfcheck 4, sim_incomplete 4, no_edit 2, best_edit_restored 1

