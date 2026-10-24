#### Paired effect against the base (`A`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| C | no detectable effect | -1.6 [-6.5, +3.3] | 9 / 11 / 72 | 0.824 | 92 | 0 |
| D | no detectable effect | -1.6 [-6.0, +2.7] | 5 / 9 / 78 | 0.424 | 92 | 0 |
| G | no detectable effect | -1.6 [-7.1, +3.8] | 7 / 11 / 74 | 0.481 | 92 | 0 |
| B | no detectable effect | -1.1 [-6.0, +4.3] | 8 / 11 / 73 | 0.648 | 92 | 0 |
| E | no detectable effect | -0.5 [-4.9, +4.3] | 5 / 7 / 80 | 0.774 | 92 | 0 |
| F | no detectable effect | +3.8 [-1.1, +9.2] | 9 / 5 / 78 | 0.424 | 92 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| A (base) | 2: 57.6%, 55.4% | 104/184 = 56.5% [46.7, 66.3] | $1.1059 | $0.0060 | $0.0106 | 54 s | 5,388,892 |
| C | 2: 54.3%, 55.4% | 101/184 = 54.9% [46.2, 63.6] | ≥$1.4788 (1 unreported) | ≥$0.0080 | ≥$0.0146 | 60 s | 6,914,086 |
| D | 2: 54.3%, 55.4% | 101/184 = 54.9% [45.7, 63.6] | $1.7060 | $0.0093 | $0.0169 | 58 s | 8,297,182 |
| G | 2: 54.3%, 55.4% | 101/184 = 54.9% [45.7, 63.6] | $1.1886 | $0.0065 | $0.0118 | 52 s | 5,860,807 |
| B | 2: 58.7%, 52.2% | 102/184 = 55.4% [45.7, 64.7] | $1.0719 | $0.0058 | $0.0105 | 45 s | 5,424,321 |
| E | 2: 57.6%, 54.3% | 103/184 = 56.0% [46.2, 65.8] | $1.1152 | $0.0061 | $0.0108 | 55 s | 5,513,085 |
| F | 2: 62.0%, 58.7% | 111/184 = 60.3% [50.5, 69.6] | $1.1649 | $0.0063 | $0.0105 | 59 s | 5,975,170 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| B | $0.0058 | 55.4% | yes |
| A | $0.0060 | 56.5% | yes |
| E | $0.0061 | 56.0% |  |
| F | $0.0063 | 60.3% | yes |
| G | $0.0065 | 54.9% |  |
| C | ≥$0.0080 | 54.9% | n/a (cost a lower bound) |
| D | $0.0093 | 54.9% |  |

≥: some of the arm's cost was not reported, so its $/problem is a lower bound. It is drawn hollow and kept off the frontier.

