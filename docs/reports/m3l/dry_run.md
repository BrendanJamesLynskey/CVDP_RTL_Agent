# M3l dry run of the retriever (pack v4.0)

Free and local: the retriever run over the visible files of each problem (prompt, docs/, rtl/, verif/), no model call. Ids and numbers only: no pack text and no code. Rule and constants: [preregistration.md](preregistration.md).

Pack entries: 86 in the index; 49 withheld by the repo deny-list (for every problem); **37 remain** (35 upstream files); 0 dropped as not byte-exact. Constants: K=2, minimum score 0.55, 12000 bytes, overlap rule 5-line shingles at 0.10.

Remaining entries by repo: Xilinx/open-nic-shell 3, chipsalliance/caliptra-rtl 5, lowRISC/opentitan 26, nvdla/hw 3.
Withheld by the repo deny-list: axi 5, cc 27, cv32e40p 4, cva6 5, ibex 8 (entry-id prefixes).

## heldout100: 100 problems

- problems that get an example: **3** (one: 3, two: 0); **no example: 97** (these runs are arm R exactly)
- withheld by the overlap rule: 0 entry/problem pairs (0 problems); the rule would withhold 0 pairs if every entry were tried
- bytes shown: mean 1830, max 3050
- most-used entries: ot-prim-ram-1p (1), caliptra-ahb-to-reg-adapter (1), ot-prim-subreg (1)

| Problem | Chosen entries | Scores |
|---|---|---|
| cvdp_copilot_MSHR_0001 | ot-prim-ram-1p | 0.577 |
| cvdp_copilot_apb_dsp_unit_0001 | caliptra-ahb-to-reg-adapter | 0.556 |
| cvdp_copilot_axi_register_0001 | ot-prim-subreg | 0.620 |

## dev86: 86 problems

- problems that get an example: **13** (one: 11, two: 2); **no example: 73** (these runs are arm R exactly)
- withheld by the overlap rule: 0 entry/problem pairs (0 problems); the rule would withhold 0 pairs if every entry were tried
- bytes shown: mean 1835, max 3050
- most-used entries: ot-prim-fifo-async-gray-pointers (4), ot-prim-ram-1p (3), ot-aes-shift-rows (2), ot-aes-mix-columns (1), ot-prim-subreg (1), ot-uart-rx (1), ot-prim-pulse-sync (1), ot-prim-clock-gating (1)

| Problem | Chosen entries | Scores |
|---|---|---|
| cvdp_agentic_AES_encryption_decryption_0003 | ot-aes-shift-rows | 0.587 |
| cvdp_agentic_AES_encryption_decryption_0005 | ot-aes-shift-rows, ot-aes-mix-columns | 0.671, 0.601 |
| cvdp_agentic_async_fifo_compute_ram_application_0001 | ot-prim-fifo-async-gray-pointers | 0.674 |
| cvdp_agentic_async_fifo_compute_ram_application_0006 | ot-prim-fifo-async-gray-pointers | 0.625 |
| cvdp_agentic_async_filo_0001 | ot-prim-fifo-async-gray-pointers | 0.625 |
| cvdp_agentic_axi4lite_to_pcie_config_0003 | ot-prim-subreg | 0.597 |
| cvdp_agentic_axis_to_uart_0004 | ot-uart-rx | 0.621 |
| cvdp_agentic_byte_enable_ram_0002 | ot-prim-ram-1p | 0.639 |
| cvdp_agentic_dual_port_memory_0004 | ot-prim-ram-1p | 0.577 |
| cvdp_agentic_ethernet_mii_0004 | ot-prim-fifo-async-gray-pointers | 0.787 |
| cvdp_agentic_ethernet_mii_0006 | ot-prim-ram-1p | 0.577 |
| cvdp_agentic_hdbn_codec_0001 | ot-prim-pulse-sync | 0.559 |
| cvdp_agentic_low_power_channel_0001 | ot-prim-clock-gating, opennic-request-queue | 0.587, 0.564 |

All problems, including those with no example, are in [retrieval.csv](retrieval.csv); the overlap deny-list is [overlap_deny.csv](overlap_deny.csv).
