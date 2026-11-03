#### Paired effect against the base (`PA`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| B | no detectable effect | +0.0 [-7.6, +7.6] | 5 / 5 / 69 | 1 | 79 | 0 |
| D | no detectable effect | +1.3 [-6.3, +8.9] | 5 / 4 / 70 | 1 | 79 | 0 |
| R | no detectable effect | +1.3 [-5.1, +7.6] | 4 / 3 / 72 | 1 | 79 | 0 |
| P | no detectable effect | +3.8 [-2.5, +10.1] | 5 / 2 / 72 | 0.453 | 79 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| PA (base) | 1: 72.2% | 57/79 = 72.2% [62.0, 82.3] | ≥$0.0000 (79 unreported) | ≥$0.0000 | ≥$0.0000 | 44 s | 12,980,526 |
| B | 1: 72.2% | 57/79 = 72.2% [62.0, 81.0] | ≥$0.0000 (79 unreported) | ≥$0.0000 | ≥$0.0000 | 37 s | 11,380,937 |
| D | 1: 73.4% | 58/79 = 73.4% [63.3, 82.3] | ≥$0.0000 (79 unreported) | ≥$0.0000 | ≥$0.0000 | 90 s | 35,065,330 |
| R | 1: 73.4% | 58/79 = 73.4% [63.3, 82.3] | ≥$0.0000 (79 unreported) | ≥$0.0000 | ≥$0.0000 | 37 s | 10,498,116 |
| P | 1: 75.9% | 60/79 = 75.9% [65.8, 84.8] | ≥$0.0000 (79 unreported) | ≥$0.0000 | ≥$0.0000 | 44 s | 13,659,938 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| PA | ≥$0.0000 | 72.2% | n/a (cost a lower bound) |
| B | ≥$0.0000 | 72.2% | n/a (cost a lower bound) |
| R | ≥$0.0000 | 73.4% | n/a (cost a lower bound) |
| P | ≥$0.0000 | 75.9% | n/a (cost a lower bound) |
| D | ≥$0.0000 | 73.4% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

