# arbiters-encoders-and-muxes

## When it applies

When several requesters share a resource (bus, memory port, output), or the spec asks for a priority encoder,
one-hot or binary decoder, leading-zero/one count, round-robin or fixed-priority arbiter, or a wide multiplexer.

## Key rules

1. **Priority encoder**: define which end wins. The most common default is **lowest index = highest priority**
   (bit 0 wins). Output an index plus a `valid`/`found` flag for the all-zero case.
2. **One-hot vs binary**: grant vectors are usually one-hot (`[N-1:0]`, at most one bit set). Indices are binary
   (`[$clog2(N)-1:0]`). Convert explicitly; say which the spec wants.
3. **Fixed priority with one-hot grant**: `grant = req & ~(req - 1)` isolates the lowest set bit (the
   two's-complement trick).
4. **Round-robin:** after granting k, k becomes lowest priority. Standard method: one fixed-priority pass on
   `req & mask` (requests above the last grant), one on `req`; use the masked result if non-zero.
5. **Update the round-robin state only on an accepted grant,** not every cycle.
6. **Hold the grant** for multi-cycle transfers only if the spec says so; otherwise re-arbitrate each cycle.
7. **Muxes:** `d[sel]` or a `case`; for one-hot selects an AND-OR mux avoids priority logic. Define the output
   for an out-of-range select (default 0).

## Usual defaults when the spec is silent (defaults, not laws)

- Fixed priority: bit 0 highest. Round robin: start with requester 0 highest after reset.
- Combinational grant from the current requests (grant in the same cycle) unless "registered grant" is stated.
- No request: grant all zeros, valid low, index 0.

## Idiom: round-robin arbiter (mask method)

```systemverilog
module rr_arbiter #(parameter int N = 4) (
  input  logic         clk, rst_n,
  input  logic [N-1:0] req,
  input  logic         accept,       // grant consumed this cycle
  output logic [N-1:0] grant
);
  logic [N-1:0] mask_q;              // 1 = eligible in the masked pass
  logic [N-1:0] req_m, gnt_m, gnt_u;

  assign req_m = req & mask_q;
  assign gnt_m = req_m & ~(req_m - 1'b1);   // lowest set bit
  assign gnt_u = req   & ~(req   - 1'b1);
  assign grant = (|req_m) ? gnt_m : gnt_u;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) mask_q <= '1;
    else if (accept && |grant)
      mask_q <= ~((grant << 1) - 1'b1);     // bits above the granted one
  end
endmodule
```

Priority encoder with a valid flag:

```systemverilog
module prio_enc #(parameter int N = 8) (
  input  logic [N-1:0]         d,
  output logic [$clog2(N)-1:0] idx,
  output logic                 valid
);
  always_comb begin
    idx   = '0;
    valid = 1'b0;
    for (int i = N-1; i >= 0; i--)      // last assignment wins: lowest index
      if (d[i]) begin
        idx   = i[$clog2(N)-1:0];
        valid = 1'b1;
      end
  end
endmodule
```

## Pitfalls

- Round-robin state updated without an accepted grant, or a mask built from requests instead of the grant.
- A grant that is not one-hot.
- A priority encoder with no valid flag: "bit 0" and "none" look the same.
- `break` in loops is less portable to older tools; the "last assignment wins" loop avoids it.

## How to check it

- All requests high: grants rotate 0, 1, ..., N-1, 0.
- Grant is one-hot or zero every cycle (`$onehot0(grant)`).
- With random requests, a persistent requester is granted within N accepted grants.

## Sources

- Dally, W. J. and Towles, B., *Principles and Practices of Interconnection Networks*, Morgan Kaufmann
  (arbitration chapter).
- Weber, M., "Arbiters: Design Ideas and Coding Styles", SNUG Boston 2001.
- Warren, H. S., *Hacker's Delight*, Addison-Wesley (isolating the lowest set bit).
