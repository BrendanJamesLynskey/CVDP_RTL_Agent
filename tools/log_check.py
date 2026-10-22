"""Classify the harness's per-test logs (work/*/reports/<n>.txt): did each failure come from the tests running and
failing, or from something before the tests (a missing bundle, a harness or Docker error)?

  tests_failed   pytest ran the hidden tests and they failed (assertions, cocotb "Failed N of M tests")
  build_failed   the tests ran but the design did not compile or elaborate (e.g. a module the agent must write)
  harness_error  no test session: missing repository bundle, Docker or harness error, empty log
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


def classify(text):
    if not text.strip() or not _SESSION.search(text):
        return "harness_error"
    if _PASSED.search(text) and not _FAILED.search(text):
        return "passed"
    if _BUILD.search(text) and not re.search(r"Failed \d+ of \d+ tests|AssertionError", text):
        return "build_failed"
    if _FAILED.search(text):
        return "tests_failed"
    return "harness_error"


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


if __name__ == "__main__":
    main(sys.argv[1], "--excerpt" in sys.argv)
