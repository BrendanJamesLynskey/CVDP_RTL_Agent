#### Skills loaded (300 problem-runs)

Status: loaded 299, not_chosen 1. Bytes loaded: mean 11809, min 0, max 12554.
 Cut by the cap: 0. Unknown names: arbiters-and-encoders-and-muxes (5), arbiters-and-encoders (3), arithmetic-widths (1), arbiters-and-encoders-muxes (1).

| Skill | Loaded in | Share | Pass rate when loaded | Pass rate when not |
|---|---|---|---|---|
| `spec-reading` | 299 | 99.7% | 52.2% | 0.0% |
| `self-check-and-cocotb` | 156 | 52.0% | 60.3% | 43.1% |
| `fsm-design` | 84 | 28.0% | 32.1% | 59.7% |
| `arithmetic-and-widths` | 71 | 23.7% | 70.4% | 46.3% |
| `reset-strategy` | 66 | 22.0% | 56.1% | 50.9% |
| `sequential-and-combinational-coding` | 46 | 15.3% | 50.0% | 52.4% |
| `synthesisable-subset-and-parameters` | 40 | 13.3% | 47.5% | 52.7% |
| `valid-ready-handshake` | 29 | 9.7% | 27.6% | 54.6% |
| `pipelining-and-latency` | 18 | 6.0% | 83.3% | 50.0% |
| `counters-timers-and-edges` | 16 | 5.3% | 56.2% | 51.8% |
| `arbiters-encoders-and-muxes` | 15 | 5.0% | 40.0% | 52.6% |
| `bus-and-register-interfaces` | 13 | 4.3% | 23.1% | 53.3% |
| `clock-domain-crossing` | 11 | 3.7% | 18.2% | 53.3% |
| `fifo-design` | 10 | 3.3% | 40.0% | 52.4% |
| `memories-and-register-files` | 9 | 3.0% | 66.7% | 51.5% |

Own testbench run: 61 of 156 rows (39.1%) with `self-check-and-cocotb` loaded, 29 of 144 (20.1%) without it.

| Set of skills loaded | Problem-runs | Pass rate |
|---|---|---|
| spec-reading, fsm-design, self-check-and-cocotb | 35 | 31.4% |
| spec-reading, arithmetic-and-widths, self-check-and-cocotb | 27 | 74.1% |
| spec-reading, reset-strategy, self-check-and-cocotb | 20 | 80.0% |
| spec-reading, synthesisable-subset-and-parameters, self-check-and-cocotb | 18 | 66.7% |
| spec-reading, sequential-and-combinational-coding, self-check-and-cocotb | 18 | 72.2% |
| spec-reading, reset-strategy, sequential-and-combinational-coding | 12 | 58.3% |
| spec-reading, fsm-design, arithmetic-and-widths | 12 | 50.0% |
| spec-reading, self-check-and-cocotb | 10 | 70.0% |
| spec-reading, arithmetic-and-widths, reset-strategy | 8 | 87.5% |
| spec-reading, pipelining-and-latency, arithmetic-and-widths | 6 | 100.0% |

#### Prompt and completion tokens per problem-run

| Arm | Rows | Prompt tokens mean / median | Completion tokens mean | LLM calls mean | Turns mean | Rows with a self-check run |
|---|---|---|---|---|---|---|
| A | 300 | 8,286 / 5,792 | 3,658 | 4.14 | 1.57 | 72 (24.0%) |
| K | 300 | 12,979 / 9,532 | 3,766 | 3.84 | 1.42 | 90 (30.0%) |

#### Pass rate by category (pooled over runs)

| Category | A | K |
|---|---|---|
| cid002 | 41.3% (126) | 40.5% (126) |
| cid003 | 60.2% (123) | 63.4% (123) |
| cid004 | 52.9% (51) | 52.9% (51) |
