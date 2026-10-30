# reset-strategy

## When it applies

Whenever you write a register (`always_ff`) and the spec mentions reset, or when a spec names a reset port but
does not say how it behaves.

## Key rules

1. **Follow the spec first.** If it states polarity and sync/async, do exactly that.
2. **Infer polarity from the name** when the spec is silent: a suffix `_n`, `n`, `_b` or `_l` (`rst_n`,
   `aresetn`) means active low; plain `rst` or `reset` means active high.
3. **Write the reset in the sensitivity list only for an asynchronous reset.**
   - Async active low: `always_ff @(posedge clk or negedge rst_n) if (!rst_n) ...`
   - Async active high: `always_ff @(posedge clk or posedge rst) if (rst) ...`
   - Sync: `always_ff @(posedge clk) if (rst) ...`
4. **The reset branch must come first** and be the whole `if`; the normal behaviour goes in the `else`. Synthesis
   tools recognise only this shape for an asynchronous reset.
5. **Reset every control register**: state registers, counters, valid bits, flags, pointers. Datapath registers
   whose value is ignored until a valid bit is set may be left unreset, but if the spec lists a reset value for
   an output, reset it.
6. **Reset values come from the spec.** Without one, reset to zero, and reset FSMs to the idle state.
7. **Do not mix** reset and unreset registers in one `always_ff`: the unreset ones gain an unintended hold
   during reset. Use separate blocks.
8. **Never use `initial` as a reset;** it acts only at time zero.
9. **Release an external async reset synchronously** (async assert, sync deassert) when you generate a reset for
   other logic. Inside a given module, use the reset port as given.

## Usual defaults when the spec is silent (defaults, not laws)

Practice genuinely varies:

- ASIC and many IP libraries: **asynchronous, active-low**, because it works without a running clock.
- FPGA vendor guides: often **synchronous, active-high**, for simpler timing and better use of flip-flop
  resources.
- Rule here: `*_n` port: **async active-low**; `rst`/`reset`: **sync active-high**, unless the spec or
  surrounding code says otherwise. A test that holds reset over several edges passes with either; a test that
  checks outputs *before* the first clock edge needs async.

## Idiom: reset synchroniser (async assert, sync release)

```systemverilog
module reset_sync (
  input  logic clk,
  input  logic arst_n,   // raw asynchronous reset
  output logic rst_n     // safe to use in clk domain
);
  logic meta;
  always_ff @(posedge clk or negedge arst_n) begin
    if (!arst_n) {rst_n, meta} <= 2'b00;
    else         {rst_n, meta} <= {meta, 1'b1};
  end
endmodule
```

## Pitfalls

- Wrong polarity: the design sits in reset for the whole test.
- Wrong edge in the sensitivity list (`posedge rst_n`).
- Logic before the `if (!rst_n)`, or reset read again in the `else`.
- An unreset valid or busy flag: the design starts at X and X propagates.

## How to check it

- In every `always_ff`, reset is the first `if` and the sensitivity list matches sync/async.
- After 2 to 5 cycles of reset every output equals its reset value and none is X.
- Reset asserted mid-operation returns the design cleanly to idle.

## Sources

- Cummings, C. E. and Mills, D., "Synchronous Resets? Asynchronous Resets? I am so confused! How will I ever know
  which to use?", SNUG 2002.
- Cummings, C. E., Mills, D. and Golson, S., "Asynchronous & Synchronous Reset Design Techniques - Part Deux",
  SNUG Boston 2003.
- FPGA vendor HDL coding guides (for example the AMD UltraFast Design Methodology Guide) on synchronous resets.
