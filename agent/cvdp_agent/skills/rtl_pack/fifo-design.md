# fifo-design

## When it applies

When the spec asks for a FIFO, queue, buffer, elastic buffer, or "first-in first-out" storage in a single clock
domain, or names `full`, `empty`, `almost_full`, `count`, `push`/`pop`, `wr_en`/`rd_en`. For two clocks, load
`clock-domain-crossing` as well.

## Key rules

1. **Pointers one bit wider than the address** (`$clog2(DEPTH)+1` bits) distinguish full from empty without a
   separate count: equal pointers = empty; equal address bits but different MSB = full. This works when DEPTH is a
   power of two. For any DEPTH, keep an explicit occupancy counter instead.
2. **Ignore a write when full and a read when empty** (unless the spec defines overflow behaviour). Gate them:
   `do_wr = wr_en && !full; do_rd = rd_en && !empty;`.
3. **Simultaneous read and write:** both happen, count unchanged. When empty, the read is ignored. When full,
   the write is ignored (gated as above) unless the spec allows write-through on a read.
4. **Decide the read timing:**
   - *Standard (registered read)*: `rd_data` is valid the cycle after `rd_en`.
   - *First-word fall-through (FWFT / show-ahead)*: `rd_data` shows the head entry whenever `!empty`; `rd_en`
     pops it. Combinational read from the array.
5. **Flags** come from registered pointers or counts; `almost_full` is `count >= THRESH` (state it).
6. **Count width** is `$clog2(DEPTH+1)` so it can hold DEPTH.

## Usual defaults when the spec is silent (defaults, not laws)

- Synchronous FIFO, power-of-two DEPTH, standard (not FWFT) read, overflow and underflow ignored.
- Reset empties the FIFO (pointers and count to zero); the storage array is not reset.
- Spec wording like "data is available whenever not empty" means FWFT.

## Idiom: synchronous FIFO, FWFT read, count output

```systemverilog
module sync_fifo #(parameter int W = 8, parameter int DEPTH = 16) (
  input  logic                       clk, rst_n,
  input  logic                       wr_en,
  input  logic [W-1:0]               wr_data,
  output logic                       full,
  input  logic                       rd_en,
  output logic [W-1:0]               rd_data,
  output logic                       empty,
  output logic [$clog2(DEPTH+1)-1:0] count
);
  localparam int AW = $clog2(DEPTH);
  logic [W-1:0] mem [DEPTH];
  logic [AW:0]  wptr, rptr;            // one extra bit

  wire do_wr = wr_en && !full;
  wire do_rd = rd_en && !empty;

  assign empty   = (wptr == rptr);
  assign full    = (wptr[AW-1:0] == rptr[AW-1:0]) && (wptr[AW] != rptr[AW]);
  assign count   = wptr - rptr;        // modular difference
  assign rd_data = mem[rptr[AW-1:0]];  // FWFT: head is always visible

  always_ff @(posedge clk) if (do_wr) mem[wptr[AW-1:0]] <= wr_data;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      wptr <= '0;
      rptr <= '0;
    end else begin
      if (do_wr) wptr <= wptr + 1'b1;
      if (do_rd) rptr <= rptr + 1'b1;
    end
  end
endmodule
```

For a standard read, register the output: `always_ff @(posedge clk) if (do_rd) rd_data <= mem[rptr[AW-1:0]];`.

## Pitfalls

- Pointers only `AW` bits wide: full and empty look the same.
- The pointer trick with a non-power-of-two DEPTH; use a counter and wrap pointers at `DEPTH-1` instead.
- `count` only `AW` bits: overflows at DEPTH.
- Writing when full corrupts the oldest entry.
- FWFT versus standard read: a one-cycle mismatch.
- `DEPTH = 1` gives `AW = 0` (zero-width slices): special-case it or require `DEPTH >= 2`.

## How to check it

- Fill: `full` exactly at DEPTH writes; drain: order and `empty`.
- Random push/pop against a `collections.deque` model; check data, count and flags every cycle.
- Write when full and read when empty change nothing.

## Sources

- Cummings, C. E., "Simulation and Synthesis Techniques for Asynchronous FIFO Design", SNUG San Jose 2002 (the
  extra-pointer-bit method, which applies equally to synchronous FIFOs).
- FPGA vendor FIFO generator product guides (standard versus first-word fall-through read modes).
