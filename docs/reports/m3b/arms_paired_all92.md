#### Paired effect against the base (`A`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| C | no detectable effect | +1.4 [-2.9, +5.8] | 10 / 8 / 74 | 0.815 | 92 | 0 |
| B | better than base | +4.0 [+0.0, +8.3] | 15 / 8 / 69 | 0.21 | 92 | 0 |
| D | better than base | +6.9 [+2.2, +12.0] | 14 / 4 / 74 | 0.0309 | 92 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| A (base) | 6: 55.8%, 59.3%, 58.1%, 0.0%, 0.0%, 0.0% | 149/276 = 54.0% [44.9, 63.0] | $1.9694 | $0.0071 | $0.0132 | 52 s | 9,575,660 |
| C | 6: 59.3%, 59.3%, 59.3%, 0.0%, 0.0%, 0.0% | 153/276 = 55.4% [46.4, 65.2] | $1.8727 | $0.0068 | $0.0122 | 51 s | 8,996,359 |
| B | 6: 62.8%, 59.3%, 64.0%, 0.0%, 0.0%, 0.0% | 160/276 = 58.0% [48.9, 67.0] | $2.0495 | $0.0074 | $0.0128 | 73 s | 49,603,302 |
| D | 6: 60.5%, 68.6%, 66.3%, 0.0%, 0.0%, 0.0% | 168/276 = 60.9% [51.4, 69.9] | $1.9013 | $0.0069 | $0.0113 | 68 s | 46,909,185 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| C | $0.0068 | 55.4% | yes |
| D | $0.0069 | 60.9% | yes |
| A | $0.0071 | 54.0% |  |
| B | $0.0074 | 58.0% |  |


| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| D | no detectable effect | +2.9 [-0.4, +6.5] | 9 / 3 / 80 | 0.146 | 92 | 0 |

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| D | better than base | +5.4 [+1.8, +9.8] | 9 / 1 / 82 | 0.0215 | 92 | 0 |

