# M3h report: the knowledge pack as Claude Code's own skills, with Haiku 5.5

**Status: DONE (2026-11-02). Decision: null.** The held-out phase ran on 2026-10-31 and the phase on the 86 on
2026-11-02, once per arm (see the deviation under "The 86"). Neither shows an effect of the pack, so the
pre-registered rule is not met and the pack is not adopted as a Claude Code feature.

- **Pre-registration:** [`m3h/preregistration.md`](m3h/preregistration.md). It was amended twice before any
  pack-arm result was read, and both amendments are in the file:
  - the first, `9bcbe93`, made the pack arms hinted;
  - the second, `958dc48`, changed the leak guard.
- **Where the sweeps ran from:** the first scored sweep (A1) ran from `9bcbe93`. The other 9 ran from `958dc48`,
  after the leak-guard change. That change touched only the workflow's guard step and the guard tool; the agent
  image (`be5c24f`) and the run path were the same for all 10.
- **Smoke runs:** [`m3h/smoke.md`](m3h/smoke.md).

The rules from the M1 report still apply: the LLM never produces a score or a label, and the hidden tests are
CVDP's. Nothing is billed per call on the plan, so there is no provider-reported cost: the `≥$0.0000` and "300
unreported" cells in `ablate.py`'s tables mean only that.

The pack is private. This report names it only by tag and manifest hash. It names the skills but never quotes them.

## In short

**Held-out set (the primary):**

- **Primary: S2c − A = −2.0 points [−6.3, +1.7]** (9 better, 12 worse, 79 same; sign test p = 0.66). That is no
  detectable effect. S2c (`v2.0` plus the one-line hint) passed 56.3% and A 58.3%. The interval rules out a gain of
  more than 1.7 points.
- **S1c − A = +1.3 [−2.7, +5.7]** (13 / 9 / 78, p = 0.52): no detectable effect.
- **S2c − S1c = −3.3 [−7.0, −0.0]** (3 / 11 / 86, p = 0.057). This is a secondary comparison and the interval only
  just excludes 0, so by the interval rule `v2.0` did slightly worse than `v1.0` under the same hint. It is one of
  several secondaries, with no correction for multiplicity, and the 86 has not run.
- **Did Haiku use the pack?**
  - With the hint, almost always: S1c loaded a pack skill in 300 of 300 problem-runs, and S2c in 299 of 300. The
    first load was at turn 1 (median).
  - Without the hint, almost never: the single S2 run loaded one in 3 of 100.
  - `spec-reading` was loaded in 93% (S1c) and 88% (S2c) of problem-runs.
- **Using the pack costs effort.** Median turns went from 6 (A) to 12 (S1c) and 11 (S2c). Median wall time went
  from 32 s to 46–48 s, and prompt tokens rose by about 46–51% per problem-run.
- **The answers seldom reproduce skill text.** One S2c problem-run out of 300 held 80 bytes of
  `valid-ready-handshake` in its own RTL, and the guard withheld that file. No other pack-arm problem-run did, and
  neither did any A problem-run (the control).

**The 86 (development set, one run per arm, descriptive):**

- **S2c − A = +3.5 [−2.3, +9.3]** (5 / 2 / 79); **S1c − A = −1.2 [−7.0, +4.7]** (3 / 4 / 79). Both are no detectable
  effect. S2c − S1c = +4.7 [−2.3, +11.6] (7 / 3 / 76), the opposite sign to the held-out secondary, and also null.
  The 79 view agrees (S2c − A +3.8 [−2.5, +10.1]; S1c − A −1.3 [−7.6, +5.1]).
- Skills were loaded in 86 of 86 problem-runs in both pack arms. Effort rose again (median turns 11 to 17.5 and 18).
- **Decision: null.** The held-out primary is −2.0 [−6.3, +1.7]. The 86 cannot turn that into a finding.

## Setup

| Arm | Sweep inputs | Skills installed | Held-out runs |
|---|---|---|---|
| A | `harness=claudecode`, `model=claude-haiku-5-5` | none (Claude Code's 19 bundled skills only, as in every arm) | 3 |
| S1c | A + `skill_pack=v1.0`, `skill_hint=true` | 15 (`v1.0`, manifest `7ba7b4b3…`), plus the hint | 3 |
| S2c | A + `skill_pack=v2.0`, `skill_hint=true` | 25 (`v2.0`, manifest `e405fe31…`), plus the hint | 3 |
| S2 | A + `skill_pack=v2.0` | 25, no hint | 1 (descriptive) |

The hint is a user `CLAUDE.md` with the line "RTL design skills are installed; check them before you start."
**Caveat:** a hinted arm differs from A by the pack *and* that line.

Common settings: Claude Code 2.1.310, 60 turns at most, 480 s wall cap, `ubuntu-24.04-arm`, 4 threads; agent image
`be5c24f`; harness `8e894cf`; dataset revision `5b807d9`.

The held-out set is M3g's frozen 100 (`tools/m3g_heldout_ids.txt`). The sweeps ran one at a time, interleaved as
pre-registered (A1, S1c1, S2c1, A2, …, S2c3, then S2), on 2026-10-31.

## Runs (held-out)

| Arm | Seed | Run | Passed | Rate-limited | Leak guard | Files withheld |
|---|---|---|---|---|---|---|
| A | 1 | [41188919982](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41188919982) | 57 | 0 | (no pack) | — |
| S1c | 1 | [41194367820](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41194367820) | 61 | 0 | passed | 0 |
| S2c | 1 | [41197391377](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41197391377) | 57 | 0 | passed | 0 |
| A | 2 | [41200241988](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41200241988) | 56 | 0 | (no pack) | — |
| S1c | 2 | [41202961897](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41202961897) | 60 | 0 | passed | 0 |
| S2c | 2 | [41206368857](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41206368857) | 58 | 0 | passed | 1 |
| A | 3 | [41209572395](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41209572395) | 62 | 0 | (no pack) | — |
| S1c | 3 | [41212360117](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41212360117) | 58 | 0 | passed | 0 |
| S2c | 3 | [41215897687](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41215897687) | 54 | 0 | passed | 0 |
| S2 | 1 | [41219406975](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41219406975) | 57 | 0 | passed | 0 |

**Notes on the runs:**

- **The first S1c1 dispatch** ([41191246494](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41191246494))
  failed at the leak guard and uploaded nothing. The guard found one 80-byte match of `valid-ready-handshake` in
  the model's own RTL for `cascaded_adder`. The guard was then changed (the second amendment), and S1c1 was rerun.
  No result of the first dispatch was ever available.
- **Rate limits:** no problem was rate-limited, so `tools/m3h_merge.py` had nothing to merge.
- **Checks on the published material:**
  - Every pack sweep's guard passed in CI.
  - I downloaded every artifact and scanned it again locally. I did the same for the public job logs of the
    `v2.0` sweeps and for every CSV committed here: none holds a window of `v2.0`'s private text.
- **Plan `/usage`** (week, all models): 68% before A1, 80% after S2.
- **Status of this section:** the 86 phase's runs are listed under "The 86" below.

The run CSVs are in [`m3h/runs/`](m3h/runs/), with each pack sweep's `withheld_*.csv`. The tables are made by
[`m3h/analyze.sh`](m3h/analyze.sh) from the committed tools.

## Results (held-out set)

### Primary: S2c − A ([`m3h/heldout_paired.md`](m3h/heldout_paired.md))

| | A | S2c | S2c − A [95% CI] | better / worse / same | sign test p |
|---|---|---|---|---|---|
| pass@1, 100 problems × 3 runs | 175/300 = 58.3% | 169/300 = 56.3% | **−2.0 [−6.3, +1.7]** | 9 / 12 / 79 | 0.66 |

**No detectable effect.** The realised half-width, about 4.0 points, is close to the 3.7 assumed in the power
calculation. The interval rules out a gain of more than 1.7 points, and does not rule out a loss of up to 6.

### Secondary comparisons on the held-out set ([`m3h/heldout_paired.md`](m3h/heldout_paired.md), [`m3h/heldout_paired_S2c_S1c.md`](m3h/heldout_paired_S2c_S1c.md))

| Comparison | Effect [95% CI] | better / worse / same | sign test p | Read |
|---|---|---|---|---|
| S1c − A | +1.3 [−2.7, +5.7] | 13 / 9 / 78 | 0.52 | no detectable effect |
| S2c − S1c | −3.3 [−7.0, −0.0] | 3 / 11 / 86 | 0.057 | interval just excludes 0: `v2.0` slightly worse than `v1.0` under the same hint |

`v2.0` adds ten skills and a new index to `v1.0`. Under the hint, S2c loaded fewer pack skills per problem-run
than S1c (1.72 against 2.14). It used the new skills only on a few problem-runs:
`working-in-existing-code` 21 times, `minimal-change-modification` 17 and `hardware-algorithms` 9. The rest are in
the tables. The S2c − S1c difference is a secondary comparison, has no correction for the number of secondaries,
and its sign test is not significant. The 86 will show whether it holds.

### Decision

**Null.** The pre-registered rule needs the 86 to agree with a held-out gain. On the held-out set the primary
shows no gain (−2.0 [−6.3, +1.7]), so even a positive result on the 86 could not make this a finding. The 86 phase
ran for the development-set view (below). It shows no detectable effect either, so the decision stands.

### Skill use ([`m3h/tables_heldout.md`](m3h/tables_heldout.md))

| Arm | Problem-runs loading any pack skill | First-load turn, median [range] | Distinct pack skills per loading run | Pass rate, loading / not |
|---|---|---|---|---|
| S1c | 300 of 300 (100%) | 1 [1–3] | 2.14 | 59.7% / – |
| S2c | 299 of 300 (99.7%) | 1 [1–3] | 1.72 | 56.2% / 100% (1 run) |
| S2, no hint (1 run) | 3 of 100 (3%) | 1 [1–3] | 1.33 | 66.7% / 56.7% |

- **Most loaded:**
  - S1c: `spec-reading` 278, `fsm-design` 75, `reset-strategy` 62, `self-check-and-cocotb` 50.
  - S2c: `spec-reading` 265, `fsm-design` 59, `arithmetic-and-widths` 23, `working-in-existing-code` 21.
- **Bundled skills:** no arm loaded any of Claude Code's own bundled skills. For A this was counted from its kept
  streams.
- **The hint does the work.** Claude Code offers every pack skill in every pack run (`skills_listed` 15 or 25).
  Without the hint, Haiku seldom looks at them.
- **Per-skill pass rates (loaded against not) are descriptive only.** For example, `fsm-design` 36% against 68% in
  S1c mostly reflects which problems it is chosen for, as in M3g.

### Answers that reproduce skill text ([`m3h/copied_heldout.md`](m3h/copied_heldout.md); descriptive, added in the second amendment)

| Arm | Problem-runs whose own files hold ≥ 80 bytes of pack text | Skills |
|---|---|---|
| S1c | 0 of 300 | — |
| S2c | 1 of 300 | `valid-ready-handshake` |
| S2 (no hint) | 0 of 100 | — |
| A (control, no pack installed) | 0 of 300 | — |

Text a model reproduces is evidence of use, but it is rare here. Haiku applies the advice in its own words more
often than it copies idioms. The first S1c1 dispatch, which was not scored, had one such match on the same
problem.

## Effort (held-out; Claude Code's own counts, nothing billed per call)

| Arm | Turns: median (mean) | Median wall s | Wall-cap stops | Prompt tokens incl. cache per run (mean) | Completion tokens per run (mean) |
|---|---|---|---|---|---|
| A | 6 (6.9) | 32 | 0 | 167,423 | 10,156 |
| S1c | 12 (12.7) | 46 | 2 | 253,396 | 13,045 |
| S2c | 11 (11.7) | 48 | 1 | 244,171 | 12,612 |
| S2, no hint (1 run) | 7 (7.7) | 36 | 0 | 209,515 | 11,456 |

## Failure taxonomy (held-out, [`m3h/taxonomy_heldout.md`](m3h/taxonomy_heldout.md))

| Label | A | S1c | S2c | S2 (1 run) |
|---|---|---|---|---|
| tests failed (the taxonomy cannot see Claude Code's own testbench runs) | 94 | 89 | 100 | 33 |
| interface: `signal_missing_hidden` | 13 | 14 | 13 | 4 |
| `compile_fail_own` | 11 | 10 | 10 | 3 |
| `sim_incomplete` | 7 | 7 | 7 | 3 |
| `stopped_by_cap` | 0 | 1 | 1 | 0 |
| **all failures** | 125 of 300 | 121 of 300 | 131 of 300 | 43 of 100 |

The mix of failures barely moves. In particular, interface mismatches did not fall, although `spec-reading` was
loaded on nearly every problem-run.

## The 86 (development set)

**Deviation from the pre-registration (recorded in its amendments section too).** The pre-registration asked for 3
runs per arm on the 86. The phase was cut to **1 run per arm**. The reason was the weekly plan usage budget. The
planner made the decision after the held-out primary was known to be null (so it cannot have been chosen to favour a
result). One run per arm means the 86 numbers below are descriptive: they carry no repeat-to-repeat spread, and the
intervals cover only the sampling of problems.

Setup as for the held-out sweeps (Claude Code 2.1.310, `claude-haiku-5-5`, arm runner, 4 threads, `split=agentic`,
seed offset 0), run from `789145f` on 2026-11-02. The 86 are `tools/m3b_eval_ids.txt`. Each run covers 92 rows (6
more ids); the tables use the 86 only.

| Arm | Run | Passed (of 86) | Rate-limited | Leak guard | Files withheld |
|---|---|---|---|---|---|
| A | [41507899046](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41507899046) | 58 | 0 | (no pack) | — |
| S1c | [41522822846](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41522822846) | 57 | 0 | passed | 0 |
| S2c | [41532901632](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41532901632) | 61 | 0 | passed | 12 (7 problem-runs) |

The run CSVs and withheld lists are in [`m3h/runs/`](m3h/runs/) (`dev86_*`, `withheld_dev86_*`). The tables are made by
[`m3h/analyze.sh`](m3h/analyze.sh).

### Paired effects ([`m3h/dev86_paired.md`](m3h/dev86_paired.md), [`79`](m3h/dev79_paired.md), [`S2c − S1c`](m3h/dev86_paired_S2c_S1c.md))

| Comparison | 86 problems | better / worse / same | 79 view (7 benchmark-limited left out) | better / worse / same |
|---|---|---|---|---|
| S2c − A | +3.5 [−2.3, +9.3] | 5 / 2 / 79 | +3.8 [−2.5, +10.1] | 5 / 2 / 72 |
| S1c − A | −1.2 [−7.0, +4.7] | 3 / 4 / 79 | −1.3 [−7.6, +5.1] | 3 / 4 / 72 |
| S2c − S1c | +4.7 [−2.3, +11.6] | 7 / 3 / 76 | | |

Pass counts: A 58/86 (67.4%), S1c 57/86 (66.3%), S2c 61/86 (70.9%); on the 79, 58, 57 and 61 of 79. No interval
excludes 0 and no sign test is below 0.45. **The old ladder's Haiku run** (Claude Code with no pack, 57/86) is for reference only. Against A it reads −1.2
[−8.1, +5.8] (4 / 5 / 77; [`m3h/dev86_vs_ladder.md`](m3h/dev86_vs_ladder.md)): two plain runs of the same setup differ
by one problem, which is the run-to-run noise to keep in mind when reading the arms above.
The sign of S2c − S1c is opposite to the held-out secondary (−3.3), which is what chance alone would give with both
nulls.

### Skill use and effort on the 86 ([`m3h/tables_dev86.md`](m3h/tables_dev86.md))

| Arm | Problem-runs loading any pack skill | Distinct pack skills per run | Turns: median (mean) | Median wall s | Wall-cap stops | Prompt tokens per run (mean) |
|---|---|---|---|---|---|---|
| A | – | – | 11 (12.5) | 89 | 2 | 431,567 |
| S1c | 86 of 86 | 2.60 | 17.5 (17.5) | 100 | 4 | 456,353 |
| S2c | 86 of 86 | 2.72 | 18 (19.1) | 109 | 1 | 487,439 |

- `spec-reading` was loaded in 98.8% (S1c) and 79.1% (S2c) of problem-runs. S2c's new `working-in-existing-code`
  (24), `module-integration` (18) and `minimal-change-modification` (16) were used on the 86's modification-style
  tasks. Their pass rates when loaded (71%, 67%, 63%) are descriptive and not better than when not loaded.
- No arm loaded Claude Code's bundled skills.
- **Answers reproducing skill text** (the CSV column): A 0 and S1c 0 of 86; S2c 5 of 86 (6 of 92 rows), and the guard
  withheld 12 files (7 problem-runs, counting the 6 extra ids). The skills involved were `fifo-design` (3),
  `block-ciphers-in-hardware`, `bus-and-register-interfaces`, `fsm-design` and `self-check-and-cocotb` (1 each).
  The 86 are development tasks, and a copy of idioms from a skill is not a gain: it did not lift the pass rate.
- **Failures** ([`m3h/taxonomy_dev86.md`](m3h/taxonomy_dev86.md); `taxonomy.py` has no id filter, so it covers all
  92 rows per arm, the 6 extra ids included): A 34, S1c 35 and S2c 31 failed rows of 92. The mix is as in the
  held-out set; `tests_failed_no_selfcheck` is 22, 19 and 18.

## Caveats

- **The pack arms differ from A by the pack plus a one-line hint.** The unhinted S2 run shows that without the hint
  the pack is barely used (3%), so an unhinted comparison would mostly measure "not used".
- **Mid-phase change.** The guard change came between A1 and the other sweeps. It is workflow-only, with the same
  image and the same run path. A1 is kept.
- **One model and one harness:** Haiku 5.5 on Claude Code 2.1.310.
- **The plan is not a stable meter.** The held-out phase used about 12 points of the weekly limit for 10 sweeps.
- **One run per arm on the 86** (the deviation above), so the 86 view is descriptive.
- **The taxonomy is coarse here.** `tools/taxonomy.py` cannot see Claude Code's own self-checks, so every test
  failure is labelled "no own testbench".
