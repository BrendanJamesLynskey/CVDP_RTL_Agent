#### anthropic/claude-haiku-5.5 (reasoning low)

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 19/34 = 55.9% [39.5, 71.1] | $0.3034 | $0.0089 | $0.0160 | 36 s | 1,529,762 |
| cid004 RTL modification | 13/25 = 52.0% [33.5, 70.0] | $0.3422 | $0.0137 | $0.0263 | 48 s | 1,772,104 |
| cid005 spec to RTL, module reuse | 13/22 = 59.1% [38.7, 76.7] | $0.3160 | $0.0144 | $0.0243 | 41 s | 1,866,554 |
| cid016 bug fixing | 7/11 = 63.6% [35.4, 84.8] | $0.1508 | $0.0137 | $0.0215 | 48 s | 685,092 |
| AMBA slice | 5/8 = 62.5% [30.6, 86.3] | $0.0715 | $0.0089 | $0.0143 | 54 s | 348,075 |
| **All** | 52/92 = 56.5% [46.3, 66.2] | $1.1123 | $0.0121 | $0.0214 | 44 s | 5,853,512 |

Stop reasons: give_up 7, submit 85

Empty replies: 0 (retried 0); reflect parse retries: 0; reasoning tokens (reported): 653,749

#### deepseek/deepseek-v4.1-flash-1017 (reasoning off)

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 19/34 = 55.9% [39.5, 71.1] | $0.2447 | $0.0072 | $0.0129 | 26 s | 1,498,224 |
| cid004 RTL modification | 11/25 = 44.0% [26.7, 62.9] | $0.4061 | $0.0162 | $0.0369 | 37 s | 1,696,553 |
| cid005 spec to RTL, module reuse | 7/22 = 31.8% [16.4, 52.7] | $0.2567 | $0.0117 | $0.0367 | 34 s | 1,310,019 |
| cid016 bug fixing | 6/11 = 54.5% [28.0, 78.7] | $0.1238 | $0.0113 | $0.0206 | 23 s | 651,837 |
| AMBA slice | 3/8 = 37.5% [13.7, 69.4] | $0.0992 | $0.0124 | $0.0331 | 45 s | 557,050 |
| **All** | 43/92 = 46.7% [36.9, 56.9] | $1.0314 | $0.0112 | $0.0240 | 29 s | 5,156,633 |

Stop reasons: budget 1, give_up 1, max_turns 8, submit 81, wall_time 1

Empty replies: 0 (retried 0); reflect parse retries: 1; reasoning tokens (reported): 0

#### openai/gpt-6-luna (reasoning default)

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 20/34 = 58.8% [42.2, 73.6] | $0.1682 | $0.0049 | $0.0084 | 72 s | 678,787 |
| cid004 RTL modification | 15/25 = 60.0% [40.7, 76.6] | $0.1800 | $0.0072 | $0.0120 | 79 s | 923,704 |
| cid005 spec to RTL, module reuse | 12/22 = 54.5% [34.7, 73.1] | $0.1466 | $0.0067 | $0.0122 | 62 s | 793,697 |
| cid016 bug fixing | 5/11 = 45.5% [21.3, 72.0] | $0.0507 | $0.0046 | $0.0101 | 102 s | 231,232 |
| AMBA slice | 4/8 = 50.0% [21.5, 78.5] | $0.0374 | $0.0047 | $0.0094 | 87 s | 151,187 |
| **All** | 52/92 = 56.5% [46.3, 66.2] | $0.5455 | $0.0059 | $0.0105 | 76 s | 2,627,420 |

Stop reasons: max_turns 3, submit 88, wall_time 1

Empty replies: 0 (retried 0); reflect parse retries: 0; reasoning tokens (reported): 349,792

