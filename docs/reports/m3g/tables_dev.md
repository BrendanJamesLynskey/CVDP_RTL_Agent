#### Skills loaded (258 problem-runs)

Status: loaded 253, not_chosen 5. Bytes loaded: mean 11572, min 0, max 12517.
 Cut by the cap: 0. Unknown names: synthesizable-subset-and-parameters (4), arbiters-and-encoders-and-muxes (2), bus-register-interfaces (1), memories-register-files (1).

| Skill | Loaded in | Share | Pass rate when loaded | Pass rate when not |
|---|---|---|---|---|
| `spec-reading` | 253 | 98.1% | 59.7% | 0.0% |
| `self-check-and-cocotb` | 105 | 40.7% | 59.0% | 58.2% |
| `fsm-design` | 67 | 26.0% | 41.8% | 64.4% |
| `arithmetic-and-widths` | 59 | 22.9% | 57.6% | 58.8% |
| `synthesisable-subset-and-parameters` | 57 | 22.1% | 73.7% | 54.2% |
| `pipelining-and-latency` | 49 | 19.0% | 59.2% | 58.4% |
| `sequential-and-combinational-coding` | 32 | 12.4% | 78.1% | 55.8% |
| `reset-strategy` | 28 | 10.9% | 71.4% | 57.0% |
| `clock-domain-crossing` | 20 | 7.8% | 50.0% | 59.2% |
| `valid-ready-handshake` | 19 | 7.4% | 52.6% | 59.0% |
| `fifo-design` | 17 | 6.6% | 76.5% | 57.3% |
| `memories-and-register-files` | 17 | 6.6% | 58.8% | 58.5% |
| `counters-timers-and-edges` | 12 | 4.7% | 25.0% | 60.2% |
| `arbiters-encoders-and-muxes` | 5 | 1.9% | 100.0% | 57.7% |
| `bus-and-register-interfaces` | 5 | 1.9% | 20.0% | 59.3% |

Own testbench run: 49 of 105 rows (46.7%) with `self-check-and-cocotb` loaded, 66 of 153 (43.1%) without it.

| Set of skills loaded | Problem-runs | Pass rate |
|---|---|---|
| spec-reading, fsm-design, self-check-and-cocotb | 25 | 60.0% |
| spec-reading, arithmetic-and-widths, self-check-and-cocotb | 18 | 38.9% |
| spec-reading, pipelining-and-latency, self-check-and-cocotb | 17 | 58.8% |
| spec-reading, sequential-and-combinational-coding, self-check-and-cocotb | 11 | 72.7% |
| spec-reading, synthesisable-subset-and-parameters, self-check-and-cocotb | 9 | 100.0% |
| spec-reading, valid-ready-handshake, self-check-and-cocotb | 9 | 66.7% |
| spec-reading, arithmetic-and-widths, synthesisable-subset-and-parameters | 8 | 62.5% |
| spec-reading, memories-and-register-files, synthesisable-subset-and-parameters | 8 | 62.5% |
| spec-reading, pipelining-and-latency, synthesisable-subset-and-parameters | 8 | 62.5% |
| spec-reading, clock-domain-crossing, fifo-design | 6 | 100.0% |

#### Prompt and completion tokens per problem-run

| Arm | Rows | Prompt tokens mean / median | Completion tokens mean | LLM calls mean | Turns mean | Rows with a self-check run |
|---|---|---|---|---|---|---|
| A | 258 | 26,040 / 13,542 | 7,378 | 6.08 | 2.55 | 115 (44.6%) |
| K | 258 | 34,527 / 18,725 | 7,889 | 5.87 | 2.45 | 115 (44.6%) |

#### Pass rate by category (pooled over runs)

| Category | A | K |
|---|---|---|
| cid003 | 61.6% (99) | 57.6% (99) |
| cid004 | 56.9% (72) | 56.9% (72) |
| cid005 | 64.8% (54) | 63.0% (54) |
| cid016 | 60.6% (33) | 57.6% (33) |
