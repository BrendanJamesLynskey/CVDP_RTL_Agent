#### anthropic/claude-haiku-5.5 (reasoning low)

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 2/3 = 66.7% [20.8, 93.9] | $0.0134 | $0.0045 | $0.0067 | 26 s | 57,513 |
| cid004 RTL modification | 3/3 = 100.0% [43.9, 100.0] | $0.0256 | $0.0085 | $0.0085 | 36 s | 156,449 |
| cid005 spec to RTL, module reuse | 0/2 = 0.0% [0.0, 65.8] | $0.0408 | $0.0204 | n/a | 84 s | 256,793 |
| cid016 bug fixing | 2/2 = 100.0% [34.2, 100.0] | $0.0065 | $0.0032 | $0.0032 | 22 s | 36,542 |
| AMBA slice | 2/2 = 100.0% [34.2, 100.0] | $0.0110 | $0.0055 | $0.0055 | 38 s | 46,963 |
| **All** | 7/10 = 70.0% [39.7, 89.2] | $0.0863 | $0.0086 | $0.0123 | 24 s | 507,297 |

Stop reasons: submit 10

Empty replies: 0 (retried 0); reflect parse retries: 0; reasoning tokens (reported): 43,322

#### anthropic/claude-haiku-5.5 (reasoning off)

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 1/3 = 33.3% [6.1, 79.2] | $0.0207 | $0.0069 | $0.0207 | 30 s | 100,994 |
| cid004 RTL modification | 2/3 = 66.7% [20.8, 93.9] | $0.0954 | $0.0318 | $0.0477 | 105 s | 599,241 |
| cid005 spec to RTL, module reuse | 0/2 = 0.0% [0.0, 65.8] | $0.0359 | $0.0179 | n/a | 53 s | 250,370 |
| cid016 bug fixing | 2/2 = 100.0% [34.2, 100.0] | $0.0050 | $0.0025 | $0.0025 | 13 s | 36,472 |
| AMBA slice | 1/2 = 50.0% [9.5, 90.5] | $0.0160 | $0.0080 | $0.0160 | 39 s | 75,193 |
| **All** | 5/10 = 50.0% [23.7, 76.3] | $0.1570 | $0.0157 | $0.0314 | 27 s | 987,077 |

Stop reasons: give_up 1, submit 9

Empty replies: 0 (retried 0); reflect parse retries: 0; reasoning tokens (reported): 0

#### openai/gpt-6-luna (reasoning default)

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 1/3 = 33.3% [6.1, 79.2] | $0.0093 | $0.0031 | $0.0093 | 55 s | 36,185 |
| cid004 RTL modification | 3/3 = 100.0% [43.9, 100.0] | $0.0276 | $0.0092 | $0.0092 | 126 s | 148,605 |
| cid005 spec to RTL, module reuse | 0/2 = 0.0% [0.0, 65.8] | $0.0122 | $0.0061 | n/a | 62 s | 72,747 |
| cid016 bug fixing | 2/2 = 100.0% [34.2, 100.0] | $0.0029 | $0.0015 | $0.0015 | 26 s | 14,207 |
| AMBA slice | 1/2 = 50.0% [9.5, 90.5] | $0.0075 | $0.0037 | $0.0075 | 73 s | 29,359 |
| **All** | 6/10 = 60.0% [31.3, 83.2] | $0.0519 | $0.0052 | $0.0087 | 64 s | 271,744 |

Stop reasons: submit 10

Empty replies: 0 (retried 0); reflect parse retries: 0; reasoning tokens (reported): 25,681

#### openai/gpt-6-luna (reasoning low)

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 1/3 = 33.3% [6.1, 79.2] | $0.0074 | $0.0025 | $0.0074 | 26 s | 35,887 |
| cid004 RTL modification | 2/3 = 66.7% [20.8, 93.9] | $0.0507 | $0.0169 | $0.0254 | 119 s | 324,530 |
| cid005 spec to RTL, module reuse | 0/2 = 0.0% [0.0, 65.8] | $0.0097 | $0.0048 | n/a | 33 s | 67,817 |
| cid016 bug fixing | 2/2 = 100.0% [34.2, 100.0] | $0.0016 | $0.0008 | $0.0008 | 16 s | 9,416 |
| AMBA slice | 1/2 = 50.0% [9.5, 90.5] | $0.0063 | $0.0032 | $0.0063 | 54 s | 30,768 |
| **All** | 5/10 = 50.0% [23.7, 76.3] | $0.0694 | $0.0069 | $0.0139 | 33 s | 437,650 |

Stop reasons: max_turns 1, submit 9

Empty replies: 0 (retried 0); reflect parse retries: 0; reasoning tokens (reported): 15,308

#### openai/gpt-6-luna (reasoning off)

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 1/3 = 33.3% [6.1, 79.2] | $0.0051 | $0.0017 | $0.0051 | 13 s | 28,159 |
| cid004 RTL modification | 1/3 = 33.3% [6.1, 79.2] | $0.0287 | $0.0096 | $0.0287 | 33 s | 160,790 |
| cid005 spec to RTL, module reuse | 0/2 = 0.0% [0.0, 65.8] | $0.0094 | $0.0047 | n/a | 13 s | 67,189 |
| cid016 bug fixing | 2/2 = 100.0% [34.2, 100.0] | $0.0025 | $0.0012 | $0.0012 | 12 s | 18,067 |
| AMBA slice | 1/2 = 50.0% [9.5, 90.5] | $0.0040 | $0.0020 | $0.0040 | 16 s | 22,729 |
| **All** | 4/10 = 40.0% [16.8, 68.7] | $0.0457 | $0.0046 | $0.0114 | 13 s | 274,205 |

Stop reasons: max_turns 1, submit 9

Empty replies: 0 (retried 0); reflect parse retries: 0; reasoning tokens (reported): 0

