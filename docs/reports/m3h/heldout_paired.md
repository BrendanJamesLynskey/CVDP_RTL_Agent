#### Paired effect against the base (`A`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| S2c | no detectable effect | -2.0 [-6.3, +1.7] | 9 / 12 / 79 | 0.664 | 100 | 0 |
| S1c | no detectable effect | +1.3 [-2.7, +5.7] | 13 / 9 / 78 | 0.523 | 100 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| A (base) | 3: 57.0%, 56.0%, 62.0% | 175/300 = 58.3% [49.3, 66.7] | ≥$0.0000 (300 unreported) | ≥$0.0000 | ≥$0.0000 | 32 s | 53,273,631 |
| S2c | 3: 57.0%, 58.0%, 54.0% | 169/300 = 56.3% [46.7, 65.3] | ≥$0.0000 (300 unreported) | ≥$0.0000 | ≥$0.0000 | 48 s | 77,034,728 |
| S1c | 3: 61.0%, 60.0%, 58.0% | 179/300 = 59.7% [50.3, 69.0] | ≥$0.0000 (300 unreported) | ≥$0.0000 | ≥$0.0000 | 46 s | 79,932,421 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| A | ≥$0.0000 | 58.3% | n/a (cost a lower bound) |
| S1c | ≥$0.0000 | 59.7% | n/a (cost a lower bound) |
| S2c | ≥$0.0000 | 56.3% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

