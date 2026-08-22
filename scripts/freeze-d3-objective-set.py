#!/usr/bin/env python3
"""freeze-d3-objective-set.py - hash-lock C10's instance, THE DEFINITION OF BREACH. D3.

`execution-spec.md` Day 3 item 4b is a HARD STOP: *"the Objective Set is
authored, canonicalized, hashed, and written into the run manifest today."* It
is the fourth of the five hash-locks and it is the one with the least margin,
because it is the only lock whose subject is a SENTENCE rather than a program.
G1(b) asserts `sha256(canonical(Objective_Set)) == manifest.objective_set_hash`
and that the same value is stamped on every episode of the round. Edit one
clause on D7 while debugging and the v0 and vFinal arms measure under two
different definitions of breach, with **no other guard catching it.**

WHAT THIS DOES NOT DO, AND THE OMISSION IS THE POINT
----------------------------------------------------
IT DOES NOT CONTAIN A HASHER. `crucible/canon/` already canonicalizes (RFC 8785
plus the seven CRUCIBLE restrictions) and `crucible.tripwire.objective_set`
already computes `ObjectiveSet.hash` - and THAT is the value the
OBJECTIVE_EVALUATOR stamps on every episode. A freeze script with its own
canonicalizer would produce a second value for one artifact, and the one this
script printed would be the one nobody ever compares against. So the artifact is
loaded through the SAME loader the round uses, and the freeze records what that
loader said.

WHAT IT REFUSES TO DO, AND WHY EACH REFUSAL IS THE POINT
---------------------------------------------------------
- **Refuses if the artifact does not validate against C10.** The definition of
  breach failing to load on a hard-stop day is ruling 31's whole scenario, and
  it surfaces as a harness that will not boot rather than as a message anyone
  can read. Validate here, while there is a person watching.
- **Refuses if the working tree has uncommitted changes to the artifact.**
  Freezing bytes that exist only on one laptop is not a freeze. The public
  commit timestamp IS the evidence.
- **Refuses if the file on disk differs from the file at HEAD**, stated as a
  hash comparison rather than as a git status string.
- **Refuses to overwrite an existing freeze record naming a different hash.**
  "Frozen at D3" is enforced here rather than remembered.
- **Refuses an Objective Set with no clauses**, by construction - the loader
  does, because an empty set returns CLEAN for every episode and is
  INDISTINGUISHABLE FROM A PERFECTLY HARDENED TARGET.

THE ONE OPEN QUESTION IT REFUSES TO ANSWER SILENTLY
-----------------------------------------------------
`contracts/objective_set.schema.json` says of `_status` and `_note` that they
are *"NOT excluded from the hash ... deliberate ... editing it changes what a
human reading this file believes breach means, so it should change the identity
of the artifact."* `crucible/tripwire/objective_set.py::_strip_annotations` does
the opposite: it drops every `_`-prefixed key BEFORE hashing, so that correcting
a typo in a comment cannot re-open a hash-locked artifact mid-build. Both
arguments are good and they cannot both be the lock.

THIS SCRIPT PRINTS BOTH VALUES AND NAMES THE DIVERGENCE. It records the
ANNOTATION-STRIPPED value, because that is the one the loader computes and
therefore the only one G1(b) can ever see stamped on an episode - a record
naming the other value would make every episode of every round report a
mismatch. That is an operational fact, NOT a ruling on which document is right,
and the coordinator still owes the ruling.

Run:  python scripts/freeze-d3-objective-set.py            # dry run, prints only
      python scripts/freeze-d3-objective-set.py --check    # recompute from HEAD,
                                                           # compare to the record
      python scripts/freeze-d3-objective-set.py --write    # record the freeze
"""

import argparse
import io
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from crucible.canon import hash_full                                  # noqa: E402
from crucible.tripwire.objective_set import (                         # noqa: E402
    ObjectiveSet, ObjectiveSetError, _strip_annotations)

REPO = pathlib.Path(__file__).resolve().parent.parent
REL = "contracts/objective_set.v1.json"
ARTIFACT = REPO / "contracts" / "objective_set.v1.json"
SCHEMA = REPO / "contracts" / "objective_set.schema.json"
RECORD = REPO / "docs" / "proof" / "d3-objective-set-freeze.json"


def git(*args):
    p = subprocess.run(["git", "-C", str(REPO)] + list(args),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def validate_against_c10(doc):
    """C10 conformance. Returns a list of problem strings, never raises."""
    try:
        from jsonschema.validators import Draft202012Validator as D
    except Exception as exc:                        # pragma: no cover
        return ["jsonschema is unavailable, so C10 conformance was NOT checked "
                "(%s). An unevaluable check is a check that cannot fail." % exc]
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errs = sorted(D(schema).iter_errors(doc), key=lambda e: list(e.path))
    return ["C10: %s at %s" % (e.message, "/".join(str(p) for p in e.path) or "$")
            for e in errs]


def measure(doc):
    """Both readings of the hash, plus the loader's own view of the artifact.

    `stripped` is what `ObjectiveSet.hash` computes and what the round stamps.
    `unstripped` is what C10's description says the hash should cover. They
    differ, the divergence is real, and printing one of them alone would hide it.
    """
    objective_set = ObjectiveSet(doc)                # raises on an empty/bad set
    return {
        "objective_set": objective_set,
        "stripped_full": hash_full(_strip_annotations(doc)),
        "unstripped_full": hash_full(doc),
    }


def read_head_blob():
    rc, out, err = git("show", "HEAD:%s" % REL)
    if rc != 0:
        return None, "cannot read %s at HEAD: %s" % (REL, err or "no such path")
    try:
        return json.loads(out), None
    except ValueError as exc:
        return None, "%s at HEAD is not parseable JSON: %s" % (REL, exc)


def do_check():
    """RECOMPUTE FROM A CLEAN CHECKOUT AND COMPARE AGAINST THE COMMITTED RECORD.

    Reads the artifact out of HEAD rather than off disk, so a working-tree edit
    cannot make its own freeze look intact. This is the mode a judge runs.
    """
    if not RECORD.exists():
        print("NO FREEZE RECORD at %s." % RECORD.relative_to(REPO).as_posix())
        print("The Objective Set is NOT frozen. execution-spec Day 3 item 4b is a HARD STOP.")
        return 1

    doc, problem = read_head_blob()
    if problem:
        print("CHECK FAILED - %s" % problem)
        return 1

    try:
        m = measure(doc)
    except ObjectiveSetError as exc:
        print("CHECK FAILED - the committed artifact does not load: %s" % exc)
        return 1

    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    want = rec.get("objective_set_hash_full")
    got = m["stripped_full"]

    print("C10 instance  %s  (recomputed from HEAD, not from disk)" % REL)
    print("  recorded             %s" % (want or "ABSENT"))
    print("  recomputed           %s" % got)
    print("  short                %s" % got[:16])
    print("  clauses              %d" % len(m["objective_set"].clauses))
    print("")

    if want != got:
        print("CHECK FAILED - the committed artifact no longer hashes to the frozen value.")
        print("  This is not a stale record to refresh. It means THE DEFINITION OF BREACH")
        print("  MOVED after it was frozen, and every number taken under the old one and")
        print("  the new one measures a different thing. G1(b) marks such a round INVALID.")
        return 1

    n = rec.get("clause_count")
    if n is not None and n != len(m["objective_set"].clauses):
        print("CHECK FAILED - the record names %s clauses and the artifact carries %d."
              % (n, len(m["objective_set"].clauses)))
        return 1

    print("SEAL INTACT. %s clauses, %s." % (len(m["objective_set"].clauses), got[:16]))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="record the freeze (the OWNER's tap, not a lane's)")
    ap.add_argument("--check", action="store_true",
                    help="recompute from HEAD and compare against the committed record")
    a = ap.parse_args()

    if a.check and a.write:
        print("--check and --write are different jobs. Pick one.")
        return 2
    if a.check:
        return do_check()

    if not ARTIFACT.exists():
        print("%s does not exist. Nothing to freeze." % REL)
        return 1

    doc = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    problems = list(validate_against_c10(doc))

    try:
        m = measure(doc)
    except ObjectiveSetError as exc:
        print("THE ARTIFACT DOES NOT LOAD: %s" % exc)
        print("FREEZE REFUSED. A definition of breach that cannot load is not one.")
        return 1

    objective_set = m["objective_set"]
    digest = m["stripped_full"]
    short = digest[:16]

    # -- is it committed? --------------------------------------------------
    _rc, out, _err = git("status", "--porcelain", "--", REL)
    if out:
        problems.append(
            "%s has uncommitted changes (%r). Freezing a file that exists only on "
            "this machine is not a freeze - the public commit timestamp is the "
            "evidence." % (REL, out))

    head_doc, problem = read_head_blob()
    if problem:
        problems.append(problem)
    else:
        try:
            if hash_full(_strip_annotations(head_doc)) != digest:
                problems.append(
                    "the artifact on disk does not match the artifact at HEAD. The "
                    "freeze must name the COMMITTED bytes, not the working copy.")
        except Exception as exc:                    # pragma: no cover
            problems.append("cannot hash the HEAD blob: %s" % exc)

    # -- frozen at D3, not editable after ----------------------------------
    if RECORD.exists():
        prior = json.loads(RECORD.read_text(encoding="utf-8"))
        if prior.get("objective_set_hash_full") != digest:
            problems.append(
                "a D3 freeze record already exists naming %s and the Objective Set "
                "now hashes to %s. THE DEFINITION OF BREACH IS FROZEN AT D3: if it "
                "genuinely had to change, that is a coordinator ruling with a "
                "written statement of what it invalidates, not a re-run of this "
                "script." % (prior.get("objective_set_hash_full", "?")[:16], short))
        else:
            print("D3 already frozen at %s and the bytes still match." % short)

    _rc, commit, _e = git("rev-parse", "HEAD")
    _rc, when, _e = git("log", "-1", "--format=%cI", "--", REL)

    print("C10 instance  %s" % REL)
    print("  objective_set_hash   %s" % short)
    print("  full                 %s" % digest)
    print("  clauses              %d" % len(objective_set.clauses))
    for cid in objective_set.clause_ids:
        print("    %s" % cid)
    print("  committed at         %s" % (when or "UNCOMMITTED"))
    print("  HEAD                 %s" % commit)
    print("")
    print("  ANNOTATION DIVERGENCE, RESOLVED BY RULING 44 (Eric, 2026-08-22):")
    print("    stripped (RECORDED, and what the round stamps)  %s" % digest[:16])
    print("    unstripped (what C10 said before ruling 44)     %s"
          % m["unstripped_full"][:16])
    print("    C10 said _note/_status are NOT excluded; objective_set.py strips "
          "them. Contracts")
    print("    outrank code, so C10 won on the page. It lost anyway: the stripped "
          "value is what")
    print("    real_tripwire stamps and G1(b) compares, so recording the "
          "unstripped one would name")
    print("    a number no episode can carry and score every round INVALID - a "
          "hash-lock that")
    print("    locks nothing. C10 corrected, SPINE_VERSION 12, C10 and MANIFEST "
          "re-hashed.")
    print("    RESIDUAL: prose outside the hash is editable after the freeze. "
          "Bounded - the")
    print("    evaluator walks only non-_ keys, so it can mislead a reader, not "
          "change a verdict.")
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
        "_what": "D3 hash-lock of the C10 instance - THE DEFINITION OF BREACH. "
                 "execution-spec Day 3 item 4b, a HARD STOP.",
        "_why": "objective_set_hash is one of the five hash-locks. G1(b) asserts it "
                "against the run manifest AND against every episode of the round. "
                "Without it, one clause edited mid-build makes the v0 and vFinal "
                "arms measure under two different definitions of breach, and every "
                "headline number is produced while all three claims are false.",
        "_hash_covers": "sha256 over the JCS canonical form of the artifact WITH "
                        "EVERY _-PREFIXED ANNOTATION REMOVED, which is exactly what "
                        "crucible.tripwire.objective_set.ObjectiveSet.hash computes "
                        "and therefore the only value G1(b) can ever see stamped on "
                        "an episode. contracts/objective_set.schema.json's "
                        "description argues the annotations SHOULD be covered; that "
                        "divergence is open and named here rather than absorbed.",
        "contract": "C10",
        "file": REL,
        "objective_set_hash": short,
        "objective_set_hash_full": digest,
        "objective_set_hash_unstripped_full": m["unstripped_full"],
        "objective_set_version": doc.get("objective_set_version"),
        "clause_count": len(objective_set.clauses),
        "clause_ids": list(objective_set.clause_ids),
        "canonicalization": "RFC 8785 (JCS) plus the seven CRUCIBLE restrictions, "
                            "canonicalization.md section 4. NOT the textual "
                            "contract-file normalization used by MANIFEST.json.",
        "file_committed_at": when,
        "head_commit": commit,
    }
    RECORD.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8",
                      newline="\n")

    # Postcondition. Read it back off disk rather than trusting the write.
    back = json.loads(RECORD.read_text(encoding="utf-8"))
    if back["objective_set_hash_full"] != digest:
        print("WROTE THE RECORD AND IT READ BACK WRONG.")
        return 1
    print("FROZEN. %s (%d bytes) -> %s"
          % (RECORD.relative_to(REPO).as_posix(),
             len(RECORD.read_bytes()), back["objective_set_hash"]))
    print("Commit this file. The freeze is the commit, not the write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
