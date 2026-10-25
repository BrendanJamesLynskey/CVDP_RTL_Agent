# M2 report: the free agentic split, three models

23 October 2026. Agent image from `main` at `f636506` (M2a merged), harness `8e894cf`, dataset revision `5b807d9`.
Every sweep ran in GitHub Actions. The rules from the M1 report still apply: the LLM never produces a score, and
every cost comes from the provider's own usage report.

**In short:**
- Haiku 5.5 and gpt-6-luna solve the same share of the 92 free agentic problems: 52–56 and 52–53 out of 92 across
  the two runners. Luna does it for **half the cost**: $0.011 per solved problem, against $0.018–0.021 for Haiku.
- The open-weights DeepSeek V4.1 Flash solves 41–43, about 10 fewer, at $0.024 per solved problem.
- **Ten problems change result between two identical runs** of the same model, and 3 seeds on the 30-problem subset
  vary by up to 4 problems. So a gap of a few problems between models means nothing. Haiku and Luna are tied
  (each beats the other on 12 problems). Both beat DeepSeek (24 against 6, and 21 against 6).
- 28 of the 92 problems were solved by none of the 6 full runs; 29 by all 6. The null agent solves 0 (M0).
- The whole of M2, including the reasoning pick, cost **$8.55** of provider-reported spend, with 1 call unreported.

## Settings

| Model | Reasoning | Why (on the 10 M1 problems, Arm64; [`m2/reasoning_pick/`](m2/reasoning_pick/)) |
|---|---|---|
| `anthropic/claude-haiku-5.5` | `low` | `low` 7/10 for $0.0863; `off` 5/10 for $0.1570 |
| `openai/gpt-6-luna` | `default` | `default` 6/10 for $0.0519; `low` 5/10 for $0.0694; `off` 4/10 for $0.0457 |
| `deepseek/deepseek-v4.1-flash-1017` | `off` | M2a: `off` 6/10 for $0.0867; `low` 6/10 for $0.2194 |

The rule (owner decision, M2a review): each model's cheapest setting that loses no problem against its best
setting on the M1 10. One run of 10 problems is a weak test, so the rule only picks a setting; it does not rank the
settings. Before these runs, `tools/models.py`'s endpoint data showed every provider serving Haiku and Luna caps
output at 128,000 tokens, above the agent's largest request (56,000 at `high`), so no call could be refused for
its `max_tokens`.

Everything else is the sweep default: per-problem budget $0.10, 10 turns, self-check and lint on, 4 problems in
parallel (the M2a seed rule refuses 92 problems at 2 threads: its worst case is 30,660 s against the 19,000 s
step).

## Results: all 92 problems, one run per runner

| Model (reasoning) | Runner | pass@1 [Wilson 95%] | Cost | $/solved | Harness wall time | Run |
|---|---|---|---|---|---|---|
| Haiku 5.5 (low) | x86-64 | 52/92 = 56.5% [46.3, 66.2] | $1.1123 | $0.0214 | 2,417 s | 39967302029 |
| Haiku 5.5 (low) | Arm64 | 56/92 = 60.9% [50.7, 70.2] | $1.0300 | $0.0184 | 2,280 s | 39975578761 |
| gpt-6-luna (default) | x86-64 | 52/92 = 56.5% [46.3, 66.2] | $0.5455 | $0.0105 | 3,337 s | 39967317698 |
| gpt-6-luna (default) | Arm64 | 53/92 = 57.6% [47.4, 67.2] | $0.5776 | $0.0109 | 3,150 s | 39981444074 |
| DeepSeek V4.1 Flash (off) | x86-64 | 43/92 = 46.7% [36.9, 56.9] | $1.0314 | $0.0240 | 1,765 s | 39975562293 |
| DeepSeek V4.1 Flash (off) | Arm64 | 41/92 = 44.6% [34.8, 54.7] | $0.9763 | $0.0238 | 1,681 s | 39981458867 |
| Null agent (M0) | both | 0/92 | $0 | n/a | | |

Per-category tables (cid003, cid004, cid005, cid016 and the AMBA slice) are in [`m2/x86/table.md`](m2/x86/table.md)
and [`m2/arm64/table.md`](m2/arm64/table.md); per-problem rows in the CSVs beside them.

## Repeat runs: 3 seeds on 30 problems (Arm64)

The 30 problems are in [`tools/m2_seed_ids.txt`](../../tools/m2_seed_ids.txt): `pick_ids.py --seed 2`, quotas in
proportion to the split (cid003 11, cid004 8, cid005 7, cid016 4), exactly 3 from the AMBA slice.

| Model (reasoning) | Mean pass@1 [min–max over seeds] | Pooled [95% problem bootstrap] | Cost, 3 seeds | $/solved | Run |
|---|---|---|---|---|---|
| Haiku 5.5 (low) | 50.0% [46.7–53.3] | 45/90 = 50.0% [32.2, 66.7] | $1.0762 | $0.0239 | 39989184353 |
| gpt-6-luna (default) | 43.3% [36.7–50.0] | 39/90 = 43.3% [27.8, 60.0] | $0.6338 | $0.0163 | 39989199773 |
| DeepSeek V4.1 Flash (off) | 43.3% [43.3–43.3] | 39/90 = 43.3% [26.7, 60.0] | ≥$1.1605 (1 unreported) | ≥$0.0298 | 39997916502 |

The bootstrap resamples problems with each problem's three seeds kept together, so its interval is about twice
the width of a Wilson interval on 90 trials that are not independent. The subset came out harder than the split:
Haiku scores 50% on it against 57–61% on all 92. That is the draw of problems, not the model.

## What the runs show

- **Run-to-run noise is large.** Between its x86 and Arm64 runs, Haiku changed result on 10 problems, Luna on 9 and
  DeepSeek on 12. The same image, problems and settings ran on both, and the direction is not consistent (Haiku and
  Luna did better on Arm64, DeepSeek on x86), so this reads as the model's sampling, not the runner.
- **Haiku against Luna is a tie on pass rate.** Counting each problem's passes over both runners, Haiku is ahead on
  12 problems and Luna on 12. Luna uses less than half Haiku's tokens (2.6–2.8 M against 5.4–5.9 M per sweep) and
  costs half as much. It is slower per problem (median 67–76 s against 44–47 s).
- **DeepSeek is behind both.** Haiku is ahead on 24 problems and behind on 6; Luna is ahead on 21 and behind on 6.
  It also hits the turn cap more often (8–12 per sweep, against 0 for Haiku and 2–8 for Luna).
- **What no run solves.** 28 problems failed in all 6 full runs: 10 in cid003, 8 in cid004, 8 in cid005 and 2 in
  cid016. These are where M3's changes to the agent have room to show.
- **Arm64 is a little faster** for the same model (2,280 s against 2,417 s for Haiku; 1,681 s against 1,765 s for
  DeepSeek), as in M0 and M1.

## Cost bookkeeping

- Total M2 spend, summed from `results.csv` over every run here: **$8.5539**, against the $10–15 planned.
- **One unreported call**, in DeepSeek's seed run: on `monte_carlo_0006` (seed 1) a call got no reply within its
  445 s deadline and was abandoned. That is the M2a hard deadline doing its job: the problem stopped on
  `llm_error` at 478 s, under the harness's 600 s, the call is counted as unreported, and the guard charged it the
  full per-problem budget ($0.10).
- **Empty replies: 1 in all of M2**, from Luna on Arm64 (`custom_fifo_0004`). It came at 470 s, so the wall-time
  rule stopped the problem instead of retrying, as designed. No empty reply from DeepSeek at `off`.
- **Serving providers** (now traced per call): Haiku went to Anthropic's platform on AWS for all but 1 of 1,962 calls (that one to Google); Luna
  always to OpenAI; DeepSeek to 15–19 different providers per sweep.

## Known gaps

- One run per runner is one sample. The seeds give the noise on 30 problems, not on 92.
- The heavy split (75 problems, 56 of them bug fixing) is not run in M2.
- The plan's "leaderboard rows of 1.1.0" comparison is not here: the published rows are for full CVDP with
  commercial tools, not for the free split, and comparing them would mislead. M3 will say what is comparable.
  **Correction (2026-10-25).** This is wrong: LBC-bench (https://lbc-bench.si2.org) has three rows on exactly
  these 92 problems of release 1.1.0 (`agentic_code_generation_no_commercial`): 48, 52 and 53 of 92, one run each,
  marked not independently verified ([leaderboards.json at b835413](https://github.com/si2org/lbc-bench.github.io/blob/b8354131ba89f915f5f940a3300a06777ebe1e98/data/leaderboards.json)).
  They land in the same range as the sweeps here (41 to 56 of 92). The story page's "How this compares" section
  sets them side by side with their caveats; the M3b report does too.
- `tools/log_check.py` labels a log that ends inside a cocotb run with no pytest summary as `harness_error` (4
  in the first two sweeps). Those are simulations that hung or were killed, which the harness scores as failures.
  The pass rates are right; the label should say "simulation did not finish".
- The reasoning pick ran each setting once on 10 problems.

## Data

| Folder | What |
|---|---|
| [`m2/x86/`](m2/x86/) | The three full runs on `ubuntu-24.04`: `results_*.csv`, `table.md` |
| [`m2/arm64/`](m2/arm64/) | The three full runs on `ubuntu-24.04-arm` |
| [`m2/seeds/`](m2/seeds/) | 3 seeds × 30 problems per model, with the across-seeds table |
| [`m2/reasoning_pick/`](m2/reasoning_pick/) | The 10-problem runs that set the reasoning level for Haiku and Luna |

Tables are made from the CSVs by `python3 tools/table.py <csv>…` (`--seeds` for the across-seeds table).
