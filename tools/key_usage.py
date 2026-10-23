"""Print the OpenRouter key's cumulative usage (USD) as `usage=<value>` for $GITHUB_OUTPUT, and nothing else: never
the key and never its label (the label holds part of the key). Prints `usage=unknown` if the call fails.

Usage: OPENROUTER_API_KEY=... python3 tools/key_usage.py >> "$GITHUB_OUTPUT"
"""
import json
import os
import urllib.request


def main():
    key = os.environ.get("OPENROUTER_API_KEY", "")
    usage = "unknown"
    if key:
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/key",
                                         headers={"Authorization": f"Bearer {key}"})
            with urllib.request.urlopen(req, timeout=20) as r:
                u = (json.load(r).get("data") or {}).get("usage")
            if isinstance(u, (int, float)):
                usage = f"{u:.6f}"
        except Exception:
            pass
    print(f"usage={usage}")


if __name__ == "__main__":
    main()
