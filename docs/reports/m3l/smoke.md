# M3l smoke runs (plumbing, not results)

2026-11-08, branch `m3l-examples` at `5af7dec` (PR #57 head when dispatched), `harness=apiloop`, Claude Haiku 5.5
(`claude-haiku-5-5`), `fixed_checks=retrieved_examples skill_pack=v4.0`, `ubuntu-24.04-arm`, 4 threads, 1 seed, `run_budget_usd` 1.
Estimates are `api_cost_estimate_usd` (a list-rate estimate from tokens, summed over the run's rows). None of this is a result.

| # | Set | Run | Passed | Examples shown | Stop reasons | Estimate | Job wall |
|---|---|---|---|---|---|---|---|
| 1 | `m3g_smoke` (3 problems of `tools/m3g_smoke_ids.txt`) | [42535199092](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/42535199092) | 2/3 | 0 of 3 | submit x3 | $0.0130 | 2.1 min |
| 2 | 3 dev problems chosen because the dry run gives them an example: `async_filo_0001`, `byte_enable_ram_0002`, `AES_encryption_decryption_0005` (`split=agentic`, `ids=`) | [42535380417](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/42535380417) | 3/3 | 3 of 3 (4 modules) | submit x3 | $0.0396 | 4.4 min |

Per-problem wall times 25-144 s (run 2). No `run_budget_exhausted`, `rate_limited` or `llm_error` row. Total about $0.05 of estimated API credit.

Checked from the CSVs, `work.run.json` and the artifacts:

- **The pack was verified before any model call.** Every run's log has `skill pack v4.0: reference layer, 86 entries,
  MANIFEST.sha256 c36d5df5...: matches the pinned hash`, and `examples bundle v4.0: 86 entries in the index, 49 withheld by the
  repo deny-list, 0 dropped, 37 kept from 35 upstream files`. The upstream files were fetched from `raw.githubusercontent.com`
  on the runner; `work.run.json` holds `examples_files` (35 repo@sha:path to sha256 pairs), `examples_bundle_sha256` and
  `examples_pack`. The files fetched on the runner are the same as those read from the local clones
  (the same 35 file sums: `files sha256 63e2214b...` in the run log and in the local build).
- **The examples reached the first user message.** The artifact keeps no request record (only `api_tools.jsonl`), so this is
  read from the summary and the tool log: in run 2 each problem's `summary.json` has `examples_ids`, `examples_bytes` (2,403,
  3,050 and 1,196), a non-empty `examples_block_sha256` (the sha256 of the appended block), and `api_tools.jsonl` has one
  `examples` line with the ids, scores (0.671 and 0.601; 0.639; 0.625) and the sha256 of each shown upstream file. Those
  sums are the ones in `work.run.json`. The unit test `test_e_examples_reach_the_first_user_message_after_the_task` shows the
  block's place and that nothing else in the request differs from R's.
- **No example, no change** (run 1): `examples_ids` empty, `examples_block_sha256` empty, `examples_top_score` 0.33-0.39, so
  all three requests were R's. The `m3g_smoke` problems, like the held-out ones, have the specification in the prompt and no
  `docs/`, which is why the dry run gives held-out problems so few examples.
- **Leak guard passed** (both runs; the text below is run 1's log line): `leak guard: 187 file(s) scanned, no 80-byte window of the pack's private text in any of
  them (public text allowed: 11558687 bytes)`. The new `--reference` option was on, so the pack's reference prose and index
  text were among the secrets. The secret-shape check on the upload passed.
- **The artifact holds no pack prose.** The uploaded files contain the entry ids, scores and file sums only; searching them for
  the pack's section headings found nothing. The examples bundle is outside `work*` and was not uploaded.
- **Problems were scored** (harness `tests_passed` 2/3 and 3/3). Copying of a shown module into the design is the report's question, not checked here.
- **CSV columns.** Only the five arm-E columns were added (`examples_ids`, `examples_bytes`, `examples_withheld_repo` = 49,
  `examples_withheld_overlap` = 0, `examples_top_score`); M3h's skill columns were not added for this arm.

Cost: run 1 averaged $0.0043 per problem, run 2 $0.0132 (the three dev problems are longer: 17 turns for the FIFO problem).
R's repriced figures are $0.0048 per held-out problem-run and $0.0088 per problem on the 86, so E costs about R's.
**Expected per scored dispatch: about $0.5 for a held-out dispatch (100 problems, one seed), $0.85 to $0.9 for the 86;
guards at about 3x: `run_budget_usd` 1.6 for each held-out dispatch, 2.6 for the 86.**
