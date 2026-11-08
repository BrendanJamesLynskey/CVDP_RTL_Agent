"""M3h: check a checkout of the private knowledge pack against the hashes pinned in this repo, before any model call.

    python3 tools/skill_pack.py verify <pack checkout> <tag>
    python3 tools/skill_pack.py verify-reference <pack checkout> <tag>      (M3l: the reference/ layer)

Checks, in order: the tag is pinned (agent/cvdp_agent/native_skills.py, PINNED); the checkout's HEAD is the pinned
commit (when the checkout is a git repository); every file of `generic/` matches `generic/MANIFEST.sha256`, and no
other .md file is there; the manifest's own SHA-256 is the pinned one; INDEX.md and the skill files match one to
one. Prints the manifest hash and the number of skills, never any file's contents. Exit 0 if all hold, else 2."""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent"))

from cvdp_agent import native_skills  # noqa: E402


def verify(checkout, tag, pinned=None):
    """(manifest sha, skills) or raise native_skills.PackError."""
    pinned = native_skills.PINNED if pinned is None else pinned
    if tag not in pinned:
        raise native_skills.PackError(f"unknown tag {tag!r}; pinned: {', '.join(sorted(pinned))}")
    if os.path.isdir(os.path.join(checkout, ".git")) or os.path.isfile(os.path.join(checkout, ".git")):
        head = subprocess.run(["git", "-C", checkout, "rev-parse", "HEAD"], capture_output=True, text=True).stdout
        if head.strip() != pinned[tag]["commit"]:
            raise native_skills.PackError(f"{tag}: checkout is at {head.strip()[:12]}, pinned "
                                          f"{pinned[tag]['commit'][:12]}")
    gen = os.path.join(checkout, "generic")
    sha = native_skills.verify(gen, tag, pinned)
    n = len(native_skills.index(gen))
    if "skills" in pinned[tag] and n != pinned[tag]["skills"]:
        raise native_skills.PackError(f"{tag}: {n} skills, pinned {pinned[tag]['skills']}")
    return sha, n


def verify_reference(checkout, tag, pinned=None):
    """(manifest sha, entries) for the pack's reference/ layer (M3l): the tag is pinned in agent/cvdp_agent/examples.py,
    the checkout's HEAD is the pinned commit, and reference/MANIFEST.sha256 is the pinned hash. The files are checked
    against that manifest when the bundle is built (examples.build_bundle)."""
    from cvdp_agent import examples

    pinned = examples.REFERENCE_PINNED if pinned is None else pinned
    if tag not in pinned:
        raise native_skills.PackError(f"unknown tag {tag!r}; pinned for the reference layer: {', '.join(sorted(pinned))}")
    if os.path.isdir(os.path.join(checkout, ".git")) or os.path.isfile(os.path.join(checkout, ".git")):
        head = subprocess.run(["git", "-C", checkout, "rev-parse", "HEAD"], capture_output=True, text=True).stdout
        if head.strip() != pinned[tag]["commit"]:
            raise native_skills.PackError(f"{tag}: checkout is at {head.strip()[:12]}, pinned "
                                          f"{pinned[tag]['commit'][:12]}")
    mf = os.path.join(checkout, "reference", "MANIFEST.sha256")
    try:
        sha = native_skills.skillpack.sha256(mf)
    except OSError as e:
        raise native_skills.PackError(f"{checkout}: no reference/MANIFEST.sha256 ({e})") from None
    if sha != pinned[tag]["manifest_sha256"]:
        raise native_skills.PackError(f"{tag}: reference/MANIFEST.sha256 is {sha[:12]}..., pinned "
                                      f"{pinned[tag]['manifest_sha256'][:12]}...")
    n = sum(1 for ln in open(os.path.join(checkout, "reference", "INDEX.jsonl")) if ln.strip())
    if n != pinned[tag]["entries"]:
        raise native_skills.PackError(f"{tag}: {n} entries, pinned {pinned[tag]['entries']}")
    return sha, n


def pins():
    """The pinned table; tests point SKILL_PACK_PINS at a JSON file of their own (the workflow never sets it, and the
    agent checks the manifest again against its own built-in table, which this cannot change)."""
    f = os.environ.get("SKILL_PACK_PINS", "")
    return json.load(open(f)) if f else native_skills.PINNED


def main(argv):
    if len(argv) != 3 or argv[0] not in ("verify", "verify-reference"):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        if argv[0] == "verify-reference":
            f = os.environ.get("REFERENCE_PINS", "")  # tests only, as SKILL_PACK_PINS; the workflow never sets it
            sha, n = verify_reference(argv[1], argv[2], json.load(open(f)) if f else None)
            print(f"skill pack {argv[2]}: reference layer, {n} entries, MANIFEST.sha256 {sha}: matches the pinned hash")
            return 0
        sha, n = verify(argv[1], argv[2], pins())
    except (native_skills.PackError, OSError) as e:
        print(f"skill_pack.py: refused: {e}", file=sys.stderr)
        return 2
    print(f"skill pack {argv[2]}: {n} skills, MANIFEST.sha256 {sha}: matches the pinned hash")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
