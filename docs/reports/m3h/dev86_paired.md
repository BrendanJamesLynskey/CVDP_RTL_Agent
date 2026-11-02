#### Paired effect against the base (`A`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| S1c | no detectable effect | -1.2 [-7.0, +4.7] | 3 / 4 / 79 | 1 | 86 | 0 |
| S2c | no detectable effect | +3.5 [-2.3, +9.3] | 5 / 2 / 79 | 0.453 | 86 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| A (base) | 1: 67.4% | 58/86 = 67.4% [58.1, 76.7] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 89 s | 38,944,289 |
| S1c | 1: 66.3% | 57/86 = 66.3% [55.8, 76.7] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 100 s | 41,063,673 |
| S2c | 1: 70.9% | 61/86 = 70.9% [61.6, 80.2] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 109 s | 43,841,600 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| A | ≥$0.0000 | 67.4% | n/a (cost a lower bound) |
| S1c | ≥$0.0000 | 66.3% | n/a (cost a lower bound) |
| S2c | ≥$0.0000 | 70.9% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

