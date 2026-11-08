"""M3l arm E: real, well-reviewed RTL shown as examples (`CVDP_RETRIEVED_EXAMPLES=1`, apiloop harness only).

Per problem the agent's first user message gets, after the task, the one or two closest modules from the private
pack's `reference/` layer (pack tag v4.0): the upstream code only, never the pack's own prose. Everything here is
deterministic and stdlib only; no model, no network inside the run.

Three stages.
1. `build_bundle` (run once per sweep, on the runner, by tools/fetch_examples.py): checks the pack's reference/ layer
   against the manifest pinned here, drops every entry of a deny-listed repo, fetches each remaining upstream file
   from the public repository at its pinned SHA (once per file; the sha256 of every file is recorded), checks that
   the entry's excerpt is byte-for-byte in that file, and writes one JSON bundle: index fields, the file's notice,
   the text to show, and the upstream file itself. The bundle holds index metadata and public code, no pack prose.
2. `retrieve` (in the run, per problem): an idf-weighted word-coverage score (score_entries) of the entries' title, keywords, section, module, port and parameter
   names, queried with what the agent can see (the prompt and the docs/, rtl/ and verif/ files; never a hidden test
   or a harness file). Entries of a problem-specific overlap deny-list are withheld: the entry's source file shares
   a module name with a visible file, or shares at least OVERLAP_MIN of its 5-line shingles with the visible text.
   The top K entries at or above MIN_SCORE are shown, at most MAX_BYTES in all. Below the threshold: no example, and
   the run is exactly arm R.
3. `block` formats the shown code under a fixed lead-in (LEAD_IN) and a fixed one-line header per example."""
import hashlib
import json
import math
import os
import re

from .files import TEXT_EXT
from .memory import _STOP

K = 2                  # examples per problem, at most
MIN_SCORE = 0.55       # idf-weighted share of an entry's words found in the task, at least (chosen on the 86 dev problems only: docs/reports/m3l)
MAX_BYTES = 12_000     # shown code per problem, at most
WHOLE_MAX_LINES = 250  # a whole module is shown only up to this many lines; longer, the excerpt
SHINGLE = 5            # lines per shingle of the overlap deny-list
SHINGLE_MIN_CHARS = 40 # a shingle of less normalised text than this is boilerplate and is not counted
OVERLAP_MIN = 0.10     # share of the entry's source-file shingles found in the visible text that withholds the entry
VISIBLE_ROOTS = ("docs", "rtl", "verif")

# Repos the benchmark's tasks are drawn from (agreed with the owner, 2026-11-08). The pack names the OpenHW projects
# under openhwgroup/; the owner's list names openhwfoundation/: both spellings are denied.
REPO_DENY_EXACT = ("openhwfoundation/cv32e40p", "openhwfoundation/cva6", "openhwgroup/cv32e40p", "openhwgroup/cva6",
                   "lowrisc/ibex")
REPO_DENY_OWNER = ("pulp-platform",)
REPO_DENY_NAME_PART = ("ibex",)   # any ibex fork, for example cheriot-ibex

# The pack's reference/ layer at its tag: the commit and the SHA-256 of reference/MANIFEST.sha256.
REFERENCE_PINNED = {
    "v4.0": {"commit": "2af8e0e6ce68c8e1756192103904afc47ad73684",
             "manifest_sha256": "c36d5df5c65a1f49af2628ccd00cc7d5ca090a6dfd2ffbe0fb66e4543291a917", "entries": 86},
}

LEAD_IN_ONE = ("# Reference examples\n"
               "Below is 1 module from well-reviewed open-source hardware projects, picked automatically because it "
               "looks related to this task. It is an example of how such designs are written, not part of the task: "
               "the task's own interface, names and timing rules come first. Use it as you see fit.\n")
LEAD_IN_MANY = ("# Reference examples\n"
                "Below are {n} modules from well-reviewed open-source hardware projects, picked automatically because "
                "they look related to this task. They are examples of how such designs are written, not part of the "
                "task: the task's own interface, names and timing rules come first. Use them as you see fit.\n")
HEADER = "// repo: {repo} | path: {path} | sha: {sha} | licence: {licence} | notice: {notice}"


class ExamplesError(ValueError):
    """The bundle or the pack's reference layer is not what is pinned, or is not usable."""


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


# ---------- the repo deny-list ----------

def repo_denied(repo):
    r = (repo or "").strip().lower()
    owner, _, name = r.partition("/")
    return r in REPO_DENY_EXACT or owner in REPO_DENY_OWNER or any(p in name for p in REPO_DENY_NAME_PART)


# ---------- text helpers ----------

def _words(text):
    out = []
    for w in re.findall(r"[A-Za-z][A-Za-z0-9_]+", text or ""):
        w = w.lower()
        parts = [w] + [p for p in w.split("_") if len(p) > 2] if "_" in w else [w]
        out.extend(parts)
    return out


def tokens(text):
    """Lower-case word tokens: identifiers whole and split at `_`, stop words and 1-2 letter words dropped, a plural
    `s` removed from words of five letters or more."""
    out = []
    for w in _words(text):
        if len(w) <= 2 or w in _STOP:
            continue
        out.append(w[:-1] if len(w) >= 5 and w.endswith("s") and not w.endswith("ss") else w)
    return out


def entry_text(e):
    """What an entry is scored on: title, keywords, section and also-sections, and the module name. Port and parameter
    names (clk_i, data_i, Width) are in the index but not scored: they are the words every module shares."""
    return " ".join([e.get("title", ""), " ".join(e.get("keywords", [])), e.get("section", ""),
                     " ".join(e.get("also", [])), e.get("module", "")])


def declared_modules(text):
    text = re.sub(r"//[^\n]*|/\*.*?\*/", " ", text or "", flags=re.DOTALL)
    return set(re.findall(r"\b(?:module|package|interface)\s+(?:automatic\s+|static\s+)?([A-Za-z_]\w*)", text))


def norm_lines(text):
    """Code lines normalised for shingling: comments dropped, lower-cased, white space collapsed, empty lines dropped."""
    text = re.sub(r"/\*.*?\*/", " ", text or "", flags=re.DOTALL)
    out = []
    for ln in text.splitlines():
        ln = re.sub(r"//.*", "", ln).strip().lower()
        ln = re.sub(r"\s+", " ", ln)
        if ln:
            out.append(ln)
    return out


def shingles(text, n=SHINGLE):
    ls = norm_lines(text)
    out = set()
    for i in range(len(ls) - n + 1):
        s = "\n".join(ls[i:i + n])
        if len(s) >= SHINGLE_MIN_CHARS:
            out.add(hashlib.sha1(s.encode()).hexdigest()[:16])
    return out


# ---------- what the agent can see ----------

def visible_from_root(root):
    """(prompt, {relative path: text}) from the task tree: prompt.json and the text files under docs/, rtl/ and
    verif/. Nothing else is opened: no hidden test, no harness file, nothing under rundir/ or src/."""
    prompt = ""
    try:
        with open(os.path.join(root, "prompt.json")) as f:
            prompt = json.load(f).get("prompt", "") or ""
    except (OSError, ValueError):
        pass
    files = {}
    for top in VISIBLE_ROOTS:
        base = os.path.join(root, top)
        for d, dirs, names in os.walk(base):
            dirs.sort()
            for n in sorted(names):
                if os.path.splitext(n)[1].lower() not in TEXT_EXT:
                    continue
                full = os.path.join(d, n)
                try:
                    if os.path.getsize(full) > 400_000:
                        continue
                    with open(full, errors="replace") as f:
                        files[os.path.relpath(full, root)] = f.read()
                except OSError:
                    continue
    return prompt, files


def visible_from_record(record):
    """The same from a dataset-shaped record ({"prompt", "context": {path: text}}), for the dry run."""
    ctx = record.get("context") or {}
    files = {p: t or "" for p, t in ctx.items()
             if p.split("/")[0] in VISIBLE_ROOTS and os.path.splitext(p)[1].lower() in TEXT_EXT}
    return record.get("prompt") or "", files


# ---------- retrieval ----------

def score_entries(entries, query):
    """[(score, entry index)] for every entry, best first; ties broken by the order in the bundle.

    The score is the share of an entry's descriptive words that the query holds, each word weighted by its inverse
    document frequency over the entries (BM25's idf, log(1 + (N - df + 0.5) / (df + 0.5))): 1.0 when every word of the
    entry's title, keywords, sections and module name is in what the agent can see, 0.0 when none is. A plain BM25 sum
    grows with the length of the query (a prompt plus its docs) and scored every module high for every problem on
    the dev set; this share does not, so one fixed threshold means the same thing for a short and a long task."""
    if not entries:
        return []
    docs = [set(tokens(entry_text(e))) for e in entries]
    n = len(docs)
    df = {}
    for d in docs:
        for t in d:
            df[t] = df.get(t, 0) + 1
    idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
    q = set(tokens(query))
    out = []
    for i, d in enumerate(docs):
        tot = sum(idf[t] for t in d)
        out.append((round(sum(idf[t] for t in d & q) / tot, 6) if tot else 0.0, i))
    return sorted(out, key=lambda x: (-x[0], x[1]))


def overlap_reason(entry, vis_modules, vis_shingles):
    """"module" / "text" / "" : why this entry is withheld for a problem whose visible files have these declared
    module names and shingles."""
    if declared_modules(entry.get("src_text", "")) & vis_modules:
        return "module"
    mine = shingles(entry.get("src_text", ""))
    if mine and vis_shingles and len(mine & vis_shingles) / len(mine) >= OVERLAP_MIN:
        return "text"
    return ""


def overlap_score(entry, vis_shingles):
    mine = shingles(entry.get("src_text", ""))
    return round(len(mine & vis_shingles) / len(mine), 4) if mine and vis_shingles else 0.0


def retrieve(entries, prompt, files, k=K, min_score=MIN_SCORE, max_bytes=MAX_BYTES, repo_denied_n=0):
    """The retrieval record for one problem: {"ids", "shown" (entries, in order), "bytes", "top_score",
    "withheld_repo", "withheld_overlap", "withheld": [(id, reason, score)], "ranked": [(id, score)]}. `entries` are the
    bundle's (already without the deny-listed repos)."""
    texts = [prompt] + [files[p] for p in sorted(files)]
    query = "\n".join(texts)
    vis_text = "\n".join(files[p] for p in sorted(files)) + "\n" + (prompt or "")
    vis_modules = set()
    for p in sorted(files):
        vis_modules |= declared_modules(files[p])
    vis_sh = shingles(vis_text)
    ranked = score_entries(entries, query)
    top_score = ranked[0][0] if ranked else 0.0
    chosen, withheld, used = [], [], 0
    for score, i in ranked:
        if score < min_score or len(chosen) >= k:
            break
        e = entries[i]
        why = overlap_reason(e, vis_modules, vis_sh)
        if why:
            withheld.append((e["id"], why, overlap_score(e, vis_sh), score))
            continue
        shown = e["shown"]
        size = len(shown.encode())
        if used + size > max_bytes:
            if e.get("shown_kind") == "module" and e.get("excerpt") and used + len(e["excerpt"].encode()) <= max_bytes:
                e = dict(e, shown=e["excerpt"], shown_kind="excerpt")
                size = len(e["shown"].encode())
            else:
                continue
        chosen.append(e)
        used += size
    return {"ids": [e["id"] for e in chosen], "shown": chosen, "bytes": used, "top_score": top_score,
            "withheld_repo": repo_denied_n, "withheld_overlap": len(withheld), "withheld": withheld,
            "ranked": [(entries[i]["id"], s) for s, i in ranked[:5]]}


def header(e):
    return HEADER.format(repo=e["repo"], path=e["path"], sha=e["sha"], licence=e["licence"], notice=e["notice"])


def lead_in(n):
    return LEAD_IN_ONE if n == 1 else LEAD_IN_MANY.format(n=n)


def block(chosen):
    """The text appended to the first user message; "" when nothing was chosen."""
    if not chosen:
        return ""
    parts = [lead_in(len(chosen))]
    for i, e in enumerate(chosen, 1):
        parts.append(f"\n## Example {i}\n```systemverilog\n{header(e)}\n{e['shown'].rstrip()}\n```\n")
    return "".join(parts)


# ---------- the bundle ----------

def load_bundle(path):
    with open(path) as f:
        b = json.load(f)
    if b.get("version") != 1 or not isinstance(b.get("entries"), list):
        raise ExamplesError(f"{path}: not an examples bundle")
    return b


def parse_source(md):
    """The `## Source` block of an entry as a dict of strings (a flat YAML subset), and the excerpt runs."""
    m = re.search(r"## Source\s*```yaml\n(.*?)```", md, re.DOTALL)
    src = {}
    if m:
        for ln in m.group(1).splitlines():
            k, _, v = ln.partition(":")
            v = v.strip()
            if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
                v = json.loads(v)
            src[k.strip()] = v
    ex = re.search(r"## Excerpt\s.*?```systemverilog\n(.*?)```", md, re.DOTALL)
    return src, (ex.group(1) if ex else "")


def line_ranges(spec):
    out = []
    for part in spec.split(","):
        a, _, b = part.strip().partition("-")
        out.append((int(a), int(b or a)))
    return out


def slice_runs(text, spec):
    """The excerpt as the pack writes it: each run of the listed lines, runs joined by a `// ...` marker line."""
    ls = text.split("\n")
    runs = ["\n".join(ls[a - 1:b]) for a, b in line_ranges(spec)]
    return "\n// ...\n".join(runs) + "\n"


def module_text(text, name):
    """From the line that declares module `name` to its `endmodule` (comments before it, such as a doc block, are
    left out), or None."""
    m = re.search(rf"^[ \t]*module\s+(?:automatic\s+|static\s+)?{re.escape(name)}\b", text, re.M)
    if not m:
        return None
    e = re.compile(r"^[ \t]*endmodule\b[^\n]*", re.M).search(text, m.end())
    return text[m.start():e.end()] + "\n" if e else None


def build_bundle(ref_dir, tag, fetch, pinned=None):
    """(bundle dict, report dict). `fetch(repo, sha, path)` returns the upstream file's bytes. Raises ExamplesError
    when the layer is not the pinned one."""
    pinned = REFERENCE_PINNED if pinned is None else pinned
    if tag not in pinned:
        raise ExamplesError(f"unknown pack tag {tag!r}; pinned: {', '.join(sorted(pinned))}")
    mf = os.path.join(ref_dir, "MANIFEST.sha256")
    try:
        got = sha256_bytes(open(mf, "rb").read())
    except OSError as e:
        raise ExamplesError(f"{ref_dir}: no MANIFEST.sha256 ({e})") from None
    if got != pinned[tag]["manifest_sha256"]:
        raise ExamplesError(f"{tag}: reference/MANIFEST.sha256 is {got[:12]}..., pinned "
                            f"{pinned[tag]['manifest_sha256'][:12]}...")
    for ln in open(mf):
        if not ln.strip():
            continue
        h, name = ln.split()[0], ln.split()[1].lstrip("*")
        full = os.path.join(ref_dir, name)
        if not os.path.isfile(full) or sha256_bytes(open(full, "rb").read()) != h:
            raise ExamplesError(f"{tag}: {name} does not match the manifest")
    index = [json.loads(ln) for ln in open(os.path.join(ref_dir, "INDEX.jsonl")) if ln.strip()]
    if "entries" in pinned[tag] and len(index) != pinned[tag]["entries"]:
        raise ExamplesError(f"{tag}: {len(index)} entries, pinned {pinned[tag]['entries']}")
    files, cache, entries = {}, {}, []
    rep = {"index": len(index), "repo_denied": [], "dropped": [], "kept": 0}
    for e in index:
        if repo_denied(e["repo"]):
            rep["repo_denied"].append(e["id"])
            continue
        key = f"{e['repo']}@{e['sha']}:{e['path']}"
        if key not in cache:
            raw = fetch(e["repo"], e["sha"], e["path"])
            cache[key] = raw
            files[key] = sha256_bytes(raw)
        text = cache[key].decode("utf-8", errors="replace")
        md = open(os.path.join(ref_dir, e["section"], e["id"] + ".md")).read()
        src, excerpt_md = parse_source(md)
        excerpt = slice_runs(text, e["lines"])
        if excerpt.rstrip("\n") != excerpt_md.rstrip("\n"):
            rep["dropped"].append((e["id"], "excerpt is not byte-exact in the fetched file"))
            continue
        if not src.get("notice") or src["notice"] not in text:
            rep["dropped"].append((e["id"], "notice not found in the fetched file"))
            continue
        shown, kind = excerpt, "excerpt"
        if e.get("whole_module"):
            mt = module_text(text, e["module"])
            if mt and mt.count("\n") <= WHOLE_MAX_LINES:
                shown, kind = mt, "module"
        entries.append({**{k: e[k] for k in ("id", "title", "section", "also", "keywords", "repo", "sha", "path", "lines",
                                             "licence", "module", "ports", "params", "whole_module")},
                        "notice": src["notice"], "file_sha256": files[key], "shown": shown, "shown_kind": kind,
                        "excerpt": excerpt, "src_text": text})
    rep["kept"] = len(entries)
    bundle = {"version": 1, "pack_tag": tag, "pack_commit": pinned[tag]["commit"], "index_n": len(index),
              "repo_denied_n": len(rep["repo_denied"]), "repo_denied_ids": rep["repo_denied"],
              "dropped": rep["dropped"], "files": files, "entries": entries}
    return bundle, rep
