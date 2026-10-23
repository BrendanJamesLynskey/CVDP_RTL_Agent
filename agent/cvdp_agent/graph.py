"""The agent graph: read_task -> plan -> edit -> check -> reflect -> (edit | finalize).

Stop rules are checked in code before every step: turn cap, per-problem budget (provider-reported cost), a call
whose cost was not reported, and wall time. On any stop, and on a crash, finalize keeps the best edit so far (the
last one that compiled), writes the summary and the ledger entry, and the process exits 0."""
import json
import os
import time
import uuid
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from . import checks as checks_mod
from . import prompts
from .files import EDIT_ROOTS, TEXT_EXT, FileTool, PathRefused
from .parse import parse_decision, parse_edit, parse_plan
from .trace import Tracer, truncate

MAX_TOKENS = {"plan": 4000, "edit": 32000, "reflect": 2000}
LLM_NODES = ("plan", "edit", "reflect")
MIN_LLM_S = 20.0   # an LLM call is not started with less time than this before the wall cap
# Worst case after the wall cap (480 s): an LLM call started before it ends by then (two attempts of at most half
# the time left each, plus at most 10 s for the cost lookup), checks are cut to the time left, and finalize has
# cfg.finalize_s (30 s): about 520 s in all, under the harness's 600 s kill.


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
                                                     clock=clock, time_left=self.time_left)
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
        self.finished = None    # set once finish() has written the summary
        self.ledger_name = f"{uuid.uuid4().hex}.json"  # one entry per problem, rewritten as the cost grows
        self.last_state = {}

    # ---------- stop rules ----------
    def elapsed(self):
        return self.clock() - self.t0

    def time_left(self):
        return self.cfg.wall_s - self.elapsed()

    def cap(self, state, nxt):
        """The reason to stop instead of running `nxt`, or None."""
        if self.elapsed() >= self.cfg.wall_s:
            return "wall_time"
        if nxt in LLM_NODES and self.time_left() < MIN_LLM_S:
            return "wall_time"
        if nxt in LLM_NODES and self.cost_unreported:
            return "cost_unreported"  # the budget can no longer be enforced from reported cost
        if nxt in LLM_NODES and self.spent >= self.cfg.budget_usd:
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
                                timeout=max(5.0, min(150.0, (remaining - 10) / 2)))
        except Exception as e:  # provider errors end the run; the best edit is still kept
            self.cost_unreported += 1  # an errored or timed-out call may still have been billed
            self.tracer.log("llm", node=node, model=getattr(self.llm, "model", None), turn=state.get("turn", 0),
                            cost=None, error=truncate(f"{type(e).__name__}: {e}", 1000),
                            remaining_s=round(remaining, 1))
            checkpoint(self, state)
            return None
        self.models.add(r.model)
        self.prompt_tokens += r.prompt_tokens or 0
        self.completion_tokens += r.completion_tokens or 0
        if r.cost is None:
            self.cost_unreported += 1
        else:
            self.spent += r.cost
        checkpoint(self, state)
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
            except Exception as ex:  # refused path, bad diff, non-UTF-8 file, I/O: reported to the LLM
                errors.append(f"{item['path']}: {type(ex).__name__}: {ex}")
                rt.tracer.log("tool", check="file_write", command=f"write {item['path']}", exit_code=1,
                              output=str(ex), turn=turn)
        for item in e["tb"]:
            if not cfg.self_check:
                errors.append(f"{item['path']}: testbench ignored (self-check is off)")
                continue
            try:
                if not item["content"].strip():  # an existing testbench under verif/, run as it is
                    full, rel = rt.files.resolve_edit(item["path"])
                    if not rel.startswith("verif/") or not os.path.isfile(full):
                        raise PathRefused(f"{item['path']}: no such testbench under verif/")
                    tb_files.append(rel)
                    tb_top = item["top"] or tb_top
                    continue
                tb_files.append(rt.files.write_tb(item["path"], item["content"]))
                tb_top = item["top"] or tb_top
                rt.tracer.log("tool", check="tb_write", command=f"write {tb_files[-1]}", exit_code=0, turn=turn)
            except Exception as ex:
                errors.append(f"{item['path']}: {type(ex).__name__}: {ex}")
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


def finish(rt, state, error=None):
    """Keep the best edit, write summary.json and the ledger entry. Runs once, also after a crash."""
    if rt.finished:
        return {"stop_reason": rt.finished}
    compiled = state.get("compiled")
    kept = "none"
    try:
        if hasattr(rt.checker, "time_left"):  # finalize has its own small reserve after the wall cap
            deadline = rt.clock() + rt.cfg.finalize_s
            rt.checker.time_left = lambda: deadline - rt.clock()
        if rt.edited and not state.get("checked", True):
            compiled = rt.checker.run([]).get("compile", {}).get("ok")  # edits made after the last check
            if compiled:
                rt.best, rt.best_turn = rt.files.snapshot(), state.get("turn")
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
    except Exception as e:  # keep going: the summary and the ledger entry matter more
        error = error or f"finalize: {type(e).__name__}: {e}"
    stop = "error" if error else (state.get("stop_reason") or rt.stop_reason or "submit")
    summary = make_summary(rt, state, stop, kept, compiled)
    if error:
        summary["error"] = truncate(error, 2000)
    rt.finished = stop
    write_summary(rt, summary)
    rt.tracer.log("summary", **summary)
    return {"stop_reason": stop}


def checkpoint(rt, state):
    """After every LLM call: a provisional summary and ledger entry, so a problem the harness kills (at its agent
    timeout) still shows what it spent. stop_reason "killed" is what is left if finalize never runs."""
    if rt.finished:
        return
    try:
        write_summary(rt, make_summary(rt, state, "killed", None, state.get("compiled")))
    except Exception:
        pass


def write_summary(rt, summary):
    os.makedirs(rt.cfg.agent_out, exist_ok=True)
    tmp = os.path.join(rt.cfg.agent_out, "summary.json.tmp")
    with open(tmp, "w") as f:
        json.dump(summary, f, indent=1)
    os.replace(tmp, os.path.join(rt.cfg.agent_out, "summary.json"))
    write_ledger(rt.cfg, summary, rt.ledger_name)


def make_summary(rt, state, stop, kept, compiled):
    return {
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


def ledger_totals(ledger_dir):
    """(reported cost, calls with unreported cost, guard charge) summed over the run's ledger entries."""
    reported, unreported, charge = 0.0, 0, 0.0
    for fn in os.listdir(ledger_dir):
        if fn.endswith(".json"):
            try:
                with open(os.path.join(ledger_dir, fn)) as f:
                    e = json.load(f)
                c = float(e.get("cost_usd") or 0.0)
                reported += c
                unreported += int(e.get("cost_unreported_calls") or 0)
                charge += float(e.get("guard_charge_usd", c))
            except (OSError, ValueError, TypeError):
                continue
    return reported, unreported, charge


def ledger_total(ledger_dir):
    return ledger_totals(ledger_dir)[0]


def run_budget_exhausted(cfg, tracer):
    """The whole-run guard trips on the guard charge: reported cost, plus the per-problem budget for every call
    whose cost was not reported (a stated ceiling, used by the guard only; reported cost is never estimated)."""
    if not cfg.ledger_dir or cfg.run_budget_usd is None or not os.path.isdir(cfg.ledger_dir):
        return False
    reported, unreported, charge = ledger_totals(cfg.ledger_dir)
    tracer.log("tool", check="run_budget", command="sum ledger", exit_code=0,
               output=f"reported ${reported:.4f}, {unreported} unreported calls, guard charge ${charge:.4f} "
                      f"of ${cfg.run_budget_usd:.4f}")
    return charge >= cfg.run_budget_usd


def write_ledger(cfg, summary, name=None):
    if not cfg.ledger_dir or not os.path.isdir(cfg.ledger_dir):
        return
    reported = summary["cost_usd"] or 0.0
    unreported = summary["cost_unreported_calls"] or 0
    entry = {"cost_usd": summary["cost_usd"], "cost_unreported_calls": unreported,
             "guard_charge_usd": round(reported + unreported * cfg.budget_usd, 8),
             "stop_reason": summary["stop_reason"]}
    try:
        path = os.path.join(cfg.ledger_dir, name or f"{uuid.uuid4().hex}.json")
        with open(path + ".tmp", "w") as f:
            json.dump(entry, f)
        os.replace(path + ".tmp", path)
    except OSError:
        pass


def run(cfg, llm=None, **kw):
    from . import llm as llm_mod

    tracer = kw.pop("tracer", None) or Tracer(cfg.agent_out)
    rt = Runtime(cfg, llm or llm_mod.make(cfg), tracer=tracer, **kw)
    graph = build(rt)
    state = {}
    try:
        for state in graph.stream({}, {"recursion_limit": 10 * cfg.max_turns + 20}, stream_mode="values"):
            pass
    except Exception as e:
        import traceback

        rt.tracer.log("error", error=truncate(f"{type(e).__name__}: {e}\n{traceback.format_exc()}", 4000))
        finish(rt, state, error=f"{type(e).__name__}: {e}")
    finally:
        finish(rt, state)  # a no-op when finalize already ran
    with open(os.path.join(cfg.agent_out, "summary.json")) as f:
        return json.load(f)


def mermaid():
    """The compiled graph as mermaid, for the README (and its drift test)."""
    from .config import Config
    from .llm import FakeLLM

    rt = Runtime(Config(root="/nonexistent", out_dir=""), FakeLLM(), tracer=Tracer(None), tools={})
    return build(rt).get_graph().draw_mermaid()
