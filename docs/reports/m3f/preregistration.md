# M3f: pre-registration

Written 2026-10-30, after the smoke runs and before any scored run was dispatched. The commit that adds this file is
the record of what was decided in advance. Any change to the agent, the prompts, the settings or the analysis after
the first scored dispatch voids the runs made before it, and is stated in the report.

## Why

- Three process changes on `openai/gpt-6-luna` were null: M3b's lessons memory, M3c's checks, and M3d's
  verify-before-submit and blind spec cases. In M3d, forcing luna to test moved its failures to "own testbench passed,
  hidden tests failed". Where all of luna's blind spec cases passed, the hidden tests passed 61% of the time; where
  some failed, 57%. A testbench from the same model carries the same reading of the spec.
- M3e: the same LangGraph agent with Opus 5.5 scored +13.4 points [+4.0, +22.4] over luna, and the harness effect
  (Claude Code against LangGraph, both Opus) was −4.5, null. The gap is the model.

M3f asks **which part of the model's job carries the gap**: reading the spec and planning, or writing the spec cases
the design is checked against. In both new arms luna still writes and fixes the RTL.

## The code (fixed now)

Per-role model overrides, all blank by default (`agent/cvdp_agent/config.py`):

| Setting | Sweep input | Used by |
|---|---|---|
| `CVDP_PLAN_MODEL` | `plan_model` | the `plan` call |
| `CVDP_SPEC_MODEL` | `spec_model` | M3d's blind `spec` call (needs `spec_vectors`) |
| `CVDP_ROLE_REASONING` | `role_reasoning` | the reasoning level of those calls (blank = `reasoning`) |
| `CVDP_ROLE_BUDGET_USD` | `role_budget_usd` | their own per-problem budget, kept apart from `budget_usd` |

- `CVDP_MODEL` stays the edit-and-fix model (`edit`, `reflect`).
- `read_task` makes no LLM call: it reads `prompt.json` and lists the files. The model that "reads the spec" is the
  one that writes the plan. Its prompt holds the task, the file listing and the files under `rtl/`, `docs/` and
  `verif/`, as today. So the brief's `CVDP_SPEC_MODEL` for `read_task` and `CVDP_TESTER_MODEL` became two settings:
  `plan_model` for the reader and `spec_model` for the tester.
- The spec call sees exactly what M3d's S step saw: the task, `docs/` and the port table of the given RTL. Never an
  RTL body, never `verif/`, and nothing the agent wrote. Nothing sees the hidden tests or their logs.
- A role model gets its own client. OpenRouter routes it freely: `provider_order` is not applied to it. A refusal of
  its `reasoning` field drops only the roles to `default`.
- Budgets: the edit loop keeps M3d's $0.10 per problem on its own spend, so a strong model's plan does not eat luna's
  budget. Role calls have their own $0.50 per problem; the largest smoke role cost was $0.029.
- Records: each `llm` trace event names the model that served it, and the start event's switches name the roles.
  `summary.json` gains `role_models`, `role_reasoning_used`, `role_calls`, `role_cost_usd`, `main_cost_usd` and
  `cost_by_model`, and the CSV gains `plan_model`, `spec_model`, `role_reasoning_used`, `role_calls`,
  `role_cost_usd`, `main_cost_usd` and `cost_by_model`. All of them appear only when a role model is set.
- **Default arm unchanged:** with every role setting blank, the prompts, the trace and the summary are byte-for-byte
  the golden ones (`tests/test_m3f.py::test_langgraph_golden_unchanged_with_the_role_settings_explicitly_blank`,
  as in M3b, M3c and M3d), and the sweep passes no role variable to the agent.

## The strong model

`anthropic/claude-sonnet-5.5`, at `role_reasoning=low`, the level M3e ran the Claude models at. It was chosen over
Opus 5.5 because it is cheaper ($2/$10 per million tokens against $4/$20). The smoke runs gave no sign that its
spec reading is clearly worse. Its plans named the right ports, parameters and state changes on all 3 problems, and
on `lfsr_0005` it worked the given table through to the tap error. So the default stands, as the brief says. With 3
problems, that is a check that the role works, not a measure of quality.

## Arms (scored)

The cheapest design that answers "P or T": two new arms, 2 runs each.

| Arm | plan | spec cases | edit, reflect | Source |
|---|---|---|---|---|
| A (base) | luna | off | luna | M3d's fresh arm A, `m3d/runs/A*.csv`, 3 runs, from 2026-10-26 |
| **P** | Sonnet 5.5 | off | luna | new, 2 runs (seeds 1, 2) |
| **T** | luna | Sonnet 5.5, M3d's S machinery (`spec_vectors=true`) | luna | new, 2 runs (seeds 1, 2) |
| S (secondary base for T) | luna | luna, M3d's S machinery | luna | M3d's arm S, `m3d/runs/S*.csv`, 3 runs |

**Settings:** M3c arm A's, as in M3d. LangGraph harness; `openai/gpt-6-luna` at reasoning `default`;
`ubuntu-24.04-arm`; 4 threads; $0.10 per problem for the edit loop; 10 turns; self-check and lint on; 480 s wall cap;
no lessons memory; M3c's switches off; the 86 problems in `tools/m3b_eval_ids.txt`. Role settings:
`role_reasoning=low`, `role_budget_usd=0.50`.

**Dispatch.** All 4 sweeps come from one commit of `m3f-split-roles` (the one that adds this file, or a later one
that changes only `docs/`), on the same day, at most 2 in flight. Example:

```
ids=$(grep -v '^#' tools/m3b_eval_ids.txt | paste -sd,)
common="-f model=openai/gpt-6-luna -f split=agentic -f runner=ubuntu-24.04-arm -f threads=4 -f reasoning=default \
  -f budget_usd=0.10 -f harness=langgraph -f role_reasoning=low -f role_budget_usd=0.50 -f seeds=1 -f ids=$ids"
# P, seeds 1 and 2
gh workflow run sweep.yml --ref m3f-split-roles $common -f plan_model=anthropic/claude-sonnet-5.5 \
  -f run_budget_usd=7.00 -f seed_offset=<0|1>
# T, seeds 1 and 2
gh workflow run sweep.yml --ref m3f-split-roles $common -f spec_vectors=true -f spec_model=anthropic/claude-sonnet-5.5 \
  -f run_budget_usd=9.00 -f seed_offset=<0|1>
```

**Possible later arms (not part of this design, not scored here):**

- **PT**: Sonnet for both the plan and the spec cases, luna for the edit loop. Smoked once (below).
- **C**: Sonnet plans, and a code-specialised model does the edit/fix role (`model=` the coder). The candidate,
  pinned from OpenRouter's model list on 2026-10-30, is `moonshotai/kimi-k2.7-code` ($0.60/$3.50 per million).
  Smoked once (below). The list also serves `mistralai/devstral-2512`, `bytedance-seed/seed-2.0-code`,
  `qwen/qwen3-coder-next` and `openai/gpt-5.3-codex`.
- **Q** (open-weights general model plus open-weights coder) was dropped: the owner meant specialised models per
  role, not Qwen in particular. No spend went to it.
- **A third run of P and T** (seed 3), if the owner wants the 3 × 3 design.

Each later arm would get its own pre-registration addendum before it is dispatched.

## Comparisons

**Primary**, each paired on the 86 problems with `tools/ablate.py --base A --ids tools/m3b_eval_ids.txt`. Each uses
the paired bootstrap over problems and the exact two-sided sign test, as in M3d:

1. **P − A**
2. **T − A**

**Holm at α = 0.05 overall** across the two. Order them by their sign-test p. The first must have its 97.5% interval
(`--level 0.975`) exclude zero. Only if it does, the second must have its 95% interval exclude zero. A comparison
that passes is **better** or **worse** by its sign. Every other result is **no detectable effect**: report the
interval, and the effect size it rules out.

**Secondary** (descriptive, 95% intervals, no test):

- **T − S**: the tester's model, with the machinery held fixed (`--base S`).
- **P − T**: which role matters more, paired directly.
- P and T against M3e's LG+Opus on its 67 attempted problems (`--ids docs/reports/m3e/attempted_ids.txt`), labelled
  partial.
- The 79-problem view (`--exclude tools/benchmark_limited_ids.txt`) beside every 86-problem number, never in its
  place.
- The failure taxonomy per arm (`tools/taxonomy.py`), especially the share of `tests_failed_selfcheck_passed` ("own
  testbench passed, hidden tests failed").
- For T against S: spec-case outcome against hidden-test pass (M3d's 2×2), and how often the spec step failed open.
- $/solved and $/problem per arm, provider-reported, and the share of each arm's spend that went to Sonnet
  (`role_cost_usd / cost_usd`).
- Turns, LLM calls and self-check runs per problem-run; stops on `budget`, `wall_time` and `max_turns`.

## Decision rule, in words

- If **P or T is better** than A, and that arm costs much less per problem than an all-strong agent, **the split
  works** for that role. "Much less" means under half of M3e's LG+Opus at $0.255 per problem: under $0.13.
- If **P and T are both no detectable effect**, the gain from a strong model needs it in the edit loop too, or is
  smaller than this design can see (below).
- If exactly one is better, that role carries a detectable part of the gap. P − T then says whether the two roles
  differ.
- **T − S** is read by itself. If it is positive while T − A is null, Sonnet's spec cases are better than luna's, but
  M3d's machinery still costs about what they gain.

## Power, stated in advance

On M3d's data at 97.5%, the paired half-width was 4.9 points for 2 V runs against 3 A runs, and 7.0 points for 2 S
runs against 3 A runs (6.4 with 3 S runs). So with 2 runs per new arm, against A's 3:

- a true effect of about **+9 to +10 points** has roughly an 80% chance of being detected (T's machinery is the
  noisier one);
- **+5 points** has about a 30% chance;
- an effect of 3 points or less will very likely read as no detectable effect.

M3e's model gap was +13.4 points. A role that carries most of it would be detected; one that carries a third of it
would not. A third run per arm would cut the half-widths by about 10%.

## Spend

- The key: $83.53 left of a $159 limit at the start of this brief (key check run 41095872516). The owner has said
  $150 is the project's ceiling and prefers to spend less. A second session finishing M3e shares the key, at about $5.
- Smoke spend (4 runs, below): $0.594 provider-reported, plus 3 calls whose cost was not reported (abandoned at
  the wall-cap deadline; under about $0.10 together). The key had $78.71 left after them (key check 41098410322;
  the M3e session spent from it at the same time).
- **Expected cost of this design.** The smoke problems' prompts are about 0.67× the size of the average problem's
  (luna's tokens per call on M3d arm A), so the role cost is scaled up by 1.5. It is then raised by another 1.5,
  because M3e's estimate came in 50% low. Luna's own cost is M3d's measured cost.

| Arm | Sonnet per problem (smoke → estimate) | Luna per run | Per run | Runs | Arm total | Guard per sweep |
|---|---|---|---|---|---|---|
| P | $0.016 → $0.037 | $0.59 (A) | about $3.8 | 2 | about $7.6 | $7.00 |
| T | $0.021 → $0.047 | $1.13 (S) | about $5.2 | 2 | about $10.4 | $9.00 |
| **This design** | | | | **4** | **about $18** | at most $32 |

- Guards: each sweep's `run_budget_usd` is set to the expected cost × 1.5, plus 4 threads × the $0.10 that the
  guard charges a call still in flight, rounded up. If a guard still refuses problems, the problems it refused are
  listed and left out of that arm's comparisons, as in M3e. The full-86 numbers that count them as failures are shown
  beside.
- **For comparison, the full 3 × 3 design** (P, T and PT, 3 runs each): P about $11.4, T about $15.6, and PT about
  $25 (T's cost plus a Sonnet plan, about $8.4 per run). About **$52** in all, with guards up to about $90.
- **Stop:** before each dispatch, its guard plus the M3f spend so far must stay under **$35**, and the key must stay
  above $3. If not, the sweep is not dispatched, and the report says which runs are missing.
- The planner dispatches after the owner says go.

## Smoke runs (not scored, before this file)

The same 3 problems for every run, from brief 09's part two, which M3d and M3e also smoked: `queue_0001`,
`lfsr_0005` and `binary_search_tree_algorithms_0001`. Luna's arm A never solved any of them (0 of 9 in M3d), and
neither did arm S. Scored settings, except 3 threads and a $1.00–1.50 guard. Details in [`smoke.md`](smoke.md).

| Run | Arm | Passed | Reported spend | Sonnet's share | Notes |
|---|---|---|---|---|---|
| 41095968060 | P | 0 / 3 | $0.0663 | $0.0490 (74%) | 1 Sonnet call per problem (the plan); luna then submitted without a testbench on all 3 |
| 41095985036 | T | 0 / 3 | $0.1021 | $0.0636 (62%) | Sonnet wrote 2, 1 and 7 cases; on `lfsr_0005` they all passed and the hidden tests failed |
| 41096941362 | PT | 0 / 3 | $0.1674 (1 unreported) | $0.1127 (67%) | 2 Sonnet calls per problem; one luna edit abandoned at the wall-cap deadline |
| 41096957348 | C | 0 / 3 | $0.2583 (2 unreported) | $0.0479 (19%) | `moonshotai/kimi-k2.7-code` as the edit model, reasoning `default`, $0.30 budget: very slow (one edit ran past 470 s), 2 of 3 ended `llm_error` |

- Every role call went to Sonnet ("Claude Platform on AWS"), and every edit and reflect call to the edit model.
  `role_models`, `role_cost_usd` and `cost_by_model` were filled on every row.
- No role call was refused for its `reasoning` field. Sonnet reported 0 reasoning tokens on all 15 of its calls at
  `low`.
- The largest role cost on one problem was $0.057 (PT, two calls), far under the $0.50 role budget. No row stopped
  on `budget`.
- Arm C as smoked is not a fair arm yet. A later C would need the coder at a low reasoning level (or a faster
  coder), and its own budget, fixed in its own addendum.

## Caveats stated in advance

- **The base is from another day.** A and S ran on 2026-10-26, from `c96f058`. P and T run later, from this branch.
  With every role setting blank the agent is byte-identical, but the agent image is rebuilt from new code, and
  OpenRouter's routing for luna may differ. The new arms differ from A only in their role models.
- **P's planner reaches luna only through the plan JSON**: `files_to_change`, `approach` and `check_plan`. Luna still
  reads the task and the files itself on every edit. P measures a better plan handed to luna. It does not replace
  luna as the reader.
- **T includes M3d's verify step**, which on luna cost about 4.7 points (S − A, null). T − A is the whole package;
  T − S isolates the tester's model.
- Sonnet at `low` reasoning often reports 0 reasoning tokens on these short calls (as in M3e's smoke). `low` is a
  ceiling, not a minimum.
- The throughput clamp on `max_tokens`, which only bites when time is short, pools tokens per second across the
  models in a problem.
- 2 runs per arm, so run-to-run spread (about ±3 points between identical sweeps of A) is only partly averaged out.
