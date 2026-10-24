#### Paired effect against the base (`A1`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| A2 | no detectable effect | -2.2 [-8.7, +4.3] | 3 / 5 / 84 | 0.727 | 92 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| A1 (base) | 1: 57.6% | 53/92 = 57.6% [46.7, 67.4] | $0.5776 | $0.0063 | $0.0109 | 67 s | 2,801,972 |
| A2 | 1: 55.4% | 51/92 = 55.4% [45.7, 65.2] | $0.5282 | $0.0057 | $0.0104 | 47 s | 2,586,920 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| A2 | $0.0057 | 55.4% | yes |
| A1 | $0.0063 | 57.6% | yes |

