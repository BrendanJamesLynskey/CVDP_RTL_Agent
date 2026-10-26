# M3c report: mutation testing and elaboration in the loop

**Status: done (2026-10-26).** The tooling PR (#16, `m3c-formal-checks`) added the two checks and the sweep inputs;
the 9 scored sweeps ran from `main` at `dd8be4f` on 2026-10-26 (runs 40257040625 to 40274995282, listed in
`m3c/runs/`). The tables are filled from the run CSVs by the committed tools (`ablate.py`, `taxonomy.py`, and a
column count for the gate and interface tables), nothing by hand. A first set of 9 sweeps on 2026-10-25 (runs
40213580065 to 40215295542) is void: the OpenRouter balance was too low and every call failed with 402
`in_flight_budget_exhausted`; none of its rows is used. Harness `8e894cf`, dataset revision `5b807d9`. The rules
from the M1 report still apply: the LLM never produces a score or a label, every cost is provider-reported, and a
missing cost is recorded as unreported, never estimated.

**The question.** M3 and M3b found the agent's failures in two places: **interface mismatches** with the hidden
testbench (`signal_missing_hidden`, `compile_fail_hidden`) and **weak self-checks** (no testbench of its own,
`tests_failed_no_selfcheck`, the largest label; or one that passes on code the hidden tests fail,
`tests_failed_selfcheck_passed`). M3c adds one deterministic, model-free check for each, as a fixed step of the
LangGraph graph that the model cannot skip, and asks whether either moves pass@1:

| Arm | Sweep inputs | What changes |
|---|---|---|
| A | (defaults) | nothing: the M2/M3b agent, byte-for-byte; fresh runs on this PR's image |
| M | `mutation_gate=true` | mutation-score gate before submit |
| I | `interface_check=true` | interface diff by elaboration after each edit |

Pre-registered: **M − A** and **I − A**, primary, paired on M3b's 86 evaluation problems, negative and null findings
first. No combined arm.

## In short

**Neither check moves pass@1.** Both pre-registered comparisons are null:

- **M − A: +0.8 points [−3.9, +5.8]**, better / worse / same 13 / 10 / 63, sign test p = 0.68. M costs about twice
  as much per solved problem (≥$0.0190 against ≥$0.0099) and takes a median 135 s per problem against 51 s.
- **I − A: −1.6 points [−6.2, +3.1]**, 10 / 13 / 63, p = 0.68, at about the same cost ($0.0113 per solved problem).

**The gate changes the kind of failure, not the number.** It removes `tests_failed_no_selfcheck` entirely (56 failed
problem-runs on A, 0 on M), because it will not let the agent submit without a testbench. But the failures move to
`tests_failed_selfcheck_passed` (14 → 50) and `stopped_by_cap` (4 → 19): the agent now writes a testbench, the
testbench passes, and the hidden tests still fail. The testbenches the gate forced killed 56% of compiled mutants
(1,051 of 1,872). 16% of gate runs (61 of 390) were `skipped` and let the submission through.

**The interface check found little to fix.** Of 672 checks, 99 reported a mismatch, on 38 problem-runs, and 21 of
those 38 then passed the hidden tests, so most findings were false or harmless. It turned 3 submits into edits.
`signal_missing_hidden` and `compile_fail_hidden` together are 16 failures on A and 16 on I.

The noise floor to read them against, from M3b: the base's runs differ by about ±2 points on these 86 problems
between identical runs, and M3b's largest single-change effect (+4.3, Deep Agents) had an interval reaching zero.

## Arms and settings

All arms: LangGraph harness, `openai/gpt-6-luna`, reasoning `default`, `ubuntu-24.04-arm`, 4 threads, the M2
defaults ($0.10 per problem, 10 turns, self-check and lint on, 480 s wall cap), no lessons memory. Every arm runs on
`tools/m3b_eval_ids.txt` (86 problems), 3 runs per arm (`seed_offset` 0, 1, 2):

```
gh workflow run sweep.yml -f model=openai/gpt-6-luna -f split=agentic -f runner=ubuntu-24.04-arm -f threads=4 \
  -f reasoning=default -f seed_offset=<0|1|2> -f ids=$(grep -v '^#' tools/m3b_eval_ids.txt | paste -sd,) \
  [-f mutation_gate=true | -f interface_check=true]
```

Arm A's switches are off, so its graph, prompts, trace and summary are M3b's arm A: the golden test of the LangGraph
agent (committed in M3b) passes unchanged, and also with both switches passed explicitly as off, which is what the
sweep now sends (`CVDP_MUTATION_GATE=0`, `CVDP_INTERFACE_CHECK=0`).

### The mutation-score gate (`mutation_gate=true`)

`agent/cvdp_agent/mutation.py`, a `gate` node between reflect's `submit` and finalize.

- **No testbench of the agent's ran in this problem**: the gate fails with "write and run a testbench for the
  specified behaviour before submitting".
- Otherwise the agent's last testbench is re-run on the design as it is; if it fails there, the gate fails.
- **Mutants**: Yosys `mutate -list 12 -seed 1` on the design read with `read_verilog -sv` and `prep -flatten -top
  <the module the testbench drives>` (with `chparam` for literal parameter overrides in the testbench). This is
  MCY's approach with core Yosys; MCY itself is not used.
- **One build**: all 12 mutations go into one netlist with `mutate -ctrl mutsel 8 <i>`; the module is renamed and
  a wrapper with the design's name and ports sets `mutsel` from a `+mutsel=<i>` plusarg (MCY's method). The
  testbench is built once against it and run once per mutant, with the simulator it used (Icarus for a
  SystemVerilog testbench, cocotb on Icarus for a cocotb one). The unmutated wrapper (`mutsel=0`) must pass the
  testbench; if it does not (the testbench reads an internal signal through the hierarchy, say), the gate falls
  back to **one netlist and one build per mutant**, whose unmutated netlist must pass too.
- **Killed** = the testbench fails on the mutant, or runs past 5 times its own run on the design (a hang). **Kill
  rate** = killed / mutants that compiled. The gate passes at a kill rate of at least **0.5**. Equivalent mutants (a
  change the design cannot show at its outputs) make 100% unreachable for any testbench, which is why the threshold
  is not higher.
- **Survivors** go to reflect as one more check result, each by its kind and location from `mutate -list` (for
  example `mutant 3: const1 on wire wrap bit 0 (rtl/counter.sv:12.17-12.47)`), never the mutated code.
- **Bounds**: at most 60 s of gate wall time per run (each tool call is cut at the bound; mutants not finished
  count as not killed, the outcome is `timeout` and the trace says how many); at most 2 gate failures per problem,
  after which the agent submits anyway with `gate_overridden`. The 480 s wall cap wins: the gate's bound is cut to
  the time left less 5 s, and a gate failure with no budget or time left for another reflect submits too
  (`gate_overridden`).
- Parameters the testbench sets on the design are applied with `chparam` when they resolve to integers: literals,
  the testbench's own literal `parameter`/`localparam` values, and integer arithmetic over them; the wrapper and the
  per-mutant netlists declare them so the testbench's instantiation compiles.
- Outcomes per run: `no_tb`, `pass`, `fail`, `timeout`, and `skipped` (Yosys could not read or mutate the design, the
  testbench sets parameters to values that do not resolve to integers, or no netlist could drive the testbench;
  never blocks).

### The interface check (`interface_check=true`)

`agent/cvdp_agent/interface.py`, an `interface` node after every edit and before check.

- **The design**: `rtl/` elaborated with **pyslang 12.0.0** (pinned; manylinux wheels for x86-64 and aarch64). If
  pyslang reports an error, the fallback is Yosys `read_verilog -sv; hierarchy -top <top>; proc; write_json`, where
  widths count as constant only in a module with no parameters. Extracted per module: name, ports (direction,
  width where the declared type has no parameter in it) and parameters.
- **The given interface**, read once at the start (before any edit) from `prompt.json`, `docs/`, `rtl/` and
  `verif/` only:
  - a module the context's original RTL defines (cid004, cid016 and the reused modules of cid005): that file's
    original ports and parameters;
  - a Verilog module header in the prompt or a document;
  - the documents' port tables (a direction column) and the bullets under an interface, port or signal heading,
    and the parameters under a parameter heading; each goes to the module its heading names, or to the one new
    module the prompt asks for (a submodule only a heading names is compared if it exists, never required);
  - the ports and parameters a visible testbench under `verif/` connects by name, for a module the prompt names;
  - a module the prompt names ("the module should be defined as `des_dec`"), even with no ports found.
  The names-given extraction is `tools/reachable.py`'s, moved into the agent package (`cvdp_agent/given.py`).
- **Required modules**: `missing_module` only for a module the original RTL defines, the prompt names or a visible
  testbench instantiates; a module only a document names is compared if the design has it, never required.
- **Findings**: `missing_module`, `missing_port`, `missing_param` (a given name the design lacks; a given parameter
  may be a localparam), `spelling` (a design name the given interface spells differently, by case or underscores
  only) and `width` (only when both widths are constant).
- **Never reads the hidden testbench or any harness file**: every file is opened in Python, inside the task tree;
  pyslang gets text, includes are inlined from `rtl/`, symlinks are not followed, and the Yosys fallback gets only
  paths under `rtl/`. A test audits every open and every subprocess.
- **Soft block**: the result goes to reflect as one more check, in lint's format. A submit with a mismatch set
  reported only once becomes one more edit (if a turn and budget are left); once the same set has been reported
  twice, the agent may submit anyway.

**How much the check knows** ([`m3c/given_interface_eval86.md`](m3c/given_interface_eval86.md),
`tools/interface_given.py`, offline; it reads the hidden files as `reachable.py` does, the agent never does): on the
86 problems the given interface has the hidden testbench's top module for **83**; of the 848 top-level `dut.`
handles the hidden testbenches read, 704 (83%) are ports or parameters of that given module. Sources of the top
module's interface: original RTL 29, docs 25, a module header 15, a visible testbench 9, the prompt's module name
only 5, not given 3. This bounds what the check can catch; it says nothing about false findings, which only the runs
show (below).

## Paired results

`python3 tools/ablate.py --ids tools/m3b_eval_ids.txt --base A --arm A=A1…,A2…,A3… --arm M=M1…,M2…,M3…
--arm I=I1…,I2…,I3…` on the CSVs in `m3c/runs/`; full output in
[`m3c/arms_paired_eval86.md`](m3c/arms_paired_eval86.md). All 86 problems are in every arm (none dropped).

| Comparison | Effect (points) | 95% CI | Better | Worse | Same | Sign test p |
|---|---|---|---|---|---|---|
| M − A (primary) | +0.8 | [−3.9, +5.8] | 13 | 10 | 63 | 0.678 |
| I − A (primary) | −1.6 | [−6.2, +3.1] | 10 | 13 | 63 | 0.678 |

Pooled pass@1 per arm (258 problem-runs each): **A 159 = 61.6%** (runs 65.1, 59.3, 60.5), **M 161 = 62.4%**
(59.3, 64.0, 64.0), **I 155 = 60.1%** (59.3, 65.1, 55.8). Both intervals contain 0 and both effects are inside the
±2-point spread between identical runs of the base. This A (61.6%) sits between M3b's arm A (57.9% in the confirming
runs) and arm B (62.6%), within run-to-run noise.

## Pareto

pass@1 against $ per problem ([`m3c/pareto.csv`](m3c/pareto.csv), [`m3c/pareto.svg`](m3c/pareto.svg)). The gate's
extra reflect calls and the interface check's extra edits cost tokens; the checks themselves cost none. A cost
marked ≥ has unreported calls and is a lower bound.

| Arm | pass@1 | $ / problem | $ / solved | Median wall s | Calls unreported |
|---|---|---|---|---|---|
| A | 61.6% | ≥$0.0061 | ≥$0.0099 | 51 | 1 |
| M | 62.4% | ≥$0.0119 | ≥$0.0190 | 135 | 3 |
| I | 60.1% | $0.0068 | $0.0113 | 59 | 0 |

M makes 2,984 LLM calls against A's 1,414 (median 4 turns against 1) and uses 14.8 M tokens against 7.7 M. I makes
1,599 calls (median 2 turns). Only I is on the frontier, because A's and M's costs are lower bounds; in practice A
is the cheapest arm, and no arm buys pass rate.

## Failure taxonomy by arm

`taxonomy.py --arm A=... --arm M=... --arm I=...`; full output in
[`m3c/taxonomy_by_arm.md`](m3c/taxonomy_by_arm.md). No new label; three new flags say which failures each arm
touched: `gate_overridden` (the gate failed twice and the agent submitted anyway), `gate_no_tb`
(the gate found no testbench at least once) and `interface_mismatch_unresolved` (the last interface check still
reported a mismatch).

| Label | A | M | I |
|---|---|---|---|
| tests_failed_no_selfcheck | 56 | 0 | 45 |
| tests_failed_selfcheck_passed | 14 | 50 | 18 |
| signal_missing_hidden | 5 | 4 | 3 |
| compile_fail_hidden | 11 | 11 | 13 |
| stopped_by_cap | 4 | 19 | 12 |
| other (`tests_failed_selfcheck_failed`, `sim_incomplete`, `llm_error`) | 9 | 13 | 12 |
| **All failures** | 99 | 97 | 103 |

| Flag (failed problem-runs) | A | M | I |
|---|---|---|---|
| gate_overridden | — | 25 | — |
| gate_no_tb | — | 66 | — |
| interface_mismatch_unresolved | — | — | 7 |

What each arm is expected to move, if it works: M, `tests_failed_no_selfcheck` (the gate demands a testbench) and
`tests_failed_selfcheck_passed` (it demands a stronger one); I, `signal_missing_hidden` and `compile_fail_hidden`.
Expected side effects: more `stopped_by_cap` on M (the gate's extra reflects and edits use turns and wall time).

What happened: M moved `tests_failed_no_selfcheck` as expected (56 → 0), but not into passes: 36 more failures are
`tests_failed_selfcheck_passed` and 15 more are `stopped_by_cap`. M stopped on the turn cap 34 times; 16 of those still passed. Requiring a
testbench is not the same as requiring a correct one. I moved neither of its labels (16 → 16 together); its
`stopped_by_cap` rose 4 → 12.

## Gate and interface-check statistics

From the new `results.csv` columns (after `memory`: `mutation_gate`, `interface_check`,
`gate_runs`, `gate_outcomes`, `gate_failures`, `gate_overridden`, `mutants_generated`, `mutants_compiled`,
`mutants_killed`, `mutants_unfinished`, `gate_wall_s`, `interface_runs`, `interface_mismatch_runs`,
`interface_kinds`, `interface_fallbacks`, `interface_blocks`, `interface_unresolved`; blank when the switch is off).

| Gate (arm M, 258 problem-runs) | Value |
|---|---|
| Problem-runs where the gate ran | 242 (the other 16 never reached a submit) |
| Gate runs, by outcome (no_tb / pass / fail / timeout / skipped) | 390: 141 / 103 / 85 / 0 / 61 |
| Problem-runs with gate_overridden | 51 (26 of them passed) |
| Mutants generated / compiled / killed / unfinished | 2,904 / 1,872 / 1,051 / 0 |
| Kill rate over compiled mutants | 56.1% |
| Gate wall time per problem-run (median, 90th percentile, max) | 0.2 s, 6.1 s, 60.0 s (2 at the bound) |
| Wrapper vs per-mutant builds | not in the CSV (the method is in the trace only) |
| Passed problems with a gate failure first (`no_tb` or `fail`) | 91 of M's 161 passes |
| `skipped` (fails open) | 61 gate runs on 61 problem-runs, 38 distinct problems |

| Interface check (arm I, 258 problem-runs) | Value |
|---|---|
| Checks run | 672 |
| Checks with a mismatch | 99, on 38 problem-runs (21 of them passed) |
| Findings by kind (missing_module / missing_port / missing_param / spelling / width) | problem-runs with each kind: 11 / 18 / 13 / 0 / 0 |
| Yosys fallbacks; could not elaborate | 16 fallbacks on 11 problem-runs; none failed to elaborate |
| Submits turned into an edit (interface_blocks) | 3 (bcd_adder_0004 twice, passed both; DES_0007 once, failed) |
| Problem-runs ending with a mismatch unresolved; of them passed | 13; 6 passed |

The 13 unresolved problem-runs are on 5 problems: `DES_0007`, `bcd_adder_0004`, `ethernet_mii_0006`,
`phase_rotation_0013` and `programmable_fsm_dynamic_state_encoding_0001`. No `spelling` or `width` finding was made
in 672 checks.

A mismatch on a problem the agent then passes is a false finding of the check (or a name the hidden tests do not
read); the report counts them.

## Smoke runs (not scored)

One sweep per new arm on the 10 problems of `tools/m1_ids.txt`, Arm64, 4 threads, `run_budget_usd=0.50`, one seed,
dispatched from this PR's branch (agent image `526c621`). They check the steps end to end, not the arms; the per-problem
rows are in each run's log (the Collect step prints `results.csv`).

| Arm | Run | Passed | Provider-reported spend | Unreported calls | Harness wall s | Stop reasons |
|---|---|---|---|---|---|---|
| M | 40188841425 | 5/10 | $0.0826 | 0 | 452 | submit 9, max_turns 1 |
| I | 40188844846 | 6/10 | $0.1027 | 0 | 428 | submit 10 |

Total **$0.1853** of the $1.00 allowed (each the sum of its 10 per-problem provider-reported costs).

**Gate (M)**: 14 gate runs on 10 problems: `pass` 4, `skipped` 5, `no_tb` 4, `fail` 1; no `timeout`, no
`gate_overridden`. Where it ran to the end, the agent's testbench killed 12 of 12 mutants (`barrel_shifter_0002`),
11 of 12 (`lfsr_0001`), 8 of 12 (`csr_using_apb_interface_0001`, `ttc_lite_0001`); 48 mutants generated in passing
runs, 39 killed. Gate wall time per run was at most 2.0 s (bound 60 s): these designs are small. `no_tb` sent 4
problems back to reflect; all 4 then ran a testbench. The second gate run was `skipped` on 3
(`axis_to_uart_0001`, which then passed, `dynamic_equalizer_0004`, `phase_rotation_0010`) and `fail` on
`phase_rotation_0028` (12 mutants generated, 0 compiled: the CSV does not say whether its testbench failed on the
design itself or no mutant compiled; its last self-check failed, which points to the first). That problem then stopped
on the turn cap; it is one of M3b's 6 unreachable problems.

**Interface check (I)**: 31 checks on 10 problems, all elaborated by pyslang (no Yosys fallback, nothing that could
not be elaborated); mismatches on one problem only, `phase_rotation_0010` (10 of 10 checks, 2 `missing_module`
each, unresolved at submit), one of M3b's 6 unreachable problems. No submit was turned into an edit
(`interface_blocks` 0: by the time the agent submitted, the same set had been reported more than twice).

Odd, and fixed in this PR after the smoke runs (neither re-run; the scored runs use the fixed image):

- **5 of 14 gate runs were `skipped`**, on `DES_0003`, `dual_port_memory_0001` and the 3 second runs above. CVDP's
  own testbenches pass their parameters through their own (`parameter NBW_DATA = 'd64;` ... `.NBW_DATA(NBW_DATA)`),
  which the gate took as non-literal and skipped. The gate now resolves a testbench's literal `parameter` and
  `localparam` values (and integer arithmetic over them), sets them with `chparam`, and declares them on the
  wrapper and the per-mutant netlists so the testbench compiles (tested on both build methods). The artifact store
  is not reachable from where this PR was built, so the skip reason is inferred from the testbenches in the
  dataset, not read from the traces.
- **The 2 `missing_module` findings on `phase_rotation_0010` were false**: `slicer_top` and `slicer` are named in a
  document, not in the prompt, and the design does not need them. A module is now required only when the original
  RTL defines it, the prompt names it or a visible testbench instantiates it; a module only a document names is
  compared if it exists (tested).
- Not odd: a gate wall time of 0.09 s for 12 mutants of the barrel shifter is real (locally, Yosys takes about
  0.13 s and each `vvp` run 0.01 s on a counter).

## Known gaps

- **The given interface from prose is heuristic.** Tables, interface bullets and headings are read by rules, not by
  a parser of the specification; a port listed in an unusual format is missed (no finding), and a document that
  lists signals of another module under an interface heading without naming it can produce a false
  `missing_port`. The soft block lets the agent submit after the same mismatches are reported twice.
- **A modification task's new ports.** For cid004 and cid016 the given interface is the original RTL, so a port the
  task adds is not checked, and a port the task removes or widens on purpose is a finding the agent must override.
- **The gate sees parameters only as integers.** A testbench parameter set from something that does not resolve to
  an integer (a function call, `$clog2`, a string) is not mutated (`skipped`).
- **Hierarchy.** The design is flattened before mutating; a testbench that reads internal signals through the
  hierarchy falls back to per-mutant builds, whose netlist keeps public wire names but not every internal name.
- **Equivalent mutants.** Some mutants cannot change the design's outputs; they are survivors no testbench can
  kill. The 0.5 threshold allows for them; their share is not measured.
- **The gate scores the agent's testbench, not the design.** A design that fails the hidden tests can pass the gate
  with a testbench that checks the wrong behaviour thoroughly.
- **Deep Agents is not covered.** Both switches are steps of the LangGraph graph; the sweep refuses them with
  `harness=deepagents`.
- **The CI Yosys is not the image's.** The Tests workflow installs Ubuntu 24.04's Yosys 0.33; the agent image has the
  harness's Yosys 0.40. Both have `mutate -ctrl` (the image build checks it).

## Gotchas

- `mutate -list` with `-none` lists the unmutated design as one of the N; the gate does not pass `-none` and uses
  `mutsel=0` as the unmutated design instead, so N = 12 real mutants.
- `mutate -ctrl` adds the control input to the module that holds the mutated cell; without `-flatten` a mutation in
  a submodule would leave the control unconnected at the top.
- Yosys' `write_json` refuses a design with processes: the interface fallback runs `proc` first.
- A run cut by the gate's own bound is not a hang: it counts as unfinished (not killed), while a mutant that runs
  past its own timeout counts as killed.

## Decisions

- Both switches default off and add no node, trace event or summary field when off; arm A is M3b's arm A.
- The checks are graph steps the model cannot skip, not tools it may call.
- The gate's parameters (12 mutants, seed 1, threshold 0.5, 60 s, 2 failures) and the interface check's soft block
  (submit allowed after the same mismatch set twice) are fixed before any scored run.
- The interface check is never a hard block; neither is the gate after 2 failures.
- No combined arm: M − A and I − A are the two pre-registered comparisons.
