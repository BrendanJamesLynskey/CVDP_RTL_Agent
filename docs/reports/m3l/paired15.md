#### Paired effect against the base (`R`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| E | no detectable effect | +6.7 [-4.0, +18.7] | 4 / 1 / 10 | 0.375 | 15 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| R (base) | 10: 75.0%, 75.0%, 91.7%, 83.3%, 91.7%, 33.3%, 0.0%, 0.0%, 33.3%, 33.3% | 53/75 = 70.7% [49.3, 88.0] | ≥$0.0000 (75 unreported) | ≥$0.0000 | ≥$0.0000 | 51 s | 12,549,376 |
| E | 10: 83.3%, 83.3%, 83.3%, 100.0%, 83.3%, 33.3%, 66.7%, 0.0%, 33.3%, 66.7% | 58/75 = 77.3% [58.7, 92.0] | ≥$0.0000 (75 unreported) | ≥$0.0000 | ≥$0.0000 | 53 s | 13,162,750 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| R | ≥$0.0000 | 70.7% | n/a (cost a lower bound) |
| E | ≥$0.0000 | 77.3% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

