# M3g report: a frozen knowledge pack, loaded as skills

**Status: done (2026-10-30). No detectable effect.** Pre-registered in [`m3g/preregistration.md`](m3g/preregistration.md),
committed (`3b9aa61`) before the first scored dispatch; the held-out ids were frozen earlier still (`943cef9`). All 9
scored sweeps ran on 2026-10-30 from `3b9aa61` (the agent image built from `f5cff04`, the last commit touching
`agent/` or `docker/`), in three batches of 3, and all succeeded. Nothing in the agent, the pack, the ids or the
pre-registration was changed after the first scored dispatch; the analysis tool `tools/m3g_tables.py` and
[`m3g/analyze.sh`](m3g/analyze.sh) were added afterwards, and touch no run path. The rules from the M1 report still
apply: the LLM never produces a score or a label, every cost is provider-reported, and a missing cost is recorded as
unreported.

The tables are made from the run CSVs ([`m3g/runs/`](m3g/runs/)) by the committed tools (`ablate.py`, `taxonomy.py`,
`m3g_tables.py`, run by `m3g/analyze.sh`), nothing by hand. Harness `8e894cf`, dataset revision `5b807d9`.

## In short

- **Primary, on the held-out set: no detectable effect.** On 100 CVDP non-agentic problems nobody had inspected, luna
  with the pack (K) passes **52.0%** against **51.0%** without it (A): **K − A = +1.0 points [−2.7, +4.7]** (9 better,
  8 worse, 83 same; sign test p = 1). The interval rules out a gain of more than about 5 points.
- **The development set agrees: no gain.** On the 86 agentic problems, K scores 58.5% against M3d's arm A 60.9%:
  **K − A = −2.3 [−7.4, +2.3]** (11 / 12 / 63, p = 1). The 79-problem view: **−2.5 [−8.4, +2.5]**.
- **Decision (pre-registered rule): not a finding.** Neither set shows a gain. Like the M3b lessons memory, a pack of
  general design know-how in the prompt does not move luna's pass rate by a detectable amount.
- **The pack was used as designed.** The plan loaded skills in 552 of 558 problem-runs (3 in most), `spec-reading` in 98–100%
  of all runs and `self-check-and-cocotb` in 41–52%; the cap never cut anything. 18 names asked for in 558 problem-runs were near misses (for
  example `arbiters-and-encoders-and-muxes`) and were dropped by the exact-name rule.
- **It costs a little more.** On the held-out set K used +57% prompt tokens per problem-run and 21% more money
  ($0.0064 against ≥$0.0054 per solved problem). M3g cost **$3.84** for the 9 scored sweeps, **$3.89** with the smoke
  runs, against an estimate of $7.14.

## Setup

| Arm | Sweep inputs | What changes |
|---|---|---|
| A | (defaults) | nothing: M3c's arm A, byte-for-byte (golden test) |
| K | `skills=agent/cvdp_agent/skills/rtl_pack` | the plan sees the pack's `INDEX.md` and names up to 3 skills; their text (≤ 13,000 bytes) goes into every edit prompt |

- **The pack:** brief 18A's `rtl_pack`, 15 skills written from outside sources only by a writer barred from CVDP and
  this repo; manifest SHA-256 `e6ca1610…`, checked by a test and by the agent before use.
- **Held-out set:** 100 problems sampled (seed 20261030) from the 193 eligible cid002/003/004 problems of
  `cvdp_v1.1.0_nonagentic_code_generation_no_commercial.jsonl` (open tools, output an `rtl/` file the harness
  compiles, no design name or given file shared with the 92 agentic problems): RTL completion 42, spec to RTL 41,
  RTL modification 17. They were run through the agent in the harness's agentic format with one sentence naming the
  output file, and scored by their hidden tests. Fresh A and K, 3 runs each.
- **Development set:** M3b's 86 evaluation problems, read and analysed in depth before, so a result there is a
  development-set result. K for 3 runs, against M3d's arm A runs (40353853802, 40368004835, 40376808643).
- **Settings, both arms:** `openai/gpt-6-luna`, reasoning `default`, `ubuntu-24.04-arm`, 4 threads, $0.10 per
  problem, 10 turns, self-check and lint on, 480 s wall cap, a $2.00 guard per sweep.

## Runs

| Set | Arm | Seed | Run | Problems | Passed | Reported spend | Unreported calls |
|---|---|---|---|---|---|---|---|
| held-out | A | 1 | [41109382939](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41109382939) | 100 | 50 | $0.2665 | 0 |
| held-out | A | 2 | [41109399217](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41109399217) | 100 | 52 | $0.2829 | 0 |
| held-out | A | 3 | [41109414912](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41109414912) | 100 | 51 | $0.2719 | 1 |
| held-out | K | 1 | [41114032101](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41114032101) | 100 | 51 | $0.3361 | 0 |
| held-out | K | 2 | [41114048258](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41114048258) | 100 | 53 | $0.3352 | 0 |
| held-out | K | 3 | [41114063795](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41114063795) | 100 | 52 | $0.3255 | 0 |
| the 86 | K | 1 | [41118692095](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41118692095) | 86 | 50 | $0.6793 | 1 |
| the 86 | K | 2 | [41118707002](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41118707002) | 86 | 50 | $0.6926 | 0 |
| the 86 | K | 3 | [41118721524](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/41118721524) | 86 | 51 | $0.6527 | 4 |
| the 86 | A (M3d) | 1–3 | 40353853802, 40368004835, 40376808643 | 86 | 49, 52, 56 | $1.7592 | 4 |

No guard was reached (the largest sweep spent $0.69 of $2.00). Key usage $80.3328 before the first scored dispatch
(key check 41109310646) and $84.1755 after the last (41125121750): **$3.8427**, the same as the reported $3.8428,
so the 6 unreported calls cost about nothing.

## Results

### Primary: K − A on the held-out set ([`m3g/heldout_paired.md`](m3g/heldout_paired.md))

| | A | K | K − A [95% CI] | better / worse / same | sign test p |
|---|---|---|---|---|---|
| pass@1, 100 problems × 3 runs | 153/300 = 51.0% | 156/300 = 52.0% | **+1.0 [−2.7, +4.7]** | 9 / 8 / 83 | 1 |

**No detectable effect.** The realised half-width, 3.7 points, is narrower than the 4.3–4.5 pre-registered (the
held-out problems flip between runs less often than the agentic ones). The interval rules out a gain of more than
4.7 points; the pre-registered power to detect +6.5 points was about 80%.

By category (pooled over runs): RTL completion (cid002) 41.3% → 40.5%, spec to RTL (cid003) 60.2% → 63.4%, RTL
modification (cid004) 52.9% → 52.9%. No category stands out; these are descriptive.

### Development set: K − A on the 86 ([`m3g/dev_paired_eval86.md`](m3g/dev_paired_eval86.md), [`79`](m3g/dev_paired_eval79.md))

| View | A (M3d) | K | K − A [95% CI] | better / worse / same | sign test p |
|---|---|---|---|---|---|
| 86 problems | 60.9% | 58.5% | **−2.3 [−7.4, +2.3]** | 11 / 12 / 63 | 1 |
| 79 problems (7 benchmark-limited left out) | 66.2% | 63.7% | **−2.5 [−8.4, +2.5]** | 11 / 12 / 56 | 1 |

The development set does not show a gain either: its point estimate is slightly negative and its interval covers 0.

### Decision

By the pre-registered rule, a finding needs a held-out gain that the development set agrees with. The held-out
interval covers 0 and the development-set effect is at or below 0: **not a finding; no detectable effect of the
pack.**

### Failure taxonomy per arm ([`held-out`](m3g/taxonomy_heldout.md), [`86`](m3g/taxonomy_dev.md))

| Label | held-out A | held-out K | 86 A (M3d) | 86 K |
|---|---|---|---|---|
| tests failed, no own testbench | 103 | 95 | 55 | 52 |
| tests failed, own testbench passed | 5 | 11 | 16 | 14 |
| tests failed, own testbench failed | 3 | 0 | 2 | 7 |
| interface mismatch (`compile_fail_hidden` + `signal_missing_hidden`) | 26 | 26 | 14 | 17 |
| `sim_incomplete` | 9 | 10 | 5 | 5 |
| `stopped_by_cap` | 0 | 2 | 7 | 6 |
| `llm_error` / `no_edit` | 1 | 0 | 2 | 6 |
| **all failures** | 147 of 300 | 144 of 300 | 101 of 258 | 107 of 258 |

The pack shifts some held-out failures from "no own testbench" to "own testbench passed, hidden failed" (5 → 11):
the agent tested a little more often (rows with a self-check run 24.0% → 30.0%), but its own tests did not catch what
the hidden tests did. On the 86 the self-check share did not change (44.6% in both). Interface mismatches did not
fall in either set, although `spec-reading` (loaded almost always) says to copy names exactly.

### Skills loaded ([`held-out`](m3g/tables_heldout.md), [`86`](m3g/tables_dev.md))

| Skill | held-out loads (of 300) | pass when loaded / not | the 86: loads (of 258) | pass when loaded / not |
|---|---|---|---|---|
| `spec-reading` | 299 | 52.2% / 0% | 253 | 59.7% / 0% |
| `self-check-and-cocotb` | 156 | 60.3% / 43.1% | 105 | 59.0% / 58.2% |
| `fsm-design` | 84 | 32.1% / 59.7% | 67 | 41.8% / 64.4% |
| `arithmetic-and-widths` | 71 | 70.4% / 46.3% | 59 | 57.6% / 58.8% |
| `reset-strategy` | 66 | 56.1% / 50.9% | 28 | 71.4% / 57.0% |
| `sequential-and-combinational-coding` | 46 | 50.0% / 52.4% | 32 | 78.1% / 55.8% |
| `synthesisable-subset-and-parameters` | 40 | 47.5% / 52.7% | 57 | 73.7% / 54.2% |
| `valid-ready-handshake` | 29 | 27.6% / 54.6% | 19 | 52.6% / 59.0% |
| `pipelining-and-latency` | 18 | 83.3% / 50.0% | 49 | 59.2% / 58.4% |
| `counters-timers-and-edges` | 16 | 56.2% / 51.8% | 12 | 25.0% / 60.2% |
| `arbiters-encoders-and-muxes` | 15 | 40.0% / 52.6% | 5 | 100% / 57.7% |
| `bus-and-register-interfaces` | 13 | 23.1% / 53.3% | 5 | 20.0% / 59.3% |
| `clock-domain-crossing` | 11 | 18.2% / 53.3% | 20 | 50.0% / 59.2% |
| `fifo-design` | 10 | 40.0% / 52.4% | 17 | 76.5% / 57.3% |
| `memories-and-register-files` | 9 | 66.7% / 51.5% | 17 | 58.8% / 58.5% |

**Descriptive only.** The plan chooses the skills, so a skill's pass rate mostly reflects the problems it is chosen
for: `fsm-design` is loaded on FSM-heavy problems, which are harder, not because it hurts. Bytes loaded averaged
11,809 (held-out) and 11,572 (86) per problem-run, at most 12,554; the cap never cut a skill. In 6 problem-runs the
plan named no known skill. Unknown names: 10 on the held-out set and 8 on the 86, all near misses of a real name.

## Effort and cost

| Arm, set | $/problem | $/solved | median wall time | prompt tokens per problem-run (mean) | added prompt tokens (K − A) |
|---|---|---|---|---|---|
| A, held-out | ≥$0.0027 | ≥$0.0054 | 32 s | 8,286 | |
| K, held-out | $0.0033 | $0.0064 | 36 s | 12,979 | +4,693 (+57%) |
| A, 86 (M3d) | ≥$0.0068 | ≥$0.0112 | 74 s | 26,040 | |
| K, 86 | ≥$0.0078 | ≥$0.0134 | 56 s | 34,527 | +8,487 (+33%) |

(≥: some cost unreported, so a lower bound.) Turns and LLM calls per problem-run were slightly lower with the pack
(held-out 1.57 → 1.42 turns, 86: 2.55 → 2.45). The lower median wall time on the 86 compares a run on a different day
and image with M3d's, so it is not read as an effect.

**Spend:** smoke $0.0437, scored $3.8428, **M3g total $3.8865**, against an estimate of $7.14 ($10.72 with margin) and
a hard stop of $15. Key usage went from $80.2890 at the start of brief 18B to $84.1755 ($74.82 left of the $159 key
limit; the owner's ceiling is $150).

## Caveats

- **The held-out set is a different kind of problem.** They are CVDP's single-file copilot problems run through the
  agent, with one sentence added naming the output file; luna solves about half, with one or two turns on most. A null
  here does not show the pack would be null on harder, multi-file agentic problems, though the development set points
  the same way.
- **One pack, one way of loading it, one model.** The result is for this pack, loaded by plan-time choice into the
  edit prompts, on `gpt-6-luna`. It does not test a pack written for CVDP's conventions (deliberately excluded), a
  stronger model with the pack, or a different loading rule.
- **The 86-problem base is M3d's arm A**, run on an earlier agent image and day; the code path without a pack is
  the same (golden test).
- **Exact name matching** dropped 18 near-miss names in 558 problem-runs (at most 18 rows lost a skill). That is too few to hide an effect of
  the size the intervals rule out.
- **The index's own advice** (load `spec-reading` first and `self-check-and-cocotb` last) leaves one free choice under
  the 3-skill cap; the plan followed the first part almost always and the second about half the time.
- **Power:** the held-out interval rules out gains above about 5 points, not smaller ones.
- **Possible later arms**, listed in the pre-registration and not run: Opus + pack (does the pack help only weak
  models?), and Sonnet planning + pack (M3f's P with the pack).
