#!/usr/bin/env python3
"""Wrap the site's pages (Artifact format: no doctype/html/head/body) into docs/ for GitHub Pages and Vercel.

    python3 site/data/derive.py --inject   # refresh the story page's data block from the committed CSVs
    python3 site/data/problems.py          # refresh docs/problems.json (the problem browser's data, loaded by the page)
    python3 site/build.py                  # write docs/index.html and docs/problems.html

Stdlib only. The head carries the same small reset the Artifact skeleton adds (light colour-scheme,
safe-area padding on :root, zero body margin with a 14px system font, img max-width, [hidden]),
so the pages render the same on Pages and as an Artifact preview.
"""
import html
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
URL = "https://cvdp-rtl-agent.vercel.app/"
# (source page, output page, canonical URL)
PAGES = [
    ("story.html", "index.html", URL),
    ("problems.html", "problems.html", URL + "problems"),
]
DATA = [os.path.join("docs", "problems.json")]

RESET = (":root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);"
         "padding-bottom:env(safe-area-inset-bottom,0px)}"
         "body{margin:0;font:14px/1.4 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}"
         "img{max-width:100%}[hidden]{display:none!important}")


def wrap(src, out, url):
    body = open(os.path.join(ROOT, "site", src), encoding="utf-8").read()
    if re.search(r"<!doctype|<html[\s>]|<head[\s>]|<body[\s>]", body, re.I):
        sys.exit(f"{src} must not carry its own doctype/html/head/body")
    if "/*DATA:BEGIN*//*DATA:END*/" in body:
        sys.exit("data block is empty: run python3 site/data/derive.py --inject first")
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
    text = "\n".join(head) + "\n" + body.rstrip() + "\n</body>\n</html>\n"
    path = os.path.join(ROOT, "docs", out)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)
    print(f"wrote {path} ({len(text):,} bytes)")


def main():
    for src, out, url in PAGES:
        wrap(src, out, url)
    for f in DATA:
        if not os.path.exists(os.path.join(ROOT, f)):
            sys.exit(f"{f} is missing: run python3 site/data/problems.py first")


if __name__ == "__main__":
    main()
