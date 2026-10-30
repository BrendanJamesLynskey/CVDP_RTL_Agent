#### Effort per problem-run

| Arm | Rows | Turns median / mean | 1-turn rows | LLM calls median / mean | Self-check runs median / mean | Rows with 0 self-check runs |
|---|---|---|---|---|---|---|
| LG+luna | 201 | 2 / 2.75 | 83 (41%) | 5 / 6.46 | 1 / 1.34 | 99 (49%) |
| LG+Opus | 67 | 1 / 2.15 | 34 (51%) | 3 / 5.30 | 1 / 1.99 | 0 (0%) |
| CC+Opus | 67 | 6 / 6.49 | 0 (0%) | 6 / 6.49 | 0 / 0.00 | 67 (100%) |
| CC+Sonnet | 67 | 4 / 4.90 | 0 (0%) | 4 / 4.90 | 0 / 0.00 | 67 (100%) |

Self-check runs are counted from the trace (`taxonomy.py`): the agent's own testbench runs, verify's reruns included, the spec testbench not.

#### Stop reasons

| Arm | llm_error | max_turns | submit | wall_time |
|---|---|---|---|---|
| LG+luna | 4 | 7 | 187 | 3 |
| LG+Opus | 0 | 0 | 67 | 0 |
| CC+Opus | 0 | 0 | 67 | 0 |
| CC+Sonnet | 0 | 0 | 66 | 1 |

