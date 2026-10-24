255 failed (problem, run) rows of 552.

#### Primary label by arm

| Label | claude-haiku-5.5 (low) | deepseek-v4.1-flash (off) | gpt-6-luna (default) | All |
|---|---|---|---|---|
| stopped_by_cap | 0 | 17 | 7 | 24 |
| gave_up | 5 | 1 | 0 | 6 |
| needs_artifacts | 71 | 82 | 72 | 225 |
| **All failures** | 76 | 100 | 79 | 255 |

#### Primary label by cid

| Label | cid003 | cid004 | cid005 | cid016 | All |
|---|---|---|---|---|---|
| stopped_by_cap | 8 | 11 | 3 | 2 | 24 |
| gave_up | 1 | 3 | 0 | 2 | 6 |
| needs_artifacts | 78 | 59 | 65 | 23 | 225 |
| **All failures** | 87 | 73 | 68 | 27 | 255 |

Secondary flags: single_turn 83, partial_pass 3, best_edit_restored 3, empty_replies 1

#### The 28 problems no reference run solved (552 rows from 6 CSVs)

| Problem | cid | Labels across the runs here |
|---|---|---|
| `DES_0001` | cid003 | needs_artifacts ×5, stopped_by_cap ×1 |
| `arithmetic_progression_generator_0001` | cid016 | needs_artifacts ×6 |
| `binary_search_tree_algorithms_0001` | cid004 | needs_artifacts ×5, gave_up ×1 |
| `binary_search_tree_algorithms_0014` | cid005 | needs_artifacts ×6 |
| `csr_using_apb_interface_0001` | cid003 | needs_artifacts ×6 |
| `digital_stopwatch_0001` | cid005 | needs_artifacts ×6 |
| `dynamic_equalizer_0001` | cid003 | needs_artifacts ×6 |
| `dynamic_equalizer_0008` | cid005 | needs_artifacts ×6 |
| `elevator_control_0004` | cid004 | needs_artifacts ×5, stopped_by_cap ×1 |
| `hdbn_codec_0001` | cid005 | needs_artifacts ×6 |
| `jpeg_runlength_enc_0001` | cid005 | needs_artifacts ×6 |
| `lfsr_0005` | cid016 | needs_artifacts ×5, gave_up ×1 |
| `nmea_gps_0008` | cid004 | needs_artifacts ×3, stopped_by_cap ×2, gave_up ×1 |
| `phase_rotation_0010` | cid005 | needs_artifacts ×6 |
| `phase_rotation_0015` | cid004 | needs_artifacts ×5, stopped_by_cap ×1 |
| `phase_rotation_0028` | cid005 | needs_artifacts ×6 |
| `phase_rotation_0031` | cid004 | needs_artifacts ×6 |
| `phase_rotation_0038` | cid003 | needs_artifacts ×4, gave_up ×1, stopped_by_cap ×1 |
| `poly_decimator_0001` | cid005 | needs_artifacts ×5, stopped_by_cap ×1 |
| `queue_0001` | cid003 | needs_artifacts ×6 |
| `rc5_0001` | cid003 | needs_artifacts ×6 |
| `secure_apb_history_shift_register_0001` | cid004 | needs_artifacts ×5, stopped_by_cap ×1 |
| `sigma_delta_audio_0001` | cid003 | needs_artifacts ×6 |
| `spi_complex_mult_0002` | cid003 | needs_artifacts ×5, stopped_by_cap ×1 |
| `sync_serial_communication_0001` | cid003 | needs_artifacts ×5, stopped_by_cap ×1 |
| `thermostat_secure_0001` | cid004 | needs_artifacts ×6 |
| `traffic_light_controller_0001` | cid004 | needs_artifacts ×6 |
| `ttc_lite_0001` | cid003 | needs_artifacts ×6 |

