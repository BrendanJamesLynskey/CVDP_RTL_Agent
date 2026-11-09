# M3l report: retrieved real-RTL examples in the agent's context, on our own API loop

**Status: DONE (2026-11-09). Decision: no detectable effect; coverage is the main finding.** All four scored dispatches
ran to `completed/success`. Console cost reading: TODO (Console after).

- **Pre-registration:** [`m3l/preregistration.md`](m3l/preregistration.md), including its 2026-11-09 amendment, which
  replaced the held-out primary. **Dry run of the retriever:** [`m3l/dry_run.md`](m3l/dry_run.md). **Smoke runs:**
  [`m3l/smoke.md`](m3l/smoke.md).
- **Analysis:** [`m3l/analyze.sh`](m3l/analyze.sh) (run from the repo root) writes every table below into `m3l/`.
- Arms, all on `claude-haiku-5-5` (Anthropic Claude Haiku 5.5), `harness=apiloop`, billed to the API key:
  - **R:** a fresh control with the same settings (`fixed_checks=none`), run in parallel with E. M3j's R runs are not used.
  - **E:** R plus the one or two closest real modules of the pack's reference layer, in the first user message
    (`fixed_checks=retrieved_examples skill_pack=v4.0`).

## In short

- **Coverage first.** After the deny-lists, **37 of the pack's 86 reference entries** remain. They reach an example on
  **3 of 100 held-out problems (3%) and 13 of the 86 development problems (15%)**. Most tasks are not close to any of
  the 37 modules, so for most problems this arm is exactly arm R.
- **Primary: E − R over the 16 problems that receive an example = +6.2 points [−3.8, +16.2]** (4 problems better,
  1 worse, 11 the same; sign test p = 0.375): **no detectable effect.** Pooled over 5 runs per arm, R passed 53/80 (66.2%)
  and E 58/80 (72.5%). With 16 problems and 5 runs, only an effect of about 15 points or more could have been seen; the
  interval leaves open a loss of up to 3.8 points and a gain of up to 16.2.
- **The 16 are partly the development set** (13 of them): the retrieval constants were chosen on the 86 from coverage
  counts only, never from pass results, but the problems are the same ones. The 3 held-out problems are too few to say
  anything alone (E 6/15, R 3/15, all of the difference on one problem).
- **No win is claimed.** Three problems moved by 2 or more runs of 5, one of them (ethernet_mii_0006) the wrong way, and
  R's own pass counts are spread across 0 to 5 on several problems.
- **Cost:** estimated **$0.92 for E and $0.93 for R** (`api_cost_estimate_usd`, list price), $1.85 for the four dispatches.
  Examples cost nothing measurable: E used 7% fewer prompt tokens than R (13.46 M against 14.47 M) because it needed
  slightly fewer turns. Console reading: TODO (Console after).
- **Two E rows are `llm_error`** (`hdbn_codec_0001`, seeds 3 and 4, `agent_status=completed_no_patch`). Under the
  pre-registration they are not runs of the model; the primary table counts them as failures, as `ablate.py` does. The
  problem fails 0/5 in both arms, and leaving it out gives +6.7 [−4.0, +18.7] (4 / 1 / 10, p = 0.375,
  [`m3l/paired15.md`](m3l/paired15.md)). Not rerun, as pre-registered. No `rate_limited` or `run_budget_exhausted` rows.

## Runs

`runner=ubuntu-24.04-arm`, `threads=2`, `seeds=5`, `seed_offset=0`, `skill_pack=v4.0` for E. One dispatch per arm per
split, all `completed/success`.

| Arm | Set | Run | Rows | Passed | Guard (`run_budget_usd`) |
|---|---|---|---|---|---|
| E | 13 dev problems | [42545534466](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/42545534466) | 65 | 52 | 2.6 |
| R | 13 dev problems | [42545543795](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/42545543795) | 65 | 50 | 2.6 |
| E | 3 held-out problems | [42545553518](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/42545553518) | 15 | 6 | 0.6 |
| R | 3 held-out problems | [42545563498](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/42545563498) | 15 | 3 | 0.6 |

Run CSVs: [`m3l/runs/`](m3l/runs/). Every one of E's 80 rows carried at least one example (median 1,488 bytes).

## Results

### Primary: E − R (the 16 problems that receive an example, paired by problem)

| | R | E | E − R [95% CI] | better / worse / same | sign test p |
|---|---|---|---|---|---|
| pass@1, 16 problems × 5 runs | 53/80 = 66.2% | 58/80 = 72.5% | +6.2 [−3.8, +16.2] | 4 / 1 / 11 | 0.375 |

Tables: [`m3l/paired16.md`](m3l/paired16.md). Decision rule (M3j's): the interval includes 0, so no detectable effect.

### Per problem (passes out of 5, and the entry shown)

| Problem | Set | R | E | Entry shown |
|---|---|---|---|---|
| AES_encryption_decryption_0003 | dev | 5 | 5 | ot-aes-shift-rows |
| AES_encryption_decryption_0005 | dev | 5 | 5 | ot-aes-shift-rows, ot-aes-mix-columns |
| async_fifo_compute_ram_application_0001 | dev | 3 | 5 | ot-prim-fifo-async-gray-pointers |
| async_fifo_compute_ram_application_0006 | dev | 5 | 5 | ot-prim-fifo-async-gray-pointers |
| async_filo_0001 | dev | 5 | 5 | ot-prim-fifo-async-gray-pointers |
| axi4lite_to_pcie_config_0003 | dev | 0 | 1 | ot-prim-subreg |
| axis_to_uart_0004 | dev | 5 | 5 | ot-uart-rx |
| byte_enable_ram_0002 | dev | 5 | 5 | ot-prim-ram-1p |
| dual_port_memory_0004 | dev | 4 | 5 | ot-prim-ram-1p |
| ethernet_mii_0004 | dev | 4 | 4 | ot-prim-fifo-async-gray-pointers |
| ethernet_mii_0006 | dev | 4 | 2 | ot-prim-ram-1p |
| hdbn_codec_0001 | dev | 0 | 0 (2 `llm_error`) | ot-prim-pulse-sync |
| low_power_channel_0001 | dev | 5 | 5 | ot-prim-clock-gating, opennic-request-queue |
| copilot_MSHR_0001 | held-out | 0 | 0 | ot-prim-ram-1p |
| copilot_apb_dsp_unit_0001 | held-out | 0 | 3 | caliptra-ahb-to-reg-adapter |
| copilot_axi_register_0001 | held-out | 3 | 3 | ot-prim-subreg |

Full ids and the per-run table: [`m3l/tables16.md`](m3l/tables16.md). Seven of the 16 problems are 5/5 in both arms, so
they cannot move; the 16 only have room to move on about 9 problems.

### Dev and held-out, split (descriptive only)

| Set | Problems | R passes | E passes |
|---|---|---|---|
| held-out | 3 (15 runs) | 3 (20.0%) | 6 (40.0%) |
| dev | 13 (65 runs) | 50 (76.9%) | 52 (80.0%) |

### Secondary (exploratory, no correction)

- **Tokens and turns.** Prompt tokens 13.46 M (E) against 14.47 M (R); completion tokens 1.14 M against 1.15 M; turns
  median 7.0 against 6.5, mean 8.3 against 8.5; wall time per run median 58.7 s against 53.3 s, mean 79.5 s against 79.7 s.
  An example is small (about 1.5 KB) and is cached after the first call.
- **Estimated cost.** `api_cost_estimate_usd`: E $0.9183 (80 rows), R $0.9350 (80 rows). The provider-reported
  `cost_usd` is unreported on every row, so the estimate is the only figure.
- **Failure labels** ([`m3l/taxonomy16.md`](m3l/taxonomy16.md)): failures E 22, R 27. `tests_failed_no_selfcheck` 14 and
  14; `sim_incomplete` 5 and 5; `compile_fail_own` 0 and 4; `signal_missing_hidden` 1 and 3; `stopped_by_cap` 0 and 1;
  `llm_error` 2 and 0. The fewer own-compile failures under E (0 against 4) are the one visible shift; it is not
  tested and is exploratory.
- **Copying of the shown code into the final `rtl/`: not measured** (see known gaps).

## Keeping the examples clean

The point of the arm is to show real code without handing the agent the benchmark's own sources or the private pack's
prose. Five measures do that, and the first four are decided before any run:

1. **The reference layer cites exact sources.** Every entry records the upstream repo, path, pinned commit SHA, licence
   and the file's own copyright or SPDX line. At run start a tool fetches each file from the public repo at that SHA and
   checks that the entry's excerpt is byte-for-byte in it and its notice occurs in it; otherwise the entry is dropped and
   the drop printed. The sha256 of every fetched file is recorded in the run's `run.json`. Only real upstream code and its
   attribution are shown, never the pack's own prose (pattern, when-to-use, pitfalls).
2. **The repo deny-list.** Entries from the projects the benchmark's tasks are drawn from are never shown, on any run:
   the CV32E40P and CVA6 cores (both spellings of the organisation), Ibex and any repo with `ibex` in its name, and every
   `pulp-platform` repo. It removed **49 of 86 entries** (common_cells 27, ibex 8, axi 5, cva6 5, cv32e40p 4); **37
   remain**, mostly from OpenTitan (26), plus Caliptra (5), NVDLA (3) and the Xilinx open-nic-shell (3). This is also
   why coverage is low: the closest matches to many tasks were precisely the projects that had to go.
3. **The per-problem overlap deny-list.** For each problem, an entry is withheld when its source file shares a declared
   module, package or interface name with any of the problem's visible files, or when at least 10% of the source file's
   5-line code shingles appear in the problem's visible text. **It bound on no problem**: 0 entry-problem pairs on the
   186 problems of the dry run, and `examples_withheld_overlap` is 0 on all 80 scored E rows. The rule is in force and
   tested, but nothing the retriever picked overlapped a task.
4. **The leak guard.** `tools/leak_guard.py` adds the reference layer's own prose (README, sources file, entry titles,
   keywords and every section other than the excerpt and source block) to the private text it scans for in the work
   directory, outputs and step summary. A match anywhere else fails the job and uploads nothing. The public upstream code
   itself is not a secret. It ran on both E dispatches and passed; it is skipped on R, which has no pack.
5. **Withheld entries are logged per run.** The CSV carries `examples_withheld_repo` (49 on every E row) and
   `examples_withheld_overlap` (0 on every E row); the examples shown are in `examples_ids`, and the guard's own
   `withheld.csv` is empty on both E dispatches (header only).

## The run of nulls

M3l joins the other agent changes tried on this benchmark with one model and one loop: M3b's memory, M3g's knowledge
pack, M3h's skills, M3i's plain Claude Code, M3j's own loop and M3k's pre-submit check and timing turn, none of which
moved the pass rate detectably. The only confirmed gain remains **M3b's harness result, +4.7 [+1.0, +8.5]**. M3l differs
from the others in that it was a null of reach before it was a null of effect: written advice and code examples both
needed a task close enough to a reviewed module, and after decontamination few tasks are.

## What this shows and does not show

Shows: where the retriever fires (3% of held-out, 15% of dev problems), no large effect there (+6.2 [−3.8, +16.2]), and
that examples did not raise cost. Does not show: that retrieved examples never help; any effect on the other 84 held-out
and 73 dev problems (they received no example, so E equals R there by construction); anything about a larger or
differently chosen pool; an effect smaller than about 15 points on these 16. One model (Claude Haiku 5.5), one loop, one
benchmark, one retrieval rule and threshold, a pool of 37 modules.

## Known gaps

- 13 of the 16 problems are the development set; the 3 held-out problems alone are too few to read.
- Copying of the shown code into the final `rtl/` (shingles shared with the example) was not computed.
- The Console credit reading is TODO (Console after).
- Two E rows (`hdbn_codec_0001`) are `llm_error` and were not rerun.
