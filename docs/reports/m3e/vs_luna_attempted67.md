#### Paired effect against the base (`LG+luna`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| CC+Opus | no detectable effect | +9.0 [-1.0, +18.9] | 16 / 6 / 45 | 0.0525 | 67 | 0 |
| CC+Sonnet | no detectable effect | +9.0 [-1.5, +19.4] | 17 / 6 / 44 | 0.0347 | 67 | 0 |
| LG+Opus | better than base | +13.4 [+4.0, +22.4] | 19 / 3 / 45 | 0.000855 | 67 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| LG+luna (base) | 3: 62.7%, 62.7%, 67.2% | 129/201 = 64.2% [54.2, 74.1] | ≥$1.5114 (4 unreported) | ≥$0.0075 | ≥$0.0117 | 84 s | 7,488,325 |
| CC+Opus | 1: 73.1% | 49/67 = 73.1% [62.7, 83.6] | ≥$0.0000 (67 unreported) | ≥$0.0000 | ≥$0.0000 | 49 s | 11,247,513 |
| CC+Sonnet | 1: 73.1% | 49/67 = 73.1% [62.7, 83.6] | ≥$0.0000 (67 unreported) | ≥$0.0000 | ≥$0.0000 | 23 s | 7,755,818 |
| LG+Opus | 1: 77.6% | 52/67 = 77.6% [67.2, 86.6] | $17.1147 | $0.2554 | $0.3291 | 44 s | 2,728,813 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| CC+Opus | ≥$0.0000 | 73.1% | n/a (cost a lower bound) |
| CC+Sonnet | ≥$0.0000 | 73.1% | n/a (cost a lower bound) |
| LG+luna | ≥$0.0075 | 64.2% | n/a (cost a lower bound) |
| LG+Opus | $0.2554 | 77.6% | yes |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

