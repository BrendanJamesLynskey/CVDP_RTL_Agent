"""M3c: the interface check. Elaborate the agent's RTL and compare the modules' names, ports (direction, width
where it is constant) and parameters with the interface the agent was given: the prompt, the docs and the
original context files. Deterministic, no LLM.

It reads only files inside the task tree it is given (prompt.json, docs/, rtl/, verif/), never the hidden tests
or any harness file. Every file is read here, in Python (pyslang gets text, `include`s are inlined from rtl/), and
the Yosys fallback is given only paths under rtl/.

The given interface:
- a module the context's original RTL defines (cid004, cid016, and the reused modules of cid005): that file's
  original ports and parameters;
- a Verilog module header in the prompt or a document;
- otherwise, from the documents: markdown tables with a direction column, and bullets under an interface, port or
  signal heading (`**name [7:0]**: ...`, `` `name` (WIDTH bits): ``), and the parameters under a parameter
  heading. Those go to the module the heading names, or to the one new module the prompt asks for.

Findings, in three kinds (plus the module itself missing):
- missing_port, missing_param, missing_module: a name in the given interface the design does not have;
- spelling: a name in the design that the given interface spells differently (case or underscores only);
- width: a port whose width differs, only when both widths are constant (no parameter in either)."""
import json
import os
import re
import shutil
import subprocess

from .given import code_spans

DESIGN_EXT = (".sv", ".v")
INCLUDE_EXT = (".svh", ".vh", ".sv", ".v")
CONTEXT_ROOTS = ("docs", "rtl", "verif")
TEXT_EXT = (".md", ".txt", ".rst", ".sv", ".v", ".svh", ".vh", ".json", ".yml", ".yaml", ".py", "")
_DIRS = {"input": "input", "output": "output", "inout": "inout", "in": "input", "out": "output"}
_TYPE_WORDS = {"logic", "reg", "wire", "bit", "signed", "unsigned", "int", "integer", "byte", "shortint", "longint",
               "tri", "var", "input", "output", "inout", "uwire", "wand", "wor", "supply0", "supply1", "tri0", "tri1"}
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*")
_IFACE_HEADING = re.compile(r"(?i)\b(interface|interfaces|ports?|signals?|i/o|io|pins?|inputs?|outputs?)\b")
_NOT_IFACE_HEADING = re.compile(r"(?i)\b(internal|register|registers|state|states|local|fsm|timing|example)\b")
_PARAM_HEADING = re.compile(r"(?i)\bparam")
KINDS = ("missing_module", "missing_port", "missing_param", "spelling", "width")


def norm(name):
    return name.replace("_", "").lower()


# ---------- reading the task tree (inside the root only) ----------

def _inside(root, path):
    root = os.path.realpath(root)
    full = os.path.realpath(path)
    return full == root or full.startswith(root + os.sep)


def _files(root, sub, exts):
    out = []
    base = os.path.join(root, sub)
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            if os.path.splitext(fn)[1].lower() in exts and _inside(root, full) and not os.path.islink(full):
                out.append(full)
    return out


def _read(root, path):
    if not _inside(root, path):
        raise PermissionError(f"{path} is outside the task tree")
    with open(path, errors="replace") as f:
        return f.read()


def given_record(root):
    """The task as the agent sees it at the start, shaped like a dataset record: {"prompt", "context"}. Read once,
    before any edit, so the original RTL is the given interface."""
    prompt = ""
    p = os.path.join(root, "prompt.json")
    if os.path.isfile(p):
        try:
            prompt = json.loads(_read(root, p)).get("prompt", "") or ""
        except ValueError:
            prompt = ""
    context = {}
    for sub in CONTEXT_ROOTS:
        for full in _files(root, sub, TEXT_EXT):
            try:
                if os.path.getsize(full) <= 2_000_000:
                    context[os.path.relpath(full, root)] = _read(root, full)
            except OSError:
                continue
    return {"prompt": prompt, "context": context}


def _inline_includes(text, sources, depth=0):
    """`include "x.vh"` replaced by the text of an rtl/ file of that name (others are dropped): no file outside
    the tree is ever opened, by us or by pyslang."""
    def sub(m):
        name = os.path.basename(m.group(1))
        body = sources.get(name)
        return _inline_includes(body, sources, depth + 1) if body is not None and depth < 8 else ""
    return re.sub(r'(?m)^\s*`include\s+"([^"]+)"\s*$', sub, text)


# ---------- elaboration ----------

def _const_type(syntax):
    """True when a port's declared type has no names in it (no parameter): its width is a constant."""
    words = [w for w in _IDENT.findall(syntax or "") if w not in _TYPE_WORDS]
    return not words


def _modules_pyslang(texts):
    """{module: {"ports": {name: {"dir", "width"}}, "params": {name: is_local}}}, and the error lines."""
    from pyslang.ast import Compilation, SymbolKind
    from pyslang.syntax import SyntaxTree

    comp = Compilation()
    for name, text in texts.items():
        comp.addSyntaxTree(SyntaxTree.fromText(text, name))
    errors = [f"{d.code}" for d in comp.getAllDiagnostics() if d.isError()]
    bodies = {}

    def visit(sym):
        if sym.kind == SymbolKind.Instance:
            bodies.setdefault(sym.body.definition.name, sym.body)
        return True

    for top in comp.getRoot().topInstances:
        top.visit(visit)
    mods = {}
    for name, body in bodies.items():
        ports = {}
        for p in body.portList:
            if not p.name:
                continue
            direction = getattr(p, "direction", None)
            d = {"In": "input", "Out": "output", "InOut": "inout", "Ref": "ref"}.get(getattr(direction, "name", ""))
            width = None
            sym = getattr(p, "internalSymbol", None)
            dt = getattr(sym, "declaredType", None) if sym is not None else None
            ts = getattr(dt, "typeSyntax", None) if dt is not None else None
            try:
                if _const_type(str(ts) if ts is not None else "") and p.type is not None:
                    width = int(p.type.bitWidth) or None
            except (AttributeError, TypeError, ValueError):
                width = None
            ports[p.name] = {"dir": d, "width": width}
        params = {prm.name: bool(prm.isLocalParam) for prm in body.parameters if prm.name}
        mods[name] = {"ports": ports, "params": params}
    return mods, errors


def _modules_yosys(root, files, top, timeout, env=None, user=None):
    """Yosys `read_verilog -sv; hierarchy -top <top>` and its JSON. Widths count as constant only in a module with
    no parameters (Yosys has already evaluated them)."""
    if not shutil.which("yosys"):
        return None, "yosys not available"
    rel = [os.path.relpath(f, root) for f in files]
    script = f"read_verilog -sv {' '.join(rel)}; hierarchy {'-top ' + top if top else '-auto-top'}; proc; write_json -"
    try:
        p = subprocess.run(["yosys", "-q", "-p", script], cwd=root, capture_output=True, text=True, errors="replace",
                           timeout=timeout, env=env, user=user)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, f"yosys: {type(e).__name__}"
    if p.returncode != 0:
        return None, (p.stderr or p.stdout or "").strip()[-400:]
    try:
        data = json.loads(p.stdout[p.stdout.index("{"):])
    except ValueError:
        return None, "yosys wrote no JSON"
    mods = {}
    for name, m in (data.get("modules") or {}).items():
        if name.startswith("$"):
            continue
        name = re.sub(r"^\$paramod\\(\w+)\\.*$", r"\1", name)
        params = {k: False for k in (m.get("parameter_default_values") or {})}
        ports = {k: {"dir": v.get("direction"), "width": len(v.get("bits", [])) if not params else None}
                 for k, v in (m.get("ports") or {}).items()}
        mods.setdefault(name, {"ports": ports, "params": params})
    return mods, ""


def design_sources(root):
    """{relative path: text} of the design under rtl/, with includes inlined."""
    inc = {}
    for full in _files(root, "rtl", INCLUDE_EXT):
        inc.setdefault(os.path.basename(full), _read(root, full))
    out = {}
    for full in _files(root, "rtl", DESIGN_EXT):
        out[os.path.relpath(full, root)] = _inline_includes(_read(root, full), inc)
    return out


def elaborate(root, top_hint=None, timeout=30.0, env=None, user=None):
    """(modules, engine, note). engine is "pyslang", "yosys" (the fallback) or None (could not elaborate)."""
    texts = design_sources(root)
    if not texts:
        return {}, None, "no .sv/.v files under rtl/"
    try:
        mods, errors = _modules_pyslang(texts)
    except Exception as e:  # pyslang itself failed on the input
        mods, errors = {}, [f"pyslang: {type(e).__name__}"]
    if mods and not errors:
        return mods, "pyslang", ""
    top = top_hint if top_hint and top_hint in mods else None
    ymods, why = _modules_yosys(root, [os.path.join(root, r) for r in texts], top, timeout, env, user)
    if ymods:
        return ymods, "yosys", f"pyslang could not elaborate it ({', '.join(sorted(set(errors))[:3])}); Yosys did"
    if mods:
        return mods, "pyslang", f"elaborated with errors ({', '.join(sorted(set(errors))[:3])})"
    return {}, None, f"could not elaborate: pyslang {', '.join(sorted(set(errors))[:3])}; yosys {why[:200]}"


# ---------- the given interface ----------

def _module_headers(text):
    """Verilog module headers (`module x ... );`) anywhere in a text, each closed with endmodule."""
    out = []
    for m in re.finditer(r"\bmodule\s+[A-Za-z_]\w*\s*(?:#\s*\(.*?\)\s*)?\(.*?\)\s*;", text, re.DOTALL):
        out.append(m.group(0) + "\nendmodule\n")
    return out


def _width_text(s):
    """A width from a doc cell or note: [7:0] -> 8, '8', '8-bit', '8 bits' -> 8; anything with a name -> None."""
    s = (s or "").strip().strip("`*")
    m = re.search(r"\[\s*([^\]:]+?)\s*:\s*([^\]]+?)\s*\]", s)
    if m:
        try:
            hi, lo = int(m.group(1)), int(m.group(2))
            return abs(hi - lo) + 1
        except ValueError:
            return None
    m = re.fullmatch(r"(\d+)(?:\s*-?\s*bits?)?", s, re.IGNORECASE)
    return int(m.group(1)) if m else None


_HEADER_WORDS = {"name", "signal", "signals", "port", "ports", "pin", "description", "type", "function", "width",
                 "direction", "dir", "parameter", "parameters", "value", "default", "size", "bits", "range", "notes",
                 "note", "purpose", "field", "comment", "comments", "details"}


def _name_cell(cell):
    """(name, width) from a table cell or a bullet's lead: `name`, **name**, name[7:0], name [WIDTH-1:0]."""
    c = cell.strip().strip("*`").strip()
    if c.lower() in _HEADER_WORDS and c[:1].isupper() and c[1:].islower():
        return None, None  # a table's header word ("Type", "Description"), not a name
    m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*(\[[^\]]*\])?\s*$", c.replace("`", "").replace("*", "").strip())
    if not m:
        return None, None
    return m.group(1), (_width_text(m.group(2)) if m.group(2) else None)


def _sections(text):
    """[(heading chain, lines)] of a markdown text."""
    chain, out, cur = [], [], []
    for ln in text.splitlines():
        h = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if h:
            out.append((list(chain), cur))
            level = len(h.group(1))
            chain = [c for c in chain if c[0] < level] + [(level, h.group(2).strip())]
            cur = []
        else:
            cur.append(ln)
    out.append((list(chain), cur))
    return out


def _table_rows(lines):
    """Rows of the markdown tables in `lines`, each a dict with the header's cells as keys (lower-cased)."""
    rows, header = [], None
    for ln in lines + [""]:
        if ln.strip().startswith("|"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if header is None:
                header = [c.lower().strip("*` ") for c in cells]
            elif all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            else:
                rows.append(dict(zip(header, cells)))
        else:
            header = None
    return rows


def _col(row, *words):
    for k, v in row.items():
        if any(w in k for w in words):
            return v
    return None


def _doc_interface(text):
    """(ports {name: {"dir", "width"}}, params set, the heading chain each came from) from one document."""
    found = []  # (kind, name, dir, width, headings)
    for chain, lines in _sections(text):
        heads = [h for _, h in chain]
        last = chain[-1][1] if chain else ""
        iface = any(_IFACE_HEADING.search(h) for _, h in chain) and not _NOT_IFACE_HEADING.search(last)
        param = bool(chain) and bool(_PARAM_HEADING.search(last))
        for row in _table_rows(lines):
            cells = list(row.values())
            name_cell = _col(row, "signal", "port", "name", "pin") or (cells[0] if cells else "")
            name, w = _name_cell(name_cell or "")
            if not name:
                continue
            if any("param" in k for k in row) or param:
                found.append(("param", name, None, None, heads))
                continue
            dcell = (_col(row, "direction", "dir", "i/o", "type") or "").strip("*` ").lower()
            d = _DIRS.get(dcell) or next((_DIRS[c.strip("*` ").lower()] for c in cells
                                          if c.strip("*` ").lower() in ("input", "output", "inout")), None)
            if d:
                wcell = _col(row, "width", "size", "bits", "range")
                found.append(("port", name, d, w if w is not None else _width_text(wcell or ""), heads))
        if not (iface or param):
            continue
        sub_dir = next((_DIRS[w.lower()] for w in re.findall(r"(?i)\b(input|output|inout)s?\b", last)), None)
        for ln in lines:
            b = re.match(r"^\s*[-*+]\s+(.*)$", ln)
            if not b:
                continue
            body = b.group(1)
            m = re.match(r"(\*\*[^*]+\*\*|`[^`]+`)\s*(\[[^\]]*\])?\s*:?\s*(.*)$", body)
            if m:
                lead, rng, rest = m.group(1), m.group(2), m.group(3)
            else:
                m = re.match(r"([A-Za-z_]\w*)\s*(\[[^\]]*\])?\s*:\s*(.*)$", body)
                if not m:
                    continue
                lead, rng, rest = m.group(1), m.group(2), m.group(3)
            name, w = _name_cell(lead.rstrip(":").replace(":**", "**"))
            if not name:
                continue
            if rng and w is None:
                w = _width_text(rng)
            if param:
                found.append(("param", name, None, None, heads))
                continue
            d = next((_DIRS[x.lower()] for x in re.findall(r"(?i)\b(input|output|inout)\b", rest[:80])), sub_dir)
            if w is None:
                wm = re.search(r"\((\d+)[- ]bits?\)|\b(\d+)-bit\b", rest[:80])
                w = int(wm.group(1) or wm.group(2)) if wm else None
            found.append(("port", name, d, w, heads))
    return found


def _owner(heads, known):
    """The module a doc section is about: the deepest heading that names a known module, or a module-shaped name
    (in backticks, or with an underscore) in a heading. None when no heading names one."""
    for h in reversed(heads):
        h = h.replace("**", "")
        for n in known:
            if re.search(rf"(?<![\w]){re.escape(n)}(?![\w])", h):
                return n
        m = re.search(r"`([A-Za-z_]\w*)`", h) or re.search(r"(?<![\w/])([a-z][a-z0-9]*_[a-z0-9_]+)(?![\w/])", h)
        if m:
            return m.group(1)
    return None


def _named_modules(prompt, docs, existing=()):
    """Module names the prompt or a document asks for, in order of appearance. A file name counts as a module name
    (`timer_module.sv`), unless that file is already in the context (its module may be named otherwise)."""
    pats = [r"`(\w+)`\s+(?:top-level\s+|top\s+)?module", r"\bmodule,?\s+(?:named\s+|called\s+)?`(\w+)`",
            r"\bdefined as\s+`(\w+)`", r"(?:/code/)?rtl/(\w+)\.s?v\b", r"`(\w+)\.s?v`",
            r"\bModule Name:?\s*`?(\w+)`?", r"\bmodule named\s+(\w+)"]
    out = []
    for text in [prompt] + docs:
        text = (text or "").replace("**", "")
        hits = sorted((m.start(), m.group(1)) for p in pats for m in re.finditer(p, text))
        for _, n in hits:
            if n not in out and n not in existing and not re.match(r"(?i)^(tb_|test_)|.*_(tb|test)$", n):
                out.append(n)
    return out


_NOT_MODULE = {"if", "for", "while", "case", "assign", "always", "initial", "module", "function", "task", "begin",
               "end", "return", "foreach", "repeat", "wait", "forever", "else", "automatic", "static", "property",
               "sequence", "assert", "assume", "cover", "covergroup", "class", "new", "bind", "fork", "join"}
_INST = re.compile(r"(?<![\w.$`])([A-Za-z_]\w*)\s*(?:#\s*\(((?:[^()]|\([^()]*\))*)\)\s*)?([A-Za-z_]\w*)\s*"
                   r"(?:\[[^\]]*\]\s*)?\(((?:[^;])*?)\)\s*;", re.DOTALL)


def _tb_instances(text):
    """{module: (port names, parameter names)} from named connections in a testbench under verif/."""
    text = re.sub(r"//[^\n]*|/\*.*?\*/", " ", text, flags=re.DOTALL)
    out = {}
    for m in _INST.finditer(text):
        mod, params, conns = m.group(1), m.group(2) or "", m.group(4)
        ports = re.findall(r"\.(\w+)\s*\(", conns)
        if mod in _NOT_MODULE or not ports:
            continue
        got = out.setdefault(mod, (set(), set()))
        got[0].update(ports)
        got[1].update(re.findall(r"\.(\w+)\s*\(", params))
    return out


def given_interface(record):
    """{module: {"ports", "params", "source"}} and the set of names given in code spans, from a record of what the
    agent was given (given_record)."""
    ctx = record.get("context") or {}
    prompt = record.get("prompt") or ""
    mods = {}
    rtl = {k: v for k, v in ctx.items() if k.startswith("rtl/") and k.endswith(DESIGN_EXT)}
    if rtl:
        inc = {os.path.basename(k): v for k, v in ctx.items() if k.startswith("rtl/") and k.endswith(INCLUDE_EXT)}
        try:
            got, _ = _modules_pyslang({k: _inline_includes(v, inc) for k, v in rtl.items()})
        except Exception:
            got = {}
        for name, m in got.items():
            mods[name] = {**m, "source": "rtl"}
    docs = [v for k, v in ctx.items() if not k.endswith((".sv", ".v", ".svh", ".vh", ".py"))]
    for text in [prompt] + docs:
        for hdr in _module_headers(text):
            try:
                got, _ = _modules_pyslang({"header.sv": hdr})
            except Exception:
                continue
            for name, m in got.items():
                if name not in mods:
                    mods[name] = {**m, "source": "header"}
    files = {os.path.splitext(os.path.basename(k))[0] for k in ctx if k.startswith("rtl/")}
    named = _named_modules(prompt, docs, existing=files)
    targets = [n for n in named if n not in mods]
    known = list(named) + [n for n in mods if n not in named]
    doc_items = [(k, v) for k, v in ctx.items() if not k.endswith((".sv", ".v", ".svh", ".vh", ".py"))]
    for doc_name, text in doc_items:
        stem = os.path.splitext(os.path.basename(doc_name))[0]
        default = stem if stem in known else (targets[0] if len(targets) == 1 else None)
        for kind, name, d, w, heads in _doc_interface(text):
            owner, sub = _owner(heads, known), False
            if owner is None:
                owner = default
            elif owner not in known:
                sub = True  # a module only a heading names (a submodule): compared if it exists, never required
            if not owner or (owner in mods and mods[owner]["source"] not in ("doc", "doc_sub")):
                continue  # an original file or a header already gives this module's interface
            m = mods.setdefault(owner, {"ports": {}, "params": {}, "source": "doc_sub" if sub else "doc"})
            if kind == "param":
                m["params"].setdefault(name, False)
            elif name not in m["params"]:
                m["ports"].setdefault(name, {"dir": d, "width": w})
    for k, text in ctx.items():  # the module a visible testbench instantiates: its port and parameter names
        if not (k.startswith("verif/") and k.endswith(DESIGN_EXT)):
            continue
        for mod, (ports, params) in _tb_instances(text).items():
            if mod in mods and mods[mod]["source"] not in ("doc", "prompt"):
                continue
            if mod not in mods and mod not in named:
                continue  # a module no one asked for (a model, a helper): not the interface
            m = mods.setdefault(mod, {"ports": {}, "params": {}, "source": "testbench"})
            for p in ports:
                m["ports"].setdefault(p, {"dir": None, "width": None})
            for p in params:
                m["params"].setdefault(p, False)
    for n in targets:  # a module the prompt asks for, even with no interface found: its name is given
        mods.setdefault(n, {"ports": {}, "params": {}, "source": "prompt"})
    for owner in targets[:1]:  # the prompt's own parameter list: "parameterization (XLEN=32, LINES=8192)"
        if owner in mods and mods[owner]["source"] == "doc":
            for n in re.findall(r"\b([A-Z][A-Z0-9_]*)\s*=\s*\d", prompt):
                mods[owner]["params"].setdefault(n, False)
    # A module is required (missing_module when the design lacks it) when the original RTL defines it, the prompt
    # itself names it, or a visible testbench instantiates it; one only a document names is compared if it exists.
    asked = set(_named_modules(prompt, [], existing=files))
    for name, m in mods.items():
        m["required"] = m["source"] in ("rtl", "testbench") or name in asked
    names = set(_IDENT.findall(code_spans("\n".join([prompt] + docs))))
    for m in mods.values():
        names |= set(m["ports"]) | set(m["params"])
    names |= set(mods)
    return mods, names


# ---------- the comparison ----------

def compare(given, given_names, design):
    """Findings: [{"kind", "module", "name", "detail"}], sorted, without duplicates."""
    out = []
    dnorm = {}
    for d in design:
        dnorm.setdefault(norm(d), d)
    for g, gm in sorted(given.items()):
        if g in design:
            dname = g
        elif norm(g) in dnorm:
            dname = dnorm[norm(g)]
            out.append({"kind": "spelling", "module": dname, "name": dname,
                        "detail": f"module `{dname}` is spelled `{g}` in the given interface"})
        elif gm.get("source") == "doc_sub" or not gm.get("required", True):
            continue
        else:
            out.append({"kind": "missing_module", "module": g, "name": g,
                        "detail": f"module `{g}` ({_src(gm)}) is not in the design"})
            continue
        dm = design[dname]
        pnorm = {norm(p): p for p in dm["ports"]}
        for p, gp in sorted(gm["ports"].items()):
            if p in dm["ports"]:
                dw, gw = dm["ports"][p].get("width"), gp.get("width")
                if dw and gw and dw != gw:
                    out.append({"kind": "width", "module": dname, "name": p,
                                "detail": f"port `{p}` of `{dname}` is {dw} bits wide; the given interface says {gw}"})
            elif norm(p) in pnorm:
                out.append({"kind": "spelling", "module": dname, "name": pnorm[norm(p)],
                            "detail": f"port `{pnorm[norm(p)]}` of `{dname}` is spelled `{p}` in the given "
                                      f"interface"})
            else:
                out.append({"kind": "missing_port", "module": dname, "name": p,
                            "detail": f"port `{p}` ({_src(gm)}) is not a port of `{dname}`"})
        anorm = {norm(x): x for x in list(dm["params"]) + list(dm["ports"])}
        for p in sorted(gm["params"]):
            if p in dm["params"]:
                continue
            if norm(p) in anorm and anorm[norm(p)] in dm["params"]:
                out.append({"kind": "spelling", "module": dname, "name": anorm[norm(p)],
                            "detail": f"parameter `{anorm[norm(p)]}` of `{dname}` is spelled `{p}` in the given "
                                      f"interface"})
            elif not gm["params"][p]:  # a given localparam need not be a parameter
                out.append({"kind": "missing_param", "module": dname, "name": p,
                            "detail": f"parameter `{p}` ({_src(gm)}) is not a parameter of `{dname}`"})
    # names in the design (modules, ports, parameters) that a given name spells differently
    gnorm = {}
    for n in given_names:
        gnorm.setdefault(norm(n), set()).add(n)
    for d, dm in sorted(design.items()):
        for n in [d] + sorted(dm["ports"]) + sorted(x for x, local in dm["params"].items() if not local):
            if n in given_names or norm(n) not in gnorm:
                continue
            alt = sorted(gnorm[norm(n)])[0]
            out.append({"kind": "spelling", "module": d, "name": n,
                        "detail": f"`{n}` in `{d}` is spelled `{alt}` in the given interface"})
    seen, uniq = set(), []
    for f in sorted(out, key=lambda f: (KINDS.index(f["kind"]), f["module"], f["name"])):
        k = (f["kind"], f["module"], f["name"])
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    return uniq


def _src(gm):
    return {"rtl": "in the original RTL", "header": "in a module header you were given",
            "doc": "in the specification", "doc_sub": "in the specification",
            "testbench": "in the testbench you were given",
            "prompt": "named in the task"}.get(gm.get("source"), "given")


class InterfaceCheck:
    """One per problem: the given interface is read at the start; check() elaborates the current RTL and compares.
    Its result has the shape of a check result ({"ok", "summary"}), so reflect sees it like lint."""

    def __init__(self, root, timeout_s=30.0, env=None, user=None):
        self.root = root
        self.timeout_s = timeout_s
        self.env = env
        self.user = user
        self.record = given_record(root)
        self.given, self.names = given_interface(self.record)

    def check(self):
        tops = [n for n, m in self.given.items() if m["source"] != "rtl"] or sorted(self.given)
        design, engine, note = elaborate(self.root, top_hint=tops[0] if tops else None, timeout=self.timeout_s,
                                         env=self.env, user=self.user)
        res = {"engine": engine, "note": note, "findings": []}
        if not self.given:
            return {**res, "ok": None, "summary": "no interface given in the prompt, docs or original files"}
        if engine is None:
            return {**res, "ok": None, "summary": note}
        findings = compare(self.given, self.names, design)
        res["findings"] = findings
        head = (f"[the design elaborated with {engine}{'; ' + note if note else ''}; compared with the interface "
                f"in the prompt, the docs and the original files: {len(self.given)} module(s)]")
        if not findings:
            return {**res, "ok": True, "summary": head + "\nno mismatch"}
        lines = [f"- {f['kind']}: {f['detail']}" for f in findings[:40]]
        more = [f"- and {len(findings) - 40} more"] if len(findings) > 40 else []
        return {**res, "ok": False, "summary": "\n".join([head] + lines + more)}


def mismatch_key(result):
    """The mismatch set of one check result, to tell a repeat from a new mismatch."""
    return tuple(sorted((f["kind"], f["module"], f["name"]) for f in (result or {}).get("findings", [])))
