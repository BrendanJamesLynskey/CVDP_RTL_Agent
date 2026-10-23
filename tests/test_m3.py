"""M3: paired ablation statistics, the Pareto frontier, the failure taxonomy, log_check's sim_incomplete and the
sweep's seed_offset. No test needs an LLM."""
import csv
import json
import os
import subprocess
import xml.etree.ElementTree as ET

import pytest

import ablate
import collect
import log_check
import taxonomy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAX = os.path.join(ROOT, "tests", "fixtures", "taxonomy")


def rows(passes, run="r1", label="m", **kw):
    """Rows for problems p0..pN with the given pass string ("1101...")."""
    base = {"label": label, "cid": "cid003", "amba": "0", "wall_time_s": "10", "harness_agent_s": "",
            "prompt_tokens": "100", "completion_tokens": "10", "stop_reason": "submit", "cost_unreported_calls": "0",
            "cost_usd": "0.01", "seed": "1", **kw}
    return [dict(base, id=f"p{i}", _run=run, **{"pass": p}) for i, p in enumerate(passes)]


# ---------- ablate ----------

def test_paired_bootstrap_is_deterministic_and_covers_the_true_difference():
    # 100 problems: the arm gains 30, loses 10, ties 60, so the true mean difference is +0.20
    base = rows("0" * 30 + "1" * 10 + "01" * 30)
    arm = rows("1" * 30 + "0" * 10 + "01" * 30)
    p1, p2 = ablate.paired(arm, base), ablate.paired(arm, base)
    assert p1 == p2
    assert p1["effect"] == pytest.approx(0.20)
    assert p1["lo"] < 0.20 < p1["hi"] and p1["lo"] > 0  # covers the truth, and excludes 0 here
    assert (p1["better"], p1["worse"], p1["same"]) == (30, 10, 60)


def test_paired_uses_each_problems_pass_rate_over_runs():
    base = rows("10", run="a") + rows("10", run="b")
    arm = rows("11", run="c") + rows("10", run="d")  # p1 passes in one of the arm's two runs
    p = ablate.paired(arm, base)
    assert p["effect"] == pytest.approx((0 + 0.5) / 2) and (p["better"], p["worse"]) == (1, 0)


def test_sign_test_known_values():
    assert ablate.sign_test(8, 2) == pytest.approx(0.109375)  # 2 x (1 + 10 + 45) / 1024
    assert ablate.sign_test(10, 0) == pytest.approx(2 / 1024)
    assert ablate.sign_test(5, 5) == 1.0 and ablate.sign_test(0, 0) == 1.0


def test_arm_identical_to_base_has_no_detectable_effect_and_comes_first():
    base = rows("1100110011", run="b1")
    arms = {"base": base, "same": rows("1100110011", run="s1"), "better": rows("1111111111", run="x1")}
    md, _, pairs, _, _ = ablate.report(arms, "base")
    assert pairs["same"]["effect"] == 0 and (pairs["same"]["lo"], pairs["same"]["hi"]) == (0, 0)
    assert ablate.verdict(pairs["same"]) == "no detectable effect"
    body = md.split("#### Arms")[0]
    assert body.index("| same | no detectable effect") < body.index("| better |")


def test_pareto_frontier_on_a_hand_made_set():
    pts = {"cheap_weak": (0.001, 0.40), "mid": (0.005, 0.60), "dear_best": (0.010, 0.70),
           "dominated": (0.006, 0.55), "tie_cost_worse": (0.005, 0.50), "same_as_mid": (0.005, 0.60)}
    assert ablate.pareto(pts) == {"cheap_weak", "mid", "dear_best", "same_as_mid"}


def test_arms_grouped_by_label_and_settings_and_the_base_is_found(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    fields = ["label", "id", "seed", "pass", "cid", "self_check", "lint", "max_turns", "budget_usd", "cost_usd",
              "cost_unreported_calls", "wall_time_s", "prompt_tokens", "completion_tokens", "stop_reason"]
    for path, sc in ((a, "1"), (b, "0")):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for i in range(4):
                w.writerow({"label": "luna (reasoning default)", "id": f"p{i}", "seed": "1", "pass": str(i % 2),
                            "cid": "cid003", "self_check": sc, "lint": "1", "max_turns": "10", "budget_usd": "0.1",
                            "cost_usd": "0.002", "cost_unreported_calls": "0", "wall_time_s": "30",
                            "prompt_tokens": "1", "completion_tokens": "1", "stop_reason": "submit"})
    arms = ablate.arms_from(None, [str(a), str(b)])
    assert set(arms) == {"luna (reasoning default)", "luna (reasoning default) self_check=0"}
    assert ablate.pick_base(arms, None) == "luna (reasoning default)"
    svg_path, csv_path = tmp_path / "p.svg", tmp_path / "p.csv"
    ablate.main([str(a), str(b), "--pareto-svg", str(svg_path), "--pareto-csv", str(csv_path)])
    ET.parse(svg_path)  # well-formed SVG
    assert len(list(csv.DictReader(open(csv_path)))) == 2


def test_two_runs_of_an_arm_from_files_with_the_same_name_stay_two_runs(tmp_path):
    for d in ("x86", "arm"):
        (tmp_path / d).mkdir()
        with open(tmp_path / d / "r.csv", "w") as f:
            f.write("id,seed,pass,cid\np0,1,1,cid003\np1,1,0,cid003\n")
    arms = ablate.arms_from([f"a={tmp_path / 'x86' / 'r.csv'},{tmp_path / 'arm' / 'r.csv'}"], None)
    assert len(ablate.run_rates(arms["a"])) == 2


# ---------- taxonomy ----------

@pytest.fixture(scope="module")
def fixture_rows():
    rows_ = taxonomy.rows_from_work("fixture", os.path.join(TAX, "work"))
    for r in rows_:
        if r["pass"] != "1":
            r["_label"], r["_flags"] = taxonomy.label(r)
    return {r["id"]: r for r in rows_}


def test_each_label_fires_on_its_own_fixture_and_on_no_other(fixture_rows):
    for lb in taxonomy.LABELS:
        own = fixture_rows[f"cvdp_agentic_tax_{lb}_0001"]
        assert own["_label"] == lb, (lb, own["_label"], own["_flags"])
        # the review-round-1 fixtures each test one of these labels again on a different input
        extra = ("ambiguous", "partial", "harness_killed", "restored_best", "no_tests")
        others = [i for i, r in fixture_rows.items() if r.get("_label") == lb and i != own["id"]
                  and not any(i.startswith(f"cvdp_agentic_tax_{e}") for e in extra)]
        assert others == [], (lb, others)
    assert fixture_rows["cvdp_agentic_tax_passes_0001"]["pass"] == "1"


def test_flags_carry_the_other_rules_that_hold(fixture_rows):
    amb = fixture_rows["cvdp_agentic_tax_ambiguous_cap_mismatch_0001"]
    assert amb["_label"] == "stopped_by_cap" and "compile_fail_hidden" in amb["_flags"]
    assert "partial_pass" in fixture_rows["cvdp_agentic_tax_partial_selfcheck_passed_0001"]["_flags"]
    cap = fixture_rows["cvdp_agentic_tax_stopped_by_cap_0001"]
    assert "tests_failed_selfcheck_failed" in cap["_flags"]


def test_collect_writes_the_label_and_its_evidence(fixture_rows):
    rows_ = {r["id"]: r for r in collect.rows(os.path.join(TAX, "work", "seed1"))}
    hid = rows_["cvdp_agentic_tax_compile_fail_hidden_0001"]
    assert (hid["failure_label"], hid["log_class"], hid["own_compile_last"]) == ("compile_fail_hidden", "build_failed",
                                                                                 "pass")
    assert rows_["cvdp_agentic_tax_passes_0001"]["failure_label"] == ""
    assert rows_["cvdp_agentic_tax_no_edit_0001"]["rtl_changed"] == 0


def test_a_csv_without_evidence_labels_only_what_stop_reason_shows():
    assert taxonomy.label({"stop_reason": "submit", "pass": "0"})[0] == "needs_artifacts"
    assert taxonomy.label({"stop_reason": "max_turns", "pass": "0"})[0] == "stopped_by_cap"
    assert taxonomy.label({"stop_reason": "give_up", "pass": "0"})[0] == "gave_up"
    assert taxonomy.label({"stop_reason": "llm_error", "pass": "0"})[0] == "llm_error"


def test_hand_labels_agreement_and_excerpts_are_redacted(fixture_rows, monkeypatch):
    out = taxonomy.agreement(list(fixture_rows.values()), os.path.join(TAX, "hand_labels.csv"))
    assert "14/15 agree" in out and "stopped_by_cap ✗" in out
    key = "sk-or-v1-0123456789abcdef0123456789abcdef"
    r = dict(fixture_rows["cvdp_agentic_tax_llm_error_0001"])
    r["_paths"] = {"logs": [], "events": [{"kind": "llm", "node": "edit", "error": f"Bearer {key}"}]}
    ex = taxonomy.excerpt(r)
    assert key not in ex and len(ex.splitlines()) <= 10


def test_fixture_tree_matches_its_generator(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("make", os.path.join(TAX, "make.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    hand = os.path.join(TAX, "hand_labels.csv")
    before = open(hand).read()
    mod.main(str(tmp_path / "work"))
    assert open(hand).read() == before
    for dirpath, _, files in os.walk(tmp_path / "work"):
        for fn in files:
            p = os.path.join(dirpath, fn)
            committed = os.path.join(TAX, "work", os.path.relpath(p, tmp_path / "work"))
            assert open(p).read() == open(committed).read(), committed


# ---------- log_check ----------

def test_log_check_cut_off_cocotb_log_is_sim_incomplete():
    text = open(os.path.join(TAX, "work", "seed1", "cvdp_agentic_tax_sim_incomplete", "reports", "1.txt")).read()
    assert log_check.classify(text) == "sim_incomplete"
    assert log_check.classify(text + "=========== 1 failed in 600.1s ===========\n") == "tests_failed"
    harness = "docker: Error response from daemon: no such container\n"
    assert log_check.classify(harness) == "harness_error"
    ran = "============================= test session starts ==============================\n"
    assert log_check.classify(ran + "=========== no tests ran in 0.01s ===========\n") == "harness_error"


# ---------- seed_offset ----------

def test_seed_offset_two_and_one_seed_gives_seed_three_everywhere(tmp_path):
    from test_m2a import FAKE_HARNESS, PLAN, decide, edit

    cvdp = tmp_path / "cvdp"
    cvdp.mkdir()
    (cvdp / "run_benchmark.py").write_text(FAKE_HARNESS)
    (cvdp / "run_benchmark.py").chmod(0o755)
    data = tmp_path / "data"
    data.mkdir()
    (data / "agentic_code_generation_no_commercial.jsonl").write_text(
        json.dumps({"id": "cvdp_agentic_lfsr_0001", "categories": ["cid016", "easy"]}) + "\n")
    work = tmp_path / "work"
    script = json.dumps([{"text": PLAN, "cost": 0.001}, {"text": edit(), "cost": 0.001},
                         {"text": decide("submit"), "cost": 0.001}])
    env = dict(os.environ, SEEDS="1", SEED_OFFSET="2", MODEL="fake", THREADS="1", WORK=str(work),
               CVDP_DIR=str(cvdp), DATA_DIR=str(data), AGENT_IMAGE="unused", FAKE_SCRIPT=script,
               AGENT_PYTHONPATH=os.path.join(ROOT, "agent"), SEEN_ENV=str(tmp_path / "seen.jsonl"),
               OPENROUTER_API_KEY="")
    r = subprocess.run(["bash", os.path.join(ROOT, "tools", "sweep.sh")], env=env, capture_output=True, text=True,
                       timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (work / "seed3" / "raw_result.json").exists() and not (work / "seed1").exists()
    assert [json.loads(x)["CVDP_SEED"] for x in open(tmp_path / "seen.jsonl")] == ["3"]
    assert [row["seed"] for row in csv.DictReader(open(work / "results.csv"))] == ["3"]
    s = json.load(open(work / "seed3" / "cvdp_agentic_lfsr" / "harness" / "1" / "rundir" / "agent_out"
                       / "summary.json"))
    assert s["seed"] == "3"
    assert "Seed 3:" in (work / "table.md").read_text()
    run = json.load(open(str(work) + ".run.json"))
    assert run["seed_offset"] == 2 and list(run["seed_runs"]) == ["3"]


# ---------- review round 1 ----------

def test_harness_kill_with_null_log_falls_back_to_reports_n_txt(fixture_rows):
    """raw_result.json has "log": null and an error_msg; the log at reports/<n>.txt ends mid-cocotb."""
    r = fixture_rows["cvdp_agentic_tax_harness_killed_log_0001"]
    assert (r["log_class"], r["_label"]) == ("sim_incomplete", "sim_incomplete")


def test_harness_kill_with_no_log_at_all_is_a_harness_error(fixture_rows):
    r = fixture_rows["cvdp_agentic_tax_harness_killed_nolog_0001"]
    assert (r["log_class"], r["_label"]) == ("no_log", "harness_error") and "no_log" in r["_flags"]
    ex = taxonomy.excerpt(dict(r))
    assert "harness: Failed to execute objective harness" in ex


def test_failed_problem_with_no_tests_is_a_harness_error(fixture_rows):
    r = fixture_rows["cvdp_agentic_tax_no_tests_0001"]
    assert (r["log_class"], r["_label"]) == ("no_tests", "harness_error")


def test_unclassified_never_fires_on_the_fixtures(fixture_rows):
    labels = {r.get("_label") for r in fixture_rows.values() if r["pass"] != "1"}
    assert "unclassified" not in labels and "needs_artifacts" not in labels


def test_restored_best_compiled_edit_counts_as_own_compile_passed(fixture_rows):
    r = fixture_rows["cvdp_agentic_tax_restored_best_0001"]
    assert r["kept"] == "best_compiled_turn_1" and r["own_compile_last"] == "pass"
    assert r["_label"] == "compile_fail_hidden" and "best_edit_restored" in r["_flags"]
    ev = taxonomy.trace_evidence([], {"kept": "best_compiled_turn_2", "final_compiled": False,
                                      "files_changed": ["rtl/a.sv"]})
    assert ev["own_compile_last"] == "pass"


def test_stop_reasons_that_end_before_any_edit():
    base = {"pass": "0", "log_class": "tests_failed", "rtl_changed": "0", "selfcheck_runs": "0"}
    p, flags = taxonomy.label(dict(base, stop_reason="run_budget_exhausted"))
    assert p == "stopped_by_cap" and "no_edit" not in flags and "run_budget_exhausted" in flags
    p, flags = taxonomy.label(dict(base, stop_reason="no_task"))
    assert p == "agent_error" and "no_edit" not in flags and "no_task" in flags
    assert taxonomy.label(dict(base, stop_reason="submit"))[0] == "no_edit"


def test_pareto_keeps_lower_bound_arms_off_the_frontier():
    pts = {"a": (0.010, 0.50), "b": (0.020, 0.60), "lb_cheap": (0.005, 0.70)}
    assert ablate.pareto(pts) == {"lb_cheap"}  # if its cost were known
    assert ablate.pareto(pts, lower={"lb_cheap"}) == {"a", "b"}  # it is only a lower bound: neither on nor over
    out = ablate.svg(pts, {"a", "b"}, lower={"lb_cheap"})
    ET.fromstring(out)
    assert 'fill="#ffffff"' in out and "lb_cheap (≥$0.0050/problem)" in out


def test_pareto_table_marks_unreported_arms():
    base = rows("1100", run="b")
    lb = rows("1111", run="l")
    lb[0]["cost_unreported_calls"] = "1"
    md = ablate.report({"base": base, "lb": lb}, "base")[0]
    assert "| lb | ≥$0.0100 | 100.0% | n/a (cost a lower bound) |" in md and "drawn hollow" in md


def test_problems_dropped_from_the_paired_effect_are_listed():
    base = rows("1100")              # p0..p3
    arm = rows("11") + [dict(rows("1")[0], id="extra")]  # p0, p1 and one problem the base lacks
    md, _, pairs, _, _ = ablate.report({"base": base, "arm": arm}, "base")
    assert pairs["arm"]["arm_only"] == ["extra"] and pairs["arm"]["base_only"] == ["p2", "p3"]
    assert "- arm: 1 only in the arm (`extra`); 2 only in the base (`p2`, `p3`)" in md
    assert "| 2 | 3 |" in md  # 2 problems paired, 3 dropped


def test_log_check_collected_tests_and_no_summary_is_sim_incomplete():
    head = ("============================= test session starts ==============================\n"
            "platform linux -- Python 3.12.3, pytest-8.3.2\ncollected 3 items\n\nsrc/test_runner.py ")
    assert log_check.classify(head) == "sim_incomplete"  # pytest capturing output, then killed
    assert log_check.classify(head.replace("collected 3 items", "collected 0 items")) == "harness_error"
