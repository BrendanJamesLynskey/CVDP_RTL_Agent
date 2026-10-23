#### Across seeds

| Model | Seeds | Problems per seed | Mean pass@1 [min–max] | Pooled pass@1 [95% problem bootstrap] | Cost, all seeds | $/solved, pooled |
|---|---|---|---|---|---|---|
| anthropic/claude-haiku-5.5 (reasoning low) | 3 | 30 | 50.0% [46.7–53.3] | 45/90 = 50.0% [32.2, 66.7] | $1.0762 | $0.0239 |
| deepseek/deepseek-v4.1-flash-1017 (reasoning off) | 3 | 30 | 43.3% [43.3–43.3] | 39/90 = 43.3% [26.7, 60.0] | ≥$1.1605 (1 unreported) | ≥$0.0298 |
| openai/gpt-6-luna (reasoning default) | 3 | 30 | 43.3% [36.7–50.0] | 39/90 = 43.3% [27.8, 60.0] | $0.6338 | $0.0163 |

#### anthropic/claude-haiku-5.5 (reasoning low)

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 20/33 = 60.6% [43.7, 75.3] | $0.2437 | $0.0074 | $0.0122 | 35 s | 1,136,100 |
| cid004 RTL modification | 7/24 = 29.2% [14.9, 49.2] | $0.3919 | $0.0163 | $0.0560 | 75 s | 1,912,738 |
| cid005 spec to RTL, module reuse | 9/21 = 42.9% [24.5, 63.5] | $0.2770 | $0.0132 | $0.0308 | 43 s | 1,649,921 |
| cid016 bug fixing | 9/12 = 75.0% [46.8, 91.1] | $0.1636 | $0.0136 | $0.0182 | 36 s | 761,255 |
| AMBA slice | 3/9 = 33.3% [12.1, 64.6] | $0.1202 | $0.0134 | $0.0401 | 52 s | 590,312 |
| **All** | 45/90 = 50.0% [39.9, 60.1] | $1.0762 | $0.0120 | $0.0239 | 44 s | 5,460,014 |

Stop reasons: give_up 5, submit 85

Empty replies: 0 (retried 0); reflect parse retries: 0; reasoning tokens (reported): 763,939

#### deepseek/deepseek-v4.1-flash-1017 (reasoning off)

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 15/33 = 45.5% [29.8, 62.0] | $0.2066 | $0.0063 | $0.0138 | 26 s | 992,974 |
| cid004 RTL modification | 6/24 = 25.0% [12.0, 44.9] | $0.6795 | $0.0283 | $0.1133 | 51 s | 2,359,011 |
| cid005 spec to RTL, module reuse | 7/21 = 33.3% [17.2, 54.6] | $0.2459 | $0.0117 | $0.0351 | 33 s | 1,719,629 |
| cid016 bug fixing | 11/12 = 91.7% [64.6, 98.5] | ≥$0.0285 (1 unreported) | ≥$0.0024 | ≥$0.0026 | 12 s | 338,827 |
| AMBA slice | 3/9 = 33.3% [12.1, 64.6] | $0.1527 | $0.0170 | $0.0509 | 47 s | 554,279 |
| **All** | 39/90 = 43.3% [33.6, 53.6] | ≥$1.1605 (1 unreported) | ≥$0.0129 | ≥$0.0298 | 34 s | 5,410,441 |

Stop reasons: budget 1, llm_error 1, max_turns 12, submit 76

Empty replies: 0 (retried 0); reflect parse retries: 0; reasoning tokens (reported): 0

#### openai/gpt-6-luna (reasoning default)

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 17/33 = 51.5% [35.2, 67.5] | $0.1770 | $0.0054 | $0.0104 | 73 s | 807,882 |
| cid004 RTL modification | 6/24 = 25.0% [12.0, 44.9] | $0.2621 | $0.0109 | $0.0437 | 80 s | 1,343,665 |
| cid005 spec to RTL, module reuse | 8/21 = 38.1% [20.8, 59.1] | $0.1567 | $0.0075 | $0.0196 | 64 s | 1,018,728 |
| cid016 bug fixing | 8/12 = 66.7% [39.1, 86.2] | $0.0380 | $0.0032 | $0.0048 | 42 s | 188,147 |
| AMBA slice | 2/9 = 22.2% [6.3, 54.7] | $0.0751 | $0.0083 | $0.0375 | 100 s | 396,783 |
| **All** | 39/90 = 43.3% [33.6, 53.6] | $0.6338 | $0.0070 | $0.0163 | 69 s | 3,358,422 |

Stop reasons: max_turns 8, submit 82

Empty replies: 0 (retried 0); reflect parse retries: 0; reasoning tokens (reported): 403,896

