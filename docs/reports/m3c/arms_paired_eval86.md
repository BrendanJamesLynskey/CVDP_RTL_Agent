#### Paired effect against the base (`A`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| I | no detectable effect | -1.6 [-6.2, +3.1] | 10 / 13 / 63 | 0.678 | 86 | 0 |
| M | no detectable effect | +0.8 [-3.9, +5.8] | 13 / 10 / 63 | 0.678 | 86 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| A (base) | 3: 65.1%, 59.3%, 60.5% | 159/258 = 61.6% [52.3, 70.5] | ≥$1.5805 (1 unreported) | ≥$0.0061 | ≥$0.0099 | 51 s | 7,674,963 |
| I | 3: 59.3%, 65.1%, 55.8% | 155/258 = 60.1% [50.8, 69.0] | $1.7528 | $0.0068 | $0.0113 | 59 s | 8,891,798 |
| M | 3: 59.3%, 64.0%, 64.0% | 161/258 = 62.4% [52.7, 71.7] | ≥$3.0588 (3 unreported) | ≥$0.0119 | ≥$0.0190 | 135 s | 14,783,930 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| A | ≥$0.0061 | 61.6% | n/a (cost a lower bound) |
| I | $0.0068 | 60.1% | yes |
| M | ≥$0.0119 | 62.4% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

