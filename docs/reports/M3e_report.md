# M3e report: harness or model? The LangGraph agent with Claude

**Status: exploratory; LangGraph + Opus complete on all 86 problems, LangGraph + Sonnet not run (spend)
(2026-10-30).** Pre-registered in [`m3e/preregistration.md`](m3e/preregistration.md), committed (`a152c14`) before the
first scored dispatch. **LangGraph + Opus 5.5** is one 86-problem arm put together from **three dispatches on
2026-10-30**: run 41040802008 (from `a152c14`; its whole-run guard refused the last 19 problems), then, with the agent
code unchanged (`git diff a152c14 main -- agent/ tools/sweep.sh .github/workflows/sweep.yml` is empty), run
41095517652 on those 19 (its own guard, set too tight, refused the last 6 again) and run 41097171384 on the 6. Each
problem appears once, from the dispatch that attempted it; no problem was run twice. Brief 14 ran the first, brief 14b
the other two. **LangGraph + Sonnet 5.5 was not run**, to keep within the owner's spend ceiling; its expected cost is
given under [Effort and cost](#effort-and-cost). Nothing was changed after a scored dispatch. The rules from the M1
report still apply: the LLM never produces a score or a label, every cost is provider-reported, and a missing cost is
recorded as unreported.

The tables are made from the run CSVs by the committed tools (`ablate.py`, `taxonomy.py`, `m3d_tables.py`, run by
[`m3e/analyze.sh`](m3e/analyze.sh)), nothing by hand. Harness `8e894cf`, dataset revision `5b807d9`, agent image from
`29a6ec8` (the image M3d ran). The first dispatch's 67-problem results are kept below as they were reported, beside the
full ones.

## In short

On all 86 problems (the LG+Opus arm merged from three dispatches; see Status):

- **The model matters, at our harness.** Our unchanged LangGraph agent with Opus 5.5 scores **72.1%** (62/86) against
  luna's 60.9%: **LG+Opus − LG+luna = +11.2 points [+2.7, +20.2]** (24 better, 6 worse, 56 same; sign test
  p = 0.0014). It is still the largest effect this project has measured on its own agent.
- **The harness does not, at a fixed model.** Claude Code with Opus scores 73.3%: **CC+Opus − LG+Opus = +1.2 points
  [−7.0, +9.3]** (7 better, 6 worse, 73 same, p = 1). No detectable effect; the interval rules out a Claude Code
  advantage of more than about 9 points.
- **The decomposition.** Claude Code + Opus's lead over LangGraph + luna, **+12.4 [+3.1, +21.7]**, is **+11.2 model
  and +1.2 harness**. Nearly all of the gap is the model.
- **The 79-problem view** (the 7 benchmark-limited problems left out): model +12.2 [+3.4, +21.5], harness
  +1.3 [−7.6, +10.1], total +13.5 [+3.4, +23.2]. Same reading.
- **The 19 problems finished later were the hard tail.** LG+Opus solved 10 of them, Claude Code + Opus 14, which is
  why the harness effect moved from −4.5 on the first 67 to +1.2 on all 86. The first report's caveat (the effect "on
  all 86 could be less negative") was right; the reading did not change.
- **It costs.** LG+Opus spent $22.25 on 86 problems: **$0.259 per problem, $0.359 per solved problem**, against luna's
  ≥$0.0112 per solved problem (32× as much). The per-problem budget did not bind (0 budget stops).
- **Sonnet was not run** (spend), so the Sonnet half of the decomposition is not measured. CC+Sonnet against luna is
  given for reference only: +8.9 [+0.8, +18.2].

### On the 67 problems of the first dispatch (as first reported)

These are kept as they were reported; they are superseded by the full-86 results above, not replaced.

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
| **LG+Opus** | LangGraph, 10 turns | `anthropic/claude-opus-5.5`, reasoning `low` | 1 (three dispatches) | **new**, [`m3e/full86/`](m3e/full86/) (merged); the first dispatch alone: [`m3e/runs/LG_opus_41040802008.csv`](m3e/runs/LG_opus_41040802008.csv) |
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

**Finishing the arm (brief 14b).** The two later dispatches used the same inputs as the first, from branch
`m3e-finish` (`54caebb`, the same agent code and agent image), with `ids` set to the problems still missing:

```
gh workflow run sweep.yml --ref m3e-finish -f model=anthropic/claude-opus-5.5 -f split=agentic \
  -f runner=ubuntu-24.04-arm -f threads=4 -f reasoning=low -f budget_usd=1.00 -f run_budget_usd=6.00 \
  -f seed_offset=0 -f seeds=1 -f harness=langgraph -f ids=$(grep -v '^#' docs/reports/m3e/guard_refused_ids.txt | paste -sd,)
# run 41095517652: 13 attempted ($4.21), the last 6 refused by its guard; then, on those 6, run_budget_usd=5.50:
# run 41097171384: 6 attempted ($0.93), none refused
```

The first finishing guard ($6.00) was too tight: the guard charges every call in flight at `budget_usd`, so with 4
threads it stops new problems once reported spend reaches about $2 below it. It tripped at $4.21 reported. The merged
CSV takes each problem's row from the dispatch that attempted it (67 + 13 + 6 = 86); it has no `run_budget_exhausted`
row. The raw CSVs of the two finishing runs are in [`m3e/finish/`](m3e/finish/).

**Reasoning.** `reasoning=low` sends OpenRouter `reasoning: {effort: "low", exclude: true}`. All 86 rows of the
merged arm record `reasoning_used = low`; no request was refused for its reasoning field; 89,576 reasoning tokens were
reported over the 86 problems (17% of completion tokens; 65,046 over the first 67). Every call was served by "Claude
Platform on AWS".

**The first dispatch's guard.** The sweep's guard was $17.50, the most the hard stop allowed after $2.13 of smoke runs. The guard
stops new problems once reported spend plus `budget_usd` for each call in flight reaches it. Opus cost $0.255 per
attempted problem against the $0.17 the pre-registration expected from the smoke runs, so the guard was reached after
67 problems ($17.11 reported) and the last 19 problems in the harness's order were refused before any LLM call.
They are listed in [`m3e/guard_refused_ids.txt`](m3e/guard_refused_ids.txt) and left out of every 67-problem comparison
([`m3e/attempted_ids.txt`](m3e/attempted_ids.txt)), as pre-registered. Brief 14b then ran them (above).

## Results

### All 86 problems (the merged LG+Opus arm)

`ablate.py --ids tools/m3b_eval_ids.txt`, and with `--exclude tools/benchmark_limited_ids.txt` for the 79; full
outputs in [`m3e/`](m3e/) (`vs_luna_eval86.md`, `harness_opus_eval86.md`, `vs_luna_eval79.md`,
`harness_opus_eval79.md`).

| Arm | Pooled pass@1, 86 problems [95%] |
|---|---|
| LG+luna (3 runs) | 157/258 = 60.9% [51.9, 69.8] |
| CC+Sonnet | 60/86 = 69.8% [59.3, 79.1] |
| **LG+Opus** | **62/86 = 72.1% [62.8, 81.4]** |
| CC+Opus | 63/86 = 73.3% [64.0, 82.6] |

| Comparison | 86 problems | 79 (benchmark-limited out) | Better / worse / same (86) | Sign p (86) |
|---|---|---|---|---|
| **Model:** LG+Opus − LG+luna | **+11.2 [+2.7, +20.2]** | +12.2 [+3.4, +21.5] | 24 / 6 / 56 | 0.0014 |
| Model: LG+Sonnet − LG+luna | not run (spend) | not run (spend) | | |
| **Harness:** CC+Opus − LG+Opus | **+1.2 [−7.0, +9.3]** | +1.3 [−7.6, +10.1] | 7 / 6 / 73 | 1 |
| Harness: CC+Sonnet − LG+Sonnet | not run (spend) | not run (spend) | | |
| Total: CC+Opus − LG+luna | +12.4 [+3.1, +21.7] | +13.5 [+3.4, +23.2] | 25 / 8 / 53 | 0.0046 |
| Reference: CC+Sonnet − LG+luna | +8.9 [+0.8, +18.2] | +9.7 [+0.4, +18.6] | 23 / 7 / 56 | 0.0052 |

On the 19 problems finished by brief 14b, LG+Opus solved 10 and Claude Code + Opus 14 (4 problems Claude Code won,
none the other way: `sigma_delta_audio_0001`, `sorter_0009`, `spi_complex_mult_0002`, `ttc_lite_0001`).

### The first dispatch's 67 problems (as first reported)

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
measurements of the model: 19 of LG+Opus's 86 rows never called it. The merged arm above replaces this view.

## The decomposition

On all 86 problems, and on the 79 without the benchmark-limited problems, the paired effects add exactly:

| | Opus, 86 | Opus, 79 | Sonnet |
|---|---|---|---|
| Total, CC − LG+luna | +12.4 [+3.1, +21.7] | +13.5 [+3.4, +23.2] | CC+Sonnet − LG+luna +8.9 [+0.8, +18.2] |
| = model, LG+model − LG+luna | +11.2 [+2.7, +20.2] | +12.2 [+3.4, +21.5] | not run (spend) |
| + harness, CC − LG+model | +1.2 [−7.0, +9.3] | +1.3 [−7.6, +10.1] | not run (spend) |

**Opus:** of Claude Code + Opus's +12.4-point lead over our luna agent, +11.2 is the model and +1.2 (no detectable
effect) the harness. **Sonnet:** not decomposed; LangGraph + Sonnet was not run, so only the total (+8.9) is known.

### On the first dispatch's 67 problems (as first reported)

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

From [`m3e/secondary_tables_eval86.md`](m3e/secondary_tables_eval86.md) and
[`m3e/taxonomy_by_arm_eval86.md`](m3e/taxonomy_by_arm_eval86.md) (all 86 problems, merged arm):

| Arm | Turns median / mean | 1-turn rows | LLM calls median / mean | Self-check runs median / mean | Rows with 0 self-check runs | Median wall |
|---|---|---|---|---|---|---|
| LG+luna | 2 / 2.55 | 47% | 5 / 6.08 | 0 / 1.19 | 55% | 74 s |
| LG+Opus | 2 / 2.30 | 47% | 5 / 5.60 | 1 / 2.06 | **0%** | 46 s |
| CC+Opus | 6 / 6.43 | 0% | 6 / 6.43 | not recorded | not recorded | 50 s |

- **Opus tests its own work without being made to**, on all 86 as on the 67: every LG+Opus problem-run ran the agent's
  own testbench at least once; luna skipped it on 55% of runs.
- **Failure mix.** LG+Opus failed 24 of 86: `tests_failed_selfcheck_passed` 17, `compile_fail_hidden` 4,
  `signal_missing_hidden` 1, `tests_failed_selfcheck_failed` 1, `gave_up` 1. No `tests_failed_no_selfcheck`, no
  `llm_error`, no cap stops. Claude Code's rows carry no self-check record, so their `tests_failed_no_selfcheck` label
  means "not recorded", not "did not test".
- **Stops.** 85 `submit`, 1 `give_up`; 0 on `budget`, 0 on the wall cap (longest 408 s), 0 on the turn cap. The budget
  came closest on one problem at $0.94 of $1.00; 12 problems cost more than $0.50.

### On the first dispatch's 67 problems (as first reported)

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
| LG+luna (3 runs, 86 problems) | 258 rows | ≥$1.76 (4 unreported) | ≥$0.0068 | ≥$0.0112 | 8.6 M |
| LG+Opus (merged) | 86 | $22.25 (0 unreported) | $0.259 | $0.359 | 3.52 M (3.00 M prompt, 0.51 M completion) |
| CC+Opus | 86 | plan, not provider-reported | | | 14.1 M |

LG+Opus costs 32× luna per solved problem and uses about a quarter of Claude Code's tokens per problem. Claude Code's
plan cost estimate (the ladder: $24.86 for 86 problems) is kept apart: it is not a provider-reported cost. Pareto
chart on all 86: [`m3e/pareto_eval86.svg`](m3e/pareto_eval86.svg), [`m3e/pareto_eval86.csv`](m3e/pareto_eval86.csv).

**LG+Sonnet, if it were run.** From the smoke runs, Sonnet cost $0.169 a problem on the 5 smoke problems where Opus
cost $0.257 (a ratio of 0.66). Scaled to Opus's measured $22.25 on all 86, that gives **about $14.70 for one Sonnet run
on the 86** (the smoke mean times 86 gives $14.54). The smoke runs underestimated Opus's per-problem cost by half in
brief 14, so the run should be budgeted at up to about $20. At `budget_usd` = $0.75 (3× Sonnet's smoke 90th
percentile) and 4 threads, the guard charges up to $3 for calls in flight, so a guard of about **$21** would keep it
from refusing problems.

**Spend for brief 14b: $5.14** (run 41095517652 $4.2101, run 41097171384 $0.9291; no smoke run). The key's usage moved
from $74.40 to $79.94 over the brief (key checks 41095453120, 41096944887, 41097993907); the $0.41 beyond this brief's
runs is another brief's smoke spend on the shared key. **M3e in all: $24.38** (brief 14 $19.24, brief 14b $5.14).
$79.94 of the owner's $150 ceiling is used.

### Brief 14 (the first dispatch, as first reported)

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

- **One run per arm, exploratory.** No confirmatory claim. The base's identical runs range 57.0–65.1% on the 86
  problems (62.7–67.2% on the first 67).
- **The LG+Opus arm comes from three dispatches, on one date (2026-10-30), from two commits with the same agent code
  and agent image** (`a152c14` for run 41040802008; `54caebb` for runs 41095517652 and 41097171384). Each problem was
  run once. The later 19 ran a few hours after the first 67, so the provider's load or routing could differ between
  the two parts; every call in all three was served by "Claude Platform on AWS". The two parts are not a random split
  (the 19 are the alphabetical tail).
- **Sonnet is not run** (spend). The Sonnet half of the decomposition is missing; only CC+Sonnet − LG+luna is known.
- **The ladder ran on 2026-10-25/26, this arm on 2026-10-30.** Same simulation and agent images; the providers differ
  (Claude Code on the plan, against OpenRouter routing to Anthropic on AWS).
- **Claude Code's turn budget is 60, ours 10.** The wall cap is the same (480 s). The harness effect includes that.
- **The base ran luna at reasoning `default`, the Claude arms at `low`.** The model effect includes the reasoning label.
- **The pre-registration's cost estimate was low** ($0.17 per problem expected, $0.259 seen on all 86).
- **The 67-problem results are kept as first reported.** They were the pre-registered view while 19 problems were
  missing; the full-86 results supersede them. The harness effect moved from −4.5 to +1.2 when the tail was added.

## Data

[`m3e/`](m3e/): `runs/LG_opus_41040802008.csv` (the first dispatch); `finish/` (the two finishing runs' raw CSVs);
`full86/LG_opus_41040802008+41095517652+41097171384.csv` (the merged arm); `smoke/` (the 4 smoke CSVs);
`attempted_ids.txt`, `guard_refused_ids.txt`, `guard_refused_and_benchmark_limited_ids.txt`; the `ablate.py` outputs
`vs_luna_*.md` and `harness_opus_*.md` (`eval86`, `eval79`, and the first dispatch's `attempted67`, `attempted63` and
`full86_refused_as_fail`); `taxonomy_by_arm_eval86.md`, `taxonomy_by_arm_all_rows.md`; `secondary_tables_eval86.md`,
`secondary_tables_attempted67.md`; `pareto_eval86.*`, `pareto.*`; `analyze.sh`, the commands that made them.
