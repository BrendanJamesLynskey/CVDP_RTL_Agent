"""M3h: Claude Code's native skills from the private pack (the sweep input, the pinned manifest check, the install,
the CSV columns, the transcript kept out, rate limits recorded as not run) and the leak guard. Fake `claude` only;
the pack here is a synthetic one written by the test, never the private text. Tests that use the real private pack
run only where a checkout is present (RTL_PACK_CHECKOUT), and compare hashes, so nothing of it is ever printed."""
import csv
import hashlib
import json
import os
import shutil
import stat
import subprocess

import ablate
import collect
import golden_claudecode
import leak_guard
import pytest
import skill_pack
import taxonomy
from cvdp_agent import claude_code, native_skills
from cvdp_agent.config import Config, from_env
from test_m3g import RECORDING_HARNESS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL = os.environ.get("RTL_PACK_CHECKOUT") or os.path.join(ROOT, "..", "RTL_Knowledge_Pack")

BODY_A = ("# alpha-skill\n\n## When it applies\nAny design with a widget bus; read the spec for the widget width.\n\n"
          "## Key rules\n- Register every widget output once, on the rising edge, and never in two processes.\n"
          "- Name the reset \"rst_n\" when the spec is silent, and keep it active low — a default, not a law.\n")
BODY_B = ("# beta-skill\n\n## When it applies\nGadget pipelines with a valid/ready pair at each stage boundary.\n\n"
          "## Idiom: skid buffer\n```systemverilog\nalways_ff @(posedge clk) if (in_ready) gadget_q <= gadget_d;\n"
          "assign out_valid = gadget_valid_q && !stall_q;\n```\n")
INDEX = ("# Synthetic pack\n\nLoad a skill by name. These lines are only for the tests and carry no design advice.\n\n"
         "alpha-skill: widget buses, their widths and their \"registered once\" outputs; use before writing any RTL\n"
         "beta-skill: gadget pipelines and skid buffers with valid/ready at every stage, and back-pressure rules\n")


def make_pack(tmp_path, name="pack"):
    """A git checkout with generic/ (INDEX.md, two skills, MANIFEST.sha256) and its pin table."""
    co = tmp_path / name
    gen = co / "generic"
    gen.mkdir(parents=True)
    for n, t in (("INDEX.md", INDEX), ("alpha-skill.md", BODY_A), ("beta-skill.md", BODY_B)):
        (gen / n).write_bytes(t.encode())
    lines = "".join(f"{hashlib.sha256((gen / n).read_bytes()).hexdigest()}  {n}\n"
                    for n in ("INDEX.md", "alpha-skill.md", "beta-skill.md"))
    (gen / "MANIFEST.sha256").write_text(lines)
    git = ["git", "-C", str(co), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(git[:3] + ["init", "-q"], check=True)
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + ["commit", "-qm", "pack"], check=True)
    commit = subprocess.run(git[:3] + ["rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    pins = {"v9.9": {"commit": commit, "manifest_sha256": hashlib.sha256((gen / "MANIFEST.sha256").read_bytes())
                     .hexdigest(), "skills": 2}}
    return co, pins


# ---------- the default arm is byte-for-byte unchanged ----------

def test_claudecode_golden_unchanged_with_no_pack():
    got = json.loads(json.dumps(golden_claudecode.golden(), sort_keys=True))
    assert got == json.load(open(golden_claudecode.GOLDEN))
    assert "skill_pack" not in Config(harness="claudecode").switches()


def test_collect_header_unchanged_without_a_pack_and_appended_with_one():
    frozen = json.load(open(os.path.join(ROOT, "tests", "fixtures", "golden", "collect_fields_m3g.json")))
    assert collect.FIELDS == frozen
    assert set(collect.M3H_FIELDS).isdisjoint(frozen)
    assert {"skill_pack", "skill_pack_sha", "skills_n", "skill_first_turn"} <= set(collect.M3H_FIELDS)
    assert "skills_loaded" in frozen  # M3g's column, filled by an M3h row rather than added twice


def test_pack_settings_refused_off_claudecode():
    with pytest.raises(ValueError, match="claudecode"):
        Config(harness="langgraph", skill_pack="v2.0")
    with pytest.raises(ValueError, match="needs CVDP_SKILL_PACK"):
        Config(harness="claudecode", skill_hint=True)
    assert Config(harness="claudecode", skill_pack="v2.0", skill_hint=True).switches()["skill_pack"] == "v2.0"


# ---------- the pinned manifest check ----------

def test_pinned_tags_are_the_planners_hashes():
    assert native_skills.PINNED["v2.0"]["manifest_sha256"] == \
        "e405fe319fcc3392a415c0911ecc20eb5a90093a1d27b1076e92593e6b9a3298"
    assert native_skills.PINNED["v1.0"]["commit"].startswith("b30b329")
    assert native_skills.PINNED["v2.0"]["commit"].startswith("19ac3ec")


def test_verify_accepts_the_pinned_pack_and_refuses_any_change(tmp_path):
    co, pins = make_pack(tmp_path)
    sha, n = skill_pack.verify(str(co), "v9.9", pins)
    assert n == 2 and sha == pins["v9.9"]["manifest_sha256"]
    with pytest.raises(native_skills.PackError, match="unknown tag"):
        skill_pack.verify(str(co), "v1.0", pins)
    with pytest.raises(native_skills.PackError, match="checkout is at"):
        skill_pack.verify(str(co), "v9.9", {"v9.9": dict(pins["v9.9"], commit="0" * 40)})
    with pytest.raises(native_skills.PackError, match="pinned"):
        skill_pack.verify(str(co), "v9.9", {"v9.9": dict(pins["v9.9"], manifest_sha256="0" * 64)})
    gen = co / "generic"
    with open(gen / "beta-skill.md", "a") as f:
        f.write("one more line\n")
    with pytest.raises(native_skills.PackError, match="beta-skill.md does not match"):
        native_skills.verify(str(gen), "v9.9", pins)
    (gen / "beta-skill.md").write_text(BODY_B)
    (gen / "gamma.md").write_text("# gamma\n")
    with pytest.raises(native_skills.PackError, match="not in the manifest"):
        native_skills.verify(str(gen), "v9.9", pins)


def test_verify_cli_prints_hashes_only(tmp_path):
    co, pins = make_pack(tmp_path)
    (tmp_path / "pins.json").write_text(json.dumps(pins))
    env = dict(os.environ, SKILL_PACK_PINS=str(tmp_path / "pins.json"))
    r = subprocess.run(["python3", os.path.join(ROOT, "tools", "skill_pack.py"), "verify", str(co), "v9.9"],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0 and pins["v9.9"]["manifest_sha256"] in r.stdout
    assert "widget" not in r.stdout + r.stderr
    r = subprocess.run(["python3", os.path.join(ROOT, "tools", "skill_pack.py"), "verify", str(co), "v9.9"],
                       capture_output=True, text=True)  # the built-in pins do not know this tag
    assert r.returncode == 2 and "refused" in r.stderr


# ---------- the install ----------

def test_install_writes_front_matter_and_the_files_bytes_unchanged(tmp_path):
    yaml = pytest.importorskip("yaml")
    co, _ = make_pack(tmp_path)
    home = tmp_path / "home"
    names = native_skills.install(str(co / "generic"), str(home))
    assert names == ["alpha-skill", "beta-skill"]
    idx = dict(native_skills.index(str(co / "generic")))
    for n in names:
        md = (home / ".claude" / "skills" / n / "SKILL.md").read_bytes()
        assert native_skills.skill_body(md) == (co / "generic" / f"{n}.md").read_bytes()
        fm = yaml.safe_load(md.split(b"---\n")[1])
        assert fm == {"name": n, "description": idx[n]}
    assert not (home / ".claude" / "CLAUDE.md").exists()
    native_skills.install(str(co / "generic"), str(tmp_path / "home2"), hint=True)
    assert (tmp_path / "home2" / ".claude" / "CLAUDE.md").read_text() == \
        "RTL design skills are installed; check them before you start.\n"


@pytest.mark.skipif(not os.path.isdir(os.path.join(REAL, "generic")), reason="no private pack checkout here")
@pytest.mark.parametrize("tag", ["v1.0", "v2.0"])
def test_real_pack_tags_verify_and_install_byte_for_byte(tmp_path, tag):
    """Local only: each tag of the private pack, exported with git, passes the pins; each SKILL.md body hashes to its
    source file's hash (hashes compared, so no text is ever shown)."""
    yaml = pytest.importorskip("yaml")
    out = tmp_path / tag
    out.mkdir()
    arch = subprocess.run(["git", "-C", REAL, "archive", tag, "generic"], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(out)], input=arch, check=True)
    gen = out / "generic"
    assert native_skills.verify(str(gen), tag) == native_skills.PINNED[tag]["manifest_sha256"]
    home = tmp_path / "home"
    names = native_skills.install(str(gen), str(home))
    assert len(names) == native_skills.PINNED[tag]["skills"]
    h = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
    for n in names:
        md = (home / ".claude" / "skills" / n / "SKILL.md").read_bytes()
        assert h(native_skills.skill_body(md)) == h((gen / f"{n}.md").read_bytes()), n
        fm = yaml.safe_load(md.split(b"---\n")[1])
        assert fm["name"] == n and 40 < len(fm["description"]) < 1536, n


# ---------- the harness with a pack, on a fake claude ----------

FAKE = """#!/usr/bin/env python3
import json, os, sys
home = os.environ["HOME"]
skills = sorted(os.listdir(os.path.join(home, ".claude", "skills"))) if os.path.isdir(os.path.join(home, ".claude", "skills")) else []
json.dump({"home": home, "skills": skills, "cwd": os.getcwd(), "argv": sys.argv[1:],
           "hint": os.path.exists(os.path.join(home, ".claude", "CLAUDE.md"))}, open(os.environ["FAKE_RECORD"], "w"))
open(os.path.join("rtl", "top.sv"), "w").write("module top; endmodule\\n")
body = open(os.path.join(home, ".claude", "skills", "beta-skill", "SKILL.md")).read() if skills else ""
mode = os.environ.get("FAKE_MODE", "ok")
ev = [{"type": "system", "subtype": "init", "skills": skills + ["debug"]},
      {"type": "assistant", "message": {"id": "m1", "model": "claude-haiku-5-5", "content": [
        {"type": "tool_use", "name": "Skill", "input": {"skill": "debug"}}]}},
      {"type": "assistant", "message": {"id": "m2", "model": "claude-haiku-5-5", "content": [
        {"type": "text", "text": "reading"}]}},
      {"type": "assistant", "message": {"id": "m2", "model": "claude-haiku-5-5", "content": [
        {"type": "tool_use", "name": "Skill", "input": {"skill": "beta-skill"}}]}},
      {"type": "user", "message": {"content": [{"type": "text", "text": body}]}},
      {"type": "assistant", "message": {"id": "m3", "model": "claude-haiku-5-5", "content": [
        {"type": "tool_use", "name": "Skill", "input": {"skill": "/alpha-skill"}},
        {"type": "tool_use", "name": "Skill", "input": {"skill": "beta-skill"}},
        {"type": "tool_use", "name": "Bash", "input": {"command": "iverilog rtl/top.sv"}}]}}]
if mode == "limit":
    ev = ev[:2] + [{"type": "rate_limit_event", "rate_limit_info": {"status": "rejected", "rateLimitType": "seven_day"}},
                   {"type": "result", "subtype": "success", "is_error": True, "num_turns": 1, "api_error_status": 429,
                    "api_error": "usage_limit_reached", "terminal_reason": "api_error",
                    "result": "You've hit your weekly limit"}]
else:
    ev.append({"type": "result", "subtype": "success", "result": "done", "num_turns": 3, "total_cost_usd": 0.01,
               "usage": {"input_tokens": 5, "output_tokens": 7}})
for e in ev:
    print(json.dumps(e))
"""


def setup_cc(tmp_path, monkeypatch, pins=None, pack=True, hint=False, mode="ok"):
    co, made = make_pack(tmp_path)
    monkeypatch.setattr(native_skills, "PINNED", pins if pins is not None else made)
    root = tmp_path / "code"
    (root / "rtl").mkdir(parents=True)
    (root / "prompt.json").write_text(json.dumps({"prompt": "Write module top. Write your answer to `rtl/top.sv`."}))
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "claude"
    fake.write_text(FAKE)
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-" + "z" * 40)
    monkeypatch.setenv("FAKE_RECORD", str(tmp_path / "rec.json"))
    monkeypatch.setenv("FAKE_MODE", mode)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "elsewhere"))
    (tmp_path / "userhome").mkdir()
    monkeypatch.setenv("HOME", str(tmp_path / "userhome"))
    for k, v in (("CVDP_HARNESS", "claudecode"), ("CVDP_PROVIDER", "claude_plan"), ("CVDP_MODEL", "claude-haiku-5-5"),
                 ("CVDP_ROOT", str(root)), ("CVDP_OUT_DIR", str(root / "rundir" / "agent_out"))):
        monkeypatch.setenv(k, v)
    if pack:
        monkeypatch.setenv("CVDP_SKILL_PACK", "v9.9")
        monkeypatch.setenv("CVDP_SKILL_PACK_DIR", str(co / "generic"))
        monkeypatch.setenv("CVDP_SKILL_HINT", "1" if hint else "0")
    return root, from_env()


def test_pack_is_installed_outside_the_tree_and_loads_are_recorded(tmp_path, monkeypatch):
    root, cfg = setup_cc(tmp_path, monkeypatch)
    s = claude_code.run(cfg)
    rec = json.load(open(tmp_path / "rec.json"))
    assert rec["skills"] == ["alpha-skill", "beta-skill"] and not rec["hint"]
    assert not os.path.realpath(rec["home"]).startswith(os.path.realpath(str(root)))
    assert s["stop_reason"] == "submit" and s["skill_pack"] == "v9.9" and s["skills_installed"] == 2
    assert s["skill_pack_sha"] == native_skills.PINNED["v9.9"]["manifest_sha256"]
    # every Skill call in order, the bundled one included; distinct pack skills; turn of the first pack load
    assert s["skills_loaded"] == ["debug", "beta-skill", "alpha-skill", "beta-skill"]
    assert s["skills_n"] == 2 and s["skill_first_turn"] == 2
    assert s["switches"]["skill_pack"] == "v9.9" and "skill_hint" not in s["switches"]
    out = root / "rundir" / "agent_out"
    assert sorted(os.listdir(out)) == ["claude_tools.jsonl", "summary.json"]  # no raw stream
    skel = [json.loads(x) for x in open(out / "claude_tools.jsonl")]
    assert {"turn": 2, "tool": "Skill", "skill": "beta-skill"} in skel
    for dirpath, _, names in os.walk(root):  # no pack text anywhere in the task tree, agent_out included
        for n in names:
            text = open(os.path.join(dirpath, n), "rb").read()
            assert b"skid buffer" not in text and b"widget bus" not in text and n != "SKILL.md", n
    # the argv is the default arm's: the pack changes only what is installed
    golden = json.load(open(golden_claudecode.GOLDEN))["record"]["argv"]
    assert [a for a in rec["argv"] if not a.startswith("You are solving")] == \
        [a for a in golden if not a.startswith("You are solving")]


def test_hint_writes_the_one_line_claude_md(tmp_path, monkeypatch):
    _, cfg = setup_cc(tmp_path, monkeypatch, hint=True)
    s = claude_code.run(cfg)
    assert json.load(open(tmp_path / "rec.json"))["hint"] and s["switches"]["skill_hint"] is True


def test_a_pack_that_is_not_the_pinned_one_stops_before_claude_runs(tmp_path, monkeypatch):
    bad = {"v9.9": {"commit": "x", "manifest_sha256": "0" * 64, "skills": 2}}
    _, cfg = setup_cc(tmp_path, monkeypatch, pins=bad)
    s = claude_code.run(cfg)
    assert s["stop_reason"] == "skills_error" and "refused" in s["error"]
    assert not (tmp_path / "rec.json").exists()  # claude was never started


def test_rate_limited_problem_is_recorded_as_such_and_left_out_of_the_score(tmp_path, monkeypatch):
    root, cfg = setup_cc(tmp_path, monkeypatch, pack=False, mode="limit")
    s = claude_code.run(cfg)
    assert s["stop_reason"] == "rate_limited" and s["rate_limit"] == "seven_day", s.get("error")
    # the ladder's real 429 result (no rejected event) is caught too
    r = {"subtype": "success", "is_error": True, "api_error_status": 429, "api_error": "usage_limit_reached"}
    assert claude_code.rate_limited([], r) == "usage_limit_reached"
    ok = [json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": "allowed"}})]
    assert claude_code.rate_limited(ok, {"subtype": "success", "result": "done"}) is None
    assert taxonomy.label({"stop_reason": "rate_limited"})[0] == "llm_error"
    # ablate leaves the row out (not run), not as a failure
    p = tmp_path / "a.csv"
    p.write_text("id,seed,pass,stop_reason\nx,1,0,rate_limited\ny,1,1,submit\n")
    rows = ablate.load(str(p))
    assert [r["id"] for r in rows] == ["y"]


def test_collect_writes_the_m3h_columns_with_skill_pack(tmp_path, monkeypatch):
    root, cfg = setup_cc(tmp_path, monkeypatch)
    # lay the tree out the way the harness does: work/<repo>/harness/<n>
    work = tmp_path / "work"
    pdir = work / "cvdp_copilot_top" / "harness" / "1"
    pdir.parent.mkdir(parents=True)
    shutil.move(str(root), str(pdir))
    monkeypatch.setenv("CVDP_ROOT", str(pdir))
    monkeypatch.setenv("CVDP_OUT_DIR", str(pdir / "rundir" / "agent_out"))
    claude_code.run(from_env())
    (work / "raw_result.json").write_text(json.dumps({"cvdp_copilot_top_0001": {
        "category": "cid003", "difficulty": "easy", "tests": [{"result": 0, "log": "/x/1.txt"}]}}))
    r = collect.rows(str(work), skill_pack=True)[0]
    assert (r["skill_pack"], r["skills_n"], r["skill_first_turn"]) == ("v9.9", 2, 2)
    assert r["skills_loaded"] == "debug;beta-skill;alpha-skill;beta-skill" and r["skills_installed"] == 2
    assert "skill_pack" not in collect.rows(str(work))[0]


# ---------- the sweep input ----------

def sweep(tmp_path, **kw):
    cvdp = tmp_path / "cvdp"
    cvdp.mkdir(exist_ok=True)
    (cvdp / "run_benchmark.py").write_text(RECORDING_HARNESS)
    (cvdp / "run_benchmark.py").chmod(0o755)
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    (data / "agentic_code_generation_no_commercial.jsonl").write_text(
        json.dumps({"id": "cvdp_agentic_lfsr_0001", "categories": ["cid016", "easy"]}) + "\n")
    (data / "m3g_heldout_agentic.jsonl").write_text(
        json.dumps({"id": "cvdp_copilot_x_0001", "categories": ["cid003", "easy"]}) + "\n")
    env = dict(os.environ, MODEL="claude-haiku-5-5", HARNESS="claudecode", THREADS="1", WORK=str(tmp_path / "work"),
               CVDP_DIR=str(cvdp), DATA_DIR=str(data), AGENT_IMAGE="unused", SEEN=str(tmp_path / "seen.json"),
               CLAUDE_CODE_OAUTH_TOKEN="sk-ant-oat01-" + "q" * 40, OPENROUTER_API_KEY="")
    env.update(kw)
    r = subprocess.run(["bash", os.path.join(ROOT, "tools", "sweep.sh"), "run"], env=env, capture_output=True,
                       text=True, timeout=120, cwd=ROOT)
    return r, (json.load(open(tmp_path / "seen.json")) if r.returncode == 0 else None)


def test_sweep_claudecode_default_has_no_pack_and_runs_the_heldout_split(tmp_path):
    r, seen = sweep(tmp_path, SPLIT="m3g_heldout")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "--force-agentic" in seen["argv"] and seen["ids"] == ["cvdp_copilot_x_0001"]
    assert "CVDP_SKILL_PACK" not in seen["env"] and "/skill_pack" not in seen["mounts"]
    assert "CLAUDE_CODE_OAUTH_TOKEN" in seen["env"] and "OPENROUTER_API_KEY" not in seen["env"]
    run_json = json.load(open(str(tmp_path / "work") + ".run.json"))
    assert "skill_pack" not in run_json and run_json["harness"] == "claudecode"


def test_sweep_mounts_the_verified_pack_read_only(tmp_path):
    co, pins = make_pack(tmp_path)
    (tmp_path / "pins.json").write_text(json.dumps(pins))
    r, seen = sweep(tmp_path, SKILL_PACK="v9.9", SKILL_PACK_DIR=str(co), SKILL_PACK_PINS=str(tmp_path / "pins.json"),
                    SPLIT="m3g_heldout")
    assert r.returncode == 0, r.stdout + r.stderr
    specs = [x.split(":") for x in seen["mounts"].split(";") if x.strip()]
    assert [x[1] for x in specs] == ["/ledger", "/skill_pack"] and specs[1][2] == "ro"
    assert os.path.samefile(specs[1][0], co / "generic")
    assert seen["env"].endswith(",CVDP_SKILL_PACK,CVDP_SKILL_PACK_DIR,CVDP_SKILL_HINT")
    run_json = json.load(open(str(tmp_path / "work") + ".run.json"))
    assert (run_json["skill_pack"], run_json["skill_pack_sha"], run_json["skill_hint"]) == \
        ("v9.9", pins["v9.9"]["manifest_sha256"], False)
    assert "widget" not in r.stdout + r.stderr


@pytest.mark.parametrize("kw,msg", [
    ({"SKILL_PACK": "latest"}, "pack tag"),
    ({"SKILL_PACK": "v2.0", "HARNESS": "langgraph"}, "HARNESS=claudecode"),
    ({"SKILL_PACK": "v2.0", "SKILL_PACK_DIR": "/nonexistent"}, "refused"),
    ({"SKILL_HINT": "1"}, "needs SKILL_PACK"),
])
def test_sweep_refuses_bad_pack_settings_before_running(tmp_path, kw, msg):
    r, _ = sweep(tmp_path, **kw)
    assert r.returncode == 2 and msg in r.stderr, r.stderr
    assert not (tmp_path / "seen.json").exists()  # the harness never started


def test_sweep_refuses_a_pack_that_differs_from_its_pin(tmp_path):
    co, pins = make_pack(tmp_path)
    with open(co / "generic" / "alpha-skill.md", "a") as f:
        f.write("changed\n")
    (tmp_path / "pins.json").write_text(json.dumps(pins))
    r, _ = sweep(tmp_path, SKILL_PACK="v9.9", SKILL_PACK_DIR=str(co), SKILL_PACK_PINS=str(tmp_path / "pins.json"))
    assert r.returncode == 2 and "does not match" in r.stderr and not (tmp_path / "seen.json").exists()


def test_workflow_wires_the_private_pack_and_the_guard():
    yaml = pytest.importorskip("yaml")
    wf = yaml.safe_load(open(os.path.join(ROOT, ".github", "workflows", "sweep.yml")))
    on = wf.get("on") or wf.get(True)
    assert on["workflow_dispatch"]["inputs"]["skill_pack"]["default"] == ""
    steps = wf["jobs"]["sweep"]["steps"]
    names = [s.get("name", s.get("uses", "")) for s in steps]
    co = steps[names.index("Private skill pack, checkout at its tag")]
    assert co["with"]["repository"] == "BrendanJamesLynskey/RTL_Knowledge_Pack"
    assert co["with"]["ssh-key"] == "${{ secrets.RTL_PACK_DEPLOY_KEY }}" and co["with"]["path"] == "_pack"
    # the pack is checked before any model call, and the guard runs before the table, the log rows and the upload
    assert names.index("Private skill pack, pinned commit and manifest") < names.index("Run")
    guard = names.index("Leak guard (skill pack text)")
    assert names.index("Collect and tabulate") < guard < names.index("Publish the table")
    upload = [s for s in steps if s.get("uses", "").startswith("actions/upload-artifact")][0]
    assert guard < steps.index(upload) and "steps.leak.outcome != 'failure'" in upload["if"]
    assert "GITHUB_STEP_SUMMARY" not in steps[names.index("Collect and tabulate")]["run"]
    assert all("cat " not in str(s.get("run", "")) or "_pack" not in str(s.get("run", "")) for s in steps)


# ---------- the leak guard ----------

def test_guard_catches_a_planted_window_in_every_form(tmp_path):
    co, _ = make_pack(tmp_path)
    gen = str(co / "generic")
    up = tmp_path / "upload"
    up.mkdir()
    (up / "clean.txt").write_text("module top; endmodule\n" * 50)
    assert leak_guard.scan(gen, [str(up)]) == []
    win = BODY_A.encode()[30:110]  # 80 bytes
    (up / "raw.log").write_bytes(b"prefix " + win + b" suffix")
    (up / "short.log").write_bytes(b"x " + win[:79] + b" y")  # 79 bytes: not a window
    (up / "s.json").write_text(json.dumps({"error": BODY_A}))  # JSON-escaped, — included
    (up / "p.patch").write_text("".join("+" + ln + "\n" for ln in BODY_B.splitlines()))  # diff-prefixed
    (up / "idx.md").write_text("see: " + INDEX.splitlines()[4][:85])  # an INDEX line
    leaks = leak_guard.scan(gen, [str(up)])
    hit = {os.path.basename(f) for f, *_ in leaks}
    assert hit == {"raw.log", "s.json", "p.patch", "idx.md"}, leaks
    # the CLI fails and prints file, form, offset, label, length: never the text
    r = subprocess.run(["python3", os.path.join(ROOT, "tools", "leak_guard.py"), "--pack", gen, str(up)],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "raw.log" in r.stdout and "alpha-skill" in r.stdout
    assert win.decode() not in r.stdout + r.stderr and "widget" not in r.stdout + r.stderr


def test_guard_allows_text_that_is_also_in_the_public_inputs(tmp_path):
    co, _ = make_pack(tmp_path)
    gen = str(co / "generic")
    pub = tmp_path / "data"
    pub.mkdir()
    common = BODY_B.split("```systemverilog\n")[1].split("```")[0]  # an idiom, also "in the public dataset"
    assert len(common) >= 80
    (pub / "dataset.jsonl").write_text(json.dumps({"harness": {"tb.sv": "// x\n" + common}}) + "\n")
    up = tmp_path / "upload"
    up.mkdir()
    (up / "rtl.sv").write_text("module m;\n" + common + "endmodule\n")
    assert leak_guard.scan(gen, [str(up)]) != []                 # without --public it counts
    assert leak_guard.scan(gen, [str(up)], [str(pub)]) == []     # it is public text
    (up / "more.sv").write_text(BODY_A)                          # private text still counts
    assert {os.path.basename(f) for f, *_ in leak_guard.scan(gen, [str(up)], [str(pub)])} == {"more.sv"}
    r = subprocess.run(["python3", os.path.join(ROOT, "tools", "leak_guard.py"), "--pack", gen, "--public", str(pub),
                        str(up / "rtl.sv")], capture_output=True, text=True)
    assert r.returncode == 0 and "no 80-byte window" in r.stdout


def test_guard_fails_without_a_pack(tmp_path):
    r = subprocess.run(["python3", os.path.join(ROOT, "tools", "leak_guard.py"), "--pack", str(tmp_path / "none"),
                        str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 2
