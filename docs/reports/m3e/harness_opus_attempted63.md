#### Paired effect against the base (`LG+Opus`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| CC+Opus | no detectable effect | -4.8 [-14.3, +4.8] | 3 / 6 / 54 | 0.508 | 63 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| LG+Opus (base) | 1: 82.5% | 52/63 = 82.5% [73.0, 92.1] | $16.1769 | $0.2568 | $0.3111 | 43 s | 2,593,570 |
| CC+Opus | 1: 77.8% | 49/63 = 77.8% [68.3, 87.3] | ≥$0.0000 (63 unreported) | ≥$0.0000 | ≥$0.0000 | 48 s | 10,602,640 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| CC+Opus | ≥$0.0000 | 77.8% | n/a (cost a lower bound) |
| LG+Opus | $0.2568 | 82.5% | yes |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

