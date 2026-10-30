# counters-timers-and-edges

## When it applies

When the spec asks for a counter, timer, prescaler, clock divider, PWM, watchdog, timeout, edge or pulse detector,
debouncer, or "wait N cycles" behaviour.

## Key rules

1. **Decide the count range exactly.** "Counts 0 to N-1 then wraps" (modulo N) versus "counts to N". A modulo-N
   counter compares with `N-1` and resets to 0 on that cycle.
2. **Width**: a counter that must hold value N needs `$clog2(N+1)` bits; modulo N needs `$clog2(N)` bits (at
   least 1).
3. **Priority of controls** (state it): the usual order is reset > load > clear > enable > count. Write it as an
   `if / else if` chain in that order.
4. **Terminal count:** combinational (`tc = (cnt == N-1) && en`, same cycle as the wrap) or registered (one
   cycle later); match the spec's timing.
5. **No logic-derived clocks** unless the spec asks for a divided clock output: use a clock *enable* pulse and
   run everything on the main clock.
6. **Edge detection:** `d_q <= d`; rise = `d & ~d_q`, fall = `~d & d_q`, any = `d ^ d_q`. Synchronise an
   asynchronous input first.
7. **Debounce:** synchronise, then accept a new level only after M consecutive cycles at that level.
8. **PWM:** counter 0..PERIOD-1, output `cnt < duty`; the duty register must hold PERIOD (always high).
9. **Up/down counters:** define wrap or saturate at both limits.

## Usual defaults when the spec is silent (defaults, not laws)

- Reset to 0, count up, wrap; enable low holds.
- Edge-detector output: one-cycle pulse.
- "Divide by N": 50% duty for even N; for odd N state the duty chosen.

## Idiom: modulo-N counter with clock-enable pulse

```systemverilog
module mod_counter #(
  parameter  int N  = 10,
  localparam int CW = (N > 1) ? $clog2(N) : 1
) (
  input  logic          clk, rst_n,
  input  logic          clr,
  input  logic          en,
  output logic [CW-1:0] cnt,
  output logic          tick    // one-cycle pulse on wrap
);
  localparam logic [CW-1:0] LAST = CW'(N - 1);
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n)              cnt <= '0;
    else if (clr)            cnt <= '0;
    else if (en) begin
      if (cnt == LAST)       cnt <= '0;
      else                   cnt <= cnt + 1'b1;
    end
  end
  assign tick = en && (cnt == LAST);
endmodule
```

Edge detect on an asynchronous input:

```systemverilog
module edge_detect (
  input  logic clk, rst_n,
  input  logic din_async,
  output logic rise, fall
);
  logic s1, s2, s3;
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) {s3, s2, s1} <= 3'b000;
    else        {s3, s2, s1} <= {s2, s1, din_async};
  end
  assign rise = s2 & ~s3;
  assign fall = ~s2 & s3;
endmodule
```

## Pitfalls

- Comparing with N instead of N-1 (period N+1).
- Terminal count held for several cycles because the counter stops at the limit.
- Width too small for the terminal value.
- Edge detector on a raw async input: double pulses.
- Delay register reset to the opposite of the input's idle level: a false edge after reset.

## How to check it

- Cycles between ticks for N = 1, 2 and a typical N; clear together with enable checks priority.
- One-cycle and long input pulses each give exactly one output pulse per edge.

## Sources

- Harris and Harris, *Digital Design and Computer Architecture*, ch. 5 (counters, shift registers).
- Wakerly, J. F., *Digital Design: Principles and Practices*, Pearson (counters, synchronous design practices).
- Ganssle, J., "A Guide to Debouncing" (switch-bounce measurements).
