"""Golden run of the claudecode harness with no skill pack, on a fake `claude`: the command line it builds, the
environment names it passes, the files it writes and the summary (without the wall time). Written once from `main`
before M3h (`write`), and compared by tests/test_m3h.py, so `harness=claudecode` with `skill_pack` blank stays
byte-for-byte what it was.

Usage (repo root): python3 tests/golden_claudecode.py write
"""
import json
import os
import stat
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))

GOLDEN = os.path.join(HERE, "fixtures", "golden", "claudecode_fake.json")
TOKEN = "sk-ant-oat01-" + "g" * 40

# Records its argv and the environment names it was given (never values), then prints a short stream with a Skill
# call (a bundled skill's name), so the default arm's handling of one is frozen too.
FAKE = """#!/usr/bin/env python3
import json, os, sys
home = os.environ.get("HOME", "")
rec = {"argv": sys.argv[1:], "env_names": sorted(k for k in os.environ if k.startswith(("CVDP_", "CLAUDE"))),
       "home_has_claude_dir": os.path.isdir(os.path.join(home, ".claude"))}
json.dump(rec, open(os.environ["FAKE_RECORD"], "w"))
open(os.path.join("rtl", "top.sv"), "w").write("module top; endmodule\\n")
ev = [
  {"type": "system", "subtype": "init", "tools": ["Bash", "Skill"], "skills": ["debug"]},
  {"type": "assistant", "message": {"id": "m1", "model": "claude-haiku-5-5", "content": [
    {"type": "tool_use", "name": "Skill", "input": {"skill": "debug"}}]}},
  {"type": "user", "message": {"content": [{"type": "text", "text": "skill body"}]}},
  {"type": "assistant", "message": {"id": "m2", "model": "claude-haiku-5-5", "content": [
    {"type": "tool_use", "name": "Bash", "input": {"command": "iverilog -g2012 rtl/top.sv"}},
    {"type": "tool_use", "name": "Write", "input": {"file_path": "rtl/top.sv"}}]}},
  {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed", "rateLimitType": "five_hour"}},
  {"type": "result", "subtype": "success", "result": "done", "num_turns": 3, "total_cost_usd": 0.02,
   "usage": {"input_tokens": 10, "cache_read_input_tokens": 900, "cache_creation_input_tokens": 90,
   "output_tokens": 50}},
]
for e in ev:
    print(json.dumps(e))
"""


def run_once(tmp, extra_env=None):
    """(record of what the fake claude saw, summary, {agent_out file: text}) for one run in `tmp`."""
    from cvdp_agent import claude_code
    from cvdp_agent.config import from_env

    root = os.path.join(tmp, "code")
    os.makedirs(os.path.join(root, "rtl"))
    os.makedirs(os.path.join(root, "docs"))
    with open(os.path.join(root, "prompt.json"), "w") as f:
        json.dump({"prompt": "Write module top."}, f)
    bin_dir = os.path.join(tmp, "bin")
    os.makedirs(bin_dir)
    fake = os.path.join(bin_dir, "claude")
    with open(fake, "w") as f:
        f.write(FAKE)
    os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC)
    env = {"PATH": bin_dir + os.pathsep + os.environ["PATH"], "CLAUDE_CODE_OAUTH_TOKEN": TOKEN,
           "CVDP_HARNESS": "claudecode", "CVDP_PROVIDER": "claude_plan", "CVDP_MODEL": "claude-haiku-5-5",
           "CVDP_ROOT": root, "CVDP_OUT_DIR": os.path.join(tmp, "out"), "CVDP_SEED": "1",
           "FAKE_RECORD": os.path.join(tmp, "record.json"), "HOME": os.path.join(tmp, "home")}
    env.update(extra_env or {})
    os.makedirs(env["HOME"], exist_ok=True)
    old = dict(os.environ)
    try:
        for k in [k for k in os.environ if k.startswith(("CVDP_", "CLAUDE"))]:
            del os.environ[k]
        os.environ.update(env)
        summary = claude_code.run(from_env())
    finally:
        os.environ.clear()
        os.environ.update(old)
    rec = json.load(open(env["FAKE_RECORD"]))
    out = env["CVDP_OUT_DIR"]
    files = {n: open(os.path.join(out, n)).read() for n in sorted(os.listdir(out))}
    return rec, summary, files


def golden():
    with tempfile.TemporaryDirectory() as tmp:
        rec, summary, files = run_once(tmp)
    summary = {k: v for k, v in summary.items() if k != "wall_time_s"}
    files = {n: (json.dumps({k: v for k, v in json.loads(t).items() if k != "wall_time_s"}, indent=1)
                 if n == "summary.json" else t) for n, t in files.items()}
    return {"record": rec, "summary": summary, "files": files}


if __name__ == "__main__":
    if sys.argv[1:] == ["write"]:
        os.makedirs(os.path.dirname(GOLDEN), exist_ok=True)
        with open(GOLDEN, "w") as f:
            json.dump(golden(), f, indent=1, sort_keys=True)
        print(f"wrote {GOLDEN}")
    else:
        print(json.dumps(golden(), indent=1, sort_keys=True))
