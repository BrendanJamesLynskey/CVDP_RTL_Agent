#### Paired effect against the base (`A`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| K | no detectable effect | -2.3 [-7.4, +2.3] | 11 / 12 / 63 | 1 | 86 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| A (base) | 3: 57.0%, 60.5%, 65.1% | 157/258 = 60.9% [51.9, 69.8] | ≥$1.7592 (4 unreported) | ≥$0.0068 | ≥$0.0112 | 74 s | 8,621,964 |
| K | 3: 58.1%, 58.1%, 59.3% | 151/258 = 58.5% [49.2, 67.8] | ≥$2.0245 (5 unreported) | ≥$0.0078 | ≥$0.0134 | 56 s | 10,943,228 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| A | ≥$0.0068 | 60.9% | n/a (cost a lower bound) |
| K | ≥$0.0078 | 58.5% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

