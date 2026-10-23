#### Paired effect against the base (`gpt-6-luna (default)`)

Effect = mean over common problems of (arm pass rate − base pass rate), in points of pass rate. 95% interval: paired bootstrap over problems. Sign test: exact, two-sided, on the problems that changed. Arms whose interval includes 0 come first.

| Arm | Finding | Effect [95%] | Better / worse / same | Sign test p | Problems | Dropped |
|---|---|---|---|---|---|---|
| claude-haiku-5.5 (low) | no detectable effect | +1.6 [-4.9, +8.2] | 12 / 12 / 68 | 1 | 92 | 0 |
| deepseek-v4.1-flash (off) | worse than base | -11.4 [-20.1, -2.7] | 6 / 21 / 65 | 0.00592 | 92 | 0 |

Problems left out of the paired effect (in only one of the arm and the base; the Arms table below still pools over them): none.

#### Arms

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| gpt-6-luna (default) (base) | 2: 57.6%, 56.5% | 105/184 = 57.1% [46.7, 66.8] | $1.1231 | $0.0061 | $0.0107 | 72 s | 5,429,392 |
| claude-haiku-5.5 (low) | 2: 60.9%, 56.5% | 108/184 = 58.7% [49.5, 67.4] | $2.1423 | $0.0116 | $0.0198 | 45 s | 11,272,864 |
| deepseek-v4.1-flash (off) | 2: 44.6%, 46.7% | 84/184 = 45.7% [35.9, 54.9] | $2.0077 | $0.0109 | $0.0239 | 31 s | 10,345,544 |

#### Pareto: pass rate against $ per problem

| Arm | $/problem | Pass rate | Frontier |
|---|---|---|---|
| gpt-6-luna (default) | $0.0061 | 57.1% | yes |
| deepseek-v4.1-flash (off) | $0.0109 | 45.7% |  |
| claude-haiku-5.5 (low) | $0.0116 | 58.7% | yes |

