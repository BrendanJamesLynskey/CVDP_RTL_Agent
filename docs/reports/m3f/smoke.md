# M3f: smoke runs

These runs check the plumbing, not the score. There were 4 runs on 3 problems, from `m3f-split-roles` at `a26c924`,
on 2026-10-30. The problems come from brief 09's part two (`queue_0001`, `lfsr_0005`,
`binary_search_tree_algorithms_0001`), which luna's arms A and S never solved in M3d (0 of 9 each).

Settings: those of M3c arm A, except as follows:

- 3 threads;
- a $1.00 guard for P and T, and $1.50 for PT and C;
- `role_reasoning=low` and `role_budget_usd=0.50`;
- for C, a $0.30 edit-loop budget.

The per-problem CSVs are in [`smoke/`](smoke/).

| Run | Arm | plan | spec cases | edit, reflect | Reported spend | Unreported calls |
|---|---|---|---|---|---|---|
| [41095968060](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41095968060) | P | Sonnet 5.5 | off | luna | $0.0663 | 0 |
| [41095985036](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41095985036) | T | luna | Sonnet 5.5 | luna | $0.1021 | 0 |
| [41096941362](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41096941362) | PT | Sonnet 5.5 | Sonnet 5.5 | luna | $0.1674 | 1 |
| [41096957348](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41096957348) | C | Sonnet 5.5 | off | `moonshotai/kimi-k2.7-code` | $0.2583 | 2 |
| | | | | | **$0.5941** | 3 |

The 3 unreported calls are edits abandoned at the wall-cap deadline: 1 by luna and 2 by kimi. They cost under about
$0.10 together. Key: $83.53 left before the smoke runs (run 41095872516) and $78.71 after (run 41098410322). The
M3e-finish session spent from the same key in that window, so the difference is not M3f's alone.

## Per problem

| Arm | Problem | Pass | Stop | Failure label | Turns | LLM calls | Cost | Sonnet's cost | Spec cases | Spec cases on final |
|---|---|---|---|---|---|---|---|---|---|---|
| P | `binary_search_tree_algorithms_0001` | 0 | submit | tests_failed_no_selfcheck | 3 | 7 | $0.0364 | $0.0284 | - | - |
| P | `lfsr_0005` | 0 | submit | tests_failed_no_selfcheck | 2 | 5 | $0.0164 | $0.0098 | - | - |
| P | `queue_0001` | 0 | submit | tests_failed_no_selfcheck | 2 | 5 | $0.0136 | $0.0108 | - | - |
| T | `binary_search_tree_algorithms_0001` | 0 | max_turns | stopped_by_cap | 10 | 22 | $0.0509 | $0.0293 | 2 | fail |
| T | `lfsr_0005` | 0 | submit | tests_failed_selfcheck_passed | 3 | 8 | $0.0197 | $0.0123 | 1 | pass |
| T | `queue_0001` | 0 | submit | tests_failed_selfcheck_passed | 5 | 12 | $0.0315 | $0.0220 | 7 | fail |
| PT | `binary_search_tree_algorithms_0001` | 0 | llm_error | llm_error | 9 | 19 | $0.0859 | $0.0572 | 2 | pass |
| PT | `lfsr_0005` | 0 | submit | tests_failed_selfcheck_passed | 2 | 6 | $0.0294 | $0.0231 | 1 | pass |
| PT | `queue_0001` | 0 | max_turns | stopped_by_cap | 10 | 22 | $0.0521 | $0.0324 | 7 | fail |
| C | `binary_search_tree_algorithms_0001` | 0 | llm_error | llm_error | 1 | 2 | $0.0289 | $0.0289 | - | - |
| C | `lfsr_0005` | 0 | submit | tests_failed_selfcheck_failed | 1 | 3 | $0.1325 | $0.0086 | - | - |
| C | `queue_0001` | 0 | llm_error | llm_error | 2 | 4 | $0.0968 | $0.0103 | - | - |

## What the smoke runs show

- **Routing works.** In every trace, `plan` (P, PT, C) and `spec` (T, PT) are served by
  `anthropic/claude-sonnet-5.5` through "Claude Platform on AWS". Every `edit` and `reflect` call goes to the edit
  model. Each start event's switches name the role models, and every row carries `role_models`, `role_cost_usd`,
  `main_cost_usd` and `cost_by_model`.
- **Reasoning.** No role call was refused for its `reasoning` field. Sonnet at `low` reported 0 reasoning tokens on
  all 15 of its calls, as M3e's Sonnet smoke mostly did. Luna stayed at `default` throughout.
- **Sonnet's plans read the spec well.** They named the right ports, parameters and state changes on all 3
  problems. On `lfsr_0005` the plan worked the documented sequence through to the wrong taps. Luna still failed all 3
  in P, and submitted each time without a testbench, as arm A does. A good plan does not make luna test.
- **Sonnet's spec cases.** It wrote 2, 1 and 7 cases. On `lfsr_0005` its single case passed on luna's final design
  in both T and PT while the hidden tests failed, so one case was too few to catch the bug. On the other two problems
  the cases failed on the final design in 3 of the 4 rows (PT's `binary_search_tree_algorithms_0001` passed them). They
  disagreed with luna's RTL, but luna did not fix it within the turns.
- **Cost.** Sonnet's share of spend is 62–74% in P, T and PT, at $0.010–0.057 per problem, far under the $0.50
  role budget.
- **Arm C as smoked is not usable yet.** kimi-k2.7-code at reasoning `default` was very slow: one edit ran past
  470 s, and 2 of 3 problems ended `llm_error` at the wall-cap deadline. A later C would need the coder at a low
  reasoning level, or a faster coder, and a budget set from its own smoke run.
- **Sonnet or Opus.** Nothing here shows that Sonnet's spec reading is clearly worse, so the default (Sonnet) stands.
  With 3 problems this is a check that the role works, not a measure of quality.
