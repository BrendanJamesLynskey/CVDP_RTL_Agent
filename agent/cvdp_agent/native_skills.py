"""M3h: the private RTL knowledge pack as Claude Code's own skills (`CVDP_SKILL_PACK`, claudecode harness only).

The pack is a tagged version of a private repository, checked out by the workflow outside the work dir and mounted
read-only into the agent's container. Its `generic/` directory holds INDEX.md (one "name: description" line per
skill), one <name>.md per skill and MANIFEST.sha256. Before any model call the pack is checked twice: every file
against the manifest, and the manifest's own SHA-256 against the value pinned here for its tag. Anything that
differs refuses the run (stop reason `skills_error`).

Install: each skill becomes `<home>/.claude/skills/<name>/SKILL.md`, a YAML front matter (`name`, and `description`
from INDEX.md) followed by the skill file's bytes unchanged. `<home>` is a fresh directory outside the task tree, set
as HOME for Claude Code only, so the skills never appear in the workspace, the patch or agent_out. Claude Code
(2.1.310) lists user skills from `~/.claude/skills` to the model by name and description and loads a body only on a
`Skill` tool call, which is allowed in `-p` mode without a permission rule.

Nothing here writes or logs skill text anywhere except that private HOME. What is recorded is names, counts, turn
numbers and the manifest hash."""
import json
import os
import re

from . import skillpack

# The tags of the private pack repository and their frozen hashes. The workflow checks the checkout's commit and
# the manifest's SHA-256 against these; the agent checks the manifest again inside its container.
PINNED = {
    "v1.0": {"commit": "b30b32914532b1631a37e160200ebeb815a9bdf6",
             "manifest_sha256": "7ba7b4b39c1a3238e58eec963eb359d64b521305937fd5318eade79faa45285b", "skills": 15},
    "v2.0": {"commit": "19ac3ec485e8b14850f59c89e6244063e9dd81a4",
             "manifest_sha256": "e405fe319fcc3392a415c0911ecc20eb5a90093a1d27b1076e92593e6b9a3298", "skills": 25},
}
# S2c's one line, written as the user-level CLAUDE.md in the same private HOME (CVDP_SKILL_HINT=1)
HINT = "RTL design skills are installed; check them before you start.\n"
_LINE = re.compile(r"^([a-z0-9][a-z0-9-]*):\s+(.+)$")


class PackError(ValueError):
    """The pack is not the pinned one, or is not a pack."""


def verify(path, tag, pinned=None):
    """The manifest's SHA-256, after checking every file and the manifest itself against the pin for `tag`."""
    pinned = PINNED if pinned is None else pinned
    if tag not in pinned:
        raise PackError(f"unknown skill pack tag {tag!r}; known: {', '.join(sorted(pinned))}")
    try:
        files = skillpack.verify(path)
    except skillpack.PackError as e:
        raise PackError(str(e)) from None
    got = skillpack.manifest_hash(path)
    if got != pinned[tag]["manifest_sha256"]:
        raise PackError(f"{tag}: MANIFEST.sha256 is {got[:12]}..., pinned {pinned[tag]['manifest_sha256'][:12]}...")
    if "INDEX.md" not in files:
        raise PackError(f"{tag}: no INDEX.md in the manifest")
    return got


def index(path):
    """[(name, description)] from INDEX.md, in its order; every name has a file and every skill file a line."""
    out = []
    for ln in open(os.path.join(path, "INDEX.md"), encoding="utf-8"):
        m = _LINE.match(ln.strip())
        if m:
            out.append((m.group(1), m.group(2).strip()))
    names = [n for n, _ in out]
    files = sorted(f[:-3] for f in os.listdir(path) if f.endswith(".md") and f != "INDEX.md")
    if sorted(names) != files or len(set(names)) != len(names):
        raise PackError("INDEX.md lines and skill files do not match one to one")
    return out


def front_matter(name, description):
    """YAML front matter; the description as a double-quoted scalar (JSON's escapes are YAML's)."""
    return f"---\nname: {name}\ndescription: {json.dumps(description, ensure_ascii=False)}\n---\n".encode()


def install(path, home, hint=False):
    """Write every skill as <home>/.claude/skills/<name>/SKILL.md (front matter + the file's bytes unchanged), and
    S2c's CLAUDE.md when `hint`. Returns the names installed, in INDEX order."""
    base = os.path.join(home, ".claude", "skills")
    names = []
    for name, desc in index(path):
        with open(os.path.join(path, f"{name}.md"), "rb") as f:
            body = f.read()
        d = os.path.join(base, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "SKILL.md"), "wb") as f:
            f.write(front_matter(name, desc) + body)
        names.append(name)
    if hint:
        with open(os.path.join(home, ".claude", "CLAUDE.md"), "w") as f:
            f.write(HINT)
    return names


def skill_body(skill_md):
    """The bytes after the front matter of a SKILL.md written by `install` (for the tests)."""
    assert skill_md.startswith(b"---\n")
    end = skill_md.index(b"\n---\n", 4) + len(b"\n---\n")
    return skill_md[end:]


def skill_calls(lines):
    """[(turn, skill name)] for every `Skill` tool call in Claude Code's stream-json lines, in order. A turn is a
    distinct assistant message id (stream events split one message's content blocks), counted from 1."""
    calls, ids = [], []
    for line in lines:
        try:
            ev = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(ev, dict) or ev.get("type") != "assistant":
            continue
        msg = ev.get("message") or {}
        mid = msg.get("id") or f"_anon{len(ids)}"
        if mid not in ids:
            ids.append(mid)
        for c in msg.get("content") or []:
            if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "Skill":
                name = str((c.get("input") or {}).get("skill", "")).strip().lstrip("/")
                calls.append((ids.index(mid) + 1, name[:80]))
    return calls


def listed(lines):
    """The skill names Claude Code's `init` event says the model was offered (bundled ones included), or None."""
    for line in lines:
        try:
            ev = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(ev, dict) and ev.get("type") == "system" and ev.get("subtype") == "init":
            return [str(x)[:80] for x in ev.get("skills") or []]
    return None


def tool_skeleton(lines):
    """What the pack arms keep of the transcript: per tool call, its turn and tool name (and a Skill call's skill
    name), no text, no inputs, no results. The raw stream holds the loaded skill bodies, so it is never written."""
    out, ids = [], []
    for line in lines:
        try:
            ev = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(ev, dict):
            continue
        if ev.get("type") == "assistant":
            msg = ev.get("message") or {}
            mid = msg.get("id") or f"_anon{len(ids)}"
            if mid not in ids:
                ids.append(mid)
            for c in msg.get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    rec = {"turn": ids.index(mid) + 1, "tool": str(c.get("name", ""))[:40]}
                    if rec["tool"] == "Skill":
                        rec["skill"] = str((c.get("input") or {}).get("skill", "")).strip().lstrip("/")[:80]
                    out.append(rec)
        elif ev.get("type") == "result":
            out.append({"result": str(ev.get("subtype", ""))[:40], "num_turns": ev.get("num_turns")})
    return out
