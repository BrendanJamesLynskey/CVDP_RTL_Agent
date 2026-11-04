# M3k pre-registration: a pre-submit interface check (K) and a timing-claims turn (T) on the plain API loop

Written on 2026-11-04, on the branch `m3k-presubmit-timing` (from `main` 5f569e9), before any scored dispatch. Nothing
here may change after the first scored dispatch. Anything learned later goes in the report, marked as such.

## The question

Knowledge additions were null three times (M3b memory, M3g pack, M3h skills); the only confirmed gain was harness work
(M3b, +4.7 [+1.0, +8.5]). On the 86, M3i's failures were mostly `tests_failed_no_selfcheck` (41 of 65), then
`compile_fail_own` (13) and `signal_missing_hidden` (10); M3j shows 10-14 interface-type failures per arm. M3k tests two
cheap harness steps aimed at those labels, with the model (`claude-haiku-5-5`) and the loop (M3j's arm R, `harness=apiloop`)
held fixed: **does either change the held-out pass rate?**

## Arms

| Arm | What | Sweep input |
|---|---|---|
| R (control) | M3j's arm R. **Not rerun**: its request path is byte-identical (below). Reused: the three held-out R CSVs (`m3j/runs/heldout_R12_41673126672.csv`, `heldout_R3_41709498919.csv`) and the dev-86 R run (`dev86_R_merged.csv`). | `harness=apiloop` |
| K | R, plus one deterministic check when the model signals it is finished (a turn with no tool call, not `GIVE_UP`), before scoring | `harness=apiloop fixed_checks=presubmit_iface` |
| T | R, plus one extra model turn at the start | `harness=apiloop fixed_checks=timing_claims` |

`workflow_dispatch` is at 24 of GitHub's 25 inputs, so both arms extend the existing `fixed_checks` choice
(`presubmit_iface`, `timing_claims`); `sweep.sh` accepts them only with `HARNESS=apiloop` and refuses M3c/M3d values
with apiloop. `tests/test_m3k.py` covers the validation and the input count.

### R's path is unchanged

`tests/golden_apiloop.json` is the list of requests R's loop sent to a scripted fake client, recorded from `main` at
5f569e9 before any M3k change; `test_r_request_path_is_byte_identical_to_the_m3j_golden` compares today's requests with
it (system, tools, messages, thinking, effort, caching, max_tokens, model; the per-call `timeout` is left out). With both
switches off the summary gains no key and the CSV no column. **The guard's pricing changed** (below), so
`api_cost_estimate_usd` and `guard_estimate_usd` mean something different from M3j's rows (M3j: an upper bound with
every input token at $0.50 per million; now an estimate at list rates by usage). M3j's tables are not regenerated.

### K, in detail

`agent/cvdp_agent/presubmit.py`. At the start of the run K reads the given interface from the task tree (`prompt.json`,
`docs/`, the original `rtl/` and `verif/` files; `interface.InterfaceCheck`, M3c's reader). It never opens a hidden test
or a harness file. When the model ends a turn with no tool call, K elaborates the current `rtl/` (pyslang, then Yosys as
M3c's fallback) and reports:

1. **Interface:** module names, ports (names, directions, widths) and parameters against the given interface
   (`interface.compare` plus a direction check), **after these filters**: `missing_module` only for a module the original
   RTL defines or a visible testbench instantiates, and not when any `rtl/` file declares it; `width` only when the given
   width comes from the original RTL, a module header or a visible testbench (not from prose); `direction` only for an
   input/output swap.
2. **Files:** every `rtl/<name>.(sv|v|svh|vh)` that the prompt or a document names must exist; a file with the other
   extension (`rtl/foo.v` for `rtl/foo.sv`) is `file_extension`, an absent one `missing_file`.
3. **Compile:** `compile_error` when pyslang and then Yosys both fail to elaborate `rtl/` (or there is no `.sv`/`.v` file).

If anything is found, the loop sends **one user message** and lets the model continue, **at most twice per problem**; if
nothing is found, or the two round trips are used, the run ends exactly as R would. The message (`presubmit.TEMPLATE`,
`n` the number of findings, one `- ...` line each, at most 30):

```
Before you finish: an automatic check of your files under rtl/ against the task, the docs and the files you were given found {n} problem{s}:
{lines}
Fix each one that is a real mismatch with the task, then stop with a one-line summary again. If a finding is wrong because the task does not require it, say so in one line and stop.
```

Each check is a line in `api_tools.jsonl` (`tool: presubmit`, turn, findings, kinds, engine, round, and the message
sent). CSV columns (appended only with an M3k arm): `presubmit_findings_n` (findings at the first check),
`presubmit_rounds` (round trips sent, 0-2), `presubmit_final_findings_n` (findings at the last check), `timing_claims_n`.

### T, in detail

Before the first normal turn, one call (adaptive thinking, effort `medium`, the same tools listed, `tool_choice: none`
so no tool can be used). The first user message is R's, followed by `\n\n# First step\n` and this instruction, verbatim:

```
Before you write any RTL, list every cycle-level claim in the task: latency in cycles, how long signals are held, reset values, when each output is valid, handshakes, and what happens on back-to-back inputs. Give one line per claim, quoting the task's own words, and write "not stated" where the task is silent. Reply with the list only; do not use any tool in this reply.
```

The reply (thinking blocks included) stays in the conversation as the first assistant turn, then a user message
`Now carry out the task.` and the normal loop starts. The extra call counts toward the 60-call cap and the wall cap.
`timing_claims_n` = the non-empty lines of the reply's text.

## The guard fix

`UPPER_RATES` priced every input token at $0.50 per million. Now `RATES`/`call_cost`: each request priced on its own by
its prompt length (fresh + cache reads + cache writes), up to 100,000 tokens $0.10 fresh / $0.125 5-minute cache write /
$0.01 cache read / $0.50 output per million, over 100,000 $0.50 / $0.625 / $0.05 / $2.50. **Source:**
platform.claude.com/docs/en/about-claude/pricing, "Claude Haiku 5.5 (for prompts up to / over 100,000 tokens)", read
2026-11-04. It uses the 5-minute write rate (the automatic cache's), charges every output token (thinking included),
and is a list-price estimate, not the Console's bill. Test: `test_call_cost_prices_cached_input_apart_and_by_tier`.

## Replay of K on M3j's runs (free, offline)

[`replay.md`](replay.md), made by `tools/m3k_replay.py` from M3j's arm R artifacts. K fires on 16 of 300 held-out
problem-runs: **9 failing (5 distinct problems: `compile_fail_own` 3, `tests_failed_no_selfcheck` 6) and 7 passing (false
alarms, 3 problems)**; on the dev 86, 15 of 92: 6 failing, 9 passing (15.5% of passing runs). The first version fired on 53
held-out runs (29 failing, 24 passing); three filters were added after seeing that, on the same held-out problems, so the
held-out numbers are not independent. **Expected ceiling for K: at most +3.0 points of pass@1 on the held-out set (9 of
300 problem-runs), a few-problem effect, below the ~4.9-point resolution below.** The threshold in the brief ("fewer than
5 failing held-out problem-runs") is not met; the planner may still judge K too narrow to spend on.

## Sets and runs (dispatched by the planner)

| Set | K | T | R |
|---|---|---|---|
| Held-out 100 (`split=m3g_heldout`) | 3 | 3 | 3 (M3j, reused) |
| The 86 (`split=agentic`, ids `tools/m3b_eval_ids.txt`) | 1 | 1 | 1 (M3j, reused; descriptive) |

One dispatch per seed (`seeds=1`, `seed_offset` 0, 1, 2; a `seeds=3` dispatch skips seed 3 under the step-time guard),
`runner=ubuntu-24.04-arm`, `threads=4`, model `claude-haiku-5-5`, one sweep at a time. A `rate_limited` or
`run_budget_exhausted` row is not run and is rerun (as M3j).

## Primary and decision rule

**Planner amendment, 2026-11-04, before any scored sweep.** Because the replay puts K's ceiling (+3.0 points) below the
resolution of three runs, and the held-out replay was used to tune K's filters, **K is demoted to a secondary,
exploratory arm.** It is still run (3 held-out + 1 on the 86, about $2.4 of API credit) and reported with the same
statistics, but it decides nothing and takes no share of the error rate.

**Primary: T - R on the held-out set, the only primary comparison,** paired by problem, as in M3g-M3j (`tools/ablate.py`):
each problem's pass rate over its 3 runs per arm, the mean difference, a paired bootstrap interval over problems (2,000
resamples) and the exact two-sided sign test (ties dropped), **95% intervals, no correction** (the sign test is reported
beside them and does not decide). T is **better** if its interval lies wholly above zero, **worse** if wholly below,
otherwise **no detectable effect**, reported with the interval's ends as the largest loss and gain it leaves open (bounds
rounded before the verdict, as `ablate.py` now does).

**Power.** M3j's R - PA half-width on this set, with 3 runs, was 4.3 points at 95%. An effect smaller than that reads as
no detectable effect.

**K - R (exploratory):** the same paired statistics at 95%, labelled exploratory; read beside the replay ceiling, with K's
false alarms on passing runs counted (a pass under R that fails under K after a K round trip).

**Secondary (exploratory, no correction):** label shift on the 86 (does K cut `compile_fail_own` + `signal_missing_hidden`;
does T cut `tests_failed_no_selfcheck`), K's round trips and how often the findings were fixed, tokens, turns, wall time,
stop reasons, `timing_claims_n`.

## Cost and guards

Smoke (`smoke.md`): K and T cost $0.003-0.005 per `m3g_smoke` problem, K up to $0.016 and T up to $0.030 on the longer dev problems. Expected, from M3j's R repriced (R held-out: 300 problem-runs for $1.44, $0.0048 each; R on the 86: $0.81 for 92) and the
smoke (K about the same as R when it does not fire, up to about +50% on a problem where it fires twice; T about +10%):
about **$0.5 per held-out dispatch (100 problems, one seed)** for K, **$0.55** for T, **$0.85-0.9 per 86 dispatch**, so
about **$5 in all** (the brief's estimate was $6-8). Run guards at about 3x: `run_budget_usd` **1.6** for each held-out
dispatch, **2.6** for each 86 dispatch. The money spent is the Console's, read by the owner before and after.

## What it cannot show

One model, one loop, one benchmark. K's filters were chosen on the held-out replay. T's effect is the effect of this
instruction text, not of any timing-aware prompt. At 3 runs on 100 problems, effects under about 5 points are not
detectable.
