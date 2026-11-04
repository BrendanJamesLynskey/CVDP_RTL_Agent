# M3k report: a pre-submit interface check and a timing-claims turn, on our own API loop

**Status: SKELETON. Nothing has been scored; every number is TODO.** The planner dispatches the scored runs after
PR #54 merges.

- **Pre-registration:** [`m3k/preregistration.md`](m3k/preregistration.md). **Replay of K on M3j's R:**
  [`m3k/replay.md`](m3k/replay.md). **Smoke runs:** [`m3k/smoke.md`](m3k/smoke.md).
- Arms, all on `claude-haiku-5-5`, `harness=apiloop`, billed to the API key: **R** (M3j's arm R, reused), **K**
  (`fixed_checks=presubmit_iface`), **T** (`fixed_checks=timing_claims`).

## In short

- **Primary: K − R on the held-out set = TODO [TODO, TODO]** (TODO better / TODO worse / TODO same; sign test p = TODO).
- **Primary: T − R on the held-out set = TODO [TODO, TODO]** (TODO / TODO / TODO; p = TODO).
- Decision (Bonferroni over two, 97.5% intervals): K TODO; T TODO.
- Cost: TODO of API credit (Console before TODO, after TODO).

## Runs

| Arm | Set | Seed | Run | Passed |
|---|---|---|---|---|
| K | held-out | 1 / 2 / 3 | TODO | TODO |
| T | held-out | 1 / 2 / 3 | TODO | TODO |
| K | the 86 | 1 | TODO | TODO |
| T | the 86 | 1 | TODO | TODO |
| R (M3j, reused) | held-out / the 86 | 1-3 / 1 | 41673126672, 41709498919 / 41694588753 + 41713923011 | 53, 57, 54 / 58 |

## Results

### Primary (held-out, paired by problem)

TODO: `tools/ablate.py` table, K − R and T − R.

### Secondary (the 86, descriptive)

TODO: label shift. Does K cut `compile_fail_own` + `signal_missing_hidden`; does T cut `tests_failed_no_selfcheck`.

### K's round trips, tokens, turns

TODO: `presubmit_findings_n`, `presubmit_rounds`, `presubmit_final_findings_n`; tokens per run against R; `timing_claims_n`.

### Cost

TODO.

## What it means

TODO.

## What it cannot show

- One model (Claude Haiku 5.5), one loop, one benchmark.
- K's filters were chosen after looking at the held-out replay (see [`m3k/replay.md`](m3k/replay.md)).
- At 3 runs on 100 problems, effects under about 4-5 points read as no detectable effect.
