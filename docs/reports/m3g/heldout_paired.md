#### Paired effect against the base (`A`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| K | no detectable effect | +1.0 [-2.7, +4.7] | 9 / 8 / 83 | 1 | 100 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| A (base) | 3: 50.0%, 52.0%, 51.0% | 153/300 = 51.0% [41.7, 60.0] | ≥$0.8214 (1 unreported) | ≥$0.0027 | ≥$0.0054 | 32 s | 3,583,321 |
| K | 3: 51.0%, 53.0%, 52.0% | 156/300 = 52.0% [42.7, 61.3] | $0.9968 | $0.0033 | $0.0064 | 36 s | 5,023,558 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| A | ≥$0.0027 | 51.0% | n/a (cost a lower bound) |
| K | $0.0033 | 52.0% | yes |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

