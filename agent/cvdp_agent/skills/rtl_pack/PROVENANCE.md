# Provenance: RTL design knowledge pack

Date written: 2026-10-30. Author: an LLM executor session (brief 18A), working alone from a written brief.

## Contamination rule statement

The pack was written without any knowledge of the benchmark it will be tested on:

- No file in the benchmark agent's project directory was opened, listed or searched.
- No file in the planner's hand-off folder for this project was read except the brief that commissioned this
  pack. The project plan log was appended to without being read.
- The benchmark's paper, repository and dataset were not consulted, and no web search was made for it or for
  any other benchmark's problem set (VerilogEval, RTLLM, HDLBits or similar).
- No web search or web fetch was made at all. The text was written from the author's general knowledge of
  digital design and the sources below, summarised in original words. No passage was copied.
- Topics were chosen from a general digital-design curriculum and industry practice: specification reading,
  reset, RTL coding rules, FSMs, handshakes, pipelines, FIFOs, CDC, arithmetic, counters, memories, register
  buses, arbiters, the synthesisable subset, and self-checking.

## Sources cited

Textbooks:

- Harris, D. M. and Harris, S. L., *Digital Design and Computer Architecture*, Morgan Kaufmann.
- Wakerly, J. F., *Digital Design: Principles and Practices*, Pearson.
- Mano, M. M. and Ciletti, M. D., *Digital Design*, Pearson.
- Dally, W. J. and Harting, R. C., *Digital Design: A Systems Approach*, Cambridge University Press.
- Dally, W. J. and Towles, B., *Principles and Practices of Interconnection Networks*, Morgan Kaufmann.
- Patterson, D. A. and Hennessy, J. L., *Computer Organization and Design* (including the RISC-V Edition),
  Morgan Kaufmann.
- Parhi, K. K., *VLSI Digital Signal Processing Systems: Design and Implementation*, Wiley.
- Ercegovac, M. D. and Lang, T., *Digital Arithmetic*, Morgan Kaufmann.
- Warren, H. S., *Hacker's Delight*, Addison-Wesley.
- Keating, M. and Bricaud, P., *Reuse Methodology Manual for System-on-a-Chip Designs*, Springer.
- Sutherland, S., Davidmann, S. and Flake, P., *SystemVerilog for Design*, 2nd ed., Springer.
- Sutherland, S., *Verilog and SystemVerilog Gotchas*, Springer.
- Bergeron, J., *Writing Testbenches: Functional Verification of HDL Models*, Springer.
- Spear, C. and Tumbush, G., *SystemVerilog for Verification*, Springer.

Standards and protocol documents:

- IEEE Std 1800-2017, *SystemVerilog Language Reference Manual* (clauses 6.20, 9.2.2, 10.4, 11.6, 11.8, 12.5,
  13.4, 20.8, 27).
- Arm, *AMBA APB Protocol Specification* (IHI 0024); *AMBA AXI Protocol Specification* (IHI 0022), including
  AXI4-Lite; *AMBA 4 AXI4-Stream Protocol Specification*.
- Wishbone B4 specification (OpenCores); IEEE 1685 IP-XACT (register access types).

Papers:

- Cummings, C. E., "Nonblocking Assignments in Verilog Synthesis, Coding Styles That Kill!", SNUG San Jose 2000.
- Cummings, C. E. and Mills, D., "Synchronous Resets? Asynchronous Resets? I am so confused! How will I ever know
  which to use?", SNUG 2002.
- Cummings, C. E., Mills, D. and Golson, S., "Asynchronous & Synchronous Reset Design Techniques - Part Deux",
  SNUG Boston 2003.
- Cummings, C. E., "The Fundamentals of Efficient Synthesizable Finite State Machine Design using NC-Verilog and
  BuildGates", ICU 2002; "Synthesizable Finite State Machine Design Techniques Using the New SystemVerilog 3.0
  Enhancements", SNUG San Jose 2003.
- Cummings, C. E., "Simulation and Synthesis Techniques for Asynchronous FIFO Design", SNUG San Jose 2002.
- Cummings, C. E., "Clock Domain Crossing (CDC) Design & Verification Techniques Using SystemVerilog", SNUG
  Boston 2008.
- Ginosar, R., "Metastability and Synchronizers: A Tutorial", IEEE Design & Test of Computers, 2011.
- Sutherland, S. and Mills, D., "Synthesizing SystemVerilog: Busting the Myth that SystemVerilog is only for
  Verification", SNUG Silicon Valley 2013.
- Weber, M., "Arbiters: Design Ideas and Coding Styles", SNUG Boston 2001.
- Ganssle, J., "A Guide to Debouncing".

Tool and vendor documentation:

- cocotb documentation (docs.cocotb.org), including the 2.0 migration notes.
- Verilator manual; Icarus Verilog documentation; Yosys manual.
- FPGA vendor guides: AMD UltraFast Design Methodology Guide; AMD Vivado Design Suite User Guide: Synthesis
  (UG901); FIFO generator product guides.

Citations were made from the author's knowledge of these works; none was re-read for this pack, so treat
section numbers as pointers, not quotations.

## Tool checks

Every SystemVerilog idiom block (18 modules in 17 blocks) was extracted and linted with Verilator 5.020
(`--lint-only -Wall -Wno-DECLFILENAME`) and Icarus Verilog 12.0 (`iverilog -g2012 -Wall`), run under
`systemd-run --user --scope -p MemoryMax=3G nice -n 15`. All pass both tools; the one remaining Verilator
warning is intended (`UNUSEDSIGNAL` on `paddr[1:0]` in the APB idiom, whose byte-offset bits are ignored by
design). Icarus prints informational "sorry" notes about constant selects in `always_*` sensitivity and ignored
`unique` qualifiers; these are not errors.

Functional simulation in Icarus (self-checking testbench, not part of the pack): skid buffer (random
valid/ready, order check), synchronous FIFO (random push/pop against a queue model, plus directed fill/drain),
round-robin arbiter (rotation and masked cases), modulo counter (tick period), saturating adder (exhaustive at
W = 4), priority encoder (exhaustive at N = 8): all pass. The cocotb test and Makefile in
`self-check-and-cocotb` were run verbatim with cocotb 2.0.1 and Icarus on the `pipe_stage` idiom: pass.

Yosys is not installed on the authoring machine, so no synthesis check was run.

## Word count per skill

| Skill | Words |
|---|---|
| spec-reading | 674 |
| reset-strategy | 587 |
| sequential-and-combinational-coding | 609 |
| fsm-design | 596 |
| valid-ready-handshake | 615 |
| pipelining-and-latency | 549 |
| fifo-design | 594 |
| clock-domain-crossing | 601 |
| arithmetic-and-widths | 597 |
| counters-timers-and-edges | 582 |
| memories-and-register-files | 585 |
| bus-and-register-interfaces | 613 |
| arbiters-encoders-and-muxes | 580 |
| synthesisable-subset-and-parameters | 607 |
| self-check-and-cocotb | 533 |
| **Total (15 skills)** | **8922** |

Word counts are `wc -w` of each file, including code blocks and sources.

## Licence

Original text, written for publication under the MIT licence. Short code idioms were written by the author.
