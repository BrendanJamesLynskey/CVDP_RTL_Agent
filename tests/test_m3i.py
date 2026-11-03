"""M3i: Claude Code's `plain` profile (our system prompt, Read/Write/Edit/Bash only, no settings, skills or MCP):
the sweep input, the default command line unchanged, the plain command line, the init-event check, the CSV columns.
Fake `claude` only; no model is called."""
import hashlib
import json
import os
import shutil
import stat

import ablate
import collect
import golden_claudecode
import pytest
import taxonomy
from cvdp_agent import claude_code
from cvdp_agent.config import Config, from_env
from cvdp_agent.prompts import SYSTEM
from test_m3h import sweep

TOKEN = "sk-ant-oat01-" + "i" * 40

# Records argv and the environment (names, plus HOME's contents and the memory switch), then prints a stream whose
# init event is chosen by FAKE_INIT.
FAKE = """#!/usr/bin/env python3
import json, os, sys
home = os.environ.get("HOME", "")
json.dump({"argv": sys.argv[1:], "home": home, "home_files": sorted(os.listdir(home)),
           "no_memory": os.environ.get("CLAUDE_CODE_DISABLE_AUTO_MEMORY"), "cwd": os.getcwd()},
          open(os.environ["FAKE_RECORD"], "w"))
tools = os.environ.get("FAKE_TOOLS", "Bash,Edit,Read,Write").split(",")
skills = [s for s in os.environ.get("FAKE_SKILLS", "").split(",") if s]
mcp = [{"name": "x", "status": "connected"}] if os.environ.get("FAKE_MCP") else []
ev = []
if os.environ.get("FAKE_INIT", "1") == "1":
    ev.append({"type": "system", "subtype": "init", "tools": tools, "skills": skills, "mcp_servers": mcp,
               "model": "claude-haiku-5-5"})
ev += [
  {"type": "assistant", "message": {"id": "m1", "model": "claude-haiku-5-5", "content": [
    {"type": "tool_use", "name": "Write", "input": {"file_path": "rtl/top.sv"}}]}},
  {"type": "result", "subtype": "success", "result": "done", "num_turns": 2, "total_cost_usd": 0.01,
   "usage": {"input_tokens": 10, "output_tokens": 5}},
]
print(json.dumps(ev[0]), flush=True) if os.environ.get("FAKE_INIT", "1") == "1" else None
import time
time.sleep(1.5)  # the harness kills a run that is not the profile in this window; only a live run reaches the write
open("rtl/top.sv" if set(tools) == {"Bash", "Edit", "Read", "Write"} and not skills and not mcp else "rtl/ran_anyway.sv",
     "w").write("module top; endmodule\\n")
for e in ev[1 if os.environ.get("FAKE_INIT", "1") == "1" else 0:]:
    print(json.dumps(e), flush=True)
"""


def setup(tmp_path, monkeypatch, profile="plain", **env):
    root = tmp_path / "code"
    (root / "rtl").mkdir(parents=True)
    (root / "prompt.json").write_text(json.dumps({"prompt": "Write module top."}))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "claude"
    fake.write_text(FAKE)
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    for k, v in dict(CLAUDE_CODE_OAUTH_TOKEN=TOKEN, CVDP_HARNESS="claudecode", CVDP_PROVIDER="claude_plan",
                     CVDP_MODEL="claude-haiku-5-5", CVDP_ROOT=str(root), CVDP_OUT_DIR=str(tmp_path / "out"),
                     FAKE_RECORD=str(tmp_path / "rec.json"), CVDP_CC_PROFILE=profile, **env).items():
        monkeypatch.setenv(k, v)
    return root, from_env()


# ---------- the input ----------

def test_profile_input_and_its_refusals():
    assert Config(harness="claudecode").cc_profile == "default"
    assert "cc_profile" not in Config(harness="claudecode").switches()
    assert Config(harness="claudecode", cc_profile="plain").switches()["cc_profile"] == "plain"
    with pytest.raises(ValueError, match="claudecode"):
        Config(harness="langgraph", cc_profile="plain")
    with pytest.raises(ValueError, match="default, plain or bare"):
        Config(harness="claudecode", cc_profile="lean")
    with pytest.raises(ValueError, match="API key"):  # M3j: bare needs the API key, not the plan
        Config(harness="claudecode", cc_profile="bare")
    with pytest.raises(ValueError, match="no skills"):
        Config(harness="claudecode", cc_profile="plain", skill_pack="v2.0")


# ---------- the default arm is unchanged ----------

def test_default_command_line_is_the_golden_one_with_the_profile_named_default(tmp_path):
    frozen = json.load(open(golden_claudecode.GOLDEN))
    got = json.loads(json.dumps(_golden_with(tmp_path, {}), sort_keys=True))
    assert got == frozen  # profile not set: the frozen M3h golden run, byte for byte
    # profile set to "default" (the sweep never exports it then): same argv, summary and files; only the env name differs
    got = json.loads(json.dumps(_golden_with(tmp_path, {"CVDP_CC_PROFILE": "default"}), sort_keys=True))
    assert got["record"]["argv"] == frozen["record"]["argv"]
    assert got["summary"] == frozen["summary"] and got["files"] == frozen["files"]


def _golden_with(tmp_path, extra):
    import tempfile
    with tempfile.TemporaryDirectory(dir=str(tmp_path)) as tmp:
        rec, summary, files = golden_claudecode.run_once(tmp, extra)
    summary = {k: v for k, v in summary.items() if k != "wall_time_s"}
    files = {n: (json.dumps({k: v for k, v in json.loads(t).items() if k != "wall_time_s"}, indent=1)
                 if n == "summary.json" else t) for n, t in files.items()}
    return {"record": rec, "summary": summary, "files": files}


# ---------- the plain command line ----------

def test_plain_command_line_and_environment(tmp_path, monkeypatch):
    root, cfg = setup(tmp_path, monkeypatch)
    s = claude_code.run(cfg)
    rec = json.load(open(tmp_path / "rec.json"))
    a = rec["argv"]
    flag = lambda f: a[a.index(f) + 1]  # noqa: E731
    assert a[0] == "-p" and a[1].startswith("You are solving one hardware-design task")  # the default arm's user message
    assert flag("--system-prompt") == SYSTEM and "--append-system-prompt" not in a
    assert flag("--tools") == "Read,Write,Edit,Bash"
    assert a[a.index("--allowedTools") + 1:a.index("--allowedTools") + 5] == ["Read", "Write", "Edit", "Bash"]
    denied = a[a.index("--disallowedTools") + 1:a.index("--setting-sources")]
    assert "Bash(curl:*)" in denied and "WebFetch" not in denied  # the tools are not offered at all
    assert flag("--setting-sources") == "" and "--strict-mcp-config" in a
    assert json.loads(flag("--mcp-config")) == {"mcpServers": {}}
    assert "--disable-slash-commands" in a and "--safe-mode" in a and "--bare" not in a
    assert flag("--max-turns") == "60" and flag("--permission-mode") == "acceptEdits"
    assert flag("--model") == "claude-haiku-5-5" and "--effort" not in a
    assert rec["home_files"] == [] and rec["no_memory"] == "1" and rec["cwd"] == str(root)
    assert not os.path.realpath(rec["home"]).startswith(os.path.realpath(str(root)))
    assert s["stop_reason"] == "submit"


def test_the_prompt_is_the_agent_codes_own_text_with_its_hash_recorded(tmp_path, monkeypatch):
    from cvdp_agent import prompts
    root, cfg = setup(tmp_path, monkeypatch)
    s = claude_code.run(cfg)
    assert claude_code.SYSTEM is prompts.SYSTEM  # imported at run time from the agent code, not copied
    assert s["cc_prompt_sha256"] == hashlib.sha256(prompts.SYSTEM.encode()).hexdigest()
    assert s["switches"]["cc_profile"] == "plain"


# ---------- the init event ----------

def test_init_event_columns(tmp_path, monkeypatch):
    root, cfg = setup(tmp_path, monkeypatch)
    s = claude_code.run(cfg)
    assert (s["cc_profile"], s["cc_tools"], s["cc_skills_n"], s["cc_mcp_n"], s["cc_model"]) == \
        ("plain", "Bash;Edit;Read;Write", 0, 0, "claude-haiku-5-5")


@pytest.mark.parametrize("env,what", [({"FAKE_TOOLS": "Bash,Edit,Read,Write,WebFetch"}, "tools"),
                                       ({"FAKE_TOOLS": "Bash,Edit,Read"}, "tools"),
                                       ({"FAKE_MCP": "1"}, "MCP"), ({"FAKE_SKILLS": "debug"}, "skill"),
                                       ({"FAKE_INIT": "0"}, "no init")])
def test_an_init_event_that_is_not_the_profile_fails_the_run_before_scoring(tmp_path, monkeypatch, env, what):
    root, cfg = setup(tmp_path, monkeypatch, **env)
    s = claude_code.run(cfg)
    assert s["stop_reason"] == "profile_error" and what in s["error"]
    assert not (root / "rtl" / "ran_anyway.sv").exists()  # killed at the init event, before it did anything
    # the row is not a result: ablate leaves it out like a rate limit, and a failure label is not a model failure
    p = tmp_path / "a.csv"
    p.write_text("id,seed,pass,stop_reason\nx,1,0,profile_error\ny,1,1,submit\n")
    assert [r["id"] for r in ablate.load(str(p))] == ["y"]
    assert taxonomy.label({"stop_reason": "profile_error"})[0] == "llm_error"


def test_profile_problems_unit():
    ok = {"tools": ["Read", "Write", "Edit", "Bash"], "skills": [], "mcp_servers": []}
    assert claude_code.profile_problems(ok) == []
    assert claude_code.profile_problems(dict(ok, tools=ok["tools"] + ["Agent"]))
    assert claude_code.profile_problems(None)


# ---------- the CSV ----------

def test_collect_columns_only_with_the_profile_flag(tmp_path, monkeypatch):
    root, cfg = setup(tmp_path, monkeypatch)
    work = tmp_path / "work"
    pdir = work / "cvdp_copilot_top" / "harness" / "1"
    pdir.parent.mkdir(parents=True)
    shutil.move(str(root), str(pdir))
    monkeypatch.setenv("CVDP_ROOT", str(pdir))
    monkeypatch.setenv("CVDP_OUT_DIR", str(pdir / "rundir" / "agent_out"))
    claude_code.run(from_env())
    (work / "raw_result.json").write_text(json.dumps({"cvdp_copilot_top_0001": {
        "category": "cid003", "difficulty": "easy", "tests": [{"result": 0, "log": "/x/1.txt"}]}}))
    r = collect.rows(str(work), cc_profile=True)[0]
    assert (r["cc_profile"], r["cc_tools"], r["cc_skills_n"], r["cc_mcp_n"], r["cc_model"]) == \
        ("plain", "Bash;Edit;Read;Write", 0, 0, "claude-haiku-5-5")
    assert r["cc_prompt_sha256"] == hashlib.sha256(SYSTEM.encode()).hexdigest()
    assert "cc_profile" not in collect.rows(str(work))[0]
    assert set(collect.M3I_FIELDS).isdisjoint(collect.FIELDS) and set(collect.M3I_FIELDS).isdisjoint(collect.M3H_FIELDS)
    frozen = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests",
                                         "fixtures", "golden", "collect_fields_m3g.json")))
    assert collect.FIELDS == frozen


# ---------- the sweep ----------

def test_sweep_plain_names_the_profile_and_default_does_not(tmp_path):
    r, seen = sweep(tmp_path, CC_PROFILE="plain")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "CVDP_CC_PROFILE" in seen["env"]
    assert json.load(open(str(tmp_path / "work") + ".run.json"))["cc_profile"] == "plain"
    (tmp_path / "d").mkdir()
    r, seen = sweep(tmp_path / "d")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "CVDP_CC_PROFILE" not in seen["env"]
    assert "cc_profile" not in json.load(open(str(tmp_path / "d" / "work") + ".run.json"))


@pytest.mark.parametrize("kw,msg", [({"CC_PROFILE": "lean"}, "default, plain or bare"),
                                     ({"CC_PROFILE": "bare"}, "CLAUDE_ENDPOINT=api"),
                                     ({"CC_PROFILE": "plain", "HARNESS": "langgraph", "MODEL": "fake"}, "claudecode")])
def test_sweep_refuses_bad_profile_settings(tmp_path, kw, msg):
    r, _ = sweep(tmp_path, **kw)
    assert r.returncode == 2 and msg in r.stderr and not (tmp_path / "seen.json").exists()


def test_workflow_has_the_input_and_pull_requests_get_default():
    import yaml
    wf = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".github",
                                          "workflows", "sweep.yml")))
    on = wf.get("on") or wf.get(True)
    inp = on["workflow_dispatch"]["inputs"]["cc_profile"]
    assert inp["options"] == ["default", "plain", "bare"] and inp["default"] == "default"
    assert "'default'" in wf["env"]["CC_PROFILE"] and "inputs.cc_profile" in wf["env"]["CC_PROFILE"]


def test_workflow_dispatch_has_at_most_25_inputs():
    # GitHub rejects a workflow_dispatch with more than 25 inputs: the file is then invalid and every push logs a
    # failed run with no jobs.
    import yaml
    wf = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".github",
                                          "workflows", "sweep.yml")))
    on = wf.get("on") or wf.get(True)
    inputs = on["workflow_dispatch"]["inputs"]
    assert len(inputs) <= 25
    assert "inputs.mutation_gate" not in str(wf) and "fixed_checks" in wf["env"]["SPEC_VECTORS"]
