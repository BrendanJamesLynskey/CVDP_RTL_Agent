#### Paired effect against the base (`A`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| K | no detectable effect | -2.5 [-8.4, +2.5] | 11 / 12 / 56 | 1 | 79 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| A (base) | 3: 62.0%, 65.8%, 70.9% | 157/237 = 66.2% [57.0, 75.1] | ≥$1.6037 (4 unreported) | ≥$0.0068 | ≥$0.0102 | 74 s | 7,905,267 |
| K | 3: 63.3%, 63.3%, 64.6% | 151/237 = 63.7% [54.9, 72.6] | ≥$1.9209 (4 unreported) | ≥$0.0081 | ≥$0.0127 | 56 s | 10,445,956 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| A | ≥$0.0068 | 66.2% | n/a (cost a lower bound) |
| K | ≥$0.0081 | 63.7% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

