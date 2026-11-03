#### Paired effect against the base (`D`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| R | no detectable effect | -3.7 [-8.3, +0.3] | 10 / 15 / 75 | 0.424 | 100 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| D (base) | 3: 57.0%, 56.0%, 62.0% | 175/300 = 58.3% [49.3, 66.7] | ≥$0.0000 (300 unreported) | ≥$0.0000 | ≥$0.0000 | 32 s | 53,273,631 |
| R | 3: 53.0%, 57.0%, 54.0% | 164/300 = 54.7% [45.3, 63.7] | ≥$0.0000 (300 unreported) | ≥$0.0000 | ≥$0.0000 | 22 s | 15,828,041 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| D | ≥$0.0000 | 58.3% | n/a (cost a lower bound) |
| R | ≥$0.0000 | 54.7% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

