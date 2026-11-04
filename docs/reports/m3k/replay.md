# M3k: arm K's check replayed on M3j's arm R (offline, no model call)

Made by `tools/m3k_replay.py` on the final RTL of M3j's arm R runs: held-out runs 41673126672 (seeds 1-2) and
41709498919 (seed 3), dev-86 runs 41694588753 and 41713923011 (the rerun of the 30 guard-stopped problems; those 30
rows had no model call and are not checked). The task tree is rebuilt from `work.problems.jsonl` (prompt and context
files only; the reference patch and harness files in that file are never read), the given interface is read from it,
and the agent's own `agent_changes.patch` is applied to get its final RTL. K runs only when a run ended with `submit`.
Per-run rows: [`replay_heldout_R.csv`](replay_heldout_R.csv), [`replay_dev86_R.csv`](replay_dev86_R.csv).

## What the check does after the replay (and a caveat)

The first version used M3c's comparison as it was. On the held-out runs it fired on 53 of 300 problem-runs (29 failing,
24 passing), mostly `missing_module` (42): a module "named in the task" only by a file name or a phrase in prose
(`rtl/16qam_demapper.sv`, "The"). Those passed the hidden tests with a differently named module, so they are false
alarms. Three changes were made (`presubmit.precise`, `direction_findings`): `missing_module` only for a module the
original RTL defines or a visible testbench instantiates; `width` only when the given width comes from original RTL, a
module header or a visible testbench (not prose); a `direction` finding only for an input/output swap (not a doc's
"inout"). **These filters were chosen after looking at the held-out replay, on the same problems arm K will be scored
on.** The held-out replay below is therefore not an independent estimate of K's false-alarm rate; the dev-86 replay,
which the filters were not tuned on, is the fairer one.

## Result (final check)

| Set | Problem-runs | Checked (ended in `submit`) | Fires | On failing runs | On passing runs |
|---|---|---|---|---|---|
| Held-out, 3 seeds | 300 | 300 | 16 | 9 (5 distinct problems) | 7 (3 distinct problems) |
| Dev 86 (92 problems run) | 122 rows (30 not run) | 92 | 15 | 6 | 9 |

- **Held-out, the failing fires by label:** `tests_failed_no_selfcheck` 6, `compile_fail_own` 3. None was
  `signal_missing_hidden`. By kind over all 16 fires: spelling 4, width 3, missing_module 6, compile_error 2,
  missing_port 1. The 9 failing fires are 5 problems: `findfasterclock_0001` (3 seeds, `compile_fail_own`,
  `FindFasterClock` against `findfasterclock`), `run_length_0007` (3 seeds), `microcode_sequencer_0001`,
  `apb_gpio_0005` (missing ports), `serial_in_parallel_out_0014` (compile error).
- **Held-out, false alarms (passing runs):** `gf_multiplier_0005` (width read from a header, 3 seeds),
  `hamming_code_tx_and_rx_0011` (a module the original RTL defines, absent from the design; 3 seeds),
  `bus_arbiter_0004` (a compile error pyslang reports; 1 seed). 7 of 164 passing runs (4.3%).
- **Dev 86, the failing fires:** `tests_failed_no_selfcheck` 5, `signal_missing_hidden` 1. False alarms 9 of 58 passing
  runs (15.5%): missing ports/parameters read from prose, directions, one compile error.

**Compile findings.** `compile_error` fires only when pyslang and then Yosys (M3c's fallback) both fail to elaborate.
The replay machine had no Yosys, so its 2 held-out and 2 dev-86 `compile_error` fires are pyslang-only and may be
fewer in the agent image (which has Yosys); a pyslang error that Yosys accepts (an undeclared identifier, say) is not
reported.

**Ceiling for K.** A fire is not a fix: K can at most turn each failing fire into a pass. On the held-out set that is
at most 9 of 300 problem-runs = +3.0 points of pass@1 (5 problems, so it is a few-problem effect), against up to 7
passing runs that a false alarm could disturb (K lets the model argue the finding away in one line, but it may also
break a passing design). The brief's threshold, "fewer than 5 failing held-out problem-runs", is not met (9), but the
fires concentrate in 5 problems: **the planner may judge K too narrow to spend on** (resolution of the held-out design
is about 4 points; the ceiling is 3).
