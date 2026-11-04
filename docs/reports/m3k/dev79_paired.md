#### Paired effect against the base (`R`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| T | no detectable effect | -1.3 [-8.9, +6.3] | 4 / 5 / 70 | 1 | 79 | 0 |
| K | no detectable effect | +1.3 [-5.1, +7.6] | 4 / 3 / 72 | 1 | 79 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| R (base) | 1: 73.4% | 58/79 = 73.4% [63.3, 82.3] | ≥$0.0000 (79 unreported) | ≥$0.0000 | ≥$0.0000 | 37 s | 10,498,116 |
| T | 1: 72.2% | 57/79 = 72.2% [62.0, 82.3] | ≥$0.0000 (79 unreported) | ≥$0.0000 | ≥$0.0000 | 60 s | 15,377,270 |
| K | 1: 74.7% | 59/79 = 74.7% [64.6, 83.5] | ≥$0.0000 (79 unreported) | ≥$0.0000 | ≥$0.0000 | 37 s | 11,302,674 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| R | ≥$0.0000 | 73.4% | n/a (cost a lower bound) |
| T | ≥$0.0000 | 72.2% | n/a (cost a lower bound) |
| K | ≥$0.0000 | 74.7% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

