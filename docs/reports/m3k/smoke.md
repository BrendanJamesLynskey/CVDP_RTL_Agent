# M3k smoke runs (plumbing, not results)

2026-11-04, `harness=apiloop`, Claude Haiku 5.5, `ubuntu-24.04-arm`, 4 threads, 1 seed, `run_budget_usd` 1. `m3g_smoke` = the 3
problems of `tools/m3g_smoke_ids.txt`; "dev 3" = `cvdp_agentic_queue_0001`, `_DES_0007`, `_gcd_0007` (picked because the
replay fired K on them). Estimates are `api_cost_estimate_usd` (list-rate estimate from tokens, summed over the run's rows).
None of this is a result. Runs 1-5 are at commit `2d7299c`; runs 6-7 after the fix noted below.

| # | Arm | Set | Run | Passed | Stop reasons | Estimate | Wall (job) |
|---|---|---|---|---|---|---|---|
| 1 | K (`presubmit_iface`) | m3g_smoke | 41743143148 | 2/3 | submit x3 | $0.0146 | 2.5 min |
| 2 | T (`timing_claims`) | m3g_smoke | 41743146634 | 2/3 | submit x3 | $0.0157 | 2.3 min |
| 3 | R (`fixed_checks=none`), one problem | m3g_smoke | 41743149204 | 1/1 | submit | $0.0026 | 1.7 min |
| 4 | K | dev 3 | 41743152539 | 1/3 | submit x3 | $0.0374 | 3.0 min |
| 5 | T | dev 3 | 41743155178 | 1/3 | submit x3 | $0.0538 | 4.1 min |
| 6 | K (after the fix) | dev 3 | 41743894659 | 1/3 | submit x3 | $0.0323 | 4.9 min |
| 7 | K (after the fix) | m3g_smoke | 41743898276 | 2/3 | submit x3 | $0.0089 | 2.0 min |

(Job wall includes image pull/build and the dataset download; per-problem wall times are 10-195 s in `wall_time_s`.)
Total about $0.17 of estimated API credit. No `run_budget_exhausted`, `rate_limited` or `llm_error` row in any run.

Checked from the CSVs and the artifacts:

- **R's CSV shape is unchanged** (run 3): no `presubmit_*` or `timing_claims_n` column; its `run.json` has neither key;
  summary has no K/T key.
- **K ran and its findings are in the transcript.** `api_tools.jsonl` has one `presubmit` line per check (turn, findings,
  kinds, engine, round) and, when it fired, the message sent. Runs 4 and 6: `DES_0007` was told 4 missing ports
  (`i_valid`/`o_valid` of `des_enc`/`des_dec`, ports of the original RTL) twice and ended with the same 4 (failed);
  `queue_0001` was told `re_i` is an input where the given interface says output twice and kept it (failed). Both show the
  model overruling the finding; whether it was right is the report's question. `presubmit_rounds` was 2 in both, the cap.
- **Bug found by the smoke and fixed.** Run 4 told `gcd_0007` (passing) that 7 modules of the original RTL were
  "not in the design": with the Yosys fallback, `hierarchy -top` prunes modules the top does not use. K now never reports
  a module that any `rtl/` file declares (`presubmit.declared_modules`, test `test_k_declared_module_is_never_missing`);
  run 6 shows `gcd_0007` with 0 findings and 0 rounds. The replay (no Yosys on the replay machine) could not show this.
- **T's list is the first assistant turn.** `api_tools.jsonl`'s first line is `timing_claims` (turn 1, `claims_n` 14-21, the
  reply, redacted); `summary.json` has `timing_claims_n` and `switches.timing_claims`; the request that follows carries the
  list as the first assistant message and `Now carry out the task.` (unit test; the real replies quote the task and write
  "not stated").
- **Scoring:** every problem is scored (`pass` 0/1, a failure label on the failing ones).

API-cost estimate per sweep: see the pre-registration (about $0.5 per held-out dispatch).
