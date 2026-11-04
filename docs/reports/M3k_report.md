# M3k report: a pre-submit interface check and a timing-claims turn, on our own API loop

**Status: DONE (2026-11-04). Decision: null.** All held-out runs and the one descriptive run per arm on the 86 are in.

- **Pre-registration:** [`m3k/preregistration.md`](m3k/preregistration.md). **Replay of K on M3j's R:**
  [`m3k/replay.md`](m3k/replay.md). **Smoke runs:** [`m3k/smoke.md`](m3k/smoke.md).
- **Analysis:** [`m3k/analyze.sh`](m3k/analyze.sh) (run from the repo root) writes every table below.
- Arms, all on `claude-haiku-5-5` (Anthropic Claude Haiku 5.5), `harness=apiloop` (our own Messages API loop), billed to
  the API key:
  - **R:** M3j's arm R, reused (not rerun; its request path is byte-identical, see the pre-registration).
  - **T:** R plus one extra first turn that lists the task's cycle-level claims (`fixed_checks=timing_claims`).
  - **K (exploratory):** R plus one deterministic interface, file-name and compile check when the model says it is
    finished, at most two round trips (`fixed_checks=presubmit_iface`).

## In short

- **Primary: T − R on the held-out set = +0.3 points [−4.7, +5.3]** (9 better, 9 worse, 82 same; sign test p = 1):
  no detectable effect. The extra "list the timing claims" turn passed 165/300 (55.0%) against R's 164/300 (54.7%).
- **Exploratory: K − R = +1.3 [−0.7, +3.7]** (7 / 3 / 90; p = 0.344): no detectable effect. K passed 168/300 (56.0%).
  The 7 problems where K did better and the 3 where it did worse are all problems where K's check **never fired**, so
  this is run-to-run noise, not an effect of the check.
- **Decision (T only; K was demoted to exploratory before any scored sweep): null.** Neither step moved the pass rate.
- **K's check rarely fired.** It sent a message in 18 of 300 held-out problem-runs (7 problems). The model cleared all the
  findings in 3 of them, and all 3 still failed. On the problems where it fired, K and R passed the same number of runs
  (net 0). The replay had put the ceiling at +3.0 points; the result is below even that.
- **T is the expensive one:** 61% more input tokens per held-out problem-run (75,086 against 46,570), median wall time
  36 s against 22 s, and $2.27 against R's $1.44 for the same score.
- **Cost:** about **$5.75 of API credit** for all scored runs (the repriced `api_cost_estimate_usd`, a list-price
  estimate). Console: TODO (planner: before TODO, after TODO).

**Decision: null.** This is another null for an agent change, after M3b's memory, M3g's pack, M3h's skills, M3i and M3j.
The only confirmed gain on this benchmark remains M3b's harness result (+4.7 [+1.0, +8.5]).

## Runs

Held-out: `split=m3g_heldout`; the 86: `split=agentic`, filtered by `tools/m3b_eval_ids.txt`. All runs used
`ubuntu-24.04-arm`, 4 threads, one dispatch per seed (`seeds=1`, `seed_offset` 0, 1, 2).

| Arm | Set | Seed | Run | Passed |
|---|---|---|---|---|
| T | held-out | 1 | [41745552617](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41745552617) | 57 |
| T | held-out | 2 | [41750211731](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41750211731) | 55 |
| T | held-out | 3 | [41754394269](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41754394269) | 53 |
| K | held-out | 1 | [41758368678](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41758368678) | 55 |
| K | held-out | 2 | [41761887580](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41761887580) | 56 |
| K | held-out | 3 | [41764768451](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41764768451) | 57 |
| T | the 86 | 1 | [41767578395](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41767578395) | 57 of 86 |
| K | the 86 | 1 | [41772404435](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41772404435) | 59 of 86 |
| R (M3j, reused) | held-out / the 86 | 1-3 / 1 | 41673126672, 41709498919 / 41694588753 + 41713923011 | 53, 57, 54 / 58 |

Every run was `completed/success`. No held-out row was `run_budget_exhausted`, `rate_limited` or `llm_error`. On the 86
there were **3 `llm_error` rows** (T 2: `binary_search_tree_algorithms_0001`, `hdbn_codec_0001`; K 1: `hdbn_codec_0001`).
They are not runs of the model, so they are reported as not run and are **not rerun** (the 86 are descriptive). The
tables count them as failures; leaving the two problems out of all three arms changes nothing
([`dev84_paired.md`](m3k/dev84_paired.md): T − R −1.2 [−8.3, +6.0], K − R +1.2 [−4.8, +7.1]).

## Results

### Primary: T − R (held-out, paired by problem)

| | R | T | T − R [95% CI] | better / worse / same | sign test p |
|---|---|---|---|---|---|
| pass@1, 100 problems × 3 runs | 164/300 = 54.7% | 165/300 = 55.0% | +0.3 [−4.7, +5.3] | 9 / 9 / 82 | 1 |

Per run: R 53, 57, 54; T 57, 55, 53. The realised half-width is 5.0 points (planned: about 4.3; T's per-problem
differences were a little more spread). The interval leaves open a loss of up to 4.7 points and a gain of up to 5.3.
Tables: [`m3k/heldout_paired.md`](m3k/heldout_paired.md).

### Exploratory: K − R (held-out)

| | R | K | K − R [95% CI] | better / worse / same | sign test p |
|---|---|---|---|---|---|
| pass@1, 100 problems × 3 runs | 164/300 = 54.7% | 168/300 = 56.0% | +1.3 [−0.7, +3.7] | 7 / 3 / 90 | 0.344 |

Per run: K 55, 56, 57. **Exploratory, no correction, decides nothing.** The replay on M3j's R runs had put K's ceiling at
+3.0 points ([`m3k/replay.md`](m3k/replay.md)). The interval's upper end, +3.7, sits just above it, but the point
estimate is not caused by the check: K's check fired on only 7 problems, and on those K and R have identical totals
(see "K's round trips" below). All 10 problems that differ between K and R are problems where K never sent a message.

### The 86 (descriptive, one run per arm)

| Arm | 86 problems | Against R [95% CI] | 79 (7 benchmark-limited left out) |
|---|---|---|---|
| R (M3j) | 58 (67.4%) | — | 58 (73.4%) |
| T | 57 (66.3%) | −1.2 [−8.1, +5.8] (4 / 5 / 77) | 57 (72.2%), −1.3 [−8.9, +6.3] |
| K | 59 (68.6%) | +1.2 [−4.7, +8.1] (4 / 3 / 79) | 59 (74.7%), +1.3 [−5.1, +7.6] |

Tables: [`m3k/dev86_paired.md`](m3k/dev86_paired.md), [`m3k/dev79_paired.md`](m3k/dev79_paired.md). The 86 are the
development set, so they cannot confirm anything.

### Secondary (exploratory, no correction)

**Did K cut `compile_fail_own` + `signal_missing_hidden`?** No. Failures by primary label
([`taxonomy_dev86.md`](m3k/taxonomy_dev86.md), [`taxonomy_heldout.md`](m3k/taxonomy_heldout.md)):

| Label | 86: R / T / K | Held-out (300 runs): R / T / K |
|---|---|---|
| `compile_fail_own` | 7 / 6 / 5 | 11 / 10 / 13 |
| `signal_missing_hidden` | 7 / 7 / 7 | 16 / 11 / 16 |
| `tests_failed_no_selfcheck` | 19 / 19 / 19 | 104 / 108 / 99 |
| `sim_incomplete` | 1 / 1 / 1 | 5 / 6 / 4 |
| `llm_error` (not run) | 0 / 2 / 1 | 0 / 0 / 0 |
| All failures | 34 / 35 / 33 | 136 / 135 / 132 |

The two labels K targets total 14 / 13 / 12 on the 86 and 27 / 21 / 29 on the held-out runs (R / T / K): K 29 against
R's 27, so no cut. (T's 11 `signal_missing_hidden` against R's 16 is the one visible shift; its failures moved to
`tests_failed_no_selfcheck`, and the pass rate did not change.)

**Did T cut `tests_failed_no_selfcheck`?** No: 19 / 19 on the 86 and 108 against R's 104 on the held-out runs.

**K's round trips, and how often the findings were fixed.**

| | Held-out (300 runs) | The 86 (92 runs) |
|---|---|---|
| Runs where the check sent a message | 18 (6 passed) in 7 problems | 16 (10 passed) in 16 problems |
| Round trips: 1 / 2 | 3 / 15 | 1 / 15 |
| Findings at the first check, mean when fired | 1.6 | 3.0 |
| All findings gone at the last check | 3 (all three still failed) | 1 (passed) |
| Fewer findings, not none | 0 | 1 (4 to 1; passed) |
| Findings unchanged after two round trips | 15 | 14 |

In 29 of 34 firing runs the findings were the same count at the last check as at the first. Either the model judged
the findings not to be real mismatches (the message invites that), or it could not fix them; the CSV does not say which.

**K's false alarms** (a problem R passed that K failed after a K round trip, read from `api_tools.jsonl`):
- **Held-out: none.** The 12 failing K runs where the check fired are on 5 problems, and R passed none of them in any
  seed (0/3 each). The 6 passing runs where it fired (`gf_multiplier_0005`, `hamming_code_tx_and_rx_0011`; R passed both
  3/3) passed despite unresolved findings, so the check was harmless there.
- **The 86: one candidate**, `phase_rotation_0013`: R passed its one run, K failed after two round trips. The check
  reported 10 findings (original-RTL ports and a parameter of `slicer` and `slicer_top` that the task replaced); the
  model grepped the files and stopped without changing the interface. This is a false alarm by content, but it cannot
  be told from run-to-run noise on one run. The other five failing runs where K fired are on problems R failed too.

**`timing_claims_n` (T's list).** Held-out: mean 21.1 lines, median 21, range 9–47. The 86: mean 17.3, median 17,
range 7–31. The list was long but did not improve the score.

**Tokens, turns, wall time** ([`heldout_effort.md`](m3k/heldout_effort.md), [`dev86_effort.md`](m3k/dev86_effort.md)):

| Held-out, 300 runs per arm | Turns: median (mean) | Wall s: median | Prompt tokens incl. cache, per run | Completion tokens per run |
|---|---|---|---|---|
| R | 5 (5.4) | 22 | 46,570 | 6,190 |
| T | 6 (6.4) | 36 | 75,086 (+61%) | 10,224 (+65%) |
| K | 5 (5.6) | 22 | 49,484 (+6%) | 6,247 (+1%) |

On the 86: prompt tokens R 119,011, T 180,380 (+52%), K 127,425 (+7%); median wall time 37 s, 60 s, 38 s. All rows ended
in `submit`, except the 3 `llm_error` rows above.

### Cost

| | R (M3j, repriced) | T | K |
|---|---|---|---|
| Held-out (300 problem-runs) | $1.44 | $2.27 | $1.47 |
| The 86 (92 problems run) | $0.81 | $1.17 | $0.84 |

T and K: `api_cost_estimate_usd`, summed over rows, at Claude Haiku 5.5's list rates by usage per request (the corrected
guard; pre-registration, "The guard fix"). T and K total **$5.75**. R is M3j's figure (priced from tokens at the same
list rates; M3j's own `api_cost_estimate_usd` column used the old upper bound and is not used here). It is a list-price
estimate, not the Console's bill. **TODO (planner): Console before TODO, after TODO.**

## What it means

- **Two more nulls.** A timing-claims first turn (T) and a pre-submit interface check (K) do not move Claude Haiku 5.5's
  held-out pass rate. With M3b's memory, M3g's pack, M3h's skills, M3i's profile and M3j's loop, every agent change tried since M3b's
  harness result has been null. The failures that remain are mostly hidden tests that the model's RTL compiles for but
  fails (`tests_failed_no_selfcheck`, 104 of 136 on the held-out R runs), which neither step addresses.
- **K was aimed at too few failures.** The replay predicted at most 9 failing runs in 300 where the check could speak.
  It spoke in 12 failing runs on 5 problems, and the model rarely changed anything in response. A deterministic
  interface check is cheap (+6% input tokens) and harmless, but there is little for it to find on this benchmark with
  this model.
- **T costs more and returns nothing.** 61% more input tokens and 64% more wall time per problem for +0.3 points.
- **Do not read K's +1.3 as a gain.** It is in the direction the check was meant to push, but none of the 10 problems that
  differ between K and R is one where the check fired.

## What it cannot show

- One model (Claude Haiku 5.5), one loop, one benchmark.
- K's filters were chosen after looking at the held-out replay (see [`m3k/replay.md`](m3k/replay.md)); K's check text
  and T's instruction are one wording each.
- T's effect is the effect of this instruction text, not of any timing-aware prompt.
- At 3 runs on 100 problems, effects under about 5 points read as no detectable effect.
- R was reused from M3j (a day earlier), not run alongside T and K. Its request path is byte-identical.
