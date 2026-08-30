#!/usr/bin/env python
"""The pre-read seal proof, generated rather than written.

WHAT THIS IS FOR. The pre-registration requires a FRESH seal proof immediately
before the sealed read - not one taken days earlier and cited. A proof written
by hand ages the moment it is committed and nothing says when it stopped being
true. So this is a command, run minutes before the unseal, that emits a dated
artifact from things it actually checked.

WHAT IT CHECKS, and each one is a different question:

  1. the sealed set is byte-identical to the public commitment
     (`seal-commitment.py --verify`) - nothing has moved since the hash was
     published, which is the whole content of the commitment
  2. no public artifact leaks the sealed family (`seal-leak-check.py`) - the
     withholding of the filenames actually held, across every tracked file
     rather than only the one that was meant to withhold them
  3. the working tree is clean and the HEAD is recorded - a proof taken over
     uncommitted changes describes a state nobody else can reach

WHAT IT DELIBERATELY DOES NOT DO.

**It does not touch `gs://crucible-sealed-x7`.** Not the objects, not a list,
not a metadata read. The holdout counter measures Cloud Audit Log DATA ACCESS
entries against that bucket, and an unattested read by the operator identity is
exactly what marks the run INVALID. A proof that spent the thing it was proving
would be the most expensive kind of check there is.

**It prints no fingerprint value.** Ruling 46: a frozen hash has exactly one
owner, the artifact. This records that the recompute AGREED and cites the file;
copying the value here would create a second source for it.

**It prints no sealed content**, and neither does anything it calls.

    python scripts/pre-read-seal-proof.py            # check and print
    python scripts/pre-read-seal-proof.py --write    # and emit the artifact
"""

import argparse
import datetime
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "docs" / "proof"
COMMITMENT = "docs/proof/sealed-family-commitment.json"


def _utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(args, label):
    """One checked subprocess. Returns (ok, tail).

    The tail is kept short and is NEVER the full stdout: `seal-leak-check.py`
    holds the sealed signal list in memory while it runs, and a proof artifact
    that captured its whole output would be one refactor away from publishing
    the thing it exists to protect.
    """
    proc = subprocess.run([sys.executable] + args, cwd=str(ROOT),
                          capture_output=True, text=True, timeout=600)
    lines = [ln.rstrip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    return proc.returncode == 0, (lines[-1][:160] if lines else "(no output)")


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=str(ROOT),
                          capture_output=True, text=True).stdout.strip()


def gather():
    checks = []

    ok, tail = _run(["scripts/seal-commitment.py", "--verify"],
                    "commitment")
    checks.append({
        "check": "sealed set matches the published commitment",
        "how": "scripts/seal-commitment.py --verify recomputes the fingerprint "
               "over the sealed set and compares it with the one published in "
               + COMMITMENT,
        "value_lives_in": COMMITMENT,
        "result": "AGREED" if ok else "DISAGREED",
        "ok": ok,
        "last_line": tail,
    })

    ok, tail = _run(["scripts/seal-leak-check.py"], "leak")
    checks.append({
        "check": "no public artifact leaks the sealed family",
        "how": "scripts/seal-leak-check.py scans every tracked file for full "
               "instance slugs, pretext token pairs, smuggled instrument ids "
               "and per-instance hashes",
        "result": "NO LEAKS" if ok else "LEAK FOUND",
        "ok": ok,
        "last_line": tail,
    })

    dirty = git("status", "--porcelain")
    checks.append({
        "check": "the working tree is clean",
        "how": "git status --porcelain",
        "result": "CLEAN" if not dirty else "DIRTY",
        "ok": not dirty,
        # THE PATHS, NOT THE DIFF. A proof artifact carrying a diff of a dirty
        # tree could carry anything that was in it.
        "last_line": ("clean" if not dirty
                      else "%d path(s) modified" % len(dirty.splitlines())),
    })

    return checks


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true",
                    help="emit the dated artifact under docs/proof/")
    args = ap.parse_args(argv)

    checks = gather()
    stamp = _utc()
    head = git("rev-parse", "HEAD")

    doc = {
        "artifact": "PRE-READ SEAL PROOF. Generated, not written.",
        "_why": "The pre-registration requires a FRESH proof immediately before "
                "the sealed read. A hand-written one ages the moment it is "
                "committed and nothing records when it stopped being true.",
        "_what_this_does_not_do": [
            "It does not touch gs://crucible-sealed-x7 in any way - not the "
            "objects, not a list, not metadata. The holdout counter measures "
            "audit-log DATA ACCESS entries against that bucket and an "
            "unattested operator read marks the run INVALID.",
            "It prints no fingerprint value. Ruling 46: the hash has one owner, "
            "and it is " + COMMITMENT + ".",
            "It prints no sealed content.",
        ],
        "_what_it_does_not_prove": [
            "That nothing read the bucket. That is the holdout counter's job, "
            "measured across the run's own audit window, and it cannot be "
            "answered from the repository.",
            "That the set was sealed before the first patch existed. That rests "
            "on the PUBLIC COMMIT TIMESTAMP of the commitment, which a reader "
            "checks against the repository history rather than against this "
            "file.",
        ],
        "generated_at": stamp,
        "head": head,
        "checks": checks,
        "verdict": "PASS" if all(c["ok"] for c in checks) else "FAIL",
    }

    width = 74
    print("=" * width)
    print("PRE-READ SEAL PROOF   %s" % stamp)
    print("  HEAD %s" % head)
    print("=" * width)
    for c in checks:
        print("  %-4s %s" % ("ok" if c["ok"] else "FAIL", c["check"]))
        print("       -> %s  (%s)" % (c["result"], c["last_line"]))
    print("=" * width)
    print("  VERDICT  %s" % doc["verdict"])
    if doc["verdict"] != "PASS":
        print("  THE SEAL MAY NOT BE OPENED on a failing proof.")

    if args.write:
        out = OUTDIR / ("pre-read-seal-proof-%s.json"
                        % stamp.replace(":", "").replace("-", ""))
        out.write_text(json.dumps(doc, indent=2) + "\n",
                       encoding="utf-8", newline="")
        # ASSERT THE POSTCONDITION. A printed "written" over a missing file is
        # the shape this repository keeps catching.
        if not out.is_file() or out.stat().st_size < 400:
            print("REFUSED: the artifact was not written, or is too small to "
                  "hold the record.")
            return 2
        print("  artifact %s" % out.relative_to(ROOT))

    return 0 if doc["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
