# Unreachable agentic problems (M3b evaluation set)

Made by `tools/reachable.py` from the dataset's hidden harness files and M3's 14 runs (`docs/reports/m3/runs/*.csv`). A problem is unreachable when a name the hidden testbench reads is given nowhere to the agent **and** M3 labels it `signal_missing_hidden` or `compile_fail_hidden` in at least half of its runs. 6 of 92 are excluded; the evaluation set is the other 86 (`tools/m3b_eval_ids.txt`).

The exclusions rest on identifier-shaped names such as `hour_pulse` and `CLK_FREQ`: 6 of the 6 excluded problems read at least one the agent is not given. Common words such as `clk` and `hour` are also listed as not given when they appear only in prose, which may be too strict for them; no exclusion rests on them alone.

| Problem | cid | Interface failures in M3 | Names the hidden testbench reads that the agent is not given (where read) |
|---|---|---|---|
| `digital_stopwatch_0001` | cid005 | 11/14 | `CLK_FREQ` (dut.CLK_FREQ, parameter); `beep` (dut.beep); `clk` (dut.clk); `hour` (dut.hour); `hour_pulse` (dut.hour_pulse); `minute_pulse` (dut.minute_pulse); `minutes` (dut.minutes); `reset` (dut.reset) and 3 more |
| `phase_rotation_0010` | cid005 | 13/14 | `data_i4_ff` (dut.data_i4_ff); `data_i4_ff_sat` (dut.data_i4_ff_sat); `data_q4_ff` (dut.data_q4_ff); `data_q4_ff_sat` (dut.data_q4_ff_sat); `phase_div4` (dut.phase_div4); `phase_div4_sat` (dut.phase_div4_sat) |
| `phase_rotation_0028` | cid005 | 14/14 | `NBW_TH_PROC` (dut.NBW_TH_PROC, parameter); `NS_PROC_OVERLAP` (parameter); `conj_proc_seq` (dut.conj_proc_seq); `proc_buffer_i_dff` (dut.proc_buffer_i_dff); `proc_buffer_q_dff` (dut.proc_buffer_q_dff); `proc_calc_energy` (dut.proc_calc_energy); `proc_pol_dff` (dut.proc_pol_dff); `uu_cross_correlation` (dut.uu_cross_correlation) |
| `phase_rotation_0031` | cid004 | 11/14 | `curr_state` (dut.curr_state); `ts_count_dff` (dut.ts_count_dff); `ts_undetected_count_dff` (dut.ts_undetected_count_dff); `w_aware_mode` (dut.w_aware_mode) |
| `phase_rotation_0038` | cid003 | 14/14 | `cnt_ff` (dut.cnt_ff); `cnt_rstctrl` (dut.cnt_rstctrl); `state_ff` (dut.state_ff) |
| `poly_decimator_0001` | cid005 | 13/14 | `poly_branches` (dut.poly_branches); `u_poly_filter` (dut.poly_branches.u_poly_filter) |

**Kept although M3's interface labels dominate** (every name the hidden testbench reads is given somewhere, so the failure is the agent's):

| Problem | cid | Interface failures in M3 |
|---|---|---|
| `cache_controller_0001` | cid003 | 13/14 |
| `hdbn_codec_0001` | cid005 | 8/14 |
| `sigma_delta_audio_0001` | cid003 | 14/14 |
| `sync_serial_communication_0001` | cid003 | 13/14 |
| `ttc_lite_0001` | cid003 | 12/14 |
