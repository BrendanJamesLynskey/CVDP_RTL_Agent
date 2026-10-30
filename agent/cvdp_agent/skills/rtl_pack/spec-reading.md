# spec-reading

## When it applies

At the start of every RTL task, before writing any code. Use it again whenever the spec seems to contradict itself
or a test result surprises you.

## Key rules

1. **Read the whole spec once without coding,** then extract the items below into a short working list.
2. **Extract the interface exactly.** For every port write: name, direction, width, signedness, and which clock it
   belongs to. Copy module, port and parameter names exactly, including case and suffixes. Never add, rename or
   drop a port.
3. **Extract parameters and their defaults.** Note which widths depend on which parameter (for example
   `ADDR_W = $clog2(DEPTH)`).
4. **Extract the timing contract.** For each output answer:
   - Is it combinational from inputs, or registered?
   - Latency: how many clock edges from the input being sampled to the output being valid? "Next cycle" means one
     register stage. "Same cycle" means combinational.
   - Throughput: can a new input be accepted every cycle, or is there a busy period?
   - How long is an output held: one cycle (a pulse) or until the next event (a level)?
5. **Extract reset behaviour.** Polarity (active high or low), synchronous or asynchronous, and the value of every
   register and output after reset. Note whether outputs must be valid *during* reset.
6. **Extract corner cases the spec names**: overflow, wrap, empty/full, simultaneous events (read and write in the
   same cycle, start while busy), illegal inputs.
7. **Use worked examples, tables and waveforms;** they are often more precise than prose. If they disagree with
   the prose, the example usually reflects the intent: prefer it and record the conflict.
8. **List ambiguities explicitly.** Write each one as a question, then write the assumption you chose and why.
   Choose the assumption that is (a) the industry default (see the other skills), (b) the simplest to implement,
   and (c) consistent with every other statement in the spec.
9. **Put the assumptions in a comment block** at the top of the module.

## Working list template

```text
MODULE: name, parameters (defaults)
PORTS:  name | dir | width | signed? | clock domain | meaning
CLOCK/RESET: clk edge, reset name, polarity, sync/async, reset values
TIMING: output -> comb/reg, latency N, throughput, pulse/level
BEHAVIOUR: numbered rules, one per sentence of the spec
CORNERS: overflow, empty/full, simultaneous events, illegal input
AMBIGUITIES: Q -> assumption (reason)
```

## Usual defaults when the spec is silent (defaults, not laws)

- Clock: rising edge (`posedge clk`).
- Reset: the port name tells you. `rst_n`, `resetn`, `aresetn` mean active low; `rst`, `reset` mean active high.
  Sync versus async varies; see `reset-strategy`.
- Outputs of a sequential block are registered unless the spec says "combinational" or "same cycle".
- A "pulse" or "strobe" lasts exactly one clock cycle.
- A "done" or "valid" without further words: a one-cycle pulse when the result first appears.
- Unsigned arithmetic unless a port is described as signed or two's complement.
- Bit 0 is the least significant bit; vectors are declared `[W-1:0]`.
- "Enable" means the register holds its value when the enable is low.

## Pitfalls

- Inventing extra behaviour (extra ports, extra error states) that a test does not expect.
- Off-by-one latency: counting a register you did not intend, or forgetting one the spec implied.
- Treating "after N cycles" loosely: decide whether cycle 0 is the cycle the input is sampled.
- Ignoring widths in examples (an 8-bit example result may imply wrap-around, not saturation).

## How to check it

- Every sentence of the spec maps to at least one rule, port or assumption in your list.
- The module header matches the PORTS row: names, widths, directions.
- A cycle-by-cycle table of one spec example matches what your design produces.

## Sources

- Harris, D. M. and Harris, S. L., *Digital Design and Computer Architecture*, Morgan Kaufmann (chapters on
  sequential logic and timing).
- Keating, M. and Bricaud, P., *Reuse Methodology Manual for System-on-a-Chip Designs*, Springer.
- Bergeron, J., *Writing Testbenches: Functional Verification of HDL Models*, Springer (verification plans).
