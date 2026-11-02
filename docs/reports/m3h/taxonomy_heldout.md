420 failed (problem, run) rows of 1000.

#### Primary label by arm

| Label | heldout_A | heldout_S1c | heldout_S2 | heldout_S2c | All |
|---|---|---|---|---|---|
| stopped_by_cap | 0 | 1 | 0 | 1 | 2 |
| sim_incomplete | 7 | 7 | 3 | 7 | 24 |
| compile_fail_own | 11 | 10 | 3 | 10 | 34 |
| signal_missing_hidden | 13 | 14 | 4 | 13 | 44 |
| tests_failed_no_selfcheck | 94 | 89 | 33 | 100 | 316 |
| **All failures** | 125 | 121 | 43 | 131 | 420 |

#### Primary label by cid

| Label | cid002 | cid003 | cid004 | All |
|---|---|---|---|---|
| stopped_by_cap | 1 | 1 | 0 | 2 |
| sim_incomplete | 14 | 10 | 0 | 24 |
| compile_fail_own | 24 | 10 | 0 | 34 |
| signal_missing_hidden | 11 | 14 | 19 | 44 |
| tests_failed_no_selfcheck | 169 | 90 | 57 | 316 |
| **All failures** | 219 | 125 | 76 | 420 |

Secondary flags: tests_failed_no_selfcheck 2

