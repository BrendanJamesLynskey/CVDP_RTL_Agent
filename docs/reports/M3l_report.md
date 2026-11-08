# M3l report: retrieved real-RTL examples in the agent's context, on our own API loop

**Status: SKELETON (2026-11-08). No scored sweep has run; every number below is TODO.**

- **Pre-registration:** [`m3l/preregistration.md`](m3l/preregistration.md). **Dry run of the retriever:**
  [`m3l/dry_run.md`](m3l/dry_run.md). **Smoke runs:** [`m3l/smoke.md`](m3l/smoke.md).
- Arms, all on `claude-haiku-5-5` (Anthropic Claude Haiku 5.5), `harness=apiloop`, billed to the API key:
  - **R:** M3j's arm R, reused (not rerun; request path byte-identical).
  - **E:** R plus the one or two closest real modules of the pack's reference layer, in the first user message
    (`fixed_checks=retrieved_examples skill_pack=v4.0`).

## In short

- **Primary: E − R on the held-out set = TODO** (TODO better, TODO worse, TODO same; sign test p = TODO): TODO.
- **Decision (M3j's rule): TODO.**
- **Retrieval:** TODO of 100 held-out problems and TODO of the 86 received an example (dry run: 3 and 13).
- **Cost:** TODO of API credit for all scored runs.

## Runs

| Arm | Set | Seed | Run | Passed |
|---|---|---|---|---|
| E | held-out | 1 | TODO | TODO |
| E | held-out | 2 | TODO | TODO |
| E | held-out | 3 | TODO | TODO |
| E | the 86 | 1 | TODO | TODO of 86 |
| R (M3j, reused) | held-out / the 86 | 1-3 / 1 | 41673126672, 41709498919 / 41694588753 + 41713923011 | 53, 57, 54 / 58 |

## Results

### Primary: E − R (held-out, paired by problem)

| | R | E | E − R [95% CI] | better / worse / same | sign test p |
|---|---|---|---|---|---|
| pass@1, 100 problems × 3 runs | 164/300 = 54.7% | TODO | TODO | TODO | TODO |

### Secondary (exploratory, no correction)

- Problems that received an example against those that did not: TODO.
- Label shift on the 86: TODO.
- Tokens and turns: TODO.
- Copying of the shown code into the final `rtl/`: TODO.

## Keeping the examples clean

Repo deny-list removed 49 of 86 entries (37 remain); the overlap rule removed 0 pairs on the 186 dry-run problems; TODO
for the scored runs (`examples_withheld_overlap`).

## Leak guard

TODO: result on each scored run.

## What this shows and does not show

TODO.
