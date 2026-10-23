"""collect.py and table.py on a small fixture work dir, laid out like a real harness run (raw_result.json copied
in shape from a local null-agent run at the pinned harness commit)."""
import csv
import io
import os

import pytest

import collect
import table

WORK = os.path.join(os.path.dirname(__file__), "fixtures", "work")


def test_collect_rows():
    rows = {r["id"]: r for r in collect.rows(WORK)}
    assert len(rows) == 5
    lfsr = rows["cvdp_agentic_lfsr_0001"]
    assert (lfsr["pass"], lfsr["cid"], lfsr["cost_usd"], lfsr["stop_reason"], lfsr["turns"]) == (1, "cid016", 0.012,
                                                                                               "submit", 3)
    assert rows["cvdp_agentic_barrel_shifter_0002"]["pass"] == 0
    assert rows["cvdp_agentic_axis_to_uart_0001"]["pass"] == 1           # both tests pass
    assert rows["cvdp_agentic_axis_to_uart_0001"]["cost_usd"] == ""      # unreported stays empty, never estimated
    assert rows["cvdp_agentic_axis_to_uart_0001"]["amba"] == 1
    assert rows["cvdp_agentic_ttc_lite_0001"]["pass"] == 0               # one of two tests fails
    assert rows["cvdp_agentic_ttc_lite_0001"]["amba"] == 0               # dropped from the AMBA slice by hand
    des = rows["cvdp_agentic_DES_0003"]
    assert (des["summary_found"], des["stop_reason"], des["requested_model"]) == (0, "no_summary", "unknown")
    assert lfsr["self_check"] == 1 and lfsr["lint"] == 0


def test_wilson():
    lo, hi = table.wilson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(0.2775, abs=1e-3)
    lo, hi = table.wilson(5, 10)
    assert (lo, hi) == (pytest.approx(0.2366, abs=1e-3), pytest.approx(0.7634, abs=1e-3))
    assert table.wilson(0, 0) == (0.0, 0.0)


def test_collect_keeps_rows_without_summary_in_the_requested_model():
    rows = {r["id"]: r for r in collect.rows(WORK, model="m/a")}
    assert rows["cvdp_agentic_DES_0003"]["requested_model"] == "m/a"
    assert rows["cvdp_agentic_DES_0003"]["model"] == ""  # nothing served: no summary
    md = table.table(_csv_rows(model="m/a"))
    assert "#### unknown" not in md and "| **All** | 2/5 = 40.0%" in md


def _csv_rows(model=""):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=collect.FIELDS)
    w.writeheader()
    for r in collect.rows(WORK, model=model):
        w.writerow(r)
    return list(csv.DictReader(io.StringIO(buf.getvalue())))


def test_table_numbers():
    rows = [r for r in _csv_rows() if r["requested_model"] == "m/a"]
    s = table.stats(rows)
    assert (s["n"], s["k"]) == (4, 2)
    assert s["cost"] == pytest.approx(0.062) and s["unreported"] == 1
    assert s["per_problem"] == pytest.approx(0.062 / 4)
    assert s["per_solved"] == pytest.approx(0.031)
    assert s["wall"] == 40.0


def test_table_markdown():
    md = table.table(_csv_rows())
    assert "#### m/a" in md and "#### unknown" in md
    assert "| AMBA slice | 1/1" in md
    # one row's cost is unreported, so every money column for the slice is a lower bound
    assert "| **All** | 2/4 = 50.0% [15.0, 85.0] | ≥$0.0620 (1 unreported) | ≥$0.0155 | ≥$0.0310 | 40 s |" in md
    assert "Stop reasons: budget 1, give_up 1, max_turns 1, submit 1" in md


def test_log_check_classifies():
    import log_check

    ran = "============================= test session starts ==============================\n"
    assert log_check.classify("") == "harness_error"
    assert log_check.classify("fatal: bundle not found\n") == "harness_error"
    assert log_check.classify(ran + "AssertionError: bad\nERROR: Failed 2 of 2 tests.\nFAILED\n") == "tests_failed"
    assert log_check.classify(ran + "subprocess.CalledProcessError: iverilog\n1 failed in 0.5s\n") == "build_failed"
    assert log_check.classify(ran + "============================== 1 passed in 4.50s ======\n") == "passed"


def test_partly_unreported_row_makes_money_a_lower_bound():
    base = {"requested_model": "m", "model": "m", "cid": "cid003", "amba": "0", "pass": "1", "wall_time_s": "10",
            "harness_agent_s": "", "prompt_tokens": "1", "completion_tokens": "1", "stop_reason": "submit"}
    rows = [dict(base, id="a", cost_usd="0.02", cost_unreported_calls="0"),
            dict(base, id="b", cost_usd="0.02", cost_unreported_calls="1")]  # reported $0.02 plus a call with none
    md = table.table(rows)
    assert "| **All** | 2/2 = 100.0% [34.2, 100.0] | ≥$0.0400 (1 unreported) | ≥$0.0200 | ≥$0.0200 |" in md
    rows[1]["cost_unreported_calls"] = "0"
    assert "| $0.0400 | $0.0200 | $0.0200 |" in table.table(rows)


def test_killed_problem_stays_in_the_requested_models_denominator(tmp_path):
    """The Arm64 re-run case: one of two problems was killed by the harness and left no summary.json. With the
    requested model passed in, the table reads 1/2 for that model, not 1/1 plus a separate "unknown" table."""
    import json as _json

    work = tmp_path / "work"
    raw = {}
    for pid, res in (("cvdp_agentic_lfsr_0001", 0), ("cvdp_agentic_ttc_lite_0001", 1)):
        repo, n = pid.rsplit("_", 1)
        (work / repo / "reports").mkdir(parents=True)
        raw[pid] = {"category": "cid016", "difficulty": "easy", "agent_status": "timeout",
                    "tests": [{"result": res, "log": f"/x/{repo}/reports/{int(n)}.txt", "execution": 1.0}]}
    out = work / "cvdp_agentic_lfsr" / "harness" / "1" / "rundir" / "agent_out"
    out.mkdir(parents=True)
    (out / "summary.json").write_text(_json.dumps({"model": "deepseek/x", "requested_model": "deepseek/x",
                                                   "cost_usd": 0.01, "cost_unreported_calls": 0,
                                                   "stop_reason": "submit", "wall_time_s": 20}))
    (work / "raw_result.json").write_text(_json.dumps(raw))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=collect.FIELDS)
    w.writeheader()
    for r in collect.rows(str(work), model="deepseek/x"):
        w.writerow(r)
    md = table.table(list(csv.DictReader(io.StringIO(buf.getvalue()))))
    assert "#### unknown" not in md
    assert "| **All** | 1/2 = 50.0%" in md
    assert "≥$0.0100 (1 unreported)" in md  # the killed problem's cost is not known, so the money is a lower bound
