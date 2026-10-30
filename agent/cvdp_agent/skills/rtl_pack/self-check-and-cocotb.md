# self-check-and-cocotb

## When it applies

After writing any RTL and before declaring it finished; when asked to write a testbench; when you can run tools
(Verilator, Icarus, Yosys, cocotb) on your own design.

## Key rules

1. **Lint first, always.** `verilator --lint-only -Wall top.sv` (add `--top-module name` if there are several
   modules). Then `iverilog -g2012 -Wall -o /dev/null top.sv`. Fix every error; read every warning. Treat
   `LATCH`, `MULTIDRIVEN`, `WIDTH*`, `CASEINCOMPLETE`, `UNDRIVEN`, `BLKSEQ` as bugs until explained.
2. **Optional synthesis check:** `yosys -p "read_verilog -sv top.sv; synth -top top; stat"` (finds
   unsynthesisable code and latch cells).
3. **Re-check the interface** against the spec: names, widths, directions, parameters.
4. **Directed test per spec rule and corner case,** then a random test against a reference model.
5. **Check outputs on the exact cycle;** most failures are one cycle early or late.
6. **Never drive and sample on the same edge:** drive on the falling edge (or after the rising edge) and sample
   at a consistent point.

## cocotb essentials (cocotb 2.x)

- A test is an `async def` decorated with `@cocotb.test()`; the DUT is its argument.
- Start a clock: `cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())`.
- Wait: `await RisingEdge(dut.clk)`, `await FallingEdge(dut.clk)`, `await ClockCycles(dut.clk, n)`,
  `await Timer(1, unit="ns")`, `await ReadOnly()` (sample after all updates in the time step).
- Drive: `dut.a.value = 5`. Read: `int(dut.y.value)`; signed: `dut.y.value.to_signed()`.
- `int()` of a value holding X or Z raises; check `dut.y.value.is_resolvable`.
- Older code uses `units=` and `cocotb.fork`; cocotb 2.0 uses `unit=` and `cocotb.start_soon`.

## Idiom: cocotb test with reset and reference model

```python
import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles

async def reset(dut):
    dut.rst_n.value = 0
    dut.in_valid.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

@cocotb.test()
async def random_stream(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    expected = []
    for _ in range(200):
        await FallingEdge(dut.clk)              # drive away from the active edge
        if int(dut.out_valid.value):
            assert int(dut.out_data.value) == expected.pop(0)
        v = random.random() < 0.7
        dut.in_valid.value = int(v)
        if v:
            d = random.randrange(256)
            dut.in_data.value = d
            expected.append(d)
```

A minimal Makefile (cocotb 2.x):

```make
SIM ?= icarus
TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $(PWD)/top.sv
COCOTB_TOPLEVEL = top
COCOTB_TEST_MODULES = test_top
include $(shell cocotb-config --makefiles)/Makefile.sim
```

(cocotb 1.x used `TOPLEVEL` and `MODULE`.) With Icarus, pass `-g2012` via `COMPILE_ARGS` if needed.

## Usual defaults (defaults, not laws)

- Reset held 2 to 5 cycles; 10 ns clock unless the spec gives one; random seed printed (cocotb does).

## Self-review checklist

- Every output assigned on every path; no latches. Every control register reset.
- Every counter and pointer wide enough for its maximum.
- Transfers counted only on `valid && ready`; latencies equal the spec; side-band aligned.
- Signedness consistent; no `initial`, `#delay` or simulation-only code in RTL; assumptions in the header.

## Pitfalls

- Driving and sampling on the same edge: results depend on scheduling order.
- Only the happy path: no back-pressure, no full FIFO, no simultaneous events.
- A reference model written from your RTL, not the spec, repeats your bug.

## Sources

- cocotb documentation, docs.cocotb.org (quickstart, triggers, 2.0 migration guide).
- Verilator manual ("Errors and Warnings"); Yosys manual (`synth`, `stat`).
- Spear, C. and Tumbush, G., *SystemVerilog for Verification*, Springer (self-checking testbenches).
