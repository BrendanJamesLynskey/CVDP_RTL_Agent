"""M3g: the knowledge pack (manifest, frozen hashes, skill selection, the cap, unknown names, the CSV columns), the
default agent unchanged (golden), the held-out set tool and the sweep's new inputs. Fake provider only."""
import csv
import hashlib
import io
import json
import os
import shutil
import subprocess

import collect
import golden_langgraph
import m3g_heldout
import pytest
from cvdp_agent import prompts, skillpack
from cvdp_agent.config import Config
from cvdp_agent.graph import run
from cvdp_agent.llm import FakeLLM
from cvdp_agent.trace import Tracer
from conftest import FakeChecker, FakeClock
from test_graph import GOOD, decide, edit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, "agent", "cvdp_agent", "skills", "rtl_pack")
# Recorded by the planner in _handoff/cvdp_agent/cvdp_agent_plan.md after reviewing brief 18A's pack
FROZEN_INDEX = "87d242eda20d1c97061e14acfb6d244ec9d35676c5c8a36700b20d1d32f62f69"
FROZEN_MANIFEST = "e6ca1610e84fc775a89d812d4f6fcd96cf3afce7d2a24d5add0a9caeae2a7245"
TOOLS = {"iverilog": True, "verilator": True, "yosys": True, "cocotb": True}


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def plan_with(skills):
    return json.dumps({"files_to_change": ["rtl/adder.sv"], "approach": "y = a + b", "check_plan": "compile",
                       "skills": skills})


def go(task_tree, script, **kw):
    clock = FakeClock()
    cfg = Config(root=str(task_tree), provider="fake", **kw)
    llm = FakeLLM([{"text": t, "cost": 0.001} if isinstance(t, str) else t for t in script], clock=clock)
    s = run(cfg, llm=llm, checker=FakeChecker(str(task_tree), clock=clock), tools=TOOLS, clock=clock,
            tracer=Tracer(cfg.agent_out))
    trace = [json.loads(x) for x in open(os.path.join(cfg.agent_out, "trace.jsonl"))]
    return s, llm, trace


def user_msg(req):
    return [m["content"] for m in req["messages"] if m["role"] == "user"][0]


# ---------- the pack in the repo is the frozen one ----------

def test_pack_files_match_their_manifest_and_the_planners_frozen_hashes():
    want = skillpack.verify(PACK)  # raises on any missing or changed file
    assert len(want) == 17 and "INDEX.md" in want and "PROVENANCE.md" in want
    assert sha(os.path.join(PACK, "INDEX.md")) == FROZEN_INDEX
    assert sha(os.path.join(PACK, "MANIFEST.sha256")) == FROZEN_MANIFEST
    assert sorted(f for f in os.listdir(PACK)) == sorted(list(want) + ["MANIFEST.sha256"])
    p = skillpack.Pack(PACK)
    assert len(p.names) == 15 and p.names[0] == "spec-reading" and p.hash == FROZEN_MANIFEST
    # the cap holds any three skills of this pack whole
    assert sum(sorted((len(b.encode()) for b in p.bodies.values()), reverse=True)[:3]) <= skillpack.CAP_BYTES


def test_a_changed_or_extra_file_refuses_the_pack(tmp_path):
    bad = tmp_path / "pack"
    shutil.copytree(PACK, bad)
    with open(bad / "fsm-design.md", "a") as f:
        f.write("\nextra advice\n")
    with pytest.raises(skillpack.PackError, match="fsm-design.md does not match"):
        skillpack.Pack(str(bad))
    shutil.rmtree(bad)
    shutil.copytree(PACK, bad)
    (bad / "uart.md").write_text("# uart\n")
    with pytest.raises(skillpack.PackError, match="not in the manifest: uart.md"):
        skillpack.Pack(str(bad))
    os.remove(bad / "MANIFEST.sha256")
    with pytest.raises(skillpack.PackError, match="no MANIFEST"):
        skillpack.Pack(str(bad))


def test_a_pack_that_fails_its_manifest_stops_before_any_llm_call(task_tree, tmp_path):
    bad = tmp_path / "pack"
    shutil.copytree(PACK, bad)
    (bad / "INDEX.md").write_text("spec-reading: changed\n")
    s, llm, trace = go(task_tree, [plan_with([]), edit(), decide("submit")], skills=str(bad))
    assert s["stop_reason"] == "skills_error" and s["llm_calls"] == 0 and llm.requests == []
    assert s["skills_status"] == "pack_error" and s["skills_pack"] is None
    assert any(e["kind"] == "skills" and "does not match" in e["error"] for e in trace if "error" in e)


# ---------- the default arm is byte-for-byte unchanged ----------

def test_langgraph_golden_unchanged_with_no_pack():
    got = json.loads(json.dumps(golden_langgraph.run_all({"skills": ""}), sort_keys=True))
    assert got == json.load(open(golden_langgraph.GOLDEN))
    assert "skills" not in Config().switches()


# ---------- selection, the prompts, the trace and the summary ----------

def test_plan_gets_the_index_and_edit_prompts_get_the_chosen_bodies(task_tree):
    asked = ["spec-reading", "FSM-Design.md", "uart", "spec-reading", "fifo-design", "reset-strategy"]
    script = [plan_with(asked), edit(), decide("edit_again"), edit(GOOD + "// v2\n"), decide("submit")]
    s, llm, trace = go(task_tree, script, skills=PACK)
    pack = skillpack.Pack(PACK)
    plan, e1, r1, e2, r2 = (user_msg(r) for r in llm.requests)
    assert plan.endswith(prompts.SKILLS_INDEX.format(k=3, index=pack.index))
    loaded = ["spec-reading", "fsm-design", "fifo-design"]  # in the plan's order, at most 3, repeats dropped
    for e in (e1, e2):
        assert e.count("## Skill: ") == 3 and all(pack.bodies[n] in e for n in loaded)
        assert e.index("# Plan") < e.index("# Skills loaded") < e.index("# Current files")
        assert pack.bodies["reset-strategy"] not in e
    assert "## Skill:" not in r1 and "## Skill:" not in r2 and "## Skill:" not in plan  # reflect gets none
    want_bytes = sum(len(pack.bodies[n].encode()) for n in loaded)
    assert (s["skills_loaded"], s["skills_unknown"], s["skills_bytes"]) == (loaded, ["uart"], want_bytes)
    assert s["skills_status"] == "loaded" and s["skills_truncated"] is False and s["skills_pack"] == FROZEN_MANIFEST
    assert s["skills_requested"] == asked and s["switches"]["skills"] == PACK
    ev = [e for e in trace if e["kind"] == "skills"]
    assert len(ev) == 1 and ev[0]["loaded"] == loaded and ev[0]["bytes"] == want_bytes and ev[0]["cap"] == 13_000


def test_the_cap_cuts_the_last_skill_at_a_line_and_says_so(task_tree):
    s, llm, _ = go(task_tree, [plan_with(["spec-reading", "fsm-design", "fifo-design"]), edit(),
                                      decide("submit")], skills=PACK, skills_cap_bytes=6000)
    e = user_msg(llm.requests[1])
    pack = skillpack.Pack(PACK)
    assert s["skills_truncated"] is True and s["skills_bytes"] <= 6000
    assert s["skills_loaded"] == ["spec-reading", "fsm-design"]  # fifo-design no longer fits at all
    assert pack.bodies["spec-reading"] in e and pack.bodies["fsm-design"] not in e
    assert "[... cut: the loaded skills' size cap]" in e and "## Skill: fifo-design" not in e
    text, loaded, used, cut = pack.block(["spec-reading"], cap=100)
    assert cut and used <= 100 and (loaded == [] or text.endswith("cap]\n"))


@pytest.mark.parametrize("skills", [[], ["uart", "spi"], "not a list", None, {"a": 1}])
def test_no_known_skill_leaves_the_edit_prompt_as_without_a_pack(task_tree, skills):
    script = [plan_with(skills), edit(), decide("submit")]
    s, llm, _ = go(task_tree, script, skills=PACK)
    assert s["skills_status"] == "not_chosen" and s["skills_loaded"] == [] and s["skills_bytes"] == 0
    assert "# Skills loaded" not in user_msg(llm.requests[1])


def test_edit_prompt_without_a_pack_is_the_same_text_as_with_one_that_loaded_nothing(tmp_path):
    def tree(name):
        root = tmp_path / name
        for d in ("docs", "rtl", "verif", "rundir"):
            (root / d).mkdir(parents=True)
        (root / "prompt.json").write_text(json.dumps({"prompt": "Fix the adder."}))
        (root / "rtl" / "adder.sv").write_text("module adder(input [3:0] a, b, output [4:0] y);\nendmodule\n")
        return root

    _, a, _ = go(tree("a"), [plan_with([]), edit(), decide("submit")])
    _, b, _ = go(tree("b"), [plan_with([]), edit(), decide("submit")], skills=PACK)
    assert user_msg(a.requests[1]).replace(str(tmp_path / "a"), "R") == \
        user_msg(b.requests[1]).replace(str(tmp_path / "b"), "R")
    assert user_msg(b.requests[0]).startswith(user_msg(a.requests[0]).replace(str(tmp_path / "a"),
                                                                               str(tmp_path / "b")))


def test_skills_refused_off_langgraph():
    with pytest.raises(ValueError, match="LangGraph"):
        Config(skills=PACK, harness="deepagents")


# ---------- the CSV columns ----------

def test_csv_columns_for_a_pack_and_blank_without():
    assert collect.FIELDS[-7:] == ["skills_pack", "skills_status", "skills_loaded", "skills_requested",
                                   "skills_unknown", "skills_bytes", "skills_truncated"]
    assert collect.FIELDS[collect.FIELDS.index("skills_pack") - 1] == "spec_final_total"  # after M3d's
    s = {"skills_pack": FROZEN_MANIFEST, "skills_status": "loaded", "skills_loaded": ["spec-reading", "fsm-design"],
         "skills_requested": ["spec-reading", "fsm-design", "x"], "skills_unknown": ["x"], "skills_bytes": 8153,
         "skills_truncated": False}
    got = collect.m3g_columns(s)
    assert got == {"skills_pack": FROZEN_MANIFEST, "skills_status": "loaded", "skills_loaded": "spec-reading+fsm-design",
                   "skills_requested": "spec-reading+fsm-design+x", "skills_unknown": "x", "skills_bytes": 8153,
                   "skills_truncated": 0}
    assert set(collect.m3g_columns({"model": "m"}).values()) == {""}
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=collect.FIELDS)
    w.writeheader()
    w.writerow({**{k: "" for k in collect.FIELDS}, **got})
    assert list(csv.DictReader(io.StringIO(buf.getvalue())))[0]["skills_loaded"] == "spec-reading+fsm-design"


def test_collect_reads_the_skills_from_a_real_summary(task_tree, tmp_path):
    s, _, _ = go(task_tree, [plan_with(["fifo-design"]), edit(), decide("submit")], skills=PACK)
    assert collect.m3g_columns(s)["skills_loaded"] == "fifo-design"
    assert collect.m3g_columns(s)["skills_bytes"] == len(skillpack.Pack(PACK).bodies["fifo-design"].encode())


# ---------- the held-out set ----------

def _row(pid, cat="cid003", out="rtl/x.sv", image="__OSS_SIM_IMAGE__", ctx=None, srcs=None):
    srcs = srcs if srcs is not None else [out]
    return {"id": pid, "categories": [cat, "easy"], "input": {"prompt": "P", "context": ctx or {}},
            "output": {"response": "", "context": {out: "module x; endmodule\n"}},
            "harness": {"files": {"docker-compose.yml": f"services:\n  direct:\n    image: {image}\n",
                                  "src/.env": "VERILOG_SOURCES = " + " ".join(f"/code/{x}" for x in srcs) + "\n",
                                  "src/test_x.py": "secret"}}}


def test_eligibility_rules():
    na = [_row("cvdp_copilot_alpha_0001"), _row("cvdp_copilot_beta_0001", cat="cid007"),
          _row("cvdp_copilot_gamma_0001", image="__VERIF_EDA_IMAGE__"),
          _row("cvdp_copilot_delta_0001", out="verif/tb.sv"),
          _row("cvdp_copilot_eps_0001", srcs=["rtl/other.sv"]),
          _row("cvdp_copilot_lfsr_0009"),
          _row("cvdp_copilot_zeta_0002", ctx={"rtl/a.sv": "module same; endmodule\n"}),
          _row("cvdp_copilot_eta_0001", cat="cid002")]
    ag = [{"id": "cvdp_agentic_lfsr_0001", "context": {"rtl/q.sv": "module same; endmodule\n"}}]
    pool, out = m3g_heldout.eligible(na, ag)
    assert pool == ["cvdp_copilot_alpha_0001", "cvdp_copilot_eta_0001"]
    assert "cvdp_copilot_beta_0001" not in out  # another category is simply not a candidate
    assert out == {"cvdp_copilot_gamma_0001": "not open tools",
                   "cvdp_copilot_delta_0001": "output not an rtl/ file the harness compiles",
                   "cvdp_copilot_eps_0001": "output not an rtl/ file the harness compiles",
                   "cvdp_copilot_lfsr_0009": "design name shared with an agentic problem",
                   "cvdp_copilot_zeta_0002": "a given file identical to an agentic problem's"}


def test_freeze_is_seeded_and_keeps_smoke_problems_out(tmp_path):
    na = [_row(f"cvdp_copilot_d{i:03d}_0001") for i in range(30)]
    (tmp_path / "na.jsonl").write_text("".join(json.dumps(r) + "\n" for r in na))
    (tmp_path / "ag.jsonl").write_text(json.dumps({"id": "cvdp_agentic_other_0001", "context": {}}) + "\n")
    outs = []
    for k in (1, 2):
        ids, smoke = tmp_path / f"ids{k}.txt", tmp_path / f"smoke{k}.txt"
        m3g_heldout.main(["freeze", str(tmp_path / "na.jsonl"), str(tmp_path / "ag.jsonl"), "--revision", "abc",
                          "--seed", "7", "--sample", "10", "--max", "12", "--out", str(ids), "--smoke-out", str(smoke)])
        outs.append((m3g_heldout.read_ids(ids), m3g_heldout.read_ids(smoke)))
    (chosen, smoke), again = outs
    assert outs[0] == again and len(chosen) == 10 and chosen == sorted(chosen) and len(smoke) == 3
    assert not set(chosen) & set(smoke)
    head = open(tmp_path / "ids1.txt").read()
    assert "# revision: abc" in head and "random.Random(7)" in head and "# count: 10" in head


def test_build_adds_the_output_file_to_the_prompt_with_the_harness_transformer(tmp_path):
    cvdp = tmp_path / "cvdp" / "src"
    cvdp.mkdir(parents=True)
    (cvdp / "data_transformer.py").write_text(
        "class DataTransformer:\n"
        "    def transform_datapoint_to_agentic(self, d):\n"
        "        return {'id': d['id'], 'categories': d['categories'], 'prompt': d['input']['prompt'],\n"
        "                'context': d['input']['context'], 'patch': {}, 'harness': d['harness']['files']}\n")
    rows = m3g_heldout.build_rows([_row("cvdp_copilot_alpha_0001")], ["cvdp_copilot_alpha_0001"],
                                  m3g_heldout.transformer(str(tmp_path / "cvdp")))
    assert rows[0]["prompt"].startswith("P\n\nWrite your answer to `rtl/x.sv`:") and rows[0]["id"].startswith(
        "cvdp_copilot_")
    with pytest.raises(SystemExit, match="not in the dataset"):
        m3g_heldout.build_rows([], ["cvdp_copilot_nope_0001"], None)


def test_the_frozen_set_file():
    ids = m3g_heldout.read_ids(os.path.join(ROOT, "tools", "m3g_heldout_ids.txt"))
    smoke = m3g_heldout.read_ids(os.path.join(ROOT, "tools", "m3g_smoke_ids.txt"))
    head = [ln for ln in open(os.path.join(ROOT, "tools", "m3g_heldout_ids.txt")) if ln.startswith("#")]
    assert len(ids) == 100 == len(set(ids)) and ids == sorted(ids) and all(i.startswith("cvdp_copilot_") for i in ids)
    assert len(smoke) == 3 and not set(smoke) & set(ids)
    assert not {m3g_heldout.stem(i) for i in smoke} & {m3g_heldout.stem(i) for i in ids}
    agentic = {m3g_heldout.stem(x) for x in open(os.path.join(ROOT, "tools", "m3b_eval_ids.txt")) if x.strip()
               and not x.startswith("#")}
    assert not {m3g_heldout.stem(i) for i in ids} & agentic
    assert any("revision: 5b807d945f6a99aa645f7e43a64a2115e281b4bf" in h for h in head)
    assert any("cbcd81295561ebb16e4d857e096f4d9908d042c33aff3b58abf236e868411857" in h for h in head)


# ---------- the sweep's new inputs ----------

RECORDING_HARNESS = r'''#!/usr/bin/env python3
"""Records its argv, mounts and env names, and writes an empty-test raw_result.json. No agent, no Docker."""
import json, os, sys
p = sys.argv[sys.argv.index("-p") + 1]
f = sys.argv[sys.argv.index("-f") + 1]
json.dump({"argv": sys.argv[1:], "mounts": os.environ["CVDP_AGENT_MOUNTS"], "env": os.environ["CVDP_AGENT_ENV"],
           "skills": os.environ.get("CVDP_SKILLS"), "ids": [json.loads(l)["id"] for l in open(f) if l.strip()]},
          open(os.environ["SEEN"], "w"))
os.makedirs(p, exist_ok=True)
json.dump({}, open(os.path.join(p, "raw_result.json"), "w"))
'''


def sweep(tmp_path, **kw):
    cvdp = tmp_path / "cvdp"
    cvdp.mkdir(exist_ok=True)
    (cvdp / "run_benchmark.py").write_text(RECORDING_HARNESS)
    (cvdp / "run_benchmark.py").chmod(0o755)
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    (data / "agentic_code_generation_no_commercial.jsonl").write_text(
        json.dumps({"id": "cvdp_agentic_lfsr_0001", "categories": ["cid016", "easy"]}) + "\n")
    (data / "m3g_smoke_agentic.jsonl").write_text(
        json.dumps({"id": "cvdp_copilot_x_0001", "categories": ["cid003", "easy"]}) + "\n")
    env = dict(os.environ, MODEL="fake", THREADS="1", WORK=str(tmp_path / "work"), CVDP_DIR=str(cvdp),
               DATA_DIR=str(data), AGENT_IMAGE="unused", SEEN=str(tmp_path / "seen.json"), OPENROUTER_API_KEY="",
               **kw)
    r = subprocess.run(["bash", os.path.join(ROOT, "tools", "sweep.sh"), "run"], env=env, capture_output=True,
                       text=True, timeout=120, cwd=ROOT)
    return r, (json.load(open(tmp_path / "seen.json")) if r.returncode == 0 else None)


def test_sweep_default_passes_no_pack_and_no_force_flag(tmp_path):
    r, seen = sweep(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "--force-agentic" not in seen["argv"] and seen["skills"] is None and "CVDP_SKILLS" not in seen["env"]
    assert "/skills/" not in seen["mounts"]
    run_json = json.load(open(str(tmp_path / "work") + ".run.json"))
    assert "skills" not in run_json and "split" not in run_json


def test_sweep_mounts_the_pack_read_only_and_runs_the_heldout_format(tmp_path):
    rel = os.path.relpath(PACK, ROOT)
    r, seen = sweep(tmp_path, SKILLS=rel, SPLIT="m3g_smoke")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "--force-agentic" in seen["argv"] and seen["ids"] == ["cvdp_copilot_x_0001"]
    specs = [x.split(":") for x in seen["mounts"].split(";") if x.strip()]
    assert [x[1] for x in specs] == ["/ledger", "/skills/rtl_pack"] and specs[1][2] == "ro"
    assert os.path.samefile(specs[1][0], PACK)
    assert seen["skills"] == "/skills/rtl_pack" and seen["env"].endswith(",CVDP_SKILLS")
    run_json = json.load(open(str(tmp_path / "work") + ".run.json"))
    assert (run_json["skills"], run_json["split"]) == (rel, "m3g_smoke")


@pytest.mark.parametrize("kw,msg", [({"SKILLS": "nope"}, "MANIFEST"), ({"SKILLS": "a;b"}, "SKILLS must"),
                                    ({"SKILLS": "agent/cvdp_agent/skills/rtl_pack", "HARNESS": "deepagents"},
                                     "LangGraph")])
def test_sweep_refuses_bad_skills(tmp_path, kw, msg):
    r, _ = sweep(tmp_path, **kw)
    assert r.returncode == 2 and msg in r.stderr, r.stderr
