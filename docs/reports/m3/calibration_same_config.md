#### Paired effect against the base (`luna default, Arm64 run (39981444074)`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems |
|---|---|---|---|---|---|
| luna default, x86 run (39967317698) | no detectable effect | -1.1 [-7.6, +5.4] | 4 / 5 / 83 | 1 | 92 |

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| luna default, Arm64 run (39981444074) (base) | 1: 57.6% | 53/92 = 57.6% [46.7, 67.4] | $0.5776 | $0.0063 | $0.0109 | 67 s | 2,801,972 |
| luna default, x86 run (39967317698) | 1: 56.5% | 52/92 = 56.5% [45.7, 66.3] | $0.5455 | $0.0059 | $0.0105 | 76 s | 2,627,420 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| luna default, x86 run (39967317698) | $0.0059 | 56.5% | yes |
| luna default, Arm64 run (39981444074) | $0.0063 | 57.6% | yes |

