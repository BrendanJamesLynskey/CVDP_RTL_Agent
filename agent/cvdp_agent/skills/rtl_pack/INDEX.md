# RTL design knowledge pack: index

Load a skill by reading `<name>.md`. Load `spec-reading` first on every task, `self-check-and-cocotb` last.

spec-reading: start of every RTL task; extract ports, parameters, latency/throughput, reset, corner cases; list ambiguities with stated assumptions and silent-spec defaults.
reset-strategy: any register with a reset; polarity from port name, sync vs async choice, reset values, reset synchroniser.
sequential-and-combinational-coding: writing always_ff/always_comb; blocking vs nonblocking, latches, multiple drivers, sizing literals, unique/priority case.
fsm-design: spec describes states, modes, phases, sequences or a controller; Moore vs Mealy timing, two-block enum FSM, sequence detectors.
valid-ready-handshake: valid/ready, tvalid/tready, back-pressure or stall; transfer rules, pipeline stage with ready, skid buffer, req/ack.
pipelining-and-latency: spec gives a latency in cycles, "pipelined", "registered output", or a test is off by a cycle; valid shift registers, side-band alignment.
fifo-design: single-clock FIFO/queue/buffer with full/empty/count; pointer extra bit, simultaneous push/pop, FWFT vs standard read.
clock-domain-crossing: two clocks, asynchronous inputs, synchronisers, pulse crossing, Gray code, async FIFO.
arithmetic-and-widths: add/sub/multiply/compare/shift, signed or fixed-point data, overflow, saturation, rounding, width and sign-extension rules.
counters-timers-and-edges: counters, timers, prescalers, clock enables, PWM, edge detection, debouncing, "wait N cycles".
memories-and-register-files: RAM, ROM, register file, byte enables; sync vs async read, read-during-write behaviour, RAM inference.
bus-and-register-interfaces: CSR/register maps, APB, AXI4-Lite, Wishbone; access types (RW, RO, W1C, RC), address decode, responses.
arbiters-encoders-and-muxes: shared resource, priority encoder, fixed or round-robin arbiter, one-hot/binary conversion, wide muxes.
synthesisable-subset-and-parameters: what synthesises, parameters/localparams, generate, $clog2 edge cases, packages, open-tool portability.
self-check-and-cocotb: after writing RTL or when writing a testbench; lint commands, cocotb 2.x idioms and Makefile, self-review checklist.
