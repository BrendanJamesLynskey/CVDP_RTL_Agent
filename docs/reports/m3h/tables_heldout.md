#### Pack skill use per arm

| Arm | Problem-runs | Pack skills offered (mean `skills_listed`) | Loading any pack skill | Distinct pack skills per loading run (mean) | First-load turn: median [min–max] | Pass rate, loading / not |
|---|---|---|---|---|---|---|
| A | 300 | — | — | — | — | — |
| S1c | 300 | 15.0 | 300 (100.0%) | 2.14 | 1 [1–3] | 59.7% / – |
| S2c | 300 | 25.0 | 299 (99.7%) | 1.72 | 1 [1–3] | 56.2% / 100.0% |
| S2 (no hint, 1 run) | 100 | 25.0 | 3 (3.0%) | 1.33 | 1 [1–3] | 66.7% / 56.7% |

#### S1c: each skill loaded (300 problem-runs; pack v1.0)

Counted once per problem-run in which it was loaded. Descriptive only: the model chooses what to load, so a skill's pass rate mostly reflects the problems it is chosen for.

| Skill | Problem-runs loading it | Share | Pass rate when loaded | Pass rate when not |
|---|---|---|---|---|
| `spec-reading` | 278 | 92.7% | 59.0% | 68.2% |
| `fsm-design` | 75 | 25.0% | 36.0% | 67.6% |
| `reset-strategy` | 62 | 20.7% | 64.5% | 58.4% |
| `self-check-and-cocotb` | 50 | 16.7% | 62.0% | 59.2% |
| `sequential-and-combinational-coding` | 46 | 15.3% | 71.7% | 57.5% |
| `arithmetic-and-widths` | 27 | 9.0% | 74.1% | 58.2% |
| `pipelining-and-latency` | 26 | 8.7% | 92.3% | 56.6% |
| `bus-and-register-interfaces` | 16 | 5.3% | 31.2% | 61.3% |
| `valid-ready-handshake` | 16 | 5.3% | 56.2% | 59.9% |
| `counters-timers-and-edges` | 11 | 3.7% | 63.6% | 59.5% |
| `synthesisable-subset-and-parameters` | 10 | 3.3% | 80.0% | 59.0% |
| `memories-and-register-files` | 7 | 2.3% | 42.9% | 60.1% |
| `arbiters-encoders-and-muxes` | 6 | 2.0% | 100.0% | 58.8% |
| `clock-domain-crossing` | 6 | 2.0% | 33.3% | 60.2% |
| `fifo-design` | 5 | 1.7% | 60.0% | 59.7% |

#### S2c: each skill loaded (300 problem-runs; pack v2.0)

Counted once per problem-run in which it was loaded. Descriptive only: the model chooses what to load, so a skill's pass rate mostly reflects the problems it is chosen for.

| Skill | Problem-runs loading it | Share | Pass rate when loaded | Pass rate when not |
|---|---|---|---|---|
| `spec-reading` | 265 | 88.3% | 55.1% | 65.7% |
| `fsm-design` | 59 | 19.7% | 35.6% | 61.4% |
| `arithmetic-and-widths` | 23 | 7.7% | 60.9% | 56.0% |
| `working-in-existing-code` | 21 | 7.0% | 52.4% | 56.6% |
| `minimal-change-modification` | 17 | 5.7% | 52.9% | 56.5% |
| `reset-strategy` | 17 | 5.7% | 70.6% | 55.5% |
| `valid-ready-handshake` | 13 | 4.3% | 38.5% | 57.1% |
| `sequential-and-combinational-coding` | 13 | 4.3% | 69.2% | 55.7% |
| `bus-and-register-interfaces` | 12 | 4.0% | 41.7% | 56.9% |
| `pipelining-and-latency` | 11 | 3.7% | 100.0% | 54.7% |
| `hardware-algorithms` | 9 | 3.0% | 22.2% | 57.4% |
| `clock-domain-crossing` | 8 | 2.7% | 37.5% | 56.8% |
| `self-check-and-cocotb` | 7 | 2.3% | 71.4% | 56.0% |
| `counters-timers-and-edges` | 6 | 2.0% | 66.7% | 56.1% |
| `arbiters-encoders-and-muxes` | 5 | 1.7% | 100.0% | 55.6% |
| `caches-and-memory-systems` | 5 | 1.7% | 80.0% | 55.9% |
| `fifo-design` | 5 | 1.7% | 40.0% | 56.6% |
| `crc-lfsr-and-line-codes` | 5 | 1.7% | 40.0% | 56.6% |
| `fixed-point-and-dsp-datapaths` | 4 | 1.3% | 100.0% | 55.7% |
| `serial-and-network-protocols` | 3 | 1.0% | 0.0% | 56.9% |
| `synthesisable-subset-and-parameters` | 3 | 1.0% | 100.0% | 55.9% |
| `memories-and-register-files` | 2 | 0.7% | 50.0% | 56.4% |
| `module-integration` | 1 | 0.3% | 0.0% | 56.5% |

#### S2 (no hint, 1 run): each skill loaded (100 problem-runs; pack v2.0)

Counted once per problem-run in which it was loaded. Descriptive only: the model chooses what to load, so a skill's pass rate mostly reflects the problems it is chosen for.

| Skill | Problem-runs loading it | Share | Pass rate when loaded | Pass rate when not |
|---|---|---|---|---|
| `spec-reading` | 2 | 2.0% | 50.0% | 57.1% |
| `fixed-point-and-dsp-datapaths` | 1 | 1.0% | 100.0% | 56.6% |
| `pipelining-and-latency` | 1 | 1.0% | 100.0% | 56.6% |

#### Bundled (Claude Code's own) skills loaded

| Arm | Problem-runs | Bundled skill calls |
|---|---|---|
| S1c | 300 | none |
| S2c | 300 | none |
| S2 (no hint, 1 run) | 100 | none |

#### Effort per arm (Claude Code's own counts; nothing billed per call)

| Arm | Problem-runs | Turns: median (mean) | Wall s: median | Wall-cap stops | Prompt tokens incl. cache, per run (mean) | Completion tokens per run (mean) |
|---|---|---|---|---|---|---|
| A | 300 | 6 (6.9) | 32 | 0 | 167,423 | 10,156 |
| S1c | 300 | 12 (12.7) | 46 | 2 | 253,396 | 13,045 |
| S2c | 300 | 11 (11.7) | 48 | 1 | 244,171 | 12,612 |
| S2 (no hint, 1 run) | 100 | 7 (7.7) | 36 | 0 | 209,515 | 11,456 |

#### Stop reasons per arm

| Arm | Stop reasons |
|---|---|
| A | submit 300 |
| S1c | submit 298, wall_time 2 |
| S2c | submit 299, wall_time 1 |
| S2 (no hint, 1 run) | submit 100 |
