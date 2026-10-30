# synthesisable-subset-and-parameters

## When it applies

When writing any RTL that must synthesise (Yosys, FPGA or ASIC flows) and simulate in Verilator and Icarus; when
using parameters, `generate`, loops, functions, packages or structs; when a tool rejects a construct.

## Key rules: stay in the synthesisable subset

1. **No `#` delays, `wait`, `fork`, `force`, reals or dynamic types** (classes, queues, strings) in RTL;
   `initial` only for memory/ROM initialisation where the flow supports it.
2. **Loops need constant bounds;** they unroll into parallel hardware, not iterations over time. For "repeat
   until", use an FSM and a counter.
3. **One clock edge per `always_ff`,** plus at most an async reset.
4. **No internal tri-states (`'z`);** use multiplexers.
5. **Avoid `'x` defaults;** they make simulation optimistic. Prefer a defined value.
6. **`function automatic` is fine** for combinational helpers; tasks with timing are not.

## Key rules: parameters and generate

1. **Use `parameter int` with a sensible default** for widths and depths; `localparam` for derived values
   (`localparam int AW = $clog2(DEPTH);`).
2. **Use the exact parameter names from the spec.** Keep them overridable (in the `#(...)` header).
3. **`$clog2(1)` is 0**: a width of `$clog2(N)` breaks when N = 1. Guard with `N > 1 ? $clog2(N) : 1` or state
   the minimum N.
4. **`generate` for structural replication and conditional hardware**: `for (genvar i = 0; ...) begin : g_name`
   and `if (P) begin : g_name`. Name every generate block.
5. **Variable part-select:** `x[base +: W]` with constant W, not `x[hi:lo]` with variable bounds.
6. **Packed structs and enums** are fine; put shared types in a `package`, compiled first.
7. **Prefer packed 2-D ports** (`input logic [N-1:0][W-1:0] d`) to unpacked port arrays: more portable and
   easier to access from cocotb.
8. **Reductions** (`&x`, `|x`, `^x`) are synthesisable; `$countones` support varies, a loop sum always works.

## Usual defaults when the spec is silent (defaults, not laws)

- `` `default_nettype none `` at the top catches typos; restore `` `default_nettype wire `` at the end.
- File name = module name, one module per file, unless the task asks otherwise.

## Idiom: parameterised generate with a reduction

```systemverilog
`default_nettype none
module par_or_tree #(parameter int N = 4, parameter int W = 8) (
  input  wire logic [N-1:0][W-1:0] d,
  input  wire logic [N-1:0]        en,
  output      logic [W-1:0]        y,
  output      logic [$clog2(N+1)-1:0] n_en
);
  logic [N-1:0][W-1:0] masked;
  for (genvar i = 0; i < N; i++) begin : g_mask
    assign masked[i] = en[i] ? d[i] : '0;
  end

  always_comb begin
    y    = '0;
    n_en = '0;
    for (int i = 0; i < N; i++) begin
      y    = y | masked[i];
      n_en = n_en + {{($bits(n_en)-1){1'b0}}, en[i]};
    end
  end
endmodule
`default_nettype wire
```

## Pitfalls

- Unnamed generate blocks (tool-specific hierarchical names).
- `localparam` where the spec expects an overridable `parameter`.
- With `default_nettype none`, an input declared only as `input logic` has no net type under the standard's
  rules; declare inputs as `input wire logic` (as in the idiom) to stay portable.
- Interfaces are weakly supported in open tools (Icarus especially); avoid unless the spec uses them. If Icarus
  rejects a construct, rewrite it more plainly.

## How to check it

- Lint in both Verilator and Icarus (`-g2012`); they catch different things.
- Elaborate with the smallest and a larger parameter value to catch width bugs.

## Sources

- IEEE Std 1800-2017, clauses 6.20 (parameters), 27 (generate constructs), 13.4 (functions), 20.8 (`$clog2`).
- Sutherland, Davidmann and Flake, *SystemVerilog for Design*, Springer.
- Sutherland, S. and Mills, D., "Synthesizing SystemVerilog: Busting the Myth that SystemVerilog is only for
  Verification", SNUG Silicon Valley 2013.
- Yosys and Verilator manuals (supported language subsets).
