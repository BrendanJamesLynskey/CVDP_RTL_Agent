#### Paired effect against the base (`A`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| S1c | no detectable effect | -1.3 [-7.6, +5.1] | 3 / 4 / 72 | 1 | 79 | 0 |
| S2c | no detectable effect | +3.8 [-2.5, +10.1] | 5 / 2 / 72 | 0.453 | 79 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| A (base) | 1: 73.4% | 58/79 = 73.4% [63.3, 82.3] | ≥$0.0000 (79 unreported) | ≥$0.0000 | ≥$0.0000 | 90 s | 35,065,330 |
| S1c | 1: 72.2% | 57/79 = 72.2% [62.0, 82.3] | ≥$0.0000 (79 unreported) | ≥$0.0000 | ≥$0.0000 | 97 s | 36,813,853 |
| S2c | 1: 77.2% | 61/79 = 77.2% [67.1, 86.1] | ≥$0.0000 (79 unreported) | ≥$0.0000 | ≥$0.0000 | 110 s | 40,183,716 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| A | ≥$0.0000 | 73.4% | n/a (cost a lower bound) |
| S1c | ≥$0.0000 | 72.2% | n/a (cost a lower bound) |
| S2c | ≥$0.0000 | 77.2% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

