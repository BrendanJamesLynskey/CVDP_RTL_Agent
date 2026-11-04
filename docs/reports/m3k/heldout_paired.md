#### Paired effect against the base (`R`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| T | no detectable effect | +0.3 [-4.7, +5.3] | 9 / 9 / 82 | 1 | 100 | 0 |
| K | no detectable effect | +1.3 [-0.7, +3.7] | 7 / 3 / 90 | 0.344 | 100 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| R (base) | 3: 53.0%, 57.0%, 54.0% | 164/300 = 54.7% [45.3, 63.7] | ≥$0.0000 (300 unreported) | ≥$0.0000 | ≥$0.0000 | 22 s | 15,828,041 |
| T | 3: 57.0%, 55.0%, 53.0% | 165/300 = 55.0% [46.0, 64.0] | ≥$0.0000 (300 unreported) | ≥$0.0000 | ≥$0.0000 | 36 s | 25,592,896 |
| K | 3: 55.0%, 56.0%, 57.0% | 168/300 = 56.0% [46.7, 65.0] | ≥$0.0000 (300 unreported) | ≥$0.0000 | ≥$0.0000 | 22 s | 16,719,350 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| R | ≥$0.0000 | 54.7% | n/a (cost a lower bound) |
| T | ≥$0.0000 | 55.0% | n/a (cost a lower bound) |
| K | ≥$0.0000 | 56.0% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

