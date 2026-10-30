"""The agent graph: read_task -> plan -> edit -> check -> reflect -> (edit | finalize).

M3d adds two more, each behind its own switch: `verify` between a submit and finalize (verify_submit: a submit is
refused until the design as it stands has passed a simulation of a testbench), and `spec` between read_task and
plan (spec_vectors: a blind LLM call writes reference cases from the specification, which verify then applies too).

M3c adds two fixed steps, each only when its switch is on: `interface` between edit and check (interface_check:
the design's interface by elaboration against the given one, shown to reflect like lint), and `gate` between a
submit and finalize (mutation_gate: the agent's own testbench must kill half of 12 mutants of its design).

Stop rules are checked in code before every step: turn cap, per-problem budget (provider-reported cost), a call
whose cost was not reported, and wall time. On any stop, and on a crash, finalize keeps the best edit so far (the
last one that compiled), writes the summary and the ledger entry, and the process exits 0."""
import json
import os
import threading
import time
import uuid
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from . import checks as checks_mod
from . import prompts
from .files import EDIT_ROOTS, TEXT_EXT, FileTool, PathRefused
from .llm import LOWER, ReasoningRejected
from .parse import empty_reply, parse_decision, parse_edit, parse_plan
from .trace import Tracer, redact, truncate

MAX_TOKENS = {"plan": 4000, "edit": 32000, "reflect": 2000, "agent": 32000, "spec": 12000}  # room for the answer itself
# Room for reasoning on top of the answer's. Reasoning tokens count against max_tokens (with exclude: true too), so
# without this a model that reasons at length fills the cap and returns an empty reply (finish_reason: length).
REASONING_HEADROOM = {"off": 0, "low": 8000, "medium": 16000, "high": 24000, "default": 16000}
LLM_NODES = ("plan", "edit", "reflect", "spec")  # spec: M3d, only in the graph with spec_vectors on
MIN_LLM_S = 20.0          # an LLM call is not started with less time than this before the wall cap
DEADLINE_MARGIN_S = 2.0   # every call (its cost lookup included) must be back this long before the wall cap
SHORT_CALL_S = 60.0       # a call with less time than this gets no client-side retry
MIN_MAX_TOKENS = 512      # the throughput clamp never cuts max_tokens below this
# Worst case after the wall cap (480 s): every LLM call has a hard deadline DEADLINE_MARGIN_S before it and is
# abandoned there (counted as cost unreported); checks are cut to the time left; finalize has cfg.finalize_s
# (30 s): about 510 s in all, under the harness's 600 s kill.


class CallDeadline(TimeoutError):
    """An LLM call did not return by its deadline and was abandoned. It may still be billed."""


def run_with_deadline(fn, seconds):
    """fn() in a daemon thread; its result, or CallDeadline if it has not returned within `seconds`. The thread is
    left behind (it cannot be killed), so it must not touch shared state; it never does here."""
    box = {}

    def work():
        try:
            box["r"] = fn()
        except BaseException as e:  # handed to the caller
            box["e"] = e

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(seconds)
    if t.is_alive():
        raise CallDeadline(f"no reply within {seconds:.1f} s; call abandoned")
    if "e" in box:
        raise box["e"]
    return box["r"]


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
    interface: dict  # M3c: the last interface check's result


class Runtime:
    """What the nodes share that is not graph state: settings, the LLM, the tools, and the running totals."""

    def __init__(self, cfg, llm, tracer=None, checker=None, tools=None, clock=time.monotonic, role_llms=None):
        self.cfg = cfg
        self.llm = llm
        # M3f: a client per role given its own model ({} for the default agent: every call goes to `llm`)
        if role_llms is None:
            from .llm import make_role

            role_llms = {node: make_role(cfg, m, llm) for node, m in cfg.role_models().items()}
        self.role_llms = role_llms
        self.role_reasoning = cfg.role_reasoning or cfg.reasoning  # the roles' level, with its own fallback
        self.role_spent = 0.0    # provider-reported cost of the role calls, kept apart from the edit loop's budget
        self.role_calls = 0
        self.cost_by_model = {}  # model -> provider-reported cost (summary field only with roles set)
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
        self.reasoning = cfg.reasoning  # falls back to "default" for the rest of the problem if the model refuses it
        self.reasoning_rejected = 0
        self.reasoning_tokens = 0
        self.empty_replies = 0
        self.empty_retries = 0
        self.reflect_parse_retries = 0
        self.in_flight = 0       # an LLM call under way: counted as unreported in a provisional summary
        self.out_tokens = 0      # completion tokens and seconds of the calls so far, for the throughput clamp
        self.out_seconds = 0.0
        self.providers = {}      # the provider OpenRouter served each call from, with counts
        self.summary_extra = {}  # fields only M3b settings add to summary.json (none for the M1-M3 agent)
        self.best = None        # snapshot of rtl/verif/docs after the last edit that compiled
        self.best_turn = None
        self.stop_reason = None
        self.edited = False
        self.changed_all = set()
        self.finished = None    # set once finish() has written the summary
        self.ledger_name = f"{uuid.uuid4().hex}.json"  # one entry per problem, rewritten as the cost grows
        self.last_state = {}
        # M3c: the interface check and the mutation gate, and what they did (summary fields only when on)
        self.iface = None
        self.iface_stats = {"interface_runs": 0, "interface_mismatch_runs": 0, "interface_kinds": {},
                            "interface_engines": {}, "interface_blocks": 0, "interface_mismatch_unresolved": False}
        self.iface_seen = {}     # mismatch set -> how many checks reported it
        self.last_tb = None      # the testbench of the last testbench check that ran
        self.gate_stats = {"gate_runs": 0, "gate_outcomes": [], "gate_failures": 0, "gate_overridden": False,
                           "mutants_generated": 0, "mutants_compiled": 0, "mutants_killed": 0,
                           "mutants_unfinished": 0, "gate_wall_s": 0.0, "gate_methods": []}
        # M3d: which version of the files each testbench result belongs to (bumped by every edit that changed a
        # file), so verify can tell a pass on the design as it stands from a pass on an older one
        self.version = 0
        self.tb_runs = 0
        self.tb_run_version = None
        self.tb_pass_version = None
        self.tb_last = None
        self.verify_stats = {"verify_runs": 0, "verify_refusals": 0, "verify_let_through": 0, "verify_outcomes": [],
                             "verify_reruns": 0, "testbench_runs": 0, "verified_at_submit": None}
        self.spec_inputs = None   # what the blind spec call may see, read before any edit
        self.spec = None          # the parsed cases
        self.spec_version = None  # file version of the last spec run
        self.spec_last = None
        self.spec_stats = {"spec_status": "not_run", "spec_failed_open": False, "spec_cases": 0, "spec_steps": 0,
                           "spec_cases_dropped": 0, "spec_runs": 0, "spec_unbuildable_runs": 0,
                           "spec_final_status": None, "spec_final_passed": None, "spec_final_total": None}

    # ---------- stop rules ----------
    def elapsed(self):
        return self.clock() - self.t0

    def time_left(self):
        return self.cfg.wall_s - self.elapsed()

    def llm_cap(self, node=None):
        """The reason not to start another LLM call (for `node`, or the edit loop's calls), or None. With M3f's
        role models, a role call is held to role_budget_usd and the rest to budget_usd, each on its own spend;
        with none, role_spent is 0 and this is the M3d rule."""
        if self.elapsed() >= self.cfg.wall_s or self.time_left() < MIN_LLM_S:
            return "wall_time"
        if self.cost_unreported:
            return "cost_unreported"  # the budget can no longer be enforced from reported cost
        if node in self.role_llms:
            if self.role_spent >= self.cfg.role_budget_usd:
                return "budget"
        elif self.spent - self.role_spent >= self.cfg.budget_usd:
            return "budget"
        return None

    def llm_for(self, node):
        return self.role_llms.get(node, self.llm)

    def level_for(self, node):
        """The node's current reasoning level: the problem's, or (M3f) the roles' own."""
        return self.role_reasoning if node in self.role_llms else self.reasoning

    def cap(self, state, nxt):
        """The reason to stop instead of running `nxt`, or None."""
        if self.elapsed() >= self.cfg.wall_s:
            return "wall_time"
        if nxt in LLM_NODES:
            reason = self.llm_cap(nxt)
            if reason:
                return reason
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
    def max_tokens_for(self, node, level, seconds):
        """The answer's room plus reasoning headroom for the level, cut to what the model can produce in `seconds`
        at the throughput seen so far in this problem."""
        cap = MAX_TOKENS.get(node, 4000) + REASONING_HEADROOM.get(level, 0)
        if self.out_seconds > 0 and self.out_tokens > 0:
            cap = min(cap, max(MIN_MAX_TOKENS, int(self.out_tokens / self.out_seconds * seconds * 0.9)))
        return cap

    def _attempt(self, node, messages, level, state, tools=None):
        seconds = max(1.0, self.time_left() - DEADLINE_MARGIN_S)
        max_tokens = self.max_tokens_for(node, level, seconds)
        self.in_flight = 1
        checkpoint(self, state)  # if the harness kills us mid-call, the call shows as unreported
        try:
            extra = {"tools": tools} if tools is not None else {}  # Deep Agents only
            client = self.llm_for(node)
            r = run_with_deadline(lambda: client.invoke(
                node, messages, max_tokens=max_tokens, timeout=min(150.0, seconds), reasoning=level,
                max_retries=0 if seconds < SHORT_CALL_S else None, **extra), seconds)
        finally:
            self.in_flight = 0
        r.max_tokens = max_tokens
        return r

    def call(self, node, messages, state, reasoning=None, retry_of=None, tools=None):
        """One LLM call, at `reasoning` (default: the problem's current level), with a hard deadline before the
        wall cap. If the model refuses the reasoning field, that is traced and the call is made again: at the
        problem's own level when only a retry's lower level was refused (say `off` on a model that must reason),
        otherwise without the field, and the problem then stays at "default" for good."""
        level = reasoning or self.level_for(node)
        base = self.level_for(node)
        remaining = self.time_left()
        self.llm_calls += 1
        call_id = self.llm_calls
        try:
            try:
                r = self._attempt(node, messages, level, state, tools)
            except ReasoningRejected as e:  # refused before generating anything: not billed, never fails the problem
                self.reasoning_rejected += 1
                fallback = base if level != base else "default"
                self.tracer.log("llm", node=node, model=getattr(self.llm_for(node), "model", None), turn=state.get("turn", 0),
                                call_id=call_id, retry_of=retry_of, reasoning=level, reasoning_rejected=True,
                                cost=0.0, error=truncate(redact(f"{type(e).__name__}: {e}"), 1000),
                                fallback=fallback)
                if fallback == "default":
                    if node in self.role_llms:
                        self.role_reasoning = "default"
                    else:
                        self.reasoning = "default"
                level = fallback
                r = self._attempt(node, messages, level, state, tools)
        except Exception as e:  # provider errors and missed deadlines end the run; the best edit is still kept
            self.cost_unreported += 1  # an errored, timed-out or abandoned call may still have been billed
            self.tracer.log("llm", node=node, model=getattr(self.llm_for(node), "model", None),
                            turn=state.get("turn", 0), call_id=call_id, retry_of=retry_of, reasoning=level, cost=None,
                            deadline_missed=isinstance(e, CallDeadline),
                            error=truncate(redact(f"{type(e).__name__}: {e}"), 1000), remaining_s=round(remaining, 1))
            checkpoint(self, state)
            return None
        r.call_id, r.retry_of, r.reasoning, r.empty = call_id, retry_of, level, empty_reply(node, r.text)
        self.models.add(r.model)
        if r.provider:
            self.providers[r.provider] = self.providers.get(r.provider, 0) + 1
        self.prompt_tokens += r.prompt_tokens or 0
        self.completion_tokens += r.completion_tokens or 0
        self.reasoning_tokens += r.reasoning_tokens or 0
        if r.completion_tokens and r.latency_s >= 1.0:
            self.out_tokens += r.completion_tokens
            self.out_seconds += r.latency_s
        if node in self.role_llms:
            self.role_calls += 1
        if r.cost is None:
            self.cost_unreported += 1
        else:
            self.spent += r.cost
            if node in self.role_llms:
                self.role_spent += r.cost
            self.cost_by_model[r.model] = self.cost_by_model.get(r.model, 0.0) + r.cost
        checkpoint(self, state)
        return r

    def ask(self, node, messages, state):
        """call(), and if the reply is empty, one retry with reasoning one step lower and a line asking for the
        answer only. The empty call's cost counts. If the retry is empty too (or a cap leaves no room for it), the
        empty reply is what the node gets, as before. Every call is traced once."""
        r = self.call(node, messages, state)
        if r is None or not r.empty:
            return r
        self.empty_replies += 1
        if self.llm_cap(node):
            return r  # the node traces it, marked empty
        self.log_llm(node, r, state, decision="empty")
        self.empty_retries += 1
        r2 = self.call(node, messages + [{"role": "user", "content": prompts.ANSWER_ONLY}], state,
                       reasoning=LOWER.get(r.reasoning, "low"), retry_of=r.call_id)
        if r2 is not None and r2.empty:
            self.empty_replies += 1
        return r2

    def log_llm(self, node, r, state, decision):
        self.tracer.log("llm", node=node, model=r.model, provider=r.provider, turn=state.get("turn", 0),
                        call_id=getattr(r, "call_id", None), retry_of=getattr(r, "retry_of", None),
                        reasoning=getattr(r, "reasoning", None), max_tokens=getattr(r, "max_tokens", None),
                        prompt_tokens=r.prompt_tokens, completion_tokens=r.completion_tokens,
                        reasoning_tokens=r.reasoning_tokens, finish_reason=r.finish_reason,
                        empty=getattr(r, "empty", False), cost=r.cost, latency_s=round(r.latency_s, 3),
                        generation_id=r.generation_id, decision=decision, completion=truncate(r.text, 3000))

    # ---------- lessons memory (M3b) ----------
    def lessons_block(self, task):
        """The plan prompt's lessons section, or "" with no memory. Retrieval is BM25 over the snapshot, queried
        with the task and the problem's docs; the lessons retrieved are traced and named in the summary."""
        if not self.cfg.memory:
            return ""
        from . import memory

        snap = memory.load(self.cfg.memory)
        docs = "\n".join(self.files.read(r) for r in self.files.list_files()
                         if r.startswith("docs/") and os.path.splitext(r)[1] in TEXT_EXT)
        got = memory.retrieve(snap["lessons"], f"{task}\n{docs}", k=self.cfg.memory_k)
        self.summary_extra.update({"memory": snap["hash"], "lessons": [x["id"] for x, _ in got]})
        self.tracer.log("lessons", memory=snap["hash"], k=self.cfg.memory_k,
                        retrieved=[{"id": x["id"], "score": sc} for x, sc in got])
        return prompts.LESSONS.format(lessons="\n".join(f"- {x['text']}" for x, _ in got)) if got else ""

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
        if cfg.interface_check:  # the given interface is read now, before any edit changes the original files
            from .interface import InterfaceCheck

            try:
                rt.iface = InterfaceCheck(cfg.root, timeout_s=min(30.0, cfg.tool_timeout_s), env=checks_mod.tool_env(),
                                          user=getattr(rt.checker, "user", None))
                given = {m: {"source": v["source"], "ports": sorted(v["ports"]), "params": sorted(v["params"])}
                         for m, v in rt.iface.given.items()}
                rt.tracer.log("tool", check="interface_given", command="read prompt, docs/, rtl/, verif/",
                              exit_code=0, output=truncate(json.dumps(given), 3000))
            except Exception as e:  # the check is then skipped; the problem goes on
                rt.tracer.log("tool", check="interface_given", command="read prompt, docs/, rtl/, verif/",
                              exit_code=1, output=truncate(f"{type(e).__name__}: {e}", 1000))
        if cfg.spec_vectors:  # M3d: what the blind spec call may see, read now, before any edit
            rt.spec_inputs = spec_inputs(rt, task)
        if run_budget_exhausted(cfg, rt.tracer):
            out["stop_reason"] = "run_budget_exhausted"
        return out

    def spec(state):
        """M3d: one LLM call that sees only the task, docs/ and the given ports, and writes reference cases. It fails
        open: an error, an unreadable reply or no usable case leaves the problem to verify's own-testbench rule."""
        from . import spec as spec_mod

        inp = rt.spec_inputs or {"docs": "(no documents)", "ports": "(none: no RTL was given)"}
        msg = prompts.SPEC.format(task=state["task"], docs=inp["docs"], ports=inp["ports"])
        st = rt.spec_stats
        r = rt.ask("spec", [{"role": "system", "content": prompts.SPEC_SYSTEM}, {"role": "user", "content": msg}],
                   state)
        if r is None:  # a provider error: counted unreported by call(), which then stops the problem as usual
            st.update(spec_status="llm_error", spec_failed_open=True)
            return {}
        parsed, notes = spec_mod.parse_cases(r.text)
        rt.log_llm("spec", r, state, decision={"cases": len(parsed["cases"]) if parsed else 0,
                                                "notes": notes[:20]})
        if parsed is None:
            st.update(spec_status="empty" if r.empty else "unusable", spec_failed_open=True,
                      spec_cases_dropped=sum(1 for n in notes if n.startswith("case ")))
            return {}
        try:
            path = spec_mod.write(cfg.root, parsed)
        except OSError as e:
            st.update(spec_status="error", spec_failed_open=True)
            rt.tracer.log("error", error=truncate(f"spec write: {type(e).__name__}: {e}", 1000))
            return {}
        rt.spec = parsed
        n, steps = spec_mod.count(parsed)
        st.update(spec_status="generated", spec_cases=n, spec_steps=steps,
                  spec_cases_dropped=sum(1 for x in notes if x.startswith("case ")))
        rt.tracer.log("tool", check="spec_write", command=f"write {os.path.relpath(path, cfg.root)}", exit_code=0,
                      output=f"{n} cases, {steps} steps" + ("; " + "; ".join(notes[:10]) if notes else ""))
        return {}

    def plan(state):
        msg = prompts.PLAN.format(
            task=state["task"], listing="\n".join(state["listing"]), contents=rt.contents(),
            tools=", ".join(k for k, v in rt.tools.items() if v) or "none",
            check_options=prompts.check_options(cfg, rt.tools))
        msg += rt.lessons_block(state["task"])  # "" with no memory: the M1-M3 prompt, unchanged
        r = rt.ask("plan", [{"role": "system", "content": prompts.SYSTEM}, {"role": "user", "content": msg}], state)
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
        r = rt.ask("edit", [{"role": "system", "content": prompts.SYSTEM}, {"role": "user", "content": msg}],
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
        if changed:
            rt.version += 1
        rt.changed_all.update(changed)
        requested = [c for c in e["checks"] if allowed_check(c, cfg)]
        tb = {"files": tb_files, "top": tb_top} if tb_files else (state.get("tb") if cfg.self_check else None)
        rt.log_llm("edit", r, {"turn": turn}, decision={"changed": changed, "errors": len(errors),
                                                        "checks": requested, "testbench": tb_files})
        return {"turn": turn, "changed": changed, "edit_errors": errors, "requested": requested, "tb": tb,
                "checked": False}

    def interface(state):
        """M3c: elaborate the RTL and compare its interface with the given one. Never blocks by itself."""
        if rt.iface is None:
            res = {"ok": None, "summary": "the given interface could not be read", "findings": [], "engine": None}
        else:
            try:
                res = rt.iface.check()
            except Exception as e:
                res = {"ok": None, "summary": f"interface check failed: {type(e).__name__}", "findings": [],
                       "engine": None}
        st = rt.iface_stats
        st["interface_runs"] += 1
        eng = res.get("engine") or "none"
        st["interface_engines"][eng] = st["interface_engines"].get(eng, 0) + 1
        if res.get("findings"):
            from .interface import mismatch_key

            st["interface_mismatch_runs"] += 1
            for f in res["findings"]:
                st["interface_kinds"][f["kind"]] = st["interface_kinds"].get(f["kind"], 0) + 1
            key = mismatch_key(res)
            rt.iface_seen[key] = rt.iface_seen.get(key, 0) + 1
        rt.tracer.log("tool", check="interface", command=f"elaborate rtl/ ({eng})", exit_code={True: 0, False: 1}.get(
            res.get("ok")), turn=state.get("turn"), output=truncate(res.get("summary", ""), 3000),
            findings=len(res.get("findings", [])), engine=res.get("engine"))
        return {"interface": res}

    def check(state):
        results = rt.checker.run(state.get("requested", []), state.get("tb"))
        if cfg.interface_check and state.get("interface"):
            results["interface"] = {"ok": state["interface"].get("ok"), "summary": state["interface"]["summary"]}
        if (results.get("testbench") or {}).get("ok") is not None:
            rt.last_tb = state.get("tb")
            note_tb(rt, results["testbench"])
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
        msgs = [{"role": "system", "content": prompts.SYSTEM}, {"role": "user", "content": msg}]
        r = rt.ask("reflect", msgs, state)
        if r is None:
            return {"stop_reason": "llm_error"}
        d = parse_decision(r.text)
        if not d["parsed"] and not empty_reply("reflect", r.text) and not rt.llm_cap():
            # one retry asking for the JSON decision only; if that cannot be read either, submit
            rt.log_llm("reflect", r, state, decision="unparseable")
            rt.reflect_parse_retries += 1
            r = rt.call("reflect", msgs + [{"role": "user", "content": prompts.JSON_ONLY}], state,
                        retry_of=r.call_id)
            if r is None:
                return {"stop_reason": "llm_error"}
            d = parse_decision(r.text)
        rt.log_llm("reflect", r, state, decision=d["decision"])
        if d["decision"] == "submit" and cfg.interface_check:
            from .interface import mismatch_key

            key = mismatch_key(state.get("interface"))
            room = state.get("turn", 0) < cfg.max_turns and not rt.llm_cap()  # else the submit goes through
            if key and rt.iface_seen.get(key, 0) < 2 and room:  # reported once: one more edit before submitting
                rt.iface_stats["interface_blocks"] += 1
                rt.tracer.log("tool", check="interface_block", command="submit", exit_code=1,
                              output="interface mismatches reported once: edit again (submitting is allowed after "
                                     "the same mismatches are reported twice)")
                d = {"decision": "edit_again", "reason": "The interface check found mismatches with the given "
                     "interface (above). Fix the names, ports, parameters or widths, or leave them if the task asks "
                     "for them: submitting is allowed once the same mismatches are reported twice. "
                     + d["reason"]}
        out = {"decision": d["decision"], "reason": d["reason"]}
        if d["decision"] in ("submit", "give_up"):
            out["stop_reason"] = d["decision"]
        return out

    def gate(state):
        """M3c: the mutation-score gate on a submit. A failure goes back to reflect with the survivors; after
        cfg.gate_max_failures failures the agent submits anyway (gate_overridden)."""
        st = rt.gate_stats
        if st["gate_failures"] >= cfg.gate_max_failures:
            st["gate_overridden"] = True
            rt.tracer.log("tool", check="gate_override", command="submit", exit_code=0,
                          output=f"the gate failed {st['gate_failures']} times: submitting anyway")
            return {}
        from .mutation import MutationGate

        g = MutationGate(cfg.root, rt.tracer, rt.tools, n=cfg.gate_mutants, seed=cfg.gate_seed,
                         threshold=cfg.gate_threshold, bound_s=cfg.gate_s, clock=rt.clock, time_left=rt.time_left,
                         user=getattr(rt.checker, "user", None))
        try:
            res = g.run(rt.last_tb)
        except Exception as e:  # a gate that breaks never blocks the submission
            res = {"outcome": "skipped", "ok": None, "note": f"{type(e).__name__}: {e}",
                   "summary": f"mutation gate: not applied ({type(e).__name__})", "generated": 0, "compiled": 0,
                   "killed": 0, "unfinished": 0, "wall_s": 0.0, "method": None}
            rt.tracer.log("error", error=truncate(redact(f"gate: {type(e).__name__}: {e}"), 2000))
        st["gate_runs"] += 1
        st["gate_outcomes"].append(res["outcome"])
        for k in ("generated", "compiled", "killed", "unfinished"):
            st[f"mutants_{k}"] += res.get(k, 0)
        st["gate_wall_s"] = round(st["gate_wall_s"] + res.get("wall_s", 0.0), 2)
        if res.get("method"):
            st["gate_methods"].append(res["method"])
        results = {**state.get("results", {}), "mutation_gate": {"ok": res["ok"], "summary": res["summary"]}}
        if res["ok"] is False:
            st["gate_failures"] += 1
            if rt.llm_cap() or rt.elapsed() >= cfg.wall_s:  # no budget or time for another reflect: submit
                st["gate_overridden"] = True
                rt.tracer.log("tool", check="gate_override", command="submit", exit_code=0,
                              output=f"the gate failed, and {rt.llm_cap() or 'wall_time'} leaves no room to "
                                     "reflect again: submitting anyway")
                return {"results": results}
            return {"results": results, "stop_reason": "", "decision": "gate_failed",
                    "reason": "The mutation gate failed (above)."}
        return {"results": results}

    def verify(state):
        """M3d: a submit goes through only if the design as it stands has passed a testbench of the agent's (one it
        wrote, or one given under verif/ that it ran), and with spec_vectors the specification cases too. A refusal
        goes back to edit with what is missing; after cfg.verify_max_refusals refusals, or with no turn, budget or
        time left for another edit, the submit is let through."""
        st = rt.verify_stats
        st["verify_runs"] += 1
        results = dict(state.get("results") or {})
        missing = []
        tb = state.get("tb") or rt.last_tb
        if rt.tb_pass_version != rt.version:
            if tb and tb.get("files") and rt.tb_run_version != rt.version:
                st["verify_reruns"] += 1  # the testbench has not run on these files yet: run it now
                res = rt.checker.run(["testbench"], tb)
                tbr = res.get("testbench") or {}
                if tbr.get("ok") is not None:
                    rt.last_tb = tb
                    note_tb(rt, tbr)
                results.update(res)
                if res.get("compile", {}).get("ok"):
                    rt.best, rt.best_turn = rt.files.snapshot(), state.get("turn")
            if rt.tb_pass_version != rt.version:
                if rt.tb_run_version == rt.version and rt.tb_last is not None:
                    missing.append("tb_fail")
                else:
                    missing.append("no_tb")
        spec_note = ""
        if cfg.spec_vectors and rt.spec is not None:
            sr = rt.spec_last if rt.spec_version == rt.version else run_spec(rt, "spec")
            if sr["status"] in ("fail", "timeout"):
                missing.append("spec_fail")
            elif sr["status"] in ("unbuildable", "error", "skipped"):
                spec_note = (f"\n(specification cases not applied: {sr['status']}; this does not block the "
                             "submit)\n" + truncate(sr.get("summary", ""), 800))
            results["spec_cases"] = {"ok": None if sr["status"] in ("unbuildable", "error", "skipped")
                                     else sr["status"] == "pass", "summary": spec_render(sr) + spec_note}
        if not missing:
            st["verify_outcomes"].append("pass")
            st["verified_at_submit"] = True
            rt.tracer.log("tool", check="verify_submit", command="submit", exit_code=0, output="verified: submit")
            return {"results": results}
        room = rt.cap({**state}, "edit") is None
        if st["verify_refusals"] >= cfg.verify_max_refusals or not room:
            st["verify_let_through"] += 1
            st["verify_outcomes"].append("let_through")
            st["verified_at_submit"] = False
            why = (f"refused {st['verify_refusals']} times" if room else
                   f"{rt.cap({**state}, 'edit')} leaves no room for another edit")
            rt.tracer.log("tool", check="verify_submit", command="submit", exit_code=0,
                          output=f"not verified ({'+'.join(missing)}), but {why}: submitting anyway")
            return {"results": results}
        st["verify_refusals"] += 1
        st["verify_outcomes"].append("refused_" + "+".join(missing))
        msg = refusal(rt, missing)
        rt.tracer.log("tool", check="verify_submit", command="submit", exit_code=1, output=truncate(msg, 3000))
        results["verify_submit"] = {"ok": False, "summary": msg}
        return {"results": results, "stop_reason": "", "decision": "verify_refused", "reason": msg,
                "checked": True}

    def finalize(state):
        return finish(rt, state)

    g = StateGraph(State)
    nodes = [("read_task", read_task), ("plan", plan), ("edit", edit), ("check", check), ("reflect", reflect),
             ("finalize", finalize)]
    if cfg.interface_check:
        nodes.insert(3, ("interface", interface))
    if cfg.mutation_gate:
        nodes.insert(-1, ("gate", gate))
    if cfg.verify_submit and cfg.mutation_gate:
        raise ValueError("verify_submit and mutation_gate are separate arms: turn one of them off")
    if cfg.verify_submit:
        nodes.insert(-1, ("verify", verify))
    if cfg.spec_vectors:
        nodes.insert(1, ("spec", spec))
    for name, fn in nodes:
        g.add_node(name, fn)
    after_edit = "interface" if cfg.interface_check else "check"
    g.add_edge(START, "read_task")
    if cfg.spec_vectors:
        g.add_conditional_edges("read_task", lambda s: "finalize" if s.get("stop_reason") else rt.go(s, "spec"),
                                ["spec", "finalize"])
        g.add_conditional_edges("spec", lambda s: "finalize" if s.get("stop_reason") else rt.go(s, "plan"),
                                ["plan", "finalize"])
    else:
        g.add_conditional_edges("read_task", lambda s: "finalize" if s.get("stop_reason") else rt.go(s, "plan"),
                                ["plan", "finalize"])
    g.add_conditional_edges("plan", lambda s: "finalize" if s.get("stop_reason") else rt.go(s, "edit"),
                            ["edit", "finalize"])
    g.add_conditional_edges("edit", lambda s: "finalize" if s.get("stop_reason") else rt.go(s, after_edit),
                            [after_edit, "finalize"])
    if cfg.interface_check:
        g.add_conditional_edges("interface", lambda s: rt.go(s, "check"), ["check", "finalize"])
    g.add_conditional_edges("check", lambda s: rt.go(s, "reflect"), ["reflect", "finalize"])
    if cfg.mutation_gate:
        g.add_conditional_edges("reflect", lambda s: (rt.go(s, "gate") if s.get("stop_reason") == "submit" else
                                                      "finalize") if s.get("stop_reason") else rt.go(s, "edit"),
                                ["edit", "gate", "finalize"])
        g.add_conditional_edges("gate", lambda s: "finalize" if s.get("stop_reason") else rt.go(s, "reflect"),
                                ["reflect", "finalize"])
    elif cfg.verify_submit:
        g.add_conditional_edges("reflect", lambda s: (rt.go(s, "verify") if s.get("stop_reason") == "submit" else
                                                      "finalize") if s.get("stop_reason") else rt.go(s, "edit"),
                                ["edit", "verify", "finalize"])
        g.add_conditional_edges("verify", lambda s: "finalize" if s.get("stop_reason") else rt.go(s, "edit"),
                                ["edit", "finalize"])
    else:
        g.add_conditional_edges("reflect", lambda s: "finalize" if s.get("stop_reason") else rt.go(s, "edit"),
                                ["edit", "finalize"])
    g.add_edge("finalize", END)
    return g.compile()


def note_tb(rt, result):
    """M3d bookkeeping (kept for every arm, shown only with verify_submit): a testbench result on these files."""
    rt.tb_runs += 1
    rt.tb_run_version = rt.version
    rt.tb_last = result
    if result.get("ok"):
        rt.tb_pass_version = rt.version


def spec_inputs(rt, task):
    """M3d: the blind spec call's inputs: the documents under docs/ and a port table of the given RTL. Never an
    RTL body, verif/, or anything the agent writes."""
    from . import spec as spec_mod

    docs = {}
    for rel in rt.files.list_files():
        if rel.startswith("docs/") and os.path.splitext(rel)[1] in TEXT_EXT:
            try:
                docs[rel] = rt.files.read(rel)
            except OSError:
                continue
    ports = "(none: no RTL was given)"
    try:
        from .interface import given_interface, given_record

        given, _ = given_interface(given_record(rt.cfg.root))
        ports = spec_mod.port_table(given)
    except Exception as e:  # the call still runs, without the port table
        rt.tracer.log("tool", check="spec_ports", command="read rtl/ ports", exit_code=1,
                      output=truncate(f"{type(e).__name__}: {e}", 500))
    return {"docs": spec_mod.docs_text(docs), "ports": ports}


def run_spec(rt, tag):
    """M3d: the spec testbench on the files as they stand; fails open on any error."""
    from . import spec as spec_mod

    st = rt.spec_stats
    try:
        res = spec_mod.run(rt.checker, rt.cfg.root, rt.spec, tag=tag)
    except Exception as e:
        res = {"status": "error", "passed": 0, "total": len(rt.spec["cases"]), "failed_cases": [], "mismatches": [],
               "summary": f"{type(e).__name__}: {e}"}
    if res["status"] != "skipped":
        st["spec_runs"] += 1
    if res["status"] == "unbuildable":
        st["spec_unbuildable_runs"] += 1
    rt.spec_version, rt.spec_last = rt.version, res
    rt.tracer.log("tool", check=f"{tag}_result", command="spec cases", exit_code=0 if res["status"] == "pass" else 1,
                  output=f"{res['status']}: {res['passed']}/{res['total']} cases passed")
    return res


def spec_render(res):
    from . import spec as spec_mod

    return spec_mod.render(res)


def refusal(rt, missing):
    """The message a refused submit sends back to edit: what is missing and what would satisfy the rule."""
    given = [r for r in rt.files.list_files() if r.startswith("verif/") and r.endswith((".sv", ".v", ".py"))]
    parts = ["Submit refused: the design as it now stands has not passed a simulation."]
    if "no_tb" in missing:
        parts.append("No testbench has run on the current files.")
    if "tb_fail" in missing:
        parts.append("Your testbench fails on the current files (its result is above).")
    if "spec_fail" in missing:
        parts.append("The specification cases fail (above). They were written from the specification alone, by a "
                     "reviewer who has not seen your design; inputs change just after a rising edge and outputs are "
                     "compared 1 ns after the next one. Fix the design where the specification supports the "
                     "expected value.")
    if "no_tb" in missing or "tb_fail" in missing:
        if given:
            parts.append("The task gives a testbench: run it by naming it with an empty body, e.g. "
                         f'<tb path="{given[0]}" top="<its top module>"></tb>, and choose the testbench check. '
                         f"Given under verif/: {', '.join(given[:6])}.")
        else:
            parts.append("Write a self-checking testbench with a small reference model that covers the "
                         "specification's examples, its error cases and any latency, count or flag it states, "
                         "choose the testbench check, and fix what it finds.")
    return " ".join(parts)


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
                rt.version += 1
                kept = f"best_compiled_turn_{rt.best_turn}"
                rt.tracer.log("tool", check="keep_best", command=f"restore turn {rt.best_turn}", exit_code=0)
        if rt.cfg.spec_vectors and rt.spec is not None:  # M3d: the spec cases on the final design (measurement)
            final = rt.spec_last if rt.spec_version == rt.version else run_spec(rt, "spec_final")
            rt.spec_stats.update(spec_final_status=final["status"], spec_final_passed=final["passed"],
                                 spec_final_total=final["total"])
        for f in ("compile.vvp", "tb.vvp"):
            p = os.path.join(rt.checker.tb_dir, f) if hasattr(rt.checker, "tb_dir") else None
            if p and os.path.exists(p):
                os.remove(p)
    except Exception as e:  # keep going: the summary and the ledger entry matter more
        error = error or f"finalize: {type(e).__name__}: {e}"
    stop = "error" if error else (state.get("stop_reason") or rt.stop_reason or "submit")
    summary = make_summary(rt, state, stop, kept, compiled)
    if error:
        summary["error"] = truncate(redact(error), 2000)
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
    extra = {}
    if rt.cfg.interface_check:
        rt.iface_stats["interface_mismatch_unresolved"] = bool((state.get("interface") or {}).get("findings"))
        extra.update(json.loads(json.dumps(rt.iface_stats)))
    if rt.cfg.mutation_gate:
        extra.update(json.loads(json.dumps(rt.gate_stats)))
    if rt.cfg.verify_submit:
        rt.verify_stats["testbench_runs"] = rt.tb_runs
        extra.update(json.loads(json.dumps(rt.verify_stats)))
    if rt.cfg.spec_vectors:
        extra.update(json.loads(json.dumps(rt.spec_stats)))
    if rt.role_llms:  # M3f: who did what, and what each part cost
        extra.update({"role_models": {n: getattr(c, "model", None) for n, c in sorted(rt.role_llms.items())},
                      "role_reasoning_used": rt.role_reasoning, "role_calls": rt.role_calls,
                      "role_cost_usd": round(rt.role_spent, 8),
                      "main_cost_usd": round(rt.spent - rt.role_spent, 8),
                      "cost_by_model": {m: round(c, 8) for m, c in sorted(rt.cost_by_model.items())}})
    return {**_summary(rt, state, stop, kept, compiled), **rt.summary_extra, **extra}


def _summary(rt, state, stop, kept, compiled):
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
        "cost_unreported_calls": rt.cost_unreported + rt.in_flight,
        "in_flight_calls": rt.in_flight,
        "providers": dict(sorted(rt.providers.items())),
        "reasoning": rt.cfg.reasoning,
        "reasoning_used": rt.reasoning,
        "reasoning_rejected": rt.reasoning_rejected,
        "reasoning_tokens": rt.reasoning_tokens,
        "empty_replies": rt.empty_replies,
        "empty_retries": rt.empty_retries,
        "reflect_parse_retries": rt.reflect_parse_retries,
        "seed": rt.cfg.seed or None,
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
    if cfg.harness == "claudecode":  # no LLM client of ours: Claude Code makes its own calls
        from . import claude_code

        return claude_code.run(cfg)
    from . import llm as llm_mod

    tracer = kw.pop("tracer", None) or Tracer(cfg.agent_out)
    if cfg.harness == "deepagents":
        from . import deep

        return deep.run(cfg, llm or llm_mod.make(cfg), tracer=tracer, **kw)
    rt = Runtime(cfg, llm or llm_mod.make(cfg), tracer=tracer, **kw)
    rt.tracer.log("start", model=cfg.model or None, provider=cfg.provider, seed=cfg.seed or None,
                  switches=cfg.switches())
    graph = build(rt)
    state = {}
    try:
        limit = 10 * cfg.max_turns + (40 if cfg.mutation_gate or cfg.interface_check or cfg.verify_submit
                                      else 20)  # M3c, M3d: more steps
        for state in graph.stream({}, {"recursion_limit": limit}, stream_mode="values"):
            pass
    except Exception as e:
        import traceback

        rt.tracer.log("error", error=truncate(redact(f"{type(e).__name__}: {e}\n{traceback.format_exc()}"), 4000))
        finish(rt, state, error=f"{type(e).__name__}: {e}")
    finally:
        finish(rt, state)  # a no-op when finalize already ran
    with open(os.path.join(cfg.agent_out, "summary.json")) as f:
        return json.load(f)


def mermaid(**switches):
    """The compiled graph as mermaid, for the README (and its drift test). With M3c's switches
    (mutation_gate=True, interface_check=True) or M3d's (verify_submit=True, spec_vectors=True), the graph with
    their steps."""
    from .config import Config
    from .llm import FakeLLM

    rt = Runtime(Config(root="/nonexistent", out_dir="", **switches), FakeLLM(), tracer=Tracer(None), tools={})
    return build(rt).get_graph().draw_mermaid()
