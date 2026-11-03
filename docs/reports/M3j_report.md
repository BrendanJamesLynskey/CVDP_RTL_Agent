# M3j report: lean Claude Code against a plain API loop

**Status: DONE (2026-11-03). Decision: null.** All held-out runs and the one descriptive run per arm on the 86 are in.

- **Pre-registration:** [`m3j/preregistration.md`](m3j/preregistration.md). **Smoke runs:** [`m3j/smoke.md`](m3j/smoke.md).
- **Analysis:** [`m3j/analyze.sh`](m3j/analyze.sh) (run from the repo root) writes every table below.
- Arms, all on `claude-haiku-5-5` (Anthropic Claude Haiku 5.5), billed to the API key unless marked:
  - **PA:** M3i's plain profile (Claude Code 2.1.310 with our prompt and Read/Write/Edit/Bash).
  - **B:** PA plus `--bare`.
  - **R:** no Claude Code. It is our own Messages API loop (`agent/cvdp_agent/apiloop.py`) with four tools of our own.
  - **P:** M3i's plain profile on the Max plan, reused.
  - **D:** Claude Code as shipped (M3h's arm A, plan), reused.

## In short

- **Primary: R − PA = +0.0 points [−4.3, +4.3]** (7 better, 7 worse, 86 same; sign test p = 1): no detectable effect.
  A plain API loop of our own, with one system block and four one-line tools, passes exactly as often as lean Claude
  Code at this model: 164/300 (54.7%) each.
- **B − PA = +3.7 [+0.0, +7.7]** (13 / 5 / 82; p = 0.096): no detectable effect. The interval's lower end is exactly 0.
  B passed 58.3%, the same as P (58.0%) and D (58.3%), so this reads as PA being low rather than `--bare` helping.
- **PA − P = −3.3 [−7.3, +0.7]** (6 / 12 / 82; p = 0.24): no detectable effect. The two arms ran the same command on
  different billing, a day apart.
- **R − D = −3.7 [−8.3, +0.3]** (10 / 15 / 75; p = 0.42): no detectable effect. This is descriptive only, because the
  billing and the dates differ.
- **The 86, descriptive:** every arm is between 57 and 61 of 86, and every interval against PA includes zero.
- **Cost:** about **$7.3 of API credit** for all scored runs, against the $60 the guards allowed (the Console reads
  $7.83 for the month, smoke and the cancelled run included). Per held-out problem-run: R about $0.005, PA and B about
  $0.0055.
- **Tokens:** R used the fewest prompt tokens: 46,570 per held-out problem-run including cache. That is 70% of PA's
  66,787, 83% of B's 56,391 and 28% of D's 167,423. Turns and wall time were the same across the arms (median 5 turns,
  22–23 s).

**Decision: null.** Replacing Claude Code with a plain loop made no detectable difference. Neither did stripping it
further with `--bare`, or moving it from the plan to the API key. For this task and model, the harness that matters
is small: our prompt, four tools and a loop. Claude Code's extra system blocks, environment message, longer tool
descriptions and request settings neither help nor hurt by more than about 4 points.

## Runs

Held-out: `split=m3g_heldout`; the 86: `split=agentic`, filtered by `tools/m3b_eval_ids.txt`. All runs used
`ubuntu-24.04-arm` and 4 threads.

| Arm | Set | Seeds | Run | Passed | Not run, rerun |
|---|---|---|---|---|---|
| PA | held-out | 1–2 | [41653171329](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41653171329) | 53, 54 | 0 |
| PA | held-out | 3 | [41699661060](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41699661060) | 57 | 0 |
| B | held-out | 1–2 | [41663383742](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41663383742) | 61, 56 | 0 |
| B | held-out | 3 | [41705092841](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41705092841) | 58 | 0 |
| R | held-out | 1–2 | [41673126672](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41673126672) | 53, 57 | 0 |
| R | held-out | 3 | [41709498919](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41709498919) | 54 | 0 |
| PA | the 86 | 1 | [41682372640](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41682372640) | 57 of 86 | 0 |
| B | the 86 | 1 | [41688746438](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41688746438) | 57 of 86 | 0 |
| R | the 86 | 1 | [41694588753](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41694588753) + rerun [41713923011](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41713923011) | 58 of 86 | 30 (guard) |

Every PA and B row recorded `cc_api_key_source = ANTHROPIC_API_KEY`. There were no `profile_error` and no
`rate_limited` rows. B's init events listed Bash, Edit and Read, as captured.

### What happened that the pre-registration did not plan for

- **Seed 3 was a separate dispatch for every held-out arm.** Each held-out arm was sent as one dispatch with
  `seeds=3`. The workflow's step-time check then skipped seed 3, because the step had 15,400–15,800 s left against a
  worst case of 16,800 s. M3i had avoided this by sending one dispatch per seed. Seed 3 was sent afterwards with
  `seed_offset=2` and the same inputs. `ablate.py` pools the two dispatches as distinct runs.
- **R's first run on the 86 hit its guard.** The $5 guard stopped 30 of the 92 problems before their first model
  call (`run_budget_exhausted` with 0 LLM calls). R's guard charge is an upper bound: it prices every input token,
  cached or not, at $0.50 per million, which is about 50 times the cached rate. Those 30 problems were not run, so
  they were rerun in the same arm with the same seed. `tools/m3h_merge.py` now treats such rows as not run, like
  `rate_limited` and `profile_error`.
- **The chain overlapped once.** At 15:52 UTC the dispatch script's watch command exited early, while B's held-out run
  was still going, so the script started R alongside it. That R run was cancelled after 17 minutes and none of its
  rows are used. It was then rerun alone. Its spend is in the Console total.
- **A zero bound in `ablate.py`.** Per-problem pass rates are thirds, so an interval end that is exactly 0 could come
  out as ±1e-17. The tool then labelled the arm "better" or "worse" when the pre-registered rule says "no detectable
  effect". B − PA's lower end was exactly 0. `ablate.py` now rounds the bounds before the verdict, with a test
  (`tests/test_m3j.py`). Earlier generated tables with a printed bound of `+0.0` or `−0.0` were labelled the old way:
  M3b's first B − A (`m3b/arms_paired_*.md`) and M3h's secondary S2c − S1c. Both reports already treated those
  results with caution, and M3b's effect was later confirmed on new runs ([+1.0, +8.5]). Neither file is regenerated
  here.

## Results

### Primary: R − PA (held-out)

| | PA | R | R − PA [95% CI] | better / worse / same | sign test p |
|---|---|---|---|---|---|
| pass@1, 100 problems × 3 runs | 164/300 = 54.7% | 164/300 = 54.7% | +0.0 [−4.3, +4.3] | 7 / 7 / 86 | 1 |

Per run: PA 53, 54, 57; R 53, 57, 54. The realised half-width is 4.3 points, as planned. The interval rules out a
gain or a loss of more than about 4 points from replacing lean Claude Code with this loop.

Tables: [`m3j/heldout_paired.md`](m3j/heldout_paired.md).

### Secondary (exploratory, no correction)

| Comparison | Effect [95% CI] | better / worse / same | sign test p | File |
|---|---|---|---|---|
| B − PA (`--bare`) | +3.7 [+0.0, +7.7] | 13 / 5 / 82 | 0.096 | [`heldout_paired.md`](m3j/heldout_paired.md) |
| PA − P (API key against plan, a day apart) | −3.3 [−7.3, +0.7] | 6 / 12 / 82 | 0.24 | [`heldout_PA_vs_P.md`](m3j/heldout_PA_vs_P.md) |
| R − D (plain loop against Claude Code as shipped) | −3.7 [−8.3, +0.3] | 10 / 15 / 75 | 0.42 | [`heldout_R_vs_D.md`](m3j/heldout_R_vs_D.md) |

Pooled held-out pass@1: D 58.3%, P 58.0%, B 58.3%, PA 54.7%, R 54.7%. B − P, computed the same way, is
+0.3 [−3.7, +4.3] (11 / 10 / 79). That is not pre-registered and is shown only because it frames B − PA: B looks
better than PA mainly because PA's three runs came out low.

### The 86 (descriptive, one run per arm)

| Arm | 86 problems | Against PA [95% CI] | 79 (7 benchmark-limited left out) |
|---|---|---|---|
| PA | 57 (66.3%) | — | 57 (72.2%) |
| B | 57 (66.3%) | +0.0 [−7.0, +7.0] | 57 (72.2%) |
| R | 58 (67.4%) | +1.2 [−4.7, +7.0] | 58 (73.4%) |
| D (M3h) | 58 (67.4%) | +1.2 [−5.8, +8.1] | 58 (73.4%) |
| P (M3i) | 61 (70.9%) | +4.7 [−1.2, +11.6] | 60 (75.9%) |

Tables: [`m3j/dev86_paired.md`](m3j/dev86_paired.md), [`m3j/dev79_paired.md`](m3j/dev79_paired.md). The 86 are the
development set, analysed in depth before, so they cannot confirm anything. The 92-row failure taxonomy
([`m3j/taxonomy_dev86.md`](m3j/taxonomy_dev86.md)) has the same shape in all three arms. Most failures compile and
run but fail the hidden tests (19–23 per arm). Then come compile failures in the agent's own RTL (5–7) and signals
the hidden test needs but the RTL lacks (5–7).

### Effort and tokens (held-out, 300 problem-runs per arm)

| Arm | Turns: median (mean) | Wall s: median | Wall-cap stops | Prompt tokens incl. cache, per run | Completion tokens per run |
|---|---|---|---|---|---|
| PA | 5 (5.8) | 23 | 3 | 66,787 | 7,171 |
| B | 5 (5.6) | 22 | 0 | 56,391 | 6,855 |
| R | 5 (5.4) | 22 | 0 | 46,570 | 6,190 |

Tables: [`m3j/heldout_effort.md`](m3j/heldout_effort.md), [`m3j/dev86_effort.md`](m3j/dev86_effort.md). For
comparison, M3i's P used 61,805 prompt tokens per run (plan) and D 167,423.

### Cost

| | PA | B | R |
|---|---|---|---|
| Held-out (300 problem-runs) | $1.68 (Claude Code's figure) | $1.57 (Claude Code's figure) | $1.44 (from tokens at list rates) |
| The 86 (92 problems run) | $0.93 | $0.84 | $0.81 |

- **PA and B:** Claude Code's own `total_cost_usd`, which uses API rates (`plan_cost_estimate_usd`).
- **R:** priced from its recorded tokens at Claude Haiku 5.5's list rates for requests under 100K tokens: $0.10 per
  million fresh input, $0.01 per million cache reads, $0.125 per million cache writes and $0.50 per million output.
  Its pre-registered upper bound, the guard charge, was $19.62. That is how the guard came to stop 30 problems.
- **The Console:** the organization's spend for the month read $0.57 at 14:51 UTC, during PA's first held-out run, and
  $7.83 after the last run. The scored runs' estimates add up to about $7.3. Smoke runs, which Claude Code estimated
  at about $0.08, and the cancelled R run make up the rest.
- `cost_usd` stays blank in every row, by design: the API reports tokens, not cost. That is why `ablate.py` prints
  `≥$0.0000`.

## What it means

- **The harness is not where Claude Haiku 5.5's score comes from on this benchmark.** Five arms now span Claude
  Code as shipped, stripped in two ways, on two billing routes, and a 250-line loop of our own. They sit within about
  4 points of each other on the held-out set (54.7–58.3%), and no pairwise interval excludes zero.
- **The cheapest arm is our own loop.** It sends 28% of shipped Claude Code's prompt tokens for the same score. That
  makes it the natural baseline for later API-billed work, such as retrieved examples or a pre-submit interface check.
- **Plan against API key:** PA − P is −3.3 [−7.3, +0.7]. That is not detectable, and it is confounded with the date.
  M3i's plan results do not need to be rerun on the API.

## What it cannot show

- One model (Claude Haiku 5.5), one Claude Code version (2.1.310) and one benchmark.
- R − PA compares "this loop" with lean Claude Code, not every possible minimal loop.
- At 3 runs on 100 problems, effects under about 4 points read as no detectable effect.
