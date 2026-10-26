# M3d report: verify before submit

**Status: done (2026-10-26).** The code and the pre-registration ([`m3d/preregistration.md`](m3d/preregistration.md))
are on the branch `m3d-verify-submit`, PR #22. The pre-registration was committed before any scored dispatch. The 9
scored sweeps ran on 2026-10-26, all from commit `c96f058`, which is unchanged since the pre-registration commit
(runs 40353853802 to 40389203542, listed in `m3d/runs/`).

The tables are made from the run CSVs by the committed tools, nothing by hand:
- `ablate.py --level 0.975`;
- `taxonomy.py`;
- the new `tools/m3d_tables.py`.

Harness `8e894cf`, dataset revision `5b807d9`. The rules from the M1 report still apply:
- the LLM never produces a score or a label;
- every cost is provider-reported;
- a missing cost is recorded as unreported, never estimated.

Nothing was changed after the first scored dispatch.

**The question.** M3c's arm A (LangGraph, `gpt-6-luna`) uses one turn on about half its problem-runs and runs no
testbench on most. Brief 09 ([`unsolved_analysis.md`](unsolved_analysis.md), part two) found that on the 7 problems
Claude Code solved and arm A never did, arm A submitted untested in 14 of 20 attempts. M3d adds two fixed graph steps
that the model cannot skip:

| Arm | Sweep inputs | What changes |
|---|---|---|
| A | (defaults) | nothing: M3c's arm A, byte-for-byte; fresh runs |
| V | `verify_submit=true` | a submit is refused until the design as it stands has passed a testbench |
| S | `spec_vectors=true` | V, plus reference cases that a blind LLM call writes from the specification; verify applies them too |

Pre-registered: **V − A** and **S − A**, each two-sided at α = 0.025 (Bonferroni over 2), paired on M3b's 86
evaluation problems.

## In short

**Neither step moves pass@1. Both pre-registered comparisons are null, and both point slightly downwards.**

- **V − A: −1.9 points [−6.6, +2.3]** (97.5% interval). Better / worse / same is 7 / 9 / 70, sign test p = 0.80.
  - The interval rules out a gain of more than 2.3 points.
  - V costs 1.6× as much per solved problem (≥$0.0181 against ≥$0.0112) and takes a median 135 s per problem against
    74 s.
- **S − A: −4.7 points [−11.2, +1.6]**. Better / worse / same is 12 / 19 / 55, p = 0.28.
  - The interval rules out a gain of more than 1.6 points.
  - S costs 2.1× as much per solved problem (≥$0.0234) at a median 247 s.
- **Pooled pass@1:** A 60.9%, V 58.9%, S 56.2%. With brief 09's 7 benchmark-limited problems left out (79 problems):
  A 66.2%, V 64.1%, S 61.2%, and the effects are −2.1 [−7.2, +2.5] and −5.1 [−12.7, +1.7].

**The steps change how the agent works, not how often it is right.**
- **Testing.** Under V the agent almost always tests before submitting: problem-runs with no self-check run fall
  from 55% to 1%.
- **Turns.** The median number of turns goes from 2 to 3 (V) and 4 (S), and 1-turn runs fall from 47% to 10% and
  7%.
- **The verify step.** It refused a submit on 155 of V's 258 problem-runs, and the agent then edited.
- **The failure mix.** As with M3c's mutation gate, failures move from `tests_failed_no_selfcheck` (55 on A, 0 on V,
  2 on S) to `tests_failed_selfcheck_passed` (16 → 48 and 44). The agent now writes a testbench, the testbench passes,
  and the hidden tests still fail.
- **The cost in time.** The extra turns hit the 480 s wall cap. `stopped_by_cap` rises from 7 to 27 (V) and 43 (S),
  and `llm_error` (calls abandoned at the wall-cap deadline) from 2 to 14 and 9. Those stops are where most of the
  lost problem-runs went.

**The blind specification cases do not separate right from wrong designs.**
- When every spec case passed on the final design, the hidden tests passed 82 times in 135 (61%).
- When some case failed, they passed 36 times in 63 (57%).
- The cases mostly confirm what the agent already believes, or they disagree for reasons the hidden tests do not
  share (an unstated latency, a reading of an ambiguous rule).

**None of the 7 problems from brief 09's part two is won.** On `nmea_gps_0008`, `binary_search_tree_algorithms_0001`,
`ethernet_mii_0006`, `lfsr_0005`, `queue_0001` and `csr_using_apb_interface_0001`, V and S score 0 of 3, as A does.
`DES_0001` is 1 of 3 in every arm. Making the agent run a testbench is not what Claude Code did on these problems.
What Claude Code did was write a testbench that checks the right behaviour.

The noise floor: arm A's three runs here range from 57.0% to 65.1%, and M3c's fresh arm A scored 61.6%.

## Arms and settings

All arms use M3c arm A's settings exactly:
- LangGraph harness, `openai/gpt-6-luna`, reasoning `default`;
- `ubuntu-24.04-arm`, 4 threads;
- the M2 defaults: $0.10 per problem, 10 turns, self-check and lint on, 480 s wall cap;
- no lessons memory.

Every arm runs on `tools/m3b_eval_ids.txt` (86 problems), 3 runs per arm (`seed_offset` 0, 1, 2), each with a $2.00
whole-run guard:

```
gh workflow run sweep.yml --ref m3d-verify-submit -f model=openai/gpt-6-luna -f split=agentic \
  -f runner=ubuntu-24.04-arm -f threads=4 -f reasoning=default -f seed_offset=<0|1|2> -f run_budget_usd=2.00 \
  -f ids=$(grep -v '^#' tools/m3b_eval_ids.txt | paste -sd,) [-f verify_submit=true | -f spec_vectors=true]
```

With both switches off, the graph, prompts, trace and summary are M3c's arm A. The golden test of the LangGraph agent
passes unchanged, and also with both switches passed explicitly as off, which is what the sweep sends.

### The verify step (`verify_submit=true`)

`verify` sits between reflect's `submit` and finalize (`agent/cvdp_agent/graph.py`).

- **When a submit passes.** The files as they now stand must have passed a testbench the agent ran: its own, or one
  given under `verif/` that it named. Every edit that changes a file bumps a version, and a testbench pass counts
  only for the version it ran on.
- **The rerun.** If the agent's last testbench has not run since the last edit, `verify` runs it itself. This
  happened 15 times on V.
- **A refusal** goes back to edit with what is missing (no testbench, a failing one, failing spec cases). It also
  gives brief 09's advice:
  - run the task's testbench when there is one; the message names the given files;
  - otherwise write a self-checking testbench with a small reference model covering the examples, the error cases
    and any stated latency, count or flag.
- **Let-through.** After 2 refusals the next submit goes through. A submit also goes through when the turn cap,
  budget or wall time leaves no room for another edit.

### The specification cases (`spec_vectors=true`)

A `spec` step before plan makes one LLM call. Its prompt (`prompts.SPEC`) holds:
- the task prompt;
- the files under `docs/`;
- a port table of the modules the given `rtl/` defines (names, directions, constant widths, parameter names),
  extracted in code before any edit.

It never holds an RTL body, a file under `verif/`, or anything the agent wrote. The test
`test_spec_call_is_blind_and_its_cases_block_a_wrong_design` checks this on the recorded request:
- a marker inside the original module body, and one inside a given testbench, are both absent;
- the docs and the port table are present.

The trace records the call's reply, not its prompt. In run 40353898485, for example, `lfsr_0005`'s spec reply begins
`{"top":"bit16_lfsr","params":{},"clock":"clock","ports":{"clock":{"dir":"in","width":1},...` and names only the
ports from the table.

**The reply is cycle-level vectors in one JSON object** (format in the pre-registration; `agent/cvdp_agent/spec.py`).
- **Checking.** The code checks the reply and drops any case that names an unknown port or carries a bad value. It
  writes a SystemVerilog testbench with a global time-out, which is built with Icarus against `rtl/`.
- **When it is applied.** The cases are applied at every `verify`, and once more on the final design for
  measurement.
- **What the agent sees.** A refusal shows the mismatches (case, step, signal, expected, got), never the cases'
  source.
- **Failing open.** The step fails open on an error, an unusable reply, or a testbench that does not build against
  the design.

## Paired results

From [`m3d/arms_paired_eval86.md`](m3d/arms_paired_eval86.md) (`ablate.py --base A --ids tools/m3b_eval_ids.txt
--level 0.975`):

| Arm | Finding | Effect [97.5%] | Better / worse / same | Sign test p | Problems |
|---|---|---|---|---|---|
| S | no detectable effect | −4.7 [−11.2, +1.6] | 12 / 19 / 55 | 0.281 | 86 |
| V | no detectable effect | −1.9 [−6.6, +2.3] | 7 / 9 / 70 | 0.804 | 86 |

| Arm | Runs: pass rate each | Pooled pass@1 [95% problem bootstrap] | Cost | $/problem | $/solved | Median wall | Tokens |
|---|---|---|---|---|---|---|---|
| A (base) | 57.0%, 60.5%, 65.1% | 157/258 = 60.9% [51.9, 69.8] | ≥$1.7592 (4 unreported) | ≥$0.0068 | ≥$0.0112 | 74 s | 8,621,964 |
| V | 59.3%, 61.6%, 55.8% | 152/258 = 58.9% [49.6, 68.6] | ≥$2.7506 (15 unreported) | ≥$0.0107 | ≥$0.0181 | 135 s | 13,226,965 |
| S | 55.8%, 57.0%, 55.8% | 145/258 = 56.2% [46.9, 65.1] | ≥$3.3892 (18 unreported) | ≥$0.0131 | ≥$0.0234 | 247 s | 15,249,575 |

**Verdicts under the pre-registered rule.**
- **V − A: no detectable effect.** The interval [−6.6, +2.3] includes zero and rules out a V gain of more than 2.3
  points.
- **S − A: no detectable effect.** The interval [−11.2, +1.6] includes zero and rules out an S gain of more than 1.6
  points. It does not rule out a loss of up to 11 points.

**Benchmark-limited problems excluded** (secondary, [`m3d/arms_paired_eval79.md`](m3d/arms_paired_eval79.md),
`--exclude tools/benchmark_limited_ids.txt`). On 79 problems: A 66.2%, V 64.1%, S 61.2%. V − A is −2.1 [−7.2, +2.5]
and S − A is −5.1 [−12.7, +1.7]. Excluding them shifts the effects only a little, because no arm passed any of those 7 problems in any run.

## Pareto

[`m3d/pareto.svg`](m3d/pareto.svg), [`m3d/pareto.csv`](m3d/pareto.csv): pass rate against $ per problem.

Every arm has some unreported cost, so each $/problem is a lower bound and no arm is drawn on the frontier.
- A is both the cheapest arm (≥$0.0068 per problem) and the most accurate one.
- V costs 1.6× as much and S 1.9× as much, for less.

## What V and S did to the turn count and the failure mix

From [`m3d/secondary_tables.md`](m3d/secondary_tables.md) (`tools/m3d_tables.py`):

| Arm | Turns median / mean | 1-turn rows | LLM calls median / mean | Self-check runs median / mean | Rows with 0 self-check runs |
|---|---|---|---|---|---|
| A | 2 / 2.55 | 122 (47%) | 5 / 6.08 | 0 / 1.19 | 143 (55%) |
| V | 3 / 4.37 | 26 (10%) | 7 / 9.62 | 2 / 2.84 | 3 (1%) |
| S | 4 / 4.68 | 17 (7%) | 10 / 11.10 | 2 / 3.03 | 17 (7%) |

| Arm | submit | max_turns | wall_time | llm_error | run_budget_exhausted |
|---|---|---|---|---|---|
| A | 243 | 8 | 3 | 4 | 0 |
| V | 201 | 18 | 24 | 15 | 0 |
| S | 177 | 17 | 38 | 18 | 8 |

**The verify step.**

| Arm | verify runs | Refusals | Rows with a refusal | Let-throughs | Reruns by verify | Verified submits: hidden pass | Let-through submits: hidden pass |
|---|---|---|---|---|---|---|---|
| V | 383 | 182 | 155 | 10 | 15 | 131/191 (69%) | 5/10 |
| S | 423 | 246 | 178 | 46 | 19 | 88/131 (67%) | 28/46 |

- **Refusals.** Most of them were "no testbench has run on the current files" (149 of V's 182). The rest were
  "your testbench fails" (33).
- **Submits.** A verified submit passed the hidden tests 69% of the time on V. A's submits passed 151/243 (62%).
- **Who gets refused.** A refusal falls mostly on problems the agent was going to get right anyway. On V's 155
  refused problem-runs, the hidden tests passed 80 times; A, on the same problem and seed, passed 86 times.

**Failure taxonomy** ([`m3d/taxonomy_by_arm.md`](m3d/taxonomy_by_arm.md)):

| Label | A | V | S |
|---|---|---|---|
| llm_error | 2 | 14 | 9 |
| stopped_by_cap | 7 | 27 | 43 |
| sim_incomplete | 5 | 2 | 1 |
| compile_fail_hidden | 10 | 9 | 10 |
| signal_missing_hidden | 4 | 3 | 0 |
| tests_failed_selfcheck_passed | 16 | 48 | 44 |
| tests_failed_selfcheck_failed | 2 | 3 | 4 |
| tests_failed_no_selfcheck | 55 | 0 | 2 |
| **All failures** | **101** | **106** | **113** |

**Where the problem-runs were won and lost against A** (same problem and seed):
- **V** won 13 problem-runs. A had failed 6 of them untested (`tests_failed_no_selfcheck`) and 3 of them on a hang
  (`sim_incomplete`).
- **V** lost 18: 7 `stopped_by_cap`, 7 `tests_failed_selfcheck_passed`, 2 `tests_failed_selfcheck_failed` and
  2 `llm_error`.
- **S** won 17 (9 of them untested failures on A) and lost 29 (14 of them `stopped_by_cap`).

The step does catch some untested wrong designs. It loses about as many right ones to the time cap, and to
testbenches that sent the agent on to a wrong rewrite.

The new flags on failed rows:
- `spec_checks_passed` 53: the agent's own checks and the spec checks passed, and the hidden tests failed. This is
  the new failure kind the brief asked to name;
- `spec_checks_failed` 27;
- `spec_failed_open` 25;
- `verify_let_through` 23.

## The specification cases (arm S)

- **The spec call:**
  - produced usable cases on 239 of 258 problem-runs, with a median of 4 cases per set;
  - gave an unusable reply on 11;
  - did not run on 8, which the whole-run guard stopped before their first call (see Gotchas).
- **On the final design** the cases passed on 135 problem-runs and failed on 63. They did not build on 41 (failed
  open, usually a port the cases name that the design lacks), and 19 had no cases or no final run.

| All spec cases pass on the final design | Hidden tests pass | Hidden tests fail |
|---|---|---|
| yes | 82 | 53 |
| no (fail or timeout) | 36 | 27 |
| not applied (no cases, unbuildable, error, or not run) | 27 | 33 |

The cases agree with the hidden tests barely better than chance: a 61% hidden pass rate when they all pass, 57% when
they do not. 60 refusals came from failing spec cases. After two refusals, 46 problem-runs were let through, and 28
of those passed the hidden tests: a spec case was refusing a design the hidden tests accept. Written from the
specification alone, by the same model, the cases carry the same misreadings as the agent's own testbench, plus
their own guesses at timing the specification leaves open.

## Smoke runs (not scored)

The smoke runs are in the pre-registration. They used five problems from brief 09's part two, one run each:
- V, run 40346289641;
- S, run 40346313430;
- S again, run 40348875200, after character values (`"$"`) were allowed in the cases. That change was made before
  the pre-registration was committed.

## Spend

- **Scored runs.** The 9 sweeps' provider-reported cost is $7.8990, with 37 calls unreported.
- **Key usage.** OpenRouter's key usage (`key_check.yml`) moved from $47.2210 before the first scored dispatch to
  $55.1526 after the last run: **$7.93**. So the unreported calls cost about $0.03.
- **Smoke runs.** $0.26 reported.
- **Total for this brief:** about **$8.19**, under the $10 hard stop.

## Known gaps

- **The time cap is part of the result.** V and S use the same 480 s wall cap and 10 turns as A, as pre-registered.
  A good share of their losses is `stopped_by_cap` and `llm_error` at the wall-cap deadline. A larger cap might
  change the sign, but it would be a different experiment, and it would cost more.
- **"Passed a testbench" is the agent's own judgement of a testbench it wrote.** A testbench that prints nothing and
  exits 0 counts as a pass, exactly as in M1–M3c's self-check rule. The verify step only makes sure one was run.
- **The spec writer is the same model.** The cases are blind to the design but not to the model's way of reading a
  specification. A different (stronger) model for the spec call was not tested.
- **The port table.** The spec call is given the given RTL's ports. For a modification task this tells it nothing
  about ports the task adds.
- **No combined arm with the mutation gate.** The sweep refuses `verify_submit` with `mutation_gate`.
- **Deep Agents is not covered.** Both steps belong to the LangGraph graph.
- **Brief 09's two smaller lessons are not implemented:** generating tables from the docs with a script, and making
  minimal changes when fixing a given module.

## Gotchas

- **Character values.** The first S smoke run lost every case of a serial-protocol task, because the model wrote
  byte inputs as characters (`"$"`). Single characters, and `'G'` in quotes, are now read as ASCII codes. Digits are
  still numbers.
- **The whole-run guard and S.** The guard charges $0.10 (the per-problem budget) for every call whose cost was not
  reported. That includes a call still in flight, because the provisional summary counts it as unreported. S makes
  more calls, so more of them go unreported, and with 4 threads in flight the charge also rises for a while during
  the run. Two of S's runs crossed $2.00 near their end:
  - run 2 had a final guard charge of $1.91 for $1.21 actually spent, and 2 problems were refused;
  - run 3 had $1.73 for $1.03, and 6 problems were refused.

  The 8 refused problem-runs (`run_budget_exhausted`) count as failures for S, as pre-registered. Counted at A's pass
  rate instead, they would move S − A by about +1.9 points, which is still negative. A future S run should use a
  larger guard.
- **Spec testbenches can hang.** Two hidden tests loop forever on RTL that never completes (brief 09). The spec
  testbench therefore has a global time-out derived from its own step count, and each `until` has a `max_cycles`.
- **The trace keeps replies, not prompts.** Blindness of the spec call is shown by the unit test on the recorded
  request, and by the code path that builds the prompt. It cannot be shown from a sweep trace.

## Decisions

- Both switches default to off and add no node, trace event or summary field when off; arm A is M3c's arm A.
- Both steps are graph nodes the model cannot skip, not tools it may call.
- `spec_vectors` turns `verify_submit` on: S is V plus the spec cases.
- A refusal goes back to edit (not reflect), and the let-through comes after 2 refusals. A submit is also let through
  when no edit can follow, so the step never turns a submit into a cap stop.
- The step reruns the agent's last testbench itself rather than refusing when it is merely stale, so a refusal is
  never spent on that.
- The spec cases are cycle-level vectors, not a model-written reference model, and the step fails open. The case
  format, the prompt and the analysis were fixed in the pre-registration before the first scored dispatch.
- **Verdict:** V and S are null against A, and both cost more. Neither should become a default.
