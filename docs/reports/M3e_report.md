# M3e report: harness or model? The LangGraph agent with Claude

**Status: exploratory, partly run (2026-10-30).** Pre-registered in [`m3e/preregistration.md`](m3e/preregistration.md),
committed (`a152c14`) before the one scored dispatch. One of the two planned new arms ran: **LangGraph + Opus 5.5**
(run 41040802008, from `a152c14`, success). Its whole-run guard, capped by the brief's $20 hard stop, refused the
last **19 of the 86 problems**, so the comparisons below are on the **67 problems it attempted**, as the
pre-registration says. **LangGraph + Sonnet 5.5 was not run**: after Opus, $0.76 of the $20 was left, and a Sonnet
run needs about $10. Nothing was changed after the scored dispatch. The rules from the M1 report still apply: the LLM
never produces a score or a label, every cost is provider-reported, and a missing cost is recorded as unreported.

The tables are made from the run CSVs by the committed tools (`ablate.py`, `taxonomy.py`, `m3d_tables.py`), nothing
by hand. Harness `8e894cf`, dataset revision `5b807d9`, agent image from `29a6ec8` (the image M3d ran).

## In short

On the 67 problems all arms attempted:

- **The model matters, at our harness.** Our unchanged LangGraph agent with Opus 5.5 scores **77.6%** against luna's
  64.2%: **+13.4 points [+4.0, +22.4]** (19 better, 3 worse, 45 same; sign test p = 0.0009). It is the largest
  effect this project has measured on its own agent.
- **The harness does not, at a fixed model.** Claude Code with Opus scores 73.1% on the same problems:
  **CC+Opus − LG+Opus = −4.5 points [−13.4, +4.5]** (3 better, 6 worse, 58 same, p = 0.51). No detectable effect;
  the interval rules out a Claude Code advantage of more than about 4.5 points here.
- **The decomposition.** Claude Code + Opus's lead over LangGraph + luna on these 67 problems, **+9.0 [−1.0, +18.9]**,
  is **+13.4 model and −4.5 harness**. All of the gap, and more, is the model.
- **With the 7 benchmark-limited problems left out** (63 problems): model +14.3 [+4.2, +23.8], harness
  −4.8 [−14.3, +4.8]. Same reading.
- **It costs.** LG+Opus spent $17.11 on 67 problems: **$0.255 per problem, $0.329 per solved problem**, against luna's
  ≥$0.0117 per solved problem (28× as much). The per-problem budget did not bind (0 budget stops).
- **The 67 are not a random sample.** The guard refused the alphabetical tail (`prbs_0001` to
  `universal_shift_reg_0003`). On that tail, Claude Code + Opus solved 14 of 19 and luna 28 of 57 (49%), so the tail
  is where Claude Code's lead over luna was largest. Counting the 19 refused problems as failures (full 86, shown
  only for completeness) gives LG+Opus 60.5%, which says nothing about the model: those rows have no LLM call.
- **Sonnet is missing**, so the Sonnet half of the decomposition is not measured. CC+Sonnet against this report's
  luna base is given for reference only.

## Setup

| Arm | Harness | Model | Runs | Source |
|---|---|---|---|---|
| LG+luna (base) | LangGraph, 10 turns | `openai/gpt-6-luna`, reasoning `default` | 3 | M3d arm A, [`m3d/runs/A*.csv`](m3d/runs/) (2026-10-26) |
| **LG+Opus** | LangGraph, 10 turns | `anthropic/claude-opus-5.5`, reasoning `low` | 1 | **new**, [`m3e/runs/LG_opus_41040802008.csv`](m3e/runs/LG_opus_41040802008.csv) |
| LG+Sonnet | LangGraph, 10 turns | `anthropic/claude-sonnet-5.5`, reasoning `low` | 0 | **not run** (spend) |
| CC+Opus | Claude Code, 60 turns | `claude-opus-5-5`, effort `low` | 1 | the ladder, [`claude_code/runs/`](claude_code/runs/) |
| CC+Sonnet | Claude Code, 60 turns | `claude-sonnet-5-5`, effort `low` | 1 | the ladder |

LG+Opus uses M3c arm A's harness settings unchanged: `ubuntu-24.04-arm`, 4 threads, 10 turns, self-check and lint on,
480 s wall cap, no memory, every M3c and M3d switch off, the 86 problems of `tools/m3b_eval_ids.txt`. What differs
from arm A is the model, reasoning `low`, and `budget_usd` = $1.00 (about 3× the smoke run's 90th-percentile cost per
problem, $0.327). The dispatch:

```
gh workflow run sweep.yml --ref m3e-harness-or-model -f model=anthropic/claude-opus-5.5 -f split=agentic \
  -f runner=ubuntu-24.04-arm -f threads=4 -f reasoning=low -f budget_usd=1.00 -f run_budget_usd=17.50 \
  -f seed_offset=0 -f seeds=1 -f harness=langgraph -f ids=$(grep -v '^#' tools/m3b_eval_ids.txt | paste -sd,)
```

**Reasoning.** `reasoning=low` sends OpenRouter `reasoning: {effort: "low", exclude: true}`. All 86 rows record
`reasoning_used = low`; no request was refused for its reasoning field; 65,046 reasoning tokens were reported over
the 67 attempted problems (17% of completion tokens). Every call was served by "Claude Platform on AWS".

**The guard.** The sweep's guard was $17.50, the most the hard stop allowed after $2.13 of smoke runs. The guard
stops new problems once reported spend plus `budget_usd` for each call in flight reaches it. Opus cost $0.255 per
attempted problem against the $0.17 the pre-registration expected from the smoke runs, so the guard was reached after
67 problems ($17.11 reported) and the last 19 problems in the harness's order were refused before any LLM call.
They are listed in [`m3e/guard_refused_ids.txt`](m3e/guard_refused_ids.txt) and left out of every comparison
([`m3e/attempted_ids.txt`](m3e/attempted_ids.txt)), as pre-registered.

## Results

`ablate.py --ids docs/reports/m3e/attempted_ids.txt`; full outputs in [`m3e/`](m3e/)
(`vs_luna_attempted67.md`, `harness_opus_attempted67.md`, and the `attempted63` and `full86_refused_as_fail`
views).

| Arm | Pooled pass@1, 67 problems [95%] |
|---|---|
| LG+luna (3 runs) | 129/201 = 64.2% [54.2, 74.1] |
| CC+Sonnet | 49/67 = 73.1% [62.7, 83.6] |
| CC+Opus | 49/67 = 73.1% [62.7, 83.6] |
| **LG+Opus** | **52/67 = 77.6% [67.2, 86.6]** |

| Comparison | 67 problems | 63 (benchmark-limited out) | Better / worse / same (67) | Sign p (67) |
|---|---|---|---|---|
| **Model:** LG+Opus − LG+luna | **+13.4 [+4.0, +22.4]** | +14.3 [+4.2, +23.8] | 19 / 3 / 45 | 0.0009 |
| Model: LG+Sonnet − LG+luna | not run | not run | | |
| **Harness:** CC+Opus − LG+Opus | **−4.5 [−13.4, +4.5]** | −4.8 [−14.3, +4.8] | 3 / 6 / 58 | 0.51 |
| Harness: CC+Sonnet − LG+Sonnet | not run | not run | | |
| Total: CC+Opus − LG+luna | +9.0 [−1.0, +18.9] | +9.5 [−1.1, +20.6] | 16 / 6 / 45 | 0.053 |
| Reference: CC+Sonnet − LG+luna | +9.0 [−1.5, +19.4] | +9.5 [−1.6, +20.6] | 17 / 6 / 44 | 0.035 |

For completeness, on the full 86 with the 19 refused problems counted as failures: LG+Opus − LG+luna −0.4
[−10.5, +9.7], CC+Opus − LG+Opus +12.8 [+2.3, +23.3], CC+Opus − LG+luna +12.4 [+3.1, +21.7]. These are not
measurements of the model: 19 of LG+Opus's 86 rows never called it.

## The decomposition

On the 67 attempted problems the paired effects add exactly:

| | Opus |
|---|---|
| Total, CC+Opus − LG+luna | +9.0 [−1.0, +18.9] |
| = model, LG+Opus − LG+luna | +13.4 [+4.0, +22.4] |
| + harness, CC+Opus − LG+Opus | −4.5 [−13.4, +4.5] |

79-problem view, in the pre-registration's sense (the attempted problems less the 7 benchmark-limited ones, 63):
total +9.5, model +14.3, harness −4.8.

Read with care: this is one run of each Opus arm on 67 problems, the base's own runs differ by about ±3 points, and
the harness interval is wide. What it rules out is that Claude Code's agent loop is what put the ladder's Opus arm
ahead. Our 10-turn graph with the same model did at least as well on these problems.

## How the agent works with Opus

From [`m3e/secondary_tables_attempted67.md`](m3e/secondary_tables_attempted67.md) and
[`m3e/taxonomy_by_arm_all_rows.md`](m3e/taxonomy_by_arm_all_rows.md) (67 attempted problems):

| Arm | Turns median / mean | 1-turn rows | LLM calls median / mean | Self-check runs median / mean | Rows with 0 self-check runs | Median wall |
|---|---|---|---|---|---|---|
| LG+luna | 2 / 2.75 | 41% | 5 / 6.46 | 1 / 1.34 | 49% | 84 s |
| LG+Opus | 1 / 2.15 | 51% | 3 / 5.30 | 1 / 1.99 | **0%** | 44 s |
| CC+Opus | 6 / 6.49 | 0% | 6 / 6.49 | not recorded | not recorded | 49 s |

- **Opus tests its own work without being made to.** Every LG+Opus problem-run ran the agent's own testbench at least
  once; luna skipped it on 49% of runs. M3c's gate and M3d's verify step forced luna to test and gained nothing; Opus
  tests by itself and its tests are better at catching what the hidden tests catch.
- **Failure mix (attempted rows).** LG+Opus failed 15 of 67: `tests_failed_selfcheck_passed` 11,
  `compile_fail_hidden` 3, `tests_failed_selfcheck_failed` 1. No `tests_failed_no_selfcheck`, no `llm_error`, no cap
  stops. (Its `stopped_by_cap` count of 19 in the taxonomy file is the guard-refused rows.) Claude Code's rows carry no
  self-check record, so their `tests_failed_no_selfcheck` label means "not recorded", not "did not test".
- **Stops.** 0 on `budget`, 0 on the wall cap (longest 408 s), 0 on the turn cap. The budget came closest on one
  problem at $0.94 of $1.00; 10 problems cost more than $0.50.

## Effort and cost

| Arm | Problems | Provider-reported cost | $/problem | $/solved | Tokens (prompt + completion) |
|---|---|---|---|---|---|
| LG+luna (3 runs, 67 problems) | 201 rows | ≥$1.51 (4 unreported) | ≥$0.0075 | ≥$0.0117 | 7.5 M |
| LG+Opus | 67 | $17.11 (0 unreported) | $0.255 | $0.329 | 2.73 M (2.34 M prompt, 0.39 M completion) |
| CC+Opus | 67 | plan, not provider-reported | | | 11.2 M |

Claude Code's plan cost estimate (the ladder: $24.86 for 86 problems, $0.289 per problem) is kept apart: it is not a
provider-reported cost. LG+Opus uses about a quarter of Claude Code's tokens per problem.
Pareto chart: [`m3e/pareto.svg`](m3e/pareto.svg), [`m3e/pareto.csv`](m3e/pareto.csv) (LangGraph arms, 67 problems).
LG+Opus is the higher-pass, far-higher-cost point; luna's cost is a lower bound.

**Spend for this brief: $19.24** (smoke runs $2.13: 41039492587, 41039501474, 41040074667, 41040083804; scored run
$17.11). The key's usage moved by the same amount (key checks 41039346705, 41040768261, 41044292403); $5.60 of its $80
limit is left.

## Caveats

- **One run per arm, exploratory.** No confirmatory claim. The base's identical runs range 62.7–67.2% on these 67
  problems.
- **67 of 86 problems, not chosen at random.** The refused 19 are the alphabetical tail, where Claude Code + Opus's lead
  over luna was largest (74% against 49%). The harness effect on all 86 could be less negative than −4.5.
- **Sonnet is not run.** The Sonnet half of the decomposition is missing.
- **The ladder ran on 2026-10-25/26, this arm on 2026-10-30.** Same simulation and agent images; the providers differ
  (Claude Code on the plan, against OpenRouter routing to Anthropic on AWS).
- **Claude Code's turn budget is 60, ours 10.** The wall cap is the same (480 s). The harness effect includes that.
- **The base ran luna at reasoning `default`, the Claude arms at `low`.** The model effect includes the reasoning label.
- **The pre-registration's cost estimate was low** ($0.17 per problem expected, $0.255 seen): the smoke problems were
  not as much harder than average for Opus as they were for luna.

## Data

[`m3e/`](m3e/): `runs/LG_opus_41040802008.csv`; `smoke/` (the 4 smoke CSVs); `attempted_ids.txt`,
`guard_refused_ids.txt`, `guard_refused_and_benchmark_limited_ids.txt`; the `ablate.py` outputs `vs_luna_*.md` and
`harness_opus_*.md`; `taxonomy_by_arm_all_rows.md`; `secondary_tables_attempted67.md`; `pareto.csv`, `pareto.svg`;
`analyze.sh`, the commands that made them.
