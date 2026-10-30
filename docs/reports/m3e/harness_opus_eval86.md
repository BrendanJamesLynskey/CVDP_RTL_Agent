#### Paired effect against the base (`LG+Opus`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| CC+Opus | no detectable effect | +1.2 [-7.0, +9.3] | 7 / 6 / 73 | 1 | 86 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| LG+Opus (base) | 1: 72.1% | 62/86 = 72.1% [62.8, 81.4] | $22.2539 | $0.2588 | $0.3589 | 46 s | 3,515,809 |
| CC+Opus | 1: 73.3% | 63/86 = 73.3% [64.0, 82.6] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 50 s | 14,128,926 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| CC+Opus | ≥$0.0000 | 73.3% | n/a (cost a lower bound) |
| LG+Opus | $0.2588 | 72.1% | yes |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

