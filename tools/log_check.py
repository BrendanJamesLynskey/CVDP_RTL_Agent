"""Classify the harness's per-test logs (work/*/reports/<n>.txt): did each failure come from the tests running and
failing, or from something before the tests (a missing bundle, a harness or Docker error)?

  tests_failed   pytest ran the hidden tests and they failed (assertions, cocotb "Failed N of M tests")
  build_failed   the tests ran but the design did not compile or elaborate (e.g. a module the agent must write)
  sim_incomplete pytest started and a simulation (cocotb / the simulator) was running, but the log ends with no
                 pytest summary: the simulation hung or was killed. The harness scores it as a failure.
  harness_error  no test session, or a session that ended with no result: missing repository bundle, Docker or
                 harness error, empty log
  passed         pytest reported only passes

Usage: python3 tools/log_check.py <work_dir> [--excerpt]   (markdown on stdout)
"""
import collections
import glob
import os
import re
import sys

_SESSION = re.compile(r"=+ test session starts =+")
_FAILED = re.compile(r"(\d+ failed|FAILED|Failed \d+ of \d+ tests|AssertionError)")
_BUILD = re.compile(r"(?i)(syntax error|unknown module|I give up|error: .*elaborat|Unable to bind|"
                    r"was not found|No such file or directory: '/code/rtl|%Error|CalledProcessError)")
_PASSED = re.compile(r"=+ \d+ passed")
# pytest's closing line ("=== 1 failed in 3.2s ===", "=== no tests ran in 0.1s ===")
_SUMMARY = re.compile(r"=+ .*\bin [\d.]+s\b.*=+|=+ no tests ran")
_SIM = re.compile(r"(?i)cocotb|running test|\bvvp\b|iverilog|verilator|sim(ulation)? (started|running)")


def classify(text):
    if not text.strip() or not _SESSION.search(text):
        return "harness_error"
    if _PASSED.search(text) and not _FAILED.search(text):
        return "passed"
    if _BUILD.search(text) and not re.search(r"Failed \d+ of \d+ tests|AssertionError", text):
        return "build_failed"
    if _FAILED.search(text):
        return "tests_failed"
    if not _SUMMARY.search(text) and _SIM.search(text):
        return "sim_incomplete"
    return "harness_error"


def build_errors(log_path, n=6):
    """For a build failure, the compiler's own messages: they go to rundir/{sim,build}.log, not to the report."""
    pdir = os.path.dirname(os.path.dirname(log_path))
    num = os.path.basename(log_path).split(".")[0].split("_")[0]
    out = []
    for name in ("build.log", "sim.log"):
        f = os.path.join(pdir, "harness", num, "rundir", name)
        if os.path.exists(f):
            out += [ln.strip()[:200] for ln in open(f, errors="replace")
                    if re.search(r"(?i)error|unknown|not found|unable|give up", ln)]
    return out[:n]


def excerpt(text, n=12):
    lines = [ln for ln in text.splitlines() if re.search(r"(?i)assert|fail|error|passed", ln)]
    return "\n".join(ln[:200] for ln in lines[:n])


def main(work, show):
    logs = sorted(f for f in glob.glob(os.path.join(work, "*", "reports", "*.txt")) if not f.endswith("_agent.txt"))
    kinds = collections.defaultdict(list)
    for f in logs:
        kinds[classify(open(f, errors="replace").read())].append(f)
    print(f"Per-test logs in `{work}`: {len(logs)}; " +
          ", ".join(f"{k} {len(v)}" for k, v in sorted(kinds.items())))
    if show:
        for k, v in sorted(kinds.items()):
            f = v[0]
            print(f"\n**{k}**, e.g. `{os.path.relpath(f, work)}`:\n```")
            print(excerpt(open(f, errors="replace").read()) or "(empty)")
            print("```")
        msgs = collections.Counter()
        for f in kinds.get("build_failed", []):
            for m in build_errors(f)[:1] or ["(no build.log/sim.log in rundir)"]:
                msgs[re.sub(r"\S*/", "", re.sub(r":\d+", "", m))[:110]] += 1
        if msgs:
            print("\n**build_failed**, first compiler message per log (paths and line numbers stripped):\n")
            for m, c in msgs.most_common(15):
                print(f"- {c} × `{m}`")
        for f in kinds.get("harness_error", []):
            text = open(f, errors="replace").read()
            first = " | ".join(ln.strip()[:120] for ln in text.splitlines()[:3]) or "(empty)"
            print(f"- harness_error `{os.path.relpath(f, work)}` ({len(text)} bytes): {first}")


if __name__ == "__main__":
    main(sys.argv[1], "--excerpt" in sys.argv)
