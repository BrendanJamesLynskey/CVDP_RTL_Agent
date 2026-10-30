# bus-and-register-interfaces

## When it applies

When the design has a configuration/status register block (CSRs), or a memory-mapped interface: APB (`psel`,
`penable`, `pwrite`, `pready`), AXI4-Lite (`awvalid`, `wvalid`, `bvalid`, `arvalid`, `rvalid`), Wishbone
(`cyc`, `stb`, `ack`), or a simple `addr/wr_en/rd_en` bus.

## Key rules: register blocks

1. **Make an address map table first**: offset, name, access (RW, RO, WO, W1C, RC), reset value, fields.
2. **Address decode on word offsets**: with 32-bit registers, byte address bits [1:0] are ignored; decode
   `addr[AW-1:2]`.
3. **Access types**:
   - RW: write stores, read returns the stored value.
   - RO: write ignored, read returns hardware status.
   - W1C: hardware sets, writing 1 clears; on a same-cycle set and clear, **set wins** (default).
   - RC (read-to-clear): cleared once, on the actual read handshake.
   - WO / self-clearing "go" bits: read as 0, pulse for one cycle when written.
4. **Unmapped addresses**: reads return 0, writes ignored, unless the spec requires an error response (APB
   `pslverr`, AXI `SLVERR`/`DECERR`).
5. **Byte strobes** (`pstrb`, `wstrb`): honour them per byte if the interface has them.

## Key rules: APB (AMBA APB, protocol versions 3/4)

- Setup phase `psel && !penable`, then access phase `psel && penable`; the transfer completes on the edge where
  `psel && penable && pready`. Do writes and read side effects only then.
- `prdata` must be valid in that access phase; a simple slave ties `pready = 1`.

## Key rules: AXI4-Lite

- Five independent channels: AW, W, B (write); AR, R (read). Each uses valid/ready (see
  `valid-ready-handshake`).
- AW and W may arrive in either order or together; accept both (track `aw_seen`, `w_seen`) before issuing B.
- Hold `bvalid` until `bready`, `rvalid`/`rdata` until `rready`; never wait for the ready first.
- `bresp`/`rresp`: `2'b00` OKAY, `2'b10` SLVERR, `2'b11` DECERR. One outstanding transaction suffices.

## Usual defaults when the spec is silent (defaults, not laws)

- 32-bit data, byte addresses, word-aligned registers, reset values 0.
- APB slave with zero wait states (`pready = 1`), `pslverr = 0`.
- AXI4-Lite slave answering OKAY, one transaction at a time.

## Idiom: APB register block with RW, RO and W1C

```systemverilog
module apb_regs (
  input  logic        pclk, presetn,
  input  logic        psel, penable, pwrite,
  input  logic [7:0]  paddr,
  input  logic [31:0] pwdata,
  output logic [31:0] prdata,
  output logic        pready, pslverr,
  input  logic [31:0] status_i,    // RO
  input  logic [3:0]  irq_set_i,   // hardware sets W1C bits
  output logic [31:0] ctrl_o       // RW
);
  logic [3:0] irq_q;
  wire wr = psel && penable && pwrite;

  assign pready  = 1'b1;
  assign pslverr = 1'b0;

  always_ff @(posedge pclk or negedge presetn) begin
    if (!presetn) begin
      ctrl_o <= '0;
      irq_q  <= '0;
    end else begin
      if (wr && paddr[7:2] == 6'h0) ctrl_o <= pwdata;
      // W1C, set wins over clear
      irq_q <= (irq_q & ~((wr && paddr[7:2] == 6'h2) ? pwdata[3:0] : 4'h0)) | irq_set_i;
    end
  end

  always_comb begin
    prdata = '0;
    case (paddr[7:2])
      6'h0: prdata = ctrl_o;
      6'h1: prdata = status_i;
      6'h2: prdata = {28'h0, irq_q};
      default: prdata = '0;
    endcase
  end
endmodule
```

## Pitfalls

- Acting in the APB setup phase as well as the access phase: double side effects.
- An AXI4-Lite slave requiring AW and W together: deadlocks with masters that send them apart.
- Byte address bits used as the word index.
- Read-to-clear firing every cycle `psel` is high.

## How to check it

- Reset values, then write/read every RW register; W1C set and clear, including simultaneously.
- AXI4-Lite: AW before W, W before AW, both together, with delayed `bready`/`rready`.

## Sources

- Arm, *AMBA APB Protocol Specification* (IHI 0024) and *AMBA AXI Protocol Specification* (IHI 0022), AXI4-Lite
  section (public documents).
- Wishbone B4 specification, OpenCores; IEEE 1685 IP-XACT (register access types).
