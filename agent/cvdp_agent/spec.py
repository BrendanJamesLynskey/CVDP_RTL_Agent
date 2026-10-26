"""M3d, spec_vectors: reference cases written from the specification alone, turned into a testbench in code.

A separate LLM call (graph node `spec`, before plan) is given the task prompt, the documents under docs/ and a port
table of the modules in the given RTL (names, directions, widths; read before any edit). It never sees an RTL body,
a file under verif/, or anything the agent writes. It replies with one JSON object (prompts.SPEC):

    {"top": "queue", "params": {"DEPTH": 4}, "clock": "clk" | null,
     "ports": {"clk": {"dir": "in", "width": 1}, ...},
     "cases": [{"name": "reset", "steps": [{"in": {...}, "expect_now": {...}, "wait": 0,
                                            "until": {"signal": "done", "value": 1, "max_cycles": 50},
                                            "expect": {...}}]}]}

`parse_cases` checks it and drops what cannot be used (a case naming an unknown port, a bad value); `testbench`
writes the SystemVerilog testbench; `run` builds and runs it with Icarus on the design as it stands and reads the
per-case lines it prints. Deterministic from here on: no LLM sees the testbench or judges its result.

Fail-open: a spec call that errors, a reply that cannot be read, no usable case, or a testbench that does not build
against the design never blocks a submit. Each is counted (spec_status, spec_unbuildable_runs)."""
import json
import os
import re

from .parse import extract_json
from .trace import truncate

SPEC_DIR = os.path.join("rundir", "agent_tb", "spec_vectors")
TB_NAME = "spec_tb"
_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MAX_CASES = 16
MAX_STEPS = 60
MAX_WIDTH = 4096
MAX_UNTIL = 100_000
PERIOD = 10
_CASE_LINE = re.compile(r"^SPEC_CASE (\S+) (PASS|FAIL)\s*$", re.M)
_MISMATCH = re.compile(r"^SPEC_MISMATCH .*$", re.M)
_DONE = re.compile(r"^SPEC_DONE cases=(\d+) failed=(\d+)\s*$", re.M)


# ---------- the blind prompt ----------

def docs_text(files, limit=60000):
    """The documents under docs/, as the spec writer sees them: {rel: text} -> one block."""
    parts, total = [], 0
    for rel in sorted(files):
        text = truncate(files[rel], 30000)
        if total + len(text) > limit:
            parts.append(f"=== {rel} === (not shown: length limit)")
            continue
        total += len(text)
        parts.append(f"=== {rel} ===\n{text}")
    return "\n\n".join(parts) or "(no documents)"


def port_table(given):
    """The given RTL's modules as a port table: names, directions, constant widths, parameter names. Only modules
    an original rtl/ file defines (the interface check's `given` with source "rtl"); nothing from their bodies."""
    lines = []
    for mod in sorted(given):
        m = given[mod]
        if m.get("source") != "rtl":
            continue
        params = sorted(m.get("params") or {})
        lines.append(f"module {mod}" + (f" (parameters: {', '.join(params)})" if params else ""))
        for name, p in (m.get("ports") or {}).items():
            w = p.get("width")
            lines.append(f"  {p.get('dir') or '?'} {name}" + (f" [{w} bits]" if isinstance(w, int) else
                                                              " [width set by a parameter]"))
    return "\n".join(lines) or "(none: no RTL was given)"


# ---------- the reply ----------

def value(v, width):
    """An expected or driven value as an int at `width` bits, "x" for don't-care, or None if unusable."""
    if v is None:
        return "x"
    if isinstance(v, bool):
        v = int(v)
    if isinstance(v, str):
        s = v.strip().lower().replace("_", "")
        if s in ("x", "?", "", "dontcare", "don't care", "any"):
            return "x"
        m = re.fullmatch(r"(?:\d+)?'[s]?([bhd])([0-9a-f]+)", s)
        try:
            if m:
                v = int(m.group(2), {"b": 2, "h": 16, "d": 10}[m.group(1)])
            else:
                v = int(s, 0)
        except ValueError:
            return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if not isinstance(v, int):
        return None
    if v < 0:
        if v < -(1 << (width - 1)) and width > 0:
            return None
        v &= (1 << width) - 1
    if v >= (1 << width):
        return None
    return v


def parse_cases(text):
    """(spec, notes): the usable spec, or None, and what was dropped and why."""
    obj = extract_json(text)
    notes = []
    if not isinstance(obj, dict):
        return None, ["no JSON object in the reply"]
    top = str(obj.get("top") or "")
    if not _ID.match(top):
        return None, [f"bad top module name {top!r}"]
    ports = {}
    for name, p in (obj.get("ports") or {}).items():
        if not isinstance(p, dict) or not _ID.match(str(name)):
            notes.append(f"port {name!r} dropped")
            continue
        d = str(p.get("dir", "")).lower()
        d = {"input": "in", "output": "out"}.get(d, d)
        try:
            w = int(p.get("width", 1))
        except (TypeError, ValueError):
            w = 0
        if d not in ("in", "out") or not 1 <= w <= MAX_WIDTH:
            notes.append(f"port {name!r} dropped (dir {d!r}, width {p.get('width')!r})")
            continue
        ports[str(name)] = {"dir": d, "width": w}
    clock = obj.get("clock")
    clock = str(clock) if clock else None
    if clock and (clock not in ports or ports[clock]["dir"] != "in" or ports[clock]["width"] != 1):
        return None, [f"clock {clock!r} is not a 1-bit input port"]
    params = {}
    for k, v in (obj.get("params") or {}).items():
        if _ID.match(str(k)) and isinstance(v, int) and not isinstance(v, bool) and 0 <= v < (1 << 31):
            params[str(k)] = v
        else:
            notes.append(f"parameter {k!r} dropped")
    cases, names = [], set()
    for i, c in enumerate((obj.get("cases") or [])[:MAX_CASES]):
        if not isinstance(c, dict):
            continue
        name = re.sub(r"\W", "_", str(c.get("name") or f"case{i + 1}"))[:40] or f"case{i + 1}"
        if name in names or not re.match(r"[A-Za-z_]", name):
            name = f"c{i + 1}_{name}"[:40]
        names.add(name)
        steps, why = _steps(c.get("steps"), ports, clock)
        if why:
            notes.append(f"case {name} dropped: {why}")
            continue
        cases.append({"name": name, "steps": steps})
    if not cases:
        return None, notes + ["no usable case"]
    return {"top": top, "params": params, "clock": clock, "ports": ports, "cases": cases}, notes


def _sigs(d, ports, want_dir):
    out = {}
    for k, v in (d or {}).items():
        if k not in ports or ports[k]["dir"] != want_dir:
            return None, f"{k!r} is not an {want_dir}put port"
        x = value(v, ports[k]["width"])
        if x is None:
            return None, f"bad value {v!r} for {k}"
        if want_dir == "in" and x == "x":
            return None, f"input {k} driven to x"
        out[k] = x
    return out, None


def _steps(raw, ports, clock):
    if not isinstance(raw, list) or not raw:
        return None, "no steps"
    if len(raw) > MAX_STEPS:
        return None, f"{len(raw)} steps (at most {MAX_STEPS})"
    steps = []
    for j, s in enumerate(raw):
        if not isinstance(s, dict):
            return None, f"step {j + 1} is not an object"
        ins, why = _sigs(s.get("in"), ports, "in")
        if why:
            return None, f"step {j + 1}: {why}"
        if clock and clock in ins:
            return None, f"step {j + 1}: drives the clock"
        now, why = _sigs(s.get("expect_now"), ports, "out")
        if why:
            return None, f"step {j + 1}: {why}"
        exp, why = _sigs(s.get("expect"), ports, "out")
        if why:
            return None, f"step {j + 1}: {why}"
        try:
            wait = int(s.get("wait") or 0)
        except (TypeError, ValueError):
            return None, f"step {j + 1}: bad wait"
        until = s.get("until")
        if until:
            if not clock or not isinstance(until, dict):
                return None, f"step {j + 1}: until needs a clock"
            sig = str(until.get("signal", ""))
            if sig not in ports or ports[sig]["dir"] != "out":
                return None, f"step {j + 1}: until on {sig!r}, not an output"
            uv = value(until.get("value", 1), ports[sig]["width"])
            try:
                mc = int(until.get("max_cycles") or 100)
            except (TypeError, ValueError):
                mc = 0
            if uv in (None, "x") or not 1 <= mc <= MAX_UNTIL:
                return None, f"step {j + 1}: bad until"
            until = {"signal": sig, "value": uv, "max_cycles": mc}
        else:
            until = None
        if not 0 <= wait <= MAX_UNTIL or (wait and not clock):
            return None, f"step {j + 1}: bad wait"
        steps.append({"in": ins, "expect_now": now, "wait": wait, "until": until, "expect": exp})
    return steps, None


def count(spec):
    return len(spec["cases"]), sum(len(c["steps"]) for c in spec["cases"])


# ---------- the testbench ----------

def _lit(v, w):
    return f"{w}'h{v:x}"


def _checks(lines, spec, case, step, exp, when):
    for sig, v in exp.items():
        if v == "x":
            continue
        w = spec["ports"][sig]["width"]
        lines.append(f"    if ({sig} !== {_lit(v, w)}) begin errs = errs + 1; $display(\"SPEC_MISMATCH case={case} "
                     f"step={step} {when} signal={sig} expected=%h got=%h\", {_lit(v, w)}, {sig}); end")


def testbench(spec):
    """The SystemVerilog testbench for a parsed spec. It prints SPEC_CASE <name> PASS|FAIL per case, a
    SPEC_MISMATCH line per failed comparison, and SPEC_DONE cases=<n> failed=<k>; a global time-out ends a hang."""
    clk = spec["clock"]
    ports = spec["ports"]
    budget = 0
    for c in spec["cases"]:
        for s in c["steps"]:
            budget += 2 + s["wait"] + ((s["until"] or {}).get("max_cycles", 0))
    timeout = (budget + 10) * PERIOD
    L = ["`timescale 1ns/1ps", f"module {TB_NAME};"]
    for n, p in ports.items():
        rng = f"[{p['width'] - 1}:0] " if p["width"] > 1 else ""
        L.append(f"  logic {rng}{n}" + (" = '0;" if p["dir"] == "in" else ";"))
    L.append("  integer errs = 0, failed = 0;")
    params = ", ".join(f".{k}({v})" for k, v in spec["params"].items())
    conns = ", ".join(f".{n}({n})" for n in ports)
    L.append(f"  {spec['top']} {'#(' + params + ') ' if params else ''}dut ({conns});")
    if clk:
        L.append(f"  always #{PERIOD // 2} {clk} = ~{clk};")
    L.append(f"  initial begin #{timeout}; $display(\"SPEC_TIMEOUT at %0t\", $time); "
             f"$display(\"SPEC_DONE cases={len(spec['cases'])} failed=-1\"); $finish; end")
    L.append("  initial begin")
    L.append("    #1;" if clk else "    #0;")
    for c in spec["cases"]:
        name = c["name"]
        L.append(f"    // case {name}")
        L.append("    errs = 0;")
        for j, s in enumerate(c["steps"], 1):
            for sig, v in s["in"].items():
                L.append(f"    {sig} = {_lit(v, ports[sig]['width'])};")
            L.append("    #1;")
            _checks(L, spec, name, j, s["expect_now"], "now")
            if clk:
                L.append(f"    @(posedge {clk}); #1;")
                if s["wait"]:
                    L.append(f"    repeat ({s['wait']}) begin @(posedge {clk}); #1; end")
                u = s["until"]
                if u:
                    w = ports[u["signal"]]["width"]
                    L.append(f"    begin : u_{name}_{j}")
                    L.append("      integer n; n = 0;")
                    L.append(f"      while ({u['signal']} !== {_lit(u['value'], w)} && n < {u['max_cycles']}) "
                             f"begin @(posedge {clk}); #1; n = n + 1; end")
                    L.append(f"      if ({u['signal']} !== {_lit(u['value'], w)}) begin errs = errs + 1; "
                             f"$display(\"SPEC_MISMATCH case={name} step={j} until signal={u['signal']} never became "
                             f"%h within {u['max_cycles']} cycles\", {_lit(u['value'], w)}); end")
                    L.append("    end")
            _checks(L, spec, name, j, s["expect"], "after")
            if not clk:
                L.append("    #1;")
        L.append(f"    if (errs == 0) $display(\"SPEC_CASE {name} PASS\"); "
                 f"else begin failed = failed + 1; $display(\"SPEC_CASE {name} FAIL\"); end")
    L.append(f"    $display(\"SPEC_DONE cases={len(spec['cases'])} failed=%0d\", failed);")
    L.append("    $finish;")
    L.append("  end")
    L.append("endmodule")
    return "\n".join(L) + "\n"


# ---------- running it ----------

def write(root, spec, reply_text=None):
    d = os.path.join(root, SPEC_DIR)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{TB_NAME}.sv")
    with open(path, "w") as f:
        f.write(testbench(spec))
    with open(os.path.join(d, "spec_cases.json"), "w") as f:
        json.dump(spec, f, indent=1)
    return path


def read_result(rc, text, n_cases):
    """{"status": pass|fail|timeout|error, "passed", "total", "failed_cases", "mismatches"} from the run's output."""
    cases = _CASE_LINE.findall(text or "")
    passed = sum(1 for _, r in cases if r == "PASS")
    failed = [n for n, r in cases if r == "FAIL"]
    mism = _MISMATCH.findall(text or "")
    done = _DONE.search(text or "")
    if "SPEC_TIMEOUT" in (text or "") or rc == 124:
        status = "timeout"
    elif done and int(done.group(2)) == 0 and passed == n_cases and rc == 0:
        status = "pass"
    elif cases or done:
        status = "fail"
    else:
        status = "error"
    return {"status": status, "passed": passed, "total": n_cases, "failed_cases": failed, "mismatches": mism}


def run(checker, root, spec, tag="spec"):
    """Build the spec testbench against rtl/ as it stands and run it. Uses the checker's tool runner (time limits,
    the unprivileged tool user, the scrubbed environment). Status "unbuildable" when it does not compile."""
    path = os.path.join(root, SPEC_DIR, f"{TB_NAME}.sv")
    if not os.path.exists(path):
        write(root, spec)
    checker._tb_dir_ready()
    d = os.path.join(root, SPEC_DIR)
    os.makedirs(d, exist_ok=True)
    if getattr(checker, "user", None):
        os.chmod(d, 0o777)
    files, inc = checker._sources()
    out = os.path.join(d, "spec_tb.vvp")
    cmd = ["iverilog", "-g2012", "-o", out, "-s", TB_NAME] + [f"-I{x}" for x in inc] + files + [path]
    n = len(spec["cases"])
    rc, text, s = checker._run(f"{tag}_build", cmd)
    if rc is None:
        return {"status": "skipped", "passed": 0, "total": n, "failed_cases": [], "mismatches": [], "summary": s}
    if rc != 0:
        return {"status": "unbuildable", "passed": 0, "total": n, "failed_cases": [], "mismatches": [],
                "summary": truncate(s, 1500)}
    rc, text, s = checker._run(f"{tag}_run", ["vvp", "-n", out], cwd=d)
    try:
        os.remove(out)
    except OSError:
        pass
    if rc is None:
        return {"status": "skipped", "passed": 0, "total": n, "failed_cases": [], "mismatches": [], "summary": s}
    res = read_result(rc, text, n)
    res["summary"] = s
    return res


def render(res, limit=12):
    """A spec run as the agent sees it on a refusal: counts and the first mismatches, never the cases' source."""
    head = f"{res['passed']} of {res['total']} specification cases passed"
    if res["status"] == "timeout":
        head += " (the simulation timed out: an output the cases wait for may never change)"
    lines = [head] + [m.replace("SPEC_MISMATCH ", "- ") for m in res["mismatches"][:limit]]
    if len(res["mismatches"]) > limit:
        lines.append(f"- and {len(res['mismatches']) - limit} more mismatches")
    if res["failed_cases"]:
        lines.append("failed cases: " + ", ".join(res["failed_cases"][:20]))
    return "\n".join(lines)
