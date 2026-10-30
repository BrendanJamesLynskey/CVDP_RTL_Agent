#### Effort per problem-run

| Arm | Rows | Turns median / mean | 1-turn rows | LLM calls median / mean | Self-check runs median / mean | Rows with 0 self-check runs |
|---|---|---|---|---|---|---|
| LG+luna | 258 | 2 / 2.55 | 122 (47%) | 5 / 6.08 | 0 / 1.19 | 143 (55%) |
| LG+Opus | 86 | 2 / 2.30 | 40 (47%) | 5 / 5.60 | 1 / 2.06 | 0 (0%) |
| CC+Opus | 86 | 6 / 6.43 | 0 (0%) | 6 / 6.43 | 0 / 0.00 | 86 (100%) |
| CC+Sonnet | 86 | 4 / 4.69 | 0 (0%) | 4 / 4.69 | 0 / 0.00 | 86 (100%) |

Self-check runs are counted from the trace (`taxonomy.py`): the agent's own testbench runs, verify's reruns included, the spec testbench not.

#### Stop reasons

| Arm | give_up | llm_error | max_turns | submit | wall_time |
|---|---|---|---|---|---|
| LG+luna | 0 | 4 | 8 | 243 | 3 |
| LG+Opus | 1 | 0 | 0 | 85 | 0 |
| CC+Opus | 0 | 0 | 0 | 86 | 0 |
| CC+Sonnet | 0 | 0 | 0 | 85 | 1 |

