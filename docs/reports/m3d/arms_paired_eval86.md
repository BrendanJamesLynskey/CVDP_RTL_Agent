#### Paired effect against the base (`A`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 97.5% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [97.5%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| S | no detectable effect | -4.7 [-11.2, +1.6] | 12 / 19 / 55 | 0.281 | 86 | 0 |
| V | no detectable effect | -1.9 [-6.6, +2.3] | 7 / 9 / 70 | 0.804 | 86 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| A (base) | 3: 57.0%, 60.5%, 65.1% | 157/258 = 60.9% [51.9, 69.8] | ≥$1.7592 (4 unreported) | ≥$0.0068 | ≥$0.0112 | 74 s | 8,621,964 |
| S | 3: 55.8%, 57.0%, 55.8% | 145/258 = 56.2% [46.9, 65.1] | ≥$3.3892 (18 unreported) | ≥$0.0131 | ≥$0.0234 | 247 s | 15,249,575 |
| V | 3: 59.3%, 61.6%, 55.8% | 152/258 = 58.9% [49.6, 68.6] | ≥$2.7506 (15 unreported) | ≥$0.0107 | ≥$0.0181 | 135 s | 13,226,965 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| A | ≥$0.0068 | 60.9% | n/a (cost a lower bound) |
| V | ≥$0.0107 | 58.9% | n/a (cost a lower bound) |
| S | ≥$0.0131 | 56.2% | n/a (cost a lower bound) |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

