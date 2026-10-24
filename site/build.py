#!/usr/bin/env python3
"""Wrap site/story.html (Artifact format: no doctype/html/head/body) into docs/index.html for GitHub Pages.

    python3 site/data/derive.py --inject   # refresh the data block from the committed CSVs
    python3 site/build.py                  # write docs/index.html

Stdlib only. The head carries the same small reset the Artifact skeleton adds (light colour-scheme,
safe-area padding on :root, zero body margin with a 14px system font, img max-width, [hidden]),
so the page renders the same on Pages and as an Artifact preview.
"""
import html
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "site", "story.html")
OUT = os.path.join(ROOT, "docs", "index.html")
URL = "https://brendanjameslynskey.github.io/CVDP_RTL_Agent/"

RESET = (":root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);"
         "padding-bottom:env(safe-area-inset-bottom,0px)}"
         "body{margin:0;font:14px/1.4 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}"
         "img{max-width:100%}[hidden]{display:none!important}")


def main():
    body = open(SRC, encoding="utf-8").read()
    if re.search(r"<!doctype|<html|<head|<body", body, re.I):
        sys.exit("story.html must not carry its own doctype/html/head/body")
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
        f'<meta property="og:url" content="{URL}">',
        '<meta name="twitter:card" content="summary">',
        f'<link rel="canonical" href="{URL}">',
        "</head>",
        "<body>",
    ]
    out = "\n".join(head) + "\n" + body.rstrip() + "\n</body>\n</html>\n"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(out)
    print(f"wrote {OUT} ({len(out):,} bytes)")


if __name__ == "__main__":
    main()
