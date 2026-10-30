# memories-and-register-files

## When it applies

When the spec needs a RAM, ROM, lookup table, register file, cache array, or line buffer; when it names ports like
`addr`, `we`, `wdata`, `rdata`, `be` (byte enable), or says single-port / dual-port.

## Key rules

1. **Declare memory as an unpacked array**: `logic [W-1:0] mem [DEPTH];` (or `[0:DEPTH-1]`).
2. **Write in `always_ff` with an enable; never reset the array** (it prevents RAM inference).
3. **Choose the read style and match the spec:**
   - *Synchronous read* (registered `rdata`, latency 1): maps to block RAM; the default for "RAM".
   - *Asynchronous read* (`assign rdata = mem[raddr];`): flip-flops or distributed RAM; typical for register
     files.
4. **Read-during-write to the same address** has three behaviours; the spec should say which:
   - *read-first* (old data): read and write in the same `always_ff` with `<=` gives this naturally;
   - *write-first* (new data, "write-through"): forward `wdata` when addresses match;
   - *undefined / no-change*.
5. **Byte enables**: loop over bytes, write `mem[a][8*i +: 8]` when `be[i]`.
6. **Register file with register 0 hard-wired to zero** (RISC style): ignore writes to address 0 and/or force the
   read to 0.
7. **ROM:** a `case` in `always_comb`, or `$readmemh` in an `initial` block (FPGA flows and Yosys accept it).
8. **Out-of-range addresses** (non-power-of-two DEPTH): default writes ignored, reads 0; state it.

## Usual defaults when the spec is silent (defaults, not laws)

- RAM: synchronous write, synchronous read, read-first, no reset of contents.
- Register file: synchronous write, asynchronous read, no bypass (a read in the same cycle as a write to that
  register returns the old value).
- Dual-port "simple" means one write port and one read port; "true" dual port means two read/write ports.

## Idiom: simple dual-port RAM, sync read, read-first, byte enables

```systemverilog
module sdp_ram #(parameter int DEPTH = 256, parameter int NB = 4) (
  input  logic                     clk,
  input  logic                     we,
  input  logic [NB-1:0]            be,
  input  logic [$clog2(DEPTH)-1:0] waddr,
  input  logic [8*NB-1:0]          wdata,
  input  logic                     re,
  input  logic [$clog2(DEPTH)-1:0] raddr,
  output logic [8*NB-1:0]          rdata
);
  logic [8*NB-1:0] mem [DEPTH];

  always_ff @(posedge clk) begin
    if (we) begin
      for (int i = 0; i < NB; i++)
        if (be[i]) mem[waddr][8*i +: 8] <= wdata[8*i +: 8];
    end
    if (re) rdata <= mem[raddr];      // old data on a same-address collision
  end
endmodule
```

Register file, async read, x0 = 0:

```systemverilog
module regfile #(parameter int W = 32, parameter int N = 32) (
  input  logic                 clk,
  input  logic                 we,
  input  logic [$clog2(N)-1:0] waddr, raddr_a, raddr_b,
  input  logic [W-1:0]         wdata,
  output logic [W-1:0]         rdata_a, rdata_b
);
  logic [W-1:0] rf [N];
  always_ff @(posedge clk) if (we && waddr != '0) rf[waddr] <= wdata;
  assign rdata_a = (raddr_a == '0) ? '0 : rf[raddr_a];
  assign rdata_b = (raddr_b == '0) ? '0 : rf[raddr_b];
endmodule
```

## Pitfalls

- Expecting same-cycle data from a synchronous-read RAM, or forgetting that latency in read-modify-write.
- Writing the array from two `always` blocks without meaning a true dual-port RAM.
- Unwritten locations read as X in simulation.
- `$readmemh` paths are relative to the simulator's working directory.

## How to check it

- Write and read back every address; test a same-address read and write in one cycle; test each byte enable.

## Sources

- FPGA vendor synthesis guides on RAM inference templates (for example the AMD Vivado Design Suite User Guide:
  Synthesis, UG901, RAM HDL coding techniques).
- Yosys manual, memory inference (`memory` pass).
- Patterson, D. A. and Hennessy, J. L., *Computer Organization and Design RISC-V Edition* (register file, x0).
