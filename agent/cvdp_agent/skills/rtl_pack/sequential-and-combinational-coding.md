# sequential-and-combinational-coding

## When it applies

Every time you write an `always` block or a continuous assignment. Load it when unsure whether to use blocking or
nonblocking assignment, when a lint tool reports a latch, or when simulation and intent disagree by one cycle.

## Key rules

1. **Registers: `always_ff @(posedge clk ...)` with nonblocking `<=` only.**
2. **Combinational logic: `always_comb` with blocking `=` only**, or `assign`.
3. **Never assign the same variable from two `always` blocks.** One driver per signal.
4. **Never mix `=` and `<=` in one block.**
5. **In `always_comb`, give every output a value on every path.** Put default assignments at the top of the block,
   then override. A path that leaves a variable unassigned infers a latch.
6. **Every `case` in combinational logic needs a `default`** (or full coverage plus top-of-block defaults).
7. **Use `logic` for everything** except multiply-driven nets (tri-state, which you should avoid in RTL).
8. **Separate next-state logic and registers** when non-trivial: `x_d` in `always_comb`, `x_q <= x_d`.
9. **Size every literal** (`8'd0`, `'0`, `'1`) and every operand. Unsized `0` is 32 bits and hides width bugs.
10. **Use `unique`/`priority case` only when you mean it:** `unique` claims the items are exclusive and complete,
    and synthesis may optimise on that claim. A plain `case` with `default` is the safe choice.
11. **In `always_comb`, do not read a variable before the block assigns it** (feedback or a sim/synth mismatch).

## Why nonblocking for registers

With `<=`, all right-hand sides are evaluated before any register updates, as in hardware. With `=` in a clocked
block, statement order decides whether later reads see old or new values: shift registers collapse and blocks
race.

## Idiom

```systemverilog
module seq_comb_idiom (
  input  logic       clk,
  input  logic       rst_n,
  input  logic [1:0] sel,
  input  logic [7:0] a, b,
  output logic [7:0] y_q
);
  logic [7:0] y_d;

  always_comb begin
    y_d = y_q;              // default: hold (no latch, since y_q is a register)
    case (sel)
      2'd0:    y_d = a;
      2'd1:    y_d = b;
      2'd2:    y_d = a + b;
      default: y_d = y_q;
    endcase
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) y_q <= '0;
    else        y_q <= y_d;
  end
endmodule
```

## Usual defaults when the spec is silent (defaults, not laws)

- A held value is held in a register (as above), not by an implied latch.
- `if` without `else` in `always_ff` means "hold"; that is fine and intended.
- Use `always_comb`, not `always @*`, in SystemVerilog: it also checks for multiple drivers and runs once at time
  zero.

## Pitfalls

- A latch from an incomplete `if` in `always_comb` (Verilator: `LATCH`; Yosys: "Latch inferred").
- An extra cycle from putting combinational logic in `always_ff`; a missing one from using `assign` for a
  value meant to be registered.
- A blocking temporary in a clocked block that another block also reads: race.
- Width truncation: `assign sum = a + b;` with `sum` the same width as `a` drops the carry. Size the result.
- Comparisons between signed and unsigned operands silently become unsigned (see `arithmetic-and-widths`).

## How to check it

- Run `verilator --lint-only -Wall top.sv` and treat `LATCH`, `MULTIDRIVEN`, `WIDTH`, `BLKSEQ`, `COMBDLY` and
  `UNOPTFLAT` warnings as bugs unless you can explain them.
- Run `iverilog -g2012 -Wall` as a second opinion; optionally Yosys `synth; stat` and look for latch cells.

## Sources

- Cummings, C. E., "Nonblocking Assignments in Verilog Synthesis, Coding Styles That Kill!", SNUG San Jose 2000.
- IEEE Std 1800-2017, *SystemVerilog Language Reference Manual*, clauses 9.2.2 (always_comb, always_ff) and 10.4
  (blocking and nonblocking assignments), 12.5 (unique/priority).
- Sutherland, S., Davidmann, S. and Flake, P., *SystemVerilog for Design*, 2nd ed., Springer.
