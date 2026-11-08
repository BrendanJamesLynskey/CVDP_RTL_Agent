"""M3l: build the examples bundle for arm E, on the runner, before the run (no model, no pack prose in the output).

    python3 tools/fetch_examples.py <pack checkout>/reference <tag> <out.json> [--local-clones DIR] [--upstream-dir DIR]

Checks the reference layer against the manifest pinned in agent/cvdp_agent/examples.py, drops every entry of a
deny-listed repo, fetches each remaining upstream file once from the public repository at its pinned SHA
(raw.githubusercontent.com/<repo>/<sha>/<path>), and writes the bundle (index fields, the file's notice, the code to
show and the upstream file). Prints counts and the sha256 of every fetched file's group, never pack text.
--upstream-dir writes each fetched file there too (the leak guard's public text). --local-clones reads `git show <sha>:<path>` from DIR/<owner>_<repo> instead (tests and the dry run only).
Exit 0 on success, 2 on a refusal."""
import hashlib
import json
import os
import subprocess
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent"))

from cvdp_agent import examples  # noqa: E402


def fetch_http(repo, sha, path):
    url = f"https://raw.githubusercontent.com/{repo}/{sha}/{path}"
    last = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception as e:  # retried; a persistent failure refuses the run
            last = e
    raise examples.ExamplesError(f"cannot fetch {url}: {type(last).__name__}")


def fetch_local(clones):
    def f(repo, sha, path):
        d = os.path.join(clones, repo.replace("/", "_"))
        p = subprocess.run(["git", "-C", d, "show", f"{sha}:{path}"], capture_output=True)
        if p.returncode:
            raise examples.ExamplesError(f"{repo}@{sha[:8]}:{path} not in {d}")
        return p.stdout
    return f


def fetch_dir(base):
    """Tests only (EXAMPLES_FETCH_DIR): files laid out as <base>/<owner>/<repo>/<sha>/<path>; no network."""
    def f(repo, sha, path):
        p = os.path.join(base, repo, sha, path)
        if not os.path.isfile(p):
            raise examples.ExamplesError(f"{repo}@{sha[:8]}:{path} not in the fixture")
        return open(p, "rb").read()
    return f


def main(argv):
    clones, upstream, args = None, None, []
    it = iter(argv)
    for a in it:
        if a == "--local-clones":
            clones = next(it, None)
        elif a == "--upstream-dir":
            upstream = next(it, None)
        else:
            args.append(a)
    if len(args) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    ref, tag, out = args
    try:
        fixture = os.environ.get("EXAMPLES_FETCH_DIR", "")  # tests only; the workflow never sets it
        pins = os.environ.get("EXAMPLES_PINS", "")
        fetch = fetch_dir(fixture) if fixture else fetch_local(clones) if clones else fetch_http
        bundle, rep = examples.build_bundle(ref, tag, fetch, json.load(open(pins)) if pins else None)
    except (examples.ExamplesError, OSError) as e:
        print(f"fetch_examples.py: refused: {e}", file=sys.stderr)
        return 2
    with open(out, "w") as f:
        json.dump(bundle, f, sort_keys=True)
    if upstream:
        os.makedirs(upstream, exist_ok=True)
        for e in bundle["entries"]:
            with open(os.path.join(upstream, e["file_sha256"] + ".sv"), "w") as f:
                f.write(e["src_text"])
    digest = hashlib.sha256(json.dumps(bundle["files"], sort_keys=True).encode()).hexdigest()
    print(f"examples bundle {tag}: {rep['index']} entries in the index, {len(rep['repo_denied'])} withheld by the repo "
          f"deny-list, {len(rep['dropped'])} dropped, {rep['kept']} kept from {len(bundle['files'])} upstream files "
          f"(files sha256 {digest})")
    for i, why in rep["dropped"]:
        print(f"dropped {i}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
