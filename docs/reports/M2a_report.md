# M2a report: reasoning limits, empty replies, seeds

23 October 2026. Branch `m2a-reasoning-seeds`,
[pull request 2](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/pull/2). A small change before M2. The rules
from the M1 report still apply.

**In short:** the empty replies were `max_tokens` truncation. A model that reasons fills the cap before it writes
anything (`finish_reason: length`), and `reasoning=low` alone does not prevent that.
- **Before review round 1** (first `low` run): DeepSeek returned 14 empty replies in 66 calls, against 8 in 49 in
  M1, and 90% of its completion tokens were reasoning. At `off` it returned none: 6/10 for $0.0867, against 7/10
  for $0.3546 at `low`, so **$0.0145 per solved problem against $0.0507**.
- **After review round 1**, which added reasoning headroom on top of each cap, a hard deadline per call, DSML
  markup detection and the `low → off` retry step: DeepSeek at `low` returned 5 empty replies in 56 calls, all 5
  retried successfully. It solved 6/10 for $0.2194 ($0.0366 per solved problem), and no problem went past the
  480 s cap.
- **Owner decision for M2** (review round 1): reasoning is set per model and declared in every row label.
  DeepSeek runs `off`; the third model is `openai/gpt-6-luna`.

## Done

- **`CVDP_REASONING`** (`default` | `low` | `medium` | `high` | `off`), passed through `CVDP_AGENT_ENV` like the
  other settings. The sweep has a matching `reasoning` input (default `low`). How each value is sent:
  - `default` sends no `reasoning` field, so the request is the same as M1's.
  - The other values send OpenRouter's `reasoning: {effort, exclude: true}`, where `off` is `effort: "none"`
    (checked against OpenRouter's reasoning-tokens docs on the day).
  - The reply text is the message `content` only. Reasoning text never reaches the parsers or the trace. The
    count, `usage.completion_tokens_details.reasoning_tokens`, goes into each trace event (`reasoning_tokens`,
    with `finish_reason`), and is summed into `summary.json`.
  - Since review round 1, a call that may reason gets headroom over the answer's cap (below).
- **A model that refuses the field.** An HTTP 400 on a request that carries the field becomes `ReasoningRejected`.
  - The trace records it (`reasoning_rejected: true`, the error with redaction, `fallback`). The call is made
    again without the field, and the problem stays at `default` from then on (`reasoning_used` in the summary).
  - It never fails the problem. A 400 generates nothing, so it is not counted as unreported cost.
- **Empty replies.** A reply counts as empty when its text is empty after stripping, or when it holds only
  tool-call markup with nothing usable inside: no edit block for an edit, no plan keys for a plan, no `decision`
  for a reflect. Markup here means DeepSeek-style `<｜tool▁calls▁begin｜>…` tokens, DeepSeek's DSML tags
  (`<｜DSML｜ calls>`, `<｜DSML｜ invoke …>`, added in review round 1), and `<tool_call>` or `<function_calls>`
  blocks. An empty reply is retried **once**:
  - reasoning goes one step lower: high → medium → low → off, and default → low;
  - one line is added to the messages (`prompts.ANSWER_ONLY`) asking for the answer only, in the format asked.

  The empty call's cost counts. Both calls are traced, each with a `call_id`, and the retry carries `retry_of`.
  The lower level applies to that retry only. If the retry is empty too, or a stop rule (budget, wall time,
  unreported cost) leaves no room for it, the turn goes on as before: it is used and the best edit is kept. If a
  model refuses the lower level on a retry (say `off` on a model that must reason), the retry is made at the
  problem's own level, which stays as it was.
- **Unparseable reflect replies.** These are replies with neither a JSON decision nor a bare decision word, the
  case that fell back to `submit` in M1. They now get one retry asking for the JSON decision only
  (`prompts.JSON_ONLY`). If the retry cannot be read either, the agent submits.
- **Counters** in `summary.json`: `empty_replies`, `empty_retries`, `reflect_parse_retries`, `reasoning_tokens`,
  `reasoning`, `reasoning_used`, `reasoning_rejected` and `seed`. `collect.py` writes them as columns. `table.py`
  puts one total line per model under the table: `Empty replies: N (retried M); reflect parse retries: K;
  reasoning tokens (reported): T`.
- **Seeds.** The sweep has a `seeds` input (default 1); `tools/sweep.sh` takes `SEEDS`.
  - Each seed gets its own work directory (`work/seed<n>/`) and its own harness run, one after another in the same
    job, with `CVDP_SEED=<n>` passed to the agent. The agent uses it only as a label, in the trace's `start` event
    and in the summary, because OpenRouter sampling is not seedable across providers.
  - All seeds share one ledger, so the spend guard covers the whole job. The default guard is now
    budget × problems × seeds × 1.2.
  - `collect.py` has a `seed` column (`--seed`). `table.py --seeds` reports mean pass@1 across seeds with the
    min–max range, pooled pass@1 with a 95% interval from a bootstrap over problems (each problem's seeds kept
    together; review round 1 replaced a Wilson interval that treated problem × seed rows as independent), and
    cost per solved problem pooled across seeds. The sweep uses it when more than one seed was collected.
  - The PR smoke run now uses 2 seeds, so this path runs on every pull request. The sweep also prints
    `results.csv` to the job log.
- **`tools/models.py`.** For a list of OpenRouter model IDs it prints whether each exists, its prices (including
  conditional prices by prompt length or time of day), its context length, and whether it takes `reasoning` (the
  efforts it lists, its default, and whether reasoning is on by default or mandatory). The source is the public
  `https://openrouter.ai/api/v1/models`, with no key. `--search` lists candidate IDs.
- **README**: the new settings, the sweep inputs `reasoning` and `seeds`, the seed layout, and `models.py`.

## How it was verified

**Tests:** 82 passed, 1 skipped locally (the skipped test needs Icarus, which CI installs). 28 of them are new, in
`tests/test_m2a.py`, all with the fake provider or a mock HTTP transport, so no test needs an LLM:

- **Each reasoning setting reaches the request body.** Through the graph with the fake provider. Separately,
  through the real `OpenRouterLLM` against an `httpx.MockTransport`: the captured JSON body has the right
  `reasoning` field (none for `default`), `usage.include` is still sent, `reasoning_tokens` is read from `usage`,
  and the reasoning text stays out of the reply.
- **A model that rejects the field falls back without failing.** With the fake provider, and with the whole agent
  on the mock OpenRouter returning 400 to any request with the field. Only the first request carries the field,
  and the problem submits.
- **Empty replies.**
  - An empty reply is retried once, one step lower, with the answer-only line. Both costs count, the trace links
    them with `retry_of`, and the retry's level does not carry over to later calls.
  - A second empty reply ends the turn as before: no third call, checks ran, then reflect.
  - DeepSeek tool-call markup counts as empty.
  - No retry when the empty call used up the budget.
  - A refused lower level on a retry is made at the problem's level.
- **The reflect-parse retry happens once.** It submits if the retry still cannot be read, and follows the retry's
  decision if it can. A readable reply is not retried.
- **`seeds=3`, end to end, through `tools/sweep.sh`.** A stand-in `run_benchmark.py` runs the real agent (fake
  provider) and writes `raw_result.json`. The test checks:
  - three work directories, and `CVDP_SEED` 1, 2 and 3 reaching the agent;
  - the `seed` column, and the across-seed table;
  - one ledger: seed 1 spends $0.012, seed 2 starts under the $0.02 guard and ends at $0.024, and both of seed 3's
    problems stop with `run_budget_exhausted`;
  - `smoke_check.py` passes on the same layout.

  `sweep.sh` also rejects bad `SEEDS` and `REASONING` values.
- **The key never appears in a trace from any of these paths.** Every test in the file runs with a fake key in the
  environment. The mock OpenRouter's 400 echoes the request's `Authorization` header, and the trace shows
  `[REDACTED]` instead. After each run every file in `agent_out/` (and, for the seeds test, the whole work tree)
  is scanned for the key.
- The M1 tables recompute unchanged: `table.py` on the M1 CSVs is identical to `docs/reports/m1/table.md`.

**CI runs on this branch.** Status is from the Actions API, the same fields `gh run view <id> --json
status,conclusion` prints. `gh` is not logged in in this session, so the API was read directly, as in M1.

| Run | Workflow | Commit | What it shows | status, conclusion |
|---|---|---|---|---|
| [39938384439](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39938384439) | Tests (push) | `b7b2269` | pytest, including the Icarus test | completed, success |
| [39938394603](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39938394603) | Tests (PR) | `b7b2269` | the same on the PR merge commit | completed, success |
| [39938384475](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39938384475) | Images | `b7b2269` | agent image rebuilt on x86-64 and Arm64 and joined | completed, success |
| [39938394544](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39938394544) | Sweep (PR smoke) | `b7b2269` | fake provider, 2 problems × **2 seeds** through the real harness; `smoke_check.py work 2 2` | completed, success |
| [39925914003](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39925914003) | Sweep (dispatch) | `d568299` | Haiku 5.5, 10 problems, `reasoning=low`, Arm64 | completed, success |
| [39936095610](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39936095610) | Sweep (dispatch) | `261367d` | DeepSeek, 10 problems, `reasoning=low`, Arm64 | completed, success |
| [39938587492](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39938587492) | Sweep (dispatch) | `b7b2269` | DeepSeek, 10 problems, `reasoning=off`, Arm64 | completed, success |

Earlier pushes on the branch (`c7a813a`, `d568299`, `261367d`) also passed Tests, Images and the PR smoke run.
Every dispatched sweep's key scan found nothing, and its upload ran.

## Live check

The same 10 M1 problems (`tools/m1_ids.txt`) with M1's settings: $0.10 per problem, 10 turns, self-check and lint
on, 2 threads. All runs were in Actions on `ubuntu-24.04-arm`. Pass/fail is the harness's. Cost and tokens are
OpenRouter's reported usage. Wall time is the harness invocation, timed by `sweep.sh`.

**Price.** DeepSeek V4.1 Flash is listed with time-of-day prices: $0.15/$0.60 per M off-peak, and $0.30/$1.20 on
weekdays 01:00–04:00 and 06:00–10:00 UTC (see the model list below). The DeepSeek runs started after 10:00 UTC
(10:01, 10:22 and 11:35). That does **not** mean every call was billed at the off-peak price. The planner's review
read the artifacts: 20 of 66 calls in the first `low` run, and 7 of 80 in the `off` run, were billed at exactly
2.0× the list price. That is consistent with OpenRouter routing those calls to a provider that charges more. Until
review round 1, nothing recorded which provider served a call. The round-1 re-run records it: 7 different
providers served its 56 calls.

**DeepSeek against M1:**

| | M1, local x86-64, default reasoning | M1, Arm64 in Actions, default | **M2a `low`**, Arm64 (old `low → minimal` retry, no headroom) | **M2a `off`**, Arm64 | **Round 1 `low`**, Arm64 (`low → off`, headroom, deadline) |
|---|---|---|---|---|---|
| Run | local | 39882473408 | 39936095610 | 39938587492 | 39947121488 |
| pass@1 [Wilson 95%] | 5/10 [23.7, 76.3] | 6/10 [31.3, 83.2] | **7/10** [39.7, 89.2] | **6/10** [31.3, 83.2] | **6/10** [31.3, 83.2] |
| Cost (provider) | $0.2704 | ≥ $0.2401 (1 problem unreported) | $0.3546 | **$0.0867** | $0.2194 |
| $/solved | $0.0541 | ≥ $0.0400 | $0.0507 | **$0.0145** | $0.0366 |
| LLM calls | 49 | 40 | 66 | 80 | 56 |
| Empty replies | 8 (6 plans, 2 edits) | not read | **14**: 11 first empties (10 retried, 1 capped by wall time), 3 retries empty (all plans, at `minimal`) | **0** | **5**, all retried, no retry empty |
| Reflect parse retries | (1 markup reply, defaulted to submit) | n/a | 4 (all DSML-only replies, then not caught as empty) | 0 | 0 |
| Completion tokens (of which reasoning) | 357,638 (not recorded) | 246,734 (not recorded) | 384,304 (346,935 = 90%) | 55,666 (0) | 305,580 (265,158 = 87%) |
| Median wall per problem | 144 s | 95 s | 136 s | 13 s | 52 s |
| Longest problem | 528 s | killed at 600 s | 541 s | 62 s | 464 s |
| Harness wall time, 10 problems | not recorded | not recorded | 954 s | 194 s | 741 s |
| Stop reasons | submit 9, wall_time 1 | n/a | submit 8, budget 1, wall_time 1 | submit 9, max_turns 1 | submit 9, wall_time 1 |

What this shows:

- **`low` alone did not stop the empty replies, because they were truncation.**
  - In the first `low` run the empty-reply rate went from 16% (8 of 49) to 21% (14 of 66), and reasoning was 90% of
    completion tokens.
  - Every first empty had `finish_reason: length`, with reasoning tokens equal to the cap: 6 of 10 plans spent all
    4,000 tokens reasoning (from the planner's review of the artifacts). `exclude: true` hides the reasoning but
    does not exempt it from `max_tokens`.
  - With headroom over the cap (round 1), empties fell to 5 in 56 calls, and every retry succeeded.
  - `tools/effort_probe.py` (output in [`m2a/effort_probe.txt`](m2a/effort_probe.txt), 11:32 UTC) gave 166 / 309 /
    102 / 0 reasoning tokens at `default` / `high` / `low` / `off` on one small prompt. So the effort level does
    change DeepSeek's reasoning, and only `off` stops it. One prompt, one call each, varies from run to run: an
    earlier uncommitted run of the same prompt gave 174 / 214 / 186 / 0.
- **The retry recovered problems.** `dynamic_equalizer_0004` was the M1 problem lost to an empty edit. At `low` it
  had 2 empty replies, both retried, and it passed, though at $0.1203 it stopped on `budget`. Of the 6 problems
  with empty replies, 3 passed (`DES_0003`, `dynamic_equalizer_0004` and `ttc_lite_0001`; the first two failed in
  M1) and 3 failed.
- **At `off`, DeepSeek was quicker and much cheaper for no fewer passes than the round-1 `low` run** (6/10 each;
  the first `low` run got 7/10). Ten problems cannot separate 6 from 7: the intervals overlap almost entirely.
  Every number above is from the provider.
- **Per problem (pass, $, empty replies):**

| Problem | M1 local | M2a `low` (old retry) | M2a `off` | Round 1 `low` |
|---|---|---|---|---|
| `DES_0003` | fail, $0.0180 | PASS, $0.0511, 3 empty | fail, $0.0147 | PASS, $0.0399 |
| `axis_to_uart_0001` | PASS, $0.0244 | PASS, $0.0099 | PASS, $0.0062 | PASS, $0.0243 |
| `barrel_shifter_0002` | PASS, $0.0189 | PASS, $0.0119 | PASS, $0.0031 | PASS, $0.0024 |
| `csr_using_apb_interface_0001` | fail, $0.0501 | fail, $0.0331, 3 empty | fail, $0.0099 (max_turns) | fail, $0.0399, 1 empty |
| `dual_port_memory_0001` | PASS, $0.0133 | PASS, $0.0020 | PASS, $0.0005 | PASS, $0.0039 |
| `dynamic_equalizer_0004` | fail, $0.0195 | PASS, $0.1203, 2 empty (budget) | PASS, $0.0230 | PASS, $0.0416, 1 empty (wall_time, 464 s) |
| `lfsr_0001` | PASS, $0.0005 | PASS, $0.0021 | PASS, $0.0012 | PASS, $0.0014 |
| `phase_rotation_0010` | fail, $0.0453 | fail, $0.0463, 1 empty | fail, $0.0138 | fail, $0.0087 |
| `phase_rotation_0028` | fail, $0.0379 | fail, $0.0607, 4 empty (wall_time, 541 s) | fail, $0.0040 | fail, $0.0359, 2 empty |
| `ttc_lite_0001` | PASS, $0.0426 | PASS, $0.0171, 1 empty | PASS, $0.0104 | fail, $0.0215, 1 empty |

**Haiku.** I could not check M1's traces for Haiku empty replies: the artifact store is blocked from this session
(403 at the proxy), and the M1 report mentions empty replies only for DeepSeek. So Haiku was run once, as the
brief allows:

| | M1, local | M1, Arm64 (39882465527) | **M2a `low`**, Arm64 (39925914003) |
|---|---|---|---|
| pass@1 | 6/10 [31.3, 83.2] | 6/10 [31.3, 83.2] | 5/10 [23.7, 76.3] |
| Cost | $0.1172 | $0.0882 | $0.0707 |
| $/solved | $0.0195 | $0.0147 | $0.0141 |
| Empty replies | none reported | n/a | **0** (reflect parse retries 0) |
| Harness wall time | not recorded | not recorded | 221 s (median 24 s per problem) |

Haiku accepted the field (no rejections) and gave no empty replies. At `low`, its reasoning was 27,926 of 72,503
completion tokens (38.5%), read from the artifacts by the planner's review: `low` does turn Haiku's thinking on.

**Spend for M2a: $0.7326**, all provider-reported:

- $0.0707 Haiku `low`;
- $0.3546 DeepSeek `low`;
- $0.0867 DeepSeek `off`;
- $0.2194 DeepSeek `low`, round 1;
- $0.0006 and $0.0006 for the two four-call effort checks.

The key's `usage` before each run agrees:
- 0.802830 → 0.873521: +$0.0707, Haiku;
- → 1.228696: +$0.3552, DeepSeek `low` plus the first effort check;
- → 1.315989: +$0.0873, DeepSeek `off` plus the committed effort check.

The round-1 run's "after" value is in its job summary, not its log.

## The model list (`tools/models.py`, 23 October 2026)

`python3 tools/models.py anthropic/claude-haiku-5.5 deepseek/deepseek-v4.1-flash-1017 openai/gpt-6-luna google/gemini-3.1-flash-lite qwen/qwen3.6-35b-a3b`:

| Model | Exists | $/M input | $/M output | Context | `reasoning` parameter | Other prices (input/output) |
|---|---|---|---|---|---|---|
| `anthropic/claude-haiku-5.5` | yes | $0.100 | $0.500 | 1,000,000 | yes (efforts: max, xhigh, high, medium, low, none; default medium) | $0.500/$2.500 for prompt ≥ 100,000 tokens |
| `deepseek/deepseek-v4.1-flash-1017` | yes | $0.300 | $1.200 | 1,048,576 | yes (efforts: max, high, low, none; default high; on by default) | $0.150/$0.600 for weekends, weekdays 00:00–01:00 UTC, weekdays 04:00–06:00 UTC, weekdays 10:00–00:00 UTC; $0.300/$1.200 for weekdays 01:00–04:00 UTC, weekdays 06:00–10:00 UTC |
| `openai/gpt-6-luna` | yes | $0.100 | $0.500 | 1,050,000 | yes (efforts: max, xhigh, high, medium, low, none; default medium; on by default) | $0.200/$0.750 for prompt ≥ 272,000 tokens |
| `google/gemini-3.1-flash-lite` | yes | $0.250 | $1.500 | 1,048,576 | yes (efforts: high, medium, low, minimal, none; default minimal; on by default) |  |
| `qwen/qwen3.6-35b-a3b` | yes | $0.100 | $0.950 | 262,144 | yes (efforts: any; on by default) |  |

The two candidates asked for are `openai/gpt-6-luna` (the Google or OpenAI small model) and `qwen/qwen3.6-35b-a3b`
(open weights: OpenRouter describes it as "an open-weight multimodal model … 35 billion total parameters and
3 billion active"). `gemini-3.1-flash-lite` is listed for comparison: it costs 2.5–3× Luna.

**Recommendation: `openai/gpt-6-luna`.**

- **It fills the slot M2 actually has open.** M2 calls for two cheap models and one open-weights model. DeepSeek is
  already the open-weights model, so the third model should be a second cheap one from another vendor. Qwen would
  make two open-weights models and no second cheap one.
- **Its list price matches Haiku's** ($0.10/$0.50), so cost per solved problem compares like with like. It has no
  time-of-day pricing. Its long-prompt price only starts at 272k tokens, and the agent's context is capped at
  120,000 characters of files.
- **Its reasoning can be turned off** (`none` is listed, not mandatory), so it can be run at the same setting as
  DeepSeek if `off` becomes the choice.

Against it: it is untested with this agent, and it reasons by default (medium), so it will be exposed to the same
empty-reply risk at `low`. I would run it once on the 10 problems before the full sweep (about $0.05–0.10).

## Known gaps

- **Reasoning is set per model** (owner decision, below). The sweep's default input is still `low`, so a dispatch
  must name the model's setting. Each row label now carries it.
- **One run each of 10 problems.** It cannot say whether `off` costs DeepSeek passes against `low` (7/10, 6/10 and
  6/10 across the three runs). The M3 reasoning ablation on all 92 is the place for that.
- **Reasoning headroom has a price.** At `low` a plan may now use up to 12,000 tokens and an edit up to 40,000.
  Most of that is reasoning, and every token is billed. The round-1 run cost $0.2194, against $0.0867 at `off`.
- **The throughput clamp learns per problem.** The first call has no rate yet, so only its hard deadline bounds it.
  A late first call is abandoned at the deadline rather than cut short in advance.
- **An abandoned call is still running at the provider and may be billed.** The agent counts it as unreported,
  which stops the problem and charges the guard the per-problem budget. Its real cost never reaches the agent.
- **Seeds above 1 have only run with the fake provider**: the PR smoke run (2 seeds through the real harness) and
  the pytest with a stand-in harness (3 seeds).
- **The seed time rule is strict.** A seed's worst case is ceil(problems / threads) × 660 s + 300 s. For all 92
  problems at 2 threads that is 30,660 s, more than the Run step's 19,000 s, so the sweep would refuse to start
  even seed 1. 4 threads give 15,480 s and fit one seed; two seeds of 92 need 8 threads or a matrix job per seed.
  The full M2 sweep has to choose one of those.
- **Provider routing is recorded, not controlled, by default.** `provider_order` pins it, at the risk of failed
  calls when a pinned provider is down (no fallbacks). The 2.0× bills in the first runs cannot be attributed to a
  provider, because those runs predate the provider trace.
- **A 400 on a request carrying the field counts as a rejection, whatever the cause.** A 400 from a prompt that is
  too long, for example, costs one more (unbilled) call before the usual error path.
- **The budget cap is soft by one call.** It happened once: `dynamic_equalizer_0004` in the first `low` run,
  $0.1203 against $0.10.
- **The artifacts were not read from this session.** It cannot reach the artifact store. The numbers above come
  from the job logs. The figures marked as the planner's review (finish reasons, 2.0× bills, first empties,
  Haiku's reasoning share) were read from the artifacts by the planner.

## Gotchas

- **DeepSeek V4.1 Flash's price depends on the time of day** (UTC hours and weekday). The cost of a run depends on
  when it ran. Comparisons of cost per solved problem across runs or models need the run times, or need DeepSeek
  runs kept to off-peak hours, or both.
- **DeepSeek lists only `max`, `high`, `low` and `none`.** OpenRouter maps `medium` and `minimal` to the nearest
  listed effort.
- **langchain-openai drops OpenRouter's `provider` field** from the response. Since review round 1 the agent calls
  OpenRouter through the `openai` client directly; LangGraph still runs the graph.
- **`exclude: true` does not exempt reasoning from `max_tokens`.** The OpenRouter docs say so, and the M2a empties
  were exactly that.
- **httpx's `timeout` is per read, not a deadline.** The 541 s problem's last edit call started at about 397 s
  with a 36.6 s timeout and ran 144.3 s. A deadline has to be enforced outside the HTTP client.
- **The harness writes `raw_result.json` only when a run ends**, so a seed cut off by the step timeout loses
  everything it finished.
- **`workflow_dispatch` took 13 inputs here.** The older limit of 10 no longer applies.
- **`off` must be quoted in the workflow's `options`**, or YAML reads it as a boolean.

## Decisions

- **`default` sends no field at all**, not `{exclude: true}` alone, so a model that refuses the field gets exactly
  M1's request.
- **`exclude: true` on every other level**, so reasoning text never comes back to the agent. Its count still does.
- **Retries obey the stop rules** (budget, wall time, unreported cost) but not the turn cap, because a retry is part
  of the same turn. A retry's lower reasoning level is for that one call. Lowering it for the rest of the problem
  might cost passes the retry did not need to lose.
- **"Unparseable" keeps M1's reading.** A bare `edit_again`, `submit` or `give_up` in prose still counts as a
  decision. Only replies that fell through to the `submit` default are retried.
- **The retry steps from `low` to `off`, not `minimal`.** `minimal` is not one of the settings and is not listed by
  every model (above).
- **Seed work directories are `work/seed<n>/` even for one seed**, so the layout, the upload paths and the smoke
  check are the same whatever the count. Seeds run one after another, as the brief says, and share one ledger.
- **A third live run, DeepSeek at `off`, beyond the brief.** `low` had not done what it was for, and the obvious
  next question was cheap to answer ($0.0867).
- **Owner decisions for M2, from review round 1:**
  - Reasoning is set per model and declared. DeepSeek runs `off`. Haiku and the third model each get their
    cheapest setting that solves no fewer of the 10 M1 problems. `table.md` and `results.csv` carry the setting
    in the row label, e.g. `deepseek/deepseek-v4.1-flash-1017 (reasoning off)`. M3 adds a reasoning ablation on
    all 92.
  - The third model is `openai/gpt-6-luna`. The planner picks its setting on the 10 M1 problems after the merge.
- **Headroom rather than `reasoning.max_tokens`.** OpenRouter takes either `effort` or `max_tokens` for reasoning,
  not both. DeepSeek does not list `max_tokens` support, so a reasoning budget would be mapped back to an effort.
  Room over the answer cap works for every model.
- **A deadline thread, not streaming.** It keeps the one-request shape and the provider-reported usage.

## Review round 1

The planner's review of `a81a352` asked for nine fixes and one more run. All are in commit `4599ee5`. Tests went
from 82 to 97; no test needs an LLM.

| # | Finding | Fix |
|---|---|---|
| 1 | The wall cap was not a deadline: httpx's timeout is per read, and one call ran 144 s, to 541 s | Every LLM call runs in a worker thread with a hard deadline 2 s before the wall cap; one that misses it is abandoned and counted as `cost_unreported` (`deadline_missed` in the trace). `max_tokens` is cut to the time left at the problem's observed tokens/s (never below 512). Calls with under 60 s left get `max_retries=0`. A checkpoint before each call writes the summary and ledger entry with that call counted as unreported (`in_flight_calls`), and the next checkpoint clears it. The comment now says about 510 s at worst. Tests: a provider that sleeps 30 s against a 4 s cap is abandoned within cap + finalize; the in-flight call is on disk, and charged by the guard, before it returns; the clamp and the retry switch. |
| 2 | DSML markup was not caught | `<｜DSML｜ calls>`, `invoke` and `parameter` blocks (both closing forms, or cut off) count as markup. Tests use the live string. A DSML-only reflect now gets the empty-reply retry at a lower level, not the JSON-only retry. |
| 3 | Every empty was `max_tokens` truncation | Calls that may reason get headroom over the answer cap: low +8,000, medium +16,000, high +24,000, default +16,000, off +0. The report now says the empties were truncation. Test: the caps per level. |
| 4 | The pooled Wilson interval across seeds counted problem × seed rows as independent | `table.py --seeds` bootstraps over problems (2,000 resamples, each problem's seeds kept together). The test case gives [16.7, 83.3] where Wilson gave [25.4, 74.6]. |
| 5 | A seed killed by the step timeout loses its finished problems | A seed starts only if the Run step has its worst case left (`STEP_BUDGET_S` 19,000 in the workflow; worst case ceil(problems / threads) × 660 s + 300 s). A seed not started is written to `seed<n>.skipped` and listed in bold in `table.md`. Test: two seeds that cannot fit are both listed and neither runs. |
| 6 | Cost depends on routing or time, and nothing recorded it | The agent calls OpenRouter through the `openai` client directly. Each call's serving `provider` goes into the trace, the summary (`providers`) and `results.csv`. Each seed's UTC start and end go into `work.run.json` and `table.md`. The new sweep input `provider_order` pins routing (`provider: {order, allow_fallbacks: false}`). Tests: the provider is recorded per call; the order reaches the request body. |
| 7 | A capped empty reply was traced twice with one `call_id` | It is traced once, by the node, with `empty: true`. Test: unique `call_id`s. |
| 8 | The rejection event had no `retry_of`; errors were truncated before redaction | Both fixed. Test: an empty reply whose retry errors with the key placed across the truncation point. No 12-character piece of the key reaches the trace, and the call counts as unreported. |
| 9 | Report corrections | The probe is committed (`tools/effort_probe.py`, output in `m2a/effort_probe.txt`; its numbers replace the uncommitted ones). Also added: Haiku's reasoning share, the 541 s cause, DSML, the first-empty breakdown, and the old retry flagged in the headline table. The "off-peak price" claim is withdrawn. |
| also | Row labels carry the reasoning setting (owner decision) | `collect.py` writes a `label` column (`model (reasoning X)`), and `table.py` groups by it. The M1 tables, which have no label, recompute unchanged. |

**Re-run at `low`** (run [39947121488](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39947121488),
`4599ee5`, Arm64, 11:35–11:48 UTC):

- 6/10, $0.2194 ($0.0366 per solved problem);
- 5 empty replies in 56 calls, all retried, none of the retries empty;
- no reflect-parse retries;
- reasoning 87% of completion tokens;
- longest problem 464 s (`dynamic_equalizer_0004`, stopped on `wall_time` under the cap and passed); harness wall
  time 741 s;
- served by 7 providers (`results.csv` in [`m2a/`](m2a/)).

Against the first `low` run, empties fell from 14 to 5 and cost from $0.3546 to $0.2194, for one pass fewer
(`ttc_lite_0001`).

CI on `4599ee5` (status from the Actions API):

| Run | Workflow | status, conclusion |
|---|---|---|
| [39946915395](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39946915395) | Tests (push) | completed, success |
| [39946920309](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39946920309) | Tests (PR) | completed, success |
| [39946915349](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39946915349) | Images: agent image with the deadline and the `openai` client, both arches | completed, success |
| [39946920477](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39946920477) | Sweep (PR smoke): fake provider, 2 problems × 2 seeds, through the real harness | completed, success |
| [39947121488](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39947121488) | Sweep (dispatch): the DeepSeek `low` re-run above | completed, success |
