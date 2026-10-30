# clock-domain-crossing

## When it applies

When a design has two or more clocks, an input that is asynchronous to the clock (a button, an external
interrupt, a signal from another chip), or the spec says "synchroniser", "async FIFO", "CDC", "metastability",
or "gray code".

## Key rules

1. **Never sample an asynchronous signal with logic directly.** Pass a single-bit level through a two-flop
   synchroniser in the destination domain first. Use three flops only if the spec asks (very high clock rates).
2. **Drive a crossing straight from a source-domain flip-flop,** never from combinational logic (glitches).
3. **Never synchronise a multi-bit bus bit by bit.** The bits can resolve on different cycles and the destination
   sees a value that never existed. Instead use one of:
   - Gray-coded values that change by one bit per step (counters, FIFO pointers);
   - a handshake: hold the data stable, synchronise a single request bit, sample the data when the request arrives
     (data stays constant for the whole crossing);
   - an asynchronous FIFO.
4. **Pulses** from a fast domain can be missed by a slow one: toggle a flop in the source, synchronise the
   toggle, edge-detect it in the destination.
5. **Reconvergence:** separately synchronised signals can arrive a cycle apart; never rely on their alignment.
6. **Async FIFO:** binary and Gray pointers in each domain; the Gray write pointer is synchronised into the read
   domain for `empty`, the read pointer into the write domain for `full`. Flags are late, never wrong.
7. **Name synchroniser flops clearly** (`*_sync1`, `*_sync2`).

## Usual defaults when the spec is silent (defaults, not laws)

- Two-flop synchroniser, reset to the inactive value.
- Async FIFO depth a power of two, at least 8 for unrelated clocks.
- Gray code: `gray = bin ^ (bin >> 1)`; back to binary: `bin[MSB] = gray[MSB]`,
  `bin[i] = bin[i+1] ^ gray[i]` (a loop from the MSB down).
- Full in Gray form: the synchronised read pointer equals the write pointer with its two MSBs inverted.

## Idiom: two-flop synchroniser and toggle pulse crossing

```systemverilog
module sync_2ff (
  input  logic clk_dst, rst_dst_n,
  input  logic d_async,
  output logic q
);
  logic s1;
  always_ff @(posedge clk_dst or negedge rst_dst_n) begin
    if (!rst_dst_n) {q, s1} <= 2'b00;
    else            {q, s1} <= {s1, d_async};
  end
endmodule

module pulse_cdc (
  input  logic clk_src, rst_src_n, pulse_src,
  input  logic clk_dst, rst_dst_n,
  output logic pulse_dst
);
  logic tog_src, tog_dst, tog_dst_d;
  always_ff @(posedge clk_src or negedge rst_src_n)
    if (!rst_src_n)     tog_src <= 1'b0;
    else if (pulse_src) tog_src <= ~tog_src;

  sync_2ff u_sync (.clk_dst, .rst_dst_n, .d_async(tog_src), .q(tog_dst));

  always_ff @(posedge clk_dst or negedge rst_dst_n)
    if (!rst_dst_n) tog_dst_d <= 1'b0;
    else            tog_dst_d <= tog_dst;

  assign pulse_dst = tog_dst ^ tog_dst_d;
endmodule
```

## Pitfalls

- Synchronising a binary counter (use Gray), or a synchroniser fed from combinational logic.
- Toggle-scheme pulses closer than about three destination cycles merge; use a handshake or FIFO.
- Gray FIFO with a non-power-of-two depth: adjacency breaks at the wrap.
- A synchronised signal arrives 2 to 3 destination cycles late; tests must allow it.
- Simulation does not show metastability: correctness rests on structure.

## How to check it

- List every crossing signal and its scheme; lint does not check CDC.
- Simulate with unrelated clock periods (for example 10 ns and 7.3 ns).
- Async FIFO: scoreboard with random push/pop in both domains.

## Sources

- Cummings, C. E., "Clock Domain Crossing (CDC) Design & Verification Techniques Using SystemVerilog", SNUG Boston
  2008.
- Cummings, C. E., "Simulation and Synthesis Techniques for Asynchronous FIFO Design", SNUG San Jose 2002.
- Ginosar, R., "Metastability and Synchronizers: A Tutorial", IEEE Design & Test of Computers, 2011.
