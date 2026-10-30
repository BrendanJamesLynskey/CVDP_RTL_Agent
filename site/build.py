#!/usr/bin/env python3
"""Wrap the site's pages (Artifact format: no doctype/html/head/body) into docs/ for GitHub Pages and Vercel.

    python3 site/data/derive.py --inject   # refresh the story's data block and prose numbers from the committed CSVs
    python3 site/data/problems.py          # refresh docs/problems.json (the problem browser's data, loaded by the page)
    python3 site/build.py                  # write docs/index.html, the story's sub-pages and docs/problems.html
    python3 site/build.py --check          # exit 1 if any docs/ page differs from what the sources build

The story has one source, site/story.html. Each of its sections names its page in data-page; this script splits it into
the front page (docs/index.html) and the sub-pages (docs/how.html, ...), each with the same CSS, bar, data block and
script, a breadcrumb at the top and prev / front / next links at the foot. Links to a section or glossary term on
another page are rewritten to point there, and the front page forwards old single-page anchors (index.html#m3d) to
the sub-page that now holds them.

Stdlib only. The head carries the same small reset the Artifact skeleton adds (light colour-scheme,
safe-area padding on :root, zero body margin with a 14px system font, img max-width, [hidden]),
so the pages render the same on Pages and as an Artifact preview.
"""
import html
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
URL = "https://cvdp-rtl-agent.vercel.app/"
# the story's pages, in reading order: (data-page, output file, title, short label, description)
STORY = [
    ("index", "index.html", None, "Front page", None),
    ("how", "how.html", "How it works", "Part 1 · How it works",
     "How the CVDP RTL agent works: a six-node LangGraph graph, its checks and caps, the GitHub Actions pipeline, and one real failure replayed."),
    ("results-m2-m3b", "results-m2-m3b.html", "Results, M0 to M3b", "Part 2 · Results, M0 to M3b",
     "The milestones, three models on 92 problems (M2), six ablations with no detectable effect (M3), and the Deep Agents harness and lessons memory (M3b)."),
    ("results-m3c-m3e", "results-m3c-m3e.html", "Results, M3c to M3e", "Part 3 · Results, M3c to M3e",
     "Two model-free checks (M3c), Claude Code with four Claude models, verify before submit (M3d), and the same agent with Opus 5.5 (M3e)."),
    ("analysis", "analysis.html", "Analysis", "Part 4 · Analysis",
     "Why the agent fails the hidden tests, the agent read as a verification engineer would, and how it compares with published results."),
    ("reference", "reference.html", "Reference", "Part 5 · Reference",
     "Threats to validity, open questions, questions a reviewer might ask, and a glossary."),
]
DATA = [os.path.join("docs", "problems.json")]
# short names for the breadcrumb's "on this page" links
SHORT = {"intro": "One failure, replayed", "how": "How it works", "milestones": "Milestones", "m2": "M2", "m3": "M3", "m3b": "M3b",
         "m3c": "M3c", "ladder": "Claude Code ladder", "m3d": "M3d", "m3e": "M3e", "fail": "Why it fails",
         "dv": "Verification view", "compare": "Comparison", "validity": "Validity", "next": "What's next", "faq": "FAQ",
         "glossary": "Glossary"}
# ids the story's script builds at run time, by page
JS_IDS = [(r"g-[\w-]+", "reference"), (r"q\d+", "reference")]

RESET = (":root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);"
         "padding-bottom:env(safe-area-inset-bottom,0px)}"
         "body{margin:0;font:14px/1.4 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}"
         "img{max-width:100%}[hidden]{display:none!important}")


def read(src):
    body = open(os.path.join(ROOT, "site", src), encoding="utf-8").read()
    if re.search(r"<!doctype|<html[\s>]|<head[\s>]|<body[\s>]", body, re.I):
        sys.exit(f"{src} must not carry its own doctype/html/head/body")
    if "/*DATA:BEGIN*//*DATA:END*/" in body:
        sys.exit("data block is empty: run python3 site/data/derive.py --inject first")
    return body


def wrap(body, url):
    title = re.search(r"<title>(.*?)</title>", body, re.S).group(1).strip()
    desc = re.search(r'<meta name="description" content="(.*?)">', body, re.S).group(1)
    head = [
        "<!doctype html>",
        '<html lang="en-GB">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
        f"<style>{RESET}</style>",
        f'<meta property="og:title" content="{html.escape(title)}">',
        f'<meta property="og:description" content="{desc}">',
        '<meta property="og:type" content="article">',
        f'<meta property="og:url" content="{url}">',
        '<meta name="twitter:card" content="summary">',
        f'<link rel="canonical" href="{url}">',
        "</head>",
        "<body>",
    ]
    return "\n".join(head) + "\n" + body.rstrip() + "\n</body>\n</html>\n"


def href(page):
    """The link to a story page: ./ for the front (served as /), the .html file otherwise (/how under cleanUrls)."""
    return "./" if page == "index" else dict((p, f) for p, f, *_ in STORY)[page]


def split_story():
    """{output file: page text} for the front page and every sub-page of site/story.html."""
    src = read("story.html")
    m0 = src.index('<main id="main">') + len('<main id="main">')
    m1 = src.index("<footer>")
    pre, mid, post = src[:m0], src[m0:m1], src[m1:]
    secs = list(re.finditer(r'(?:<!-- =+ [^\n]*-->\n)?<section class="sec[^"]*" id="([\w-]+)" data-page="([\w-]+)".*?</section>\n*', mid, re.S))
    if re.sub(r"\s+", "", "".join(x.group(0) for x in secs)) != re.sub(r"\s+", "", mid):
        sys.exit("story.html: something between <main> and <footer> is not inside a section with data-page")
    known = [p for p, *_ in STORY]
    bad = sorted({x.group(2) for x in secs} - set(known))
    if bad:
        sys.exit(f"story.html: unknown data-page {bad}")
    by_page = {p: [x for x in secs if x.group(2) == p] for p in known}
    idmap = {}  # every id in the story's sections -> its page
    for x in secs:
        for i in re.findall(r'\sid="([\w.-]+)"', x.group(0)):
            if i in idmap:
                sys.exit(f"story.html: id {i} appears twice")
            idmap[i] = x.group(2)

    def page_of(i):
        if i in idmap:
            return idmap[i]
        for pat, pg in JS_IDS:
            if re.fullmatch(pat, i):
                return pg
        return None

    out = {}
    for n, (page, fname, title, label, desc) in enumerate(STORY):
        body = "\n" + "".join(x.group(0) for x in by_page[page])
        head, tail = pre, post
        if page != "index":
            head = re.sub(r"<title>.*?</title>", f"<title>{title} · CVDP RTL Agent</title>", head, count=1, flags=re.S)
            head = re.sub(r'<meta name="description" content=".*?">', f'<meta name="description" content="{html.escape(desc)}">', head, count=1, flags=re.S)
            names = []
            for x in by_page[page]:
                h2 = re.sub(r"<[^>]+>", "", re.search(r"<h2>(.*?)</h2>", x.group(0), re.S).group(1))
                names.append(f'<a href="#{x.group(1)}">{html.escape(SHORT.get(x.group(1), h2))}</a>')
            crumb = (f'\n<nav class="crumb" aria-label="Where you are"><a href="./">&larr; Front page</a>'
                     f'<span><b>Part {n} of {len(STORY) - 1}</b> &middot; {html.escape(title)}</span><span>On this page: {" &middot; ".join(names)}</span></nav>\n')
            prv, nxt = STORY[n - 1], STORY[n + 1] if n + 1 < len(STORY) else None
            pnav = ['<nav class="pnav" aria-label="Pages">']
            if prv[0] != "index":
                pnav.append(f'<a class="pv" href="{href(prv[0])}"><small>&larr; PREVIOUS</small>{html.escape(prv[2])}</a>')
            pnav.append('<a class="up" href="./#contents"><small>CONTENTS</small>Front page</a>')
            if nxt:
                pnav.append(f'<a class="nx" href="{href(nxt[0])}"><small>NEXT &rarr;</small>{html.escape(nxt[2])}</a>')
            pnav.append("</nav>\n")
            body = crumb + body + "\n".join(pnav) + "\n"
        else:
            # forward old single-page anchors (index.html#m3d, #g-langgraph) to the sub-page that now holds them
            fwd = {i: href(p) for i, p in sorted(idmap.items()) if p != "index"}
            js = ("<script>(function(){var M=" + json.dumps(fwd, separators=(",", ":")) + ";"
                  "var P=" + json.dumps([[pat, href(pg)] for pat, pg in JS_IDS], separators=(",", ":")) + ";"
                  "function go(){var h=decodeURIComponent(location.hash.slice(1));if(!h||document.getElementById(h))return;"
                  "var f=M[h];if(!f)for(var i=0;i<P.length;i++)if(new RegExp('^(?:'+P[i][0]+')$').test(h)){f=P[i][1];break;}"
                  "if(f)location.replace(f+'#'+h);}go();window.addEventListener('hashchange',go);})();</script>\n")
            head = head.replace('<div class="bar"', js + '<div class="bar"', 1)
        text = head + body + tail
        ids_here = {i for i, p in idmap.items() if p == page} | {i for i in re.findall(r'href="#([\w.-]+)"', text) if page_of(i) == page}

        def fix(m):
            i = m.group(1)
            if i in ids_here:
                return m.group(0)
            pg = page_of(i)
            if pg is None:
                sys.exit(f"story.html: link to #{i} has no target")
            return f'href="{href(pg)}#{i}"'
        text = re.sub(r'href="#([\w.-]+)"', fix, text)
        out[fname] = (text, URL if page == "index" else URL + fname[:-5])
    return out, idmap


def pages():
    story, _ = split_story()
    out = {f: wrap(t, u) for f, (t, u) in story.items()}
    out["problems.html"] = wrap(read("problems.html"), URL + "problems")
    return out


def main():
    out = pages()
    if "--check" in sys.argv:
        stale = [f for f, t in out.items() if not os.path.exists(os.path.join(ROOT, "docs", f))
                 or open(os.path.join(ROOT, "docs", f), encoding="utf-8").read() != t]
        if stale:
            sys.exit(f"stale: {stale}; run python3 site/build.py")
        print(f"ok: {len(out)} pages current")
        return
    for f, text in out.items():
        path = os.path.join(ROOT, "docs", f)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(text)
        print(f"wrote {path} ({len(text):,} bytes)")
    for f in DATA:
        if not os.path.exists(os.path.join(ROOT, f)):
            sys.exit(f"{f} is missing: run python3 site/data/problems.py first")


if __name__ == "__main__":
    main()
