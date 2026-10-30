#### Paired effect against the base (`LG+luna`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| CC+Sonnet | better than base | +9.7 [+0.4, +18.6] | 23 / 7 / 49 | 0.00522 | 79 | 0 |
| LG+Opus | better than base | +12.2 [+3.4, +21.5] | 24 / 6 / 49 | 0.00143 | 79 | 0 |
| CC+Opus | better than base | +13.5 [+3.4, +23.2] | 25 / 8 / 46 | 0.00455 | 79 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| LG+luna (base) | 3: 62.0%, 65.8%, 70.9% | 157/237 = 66.2% [57.0, 75.1] | ≥$1.6037 (4 unreported) | ≥$0.0068 | ≥$0.0102 | 74 s | 7,905,267 |
| CC+Sonnet | 1: 75.9% | 60/79 = 75.9% [65.8, 84.8] | ≥$0.0000 (79 unreported) | ≥$0.0000 | ≥$0.0000 | 24 s | 8,682,904 |
| LG+Opus | 1: 78.5% | 62/79 = 78.5% [68.4, 87.3] | $20.5024 | $0.2595 | $0.3307 | 46 s | 3,263,032 |
| CC+Opus | 1: 79.7% | 63/79 = 79.7% [70.9, 88.6] | ≥$0.0000 (79 unreported) | ≥$0.0000 | ≥$0.0000 | 49 s | 13,025,448 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| CC+Opus | ≥$0.0000 | 79.7% | n/a (cost a lower bound) |
| CC+Sonnet | ≥$0.0000 | 75.9% | n/a (cost a lower bound) |
| LG+luna | ≥$0.0068 | 66.2% | n/a (cost a lower bound) |
| LG+Opus | $0.2595 | 78.5% | yes |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

