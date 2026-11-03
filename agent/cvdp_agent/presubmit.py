"""M3k arm K: one deterministic check at the point of submitting. No LLM, no hidden files.

When the model signals it is finished (a turn with no tool call), the final RTL under rtl/ is compared with what
the task gives the agent: the prompt, docs/, the original rtl/ and verif/ files (read once, at the start, by
`interface.InterfaceCheck`; it never opens a hidden test or a harness file). Three things are checked:
- the interface: module names, port names, port directions and widths, parameters (interface.compare, plus
  directions, which M3c's check did not compare);
- the files: every `rtl/<name>.(sv|v|svh|vh)` the prompt or a document names must exist; a file written with the
  other extension (`rtl/foo.v` for a requested `rtl/foo.sv`) is reported as such;
- whether the RTL elaborates at all (pyslang, then Yosys as M3c's fallback).

Findings go back to the model as one fixed user message (TEMPLATE), at most MAX_ROUNDS times per problem."""
import os
import re

from . import interface

MAX_ROUNDS = 2
FILE_RE = re.compile(r"(?<![\w./-])(?:/code/)?(rtl/[A-Za-z0-9_][\w./-]*\.(?:sv|v|svh|vh))\b")
SWAP = {".sv": ".v", ".v": ".sv", ".svh": ".vh", ".vh": ".svh"}

TEMPLATE = ("Before you finish: an automatic check of your files under rtl/ against the task, the docs and the "
            "files you were given found {n} problem{s}:\n{lines}\n"
            "Fix each one that is a real mismatch with the task, then stop with a one-line summary again. If a "
            "finding is wrong because the task does not require it, say so in one line and stop.")


def named_files(record):
    """rtl/ files the prompt or a document names, in order of appearance (not the original context's own rtl/)."""
    ctx = record.get("context") or {}
    texts = [record.get("prompt") or ""] + [v for k, v in ctx.items()
                                            if not k.endswith((".sv", ".v", ".svh", ".vh", ".py"))]
    out = []
    for t in texts:
        for m in FILE_RE.finditer(t.replace("**", "").replace("`", " ")):
            if m.group(1) not in out:
                out.append(m.group(1))
    return out


def direction_findings(given, design):
    out = []
    for g, gm in sorted(given.items()):
        dm = design.get(g)
        if not dm:
            continue
        for p, gp in sorted(gm["ports"].items()):
            d, dd = gp.get("dir"), (dm["ports"].get(p) or {}).get("dir")
            if d in ("input", "output") and dd in ("input", "output") and d != dd:  # a swap, not a doc's "inout"
                out.append({"kind": "direction", "module": g, "name": p,
                            "detail": f"port `{p}` of `{g}` is an {dd}; the given interface says {d}"})
    return out


def file_findings(root, wanted):
    out = []
    for rel in wanted:
        if os.path.isfile(os.path.join(root, rel)):
            continue
        stem, ext = os.path.splitext(rel)
        alt = stem + SWAP.get(ext, "")
        if SWAP.get(ext) and os.path.isfile(os.path.join(root, alt)):
            out.append({"kind": "file_extension", "module": "", "name": rel,
                        "detail": f"the task asks for `{rel}`, but the file is `{alt}`"})
        else:
            out.append({"kind": "missing_file", "module": "", "name": rel,
                        "detail": f"the task names `{rel}`, which does not exist"})
    return out


def precise(given, findings):
    """Keep the findings that held up in the replay on M3j's passing runs (docs/reports/m3k/replay.md): a module
    named only in prose or by a file name is not required (the design's module may be named otherwise and still
    pass), and a width read from prose is not trusted. Original RTL, a module header and a visible testbench are."""
    out = []
    for f in findings:
        src = (given.get(f["module"]) or {}).get("source")
        if f["kind"] == "missing_module" and src not in ("rtl", "testbench"):
            continue
        if f["kind"] == "width" and src not in ("rtl", "header", "testbench"):
            continue
        out.append(f)
    return out


def message(findings):
    lines = [f"- {f['detail']}" for f in findings[:30]]
    if len(findings) > 30:
        lines.append(f"- and {len(findings) - 30} more")
    return TEMPLATE.format(n=len(findings), s="" if len(findings) == 1 else "s", lines="\n".join(lines))


class PresubmitCheck:
    """One per problem; the given interface is read at construction, before the model has edited anything."""

    def __init__(self, root, timeout_s=30.0, env=None):
        self.root, self.env, self.timeout_s = root, env, timeout_s
        self.iface = interface.InterfaceCheck(root, timeout_s=timeout_s, env=env)
        self.wanted = named_files(self.iface.record)

    def check(self):
        """{"findings": [...], "engine", "note"}; findings is [] when nothing is wrong."""
        tops = [n for n, m in self.iface.given.items() if m["source"] != "rtl"] or sorted(self.iface.given)
        design, engine, note = interface.elaborate(self.root, top_hint=tops[0] if tops else None,
                                                   timeout=self.timeout_s, env=self.env)
        findings = file_findings(self.root, self.wanted)
        if engine is None or note.startswith("elaborated with errors"):
            findings.append({"kind": "compile_error", "module": "", "name": "",
                             "detail": "the RTL under rtl/ does not elaborate: " + (note or "no design")[:300]})
        if engine is not None and self.iface.given:
            findings += precise(self.iface.given, interface.compare(self.iface.given, self.iface.names, design)
                                + direction_findings(self.iface.given, design))
        return {"findings": findings, "engine": engine, "note": note}
