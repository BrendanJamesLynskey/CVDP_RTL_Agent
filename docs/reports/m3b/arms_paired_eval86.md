#### Paired effect against the base (`A`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| C | no detectable effect | +1.6 [-3.1, +6.6] | 10 / 8 / 68 | 0.815 | 86 | 0 |
| B | better than base | +4.3 [+0.0, +8.5] | 15 / 8 / 63 | 0.21 | 86 | 0 |
| D | better than base | +7.4 [+2.3, +12.8] | 14 / 4 / 68 | 0.0309 | 86 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| A (base) | 3: 55.8%, 59.3%, 58.1% | 149/258 = 57.8% [48.4, 67.1] | $1.8484 | $0.0072 | $0.0124 | 53 s | 8,878,176 |
| C | 3: 59.3%, 59.3%, 59.3% | 153/258 = 59.3% [49.6, 68.6] | $1.7268 | $0.0067 | $0.0113 | 51 s | 8,159,082 |
| B | 3: 62.8%, 59.3%, 64.0% | 160/258 = 62.0% [52.7, 71.7] | $1.9081 | $0.0074 | $0.0119 | 73 s | 45,667,940 |
| D | 3: 60.5%, 68.6%, 66.3% | 168/258 = 65.1% [55.4, 74.0] | $1.7841 | $0.0069 | $0.0106 | 68 s | 43,215,570 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| C | $0.0067 | 59.3% | yes |
| D | $0.0069 | 65.1% | yes |
| A | $0.0072 | 57.8% |  |
| B | $0.0074 | 62.0% |  |

