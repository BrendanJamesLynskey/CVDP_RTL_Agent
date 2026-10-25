# M3b confirming run: result

The test, its data and its decision rule were fixed in advance in [`confirm_preregistration.md`](confirm_preregistration.md) (commit 18c2c2d, before any run was dispatched).

## Verdict: confirmed

**B − A = +4.7 points [+1.0, +8.5]** (paired bootstrap over the 86 problems, 6 new runs per arm, seeds 4 to 9). The interval excludes zero and the effect is positive, so by the pre-registered rule the harness effect is **confirmed**: on these problems and this model, the Deep Agents harness solves more than the LangGraph agent.

How strong: the exact sign test on the problems that changed is p = 0.093 (16 better, 7 worse, 63 the same). The pre-registered rule used the interval, and the sign test was not part of it; it is reported so the reader can see the evidence is moderate, not overwhelming. The size matches M3b's estimate (+4.3 on seeds 1 to 3), on data that did not suggest the hypothesis.

| Arm | Runs | Pooled pass@1 | $/solved | Median wall |
|---|---|---|---|---|
| A (LangGraph) | 6 | 299/516 = 57.9% | ≥ $0.0126 | 51 s |
| B (Deep Agents) | 6 | 323/516 = 62.6% | ≥ $0.0119 | 72 s |

Full table: [`confirm_paired_eval86.md`](confirm_paired_eval86.md). Run CSVs: [`confirm_runs/`](confirm_runs/) (name = arm, seed, Actions run id). One call in each arm had an unreported cost, so costs are lower bounds. Total spend $7.60.

## Secondary (descriptive, as pre-registered)

The mechanism M3b described repeats on the new runs:

| Over 6 runs | A | B |
|---|---|---|
| Failures with no self-written testbench (`tests_failed_no_selfcheck`) | 121 | 79 |
| Problems stopped by the round cap (`max_turns`) | 28 | 101 |

Deep Agents leaves fewer problems untested, and stops on its 22-round cap far more often. It sends about 5× the tokens at about the same cost (provider caching, inferred).

## Limits

One model (`openai/gpt-6-luna`), one problem set (86 free agentic CVDP problems), one Deep Agents version (0.7.32). The memory arms (C, D) were not re-run; the memory finding (no detectable effect) stands as M3b reported it.
