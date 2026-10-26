#### Paired effect against the base (`luna`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| haiku | no detectable effect | +4.7 [-2.3, +11.2] | 17 / 8 / 61 | 0.108 | 86 | 0 |
| fable | no detectable effect | +5.8 [-1.2, +12.8] | 17 / 8 / 61 | 0.108 | 86 | 0 |
| sonnet | no detectable effect | +8.1 [-0.4, +17.4] | 22 / 9 / 55 | 0.0294 | 86 | 0 |
| opus | better than base | +11.6 [+1.9, +21.3] | 25 / 9 / 52 | 0.00904 | 86 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| luna (base) | 3: 65.1%, 59.3%, 60.5% | 159/258 = 61.6% [52.3, 70.5] | ≥$1.5805 (1 unreported) | ≥$0.0061 | ≥$0.0099 | 51 s | 7,674,963 |
| haiku | 1: 66.3% | 57/86 = 66.3% [55.8, 76.7] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 83 s | 39,199,840 |
| fable | 1: 67.4% | 58/86 = 67.4% [57.0, 76.7] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 265 s | 38,242,506 |
| sonnet | 1: 69.8% | 60/86 = 69.8% [59.3, 79.1] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 24 s | 9,302,520 |
| opus | 1: 73.3% | 63/86 = 73.3% [64.0, 82.6] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 50 s | 14,128,926 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| haiku | ≥$0.0000 | 66.3% | n/a (cost a lower bound) |
| sonnet | ≥$0.0000 | 69.8% | n/a (cost a lower bound) |
| opus | ≥$0.0000 | 73.3% | n/a (cost a lower bound) |
| fable | ≥$0.0000 | 67.4% | n/a (cost a lower bound) |
| luna | ≥$0.0061 | 61.6% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

