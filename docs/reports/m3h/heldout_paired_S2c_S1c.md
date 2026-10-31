#### Paired effect against the base (`S1c`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| S2c | worse than base | -3.3 [-7.0, -0.0] | 3 / 11 / 86 | 0.0574 | 100 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| S1c (base) | 3: 61.0%, 60.0%, 58.0% | 179/300 = 59.7% [50.3, 69.0] | ≥$0.0000 (300 unreported) | ≥$0.0000 | ≥$0.0000 | 46 s | 79,932,421 |
| S2c | 3: 57.0%, 58.0%, 54.0% | 169/300 = 56.3% [46.7, 65.3] | ≥$0.0000 (300 unreported) | ≥$0.0000 | ≥$0.0000 | 48 s | 77,034,728 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| S1c | ≥$0.0000 | 59.7% | n/a (cost a lower bound) |
| S2c | ≥$0.0000 | 56.3% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

