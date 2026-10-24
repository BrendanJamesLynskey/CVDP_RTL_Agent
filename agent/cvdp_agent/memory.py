"""The lessons memory (M3b): a frozen snapshot of short, general lessons, and a deterministic, model-free retrieval
of the top k for a problem (BM25 over the lessons, queried with the task prompt and the problem's docs). No
embedding API, no LLM: the same prompt always gives the same lessons in the same order.

A snapshot is a JSON file {"lessons": [{"id", "text"}, ...], "provenance": {...}, "hash": "<16 hex>"}. Its hash
is the SHA-256 (first 16 hex digits) of the canonical JSON of everything but "hash", and is in its file name
(`lessons_<hash>.json`). Every result row records it, so each result names its snapshot."""
import hashlib
import json
import math
import re

K1, B = 1.2, 0.75
_STOP = set("""a an the and or of to in on for with by at as is are be was were it its this that these those
from into than then when where which who what how not no if else do does did can may must should will would
your you we our they their them use used using each any all more most other some such only also so""".split())


def canonical_hash(snapshot):
    body = {k: v for k, v in snapshot.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]


def load(path):
    """The snapshot at `path`, after checking its recorded hash against its content."""
    with open(path) as f:
        snap = json.load(f)
    h = canonical_hash(snap)
    if snap.get("hash") != h:
        raise ValueError(f"lessons snapshot {path}: recorded hash {snap.get('hash')!r} is not its content's ({h})")
    return snap


def tokens(text):
    return [t for t in re.findall(r"[a-z][a-z0-9_]+", (text or "").lower()) if t not in _STOP and len(t) > 2]


def retrieve(lessons, query, k=5):
    """The top k lessons for `query` by BM25 score, ties broken by the order in the snapshot. Returns
    [(lesson, score)]."""
    docs = [tokens(x["text"]) for x in lessons]
    if not docs:
        return []
    n = len(docs)
    avg = sum(len(d) for d in docs) / n or 1.0
    df = {}
    for d in docs:
        for t in set(d):
            df[t] = df.get(t, 0) + 1
    q = set(tokens(query))
    scores = []
    for i, d in enumerate(docs):
        tf = {}
        for t in d:
            tf[t] = tf.get(t, 0) + 1
        s = 0.0
        for t in q & tf.keys():
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            s += idf * tf[t] * (K1 + 1) / (tf[t] + K1 * (1 - B + B * len(d) / avg))
        scores.append((round(s, 6), i))
    ranked = sorted(scores, key=lambda x: (-x[0], x[1]))[:k]
    return [(lessons[i], s) for s, i in ranked]
