"""M3g's held-out set: CVDP's non-agentic (copilot) problems that our agent can take, frozen before any run.

The 86 agentic evaluation problems have been read and analysed in depth, so a result on them is a development-set
result. This tool picks a held-out set nobody has inspected, and turns it into the agentic format the harness runs
our agent on. It reads only field names, categories, file names and the harness's image and source-list lines: never
a problem's prompt, its hidden tests, its reference solution or its patch.

  freeze  The eligible pool, from the pinned non-agentic file (no_commercial, so open tools only):
            - category cid002 (RTL completion), cid003 (spec to RTL) or cid004 (RTL modification);
            - the harness runs on the open-source simulation image (docker-compose or its Dockerfile names
              __OSS_SIM_IMAGE__, and nothing names a commercial tool);
            - every output file is under rtl/ and is in the harness's VERILOG_SOURCES;
            - its design name (the id without prefix and number) is not one of the 92 agentic problems' names, and
              no non-empty given file is byte-identical to a file of an agentic problem.
          With more than --max problems, a seeded random sample of --sample (Python's random.Random(seed).sample
          over the sorted ids). The smoke problems come from the pool's remainder, never from the frozen set,
          and share no design name with it.
          Writes the ids file (header: dataset file, revision, SHA-256, seed, counts by category).

  build   The frozen problems in the harness's agentic format, using the harness's own copilot-to-agentic
          transformer (src/data_transformer.py at the pinned commit), with one line added to each prompt naming the
          file(s) the harness compiles: in copilot mode the harness writes the model's answer to those files itself,
          so an agent must be told where to write it. Run with --force-agentic (the ids are cvdp_copilot_*).

Usage:
  python3 tools/m3g_heldout.py freeze <nonagentic.jsonl> <agentic.jsonl> --revision REV [--seed N] [--sample 100]
          [--max 120] [--smoke 3] --out tools/m3g_heldout_ids.txt --smoke-out tools/m3g_smoke_ids.txt
  python3 tools/m3g_heldout.py build <nonagentic.jsonl> <ids.txt> <out.jsonl> --cvdp <harness checkout>
"""
import argparse
import collections
import hashlib
import json
import os
import random
import re
import sys

CATEGORIES = {"cid002": "RTL completion", "cid003": "spec to RTL", "cid004": "RTL modification"}
COMMERCIAL = ("__VERIF_EDA_IMAGE__", "cadence", "xrun", "vcs", "questa", "__LICENSE_NETWORK__")
OUTPUT_NOTE = ("\n\nWrite your answer to {files}: the grader compiles the design from {there}, so the module must be "
               "complete in {there}.")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stem(pid):
    """The design name: cvdp_copilot_fifo_0003 -> fifo (agentic ids alike)."""
    return re.sub(r"^cvdp_(copilot|agentic)_", "", pid).rsplit("_", 1)[0]


def load(path):
    return [json.loads(ln) for ln in open(path) if ln.strip()]


def harness_sources(row):
    """The rtl/ files the harness's .env compiles (VERILOG_SOURCES), as relative paths."""
    env = row["harness"]["files"].get("src/.env", "")
    vs = " ".join(re.findall(r"VERILOG_SOURCES\s*=\s*(.*)", env))
    return set(re.findall(r"/code/(rtl/\S+)", vs))


def open_tools(row):
    files = row["harness"]["files"]
    text = files.get("docker-compose.yml", "") + "".join(v for k, v in files.items() if k.startswith("Dockerfile"))
    return "__OSS_SIM_IMAGE__" in text and not any(c.lower() in text.lower() for c in COMMERCIAL)


def eligible(nonagentic, agentic):
    """(pool ids, reasons excluded {id: reason}). Reads no prompt, test or solution text."""
    names = {stem(r["id"]) for r in agentic}
    hashes = {hashlib.sha256(v.encode()).hexdigest() for r in agentic for v in (r.get("context") or {}).values()
              if v.strip()}
    pool, out = [], {}
    for r in nonagentic:
        pid = r["id"]
        if r["categories"][0] not in CATEGORIES:
            continue
        outs = set(r["output"]["context"])
        if not open_tools(r):
            out[pid] = "not open tools"
        elif not outs or any(not o.startswith("rtl/") for o in outs) or not outs <= harness_sources(r):
            out[pid] = "output not an rtl/ file the harness compiles"
        elif stem(pid) in names:
            out[pid] = "design name shared with an agentic problem"
        elif any(hashlib.sha256(v.encode()).hexdigest() in hashes for v in r["input"]["context"].values() if v.strip()):
            out[pid] = "a given file identical to an agentic problem's"
        else:
            pool.append(pid)
    return sorted(pool), out


def freeze(a):
    na, ag = load(a.nonagentic), load(a.agentic)
    cats = {r["id"]: r["categories"] for r in na}
    pool, excluded = eligible(na, ag)
    rng = random.Random(a.seed)
    chosen = sorted(rng.sample(pool, a.sample)) if len(pool) > a.max else list(pool)
    taken = {stem(p) for p in chosen}  # smoke problems share no design name with the frozen set either
    rest = [p for p in pool if p not in set(chosen) and stem(p) not in taken]
    smoke = sorted(random.Random(a.seed + 1).sample(rest, min(a.smoke, len(rest)))) if rest else []
    by = collections.Counter(cats[p][0] for p in chosen)
    by_d = collections.Counter(tuple(cats[p]) for p in chosen)
    reasons = collections.Counter(excluded.values())
    head = [
        "# M3g held-out set (frozen before any scored run; do not edit)",
        f"# source: nvidia/cvdp-benchmark-dataset, {os.path.basename(a.nonagentic_name or a.nonagentic)}",
        f"# revision: {a.revision}",
        f"# sha256: {sha256_file(a.nonagentic)}",
        f"# rule: tools/m3g_heldout.py freeze (categories {', '.join(sorted(CATEGORIES))}, open tools, output in "
        "rtl/ and compiled by the harness, no design name or given file shared with the 92 agentic problems)",
        f"# eligible: {len(pool)}; excluded from {sum(1 for r in na if r['categories'][0] in CATEGORIES)}: "
        + ", ".join(f"{k} {v}" for k, v in sorted(reasons.items())),
        f"# sample: random.Random({a.seed}).sample(sorted eligible ids, {a.sample})" if len(pool) > a.max
        else "# sample: none (all eligible)",
        f"# count: {len(chosen)}: " + ", ".join(f"{k} ({CATEGORIES[k]}) {by[k]}" for k in sorted(by)),
        "# by difficulty: " + ", ".join(f"{c}/{d} {n}" for (c, d), n in sorted(by_d.items())),
        f"# smoke problems (not in this set): random.Random({a.seed + 1}).sample(the {len(rest)} eligible problems "
        f"outside it whose design name is not in it, {a.smoke}), in tools/m3g_smoke_ids.txt",
    ]
    with open(a.out, "w") as f:
        f.write("\n".join(head + chosen) + "\n")
    if a.smoke_out:
        with open(a.smoke_out, "w") as f:
            f.write("\n".join([f"# M3g smoke problems: eligible but not in the held-out set (seed {a.seed + 1})"]
                              + smoke) + "\n")
    print("\n".join(head))
    print(f"smoke: {', '.join(smoke)}")


def read_ids(path):
    return [ln.strip() for ln in open(path) if ln.strip() and not ln.startswith("#")]


def transformer(cvdp_dir):
    """The harness's own DataTransformer (src/data_transformer.py at the pinned commit), loaded from its file alone:
    it needs only the standard library, while the harness package's __init__ pulls in all its requirements."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("cvdp_data_transformer",
                                                  os.path.join(cvdp_dir, "src", "data_transformer.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.DataTransformer()


def build_rows(rows, ids, tf):
    by_id = {r["id"]: r for r in rows}
    missing = [i for i in ids if i not in by_id]
    if missing:
        raise SystemExit(f"not in the dataset: {', '.join(missing)}")
    out = []
    for pid in ids:
        r = by_id[pid]
        files = sorted(r["output"]["context"])
        t = tf.transform_datapoint_to_agentic(r)
        names = " and ".join(f"`{x}`" for x in files)
        t["prompt"] = t["prompt"] + OUTPUT_NOTE.format(files=names, there="that file" if len(files) == 1
                                                       else "those files")
        out.append(t)
    return out


def build(a):
    rows = build_rows(load(a.nonagentic), read_ids(a.ids), transformer(a.cvdp))
    with open(a.out, "w") as f:
        for t in rows:
            f.write(json.dumps(t) + "\n")
    print(len(rows))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("nonagentic")
    f.add_argument("agentic")
    f.add_argument("--nonagentic-name", default="", help="the dataset's own file name, for the header")
    f.add_argument("--revision", required=True)
    f.add_argument("--seed", type=int, default=20261030)
    f.add_argument("--sample", type=int, default=100)
    f.add_argument("--max", type=int, default=120)
    f.add_argument("--smoke", type=int, default=3)
    f.add_argument("--out", required=True)
    f.add_argument("--smoke-out", default="")
    b = sub.add_parser("build")
    b.add_argument("nonagentic")
    b.add_argument("ids")
    b.add_argument("out")
    b.add_argument("--cvdp", required=True, help="the harness checkout (for its transformer)")
    a = ap.parse_args(argv)
    (freeze if a.cmd == "freeze" else build)(a)


if __name__ == "__main__":
    main()
