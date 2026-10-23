# M2a report: reasoning limits, empty replies, seeds

23 October 2026. Branch `m2a-reasoning-seeds`,
[pull request 2](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/pull/2). A small change before M2. The rules
from the M1 report still apply.

**In short:** the plumbing works, but `reasoning=low` does not fix DeepSeek's empty replies. At `low`, DeepSeek
returned 14 empty replies in 66 calls, against 8 in 49 in M1, and 90% of its completion tokens were reasoning. At
`off` it returned none: 6/10 for $0.0867, against 7/10 for $0.3546 at `low`. That is **$0.0145 per solved
problem against $0.0507**. The sweep default stays `low` as the brief asked. Whether M2 runs DeepSeek at `off` is
your call (see Decisions).

## Done

- **`CVDP_REASONING`** (`default` | `low` | `medium` | `high` | `off`), passed through `CVDP_AGENT_ENV` like the
  other settings. The sweep has a matching `reasoning` input (default `low`). How each value is sent:
  - `default` sends no `reasoning` field, so the request is the same as M1's.
  - The other values send OpenRouter's `reasoning: {effort, exclude: true}`, where `off` is `effort: "none"`
    (checked against OpenRouter's reasoning-tokens docs on the day).
  - The reply text is the message `content` only. Reasoning text never reaches the parsers or the trace. The
    count, `usage.completion_tokens_details.reasoning_tokens`, goes into each trace event (`reasoning_tokens`,
    with `finish_reason`), and is summed into `summary.json`.
- **A model that refuses the field.** An HTTP 400 on a request that carries the field becomes `ReasoningRejected`.
  - The trace records it (`reasoning_rejected: true`, the error with redaction, `fallback`). The call is made
    again without the field, and the problem stays at `default` from then on (`reasoning_used` in the summary).
  - It never fails the problem. A 400 generates nothing, so it is not counted as unreported cost.
- **Empty replies.** A reply counts as empty when its text is empty after stripping, or when it holds only
  tool-call markup with nothing usable inside: no edit block for an edit, no plan keys for a plan, no `decision`
  for a reflect. Markup here means DeepSeek-style `<｜tool▁calls▁begin｜>…` tokens and `<tool_call>` or
  `<function_calls>` blocks. An empty reply is retried **once**:
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
    min–max range, pooled pass@1 with a Wilson interval, and cost per solved problem pooled across seeds. The
    sweep uses it when more than one seed was collected.
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

**The DeepSeek runs were timed for off-peak prices.** DeepSeek V4.1 Flash is now priced by time of day: $0.15/$0.60
per M off-peak, and $0.30/$1.20 on weekdays 01:00–04:00 and 06:00–10:00 UTC (see the model list below). M1 quoted
$0.15/$0.60. Both DeepSeek runs therefore started after 10:00 UTC (10:01 and 10:22), at the off-peak price.

**DeepSeek against M1:**

| | M1, local x86-64, default reasoning | M1, Arm64 in Actions, default | **M2a `low`**, Arm64 | **M2a `off`**, Arm64 |
|---|---|---|---|---|
| Run | local | 39882473408 | 39936095610 | 39938587492 |
| pass@1 [Wilson 95%] | 5/10 [23.7, 76.3] | 6/10 [31.3, 83.2] | **7/10** [39.7, 89.2] | **6/10** [31.3, 83.2] |
| Cost (provider) | $0.2704 | ≥ $0.2401 (1 problem unreported) | $0.3546 | **$0.0867** |
| $/solved | $0.0541 | ≥ $0.0400 | $0.0507 | **$0.0145** |
| LLM calls | 49 | 40 | 66 | 80 |
| Empty replies | 8 (6 plans, 2 edits) | not read (see Known gaps) | **14** (10 retried) | **0** |
| Reflect parse retries | (1 markup reply, defaulted to submit) | n/a | 4 | 0 |
| Completion tokens (of which reasoning) | 357,638 (not recorded) | 246,734 (not recorded) | 384,304 (346,935 = 90%) | 55,666 (0) |
| Median wall per problem | 144 s | 95 s | 136 s | 13 s |
| Harness wall time, 10 problems | not recorded | not recorded | 954 s | 194 s |
| Stop reasons | submit 9, wall_time 1 | n/a | submit 8, budget 1, wall_time 1 | submit 9, max_turns 1 |

What this shows:

- **`low` did not stop the empty replies.** The empty-reply rate went from 16% (8 of 49) to 21% (14 of 66), and
  reasoning was 90% of completion tokens.
  - A direct check explains part of it. One small prompt (a 4-bit up/down counter, `max_tokens` 4,000) gave
    174 / 214 / 186 / 0 reasoning tokens at `default` / `high` / `low` / `off` ($0.0006 for all four).
  - So DeepSeek treats `low` much like its default (`high`), and only `off` stops it reasoning.
- **The retry recovered problems.** `dynamic_equalizer_0004` was the M1 problem lost to an empty edit. At `low` it
  had 2 empty replies, both retried, and it passed, though at $0.1203 it stopped on `budget`. Of the 6 problems
  with empty replies, 3 passed (`DES_0003`, `dynamic_equalizer_0004` and `ttc_lite_0001`; the first two failed in
  M1) and 3 failed.
- **At `off`, DeepSeek was quicker and much cheaper for one pass fewer** (6/10 against 7/10). Ten problems cannot
  separate 6 from 7: the Wilson intervals overlap almost entirely. Cost fell to a quarter of `low`'s, and every
  number above is from the provider.
- **Per problem (pass, $, empty replies):**

| Problem | M1 local | M2a `low` | M2a `off` |
|---|---|---|---|
| `DES_0003` | fail, $0.0180 | PASS, $0.0511, 3 empty | fail, $0.0147 |
| `axis_to_uart_0001` | PASS, $0.0244 | PASS, $0.0099 | PASS, $0.0062 |
| `barrel_shifter_0002` | PASS, $0.0189 | PASS, $0.0119 | PASS, $0.0031 |
| `csr_using_apb_interface_0001` | fail, $0.0501 | fail, $0.0331, 3 empty | fail, $0.0099 (max_turns) |
| `dual_port_memory_0001` | PASS, $0.0133 | PASS, $0.0020 | PASS, $0.0005 |
| `dynamic_equalizer_0004` | fail, $0.0195 | PASS, $0.1203, 2 empty (budget) | PASS, $0.0230 |
| `lfsr_0001` | PASS, $0.0005 | PASS, $0.0021 | PASS, $0.0012 |
| `phase_rotation_0010` | fail, $0.0453 | fail, $0.0463, 1 empty | fail, $0.0138 |
| `phase_rotation_0028` | fail, $0.0379 | fail, $0.0607, 4 empty (wall_time, 541 s) | fail, $0.0040 |
| `ttc_lite_0001` | PASS, $0.0426 | PASS, $0.0171, 1 empty | PASS, $0.0104 |

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

Haiku accepted the field (no rejections) and gave no empty replies. Its reasoning-token count for this run is not
known: the run predates the commit that prints `results.csv` to the log, and its artifact cannot be read here.

**Spend for M2a: $0.5126**, all provider-reported:

- $0.0707 Haiku `low`;
- $0.3546 DeepSeek `low`;
- $0.0867 DeepSeek `off`;
- $0.0006 for the four-call effort check.

The key's `usage` before each run agrees: 0.802830 → 0.873521 (+$0.0707, Haiku) → 1.228696 (+$0.3552: DeepSeek
`low` plus the effort check). The DeepSeek `off` run's "after" value is in that run's job summary, not its log.

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

- **`reasoning=low` does not do what it was meant to for DeepSeek** (above). The sweep default is still `low` as the
  brief asked. For DeepSeek, `off` was cheaper per solved problem in this run. One run of 10 problems cannot say
  whether `off` costs passes.
- **The retry ladder changed after the `low` run.** That run stepped `low → minimal`. DeepSeek does not list
  `minimal`, and OpenRouter maps an unlisted effort to the nearest listed one, which may be `low` again; that would
  explain why some retries came back empty. The ladder is now `low → off` (commit `b7b2269`). The `off` effort
  check shows DeepSeek accepts `effort: none` with zero reasoning tokens. The new ladder has not been re-run live
  at `low`; the tests cover it.
- **First empties and empty retries are not counted apart.** In the `low` run, `empty_replies` is 14 and
  `empty_retries` is 10. The other 4 are either retries that also came back empty, or empty replies with no room
  for a retry. The summary does not say which. The trace does (`retry_of`, `decision: "empty"`), but this
  session cannot download artifacts.
- **The wall cap overshot past the stated worst case.** `phase_rotation_0028` (DeepSeek `low`) stopped on
  `wall_time` at 541 s, against the 480 s cap and the M1 report's worst case of about 520 s. It was still under the
  harness's 600 s, and no problem was killed. The cause is not confirmed from the trace. One possibility is that
  the LLM call's timeout is httpx's per-read timeout, which keep-alive bytes from the server would reset. Worth
  checking before full M2 runs at `low`.
- **The budget cap was soft by one call, for the first time.** `dynamic_equalizer_0004` (DeepSeek `low`) ended at
  $0.1203 against $0.10.
- **Seeds above 1 have only run with the fake provider**: the PR smoke run (2 seeds through the real harness) and
  the pytest with a stand-in harness (3 seeds). No real-model run used more than one seed, to keep this within
  budget.
- **The Run step's 320-minute timeout limits seeds × problems.** At the `low` run's pace (954 s for 10 problems,
  2 threads) one seed of all 92 would take about 2.4 h, so two seeds would not fit. At `off` (194 s for 10), five
  would.
- **A 400 on a request carrying the field counts as a rejection, whatever the cause.** A 400 from a prompt that is
  too long, for example, costs one more (unbilled) call before the usual error path.
- **Haiku's reasoning tokens for this run are unknown** (above). Whether `low` turns Haiku's thinking on, and what
  it costs, is not measured. Its cost was lower than in either M1 run, for one pass fewer.
- **The artifacts from these runs were not read here.** Every number above is from the job logs (the
  harness's tables, `results.csv` as printed, the ledger total). The artifacts are in Actions for anyone who wants
  the traces.

## Gotchas

- **DeepSeek V4.1 Flash's price depends on the time of day** (UTC hours and weekday). The cost of a run depends on
  when it ran. Comparisons of cost per solved problem across runs or models need the run times, or need DeepSeek
  runs kept to off-peak hours, or both.
- **DeepSeek lists only `max`, `high`, `low` and `none`.** `medium` and `minimal` are mapped to the nearest listed
  effort by OpenRouter, and in practice `low` behaves much like `high`.
- **A bound `extra_body` in langchain-openai replaces the constructor's**, so `usage: {include: true}` has to be
  sent again with every call that adds `reasoning`. The mock-transport test checks that it is.
- **`workflow_dispatch` took 12 inputs here.** The older limit of 10 no longer applies.
- **langchain-openai disables httpx's proxy detection** unless it is given its own `http_client`. That matters
  only when running locally behind a proxy (this session); the effort check passed one.
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
  next question was cheap to answer ($0.0867). Total spend is $0.51, within the $1 allowance.
- **The sweep default stays `low`**, as specified. The data argue for `off` on DeepSeek, or for a per-model
  setting, but that changes what M2 measures, so it is your call.
