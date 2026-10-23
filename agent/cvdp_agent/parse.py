"""Parse LLM replies. Plans and decisions are small JSON objects; edits are tagged blocks, because whole
SystemVerilog files survive tags much better than JSON string escaping."""
import json
import re

_BLOCK = re.compile(r'<(file|diff|tb)\s+path="([^"]+)"([^>]*)>\n?(.*?)</\1>', re.DOTALL)
_ATTR = re.compile(r'(\w+)="([^"]*)"')
_CHECKS = re.compile(r"<checks>(.*?)</checks>", re.DOTALL)
_FENCE = re.compile(r"^\s*```[\w-]*\n(.*?)\n```\s*$", re.DOTALL)
DECISIONS = ("edit_again", "submit", "give_up")


def extract_json(text):
    """The first JSON object in the text, or None."""
    if not text:
        return None
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(1))
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    decoder = json.JSONDecoder()
    start = text.find("{")
    while start != -1:
        try:
            obj, _ = decoder.raw_decode(text, start)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        start = text.find("{", start + 1)
    return None


def parse_plan(text):
    obj = extract_json(text) or {}
    files = obj.get("files_to_change") or []
    if isinstance(files, str):
        files = [files]
    return {
        "files_to_change": [str(f) for f in files][:20],
        "approach": str(obj.get("approach") or text or "")[:4000],
        "check_plan": str(obj.get("check_plan") or "")[:1000],
    }


def parse_decision(text):
    obj = extract_json(text) or {}
    d = str(obj.get("decision", "")).strip().lower()
    if d not in DECISIONS:
        m = re.search(r"\b(edit_again|submit|give_up)\b", text or "")
        d = m.group(1) if m else "submit"
    return {"decision": d, "reason": str(obj.get("reason") or "")[:2000]}


def parse_edit(text):
    files, diffs, tbs = [], [], []
    for kind, path, attrs, body in _BLOCK.findall(text or ""):
        fm = _FENCE.match(body)
        if fm:
            body = fm.group(1) + "\n"
        a = dict(_ATTR.findall(attrs))
        if kind == "file":
            files.append({"path": path, "content": body})
        elif kind == "diff":
            diffs.append({"path": path, "diff": body})
        else:
            tbs.append({"path": path, "content": body, "top": a.get("top", "")})
    m = _CHECKS.search(text or "")
    checks = [c.strip().lower() for c in m.group(1).split(",") if c.strip()] if m else ["compile", "lint"]
    return {"files": files, "diffs": diffs, "tb": tbs, "checks": checks}
