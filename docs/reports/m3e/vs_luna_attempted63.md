#### Paired effect against the base (`LG+luna`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| CC+Opus | no detectable effect | +9.5 [-1.1, +20.6] | 16 / 6 / 41 | 0.0525 | 63 | 0 |
| CC+Sonnet | no detectable effect | +9.5 [-1.6, +20.6] | 17 / 6 / 40 | 0.0347 | 63 | 0 |
| LG+Opus | better than base | +14.3 [+4.2, +23.8] | 19 / 3 / 41 | 0.000855 | 63 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| LG+luna (base) | 3: 66.7%, 66.7%, 71.4% | 129/189 = 68.3% [57.7, 78.8] | ≥$1.4227 (4 unreported) | ≥$0.0075 | ≥$0.0110 | 83 s | 7,077,189 |
| CC+Opus | 1: 77.8% | 49/63 = 77.8% [68.3, 87.3] | ≥$0.0000 (63 unreported) | ≥$0.0000 | ≥$0.0000 | 48 s | 10,602,640 |
| CC+Sonnet | 1: 77.8% | 49/63 = 77.8% [66.7, 87.3] | ≥$0.0000 (63 unreported) | ≥$0.0000 | ≥$0.0000 | 23 s | 7,371,839 |
| LG+Opus | 1: 82.5% | 52/63 = 82.5% [73.0, 92.1] | $16.1769 | $0.2568 | $0.3111 | 43 s | 2,593,570 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| CC+Opus | ≥$0.0000 | 77.8% | n/a (cost a lower bound) |
| CC+Sonnet | ≥$0.0000 | 77.8% | n/a (cost a lower bound) |
| LG+luna | ≥$0.0075 | 68.3% | n/a (cost a lower bound) |
| LG+Opus | $0.2568 | 82.5% | yes |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

