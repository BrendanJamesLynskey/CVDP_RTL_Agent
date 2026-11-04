#### Paired effect against the base (`R`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| T | no detectable effect | -1.2 [-8.1, +5.8] | 4 / 5 / 77 | 1 | 86 | 0 |
| K | no detectable effect | +1.2 [-4.7, +8.1] | 4 / 3 / 79 | 1 | 86 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| R (base) | 1: 67.4% | 58/86 = 67.4% [57.0, 76.7] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 37 s | 11,131,437 |
| T | 1: 66.3% | 57/86 = 66.3% [55.8, 75.6] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 60 s | 16,847,754 |
| K | 1: 68.6% | 59/86 = 68.6% [59.3, 77.9] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 38 s | 11,888,379 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| R | ≥$0.0000 | 67.4% | n/a (cost a lower bound) |
| T | ≥$0.0000 | 66.3% | n/a (cost a lower bound) |
| K | ≥$0.0000 | 68.6% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

