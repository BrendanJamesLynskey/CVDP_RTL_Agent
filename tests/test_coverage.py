"""M4's problem-coverage record (docs/reports/m4/coverage.py): coverage.json and coverage.md agree with the ids files
and the committed run CSVs, and no held-out id is in the record. The dataset recomputation (--dataset-dir) is run by hand."""
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def test_coverage_record_checks_out():
    r = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "docs", "reports", "m4", "coverage.py")], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ok: coverage.json agrees" in r.stdout
