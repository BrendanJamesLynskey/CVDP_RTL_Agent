"""What the agent is given: the names in the task's prompt and context files. Shared by tools/reachable.py (which
problems an agent can reach at all) and the interface check (interface.py). Deterministic, no LLM.

A name is given when it appears, as a whole word, in a context file that is code, or inside backticks or a fenced
code block of the prompt or a document; a name shaped like an identifier (it has `_`, a digit, or an upper-case
letter after the first) also counts when it appears in plain prose."""
import re

CODE_EXT = (".sv", ".v", ".svh", ".vh", ".py", ".c", ".h", ".json", ".yml", ".yaml", ".tcl", ".mk")
ID_SHAPED = re.compile(r"_|\d|^.+[A-Z]")


def code_spans(text):
    """Text inside backticks and fenced code blocks."""
    fenced = re.findall(r"```.*?```", text, re.DOTALL)
    rest = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    return "\n".join(fenced + re.findall(r"`([^`\n]+)`", rest))


def given_texts(record):
    """(code text, prose text, code spans of the prose) the agent can read, from a dataset-shaped record
    ({"prompt": ..., "context": {path: text}})."""
    code, prose = [], [record.get("prompt") or ""]
    for name, text in (record.get("context") or {}).items():
        (code if name.lower().endswith(CODE_EXT) else prose).append(text or "")
    prose_text = "\n".join(prose)
    return "\n".join(code), prose_text, code_spans(prose_text)


def is_given(name, texts):
    code, prose, spans = texts
    word = re.compile(rf"(?<![\w$]){re.escape(name)}(?![\w$])")
    if word.search(code) or word.search(spans):
        return True
    return bool(ID_SHAPED.search(name)) and bool(word.search(prose))
