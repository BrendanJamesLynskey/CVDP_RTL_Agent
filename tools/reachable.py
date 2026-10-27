"""Which agentic problems can an agent reach at all? A deterministic check of the names the hidden testbench needs
against what the agent is given. No LLM.

For each problem record (`harness` holds the hidden files, `prompt` and `context` what the agent sees):

1. **Handles the hidden testbench reads**:
   - `dut.<a>.<b>[i].<c>` paths in the hidden Python (cocotb tests and helpers). Each identifier on the path is a
     handle (`a`, `b`, `c`); `.value` and methods or private attributes end the path. String literals and whole
     f-strings are dropped first, so a name read only inside an assert's message does not count (M3's gotcha:
     the check had already failed when the message was built).
   - The top module: `TOPLEVEL` in `src/.env`, a literal `hdl_toplevel=`/`toplevel=` in the runner, `-s <top>` in
     a command.
   - Parameter names: string keys of a `parameter(s)` dict in the runner, `-P<top>.<NAME>=`, `-G<NAME>=`.
2. **Is a handle given?** A word-boundary match of the name, not of prose:
   - anywhere in a context file that is code (`.sv`, `.v`, `.svh`, `.vh`, `.py`, `.c`, `.h`, `.json`, `.yml`);
   - in the prompt or a document, only inside backticks or a fenced code block, unless the name is shaped like an
     identifier (it has `_`, a digit, or an upper-case letter after the first), in which case a plain word match
     in the text counts. So `enable` in prose is not "given", but `INDEX_WIDTH` in prose is.
3. **Unreachable** = some handle is given nowhere, AND M3's taxonomy labels the problem `signal_missing_hidden` or
   `compile_fail_hidden` in at least half of its runs (`--runs`, the 14 M3 CSVs). Both halves are needed: a
   missing name the agent never fails on is not evidence, and a failing problem whose names are all given is the
   agent's fault, not the benchmark's.

4. **Compiled paths (added after brief 09; reported, does not change the frozen M3b set).** Every source the hidden
   harness compiles (`VERILOG_SOURCES` in each `.env*` file) must be reachable: a file the task gives, a path or
   file name written in the prompt or a document, or the name of a module the task gives with the extension of the
   stated language (the file-per-module convention). Otherwise the path is unreachable, with one reason:
   `extension_mismatch` (the stem is a given module name but the extension is the other language's: `.sv` when
   the prompt says only "Verilog", `.v` when it says only "SystemVerilog", and no given `rtl/` file has that
   extension) or `unnamed_file` (the stem is no name the task gives). As a separate note, not an unreachable
   reason, `given_rtl_not_compiled` lists the `rtl/` files the task gives that no `.env` compiles: a design that
   instantiates them fails to compile. The generic system message ("create a Verilog module") is not counted as a
   stated language, because every problem has it.

Usage: python3 tools/reachable.py <agentic.jsonl> --runs 'docs/reports/m3/runs/*.csv'
           [--ids-out tools/m3b_eval_ids.txt] [--excluded-out tools/m3b_excluded_ids.txt]
           [--md-out docs/reports/m3b/unreachable.md] [--paths-md-out docs/reports/reachable_paths.md]
           [--ids tools/m3b_eval_ids.txt] [--limited tools/benchmark_limited_ids.txt]
"""
import argparse
import collections
import csv
import glob
import io
import json
import os
import re
import sys
import tokenize

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent"))

LABELS = ("signal_missing_hidden", "compile_fail_hidden")
# attributes and methods of a cocotb handle, not names in the design
NOT_HANDLES = {"value", "setimmediatevalue", "get", "set", "start", "kill", "handle", "log"}


# ---------- handles the hidden testbench reads ----------

def code_tokens(src):
    """The tokens of Python source with comments, string literals and whole f-strings removed."""
    out, depth = [], 0
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            name = tokenize.tok_name[tok.type]
            if name == "FSTRING_START":
                depth += 1
            elif name == "FSTRING_END":
                depth -= 1
            elif depth == 0 and name not in ("STRING", "COMMENT", "NL", "NEWLINE", "INDENT", "DEDENT",
                                             "ENCODING", "ENDMARKER"):
                out.append(tok.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return out


def dut_paths(src):
    """Handle paths read through `dut.` in Python source, outside strings: e.g. ['poly_branches', 'u_poly_filter',
    'TAPS'] for dut.poly_branches[0].u_poly_filter.TAPS."""
    toks, paths, i = code_tokens(src), [], 0
    while i < len(toks):
        if toks[i] == "dut" and (i == 0 or toks[i - 1] != ".") and i + 2 < len(toks) and toks[i + 1] == ".":
            path, j = [], i + 1
            while j + 1 < len(toks) and toks[j] == ".":
                name = toks[j + 1]
                if not name.isidentifier() or name.startswith("_") or name in NOT_HANDLES:
                    break
                path.append(name)
                j += 2
                while j + 2 < len(toks) and toks[j] == "[" and toks[j + 2] == "]":  # dut.a[0].b
                    j += 3
            if path:
                paths.append(path)
            i = j
        else:
            i += 1
    return paths


def runner_names(files):
    """(top modules, parameter names) from the runner, the .env and any command line."""
    tops, params = set(), set()
    for name, text in files.items():
        if name.endswith(".env"):
            m = re.search(r"(?m)^\s*TOPLEVEL\s*=\s*(\w+)", text)
            if m:
                tops.add(m.group(1))
        for m in re.finditer(r"\b(?:hdl_)?toplevel\s*=\s*['\"](\w+)['\"]", text):
            tops.add(m.group(1))
        for m in re.finditer(r"(?<![\w-])-s\s+(\w+)", text):
            tops.add(m.group(1))
        for m in re.finditer(r"-P\s*\w+\.(\w+)\s*=", text):
            params.add(m.group(1))
        for m in re.finditer(r"-G(\w+)\s*=", text):
            params.add(m.group(1))
        if name.endswith(".py"):
            # string keys of a dict literal assigned to a parameter(s) variable or passed as parameters=
            for m in re.finditer(r"(?:\bparam\w*\s*=|parameters\s*=)\s*\{([^{}]*)\}", text):
                params.update(re.findall(r"['\"](\w+)['\"]\s*:", m.group(1)))
    return tops, params


def handles(record):
    """{name: [where it is read]} for one problem's hidden files."""
    files = record.get("harness") or {}
    out = collections.defaultdict(set)
    tops, params = runner_names(files)
    for t in tops:
        out[t].add("top module")
    for p in params:
        out[p].add("parameter")
    for name, text in files.items():
        if name.endswith(".py"):
            for path in dut_paths(text):
                for k, comp in enumerate(path):
                    out[comp].add("dut." + ".".join(path[:k + 1]))
    return {k: sorted(v) for k, v in out.items()}


# ---------- what the agent is given ----------
# The extraction lives in the agent package (cvdp_agent/given.py), shared with M3c's interface check.
from cvdp_agent.given import CODE_EXT, given_texts, is_given  # noqa: E402,F401
from cvdp_agent.given import ID_SHAPED as _ID_SHAPED  # noqa: E402
from cvdp_agent.given import code_spans as _code_spans  # noqa: E402,F401


# ---------- source paths the hidden harness compiles ----------

RTL_EXT = (".sv", ".v", ".svh", ".vh")


def compiled_paths(record):
    """{path relative to /code (e.g. 'rtl/top.sv'): [the .env files that compile it]} from `VERILOG_SOURCES`."""
    out = collections.defaultdict(set)
    for name, text in (record.get("harness") or {}).items():
        if not os.path.basename(name).startswith(".env"):
            continue
        for m in re.finditer(r"(?m)^\s*VERILOG_SOURCES\s*=\s*(.*)$", text or ""):
            for tok in m.group(1).split():
                out[re.sub(r"^/code/", "", tok)].add(name)
    return {k: sorted(v) for k, v in out.items()}


def stated_language(record):
    """'sv', 'v' or None: the HDL the prompt names. Both or neither named is None (no rule stated)."""
    text = record.get("prompt") or ""
    sv = re.search(r"System\s*Verilog", text, re.I)
    v = re.search(r"(?<![\w-])(?<!System)(?<!System )Verilog\b", text, re.I)
    return "sv" if sv and not v else "v" if v and not sv else None


def path_reason(path, record, texts=None):
    """None when the compiled `path` is reachable, else 'extension_mismatch' or 'unnamed_file'."""
    ctx = record.get("context") or {}
    if path in ctx:
        return None
    texts = texts or given_texts(record)
    base = os.path.basename(path)
    if is_given(base, texts) or is_given(path, texts):
        return None
    stem, ext = os.path.splitext(base)
    if not is_given(stem, texts):
        return "unnamed_file"
    lang = stated_language(record)
    given_exts = {os.path.splitext(n)[1] for n in ctx if n.startswith("rtl/")}
    if ext not in given_exts and ((lang == "v" and ext == ".sv") or (lang == "sv" and ext == ".v")):
        return "extension_mismatch"
    return None


def path_check(record):
    """(unreachable compiled paths {path: reason}, given rtl/ files no .env compiles)."""
    paths, texts = compiled_paths(record), given_texts(record)
    bad = {p: r for p in paths if (r := path_reason(p, record, texts))}
    not_compiled = sorted(n for n in (record.get("context") or {})
                          if n.startswith("rtl/") and n.endswith(RTL_EXT) and n not in paths)
    return bad, not_compiled


# ---------- M3's labels ----------

def m3_labels(paths):
    """{problem id: Counter of failure_label over the runs}, and the number of runs."""
    by = collections.defaultdict(collections.Counter)
    runs = 0
    for p in paths:
        runs += 1
        for r in csv.DictReader(open(p)):
            by[r["id"]][r.get("failure_label") or ("passed" if r["pass"] == "1" else "")] += 1
    return by, runs


def check(records, label_counts, runs):
    """Rows for every problem: id, missing names (with where read), interface-label count, unreachable."""
    out = []
    for rec in records:
        h = handles(rec)
        texts = given_texts(rec)
        missing = {n: w for n, w in h.items() if not is_given(n, texts)}
        bad = sum(label_counts.get(rec["id"], {}).get(lb, 0) for lb in LABELS)
        paths_bad, not_compiled = path_check(rec)
        # `unreachable` is M3b's rule and stays as it was (tools/m3b_eval_ids.txt is frozen); `paths_unreachable`
        # is the same rule with the compiled-path check added
        out.append({"id": rec["id"], "cid": (rec.get("categories") or [""])[0], "handles": len(h), "missing": missing,
                    "interface_failures": bad, "runs": runs,
                    "unreachable": bool(missing) and runs > 0 and bad * 2 >= runs,
                    "paths": paths_bad, "given_rtl_not_compiled": not_compiled,
                    "paths_unreachable": bool(missing or paths_bad) and runs > 0 and bad * 2 >= runs})
    return out


def report_md(rows, runs):
    un = [r for r in rows if r["unreachable"]]
    flagged = [r for r in rows if not r["unreachable"] and r["interface_failures"] * 2 >= runs > 0]
    n_id = sum(any(_ID_SHAPED.search(n) for n in r["missing"]) for r in un)
    lines = [f"# Unreachable agentic problems (M3b evaluation set)\n",
             f"Made by `tools/reachable.py` from the dataset's hidden harness files and M3's {runs} runs "
             f"(`docs/reports/m3/runs/*.csv`). A problem is unreachable when a name the hidden testbench reads is "
             f"given nowhere to the agent **and** M3 labels it `signal_missing_hidden` or `compile_fail_hidden` in "
             f"at least half of its runs. {len(un)} of {len(rows)} are excluded; the evaluation set is the other "
             f"{len(rows) - len(un)} (`tools/m3b_eval_ids.txt`).\n",
             f"The exclusions rest on identifier-shaped names such as `hour_pulse` and `CLK_FREQ`: {n_id} of the "
             f"{len(un)} excluded problems read at least one the agent is not given. Common words such as `clk` and "
             f"`hour` are also listed as not given when they appear only in prose, which may be too strict for them; "
             + ("no exclusion rests on them alone.\n" if n_id == len(un) else
                f"{len(un) - n_id} exclusion(s) rest on them alone.\n"),
             "| Problem | cid | Interface failures in M3 | Names the hidden testbench reads that the agent is not given "
             "(where read) |", "|---|---|---|---|"]
    for r in un:
        names = "; ".join(f"`{n}` ({', '.join(w[:2])}{', …' if len(w) > 2 else ''})"
                          for n, w in sorted(r["missing"].items())[:8])
        more = f" and {len(r['missing']) - 8} more" if len(r["missing"]) > 8 else ""
        lines.append(f"| `{r['id'].replace('cvdp_agentic_', '')}` | {r['cid']} | {r['interface_failures']}/{runs} "
                     f"| {names}{more} |")
    lines += ["", "**Kept although M3's interface labels dominate** (every name the hidden testbench reads is given "
              "somewhere, so the failure is the agent's):\n", "| Problem | cid | Interface failures in M3 |",
              "|---|---|---|"]
    lines += [f"| `{r['id'].replace('cvdp_agentic_', '')}` | {r['cid']} | {r['interface_failures']}/{runs} |"
              for r in flagged] or ["| (none) | | |"]
    return "\n".join(lines) + "\n"


def read_ids(path):
    return {ln.strip() for ln in open(path) if ln.strip() and not ln.startswith("#")} if path else set()


def paths_md(rows, runs, eval_ids=(), limited=()):
    """docs/reports/reachable_paths.md: the compiled-path check over every problem."""
    eval_ids, limited = set(eval_ids), set(limited)
    short = lambda i: f"`{i.replace('cvdp_agentic_', '')}`"  # noqa: E731
    bad = [r for r in rows if r["paths"]]
    nc = [r for r in rows if r["given_rtl_not_compiled"]]
    in_eval = [r for r in bad if r["id"] in eval_ids]
    newly = [r for r in in_eval if r["paths_unreachable"] and not r["unreachable"]]
    lines = ["# Compiled paths the agent cannot reach\n",
             "Made by `tools/reachable.py --paths-md-out` from the dataset's hidden harness files (the revision "
             f"pinned in `sweep.yml`; all {len(rows)} problems of the agentic split) and M3's {runs} runs. It adds the check brief 09 found missing "
             "(`unsolved_analysis.md`, `sync_serial_communication_0001`): every source file the hidden harness "
             "compiles (`VERILOG_SOURCES` in its `.env` files) must be a file the task gives, a path or file name "
             "the prompt or a document writes, or a module name the task gives with the extension of the stated "
             "language. Otherwise the path is unreachable:\n",
             "- `unnamed_file`: the file's stem is no name the task gives;",
             "- `extension_mismatch`: the stem is a given module name, but the extension belongs to the other "
             "language (`.sv` while the prompt says only \"Verilog\", or `.v` while it says only \"SystemVerilog\"), "
             "and no given `rtl/` file has that extension.\n",
             "**The M3b evaluation set is not changed.** `tools/m3b_eval_ids.txt` is frozen, because every scored "
             "result since M3b depends on it. This report says what the check would have excluded.\n",
             "## Summary\n",
             f"- **{len(bad)} of {len(rows)} problems** compile a path the agent cannot reach; "
             f"{len(in_eval)} of them are in the 86-problem evaluation set.",
             f"- **{len(newly)} evaluation problem(s) would have been excluded** under M3b's rule (unreachable name "
             "or path, and M3 labels the problem `signal_missing_hidden` or `compile_fail_hidden` in at least half "
             f"of its {runs} runs): " + (", ".join(short(r["id"]) for r in newly) or "none") + "."]
    flagged = {r["id"] for r in in_eval}
    if limited:
        lines.append(f"- Against `tools/benchmark_limited_ids.txt` ({len(limited)} problems): the path check flags "
                     + (", ".join(short(i) for i in sorted(limited & flagged)) or "none") + "; it does not flag "
                     + (", ".join(short(i) for i in sorted(limited - flagged)) or "none")
                     + ", whose causes are behaviour or values, not file paths"
                     + (" (except where the given-RTL note below applies)" if limited & {r["id"] for r in nc} else "")
                     + ". Flagged and not in that list: "
                     + (", ".join(short(r["id"]) for r in in_eval if r["id"] not in limited) or "none") + ".")
    lines.append("- A flagged path with few interface or compile failures in M3 is one the agent happened to guess "
                 "(for example the `.sv` extension when the prompt says \"Verilog\"): it is kept under M3b's rule, "
                 "but it is still a gap in the task.")
    lines += ["", "## Unreachable compiled paths\n",
              "| Problem | In eval set | Path | Reason | Interface/compile failures in M3 | Excluded under M3b's rule "
              "with paths |", "|---|---|---|---|---|---|"]
    for r in bad:
        for p, why in sorted(r["paths"].items()):
            lines.append(f"| {short(r['id'])} | {'yes' if r['id'] in eval_ids else 'no (already excluded)'} | "
                         f"`{p}` | `{why}` | {r['interface_failures']}/{runs} | "
                         f"{'yes' if r['paths_unreachable'] else 'no'} |")
    if not bad:
        lines.append("| (none) | | | | | |")
    lines += ["", "## Note: given RTL that no `.env` compiles\n",
              "Not an unreachable reason by itself: it matters only when the design instantiates the given file "
              "from its own file, as the task invites in `rc5_0001` (\"choose the appropriate CA design\"). A design "
              "that does fails to compile; one that copies the module into a compiled file does not.\n",
              "| Problem | In eval set | Given `rtl/` files not compiled |", "|---|---|---|"]
    for r in nc:
        names = ", ".join(f"`{n}`" for n in r["given_rtl_not_compiled"][:6])
        more = f" and {len(r['given_rtl_not_compiled']) - 6} more" if len(r["given_rtl_not_compiled"]) > 6 else ""
        lines.append(f"| {short(r['id'])} | {'yes' if r['id'] in eval_ids else 'no'} | {names}{more} |")
    if not nc:
        lines.append("| (none) | | |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset")
    ap.add_argument("--runs", default="docs/reports/m3/runs/*.csv")
    ap.add_argument("--ids-out")
    ap.add_argument("--excluded-out", help="the unreachable ids (the lessons builder refuses these too)")
    ap.add_argument("--md-out")
    ap.add_argument("--json-out", help="every problem's handles check, for review")
    ap.add_argument("--paths-md-out", help="the compiled-path report (docs/reports/reachable_paths.md)")
    ap.add_argument("--ids", default="tools/m3b_eval_ids.txt", help="the evaluation set, for --paths-md-out")
    ap.add_argument("--limited", default="tools/benchmark_limited_ids.txt", help="for --paths-md-out")
    a = ap.parse_args(argv)
    records = [json.loads(ln) for ln in open(a.dataset) if ln.strip()]
    counts, runs = m3_labels(sorted(glob.glob(a.runs)))
    rows = check(records, counts, runs)
    if a.ids_out:
        with open(a.ids_out, "w") as f:
            f.write("# M3b evaluation set: the agentic problems tools/reachable.py finds reachable "
                    f"({sum(not r['unreachable'] for r in rows)} of {len(rows)})\n")
            f.writelines(r["id"] + "\n" for r in rows if not r["unreachable"])
    if a.excluded_out:
        with open(a.excluded_out, "w") as f:
            f.write("# M3b excluded agentic problems: the ones tools/reachable.py finds unreachable "
                    f"({sum(r['unreachable'] for r in rows)} of {len(rows)}; see docs/reports/m3b/unreachable.md)\n")
            f.writelines(r["id"] + "\n" for r in rows if r["unreachable"])
    md = report_md(rows, runs)
    if a.md_out:
        with open(a.md_out, "w") as f:
            f.write(md)
    if a.paths_md_out:
        with open(a.paths_md_out, "w") as f:
            f.write(paths_md(rows, runs, read_ids(a.ids), read_ids(a.limited)))
    if a.json_out:
        with open(a.json_out, "w") as f:
            json.dump(rows, f, indent=1)
    print(md)


if __name__ == "__main__":
    sys.exit(main())
