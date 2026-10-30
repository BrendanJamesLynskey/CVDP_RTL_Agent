# M3e: pre-registration

Written 2026-10-30, after the smoke runs and before any scored run was dispatched. The commit that adds this file is
the record of what was decided in advance. Any change to the agent, the settings or the analysis after the first
scored dispatch is stated in the report.

**Status: exploratory.** Each new arm is one run (seed 1), so every comparison here is reported with a 95% interval
and no confirmatory claim is made. A one-run arm also carries the run-to-run spread of about ±3 points seen between
identical sweeps of arm A (M3c, M3d), on top of the interval shown.

## Why

The Claude Code ladder ([`../claude_code_ladder.md`](../claude_code_ladder.md)) changed the harness and the model at
once: Claude Code with Opus 5.5 scored +11.6 points [+1.9, +21.3] over our LangGraph agent with `openai/gpt-6-luna`.
M3d showed that changing how our agent works, on luna, does nothing detectable. M3e runs **our unchanged LangGraph
agent** with `anthropic/claude-opus-5.5` and `anthropic/claude-sonnet-5.5` through OpenRouter, to split that gap into
a model part (at a fixed harness) and a harness part (at a fixed model).

## Arms

| Arm | Harness | Model | Source |
|---|---|---|---|
| LG+luna | LangGraph, 10 turns | `openai/gpt-6-luna`, reasoning `default` | M3d's fresh arm A, `m3d/runs/A*.csv` (3 runs, 2026-10-26) |
| LG+Opus | LangGraph, 10 turns | `anthropic/claude-opus-5.5`, reasoning `low` | new, 1 run (seed 1) |
| LG+Sonnet | LangGraph, 10 turns | `anthropic/claude-sonnet-5.5`, reasoning `low` | new, 1 run (seed 1); optional second run (seed 2) |
| CC+Opus | Claude Code, 60 turns | `claude-opus-5-5`, effort `low` | the ladder, `claude_code/runs/claude-opus-5-5.csv` |
| CC+Sonnet | Claude Code, 60 turns | `claude-sonnet-5-5`, effort `low` | the ladder, `claude_code/runs/claude-sonnet-5-5.csv` |

**Settings of the new arms:** M3c arm A's harness settings unchanged. LangGraph harness; `ubuntu-24.04-arm`; 4 threads;
10 turns; self-check and lint on; 480 s wall cap; no lessons memory; every M3c and M3d switch off; the 86 problems in
`tools/m3b_eval_ids.txt`. The agent image is the one M3d ran (`agent/` and `docker/` last changed in `29a6ec8`; no
change since M3d's `c96f058`). Only the model, the reasoning level and the per-problem budget differ from arm A.

**Reasoning.** The ladder ran Claude Code at effort `low`. The sweep's `reasoning=low` sends OpenRouter
`reasoning: {effort: "low", exclude: true}`, which OpenRouter maps to Anthropic's extended-thinking budget. It is the
closest equivalent, and it holds reasoning at `low` across the harness comparison. Luna's arm A ran at `default`
(the setting M2 chose for luna), so the model comparison changes the reasoning label along with the model; that is
part of "the model" here. In all 10 smoke rows the agent recorded `reasoning_used = low`, with reasoning tokens
reported, and no request was refused for its `reasoning` field. The report gives `reasoning_used` for every row.

**Per-problem budget** (`budget_usd`), about 3 × the smoke run's 90th-percentile cost per problem, so that it does not
bind:

| Model | Smoke cost per problem (5 problems) | 90th percentile (linear) | `budget_usd` |
|---|---|---|---|
| Opus 5.5 | $0.166, $0.197, $0.273, $0.309, $0.339 | $0.327 | **$1.00** |
| Sonnet 5.5 | $0.033, $0.141, $0.186, $0.241, $0.245 | $0.243 | **$0.75** |

The report counts problem-runs that stopped on `budget`.

**Dispatch** (from the branch `m3e-harness-or-model`):

```
gh workflow run sweep.yml --ref m3e-harness-or-model -f model=<anthropic/claude-opus-5.5|anthropic/claude-sonnet-5.5> \
  -f split=agentic -f runner=ubuntu-24.04-arm -f threads=4 -f reasoning=low -f budget_usd=<1.00|0.75> \
  -f run_budget_usd=<guard> -f seed_offset=<0|1> -f harness=langgraph -f ids=$(grep -v '^#' tools/m3b_eval_ids.txt | paste -sd,)
```

## Comparisons

All paired on the 86 problems with `tools/ablate.py --ids tools/m3b_eval_ids.txt` (paired bootstrap 95% interval
over problems, exact two-sided sign test):

1. **Model effect, at the LangGraph harness:** LG+Opus − LG+luna and LG+Sonnet − LG+luna (`--base LG+luna`).
2. **Harness effect, at a fixed model:** CC+Opus − LG+Opus (`--base LG+Opus`) and CC+Sonnet − LG+Sonnet
   (`--base LG+Sonnet`).

**The decomposition.** On the same problems, the paired effects add exactly: CC+Opus − LG+luna = (LG+Opus − LG+luna)
+ (CC+Opus − LG+Opus), and likewise for Sonnet. The report gives the total and its two parts, each with its interval,
for both models. The 79-problem view (`--exclude tools/benchmark_limited_ids.txt`) is reported beside the 86-problem
one, never in its place.

**Reading.** No decision rule is applied, since this is exploratory. An interval that excludes zero is described as
"detectable at this level", one that includes zero as "no detectable effect", with the effect size the interval rules
out.

**Problems the whole-run guard refuses.** If the guard stops a sweep before some problems start
(`run_budget_exhausted`), those problems carry no answer from the model. They are listed, and they are left out of
every comparison that involves that arm (with `--exclude`, in all arms of that comparison), so the pairing stays on
the problems every arm attempted. The full-86 numbers that count them as failures are shown beside, marked as such.

## Secondary analyses (descriptive only, no test)

- turns, LLM calls and self-check runs per problem-run (median and mean), by arm;
- the failure taxonomy by arm (`tools/taxonomy.py`);
- $/solved and $/problem, provider-reported for the LangGraph arms. Claude Code's plan cost estimates are kept apart
  and never mixed with provider-reported dollars;
- stops on `budget`, on the wall cap (`wall_time`) and on the turn cap;
- the Pareto chart (pass rate against $ per problem) of the LangGraph arms;
- `reasoning_used` and reasoning tokens, and the providers OpenRouter routed to.

## Spend

- Starting balance of the key: $24.85 left of its $80 limit (key check run 41039346705).
- **Hard stop: $20 for this brief, all in,** smoke runs included. Before each dispatch, its guard plus the spend so
  far must stay under $20, and the key must stay above $3. If not, the run is not dispatched, and the report says
  which arms are missing.
- Smoke spend (4 runs, below): $2.13.
- Expected cost of a scored run, scaled from the smoke runs by luna's cost on the same 5 problems against its cost on
  all 86 (the 5 are about 1.5× luna's average): **Opus about $15, Sonnet about $10.** Both together do not fit under
  the hard stop, so the order decides: **Opus first, then Sonnet only if its guard fits, then the second Sonnet run
  (seed 2) only if its guard fits after both.**
- Guards: each sweep's `run_budget_usd` is set to the expected cost plus threads × `budget_usd` (the guard charges a
  call still in flight at `budget_usd`), capped at what is left under the hard stop. For Opus that cap binds: its guard
  is **$17.50**. If the guard then stops the last problems, the rule under Comparisons applies.

## Smoke runs (not scored, before this file)

The 5 problems from brief 09's part two that M3d also smoked (`queue_0001`, `lfsr_0005`,
`binary_search_tree_algorithms_0001`, `nmea_gps_0008`, `ethernet_mii_0006`), the same 5 for both models, scored
settings except a $1.00 budget and a $3.00 guard:

- Opus: run 41039492587 (3 problems; the guard, charging 3 in-flight calls at $1.00, refused 2) and run 41040074667
  for the other 2. 3 of 5 passed (`queue_0001`, `nmea_gps_0008`,
  `binary_search_tree_algorithms_0001`, none ever solved by luna's arm A), $1.28.
- Sonnet: run 41039501474 (3 problems, 2 refused the same way) and run 41040083804 for the other 2. 1 of 5 passed
  (`nmea_gps_0008`), $0.85.
- All 10 rows: `reasoning_used = low`, 0 unreported calls, 0 empty replies, served by "Claude Platform on AWS".
- The guard refusals in the smoke runs are why the scored guards add threads × `budget_usd`.

## Caveats stated in advance

- The ladder ran on 2026-10-25/26 and these arms run on 2026-10-30. The simulation image and agent image are the
  same, but the provider (Claude Code on the plan against OpenRouter's Anthropic endpoints) and its routing may differ.
- Claude Code's turn budget is 60 against our 10; the wall cap (480 s) is the same. The harness effect includes that
  difference.
- Luna's base ran at reasoning `default`, the Claude arms at `low`.
- Every new arm is one run.
