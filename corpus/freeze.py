"""freeze.py - `corpus_hash`, the fifth hash-lock's first half. D5.

`docs/execution-spec.md` Day 5 item 3: *"Corpus hashed and committed, referencing
the frozen target hash and the gate rule hash."* That sentence is the whole
requirement, and it does not say what "the corpus" is. This module answers that
question ONCE, enumerated, with a reason on every line, so the answer is auditable
rather than implied by whatever a glob happened to match.

The one other file in the repo that states the boundary from the outside agrees:
`scripts/freeze-d5-derived-schema.py` says *"The corpus itself is covered by
`corpus_hash`, the fifth lock's other half"*, and its `SOURCE_PATHS` resolve "the
corpus" to `corpus/pairs.json`, `corpus/training` and `fixtures/benign` - three of
the four things covered below, arrived at independently for a different reason.

    corpus_hash = hash_full(payload)[:16]      # 16 hex, run_manifest.schema.json

WHAT IS INSIDE, AND WHERE EACH ANSWER CAME FROM
------------------------------------------------
`corpus/training/*.json`      the 50 training attacks. `execution-spec.md` D5.1;
                              `CONVENTIONS.md` section 4 frozen numbers.
`fixtures/benign/*.json`      the 26 benign fixtures, 14 of them near-misses.
                              `CONVENTIONS.md` ruling 23 note 2 is explicit and is
                              the closest thing to a direct answer anywhere in the
                              spec set: *"The oracle's data (which approver each
                              fixture declares) is inside the corpus hash at D5."*
                              A fixture is a benign fixture; attack episodes
                              declare no approver. `measurement-spec.md` section
                              5.2 fixes the BPR denominator at 26 "permanently",
                              and section 5.1 names denominator drift as a way the
                              measurement lies, "countered by freezing corpus_id".
`corpus/pairs.json`           the 27 pair records carrying the SEP-BY labels.
                              Ruling 17 makes the 18/4 split travel with EVERY ASR
                              and BPR figure, permanently. A split that can move
                              after D5 is a label that does not describe the run
                              it is printed beside.
`corpus/F4-MANIFEST.json`     the sealed family's 24 content-addressed
                              `instance_id` values plus its `set_digest`.
                              `corpus/F4-SEALED-FAMILY.md`: *"That is the
                              pre-registration."*
seal commitment fingerprint   the `fingerprint` field of
                              `docs/proof/sealed-family-commitment.json`, and only
                              that field. A second, INDEPENDENT digest over the
                              same 24 files - names plus LF-normalized bytes -
                              already published with a public commit timestamp.

THE SEALED SET ENTERS BY REFERENCE, NEVER BY CONTENT
-----------------------------------------------------
`corpus/sealed/` is gitignored and is not in this repository. Reading it here
would cross the blindness boundary the entire measurement rests on, and
`measurement-spec.md` makes a read across it RUN INVALID. So the sealed family
enters `corpus_hash` through two digests that were computed elsewhere, by other
code, and are already committed: `set_digest` inside `F4-MANIFEST.json`, and the
seal commitment's `fingerprint`.

**The consequence, stated plainly so nobody has to work it out later: this hash
does not change when the sealed set is "added". There is nothing to add.** A
worktree that holds the 24 files and one that does not compute the SAME
`corpus_hash`, which is exactly the property a judge cloning the public repo
needs - and it is only a real property because both referenced digests are
content-addressed over the sealed bytes by code that IS allowed to read them.

WHAT IS OUTSIDE, AND WHY EACH ONE IS NOT AN OVERSIGHT
------------------------------------------------------
Part B / `derived_schema.json`   its own lock, `derived_schema_hash`. Ruling 20
                                 split the manifest into two artifacts with two
                                 freeze dates; `crucible/manifest/load.py` says
                                 they hash separately on purpose. One hash over
                                 both would make "corpus + derived schema" one
                                 thing, and the run manifest declares six fields.
Part A / capability manifest     `manifest_hash`, frozen D3 WITH THE TARGET.
the nine known-bad fixtures      SEE THE BLOCK BELOW. This is the one exclusion
                                 that is a judgement call rather than a citation.
`corpus/*.py`, `*.md`            validators, linters, and prose. The same cut
                                 `target/refund_agent/freeze.py` makes when it
                                 leaves the fake ledger and the demo transcripts
                                 out: a freeze that moved when a docstring was
                                 reworded would be re-run until it stopped
                                 meaning anything.
`tests/golden_traces/*`          fixtures for the test suite, not corpus.
gate rule / target hashes        REFERENCED in the freeze record, not hashed into
                                 the payload. D5 item 3 says "referencing", and a
                                 `corpus_hash` that moved when the target was
                                 re-frozen would no longer be a function of the
                                 corpus. `scripts/freeze-d5-corpus.py` REFUSES if
                                 either prior lock is missing or disagrees, which
                                 is what makes the reference load-bearing.

THE NINE KNOWN-BADS ARE OUT, AND THIS IS THE ARGUMENT
-------------------------------------------------------
1. **Three of them cannot enter a hashed payload at all.** Verified against the
   files, 2026-08-22: `KB5._expected_benign_pass_rate` is `0.0` - a RATE, which
   `contracts/canonicalization.md` restriction 4 puts OUTSIDE a hashed payload by
   rule, the same class of thing `crucible/manifest/load.py` already had to
   enumerate for Part B - and `KB6.expected_invariant_id` / `KB8.expected_invariant_id`
   are `null`, which restriction 5 refuses. KB6 expects `INVALID` and KB8 expects
   `CLEAN`; neither violates an invariant, so the null is the fixture saying the
   true thing about itself. **Editing a calibration fixture so that a hash will
   accept it is weakening a gate to fit a check**, which `CONVENTIONS.md` section
   8 rule 3 makes a stop condition, and which the Part B exclusion list already
   refuses in its own comment: *it must never become "strip whatever fails to
   canonicalize."*
2. **The repository already says the D5 artifact is instance-shaped.** The comment
   above `load_known_bads` in `corpus/load.py` rejects putting the nine into the
   instance schema because it "would mean inventing a tool call that never
   happened, inside an artifact that gets hashed at D5."
3. **They are gate calibration, not corpus.** G1 is "CALIBRATION + ORACLE FREEZE";
   the nine decide whether the RUN is valid, and none of them is scored into ASR
   or BPR. `known_bad_count: 9` is already a frozen C7 parameter hash-locked at D2.

**The residual gap, named rather than papered over.** Points 2 and 3 cover the
COUNT and the expected VERDICT; neither covers a known-bad's CONTENT. A KB whose
body changed after D5 in a way that did not flip its verdict would pass G1(a) and
touch no hash-lock. So `scripts/freeze-d5-corpus.py` writes the nine LF-normalized
digests into the freeze RECORD, labelled as NOT part of `corpus_hash`. That closes
the gap with evidence instead of with a hash the payload cannot legally carry.

WHY JCS AND NOT THE TEXTUAL FORM
---------------------------------
Every file covered here is JSON that is REQUIRED to canonicalize - `corpus/load.py`
already refuses a BOM for exactly this reason, and `corpus/README.md` says the
corpus "is hash-locked at D5" as the justification for the `"NONE"` sentinel over
`null`. Hashing the canonical bytes rather than the raw ones makes that promise
load-bearing: a file that would have failed at freeze time fails HERE, by refusal,
instead of surfacing on freeze day as a corpus that will not canonicalize. The
textual form (`canonicalization.md` section 4) exists for contract files that are
not JSON at all, which is not this.
"""

import hashlib
import pathlib

from crucible.canon import CanonicalizationError, canonicalize_bytes, hash_full

from .errors import CorpusError

REPO = pathlib.Path(__file__).resolve().parent.parent

# Directories whose every `*.json` is a corpus instance. Enumerated, not
# discovered: a new directory appearing under `corpus/` must be a decision.
INSTANCE_DIRS = ("corpus/training", "fixtures/benign")

# Individual corpus data files. `F4-MANIFEST.json` is how the sealed set's
# content-addressed IDs get inside the hash without anything reading them.
DATA_FILES = ("corpus/pairs.json", "corpus/F4-MANIFEST.json")

# The second, independent digest over the sealed family. Only the `fingerprint`
# field is used - the surrounding record is prose that may legitimately be
# reworded, and a freeze that moved when a `_why` sentence was edited would be
# re-run until nobody believed it.
SEAL_COMMITMENT = "docs/proof/sealed-family-commitment.json"
SEAL_FINGERPRINT_FIELD = "fingerprint"

# Written into the payload so the algorithm travels with the artifact rather than
# living only in this docstring. A judge recomputing the hash reads this string.
ALGORITHM = (
    "For each covered file, sorted by repo-relative POSIX path at construction: "
    "sha256 over its RFC 8785 (JCS) canonical bytes, per contracts/"
    "canonicalization.md. Those digests are assembled into this object and the "
    "object is hashed the same way. corpus_hash is the first 16 hex characters. "
    "The sealed family is present by REFERENCE ONLY - its content is never read."
)

ARTIFACT = ("CRUCIBLE corpus, D5 hash-lock. The half of the fifth lock that is "
            "the corpus; derived_schema_hash is the other half.")


class DiskSource:
    """Covered files as they are on disk. What `--dry-run` hashes."""

    def __init__(self, repo=None):
        self.repo = pathlib.Path(repo or REPO)
        self.label = "working tree"

    def list_json(self, directory):
        d = self.repo / directory
        if not d.is_dir():
            return []
        return sorted("%s/%s" % (directory, p.name) for p in d.glob("*.json"))

    def read(self, relpath):
        p = self.repo / relpath
        if not p.is_file():
            return None
        return p.read_bytes()


class GitSource:
    """Covered files as they are at a git ref. What `--check` hashes.

    A recompute that reads the working tree proves the working tree agrees with
    itself. The freeze names COMMITTED bytes - `scripts/freeze-d2-gate-rule.py`
    makes the same point as a byte comparison rather than a git-status string -
    so the recompute reads the ref.
    """

    def __init__(self, run_git, ref="HEAD"):
        self._git = run_git
        self.ref = ref
        self.label = "git %s" % ref

    def list_json(self, directory):
        rc, out, _ = self._git("ls-tree", "-r", "--name-only", self.ref,
                               "--", directory + "/")
        if rc != 0:
            return []
        return sorted(line for line in out.splitlines()
                      if line.endswith(".json") and
                      line.count("/") == directory.count("/") + 1)

    def read(self, relpath):
        rc, out, _ = self._git("show", "%s:%s" % (self.ref, relpath), binary=True)
        return out if rc == 0 else None


def file_digest(raw, where):
    """sha256 over the JCS-canonical bytes of one covered file.

    REFUSES rather than repairs, and refuses by name. A corpus file that does not
    canonicalize is not a file to work around at freeze time: it is the defect
    `corpus/README.md` promises cannot exist, arriving on the one day nobody has
    slack to fix it.
    """
    if raw is None:
        raise CorpusError(
            "E_COVERED_FILE_MISSING",
            "%s is inside corpus_hash and is not present. A freeze computed over "
            "a set that quietly lost a member is a freeze over a different "
            "corpus, and the hash would look exactly as valid." % where)
    try:
        return hashlib.sha256(canonicalize_bytes(raw)).hexdigest()
    except CanonicalizationError as e:
        raise CorpusError(
            "E_COVERED_FILE_NOT_CANONICALIZABLE",
            "%s does not canonicalize (%s). The corpus is hash-locked at D5, so "
            "this is refused here rather than stripped, coerced, or skipped - "
            "each of which would put a value into a frozen artifact that the "
            "canonicalizer says cannot be in one." % (where, e)) from None


def covered_paths(source):
    """Every repo-relative path inside `corpus_hash`, sorted at construction.

    Sorted HERE, not at hash time: `canonicalization.md` restriction 6 sorts
    arrays at construction precisely so that sorting inside the canonicalizer
    would be lossless-looking and destructive.
    """
    paths = []
    for directory in INSTANCE_DIRS:
        paths.extend(source.list_json(directory))
    paths.extend(DATA_FILES)
    return sorted(set(paths))


def assert_no_sealed_path(paths):
    """The blindness boundary, asserted rather than assumed.

    `corpus/sealed/` is absent from `INSTANCE_DIRS`, and that is a fact about a
    tuple three lines long which a future edit can undo without anyone noticing.
    This is the check that notices. `measurement-spec.md` makes a read across the
    seal RUN INVALID, so the failure is a refusal, not a warning.
    """
    leaked = [p for p in paths if p.startswith("corpus/sealed/")]
    if leaked:
        raise CorpusError(
            "E_SEAL_CROSSED",
            "the covered set names %d path(s) under corpus/sealed/: %s. The "
            "sealed family enters corpus_hash by REFERENCE - F4-MANIFEST.json's "
            "content-addressed instance_ids and the published seal commitment "
            "fingerprint - and never by content. A hasher that reads it has "
            "crossed the boundary every number in this project rests on."
            % (len(leaked), leaked[:3]))


def seal_fingerprint(source):
    """The published seal commitment's fingerprint, as an opaque string.

    Read out of the committed record rather than recomputed, because recomputing
    it means reading the 24 sealed files and this module may not.
    """
    import json

    raw = source.read(SEAL_COMMITMENT)
    if raw is None:
        raise CorpusError(
            "E_NO_SEAL_COMMITMENT",
            "%s is absent. It carries the only digest over the sealed family "
            "that this module is allowed to see, and without it the held-out set "
            "is not inside corpus_hash at all - which would leave the D5 claim "
            "('the held-out attacks existed before the first patch was written') "
            "resting on nothing that a stranger can check." % SEAL_COMMITMENT)
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise CorpusError("E_SEAL_COMMITMENT_MALFORMED",
                          "%s: %s" % (SEAL_COMMITMENT, e)) from None
    value = doc.get(SEAL_FINGERPRINT_FIELD)
    if not isinstance(value, str) or len(value) != 64:
        raise CorpusError(
            "E_SEAL_FINGERPRINT_SHAPE",
            "%s.%s is %r; a full sha256 hex digest was expected. A short or "
            "absent fingerprint silently weakens the only binding between "
            "corpus_hash and the sealed set."
            % (SEAL_COMMITMENT, SEAL_FINGERPRINT_FIELD, value))
    return value


def corpus_payload(source):
    """The exact object that gets hashed.

    No timestamps, no paths outside the repo, no run id - a payload carrying any
    of those hashes differently on two machines, and recompute-from-a-clean-
    checkout is the property the whole freeze is for.
    """
    paths = covered_paths(source)
    assert_no_sealed_path(paths)

    # THE EMPTINESS CHECK IS ABOUT INSTANCES, NOT ABOUT COVERED PATHS, and the
    # difference is the whole value of it. `DATA_FILES` is a hardcoded tuple, so
    # `covered_paths` is never empty and a `if not paths` guard here could never
    # fire - a check that cannot fail, which is the exact shape CONVENTIONS
    # section 8 rule 2 forbids and which this module refuses elsewhere. What IS
    # reachable is a repository whose `corpus/training/` and `fixtures/benign/`
    # are empty or absent while both data files sit there: that hashes to a
    # perfectly valid-looking 16 hex characters over a corpus with no instances
    # in it, and nothing downstream can tell.
    instances = [p for p in paths
                 if any(p.startswith(d + "/") for d in INSTANCE_DIRS)]
    if not instances:
        raise CorpusError(
            "E_EMPTY_CORPUS",
            "the covered set holds %d file(s) and NOT ONE corpus instance - "
            "%s are empty or absent. Hashing that produces a valid-looking "
            "corpus_hash over a suite with nothing in it, and every rate "
            "computed against it would have a denominator of zero that no gate "
            "in the build inspects."
            % (len(paths), " and ".join(INSTANCE_DIRS)))
    return {
        "artifact": ARTIFACT,
        "algorithm": ALGORITHM,
        "files": [{"path": p, "sha256": file_digest(source.read(p), p)}
                  for p in paths],
        "sealed_seal_commitment_fingerprint": seal_fingerprint(source),
    }


def corpus_hash_full(source):
    return hash_full(corpus_payload(source))


def corpus_hash(source):
    """The 16 hex characters `run_manifest.schema.json` declares."""
    return corpus_hash_full(source)[:16]


def census(source):
    """Counts, for the record and for a human reading the dry run.

    DELIBERATELY OUTSIDE THE HASHED PAYLOAD. Every count here is derived from the
    file list that is already in the payload, and `corpus/schema.py` states the
    doctrine: a checked copy of a derived value is still a second copy.
    """
    paths = covered_paths(source)
    return {
        "training": sum(1 for p in paths if p.startswith("corpus/training/")),
        "benign": sum(1 for p in paths if p.startswith("fixtures/benign/")),
        "data_files": sum(1 for p in paths if p in DATA_FILES),
        "covered_files_total": len(paths),
    }
