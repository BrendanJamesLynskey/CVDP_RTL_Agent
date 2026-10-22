"""The agent graph: read_task -> plan -> edit -> check -> reflect -> (edit | finalize).

Stop rules are checked in code before every step: turn cap, per-problem budget (provider-reported cost) and wall
time. On any stop, finalize keeps the best edit so far (the last one that compiled) and the process exits 0."""
import json
import os
import time
import uuid
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from . import checks as checks_mod
from . import prompts
from .files import EDIT_ROOTS, TEXT_EXT, DiffError, FileTool, PathRefused
from .parse import parse_decision, parse_edit, parse_plan
from .trace import Tracer, truncate

MAX_TOKENS = {"plan": 4000, "edit": 32000, "reflect": 2000}


class State(TypedDict, total=False):
    task: str
    listing: list
    plan: dict
    turn: int
    changed: list
    edit_errors: list
    tb: dict
    requested: list
    results: dict
    compiled: object  # True / False / None (not checked or no compiler)
    checked: bool
    decision: str
    reason: str
    stop_reason: str


class Runtime:
    """What the nodes share that is not graph state: settings, the LLM, the tools, and the running totals."""

    def __init__(self, cfg, llm, tracer=None, checker=None, tools=None, clock=time.monotonic):
        self.cfg = cfg
        self.llm = llm
        self.clock = clock
        self.t0 = clock()
        self.tracer = tracer or Tracer(cfg.agent_out)
        self.files = FileTool(cfg.root)
        self.tools = tools if tools is not None else checks_mod.detect_tools()
        self.checker = checker or checks_mod.Checker(cfg.root, self.tracer, self.tools, cfg.tool_timeout_s,
                                                     clock=clock)
        self.spent = 0.0
        self.cost_unreported = 0
        self.llm_calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.models = set()
        self.best = None        # snapshot of rtl/verif/docs after the last edit that compiled
        self.best_turn = None
        self.stop_reason = None
        self.edited = False
        self.changed_all = set()

    # ---------- stop rules ----------
    def elapsed(self):
        return self.clock() - self.t0

    def cap(self, state, nxt):
        """The reason to stop instead of running `nxt`, or None."""
        if self.elapsed() >= self.cfg.wall_s:
            return "wall_time"
        if nxt in ("plan", "edit", "reflect") and self.spent >= self.cfg.budget_usd:
            return "budget"
        if nxt == "edit" and state.get("turn", 0) >= self.cfg.max_turns:
            return "max_turns"
        return None

    def go(self, state, nxt):
        reason = self.cap(state, nxt)
        if reason:
            self.stop_reason = reason
            return "finalize"
        return nxt

    # ---------- LLM ----------
    def call(self, node, messages, state):
        remaining = self.cfg.wall_s - self.elapsed()
        self.llm_calls += 1
        try:
            r = self.llm.invoke(node, messages, max_tokens=MAX_TOKENS.get(node),
                                timeout=max(15.0, min(150.0, (remaining - 10) / 2)))
        except Exception as e:  # provider errors end the run; the best edit is still kept
            self.tracer.log("llm", node=node, model=getattr(self.llm, "model", None), turn=state.get("turn", 0),
                            error=truncate(f"{type(e).__name__}: {e}", 1000), remaining_s=round(remaining, 1))
            return None
        self.models.add(r.model)
        self.prompt_tokens += r.prompt_tokens or 0
        self.completion_tokens += r.completion_tokens or 0
        if r.cost is None:
            self.cost_unreported += 1
        else:
            self.spent += r.cost
        return r

    def log_llm(self, node, r, state, decision):
        self.tracer.log("llm", node=node, model=r.model, turn=state.get("turn", 0), prompt_tokens=r.prompt_tokens,
                        completion_tokens=r.completion_tokens, cost=r.cost, latency_s=round(r.latency_s, 3),
                        generation_id=r.generation_id, decision=decision, completion=truncate(r.text, 3000))

    # ---------- context ----------
    def contents(self):
        parts, total = [], 0
        ordered = sorted(self.files.list_files(),
                         key=lambda p: ({"rtl": 0, "docs": 1, "verif": 2}.get(p.split("/")[0], 9), p))
        for rel in ordered:
            if rel.split("/")[0] not in EDIT_ROOTS or os.path.splitext(rel)[1] not in TEXT_EXT:
                continue
            try:
                text = self.files.read(rel)
            except OSError:
                continue
            text = truncate(text, 30000)
            if total + len(text) > self.cfg.max_context_chars:
                parts.append(f"=== {rel} === (not shown: context limit)")
                continue
            total += len(text)
            parts.append(f"=== {rel} ===\n{text}")
        return "\n\n".join(parts) or "(no files)"


def build(rt):
    cfg = rt.cfg

    def read_task(state):
        path = os.path.join(cfg.root, "prompt.json")
        try:
            with open(path) as f:
                task = json.load(f).get("prompt", "")
        except (OSError, json.JSONDecodeError) as e:
            rt.tracer.log("tool", check="read_task", command=f"read {path}", exit_code=1, output=str(e))
            return {"task": "", "stop_reason": "no_task", "turn": 0}
        listing = rt.files.list_files()
        rt.tracer.log("tool", check="read_task", command="list /code", exit_code=0,
                      output=truncate("\n".join(listing), 3000), tools=rt.tools)
        out = {"task": task, "listing": listing, "turn": 0}
        if run_budget_exhausted(cfg, rt.tracer):
            out["stop_reason"] = "run_budget_exhausted"
        return out

    def plan(state):
        msg = prompts.PLAN.format(
            task=state["task"], listing="\n".join(state["listing"]), contents=rt.contents(),
            tools=", ".join(k for k, v in rt.tools.items() if v) or "none",
            check_options=prompts.check_options(cfg, rt.tools))
        r = rt.call("plan", [{"role": "system", "content": prompts.SYSTEM}, {"role": "user", "content": msg}], state)
        if r is None:
            return {"stop_reason": "llm_error"}
        p = parse_plan(r.text)
        rt.log_llm("plan", r, state, decision="plan")
        return {"plan": p}

    def edit(state):
        turn = state.get("turn", 0) + 1
        feedback = ""
        if state.get("results"):
            errs = "".join(f"edit error: {e}\n" for e in state.get("edit_errors", []))
            feedback = prompts.FEEDBACK.format(turn=turn - 1, edit_errors=errs,
                                               results=checks_mod.render(state["results"]),
                                               reason=state.get("reason", ""))
        msg = prompts.EDIT.format(
            task=state["task"], plan=json.dumps(state.get("plan", {}), indent=1), contents=rt.contents(),
            feedback=feedback, tb_instructions=prompts.TB_ON if cfg.self_check else prompts.TB_OFF,
            check_options=prompts.check_options(cfg, rt.tools))
        r = rt.call("edit", [{"role": "system", "content": prompts.SYSTEM}, {"role": "user", "content": msg}],
                    {**state, "turn": turn})
        if r is None:
            return {"turn": turn, "stop_reason": "llm_error"}
        e = parse_edit(r.text)
        changed, errors, tb_files, tb_top = [], [], [], ""
        for item in e["files"] + e["diffs"]:
            try:
                if "diff" in item:
                    rel = rt.files.apply_diff(item["path"], item["diff"])
                else:
                    rel = rt.files.write(item["path"], item["content"])
                changed.append(rel)
                rt.tracer.log("tool", check="file_write", command=f"write {rel}", exit_code=0, turn=turn)
            except (PathRefused, DiffError, OSError) as ex:
                errors.append(f"{item['path']}: {ex}")
                rt.tracer.log("tool", check="file_write", command=f"write {item['path']}", exit_code=1,
                              output=str(ex), turn=turn)
        for item in e["tb"]:
            if not cfg.self_check:
                errors.append(f"{item['path']}: testbench ignored (self-check is off)")
                continue
            try:
                tb_files.append(rt.files.write_tb(item["path"], item["content"]))
                tb_top = item["top"] or tb_top
                rt.tracer.log("tool", check="tb_write", command=f"write {tb_files[-1]}", exit_code=0, turn=turn)
            except (PathRefused, OSError) as ex:
                errors.append(f"{item['path']}: {ex}")
                rt.tracer.log("tool", check="tb_write", command=f"write {item['path']}", exit_code=1,
                              output=str(ex), turn=turn)
        rt.edited = rt.edited or bool(changed)
        rt.changed_all.update(changed)
        requested = [c for c in e["checks"] if allowed_check(c, cfg)]
        tb = {"files": tb_files, "top": tb_top} if tb_files else (state.get("tb") if cfg.self_check else None)
        rt.log_llm("edit", r, {"turn": turn}, decision={"changed": changed, "errors": len(errors),
                                                        "checks": requested, "testbench": tb_files})
        return {"turn": turn, "changed": changed, "edit_errors": errors, "requested": requested, "tb": tb,
                "checked": False}

    def check(state):
        results = rt.checker.run(state.get("requested", []), state.get("tb"))
        compiled = results.get("compile", {}).get("ok")
        if compiled:
            rt.best = rt.files.snapshot()
            rt.best_turn = state.get("turn")
        return {"results": results, "compiled": compiled, "checked": True}

    def reflect(state):
        changed = ", ".join(state.get("changed", [])) or "nothing"
        changed += "".join(f"\nedit error: {x}" for x in state.get("edit_errors", []))
        msg = prompts.REFLECT.format(
            task=truncate(state["task"], 6000), plan=json.dumps(state.get("plan", {}), indent=1),
            changed=changed,
            results=checks_mod.render(state.get("results", {})), turn=state.get("turn", 0),
            max_turns=cfg.max_turns, spent=rt.spent, budget=cfg.budget_usd)
        r = rt.call("reflect", [{"role": "system", "content": prompts.SYSTEM}, {"role": "user", "content": msg}],
                    state)
        if r is None:
            return {"stop_reason": "llm_error"}
        d = parse_decision(r.text)
        rt.log_llm("reflect", r, state, decision=d["decision"])
        out = {"decision": d["decision"], "reason": d["reason"]}
        if d["decision"] in ("submit", "give_up"):
            out["stop_reason"] = d["decision"]
        return out

    def finalize(state):
        return finish(rt, state)

    g = StateGraph(State)
    for name, fn in (("read_task", read_task), ("plan", plan), ("edit", edit), ("check", check),
                     ("reflect", reflect), ("finalize", finalize)):
        g.add_node(name, fn)
    g.add_edge(START, "read_task")
    g.add_conditional_edges("read_task", lambda s: "finalize" if s.get("stop_reason") else rt.go(s, "plan"),
                            ["plan", "finalize"])
    g.add_conditional_edges("plan", lambda s: "finalize" if s.get("stop_reason") else rt.go(s, "edit"),
                            ["edit", "finalize"])
    g.add_conditional_edges("edit", lambda s: "finalize" if s.get("stop_reason") else rt.go(s, "check"),
                            ["check", "finalize"])
    g.add_conditional_edges("check", lambda s: rt.go(s, "reflect"), ["reflect", "finalize"])
    g.add_conditional_edges("reflect", lambda s: "finalize" if s.get("stop_reason") else rt.go(s, "edit"),
                            ["edit", "finalize"])
    g.add_edge("finalize", END)
    return g.compile()


def allowed_check(name, cfg):
    if name not in checks_mod.CHECKS:
        return False
    if name in ("lint", "synth") and not cfg.lint:
        return False
    if name == "testbench" and not cfg.self_check:
        return False
    return True


def finish(rt, state):
    """Keep the best edit, write summary.json and the ledger entry."""
    compiled = state.get("compiled")
    if rt.edited and not state.get("checked", True):
        compiled = rt.checker.run([]).get("compile", {}).get("ok")  # edits made after the last check
        if compiled:
            rt.best, rt.best_turn = rt.files.snapshot(), state.get("turn")
    kept = "none"
    if rt.edited:
        kept = "last"
        if compiled is False and rt.best is not None:
            rt.files.restore(rt.best)
            kept = f"best_compiled_turn_{rt.best_turn}"
            rt.tracer.log("tool", check="keep_best", command=f"restore turn {rt.best_turn}", exit_code=0)
    for f in ("compile.vvp", "tb.vvp"):
        p = os.path.join(rt.checker.tb_dir, f) if hasattr(rt.checker, "tb_dir") else None
        if p and os.path.exists(p):
            os.remove(p)
    stop = state.get("stop_reason") or rt.stop_reason or "submit"
    summary = {
        "provider": rt.cfg.provider,
        "model": sorted(rt.models)[0] if len(rt.models) == 1 else (sorted(rt.models) or rt.cfg.model or None),
        "requested_model": rt.cfg.model or None,
        "turns": state.get("turn", 0),
        "llm_calls": rt.llm_calls,
        "tool_calls": getattr(rt.checker, "calls", 0),
        "prompt_tokens": rt.prompt_tokens,
        "completion_tokens": rt.completion_tokens,
        "cost_usd": round(rt.spent, 8) if rt.llm_calls - rt.cost_unreported > 0 else (None if rt.llm_calls else 0.0),
        "cost_unreported_calls": rt.cost_unreported,
        "wall_time_s": round(rt.elapsed(), 2),
        "stop_reason": stop,
        "decision": state.get("decision"),
        "kept": kept,
        "final_compiled": compiled,
        "files_changed": sorted(rt.changed_all),
        "switches": rt.cfg.switches(),
        "tools": rt.tools,
        "agent_version": os.environ.get("CVDP_AGENT_VERSION", "dev"),
    }
    os.makedirs(rt.cfg.agent_out, exist_ok=True)
    with open(os.path.join(rt.cfg.agent_out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    write_ledger(rt.cfg, summary)
    rt.tracer.log("summary", **summary)
    return {"stop_reason": stop}


def ledger_total(ledger_dir):
    total = 0.0
    for fn in os.listdir(ledger_dir):
        if fn.endswith(".json"):
            try:
                with open(os.path.join(ledger_dir, fn)) as f:
                    total += float(json.load(f).get("cost_usd") or 0.0)
            except (OSError, ValueError):
                continue
    return total


def run_budget_exhausted(cfg, tracer):
    if not cfg.ledger_dir or cfg.run_budget_usd is None or not os.path.isdir(cfg.ledger_dir):
        return False
    total = ledger_total(cfg.ledger_dir)
    tracer.log("tool", check="run_budget", command="sum ledger", exit_code=0,
               output=f"run spend so far ${total:.4f} of ${cfg.run_budget_usd:.4f}")
    return total >= cfg.run_budget_usd


def write_ledger(cfg, summary):
    if not cfg.ledger_dir or not os.path.isdir(cfg.ledger_dir):
        return
    try:
        with open(os.path.join(cfg.ledger_dir, f"{uuid.uuid4().hex}.json"), "w") as f:
            json.dump({"cost_usd": summary["cost_usd"], "stop_reason": summary["stop_reason"]}, f)
    except OSError:
        pass


def run(cfg, llm=None, **kw):
    from . import llm as llm_mod

    tracer = kw.pop("tracer", None) or Tracer(cfg.agent_out)
    rt = Runtime(cfg, llm or llm_mod.make(cfg), tracer=tracer, **kw)
    graph = build(rt)
    graph.invoke({}, {"recursion_limit": 10 * cfg.max_turns + 20})
    with open(os.path.join(cfg.agent_out, "summary.json")) as f:
        return json.load(f)


def mermaid():
    """The compiled graph as mermaid, for the README (and its drift test)."""
    from .config import Config
    from .llm import FakeLLM

    rt = Runtime(Config(root="/nonexistent", out_dir=""), FakeLLM(), tracer=Tracer(None), tools={})
    return build(rt).get_graph().draw_mermaid()
