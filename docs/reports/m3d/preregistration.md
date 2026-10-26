# M3d: pre-registration

Written 2026-10-26, after the smoke runs and before any scored run was dispatched. The commit that adds this file is
the record of what was decided in advance. Any change to the agent, the prompts, the case format or the analysis
after the first scored dispatch voids the runs made before it, and is stated in the report.

## Why

M3c's arm A (LangGraph, `openai/gpt-6-luna`) has a 10-turn cap but uses one turn in about 55% of problem-runs; its
median problem has 0 self-check runs. Brief 09 (`docs/reports/unsolved_analysis.md`, part two) found that on the 7
problems Claude Code solved and arm A never did, arm A submitted without running any testbench in 14 of 20 valid
attempts, because reflect accepted a clean compile, lint and synth. M3c's mutation gate forced a testbench and moved
failures from `tests_failed_no_selfcheck` to `tests_failed_selfcheck_passed`: a testbench that agrees with a wrong
design does not help. M3d tests two fixed graph steps, each behind a switch that is off by default.

| Arm | Sweep inputs | What changes |
|---|---|---|
| A | (defaults) | nothing: M3c's arm A, byte-for-byte (golden test); fresh runs |
| V | `verify_submit=true` | `verify` step between a submit and finalize |
| S | `spec_vectors=true` | V, plus a blind `spec` step before plan whose cases verify also applies |

## The two steps, fixed now

**V, `verify`.** A submit goes through only if the files as they now stand have passed a testbench the agent ran:
one it wrote, or one given under `verif/` that it named. "As they now stand" means no edit that changed a file
since that pass. If the agent's last testbench has not run since the last edit, `verify` runs it itself (counted as
a rerun). Otherwise the submit is refused and the graph goes back to edit with the reason (no testbench; the
testbench fails; with S, the specification cases fail) and what would satisfy it: run the testbench under `verif/`
if the task gives one (named in the message), else write a self-checking testbench with a small reference model
covering the specification's examples, error cases and stated latency, counts or flags. After **2 refusals** the
next submit is let through; a submit is also let through when the turn cap, budget or wall time leaves no room for
another edit. Refusals and let-throughs are counted per problem-run.

**S, `spec`.** One LLM call, before plan, on the same model and settings. Its prompt is `prompts.SPEC_SYSTEM` and
`prompts.SPEC` as committed with this file. It contains:

- the task prompt;
- the files under `docs/`;
- a port table of the modules defined by the given `rtl/` files (module name, parameter names, port direction,
  name and constant width), extracted in code before any edit.

It never contains an RTL body, a file under `verif/`, or anything the agent wrote. The port table is a decision:
modification and bug-fix tasks (cid004, cid016) name the module's ports only in its RTL, and without them no case
could be built.

**The case format** (`agent/cvdp_agent/spec.py`) is cycle-level vectors in one JSON object:

- top module, parameter overrides, clock port (or `null`), and every port with its direction and width;
- 4 to 12 cases (at most 16 kept), each at most 60 steps;
- each step: `in` (inputs, which hold their values), `expect_now` (compared 1 ns after the inputs change, before
  the edge), `wait` (extra edges), `until` (clock until an output has a value, within `max_cycles`), and `expect`
  (compared 1 ns after the next rising edge). Values may be integers, `0x..`, `0b..`, negative numbers, or `x` for
  don't-care;
- the harness checks it, drops any case that names an unknown port or carries a bad value, and writes a
  SystemVerilog testbench with a global time-out. It is built with Icarus against `rtl/` as it stands and prints
  one `SPEC_CASE <name> PASS|FAIL` line per case.

The spec cases are applied at every `verify` and run once more on the final design for measurement. They fail open
in four ways, and each is counted:

- the call errors;
- the reply is unusable;
- no case survives the checks;
- the testbench does not build against the design.

None of these blocks a submit. This format was chosen over a Python reference model because brief 09's failures are
mostly cycle-level (latency, when a flag holds), and vectors survive real model output without running
model-written code.

## The comparisons

- **V − A** and **S − A**, each two-sided at α = 0.025 (Bonferroni over 2). Paired on M3b's 86 evaluation problems
  with `python3 tools/ablate.py --base A --ids tools/m3b_eval_ids.txt --level 0.975 --arm A=... --arm V=...
  --arm S=...`: the paired bootstrap 97.5% interval over problems, and the exact two-sided sign test.
- **Data:** 3 new runs per arm, seeds 1–3 (`seed_offset` 0, 1, 2, `seeds` 1). All 9 runs are dispatched from one
  commit of `m3d-verify-submit` on the same day. A is a fresh base: M3c's CSVs are not reused.
- **Settings:** M3c arm A's, exactly: `openai/gpt-6-luna`, reasoning `default`, `ubuntu-24.04-arm`, 4 threads, the M2
  defaults ($0.10 per problem, 10 turns, self-check and lint on, 480 s wall cap), no lessons memory, LangGraph
  harness. There is one difference from M3c: the whole-run guard is $2.00 per sweep instead of $3.00. It stops only
  new problems once a sweep has spent $2.00, and no M3c arm-A sweep came near it.
- **Decision rule** (M3b-confirm's, applied to each comparison separately):
  - the interval excludes zero and the effect is positive → **better**;
  - the interval excludes zero and the effect is negative → **worse**;
  - otherwise → **no detectable effect**: report the interval, and say what effect size it rules out.
- **Power, stated in advance.** On these 86 problems with 3 runs per arm, M3c's paired 95% half-widths were
  4.6–4.9 points. Computed on M3c's M − A data, the 97.5% interval is about 5.5 points wide on each side. So:
  - a true effect of about +8 points has roughly an 80% chance of being detected;
  - +5 points has about a 40% chance;
  - an effect of 3 points or less will very likely read as no detectable effect.
  
  Claude Code Opus's lead over arm A was +11.6 points, so a step that closed most of that gap would be detected.

## Secondary analyses (descriptive only, no test)

- pass@1 per arm and the paired effects with brief 09's 7 benchmark-limited problems (`tools/benchmark_limited_ids.txt`)
  excluded (`--exclude`), reported next to the full-86 numbers, never in their place;
- turns, LLM calls and self-check runs per problem (median and mean) by arm;
- the failure taxonomy by arm (`tools/taxonomy.py`), with M3d's flags: `verify_let_through`, `spec_checks_passed`,
  `spec_checks_failed` and `spec_failed_open`;
- $/solved, $/problem and median wall time per problem by arm, and the Pareto chart;
- refusals per problem-run, let-throughs, and verify's own reruns;
- for S, spec-case outcome against hidden-test pass: a 2×2 table of whether all spec cases passed on the final design
  against whether the hidden tests passed. Also how often the spec step failed open, and why.

## Spend

OpenRouter, `openai/gpt-6-luna` only. Each sweep has a $2.00 whole-run guard. Spend is checked after each batch,
from each sweep's key-usage lines and its ledger. If the next batch would take the total past **$10** (smoke runs
included), no more runs are started, and the report says which runs are missing. Expected: about $5–8.

## Smoke runs (not scored, before this file)

Five problems from brief 09's part two (`queue_0001`, `lfsr_0005`, `binary_search_tree_algorithms_0001`,
`nmea_gps_0008`, `ethernet_mii_0006`), one run each, M3c arm A's settings:

- **V** (run 40346289641, $0.0901 reported, 1 call unreported): the step refused 6 submits on 4 problems and the agent
  then edited each time. On `queue_0001` and `lfsr_0005` it wrote a testbench after the refusal and submitted on
  the next turn. 0 of 5 passed, as in M3c's arm A on these problems.
- **S** (run 40346313430, $0.0935, 2 unreported): the spec call produced usable cases on 4 of 5 problems (4–7 cases
  each). Its prompt in the trace holds the task, the documents and the port table only. On `nmea_gps_0008` every
  case was dropped, because the model wrote byte inputs as characters (`"$"`). Character values were then allowed
  (`'G'`, or one non-alphanumeric character) before this file was written, and S was smoked again (run
  40348875200).
- 3 of the 10 smoke rows ended `llm_error`: an edit call abandoned at the wall-cap deadline (18–33 s left). This is
  the existing deadline rule. Longer problems reach it more often, so V and S may show more of these stops; the
  report counts them.
