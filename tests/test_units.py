"""File tool, diff application, parsing, output summaries and trace redaction."""
import json
import os
import shutil

import pytest

from cvdp_agent import checks
from cvdp_agent.files import DiffError, FileTool, PathRefused, apply_unified_diff
from cvdp_agent.parse import extract_json, parse_decision, parse_edit, parse_plan
from cvdp_agent.trace import REDACTED, Tracer, redact

FAKE_KEY = "sk-or-v1-0123456789abcdef0123456789abcdef"


def test_filetool_allows_only_edit_roots(task_tree):
    ft = FileTool(str(task_tree))
    assert ft.write("rtl/new.sv", "x") == "rtl/new.sv"
    assert ft.write("/code/verif/t.sv", "x") == "verif/t.sv"
    assert ft.write("docs/sub/n.md", "x") == "docs/sub/n.md"
    for p in ["prompt.json", "rundir/a", "/tmp/x", "rtl/../prompt.json", "", "rtl", "rtl//x.sv", "..\\x"]:
        with pytest.raises(PathRefused):
            ft.write(p, "x")


def test_filetool_refuses_symlink_escape(task_tree, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    os.symlink(outside, task_tree / "rtl" / "link")
    with pytest.raises(PathRefused):
        FileTool(str(task_tree)).write("rtl/link/x.sv", "x")
    assert not (outside / "x.sv").exists()


def test_filetool_tb_root(task_tree):
    ft = FileTool(str(task_tree))
    assert ft.write_tb("agent_tb/tb.sv", "x") == "rundir/agent_tb/tb.sv"
    assert ft.write_tb("rundir/agent_tb/t.py", "x") == "rundir/agent_tb/t.py"
    for p in ["rtl/tb.sv", "rundir/tb.sv", "agent_tb/../../rtl/x.sv", "rundir/agent_out/summary.json"]:
        with pytest.raises(PathRefused):
            ft.write_tb(p, "x")


def test_snapshot_restore(task_tree):
    ft = FileTool(str(task_tree))
    snap = ft.snapshot()
    ft.write("rtl/adder.sv", "changed")
    ft.write("rtl/new.sv", "new")
    ft.restore(snap)
    assert "changed" not in (task_tree / "rtl" / "adder.sv").read_text()
    assert not (task_tree / "rtl" / "new.sv").exists()


def test_apply_diff():
    old = "a\nb\nc\nd\n"
    diff = "--- a/f\n+++ b/f\n@@ -99,3 +99,3 @@\n b\n-c\n+C\n d\n"
    assert apply_unified_diff(old, diff) == "a\nb\nC\nd\n"
    with pytest.raises(DiffError):
        apply_unified_diff(old, "@@ -1 +1 @@\n-zzz\n+y\n")
    with pytest.raises(DiffError):
        apply_unified_diff(old, "no hunks here")


def test_apply_diff_whitespace_tolerant():
    old = "module m;\n    assign a = b;\nendmodule\n"
    assert "assign a = c;" in apply_unified_diff(old, "@@\n module m;\n-  assign a = b;\n+  assign a = c;\n")


def test_parse_edit():
    text = ('Here you go.\n<file path="rtl/a.sv">\n```verilog\nmodule a; endmodule\n```\n</file>\n'
            '<diff path="rtl/b.sv">\n@@\n-x\n+y\n</diff>\n<tb path="agent_tb/t.sv" top="t">\nmodule t; endmodule\n'
            '</tb>\n<checks>compile, Lint ,testbench</checks>')
    e = parse_edit(text)
    assert e["files"] == [{"path": "rtl/a.sv", "content": "module a; endmodule\n"}]
    assert e["diffs"][0]["path"] == "rtl/b.sv"
    assert e["tb"][0]["top"] == "t"
    assert e["checks"] == ["compile", "lint", "testbench"]


def test_parse_plan_and_decision():
    assert extract_json('blah {"a": {"b": 1}} trailing') == {"a": {"b": 1}}
    assert extract_json('```json\n{"x": 2}\n```') == {"x": 2}
    assert extract_json("{not json} then {\"ok\": true}") == {"ok": True}
    p = parse_plan('{"files_to_change": "rtl/a.sv", "approach": "do it"}')
    assert p["files_to_change"] == ["rtl/a.sv"]
    assert parse_decision('{"decision": "EDIT_AGAIN"}')["decision"] == "edit_again"
    assert parse_decision("I will give_up now")["decision"] == "give_up"
    assert parse_decision("garbage")["decision"] == "submit"


def test_summarise_truncates():
    out = "\n".join(f"line {i}" for i in range(5000)) + "\n%Error: x.sv:3: syntax error\n"
    s = checks.summarise(out, limit=500)
    assert len(s) < 700 and "syntax error" in s


def test_redact_patterns(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "plain-secret-without-prefix-1234")
    text = (f"key={FAKE_KEY} Authorization: Bearer abc.def headers={{'authorization': 'x'}} "
            "and plain-secret-without-prefix-1234")
    r = redact({"out": text, "list": [FAKE_KEY]})
    blob = json.dumps(r)
    for bad in (FAKE_KEY, "sk-or-", "abc.def", "Bearer", "plain-secret-without-prefix-1234"):
        assert bad not in blob
    assert REDACTED in blob


def test_fake_key_in_tool_output_never_reaches_trace(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)
    out = tmp_path / "out"
    tracer = Tracer(str(out))
    root = tmp_path / "code"
    (root / "rtl").mkdir(parents=True)
    c = checks.Checker(str(root), tracer, {"iverilog": True})
    rc, raw, summary = c._run("echo", ["sh", "-c", f"echo {FAKE_KEY}; echo 'Authorization: Bearer {FAKE_KEY}'"])
    assert rc == 0 and FAKE_KEY in raw  # the tool really printed it
    tracer.log("llm", node="edit", completion=f"I found {FAKE_KEY}", error=f"Bearer {FAKE_KEY}")
    text = (out / "trace.jsonl").read_text()
    assert FAKE_KEY not in text and "sk-or-" not in text and "Bearer" not in text
    assert text.count(REDACTED) >= 3


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed")
def test_real_compile_and_sv_testbench(task_tree, tmp_path):
    tracer = Tracer(str(tmp_path / "out"))
    tools = checks.detect_tools()
    c = checks.Checker(str(task_tree), tracer, tools)
    ft = FileTool(str(task_tree))
    ft.write("rtl/adder.sv", "module adder(input [3:0] a, b, output [4:0] y);\n  assign y = a + b;\nendmodule\n")
    tb = ft.write_tb("agent_tb/tb.sv", "module tb; reg [3:0] a=3,b=4; wire [4:0] y; adder u(.a(a),.b(b),.y(y));\n"
                     "initial begin #1; if (y!==7) $error(\"bad\"); else $display(\"AGENT_TB_PASS\"); $finish; end\n"
                     "endmodule\n")
    r = c.run(["testbench"], {"files": [tb], "top": "tb"})
    assert r["compile"]["ok"] is True and r["testbench"]["ok"] is True
    ft.write("rtl/adder.sv", "module adder(input [3:0] a, b, output [4:0] y);\n  assign y = a - b;\nendmodule\n")
    r = c.run(["testbench"], {"files": [tb], "top": "tb"})
    assert r["compile"]["ok"] is True and r["testbench"]["ok"] is False
    ft.write("rtl/adder.sv", "module adder(; endmodule\n")
    assert c.run([])["compile"]["ok"] is False
