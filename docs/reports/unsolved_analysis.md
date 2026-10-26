# Why the unsolved problems fail

**Status: done (2026-10-26). Analysis only: no sweep, no model call, no OpenRouter or plan spend.** The subject is
the 12 of M3b's 86 evaluation problems (`tools/m3b_eval_ids.txt`) that no Claude model in the
[ladder](claude_code_ladder.md) solved. 10 of them were also never solved by M3c's arm A (LangGraph +
`gpt-6-luna`, 3 runs). The list was recomputed from `claude_code/runs/*.csv` and `m3c/runs/A*.csv` (column `pass`)
and matches the brief. For each problem, the evidence is:

- the task as the agent saw it, and the hidden harness: the dataset record at revision `5b807d9`
  (`cvdp_v1.1.0_agentic_code_generation_no_commercial.jsonl`). This split has no reference solution: every `patch`
  file in it is empty;
- all 7 attempts (4 Claude models, 3 arm-A runs): the final RTL (`agent_changes.patch`), the trace and the
  hidden-test report, from the sweep artefacts. Arm A is runs 40257040625, 40263328806 and 40270547450. The ladder's
  valid rows come from runs 40201690138, 40201705867, 40201781193, 40201854208, 40209823449, 40212363900,
  40212382474, 40233538340, 40233554454, 40257083583 and 40283726775. No artefact had expired (they expire on
  2027-01-23 and 2027-01-24);
- **local reruns.** Each of the 84 attempts was run again against the hidden tests, one at a time, in the harness's
  simulation image (`ghcr.io/brendanjameslynskey/cvdp-sim:8e894cf`: Icarus 13.0, cocotb 2.0.1) under
  `systemd-run --user --scope -p MemoryMax=5G`. 83 of 84 gave the same result as CI. The exception is described
  under `phase_rotation_0015`;
- **counterfactual reruns.** An attempt's RTL was rerun with one change: the detail the test needs but the
  specification does not give. If the attempt then passes, that detail was the only thing between it and a pass.
  These runs are diagnosis only. They are not scores, and no model wrote the change.

The classes follow the brief. **benchmark-limited**: the hidden test needs behaviour, a value or a file name that
the task does not give, or it is not deterministic. **environment**: our harness, image or runner caused the
failure. **agent-limited**: the specification is clear enough and the attempts are wrong.

## In short

- **7 of the 12 are benchmark-limited, with strong evidence.** For each of them, a counterfactual rerun shows that
  one unstated detail is enough to turn a failing attempt into a pass:
  - `traffic_light_controller_0001`: the parameter defaults;
  - `sync_serial_communication_0001`: the RTL file name;
  - `cache_controller_0001`: the file extension, and how long `hit` stays high;
  - `secure_apb_history_shift_register_0001`: unlock writes are driven without `pselx`/`penable`;
  - `dynamic_equalizer_0008`: the 16 noise LUT values and the instance names;
  - `rc5_0001`: only one file is compiled;
  - `elevator_control_0004`: the elevator must move at once when an overload clears, and the direction LED lags
    by one cycle.

  These 7 are in `tools/benchmark_limited_ids.txt`.
- **2 more look benchmark-limited, but the evidence is weaker.** They are listed here and left out of the IDs file:
  - `dynamic_equalizer_0001`: a 5-cycle latency and bit-exact LMS rounding, neither stated;
  - `phase_rotation_0015`: the same RTL passed 45/45 in one run and failed 4–8 of 45 in three others.
- **3 are agent-limited.**
  - `hdbn_codec_0001`: the decoder latency is stated (6 cycles) and missed.
  - `phase_rotation_0013`: arm A solved it twice; the Claude models misread the output levels.
  - `binary_search_tree_algorithms_0014`: the attempts are 1 or 2 cycles off a latency the spec gives, and Opus
    does not flag an invalid input. This one is borderline.
- **None is an environment failure.** The local reruns reproduce CI. Fable's wall-cap stops on 4 of these problems
  do not change any outcome, because its finished attempts fail the same way as the other models'.
- **What the scores look like without the 7.** On the other 79 problems, arm A scores 158/237 = 66.7% (61.6% on 86).
  Opus scores 63/79 = 79.7% (73.3%), Sonnet 75.9%, Fable 73.4% and Haiku 72.2%. Only one pass is lost: arm A's
  `rc5_0001` pass in run 3.
- **Part two: what Claude Code did that our agent did not.** 7 problems were solved by at least 2 Claude models
  and never by arm A. In 14 of arm A's 20 valid attempts on them, the agent submitted without running any
  testbench, because its reflect step accepted a clean compile, lint and synth. The passing Claude attempts mostly
  wrote a testbench with a reference model, or ran the testbench the task provided, and then fixed what it showed.
  One problem (`DES_0001`) was won by generating the tables with a script instead of typing them in. One
  (`csr_using_apb_interface_0001`) was won by a design convention: `prdata` registered and held, not combinational
  and cleared. Simulation does not explain that one.

## The twelve

Each subsection gives the class, the evidence and what a fix would take. The attempts are written
`model` or `A1`–`A3` (arm A runs 1–3). The hidden test files are quoted from the dataset record
(`harness/src/...`).

### `traffic_light_controller_0001`: benchmark-limited (strong)

The prompt asks for a `timer_module` with short and long intervals, which the top level passes in "(e.g.,
`SHORT_COUNT` and `LONG_COUNT`)". It gives no values. The hidden test `test_traffic_light_controller_top.py` counts
cycles against fixed defaults:

```
# The FSM triggers the long timer in S1. By default, LONG_COUNT_PARAM=20.
# 3) In S2, the FSM triggers the short timer. The default SHORT_COUNT_PARAM=10.
```

The seven attempts chose 4/8 (Sonnet), 20/100 (Opus), 5/20 (Haiku, A1, A3), 5/10 (A2) and 4/16 (Fable). All 7
fail a timing check: `Expected S2 => main=2, got 001` or `Expected S4 => main=4 (red), got 001`. **Counterfactual:**
the defaults alone were set to 10 and 20 in four attempts (Sonnet, Opus, Haiku, A1), and **all four pass**. No
self-written testbench could catch this, because the right values are not in the task. **Fix:** benchmark-side
only. State the defaults in the prompt, or count the problem out.

### `sync_serial_communication_0001`: benchmark-limited (strong)

The hidden `.env` compiles one file, `VERILOG_SOURCES = /code/rtl/sync_serial_communication_top.sv`. That file name
appears nowhere in the prompt, the specification or the given testbench. The top module is called
`sync_serial_communication_tx_rx`, and all 7 attempts named their file after it. The prompt also points to
`docs/sync_serial_communication_spec.md`, but the file given is `docs/sync_serial_communication_tx_rx_spec.md`. Every
attempt fails the compile (`iverilog ... /code/rtl/sync_serial_communication_top.sv` exit 1, 20 of 20 tests).
**Counterfactual:** each attempt's RTL was concatenated into `sync_serial_communication_top.sv`. Then **4 of the 4
Claude attempts pass all 20 tests**. Arm A's 3 still fail (`got_gray_out = 0, expected_gray_out = ...`), so arm A
would also have been agent-limited here. M3b's `reachable.py` kept this problem because it checks the names the
test reads, not the file paths it compiles. **Fix:** benchmark-side. `reachable.py` could also check that every
`VERILOG_SOURCES` path is given or follows from a module name.

### `cache_controller_0001`: benchmark-limited (strong)

The hidden test compiles `/code/rtl/cache_controller.sv`. The prompt asks for "a **Verilog**-based cache
controller" and names no file, so 6 of 7 attempts wrote `rtl/cache_controller.v`. The build log says
`/code/rtl/cache_controller.sv: No such file or directory`. The seventh, Opus, used `.sv`. It fails
`Failed for write hit` because the test reads `hit` 20 ns after the write has ended:

```
dut.write.value = 0
await Timer(20, unit="ns")
assert dut.hit.value == 1, "Failed for write hit"
```

The spec says only that "a hit occurs when a valid tag is found". **Counterfactuals:**
- Renaming `.v` to `.sv` turns the 6 compile failures into test failures: the 3 Claude attempts fail at the same
  write-hit check, and arm A fails `Failed for read miss`.
- In Opus's RTL, deleting the two lines that clear `hit` and `miss` every cycle, so that they hold until the next
  access, makes **the test pass**.

So two details the task never gives decide this problem. **Fix:** benchmark-side.

### `secure_apb_history_shift_register_0001`: benchmark-limited (strong)

The prompt says the security module "should use the existing 8-bit apb interface but with a different clock named
`i_capture_pulse`". The hidden test then performs the unlock writes with `pselx` and `penable` held at 0. It drives
only `paddr`, `pwdata` and `pwrite` around each capture pulse:

```
dut.paddr.value =0
dut.pwdata.value =171
dut.pwrite.value =1
dut.i_capture_pulse.value = 1
```

All 7 attempts gate the unlock on an APB transfer: `pselx & pwrite`, `pselx & penable & pwrite`, or `pselx &&
penable`. So none ever unlocks, and they fail either `control_register readback mismatch: Expected 0xb, got 0x0`
or `predict_history should shift in bit=1 at LSB`. **Counterfactual:** with the `pselx`/`penable` terms removed
from the unlock condition and nothing else changed, **Sonnet's and A2's attempts pass**. Opus's and Fable's still
fail for other reasons. A self-written testbench would use proper APB transfers and pass. **Fix:** benchmark-side.
The test is not a valid APB stimulus.

### `dynamic_equalizer_0008`: benchmark-limited (strong)

The hidden test `test_equalizer_top_harness.py` checks the AWGN output against a hard-coded table:

```
# Copy of RTL LUT in decimal
NOISE_LUT = [ 2048, -1024, 128, -3072, 1024, -2048, 3072, -128, 0, 512, -512, 256, -256, 768, -768, 0 ]
```

It also reads the instances `dut.uu_awgn_real` and `dut.uu_awgn_imag`. The AWGN spec gives neither: it says only
that "the noise values are stored in a lookup table". 3 attempts fail on the instance name (`equalizer_top contains
no child object named uu_awgn_real. Did you mean: 'u_awgn_real'?`). The other 4 fail on their own LUT values.
Opus, for example, used a Gaussian table, `4069, -1133, 5306, ...`. **Counterfactuals:**
- Renaming the instances in 3 attempts makes the two equalizer tests pass and leaves only the two AWGN tests
  failing.
- Putting the test's 16 values into Opus's LUT makes **all 4 tests pass**.

**Fix:** benchmark-side.

### `rc5_0001`: benchmark-limited (strong)

The prompt says that `rtl/` holds four cellular-automaton modules (`CA_1.sv` to `CA_4.sv`) and asks the agent to
"choose the appropriate CA design for S-box generation". The hidden `.env` compiles only
`/code/rtl/rc5_enc_16bit.sv`. 5 of 7 attempts instantiate `CA_1`, the right one, from its own file, and fail to
compile. **Counterfactual:** with `CA_1.sv` appended to `rc5_enc_16bit.sv`, **Haiku's and Fable's attempts pass**.
The other three then fail `Expected 0x35360, but got 0x37053`. That is the same error as A2, which inlined the CA:
those attempts take the S-box values from the CA stream on different cycles than the test expects
(`s = [0xAB, 0x29, 0x6E, 0xC1]`), and the prompt does not say when to sample the CA. A3 inlined the CA, sampled it
on the right cycles and passed, at 464 s, close to the wall cap. So the problem can be solved, but only by an
attempt that happens to inline the module. **Fix:** benchmark-side: compile the given CA files, or say that the
design must be one file.

### `elevator_control_0004`: benchmark-limited (strong)

The prompt says that in `DOOR_OPEN` the doors stay open "for a predefined duration", and "indefinitely until the
overload clears" while overloaded. It also says `up_led = 1` "when the elevator is moving up (`MOVING_UP`
state)". The hidden `elevator_control.py` clears the overload, waits 50 ns (5 cycles), and then requires `up_led`
on every cycle until the car reaches floor 4:

```
dut.overload.value = 0
await Timer(50, unit="ns")
while dut.current_floor.value != 4:
    await RisingEdge(dut.clk)
    await check_direction_leds(dut, "up")
```

The door time in simulation is 5000 cycles. All 7 attempts keep the doors open after the overload clears (Opus
restarts the door timer), and all 7 fail `up_led not active while moving up` for every floor count. **Counterfactual
on Opus's RTL:**
- Leaving `DOOR_OPEN` as soon as the overload clears is not enough. It still fails on the cycle the car arrives,
  because the given FSM changes the floor and the state on the same edge, and a literal `up_led = (state ==
  MOVING_UP)` is already 0 there.
- Adding a one-cycle registered `up_led`/`down_led` as well makes **all 4 hidden tests pass**. The LED change alone does
  not.

**Fix:** benchmark-side. The second behaviour contradicts the literal LED definition in the prompt.

### `dynamic_equalizer_0001`: benchmark-limited (borderline, not in the IDs file)

The hidden test drives `desired = input` and requires a bit-exact output equal to the input 5 cycles earlier
(`expected_real = in_history_real[i - 5]`, with the comment "After 3 cycles"). Because the failure list is reset on
every iteration, only the last sample decides the result. The specification gives no latency and no fixed-point
rounding for the update μ·e·x. It says only that the centre tap starts at 1.0 and that MU selects a shift. Two
attempts get the latency and the centre tap right: Haiku and A2 pass the quadrant test. They still miss the
identity test by a few LSB (`Expected: -8192, Got: -8189`), because the LMS update moves the coefficients when the
error is not aligned with the output. The other 5 are further off, for example Fable at
`Expected: 8192, Got: 16384`. Exact identity needs both an unstated latency and an unstated rounding and alignment
rule. No counterfactual was found that passes without redesigning the update, so the evidence is not strong.
**Fix:** benchmark-side if confirmed. An agent can at least measure the latency its own design has, but it cannot
learn the expected one.

### `phase_rotation_0015`: benchmark-limited, non-deterministic test (borderline, not in the IDs file)

The test draws random widths, enables and `i_bypass` for each of 45 simulations, and checks
`assert all(diff <= 1 for diff in angle_differences)`. That check is one-sided: any negative error passes.
Sonnet's RTL failed 5 of 45 in CI (run 40201705867), passed **45/45** in the first local rerun, and failed 8, 5 and
4 of 45 in three more reruns. Every failure falls in the first 1–4 compared cycles after reset (60–90 ns). No run
fails after that (`passed` at 130 ns in 118 of 118 passing simulations). So Sonnet's design matches the test's model
in the steady state, and the result depends on random stimulus while the pipeline fills. The other attempts are
closer to wrong: Opus fails 32/45 and Haiku 36/45, while Fable (42/45) and A1 (43/45) are near. Whether a fully
correct design would pass every time cannot be shown without the reference. **Fix:** report it with repeats, or
count it out. A verify step should look at how its design behaves during warm-up, but it cannot remove the test's
randomness.

### `hdbn_codec_0001`: agent-limited

The specification states the latency: "Decoder: 6 clock cycles (input sync + 5-stage processing)". The hidden
`hdbn_decoder_only_test` checks exactly that: the first decoded bit at the 6th cycle. 6 of the 7 attempts output 0
there (`[DEC] Bit mismatch at cycle 5: Expected 1, got 0`). Their decoders are slower than the spec. A3 meets the
decoder latency but fails both loopback tests (767 and 705 bit errors), so its encoder or decoder logic is wrong.
The odd reset expectation (`code_error_out should be HIGH Initially after reset if input is valid`) follows from
the stated zero-count error, since the pipeline outputs zeros just after reset. 4 attempts pass it, so it is not the
blocker. **Would the agents' own testbenches have caught it?** Yes, if they had measured the stated 6-cycle latency.
They tested round trips at their own latency instead. **Fix:** agent-side. Check every number the spec states
(latency, widths, counts) in the testbench.

### `phase_rotation_0013`: agent-limited

The prompt is vague: "`o_data` must receive a result based on accumulated sums of `i_sample_pos` and `i_threshold`".
But the original `slicer` has four regions and four outputs, and the test's model keeps them: `±(sample +
threshold)` outside the thresholds and `±sample` inside. A1 and A2 implemented that and pass, also in the local
reruns. A3 used `>` where the original has `>=` at the boundaries and fails `Expected 17, but got -17`. All four
Claude models made the inner levels sums too, for example Opus's `th_pos + smp_neg`, and fail with errors like
`Expected -24, but got -1`. **Would their own testbenches have caught it?** No, because each one checked its own
reading. Keeping the original module's region structure and comparisons when rewriting it would have. **Fix:**
agent-side: when modifying a given module, keep its existing behaviour unless the task says to change it.

### `binary_search_tree_algorithms_0014`: agent-limited (borderline)

The hidden test checks the latency to the cycle, but only for the two 15-element configurations. For a search of
the largest key with sorting, it expects `4 + ((N-1)*2+4) + build + sort` = 236 cycles. The specification says
"Total overhead = 3 clock cycles" under its own way of counting, which may differ from the test's by one cycle.
- Fable and Opus give 237 and Sonnet 238 (`Latency incorrect. Got: 237, Expected: 236.0`).
- Haiku and arm A are far off (163–192 cycles) and also return a wrong `key_position`.
- Opus also never raises `operation_invalid` for the configuration whose input contains the all-ones invalid key,
  which the specification requires. The hidden test then loops forever: the CI report is cut off, and a local
  rerun had to be killed.
- **Counterfactual:** Opus's RTL, with that configuration removed from the test runner, passes the first two
  configurations and fails both 15-element ones at 237.

Three models are one or two cycles off, and one model misses a stated rule, so this is agent-limited. The one-cycle
doubt about the test's counting keeps it borderline. **Would their own testbenches have caught it?** Partly. The
invalid-input case is in the spec, and a test of it would have caught Opus's bug. The cycle count needs the
submodule latencies, which the given modules make measurable. **Fix:** agent-side. Test every stated error path,
and count cycles against the spec's formula.

## Part two: problems Claude Code solved and arm A did not

These are the 7 problems solved by at least 2 of the 4 Claude models and never by arm A. Arm A's run 3 on
`nmea_gps_0008` was an `llm_error` row, so arm A has 20 valid attempts here. In 14 of the 20 the agent submitted
with **no testbench run at all** (`testbench_run` absent from the trace): reflect said `submit` after compile, lint
and synth passed. Examples: "Both RTL modules compile, pass lint/elaboration, and synthesize without errors or
warnings" (`ethernet_mii_0006`, A1); "The implementation compiles, passes lint, and is synthesizable" (`csr_*`,
A1).

| Problem | Claude passes | What the passing Claude attempts did | What arm A did |
|---|---|---|---|
| `nmea_gps_0008` | 4/4 | **Ran the given `verif/nmea_decoder_tb.sv`** and debugged with `$display` monitors until "All six checks in the supplied testbench pass" (Sonnet, 11 turns; Opus, 18 turns, plus its own `tb2.sv`) | A1 submitted at turn 1 without running the given testbench (`Expected 0x3132, got 0`); A2 ran its own testbench but missed the overflow case |
| `DES_0001` | 3/4 | **Generated the S-boxes and permutations with a Python script that parses `docs/S_box_creation.md`**, then ran the given `tb_des_enc.sv` until all 7 checks pass (Opus, Sonnet, Fable) | Copied the tables by hand. The given testbench failed on every vector in each of its 5 runs in A1, the transcription errors were never found ("The S8 row 3 constant has a typo"), and it ran out of 10 turns |
| `binary_search_tree_algorithms_0001` | 2/4 | Wrote a randomized cocotb testbench with a Python reference model, ran the 3 spec examples plus 3000 random trees at 7 sizes, and fixed its own test vectors (Opus) | Submitted at turn 1 in all 3 runs, no testbench. Missed the "reset outputs after deletion" requirement (`Key [...] should be modified as [63, ...]`) |
| `ethernet_mii_0006` | 2/4 | Read the whole spec, wrote a testbench with a reference model covering padding, backpressure, MAC programming and interrupts, and fixed the bugs it found (Haiku, 15 turns) | Submitted at turn 1 or 2, no testbench (`AXI output mismatch!`) |
| `lfsr_0005` | 2/4 | **Made a one-line fix to the given taps** (`[4,3,2,0]` to `[5,4,3,0]`) and checked the full 65 535-state period from `FFFF` (Opus, Haiku) | Rewrote the module. Its testbench checked only the 4-row table, not the maximal-length property the hidden test checks (`LFSR does not support maximal length sequence`) |
| `queue_0001` | 2/4 | Randomized self-checking testbench against a model at 5 parameter settings; fixed the write-while-full bug it found (Opus) | No testbench in 3 runs. 2 of 3 chose `DBITS = 8`, while the hidden test drives 32-bit data (`Int value (2779096485) out of range for ... 8-bit signal`). The default width is not in the spec, so Claude's `DBITS` 32 or 64 was partly luck |
| `csr_using_apb_interface_0001` | 2/4 | **Registered `prdata` and held it.** Sonnet passed without simulating ("I did not write or run a testbench") | Combinational `prdata`, cleared outside `READ_STATE`. The hidden test reads it 2 cycles after the transfer (`DATA_REG read/write mismatch`). An APB testbench sampling in the access phase would not have caught it |

**The concrete behaviour brief 10 should add.** Before submit, the agent should:
1. run the task's own testbench when there is one;
2. otherwise write a testbench with a small reference model, covering the spec's examples, its error paths and any
   property it names (period, latency, full and empty), and run it;
3. treat a failing or missing simulation as "edit again", never as "submit".

Clean compile, lint and synth is the signal arm A stops on, and in these 7 problems it was never enough. Two
smaller lessons:
- when a spec gives a table, generate the constants from the document with a script instead of retyping them
  (`DES_0001`);
- when fixing a given module, change the least code possible (`lfsr_0005`).

The verify step cannot win the 7 benchmark-limited problems above. For those, the missing information is not in the
task.

## Summary

| Problem | Class | Evidence | Counterfactual | Own testbench would catch? |
|---|---|---|---|---|
| `traffic_light_controller_0001` | benchmark-limited (strong) | test assumes `SHORT=10`, `LONG=20`; prompt gives no values | 4/4 attempts pass with those defaults | no |
| `sync_serial_communication_0001` | benchmark-limited (strong) | compiles `sync_serial_communication_top.sv`, named nowhere | 4/4 Claude attempts pass after a rename (arm A still fails) | no |
| `cache_controller_0001` | benchmark-limited (strong) | `.sv` required, prompt says "Verilog"; `hit` must hold after the access | Opus passes with `hit`/`miss` held | no |
| `secure_apb_history_shift_register_0001` | benchmark-limited (strong) | unlock driven without `pselx`/`penable` | 2/4 pass with the psel gating removed | no |
| `dynamic_equalizer_0008` | benchmark-limited (strong) | test's LUT values and `uu_awgn_*` names, given nowhere | Opus passes with the test's LUT | no |
| `rc5_0001` | benchmark-limited (strong) | only `rc5_enc_16bit.sv` compiled; given `CA_1.sv` not | 2/5 pass with `CA_1` appended | no |
| `elevator_control_0004` | benchmark-limited (strong) | resume within 5 cycles of overload clear, LED one cycle late | Opus passes with both | no |
| `dynamic_equalizer_0001` | benchmark-limited (borderline) | 5-cycle latency and bit-exact LMS rounding, unstated | none found | partly (latency) |
| `phase_rotation_0015` | benchmark-limited (borderline: non-deterministic) | same RTL 45/45 once, 4–8 failures in 3 other runs, all during warm-up | Sonnet passes 1 run in 4 | no |
| `hdbn_codec_0001` | agent-limited | stated 6-cycle decoder latency missed by 6/7 | — | yes |
| `phase_rotation_0013` | agent-limited | arm A passes 2/3; Claude changed the original levels | — | no (keeping the original structure would) |
| `binary_search_tree_algorithms_0014` | agent-limited (borderline) | latency 1–2 cycles over; invalid-input flag missing (Opus) | Opus fails at 237 vs 236 without the invalid case | partly |

Class counts: **benchmark-limited 9 (7 strong, 2 borderline), environment 0, agent-limited 3 (1 borderline)**.
Notes:
- `tools/benchmark_limited_ids.txt` lists only the 7 strong ones.
- Later experiments can report a score that excludes them next to the full-86 score, never in place of it.
- Two hidden tests loop forever when the DUT never completes: `binary_search_tree_algorithms_0014` with Opus's RTL,
  and `elevator_control_0004` with A2's. They rely on the harness's outer timeout. They are not counted as
  environment failures, because the RTL is what fails.
