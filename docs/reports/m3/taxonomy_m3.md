565 failed (problem, run) rows of 1288.

#### Primary label by arm

| Label | A1 | A2 | B1 | B2 | C1 | C2 | D1 | D2 | E1 | E2 | F1 | F2 | G1 | G2 | All |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| no_edit | 1 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 5 |
| stopped_by_cap | 4 | 2 | 1 | 2 | 8 | 6 | 3 | 3 | 6 | 9 | 3 | 1 | 5 | 3 | 56 |
| sim_incomplete | 1 | 0 | 3 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 1 | 3 | 1 | 13 |
| compile_fail_hidden | 5 | 6 | 7 | 5 | 4 | 6 | 5 | 4 | 5 | 5 | 5 | 6 | 5 | 6 | 74 |
| signal_missing_hidden | 7 | 7 | 3 | 5 | 6 | 5 | 5 | 6 | 5 | 5 | 6 | 6 | 3 | 4 | 73 |
| tests_failed_selfcheck_passed | 3 | 6 | 0 | 0 | 11 | 14 | 0 | 0 | 4 | 3 | 5 | 5 | 6 | 4 | 61 |
| tests_failed_selfcheck_failed | 1 | 1 | 0 | 0 | 2 | 2 | 0 | 0 | 0 | 1 | 0 | 1 | 2 | 2 | 12 |
| tests_failed_no_selfcheck | 17 | 19 | 23 | 30 | 11 | 8 | 27 | 28 | 17 | 18 | 16 | 18 | 18 | 21 | 271 |
| **All failures** | 39 | 41 | 38 | 44 | 42 | 41 | 42 | 41 | 39 | 42 | 35 | 38 | 42 | 41 | 565 |

#### Primary label by cid

| Label | cid003 | cid004 | cid005 | cid016 | All |
|---|---|---|---|---|---|
| no_edit | 0 | 2 | 0 | 3 | 5 |
| stopped_by_cap | 14 | 23 | 11 | 8 | 56 |
| sim_incomplete | 0 | 11 | 1 | 1 | 13 |
| compile_fail_hidden | 45 | 0 | 29 | 0 | 74 |
| signal_missing_hidden | 30 | 11 | 32 | 0 | 73 |
| tests_failed_selfcheck_passed | 13 | 8 | 16 | 24 | 61 |
| tests_failed_selfcheck_failed | 2 | 5 | 1 | 4 | 12 |
| tests_failed_no_selfcheck | 97 | 100 | 47 | 27 | 271 |
| **All failures** | 201 | 160 | 137 | 67 | 565 |

Secondary flags: single_turn 254, lint_off 166, self_check_off 165, tests_failed_selfcheck_failed 33, tests_failed_no_selfcheck 11, partial_pass 11, signal_missing_hidden 7, empty_replies 4, compile_fail_hidden 4, sim_incomplete 3, best_edit_restored 2, compile_fail_own 2, tests_failed_selfcheck_passed 1

#### The 28 problems no reference run solved (552 rows from 6 CSVs)

| Problem | cid | Labels across the runs here |
|---|---|---|
| `DES_0001` | cid003 | stopped_by_cap ×7, tests_failed_no_selfcheck ×4, tests_failed_selfcheck_passed ×1, tests_failed_selfcheck_failed ×1 |
| `arithmetic_progression_generator_0001` | cid016 | tests_failed_no_selfcheck ×6, tests_failed_selfcheck_passed ×5, tests_failed_selfcheck_failed ×2, stopped_by_cap ×1 |
| `binary_search_tree_algorithms_0001` | cid004 | tests_failed_no_selfcheck ×13, tests_failed_selfcheck_failed ×1 |
| `binary_search_tree_algorithms_0014` | cid005 | tests_failed_no_selfcheck ×8, stopped_by_cap ×3, tests_failed_selfcheck_passed ×2, compile_fail_hidden ×1 |
| `csr_using_apb_interface_0001` | cid003 | tests_failed_no_selfcheck ×11, tests_failed_selfcheck_passed ×2, signal_missing_hidden ×1 |
| `digital_stopwatch_0001` | cid005 | compile_fail_hidden ×6, signal_missing_hidden ×5, tests_failed_no_selfcheck ×2, stopped_by_cap ×1 |
| `dynamic_equalizer_0001` | cid003 | tests_failed_no_selfcheck ×13, tests_failed_selfcheck_passed ×1 |
| `dynamic_equalizer_0008` | cid005 | tests_failed_no_selfcheck ×7, stopped_by_cap ×3, tests_failed_selfcheck_passed ×2, tests_failed_selfcheck_failed ×1, signal_missing_hidden ×1 |
| `elevator_control_0004` | cid004 | sim_incomplete ×6, tests_failed_no_selfcheck ×4, stopped_by_cap ×4 |
| `hdbn_codec_0001` | cid005 | compile_fail_hidden ×8, tests_failed_no_selfcheck ×6 |
| `jpeg_runlength_enc_0001` | cid005 | tests_failed_no_selfcheck ×8, tests_failed_selfcheck_passed ×3, stopped_by_cap ×1 |
| `lfsr_0005` | cid016 | tests_failed_no_selfcheck ×7, tests_failed_selfcheck_passed ×4, no_edit ×2 |
| `nmea_gps_0008` | cid004 | tests_failed_no_selfcheck ×7, stopped_by_cap ×4, tests_failed_selfcheck_passed ×2, tests_failed_selfcheck_failed ×1 |
| `phase_rotation_0010` | cid005 | signal_missing_hidden ×13, stopped_by_cap ×1 |
| `phase_rotation_0015` | cid004 | tests_failed_no_selfcheck ×10, stopped_by_cap ×3 |
| `phase_rotation_0028` | cid005 | compile_fail_hidden ×14 |
| `phase_rotation_0031` | cid004 | signal_missing_hidden ×11, stopped_by_cap ×2, tests_failed_no_selfcheck ×1 |
| `phase_rotation_0038` | cid003 | signal_missing_hidden ×14 |
| `poly_decimator_0001` | cid005 | signal_missing_hidden ×13, stopped_by_cap ×1 |
| `queue_0001` | cid003 | tests_failed_no_selfcheck ×11, tests_failed_selfcheck_passed ×2, stopped_by_cap ×1 |
| `rc5_0001` | cid003 | tests_failed_no_selfcheck ×5, compile_fail_hidden ×5, tests_failed_selfcheck_passed ×3, tests_failed_selfcheck_failed ×1 |
| `secure_apb_history_shift_register_0001` | cid004 | tests_failed_no_selfcheck ×13, stopped_by_cap ×1 |
| `sigma_delta_audio_0001` | cid003 | compile_fail_hidden ×14 |
| `spi_complex_mult_0002` | cid003 | tests_failed_no_selfcheck ×11, tests_failed_selfcheck_passed ×2, stopped_by_cap ×1 |
| `sync_serial_communication_0001` | cid003 | compile_fail_hidden ×13, stopped_by_cap ×1 |
| `thermostat_secure_0001` | cid004 | tests_failed_no_selfcheck ×12, stopped_by_cap ×2 |
| `traffic_light_controller_0001` | cid004 | tests_failed_no_selfcheck ×12, tests_failed_selfcheck_failed ×1, stopped_by_cap ×1 |
| `ttc_lite_0001` | cid003 | signal_missing_hidden ×12, tests_failed_no_selfcheck ×2 |

#### Evidence, up to 3 per label

**no_edit**: `cvdp_agentic_lfsr_0005` (A1#seed1)
```
log:                                                             assert first_value == last_value, f"LFSR does not support maximal length sequence, first value {hex(
log:                                                         AssertionError: LFSR does not support maximal length sequence, first value 0xd670 does not match last va
log:                                                         assert 54896 == 35380
log: ======================== 1 failed, 3 warnings in 10.71s ========================
trace: llm edit decision={"changed": [], "errors": 0, "checks": ["compile", "lint", "synth"], "testbench"
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/bit16
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/bit16_lfsr.sv; hierarchy -auto-top; proc;
trace: llm reflect decision="submit"
trace: summary stop=submit files=[]
```

**no_edit**: `cvdp_agentic_caesar_cipher_0001` (B1#seed1)
```
log:                                                         assert 'QNUUX' == 'khoor'
log:                                                             assert output == expected, f"Failed for input '{text}' with key {key}: expected '{expected}', got '{
log:                                                         AssertionError: Failed for input 'hello' with key 3: expected 'khoor', got 'QNUUX'
log: ======================== 1 failed, 3 warnings in 0.76s =========================
trace: llm edit decision={"changed": [], "errors": 0, "checks": ["compile", "lint", "synth"], "testbench"
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/caesa
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/caesar_cipher.sv; hierarchy -auto-top; pr
trace: llm reflect decision="submit"
trace: summary stop=submit files=[]
```

**no_edit**: `cvdp_agentic_lfsr_0005` (B2#seed1)
```
log:                                                             assert first_value == last_value, f"LFSR does not support maximal length sequence, first value {hex(
log:                                                         AssertionError: LFSR does not support maximal length sequence, first value 0xd670 does not match last va
log:                                                         assert 54896 == 35380
log: ======================== 1 failed, 3 warnings in 10.64s ========================
trace: llm edit decision={"changed": [], "errors": 0, "checks": ["compile", "lint", "synth"], "testbench"
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/bit16
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/bit16_lfsr.sv; hierarchy -auto-top; proc;
trace: llm reflect decision="submit"
trace: summary stop=submit files=[]
```

**stopped_by_cap**: `cvdp_agentic_DES_0001` (A1#seed1)
```
log:      0.00ns WARNING  gpi                                Unable to create pc2 via any registered implementation
log:      0.00ns WARNING  gpi                                Unable to create permute_fp via any registered implementation
log:      0.00ns WARNING  gpi                                Unable to create permute_ip via any registered implementation
log: ======================== 1 failed, 3 warnings in 0.61s =========================
trace: file_write exit=0 write rtl/des_enc.sv
trace: llm edit decision={"changed": ["rtl/des_enc.sv"], "errors": 0, "checks": ["compile", "testbench"],
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/S1.sv
trace: testbench_build exit=0 iverilog -g2012 -o /code/rundir/agent_tb/tb.vvp -s tb -I/code/rtl /code/rtl/S1.s
trace: testbench_run exit=0 vvp -n /code/rundir/agent_tb/tb.vvp
trace: summary stop=wall_time files=['rtl/S1.sv', 'rtl/S2.sv', 'rtl/S3.sv', 'rtl/S4.sv', 'rtl/S5.sv', 'rtl/S6.sv', 'rtl/S7.sv', 'rtl/S8.sv', 'rtl/des_enc.sv']
```

**stopped_by_cap**: `cvdp_agentic_custom_fifo_0004` (A1#seed1)
```
log:                                                         assert (1 != 'X' and 1 == 0)
log:                                                             assert safe_int(dut.out_valid_o) != "X" and int(dut.out_valid_o.value) == 0, \
log:                                                         AssertionError: Test 2: out_valid_o should be 0 after instruction pop
log: ======================== 1 failed, 4 warnings in 0.83s =========================
trace: testbench_run exit=0 vvp -n /code/rundir/agent_tb/tb.vvp
trace: llm reflect decision="edit_again"
trace: llm edit decision={"changed": [], "errors": 0, "checks": ["compile", "lint"], "testbench": []}
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/fifo_
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: summary stop=wall_time files=['rtl/fifo_buffer.sv']
```

**stopped_by_cap**: `cvdp_agentic_dynamic_equalizer_0004` (A1#seed1)
```
log: =================================== FAILURES ===================================
log:     70.00ns ERROR    root                               FAIL: Data Output Real mismatch. Expected: 8192, Got: 8207
log:     70.00ns ERROR    root                               FAIL: Data Output Imaginary mismatch. Expected: -8192, Got: -8177
log: Cleaning up Docker resources...
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/coeff
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/coeff_update.sv /code/rtl/dynamic_equaliz
trace: testbench_build exit=4 iverilog -g2012 -o /code/rundir/agent_tb/tb.vvp -s tb_mcma -I/code/rtl /code/rtl
trace: llm reflect decision="edit_again"
trace: summary stop=wall_time files=['rtl/coeff_update.sv', 'rtl/dynamic_equalizer.sv', 'rtl/error_calc.sv']
```

**sim_incomplete**: `cvdp_agentic_elevator_control_0004` (A1#seed1)
```
harness: Failed to execute objective harness
log:  50090.00ns INFO     cocotb.elevator_control_system     Door closed successfully after reaching floor
log:  50110.00ns INFO     cocotb.elevator_control_system     Requesting floor 2,4,6
trace: llm edit decision={"changed": ["rtl/elevator_control_system.sv"], "errors": 0, "checks": ["compile
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/eleva
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/elevator_control_system.sv; hierarchy -au
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/elevator_control_system.sv']
```

**sim_incomplete**: `cvdp_agentic_axi4lite_to_pcie_config_0003` (B1#seed1)
```
harness: Failed to execute objective harness
log:                                                             Testbench for AXI4-Lite Read/Write Transactions with burst support.
log:     20.00ns INFO     cocotb.axi4lite_to_pcie_cfg_bridge TEST CASE 1: Write 0xAABBCCDD to 0x10 and Read Back
trace: llm edit decision={"changed": ["rtl/axi4lite_to_pcie_cfg_bridge.sv"], "errors": 0, "checks": ["com
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/axi4l
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/axi4lite_to_pcie_cfg_bridge.sv; hierarchy
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/axi4lite_to_pcie_cfg_bridge.sv']
```

**sim_incomplete**: `cvdp_agentic_elevator_control_0004` (B1#seed1)
```
harness: Failed to execute objective harness
log: 150230.00ns INFO     cocotb.elevator_control_system     Waiting for the door to close
log: 200190.00ns INFO     cocotb.elevator_control_system     Door closed successfully after reaching floor
trace: llm edit decision={"changed": ["rtl/elevator_control_system.sv"], "errors": 0, "checks": ["compile
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/eleva
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/elevator_control_system.sv; hierarchy -au
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/elevator_control_system.sv']
```

**compile_fail_hidden**: `cvdp_agentic_cache_controller_0001` (A1#seed1)
```
log: =================================== FAILURES ===================================
log:         CalledProcessError. The CalledProcessError object will have the return code
log:         triggered by setting any of text, encoding, errors or universal_newlines.
log: ======================== 1 failed, 3 warnings in 0.20s =========================
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/cache_controller.v; hierarchy -auto-top; 
trace: testbench_build exit=0 iverilog -g2012 -o /code/rundir/agent_tb/tb.vvp -s tb_cache_controller -I/code/r
trace: testbench_run exit=0 vvp -n /code/rundir/agent_tb/tb.vvp
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/cache_controller.v']
```

**compile_fail_hidden**: `cvdp_agentic_hdbn_codec_0001` (A1#seed1)
```
log: =================================== FAILURES ===================================
log:         CalledProcessError. The CalledProcessError object will have the return code
log:         triggered by setting any of text, encoding, errors or universal_newlines.
log: ============================== 1 failed in 0.09s ===============================
trace: llm edit decision={"changed": ["rtl/hdbn_top.sv"], "errors": 0, "checks": ["compile", "lint", "syn
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/hdbn_
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/hdbn_top.sv; hierarchy -auto-top; proc; o
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/hdbn_top.sv']
```

**compile_fail_hidden**: `cvdp_agentic_phase_rotation_0028` (A1#seed1)
```
log:         CalledProcessError. The CalledProcessError object will have the return code
log:         triggered by setting any of text, encoding, errors or universal_newlines.
log:                 raise ValueError('stdin and input arguments may not both be used.')
log: ======================== 15 failed, 3 warnings in 0.88s ========================
trace: llm edit decision={"changed": ["rtl/detect_sequence.sv"], "errors": 0, "checks": ["compile", "lint
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/adder
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/adder_2d_layers.sv /code/rtl/adder_tree_2
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/detect_sequence.sv']
```

**signal_missing_hidden**: `cvdp_agentic_csr_using_apb_interface_0001` (A1#seed1)
```
log:                                                         AttributeError: csr_apb_interface contains no child object named pclk. Did you mean: 'clk'?
log:      0.00ns WARNING  cocotb.regression                  test_csr_apb_interface.test_csr_apb_interface failed
log:                                                         ** test_csr_apb_interface.test_csr_apb_interface   FAIL           0.00           0.00          0.00  **
log: ======================== 2 failed, 3 warnings in 1.13s =========================
trace: llm edit decision={"changed": ["rtl/csr_apb_interface.sv"], "errors": 0, "checks": ["compile", "li
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/csr_a
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/csr_apb_interface.sv; hierarchy -auto-top
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/csr_apb_interface.sv']
```

**signal_missing_hidden**: `cvdp_agentic_digital_stopwatch_0001` (A1#seed1)
```
log:                                                                raise AttributeError(f"{self._path} contains no child object named {name}")
log:                                                            AttributeError: dig_stopwatch_top contains no child object named hour. Did you mean: 'hours'?
log: 666666666.00ns WARNING  cocotb.regression                  test_dig_stopwatch.test_dig_stopwatch failed
log: ============================== 4 failed in 2.03s ===============================
trace: llm edit decision={"changed": ["rtl/dig_stopwatch.sv"], "errors": 0, "checks": ["compile", "lint",
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/dig_s
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/dig_stopwatch.sv /code/rtl/dig_stopwatch_
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/dig_stopwatch.sv', 'rtl/dig_stopwatch_top.sv']
```

**signal_missing_hidden**: `cvdp_agentic_phase_rotation_0010` (A1#seed1)
```
log:                                                         AttributeError: phase_rotation_viterbi contains no child object named data_i4_ff
log:     30.00ns WARNING  cocotb.regression                  test_phase_rotation_viterbi.test_low_pass_filter failed
log:                                                         ** test_phase_rotation_viterbi.test_low_pass_filter   FAIL          30.00           0.00       7835.91  
log: ======================= 18 failed, 3 warnings in 10.01s ========================
trace: llm plan decision="plan"
trace: file_write exit=0 write rtl/phase_rotation_viterbi.sv
trace: llm edit decision={"changed": ["rtl/phase_rotation_viterbi.sv"], "errors": 0, "checks": ["compile"
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/gen_c
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/phase_rotation_viterbi.sv']
```

**tests_failed_selfcheck_passed**: `cvdp_agentic_axis_broadcaster_0001` (A1#seed1)
```
log:                                                             raise AttributeError(f"{self._path} contains no child object named {name}")
log:                                                         AttributeError: axis_broadcast contains no child object named m_axis_tvalid. Did you mean: 's_axis_tvali
log:     28.00ns WARNING  cocotb.regression                  test_axis_broadcast.test_axis_broadcast failed
log: ======================== 1 failed, 3 warnings in 0.56s =========================
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/axis_broadcast.sv; hierarchy -auto-top; p
trace: testbench_build exit=0 iverilog -g2012 -o /code/rundir/agent_tb/tb.vvp -s tb_axis_broadcast -I/code/rtl
trace: testbench_run exit=0 vvp -n /code/rundir/agent_tb/tb.vvp
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/axis_broadcast.sv']
```

**tests_failed_selfcheck_passed**: `cvdp_agentic_dynamic_equalizer_0008` (A1#seed1)
```
log: =================================== FAILURES ===================================
log:     21.00ns ERROR    root                               FAIL: Data Output mismatch. Expected: -8160, Got: -10261
log:     31.00ns ERROR    root                               FAIL: Data Output mismatch. Expected: 7936, Got: 5492
log: Cleaning up Docker resources...
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/awgn.sv /code/rtl/coeff_update.sv /code/r
trace: testbench_build exit=0 iverilog -g2012 -o /code/rundir/agent_tb/tb.vvp -s tb_awgn -I/code/rtl /code/rtl
trace: testbench_run exit=0 vvp -n /code/rundir/agent_tb/tb.vvp
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/awgn.sv', 'rtl/coeff_update.sv', 'rtl/dynamic_equalizer.sv', 'rtl/equalizer_top.sv']
```

**tests_failed_selfcheck_passed**: `cvdp_agentic_monte_carlo_0006` (A1#seed1)
```
log:                                                             assert total_transfers <= NUM_SAMPLES, " Transfers exceed input attempts — possible sync bug"
log:                                                         AssertionError:  Transfers exceed input attempts — possible sync bug
log:                                                         assert 545 <= 500
log: ======================== 1 failed, 3 warnings in 0.72s =========================
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/cross_domain_sync.sv /code/rtl/dsp_input_
trace: testbench_build exit=0 iverilog -g2012 -o /code/rundir/agent_tb/tb.vvp -s monte_carlo_dsp_monitor_top_t
trace: testbench_run exit=0 vvp -n /code/rundir/agent_tb/tb.vvp
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/cross_domain_sync.sv', 'rtl/dsp_input_stage.sv', 'rtl/dsp_output_stage.sv', 'rtl/lfsr_generator.sv', 'rtl/monte_carlo_dsp_monitor_top.sv']
```

**tests_failed_selfcheck_failed**: `cvdp_agentic_DES_0003` (A1#seed1)
```
log:    175.00ns WARNING  ..b.Test test_des_dec.test_des_dec [ERROR] DUT o_data does not match model o_data: 0x42bc326ee3673c3f != 0xeea4b765cb341b88
log:                                                         assert 4808773953967832127 == 17196070925036166024
log:                                                             assert dut_data == model_data,  f"[ERROR] DUT o_data does not match model o_data: {hex(dut_data)} !=
log: ======================== 1 failed, 3 warnings in 0.68s =========================
trace: llm reflect decision="edit_again"
trace: llm edit decision={"changed": [], "errors": 0, "checks": ["compile", "lint"], "testbench": []}
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/S1.sv
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/des_dec.sv']
```

**tests_failed_selfcheck_failed**: `cvdp_agentic_DES_0003` (A2#seed1)
```
log:      0.00ns WARNING  gpi                                Unable to create perm_p via any registered implementation
log:    175.00ns WARNING  ..b.Test test_des_dec.test_des_dec [ERROR] DUT o_data does not match model o_data: 0xa4b6c43f19915320 != 0xb5f6c53f59d05325
log:                                                         assert 11868889643272459040 == 13111884241016214309
log: ======================== 1 failed, 3 warnings in 0.64s =========================
trace: llm reflect decision="edit_again"
trace: llm edit decision={"changed": [], "errors": 0, "checks": ["compile", "lint"], "testbench": []}
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/S1.sv
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/des_dec.sv']
```

**tests_failed_selfcheck_failed**: `cvdp_agentic_arithmetic_progression_generator_0001` (C1#seed1)
```
log:                                                         assert 1 == 0
log:                                                             assert actual_done == expected_done, "Done signal not asserted after sequence completion"
log:                                                         AssertionError: Done signal not asserted after sequence completion
log: ======================== 5 failed, 3 warnings in 2.27s =========================
trace: llm reflect decision="edit_again"
trace: file_write exit=0 write rtl/arithmetic_progression_generator.sv
trace: llm edit decision={"changed": ["rtl/arithmetic_progression_generator.sv"], "errors": 0, "checks": 
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/arith
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/arithmetic_progression_generator.sv']
```

**tests_failed_no_selfcheck**: `cvdp_agentic_arithmetic_progression_generator_0001` (A1#seed1)
```
log:                                                         assert 1 == 0
log:                                                             assert actual_done == expected_done, "Done signal not asserted after sequence completion"
log:                                                         AssertionError: Done signal not asserted after sequence completion
log: ======================== 5 failed, 3 warnings in 2.58s =========================
trace: llm edit decision={"changed": ["rtl/arithmetic_progression_generator.sv"], "errors": 0, "checks": 
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/arith
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/arithmetic_progression_generator.sv; hier
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/arithmetic_progression_generator.sv']
```

**tests_failed_no_selfcheck**: `cvdp_agentic_binary_search_tree_algorithms_0001` (A1#seed1)
```
log:                                                         assert [63, 63, 63, 63, 63] == [1, 20, 0, 61, 5]
log:                                                             assert ((invalid_key_list == actual_modified_keys)), \
log:                                                         AssertionError: Failed: Key [1, 20, 0, 61, 5] should be modified as [63, 63, 63, 63, 63].
log: =================== 4 failed, 5 passed, 3 warnings in 4.59s ====================
trace: llm edit decision={"changed": ["rtl/search_binary_search_tree.sv"], "errors": 0, "checks": ["compi
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/searc
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/search_binary_search_tree.sv; hierarchy -
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/search_binary_search_tree.sv']
```

**tests_failed_no_selfcheck**: `cvdp_agentic_binary_search_tree_algorithms_0014` (A1#seed1)
```
log:                                                             raise AttributeError(f"{self._path} contains no child object named {name}")
log:                                                         AttributeError: bst_operations contains no child object named search_key. Did you mean: 'search_done'?
log:    205.00ns WARNING  cocotb.regression                  test_bst_operations.test_bst_operations failed
log: ======================== 5 failed, 3 warnings in 2.62s =========================
trace: llm edit decision={"changed": ["rtl/bst_tree_construct.sv", "rtl/binary_search_tree_sort.sv", "rtl
trace: compile exit=0 iverilog -g2012 -o /code/rundir/agent_tb/compile.vvp -I/code/rtl /code/rtl/binar
trace: lint exit=0 verilator --lint-only -Wall -Wno-fatal -Wno-MULTITOP --timing -I/code/rtl /code/
trace: synth exit=0 yosys -q -p read_verilog -sv /code/rtl/binary_search_tree_sort.sv /code/rtl/bina
trace: llm reflect decision="submit"
trace: summary stop=submit files=['rtl/binary_search_tree_sort.sv', 'rtl/binary_search_tree_sort_construct.sv', 'rtl/bst_operations.sv', 'rtl/bst_tree_construct.sv', 'rtl/delete_node_binary_search_tree.sv', 'rtl/search_binary_search_tree.sv']
```

