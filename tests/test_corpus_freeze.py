"""What `corpus_hash` covers, what moves it, and what it refuses.

`corpus_hash` is half of the fifth hash-lock. It had NO IMPLEMENTATION until
2026-08-22 - a schema field in `contracts/run_manifest.schema.json`, a row in the
replay viewer's lock table, and nothing computing it - so these tests are the
first thing that has ever been able to say the value is wrong.

THE TWO THINGS THIS FILE IS ACTUALLY FOR
-----------------------------------------
1. **The hash must move when the corpus moves.** A freeze that did not notice an
   edited training instance is a freeze-shaped object, and it would pass every
   other check in the build: the record exists, the hash is 16 hex, `--check`
   agrees with itself.
2. **The hash must NOT move for things that are not the corpus.** Re-indenting a
   fixture, reordering its keys, or checking the repo out with CRLF endings are
   not corpus changes, and a hash that moved on any of them would be re-run until
   somebody stopped believing it. `target/refund_agent/freeze.py` records the
   CRLF version of exactly that failure, already paid for once in this repo.

The tests below that assert NOTHING CHANGED are therefore not weak tests - they
are the negative controls on the first group. A hasher that ignored file contents
would pass all of group 2 and fail all of group 1; a raw-byte hasher would pass
all of group 1 and fail all of group 2. Only a JCS-canonical hasher passes both.
"""

import json
import pathlib
import subprocess
import sys

import pytest

from corpus.errors import CorpusError
from corpus.freeze import (
    DATA_FILES,
    INSTANCE_DIRS,
    SEAL_COMMITMENT,
    DiskSource,
    assert_no_sealed_path,
    census,
    corpus_hash,
    corpus_hash_full,
    covered_paths,
    file_digest,
    seal_fingerprint,
)
from corpus.model import BENIGN_TOTAL, TRAINING_TOTAL

REPO = pathlib.Path(__file__).resolve().parent.parent
FINGERPRINT = "a" * 64


class FakeSource:
    """A corpus in a dict. Lets a test move one byte and nothing else."""

    label = "fake"

    def __init__(self, files):
        self.files = dict(files)

    def list_json(self, directory):
        return sorted(p for p in self.files
                      if p.startswith(directory + "/") and p.endswith(".json"))

    def read(self, relpath):
        return self.files.get(relpath)


def instance(slug, amount=90000):
    return {"slug": slug, "kind": "attack", "amount_minor": amount,
            "approver": "NONE"}


def raw(obj, **kw):
    return json.dumps(obj, **kw).encode("utf-8")


def base_files():
    return {
        "corpus/training/F1-01.json": raw(instance("P01-attack")),
        "corpus/training/F1-02.json": raw(instance("P02-attack")),
        "fixtures/benign/ORD-01.json": raw(instance("P01-benign")),
        "corpus/pairs.json": raw({"pairs": [{"pair_id": "P01",
                                             "sep_by": "POL"}]}),
        "corpus/F4-MANIFEST.json": raw({"instances": 24,
                                        "set_digest": "6a9d35ae3f1c397f"}),
        SEAL_COMMITMENT: raw({"fingerprint": FINGERPRINT}),
    }


def source(**overrides):
    files = base_files()
    for path, value in overrides.items():
        if value is None:
            files.pop(path, None)
        else:
            files[path] = value
    return FakeSource(files)


# ---------------------------------------------------------------------------
# Shape, and the real corpus on disk.
# ---------------------------------------------------------------------------

def test_corpus_hash_is_sixteen_lowercase_hex():
    """`run_manifest.schema.json` declares `^[0-9a-f]{16}$` for `corpus_hash`.

    A hash that does not satisfy its own schema is rejected by the episode writer
    at the point where the run has already cost money.
    """
    value = corpus_hash(DiskSource(REPO))
    assert len(value) == 16
    assert all(c in "0123456789abcdef" for c in value)
    assert corpus_hash_full(DiskSource(REPO)).startswith(value)


def test_the_real_corpus_covers_the_frozen_counts():
    """78 files: 50 training, 26 benign, 2 data files.

    The expected values are READ from `corpus.model`, which owns them, rather
    than retyped here. `CONVENTIONS.md` ruling 43 moved training 48 -> 50 and
    benign 24 -> 26 on 2026-08-21, and `tests/test_corpus_sizing.py` is on record
    as having hardcoded the OLD numbers and therefore passing while the corpus
    and the ruling disagreed.
    """
    counts = census(DiskSource(REPO))
    assert counts["training"] == TRAINING_TOTAL
    assert counts["benign"] == BENIGN_TOTAL
    assert counts["data_files"] == len(DATA_FILES)
    assert counts["covered_files_total"] == TRAINING_TOTAL + BENIGN_TOTAL + 2


def test_every_covered_file_on_disk_canonicalizes():
    """The corpus is hash-locked at D5, and `corpus/README.md` uses that fact to
    justify the `"NONE"` sentinel over `null`. This is the test that makes the
    promise load-bearing instead of rhetorical."""
    disk = DiskSource(REPO)
    for path in covered_paths(disk):
        file_digest(disk.read(path), path)      # raises if it does not


# ---------------------------------------------------------------------------
# Group 1 - the hash MOVES when the corpus moves.
# ---------------------------------------------------------------------------

def test_hash_moves_when_a_training_instance_changes():
    """THE test. An edited attack instance must produce a different corpus.

    If this ever passes-as-equal, the freeze is decorative: the suite could be
    edited between the v0 arm and the vFinal arm and every published number would
    be measured against two different corpora under one hash.
    """
    before = corpus_hash_full(source())
    after = corpus_hash_full(source(**{
        "corpus/training/F1-01.json": raw(instance("P01-attack", amount=90001))}))
    assert before != after


def test_hash_moves_when_a_benign_fixture_changes():
    """The benign fixtures are inside the hash, and this is why it matters:
    `measurement-spec.md` section 5.2 fixes the BPR denominator at 26
    "permanently", and `CONVENTIONS.md` ruling 23 note 2 puts the approver each
    fixture declares inside the corpus hash by name."""
    before = corpus_hash_full(source())
    after = corpus_hash_full(source(**{
        "fixtures/benign/ORD-01.json": raw(
            {"slug": "P01-benign", "kind": "benign", "amount_minor": 90000,
             "approver": {"id": "sup_1", "tier": "T2"}})}))
    assert before != after


def test_hash_moves_when_a_sep_by_label_changes():
    """Ruling 17 makes the 18/4 SEP-BY split travel with EVERY ASR and BPR figure,
    permanently. A split that can move after D5 is a label that does not describe
    the run it is printed beside."""
    before = corpus_hash_full(source())
    after = corpus_hash_full(source(**{
        "corpus/pairs.json": raw({"pairs": [{"pair_id": "P01",
                                             "sep_by": "ORC"}]})}))
    assert before != after


def test_hash_moves_when_the_f4_manifest_changes():
    """`F4-MANIFEST.json` carries the sealed family's 24 content-addressed
    instance IDs and its `set_digest`. It is the pre-registration
    (`corpus/F4-SEALED-FAMILY.md`), and it is one of the two ways the sealed set
    is bound into `corpus_hash` without anything reading it."""
    before = corpus_hash_full(source())
    after = corpus_hash_full(source(**{
        "corpus/F4-MANIFEST.json": raw({"instances": 24,
                                        "set_digest": "0000000000000000"})}))
    assert before != after


def test_hash_moves_when_the_seal_commitment_fingerprint_changes():
    """The second binding to the sealed family, and the stronger one - a digest
    over the sealed BYTES rather than over their IDs.

    Swapping the sealed set wholesale changes this fingerprint, and therefore
    changes `corpus_hash`, without anything on this side of the boundary ever
    opening a sealed file.
    """
    before = corpus_hash_full(source())
    after = corpus_hash_full(source(**{SEAL_COMMITMENT: raw(
        {"fingerprint": "b" * 64})}))
    assert before != after


def test_hash_moves_when_an_instance_is_added():
    before = corpus_hash_full(source())
    after = corpus_hash_full(source(**{
        "corpus/training/F1-03.json": raw(instance("P03-attack"))}))
    assert before != after


def test_hash_moves_when_an_instance_is_removed():
    """A corpus that quietly lost a member is a different corpus, and the count
    is the denominator of every rate this project publishes."""
    before = corpus_hash_full(source())
    after = corpus_hash_full(source(**{"corpus/training/F1-02.json": None}))
    assert before != after


def test_hash_moves_when_an_instance_is_renamed():
    """Paths are inside the payload. A renamed file is a different corpus even
    when every byte of content is identical - the filenames carry the family and
    the ordering a reader uses to make sense of the set."""
    files = base_files()
    body = files.pop("corpus/training/F1-02.json")
    files["corpus/training/F9-99.json"] = body
    assert corpus_hash_full(source()) != corpus_hash_full(FakeSource(files))


# ---------------------------------------------------------------------------
# Group 2 - the negative controls. The hash does NOT move for non-changes.
# ---------------------------------------------------------------------------

def test_key_order_does_not_move_the_hash():
    """NEGATIVE CONTROL on group 1: proves the canonicalizer is actually being
    used rather than `sha256(raw_bytes)`.

    A raw-byte hasher passes every test above this line and fails here. Without
    this test, group 1 cannot tell a correct implementation from one that hashes
    file bytes and would then move on a re-indent, a key sort, or a checkout with
    different line endings.
    """
    reordered = {"approver": "NONE", "amount_minor": 90000,
                 "kind": "attack", "slug": "P01-attack"}
    assert corpus_hash_full(source()) == corpus_hash_full(source(**{
        "corpus/training/F1-01.json": raw(reordered)}))


def test_indentation_and_crlf_do_not_move_the_hash():
    """The CRLF failure this repository has already paid for once.

    `target/refund_agent/freeze.py` records it: `freeze.py` hashed raw bytes and
    the freeze hash differed between an LF working copy and a CRLF checkout -
    "correct on the machine that produced it and fails for the judge who clones
    it." JCS makes that structurally impossible for JSON, and this pins it.
    """
    pretty = json.dumps(instance("P01-attack"), indent=4).replace("\n", "\r\n")
    assert corpus_hash_full(source()) == corpus_hash_full(source(**{
        "corpus/training/F1-01.json": pretty.encode("utf-8")}))


def test_a_sealed_directory_appearing_does_not_move_the_hash():
    """THE PROPERTY THE BY-REFERENCE DESIGN WAS BOUGHT FOR.

    `corpus/sealed/` is gitignored and absent from a lane's worktree and from a
    judge's clone. If its arrival moved `corpus_hash`, then the value frozen at
    D5 could never be recomputed by anyone outside the build machine, and the one
    reproducibility claim the freeze exists to support would be false.

    The files created here are throwaway - the real sealed set is not read by
    this module, by this test, or by anything in this lane.
    """
    before = corpus_hash_full(source())
    after = corpus_hash_full(source(**{
        "corpus/sealed/F4-01.json": raw(instance("F4-01")),
        "corpus/sealed/F4-02.json": raw(instance("F4-02"))}))
    assert before == after


def test_no_covered_path_on_disk_is_under_the_seal():
    """The blindness boundary, asserted over the REAL repository layout.

    `measurement-spec.md` makes a read across the seal RUN INVALID. That the
    sealed directory is missing from a three-line tuple is not a guarantee; this
    is the check that would notice an edit that added it.
    """
    paths = covered_paths(DiskSource(REPO))
    assert not [p for p in paths if p.startswith("corpus/sealed/")]
    assert "corpus/sealed" not in INSTANCE_DIRS


def test_a_sealed_path_in_the_covered_set_is_refused():
    with pytest.raises(CorpusError) as e:
        assert_no_sealed_path(["corpus/training/F1-01.json",
                               "corpus/sealed/F4-01.json"])
    assert e.value.code == "E_SEAL_CROSSED"


# ---------------------------------------------------------------------------
# Refusals. Each one is a way a hash could be produced over the wrong thing.
# ---------------------------------------------------------------------------

def test_a_file_that_does_not_canonicalize_is_refused_not_skipped():
    """The failure mode this refusal exists for is SILENCE.

    Skipping an uncanonicalizable file produces a perfectly valid 16 hex
    characters over a corpus with one member missing, and nothing downstream can
    tell. `crucible/manifest/load.py` says it for Part B and it is true here: the
    exclusion list "must never become 'strip whatever fails to canonicalize'".
    """
    with pytest.raises(CorpusError) as e:
        corpus_hash_full(source(**{
            "corpus/training/F1-01.json": b'{"slug":"x","rate":0.5}'}))
    assert e.value.code == "E_COVERED_FILE_NOT_CANONICALIZABLE"


def test_a_null_in_a_covered_file_is_refused():
    """Restriction 5. `CONVENTIONS.md` ruling 23.4's correction turns on exactly
    this: `null` is not a preference that lost an argument, it is unrepresentable
    in a hash-locked artifact, which is why the corpus uses the `"NONE"`
    sentinel."""
    with pytest.raises(CorpusError) as e:
        corpus_hash_full(source(**{
            "corpus/training/F1-01.json": b'{"slug":"x","approver":null}'}))
    assert e.value.code == "E_COVERED_FILE_NOT_CANONICALIZABLE"


def test_a_bom_in_a_covered_file_is_refused():
    """Restriction 1, and `corpus/load.py` already refuses a BOM for this exact
    reason: stripping it here would move the defect to the freeze."""
    with pytest.raises(CorpusError) as e:
        corpus_hash_full(source(**{
            "corpus/training/F1-01.json":
                b"\xef\xbb\xbf" + raw(instance("P01-attack"))}))
    assert e.value.code == "E_COVERED_FILE_NOT_CANONICALIZABLE"


def test_a_missing_data_file_is_refused():
    with pytest.raises(CorpusError) as e:
        corpus_hash_full(source(**{"corpus/pairs.json": None}))
    assert e.value.code == "E_COVERED_FILE_MISSING"


def test_a_corpus_with_no_instances_is_refused():
    """Hashing an instance-less corpus yields 16 valid-looking hex characters and
    every check downstream goes green, with a denominator of zero no gate looks
    at. `CONVENTIONS.md` section 8 rule 2: a check that cannot fail is not
    measuring anything.

    NOTE the guard is on INSTANCES, not on covered paths. `DATA_FILES` is a
    hardcoded tuple, so a `covered_paths` emptiness guard could itself never
    fire - which is the same defect one level up. The first version of this test
    caught exactly that and is the reason the guard reads the way it does.
    """
    with pytest.raises(CorpusError) as e:
        corpus_hash_full(FakeSource({
            "corpus/pairs.json": raw({"pairs": []}),
            "corpus/F4-MANIFEST.json": raw({"instances": 24}),
            SEAL_COMMITMENT: raw({"fingerprint": FINGERPRINT})}))
    assert e.value.code == "E_EMPTY_CORPUS"


def test_the_emptiness_guard_can_actually_fire():
    """The negative control on the guard above.

    A guard placed where it can never trigger is indistinguishable from no guard,
    and it reads as protection in every review. This asserts that the condition
    is reachable with all the non-instance files present - which is precisely the
    case the first draft could not reach.
    """
    with pytest.raises(CorpusError):
        corpus_hash_full(FakeSource({
            "corpus/pairs.json": raw({"pairs": []}),
            "corpus/F4-MANIFEST.json": raw({"instances": 24}),
            SEAL_COMMITMENT: raw({"fingerprint": FINGERPRINT})}))
    # ... and that it does NOT fire as soon as one instance exists.
    corpus_hash_full(FakeSource({
        "corpus/training/F1-01.json": raw(instance("P01-attack")),
        "corpus/pairs.json": raw({"pairs": []}),
        "corpus/F4-MANIFEST.json": raw({"instances": 24}),
        SEAL_COMMITMENT: raw({"fingerprint": FINGERPRINT})}))


def test_an_absent_seal_commitment_is_refused():
    """Without it the held-out family is not inside `corpus_hash` at all, and the
    D5 claim rests on nothing a stranger can check."""
    with pytest.raises(CorpusError) as e:
        corpus_hash_full(source(**{SEAL_COMMITMENT: None}))
    assert e.value.code == "E_NO_SEAL_COMMITMENT"


def test_a_short_seal_fingerprint_is_refused():
    """A truncated fingerprint silently weakens the only binding between
    `corpus_hash` and the sealed set, and it would still look like a hash."""
    with pytest.raises(CorpusError) as e:
        seal_fingerprint(source(**{SEAL_COMMITMENT: raw(
            {"fingerprint": "2cde0250de00e692"})}))
    assert e.value.code == "E_SEAL_FINGERPRINT_SHAPE"


# ---------------------------------------------------------------------------
# The coverage decision itself, pinned so it cannot drift silently.
# ---------------------------------------------------------------------------

def test_the_nine_known_bads_are_not_inside_corpus_hash():
    """A DECISION, pinned. `corpus/freeze.py` carries the argument; this is what
    makes reversing it a deliberate act rather than a side effect of adding a
    directory to a tuple."""
    paths = covered_paths(DiskSource(REPO))
    assert not [p for p in paths if "known_bad" in p]
    assert not [p for p in paths if p.startswith("tests/")]


def test_the_three_known_bads_that_cannot_be_hashed_still_cannot():
    """THE CALIBRATION TEST BEHIND THAT DECISION.

    KB5 carries `_expected_benign_pass_rate: 0.0` - a rate, which restriction 4
    puts outside any hashed payload - and KB6/KB8 carry `expected_invariant_id:
    null`, which restriction 5 refuses. Those three are why the nine cannot enter
    a JCS payload without editing calibration fixtures to fit a hash.

    **If this test goes red, the reason for the exclusion has changed and the
    exclusion must be re-decided**, not repaired. That is the whole point of
    asserting a state rather than trusting a comment: the comment would have gone
    stale silently.
    """
    from crucible.canon import CanonicalizationError, canonicalize_bytes
    kb_dir = REPO / "tests" / "golden_traces" / "known_bad"
    still_unhashable = []
    for name in ("KB5", "KB6", "KB8"):
        try:
            canonicalize_bytes((kb_dir / ("%s.json" % name)).read_bytes())
        except CanonicalizationError:
            still_unhashable.append(name)
    assert still_unhashable == ["KB5", "KB6", "KB8"], (
        "one of KB5/KB6/KB8 now canonicalizes. The argument in corpus/freeze.py "
        "for keeping the nine known-bads out of corpus_hash rests on these three "
        "being unhashable by rule. Re-decide the coverage; do not just delete "
        "this test.")


def test_derived_schema_and_part_a_are_not_inside_corpus_hash():
    """Ruling 20 split the capability manifest into two artifacts with two freeze
    dates and two hashes. One hash over both would collapse `manifest_hash` and
    `derived_schema_hash` into `corpus_hash`, and the run manifest declares six
    fields."""
    paths = covered_paths(DiskSource(REPO))
    assert not [p for p in paths if p.endswith("derived_schema.json")]
    assert not [p for p in paths if p.endswith("capability_manifest.json")]


def test_census_is_not_inside_the_hashed_payload():
    """Counts are derived from the file list that is already in the payload.
    `corpus/schema.py` states the doctrine: a checked copy of a derived value is
    still a second copy."""
    from corpus.freeze import corpus_payload
    payload = corpus_payload(source())
    assert set(payload) == {"artifact", "algorithm", "files",
                            "sealed_seal_commitment_fingerprint"}


def test_covered_paths_are_sorted_at_construction():
    """Restriction 6 sorts arrays AT CONSTRUCTION, never at hash time, precisely
    so that sorting inside the canonicalizer would be lossless-looking and
    destructive."""
    from corpus.freeze import corpus_payload
    paths = [f["path"] for f in corpus_payload(DiskSource(REPO))["files"]]
    assert paths == sorted(paths)


# ---------------------------------------------------------------------------
# The freeze script. It is the owner's tap; a lane proves it refuses.
# ---------------------------------------------------------------------------

SCRIPT = REPO / "scripts" / "freeze-d5-corpus.py"


def run_script(*args, cwd=None):
    p = subprocess.run([sys.executable, str(SCRIPT)] + list(args),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(cwd or REPO))
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def test_check_and_write_are_mutually_exclusive():
    """Two different jobs. A `--check --write` that silently did one of them is a
    freeze fired by a typo."""
    rc, out = run_script("--check", "--write")
    assert rc == 2
    assert "different jobs" in out


def test_the_dry_run_is_the_default_and_writes_nothing():
    """`--write` is reserved for the owner. Running the script with no flags must
    never produce the record."""
    record = REPO / "docs" / "proof" / "d5-corpus-freeze.json"
    existed = record.exists()
    rc, out = run_script()
    assert rc in (0, 1)
    assert "corpus_hash" in out
    assert record.exists() == existed


def test_the_dry_run_refuses_without_a_sealed_directory():
    """`corpus/sealed/` is gitignored, so a lane worktree and a fresh clone both
    lack it. The hash does not need it; the CLAIM does, and the freeze refuses
    rather than recording a corpus whose held-out half nobody verified."""
    if (REPO / "corpus" / "sealed").is_dir():
        pytest.skip("this checkout holds the sealed set; the refusal cannot fire")
    rc, out = run_script()
    assert rc == 1
    assert "FREEZE REFUSED" in out
    assert "corpus/sealed/" in out


def test_check_recomputes_from_head_not_from_disk():
    """A recompute that read the working tree would prove the working tree agrees
    with itself. The freeze names COMMITTED bytes."""
    rc, out = run_script("--check")
    assert "recomputed from HEAD, not from disk" in out
    assert rc in (0, 1)


def test_the_committed_corpus_hashes_to_the_same_value_as_the_working_tree():
    """The recompute path, exercised end to end against real git objects.

    This is the half of `--check` that has to work for a judge: `GitSource` reads
    blobs out of a ref and never touches the working tree. Equality with the disk
    value proves two things at once - the ref reader works, and every covered file
    on disk is identical to the committed one.

    It goes RED when a corpus file has uncommitted changes, and that is correct
    rather than annoying: during freeze week an uncommitted corpus edit is exactly
    the condition the freeze must refuse on.
    """
    def git(*args, binary=False):
        p = subprocess.run(["git", "-C", str(REPO)] + list(args),
                           capture_output=True, text=not binary,
                           encoding=None if binary else "utf-8",
                           errors=None if binary else "replace")
        if binary:
            return p.returncode, p.stdout, p.stderr
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()

    from corpus.freeze import GitSource
    head = GitSource(git)
    assert covered_paths(head) == covered_paths(DiskSource(REPO))
    assert corpus_hash_full(head) == corpus_hash_full(DiskSource(REPO))


def test_the_recompute_reads_no_sealed_path_out_of_git_either():
    """`corpus/sealed/` is gitignored, so it is not in the ref - but the covered
    set is asserted rather than assumed on this path too. The boundary does not
    get a pass because git happens to be enforcing it today."""
    def git(*args, binary=False):
        p = subprocess.run(["git", "-C", str(REPO)] + list(args),
                           capture_output=True, text=not binary,
                           encoding=None if binary else "utf-8",
                           errors=None if binary else "replace")
        if binary:
            return p.returncode, p.stdout, p.stderr
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()

    from corpus.freeze import GitSource
    assert not [p for p in covered_paths(GitSource(git))
                if p.startswith("corpus/sealed/")]
