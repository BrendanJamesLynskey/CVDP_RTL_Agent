"""Parse LLM replies. Plans and decisions are small JSON objects; edits are tagged blocks, because whole
SystemVerilog files survive tags much better than JSON string escaping."""
import json
import re

_BLOCK = re.compile(r'<(file|diff|tb)\s+path="([^"]+)"([^>]*)>\n?(.*?)</\1>', re.DOTALL)
_ATTR = re.compile(r'(\w+)="([^"]*)"')
_CHECKS = re.compile(r"<checks>(.*?)</checks>", re.DOTALL)
_FENCE = re.compile(r"^\s*```[\w-]*\n(.*?)\n```\s*$", re.DOTALL)
DECISIONS = ("edit_again", "submit", "give_up")
# Tool-call markup some models emit as text instead of an answer: DeepSeek-style special tokens (full-width or
# ASCII bars), and <tool_call> / <function_calls> blocks. A whole block is markup, whatever it holds.
_TOOL_BLOCKS = re.compile(
    r"<[|｜]tool[▁_ ]calls?[▁_ ]begin[|｜]>.*?(?:<[|｜]tool[▁_ ]calls?[▁_ ]end[|｜]>|\Z)"
    r"|<(tool_calls?|function_calls?)\b[^>]*>.*?(?:</\1>|\Z)",
    re.DOTALL | re.IGNORECASE)
_SPECIAL_TOKEN = re.compile(r"<[|｜][^<>]{0,80}?[|｜]>")


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


def strip_tool_markup(text):
    return _SPECIAL_TOKEN.sub("", _TOOL_BLOCKS.sub("", text or ""))


def empty_reply(node, text):
    """An empty reply: nothing after stripping, or only tool-call markup with nothing usable inside it (no edit
    block for an edit, no JSON object for a plan or a decision)."""
    if not (text or "").strip():
        return True
    if strip_tool_markup(text).strip():
        return False
    if node == "edit":
        e = parse_edit(text)
        return not (e["files"] or e["diffs"] or e["tb"])
    obj = extract_json(text) or {}
    return not set(obj) & ({"decision"} if node == "reflect" else {"files_to_change", "approach", "check_plan"})


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
    """`parsed` is False when neither a JSON decision nor a bare decision word was found; `decision` is then
    "submit", the fallback."""
    obj = extract_json(text) or {}
    d = str(obj.get("decision", "")).strip().lower()
    parsed = d in DECISIONS
    if not parsed:
        m = re.search(r"\b(edit_again|submit|give_up)\b", text or "")
        parsed = bool(m)
        d = m.group(1) if m else "submit"
    return {"decision": d, "reason": str(obj.get("reason") or "")[:2000], "parsed": parsed}


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
