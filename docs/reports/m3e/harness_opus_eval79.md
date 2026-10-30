#### Paired effect against the base (`LG+Opus`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| CC+Opus | no detectable effect | +1.3 [-7.6, +10.1] | 7 / 6 / 66 | 1 | 79 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| LG+Opus (base) | 1: 78.5% | 62/79 = 78.5% [68.4, 87.3] | $20.5024 | $0.2595 | $0.3307 | 46 s | 3,263,032 |
| CC+Opus | 1: 79.7% | 63/79 = 79.7% [70.9, 88.6] | ≥$0.0000 (79 unreported) | ≥$0.0000 | ≥$0.0000 | 49 s | 13,025,448 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| CC+Opus | ≥$0.0000 | 79.7% | n/a (cost a lower bound) |
| LG+Opus | $0.2595 | 78.5% | yes |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

