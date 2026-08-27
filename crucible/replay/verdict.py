"""verdict.py - ruling 60. WHOSE FAULT IS IT, and therefore which exit code.

`integrity.verify_bundle` answers ONE question: is this bundle evidence. Ruling
60 needs a SECOND answer out of the same defect list, and it is a different
question entirely:

    STRUCTURAL   the bundle is not a faithful record of anything. A required
                 fact is absent, malformed, or written twice with two values.
                 THE FIX IS IN THE PRODUCER. Exit NON-ZERO: we emitted garbage
                 and the campaign did not finish its job.

    MEASUREMENT  the bundle is well-formed and internally consistent, and what
                 it correctly says is that this run's figures may not be quoted.
                 THE FIX IS A RE-RUN, A RE-AUTHORING, OR A DETERMINATION - never
                 an edit to the writer. Exit 0: a correct record of a bad run IS
                 the job done, and a batch of legitimately excluded runs must
                 not look like a crash.

THE OPERATIONAL TEST, and it is the one that decided every row below: LOOK AT
WHERE THE FIX GOES. Producer -> STRUCTURAL. Run, corpus, or authoring ->
MEASUREMENT. "Is a fact missing" does NOT decide it, and the two adjacent
autopsy codes are the proof: `E_AUTOPSIES_MISSING` is the array absent from a
document that always builds one, and `E_AUTOPSY_MISSING_FOR_BREACH` is the
CORONER never having been called - the second is honest reporting of an absence
that happened, and writing the record would be fabricating a finding.

WHY THE DEFAULT IS STRUCTURAL AND NOT MEASUREMENT. A code nobody classified is
a code nobody thought about. Defaulting it to MEASUREMENT exits 0 and hides it,
which is the precise shape of the defect ruling 60 exists to close - thirty-one
unreadable bundles, every one exit 0. Defaulting it to STRUCTURAL stops a batch
and someone classifies it. The noisy direction is the safe one here.

That default is a backstop, not the mechanism.
`tests/test_reader_verdict.py::test_every_code_the_reader_can_emit_is_classified`
walks `integrity.py` for string literals and fails on any code this table does
not carry, so the default is never expected to fire in production - and
`unclassified` is reported in the artifact so that when it does, it is visible
rather than merely conservative.
"""

import json
import pathlib

STRUCTURAL = "STRUCTURAL"
MEASUREMENT = "MEASUREMENT"
CLEAN = "CLEAN"

ACCEPTS = "ACCEPTS"
REJECTS = "REJECTS"

# The verdict layer's own code. `verify_bundle` documents that it raises
# nothing, but it is handed whatever the producer built, and several checks walk
# nested structures with `.get`. A bundle malformed enough to crash the reader
# is the most structural defect there is, so it gets a code rather than an
# exception that would take the artifact down with it - and the artifact is
# needed most in exactly that case.
E_READER_CRASHED = "E_READER_CRASHED"


# ---------------------------------------------------------------------------
# THE PARTITION. Every code `crucible/replay/integrity.py` can emit, classified,
# with the reason recorded beside it rather than in a document nobody re-opens.
# ---------------------------------------------------------------------------

_STRUCTURAL_REASONS = {
    # -- the document cannot be parsed, validated, or hashed ------------------
    "E_SCHEMA": "the document violates its own contract",
    "E_NO_VALIDATOR": (
        "the check could not run. NEITHER class strictly: this is an "
        "ENVIRONMENT defect, not a document one and not a run one. It is here "
        "because an unevaluable check must not exit 0 - a check that cannot "
        "fail is not measuring anything (measurement-spec.md:813)"),
    "E_NOT_CANONICALIZABLE": (
        "no canonical form, so no digest, so no figure from it pins to "
        "anything. Wraps E_NULL, E_SURROGATE, E_TOO_DEEP, E_NONSTRING_KEY, "
        "E_UNSUPPORTED_TYPE and the float rejects from crucible/canon"),

    # -- a lock or stamp the producer holds and did not write ------------------
    "E_LOCK_MISSING": "the producer holds all six locks and wrote fewer",
    "E_LOCK_MALFORMED": "the producer wrote a lock that is not a lock",
    "E_EPISODE_STAMP_MISSING": (
        "the episode writer REFUSES to write an episode missing it, so an "
        "episode in the bundle without it was not written by that writer"),
    "E_EPISODE_STAMP_MALFORMED": "same writer, malformed value",
    "E_EPISODE_STAMP_DISAGREES": (
        "two arms under two rulers. A reader cannot determine which Objective "
        "Set the figures were measured against, so the figures are unreadable"),
    "E_VERDICT_STAMP_DISAGREES": "same shape, verdict against episode",

    # -- the ruling 16 freeze block -------------------------------------------
    "E_FROZEN_CONTEXT_MISSING": "the producer records the block; absent means unwritten",
    "E_FROZEN_CONTEXT_INCOMPLETE": "same",
    "E_FROZEN_TOO_LATE": (
        "`frozen_at` is a producer-written LITERAL, not a runtime observation, "
        "so any other value is the producer writing a different constant. IF "
        "IT EVER BECOMES A REAL TIMESTAMP this row moves to MEASUREMENT and "
        "this comment is the thing that has to change with it"),

    # -- the replay prefix -----------------------------------------------------
    "E_PREFIX_MISSING": (
        "an EMPTY prefix is legal and raises nothing; this fires only on a "
        "non-list, which is a serialization defect"),
    "E_PREFIX_UNORDERED": (
        "the order carries the meaning - a prefix out of order replays a "
        "different episode than the one that ran"),

    # -- frozen-by-contract quantities ----------------------------------------
    "E_BENIGN_TRACES_SHORT": (
        "THE CLOSEST CALL IN THIS TABLE. 26 is frozen PERMANENTLY by ruling 43 "
        "and pinned by G3 to the literal string 26/26. No re-run and no "
        "authoring decision can change it, so a bundle carrying fewer traces "
        "than the corpus holds was produced by a writer that dropped some. A "
        "quantity a run cannot move is not a measurement about the run"),

    # -- ruling 17's split ----------------------------------------------------
    "E_SEP_BY_MISSING": (
        "a derived reporting field the producer computes from data it holds; "
        "absent, every rate in the bundle is unfalsifiable"),
    "E_SEP_BY_MALFORMED": "counts that are not counts",

    # -- the policy chain ------------------------------------------------------
    "E_CHAIN_ORDER": "versions out of order in a list the producer assembled",
    "E_CHAIN_PARENT": (
        "CONTESTED. The check's own text names a RUN cause - 'a gap is what a "
        "silently failed promotion looks like' - but the consequence is that "
        "the lineage cannot be traversed, so 'blocked at v3' resolves to "
        "nothing and the per-attack arc is unreadable. Unreadable decides it"),
    "E_POLICY_TEXT_MISSING": (
        "the rule text exists in the policy store and the bundle omitted it. "
        "A hash is a receipt, not a rule"),
    "E_EPISODE_POLICY_UNKNOWN": "a dangling reference; the policy cannot be read",

    # -- gate decisions --------------------------------------------------------
    "E_ROUND_OUT_OF_RANGE": "outside the frozen round cap, so unreadable against this build",
    "E_ROUND_DUPLICATED": "two decisions for one round; which one is unanswerable",

    # -- the attack catalogue --------------------------------------------------
    "E_ATTACKS_MISSING": "a scoreboard rather than a record of an engagement",
    "E_ATTACK_DUPLICATED": "which text ran is a question the bundle answers two ways",
    "E_GENERATED_ATTACK_TEXT_MISSING": (
        "the RED STRATEGIST produced the string in memory and this record is "
        "the only copy there will ever be. The writer dropped it"),
    "E_ATTACK_UNCATALOGUED": (
        "a dangling reference; the verdict cannot be traced to what was tested"),

    # -- clause coverage -------------------------------------------------------
    "E_COVERAGE_MISSING": "the table is absent from a document that always builds one",
    "E_COVERAGE_HASH_DISAGREES": "coverage of a different definition of breach. Two rulers",
    "E_COVERAGE_INCOMPLETE": "a clause that BREACHED has no row; the census is of something else",
    "E_COVERAGE_DISAGREES": "two arms counting the same clause differently",
    "E_COVERAGE_COLLAPSED": "a row shape the producer emitted short",
    "E_COVERAGE_NOT_MONOTONE": "the four numbers did not come from one measurement",
    "E_COVERAGE_STATE_DISAGREES": (
        "the check's own words: 'a producer describing a run the numbers "
        "beside it do not describe'"),
    "E_COVERAGE_SOURCES_DISAGREE": "a breakdown that disagrees with the row a reader quotes",

    # -- the exclusion ledger's SHAPE, as against its VALUES -------------------
    "E_EXCLUSION_LEDGER_MISSING": "no ledger and no denominators; the ceiling is unevaluable",
    "E_EXCLUSION_LEDGER_SHORT": (
        "the exclusions happened and their instance ids exist; the producer "
        "wrote the count and not the names, which makes the ceiling "
        "unauditable. Shape, not value"),
    "E_EXCLUSION_ORPHAN": "exclusions against a round with no denominator",
    "E_CENSUS_DUPLICATED": "one round, two census rows",
    "E_CENSUS_ARITHMETIC": "attempted != scorable + excluded. The denominator does not account for itself",
    "E_CENSUS_OUTCOME_DISAGREES": (
        "`outcome` is a label the producer assigns and it contradicts the "
        "counters printed beside it - the same shape as "
        "E_COVERAGE_STATE_DISAGREES, and what stops relabelling from being a "
        "dodge around the ceiling"),

    # -- the autopsy ARRAY, as against a MISSING AUTOPSY -----------------------
    "E_AUTOPSIES_MISSING": (
        "the array is absent from a document that always builds one. Its "
        "neighbour E_AUTOPSY_MISSING_FOR_BREACH is MEASUREMENT and the split "
        "is deliberate: that one is the CORONER never called, this one is the "
        "writer never writing"),

    # -- provenance and labels: a caveat that contradicts its own bundle -------
    "E_PROVENANCE_MISSING": "the single most important caveat about a run, absent",
    "E_MODE_DISAGREES_WITH_COMPONENTS": (
        "a stand-in run wearing a live label. A producer contradiction: every "
        "other field looks identical either way"),
    "E_LIVE_WITHOUT_MODEL_CALLS": "the exact shape of a scripted run wearing a live label",
    "E_G7G8_WITH_STANDIN_GATE": (
        "CONTESTED, and the hardest row here. The check quotes G8's failure "
        "text, whose failure mode is RUN INVALID - a MEASUREMENT reading. It "
        "sits on the structural side because nothing at runtime can make "
        "`g7_g8_exercised: true` and `gate.implementation: stand_in` both "
        "true; it is two producer-written fields contradicting each other in "
        "the same breath, and an OVERCLAIM that exits 0 is the failure ruling "
        "60 closes"),
    "E_LABELS_MISSING": "every figure then travels unlabelled",
    "E_LABEL_MISSING": "one caveat absent",
    "E_LABEL_DISAGREES": "a label that has stopped being true is worse than a missing one",

    # -- this module's own -----------------------------------------------------
    E_READER_CRASHED: "the reader could not complete. The most structural defect there is",
}

_MEASUREMENT_REASONS = {
    "E_AUTOPSY_MISSING_FOR_BREACH": (
        "NAMED IN RULING 60. The CORONER was never called for that episode, so "
        "the bundle honestly records an absence; writing the record would be "
        "fabricating a finding. `tests/test_c6_producer.py::KNOWN_GAP`"),
    "E_EXCLUSION_CEILING_RUN": (
        "NAMED IN RULING 60. The pooled denominator was quietly shrunk. THE "
        "RUN IS INCOMPLETE and must be RE-RUN, not reported"),
    "E_EXCLUSION_CEILING": (
        "the same rule of measurement-spec 5.1 scoped to one round's "
        "denominator. The round is INCOMPLETE and must be RE-RUN"),
    "E_SEP_BY_PARITY": (
        "the counts are present and well-formed and the RATIO is the finding: "
        "ruling 17's authoring gate, whose remedy is STOP AND RE-AUTHOR. The "
        "fix is in the corpus, not the writer"),
    "E_DEGENERATE_INSTANCE_RUN": (
        "the check says it in words - THE RUN IS INVALID: no rate may be "
        "quoted from it. Ruling 56"),
    "E_NO_MEASUREMENT_IN_RUN": (
        "FOUND LIVE 2026-08-27. A live run recorded zero episodes, so every "
        "per-episode check passed VACUOUSLY and the reader said ACCEPTS beside "
        "an exit code of 2. MEASUREMENT by the discriminant: the producer "
        "wrote a faithful document and the RUN is what is invalid. The fix is "
        "a re-run - and separately a C6 field for RUN_INVALID, which does not "
        "exist"),
    "E_DEGENERACY_CENSUS_MISSING": (
        "THE RUN IS INVALID, and the remedy the check itself prints is to "
        "write a determination or re-run on a build that applies the licence. "
        "Neither is an edit to the producer"),
}

CLASSIFICATION = {}
CLASSIFICATION.update({code: STRUCTURAL for code in _STRUCTURAL_REASONS})
CLASSIFICATION.update({code: MEASUREMENT for code in _MEASUREMENT_REASONS})

REASONS = {}
REASONS.update(_STRUCTURAL_REASONS)
REASONS.update(_MEASUREMENT_REASONS)


def classify(code):
    """The class of one defect code. UNKNOWN CODES ARE STRUCTURAL - see module
    docstring for why the noisy direction is the safe one."""
    return CLASSIFICATION.get(code, STRUCTURAL)


def partition(defects):
    """`(structural, measurement, unclassified)`, each a sorted unique list of
    CODES rather than defects. A batch reader wants to know which kinds fired,
    not how many times each one did; the count travels separately."""
    structural, measurement, unclassified = set(), set(), set()
    for defect in defects:
        code = getattr(defect, "code", defect)
        if code not in CLASSIFICATION:
            unclassified.add(code)
        if classify(code) == MEASUREMENT:
            measurement.add(code)
        else:
            structural.add(code)
    return sorted(structural), sorted(measurement), sorted(unclassified)


def exit_class(defects):
    """CLEAN, MEASUREMENT, or STRUCTURAL. STRUCTURAL wins over MEASUREMENT when
    both fired: a bundle we cannot read tells us nothing about the run inside
    it, so there is no honest way to report the measurement half."""
    structural, measurement, _unclassified = partition(defects)
    if structural:
        return STRUCTURAL
    if measurement:
        return MEASUREMENT
    return CLEAN


# ---------------------------------------------------------------------------
# THE PER-RUN ARTIFACT. Ruling 60: "reading a batch without consulting it should
# require IGNORING A FILE SITTING RIGHT THERE, rather than knowing to go look."
# ---------------------------------------------------------------------------

SCHEMA = "crucible.reader_verdict.v1"

# A `.reader.json` beside `run-NN.c6.json` and `run-NN.exitcode`, following
# night-batch.sh's convention of one flat sidecar per fact.
SUFFIX = ".reader.json"
_BUNDLE_SUFFIX = ".c6.json"


def verdict_path(bundle_path):
    """`<x>.c6.json` -> `<x>.reader.json`. ONE OWNER for the suffix, so the
    write path and every aggregate compute it the same way rather than each
    spelling it out - `campaign.c6_path` exists for exactly this reason."""
    text = str(bundle_path)
    if text.endswith(_BUNDLE_SUFFIX):
        return text[:-len(_BUNDLE_SUFFIX)] + SUFFIX
    return str(pathlib.Path(text).with_suffix("")) + SUFFIX


def verdict_record(report, bundle_path=None, schema_errors=()):
    """The record, from an `IntegrityReport`.

    `schema_errors` is passed separately because the PRODUCER validates against
    C6 before it ever calls the reader, and on a schema failure it returns
    without reading. The artifact has to carry that case or it would be absent
    from exactly the runs that need it most.

    NO DIGEST IS RECORDED HERE, DELIBERATELY. Ruling 46: a frozen hash has
    exactly one owner, and the canonical digest's owner is the bundle's own
    `.sha256` sidecar. A second copy here would be a second owner, and this
    file's question is whether the bundle can be READ, which no hash answers.
    """
    schema_errors = list(schema_errors or ())
    defects = list(getattr(report, "defects", ()) or ())
    codes = [getattr(d, "code", d) for d in defects]
    # A SCHEMA FAILURE IS A DEFECT CODE LIKE ANY OTHER, and it enters the
    # partition as one. Ruling 60 names schema errors on the structural side,
    # and folding them in here rather than special-casing them downstream means
    # `verdict` and `exit_class` have ONE definition instead of two that can
    # drift - the producer's early return would otherwise be a second opinion.
    if schema_errors:
        codes.append("E_SCHEMA")
    structural, measurement, unclassified = partition(codes)
    rows = list(getattr(report, "rows", ()) or ())
    record = {
        "schema": SCHEMA,
        "bundle": pathlib.Path(str(bundle_path)).name if bundle_path else None,
        "verdict": ACCEPTS if not (defects or schema_errors) else REJECTS,
        "exit_class": exit_class(codes),
        "defect_count": len(defects) + len(schema_errors),
        "structural": structural,
        "measurement": measurement,
        # Empty in every expected case. Present ALWAYS rather than only when
        # non-empty: a key that appears only on failure is a key every reader
        # forgets to look for.
        "unclassified": unclassified,
        "codes": sorted(set(codes)),
        "checks_ok": sum(1 for row in rows if getattr(row, "status", None) == "OK"),
        "checks_total": len(rows),
        "schema_errors": len(schema_errors),
    }
    return record


def Defect_like(code, where="$", detail=""):
    """A minimal stand-in for `integrity.Defect`, for callers that need to feed
    a code into `partition` without importing the reader."""
    return type("_D", (), {"code": code, "where": where, "detail": detail})()


def write_verdict(record, bundle_path):
    """Write the artifact beside the bundle. Returns the path written.

    ONE LINE, sorted keys, trailing newline, LF. One line so a whole batch is
    one command - `cat evidence/<batch>/run-*.reader.json` yields one record per
    run - and sorted so two runs with the same verdict produce the same bytes.
    """
    path = pathlib.Path(verdict_path(bundle_path))
    blob = json.dumps(record, sort_keys=True) + "\n"
    # newline="" so this file is LF on Windows too. A CRLF sidecar breaks the
    # one-command grep it exists for.
    with open(str(path), "w", encoding="utf-8", newline="") as handle:
        handle.write(blob)
    return str(path)


# ---------------------------------------------------------------------------
# THE READ SIDE. Ruling 60 part 3: every aggregate over a batch reports
# acceptance beside its figure.
# ---------------------------------------------------------------------------

class Acceptance:
    """What the reader said about a set of runs, and about the ones it did not
    say anything about.

    `unknown` IS NOT ZERO AND MUST NEVER BE PRINTED AS THOUGH IT WERE. A run
    whose verdict file is absent - a halted run, a run from before this artifact
    existed, a run whose bundle was never written - is a run whose acceptance
    NOBODY KNOWS. Folding it into `rejected` overstates what was checked;
    dropping it silently is the defect ruling 60 closes, one level up.
    """

    __slots__ = ("accepted", "rejected", "unknown")

    def __init__(self, accepted=0, rejected=0, unknown=0):
        self.accepted = accepted
        self.rejected = rejected
        self.unknown = unknown

    @property
    def total(self):
        return self.accepted + self.rejected + self.unknown

    @property
    def complete(self):
        """True when every run in the pool has a verdict."""
        return self.unknown == 0

    def phrase(self):
        """The clause ruling 60 requires beside any figure.

        Not "of which the reader accepts 4" when three verdicts are missing -
        that sentence claims six rejections the reader never made.
        """
        if not self.total:
            return "AND THE POOL IS EMPTY, so every figure below is over nothing"
        if self.complete:
            return ("of which the reader ACCEPTS %d and REJECTS %d"
                    % (self.accepted, self.rejected))
        return ("of which the reader ACCEPTS %d, REJECTS %d, and %d have NO "
                "READER VERDICT AT ALL - acceptance is UNKNOWN for those and "
                "no figure here may be read as covering them"
                % (self.accepted, self.rejected, self.unknown))

    def __repr__(self):
        return "Acceptance(accepted=%d, rejected=%d, unknown=%d)" % (
            self.accepted, self.rejected, self.unknown)


def read_verdict(bundle_path):
    """The record beside a bundle, or None when there is none.

    None means UNKNOWN, never ACCEPTS. A malformed record is also None: a
    verdict file we cannot parse tells us nothing, and guessing from it would be
    the reader's own defect wearing this module's clothes.
    """
    path = pathlib.Path(verdict_path(bundle_path))
    if not path.is_file():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        return None
    return record


def acceptance(bundle_paths):
    """`Acceptance` over an iterable of bundle paths.

    Takes the BUNDLES rather than the directory so the pool is the caller's -
    an aggregate that filters runs must count acceptance over the runs it
    actually used, not over everything on disk beside them.
    """
    counts = Acceptance()
    for bundle_path in bundle_paths:
        record = read_verdict(bundle_path)
        if record is None:
            counts.unknown += 1
        elif record.get("verdict") == ACCEPTS:
            counts.accepted += 1
        else:
            counts.rejected += 1
    return counts


BANNER_RULE = (
    "RULING 60: every figure over a batch prints its ACCEPTANCE beside it. "
    "Not \"median 2.5 across ten runs\" but \"median 2.5 across ten runs, of "
    "which the reader accepts four.\"")


def batch_banner(bundle_paths, label="run"):
    """THE LINE RULING 60 REQUIRES ABOVE ANY FIGURE OVER A BATCH.

    Returns `(text, counts)`. ONE OWNER FOR THE SENTENCE, because nine scripts
    each phrasing it themselves is nine chances to phrase it flatteringly, and
    the one that matters most - the UNKNOWN case - is the one a hand-written
    version omits. A script that filters its pool passes the FILTERED paths and
    gets a count over what it actually used.

    This is the part of ruling 60 that would have caught the defect. The exit
    code is the smaller half: twenty files saying `0` were enough to carry a
    published headline off ten runs the reader refuses, and a denominator
    printed without its acceptance count is that failure returning.
    """
    paths = list(bundle_paths)
    counts = acceptance(paths)
    lines = ["ACCEPTANCE: %d %s(s) in this pool, %s."
             % (counts.total, label, counts.phrase()),
             "  " + BANNER_RULE]
    return "\n".join(lines), counts


def print_batch_banner(bundle_paths, label="run"):
    """`batch_banner` straight to stdout. Returns the counts so a caller can
    branch on `.complete` without computing acceptance a second time."""
    text, counts = batch_banner(bundle_paths, label)
    print(text)
    return counts


def accepted_only(bundle_paths):
    """The subset the reader accepts, and the `Acceptance` over the WHOLE pool.

    Returns `(paths, counts)`. The counts describe the input, not the output,
    because a figure computed over the filtered set still has to say what it
    dropped - "median 2.5 across four runs" without "of ten" is the same
    unlabelled number in a smaller costume.
    """
    keep = []
    counts = Acceptance()
    for bundle_path in bundle_paths:
        record = read_verdict(bundle_path)
        if record is None:
            counts.unknown += 1
        elif record.get("verdict") == ACCEPTS:
            counts.accepted += 1
            keep.append(bundle_path)
        else:
            counts.rejected += 1
    return keep, counts
