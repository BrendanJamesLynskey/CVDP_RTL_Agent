"""The problem browser's data (docs/problems.json) is reproducible from the committed CSVs and reports, passes
site/data/problems.py's checks, and carries no hidden-harness content. The story's pages in docs/ are what
site/story.html builds, carry derive.py's numbers, and keep every old section and glossary anchor reachable."""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "site"))
import build  # noqa: E402

SECTIONS = ["top", "how", "milestones", "m2", "m3", "m3b", "m3c", "ladder", "m3d", "fail", "dv", "compare",
            "validity", "next", "faq", "glossary"]  # the single page's 16 sections, before brief 16
STORY_FILES = [f for _, f, *_ in build.STORY]


def doc(f):
    return open(os.path.join(ROOT, "docs", f), encoding="utf-8").read()


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
    r = subprocess.run([sys.executable, os.path.join(ROOT, "site", "build.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_page_carries_derive_numbers():
    prose = json.load(open(os.path.join(ROOT, "site", "data", "story_data.json")))["m3b"]["prose"]
    seen = set()
    for f in STORY_FILES:
        for k, v in re.findall(r'<span data-d="(\w+)">([^<]*)</span>', doc(f)):
            assert prose[k] == v, f"{f}: data-d {k} = {v!r}, derive.py says {prose[k]!r}"
            seen.add(k)
    assert {"e3_model_e", "e3_harness_e", "proc_null", "spend_all"} <= seen


def test_theme_button_says_dark_light():
    for f in STORY_FILES + ["problems.html"]:
        t = doc(f)
        m = re.search(r'<button class="tbtn theme" id="theme"[^>]*>(.*?)</button>', t)
        assert m and re.sub(r"<[^>]+>", "", m.group(1)) == "DARK / LIGHT", f
        assert 'aria-pressed=' in m.group(0) and "SCOPE" not in t and "PAPER /" not in t, f


def test_problems_link_in_hero_and_bar():
    t = doc("index.html")
    hero = t[t.index('id="top"'):t.index("</section>", t.index('id="top"'))]
    assert re.search(r'<a class="way" href="problems.html">\s*<span class="wk">READ THE <span data-d="m3b_n">86</span> PROBLEMS', hero)
    for f in STORY_FILES:
        assert ">BROWSE PROBLEMS</a>" in doc(f), f
    assert 'href="./">&larr; Back to the story' in doc("problems.html")


def test_every_old_section_id_still_present():
    _, idmap = build.split_story()
    for sec in SECTIONS + ["m3e"]:
        assert sec in idmap, sec
        f = build.href(idmap[sec])
        f = "index.html" if f == "./" else f
        assert re.search(rf'<section class="sec[^"]*" id="{sec}"', doc(f)), (sec, f)


def test_old_anchors_forward_from_the_front_page():
    t = doc("index.html")
    m = re.search(r"var M=(\{.*?\});var P=(\[.*?\]);", t)
    fwd, pats = json.loads(m.group(1)), json.loads(m.group(2))
    _, idmap = build.split_story()
    for i, p in idmap.items():
        if p != "index":
            assert fwd[i] == build.href(p)
    assert fwd["m3d"] == "results-m3c-m3e.html" and fwd["how"] == "how.html"
    assert any(re.fullmatch(pat, "g-langgraph") and f == "reference.html" for pat, f in pats)


def test_cross_page_links_land():
    """Every in-story link #x points at a page that has id x (or builds it: glossary and FAQ ids on the reference page)."""
    ids = {f: set(re.findall(r'\sid="([\w.-]+)"', doc(f))) for f in STORY_FILES}
    built = re.compile(r"g-[\w-]+|q\d+")
    for f in STORY_FILES:
        for target, i in re.findall(r'href="([\w.-]*\.html|\./|)#([\w.-]+)"', doc(f)):
            if target == "problems.html":
                continue  # problem rows are built by the browser from problems.json
            page = f if target == "" else "index.html" if target == "./" else target
            assert i in ids[page] or (page == "reference.html" and built.fullmatch(i)), (f, target, i)
