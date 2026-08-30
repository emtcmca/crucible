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

**What it captures from the tools it calls, and the residual in that.** The
earlier claim here was "it prints no sealed content, and neither does anything
it calls." The second half is FALSE: `seal-leak-check.py` prints the offending
line beside every hit it finds, which is the only way a leak report is useful
to the person fixing it.

What is actually enforced is narrower, and it is enforced rather than hoped:
this script keeps **only the last line** of each tool's stdout, **truncated to
160 characters**, and the last line of both tools is a fixed summary by
construction. So no leak DETAIL line reaches the artifact.

The residual is that the tools' last line is a property of those files rather
than a check in this one. A future edit that let a hit be the final thing
printed would put it in the artifact. Stated here rather than closed, because a
narrowed channel described as closed is worse than an open one described
accurately -- the same rule the transfer reader applies to its own argument
surface.

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


def stray_dirty_paths(porcelain, expected):
    """Paths dirty in `porcelain` other than `expected`. Pure; testable.

    SPLIT OUT SO IT CAN BE PROVEN. Inline, its only execution would have been
    inside `--write`, which writes into a tracked directory - so the check
    guarding the proof's central claim would itself have been a check nobody
    had watched fire. That is the seventeen-instance defect in this
    repository, and putting a new one inside the fix for an old one is how it
    got to seventeen.

    Porcelain lines are `XY <path>`; a path containing a space or a quote is
    emitted quoted. Rename lines carry `orig -> new` and the NEW path is what
    is dirty, so only the right-hand side is kept.
    """
    out = []
    for line in (porcelain or "").splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = path.strip('"')
        if path != expected:
            out.append(path)
    return sorted(out)


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
            "It keeps only the LAST LINE of each tool it calls, "
            "truncated to 160 characters, and the last line of both is a "
            "fixed summary. seal-leak-check.py does print the offending "
            "line beside a hit, so this is a bound on what is captured "
            "rather than a claim that nothing is ever printed.",
            "It does NOT avoid opening the sealed files on local disk - it "
            "cannot, because hashing them is how it proves the set is intact. "
            "That is FINGERPRINTING: bytes in, a digest out, nothing surfaced. "
            "The pre-registration's unit at A3.1 and A3.2 is a granted "
            "storage.objects.get naming a real object in the bucket, and this "
            "command issues none.",
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
        "_the_ordering_OF_THIS_ARTIFACT": [
            "THIS FILE CANNOT BE SIMULTANEOUSLY NEW, COMMITTED, BOUND TO THE "
            "CURRENT HEAD, AND LEAVE A CLEAN TREE. An adversarial review "
            "pointed that out and it is correct: `head` below is read BEFORE "
            "this file exists, writing it makes the tree dirty, and committing "
            "it moves HEAD past the value recorded here.",
            "So the claim is deliberately SEQUENTIAL rather than "
            "simultaneous. It is: the tree was clean at the commit named in "
            "`head`; this artifact was then the ONLY path that changed; the "
            "commit carrying it therefore has `head` as its PARENT.",
            "A READER CHECKS IT WITHOUT TRUSTING THIS FILE. Find the commit "
            "that adds this artifact. `git log -1 --format=%P` on it must "
            "print the `head` value below, and `git show --stat` on it must "
            "list this file and nothing else. Both are properties of the "
            "repository, not assertions of this document.",
            "The single-path property is not left to the reader either: "
            "--write re-runs git status after writing and REFUSES if anything "
            "other than this artifact is dirty.",
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

        # THE SEQUENTIAL CLAIM, ENFORCED RATHER THAN ASSERTED.
        #
        # The document above says the tree was clean at `head` and that THIS
        # ARTIFACT was the only path that changed afterwards. The first half
        # was checked before the write. This is the second half, and without it
        # the sentence is a description of what the operator hoped happened.
        #
        # Anything else appearing here means the tree changed during the run -
        # an editor saving, a parallel session committing, a generated file
        # landing - and the commit that carries this proof would then also
        # carry that, which is exactly the ambiguity the proof exists to
        # remove.
        expect = out.relative_to(ROOT).as_posix()
        stray = stray_dirty_paths(git("status", "--porcelain"), expect)
        if stray:
            print("REFUSED: writing the artifact was not the only change to "
                  "the tree. Also dirty: %s" % ", ".join(stray[:8]))
            print("  The proof claims this file was the single path that "
                  "changed after %s. Commit or stash the rest and re-run; the "
                  "artifact just written is stale and should be deleted."
                  % head[:12])
            return 2

        print("  artifact %s" % out.relative_to(ROOT))
        print("  the only dirty path is that artifact; its commit's parent "
              "will be %s" % head[:12])

    return 0 if doc["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
