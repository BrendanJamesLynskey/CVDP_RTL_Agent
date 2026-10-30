# valid-ready-handshake

## When it applies

When an interface has `valid`/`ready` (or `vld`/`rdy`, `tvalid`/`tready`, `req`/`ack`) signals, when the spec
mentions back-pressure, streaming, "accept", "stall", or AXI4-Stream style transfers.

## Key rules (the AXI-style valid/ready contract)

1. **A transfer happens on a clock edge where `valid && ready` are both high.** Nothing else counts.
2. **The source must not wait for `ready` before asserting `valid`.** `valid` may depend only on the source's own
   state; otherwise two blocks can deadlock waiting for each other.
3. **Once `valid` is high, the source holds `valid` and keeps the data stable until the transfer happens.**
4. **The sink may change `ready` freely;** it may depend on `valid`, though a registered `ready` times better.
5. **A long combinational `ready` chain through many stages limits clock speed;** break it with a skid buffer.
6. **A pipeline stage with back-pressure:** stage register loads when `in_valid && in_ready`; the stage is ready
   when it is empty or its contents are leaving this cycle:
   `in_ready = !out_valid || out_ready;`
7. **`req`/`ack` four-phase is different:** req up, ack up, req down, ack down. Two-phase signals an event by a
   level change.

## Usual defaults when the spec is silent (defaults, not laws)

- Data is meaningful only while `valid` is high. An always-ready sink may tie `ready = 1`.
- After reset all `valid` outputs are low.
- `last` (end of packet) is qualified by `valid && ready` like data.

## Idiom: one registered stage with back-pressure

```systemverilog
module pipe_stage #(parameter int W = 8) (
  input  logic         clk, rst_n,
  input  logic         in_valid,
  output logic         in_ready,
  input  logic [W-1:0] in_data,
  output logic         out_valid,
  input  logic         out_ready,
  output logic [W-1:0] out_data
);
  assign in_ready = !out_valid || out_ready;   // combinational ready path

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) out_valid <= 1'b0;
    else if (in_ready) out_valid <= in_valid;
  end

  always_ff @(posedge clk) begin
    if (in_valid && in_ready) out_data <= in_data;
  end
endmodule
```

## Idiom: skid buffer (registers `ready` too, full throughput)

```systemverilog
module skid_buffer #(parameter int W = 8) (
  input  logic         clk, rst_n,
  input  logic         in_valid,
  output logic         in_ready,
  input  logic [W-1:0] in_data,
  output logic         out_valid,
  input  logic         out_ready,
  output logic [W-1:0] out_data
);
  logic         skid_valid;
  logic [W-1:0] skid_data;

  assign in_ready = !skid_valid;               // registered: depends on state only

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      out_valid  <= 1'b0;
      skid_valid <= 1'b0;
    end else begin
      if (out_ready || !out_valid) begin
        // output can move: take skid first, else the input
        out_valid  <= skid_valid || in_valid;
        skid_valid <= 1'b0;
      end else if (in_valid && in_ready) begin
        skid_valid <= 1'b1;                    // output stalled: park the input
      end
    end
  end

  always_ff @(posedge clk) begin
    if (out_ready || !out_valid) begin
      out_data <= skid_valid ? skid_data : in_data;
    end
    if (in_valid && in_ready && out_valid && !out_ready) skid_data <= in_data;
  end
endmodule
```

## Pitfalls

- Counting a transfer on `valid` alone (duplicates or losses under back-pressure).
- Changing data while `valid && !ready`; making `valid` depend on `ready`.
- Losing a beat when `ready` drops as the stage loads (the skid register catches it).
- A register stage that cannot sustain one transfer per cycle.

## How to check it

- Random `valid` in, random `ready` out, numbered data: the output sequence is identical (no loss, duplication
  or reorder).
- With `out_ready` held high, one item per cycle comes out.
- If `valid && !ready` at one edge, `valid` and data are unchanged at the next.

## Sources

- Arm, *AMBA AXI and ACE Protocol Specification* and *AMBA 4 AXI4-Stream Protocol Specification*, the handshake
  process sections (public documents).
- Dally, W. J. and Harting, R. C., *Digital Design: A Systems Approach*, Cambridge University Press.
