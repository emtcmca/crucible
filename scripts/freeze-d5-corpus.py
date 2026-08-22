#!/usr/bin/env python3
"""freeze-d5-corpus.py - hash-lock the CORPUS. `corpus_hash`. D5.

The FIFTH hash-lock's FIRST half. `scripts/freeze-d5-derived-schema.py` freezes
the other half and says so from its side: *"The corpus itself is covered by
`corpus_hash`, the fifth lock's other half."* Until this script's record lands,
that sentence points at nothing - `corpus_hash` had no implementation anywhere in
the repository, only a schema field and a replay assertion.

`docs/execution-spec.md` Day 5 item 3: *"Corpus hashed and committed, referencing
the frozen target hash and the gate rule hash."* `docs/contest/BUILD-LIST.md`
Tier 4: the D5 corpus freeze **must land before the first patch is written** -
because a corpus that can move after the first patch is a corpus the patch can be
fitted to, and no gate in the build would notice.

WHAT IS FROZEN, AND WHAT MERELY REFERENCED
--------------------------------------------
`corpus/freeze.py` owns the coverage decision and its citations; read that
docstring, not this one, for what is inside the payload and why. In one line: the
50 training attacks, the 26 benign fixtures, `corpus/pairs.json`,
`corpus/F4-MANIFEST.json`, and the sealed family BY REFERENCE through two
already-published content-addressed digests.

The gate rule hash (D2) and the target agent hash (D3) are **referenced in the
record and are NOT inside the hashed payload.** D5 item 3 says "referencing", and
a `corpus_hash` that moved when the target was re-frozen would stop being a
function of the corpus. The reference is made load-bearing by refusal instead:
this script REFUSES if either prior freeze record is missing, and reprints both
values so the record names the exact locks the corpus was frozen against.

WHAT IT REFUSES TO DO, AND WHY EACH REFUSAL IS THE POINT
---------------------------------------------------------
- **Refuses if any covered file has uncommitted changes.** Freezing a corpus that
  exists only on one laptop is not a freeze; the public commit timestamp is the
  evidence. Same sentence as its three siblings, deliberately.
- **Refuses if the covered set on disk differs from the covered set at HEAD** -
  stated as a hash comparison rather than as a git status string, and covering
  ADDED and REMOVED files as well as edited ones. A corpus that gained a 51st
  training instance between the working tree and HEAD is a different corpus.
- **Refuses if a freeze record already exists naming a different hash.** "Frozen
  at D5" is enforced here rather than remembered.
- **Refuses if the corpus fails its own checks** - `python -m corpus`, via
  `corpus.check.main`. A lock over a corpus that fails its own sizing, lint,
  SEP-BY parity or blindness checks locks a defect, and every one of those checks
  exists because passing it is load-bearing for a published number.
- **Refuses if the sealed family is absent or its seal is broken.** The hash does
  not need the sealed bytes - that is the whole design - but the CLAIM does. This
  script verifies the seal by shelling out to `scripts/seal-commitment.py
  --verify`, which is the only implementation of that digest in the repo and the
  only code allowed to read those files. **The freeze can therefore only be fired
  from a machine holding the sealed set**, exactly like its D5 sibling.
- **Refuses if the D2 gate-rule freeze or the D3 target freeze is missing.**
  Item 3 says the corpus freeze REFERENCES them. A reference to a lock that was
  never taken is decoration.

`corpus/sealed/` IS GITIGNORED, SO THE COMMIT REFUSAL STRUCTURALLY CANNOT COVER IT
-----------------------------------------------------------------------------------
It can never be committed - the ignore line is not the control, the IAM boundary
is - so "no uncommitted changes" is a statement about the OTHER 78 files and about
nothing under `corpus/sealed/`. The record says that in
`sealed_not_covered_by_commit_check` rather than leaving a reader to assume it was
checked. What IS asserted for the sealed set is different and is named there too:
the published fingerprint still matches the bytes on disk.

Run:  python scripts/freeze-d5-corpus.py            # dry run, prints only
      python scripts/freeze-d5-corpus.py --check    # recompute from HEAD, compare
                                                    # to the record. Read-only,
                                                    # runs without the sealed set.
      python scripts/freeze-d5-corpus.py --write    # THE OWNER, on D5
"""

import argparse
import io
import json
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")

from corpus.errors import CorpusError                              # noqa: E402
from corpus.freeze import (                                        # noqa: E402
    DATA_FILES, DiskSource, GitSource, INSTANCE_DIRS, SEAL_COMMITMENT,
    census, corpus_hash_full, covered_paths, seal_fingerprint)

RECORD = REPO / "docs" / "proof" / "d5-corpus-freeze.json"
D2_RECORD = REPO / "docs" / "proof" / "d2-gate-rule-freeze.json"
D3_RECORD = REPO / "target" / "refund_agent" / "FROZEN.json"
SEAL_SCRIPT = REPO / "scripts" / "seal-commitment.py"

# The nine known-bad calibration fixtures. NOT in the hashed payload - see
# `corpus/freeze.py` for the argument, three of them provably cannot enter one -
# but their digests go into the RECORD, because "not in the hash" and "not
# written down anywhere" are different amounts of protection and only one of them
# is a decision anybody made.
KNOWN_BAD_DIR = REPO / "tests" / "golden_traces" / "known_bad"


def git(*args, binary=False):
    p = subprocess.run(["git", "-C", str(REPO)] + list(args),
                       capture_output=True,
                       text=not binary,
                       encoding=None if binary else "utf-8",
                       errors=None if binary else "replace")
    if binary:
        return p.returncode, p.stdout, p.stderr
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def lf(raw):
    """The textual normalization, `canonicalization.md` section 4. Used ONLY for
    the known-bad digests in the record, which are not in the hashed payload -
    three of the nine carry a rate or an explicit null and cannot be JCS-
    canonicalized at all."""
    return raw.replace(b"\r\n", b"\n")


def known_bad_digests():
    """sha256 over the LF-normalized bytes of each known-bad, for the record."""
    import hashlib
    if not KNOWN_BAD_DIR.is_dir():
        return {}
    return {p.stem: hashlib.sha256(lf(p.read_bytes())).hexdigest()
            for p in sorted(KNOWN_BAD_DIR.glob("*.json"))}


def verify_seal(expected_fingerprint, problems):
    """Verify the sealed family through the ONE implementation of that digest.

    Shelling out rather than importing is deliberate twice over. `seal-commitment.py`
    is hyphenated and not importable without gymnastics, and more importantly the
    sealed bytes never enter this process at all - this script learns a digest and
    a count, and never sees an instance. A second fingerprint implementation here
    would be a second source of truth for the number that binds the held-out
    family into `corpus_hash`.

    AN EXIT CODE IS NOT THE EVIDENCE. `--verify` returning 0 says the sealed set
    matches SOME recorded value; what this freeze needs is that it matches the
    value that is INSIDE `corpus_hash`. So the fingerprint is parsed back out of
    the subprocess's own output and compared against the one the payload carries.
    Without that comparison a green seal check and a hash built from a stale
    commitment file would agree with each other and with nothing else.
    """
    status = {"result": "NOT-RUN", "instances": None, "fingerprint": None,
              "matches_hashed_fingerprint": None}
    if not SEAL_SCRIPT.is_file():
        problems.append("scripts/seal-commitment.py is missing; the seal cannot "
                        "be verified and NOT-RUN is not a pass.")
        return status

    p = subprocess.run([sys.executable, str(SEAL_SCRIPT), "--verify"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(REPO))
    out = (p.stdout or "") + (p.stderr or "")

    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0] == "fingerprint" and len(parts[1]) == 64:
            status["fingerprint"] = parts[1]
        elif len(parts) == 2 and parts[0] == "instances" and parts[1].isdigit():
            status["instances"] = int(parts[1])

    if "no sealed instances found" in out:
        status["result"] = "NOT-RUN (no sealed set reachable from this machine)"
        problems.append(
            "no sealed instances are reachable from this machine. corpus/sealed/ "
            "is gitignored, so a worktree and a fresh clone both have none - and "
            "freezing the corpus without confirming the held-out family is "
            "intact would put the D5 claim ('the held-out attacks existed before "
            "the first patch was written') into a record that never checked it. "
            "Fire this freeze from the machine that holds the sealed set.")
        return status

    if p.returncode != 0 or "SEAL INTACT" not in out:
        status["result"] = "SEAL BROKEN"
        problems.append(
            "scripts/seal-commitment.py --verify did not report SEAL INTACT "
            "(exit %d). The sealed family's published fingerprint is INSIDE "
            "corpus_hash, so a broken seal is not a thing to freeze around:\n"
            "      %s" % (p.returncode, out.strip().replace("\n", "\n      ")))
        return status

    status["result"] = "SEAL INTACT"
    status["matches_hashed_fingerprint"] = (
        status["fingerprint"] == expected_fingerprint)
    if not status["matches_hashed_fingerprint"]:
        problems.append(
            "the seal verified INTACT against fingerprint %s, and the "
            "fingerprint inside corpus_hash is %s. The seal check and the hash "
            "are agreeing about two different sets. Whichever is stale, freezing "
            "now would publish a corpus_hash whose sealed half nobody verified."
            % ((status["fingerprint"] or "UNPARSEABLE")[:16],
               (expected_fingerprint or "ABSENT")[:16]))
    return status


def prior_locks(problems):
    """The D2 gate rule hash and the D3 target hashes, which item 3 says this
    freeze REFERENCES. Missing is a refusal, not a blank field."""
    out = {}
    if D2_RECORD.exists():
        out["gate_rule_hash"] = json.loads(
            D2_RECORD.read_text(encoding="utf-8")).get("gate_rule_hash")
    else:
        problems.append(
            "%s is absent. execution-spec D5 item 3 requires the corpus freeze to "
            "REFERENCE the gate rule hash, and a reference to a lock that was "
            "never taken is decoration."
            % D2_RECORD.relative_to(REPO).as_posix())
    if D3_RECORD.exists():
        frozen = json.loads(D3_RECORD.read_text(encoding="utf-8"))
        out["target_agent_hash"] = frozen.get("target_agent_hash")
        out["manifest_hash"] = frozen.get("manifest_hash")
    else:
        problems.append(
            "%s is absent. Item 3 requires the corpus freeze to REFERENCE the "
            "frozen target hash." % D3_RECORD.relative_to(REPO).as_posix())
    return out


def check_sealed_directory(problems):
    """Name the absent sealed set BEFORE `python -m corpus` fails on it.

    Without this, the only symptom is `E_SEALED_BELOW_FLOOR: 0 instances` buried
    in the corpus-check output, and a reader has to work out that the cause is a
    missing directory rather than a corpus that was cut.

    IT ALSO NAMES A DIVERGENCE, rather than smoothing it over. `corpus/load.py`
    resolves the sealed set at `REPO/corpus/sealed` and nowhere else, while
    `scripts/seal-commitment.py` resolves it as `$CRUCIBLE_SEALED_DIR`, then the
    in-repo path, then a build-machine default. So in a worktree the seal check
    can report INTACT against a set the corpus check cannot see at all - two
    answers to "where is the sealed family", which is one more than there should
    be. This is REPORTED here; it is another lane's file to fix.
    """
    if (REPO / "corpus" / "sealed").is_dir():
        return
    problems.append(
        "corpus/sealed/ is not present at %s. corpus.load resolves the sealed "
        "set there and only there, so `python -m corpus` will report "
        "E_SEALED_BELOW_FLOOR with 0 instances - that is this absence, not a "
        "corpus that was cut. NOTE that scripts/seal-commitment.py resolves the "
        "same directory differently ($CRUCIBLE_SEALED_DIR, then in-repo, then a "
        "build-machine default), so the seal check above may well have passed "
        "against a set this check cannot see. Fire the freeze where "
        "corpus/sealed/ is in the repository."
        % (REPO / "corpus" / "sealed"))


def run_corpus_checks(problems):
    """`python -m corpus`, in-process. Exit 0 is the only acceptable answer.

    Exit 2 - NOT-RUN, nothing could be run - is treated as a refusal here even
    though it is not a FAIL, because a corpus with nothing to check is not a
    corpus to freeze.
    """
    import contextlib
    from corpus.check import main as corpus_main
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = corpus_main([])
    except Exception as exc:                                  # pragma: no cover
        problems.append("python -m corpus raised %s: %s"
                        % (type(exc).__name__, exc))
        return 1, buf.getvalue()
    if rc != 0:
        problems.append(
            "`python -m corpus` exited %d. A lock over a corpus that fails its "
            "own sizing, lint, SEP-BY or blindness checks locks a defect, and "
            "every one of those checks is load-bearing for a published number.\n"
            "      %s" % (rc, buf.getvalue().strip().replace("\n", "\n      ")))
    return rc, buf.getvalue()


def check_git_state(disk_paths, problems):
    """Every covered file committed, and the covered SET identical to HEAD."""
    for rel in list(INSTANCE_DIRS) + list(DATA_FILES) + [SEAL_COMMITMENT]:
        _rc, out, _err = git("status", "--porcelain", "--", rel)
        if out:
            problems.append(
                "%s has uncommitted changes:\n      %s\n    Freezing a corpus "
                "that exists only on this machine is not a freeze - the public "
                "commit timestamp is the evidence."
                % (rel, out.replace("\n", "\n      ")))

    head_paths = covered_paths(GitSource(git))
    added = sorted(set(disk_paths) - set(head_paths))
    removed = sorted(set(head_paths) - set(disk_paths))
    if added or removed:
        problems.append(
            "the covered set on disk is not the covered set at HEAD. Only in the "
            "working tree: %s. Only at HEAD: %s. A corpus that gained or lost an "
            "instance between the two is a different corpus, and comparing "
            "per-file hashes alone would never see it."
            % (added or "none", removed or "none"))
    return head_paths


def emit(digest, counts, seal_status, locks, kb):
    print("CORPUS  D5 hash-lock, fifth lock first half")
    print("  corpus_hash          %s" % digest[:16])
    print("  full                 %s" % digest)
    print("  covered files        %d" % counts["covered_files_total"])
    print("    corpus/training      %d" % counts["training"])
    print("    fixtures/benign      %d" % counts["benign"])
    print("    corpus data files    %d  (%s)"
          % (counts["data_files"], ", ".join(DATA_FILES)))
    print("  sealed family        BY REFERENCE ONLY - content never read")
    print("    F4-MANIFEST.json     24 content-addressed instance_ids + set_digest")
    print("    seal commitment      %s" % SEAL_COMMITMENT)
    print("    seal verification    %s" % seal_status["result"])
    print("    verified instances   %s" % (seal_status["instances"]
                                           if seal_status["instances"] is not None
                                           else "-"))
    print("    verified fingerprint %s" % ((seal_status["fingerprint"] or "-")[:16]))
    print("    == the one hashed    %s" % {True: "yes", False: "NO",
                                           None: "-"}[seal_status[
                                               "matches_hashed_fingerprint"]])
    print("")
    print("  REFERENCED, not hashed into the payload (D5 item 3 says 'referencing'):")
    print("    gate_rule_hash       %s  (D2)" % locks.get("gate_rule_hash", "ABSENT"))
    print("    target_agent_hash    %s  (D3)" % locks.get("target_agent_hash", "ABSENT"))
    print("    manifest_hash        %s  (D3, Part A)" % locks.get("manifest_hash", "ABSENT"))
    print("")
    print("  NOT IN corpus_hash - the nine known-bad calibration fixtures, "
          "digested into")
    print("  the record instead. KB5 carries a rate and KB6/KB8 carry an "
          "explicit null,")
    print("  none of which may enter a hashed payload. %d digested." % len(kb))
    print("")


def do_check():
    """Recompute from HEAD and compare against the committed record.

    Reads the corpus out of HEAD rather than off disk, so a working-tree edit
    cannot make its own freeze look intact. This is the mode a judge runs, and it
    deliberately does NOT require the sealed set - the sealed family is inside
    the hash by reference, so the recompute needs nothing that is not in a public
    clone. That is the property the by-reference design bought.
    """
    try:
        digest = corpus_hash_full(GitSource(git))
    except CorpusError as e:
        print("CHECK FAILED - the corpus at HEAD does not hash: %s: %s"
              % (e.code, e.detail))
        return 1

    print("CORPUS  recomputed from HEAD, not from disk")
    print("  recomputed           %s" % digest)
    print("  short                %s" % digest[:16])

    if not RECORD.exists():
        print("\nNO FREEZE RECORD at %s." % RECORD.relative_to(REPO).as_posix())
        print("The corpus is NOT frozen. BUILD-LIST Tier 4: the D5 corpus freeze")
        print("must land BEFORE the first patch is written.")
        return 1

    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    want = rec.get("corpus_hash_full")
    print("  recorded             %s" % (want or "ABSENT"))
    print("")

    if want != digest:
        print("CHECK FAILED - the committed corpus no longer hashes to the "
              "frozen value.")
        print("  This is not a stale record to refresh. It means THE CORPUS "
              "MOVED after")
        print("  it was frozen, and every number taken under the old one and the "
              "new one")
        print("  was measured against a different suite.")
        return 1

    n = rec.get("covered_files_total")
    got = len(covered_paths(GitSource(git)))
    if n is not None and n != got:
        print("CHECK FAILED - the record names %s covered files and HEAD "
              "carries %d." % (n, got))
        return 1

    print("SEAL INTACT. %d covered files, %s." % (got, digest[:16]))
    print("NOTE: this mode verifies the HASH. It does not re-verify the sealed "
          "family")
    print("      on disk - that needs the sealed set, which a clone does not "
          "have.")
    print("      Run: python scripts/seal-commitment.py --verify")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true",
                    help="WRITE the freeze record. The project owner runs this, "
                         "on D5. A lane does not.")
    ap.add_argument("--check", action="store_true",
                    help="recompute from HEAD and compare against the committed "
                         "record. Read-only.")
    a = ap.parse_args(argv)

    if a.check and a.write:
        print("--check and --write are different jobs. Pick one.")
        return 2
    if a.check:
        return do_check()

    problems = []
    source = DiskSource(REPO)

    try:
        digest = corpus_hash_full(source)
        counts = census(source)
        disk_paths = covered_paths(source)
    except CorpusError as e:
        print("THE CORPUS DOES NOT HASH: %s: %s" % (e.code, e.detail))
        print("FREEZE REFUSED. A corpus that cannot be hashed cannot be frozen, "
              "and this is the day that fact is cheapest to learn.")
        return 1

    payload_fingerprint = seal_fingerprint(source)

    check_sealed_directory(problems)
    run_corpus_checks(problems)
    check_git_state(disk_paths, problems)
    seal_status = verify_seal(payload_fingerprint, problems)
    locks = prior_locks(problems)
    kb = known_bad_digests()

    if RECORD.exists():
        prior = json.loads(RECORD.read_text(encoding="utf-8"))
        if prior.get("corpus_hash_full") != digest:
            problems.append(
                "a D5 freeze record already exists naming %s and the corpus now "
                "hashes to %s. 'Frozen at D5' is enforced here rather than "
                "remembered: if the corpus genuinely had to change, that is a "
                "coordinator ruling with a written statement of what it "
                "invalidates - every number already measured against the old "
                "suite - not a re-run of this script."
                % (prior.get("corpus_hash_full", "?")[:16], digest[:16]))
        else:
            print("D5 already frozen at %s and the bytes still match.\n"
                  % digest[:16])

    _rc, commit, _e = git("rev-parse", "HEAD")
    _rc, when, _e = git("log", "-1", "--format=%cI", "--", "corpus/training")

    emit(digest, counts, seal_status, locks, kb)
    print("  HEAD                 %s" % commit)
    print("  training committed   %s" % (when or "UNKNOWN"))
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
        "_what": "D5 hash-lock of THE CORPUS. The fifth lock's first half; "
                 "derived_schema_hash is the second.",
        "_why": "The claim is that the suite every number is measured against "
                "existed, complete and unchangeable, BEFORE the first patch was "
                "written. That claim is about a moment, so the record names the "
                "commit and its timestamp rather than only the hash.",
        "_hash_covers": "sha256 over the JCS canonical bytes of each covered "
                        "file, assembled with its repo-relative path into one "
                        "payload and hashed again. Covered: corpus/training/*.json, "
                        "fixtures/benign/*.json, corpus/pairs.json, "
                        "corpus/F4-MANIFEST.json, and the `fingerprint` field of "
                        "docs/proof/sealed-family-commitment.json. The coverage "
                        "decision and its citations live in corpus/freeze.py.",
        "_hash_does_not_cover": "The nine known-bad calibration fixtures (their "
                                "digests are below, outside the hash - KB5 "
                                "carries a rate and KB6/KB8 an explicit null, "
                                "and canonicalization restrictions 4 and 5 "
                                "forbid both in a hashed payload; editing a "
                                "calibration fixture so a hash will accept it is "
                                "weakening a gate to fit a check). Also out: "
                                "capability manifest Part A (manifest_hash, D3), "
                                "derived_schema.json (derived_schema_hash, D5), "
                                "and every .py and .md under corpus/.",
        "corpus_hash": digest[:16],
        "corpus_hash_full": digest,
        "covered_files_total": counts["covered_files_total"],
        "counts": counts,
        "canonicalization": "RFC 8785 (JCS) plus the seven CRUCIBLE restrictions, "
                            "canonicalization.md. NOT the textual contract-file "
                            "normalization.",
        "references": {
            "_why": "execution-spec D5 item 3: the corpus is hashed and "
                    "committed 'referencing the frozen target hash and the gate "
                    "rule hash'. These are REFERENCED, not hashed into the "
                    "payload - a corpus_hash that moved when the target was "
                    "re-frozen would stop being a function of the corpus. The "
                    "reference is load-bearing because this script REFUSES when "
                    "either prior record is absent.",
            "gate_rule_hash": locks.get("gate_rule_hash"),
            "target_agent_hash": locks.get("target_agent_hash"),
            "manifest_hash": locks.get("manifest_hash"),
        },
        "sealed_family": {
            "_how": "BY REFERENCE ONLY. corpus/sealed/ is gitignored and its "
                    "content is never read here - a read across that boundary is "
                    "RUN INVALID. Two already-published content-addressed "
                    "digests carry it into the hash instead: the 24 instance_ids "
                    "and set_digest inside corpus/F4-MANIFEST.json, and the "
                    "fingerprint in docs/proof/sealed-family-commitment.json.",
            "_consequence": "corpus_hash is IDENTICAL on a machine holding the "
                            "sealed set and on a fresh public clone that does "
                            "not. Adding the sealed files changes nothing, "
                            "because there is nothing to add. That is what makes "
                            "this hash reproducible by a judge.",
            "hashed_fingerprint": payload_fingerprint,
            "seal_verification": seal_status,
        },
        "sealed_not_covered_by_commit_check":
            "corpus/sealed/ is gitignored and can never be committed, so the "
            "uncommitted-changes refusal structurally CANNOT cover it. What IS "
            "asserted is different and is stated rather than assumed: "
            "scripts/seal-commitment.py --verify reported SEAL INTACT on this "
            "machine, meaning the sealed bytes still match the published "
            "fingerprint that is inside corpus_hash.",
        "known_bad_calibration": {
            "_not_in_corpus_hash": True,
            "_why_recorded_anyway": "known_bad_count: 9 is a frozen C7 parameter "
                                    "and G1(a) asserts each fixture's expected "
                                    "verdict every round, but neither covers a "
                                    "known-bad's CONTENT. A KB whose body moved "
                                    "without flipping its verdict would touch no "
                                    "hash-lock. These digests close that gap with "
                                    "evidence rather than with a hash the payload "
                                    "cannot legally carry.",
            "_algorithm": "sha256 over LF-normalized file bytes "
                          "(canonicalization.md section 4, the textual form).",
            "digests": kb,
        },
        "head_commit": commit,
        "training_committed_at": when,
    }
    RECORD.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8",
                      newline="\n")

    # Postcondition. Read it back off disk rather than trusting the write.
    back = json.loads(RECORD.read_text(encoding="utf-8"))
    if back["corpus_hash_full"] != digest:
        print("WROTE THE RECORD AND IT READ BACK WRONG.")
        return 1
    print("FROZEN. %s (%d bytes) -> %s"
          % (RECORD.relative_to(REPO).as_posix(),
             len(RECORD.read_bytes()), back["corpus_hash"]))
    print("Commit this file. The freeze is the commit, not the write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
