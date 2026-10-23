"""Deterministic checks: compile, lint, synth and the agent's own testbench. The LLM picks which to run; the tools
run here, and their output is cut down in code before the LLM sees it."""
import glob
import os
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

from .files import TB_ROOT
from .trace import truncate

CHECKS = ("compile", "lint", "synth", "testbench")
_INTERESTING = re.compile(r"(?i)(%error|%warning|error|warning|syntax|fail|assert|fatal|undeclared|unknown|mismatch)")
_TB_BAD = re.compile(r"(?i)\b(fail|failed|failure|error|fatal)\b")
# Tool processes run code the model wrote (a cocotb test is Python, with network access), so they never get the
# provider key or anything else that looks like a credential.
_SECRET_NAME = re.compile(r"(?i)(KEY|TOKEN|SECRET|PASSW|AUTH|CREDENTIAL|COOKIE|SESSION)")
MIN_TOOL_S = 5.0  # a check with less time than this left is skipped, not started


def tool_env():
    return {k: v for k, v in os.environ.items() if not _SECRET_NAME.search(k)}


def tool_user():
    """In the agent image (running as root), tools run as an unprivileged user, so model-written code cannot read
    the agent's own environment through /proc. Elsewhere (tests, local runs as a user) they run as the caller."""
    name = os.environ.get("CVDP_TOOL_USER", "")
    if not name or os.geteuid() != 0:
        return None
    try:
        import pwd

        pwd.getpwnam(name)
        return name
    except KeyError:
        return None


def detect_tools(sim_python="python3"):
    tools = {t: shutil.which(t) is not None for t in ("iverilog", "vvp", "verilator", "yosys")}
    try:
        r = subprocess.run([sim_python, "-c", "import cocotb, cocotb_tools, pytest"], capture_output=True, timeout=30,
                           env=tool_env())
        tools["cocotb"] = r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        tools["cocotb"] = False
    return tools


def summarise(output, limit=2500):
    """Keep the lines that matter (errors and warnings first, then the tail), never more than `limit` chars."""
    lines = output.splitlines()
    hits = [ln for ln in lines if _INTERESTING.search(ln)]
    seen, keep = set(), []
    for ln in hits[:30] + lines[-15:]:
        if ln not in seen:
            seen.add(ln)
            keep.append(ln)
    text = "\n".join(keep)
    head = f"[{len(lines)} lines, {len(hits)} with errors/warnings]\n"
    return head + truncate(text, limit)


class Checker:
    def __init__(self, root, tracer, tools, timeout_s=60.0, sim_python="python3", clock=time.monotonic,
                 time_left=None):
        self.time_left = time_left  # seconds this check may still use (the wall cap), or None for no limit
        self.user = tool_user()
        self.root = root
        self.tracer = tracer
        self.tools = tools
        self.timeout_s = timeout_s
        self.sim_python = sim_python
        self.clock = clock
        self.calls = 0
        self.tb_dir = os.path.join(root, TB_ROOT)

    def _run(self, name, cmd, cwd=None, timeout=None):
        timeout = timeout or self.timeout_s
        if self.time_left is not None:
            left = self.time_left()
            if left < MIN_TOOL_S:
                self.tracer.log("tool", check=name, command=" ".join(cmd), exit_code=None,
                                output=f"skipped: {left:.0f}s left before the wall cap")
                return None, "", f"skipped: only {left:.0f}s left before the wall-time cap"
            timeout = min(timeout, left)
        self.calls += 1
        t0 = self.clock()
        try:
            p = subprocess.run(cmd, cwd=cwd or self.root, capture_output=True, text=True, errors="replace",
                               timeout=timeout, env=tool_env(), user=self.user)
            rc, out = p.returncode, (p.stdout or "") + (p.stderr or "")
        except subprocess.TimeoutExpired as e:
            rc, out = 124, f"timeout after {timeout:.0f}s\n" + str(e.stdout or "")[-2000:]
        except OSError as e:
            rc, out = 127, str(e)
        summary = summarise(out)
        self.tracer.log("tool", check=name, command=" ".join(cmd), exit_code=rc,
                        latency_s=round(self.clock() - t0, 3), output=truncate(out, 4000))
        return rc, out, summary

    def _tb_dir_ready(self):
        os.makedirs(self.tb_dir, exist_ok=True)
        if self.user:  # the unprivileged tool user writes its build outputs here
            os.chmod(self.tb_dir, 0o777)

    def _sources(self):
        files = []
        for ext in ("*.sv", "*.v"):
            files += glob.glob(os.path.join(self.root, "rtl", "**", ext), recursive=True)
        files = sorted(set(files))
        incdirs = sorted({os.path.dirname(f) for f in files} | {os.path.join(self.root, "rtl")})
        return files, incdirs

    def run(self, names, tb=None):
        """Run the chosen checks. Compile always runs: the best-edit rule needs it."""
        names = ["compile"] + [n for n in names if n in CHECKS and n != "compile"]
        results = {}
        for n in dict.fromkeys(names):
            results[n] = getattr(self, "check_" + n)(tb) if n == "testbench" else getattr(self, "check_" + n)()
        return results

    def check_compile(self):
        if not self.tools.get("iverilog"):
            return {"ok": None, "summary": "iverilog not available"}
        files, inc = self._sources()
        if not files:
            return {"ok": False, "summary": "no .sv/.v files under rtl/"}
        self._tb_dir_ready()
        cmd = ["iverilog", "-g2012", "-o", os.path.join(self.tb_dir, "compile.vvp")]
        cmd += [f"-I{d}" for d in inc] + files
        rc, _, s = self._run("compile", cmd)
        return {"ok": _ok(rc), "exit_code": rc, "summary": s}

    def check_lint(self):
        if not self.tools.get("verilator"):
            return {"ok": None, "summary": "verilator not available"}
        files, inc = self._sources()
        if not files:
            return {"ok": False, "summary": "no .sv/.v files under rtl/"}
        cmd = ["verilator", "--lint-only", "-Wall", "-Wno-fatal", "-Wno-MULTITOP", "--timing"]
        cmd += [f"-I{d}" for d in inc] + files
        rc, _, s = self._run("lint", cmd)
        return {"ok": _ok(rc), "exit_code": rc, "summary": s}

    def check_synth(self):
        if not self.tools.get("yosys"):
            return {"ok": None, "summary": "yosys not available"}
        files, _ = self._sources()
        if not files:
            return {"ok": False, "summary": "no .sv/.v files under rtl/"}
        script = f"read_verilog -sv {' '.join(files)}; hierarchy -auto-top; proc; opt -fast; stat"
        rc, _, s = self._run("synth", ["yosys", "-q", "-p", script])
        return {"ok": _ok(rc), "exit_code": rc, "summary": s}

    def check_testbench(self, tb):
        if not tb or not tb.get("files"):
            return {"ok": None, "summary": "not run: your reply had no <tb> block (write one, or name one under verif/)"}
        self._tb_dir_ready()
        files, inc = self._sources()
        tb_files = [os.path.join(self.root, f) for f in tb["files"]]
        top = tb.get("top") or ""
        try:
            if any(f.endswith(".py") for f in tb_files):
                return self._cocotb(files, tb_files, top)
            return self._sv_tb(files, inc, tb_files, top)
        finally:
            for pat in ("**/*.vcd", "**/*.fst", "**/*.ghw"):
                for f in glob.glob(os.path.join(self.tb_dir, pat), recursive=True):
                    os.remove(f)

    def _sv_tb(self, files, inc, tb_files, top):
        if not self.tools.get("iverilog"):
            return {"ok": None, "summary": "iverilog not available"}
        out = os.path.join(self.tb_dir, "tb.vvp")
        cmd = ["iverilog", "-g2012", "-o", out] + (["-s", top] if top else [])
        cmd += [f"-I{d}" for d in inc] + files + [f for f in tb_files if f.endswith((".sv", ".v"))]
        rc, _, s = self._run("testbench_build", cmd)
        if rc is None:
            return {"ok": None, "summary": s}
        if rc != 0:
            return {"ok": False, "exit_code": rc, "summary": "testbench did not compile\n" + s}
        rc, text, s = self._run("testbench_run", ["vvp", "-n", out], cwd=self.tb_dir)
        ok = None if rc is None else (rc == 0 and not _TB_BAD.search(text))
        return {"ok": ok, "exit_code": rc, "summary": s}

    def _cocotb(self, files, tb_files, top):
        if not self.tools.get("cocotb") or not self.tools.get("iverilog"):
            return {"ok": None, "summary": "cocotb or iverilog not available"}
        py = [f for f in tb_files if f.endswith(".py")]
        module = os.path.splitext(os.path.basename(py[0]))[0]
        build = os.path.join(self.tb_dir, "sim_build")
        xml = os.path.join(self.tb_dir, "results.xml")
        if os.path.exists(xml):
            os.remove(xml)
        runner = os.path.join(self.tb_dir, "_run_cocotb.py")
        with open(runner, "w") as f:
            f.write(
                "from cocotb_tools.runner import get_runner\n"
                "r = get_runner('icarus')\n"
                f"r.build(sources={files!r}, hdl_toplevel={top!r}, build_dir={build!r}, always=True,"
                " timescale=('1ns', '1ps'))\n"
                f"r.test(hdl_toplevel={top!r}, test_module={module!r}, test_dir={self.tb_dir!r},"
                f" build_dir={build!r}, results_xml={xml!r})\n")
        rc, _, s = self._run("testbench_cocotb", [self.sim_python, runner], cwd=self.tb_dir,
                             timeout=max(self.timeout_s, 120))
        tests, failed = _junit_counts(xml)
        ok = None if rc is None else (rc == 0 and tests > 0 and failed == 0)
        shutil.rmtree(build, ignore_errors=True)
        return {"ok": ok, "exit_code": rc, "tests": tests, "failed": failed, "summary": s}


def _ok(rc):
    return None if rc is None else rc == 0


def _junit_counts(path):
    if not os.path.exists(path):
        return 0, 0
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return 0, 0
    cases = list(root.iter("testcase"))
    failed = sum(1 for c in cases if c.find("failure") is not None or c.find("error") is not None)
    return len(cases), failed


def render(results, limit=6000):
    """Check results as the LLM sees them."""
    parts = []
    for name, r in results.items():
        status = {True: "PASS", False: "FAIL", None: "SKIPPED"}[r.get("ok")]
        parts.append(f"## {name}: {status}\n{r.get('summary', '')}")
    return truncate("\n\n".join(parts), limit)
