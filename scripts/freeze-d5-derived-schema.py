#!/usr/bin/env python3
"""freeze-d5-derived-schema.py - hash-lock C3 Part B, `derived_schema.json`. D5.

The FIFTH hash-lock's second half. Ruling 20 split the capability manifest into
two artifacts because ruling 19 asked for two things one artifact cannot do:

    PART A  capability_manifest.json   D3, with the target      manifest_hash
    PART B  derived_schema.json        D5, with the corpus      derived_schema_hash
                                       GATED ON THE LABEL-BLINDNESS CHECK PASSING

`crucible/harness/episode.py` REFUSES to seal an episode whose run manifest
carries no `derived_schema_hash`, so until this freeze lands, every episode is
unscoreable rather than clean. That is G1(c) in `measurement-spec.md:770-781`
(the episode writer's own message cites "G1(b)" - see THE CITATION DEFECT below).

WHAT THIS SCRIPT IS, AND IS NOT
--------------------------------
It is NOT a second implementation of anything. Every load-bearing operation is
called, not reimplemented:

  the field definitions        `corpus.part_b.EPISODE_FIELDS` / `DERIVED_FIELDS`
  the blindness check          `corpus.blindness.run_blindness_check`
  the gate on the freeze       `corpus.part_b.build_part_b`, which CANNOT
                               produce a document from a failing report
  the corpus sizing floor      `corpus.sizing.check_sizing`
  the hash                     `crucible.manifest.load_part_b`, which is the
                               only `derived_schema_hash` hasher in the repo

A freeze script that recomputed any of those would be a second source of truth
for the thing the fifth lock names, and the first divergence would be invisible
in exactly the direction that flatters the run.

WHAT IT REFUSES TO DO, AND WHY EACH REFUSAL IS THE POINT
---------------------------------------------------------
- **Refuses if the sealed set is absent.** `corpus/sealed/` is gitignored, so a
  worktree or a fresh clone has none. The blindness check would then run over 76
  instances of 100 and report PASS - a PASS that never looked at the 24 F4
  instances the headline transfer claim rests on. Ruling 19.3 says *the whole
  corpus*, and an unevaluable check is a check that cannot fail
  (`measurement-spec.md:813`, CONVENTIONS section 8 rule 2). **The freeze can
  therefore only be fired from a machine holding the sealed set.**
- **Refuses if any source input has uncommitted changes.** Freezing a definition
  that exists only on one laptop is not a freeze; the public commit timestamp is
  the evidence. `corpus/sealed/` is exempt BY NECESSITY - it can never be
  committed - and the record says so in `sealed_not_covered_by_commit_check`
  rather than leaving a reader to assume it was checked.
- **Refuses if a source input on disk differs from HEAD.** The same statement as
  a byte comparison rather than as a git status string.
- **Refuses if a freeze record already exists naming a different hash.** "After
  D5 both artifacts are immutable and identical in status" (ruling 20) is
  enforced here rather than remembered.
- **Refuses if the built document fails `contracts/derived_schema.schema.json`.**
  A lock over a document that violates its own contract locks a defect.

WHAT THE HASH ACTUALLY COVERS, STATED PLAINLY BECAUSE IT IS EASY TO OVERREAD
------------------------------------------------------------------------------
`derived_schema_hash` covers the ten field DEFINITIONS plus the blindness
block's `run_at`, `labels_withheld`, `result` and `removed_fields`.
`max_predictive_accuracy` is EXCLUDED (`crucible/manifest/load.py`
HASH_EXCLUSIONS): it is a rate, and two runs whose fields are identical and
whose measured accuracy differs are the SAME SCHEMA.

The consequence, which nothing else in the repo says out loud: **as long as the
check returns PASS with no removals, the hash does not depend on the corpus.**
"Frozen with the corpus" is a statement about WHEN, not about WHAT is covered.
The corpus itself is covered by `corpus_hash`, the fifth lock's other half.
So the sealed-set refusal above is protecting THE GATE, not the hash - and that
is precisely why it has to be a refusal rather than a warning: nothing
downstream would ever notice.

THE CITATION DEFECT, reported rather than silently corrected
-------------------------------------------------------------
`crucible/harness/episode.py:72` raises "G1(b)" for all three of
`objective_set_hash`, `manifest_hash` and `derived_schema_hash`.
`measurement-spec.md:769` puts `objective_set_hash` under **G1(b)** and both
manifest hashes under **G1(c)**; `contracts/derived_schema.schema.json`
FREEZE_ORDER_DEFENCE agrees ("G1(c) asserts BOTH"). The refusal is right and the
citation is wrong. Not fixed here - it is another lane's file.

Run:  python scripts/freeze-d5-derived-schema.py            # dry run, prints only
      python scripts/freeze-d5-derived-schema.py --check    # recompute vs committed
      python scripts/freeze-d5-derived-schema.py --write    # THE OWNER, on D5
"""

import argparse
import io
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")

from corpus.blindness import FIELD_COMPUTERS, run_blindness_check  # noqa: E402
from corpus.errors import CorpusError  # noqa: E402
from corpus.load import load_corpus  # noqa: E402
from corpus.part_b import build_part_b  # noqa: E402
from corpus.sizing import check_sizing  # noqa: E402
from crucible.manifest import ManifestError, load_part_b  # noqa: E402

ARTIFACT = REPO / "corpus" / "derived_schema.json"
CONTRACT = REPO / "contracts" / "derived_schema.schema.json"
RECORD = REPO / "docs" / "proof" / "d5-derived-schema-freeze.json"

# Every input the frozen document is derived from. `corpus/sealed/` is NOT here
# and cannot be: it is gitignored by design (the real boundary is IAM, not the
# ignore line). Its absence from this list is recorded in the freeze record
# rather than left for a reader to assume.
SOURCE_PATHS = (
    "corpus/part_b.py",       # the ten field definitions - the hashed content
    "corpus/blindness.py",    # the check that gates the freeze
    "corpus/load.py",         # what "the whole corpus" resolves to
    "corpus/sizing.py",       # the sealed floor
    "corpus/schema.py",       # per-instance validation the check runs behind
    "corpus/pairs.json",
    "corpus/training",
    "fixtures/benign",
)

# The one field the document carries and the hash does not. Named here so the
# --check document comparison can exclude it deliberately instead of by accident.
EXCLUDED_FROM_HASH = ("blindness_check", "max_predictive_accuracy")


def git(*args):
    p = subprocess.run(["git", "-C", str(REPO)] + list(args),
                       capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def hash_document(doc):
    """`derived_schema_hash`, through the ONE hasher that computes it.

    `load_part_b` takes a path because the production caller reads the committed
    artifact off disk. Round-tripping through a temporary file keeps this script
    on that exact code path - including the enumerated hash exclusion - rather
    than reaching past it into `_load`. The bytes written here do not reach the
    hash: `_load` parses first and canonicalizes the parsed object, so indent and
    key order on disk are irrelevant to the result.
    """
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d) / "derived_schema.json"
        tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8", newline="\n")
        _, digest = load_part_b(tmp)
    return digest


def validate_against_contract(doc, problems):
    try:
        import jsonschema
    except ImportError:
        problems.append(
            "jsonschema is not installed, so C3 Part B could not be validated "
            "against contracts/derived_schema.schema.json. NOT-RUN is not a "
            "pass: refusing rather than freezing an unvalidated document.")
        return
    schema = json.loads(CONTRACT.read_text(encoding="utf-8"))
    errors = list(jsonschema.Draft202012Validator(schema).iter_errors(doc))
    for e in errors:
        problems.append(
            "the built Part B document violates its own contract at %s: %s"
            % (list(e.absolute_path) or "<root>", e.message))


def build(problems):
    """Load the corpus, run the gate, build the document. Returns (doc, report).

    Returns (None, None) and appends to `problems` on any refusal, so the caller
    can print every problem at once rather than dying on the first.
    """
    try:
        corpus = load_corpus()
    except CorpusError as e:
        problems.append("the corpus did not load: %s: %s" % (e.code, e.detail))
        return None, None

    counts = {k: len(corpus[k]) for k in
              ("training", "sealed", "benign", "known_bad")}

    if not corpus["_present"].get("sealed"):
        problems.append(
            "corpus/sealed/ is not on disk. It is gitignored, so a worktree and "
            "a fresh clone both have none - and the blindness check would then "
            "run over %d instances instead of the whole corpus and report PASS "
            "on a set that never included the 24 sealed F4 instances. Ruling "
            "19.3 says the WHOLE corpus. Fire this freeze from a machine that "
            "holds the sealed set."
            % (counts["training"] + counts["benign"]))
    elif not corpus["sealed"]:
        problems.append(
            "corpus/sealed/ exists and holds zero instances. Present-and-empty "
            "and absent are different facts and neither one may freeze.")

    try:
        check_sizing(corpus)
    except CorpusError as e:
        problems.append(
            "the corpus fails its own sizing check, so it is not the corpus "
            "Part B would be frozen alongside: %s: %s" % (e.code, e.detail))

    labelled = corpus["training"] + corpus["sealed"] + corpus["benign"]
    try:
        report = run_blindness_check(labelled)
    except CorpusError as e:
        problems.append("the label-blindness check could not run: %s: %s"
                        % (e.code, e.detail))
        return None, None

    try:
        doc = build_part_b(report)
    except CorpusError as e:
        # build_part_b refuses on a FAIL report. That refusal IS the gate, and
        # the remedy is to remove the leaking field and re-run - a pre-run
        # repair - never to freeze anyway.
        problems.append("Part B refused to build: %s: %s" % (e.code, e.detail))
        return None, report

    validate_against_contract(doc, problems)
    return doc, report


def check_git_state(problems):
    """Every source input committed, and identical to HEAD."""
    for rel in SOURCE_PATHS:
        _, out, _ = git("status", "--porcelain", "--", rel)
        if out:
            problems.append(
                "%s has uncommitted changes:\n      %s\n    Freezing a "
                "definition that exists only on this machine is not a freeze - "
                "the public commit timestamp is the evidence."
                % (rel, out.replace("\n", "\n      ")))
        rc, _, err = git("rev-parse", "--verify", "HEAD:%s" % rel)
        if rc != 0:
            problems.append("%s does not exist at HEAD: %s" % (rel, err))

    # The artifact itself, once it exists, must also be committed - otherwise
    # `--check` on another machine compares against nothing.
    if ARTIFACT.exists():
        _, out, _ = git("status", "--porcelain", "--",
                        ARTIFACT.relative_to(REPO).as_posix())
        if out:
            problems.append(
                "%s has uncommitted changes (%r). The freeze is the commit, not "
                "the write." % (ARTIFACT.relative_to(REPO).as_posix(), out))


def check_prior_record(digest, problems):
    if not RECORD.exists():
        return
    prior = json.loads(RECORD.read_text(encoding="utf-8"))
    if prior.get("derived_schema_hash") != digest:
        problems.append(
            "a D5 freeze record already exists naming %s and Part B now hashes "
            "to %s. Ruling 20: after D5 both artifacts are IMMUTABLE and "
            "identical in status, and section 8 rule 3 makes a mid-run change a "
            "stop condition rather than a repair. If the schema genuinely had to "
            "move, that is a coordinator ruling with a written statement of what "
            "it invalidates, not a re-run of this script."
            % (prior.get("derived_schema_hash", "?"), digest))
    else:
        print("D5 already frozen at %s and the definitions still match.\n" % digest)


def strip_excluded(doc):
    """A copy with the one hash-excluded field removed, for document comparison."""
    out = json.loads(json.dumps(doc))
    cur = out
    for key in EXCLUDED_FROM_HASH[:-1]:
        cur = cur.get(key, {})
    cur.pop(EXCLUDED_FROM_HASH[-1], None)
    return out


def emit(doc, report, digest):
    print("C3 Part B  corpus/derived_schema.json")
    print("  derived_schema_hash  %s" % digest)
    print("  schema_version       %d" % doc["schema_version"])
    print("  episode fields       %d" % len(doc["episode_fields"]))
    print("  derived fields       %d" % len(doc["derived_fields"]))
    print("  blindness result     %s" % doc["blindness_check"]["result"])
    print("  removed fields       %s" % (doc["blindness_check"]["removed_fields"]
                                         or "none"))
    print("")
    print("  LABEL-BLINDNESS - the gate on this freeze, ruling 19.3")
    print("    instances          %d  (%d attack / %d non-attack)"
          % (report["instances"], report["attacks"], report["non_attacks"]))
    print("    majority baseline  %.4f" % report["majority_class_baseline"])
    print("    max predictive acc %.4f   <- NOT in the hashed payload"
          % report["max_predictive_accuracy"])
    print("    leaking fields     %s" % (report["leaking_fields"] or "none"))
    print("    near-leak (>=0.95) %s" % (report["near_leak_fields"] or "none"))
    print("")
    width = max(len(n) for n in report["per_field"])
    for name in sorted(report["per_field"],
                       key=lambda k: -report["per_field"][k]["accuracy"]):
        row = report["per_field"][name]
        print("    %-*s  acc %.4f  distinct %-4d  %s"
              % (width, name, row["accuracy"], row["distinct_values"],
                 row["separating_rule"]))
    print("")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true",
                    help="WRITE the artifact and the freeze record. The project "
                         "owner runs this, on D5. A lane does not.")
    ap.add_argument("--check", action="store_true",
                    help="recompute from the checkout and compare against the "
                         "committed artifact and freeze record. Read-only.")
    args = ap.parse_args(argv)

    problems = []
    doc, report = build(problems)

    if doc is None:
        print("FREEZE REFUSED - Part B could not be built:")
        for p in problems:
            print("  * %s" % p)
        return 1

    digest = hash_document(doc)

    if args.check:
        emit(doc, report, digest)
        if not ARTIFACT.exists():
            print("no corpus/derived_schema.json - the freeze has not been run.")
            return 1
        try:
            committed_doc, committed_digest = load_part_b(ARTIFACT)
        except ManifestError as e:
            print("the committed artifact does not load: %s" % e)
            return 2
        ok = True
        if committed_digest != digest:
            print("MISMATCH - Part B moved after the freeze.\n  committed  %s\n"
                  "  recomputed %s" % (committed_digest, digest))
            ok = False
        # `load_part_b` already stripped the excluded field from what it
        # returned, so strip it from ours too. Comparing the raw documents would
        # report a mismatch whenever the measured accuracy shifted - which is
        # exactly the measurement-vs-definition confusion the exclusion exists
        # to prevent.
        if strip_excluded(doc) != committed_doc:
            print("MISMATCH - the definitions on disk differ from the "
                  "recomputed ones.")
            ok = False
        if RECORD.exists():
            rec = json.loads(RECORD.read_text(encoding="utf-8"))
            if rec.get("derived_schema_hash") != digest:
                print("MISMATCH - the freeze record names %s."
                      % rec.get("derived_schema_hash"))
                ok = False
        else:
            print("NOTE: no freeze record at %s."
                  % RECORD.relative_to(REPO).as_posix())
        if not ok:
            return 2
        print("The committed hash MATCHES the recomputed one.")
        if problems:
            # The hash matching is not the whole check. `derived_schema_hash`
            # does not depend on the corpus while the result is PASS with no
            # removals, so a match here says the DEFINITIONS did not move - it
            # says nothing about whether the gate still passes over the whole
            # corpus. Reporting that as a clean 0 would be an OK row over a
            # check that never ran.
            print("\nCHECK INCOMPLETE - the hash matched, the GATE was not "
                  "fully re-evaluated:")
            for p in problems:
                print("  * %s" % p)
            return 1
        print("The gate was re-run over the whole corpus and still passes.")
        return 0

    check_git_state(problems)
    check_prior_record(digest, problems)

    _, commit, _ = git("rev-parse", "HEAD")
    _, when, _ = git("log", "-1", "--format=%cI", "--", "corpus/part_b.py")

    emit(doc, report, digest)
    print("  HEAD                 %s" % commit)
    print("  part_b.py committed  %s" % (when or "UNKNOWN"))
    print("")

    if problems:
        print("FREEZE REFUSED - %d problem(s):" % len(problems))
        for p in problems:
            print("  * %s" % p)
        return 1

    if not args.write:
        print("DRY RUN. Nothing written. Re-run with --write to record the freeze.")
        print("This script's exit code is not the freeze; the commit is.")
        return 0

    ARTIFACT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "_what": "D5 hash-lock of C3 Part B, the predicate schema. Ruling 20 "
                 "split the capability manifest into Part A (D3, with the "
                 "target) and Part B (D5, with the corpus).",
        "_why": "The claim is that the ten fields the policy engine reads were "
                "defined, and shown label-blind, BEFORE any measurement. That "
                "claim is about a moment, so the record names the commit and its "
                "timestamp rather than only the hash.",
        "contract": "C3 part 2 of 2",
        "file": ARTIFACT.relative_to(REPO).as_posix(),
        "derived_schema_hash": digest,
        "episode_fields": len(doc["episode_fields"]),
        "derived_fields": len(doc["derived_fields"]),
        "hash_excludes": [".".join(EXCLUDED_FROM_HASH)],
        "hash_excludes_why":
            "a rate. canonicalization.md restriction 4 puts confidences and "
            "rates outside the hashed payload. Two runs whose FIELDS are "
            "identical and whose measured accuracy differs are the SAME SCHEMA. "
            "Consequence: this hash does not depend on the corpus. 'Frozen with "
            "the corpus' is a statement about WHEN, not about WHAT is covered - "
            "the corpus is covered by corpus_hash.",
        "blindness_check": {
            "instances": report["instances"],
            "attacks": report["attacks"],
            "non_attacks": report["non_attacks"],
            "majority_class_baseline": report["majority_class_baseline"],
            "max_predictive_accuracy": report["max_predictive_accuracy"],
            "leaking_fields": report["leaking_fields"],
            "near_leak_fields": report["near_leak_fields"],
            "result": report["result"],
        },
        "sealed_not_covered_by_commit_check":
            "corpus/sealed/ is gitignored and can never be committed, so the "
            "uncommitted-changes refusal cannot cover it. What IS asserted is "
            "that the directory was present and non-empty and that the corpus "
            "passed corpus.sizing.check_sizing, whose sealed floor is 18.",
        "fields_covered": sorted(FIELD_COMPUTERS),
        "head_commit": commit,
        "part_b_committed_at": when,
    }
    RECORD.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8",
                      newline="\n")

    # Postconditions, both read back off disk rather than trusted.
    _, back_digest = load_part_b(ARTIFACT)
    back_record = json.loads(RECORD.read_text(encoding="utf-8"))
    if back_digest != digest or back_record["derived_schema_hash"] != digest:
        print("WROTE THE ARTIFACT AND IT READ BACK WRONG.\n  computed %s\n"
              "  artifact %s\n  record   %s"
              % (digest, back_digest, back_record.get("derived_schema_hash")))
        return 1
    print("FROZEN. %s -> %s" % (ARTIFACT.relative_to(REPO).as_posix(), digest))
    print("        %s" % RECORD.relative_to(REPO).as_posix())
    print("Commit both files. The freeze is the commit, not the write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
