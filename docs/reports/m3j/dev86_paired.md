#### Paired effect against the base (`PA`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| B | no detectable effect | +0.0 [-7.0, +7.0] | 5 / 5 / 76 | 1 | 86 | 0 |
| D | no detectable effect | +1.2 [-5.8, +8.1] | 5 / 4 / 77 | 1 | 86 | 0 |
| R | no detectable effect | +1.2 [-4.7, +7.0] | 4 / 3 / 79 | 1 | 86 | 0 |
| P | no detectable effect | +4.7 [-1.2, +11.6] | 6 / 2 / 78 | 0.289 | 86 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| PA (base) | 1: 66.3% | 57/86 = 66.3% [55.8, 76.7] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 47 s | 13,824,053 |
| B | 1: 66.3% | 57/86 = 66.3% [55.8, 76.7] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 38 s | 12,004,630 |
| D | 1: 67.4% | 58/86 = 67.4% [58.1, 76.7] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 89 s | 38,944,289 |
| R | 1: 67.4% | 58/86 = 67.4% [57.0, 76.7] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 37 s | 11,131,437 |
| P | 1: 70.9% | 61/86 = 70.9% [60.5, 80.2] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 44 s | 14,594,121 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| PA | ≥$0.0000 | 66.3% | n/a (cost a lower bound) |
| B | ≥$0.0000 | 66.3% | n/a (cost a lower bound) |
| R | ≥$0.0000 | 67.4% | n/a (cost a lower bound) |
| P | ≥$0.0000 | 70.9% | n/a (cost a lower bound) |
| D | ≥$0.0000 | 67.4% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

