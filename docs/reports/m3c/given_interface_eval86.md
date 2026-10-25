# M3c: the given interface against the hidden testbench's names

Made by `tools/interface_given.py` over 86 problems. The interface check knows the hidden top module's name for **83 of 86**; of the 848 top-level `dut.` handles the hidden testbenches read, 704 (83%) are ports or parameters of that given module (the rest are internal signals, new ports a modification adds, or names the agent is not given).

| Source of the top module's interface | Problems |
|---|---|
| rtl | 29 |
| doc | 25 |
| header | 15 |
| testbench | 9 |
| prompt | 5 |
| not given | 3 |

| Problem | cid | Hidden top | Given (source) | `dut.` handles given / read |
|---|---|---|---|---|
| `64b66b_codec_0001` | cid005 | `top_64b66b_codec` | yes (doc) | 11 / 11 |
| `AES_encryption_decryption_0003` | cid016 | `aes128_encrypt` | yes (rtl) | 8 / 8 |
| `AES_encryption_decryption_0005` | cid016 | `aes128_decrypt` | yes (rtl) | 8 / 8 |
| `AES_encryption_decryption_0009` | cid004 | `aes_encrypt` | yes (rtl) | 8 / 8 |
| `AES_encryption_decryption_0012` | cid004 | `aes_decrypt` | yes (rtl) | 8 / 8 |
| `AES_encryption_decryption_0018` | cid005 | `padding_top` | yes (testbench) | 18 / 22 |
| `DES_0001` | cid003 | `des_enc` | yes (testbench) | 7 / 7 |
| `DES_0003` | cid004 | `des_dec` | yes (testbench) | 7 / 7 |
| `DES_0005` | cid005 | `des3_enc` | yes (testbench) | 7 / 7 |
| `DES_0007` | cid005 | `des3_dec` | yes (testbench) | 7 / 7 |
| `Min_Hamming_Distance_Finder_0001` | cid005 | `Min_Hamming_Distance_Finder` | yes (doc) | 6 / 6 |
| `PCIe_endpoint_0001` | cid003 | `pcie_endpoint` | yes (doc) | 1 / 1 |
| `arithmetic_progression_generator_0001` | cid016 | `arithmetic_progression_generator` | yes (rtl) | 10 / 10 |
| `async_fifo_compute_ram_application_0001` | cid003 | `async_fifo` | yes (doc) | 10 / 10 |
| `async_fifo_compute_ram_application_0006` | cid005 | `async_fifo` | yes (doc) | 10 / 10 |
| `async_filo_0001` | cid003 | `async_filo` | yes (doc) | 10 / 10 |
| `axi4lite_to_pcie_config_0003` | cid004 | `axi4lite_to_pcie_cfg_bridge` | yes (rtl) | 11 / 16 |
| `axis_broadcaster_0001` | cid016 | `axis_broadcast` | yes (rtl) | 13 / 13 |
| `axis_to_uart_0001` | cid003 | `axis_to_uart_tx` | yes (doc) | 6 / 6 |
| `axis_to_uart_0004` | cid003 | `uart_rx_to_axis` | yes (doc) | 6 / 6 |
| `barrel_shifter_0001` | cid016 | `barrel_shifter` | yes (rtl) | 4 / 4 |
| `barrel_shifter_0002` | cid004 | `barrel_shifter` | yes (rtl) | 4 / 5 |
| `bcd_adder_0004` | cid004 | `bcd_top` | no | 0 / 6 |
| `binary_search_tree_algorithms_0001` | cid004 | `delete_node_binary_search_tree` | yes (doc) | 8 / 15 |
| `binary_search_tree_algorithms_0014` | cid005 | `bst_operations` | yes (prompt) | 0 / 15 |
| `binary_to_gray_0003` | cid003 | `binary_to_gray` | yes (doc) | 3 / 3 |
| `byte_enable_ram_0002` | cid003 | `custom_byte_enable_ram` | yes (doc) | 11 / 11 |
| `cache_controller_0001` | cid003 | `cache_controller` | no | 0 / 10 |
| `caesar_cipher_0001` | cid016 | `caesar_cipher` | yes (rtl) | 3 / 3 |
| `cellular_automata_0002` | cid003 | `pseudoRandGenerator_ca` | yes (doc) | 5 / 5 |
| `cic_decimator_0001` | cid003 | `cic_decimator` | yes (doc) | 9 / 9 |
| `cipher_0001` | cid003 | `cipher` | yes (doc) | 6 / 6 |
| `cont_adder_0001` | cid003 | `continuous_adder` | yes (header) | 7 / 7 |
| `csr_using_apb_interface_0001` | cid003 | `csr_apb_interface` | no | 0 / 9 |
| `custom_fifo_0004` | cid016 | `fifo_buffer` | yes (rtl) | 14 / 14 |
| `direct_map_cache_0001` | cid003 | `direct_map_cache` | yes (doc) | 20 / 20 |
| `direct_map_cache_0003` | cid004 | `direct_map_cache` | yes (rtl) | 20 / 21 |
| `dma_xfer_engine_0001` | cid003 | `dma_xfer_engine` | yes (doc) | 10 / 10 |
| `door_lock_0001` | cid003 | `door_lock` | yes (header) | 13 / 13 |
| `dual_port_memory_0001` | cid016 | `dual_port_memory` | yes (rtl) | 11 / 11 |
| `dual_port_memory_0004` | cid004 | `dual_port_memory` | yes (rtl) | 8 / 10 |
| `dynamic_equalizer_0001` | cid003 | `dynamic_equalizer` | yes (prompt) | 0 / 8 |
| `dynamic_equalizer_0004` | cid004 | `dynamic_equalizer` | yes (rtl) | 6 / 6 |
| `dynamic_equalizer_0008` | cid005 | `equalizer_top` | yes (prompt) | 0 / 10 |
| `elevator_control_0004` | cid004 | `elevator_control_system` | yes (rtl) | 7 / 11 |
| `ethernet_mii_0004` | cid003 | `ethernet_mii_tx` | yes (header) | 11 / 11 |
| `ethernet_mii_0006` | cid003 | `ethernet_mac_tx` | yes (header) | 11 / 11 |
| `event_scheduler_0001` | cid003 | `event_scheduler` | yes (doc) | 10 / 10 |
| `event_scheduler_0004` | cid004 | `event_scheduler` | yes (rtl) | 11 / 18 |
| `event_storing_0001` | cid005 | `event_array` | yes (testbench) | 13 / 13 |
| `fixed_arbiter_0010` | cid004 | `fixed_priority_arbiter` | yes (rtl) | 7 / 10 |
| `gcd_0007` | cid005 | `crypto_accelerator` | yes (header) | 12 / 12 |
| `hdbn_codec_0001` | cid005 | `hdbn_top` | yes (doc) | 13 / 13 |
| `jpeg_runlength_enc_0001` | cid005 | `jpeg_runlength_enc` | yes (doc) | 10 / 10 |
| `lfsr_0001` | cid016 | `lfsr_8bit` | yes (rtl) | 4 / 4 |
| `lfsr_0005` | cid016 | `bit16_lfsr` | yes (rtl) | 4 / 4 |
| `low_power_channel_0001` | cid005 | `low_power_channel` | yes (testbench) | 12 / 12 |
| `monte_carlo_0006` | cid016 | `monte_carlo_dsp_monitor_top` | yes (rtl) | 8 / 8 |
| `multiplexer_0001` | cid003 | `multiplexer` | yes (header) | 6 / 6 |
| `nbit_swizzling_0001` | cid003 | `nbit_swizzling` | yes (doc) | 5 / 5 |
| `nmea_gps_0008` | cid004 | `nmea_decoder` | yes (rtl) | 6 / 11 |
| `phase_rotation_0013` | cid004 | `slicer_top` | yes (rtl) | 11 / 14 |
| `phase_rotation_0015` | cid004 | `top_phase_rotation` | yes (rtl) | 11 / 16 |
| `phase_rotation_0019` | cid004 | `phase_lut` | yes (rtl) | 4 / 6 |
| `prbs_0001` | cid005 | `scrambler_descrambler` | yes (doc) | 8 / 12 |
| `programmable_fsm_dynamic_state_encoding_0001` | cid004 | `fsm` | yes (rtl) | 7 / 9 |
| `queue_0001` | cid003 | `queue` | yes (doc) | 10 / 12 |
| `rc5_0001` | cid003 | `rc5_enc_16bit` | yes (prompt) | 0 / 6 |
| `rgb_color_space_conversion_0001` | cid003 | `rgb_color_space_hsv` | yes (header) | 13 / 13 |
| `rgb_color_space_conversion_0004` | cid004 | `rgb_color_space_conversion` | yes (rtl) | 16 / 20 |
| `secure_apb_history_shift_register_0001` | cid004 | `APBGlobalHistoryRegister_secure_top` | yes (header) | 17 / 17 |
| `sigma_delta_audio_0001` | cid003 | `sigma_delta_audio` | yes (doc) | 6 / 6 |
| `signed_comparator_0001` | cid003 | `signed_comparator` | yes (header) | 9 / 9 |
| `sorter_0009` | cid004 | `sorting_engine` | yes (rtl) | 6 / 6 |
| `sorter_0016` | cid005 | `order_matching_engine` | yes (header) | 9 / 9 |
| `sorter_0026` | cid005 | `order_matching_engine` | yes (header) | 9 / 9 |
| `spi_complex_mult_0002` | cid003 | `spi_complex_mult` | yes (doc) | 7 / 7 |
| `swizzler_0001` | cid003 | `swizzler` | yes (header) | 6 / 6 |
| `swizzler_0005` | cid005 | `swizzler_supervisor` | yes (header) | 9 / 9 |
| `sync_serial_communication_0001` | cid003 | `sync_serial_communication_tx_rx` | yes (testbench) | 7 / 7 |
| `systolic_array_0001` | cid005 | `systolic_array` | yes (testbench) | 12 / 12 |
| `thermostat_secure_0001` | cid004 | `thermostat_secure_top` | yes (header) | 18 / 18 |
| `traffic_light_controller_0001` | cid004 | `traffic_light_controller_top` | yes (prompt) | 0 / 5 |
| `ttc_lite_0001` | cid003 | `ttc_counter_lite` | yes (header) | 8 / 14 |
| `universal_shift_reg_0001` | cid003 | `universal_shift_register` | yes (doc) | 9 / 9 |
| `universal_shift_reg_0003` | cid004 | `universal_shift_register` | yes (rtl) | 8 / 16 |
