# arithmetic-and-widths

## When it applies

Any time the design adds, subtracts, multiplies, compares, shifts, accumulates, or handles signed or fixed-point
numbers; when a spec mentions overflow, saturation, rounding, two's complement, Q-format, or carry.

## Key rules

1. **Know the expression width rule.** In Verilog/SystemVerilog an expression is evaluated at the width of the
   widest operand *including the left-hand side* (context-determined). So `assign s9 = a8 + b8;` keeps the carry
   (9-bit context), but `assign c = (a8 + b8) >> 1;` assigned to 8 bits loses it. Concatenation `{}` operands are
   self-determined: `{a8 + b8}` is 8 bits.
2. **Size results explicitly**: sum of two N-bit values needs N+1 bits; product of N and M bits needs N+M bits; a
   sum of K values needs N + `$clog2(K)` bits.
3. **Signedness is all or nothing.** If *any* operand is unsigned, the whole expression is unsigned. Declare signed
   ports and variables `logic signed [N-1:0]`, and cast with `$signed()` / `$unsigned()` deliberately. Part-selects
   (`x[7:0]`) and concatenations are always unsigned, even of a signed variable.
4. **Sign-extend by replicating the MSB**: `{{(M-N){x[N-1]}}, x}`, or assign a signed N-bit value to a signed
   M-bit variable.
5. **Shifts:** `>>` is logical; `>>>` is arithmetic only on a signed operand.
6. **Overflow:** signed add overflows when both operands share a sign the result lacks; unsigned, on carry out.
7. **Saturation:** compute at full width, then clamp to the output's max/min.
8. **Fixed point:** Qa.b times Qc.d is Q(a+c).(b+d); shift right by the extra fraction bits (round first if
   required).
9. **Rounding** (state which): truncation (drop bits; floor in two's complement); half-up (add `1 << (k-1)`, then
   shift); half-to-even needs a tie check.
10. **Avoid division by non-constants** unless asked. Dividing by a power of two is a shift, but `>>>` of a
    negative number rounds toward minus infinity while `/` rounds toward zero.

## Usual defaults when the spec is silent (defaults, not laws)

- Unsigned, wrap-around (modulo 2^N) on overflow.
- Truncation when reducing precision.
- Signed values are two's complement.
- Comparisons between a signed port and a constant: make the constant signed too, or the comparison is unsigned.

## Idiom: signed saturating add

```systemverilog
module sat_add #(parameter int W = 8) (
  input  logic signed [W-1:0] a, b,
  output logic signed [W-1:0] y,
  output logic                ovf
);
  // limits held at W+1 bits so every comparison is signed and same-width
  localparam logic signed [W:0] MAXV = {2'b00, {(W-1){1'b1}}};
  localparam logic signed [W:0] MINV = {2'b11, {(W-1){1'b0}}};
  logic signed [W:0] full;

  always_comb begin
    full = a + b;                       // W+1-bit signed context, sign-extended
    ovf  = (full > MAXV) || (full < MINV);
    if      (full > MAXV) y = MAXV[W-1:0];
    else if (full < MINV) y = MINV[W-1:0];
    else                  y = full[W-1:0];
  end
endmodule
```

## Pitfalls

- `a + b` with `a` unsigned and `b` signed is unsigned: `b` is not sign-extended; the same breaks products.
- `x[7:0]` of a signed variable is unsigned; `$signed(x[7:0])` restores it.
- Accumulators sized to the input width overflow.
- `count == DEPTH` with `count` too narrow to hold DEPTH: never true.

## How to check it

- Fix or justify every Verilator `WIDTH` warning.
- Test 0, 1, max, min, -1 and overflowing pairs.
- In cocotb, mask the Python reference (`& ((1 << W) - 1)`), compare bit-exact; read signed values with
  `dut.y.value.to_signed()`.

## Sources

- IEEE Std 1800-2017, clause 11.6 (expression bit lengths), 11.8 (expression evaluation rules: signedness).
- Sutherland, S., *Verilog and SystemVerilog Gotchas*, Springer (signedness and width gotchas).
- Ercegovac, M. D. and Lang, T., *Digital Arithmetic*, Morgan Kaufmann.
