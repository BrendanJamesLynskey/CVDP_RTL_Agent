#### Paired effect against the base (`A`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 97.5% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [97.5%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| S | no detectable effect | -5.1 [-12.7, +1.7] | 12 / 19 / 48 | 0.281 | 79 | 0 |
| V | no detectable effect | -2.1 [-7.2, +2.5] | 7 / 9 / 63 | 0.804 | 79 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| A (base) | 3: 62.0%, 65.8%, 70.9% | 157/237 = 66.2% [57.0, 75.1] | ≥$1.6037 (4 unreported) | ≥$0.0068 | ≥$0.0102 | 74 s | 7,905,267 |
| S | 3: 60.8%, 62.0%, 60.8% | 145/237 = 61.2% [51.5, 70.5] | ≥$3.1030 (17 unreported) | ≥$0.0131 | ≥$0.0214 | 245 s | 14,044,789 |
| V | 3: 64.6%, 67.1%, 60.8% | 152/237 = 64.1% [54.9, 73.4] | ≥$2.5326 (14 unreported) | ≥$0.0107 | ≥$0.0167 | 135 s | 12,279,443 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| A | ≥$0.0068 | 66.2% | n/a (cost a lower bound) |
| V | ≥$0.0107 | 64.1% | n/a (cost a lower bound) |
| S | ≥$0.0131 | 61.2% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

