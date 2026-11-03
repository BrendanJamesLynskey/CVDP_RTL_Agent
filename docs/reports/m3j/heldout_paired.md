#### Paired effect against the base (`PA`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| R | no detectable effect | +0.0 [-4.3, +4.3] | 7 / 7 / 86 | 1 | 100 | 0 |
| B | no detectable effect | +3.7 [+0.0, +7.7] | 13 / 5 / 82 | 0.0963 | 100 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| PA (base) | 3: 53.0%, 54.0%, 57.0% | 164/300 = 54.7% [45.0, 63.7] | ≥$0.0000 (300 unreported) | ≥$0.0000 | ≥$0.0000 | 23 s | 22,187,522 |
| R | 3: 53.0%, 57.0%, 54.0% | 164/300 = 54.7% [45.3, 63.7] | ≥$0.0000 (300 unreported) | ≥$0.0000 | ≥$0.0000 | 22 s | 15,828,041 |
| B | 3: 61.0%, 56.0%, 58.0% | 175/300 = 58.3% [48.7, 67.3] | ≥$0.0000 (300 unreported) | ≥$0.0000 | ≥$0.0000 | 22 s | 18,973,887 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| PA | ≥$0.0000 | 54.7% | n/a (cost a lower bound) |
| B | ≥$0.0000 | 58.3% | n/a (cost a lower bound) |
| R | ≥$0.0000 | 54.7% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

