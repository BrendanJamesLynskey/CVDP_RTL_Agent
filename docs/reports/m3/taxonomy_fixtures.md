15 failed (problem, run) rows of 16.

#### Primary label by arm

| Label | fixture | All |
|---|---|---|
| llm_error | 1 | 1 |
| agent_error | 1 | 1 |
| killed | 1 | 1 |
| no_edit | 1 | 1 |
| stopped_by_cap | 2 | 2 |
| gave_up | 1 | 1 |
| sim_incomplete | 1 | 1 |
| compile_fail_own | 1 | 1 |
| compile_fail_hidden | 1 | 1 |
| tests_failed_selfcheck_passed | 2 | 2 |
| tests_failed_selfcheck_failed | 1 | 1 |
| tests_failed_no_selfcheck | 1 | 1 |
| harness_error | 1 | 1 |
| **All failures** | 15 | 15 |

#### Primary label by cid

| Label | cid003 | All |
|---|---|---|
| llm_error | 1 | 1 |
| agent_error | 1 | 1 |
| killed | 1 | 1 |
| no_edit | 1 | 1 |
| stopped_by_cap | 2 | 2 |
| gave_up | 1 | 1 |
| sim_incomplete | 1 | 1 |
| compile_fail_own | 1 | 1 |
| compile_fail_hidden | 1 | 1 |
| tests_failed_selfcheck_passed | 2 | 2 |
| tests_failed_selfcheck_failed | 1 | 1 |
| tests_failed_no_selfcheck | 1 | 1 |
| harness_error | 1 | 1 |
| **All failures** | 15 | 15 |

Secondary flags: single_turn 13, tests_failed_no_selfcheck 4, compile_fail_hidden 1, compile_fail_own 1, no_edit 1, partial_pass 1, tests_failed_selfcheck_failed 1

#### Evidence, up to 3 per label

**llm_error**: `cvdp_agentic_tax_llm_error_0001` (fixture#seed1)
```
log:   1240.00ns WARNING  cocotb.regression                  test_main failed
log:     assert dut.y.value == 5, f"DUT={int(dut.y.value)} != Exp=5"
log: AssertionError: [MAIN C003] DUT=0 != Exp=5
log:   1240.00ns INFO     cocotb.regression                  TESTS=1 PASS=0 FAIL=1 SKIP=0
log: FAILED src/test_runner.py::test_runner - SystemExit
trace: llm plan decision="plan"
trace: llm edit decision=null error=CallDeadline: no reply within 440.0 s; call abandoned
```

**agent_error**: `cvdp_agentic_tax_agent_error_0001` (fixture#seed1)
```
log:   1240.00ns WARNING  cocotb.regression                  test_main failed
log:     assert dut.y.value == 5, f"DUT={int(dut.y.value)} != Exp=5"
log: AssertionError: [MAIN C003] DUT=0 != Exp=5
log:   1240.00ns INFO     cocotb.regression                  TESTS=1 PASS=0 FAIL=1 SKIP=0
log: FAILED src/test_runner.py::test_runner - SystemExit
trace: llm edit decision={"changed": ["rtl/dut.sv"], "errors": 0, "checks": ["compile", "testbench"]}
trace: compile exit=0 iverilog -g2012 -o rundir/agent_tb/compile.vvp rtl/dut.sv
```

**killed**: `cvdp_agentic_tax_killed_0001` (fixture#seed1)
```
log:   1240.00ns WARNING  cocotb.regression                  test_main failed
log:     assert dut.y.value == 5, f"DUT={int(dut.y.value)} != Exp=5"
log: AssertionError: [MAIN C003] DUT=0 != Exp=5
log:   1240.00ns INFO     cocotb.regression                  TESTS=1 PASS=0 FAIL=1 SKIP=0
log: FAILED src/test_runner.py::test_runner - SystemExit
trace: llm plan decision="plan"
trace: llm edit decision={"changed": ["rtl/dut.sv"], "errors": 0, "checks": ["compile", "testbench"]}
trace: compile exit=0 iverilog -g2012 -o rundir/agent_tb/compile.vvp rtl/dut.sv
```

**no_edit**: `cvdp_agentic_tax_no_edit_0001` (fixture#seed1)
```
log:   1240.00ns WARNING  cocotb.regression                  test_main failed
log:     assert dut.y.value == 5, f"DUT={int(dut.y.value)} != Exp=5"
log: AssertionError: [MAIN C003] DUT=0 != Exp=5
log:   1240.00ns INFO     cocotb.regression                  TESTS=1 PASS=0 FAIL=1 SKIP=0
log: FAILED src/test_runner.py::test_runner - SystemExit
trace: llm plan decision="plan"
trace: llm edit decision={"changed": [], "errors": 1}
trace: compile exit=0 iverilog -g2012 -o rundir/agent_tb/compile.vvp rtl/dut.sv
trace: llm reflect decision="submit"
```

**stopped_by_cap**: `cvdp_agentic_tax_ambiguous_cap_mismatch_0001` (fixture#seed1)
```
log: E   subprocess.CalledProcessError: Command '['iverilog', '-g2012', '-o', 'sim.vvp', '-s', 'axis_to_uart_tx']' returned non-zero exit status 1.
log: error: Unable to find the root module "axis_to_uart_tx" in the Verilog source.
log: ============================== 1 failed in 0.52s ===============================
trace: llm edit decision={"changed": ["rtl/dut.sv"], "errors": 0, "checks": ["compile", "testbench"]}
trace: compile exit=0 iverilog -g2012 -o rundir/agent_tb/compile.vvp rtl/dut.sv
```

**stopped_by_cap**: `cvdp_agentic_tax_stopped_by_cap_0001` (fixture#seed1)
```
log:     assert dut.y.value == 5, f"DUT={int(dut.y.value)} != Exp=5"
log: AssertionError: [MAIN C003] DUT=0 != Exp=5
log:   1240.00ns INFO     cocotb.regression                  TESTS=1 PASS=0 FAIL=1 SKIP=0
log: FAILED src/test_runner.py::test_runner - SystemExit
trace: llm edit decision={"changed": ["rtl/dut.sv"], "errors": 0, "checks": ["compile", "testbench"]}
trace: compile exit=0 iverilog -g2012 -o rundir/agent_tb/compile.vvp rtl/dut.sv
trace: testbench_run exit=0 vvp -n tb.vvp
trace: llm edit decision={"changed": ["rtl/dut.sv"], "errors": 0, "checks": ["compile", "testbench"]}
trace: compile exit=0 iverilog -g2012 -o rundir/agent_tb/compile.vvp rtl/dut.sv
trace: testbench_run exit=0 vvp -n tb.vvp
```

**gave_up**: `cvdp_agentic_tax_gave_up_0001` (fixture#seed1)
```
log: E   subprocess.CalledProcessError: Command '['iverilog', '-g2012', '-o', 'sim.vvp', '-s', 'axis_to_uart_tx']' returned non-zero exit status 1.
log: error: Unable to find the root module "axis_to_uart_tx" in the Verilog source.
log: ============================== 1 failed in 0.52s ===============================
trace: llm edit decision={"changed": ["rtl/dut.sv"], "errors": 0, "checks": ["compile", "testbench"]}
trace: compile exit=1 iverilog -g2012 -o rundir/agent_tb/compile.vvp rtl/dut.sv
trace: llm reflect decision="give_up"
```

**sim_incomplete**: `cvdp_agentic_tax_sim_incomplete_0001` (fixture#seed1)
```
log:    200.00ns INFO     cocotb.fifo                        writing 64 words
log:    850.00ns INFO     cocotb.fifo                        waiting for full flag
trace: llm edit decision={"changed": ["rtl/dut.sv"], "errors": 0, "checks": ["compile", "testbench"]}
trace: compile exit=0 iverilog -g2012 -o rundir/agent_tb/compile.vvp rtl/dut.sv
trace: testbench_run exit=0 vvp -n tb.vvp
```

**compile_fail_own**: `cvdp_agentic_tax_compile_fail_own_0001` (fixture#seed1)
```
log: E   subprocess.CalledProcessError: Command '['iverilog', '-g2012', '-o', 'sim.vvp', '-s', 'axis_to_uart_tx']' returned non-zero exit status 1.
log: error: Unable to find the root module "axis_to_uart_tx" in the Verilog source.
log: ============================== 1 failed in 0.52s ===============================
trace: llm edit decision={"changed": ["rtl/dut.sv"], "errors": 0, "checks": ["compile", "testbench"]}
trace: compile exit=1 iverilog -g2012 -o rundir/agent_tb/compile.vvp rtl/dut.sv
trace: llm reflect decision="submit"
```

**compile_fail_hidden**: `cvdp_agentic_tax_compile_fail_hidden_0001` (fixture#seed1)
```
log: E   subprocess.CalledProcessError: Command '['iverilog', '-g2012', '-o', 'sim.vvp', '-s', 'axis_to_uart_tx']' returned non-zero exit status 1.
log: error: Unable to find the root module "axis_to_uart_tx" in the Verilog source.
log: ============================== 1 failed in 0.52s ===============================
trace: llm edit decision={"changed": ["rtl/dut.sv"], "errors": 0, "checks": ["compile", "testbench"]}
trace: compile exit=0 iverilog -g2012 -o rundir/agent_tb/compile.vvp rtl/dut.sv
trace: testbench_run exit=0 vvp -n tb.vvp
```

**tests_failed_selfcheck_passed**: `cvdp_agentic_tax_partial_selfcheck_passed_0001` (fixture#seed1)
```
log: AssertionError: burst 3 read back 0x00 != 0xa5
log:   9000.00ns INFO     cocotb.regression                  TESTS=3 PASS=2 FAIL=1 SKIP=0
log: ERROR: Failed 1 of 3 tests.
log: ============================== 1 failed in 7.80s ===============================
trace: llm edit decision={"changed": ["rtl/dut.sv"], "errors": 0, "checks": ["compile", "testbench"]}
trace: compile exit=0 iverilog -g2012 -o rundir/agent_tb/compile.vvp rtl/dut.sv
trace: testbench_run exit=0 vvp -n tb.vvp
```

**tests_failed_selfcheck_passed**: `cvdp_agentic_tax_tests_failed_selfcheck_passed_0001` (fixture#seed1)
```
log:   1240.00ns WARNING  cocotb.regression                  test_main failed
log:     assert dut.y.value == 5, f"DUT={int(dut.y.value)} != Exp=5"
log: AssertionError: [MAIN C003] DUT=0 != Exp=5
log:   1240.00ns INFO     cocotb.regression                  TESTS=1 PASS=0 FAIL=1 SKIP=0
log: FAILED src/test_runner.py::test_runner - SystemExit
trace: llm edit decision={"changed": ["rtl/dut.sv"], "errors": 0, "checks": ["compile", "testbench"]}
trace: compile exit=0 iverilog -g2012 -o rundir/agent_tb/compile.vvp rtl/dut.sv
trace: testbench_run exit=0 vvp -n tb.vvp
```

**tests_failed_selfcheck_failed**: `cvdp_agentic_tax_tests_failed_selfcheck_failed_0001` (fixture#seed1)
```
log:   1240.00ns WARNING  cocotb.regression                  test_main failed
log:     assert dut.y.value == 5, f"DUT={int(dut.y.value)} != Exp=5"
log: AssertionError: [MAIN C003] DUT=0 != Exp=5
log:   1240.00ns INFO     cocotb.regression                  TESTS=1 PASS=0 FAIL=1 SKIP=0
log: FAILED src/test_runner.py::test_runner - SystemExit
trace: llm edit decision={"changed": ["rtl/dut.sv"], "errors": 0, "checks": ["compile", "testbench"]}
trace: compile exit=0 iverilog -g2012 -o rundir/agent_tb/compile.vvp rtl/dut.sv
trace: testbench_run exit=0 vvp -n tb.vvp
```

**tests_failed_no_selfcheck**: `cvdp_agentic_tax_tests_failed_no_selfcheck_0001` (fixture#seed1)
```
log:   1240.00ns WARNING  cocotb.regression                  test_main failed
log:     assert dut.y.value == 5, f"DUT={int(dut.y.value)} != Exp=5"
log: AssertionError: [MAIN C003] DUT=0 != Exp=5
log:   1240.00ns INFO     cocotb.regression                  TESTS=1 PASS=0 FAIL=1 SKIP=0
log: FAILED src/test_runner.py::test_runner - SystemExit
trace: llm edit decision={"changed": ["rtl/dut.sv"], "errors": 0, "checks": ["compile", "testbench"]}
trace: compile exit=0 iverilog -g2012 -o rundir/agent_tb/compile.vvp rtl/dut.sv
```

**harness_error**: `cvdp_agentic_tax_harness_error_0001` (fixture#seed1)
```
log: docker: Error response from daemon: failed to create task for container: unable to start container process: exec: "/bin/sh": no such file.
trace: llm edit decision={"changed": ["rtl/dut.sv"], "errors": 0, "checks": ["compile", "testbench"]}
trace: compile exit=0 iverilog -g2012 -o rundir/agent_tb/compile.vvp rtl/dut.sv
trace: testbench_run exit=0 vvp -n tb.vvp
```

#### Hand labels against the rules: 14/15 agree (93%)

| Problem | Run | Hand | Rules |
|---|---|---|---|
| `cvdp_agentic_tax_agent_error_0001` | fixture#seed1 | agent_error | agent_error |
| `cvdp_agentic_tax_ambiguous_cap_mismatch_0001` | fixture#seed1 | compile_fail_hidden | stopped_by_cap ✗ |
| `cvdp_agentic_tax_compile_fail_hidden_0001` | fixture#seed1 | compile_fail_hidden | compile_fail_hidden |
| `cvdp_agentic_tax_compile_fail_own_0001` | fixture#seed1 | compile_fail_own | compile_fail_own |
| `cvdp_agentic_tax_gave_up_0001` | fixture#seed1 | gave_up | gave_up |
| `cvdp_agentic_tax_harness_error_0001` | fixture#seed1 | harness_error | harness_error |
| `cvdp_agentic_tax_killed_0001` | fixture#seed1 | killed | killed |
| `cvdp_agentic_tax_llm_error_0001` | fixture#seed1 | llm_error | llm_error |
| `cvdp_agentic_tax_no_edit_0001` | fixture#seed1 | no_edit | no_edit |
| `cvdp_agentic_tax_partial_selfcheck_passed_0001` | fixture#seed1 | tests_failed_selfcheck_passed | tests_failed_selfcheck_passed |
| `cvdp_agentic_tax_sim_incomplete_0001` | fixture#seed1 | sim_incomplete | sim_incomplete |
| `cvdp_agentic_tax_stopped_by_cap_0001` | fixture#seed1 | stopped_by_cap | stopped_by_cap |
| `cvdp_agentic_tax_tests_failed_no_selfcheck_0001` | fixture#seed1 | tests_failed_no_selfcheck | tests_failed_no_selfcheck |
| `cvdp_agentic_tax_tests_failed_selfcheck_failed_0001` | fixture#seed1 | tests_failed_selfcheck_failed | tests_failed_selfcheck_failed |
| `cvdp_agentic_tax_tests_failed_selfcheck_passed_0001` | fixture#seed1 | tests_failed_selfcheck_passed | tests_failed_selfcheck_passed |

