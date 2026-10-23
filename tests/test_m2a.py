"""M2a: the reasoning setting, the retry after an empty reply, the reflect-parse retry, seeds, and the model list
tool. The OpenRouter client is exercised against a mock HTTP transport, never the network. No test needs an LLM."""
import csv
import json
import os
import subprocess
import sys

import httpx
import pytest

from cvdp_agent import config as config_mod
from cvdp_agent import prompts
from cvdp_agent.llm import LOWER, REASONING, FakeLLM, OpenRouterLLM, ReasoningRejected, reasoning_body
from cvdp_agent.parse import empty_reply
from conftest import FakeChecker
from test_graph import PLAN, GOOD, decide, edit, rtl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAKE_KEY = "sk-or-v1-feedfacefeedfacefeedfacefeedface0123"
EXPECTED_BODY = {"default": None, "low": {"effort": "low", "exclude": True},
                 "medium": {"effort": "medium", "exclude": True}, "high": {"effort": "high", "exclude": True},
                 "off": {"effort": "none", "exclude": True}}
DEEPSEEK_MARKUP = ("<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>function<｜tool▁sep｜>submit\n```json\n{}\n```"
                   "<｜tool▁call▁end｜><｜tool▁calls▁end｜>")


def events(cfg):
    return [json.loads(x) for x in open(os.path.join(cfg.agent_out, "trace.jsonl"))]


def llm_events(cfg):
    return [e for e in events(cfg) if e["kind"] == "llm"]


def assert_no_key(cfg):
    for dirpath, _, files in os.walk(cfg.agent_out):
        for fn in files:
            assert FAKE_KEY not in open(os.path.join(dirpath, fn), errors="replace").read(), fn


@pytest.fixture(autouse=True)
def fake_key(monkeypatch):
    """Every test here runs with a key in the environment, so any path that could leak it into a trace would."""
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_KEY)


# ---------- reasoning setting ----------

@pytest.mark.parametrize("level", REASONING)
def test_each_reasoning_setting_reaches_the_request(make_cfg, run_agent, level):
    cfg = make_cfg(reasoning=level)
    s, llm, _ = run_agent(cfg, [PLAN, edit(), decide("submit")])
    assert s["stop_reason"] == "submit"
    assert [r["body"]["reasoning"] for r in llm.requests] == [EXPECTED_BODY[level]] * 3
    assert s["reasoning"] == s["reasoning_used"] == level and s["switches"]["reasoning"] == level
    assert {e["reasoning"] for e in llm_events(cfg)} == {level}


def test_reasoning_from_env(monkeypatch):
    monkeypatch.setenv("CVDP_REASONING", "HIGH")
    monkeypatch.setenv("CVDP_SEED", "3")
    c = config_mod.from_env()
    assert (c.reasoning, c.seed) == ("high", "3")
    monkeypatch.delenv("CVDP_REASONING")
    assert config_mod.from_env().reasoning == "default"
    monkeypatch.setenv("CVDP_REASONING", "extreme")
    with pytest.raises(ValueError):
        config_mod.from_env()


def test_model_that_rejects_reasoning_falls_back_without_failing(make_cfg, task_tree, clock):
    from cvdp_agent.graph import run

    cfg = make_cfg(reasoning="low")
    llm = FakeLLM([{"text": PLAN, "cost": 0.001}, {"text": edit(), "cost": 0.002},
                   {"text": decide("submit"), "cost": 0.003}], clock=clock, rejects_reasoning=True)
    s = run(cfg, llm=llm, checker=FakeChecker(cfg.root), tools={}, clock=clock)
    assert s["stop_reason"] == "submit" and rtl(task_tree) == GOOD
    assert s["reasoning"] == "low" and s["reasoning_used"] == "default" and s["reasoning_rejected"] == 1
    # the first request carried the field and was refused; every later one is sent without it
    assert [r["body"]["reasoning"] for r in llm.requests] == [EXPECTED_BODY["low"], None, None, None]
    assert llm.calls == ["plan", "edit", "reflect"]
    rejected = [e for e in llm_events(cfg) if e.get("reasoning_rejected")]
    assert len(rejected) == 1 and rejected[0]["fallback"] == "default" and rejected[0]["node"] == "plan"
    assert s["cost_usd"] == pytest.approx(0.006) and s["cost_unreported_calls"] == 0
    assert_no_key(cfg)


# ---------- the OpenRouter client against a mock transport ----------

def _completion(content, reasoning_tokens=None, finish="stop"):
    usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150, "cost": 0.0012}
    if reasoning_tokens is not None:
        usage["completion_tokens_details"] = {"reasoning_tokens": reasoning_tokens}
    return {"id": "gen-test", "object": "chat.completion", "created": 1, "model": "test/model",
            "choices": [{"index": 0, "finish_reason": finish,
                         "message": {"role": "assistant", "content": content, "reasoning": "hidden thoughts"}}],
            "usage": usage}


class MockOpenRouter:
    """Records every request body; replies from a script. With `reject`, a request with a reasoning field gets
    HTTP 400, and the error echoes the request's Authorization header (so a leak would show in the trace)."""

    def __init__(self, replies, reject=False):
        self.replies = list(replies)
        self.bodies = []
        self.reject = reject

    def __call__(self, request):
        body = json.loads(request.content)
        self.bodies.append(body)
        if self.reject and "reasoning" in body:
            return httpx.Response(400, json={"error": {"message": "reasoning is not supported for this model; "
                                                       f"request had {request.headers.get('authorization')}",
                                                       "code": 400}})
        return httpx.Response(200, json=self.replies.pop(0))

    def client(self):
        return OpenRouterLLM("test/model", http_client=httpx.Client(transport=httpx.MockTransport(self)))


@pytest.mark.parametrize("level", REASONING)
def test_openrouter_request_body_and_reasoning_tokens(level):
    mock = MockOpenRouter([_completion("the answer", reasoning_tokens=37)])
    r = mock.client().invoke("plan", [{"role": "user", "content": "q"}], max_tokens=4000, reasoning=level)
    body = mock.bodies[0]
    assert body.get("reasoning") == EXPECTED_BODY[level]
    assert body["usage"] == {"include": True}  # still asked for usage when the call binds its own extra_body
    assert r.text == "the answer"              # the reasoning text is not part of the reply
    assert (r.reasoning_tokens, r.cost, r.finish_reason) == (37, 0.0012, "stop")


def test_openrouter_rejection_becomes_reasoning_rejected():
    mock = MockOpenRouter([], reject=True)
    with pytest.raises(ReasoningRejected):
        mock.client().invoke("plan", [{"role": "user", "content": "q"}], reasoning="low")


def test_whole_agent_on_mock_openrouter_rejecting_reasoning(make_cfg, task_tree):
    """The real client, the real graph: the model refuses the field, the problem goes on at default, the reasoning
    tokens OpenRouter reports are summed, and the key (echoed in the 400) never reaches the trace."""
    from cvdp_agent.graph import run

    mock = MockOpenRouter([_completion(PLAN, 10), _completion(edit(), 20), _completion(decide("submit"), 5)],
                          reject=True)
    cfg = make_cfg(provider="openrouter", model="test/model", reasoning="medium")
    s = run(cfg, llm=mock.client(), checker=FakeChecker(cfg.root), tools={})
    assert s["stop_reason"] == "submit" and s["reasoning_used"] == "default" and s["reasoning_rejected"] == 1
    assert ["reasoning" in b for b in mock.bodies] == [True, False, False, False]
    assert s["reasoning_tokens"] == 35
    assert [e.get("reasoning_tokens") for e in llm_events(cfg) if not e.get("reasoning_rejected")] == [10, 20, 5]
    assert "[REDACTED]" in json.dumps([e for e in llm_events(cfg) if e.get("reasoning_rejected")])
    assert_no_key(cfg)


# ---------- empty replies ----------

def test_lower_one_step():
    assert [LOWER[x] for x in ("high", "medium", "default", "low", "off")] == ["medium", "low", "low", "off", "off"]


def test_empty_reply_detection():
    assert empty_reply("plan", "") and empty_reply("edit", "  \n ") and empty_reply("reflect", None)
    assert empty_reply("reflect", DEEPSEEK_MARKUP)          # markup only, and `{}` is no decision
    assert empty_reply("plan", "<tool_call>{\"name\": \"read\"}</tool_call>")
    assert not empty_reply("reflect", DEEPSEEK_MARKUP.replace("{}", '{"decision": "submit"}'))
    assert not empty_reply("edit", f"<tool_call>{edit()}</tool_call>")  # an edit block inside markup is used
    assert not empty_reply("plan", PLAN) and not empty_reply("reflect", "submit")


def test_empty_reply_is_retried_once_lower_and_both_costs_count(make_cfg, run_agent, task_tree):
    cfg = make_cfg(reasoning="low")
    s, llm, _ = run_agent(cfg, [{"text": PLAN, "cost": 0.001},
                                {"text": "", "cost": 0.017, "completion_tokens": 32000, "reasoning_tokens": 32000,
                                 "finish_reason": "length"},
                                {"text": edit(), "cost": 0.002}, {"text": decide("submit"), "cost": 0.001}])
    assert llm.calls == ["plan", "edit", "edit", "reflect"]
    assert s["stop_reason"] == "submit" and rtl(task_tree) == GOOD and s["turns"] == 1
    assert s["cost_usd"] == pytest.approx(0.021)  # the empty call's cost counts
    assert (s["empty_replies"], s["empty_retries"], s["llm_calls"]) == (1, 1, 4)
    assert s["reasoning_tokens"] == 32000
    retry = llm.requests[2]
    assert retry["body"]["reasoning"] == EXPECTED_BODY["off"]             # low, one step lower
    assert retry["messages"][-1]["content"] == prompts.ANSWER_ONLY
    assert llm.requests[3]["body"]["reasoning"] == EXPECTED_BODY["low"]   # the retry's level is for the retry only
    ev = [e for e in llm_events(cfg) if e["node"] == "edit"]
    assert ev[0]["decision"] == "empty" and ev[0]["finish_reason"] == "length" and ev[0]["cost"] == 0.017
    assert ev[1]["retry_of"] == ev[0]["call_id"] and ev[1]["reasoning"] == "off"
    assert_no_key(cfg)


def test_second_empty_reply_ends_the_turn_as_before(make_cfg, run_agent, task_tree):
    cfg = make_cfg(reasoning="high")
    s, llm, checker = run_agent(cfg, [{"text": PLAN, "cost": 0.001}, {"text": "", "cost": 0.01},
                                      {"text": "", "cost": 0.01}, {"text": decide("give_up"), "cost": 0.001}])
    assert llm.calls == ["plan", "edit", "edit", "reflect"]  # no third try
    assert llm.requests[2]["body"]["reasoning"] == EXPECTED_BODY["medium"]
    assert (s["empty_replies"], s["empty_retries"], s["turns"]) == (2, 1, 1)
    assert s["files_changed"] == [] and s["cost_usd"] == pytest.approx(0.022)
    assert len(checker.requests) == 1  # the turn went on: checks ran on the unchanged tree, then reflect
    assert_no_key(cfg)


def test_empty_plan_from_default_reasoning_retries_at_low(make_cfg, run_agent):
    cfg = make_cfg(reasoning="default")
    s, llm, _ = run_agent(cfg, [{"text": DEEPSEEK_MARKUP}, PLAN, edit(), decide("submit")])
    assert llm.calls == ["plan", "plan", "edit", "reflect"]
    assert llm.requests[1]["body"]["reasoning"] == EXPECTED_BODY["low"]
    assert (s["empty_replies"], s["empty_retries"]) == (1, 1)


def test_no_retry_when_the_empty_call_used_the_budget(make_cfg, run_agent):
    s, llm, _ = run_agent(make_cfg(budget_usd=0.05), [{"text": PLAN, "cost": 0.01}, {"text": "", "cost": 0.05}])
    assert llm.calls == ["plan", "edit"] and s["stop_reason"] == "budget"
    assert (s["empty_replies"], s["empty_retries"]) == (1, 0)


def test_empty_retry_whose_lower_level_is_rejected_is_made_at_the_problems_level(make_cfg, task_tree, clock):
    """A model that must reason refuses `off` on the retry: the retry is still made, at the problem's own level,
    and the problem keeps that level (it is not dropped to default)."""
    from cvdp_agent.graph import run

    class RejectsOff(FakeLLM):
        def invoke(self, node, messages, max_tokens=None, timeout=None, reasoning="default", **kw):
            if reasoning == "off":
                self.requests.append({"node": node, "body": {"reasoning": reasoning_body(reasoning)},
                                      "messages": messages})
                raise ReasoningRejected(f"HTTP 400: effort none is not supported (key {FAKE_KEY})")
            return super().invoke(node, messages, max_tokens, timeout, reasoning)

    cfg = make_cfg(reasoning="low")
    llm = RejectsOff([PLAN, {"text": ""}, edit(), decide("submit")], clock=clock)
    s = run(cfg, llm=llm, checker=FakeChecker(cfg.root), tools={}, clock=clock)
    assert s["stop_reason"] == "submit" and s["reasoning_used"] == "low" and s["reasoning_rejected"] == 1
    assert [r["body"]["reasoning"] for r in llm.requests] == [EXPECTED_BODY["low"], EXPECTED_BODY["low"],
                                                             EXPECTED_BODY["off"], EXPECTED_BODY["low"],
                                                             EXPECTED_BODY["low"]]
    rejected = [e for e in llm_events(cfg) if e.get("reasoning_rejected")]
    assert rejected[0]["fallback"] == "low"
    assert_no_key(cfg)


# ---------- reflect replies that cannot be read ----------

def test_unparseable_reflect_is_retried_once_then_submits(make_cfg, run_agent):
    cfg = make_cfg()
    s, llm, _ = run_agent(cfg, [PLAN, edit(), "Looks fine to me.", "Still prose, sorry.", decide("edit_again")])
    assert llm.calls == ["plan", "edit", "reflect", "reflect"]  # one retry, not two
    assert s["stop_reason"] == "submit" and s["reflect_parse_retries"] == 1
    assert llm.requests[3]["messages"][-1]["content"] == prompts.JSON_ONLY
    ev = [e for e in llm_events(cfg) if e["node"] == "reflect"]
    assert ev[0]["decision"] == "unparseable" and ev[1]["retry_of"] == ev[0]["call_id"]
    assert_no_key(cfg)


def test_reflect_retry_that_parses_is_followed(make_cfg, run_agent):
    s, llm, _ = run_agent(make_cfg(), [PLAN, edit(), "Hmm.", decide("edit_again"), edit(), decide("submit")])
    assert llm.calls == ["plan", "edit", "reflect", "reflect", "edit", "reflect"]
    assert s["turns"] == 2 and s["reflect_parse_retries"] == 1 and s["stop_reason"] == "submit"


def test_parseable_reflect_is_not_retried(make_cfg, run_agent):
    s, llm, _ = run_agent(make_cfg(), [PLAN, edit(), "I will submit now.", decide("give_up")])
    assert llm.calls == ["plan", "edit", "reflect"] and s["reflect_parse_retries"] == 0


# ---------- seeds: tools/sweep.sh end to end with a stand-in harness ----------

FAKE_HARNESS = r'''#!/usr/bin/env python3
"""Stands in for the CVDP harness's run_benchmark.py: for each problem, lay out a task tree under the prefix the way
the harness does, run the real agent (fake provider) with the variables CVDP_AGENT_ENV names and the ledger mount,
and write raw_result.json. No Docker."""
import argparse, json, os, subprocess, sys
ap = argparse.ArgumentParser()
ap.add_argument("-f"); ap.add_argument("-l", action="store_true"); ap.add_argument("-g"); ap.add_argument("-p")
ap.add_argument("-t")
a = ap.parse_args()
assert not os.path.exists(os.path.join(a.p, "raw_result.json")), "work dir reused"
host_ledger = os.environ["CVDP_AGENT_MOUNTS"].split(":")[0]
env = {k: os.environ[k] for k in os.environ["CVDP_AGENT_ENV"].split(",") if os.environ.get(k)}
env.update(PATH=os.environ["PATH"], PYTHONPATH=os.environ["AGENT_PYTHONPATH"], CVDP_LEDGER_DIR=host_ledger,
           CVDP_FAKE_SCRIPT=os.environ["FAKE_SCRIPT"])
with open(os.environ["SEEN_ENV"], "a") as f:
    f.write(json.dumps({k: v for k, v in env.items() if k.startswith("CVDP_")}) + "\n")
raw = {}
for ln in open(a.f):
    p = json.loads(ln)
    repo, n = p["id"].rsplit("_", 1)
    root = os.path.join(a.p, repo, "harness", str(int(n)))
    for d in ("rtl", "docs", "verif", "rundir"):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    json.dump({"prompt": "make it"}, open(os.path.join(root, "prompt.json"), "w"))
    subprocess.run([sys.executable, "-m", "cvdp_agent"], env={**env, "CVDP_ROOT": root}, check=True,
                   capture_output=True)
    os.makedirs(os.path.join(a.p, repo, "reports"), exist_ok=True)
    open(os.path.join(a.p, repo, "reports", f"{int(n)}.txt"), "w").write("")
    raw[p["id"]] = {"category": p["categories"][0], "difficulty": p["categories"][1], "agent_status": "completed",
                    "tests": [{"result": 0, "log": f"/x/{repo}/reports/{int(n)}.txt", "execution": 1.0}]}
json.dump(raw, open(os.path.join(a.p, "raw_result.json"), "w"))
'''


def test_three_seeds_three_work_dirs_one_guard(tmp_path):
    cvdp = tmp_path / "cvdp"
    cvdp.mkdir()
    (cvdp / "run_benchmark.py").write_text(FAKE_HARNESS)
    (cvdp / "run_benchmark.py").chmod(0o755)
    data = tmp_path / "data"
    data.mkdir()
    problems = [{"id": "cvdp_agentic_lfsr_0001", "categories": ["cid016", "easy"]},
                {"id": "cvdp_agentic_DES_0003", "categories": ["cid004", "medium"]}]
    (data / "agentic_code_generation_no_commercial.jsonl").write_text(
        "".join(json.dumps(p) + "\n" for p in problems))
    # $0.006 per problem: seed 1 spends 0.012, seed 2 starts under the $0.02 guard and ends at 0.024, so seed 3's
    # agents must stop before their first LLM call. The guard is one ledger across all seeds.
    script = json.dumps([{"text": PLAN, "cost": 0.002}, {"text": edit(), "cost": 0.002},
                         {"text": decide("submit"), "cost": 0.002}])
    work = tmp_path / "work"
    env = dict(os.environ, SEEDS="3", REASONING="medium", MODEL="fake", THREADS="1", RUN_BUDGET_USD="0.02",
               WORK=str(work), CVDP_DIR=str(cvdp), DATA_DIR=str(data), AGENT_IMAGE="unused", RUNNER="test",
               AGENT_PYTHONPATH=os.path.join(ROOT, "agent"), FAKE_SCRIPT=script,
               SEEN_ENV=str(tmp_path / "seen_env.jsonl"),
               IDS=",".join(p["id"] for p in problems))
    r = subprocess.run(["bash", os.path.join(ROOT, "tools", "sweep.sh")], env=env, capture_output=True, text=True,
                       timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    for k in (1, 2, 3):
        assert (work / f"seed{k}" / "raw_result.json").exists()
        assert (work / f"seed{k}" / "cvdp_agentic_lfsr" / "harness" / "1" / "rundir" / "agent_out" /
                "summary.json").exists()
    seen = [json.loads(x) for x in open(tmp_path / "seen_env.jsonl")]
    assert [e["CVDP_SEED"] for e in seen] == ["1", "2", "3"] and {e["CVDP_REASONING"] for e in seen} == {"medium"}
    rows = list(csv.DictReader(open(work / "results.csv")))
    assert sorted(r["seed"] for r in rows) == ["1", "1", "2", "2", "3", "3"]
    assert {r["reasoning"] for r in rows} == {"medium"}
    stops = {(r["seed"], r["id"]): r["stop_reason"] for r in rows}
    assert {stops[("3", p["id"])] for p in problems} == {"run_budget_exhausted"}
    assert {stops[("1", p["id"])] for p in problems} == {"submit"}
    md = (work / "table.md").read_text()
    assert "#### Across seeds" in md
    # labelled with the reasoning setting; every problem passed, so the problem bootstrap is degenerate
    assert "| fake (reasoning medium) | 3 | 2 | 100.0% [100.0–100.0] | 6/6 = 100.0% [100.0, 100.0] | $0.0240 " \
           "| $0.0040 |" in md
    assert {r["label"] for r in rows} == {"fake (reasoning medium)"}
    assert "Run spend (sum of provider-reported cost): $0.0240" in md
    assert "Empty replies: 0 (retried 0); reflect parse retries: 0; reasoning tokens (reported): 0" in md
    assert "Seed 3: 20" in md and "harness wall time" in md  # UTC start and end per seed
    run = json.load(open(str(work) + ".run.json"))
    assert set(run["seed_runs"]) == {"1", "2", "3"} and run["seed_runs"]["1"]["start_utc"].endswith("Z")
    # the smoke check the PR run uses, on the same layout
    sc = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "smoke_check.py"), str(work), "2", "3"],
                        capture_output=True, text=True)
    assert sc.returncode == 0, sc.stdout
    for dirpath, _, files in os.walk(tmp_path):
        for fn in files:
            assert FAKE_KEY not in open(os.path.join(dirpath, fn), errors="replace").read(), fn


def test_seed_table_mean_range_and_pooled():
    import table

    base = {"requested_model": "m", "model": "m", "cid": "cid003", "amba": "0", "wall_time_s": "10",
            "harness_agent_s": "", "prompt_tokens": "1", "completion_tokens": "1", "stop_reason": "submit",
            "cost_unreported_calls": "0", "cost_usd": "0.01", "empty_replies": "1", "empty_retries": "1",
            "reflect_parse_retries": "0"}
    passes = {"1": "1100", "2": "1000", "3": "1110"}  # 2/4, 1/4, 3/4
    rows = [dict(base, id=f"p{i}", seed=s, **{"pass": p[i]}) for s, p in passes.items() for i in range(4)]
    md = table.seeds_table(rows)
    # resampling problems, not problem-seed rows: wider than the Wilson interval on 12 rows ([25.4, 74.6])
    assert "| m | 3 | 4 | 50.0% [25.0–75.0] | 6/12 = 50.0% [16.7, 83.3] | $0.1200 | $0.0200 |" in md
    assert "Empty replies: 12 (retried 12); reflect parse retries: 0;" in table.table(rows)


def test_sweep_rejects_bad_seeds_and_reasoning(tmp_path):
    for k, v in (("SEEDS", "0"), ("SEEDS", "2;rm"), ("REASONING", "max")):
        env = dict(os.environ, WORK=str(tmp_path / "w"), AGENT_IMAGE="x", **{k: v})
        r = subprocess.run(["bash", os.path.join(ROOT, "tools", "sweep.sh")], env=env, capture_output=True,
                           text=True)
        assert r.returncode == 2 and k in r.stderr


# ---------- tools/models.py on a canned model list ----------

def test_models_table():
    import models

    data = [{"id": "a/x", "context_length": 1000000, "pricing": {"prompt": "0.0000001", "completion": "0.0000005"},
             "supported_parameters": ["reasoning", "tools"],
             "reasoning": {"supported_efforts": ["high", "low", "none"], "default_effort": "high",
                           "default_enabled": True}},
            {"id": "b/y", "context_length": 8192, "pricing": {"prompt": "0.000001", "completion": "0.000002",
                                                               "overrides": [{"utc_days": ["saturday", "sunday"],
                                                                              "prompt": "0.0000005",
                                                                              "completion": "0.000001"}]},
             "supported_parameters": ["tools"]}]
    md = models.table(["a/x", "b/y", "c/missing"], data)
    assert "| `a/x` | yes | $0.100 | $0.500 | 1,000,000 | yes (efforts: high, low, none; default high; on by " \
           "default) |  |" in md
    assert "| `b/y` | yes | $1.000 | $2.000 | 8,192 | no | $0.500/$1.000 for weekends |" in md
    assert "| `c/missing` | no |" in md


# ---------- review round 1 ----------

# DeepSeek's DSML tool-call markup as it came back in the live `low` run (run 39936095610)
DSML = ('<｜DSML｜ calls>\n<｜DSML｜ invoke name="bash">\n<｜DSML｜ parameter name="command" string="true">'
        'ls -la /code/rtl</｜DSML｜ parameter>\n</｜DSML｜ invoke>\n</｜DSML｜ calls>')


def test_dsml_markup_is_an_empty_reply():
    for node in ("plan", "edit", "reflect"):
        assert empty_reply(node, DSML), node
    assert empty_reply("reflect", '<｜DSML｜ invoke name="bash">cat rtl/x.sv')            # cut off mid-call
    assert not empty_reply("reflect", DSML + '\n{"decision": "submit", "reason": "ok"}')  # an answer after it


def test_dsml_only_reflect_gets_the_empty_retry_not_the_parse_retry(make_cfg, run_agent):
    cfg = make_cfg(reasoning="low")
    s, llm, _ = run_agent(cfg, [PLAN, edit(), DSML, decide("submit")])
    assert llm.calls == ["plan", "edit", "reflect", "reflect"] and s["stop_reason"] == "submit"
    assert (s["empty_replies"], s["empty_retries"], s["reflect_parse_retries"]) == (1, 1, 0)
    assert llm.requests[3]["body"]["reasoning"] == EXPECTED_BODY["off"]


def test_a_call_past_its_deadline_is_abandoned_and_counted_unreported(make_cfg, task_tree, monkeypatch):
    """Scaled down: a 4 s wall cap. The provider takes 30 s to answer the edit; the call is abandoned at its
    deadline, counted as unreported, and the agent still stops and writes its summary within the cap + finalize."""
    import time

    from cvdp_agent import graph

    monkeypatch.setattr(graph, "MIN_LLM_S", 0.0)
    monkeypatch.setattr(graph, "DEADLINE_MARGIN_S", 0.5)
    cfg = make_cfg(wall_s=4.0, finalize_s=1.0)
    t0 = time.monotonic()
    s = graph.run(cfg, llm=FakeLLM([{"text": PLAN, "cost": 0.001}, {"text": edit(), "real_sleep": 30, "cost": 0.05}]),
                  checker=FakeChecker(cfg.root), tools={})
    took = time.monotonic() - t0
    assert took < cfg.wall_s + cfg.finalize_s + 1.0, took
    assert s["stop_reason"] == "llm_error" and s["cost_unreported_calls"] == 1
    assert s["cost_usd"] == pytest.approx(0.001)  # the abandoned call's cost is not known, so not added
    missed = [e for e in llm_events(cfg) if e.get("deadline_missed")]
    assert len(missed) == 1 and missed[0]["node"] == "edit" and "abandoned" in missed[0]["error"]


def test_the_in_flight_call_is_on_disk_as_unreported_before_it_returns(make_cfg, task_tree, tmp_path):
    from cvdp_agent.graph import ledger_totals, run

    ledger = tmp_path / "ledger"
    ledger.mkdir()
    cfg = make_cfg(ledger_dir=str(ledger), run_budget_usd=5.0, budget_usd=0.10)
    seen = {}

    class Peek(FakeLLM):
        def invoke(self, node, messages, **kw):
            if node == "edit":  # "killed" here: what does the disk say?
                seen["summary"] = json.load(open(os.path.join(cfg.agent_out, "summary.json")))
                seen["ledger"] = ledger_totals(str(ledger))
            return super().invoke(node, messages, **kw)

    s = run(cfg, llm=Peek([{"text": PLAN, "cost": 0.004}, {"text": edit(), "cost": 0.006},
                           {"text": decide("submit"), "cost": 0.001}]), checker=FakeChecker(cfg.root), tools={})
    assert seen["summary"]["stop_reason"] == "killed" and seen["summary"]["in_flight_calls"] == 1
    assert seen["summary"]["cost_unreported_calls"] == 1
    assert seen["ledger"][2] == pytest.approx(0.004 + 0.10)  # the guard charges the in-flight call the budget
    assert s["cost_unreported_calls"] == 0 and s["in_flight_calls"] == 0  # cleared when the call returned


@pytest.mark.parametrize("level,plan_cap,edit_cap", [("off", 4000, 32000), ("low", 12000, 40000),
                                                     ("high", 28000, 56000), ("default", 20000, 48000)])
def test_reasoning_gets_headroom_over_the_answer_cap(make_cfg, run_agent, level, plan_cap, edit_cap):
    _, llm, _ = run_agent(make_cfg(reasoning=level), [PLAN, edit(), decide("submit")])
    assert [r["max_tokens"] for r in llm.requests] == [plan_cap, edit_cap, 2000 + (plan_cap - 4000)]


def test_max_tokens_and_retries_are_cut_to_the_time_left(make_cfg, run_agent):
    # the plan streams 1,000 tokens in 10 s (100/s) and leaves 30 s: the edit may ask for 100 x 28 s x 0.9
    s, llm, _ = run_agent(make_cfg(wall_s=120.0, reasoning="low"),
                          [{"text": PLAN, "completion_tokens": 1000, "latency_s": 10.0, "sleep": 90.0}, edit(),
                           decide("submit")])
    assert llm.requests[0]["max_tokens"] == 12000 and llm.requests[0]["max_retries"] is None
    assert llm.requests[1]["max_tokens"] == int(100 * 28 * 0.9) and llm.requests[1]["max_retries"] == 0


def test_capped_empty_reply_is_traced_once(make_cfg, run_agent):
    cfg = make_cfg(budget_usd=0.05)
    run_agent(cfg, [{"text": PLAN, "cost": 0.01}, {"text": "", "cost": 0.05}])
    ids = [e["call_id"] for e in llm_events(cfg)]
    assert len(ids) == len(set(ids)) == 2
    assert llm_events(cfg)[1]["empty"] is True


def test_errored_empty_retry_counts_unreported_and_leaks_no_key(make_cfg, run_agent):
    """The retry raises an error whose text is long enough to be cut, with the key across the cut: redaction must
    come before truncation, or the key's second half would survive."""
    cfg = make_cfg(reasoning="low")
    msg = "x" * 480 + f" upstream said: Authorization {FAKE_KEY} " + "y" * 600
    s, llm, _ = run_agent(cfg, [PLAN, {"text": "", "cost": 0.01}, {"raise": msg}])
    assert s["stop_reason"] == "llm_error" and s["cost_unreported_calls"] == 1
    assert (s["empty_replies"], s["empty_retries"]) == (1, 1)
    errored = [e for e in llm_events(cfg) if "error" in e]
    assert errored[0]["retry_of"] == 2
    text = open(os.path.join(cfg.agent_out, "trace.jsonl")).read()
    for i in range(0, len(FAKE_KEY) - 12):
        assert FAKE_KEY[i:i + 12] not in text


def test_rejection_event_carries_retry_of(make_cfg, task_tree, clock):
    from cvdp_agent.graph import run

    class RejectsOff(FakeLLM):
        def invoke(self, node, messages, reasoning="default", **kw):
            if reasoning == "off":
                raise ReasoningRejected("HTTP 400: effort none is not supported")
            return super().invoke(node, messages, reasoning=reasoning, **kw)

    cfg = make_cfg(reasoning="low")
    run(cfg, llm=RejectsOff([PLAN, {"text": ""}, edit(), decide("submit")], clock=clock),
        checker=FakeChecker(cfg.root), tools={}, clock=clock)
    rejected = [e for e in llm_events(cfg) if e.get("reasoning_rejected")]
    assert rejected[0]["retry_of"] == 2


def test_openrouter_records_the_serving_provider_and_pins_the_order(make_cfg):
    from cvdp_agent.graph import run

    replies = [dict(_completion(t), provider=p) for t, p in ((PLAN, "Alpha"), (edit(), "Beta"),
                                                              (decide("submit"), "Alpha"))]
    mock = MockOpenRouter(replies)
    llm = OpenRouterLLM("test/model", http_client=httpx.Client(transport=httpx.MockTransport(mock)),
                        provider_order=["Alpha", "Beta"])
    cfg = make_cfg(provider="openrouter", model="test/model", reasoning="off")
    s = run(cfg, llm=llm, checker=FakeChecker(cfg.root), tools={})
    assert all(b["provider"] == {"order": ["Alpha", "Beta"], "allow_fallbacks": False} for b in mock.bodies)
    assert s["providers"] == {"Alpha": 2, "Beta": 1}
    assert [e["provider"] for e in llm_events(cfg)] == ["Alpha", "Beta", "Alpha"]
    assert_no_key(cfg)


def test_provider_order_from_env(monkeypatch):
    monkeypatch.setenv("CVDP_PROVIDER_ORDER", "DeepInfra, Novita")
    assert config_mod.from_env().provider_order == ["DeepInfra", "Novita"]


def test_seed_not_started_when_the_step_cannot_fit_its_worst_case(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "agentic_code_generation_no_commercial.jsonl").write_text(
        json.dumps({"id": "cvdp_agentic_lfsr_0001", "categories": ["cid016", "easy"]}) + "\n")
    work = tmp_path / "work"
    env = dict(os.environ, SEEDS="2", MODEL="fake", THREADS="1", WORK=str(work), CVDP_DIR=str(tmp_path / "nope"),
               DATA_DIR=str(data), AGENT_IMAGE="unused", STEP_BUDGET_S="100", SEED_PROBLEM_WORST_S="60")
    r = subprocess.run(["bash", os.path.join(ROOT, "tools", "sweep.sh")], env=env, capture_output=True, text=True,
                       timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr  # worst case 1 x 60 + 300 = 360 s > 100 s: nothing started
    md = (work / "table.md").read_text()
    assert "**Seed 1: not started**" in md and "**Seed 2: not started**" in md and "360 s" in md
    assert not (work / "seed1").exists()
