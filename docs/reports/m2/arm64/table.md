#### anthropic/claude-haiku-5.5 (reasoning low)

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 21/34 = 61.8% [45.0, 76.1] | $0.2918 | $0.0086 | $0.0139 | 45 s | 1,436,050 |
| cid004 RTL modification | 14/25 = 56.0% [37.1, 73.3] | $0.3748 | $0.0150 | $0.0268 | 61 s | 1,932,417 |
| cid005 spec to RTL, module reuse | 12/22 = 54.5% [34.7, 73.1] | $0.2575 | $0.0117 | $0.0215 | 45 s | 1,559,974 |
| cid016 bug fixing | 9/11 = 81.8% [52.3, 94.9] | $0.1059 | $0.0096 | $0.0118 | 36 s | 490,911 |
| AMBA slice | 5/8 = 62.5% [30.6, 86.3] | $0.0928 | $0.0116 | $0.0186 | 59 s | 433,614 |
| **All** | 56/92 = 60.9% [50.7, 70.2] | $1.0300 | $0.0112 | $0.0184 | 47 s | 5,419,352 |

Stop reasons: give_up 3, submit 89

Empty replies: 0 (retried 0); reflect parse retries: 0; reasoning tokens (reported): 600,796

#### deepseek/deepseek-v4.1-flash-1017 (reasoning off)

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 18/34 = 52.9% [36.7, 68.5] | $0.2835 | $0.0083 | $0.0157 | 28 s | 1,313,313 |
| cid004 RTL modification | 10/25 = 40.0% [23.4, 59.3] | $0.3596 | $0.0144 | $0.0360 | 42 s | 1,850,560 |
| cid005 spec to RTL, module reuse | 7/22 = 31.8% [16.4, 52.7] | $0.2166 | $0.0098 | $0.0309 | 39 s | 1,414,633 |
| cid016 bug fixing | 6/11 = 54.5% [28.0, 78.7] | $0.1167 | $0.0106 | $0.0194 | 38 s | 610,405 |
| AMBA slice | 3/8 = 37.5% [13.7, 69.4] | $0.0905 | $0.0113 | $0.0302 | 47 s | 474,677 |
| **All** | 41/92 = 44.6% [34.8, 54.7] | $0.9763 | $0.0106 | $0.0238 | 33 s | 5,188,911 |

Stop reasons: max_turns 9, submit 83

Empty replies: 0 (retried 0); reflect parse retries: 1; reasoning tokens (reported): 0

#### openai/gpt-6-luna (reasoning default)

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 20/34 = 58.8% [42.2, 73.6] | $0.1914 | $0.0056 | $0.0096 | 65 s | 833,863 |
| cid004 RTL modification | 14/25 = 56.0% [37.1, 73.3] | $0.1710 | $0.0068 | $0.0122 | 66 s | 878,363 |
| cid005 spec to RTL, module reuse | 13/22 = 59.1% [38.7, 76.7] | $0.1320 | $0.0060 | $0.0102 | 56 s | 719,765 |
| cid016 bug fixing | 6/11 = 54.5% [28.0, 78.7] | $0.0833 | $0.0076 | $0.0139 | 78 s | 369,981 |
| AMBA slice | 4/8 = 50.0% [21.5, 78.5] | $0.0446 | $0.0056 | $0.0111 | 72 s | 184,504 |
| **All** | 53/92 = 57.6% [47.4, 67.2] | $0.5776 | $0.0063 | $0.0109 | 67 s | 2,801,972 |

Stop reasons: max_turns 2, submit 87, wall_time 3

Empty replies: 1 (retried 0); reflect parse retries: 0; reasoning tokens (reported): 372,761

