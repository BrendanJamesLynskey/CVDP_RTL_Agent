# M3c report: mutation testing and elaboration in the loop

**Status: skeleton.** The tooling PR (`m3c-formal-checks`) adds the two checks and the sweep inputs; the 9 scored
sweeps are dispatched by the planner from `main` after it merges. Every table marked **[waits on runs]** is filled
from the run CSVs by the committed tools, nothing by hand. Harness `8e894cf`, dataset revision `5b807d9`. The rules
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

**[waits on runs]** Negative and null findings first: M − A and I − A with their 95% paired problem-bootstrap
intervals, better / worse / same, sign test; cost per solved problem by arm; which of the four focus labels each
arm moved; how often the gate failed, was overridden or found no testbench; how often the interface check found a
mismatch and of which kind.

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

**[waits on runs]** `python3 tools/ablate.py --ids tools/m3b_eval_ids.txt --base A --arm A=a1.csv,a2.csv,a3.csv
--arm M=m1.csv,m2.csv,m3.csv --arm I=i1.csv,i2.csv,i3.csv` (run CSVs in `m3c/runs/`):

| Comparison | Effect (points) | 95% CI | Better | Worse | Same | Sign test p |
|---|---|---|---|---|---|---|
| M − A (primary) | | | | | | |
| I − A (primary) | | | | | | |

Pooled pass@1 per arm (258 problem-runs each): **[waits on runs]**.

## Pareto

**[waits on runs]** pass@1 against $ per problem (`ablate.py --pareto-csv m3c/pareto.csv --pareto-svg
m3c/pareto.svg`). The gate's extra reflect calls and the interface check's extra edits cost tokens; the checks
themselves cost none.

| Arm | pass@1 | $ / problem | $ / solved | Median wall s | Calls unreported |
|---|---|---|---|---|---|
| A | | | | | |
| M | | | | | |
| I | | | | | |

## Failure taxonomy by arm

**[waits on runs]** `taxonomy.py --arm A=... --arm M=... --arm I=...`. No new label; three new flags say which
failures each arm touched: `gate_overridden` (the gate failed twice and the agent submitted anyway), `gate_no_tb`
(the gate found no testbench at least once) and `interface_mismatch_unresolved` (the last interface check still
reported a mismatch).

| Label | A | M | I |
|---|---|---|---|
| tests_failed_no_selfcheck | | | |
| tests_failed_selfcheck_passed | | | |
| signal_missing_hidden | | | |
| compile_fail_hidden | | | |
| stopped_by_cap | | | |
| other | | | |
| **All failures** | | | |

| Flag (failed problem-runs) | A | M | I |
|---|---|---|---|
| gate_overridden | — | | — |
| gate_no_tb | — | | — |
| interface_mismatch_unresolved | — | — | |

What each arm is expected to move, if it works: M, `tests_failed_no_selfcheck` (the gate demands a testbench) and
`tests_failed_selfcheck_passed` (it demands a stronger one); I, `signal_missing_hidden` and `compile_fail_hidden`.
Expected side effects: more `stopped_by_cap` on M (the gate's extra reflects and edits use turns and wall time).

## Gate and interface-check statistics

**[waits on runs]** From the new `results.csv` columns (after `memory`: `mutation_gate`, `interface_check`,
`gate_runs`, `gate_outcomes`, `gate_failures`, `gate_overridden`, `mutants_generated`, `mutants_compiled`,
`mutants_killed`, `mutants_unfinished`, `gate_wall_s`, `interface_runs`, `interface_mismatch_runs`,
`interface_kinds`, `interface_fallbacks`, `interface_blocks`, `interface_unresolved`; blank when the switch is off).

| Gate (arm M, 258 problem-runs) | Value |
|---|---|
| Problem-runs where the gate ran | |
| Gate runs, by outcome (no_tb / pass / fail / timeout / skipped) | |
| Problem-runs with gate_overridden | |
| Mutants generated / compiled / killed / unfinished | |
| Kill rate over compiled mutants | |
| Gate wall time per run (median, max) | |
| Wrapper vs per-mutant builds | |
| Passed problems with a gate failure first | |

| Interface check (arm I, 258 problem-runs) | Value |
|---|---|
| Checks run | |
| Checks with a mismatch | |
| Findings by kind (missing_module / missing_port / missing_param / spelling / width) | |
| Yosys fallbacks; could not elaborate | |
| Submits turned into an edit (interface_blocks) | |
| Problem-runs ending with a mismatch unresolved; of them passed | |

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

**Gate (M)**: 14 gate runs on 10 problems: `pass` 4, `skipped` 6, `no_tb` 3, `fail` 1; no `timeout`, no
`gate_overridden`. Where it ran to the end, the agent's testbench killed 12 of 12 mutants (`barrel_shifter_0002`),
11 of 12 (`lfsr_0001`), 8 of 12 (`csr_using_apb_interface_0001`, `ttc_lite_0001`); 48 mutants generated in passing
runs, 39 killed. Gate wall time per run was at most 2.0 s (bound 60 s): these designs are small. `no_tb` sent 3
problems back to reflect; 2 of them (`axis_to_uart_0001`, which then passed, and `dynamic_equalizer_0004`) then
ran a testbench and their second gate run was `skipped`.

**Interface check (I)**: 31 checks on 10 problems, all elaborated by pyslang (no Yosys fallback, nothing that could
not be elaborated); mismatches on one problem only, `phase_rotation_0010` (10 of 10 checks, 2 `missing_module`
each, unresolved at submit), one of M3b's 6 unreachable problems. No submit was turned into an edit
(`interface_blocks` 0: by the time the agent submitted, the same set had been reported more than twice).

Odd, and fixed in this PR after the smoke runs (neither re-run; the scored runs use the fixed image):

- **6 of 14 gate runs were `skipped`**, on `DES_0003`, `dual_port_memory_0001` and the second runs above. CVDP's
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
