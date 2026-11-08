"""M3l: arm E (retrieved real-RTL examples) on the plain API loop. Fake client, fixture files and a synthetic pack only;
no model and no network."""
import builtins
import hashlib
import json
import os
import subprocess
import sys

import collect
import leak_guard
import pytest
from cvdp_agent import apiloop, examples as X
from cvdp_agent.config import Config, from_env
from test_m3h import sweep
from test_m3j import KEY, FakeClient, api_cfg, block, reply

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHA = "a" * 40
SHA2 = "b" * 40
PRIVATE = ("PRIVATE-PROSE: a pointer is converted to Gray code before it crosses the clock boundary, because only one "
           "bit changes between neighbours and a late sample is therefore off by at most one.")
GRAY = ("// Copyright 2018 Fixture University.\n// Licensed under the fixture licence.\n\n"
        "module gray_conv #(\n    parameter int unsigned Width = 4\n)(\n    input  logic [Width-1:0] bin_i,\n"
        "    output logic [Width-1:0] gray_o\n);\n    logic [Width:0] ext;\n    assign ext    = {1'b0, bin_i};\n"
        "    assign gray_o = bin_i ^ ext[Width:1];\nendmodule\n")
FIFO = ("// Copyright 2019 Fixture University.\n\nmodule sync_fifo #(\n    parameter int Depth = 8\n)(\n    input logic clk_i,\n"
        "    input logic rst_ni,\n    input logic push_i,\n    input logic pop_i,\n    output logic full_o,\n"
        "    output logic empty_o\n);\n    logic [3:0] wr_q, rd_q;\n    always_ff @(posedge clk_i or negedge rst_ni) begin\n"
        "        if (!rst_ni) begin\n            wr_q <= '0;\n            rd_q <= '0;\n        end else begin\n"
        "            if (push_i && !full_o) wr_q <= wr_q + 1;\n            if (pop_i && !empty_o) rd_q <= rd_q + 1;\n"
        "        end\n    end\n    assign full_o  = (wr_q - rd_q) == Depth;\n    assign empty_o = wr_q == rd_q;\nendmodule\n")
DENIED = "// Copyright 2020 Somebody.\nmodule denied_mod(input logic a, output logic y);\n  assign y = a;\nendmodule\n"
FILES = {  # (repo, sha, path) -> text
    ("fixture/cells", SHA, "src/gray_conv.sv"): GRAY,
    ("fixture/cells", SHA, "src/sync_fifo.sv"): FIFO,
    ("pulp-platform/common_cells", SHA2, "src/denied_mod.sv"): DENIED,
    ("someone/cheriot-ibex", SHA2, "rtl/ibex_x.sv"): DENIED,
    ("openhwgroup/cva6", SHA2, "core/c.sv"): DENIED,
}
ENTRIES = [
    dict(id="fx-gray", title="Binary to Gray code converter", section="cdc", also=["fifo"], repo="fixture/cells",
         sha=SHA, path="src/gray_conv.sv", lines="4-13", licence="FX-1.0", module="gray_conv",
         keywords=["gray", "pointer", "async fifo", "xor"], ports=["bin_i:input:[Width-1:0]"], params=["Width"],
         whole_module=True, notice="Copyright 2018 Fixture University."),
    dict(id="fx-fifo", title="Synchronous FIFO with full and empty flags", section="fifo", also=[], repo="fixture/cells",
         sha=SHA, path="src/sync_fifo.sv", lines="3-6,20-21", licence="FX-1.0", module="sync_fifo",
         keywords=["fifo", "full", "empty", "pointer"], ports=["clk_i:input:1"], params=["Depth"], whole_module=True,
         notice="Copyright 2019 Fixture University."),
    dict(id="px-denied", title="Denied pulp module", section="cdc", also=[], repo="pulp-platform/common_cells",
         sha=SHA2, path="src/denied_mod.sv", lines="2-4", licence="SHL", module="denied_mod", keywords=["gray"],
         ports=[], params=[], whole_module=True, notice="Copyright 2020 Somebody."),
    dict(id="ib-denied", title="Denied ibex fork module", section="cdc", also=[], repo="someone/cheriot-ibex",
         sha=SHA2, path="rtl/ibex_x.sv", lines="2-4", licence="Apache-2.0", module="denied_mod", keywords=["gray"],
         ports=[], params=[], whole_module=True, notice="Copyright 2020 Somebody."),
    dict(id="cva6-denied", title="Denied cva6 module", section="cdc", also=[], repo="openhwgroup/cva6", sha=SHA2,
         path="core/c.sv", lines="2-4", licence="Apache-2.0", module="denied_mod", keywords=["gray"], ports=[],
         params=[], whole_module=True, notice="Copyright 2020 Somebody."),
]


def entry_md(e, text):
    runs = X.slice_runs(text, e["lines"])
    return (f"# {e['title']}\n\n## Pattern\n\n{PRIVATE} ({e['id']})\n\n## Excerpt\n\nLines {e['lines']} of `{e['path']}`.\n\n"
            f"```systemverilog\n{runs}```\n\n## When to use it\n\n- {PRIVATE} again, for {e['id']}.\n\n## Source\n\n"
            f"```yaml\nrepo: {e['repo']}\nsha: {e['sha']}\npath: {e['path']}\nlines: {e['lines']}\nlicence: {e['licence']}\n"
            f"notice: \"{e['notice']}\"\nmodule: {e['module']}\nwhole_module: true\n```\n")


def make_ref(tmp_path, entries=ENTRIES, name="ref"):
    """A synthetic reference/ layer (INDEX.jsonl, entries, manifest) and its pin table; the upstream fixture files."""
    ref = tmp_path / name / "reference"
    up = tmp_path / name / "upstream"
    ref.mkdir(parents=True)
    (ref / "README.md").write_text("# reference/ fixture\n\n" + PRIVATE + "\n")
    (ref / "SOURCES.yaml").write_text("version: 1\nrepos: {}\n")
    with open(ref / "INDEX.jsonl", "w") as f:
        for e in entries:
            f.write(json.dumps({**e, "bytes": 100}) + "\n")
            d = ref / e["section"]
            d.mkdir(exist_ok=True)
            (d / (e["id"] + ".md")).write_text(entry_md(e, FILES[(e["repo"], e["sha"], e["path"])]))
    for (repo, sha, path), text in FILES.items():
        p = up / repo / sha / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    lines = []
    for p in sorted(ref.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.sha256":
            lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ref)}")
    (ref / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
    pins = {"v9.9": {"commit": "c" * 40, "entries": len(entries),
                     "manifest_sha256": hashlib.sha256((ref / "MANIFEST.sha256").read_bytes()).hexdigest()}}
    return ref, pins, up


def fixture_fetch(up, log=None):
    def f(repo, sha, path):
        if log is not None:
            log.append((repo, sha, path))
        return (up / repo / sha / path).read_bytes()
    return f


@pytest.fixture
def bundle(tmp_path):
    ref, pins, up = make_ref(tmp_path)
    b, rep = X.build_bundle(str(ref), "v9.9", fixture_fetch(up), pins)
    return b, rep, ref, pins, up


GRAY_TASK = "Design a Gray code converter module for an async FIFO pointer that crosses a clock boundary."


# ---------- the repo deny-list and the bundle ----------

def test_repo_deny_list_names():
    for r in ("openhwfoundation/cv32e40p", "openhwgroup/cva6", "openhwgroup/cv32e40p", "openhwfoundation/cva6",
              "lowRISC/ibex", "pulp-platform/axi", "pulp-platform/common_cells", "pulp-platform/anything",
              "someone/cheriot-ibex", "lowRISC/Ibex-fork"):
        assert X.repo_denied(r), r
    for r in ("lowRISC/opentitan", "chipsalliance/caliptra-rtl", "nvdla/hw", "Xilinx/open-nic-shell", "fixture/cells"):
        assert not X.repo_denied(r), r


def test_bundle_withholds_denied_repos_fetches_once_and_records_sha256(tmp_path):
    ref, pins, up = make_ref(tmp_path)
    log = []
    b, rep = X.build_bundle(str(ref), "v9.9", fixture_fetch(up, log), pins)
    assert [e["id"] for e in b["entries"]] == ["fx-gray", "fx-fifo"]
    assert sorted(b["repo_denied_ids"]) == ["cva6-denied", "ib-denied", "px-denied"] and b["repo_denied_n"] == 3
    assert not any(r in ("pulp-platform/common_cells", "someone/cheriot-ibex", "openhwgroup/cva6") for r, _, _ in log)
    assert len(log) == len(set(log)) == 2                                  # once per file
    assert b["files"][f"fixture/cells@{SHA}:src/gray_conv.sv"] == hashlib.sha256(GRAY.encode()).hexdigest()
    gray = b["entries"][0]
    assert gray["shown_kind"] == "module" and gray["shown"].startswith("module gray_conv") \
        and gray["shown"].rstrip().endswith("endmodule")
    assert "PRIVATE" not in json.dumps(b)                                  # no pack prose in the bundle


def test_bundle_refuses_a_layer_that_is_not_the_pinned_one(tmp_path):
    ref, pins, up = make_ref(tmp_path)
    (ref / "README.md").write_text("changed\n")
    with pytest.raises(X.ExamplesError, match="does not match the manifest"):
        X.build_bundle(str(ref), "v9.9", fixture_fetch(up), pins)
    ref2, pins2, up2 = make_ref(tmp_path, name="ref2")
    with pytest.raises(X.ExamplesError, match="unknown pack tag"):
        X.build_bundle(str(ref2), "v1.0", fixture_fetch(up2), pins2)
    bad = json.loads(json.dumps(pins2))
    bad["v9.9"]["manifest_sha256"] = "0" * 64
    with pytest.raises(X.ExamplesError, match="pinned"):
        X.build_bundle(str(ref2), "v9.9", fixture_fetch(up2), bad)


def test_an_excerpt_that_is_not_in_the_fetched_file_is_dropped(tmp_path):
    ref, pins, up = make_ref(tmp_path)
    def tampered(repo, sha, path):
        return (up / repo / sha / path).read_bytes().replace(b"gray_o = bin_i", b"gray_o = ~bin_i")
    b, rep = X.build_bundle(str(ref), "v9.9", tampered, pins)
    assert "fx-gray" not in [e["id"] for e in b["entries"]] and rep["dropped"][0][0] == "fx-gray"


def test_the_real_pack_bundle_when_it_is_checked_out(tmp_path):
    pack = os.environ.get("RTL_PACK_CHECKOUT") or os.path.join(ROOT, "..", "RTL_Knowledge_Pack")
    clones = "/home/brendan/rtl_corpus_src"
    if not os.path.isdir(os.path.join(pack, "reference")) or not os.path.isdir(clones):
        pytest.skip("the private pack and the corpus clones are not on this machine")
    out = tmp_path / "bundle.json"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "fetch_examples.py"),
                        os.path.join(pack, "reference"), "v4.0", str(out), "--local-clones", clones],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    b = json.load(open(out))
    assert b["index_n"] == 86 and b["repo_denied_n"] == 49 and len(b["entries"]) == 37 and not b["dropped"]
    assert all(not X.repo_denied(e["repo"]) for e in b["entries"])


def test_fetch_cli_with_a_fixture_prints_counts_and_writes_the_upstream_files(tmp_path):
    ref, pins, up = make_ref(tmp_path)
    (tmp_path / "pins.json").write_text(json.dumps(pins))
    env = dict(os.environ, EXAMPLES_PINS=str(tmp_path / "pins.json"), EXAMPLES_FETCH_DIR=str(up))
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "fetch_examples.py"), str(ref), "v9.9",
                        str(tmp_path / "b.json"), "--upstream-dir", str(tmp_path / "upstream_out")], env=env,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "3 withheld by the repo deny-list" in r.stdout and "2 kept from 2 upstream files" in r.stdout
    assert "PRIVATE" not in r.stdout
    got = sorted(os.listdir(tmp_path / "upstream_out"))
    assert got == sorted(hashlib.sha256(t.encode()).hexdigest() + ".sv" for t in (GRAY, FIFO))
    bad = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "fetch_examples.py"), str(ref), "v1.0",
                          str(tmp_path / "c.json")], env=env, capture_output=True, text=True)
    assert bad.returncode == 2 and "refused" in bad.stderr


# ---------- retrieval ----------

def test_retrieval_is_deterministic_and_picks_the_close_module(bundle):
    b = bundle[0]
    a = X.retrieve(b["entries"], GRAY_TASK, {}, min_score=0.3, repo_denied_n=b["repo_denied_n"])
    c = X.retrieve(b["entries"], GRAY_TASK, {}, min_score=0.3, repo_denied_n=b["repo_denied_n"])
    assert a["ids"] == c["ids"] and a["ranked"] == c["ranked"] and a["ids"][0] == "fx-gray"
    assert a["withheld_repo"] == 3 and a["top_score"] == a["ranked"][0][1]


def test_no_example_below_the_threshold(bundle):
    b = bundle[0]
    out = X.retrieve(b["entries"], "Design a traffic light controller with a pedestrian button.", {})
    assert out["ids"] == [] and out["shown"] == [] and X.block(out["shown"]) == ""
    assert out["top_score"] < X.MIN_SCORE


def test_k_and_size_cap(bundle):
    b = bundle[0]
    both = X.retrieve(b["entries"], GRAY_TASK + " Also a synchronous FIFO with full and empty flags.", {}, min_score=0.3)
    assert len(both["ids"]) == 2
    one = X.retrieve(b["entries"], GRAY_TASK + " Also a synchronous FIFO with full and empty flags.", {}, k=1,
                     min_score=0.3)
    assert len(one["ids"]) == 1
    capped = X.retrieve(b["entries"], GRAY_TASK + " Also a synchronous FIFO with full and empty flags.", {},
                        min_score=0.3, max_bytes=len(both["shown"][0]["shown"].encode()) + 10)
    assert capped["bytes"] <= len(both["shown"][0]["shown"].encode()) + 10 and len(capped["ids"]) == 1


def test_constants_are_the_preregistered_ones():
    assert (X.K, X.MIN_SCORE, X.MAX_BYTES, X.WHOLE_MAX_LINES, X.SHINGLE, X.OVERLAP_MIN) == (2, 0.55, 12000, 250, 5, 0.10)
    assert X.REFERENCE_PINNED["v4.0"]["commit"] == "2af8e0e6ce68c8e1756192103904afc47ad73684"
    assert X.REFERENCE_PINNED["v4.0"]["manifest_sha256"] == \
        "c36d5df5c65a1f49af2628ccd00cc7d5ca090a6dfd2ffbe0fb66e4543291a917"


def test_overlap_rule_by_module_name_and_by_text(bundle):
    b = bundle[0]
    # a visible file that declares the same module: the entry is withheld, and the next one is used
    out = X.retrieve(b["entries"], GRAY_TASK, {"rtl/gray_conv.sv": "module gray_conv(input a, output y);\nendmodule\n"},
                     min_score=0.3)
    assert "fx-gray" not in out["ids"] and ("fx-gray", "module") == out["withheld"][0][:2]
    assert out["withheld_overlap"] == 1
    # a visible file that shares the module's lines under another name, spaced and commented differently
    sneaky = "\n".join(["// my own", *("   " + ln for ln in GRAY.splitlines()[3:]), ""]).replace("gray_conv", "g2b")
    out = X.retrieve(b["entries"], GRAY_TASK, {"docs/x.md": sneaky}, min_score=0.3)
    assert "fx-gray" not in out["ids"] and out["withheld"][0][1] == "text" and out["withheld"][0][2] >= X.OVERLAP_MIN
    # unrelated visible text does not withhold
    out = X.retrieve(b["entries"], GRAY_TASK, {"docs/x.md": "A module with a clock and a reset.\n"}, min_score=0.3)
    assert out["ids"][0] == "fx-gray" and out["withheld_overlap"] == 0


def test_shingles_ignore_comments_spacing_and_short_boilerplate():
    a = "module m;\n  assign   y = a & b;   // c\n  assign z = a | b;\n  assign w = a ^ b;\n  assign v = ~a;\nendmodule\n"
    b = a.replace("  ", "      ").replace("// c", "/* other */")
    assert X.shingles(a) == X.shingles(b) and X.shingles(a)
    assert X.shingles("end\nend\nend\nend\nend\nend\n") == set()


def test_only_visible_files_are_opened(tmp_path, monkeypatch):
    root = tmp_path / "code"
    for d in ("docs", "rtl", "verif", "src", "rundir/agent_out", "tests"):
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / "prompt.json").write_text(json.dumps({"prompt": GRAY_TASK}))
    (root / "docs" / "spec.md").write_text("spec")
    (root / "rtl" / "a.sv").write_text("module a; endmodule")
    (root / "verif" / "tb.sv").write_text("module tb; endmodule")
    for hidden in ("src/test_hidden.py", "src/harness_library.py", "tests/test_x.py", "rundir/agent_out/summary.json",
                   "docker-compose.yml"):
        (root / hidden).write_text("HIDDEN-GRAY-GRAY-GRAY")
    opened = []
    real = builtins.open

    def spy(file, *a, **k):
        opened.append(str(file))
        return real(file, *a, **k)
    monkeypatch.setattr(builtins, "open", spy)
    prompt, files = X.visible_from_root(str(root))
    monkeypatch.undo()
    assert prompt == GRAY_TASK and sorted(files) == ["docs/spec.md", "rtl/a.sv", "verif/tb.sv"]
    assert all(os.path.relpath(p, root).split(os.sep)[0] in ("prompt.json", "docs", "rtl", "verif") for p in opened)
    assert not any("HIDDEN" in t for t in files.values())


def test_a_dataset_records_hidden_tests_are_never_read():
    rec = {"id": "x", "prompt": "p", "context": {"docs/s.md": "d", "src/test_h.py": "HIDDEN", "rtl/a.sv": "r"},
           "harness": {"src/test_runner.py": "HIDDEN"}}
    prompt, files = X.visible_from_record(rec)
    assert sorted(files) == ["docs/s.md", "rtl/a.sv"]


# ---------- the block ----------

def test_block_format_leadin_and_header_line(bundle):
    b = bundle[0]
    out = X.retrieve(b["entries"], GRAY_TASK, {}, min_score=0.3, k=1)
    text = X.block(out["shown"])
    assert text.startswith("# Reference examples\nBelow is 1 module from well-reviewed open-source hardware projects, "
                           "picked automatically because it looks related to this task. It is an example of how such "
                           "designs are written, not part of the task: the task's own interface, names and timing "
                           "rules come first. Use it as you see fit.\n")
    first = text.split("```systemverilog\n", 1)[1].splitlines()[0]
    assert first == (f"// repo: fixture/cells | path: src/gray_conv.sv | sha: {SHA} | licence: FX-1.0 | "
                     f"notice: Copyright 2018 Fixture University.")
    assert "module gray_conv" in text and "PRIVATE" not in text and text.rstrip().endswith("```")
    two = X.block(X.retrieve(b["entries"], GRAY_TASK + " synchronous FIFO full empty", {}, min_score=0.3)["shown"])
    assert "Below are 2 modules" in two and "## Example 2" in two and "Use them as you see fit." in two


def test_a_long_module_falls_back_to_the_excerpt(tmp_path, monkeypatch):
    long_body = "\n".join(f"    assign w{i} = a{i} & b{i};" for i in range(300))
    long_src = "// Copyright 2018 Fixture University.\n\nmodule gray_conv(input logic a);\n" + long_body + "\nendmodule\n"
    monkeypatch.setitem(FILES, ("fixture/cells", SHA, "src/gray_conv.sv"), long_src)
    ref, pins, up = make_ref(tmp_path)
    b, _ = X.build_bundle(str(ref), "v9.9", fixture_fetch(up), pins)
    gray = b["entries"][0]
    assert gray["shown_kind"] == "excerpt" and gray["shown"] == gray["excerpt"] and gray["shown"].count("\n") <= 12


def test_module_text_stops_at_endmodule():
    assert X.module_text(GRAY, "gray_conv").splitlines()[0].startswith("module gray_conv") \
        and X.module_text(GRAY, "gray_conv").rstrip().endswith("endmodule")
    assert X.module_text(GRAY, "absent") is None


# ---------- arm E in the loop ----------

def e_cfg(tmp_path, bundle_obj, prompt=GRAY_TASK, **kw):
    cfg = api_cfg(tmp_path, retrieved_examples=True, skill_pack="v9.9",
                  examples_bundle=str(tmp_path / "bundle.json"), **kw)
    (tmp_path / "bundle.json").write_text(json.dumps(bundle_obj))
    (tmp_path / "code" / "prompt.json").write_text(json.dumps({"prompt": prompt}))
    return cfg


def done():
    return FakeClient([reply([block(type="text", text="done")], stop="end_turn")])


def test_e_examples_reach_the_first_user_message_after_the_task(tmp_path, bundle, monkeypatch):
    monkeypatch.setattr(X, "MIN_SCORE", 0.3)
    monkeypatch.setattr(X.retrieve, "__defaults__", (X.K, 0.3, X.MAX_BYTES, 0))
    cfg = e_cfg(tmp_path, bundle[0])
    c = done()
    s = apiloop.run(cfg, client=c)
    user0 = c.requests[0]["messages"][0]["content"]
    plain = apiloop.PROMPT.format(task=GRAY_TASK)
    assert user0.startswith(plain + "\n\n# Reference examples\n") and "module gray_conv" in user0
    assert s["examples_ids"] == "fx-gray" and s["examples_bytes"] > 0 and s["examples_withheld_repo"] == 3
    assert s["examples_withheld_overlap"] == 0 and s["examples_top_score"] > 0.3
    assert s["examples_block_sha256"] == hashlib.sha256(user0[len(plain) + 2:].encode()).hexdigest()
    assert s["switches"]["retrieved_examples"] is True and s["switches"]["skill_pack"] == "v9.9"
    # nothing else in the request differs from arm R's
    r = done()
    apiloop.run(api_cfg(tmp_path / "r"), client=r)
    a, b = dict(c.requests[0]), dict(r.requests[0])
    a.pop("timeout"), b.pop("timeout")
    assert a["messages"][0]["content"] != b["messages"][0]["content"]
    a["messages"], b["messages"] = a["messages"][1:], b["messages"][1:]
    assert a == b


def test_e_with_nothing_above_the_threshold_is_exactly_r(tmp_path, bundle):
    cfg = e_cfg(tmp_path, bundle[0], prompt="Write a traffic light controller.")
    c = done()
    s = apiloop.run(cfg, client=c)
    r = done()
    rcfg = api_cfg(tmp_path / "r")
    (tmp_path / "r" / "code" / "prompt.json").write_text(json.dumps({"prompt": "Write a traffic light controller."}))
    apiloop.run(rcfg, client=r)
    for q in (c.requests[0], r.requests[0]):
        q.pop("timeout")
    assert json.dumps(c.requests, sort_keys=True) == json.dumps(r.requests, sort_keys=True)
    assert s["examples_ids"] == "" and s["examples_bytes"] == 0 and s["examples_block_sha256"] == ""
    assert s["examples_withheld_repo"] == 3


def test_e_artifact_has_ids_and_sums_but_no_pack_prose(tmp_path, bundle, monkeypatch):
    monkeypatch.setattr(X.retrieve, "__defaults__", (X.K, 0.3, X.MAX_BYTES, 0))
    cfg = e_cfg(tmp_path, bundle[0])
    apiloop.run(cfg, client=done())
    log = [json.loads(ln) for ln in open(os.path.join(cfg.agent_out, "api_tools.jsonl"))]
    rec = [r for r in log if r["tool"] == "examples"][0]
    assert rec["ids"] == ["fx-gray"] and list(rec["file_sha256"].values()) == [hashlib.sha256(GRAY.encode()).hexdigest()]
    for name in os.listdir(cfg.agent_out):
        assert "PRIVATE" not in open(os.path.join(cfg.agent_out, name)).read()


def test_e_a_bad_bundle_stops_before_any_call(tmp_path):
    cfg = api_cfg(tmp_path, retrieved_examples=True, skill_pack="v9.9", examples_bundle=str(tmp_path / "none.json"))
    c = done()
    s = apiloop.run(cfg, client=c)
    assert s["stop_reason"] == "examples_error" and s["llm_calls"] == 0 and c.requests == []


def test_r_is_unchanged_by_the_new_code(tmp_path):
    c = done()
    s = apiloop.run(api_cfg(tmp_path), client=c)
    assert "retrieved_examples" not in s["switches"] and not any(k.startswith("examples_") for k in s)
    assert "Reference examples" not in c.requests[0]["messages"][0]["content"]


# ---------- the leak guard, both directions ----------

def test_guard_flags_pack_prose_and_passes_public_upstream_code(tmp_path, bundle):
    ref = bundle[2]
    out = tmp_path / "up"
    out.mkdir()
    (out / "prose.md").write_text("## notes\n" + PRIVATE + "\n")
    assert leak_guard.scan(None, [str(out)], [], reference=str(ref)) != []
    # escaped in a JSON summary, and as a diff line
    (out / "prose.md").unlink()
    (out / "s.json").write_text(json.dumps({"x": PRIVATE}))
    (out / "p.patch").write_text("+" + PRIVATE + "\n")
    assert {os.path.basename(f) for f, *_ in leak_guard.scan(None, [str(out)], [], reference=str(ref))} == \
        {"s.json", "p.patch"}
    # upstream code the agent copied is public text: the excerpt and Source sections are not secrets
    (out / "s.json").unlink()
    (out / "p.patch").unlink()
    (out / "design.sv").write_text(GRAY)
    assert leak_guard.scan(None, [str(out)], [], reference=str(ref)) == []
    assert leak_guard.scan(None, [str(out)], [str(tmp_path)], reference=str(ref)) == []


def test_guard_covers_index_text_and_the_readme(tmp_path, bundle):
    ref = bundle[2]
    out = tmp_path / "up"
    out.mkdir()
    (out / "a.txt").write_text("Synchronous FIFO with full and empty flags fifo full empty pointer")
    assert leak_guard.scan(None, [str(out)], [], reference=str(ref)) != []
    (out / "a.txt").write_text("# reference/ fixture\n\n" + PRIVATE)
    assert leak_guard.scan(None, [str(out)], [], reference=str(ref)) != []


def test_guard_cli_with_reference_only(tmp_path, bundle):
    ref = bundle[2]
    out = tmp_path / "up"
    out.mkdir()
    (out / "x.txt").write_text("nothing private here at all\n")
    cmd = [sys.executable, os.path.join(ROOT, "tools", "leak_guard.py"), "--reference", str(ref), str(out)]
    assert subprocess.run(cmd, capture_output=True, text=True).returncode == 0
    (out / "x.txt").write_text(PRIVATE)
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 1 and "PRIVATE" not in r.stdout + r.stderr
    assert subprocess.run([sys.executable, os.path.join(ROOT, "tools", "leak_guard.py"), str(out)],
                          capture_output=True, text=True).returncode == 2


def test_the_bundle_and_dry_run_outputs_hold_no_pack_prose(tmp_path, bundle):
    ref = bundle[2]
    p = tmp_path / "bundle.json"
    p.write_text(json.dumps(bundle[0]))
    up = bundle[4]
    # the bundle holds index titles and public code, so the real job keeps it out of work*; scanned with the
    # upstream files public it still has no 80-byte window of the prose
    assert leak_guard.scan(None, [str(p)], [str(up)], reference=str(ref)) == []


# ---------- config, sweep, workflow, columns ----------

def test_config_validation_per_harness():
    ok = dict(harness="apiloop", provider="anthropic", retrieved_examples=True, skill_pack="v4.0", examples_bundle="/b")
    assert Config(**ok).switches()["retrieved_examples"] is True
    with pytest.raises(ValueError, match="apiloop"):
        Config(**{**ok, "harness": "langgraph", "provider": "openrouter"})
    with pytest.raises(ValueError, match="apiloop"):
        Config(**{**ok, "harness": "claudecode", "provider": "claude_plan"})
    with pytest.raises(ValueError, match="own arm"):
        Config(**ok, presubmit_iface=True)
    with pytest.raises(ValueError, match="own arm"):
        Config(**ok, timing_claims=True)
    with pytest.raises(ValueError, match="needs CVDP_SKILL_PACK"):
        Config(**{**ok, "skill_pack": ""})
    with pytest.raises(ValueError, match="CVDP_SKILL_PACK"):          # the pack tag alone is still Claude Code's
        Config(harness="apiloop", provider="anthropic", skill_pack="v2.0")
    assert Config(harness="claudecode", provider="claude_plan", skill_pack="v2.0").switches()["skill_pack"] == "v2.0"


def test_config_from_env(monkeypatch):
    for k, v in dict(CVDP_HARNESS="apiloop", CVDP_PROVIDER="anthropic", CVDP_RETRIEVED_EXAMPLES="1",
                     CVDP_SKILL_PACK="v4.0", CVDP_EXAMPLES_BUNDLE="/examples/bundle.json").items():
        monkeypatch.setenv(k, v)
    c = from_env()
    assert c.retrieved_examples and c.examples_bundle == "/examples/bundle.json" and c.skill_pack == "v4.0"


def e_sweep(tmp_path, **kw):
    ref, pins, up = make_ref(tmp_path)
    (tmp_path / "pins.json").write_text(json.dumps(pins))
    co = tmp_path / "ref" / "checkout"
    co.mkdir()
    (co / "reference").symlink_to(ref)
    env = dict(HARNESS="apiloop", ANTHROPIC_API_KEY=KEY, RETRIEVED_EXAMPLES="1", SKILL_PACK="v9.9",
               SKILL_PACK_DIR=str(co), REFERENCE_PINS=str(tmp_path / "pins.json"),
               EXAMPLES_PINS=str(tmp_path / "pins.json"), EXAMPLES_FETCH_DIR=str(up), SPLIT="m3g_heldout")
    env.update(kw)
    return sweep(tmp_path, **env)


def test_sweep_builds_the_bundle_and_mounts_only_it(tmp_path):
    r, seen = e_sweep(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    specs = [x.split(":") for x in seen["mounts"].split(";") if x.strip()]
    assert [x[1] for x in specs] == ["/ledger", "/examples/bundle.json"] and specs[1][2] == "ro"
    assert os.path.basename(specs[1][0]) == "bundle.json" and "/skill_pack" not in seen["mounts"]
    assert seen["env"].endswith("CVDP_RETRIEVED_EXAMPLES,CVDP_SKILL_PACK,CVDP_EXAMPLES_BUNDLE")
    run = json.load(open(str(tmp_path / "work") + ".run.json"))
    assert run["retrieved_examples"] is True and run["skill_pack"] == "v9.9" and run["examples_kept_n"] == 2
    assert run["examples_files"][f"fixture/cells@{SHA}:src/gray_conv.sv"] == hashlib.sha256(GRAY.encode()).hexdigest()
    assert len(run["examples_bundle_sha256"]) == 64
    assert not os.path.exists(str(tmp_path / "work.examples"))
    # the bundle is outside work*, so the job's upload and its guard never see index text
    assert os.path.basename(os.path.dirname(specs[1][0])) == "examples_bundle"
    assert not os.path.dirname(specs[1][0]).startswith(str(tmp_path / "work"))


def test_sweep_refuses_bad_example_settings(tmp_path):
    for i, extra in enumerate(({"HARNESS": "langgraph"}, {"HARNESS": "claudecode"}, {"SKILL_PACK": ""},
                               {"PRESUBMIT_IFACE": "1"}, {"TIMING_CLAIMS": "1"}, {"INTERFACE_CHECK": "1"},
                               {"SKILL_PACK": "v1.0"}, {"RETRIEVED_EXAMPLES": "yes"})):
        (tmp_path / f"bad{i}").mkdir()
        r, _ = e_sweep(tmp_path / f"bad{i}", **extra)
        assert r.returncode == 2, extra


def test_sweep_refuses_a_layer_that_differs_from_its_pin(tmp_path):
    r, _ = e_sweep(tmp_path, REFERENCE_PINS=str(_other_pins(tmp_path)))
    assert r.returncode == 2 and "refused" in r.stderr


def _other_pins(tmp_path):
    p = json.load(open(tmp_path / "pins.json")) if (tmp_path / "pins.json").exists() else {"v9.9": {"commit": "c" * 40,
                                                                                                   "entries": 5}}
    p["v9.9"]["manifest_sha256"] = "0" * 64
    q = tmp_path / "other_pins.json"
    q.write_text(json.dumps(p))
    return q


def test_sweep_without_the_flag_does_not_mention_examples(tmp_path):
    r, seen = sweep(tmp_path, HARNESS="apiloop", ANTHROPIC_API_KEY=KEY)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "EXAMPLES" not in seen["env"] and "/examples" not in seen["mounts"]
    assert "retrieved_examples" not in json.load(open(str(tmp_path / "work") + ".run.json"))
    assert not os.path.exists(str(tmp_path / "examples_bundle"))


def test_workflow_option_env_and_input_count():
    import yaml
    wf = yaml.safe_load(open(os.path.join(ROOT, ".github", "workflows", "sweep.yml")))
    on = wf.get("on") or wf.get(True)
    inp = on["workflow_dispatch"]["inputs"]
    assert len(inp) <= 25 and len(inp) == 24
    assert "retrieved_examples" in inp["fixed_checks"]["options"] and "skill_hint" in inp
    assert "'retrieved_examples'" in wf["env"]["RETRIEVED_EXAMPLES"]
    text = open(os.path.join(ROOT, ".github", "workflows", "sweep.yml")).read()
    assert "--reference" in text and "examples_bundle/upstream" in text and "verify-reference" in text
    for other in ("mutation_gate", "interface_check", "verify_submit", "presubmit_iface", "timing_claims", "spec_vectors"):
        assert other not in "retrieved_examples"


def test_collect_m3l_columns_only_with_the_flag():
    assert "examples_ids" not in collect.FIELDS and "examples_ids" not in collect.M3K_FIELDS
    assert collect.M3L_FIELDS == ["examples_ids", "examples_bytes", "examples_withheld_repo",
                                  "examples_withheld_overlap", "examples_top_score"]
    cols = collect.m3l_columns({"examples_ids": "a;b", "examples_bytes": 100, "examples_withheld_repo": 49,
                                "examples_withheld_overlap": 0, "examples_top_score": 0.6})
    assert cols["examples_ids"] == "a;b" and cols["examples_top_score"] == 0.6
    assert collect.m3l_columns({})["examples_bytes"] == ""
