#### Paired effect against the base (`A`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| B | better than base | +4.7 [+1.0, +8.5] | 16 / 7 / 63 | 0.0931 | 86 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| A (base) | 6: 59.3%, 59.3%, 57.0%, 61.6%, 59.3%, 51.2% | 299/516 = 57.9% [48.6, 67.1] | ≥$3.7574 (1 unreported) | ≥$0.0073 | ≥$0.0126 | 51 s | 18,181,434 |
| B | 6: 64.0%, 62.8%, 67.4%, 58.1%, 65.1%, 58.1% | 323/516 = 62.6% [53.5, 71.7] | ≥$3.8341 (1 unreported) | ≥$0.0074 | ≥$0.0119 | 72 s | 89,914,785 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| A | ≥$0.0073 | 57.9% | n/a (cost a lower bound) |
| B | ≥$0.0074 | 62.6% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

