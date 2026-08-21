#!/usr/bin/env python3
"""freeze-d2-gate-rule.py - hash-lock C8, the promotion rule. D2.

`CONVENTIONS.md`: `gate_rule.v1.yaml` is **hash-locked D2 and not editable
after**. It is the first of the five hash-locks and the easiest one to get
wrong, because the file already exists and already has a hash in
`contracts/MANIFEST.json` -- so it is tempting to call it locked and move on.

IT IS NOT THE SAME THING. The manifest records what the file hashed to when the
contracts were frozen. The D2 lock is a separate, dated assertion that THIS is
the promotion rule the run will be judged by, made BEFORE anything is promoted.
What the Devpost post claims is *"the promotion rule existed before anything was
promoted"*, and that claim is about a moment, not about a file.

WHAT THIS REFUSES TO DO, AND WHY EACH REFUSAL IS THE POINT
-----------------------------------------------------------
- **Refuses if the working tree has uncommitted changes to the gate rule.**
  Freezing a file that only exists on one laptop is not a freeze. The public
  commit timestamp IS the evidence; without it the claim rests on our word.
- **Refuses if the file on disk differs from the file at HEAD.** Same reason,
  stated as a byte comparison rather than as a git status string.
- **Refuses if the hash disagrees with `contracts/MANIFEST.json`.** A gate rule
  that changed since the contract freeze is a different gate rule, and the
  disagreement must be loud rather than absorbed.
- **Refuses to overwrite an existing freeze record with a different hash.**
  "Not editable after" is enforced here rather than remembered.

Run:  python scripts/freeze-d2-gate-rule.py            # dry run, prints only
      python scripts/freeze-d2-gate-rule.py --write    # writes the record
"""

import argparse
import hashlib
import io
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = pathlib.Path(__file__).resolve().parent.parent
GATE_RULE = REPO / "contracts" / "gate_rule.v1.yaml"
MANIFEST = REPO / "contracts" / "MANIFEST.json"
RECORD = REPO / "docs" / "proof" / "d2-gate-rule-freeze.json"


def normalize(raw: bytes) -> bytes:
    """The contract-file normalization, `canonicalization.md` §4. Textual and
    minimal, and deliberately NOT JCS -- three of the contracts are not JSON at
    all, so a JSON canonicalizer cannot be the common form."""
    if raw[:3] == b"\xef\xbb\xbf":
        raise SystemExit("the gate rule carries a UTF-8 BOM. Refused, not stripped.")
    text = raw.decode("utf-8").replace("\r\n", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return ("\n".join(lines) + "\n").encode("utf-8")


def git(*args):
    p = subprocess.run(["git", "-C", str(REPO)] + list(args),
                       capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    problems = []

    raw = GATE_RULE.read_bytes()
    digest = hashlib.sha256(normalize(raw)).hexdigest()
    short = digest[:16]

    # -- is it committed? --------------------------------------------------
    rc, out, _ = git("status", "--porcelain", "--", "contracts/gate_rule.v1.yaml")
    if out:
        problems.append(
            "contracts/gate_rule.v1.yaml has uncommitted changes (%r). Freezing a "
            "file that exists only on this machine is not a freeze -- the public "
            "commit timestamp is the evidence." % out)

    rc, head_blob, err = git("show", "HEAD:contracts/gate_rule.v1.yaml")
    if rc != 0:
        problems.append("cannot read the gate rule at HEAD: %s" % err)
    elif hashlib.sha256(normalize(head_blob.encode("utf-8"))).hexdigest() != digest:
        problems.append(
            "the gate rule on disk does not match the gate rule at HEAD. The "
            "freeze must name the committed bytes, not the working copy.")

    # -- does it agree with the contract manifest? -------------------------
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    recorded = None
    for cid, entry in man.get("contracts", {}).items():
        files = entry.get("files", entry) if isinstance(entry, dict) else entry
        if isinstance(files, dict):
            for fname, h in files.items():
                if fname == "gate_rule.v1.yaml":
                    recorded = h if isinstance(h, str) else h.get("sha256")
    if recorded and not digest.startswith(recorded) and recorded != short:
        problems.append(
            "MANIFEST.json records %s for the gate rule; it now hashes to %s. A "
            "gate rule that changed since the contract freeze is a DIFFERENT "
            "gate rule." % (recorded, short))

    # -- not editable after ------------------------------------------------
    if RECORD.exists():
        prior = json.loads(RECORD.read_text(encoding="utf-8"))
        if prior.get("gate_rule_hash_full") != digest:
            problems.append(
                "a D2 freeze record already exists naming %s and the gate rule "
                "now hashes to %s. 'Hash-locked D2, NOT EDITABLE AFTER' is "
                "enforced here rather than remembered: if the rule genuinely "
                "had to change, that is a coordinator ruling with a written "
                "statement of what it invalidates, not a re-run of this script."
                % (prior.get("gate_rule_hash_full", "?")[:16], short))
        else:
            print("D2 already frozen at %s and the bytes still match." % short)

    _, commit, _ = git("rev-parse", "HEAD")
    _, when, _ = git("log", "-1", "--format=%cI", "--", "contracts/gate_rule.v1.yaml")

    print("C8  contracts/gate_rule.v1.yaml")
    print("  gate_rule_hash       %s" % short)
    print("  full                 %s" % digest)
    print("  bytes (normalized)   %d" % len(normalize(raw)))
    print("  committed at         %s" % (when or "UNKNOWN"))
    print("  HEAD                 %s" % commit)
    print("")

    if problems:
        print("FREEZE REFUSED - %d problem(s):" % len(problems))
        for p in problems:
            print("  * %s" % p)
        return 1

    if not a.write:
        print("DRY RUN. Nothing written. Re-run with --write to record the freeze.")
        print("This script's exit code is not the freeze; docs/proof/ is.")
        return 0

    RECORD.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "_what": "D2 hash-lock of C8, the promotion rule. CONVENTIONS: hash-locked "
                 "D2, not editable after.",
        "_why": "The claim is that the promotion rule existed BEFORE anything was "
                "promoted. That claim is about a moment, so the record names the "
                "commit and its timestamp rather than only the hash.",
        "contract": "C8",
        "file": "contracts/gate_rule.v1.yaml",
        "gate_rule_hash": short,
        "gate_rule_hash_full": digest,
        "normalization": "LF; trailing whitespace stripped per line; exactly one "
                         "trailing newline; UTF-8 no BOM. NOT JCS -- "
                         "canonicalization.md section 4.",
        "file_committed_at": when,
        "head_commit": commit,
    }
    RECORD.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8",
                      newline="\n")

    # Postcondition. Read it back off disk rather than trusting the write.
    back = json.loads(RECORD.read_text(encoding="utf-8"))
    if back["gate_rule_hash_full"] != digest:
        print("WROTE THE RECORD AND IT READ BACK WRONG.")
        return 1
    print("FROZEN. %s (%d bytes) -> %s"
          % (RECORD.relative_to(REPO).as_posix(),
             len(RECORD.read_bytes()), back["gate_rule_hash"]))
    print("Commit this file. The freeze is the commit, not the write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
