"""M3h leak guard: fail if any 80-byte window of the private pack's text is in what a job is about to publish.

    python3 tools/leak_guard.py --pack <pack generic/ dir> [--public DIR_OR_FILE ...] PATH [PATH ...]

The secrets are every skill file's bytes and every line of INDEX.md (a line shorter than 80 bytes, but at least 40,
counts whole). PATHs are files or directories (searched recursively, binary files too). A file leaks if it holds an
80-byte window of a secret, either as raw bytes or after normalising both sides: JSON string escapes undone
(`\\n`, `\\"`, `\\uXXXX`, ...), a diff's leading `+`/`-` dropped from each line, and every run of white space made one
space. So a skill pasted into a patch, a JSON summary or a re-indented file is caught too.

Public text is not private: the pack's writer used standard idioms (cocotb imports, a two-flop synchroniser), and
the same bytes are in the public benchmark itself. `--public` names text the job already holds from public sources
(the dataset files, the benchmark harness checkout; never anything under work/). A match counts only if at least one
of its 80-byte windows, normalised, is not found in that public text, normalised. Without `--public`, every match counts.

Output names the file, the form (raw or normalised), the byte offset, which secret (skill name or INDEX line number)
and the match length, never the matched text. Exit 1 on any leak, 0 if none, 2 on a usage error.

How: every 20-byte substring of every secret is indexed. Any match of 39 bytes or more must contain one of the
target's 20-byte chunks at a multiple of 20, so only those are looked up; each hit is extended both ways to its full
common length. A 20-byte substring found more than 64 times across the secrets (runs of spaces, say) is not
indexed, so a "match" made only of such filler is not reported."""
import argparse
import os
import re
import sys

WINDOW = 80
SHORT_MIN = 40
CHUNK = 20
COMMON = 64
_ESC = re.compile(rb'\\(u[0-9a-fA-F]{4}|["\\/bfnrt])')
_WS = re.compile(rb"\s+")
_DIFF = re.compile(rb"(?m)^[+-]")
_SIMPLE = {b'"': b'"', b"\\": b"\\", b"/": b"/", b"b": b"\b", b"f": b"\f", b"n": b"\n", b"r": b"\r", b"t": b"\t"}


def _unescape(m):
    s = m.group(1)
    if s[:1] == b"u":
        try:
            return chr(int(s[1:], 16)).encode("utf-8", "surrogatepass")
        except ValueError:
            return m.group(0)
    return _SIMPLE[s]


def normalise(data):
    data = _ESC.sub(_unescape, data)
    data = _DIFF.sub(b"", data)
    return _WS.sub(b" ", data)


def secrets(pack):
    """[(label, bytes, bytes needed for a match)] from a pack directory."""
    out = []
    for name in sorted(os.listdir(pack)):
        path = os.path.join(pack, name)
        if not name.endswith(".md") or not os.path.isfile(path):
            continue
        data = open(path, "rb").read()
        if name == "INDEX.md":
            for i, line in enumerate(data.split(b"\n"), 1):
                line = line.strip()
                if len(line) >= SHORT_MIN:
                    out.append((f"INDEX.md line {i}", line, min(WINDOW, len(line))))
        elif data:
            out.append((name[:-3], data, WINDOW))
    if not out:
        raise SystemExit(f"leak_guard.py: no pack text found in {pack}")
    return out


class Index:
    def __init__(self, items):
        self.items = items
        grams = {}
        for k, (_, data, _) in enumerate(items):
            for s in range(0, len(data) - CHUNK + 1):
                grams.setdefault(data[s:s + CHUNK], []).append((k, s))
        self.grams = {g: v for g, v in grams.items() if len(v) <= COMMON}

    def find(self, data):
        """[(offset in data, secret index, match length)] for each distinct match of the needed length."""
        hits, seen = [], set()
        for q in range(0, len(data) - CHUNK + 1, CHUNK):
            for k, s in self.grams.get(data[q:q + CHUNK], ()):
                sec = self.items[k][1]
                a = 0
                while a < s and a < q and data[q - a - 1] == sec[s - a - 1]:
                    a += 1
                b = CHUNK
                while s + b < len(sec) and q + b < len(data) and data[q + b] == sec[s + b]:
                    b += 1
                start, length = q - a, a + b
                if length >= self.items[k][2] and (k, start) not in seen:
                    seen.add((k, start))
                    hits.append((start, k, length))
        return hits


def files(paths):
    for p in paths:
        if os.path.isdir(p):
            for d, dirs, names in os.walk(p):
                dirs[:] = sorted(x for x in dirs if x != ".git")  # a checkout's object store: compressed, not text
                for n in sorted(names):
                    f = os.path.join(d, n)
                    if os.path.isfile(f) and not os.path.islink(f):
                        yield f
        elif os.path.isfile(p):
            yield p


class Public:
    """The public corpus, normalised (the dataset holds its files JSON-escaped), for `private()`."""

    def __init__(self, paths):
        raw = [open(f, "rb").read() for f in files(paths or [])]
        self.corpus = b"\0".join(normalise(d) for d in raw)
        self.bytes = sum(len(d) for d in raw)

    def private(self, match, need):
        """True if some `need`-byte window of the normalised `match` is not in the normalised public text."""
        if not self.corpus:
            return True
        m = normalise(match)
        need = min(need, len(m))
        if m in self.corpus:
            return False
        return any(m[i:i + need] not in self.corpus for i in range(0, len(m) - need + 1))


def scan(pack, paths, public=None):
    """[(file, form, offset, secret label, length)] for every leak."""
    pub = public if isinstance(public, Public) else Public(public)
    items = secrets(pack)
    raw = Index(items)
    norm_items = [(lab, normalise(d), n) for lab, d, n in items]
    norm_items = [(lab, d, min(n, len(d))) for lab, d, n in norm_items if len(d) >= SHORT_MIN]
    norm = Index(norm_items)
    leaks = []
    for f in files(paths):
        try:
            data = open(f, "rb").read()
        except OSError:
            continue
        for form, idx, d in (("raw", raw, data), ("normalised", norm, normalise(data))):
            for off, k, length in idx.find(d):
                if pub.private(d[off:off + length], idx.items[k][2]):
                    leaks.append((f, form, off, idx.items[k][0], length))
    return leaks


def main(argv=None):
    ap = argparse.ArgumentParser(description="M3h leak guard")
    ap.add_argument("--pack", required=True, help="the pack's generic/ directory")
    ap.add_argument("--public", action="append", default=[],
                    help="public text the job holds (dataset files, harness checkout); repeatable")
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args(argv)
    if not os.path.isdir(a.pack):
        print(f"leak_guard.py: no pack directory {a.pack}", file=sys.stderr)
        return 2
    pub = Public(a.public)
    leaks = scan(a.pack, a.paths, pub)
    n = sum(1 for _ in files(a.paths))
    for f, form, off, lab, length in leaks[:200]:
        print(f"LEAK {f}: {form} offset {off}: {length} bytes of {lab}")
    if leaks:
        print(f"leak_guard.py: {len(leaks)} match(es) of pack text in {len({x[0] for x in leaks})} file(s) of {n} "
              f"scanned: nothing may be uploaded", file=sys.stderr)
        return 1
    print(f"leak guard: {n} file(s) scanned, no {WINDOW}-byte window of the pack's private text in any of them "
          f"(public text allowed: {pub.bytes} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
