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

Usage: python3 tools/reachable.py <agentic.jsonl> --runs 'docs/reports/m3/runs/*.csv'
           [--ids-out tools/m3b_eval_ids.txt] [--md-out docs/reports/m3b/unreachable.md]
"""
import argparse
import collections
import csv
import glob
import io
import json
import re
import sys
import tokenize

LABELS = ("signal_missing_hidden", "compile_fail_hidden")
CODE_EXT = (".sv", ".v", ".svh", ".vh", ".py", ".c", ".h", ".json", ".yml", ".yaml", ".tcl", ".mk")
# attributes and methods of a cocotb handle, not names in the design
NOT_HANDLES = {"value", "setimmediatevalue", "get", "set", "start", "kill", "handle", "log"}
_ID_SHAPED = re.compile(r"_|\d|^.+[A-Z]")


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

def _code_spans(text):
    """Text inside backticks and fenced code blocks."""
    fenced = re.findall(r"```.*?```", text, re.DOTALL)
    rest = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    return "\n".join(fenced + re.findall(r"`([^`\n]+)`", rest))


def given_texts(record):
    """(code text, prose text, code spans of the prose) the agent can read."""
    code, prose = [], [record.get("prompt") or ""]
    for name, text in (record.get("context") or {}).items():
        (code if name.lower().endswith(CODE_EXT) else prose).append(text or "")
    prose_text = "\n".join(prose)
    return "\n".join(code), prose_text, _code_spans(prose_text)


def is_given(name, texts):
    code, prose, spans = texts
    word = re.compile(rf"(?<![\w$]){re.escape(name)}(?![\w$])")
    if word.search(code) or word.search(spans):
        return True
    return bool(_ID_SHAPED.search(name)) and bool(word.search(prose))


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
        out.append({"id": rec["id"], "cid": (rec.get("categories") or [""])[0], "handles": len(h), "missing": missing,
                    "interface_failures": bad, "runs": runs,
                    "unreachable": bool(missing) and runs > 0 and bad * 2 >= runs})
    return out


def report_md(rows, runs):
    un = [r for r in rows if r["unreachable"]]
    flagged = [r for r in rows if not r["unreachable"] and r["interface_failures"] * 2 >= runs > 0]
    lines = [f"# Unreachable agentic problems (M3b evaluation set)\n",
             f"Made by `tools/reachable.py` from the dataset's hidden harness files and M3's {runs} runs "
             f"(`docs/reports/m3/runs/*.csv`). A problem is unreachable when a name the hidden testbench reads is "
             f"given nowhere to the agent **and** M3 labels it `signal_missing_hidden` or `compile_fail_hidden` in "
             f"at least half of its runs. {len(un)} of {len(rows)} are excluded; the evaluation set is the other "
             f"{len(rows) - len(un)} (`tools/m3b_eval_ids.txt`).\n",
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


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dataset")
    ap.add_argument("--runs", default="docs/reports/m3/runs/*.csv")
    ap.add_argument("--ids-out")
    ap.add_argument("--md-out")
    ap.add_argument("--json-out", help="every problem's handles check, for review")
    a = ap.parse_args(argv)
    records = [json.loads(ln) for ln in open(a.dataset) if ln.strip()]
    counts, runs = m3_labels(sorted(glob.glob(a.runs)))
    rows = check(records, counts, runs)
    if a.ids_out:
        with open(a.ids_out, "w") as f:
            f.write("# M3b evaluation set: the agentic problems tools/reachable.py finds reachable "
                    f"({sum(not r['unreachable'] for r in rows)} of {len(rows)})\n")
            f.writelines(r["id"] + "\n" for r in rows if not r["unreachable"])
    md = report_md(rows, runs)
    if a.md_out:
        with open(a.md_out, "w") as f:
            f.write(md)
    if a.json_out:
        with open(a.json_out, "w") as f:
            json.dump(rows, f, indent=1)
    print(md)


if __name__ == "__main__":
    sys.exit(main())
