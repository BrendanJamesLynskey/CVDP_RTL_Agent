#### Paired effect against the base (`LG+Opus`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| CC+Opus | no detectable effect | -4.5 [-13.4, +4.5] | 3 / 6 / 58 | 0.508 | 67 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| LG+Opus (base) | 1: 77.6% | 52/67 = 77.6% [67.2, 86.6] | $17.1147 | $0.2554 | $0.3291 | 44 s | 2,728,813 |
| CC+Opus | 1: 73.1% | 49/67 = 73.1% [62.7, 83.6] | ≥$0.0000 (67 unreported) | ≥$0.0000 | ≥$0.0000 | 49 s | 11,247,513 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| CC+Opus | ≥$0.0000 | 73.1% | n/a (cost a lower bound) |
| LG+Opus | $0.2554 | 77.6% | yes |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

