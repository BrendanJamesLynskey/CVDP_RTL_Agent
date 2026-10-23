# M1 report: the agent image

22 October 2026. Branch `m1-agent`, [pull request 1](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/pull/1).

## Done

- **The agent** (`agent/cvdp_agent/`, Python 3.12, LangGraph 1.2.16): `read_task → plan → edit → check → reflect →
  (edit | finalize)`. The file tool writes only under `rtl/`, `verif/`, `docs/` (and a scratch testbench under
  `rundir/agent_tb/`); every other path is refused in code, including `..`, absolute paths outside `/code` and
  symlinks that leave the allowed roots. Checks are deterministic tools the LLM chooses from: `iverilog -g2012`
  compile (always run; the best-edit rule needs it), `verilator --lint-only -Wall`, a Yosys read/synth check, and
  its own SystemVerilog or cocotb testbench, or an existing one under `verif/`. Tool output is cut down in code
  (errors and warnings first, then the tail, at most 2,500 characters) before the LLM sees it.
- **Stop rules**, checked in code before every step: turn cap (default 10), per-problem budget in USD (default
  $0.10, provider-reported cost only), a call whose cost was not reported (`cost_unreported`), wall-time cap
  (default 480 s, under the harness's 600 s agent timeout; checks are cut to the time left, finalize has 30 s of
  its own). On any stop, on `give_up` and on a crash, the agent keeps the last edit that compiled, writes its
  summary and ledger entry, and exits 0.
- **Switches** for the M3 ablations: `CVDP_SELF_CHECK`, `CVDP_LINT`, `CVDP_MAX_TURNS`, `CVDP_BUDGET_USD` (and
  `CVDP_WALL_S`).
- **Providers**: `fake` (scripted, deterministic) and `openrouter` (`ChatOpenAI` with
  `base_url=https://openrouter.ai/api/v1`, `usage: {include: true}`). Cost per call is `usage.cost`; if that is
  missing the agent asks the generation endpoint; if that has nothing either, the call is recorded with cost `null`
  and counted in `cost_unreported_calls` (so is a call that errored or timed out, which may still be billed), and
  the problem stops. No cost is ever estimated.
- **Outputs** per problem in `rundir/agent_out/`: `trace.jsonl` (every LLM call: node, model, prompt and completion
  tokens, cost, latency, generation id, decision, the completion cut to 3,000 characters; every tool call: command,
  exit code, output cut to 4,000 characters) and `summary.json`. Every string is redacted before it is written
  (`sk-or-…`, `Bearer …`, `Authorization…`, and the literal key value). Request headers are never traced.
  **Confirmed:** `rundir/` is kept by the harness, so these land in
  `work/<cvdp_agentic_name>/harness/<n>/rundir/agent_out/` after the harness has run its tests (checked in local
  runs; in Actions the sweep's upload step found them, 15 files for 2 problems).
- **Images** (`.github/workflows/images.yml`): `ghcr.io/brendanjameslynskey/cvdp-sim:8e894cf` built from the
  pinned harness's `docker/Dockerfile.sim`, and `ghcr.io/brendanjameslynskey/cvdp-rtl-agent:<sha>` on top of it
  (`<sha>` is the last commit that changed `agent/` or `docker/`). Each is built natively on `ubuntu-24.04` and
  `ubuntu-24.04-arm` and joined with `docker buildx imagetools create`; no QEMU. The sim image is built once: the
  job skips an arch whose image is already in GHCR (`rebuild_sim` forces it).
- **M0 workflow** now pulls the GHCR sim image and tags it `nvidia/cvdp-sim:v1.0.0` (`build_sim: true` builds it
  from source as before), and uploads the per-test logs (`reports/*.txt`).
- **Results tools**: `tools/collect.py` (raw_result.json + each summary.json → one CSV row per problem, with the
  `amba` flag), `tools/table.py` (pass@1 with a Wilson 95% interval, $/problem, $/solved problem, median wall time,
  by category and for the AMBA slice; markdown), `tools/amba_ids.txt` (the AMBA slice), `tools/pick_ids.py` and
  `tools/m1_ids.txt` (the seeded 10-problem sample), `tools/sweep.sh` (what the sweep workflow runs; also runs
  locally).
- **Sweep workflow** (`.github/workflows/sweep.yml`): dispatch inputs `model`, `split`, `ids`, `budget_usd`,
  `max_turns`, `self_check`, `lint`, `threads` (default 2), `runner`. Pulls both images from GHCR, runs the
  harness, collects, tabulates into the job summary and uploads the work directory (per-test logs,
  `raw_result.json`, `report.json`, every `agent_out/` and `agent_tb/`, each `agent_changes.patch`). The key
  reaches the agent only through `CVDP_AGENT_ENV`; the job fails if anything key-shaped is in the work directory
  before upload. On `pull_request` it is a smoke run with the `fake` provider on 2 problems.
- **Whole-run spend guard**: each agent writes its cost to a ledger directory shared through
  `CVDP_AGENT_MOUNTS`; an agent that starts after the ledger has passed the guard (`run_budget_usd`, or
  `budget_usd × problems × 1.2`) stops before its first LLM call (`stop_reason: run_budget_exhausted`; the problem
  is scored as the harness finds it). For the guard only, each call with unreported cost is charged the per-problem
  budget; reported cost stays separate.
- **Tests** (`tests/`, 52, run on every push and pull request by `.github/workflows/tests.yml`): each stop rule,
  path refusal, the budget cap, the best-edit-kept rule, each switch, unreported cost staying `null`, the ledger
  guard, the exit-0 rule; trace redaction (a fake key printed by a real tool never reaches the trace); `collect.py`
  and `table.py` on a fixture work directory shaped like a real `raw_result.json`; one test that runs real Icarus;
  the README mermaid diagram against the compiled graph. No test needs an LLM.

## How it was verified

CI runs on this branch (status from the Actions API, the same fields `gh run view <id> --json status,conclusion`
prints):

| Run | Workflow | What it shows | status, conclusion |
|---|---|---|---|
| [39861781904](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39861781904) | Images | `81a591b` push: sim image built natively on x86-64 and Arm64 and pushed (about 19 min), joined; agent image built on both and joined | completed, success |
| [39864535195](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39864535195) | Images | `e030868` push: sim image found in GHCR and skipped on both arches; agent image rebuilt and joined (2 min) | completed, success |
| [39867108886](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39867108886) | Tests | `11168e9` push: pytest (the Icarus test runs here: the workflow installs Icarus) | completed, success |
| [39862078105](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39862078105) | Sweep (PR smoke) | `81a591b`: `fake` provider on 2 problems, end to end; the sim image was not in GHCR yet, so it built from source (12 min) | completed, success |
| [39867112972](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39867112972) | Sweep (PR smoke) | `11168e9`: the same, pulling the sim image from GHCR (1 min) | completed, success |
| [39864345025](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39864345025) | Sweep (dispatch) | `fake` model on 1 problem, both images pulled from GHCR | completed, success |
| [39864754142](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39864754142) | Sweep (dispatch) | **real model in Actions**: `anthropic/claude-haiku-5.5` on 2 problems (`lfsr_0001`, `axis_to_uart_0001`), Arm64 runner: 2/2 passed, $0.0093; the key reached the agent only through `CVDP_AGENT_ENV`, and the pre-upload check found no key in the work dir | completed, success |
| [39867112437](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39867112437) | M0 harness | agentic split, x86-64, sim image pulled from GHCR: golden 1/1, null agent, per-test logs uploaded and classified (10 min, against 23 min when it built the image) | completed, success |
| [39867109124](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39867109124) | M0 harness | heavy split, x86-64, the same (10 min) | completed, success |
| [39864341750](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39864341750) | M0 harness | agentic split on Arm64 with the GHCR multi-arch image (6 min, against 18 min at M0) | completed, success |

Local, in this session (Docker 29.9 with the daemon started by hand):

- The simulation image built from the pinned harness, and the agent image on it.
- The null agent through the harness on 2 problems, to get a real `raw_result.json` for the test fixture.
- The `fake` agent through the harness on the 2 smoke problems with `tools/sweep.sh`: both scored, both
  `agent_out/` present in the work dir after the tests ran, `tools/smoke_check.py` passes.
- The generated `docker-compose-agent.yml` lists the forwarded variables by name only (no values).
- The real-tool test (Icarus compile, a self-checking testbench passing and then catching a bug) inside the agent
  image.

**The M0 gap: are null-agent failures genuine test failures?** On the agentic split, yes, all of them. On the
heavy split, yes for 72 of 75 problems; 3 are not shown to be (below).

`tools/log_check.py` now reads every per-test log the harness writes and sorts it into `tests_failed` (pytest
ran the hidden tests and they failed), `build_failed` (the tests ran but the design did not compile; the compiler's
own message is taken from `rundir/sim.log` or `build.log`), `harness_error` (no pytest session) or `passed`. The
M0 workflow prints this into its job summary. From runs 39867112437 and 39867109124 (null agent, pinned harness
and dataset):

| Split | Per-test logs | tests_failed | build_failed | harness_error | passed |
|---|---|---|---|---|---|
| agentic (92 problems) | 97 | 36 | 61 | 0 | 0 |
| heavy (75 problems) | 81 | 54 | 19 | 8 | 0 |

- **Agentic split: every null failure comes from the hidden tests run against the unedited tree**; no missing
  file, no harness error. An example `tests_failed` log
  (`AES_encryption_decryption/reports/12.txt`): cocotb runs `test_aes_decrypt`, `TESTS=1 PASS=0 FAIL=1`,
  `ERROR: Failed 1 of 1 tests.` The `build_failed` logs are what an unedited tree should give: the most common
  compiler messages are `Unable to find the root module "<name>"` for the module the task asks the agent to write
  (`axis_to_uart_tx`, `des3_enc`, `async_fifo`, …), plus 11 × `Preprocessor failed with 1 errors` (an include the
  problem's files do not yet provide, by all appearances; the summary does not show which file, so this is not
  confirmed one by one). In 8 logs Icarus segfaulted after failing to find the root module; the failure is the
  same, the segfault is a tool quirk. No log shows a missing bundle or a harness error. Locally, the null agent on
  `lfsr_0001` and `barrel_shifter_0002` gives the same picture (RTL compiles, cocotb assertions fail:
  `LFSR did not initialize correctly, got 00000001, expected 170`).
- **Heavy split: 73 of 81 logs are genuine; 8 are not shown to be.** 54 are test failures (e.g.
  `2dconv-FPGA/reports/9.txt`: `AssertionError: [MAIN C003] DUT=0 != Exp=-4096`). 19 are build failures with real
  compiler messages: a missing root module the task asks for (`xcvr_ctrl`, `usb`, `uart_tx`, `rvx`, …), the
  seeded bug itself (`syntax error` in `in_fifo.v`, `phy_rx.v`, `cv32e40p_load_store_unit.sv`; `can not select
  part of scalar` in `rvx.v`), or a port or parameter the task adds (`DMA_IMM_ENABLE`, `enable_rr`), plus 5 ×
  `Preprocessor failed`. The 8 `harness_error` logs split in two:
  - 5 (`enso` 3, 45, 54, 60 and `verilog_axi` 1, all named `*_tb_test.txt`) come from a second, non-pytest test
    step ("Compiling… Executing…") that the classifier does not parse; they ran.
  - **3 cannot be confirmed: `i2c` problems 7, 46 and 49.** Each log is about 100 bytes: the harness started the
    test container and cleaned up, with no test output at all. The log does not say why (a missing bundle, a
    harness error, or a test step that prints nothing); it is not shown to be a test failure. These three should
    be treated as suspect in the heavy split until a run shows them producing test output.

The per-test logs are in the artifacts of those runs (the artifact store was not reachable from this session, so
the reading above is from the classifier's job summary, not from downloaded files).

## Results of the live check

10 problems from the 92-problem agentic split, picked in code (`python3 tools/pick_ids.py <split> --seed 1`:
cid003 3, cid004 3, cid005 2, cid016 2, exactly 2 from the AMBA slice), listed in `tools/m1_ids.txt`. Two models,
both checked against `https://openrouter.ai/api/v1/models` on the day:

- `anthropic/claude-haiku-5.5` (cheap frontier model; $0.10 / $0.50 per M input / output tokens at the time);
- `deepseek/deepseek-v4.1-flash-1017` (open weights; $0.15 / $0.60 per M).

Budget $0.10 per problem, 10 turns, self-check and lint on, 2 threads, wall cap 480 s. Run locally on x86-64 with
`tools/sweep.sh` and the agent image built from commit `e030868` (the only later change to `agent/` removes an
unused constant). Pass/fail is the CVDP harness's; cost and tokens are OpenRouter's reported usage. The CSVs are
in [`docs/reports/m1/`](m1/), the table below is `tools/table.py` on them, unedited.

#### anthropic/claude-haiku-5.5

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 1/3 = 33.3% [6.1, 79.2] | $0.0461 | $0.0154 | $0.0461 | 76 s | 183,308 |
| cid004 RTL modification | 3/3 = 100.0% [43.9, 100.0] | $0.0463 | $0.0154 | $0.0154 | 97 s | 240,571 |
| cid005 spec to RTL, module reuse | 0/2 = 0.0% [0.0, 65.8] | $0.0206 | $0.0103 | n/a | 53 s | 114,175 |
| cid016 bug fixing | 2/2 = 100.0% [34.2, 100.0] | $0.0042 | $0.0021 | $0.0021 | 16 s | 18,919 |
| AMBA slice | 1/2 = 50.0% [9.5, 90.5] | $0.0149 | $0.0074 | $0.0149 | 51 s | 56,482 |
| **All** | 6/10 = 60.0% [31.3, 83.2] | $0.1172 | $0.0117 | $0.0195 | 53 s | 556,973 |

Stop reasons: give_up 1, submit 9

#### deepseek/deepseek-v4.1-flash-1017

| Slice | pass@1 [Wilson 95%] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|
| cid003 spec to RTL | 2/3 = 66.7% [20.8, 93.9] | $0.1171 | $0.0390 | $0.0586 | 429 s | 181,544 |
| cid004 RTL modification | 1/3 = 33.3% [6.1, 79.2] | $0.0563 | $0.0188 | $0.0563 | 137 s | 147,499 |
| cid005 spec to RTL, module reuse | 0/2 = 0.0% [0.0, 65.8] | $0.0832 | $0.0416 | n/a | 166 s | 173,895 |
| cid016 bug fixing | 2/2 = 100.0% [34.2, 100.0] | $0.0138 | $0.0069 | $0.0069 | 117 s | 39,521 |
| AMBA slice | 1/2 = 50.0% [9.5, 90.5] | $0.0746 | $0.0373 | $0.0746 | 237 s | 102,744 |
| **All** | 5/10 = 50.0% [23.7, 76.3] | $0.2704 | $0.0270 | $0.0541 | 144 s | 542,459 |

Stop reasons: submit 9, wall_time 1

Per problem (pass from the harness; cost from the provider):

| Problem | cid | AMBA | Haiku 5.5: pass, $, turns, s, stop | DeepSeek V4.1 Flash: pass, $, turns, s, stop |
|---|---|---|---|---|
| `DES_0003` | cid004 medium |  | PASS, $0.0226, 3, 97, submit | fail, $0.0180, 1, 59, submit |
| `axis_to_uart_0001` | cid003 medium | yes | PASS, $0.0113, 3, 76, submit | PASS, $0.0244, 2, 44, submit |
| `barrel_shifter_0002` | cid004 easy |  | PASS, $0.0031, 2, 21, submit | PASS, $0.0189, 4, 137, submit |
| `csr_using_apb_interface_0001` | cid003 medium | yes | fail, $0.0036, 1, 26, submit | fail, $0.0501, 2, 429, submit |
| `dual_port_memory_0001` | cid016 easy |  | PASS, $0.0022, 1, 18, submit | PASS, $0.0133, 3, 220, submit |
| `dynamic_equalizer_0004` | cid004 hard |  | PASS, $0.0206, 4, 128, submit | fail, $0.0195, 1, 151, submit |
| `lfsr_0001` | cid016 easy |  | PASS, $0.0020, 1, 15, submit | PASS, $0.0005, 1, 13, submit |
| `phase_rotation_0010` | cid005 medium |  | fail, $0.0107, 1, 48, submit | fail, $0.0453, 1, 70, submit |
| `phase_rotation_0028` | cid005 hard |  | fail, $0.0100, 1, 59, submit | fail, $0.0379, 2, 262, submit |
| `ttc_lite_0001` | cid003 medium |  | fail, $0.0312, 10, 201, give_up | PASS, $0.0426, 3, 528, wall_time |

Against the null agent (0/92 on this split at M0): both models solve problems the null agent cannot. 10 problems
give wide intervals: the 95% intervals of the two models overlap almost entirely, so this check says nothing
about which model is better. That is for M2.

What the traces show:

- **Self-check was used less than hoped.** Haiku ran a testbench (its own or one under `verif/`) in 3 of 10
  problems; DeepSeek in 7 of 10. Haiku often submitted on compile and lint alone. Whether the testbench
  step pays for itself is the M3 ablation; this run is not evidence either way.
- **DeepSeek spent whole replies on reasoning.** 8 of its 49 calls (6 plans, 2 edits) returned an empty reply
  after using the full `max_tokens` (4,000 for plan, 32,000 for edit) on reasoning tokens, which are billed:
  $0.0594 together, 22% of its spend. On
  `dynamic_equalizer_0004` the only edit call came back empty after 112 s and $0.017, so the agent changed
  nothing and that problem was lost to the null result.
- **One reflect reply was raw tool-call markup** (DeepSeek), not JSON; the parser fell back to `submit`.
- **The wall cap overshot once**: `ttc_lite_0001` (DeepSeek) stopped on `wall_time` at 528 s, against the 480 s
  cap, because an LLM call that started before the cap ran past it. Still under the harness's 600 s timeout, and
  the problem passed.
- **No problem hit the $0.10 budget.** The dearest was $0.050 (DeepSeek, `csr_using_apb_interface_0001`). The
  run-level guard ($1.20 per model) was never close.

**Live-check spend: $0.3937**, all provider-reported: $0.1172 (Haiku, 10 problems), $0.2704 (DeepSeek, 10 problems),
$0.0060 for one trial problem (Haiku, `lfsr_0001`, before the prompt fix in `e030868`; it passed), and $0.0000147
for the two one-word key-check calls. Plus $0.0093 for the 2-problem Actions sweep (run 39864754142), and $0.0050 for two
one-problem runs after review round 1 to check the changed image and workflow (Haiku, `lfsr_0001`, both passed:
$0.0018 locally, $0.0032 in Actions run 39884621498). **Grand total for M1: $0.4080**, of a $5 allowance.

## Review round 1

The owner's review of `1bac336` asked for ten fixes before merge. All are in; tests went from 41 to 52, and no
test needs an LLM.

| # | Finding | Fix |
|---|---|---|
| 1 | The key scan did not block the upload | The scan step has `id: scan`; the upload runs only `if: always() && steps.scan.outcome == 'success'`. The greps no longer use `-I`, so binary files are scanned, and the scan covers `work.*` (ledger, problem list) too. |
| 2 | Tool processes inherited `OPENROUTER_API_KEY` | Checks and tool detection get an environment with every credential-like name removed (`KEY`, `TOKEN`, `SECRET`, `AUTH`, …). In the image they also run as an unprivileged user (`cvdptool`), because a child running as root could still read the agent's environment from `/proc/1/environ`. Checked in the image: a probe run as a tool sees no key and gets `PermissionError` on `/proc/1/environ`. Test: a tool printing `os.environ` does not see the key. |
| 3 | Uncosted calls counted against no budget | An errored or timed-out call counts as unreported. The first unreported call stops the problem (`stop_reason: cost_unreported`); the edit already made is checked and kept by the usual rule. The ledger records unreported calls, and the run guard charges each one the per-problem budget (a stated ceiling, for the guard only). Tests for each. |
| 4 | A crash skipped `finalize` | `run()` streams the graph and calls `finish()` in `finally` with the last state (it runs once). The edit node catches any exception per file (`UnicodeDecodeError` on a non-UTF-8 file becomes an edit error); `snapshot()` skips dangling symlinks; `from_env()` is inside `main`'s try, and the fallback summary still lands in `CVDP_ROOT`. Tests for a crashing checker, a non-UTF-8 file, a dangling symlink and `CVDP_MAX_TURNS=10.0`. |
| 5 | `table.py` understated $/problem and $/solved | A row with no cost or with `cost_unreported_calls > 0` is unreported; when any row in a slice is, Cost, $/problem and $/solved all show `≥$x`. The committed M1 tables recompute unchanged (they have no unreported cost). |
| 6 | Rows with no `summary.json` left the model's denominator | `collect.py --model` (passed by the sweep) writes a `requested_model` column; `table.py` groups by it. |
| 7 | The wall cap did not cover the check node | Each tool's timeout is `min(tool timeout, time left)`; a check with under 5 s left is skipped (reported as SKIPPED, not as a failure, so it never triggers the best-edit restore); finalize's compile has its own 30 s. Test: a hung tool is cut at the time left. |
| 8 | Spend | New dispatch input `run_budget_usd` (absolute guard; blank keeps budget × problems × 1.2, $11.04 for 92). The job records the key's `usage` (only that field, never the label) before and after the run in the job summary, next to the agents' reported total. |
| 9 | Job timeout | The Run step has `timeout-minutes: 320` under the job's 360; collect, the key-usage line, the scan and the upload are separate `always()` steps. |
| 10 | `tools/sweep.sh` | Refuses a non-empty `WORK` (and an existing ledger or problem list); validates every numeric input with a regex before it reaches Python (a value like `1);import os…` is rejected); split into `run` and `collect` phases. |

Verified after the fixes: 51 passed and 1 skipped locally (the skipped one needs Icarus, which CI installs); the
fake-provider smoke run through the real harness with the rebuilt image (every check ran as the tool user and
passed); a rerun into the same work dir refused; one real problem with Haiku 5.5 through the harness ($0.0018,
passed, no key-shaped string anywhere in the work dir); the committed tables recompute byte for byte. In Actions
on `2808ce0`: Tests [39884423115](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39884423115),
Images [39884423254](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39884423254) (agent image
with the tool user), PR smoke [39884429240](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39884429240),
and a dispatched one-problem sweep with Haiku 5.5 and `run_budget_usd=0.05`
([39884621498](https://github.com/BrendanJamesLynskey/CVDP_RTL_Agent/actions/runs/39884621498): passed, $0.0032;
every new step ran: key usage before and after, collect as its own step, the scan, the upload gated on it), all
`completed, success`.

## Known gaps

- **GHCR packages are private until you flip them.** `GITHUB_TOKEN` can push packages but cannot change their
  visibility. Once: GitHub → your profile → Packages → `cvdp-sim` and `cvdp-rtl-agent` → Package settings →
  Change visibility → Public. The workflows log in to GHCR, so they work either way.
- **Heavy split: the edit roots are wrong for most of it** (found in review). In 53 of the 75 heavy problems the
  hidden tests read design files outside `rtl/`, `verif/` and `docs/`, so the file tool's roots must come from
  `CVDP_AGENT_WORKSPACE_ROOTS` or from the tree before any heavy run. The 92-problem agentic split is not affected.
- **Three heavy-split problems may not be scorable**: `i2c` 7, 46 and 49 produced no test output under the null
  agent (see above). Check them before trusting a heavy-split number.
- **The heavy split is untested with the agent.** Heavy problems use git workspace volumes, not bind mounts, for
  the design tree; `rundir/` is still a bind mount, so `agent_out/` should land as on the agentic split, but no
  agent run on the heavy split has been made yet.
- **The live check ran locally, on x86-64 only.** The Actions path with a real model was exercised only by the
  small dispatch listed above. Arm64 wall times for the sweep are for M2.
- **Empty replies from reasoning models** are not handled (see above). The trace makes them visible; the agent
  just counts the turn.
- **An unparseable reflect reply defaults to `submit`.** Defensible (the last compiled edit is on disk), but it
  ends the run early.
- **Wall cap is soft by up to one LLM call** (each call's timeout is half the remaining time, at most 150 s,
  and the generation-endpoint fallback can add up to about 50 s). Checks no longer overrun it: each tool's timeout
  is cut to the time left, and a check is skipped when under 5 s remain.
- **Budget cap is soft by one call**: it is checked before each call, so a problem can end up to one call over
  budget. Never happened here.
- **AMBA slice rule kept as stated** (decided in review): the id or the prompt names an AMBA interface.
  `cic_decimator_0001` has AXI-Stream-style port names (`*_tready`), but its id, prompt and spec never name AXI or
  AMBA, so it stays out; `tools/amba_ids.txt` says so.
- **The AMBA slice is 8 + 12, not 10 + 10** as the M0 README said; the README is corrected. The regex in the plan
  is case-sensitive, which would miss ids like `axis_*`; the scan runs it case-insensitively and every match was
  read (the list says what was dropped and why).

## Gotchas

- **Docker Hub rate limits** (429 on `ubuntu:24.04` / `ubuntu:22.04`) hit the local session; the harness itself
  builds a `patch_image` from `ubuntu:22.04` at start-up. On GitHub runners this has not happened, but a sweep that
  fails at start-up with 429 is this.
- **This session's network**: TLS is re-terminated by a proxy, and `astral.sh` and the Hugging Face file CDN are
  blocked. To build the sim image here I used a local copy of the Dockerfile with the proxy CA, a registry mirror
  and `pip install uv`; none of that is committed, and CI builds the harness's Dockerfile unchanged. The heavy-split
  bundles cannot be downloaded here, which is why the heavy log check ran in Actions.
- **`prompt.json` has only the prompt**: the dataset's `system_message` (which tells the model to answer with a
  patch) is not passed to agents, so the agent's own system prompt is all the model sees.
- **The harness passes an env var only if it is non-empty**, so `CVDP_SELF_CHECK=0` works (it is `"0"`), but an
  empty input would silently fall back to the default.
- **`workflow_dispatch` on a branch works** from the API with `ref: m1-agent` (used for every dispatch listed
  above), so sweeps can be run before merging.
- The verif testbenches in some problems dump VCDs into the working directory; the agent deletes waveform files
  under `agent_tb/` after each run, so the harness's 50 MB directory monitor is not tripped.

## Decisions

- **Edits as tagged blocks, plans and decisions as JSON.** Whole SystemVerilog files survive `<file path=…>`
  blocks far better than JSON string escaping; small structured replies stay JSON. Unified diffs are applied by
  matching context, not line numbers, because models get line numbers wrong.
- **A turn is one edit → check → reflect cycle**; the plan call is not a turn.
- **Compile always runs**, whatever the LLM picks: "the last edit that compiled" needs a compile after every edit.
  If a cap stops the run after an edit but before its check, finalize compiles it first. If nothing ever compiled,
  the last edit is kept (it cannot do worse than the null agent).
- **`CVDP_LINT` covers both Verilator lint and the Yosys check** (the two static checks), so the M3 ablation has
  one switch for "static checks".
- **The agent runs from its own venv** (`/opt/agent/venv`) so its packages never touch the harness's `/venv`, from
  which cocotb runs.
- **The spend guard lives in the agent, via a shared ledger mount**, so the harness still runs all problems in one
  invocation with threads and one `raw_result.json`. A problem started after the guard trips still appears in the
  results, as a run that made no edit, with its stop reason.
- **The PR smoke run builds the agent image from the PR's commit** (that is part of what it checks); dispatched
  sweeps pull the image `images.yml` pushed and build it only if it is missing.
- **Models**: the newest cheap Anthropic model on OpenRouter, and the newest DeepSeek open-weights Flash release;
  both list `tools` and `structured_outputs` support, though the agent only needs plain text.
- **Live check locally rather than in Actions**, because Docker works in this session; one small Actions dispatch
  checks the secret path.

## Follow-ups

- M2: sweep the 92-problem split with both models (≈ $1.2 and $2.7 at these rates) and a second cheap model, on
  x86-64 and Arm64.
- Handle reasoning models: set OpenRouter's `reasoning` limits, or retry once on an empty reply, and measure it.
- Run the agent on the heavy split (needs the bundles; the workflow already fetches them).
- Make the packages public (above).
- M3: the ablations the switches are for, and a failure taxonomy from the traces.
