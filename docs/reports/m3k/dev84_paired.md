#### Paired effect against the base (`R`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| T | no detectable effect | -1.2 [-8.3, +6.0] | 4 / 5 / 75 | 1 | 84 | 0 |
| K | no detectable effect | +1.2 [-4.8, +7.1] | 4 / 3 / 77 | 1 | 84 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| R (base) | 1: 69.0% | 58/84 = 69.0% [58.3, 78.6] | ≥$0.0000 (84 unreported) | ≥$0.0000 | ≥$0.0000 | 37 s | 9,343,175 |
| T | 1: 67.9% | 57/84 = 67.9% [58.3, 77.4] | ≥$0.0000 (84 unreported) | ≥$0.0000 | ≥$0.0000 | 59 s | 16,718,956 |
| K | 1: 70.2% | 59/84 = 70.2% [60.7, 79.8] | ≥$0.0000 (84 unreported) | ≥$0.0000 | ≥$0.0000 | 36 s | 11,333,117 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| R | ≥$0.0000 | 69.0% | n/a (cost a lower bound) |
| T | ≥$0.0000 | 67.9% | n/a (cost a lower bound) |
| K | ≥$0.0000 | 70.2% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

