#### Paired effect against the base (`D`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| P | no detectable effect | +2.5 [-5.1, +10.1] | 6 / 4 / 69 | 0.754 | 79 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| D (base) | 1: 73.4% | 58/79 = 73.4% [63.3, 82.3] | ≥$0.0000 (79 unreported) | ≥$0.0000 | ≥$0.0000 | 90 s | 35,065,330 |
| P | 1: 75.9% | 60/79 = 75.9% [65.8, 84.8] | ≥$0.0000 (79 unreported) | ≥$0.0000 | ≥$0.0000 | 44 s | 13,659,938 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| D | ≥$0.0000 | 73.4% | n/a (cost a lower bound) |
| P | ≥$0.0000 | 75.9% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

