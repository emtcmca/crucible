#!/usr/bin/env python3
"""seal-commitment.py - publish a COMMITMENT to the sealed family, not the family.

WHAT THIS IS FOR
----------------
The headline claim is that one attack family was sealed away BEFORE the first
patch was written. Today that ordering rests on our word plus a bucket a reader
cannot see into. A commitment turns it into something a stranger can check:

    publish the HASH now, in a public repo, with a public commit timestamp
    reveal the CONTENT after the run
    anyone can then recompute the hash and confirm nothing moved

That is the same shape as pre-registering a hypothesis, and it is the cheapest
credibility available to a project whose entire thesis is that the ORDER of
operations is what makes a number honest.

WHAT IT DELIBERATELY DOES NOT PUBLISH
-------------------------------------
**Not the content, and NOT THE FILENAMES.** The instance filenames describe the
pretext each attack uses -- each one a short phrase naming that attack's pretext. A
reader who has those names knows the shape of the sealed family, which is most of
what sealing it was protecting. The filenames go INTO the hash and never into the
file this writes.

Nor does it publish per-file hashes. Twenty-four individual digests plus a
guessable naming scheme is a dictionary attack against our own seal, and there is
no reason to hand one over: the claim needs ONE number.

WHAT A GREEN RESULT DOES NOT PROVE
----------------------------------
That the set was not swapped wholesale before the commitment was published. A
commitment binds us from THIS MOMENT FORWARD; it says nothing about what happened
before it. The controls for the earlier window are different ones -- the IAM
boundary the Armorer's service account cannot cross, and the public commit
history of everything else.

Run:  python scripts/seal-commitment.py                 # print only
      python scripts/seal-commitment.py --write         # write the commitment
      python scripts/seal-commitment.py --verify        # recompute and compare
"""

import argparse
import hashlib
import io
import json
import pathlib
import subprocess
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = pathlib.Path(__file__).resolve().parent.parent
SEALED = pathlib.Path("C:/dev/crucible-wt-SEAL/corpus/sealed")
RECORD = REPO / "docs" / "proof" / "sealed-family-commitment.json"

# THE LOCAL BASELINE, and it is a different thing from the commitment.
#
# The commitment is PUBLIC and is a claim: "this is what we sealed, before the
# run." Publishing it is a decision, and one that is hard to walk back.
#
# This is PRIVATE and is a tripwire: "has anything touched the sealed set since
# the last time I looked." It answers the question that actually gets asked at
# 1am with six worktrees live, and it needs no decision from anybody.
#
# evidence/ is gitignored, so this never reaches the public repo and cannot be
# mistaken for the claim.
BASELINE = REPO / "evidence" / "seal-baseline.json"

ALGORITHM = (
    "sha256 over, for each file sorted by name: the UTF-8 filename bytes, then "
    "the file bytes with CRLF normalized to LF. Names are INSIDE the hash and "
    "are never published."
)


def fingerprint(directory):
    files = sorted(directory.glob("*.json"))
    if not files:
        raise SystemExit("no sealed instances found at %s" % directory)
    h = hashlib.sha256()
    classes = {}
    for f in files:
        h.update(f.name.encode("utf-8"))
        h.update(f.read_bytes().replace(b"\r\n", b"\n"))
        for c in json.loads(f.read_text(encoding="utf-8")).get(
                "capability_classes", []):
            classes[c] = classes.get(c, 0) + 1
    return h.hexdigest(), len(files), classes


def git(*args):
    p = subprocess.run(["git", "-C", str(REPO)] + list(args),
                       capture_output=True, text=True)
    return p.stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--baseline", action="store_true",
                    help="record a PRIVATE tripwire baseline. Not a claim.")
    a = ap.parse_args()

    digest, count, classes = fingerprint(SEALED)

    print("SEALED FAMILY COMMITMENT\n")
    print("  instances     %d" % count)
    print("  classes       %s" % json.dumps(classes, sort_keys=True))
    print("  fingerprint   %s" % digest)
    print("  short         %s" % digest[:16])
    print("")

    floor_ok = count >= 18
    print("  %s floor: %d of 18 minimum (24 preferred)"
          % ("ok  " if floor_ok else "FAIL", count))
    if not floor_ok:
        print("        Below 18 the headline claim dies: transfer is unmeasurable")
        print("        when breached_at_v0 < 12, and at ~70%% baseline potency")
        print("        that needs >= 18 instances. Arithmetic, not preference.")

    only_sealed_classes = set(classes) <= {"CAP_MOVES_MONEY",
                                           "CAP_MUTATES_DURABLE_STATE"}
    print("  %s classes: C1/C3 only, the classes the shape was never trained on"
          % ("ok  " if only_sealed_classes else "FAIL"))

    if a.baseline:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(
            {"_what": "PRIVATE tripwire baseline for the sealed family. NOT the "
                      "public commitment and NOT a claim. It answers one "
                      "question: has anything touched the sealed set since I "
                      "last looked.",
             "fingerprint": digest, "instance_count": count,
             "capability_classes": classes, "algorithm": ALGORITHM},
            indent=2) + "\n", encoding="utf-8", newline="\n")
        print("\nBASELINE RECORDED -> %s" % BASELINE)
        print("evidence/ is gitignored, so this cannot become a public claim by")
        print("accident. Check any time with: --verify")
        return 0

    if a.verify:
        # Prefer the PUBLIC commitment when one exists; it is the stronger
        # statement. Fall back to the private baseline, which is what exists
        # before anybody has decided to publish anything.
        source = RECORD if RECORD.exists() else BASELINE
        if not source.exists():
            print("\nNOTHING TO VERIFY AGAINST. No commitment, no baseline.")
            print("Record one first:  python scripts/seal-commitment.py --baseline")
            return 1
        print("  source        %s (%s)"
              % (source.name,
                 "PUBLIC commitment" if source is RECORD else "private baseline"))
        prior = json.loads(source.read_text(encoding="utf-8"))
        same = prior.get("fingerprint") == digest
        print("\n  recorded      %s" % prior.get("fingerprint", "?")[:16])
        print("  recomputed    %s" % digest[:16])
        if same:
            print("\nSEAL INTACT. The set is byte-identical to the commitment.")
            return 0
        print("\nSEAL BROKEN. The sealed family has changed since it was")
        print("committed. Every transfer number computed against it is void,")
        print("and this is not a thing to repair by re-committing.")
        return 1

    if not (a.write and floor_ok and only_sealed_classes):
        if not a.write:
            print("\nPRINT ONLY. Re-run with --write to publish the commitment.")
        else:
            print("\nREFUSED: will not commit a set that fails its own floor.")
            return 1
        return 0

    RECORD.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "_what": "A COMMITMENT to the sealed held-out attack family. The hash, "
                 "not the family.",
        "_why": "The headline claim is that this family was sealed BEFORE the "
                "first patch was written. Publishing the hash now, with a public "
                "commit timestamp, lets a stranger confirm after the reveal that "
                "nothing moved. Same shape as pre-registering a hypothesis.",
        "_withheld": "Filenames and content, deliberately. The instance names "
                     "describe each attack's pretext, so publishing them would "
                     "give away most of what sealing the family protects. Per-file "
                     "hashes are withheld for the same reason: 24 digests plus a "
                     "guessable naming scheme is a dictionary attack against our "
                     "own seal. The claim needs one number.",
        "_limits": "This binds us from this moment forward. It says NOTHING about "
                   "what happened before it was published. The controls for that "
                   "window are different: the IAM boundary the Armorer's service "
                   "account cannot cross, and the public history of everything "
                   "else in this repository.",
        "family": "F4 - destination smuggling",
        "instance_count": count,
        "capability_classes": classes,
        "floor": {"minimum": 18, "preferred": 24, "met": floor_ok},
        "algorithm": ALGORITHM,
        "fingerprint": digest,
        "fingerprint_short": digest[:16],
        "committed_at_head": git("rev-parse", "HEAD"),
    }
    RECORD.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8",
                      newline="\n")

    back = json.loads(RECORD.read_text(encoding="utf-8"))
    if back["fingerprint"] != digest:
        print("\nWROTE THE COMMITMENT AND IT READ BACK WRONG.")
        return 1
    print("\nCOMMITTED %s (%d bytes) -> %s"
          % (RECORD.relative_to(REPO).as_posix(), len(RECORD.read_bytes()),
             back["fingerprint_short"]))
    print("Commit and PUSH it. The timestamp is the evidence, and a commitment")
    print("that never left this machine is not a commitment.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
