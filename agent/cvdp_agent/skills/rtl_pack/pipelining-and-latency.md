# pipelining-and-latency

## When it applies

When the spec gives a latency in cycles, says "pipelined", "one result per cycle", "registered output", or when a
datapath (multiplier, adder tree, filter, CORDIC) must meet a clock rate. Also when a test fails by exactly one or
two cycles.

## Key rules

1. **Latency = number of register stages between sampling the input and presenting the output.** A
   combinational output has latency 0. One `always_ff` between input and output gives latency 1.
2. **Count precisely:** the input is sampled at edge 1; with latency N the output is visible after edge N.
3. **Carry a valid bit with the data through every stage** (a valid shift register); `out_valid` is its last bit.
4. **Delay side-band signals equally** (tags, `last`, IDs) so they stay aligned with the data.
5. **Throughput**: a fully pipelined design accepts one input per cycle. A multi-cycle (iterative) design accepts
   a new input only when not busy; expose `busy` or `ready` and say so.
6. **Stall handling**: either no stalls (simplest; valid just shifts), a global enable that freezes every stage, or
   per-stage valid/ready (see `valid-ready-handshake`). Pick the simplest that meets the spec.
7. **Cut after wide multiplies and adds;** balance logic depth between stages.
8. **Match the specified latency exactly,** padding with delay registers if your design is faster.

## Usual defaults when the spec is silent (defaults, not laws)

- "Registered output" means latency 1 from the inputs.
- No stall/enable input means the pipeline always advances.
- Data registers in a pipeline need not be reset; valid registers must be.
- When a latency is not given, keep it minimal and state it in the header comment.

## Idiom: fixed-latency pipeline with valid shift

```systemverilog
module pipe_mac #(parameter int W = 8) (
  input  logic                 clk, rst_n,
  input  logic                 in_valid,
  input  logic [W-1:0]         a, b,
  input  logic [2*W-1:0]       c,
  output logic                 out_valid,
  output logic [2*W:0]         y          // latency 2: y = a*b + c
);
  logic [2*W-1:0] prod_q, c_q;
  logic [1:0]     vld_q;

  always_ff @(posedge clk) begin
    prod_q <= a * b;        // stage 1
    c_q    <= c;            // keep c aligned with the product
    y      <= {1'b0, prod_q} + {1'b0, c_q};   // stage 2
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) vld_q <= '0;
    else        vld_q <= {vld_q[0], in_valid};
  end
  assign out_valid = vld_q[1];
endmodule
```

To pad latency, add a delay line: an unpacked array of registers shifted every cycle, or more `vld_q`-style
stages.

## Pitfalls

- Off-by-one latency from an extra input register or a missing output register.
- Side-band signals not delayed, pairing with the wrong data.
- Mixing stages: using a stage's input in that stage's output expression.
- An iterative unit silently dropping a start while busy: state the behaviour.
- A parameterised delay of 0 stages: guard it with a `generate if`.

## How to check it

- One isolated input: count edges until `out_valid`.
- Inputs every cycle: results every cycle, in order, checked against a queue-based reference model.

## Sources

- Patterson, D. A. and Hennessy, J. L., *Computer Organization and Design*, Morgan Kaufmann (pipelining
  principles).
- Harris and Harris, *Digital Design and Computer Architecture*, ch. 3 (parallelism and pipelining).
- Parhi, K. K., *VLSI Digital Signal Processing Systems: Design and Implementation*, Wiley (retiming).
