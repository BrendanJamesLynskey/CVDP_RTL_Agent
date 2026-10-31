# M3h report: the knowledge pack as Claude Code's own skills, with Haiku 5.5

**Status: skeleton (2026-10-31). The scored sweeps have not run; every number below is TODO.** Pre-registered in
[`m3h/preregistration.md`](m3h/preregistration.md), committed (TODO commit) before the first scored dispatch. The
smoke runs are in [`m3h/smoke.md`](m3h/smoke.md). The rules from the M1 report still apply: the LLM never produces a
score or a label, and the hidden tests are CVDP's. Nothing is billed per call on the plan, so there is no
provider-reported cost; Claude Code's own API-rate estimate is shown apart, as a guide to plan usage only.

The pack is private. This report names it only by tag and manifest hash, and names its skills, never quotes them.

## In short

- **Primary, held-out set:** S2 − A = TODO points [TODO, TODO] (TODO better, TODO worse, TODO same; sign test p = TODO).
- **Development set (the 86):** S2 − A = TODO [TODO, TODO]; the 79-problem view TODO [TODO, TODO].
- **Decision (pre-registered rule):** TODO.
- **Did Haiku use the pack?** S2 loaded at least one pack skill in TODO% of problem-runs (S1: TODO%); first load at
  turn TODO (median). S2c: TODO (run only if S2's rate was under 25%).

## Setup

| Arm | Sweep inputs | Skills installed |
|---|---|---|
| A | `harness=claudecode`, `model=claude-haiku-5-5` | none (Claude Code's bundled skills only) |
| S1 | A + `skill_pack=v1.0` | 15 (`v1.0`, manifest `7ba7b4b3…`) |
| S2 | A + `skill_pack=v2.0` | 25 (`v2.0`, manifest `e405fe31…`) |
| S2c (conditional) | S2 + `skill_hint=true` | as S2, plus the one-line user `CLAUDE.md` |

Claude Code 2.1.310, 60 turns at most, 480 s wall cap, `ubuntu-24.04-arm`, 4 threads; agent image TODO; harness
`8e894cf`, dataset revision `5b807d9`.

## Runs

| Set | Arm | Seed | Run | Problems | Valid rows | Rate-limited (rerun) | Passed |
|---|---|---|---|---|---|---|---|
| held-out | A | 1–3 | TODO | 100 | TODO | TODO | TODO |
| held-out | S1 | 1–3 | TODO | 100 | TODO | TODO | TODO |
| held-out | S2 | 1–3 | TODO | 100 | TODO | TODO | TODO |
| the 86 | A | 1–3 | TODO | 86 | TODO | TODO | TODO |
| the 86 | S1 | 1–3 | TODO | 86 | TODO | TODO | TODO |
| the 86 | S2 | 1–3 | TODO | 86 | TODO | TODO | TODO |
| the 86 | ladder Haiku (reference only) | 1 | 2026-10-26 ladder | 86 | 86 | — | 57 |

Leak guard: TODO (passed on every sweep / which failed and why). Plan usage before and after each sweep: TODO.

## Results

### Primary: S2 − A on the held-out set

| | A | S2 | S2 − A [95% CI] | better / worse / same | sign test p |
|---|---|---|---|---|---|
| pass@1, 100 problems × 3 runs | TODO | TODO | **TODO** | TODO | TODO |

Realised half-width TODO points (pre-registered power: about 80% to detect +5.3).

### Secondary: S1 − A and S2 − S1 on the held-out set; all three on the 86 (development set)

| Set | Comparison | Effect [95% CI] | better / worse / same | sign test p |
|---|---|---|---|---|
| held-out | S1 − A | TODO | TODO | TODO |
| held-out | S2 − S1 | TODO | TODO | TODO |
| the 86 | S2 − A | TODO | TODO | TODO |
| the 86 | S1 − A | TODO | TODO | TODO |
| the 86 | S2 − S1 | TODO | TODO | TODO |
| the 79 | S2 − A | TODO | TODO | TODO |

### Decision

TODO.

### Skill use

| Arm, set | Problem-runs loading any pack skill | Median first-load turn | Distinct pack skills per loading run (mean) | Bundled skills loaded |
|---|---|---|---|---|
| S1, held-out | TODO | TODO | TODO | TODO |
| S2, held-out | TODO | TODO | TODO | TODO |
| S1, the 86 | TODO | TODO | TODO | TODO |
| S2, the 86 | TODO | TODO | TODO | TODO |
| A, both | — | — | — | TODO |

Per skill (loads, pass rate when loaded / not; descriptive only): TODO.

## Effort

| Arm, set | Median turns | Median wall s | Wall-cap stops | Tokens per problem-run (prompt incl. cache + completion) | Plan estimate total (guide only) |
|---|---|---|---|---|---|
| TODO | TODO | TODO | TODO | TODO | TODO |

## Caveats

TODO after the runs. Known in advance: one model (Haiku 5.5) on one harness; Claude Code's bundled skills are present
in every arm; the plan is not a stable meter; the 86 is a development set.
