"""M3c: the mutation-score gate before submit. Deterministic, no LLM.

When the agent is about to submit, its own testbench must kill at least half of N mutants of its design:
- no testbench ran in this problem: the gate fails ("write and run a testbench ... before submitting");
- the testbench is re-run on the design as it is; if it fails there, the gate fails;
- Yosys `mutate -list N -seed S` picks N mutations of the flattened design (MCY's method; MCY itself is not
  needed). All N go into one netlist with `mutate -ctrl mutsel 8 <i>`, behind a wrapper module with the design's
  name and ports that sets `mutsel` from a `+mutsel=<i>` plusarg, so the testbench is built once and run once per
  mutant. If the wrapper cannot drive the testbench (the unmutated wrapper, mutsel=0, must pass it), it falls back
  to one netlist and one build per mutant;
- a mutant is killed when the testbench fails on it (a hang counts: it timed out). Kill rate = killed / mutants
  that compiled. The gate passes at a kill rate of at least 0.5 with N = 12: equivalent mutants (a change the design
  cannot show at its ports) make 100% unreachable, which is why the threshold is not higher.
- bounds: the gate's own wall time (60 s); mutants not finished in it count as not killed (outcome "timeout").

Survivors are reported by their location and kind (from `mutate -list`), never by the mutated code. Outcomes:
no_tb, pass, fail, timeout, and skipped (the design or the testbench could not be mutated or driven: never blocks).
"""
import json
import os
import re
import shutil
import subprocess
import time

from .checks import _TB_BAD, _junit_counts, tool_env, tool_user
from .trace import truncate

NO_TB = "write and run a testbench for the specified behaviour before submitting"
GATE_DIR = os.path.join("rundir", "agent_tb", "mutation")
_MODULE = re.compile(r"(?m)^\s*module\s+([A-Za-z_]\w*)")


def parse_mutation(line):
    """{"mode", "module", "cell", "wire", "wirebit", "portbit", "src"} of one `mutate -list` line."""
    out, toks = {"src": []}, line.split()
    for i, t in enumerate(toks[:-1]):
        if t.startswith("-") and t[1:] in ("mode", "module", "cell", "port", "portbit", "ctrlbit", "wire", "wirebit"):
            out[t[1:]] = toks[i + 1]
        elif t == "-src":
            out["src"].append(toks[i + 1])
    return out


def describe(i, m):
    """A survivor as the agent sees it: kind and location, never the mutated code."""
    where = ", ".join(m["src"]) or "unknown location"
    cell = m.get("cell", "")
    ctype = re.match(r"\$\w+", cell).group(0) if re.match(r"\$\w+", cell) else "cell"
    on = f"wire `{m['wire']}` bit {m.get('wirebit', 0)}" if m.get("wire") else f"a {ctype} {m.get('port', '')} bit"
    return f"mutant {i}: {m.get('mode', '?')} on {on} ({where})"


def _int_literal(v):
    v = v.strip().replace("_", "")
    m = re.fullmatch(r"(?:\d+)?'[sS]?([bodhBODH])([0-9a-fA-FxXzZ]+)", v)
    if m:
        try:
            return int(m.group(2), {"b": 2, "o": 8, "d": 10, "h": 16}[m.group(1).lower()])
        except ValueError:
            return None
    return int(v) if re.fullmatch(r"\d+", v) else None


def _resolve(val, consts):
    """An override's value as an int: a literal, a testbench parameter or localparam with a literal value, or
    integer arithmetic (+ - * / % parentheses) over those. None otherwise."""
    v = _int_literal(val)
    if v is not None:
        return v
    expr = re.sub(r"(?:\d+)?'[sS]?[bodhBODH][0-9a-fA-F_]+",  # sized literals first: 'd8 is not a name
                  lambda m: str(_int_literal(m.group(0))) if _int_literal(m.group(0)) is not None else "?", val)
    expr = re.sub(r"[A-Za-z_]\w*", lambda m: str(consts[m.group(0)]) if m.group(0) in consts else "?", expr)
    if not re.fullmatch(r"[\d\s+\-*/%()]+", expr):
        return None
    try:
        out = eval(compile(expr.replace("/", "//"), "<param>", "eval"), {"__builtins__": {}}, {})
    except (SyntaxError, ZeroDivisionError, TypeError, ValueError):
        return None
    return out if isinstance(out, int) and out >= 0 else None


def _consts(text):
    """{name: int} of a testbench's parameters and localparams whose values resolve (in order of declaration)."""
    out = {}
    for name, val in re.findall(r"\b(?:local)?param(?:eter)?\s+(?:(?:int|integer|logic|bit)\s+)?"
                                r"(?:\[[^\]]*\]\s*)?([A-Za-z_]\w*)\s*=\s*([^;,)]+)", text):
        v = _resolve(val.strip(), out)
        if v is not None:
            out[name] = v
    return out


class MutationGate:
    def __init__(self, root, tracer, tools, n=12, seed=1, threshold=0.5, bound_s=60.0, clock=time.monotonic,
                 time_left=None, sim_python="python3", user=None):
        self.root = root
        self.tracer = tracer
        self.tools = tools
        self.n, self.seed, self.threshold, self.bound_s = n, seed, threshold, bound_s
        self.clock = clock
        self.time_left = time_left
        self.sim_python = sim_python
        self.user = user if user is not None else tool_user()
        self.dir = os.path.join(root, GATE_DIR)

    # ---------- plumbing ----------
    def _left(self):
        return self.deadline - self.clock()

    def _run(self, name, cmd, cwd=None, timeout=None):
        """(rc, output). rc 124: the command timed out on its own timeout (a hang); rc None: the gate's time ran out
        before or while it ran (cut by the gate's bound, not the command's fault)."""
        left = self._left()
        if left < 0.5:
            return None, "not run: the gate's time is up"
        clipped = timeout is None or timeout >= left
        timeout = min(timeout or left, left)
        t0 = time.monotonic()
        try:
            p = subprocess.run(cmd, cwd=cwd or self.root, capture_output=True, text=True, errors="replace",
                               timeout=timeout, env=tool_env(), user=self.user)
            rc, out = p.returncode, (p.stdout or "") + (p.stderr or "")
        except subprocess.TimeoutExpired as e:
            rc = None if clipped else 124
            out = (f"cut at the gate's bound after {timeout:.1f}s" if clipped else f"timeout after {timeout:.1f}s") \
                + "\n" + str(e.stdout or "")[-1000:]
        except OSError as e:
            rc, out = 127, str(e)
        self.tracer.log("tool", check=name, command=truncate(" ".join(cmd), 400), exit_code=rc,
                        latency_s=round(time.monotonic() - t0, 3), output=truncate(out, 1500))
        return rc, out

    def _sources(self):
        files = []
        for dirpath, _, filenames in os.walk(os.path.join(self.root, "rtl")):
            for fn in sorted(filenames):
                if fn.endswith((".sv", ".v")):
                    files.append(os.path.relpath(os.path.join(dirpath, fn), self.root))
        files = sorted(files)
        inc = sorted({os.path.dirname(f) for f in files} | {"rtl"})
        return files, inc

    def _fresh_dir(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        os.makedirs(self.dir, exist_ok=True)
        if self.user:
            for d in (os.path.dirname(self.dir), self.dir):
                os.chmod(d, 0o777)

    # ---------- the testbench ----------
    def _dut(self, tb, files):
        """The design module the testbench drives, and the parameters it sets (None if they are not literals)."""
        mods = []
        for f in files:
            try:
                mods += _MODULE.findall(open(os.path.join(self.root, f), errors="replace").read())
            except OSError:
                continue
        if tb["kind"] == "cocotb":
            return (tb["top"] if tb["top"] in mods else None), {}
        text = "\n".join(open(os.path.join(self.root, f), errors="replace").read() for f in tb["files"])
        text = re.sub(r"//[^\n]*|/\*.*?\*/", " ", text, flags=re.DOTALL)
        consts = _consts(text)
        for m in sorted(set(mods), key=len, reverse=True):
            hit = re.search(rf"(?<![\w.$]){re.escape(m)}\s*(#\s*\(((?:[^()]|\([^()]*\))*)\))?\s*[A-Za-z_]\w*\s*\(",
                            text)
            if hit:
                params = {}
                for name, val in re.findall(r"\.(\w+)\s*\(\s*([^()]*?)\s*\)", hit.group(2) or ""):
                    v = _resolve(val, consts)
                    if v is None:
                        return m, None
                    params[name] = v
                return m, params
        return None, {}

    def _sim(self, name, tb, sources, plusarg=None, timeout=None, build_tag="base"):
        """Build (once per build_tag) and run the testbench on `sources`: (result, seconds), result True (it
        passed), False (it failed, or hung past its own timeout), "not_compiled" or "time_up" (the gate's bound)."""
        t0 = time.monotonic()
        build = os.path.join(self.dir, f"build_{build_tag}")

        def done(r):
            return r, time.monotonic() - t0

        if tb["kind"] == "sv":
            out = build + ".vvp"
            if not os.path.exists(out):
                files, inc = self._sources()
                cmd = ["iverilog", "-g2012", "-o", out] + (["-s", tb["top"]] if tb["top"] else [])
                cmd += [f"-I{os.path.join(self.root, d)}" for d in inc] + sources
                cmd += [f for f in tb["paths"] if f.endswith((".sv", ".v"))]
                rc, _ = self._run(f"gate_build_{name}", cmd)
                if rc is None:
                    return done("time_up")
                if rc != 0:
                    return done("not_compiled")
            cmd = ["vvp", "-n", out] + ([f"+mutsel={plusarg}"] if plusarg is not None else [])
            rc, text = self._run(f"gate_run_{name}", cmd, cwd=self.dir, timeout=timeout)
            if rc is None:
                return done("time_up")
            return done(rc == 0 and not _TB_BAD.search(text))
        py = [f for f in tb["paths"] if f.endswith(".py")][0]
        runner = os.path.join(self.dir, "_gate_cocotb.py")
        if not os.path.exists(runner):
            with open(runner, "w") as f:
                f.write("import json, sys\nfrom cocotb_tools.runner import get_runner\na = json.loads(sys.argv[1])\n"
                        "r = get_runner('icarus')\nif a['mode'] == 'build':\n"
                        "    r.build(sources=a['sources'], hdl_toplevel=a['top'], build_dir=a['build'], always=True,"
                        " timescale=('1ns', '1ps'))\nelse:\n"
                        "    r.test(hdl_toplevel=a['top'], test_module=a['module'], test_dir=a['test_dir'],"
                        " build_dir=a['build'], results_xml=a['xml'], plusargs=a['plusargs'])\n")
        args = {"top": tb["top"], "build": build, "sources": sources}
        if not os.path.isdir(build):
            rc, _ = self._run(f"gate_build_{name}", [self.sim_python, runner, json.dumps({**args, "mode": "build"})],
                              cwd=self.dir)
            if rc is None:
                return done("time_up")
            if rc != 0:
                return done("not_compiled")
        xml = os.path.join(self.dir, f"results_{name}.xml")
        args.update(mode="test", module=os.path.splitext(os.path.basename(py))[0], test_dir=os.path.dirname(py),
                    xml=xml, plusargs=[f"+mutsel={plusarg}"] if plusarg is not None else [])
        rc, _ = self._run(f"gate_run_{name}", [self.sim_python, runner, json.dumps(args)], cwd=self.dir,
                          timeout=timeout)
        if rc is None:
            return done("time_up")
        tests, failed = _junit_counts(xml)
        return done(rc == 0 and tests > 0 and failed == 0)

    # ---------- Yosys ----------
    def _yosys(self, name, script):
        path = os.path.join(self.dir, f"{name}.ys")
        with open(path, "w") as f:
            f.write("\n".join(script) + "\n")
        rc, out = self._run(f"gate_yosys_{name}", ["yosys", "-q", "-s", path])
        return rc == 0, out

    def _read(self, files, inc, top, params):
        return ([f"read_verilog -sv {' '.join('-I' + d for d in inc)} {' '.join(files)}"]
                + [f"chparam -set {k} {v} {top}" for k, v in sorted(params.items())]
                + [f"prep -flatten -top {top}"])

    @staticmethod
    def _param_header(params):
        """The `#(parameter ...)` a module needs so the testbench's overrides compile; the netlist is already
        elaborated at these values (chparam), so they are only accepted, never used."""
        return ("#(" + ", ".join(f"parameter {k} = {v}" for k, v in sorted(params.items())) + ") ") if params else ""

    def _add_params(self, path, top, params):
        if not params:
            return
        with open(path) as f:
            text = f.read()
        head = self._param_header(params)
        text = re.sub(rf"(?m)^(module\s+{re.escape(top)})\s*\(", lambda m: f"{m.group(1)} {head}(", text, count=1)
        with open(path, "w") as f:
            f.write(text)

    def _wrapper(self, top, ports, params=None):
        decl, conn = [], []
        for name, p in ports.items():
            if name == "mutsel":
                continue
            w = len(p["bits"])
            rng = f"[{w - 1}:0] " if w > 1 else ""
            decl.append(f"  {p['direction']} wire {rng}{name}")
            conn.append(f".{name}({name})")
        return (f"module {top} {self._param_header(params or {})}(\n" + ",\n".join(decl) + "\n);\n  reg [7:0] mutsel;\n"
                "  initial if (!$value$plusargs(\"mutsel=%d\", mutsel)) mutsel = 8'd0;\n"
                f"  {top}__mutsel u_mutsel ({', '.join(conn + ['.mutsel(mutsel)'])});\nendmodule\n")

    # ---------- the gate ----------
    def run(self, tb):
        t0 = self.clock()
        bound = self.bound_s if self.time_left is None else min(self.bound_s, max(0.0, self.time_left() - 5.0))
        self.deadline = t0 + bound
        res = {"outcome": None, "passed": False, "generated": 0, "compiled": 0, "killed": 0, "unfinished": 0,
               "method": None, "survivors": [], "note": ""}
        try:
            self._gate(tb, res)
        finally:
            res["wall_s"] = round(self.clock() - t0, 2)
            shutil.rmtree(self.dir, ignore_errors=True)
        res["summary"] = self._summary(res)
        res["ok"] = None if res["outcome"] == "skipped" else bool(res["passed"])
        self.tracer.log("gate", **{k: v for k, v in res.items() if k != "summary"})
        return res

    def _skip(self, res, why):
        res.update(outcome="skipped", passed=True, note=why)

    def _gate(self, tb, res):
        if not tb or not tb.get("files"):
            res.update(outcome="no_tb", note=NO_TB)
            return
        if not (self.tools.get("yosys") and self.tools.get("iverilog")):
            return self._skip(res, "yosys or iverilog not available")
        if self._left() < min(5.0, 0.5 * self.bound_s):
            return self._skip(res, "no time left for the gate before the wall-time cap")
        paths = [os.path.join(self.root, f) for f in tb["files"]]
        tb = {"files": tb["files"], "paths": paths, "top": tb.get("top") or "",
              "kind": "cocotb" if any(f.endswith(".py") for f in paths) else "sv"}
        if tb["kind"] == "cocotb" and not self.tools.get("cocotb"):
            return self._skip(res, "cocotb not available")
        self._fresh_dir()
        files, inc = self._sources()
        if not files:
            return self._skip(res, "no .sv/.v files under rtl/")
        top, params = self._dut(tb, files)
        if top is None:
            return self._skip(res, "could not tell which module of rtl/ the testbench drives")
        if params is None:
            return self._skip(res, f"the testbench sets parameters of `{top}` to values that are not literals")
        mlist = os.path.join(self.dir, "mutations.txt")
        ok, _ = self._yosys("list", self._read(files, inc, top, params)
                            + [f"mutate -list {self.n} -seed {self.seed} -o {mlist}"])
        lines = [ln.strip() for ln in open(mlist)] if ok and os.path.exists(mlist) else []
        lines = [ln for ln in lines if ln.startswith("mutate ") and "-mode none" not in ln]
        if not lines:
            return self._skip(res, "Yosys could not read or mutate the design" if not ok else "no mutation found")
        res["generated"] = len(lines)
        muts = [parse_mutation(ln) for ln in lines]
        # the testbench on the design as it is: it must pass there
        base, secs = self._sim("design", tb, [os.path.join(self.root, f) for f in files])
        if base == "time_up":
            return self._timeout(res, muts, 1, "the testbench did not finish on your design in the gate's time")
        if base is not True:
            res.update(outcome="fail", note="your testbench does not pass on the design you are submitting: fix the "
                                            "design or the testbench, run it, then submit")
            return
        per = max(3.0, 5.0 * secs + 1.0)  # a mutant that runs longer than this hangs: killed
        if not self._wrapped(tb, files, inc, top, params, lines, muts, per, res):
            self._per_mutant(tb, files, inc, top, params, lines, muts, per, res)

    def _timeout(self, res, muts, first, why):
        """Mutants first..N not finished in the gate's bound: counted as compiled and not killed."""
        rest = len(muts) - first + 1
        res["unfinished"] += rest
        res["compiled"] += rest
        res["survivors"] += [describe(j, m) + " (not run: the gate's time ran out)"
                             for j, m in enumerate(muts[first - 1:], first)]
        res["outcome"] = "timeout"
        res["note"] = why
        res["passed"] = res["killed"] / res["compiled"] >= self.threshold

    def _kill_loop(self, res, muts, sim):
        for i, m in enumerate(muts, 1):
            r = sim(i) if self._left() >= 0.5 else "time_up"
            if r == "time_up":
                return self._timeout(res, muts, i, f"{len(muts) - i + 1} mutant(s) not finished in the gate's "
                                                   f"{self.bound_s:g} s, counted as not killed")
            if r == "not_compiled":
                continue
            res["compiled"] += 1
            if r is True:
                res["survivors"].append(describe(i, m))
            else:
                res["killed"] += 1
        res["passed"] = res["compiled"] > 0 and res["killed"] / res["compiled"] >= self.threshold
        res["outcome"] = "pass" if res["passed"] else "fail"
        if not res["compiled"]:
            res["note"] = "no mutant compiled with your testbench"

    def _wrapped(self, tb, files, inc, top, params, lines, muts, per, res):
        """One netlist with every mutant behind mutsel. True when it drove the testbench (the result is in res)."""
        net = os.path.join(self.dir, "mutants.v")
        pj = os.path.join(self.dir, "ports.json")
        script = self._read(files, inc, top, params)
        script += [ln.replace("mutate ", f"mutate -ctrl mutsel 8 {i} ", 1) for i, ln in enumerate(lines, 1)]
        script += [f"rename {top} {top}__mutsel", f"write_verilog -noattr {net}", f"write_json {pj}"]
        ok, _ = self._yosys("ctrl", script)
        if not ok:
            return False
        try:
            ports = json.load(open(pj))["modules"][f"{top}__mutsel"]["ports"]
        except (OSError, ValueError, KeyError):
            return False
        wrap = os.path.join(self.dir, "wrapper.v")
        with open(wrap, "w") as f:
            f.write(self._wrapper(top, ports, params))
        base, _ = self._sim("mutsel0", tb, [net, wrap], plusarg=0, timeout=per, build_tag="ctrl")
        if base == "time_up":
            self._timeout(res, muts, 1, "the gate's time ran out before the mutants ran")
            return True
        if base is not True:
            self.tracer.log("tool", check="gate_wrapper", command="mutsel=0", exit_code=1,
                            output="the wrapper did not drive the testbench; one build per mutant instead")
            return False
        res["method"] = "wrapper"
        self._kill_loop(res, muts, lambda i: self._sim(f"mutant{i}", tb, [net, wrap], plusarg=i, timeout=per,
                                                       build_tag="ctrl")[0])
        return True

    def _per_mutant(self, tb, files, inc, top, params, lines, muts, per, res):
        script = self._read(files, inc, top, params)
        script += ["design -save base", f"write_verilog -noattr {self.dir}/m0.v"]
        for i, ln in enumerate(lines, 1):
            script += ["design -load base", ln, f"write_verilog -noattr {self.dir}/m{i}.v"]
        ok, _ = self._yosys("each", script)
        if not ok:
            return self._skip(res, "Yosys could not write the mutants")
        for i in range(len(lines) + 1):
            if os.path.exists(os.path.join(self.dir, f"m{i}.v")):
                self._add_params(os.path.join(self.dir, f"m{i}.v"), top, params)
        base, _ = self._sim("m0", tb, [os.path.join(self.dir, "m0.v")], timeout=per, build_tag="m0")
        if base == "time_up":
            return self._timeout(res, muts, 1, "the gate's time ran out before the mutants ran")
        if base is not True:
            return self._skip(res, "the testbench does not pass on the unmutated netlist (it may read internal "
                                   "signals or set parameters the netlist lacks)")
        res["method"] = "per_mutant"

        def sim(i):
            path = os.path.join(self.dir, f"m{i}.v")
            if not os.path.exists(path):
                return "not_compiled"
            return self._sim(f"mutant{i}", tb, [path], timeout=per, build_tag=f"m{i}")[0]

        self._kill_loop(res, muts, sim)

    def _summary(self, r):
        if r["outcome"] == "no_tb":
            return f"mutation gate: FAIL: no testbench of yours ran in this problem: {NO_TB}."
        if r["outcome"] == "skipped":
            return f"mutation gate: not applied ({r['note']})"
        if r["outcome"] == "fail" and not r["compiled"]:
            return f"mutation gate: FAIL: {r['note']}"
        rate = r["killed"] / r["compiled"] if r["compiled"] else 0.0
        head = (f"mutation gate: {'PASS' if r['passed'] else 'FAIL'}: your testbench detected {r['killed']} of "
                f"{r['compiled']} mutants of your design (kill rate {rate:.2f}; the gate needs {self.threshold:.2f})."
                + (f" {r['note']}." if r["note"] else ""))
        if r["passed"]:
            return head
        return "\n".join([head, "Each mutant changes one signal of your design; a testbench that checks the specified "
                                "behaviour fails on most of them. Not detected (kind and location):"]
                         + [f"- {s}" for s in r["survivors"][:12]]
                         + ["Strengthen the testbench to check the behaviour at these places (a few mutants may not "
                            "change the behaviour at all), run it, then submit."])
