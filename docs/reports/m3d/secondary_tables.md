#### Effort per problem-run

| Arm | Rows | Turns median / mean | 1-turn rows | LLM calls median / mean | Self-check runs median / mean | Rows with 0 self-check runs |
|---|---|---|---|---|---|---|
| A | 258 | 2 / 2.55 | 122 (47%) | 5 / 6.08 | 0 / 1.19 | 143 (55%) |
| V | 258 | 3 / 4.37 | 26 (10%) | 7 / 9.62 | 2 / 2.84 | 3 (1%) |
| S | 258 | 4 / 4.68 | 17 (7%) | 10 / 11.10 | 2 / 3.03 | 17 (7%) |

Self-check runs are counted from the trace (`taxonomy.py`): the agent's own testbench runs, verify's reruns included, the spec testbench not.

#### Stop reasons

| Arm | llm_error | max_turns | run_budget_exhausted | submit | wall_time |
|---|---|---|---|---|---|
| A | 4 | 8 | 0 | 243 | 3 |
| V | 15 | 18 | 0 | 201 | 24 |
| S | 18 | 17 | 8 | 177 | 38 |

#### The verify step

| Arm | Rows | verify runs | Refusals | Rows with a refusal | Let-throughs | Reruns by verify | Submits verified | Pass rate, verified submits | Pass rate, let-through submits |
|---|---|---|---|---|---|---|---|---|---|
| V | 258 | 383 | 182 | 155 | 10 | 15 | 191 | 131/191 | 5/10 |
| S | 258 | 423 | 246 | 178 | 46 | 19 | 131 | 88/131 | 28/46 |

#### Spec cases, arm S

Spec call outcome over 258 problem-runs: generated 239, unusable 11, not_run 8. Cases per generated set: median 4.

Final-design spec result: pass 135, fail 63, unbuildable 41, none 19.

| All spec cases pass on the final design | Hidden tests pass | Hidden tests fail |
|---|---|---|
| yes | 82 | 53 |
| no (fail or timeout) | 36 | 27 |
| not applied (no cases, unbuildable, error, or not run) | 27 | 33 |


