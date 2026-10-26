# Claude Code as the agent: a model ladder on the 86 evaluation problems

**Status: done (2026-10-26). Exploratory, not pre-registered.** This report swaps both the harness and the model.
The agent is Claude Code (`claude -p`, CLI 2.1.310) running headless inside the harness's container, on the owner's
Max plan, in place of our LangGraph agent on OpenRouter. It runs four Claude models, one run each, on M3b's 86
evaluation problems (`tools/m3b_eval_ids.txt`). The base for comparison is M3c's arm A: our LangGraph agent with
`openai/gpt-6-luna`, 3 runs, from the same day's image. The rules from the M1 report still apply. The LLM never
produces a score or a label, and the hidden tests are CVDP's.

## In short

- **Only Opus 5.5 is clearly above our agent.** It gains **+11.6 points [+1.9, +21.3]** (25 better, 9 worse,
  52 same; sign test p = 0.009).
- **Sonnet 5.5 is borderline:** +8.1 [−0.4, +17.4], p = 0.03.
- **Haiku 5.5 (+4.7) and Fable 5.1 (+5.8) show no detectable effect.** Both intervals include 0.
- **The ladder is not in order of model size.** Opus scores 73.3%, Sonnet 69.8%, Fable 67.4% and Haiku 66.3%.
- **Fable is held back by the wall cap.** It stopped on the 480 s cap on 17 of 86 problems, and 10 of those failed.
  Its median wall time is 265 s, against 24–83 s for the others. Under this cap, Fable's score is a lower bound
  on what it can do, not a measure of it.
- **Every Claude arm is one run.** The base's own runs differ by about ±3 points between identical sweeps
  (65.1, 59.3, 60.5), so a one-run arm carries that noise on top of the interval shown.
- **The comparison mixes two changes.** Each arm differs from the base in both the model and the harness. It says
  how good Claude Code on the plan is at these problems, not which of the two changes is responsible.

## Setup

| | Claude Code arms | Base (M3c arm A) |
|---|---|---|
| Agent | `claude -p --output-format stream-json --max-turns 60 --permission-mode acceptEdits` | LangGraph graph, 10 turns |
| Tools | Read, Edit, Write, Glob, Grep, Bash; no web, no `git`/`pip`/`curl` and similar (denied) | the M2 tools |
| Model | `claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5`, `claude-fable-5-1` | `openai/gpt-6-luna`, reasoning default |
| Billing | the owner's Max plan (`CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`) | OpenRouter, provider-reported |
| Wall cap | 480 s per problem | 480 s |
| Runs | 1 per model | 3 |

The harness is `claudecode` (`agent/cvdp_agent/claude_code.py`), dispatched with `-f harness=claudecode` from this
branch. It records `cost_usd` as unreported, because the plan has no per-call price. Claude Code's own
API-equivalent estimate is kept apart in `plan_cost_estimate_usd` in each problem's `summary.json`.

**Reruns.** Plan limits cut some sweeps short, in two ways: running four models at 4 threads each hit the 5-hour
session limit, and Fable later hit the weekly limit. A problem cut off this way ends with `llm_error` and no answer
from the model. Such problems were rerun with fewer threads until each of the 86 had one valid attempt. Only
`llm_error` and `error` rows were rerun, never a failure. Invalid rows dropped: Haiku 85, Sonnet 0, Opus 39,
Fable 183. The per-model CSVs in [`claude_code/runs/`](claude_code/runs/) hold the one valid row per problem.

## Results

`ablate.py --base luna --ids tools/m3b_eval_ids.txt` against M3c's three arm-A CSVs
(`docs/reports/m3c/runs/A*.csv`); full output in [`claude_code/ladder_paired_eval86.md`](claude_code/ladder_paired_eval86.md).

| Arm | pass@1 | Effect vs base [95%] | Better / worse / same | Sign test p |
|---|---|---|---|---|
| base: LangGraph + gpt-6-luna (3 runs) | 159/258 = 61.6% | | | |
| Claude Code + Haiku 5.5 | 57/86 = 66.3% | +4.7 [−2.3, +11.2] | 17 / 8 / 61 | 0.108 |
| Claude Code + Fable 5.1 | 58/86 = 67.4% | +5.8 [−1.2, +12.8] | 17 / 8 / 61 | 0.108 |
| Claude Code + Sonnet 5.5 | 60/86 = 69.8% | +8.1 [−0.4, +17.4] | 22 / 9 / 55 | 0.029 |
| Claude Code + Opus 5.5 | 63/86 = 73.3% | +11.6 [+1.9, +21.3] | 25 / 9 / 52 | 0.009 |

By difficulty (solved / problems):

| Difficulty | Haiku | Sonnet | Opus | Fable |
|---|---|---|---|---|
| easy (16) | 14 | 13 | 14 | 12 |
| medium (52) | 35 | 37 | 39 | 38 |
| hard (18) | 8 | 10 | 10 | 8 |

At least one Claude model solved 74 of the 86 problems, and all four solved 45 of them.

## Effort and cost

The plan cost estimate is what Claude Code reports the session would have cost at API prices. Nothing was paid per
call. It is a guide to how much of the plan a sweep uses, not a provider-reported cost, and it is not comparable
with the base's OpenRouter dollars.

| Arm | Median turns | Median wall s | Stopped on wall cap | Tokens (prompt + completion) | Plan cost estimate, total ($/problem) |
|---|---|---|---|---|---|
| Haiku 5.5 | 11 | 83 | 0 | 39.2 M | $1.98 ($0.023) |
| Sonnet 5.5 | 4 | 24 | 1 | 9.3 M | $8.39 ($0.098) |
| Opus 5.5 | 6 | 50 | 0 | 14.1 M | $24.86 ($0.289) |
| Fable 5.1 | 15 | 265 | 17 | 38.2 M | $109.39 ($1.272) |
| base (gpt-6-luna) | 1 | 51 | 3 runs: 5 | 7.7 M over 3 runs | provider-reported ≥$1.58 for 3 runs (≥$0.0061) |

Plan usage, from `claude -p "/usage"` logged every 5 minutes while the sweeps ran:

- **The 5-hour session limit is what stops parallel sweeps.** Four models at 4 threads each used about 63% of the
  session limit in 10 minutes.
- **The weekly limit decides how much fits in a week.** The Opus, Sonnet and Haiku sweeps and most of Fable's used
  about 25 points of the all-models weekly limit, from 75% to 100%.
- **Fable is metered separately,** in its own weekly bucket. Its 86 problems used about 64 points of that bucket,
  over two weeks.

## Caveats

- **One run per model, and not pre-registered.** Read the effects against the base's own run-to-run spread of
  about ±3 points.
- **Model and harness both change.** The LangGraph agent with a Claude model was not run, because this account has
  no Anthropic API key.
- **Claude Code's turn budget is 6× ours** (60 against 10). The wall cap is the same.
- **Fable is cap-limited.** A run with a longer wall cap would measure it better.
- **The plan is not a stable meter.** Limits and model routing on a subscription can change without notice, so a
  rerun next month may not be the same experiment.
