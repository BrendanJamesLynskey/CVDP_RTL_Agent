"""M3l: the retriever over the problems' visible files only (free, local, no model). Prints no pack prose and no code.

    python3 tools/m3l_dry_run.py <bundle.json> --set NAME:PROBLEMS.jsonl:IDS.txt [--set ...] --out DIR

Per set, per problem: the chosen entry ids and scores, the entries withheld (by the repo deny-list, which is the same
for every problem, and by the per-problem overlap rule), and whether the problem gets an example. Writes
DIR/dry_run.md (the summary), DIR/retrieval.csv (one row per problem) and DIR/overlap_deny.csv (every
(problem, entry) the overlap rule withholds: ids and scores only). The query is the prompt plus the problem's docs/,
rtl/ and verif/ files from the dataset record's `context`; a record's hidden tests (`harness`) are never read."""
import argparse
import collections
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent"))

from cvdp_agent import examples as X  # noqa: E402


def read_ids(path):
    return [ln.strip() for ln in open(path) if ln.strip() and not ln.startswith("#")]


def run_set(bundle, jsonl, ids):
    recs = {}
    for ln in open(jsonl):
        if ln.strip():
            r = json.loads(ln)
            recs[r["id"]] = {"id": r["id"], "prompt": r.get("prompt"), "context": r.get("context")}  # not `harness`
    rows, deny = [], []
    for pid in ids:
        if pid not in recs:
            raise SystemExit(f"m3l_dry_run.py: {pid} is not in {jsonl}")
        prompt, files = X.visible_from_record(recs[pid])
        out = X.retrieve(bundle["entries"], prompt, files, repo_denied_n=bundle["repo_denied_n"])
        vis_text = "\n".join(files[p] for p in sorted(files)) + "\n" + prompt
        vm = set()
        for p in files:
            vm |= X.declared_modules(files[p])
        vsh = X.shingles(vis_text)
        for e in bundle["entries"]:
            why = X.overlap_reason(e, vm, vsh)
            if why:
                deny.append({"id": pid, "entry": e["id"], "reason": why, "overlap": X.overlap_score(e, vsh)})
        rows.append({"id": pid, "ids": ";".join(out["ids"]), "top_score": round(out["top_score"], 3),
                     "top_entry": out["ranked"][0][0] if out["ranked"] else "",
                     "scores": ";".join(f"{s:.3f}" for i, s in out["ranked"] if i in out["ids"]),
                     "bytes": out["bytes"], "withheld_repo": out["withheld_repo"],
                     "withheld_overlap": out["withheld_overlap"], "n": len(out["ids"])})
    return rows, deny


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle")
    ap.add_argument("--set", action="append", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    bundle = json.load(open(a.bundle))
    os.makedirs(a.out, exist_ok=True)
    allrows, alldeny, md = [], [], []
    tag = bundle["pack_tag"]
    md += [f"# M3l dry run of the retriever (pack {tag})", "",
           "Free and local: the retriever run over the visible files of each problem (prompt, docs/, rtl/, verif/), no "
           "model call. Ids and numbers only: no pack text and no code. Rule and constants: "
           "[preregistration.md](preregistration.md).", "",
           f"Pack entries: {bundle['index_n']} in the index; {bundle['repo_denied_n']} withheld by the repo deny-list "
           f"(for every problem); **{len(bundle['entries'])} remain** ({len(bundle['files'])} upstream files); "
           f"{len(bundle['dropped'])} dropped as not byte-exact. Constants: K={X.K}, minimum score {X.MIN_SCORE}, "
           f"{X.MAX_BYTES} bytes, overlap rule {X.SHINGLE}-line shingles at {X.OVERLAP_MIN:.2f}.", ""]
    rem = collections.Counter(e["repo"] for e in bundle["entries"])
    md += ["Remaining entries by repo: " + ", ".join(f"{r} {n}" for r, n in sorted(rem.items())) + ".",
           "Withheld by the repo deny-list: " + ", ".join(
               f"{r} {n}" for r, n in sorted(collections.Counter(
                   i.split("-")[0] for i in bundle["repo_denied_ids"]).items())) + " (entry-id prefixes).", ""]
    for spec in a.set:
        name, jsonl, idsf = spec.split(":", 2)
        rows, deny = run_set(bundle, jsonl, read_ids(idsf))
        for r in rows:
            r["set"] = name
        for d in deny:
            d["set"] = name
        allrows += rows
        alldeny += deny
        got = [r for r in rows if r["n"]]
        use = collections.Counter(i for r in rows for i in r["ids"].split(";") if i)
        md += [f"## {name}: {len(rows)} problems", "",
               f"- problems that get an example: **{len(got)}** (one: {sum(1 for r in rows if r['n'] == 1)}, two: "
               f"{sum(1 for r in rows if r['n'] == 2)}); **no example: {len(rows) - len(got)}** (these runs are arm R "
               f"exactly)",
               f"- withheld by the overlap rule: {sum(r['withheld_overlap'] for r in rows)} entry/problem pairs "
               f"({len({d['id'] for d in deny})} problems); the rule would withhold {len(deny)} pairs if every entry "
               f"were tried",
               f"- bytes shown: mean {sum(r['bytes'] for r in got) / max(1, len(got)):.0f}, max "
               f"{max([r['bytes'] for r in rows] or [0])}",
               "- most-used entries: " + (", ".join(f"{i} ({n})" for i, n in use.most_common(8)) or "none"), ""]
        if got:
            md += ["| Problem | Chosen entries | Scores |", "|---|---|---|"]
            md += [f"| {r['id']} | {r['ids'].replace(';', ', ')} | {r['scores'].replace(';', ', ')} |" for r in got]
            md.append("")
    with open(os.path.join(a.out, "retrieval.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["set", "id", "n", "ids", "scores", "top_entry", "top_score", "bytes",
                                          "withheld_repo", "withheld_overlap"])
        w.writeheader()
        w.writerows(allrows)
    with open(os.path.join(a.out, "overlap_deny.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["set", "id", "entry", "reason", "overlap"])
        w.writeheader()
        w.writerows(alldeny)
    md += ["All problems, including those with no example, are in [retrieval.csv](retrieval.csv); the overlap "
           "deny-list is [overlap_deny.csv](overlap_deny.csv).", ""]
    with open(os.path.join(a.out, "dry_run.md"), "w") as f:
        f.write("\n".join(md))
    print("\n".join(md[:30]))


if __name__ == "__main__":
    main()
