#### Pack skill use per arm

| Arm | Problem-runs | Pack skills offered (mean `skills_listed`) | Loading any pack skill | Distinct pack skills per loading run (mean) | First-load turn: median [min–max] | Pass rate, loading / not |
|---|---|---|---|---|---|---|
| A | 86 | — | — | — | — | — |
| S1c | 86 | 15.0 | 86 (100.0%) | 2.60 | 1 [1–4] | 66.3% / – |
| S2c | 86 | 25.0 | 86 (100.0%) | 2.72 | 1 [1–5] | 70.9% / – |

#### S1c: each skill loaded (86 problem-runs; pack v1.0)

Counted once per problem-run in which it was loaded. Descriptive only: the model chooses what to load, so a skill's pass rate mostly reflects the problems it is chosen for.

| Skill | Problem-runs loading it | Share | Pass rate when loaded | Pass rate when not |
|---|---|---|---|---|
| `spec-reading` | 85 | 98.8% | 67.1% | 0.0% |
| `self-check-and-cocotb` | 41 | 47.7% | 63.4% | 68.9% |
| `fsm-design` | 20 | 23.3% | 45.0% | 72.7% |
| `reset-strategy` | 13 | 15.1% | 53.8% | 68.5% |
| `sequential-and-combinational-coding` | 13 | 15.1% | 61.5% | 67.1% |
| `pipelining-and-latency` | 11 | 12.8% | 63.6% | 66.7% |
| `arithmetic-and-widths` | 10 | 11.6% | 60.0% | 67.1% |
| `memories-and-register-files` | 7 | 8.1% | 85.7% | 64.6% |
| `synthesisable-subset-and-parameters` | 6 | 7.0% | 83.3% | 65.0% |
| `clock-domain-crossing` | 6 | 7.0% | 33.3% | 68.8% |
| `fifo-design` | 4 | 4.7% | 75.0% | 65.9% |
| `bus-and-register-interfaces` | 3 | 3.5% | 33.3% | 67.5% |
| `valid-ready-handshake` | 3 | 3.5% | 66.7% | 66.3% |
| `arbiters-encoders-and-muxes` | 1 | 1.2% | 100.0% | 65.9% |
| `counters-timers-and-edges` | 1 | 1.2% | 0.0% | 67.1% |

#### S2c: each skill loaded (86 problem-runs; pack v2.0)

Counted once per problem-run in which it was loaded. Descriptive only: the model chooses what to load, so a skill's pass rate mostly reflects the problems it is chosen for.

| Skill | Problem-runs loading it | Share | Pass rate when loaded | Pass rate when not |
|---|---|---|---|---|
| `spec-reading` | 68 | 79.1% | 69.1% | 77.8% |
| `working-in-existing-code` | 24 | 27.9% | 70.8% | 71.0% |
| `module-integration` | 18 | 20.9% | 66.7% | 72.1% |
| `minimal-change-modification` | 16 | 18.6% | 62.5% | 72.9% |
| `fsm-design` | 13 | 15.1% | 69.2% | 71.2% |
| `rtl-debugging` | 11 | 12.8% | 90.9% | 68.0% |
| `block-ciphers-in-hardware` | 10 | 11.6% | 80.0% | 69.7% |
| `self-check-and-cocotb` | 10 | 11.6% | 60.0% | 72.4% |
| `clock-domain-crossing` | 7 | 8.1% | 71.4% | 70.9% |
| `hardware-algorithms` | 6 | 7.0% | 83.3% | 70.0% |
| `sequential-and-combinational-coding` | 6 | 7.0% | 83.3% | 70.0% |
| `pipelining-and-latency` | 5 | 5.8% | 100.0% | 69.1% |
| `fixed-point-and-dsp-datapaths` | 5 | 5.8% | 60.0% | 71.6% |
| `crc-lfsr-and-line-codes` | 5 | 5.8% | 80.0% | 70.4% |
| `bus-and-register-interfaces` | 4 | 4.7% | 50.0% | 72.0% |
| `serial-and-network-protocols` | 4 | 4.7% | 75.0% | 70.7% |
| `arithmetic-and-widths` | 3 | 3.5% | 66.7% | 71.1% |
| `fifo-design` | 3 | 3.5% | 66.7% | 71.1% |
| `valid-ready-handshake` | 3 | 3.5% | 100.0% | 69.9% |
| `memories-and-register-files` | 3 | 3.5% | 100.0% | 69.9% |
| `caches-and-memory-systems` | 3 | 3.5% | 0.0% | 73.5% |
| `reset-strategy` | 3 | 3.5% | 66.7% | 71.1% |
| `synthesisable-subset-and-parameters` | 2 | 2.3% | 100.0% | 70.2% |
| `arbiters-encoders-and-muxes` | 1 | 1.2% | 100.0% | 70.6% |
| `counters-timers-and-edges` | 1 | 1.2% | 0.0% | 71.8% |

#### Bundled (Claude Code's own) skills loaded

| Arm | Problem-runs | Bundled skill calls |
|---|---|---|
| S1c | 86 | none |
| S2c | 86 | none |

#### Effort per arm (Claude Code's own counts; nothing billed per call)

| Arm | Problem-runs | Turns: median (mean) | Wall s: median | Wall-cap stops | Prompt tokens incl. cache, per run (mean) | Completion tokens per run (mean) |
|---|---|---|---|---|---|---|
| A | 86 | 11 (12.5) | 89 | 2 | 431,567 | 21,273 |
| S1c | 86 | 17.5 (17.5) | 100 | 4 | 456,353 | 21,131 |
| S2c | 86 | 18 (19.1) | 109 | 1 | 487,439 | 22,347 |

#### Stop reasons per arm

| Arm | Stop reasons |
|---|---|
| A | submit 84, wall_time 2 |
| S1c | submit 82, wall_time 4 |
| S2c | submit 85, wall_time 1 |
