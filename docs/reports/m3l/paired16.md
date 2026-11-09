#### Paired effect against the base (`R`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| E | no detectable effect | +6.2 [-3.8, +16.2] | 4 / 1 / 11 | 0.375 | 16 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| R (base) | 10: 69.2%, 69.2%, 84.6%, 76.9%, 84.6%, 33.3%, 0.0%, 0.0%, 33.3%, 33.3% | 53/80 = 66.2% [45.0, 85.0] | ≥$0.0000 (80 unreported) | ≥$0.0000 | ≥$0.0000 | 53 s | 15,613,507 |
| E | 10: 76.9%, 76.9%, 76.9%, 92.3%, 76.9%, 33.3%, 66.7%, 0.0%, 33.3%, 66.7% | 58/80 = 72.5% [53.8, 88.8] | ≥$0.0000 (80 unreported) | ≥$0.0000 | ≥$0.0000 | 59 s | 14,600,716 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| R | ≥$0.0000 | 66.2% | n/a (cost a lower bound) |
| E | ≥$0.0000 | 72.5% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

