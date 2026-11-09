### Per problem: passes out of 5 runs, and the example(s) shown

| Problem | Set | R | E | E - R | Example(s) shown to E | E llm_error rows |
|---|---|---|---|---|---|---|
| cvdp_agentic_AES_encryption_decryption_0003 | dev | 5/5 | 5/5 | +0 | ot-aes-shift-rows | 0 |
| cvdp_agentic_AES_encryption_decryption_0005 | dev | 5/5 | 5/5 | +0 | ot-aes-shift-rows;ot-aes-mix-columns | 0 |
| cvdp_agentic_async_fifo_compute_ram_application_0001 | dev | 3/5 | 5/5 | +2 | ot-prim-fifo-async-gray-pointers | 0 |
| cvdp_agentic_async_fifo_compute_ram_application_0006 | dev | 5/5 | 5/5 | +0 | ot-prim-fifo-async-gray-pointers | 0 |
| cvdp_agentic_async_filo_0001 | dev | 5/5 | 5/5 | +0 | ot-prim-fifo-async-gray-pointers | 0 |
| cvdp_agentic_axi4lite_to_pcie_config_0003 | dev | 0/5 | 1/5 | +1 | ot-prim-subreg | 0 |
| cvdp_agentic_axis_to_uart_0004 | dev | 5/5 | 5/5 | +0 | ot-uart-rx | 0 |
| cvdp_agentic_byte_enable_ram_0002 | dev | 5/5 | 5/5 | +0 | ot-prim-ram-1p | 0 |
| cvdp_agentic_dual_port_memory_0004 | dev | 4/5 | 5/5 | +1 | ot-prim-ram-1p | 0 |
| cvdp_agentic_ethernet_mii_0004 | dev | 4/5 | 4/5 | +0 | ot-prim-fifo-async-gray-pointers | 0 |
| cvdp_agentic_ethernet_mii_0006 | dev | 4/5 | 2/5 | -2 | ot-prim-ram-1p | 0 |
| cvdp_agentic_hdbn_codec_0001 | dev | 0/5 | 0/5 | +0 | ot-prim-pulse-sync | 2 |
| cvdp_agentic_low_power_channel_0001 | dev | 5/5 | 5/5 | +0 | ot-prim-clock-gating;opennic-request-queue | 0 |
| cvdp_copilot_MSHR_0001 | held-out | 0/5 | 0/5 | +0 | ot-prim-ram-1p | 0 |
| cvdp_copilot_apb_dsp_unit_0001 | held-out | 0/5 | 3/5 | +3 | caliptra-ahb-to-reg-adapter | 0 |
| cvdp_copilot_axi_register_0001 | held-out | 3/5 | 3/5 | +0 | ot-prim-subreg | 0 |

### Dev / held-out split of the 16 (descriptive only)

| Set | Problems | Runs per arm | R passes | E passes | R rate | E rate |
|---|---|---|---|---|---|---|
| held-out | 3 | 15 | 3 | 6 | 20.0% | 40.0% |
| dev | 13 | 65 | 50 | 52 | 76.9% | 80.0% |
| both | 16 | 80 | 53 | 58 | 66.2% | 72.5% |

### Effort and estimated cost, 16 problems x 5 runs per arm

| | R | E |
|---|---|---|
| Rows | 80 | 80 |
| Prompt tokens, total | 14,466,515 | 13,463,471 |
| Completion tokens, total | 1,146,992 | 1,137,245 |
| Cache-read tokens, total | 12,580,808 | 11,592,875 |
| Turns, median | 6.5 | 7.0 |
| Turns, mean | 8.54 | 8.28 |
| Wall time per run, median (s) | 53.3 | 58.7 |
| Wall time per run, mean (s) | 79.7 | 79.5 |
| Estimated cost, total (USD, `api_cost_estimate_usd`) | 0.9350 | 0.9183 |
| Estimated cost per run (USD) | 0.01169 | 0.01148 |

Provider-reported `cost_usd` is 0 on every row (unreported), so the estimate column is the only cost figure.

E rows by example size: runs with an example `examples_bytes` median 1488 bytes; 80 of 80 E runs carried examples.

### Failure labels (`failure_label`; empty = passed) on the 16

| Label | R | E |
|---|---|---|
| (passed) | 53 | 58 |
| compile_fail_own | 4 | 0 |
| llm_error | 0 | 2 |
| signal_missing_hidden | 3 | 1 |
| sim_incomplete | 5 | 5 |
| stopped_by_cap | 1 | 0 |
| tests_failed_no_selfcheck | 14 | 14 |

### Stop reasons

| Stop reason | R | E |
|---|---|---|
| llm_error | 0 | 2 |
| submit | 79 | 78 |
| wall_time | 1 | 0 |

### Withheld entries per E run

`examples_withheld_repo` values: ['49']; `examples_withheld_overlap` values: ['0']; `skill_text_copied` values: ['0'].
