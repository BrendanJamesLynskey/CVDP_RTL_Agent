"""The problem browser's data (docs/problems.json) is reproducible from the committed CSVs and reports, passes
site/data/problems.py's checks, and carries no hidden-harness content."""
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_problems_json_matches_csvs_and_reports():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "site", "data", "problems.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_problems_json_has_no_harness_or_solution_files():
    data = json.load(open(os.path.join(ROOT, "docs", "problems.json")))
    text = json.dumps(data)
    for needle in ("VERILOG_SOURCES", "test_runner.py", "docker-compose", "import cocotb", "harness/"):
        assert needle not in text
    for p in data["problems"]:
        assert set(p["task"]) == {"prompt", "docs", "given"}
        assert all(set(g) == {"path", "lines"} for g in p["task"]["given"])  # names and sizes, never code
        assert all(d["path"].startswith("docs/") for d in p["task"]["docs"])
    assert sum(p["eval"] for p in data["problems"]) == 86 and len(data["problems"]) == 92


def test_built_pages_are_current():
    for src, out in (("story.html", "index.html"), ("problems.html", "problems.html")):
        body = open(os.path.join(ROOT, "site", src), encoding="utf-8").read().rstrip()
        assert body in open(os.path.join(ROOT, "docs", out), encoding="utf-8").read(), f"run python3 site/build.py ({out})"
