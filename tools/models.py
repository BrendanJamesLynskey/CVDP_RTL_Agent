"""For a list of OpenRouter model IDs: does each exist, its prices, its context length, and whether it takes the
`reasoning` parameter (with the efforts it lists, and whether reasoning is mandatory). From the public model list,
https://openrouter.ai/api/v1/models, which needs no key. Markdown on stdout.

Usage: python3 tools/models.py <model id> [...]
       python3 tools/models.py --search <text> [...]   (list the IDs that contain the text, to find candidates)
"""
import json
import sys
import urllib.request

URL = "https://openrouter.ai/api/v1/models"


def fetch(url=URL):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)["data"]


def per_million(x):
    try:
        return f"${float(x) * 1e6:.3f}"
    except (TypeError, ValueError):
        return "n/a"


def _hhmm(x):
    return f"{int(x) // 100:02d}:{int(x) % 100:02d}"


def overrides(pricing):
    """Conditional prices (by prompt length, or by day and UTC time), grouped by price: "$in/$out when ..."."""
    groups = {}
    for o in pricing.get("overrides") or []:
        cond = []
        if o.get("min_prompt_tokens"):
            cond.append(f"prompt ≥ {int(o['min_prompt_tokens']):,} tokens")
        days = o.get("utc_days")
        if days:
            cond.append("weekends" if sorted(days) == ["saturday", "sunday"] else
                        "weekdays" if len(days) == 5 and "saturday" not in days else ",".join(d[:3] for d in days))
        if "utc_start" in o or "utc_end" in o:
            cond[-1:] = [f"{cond[-1] if cond else ''} {_hhmm(o.get('utc_start', 0))}–{_hhmm(o.get('utc_end', 0))} UTC"
                         .strip()]
        price = f"{per_million(o.get('prompt'))}/{per_million(o.get('completion'))}"
        groups.setdefault(price, []).append(" ".join(cond) or "always")
    return "; ".join(f"{p} for {', '.join(c)}" for p, c in groups.items())


def describe(m):
    """One row's fields for a model entry from the list."""
    params = m.get("supported_parameters") or []
    r = m.get("reasoning")
    takes = "reasoning" in params or "include_reasoning" in params
    detail = ""
    if isinstance(r, dict):
        efforts = r.get("supported_efforts")
        bits = ["efforts: " + ("any" if efforts is None else ", ".join(efforts) or "none")]
        if r.get("default_effort"):
            bits.append(f"default {r['default_effort']}")
        if r.get("default_enabled") is not None:
            bits.append("on by default" if r["default_enabled"] else "off by default")
        if r.get("mandatory"):
            bits.append("mandatory (no `none`)")
        if r.get("supports_max_tokens"):
            bits.append("max_tokens")
        detail = "; ".join(bits)
    pricing = m.get("pricing") or {}
    return {
        "input": per_million(pricing.get("prompt")),
        "output": per_million(pricing.get("completion")),
        "context": f"{int(m['context_length']):,}" if m.get("context_length") else "n/a",
        "notes": overrides(pricing),
        "reasoning": ("yes" if takes else "no") + (f" ({detail})" if detail else ""),
    }


def table(ids, data):
    by_id = {m["id"]: m for m in data}
    out = ["| Model | Exists | $/M input | $/M output | Context | `reasoning` parameter | Other prices (input/output) |",
           "|---|---|---|---|---|---|---|"]
    for i in ids:
        m = by_id.get(i)
        if m is None:
            out.append(f"| `{i}` | no | | | | | |")
            continue
        d = describe(m)
        out.append(f"| `{i}` | yes | {d['input']} | {d['output']} | {d['context']} | {d['reasoning']} "
                   f"| {d['notes']} |")
    return "\n".join(out)


def main(argv):
    data = fetch()
    if argv and argv[0] == "--search":
        for m in sorted(data, key=lambda m: m["id"]):
            if any(t.lower() in m["id"].lower() for t in argv[1:]):
                d = describe(m)
                print(f"{m['id']}\t{d['input']}\t{d['output']}\t{d['context']}\t{d['reasoning']}")
        return
    print(table(argv, data))


if __name__ == "__main__":
    main(sys.argv[1:])
