#### Paired effect against the base (`S1c`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| S2c | no detectable effect | +4.7 [-2.3, +11.6] | 7 / 3 / 76 | 0.344 | 86 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| S1c (base) | 1: 66.3% | 57/86 = 66.3% [55.8, 76.7] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 100 s | 41,063,673 |
| S2c | 1: 70.9% | 61/86 = 70.9% [61.6, 80.2] | ≥$0.0000 (86 unreported) | ≥$0.0000 | ≥$0.0000 | 109 s | 43,841,600 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| S1c | ≥$0.0000 | 66.3% | n/a (cost a lower bound) |
| S2c | ≥$0.0000 | 70.9% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

