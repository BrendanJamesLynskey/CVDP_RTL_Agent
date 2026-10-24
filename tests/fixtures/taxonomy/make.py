"""Writes the taxonomy fixture: one harness work dir (work/seed1/) with a problem built for each failure label, two
ambiguous failures for the hand-labelled set, and one pass. The log text follows the shape of the harness's real
per-test logs (pytest session, cocotb lines, compiler errors); the traces use the agent's own event format.

Run from the repo root: python3 tests/fixtures/taxonomy/make.py   (rewrites tests/fixtures/taxonomy/work/)
"""
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SESSION = ("============================= test session starts ==============================\n"
           "platform linux -- Python 3.12.3, pytest-8.3.2, pluggy-1.5.0\nrootdir: /code/rundir\ncollected 1 item\n\n"
           "src/test_runner.py ")
COCOTB = ("     0.00ns INFO     cocotb.gpi                         Running on Icarus Verilog version 13.0\n"
          "     0.00ns INFO     cocotb                             Running tests\n"
          "     0.00ns INFO     cocotb.regression                  running test_{t} (1/1)\n")
LOGS = {
    "tests_failed": SESSION + COCOTB.format(t="main") +
    "  1240.00ns WARNING  cocotb.regression                  test_main failed\n"
    "    assert dut.y.value == 5, f\"DUT={int(dut.y.value)} != Exp=5\"\n"
    "AssertionError: [MAIN C003] DUT=0 != Exp=5\n"
    "  1240.00ns INFO     cocotb.regression                  TESTS=1 PASS=0 FAIL=1 SKIP=0\n"
    "ERROR: Failed 1 of 1 tests.\nFAILED src/test_runner.py::test_runner - SystemExit\n"
    "============================== 1 failed in 4.21s ===============================\n",
    "tests_failed_partial": SESSION + COCOTB.format(t="burst") +
    "AssertionError: burst 3 read back 0x00 != 0xa5\n"
    "  9000.00ns INFO     cocotb.regression                  TESTS=3 PASS=2 FAIL=1 SKIP=0\n"
    "ERROR: Failed 1 of 3 tests.\n"
    "============================== 1 failed in 7.80s ===============================\n",
    "build_failed": SESSION +
    "F\nE   subprocess.CalledProcessError: Command '['iverilog', '-g2012', '-o', 'sim.vvp', '-s', 'axis_to_uart_tx'"
    "]' returned non-zero exit status 1.\n"
    "error: Unable to find the root module \"axis_to_uart_tx\" in the Verilog source.\n"
    "============================== 1 failed in 0.52s ===============================\n",
    "signal_missing": SESSION + COCOTB.format(t="regs") +
    "    assert dut.enable.value == 1, \"[ERROR] Control register enable not set\"\n"
    "    raise AttributeError(f\"{self._path} contains no child object named {name}\")\n"
    "AttributeError: ttc_counter_lite contains no child object named enable\n"
    "    80.00ns INFO     cocotb.regression                  TESTS=1 PASS=0 FAIL=1 SKIP=0\n"
    "FAILED src/test_runner.py::test_areg_param[0] - SystemExit: 1\n"
    "============================== 1 failed in 1.26s ===============================\n",
    # the check fails, then its f-string message reads a handle the design lacks: still tests_failed
    "signal_in_message": SESSION + COCOTB.format(t="bcast") +
    "    assert dut.m_axis_tvalid_1.value == 1, f\"[ERROR] m_axis_tvalid value is : {dut.m_axis_tvalid.value}\"\n"
    "    raise AttributeError(f\"{self._path} contains no child object named {name}\")\n"
    "AttributeError: axis_broadcast contains no child object named m_axis_tvalid. Did you mean: 's_axis_tvalid'?\n"
    "    28.00ns INFO     cocotb.regression                  TESTS=1 PASS=0 FAIL=1 SKIP=0\n"
    "FAILED src/test_runner.py::test_axis_broadcast[0] - SystemExit: 1\n"
    "============================== 1 failed in 0.56s ===============================\n",
    "sim_incomplete": SESSION + COCOTB.format(t="fifo_full") +
    "   200.00ns INFO     cocotb.fifo                        writing 64 words\n"
    "   850.00ns INFO     cocotb.fifo                        waiting for full flag\n",
    "harness_error": "docker: Error response from daemon: failed to create task for container: unable to start "
    "container process: exec: \"/bin/sh\": no such file.\n",
    "passed": SESSION + COCOTB.format(t="main") +
    "  1240.00ns INFO     cocotb.regression                  TESTS=1 PASS=1 FAIL=0 SKIP=0\n"
    "============================== 1 passed in 3.10s ===============================\n",
}


def compile_ev(rc):
    return {"kind": "tool", "check": "compile", "command": "iverilog -g2012 -o rundir/agent_tb/compile.vvp rtl/dut.sv",
            "exit_code": rc, "output": "" if rc == 0 else "rtl/dut.sv:12: syntax error"}


def tb_ev(ok):
    return {"kind": "tool", "check": "testbench_run", "command": "vvp -n tb.vvp", "exit_code": 0,
            "output": "AGENT_TB_PASS all 16 vectors" if ok else "ERROR: mismatch at vector 3: got 0 want 5"}


def llm_ev(node, decision, **kw):
    return {"kind": "llm", "node": node, "model": "openai/gpt-6-luna", "decision": decision, "cost": 0.001, **kw}


EDIT = llm_ev("edit", {"changed": ["rtl/dut.sv"], "errors": 0, "checks": ["compile", "testbench"]})
# name: (stop_reason or None for no summary, files_changed, final_compiled, trace events, log key, hand label)
CASES = {
    "llm_error": ("llm_error", [], None, [llm_ev("plan", "plan"),
                                          {"kind": "llm", "node": "edit", "cost": None, "deadline_missed": True,
                                           "error": "CallDeadline: no reply within 440.0 s; call abandoned"}],
                  "tests_failed", "llm_error"),
    "agent_error": ("error", ["rtl/dut.sv"], True, [EDIT, compile_ev(0)], "tests_failed", "agent_error"),
    "killed": (None, None, None, [llm_ev("plan", "plan"), EDIT, compile_ev(0)], "tests_failed", "killed"),
    "no_edit": ("submit", [], None, [llm_ev("plan", "plan"), llm_ev("edit", {"changed": [], "errors": 1}),
                                     compile_ev(0), llm_ev("reflect", "submit")], "tests_failed", "no_edit"),
    "stopped_by_cap": ("max_turns", ["rtl/dut.sv"], True, [EDIT, compile_ev(0), tb_ev(False)] * 3, "tests_failed",
                       "stopped_by_cap"),
    "gave_up": ("give_up", ["rtl/dut.sv"], False, [EDIT, compile_ev(1), llm_ev("reflect", "give_up")],
                "build_failed", "gave_up"),
    "sim_incomplete": ("submit", ["rtl/dut.sv"], True, [EDIT, compile_ev(0), tb_ev(True)], "sim_incomplete",
                       "sim_incomplete"),
    "compile_fail_own": ("submit", ["rtl/dut.sv"], False, [EDIT, compile_ev(1), llm_ev("reflect", "submit")],
                         "build_failed", "compile_fail_own"),
    "compile_fail_hidden": ("submit", ["rtl/dut.sv"], True, [EDIT, compile_ev(0), tb_ev(True)], "build_failed",
                            "compile_fail_hidden"),
    "signal_missing_hidden": ("submit", ["rtl/dut.sv"], True, [EDIT, compile_ev(0), tb_ev(True)],
                              "signal_missing", ""),
    "signal_in_message": ("submit", ["rtl/dut.sv"], True, [EDIT, compile_ev(0)], "signal_in_message", ""),
    "tests_failed_selfcheck_passed": ("submit", ["rtl/dut.sv"], True, [EDIT, compile_ev(0), tb_ev(True)],
                                      "tests_failed", "tests_failed_selfcheck_passed"),
    "tests_failed_selfcheck_failed": ("submit", ["rtl/dut.sv"], True, [EDIT, compile_ev(0), tb_ev(False)],
                                      "tests_failed", "tests_failed_selfcheck_failed"),
    "tests_failed_no_selfcheck": ("submit", ["rtl/dut.sv"], True, [EDIT, compile_ev(0)], "tests_failed",
                                  "tests_failed_no_selfcheck"),
    "harness_error": ("submit", ["rtl/dut.sv"], True, [EDIT, compile_ev(0), tb_ev(True)], "harness_error",
                      "harness_error"),
    # ambiguous: stopped on the wall cap, but the hidden build failed on a missing module the agent's own
    # compile never saw: by hand the failure is the interface mismatch, and the cap is incidental
    "ambiguous_cap_mismatch": ("wall_time", ["rtl/dut.sv"], True, [EDIT, compile_ev(0)], "build_failed",
                               "compile_fail_hidden"),
    # partial: 2 of 3 hidden tests passed; the agent's testbench passed
    "partial_selfcheck_passed": ("submit", ["rtl/dut.sv"], True, [EDIT, compile_ev(0), tb_ev(True)],
                                 "tests_failed_partial", "tests_failed_selfcheck_passed"),
    "passes": ("submit", ["rtl/dut.sv"], True, [EDIT, compile_ev(0), tb_ev(True)], "passed", ""),
    # review round 1. A harness kill: raw_result.json has "log": null and an error_msg, but the problem's own log
    # is still in reports/<n>.txt and ends mid-cocotb -> sim_incomplete
    "harness_killed_log": ("submit", ["rtl/dut.sv"], True, [EDIT, compile_ev(0)], "sim_incomplete", "",
                           {"log_null": True}),
    # the same with no log file at all -> harness_error, from the error_msg
    "harness_killed_nolog": ("submit", ["rtl/dut.sv"], True, [EDIT, compile_ev(0)], None, "",
                             {"log_null": True}),
    # finalize restored the edit of turn 1, which compiled; final_compiled is the discarded edit's (False); the
    # hidden build failed -> compile_fail_hidden, not compile_fail_own
    "restored_best": ("max_turns_restored", ["rtl/dut.sv"], False, [EDIT, compile_ev(0), EDIT, compile_ev(1)],
                      "build_failed", "", {"kept": "best_compiled_turn_1"}),
    # a failed problem the harness recorded no tests for -> harness_error
    "no_tests": ("submit", ["rtl/dut.sv"], True, [EDIT, compile_ev(0)], None, "", {"no_tests": True}),
}


def pid(name):
    return f"cvdp_agentic_tax_{name}_0001"


def main(out=os.path.join(HERE, "work")):
    shutil.rmtree(out, ignore_errors=True)
    seed = os.path.join(out, "seed1")
    raw = {}
    hand = []
    for name, (stop, files, compiled, events, log, hand_label, *extra) in CASES.items():
        extra = extra[0] if extra else {}
        stop = "submit" if stop == "max_turns_restored" else stop
        repo = pid(name)[:-5]
        agent_out = os.path.join(seed, repo, "harness", "1", "rundir", "agent_out")
        os.makedirs(agent_out)
        os.makedirs(os.path.join(seed, repo, "reports"))
        if log is not None:
            with open(os.path.join(seed, repo, "reports", "1.txt"), "w") as f:
                f.write(LOGS[log])
        with open(os.path.join(agent_out, "trace.jsonl"), "w") as f:
            for e in events:
                f.write(json.dumps(e) + "\n")
        if stop is not None:
            turns = 3 if stop == "max_turns" else 1
            summary = {"provider": "openrouter", "model": "openai/gpt-6-luna", "requested_model": "openai/gpt-6-luna",
                       "turns": turns, "llm_calls": len([e for e in events if e["kind"] == "llm"]),
                       "cost_usd": 0.004, "cost_unreported_calls": 1 if stop == "llm_error" else 0,
                       "stop_reason": stop, "kept": extra.get("kept", "last"), "final_compiled": compiled,
                       "files_changed": files,
                       "wall_time_s": 480.5 if stop == "wall_time" else 60.0,
                       "switches": {"self_check": True, "lint": True, "max_turns": 3 if stop == "max_turns" else 10,
                                    "budget_usd": 0.1, "reasoning": "default"}}
            with open(os.path.join(agent_out, "summary.json"), "w") as f:
                json.dump(summary, f, indent=1)
        n_tests = 3 if log == "tests_failed_partial" else 1
        results = [0, 0, 1] if n_tests == 3 else [0 if log == "passed" else 1]
        tests = [{"result": r, "log": f"/x/{repo}/reports/1.txt", "execution": 1.0} for r in results]
        if extra.get("log_null"):
            tests = [{"result": 1, "log": None, "error_msg": "Failed to execute objective harness",
                      "execution": 600.0}]
        raw[pid(name)] = {"category": "cid003", "difficulty": "medium",
                          "agent_status": "timeout" if stop is None else "completed",
                          "tests": [] if extra.get("no_tests") else tests}
        if hand_label:
            hand.append((pid(name), "fixture#seed1", hand_label))
    with open(os.path.join(seed, "raw_result.json"), "w") as f:
        json.dump(raw, f, indent=1)
    with open(os.path.join(HERE, "hand_labels.csv"), "w") as f:
        f.write("id,run,label\n" + "".join(f"{i},{r},{lb}\n" for i, r, lb in hand))


if __name__ == "__main__":
    main()
