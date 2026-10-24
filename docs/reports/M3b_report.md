# M3b report: harness against self-improvement

**Skeleton.** The tooling, the problem sets and the smoke runs are done; every table marked **[waits on runs]** is
filled in once the scored sweeps have run. Harness `8e894cf`, dataset revision `5b807d9`, agent from PR
`m3b-harness-memory`. The rules from the M1 report still apply: the LLM never produces a score or a label, and
every cost is provider-reported.

**The question.** At a fixed model, is more pass@1 bought more cheaply by a richer agent harness (Deep Agents
instead of the LangGraph graph) or by a memory of lessons learned on other problems? Four arms, three runs each,
on a fixed evaluation set:

| Arm | Harness | Memory |
|---|---|---|
| A | LangGraph (M2's agent, unchanged) | none |
| B | Deep Agents | none |
| C | LangGraph | frozen lessons snapshot |
| D | Deep Agents | the same snapshot |

Primary comparisons: **B − A** (harness) and **C − A** (memory). Secondary: **D − B** and **D − C** (does each add
to the other).

## In short

Negative and null findings first. **[waits on runs]**

- B − A: **[waits on runs]** points [95% CI], better/worse, sign-test p.
- C − A: **[waits on runs]**.
- D − B, D − C: **[waits on runs]**.
- The noise floor on this evaluation set, from M3: the base's two Arm64 runs differ by **−2.3 points
  [−9.3, +3.5]** (3 better, 5 worse, 78 the same) on the 86 problems; M3's largest effect, 20 turns, is
  **+4.1 [−0.6, +9.9]** here. An effect of the size M3 saw cannot be told from that floor with 3 runs an arm.
- Cost per solved problem by arm: **[waits on runs]**.

## Arms and settings

All arms: `openai/gpt-6-luna`, reasoning `default`, `ubuntu-24.04-arm`, 4 threads, the M2 defaults (10 turns,
$0.10 per problem, self-check and lint on, 480 s wall cap). Three runs per arm, dispatched with `seeds=1` and
`seed_offset` 0, 1, 2 (or `seeds=3`), so runs are seeds 1–3. Every arm runs all 92 agentic problems; the primary
analysis restricts to the 86 of the evaluation set with `ablate.py --ids`, and all 92 are a secondary table.

```
gh workflow run sweep.yml -f model=openai/gpt-6-luna -f split=agentic -f runner=ubuntu-24.04-arm \
  -f reasoning=default -f seed_offset=<0|1|2> -f harness=<langgraph|deepagents> \
  [-f memory=docs/reports/m3b/lessons/lessons_<hash>.json]
```

Arm A's runs are fresh runs on this PR's image (the LangGraph agent is byte-for-byte M2's, checked by the golden
test below), not M2's or M3's runs, so all four arms share an image and a period.

### The Deep Agents harness (`harness=deepagents`)

`agent/cvdp_agent/deep.py`, `deepagents==0.7.32` (with `langchain==1.4.7`; pinned in `agent/requirements.txt`).
It drives the same model through the same `Runtime.call`, so the provider code, reasoning field and its fallback,
empty-reply retry, hard deadline, provider-reported cost, unreported-cost rule, run-budget ledger, trace,
`summary.json` and stop reasons are shared with the LangGraph agent. It reuses the existing tools: the file tool's
path policy (writes only under `rtl/`, `verif/`, `docs/` and the scratch `rundir/agent_tb/`), and the `Checker`
behind one `run_checks` tool (compile, lint, synth, the agent's own testbench). The best-edit rule and `finish()`
are the same.

| Deep Agents feature | |
|---|---|
| Its agent loop (model → tool calls → model …) and system-prompt assembly | on |
| Planning tool `write_todos` (TodoListMiddleware) | on |
| File tools `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep` | on, backed by the real task tree through the file tool's policy (not a virtual file system); `delete` refused |
| Large tool-result eviction to its virtual file system | off (check output is already cut to 2,500 characters) |
| `execute` (shell) | off (not offered) |
| Sub-agents (`task`) | off (the general-purpose sub-agent is disabled by a registered harness profile), so every call is the main agent's |
| Conversation summarization (part of its base stack) | as shipped; a summarizing call goes through the same model and counts as a round |

**Round cap: 22.** The LangGraph agent's turn cap (10 edit–check–reflect cycles) has no direct meaning in a
tool-call loop, so it becomes a cap on model calls. 22 is the most LLM calls any M2 problem made in 10 turns: 1 plan
+ 10 edits + 10 reflects = 21, plus one empty-reply retry. Hitting it stops the problem with `stop_reason`
`max_turns`, so the results tools read it unchanged; `turns` in the summary counts rounds. The budget and wall-time
caps are the LangGraph agent's, checked before every call.

### The lessons memory (`memory=<snapshot>`)

- **Builder** `tools/learn_lessons.py`, run once on the learning-set work dirs. For each attempt it writes a digest
  from the harness's outcome, the taxonomy's deterministic label and the trace (stop reason, checks and their
  results, the plan's approach, the first hidden-test error line; no code), and asks the model, one call per batch
  of 15, for general lessons. Lessons are cut to at most 60 words, at most 40 in all, de-duplicated, and anything
  code-like is dropped. The snapshot is written to `docs/reports/m3b/lessons/lessons_<hash>.json`, where the hash
  is the SHA-256 (first 16 hex digits) of its canonical content; its provenance records the model, the attempts,
  each call's cost and any unreported cost. **[waits on runs]**: the snapshot, its hash and its build cost.
- **No agentic problem is ever seen.** The builder refuses any work dir that holds one of the 92 agentic problems,
  the 86 of the evaluation set or the 6 excluded from it (`tools/m3b_excluded_ids.txt`, written by
  `reachable.py`), in `raw_result.json` or as a problem dir, before reading anything from it (`EvalLeak`; tested
  with an evaluation id and an excluded one).
- **Only the learning set is learned from.** By default (`--learn-ids`) the builder also refuses a work dir holding
  any problem outside `tools/m3b_learn_in_roots_ids.txt` (`OutsideLearningSet`; tested), and the snapshot's
  provenance names the learning set.
- **Retrieval**: `cvdp_agent/memory.py`, deterministic BM25 (k1 = 1.2, b = 0.75, ties broken by snapshot order; no
  embedding API, no LLM). The query is the task prompt plus the problem's `docs/` text files; the top 5 lessons are
  appended to the plan prompt (LangGraph) or the task message (Deep Agents) under "Lessons from other problems".
  The retrieved ids and scores are a `lessons` trace event and in `summary.json`.
- **Frozen**: the snapshot is mounted read-only into the agent's container and checked against its hash on load;
  `results.csv` records it in a `memory` column (last; blank without memory), so every row names its snapshot.

## The two problem sets

- **Learning set**: the **29** heavy problems whose files to change all lie inside the agent's edit roots
  (`tools/m3b_learn_in_roots_ids.txt`), none in the evaluation set. The same agent must learn and be scored: on
  the other 46 heavy problems the reference change is to files outside `rtl/`, `verif/` and `docs/`, which the
  agent's file policy refuses, so lessons learned from those failures would be about the policy. The agent is not
  changed to reach them; the set is narrowed instead. "Files to change" are the keys of the dataset record's
  `patch` (the files the reference solution changes); `tools/learn_in_roots.py` keeps a problem when every one
  starts with an edit root, deterministically, from the dataset alone. For 27 of the 29 the hidden build's
  `VERILOG_SOURCES` also lie inside the roots; the other 2 (`i2c_0046`, `i2c_0049`) list no sources there. The full
  heavy split (75, `tools/m3b_learn_ids.txt`) is kept for the record.
  - The memory learns from arm A's configuration run on the 29 with **3 seeds**:
    ```
    gh workflow run sweep.yml -f model=openai/gpt-6-luna -f split=heavy -f runner=ubuntu-24.04-arm \
      -f reasoning=default -f seeds=3 -f ids=$(grep -v '^#' tools/m3b_learn_in_roots_ids.txt | paste -sd,)
    python3 tools/learn_lessons.py --work <work dir> --out-dir docs/reports/m3b/lessons
    ```
    **[waits on runs]** (run ID, pass count per seed, cost).
  - Three of the 29 (`i2c_0007`, `i2c_0046`, `i2c_0049`) gave no test output under the null agent in M1 and may not
    be scorable. They stay in the set (the rule is the edit roots alone); if they fail without a test log in all 3
    seeds, their attempts carry no outcome to learn from, and the report will say so.
- **Evaluation set**: the 92 agentic problems minus 6 that no agent can be expected to pass, 86 problems
  (`tools/m3b_eval_ids.txt`; the 6 in `tools/m3b_excluded_ids.txt`). Committed before any scored run.

**Exclusion rule** (`tools/reachable.py`, from the dataset's hidden harness files and M3's 14 runs): a problem is
unreachable when a name the hidden testbench reads (a `dut.` handle, the top module, or a parameter it sets) is
given nowhere to the agent (not in a code file of its context, nor in the prompt's or docs' code spans; for
identifier-shaped names, nowhere in the prose) **and** M3 labels it `signal_missing_hidden` or
`compile_fail_hidden` in at least half of its runs. Both halves are needed: `csr_using_apb_interface_0001` and
`dynamic_equalizer_0008` read names the agent is not given but failed on them in only 1 of 14 runs, so they stay.
The 6 excluded, with the names, are in [`m3b/unreachable.md`](m3b/unreachable.md): `digital_stopwatch_0001` (its
context is empty, so even the spec is missing), `phase_rotation_0010`, `phase_rotation_0028`,
`phase_rotation_0031`, `phase_rotation_0038`, `poly_decimator_0001` (internal register or instance names). Five
problems whose M3 failures are mostly interface labels are kept, because every name is given:
`cache_controller_0001`, `hdbn_codec_0001`, `sigma_delta_audio_0001`, `sync_serial_communication_0001`,
`ttc_lite_0001`.

## Paired results

`python3 tools/ablate.py --ids tools/m3b_eval_ids.txt --base A --arm A=a1.csv,a2.csv,a3.csv --arm B=... --arm C=... --arm D=...`: effect in
pass@1 points with a 95% problem-bootstrap interval, problems better / worse / same, and an exact sign test. Runs of
an arm are pooled per problem.

**[waits on runs]** Evaluation set (86 problems), primary:

| Comparison | Effect (points) | 95% CI | Better | Worse | Same | Sign test p |
|---|---|---|---|---|---|---|
| B − A | | | | | | |
| C − A | | | | | | |
| D − B | | | | | | |
| D − C | | | | | | |

**[waits on runs]** All 92 problems, secondary: the same table.

## Pareto

**[waits on runs]** pass@1 against $ per solved problem and $ per problem for the four arms (`ablate.py --pareto-csv/--pareto-svg`).

| Arm | pass@1 | $ / problem | $ / solved | Median wall s | Calls unreported |
|---|---|---|---|---|---|
| A | | | | | |
| B | | | | | |
| C | | | | | |
| D | | | | | |

## Failure taxonomy by arm

**[waits on runs]** Failed problem-runs by label (`taxonomy.py --arm A=... --work A=...`), with focus on the labels each arm is meant to move:
`signal_missing_hidden` and `compile_fail_hidden` (the lessons on interface names), `tests_failed_no_selfcheck`
and `tests_failed_selfcheck_passed` (the lessons on testing; Deep Agents' freer loop), `stopped_by_cap` (Deep
Agents' round cap).

| Label | A | B | C | D |
|---|---|---|---|---|
| tests_failed_no_selfcheck | | | | |
| tests_failed_selfcheck_passed | | | | |
| signal_missing_hidden | | | | |
| compile_fail_hidden | | | | |
| stopped_by_cap | | | | |
| other | | | | |

## The lessons and how often each is retrieved

**[waits on runs]** The real snapshot's lessons, and the problems of the evaluation set each is retrieved for
(`python3 tools/retrieval.py <snapshot> <dataset.jsonl> --ids tools/m3b_eval_ids.txt`; with `--runs`, what the
agents' summaries say they retrieved).

For the fixture snapshot (8 hand-written lessons, used by the tests and smoke runs only), retrieval over the 86
problems is in [`m3b/retrieval_fixture_snapshot.md`](m3b/retrieval_fixture_snapshot.md): lessons on interface
names come up for 71–77 problems, the one on compiling with every listed file for 19. With few lessons, BM25 picks
nearly the same 5 for most problems; a 40-lesson snapshot should spread more.

## Smoke runs (not scored)

One sweep per new arm on the 10 problems of `tools/m1_ids.txt`, Arm64, `run_budget_usd=0.50`, one seed; C and D
with the fixture snapshot `0ceb24db0ad46853`. These check the harness and the memory end to end, not the arms.

| Arm | Run | Harness | Memory | Passed | Provider-reported spend | Unreported calls | Harness wall s | Stop reasons |
|---|---|---|---|---|---|---|---|---|
| B | 40089282542 | deepagents | none | 4/10 | $0.0581 | 0 | 230 | submit 10 |
| C | 40089288510 (first) | langgraph | fixture | 0/10 | $0 | 0 | — | error 10 (mount bug, below) |
| D | 40089293910 (first) | deepagents | fixture | 0/10 | $0 | 0 | — | error 10 (mount bug, below) |
| C | 40089719945 | langgraph | fixture | 5/10 | $0.0637 | 0 | 418 | submit 10 |
| D | 40089721671 | deepagents | fixture | 6/10 | $0.0636 | 0 | 520 | submit 8, max_turns 2 |

Total **$0.1854** of the $1.50 allowed (the key's `usage` moved by the same amount over B's run: 18.369717 →
18.427809).

Per problem (pass, then model calls):

| Problem | B | C | D |
|---|---|---|---|
| DES_0003 | pass, 12 | pass, 5 | pass, 6 |
| axis_to_uart_0001 | pass, 11 | pass, 5 | pass, 22 (cap) |
| barrel_shifter_0002 | pass, 10 | pass, 5 | pass, 18 |
| csr_using_apb_interface_0001 | fail (no selfcheck), 14 | fail (selfcheck failed), 21 | fail (no selfcheck), 19 |
| dual_port_memory_0001 | fail (selfcheck passed), 11 | pass, 3 | pass, 12 |
| dynamic_equalizer_0004 | fail (no selfcheck), 16 | fail (no selfcheck), 5 | pass, 22 (cap) |
| lfsr_0001 | pass, 6 | pass, 5 | pass, 9 |
| phase_rotation_0010 * | fail (signal missing), 21 | fail (signal missing), 3 | fail (signal missing), 7 |
| phase_rotation_0028 * | fail (compile fail hidden), 9 | fail (compile fail hidden), 3 | fail (compile fail hidden), 12 |
| ttc_lite_0001 | fail (no selfcheck), 10 | fail (signal missing), 3 | fail (selfcheck passed), 17 |

\* excluded from the evaluation set as unreachable; they fail on every arm, as expected.

Odd or worth knowing (none of it is a result: one run of 10 problems each):

- **The first C and D dispatches failed on a mount bug**, not in the agent: see Gotchas. Every problem stopped with
  `error` before its first call and nothing was spent. Fixed, then both re-dispatched once.
- **D hit the round cap on 2 of 10** (axis_to_uart, dynamic_equalizer), and both passed: the best edit kept at the
  cap was a passing one. B, with the same harness and no memory, never hit it. If the scored runs show many caps,
  22 rounds is the setting to look at first.
- **C took fewer turns than M2's agent usually does**: 3 problems were submitted after a single edit turn
  (`single_turn` flag), and csr_using_apb took 21 calls and 8 testbench runs. Whether the lessons make the
  LangGraph agent submit sooner is a question for the scored runs.
- Deep Agents sends much more prompt per problem (B: 27k–653k prompt tokens, against C's 4k–63k), since the whole
  tool conversation is resent each round; at this model's prices it costs about the same per problem.
- The re-dispatched C and D ran with the workflow's default 2 threads (B had 4); the scored runs use 4.
- No unreported cost, no empty replies, no reflect parse retries on any arm.

## Known gaps

- **Heavy-split edit roots.** In 46 of the 75 heavy problems the files to change are outside `rtl/`, `verif/` and
  `docs/`, which the agent's file policy refuses (the gap M1 noted). The agent is not changed, so that arm A stays
  M2's agent; the learning set is narrowed to the other 29 instead (above). M1 gave the count as 53, from a check
  it did not commit; neither the reference patch nor the hidden build's `VERILOG_SOURCES` reproduces 53 (both give
  46 outside), so this report uses 46 and the committed script. The harness supports `CVDP_AGENT_WORKSPACE_ROOTS`
  if a later milestone widens the roots.
- **A small learning set.** 29 problems × 3 seeds is at most 87 attempts, in 6 batches of 15. The memory may hold
  fewer than 40 lessons.
- **Shared dependency drift.** Pinning `deepagents` moved one shared transitive dependency, `tenacity` 9.2.1 →
  9.1.4. The LangGraph golden test passes unchanged on the new set.
- **Summarization as shipped.** Deep Agents' summarization middleware is left as shipped; with 22 rounds and cut
  check output it should rarely trigger, and a summarizing call counts as a round. **[waits on runs]**: how often it
  ran.
- **Rounds are not turns.** B and D's `turns` count model calls; A and C's count edit cycles. Compare the arms on
  cost and wall time, not on turns.

## Gotchas

- The pinned harness joins `CVDP_AGENT_MOUNTS` with `;` (`source:target[:mode]` each), but `CVDP_AGENT_ENV` with
  `,`. The first C and D smoke runs joined the mounts with `,`; the harness dropped the whole spec as invalid, the
  snapshot was missing in the container and every problem stopped with `error` before its first call ($0). Fixed in
  `tools/sweep.sh`; the test now parses the mounts as the harness does.
- Deep Agents requires `read_file` among its file tools, and offers the `task` sub-agent unless a harness profile
  matching the model's provider disables it; the model wrapper reports provider `cvdp` so the profile applies.
- `reachable.py` must drop f-strings whole when it scans hidden testbenches for `dut.` handles: a handle inside a
  log message is not one the test reads.

## Decisions

- Pre-registered before any scored run: the evaluation set and the exclusion list (`c00071a`); the learning set
  (the 29 in-roots heavy problems, 3 seeds) and the guard's refused set (the 86 evaluation and the 6 excluded
  agentic problems) with review round 1. No learning-set or scored run had been made when they were fixed.
- The LangGraph agent is unchanged: a golden test of three fake-provider runs (requests, trace and summary, with
  volatile fields scrubbed) was committed before any agent change (`e136091`) and still passes.
- Retrieval is BM25, not embeddings: deterministic, no API, no cost, the same lessons for the same problem in every
  run.
- One frozen snapshot for C and D: the memory does not grow during evaluation, so C − A measures one fixed memory.
- The round cap is 22 (above).
