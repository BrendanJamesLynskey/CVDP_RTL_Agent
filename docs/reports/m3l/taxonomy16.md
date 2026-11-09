49 failed (problem, run) rows of 160.

#### Primary label by arm

| Label | E16 | R16 | All |
|---|---|---|---|
| llm_error | 2 | 0 | 2 |
| stopped_by_cap | 0 | 1 | 1 |
| sim_incomplete | 5 | 5 | 10 |
| compile_fail_own | 0 | 4 | 4 |
| signal_missing_hidden | 1 | 3 | 4 |
| tests_failed_no_selfcheck | 14 | 14 | 28 |
| **All failures** | 22 | 27 | 49 |

#### Primary label by cid

| Label | cid002 | cid003 | cid004 | cid005 | All |
|---|---|---|---|---|---|
| llm_error | 0 | 0 | 0 | 2 | 2 |
| stopped_by_cap | 0 | 1 | 0 | 0 | 1 |
| sim_incomplete | 0 | 1 | 9 | 0 | 10 |
| compile_fail_own | 0 | 4 | 0 | 0 | 4 |
| signal_missing_hidden | 0 | 4 | 0 | 0 | 4 |
| tests_failed_no_selfcheck | 10 | 9 | 1 | 8 | 28 |
| **All failures** | 10 | 19 | 10 | 10 | 49 |

Secondary flags: compile_fail_own 2, tests_failed_no_selfcheck 1

