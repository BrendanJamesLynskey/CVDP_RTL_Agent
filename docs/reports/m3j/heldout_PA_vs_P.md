#### Paired effect against the base (`P`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| PA | no detectable effect | -3.3 [-7.3, +0.7] | 6 / 12 / 82 | 0.238 | 100 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| P (base) | 3: 61.0%, 58.0%, 55.0% | 174/300 = 58.0% [48.7, 67.0] | ≥$0.0000 (300 unreported) | ≥$0.0000 | ≥$0.0000 | 25 s | 20,703,617 |
| PA | 3: 53.0%, 54.0%, 57.0% | 164/300 = 54.7% [45.0, 63.7] | ≥$0.0000 (300 unreported) | ≥$0.0000 | ≥$0.0000 | 23 s | 22,187,522 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| P | ≥$0.0000 | 58.0% | n/a (cost a lower bound) |
| PA | ≥$0.0000 | 54.7% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

