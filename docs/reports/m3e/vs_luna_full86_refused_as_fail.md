#### Paired effect against the base (`LG+luna`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| LG+Opus | no detectable effect | -0.4 [-10.5, +9.7] | 19 / 15 / 52 | 0.608 | 86 | 0 |
| CC+Sonnet | better than base | +8.9 [+0.8, +18.2] | 23 / 7 / 56 | 0.00522 | 86 | 0 |
| CC+Opus | better than base | +12.4 [+3.1, +21.7] | 25 / 8 / 53 | 0.00455 | 86 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| LG+luna (base) | 3: 57.0%, 60.5%, 65.1% | 157/258 = 60.9% [51.9, 69.8] | ≥$1.7592 (4 unreported) | ≥$0.0068 | ≥$0.0112 | 74 s | 8,621,964 |
| LG+Opus | 1: 60.5% | 52/86 = 60.5% [50.0, 70.9] | $17.1147 | $0.1990 | $0.3291 | 32 s | 2,728,813 |
| CC+Sonnet | 1: 69.8% | 60/86 = 69.8% [59.3, 79.1] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 24 s | 9,302,520 |
| CC+Opus | 1: 73.3% | 63/86 = 73.3% [64.0, 82.6] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 50 s | 14,128,926 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| CC+Opus | ≥$0.0000 | 73.3% | n/a (cost a lower bound) |
| CC+Sonnet | ≥$0.0000 | 69.8% | n/a (cost a lower bound) |
| LG+luna | ≥$0.0068 | 60.9% | n/a (cost a lower bound) |
| LG+Opus | $0.1990 | 60.5% | yes |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

