#### anthropic/claude-haiku-5.5

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 1/3 = 33.3% [6.1, 79.2] | $0.0218 | $0.0073 | $0.0218 | 47 s | 84,629 |
| cid004 RTL modification | 3/3 = 100.0% [43.9, 100.0] | $0.0396 | $0.0132 | $0.0132 | 67 s | 196,670 |
| cid005 spec to RTL, module reuse | 0/2 = 0.0% [0.0, 65.8] | $0.0212 | $0.0106 | n/a | 54 s | 114,302 |
| cid016 bug fixing | 2/2 = 100.0% [34.2, 100.0] | $0.0056 | $0.0028 | $0.0028 | 20 s | 26,331 |
| AMBA slice | 1/2 = 50.0% [9.5, 90.5] | $0.0183 | $0.0091 | $0.0183 | 61 s | 71,209 |
| **All** | 6/10 = 60.0% [31.3, 83.2] | $0.0882 | $0.0088 | $0.0147 | 47 s | 421,932 |

Stop reasons: submit 10


#### deepseek/deepseek-v4.1-flash-1017

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 1/3 = 33.3% [6.1, 79.2] | ≥$0.0257 (1 unreported) | ≥$0.0086 | ≥$0.0257 | 39 s | 36,752 |
| cid004 RTL modification | 3/3 = 100.0% [43.9, 100.0] | $0.0666 | $0.0222 | $0.0222 | 138 s | 204,136 |
| cid005 spec to RTL, module reuse | 0/2 = 0.0% [0.0, 65.8] | $0.1448 | $0.0724 | n/a | 197 s | 267,826 |
| cid016 bug fixing | 2/2 = 100.0% [34.2, 100.0] | $0.0029 | $0.0015 | $0.0015 | 27 s | 18,387 |
| AMBA slice | 1/2 = 50.0% [9.5, 90.5] | $0.0257 | $0.0128 | $0.0257 | 36 s | 36,752 |
| **All** | 6/10 = 60.0% [31.3, 83.2] | ≥$0.2401 (1 unreported) | ≥$0.0240 | ≥$0.0400 | 95 s | 527,101 |

Stop reasons: budget 1, no_summary 1, submit 8


