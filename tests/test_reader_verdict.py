"""test_reader_verdict.py - ruling 60, all three parts, each proved falsifiable.

THE DEFECT THIS SUITE PINS. `write_bundle` computed the offline reader's
verdict, PRINTED `OFFLINE READER: REJECTS`, and returned only the SCHEMA errors;
`campaign.py` then exited 0. Thirty-one bundles across three batches were
unreadable and every one exited 0, and a published headline was computed off ten
of them.

WHY THE STRUCTURAL FIXTURE IS SCHEMA-VALID, and it is the whole design of this
file. A structural defect the SCHEMA also catches proves nothing: the old code
returned schema errors, so such a test would have passed against the defect it
is supposed to catch. `_structural()` below mutates an episode stamp so that the
bundle VALIDATES CLEANLY against C6 and the offline reader still refuses it.
That case exits 0 on the old code and non-zero on the new one, which is what
makes this a test rather than a description.

  clean        the golden bundle                        -> exit 0,  ACCEPTS
  measurement  one autopsy removed for a breach         -> exit 0,  REJECTS
  structural   one episode stamp moved off the manifest -> non-zero, REJECTS

AND THE PARTITION IS PROVED ABLE TO FAIL. `test_the_partition_can_be_inverted_
and_the_suite_notices` flips every classification and asserts the first two
cases swap exit codes. Without it, a table that classified everything one way
would pass every other test in this file that it happened to agree with.
"""

import copy
import json
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
GOLDEN = REPO / "contracts" / "golden" / "C6-evidence_bundle.valid.json"

from crucible.conductor import bundle as B          # noqa: E402
from crucible.conductor import campaign as C        # noqa: E402
from crucible.replay import integrity as I          # noqa: E402
from crucible.replay import verdict as V            # noqa: E402


# ==========================================================================
# Fixtures. Three bundles, one clean and two damaged in exactly one way each.
# ==========================================================================

@pytest.fixture(scope="module")
def golden():
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def _measurement(golden):
    """A bundle that READS and reports an invalid run.

    One autopsy removed for a breach episode -> `E_AUTOPSY_MISSING_FOR_BREACH`,
    the code ruling 60 names on the measurement side and the code
    `tests/test_c6_producer.py::KNOWN_GAP` deliberately keeps green.
    """
    out = copy.deepcopy(golden)
    breach = next(e for e in out["episodes"]
                  if (e.get("verdict") or {}).get("verdict") == "BREACH")
    out["autopsies"] = [a for a in out["autopsies"]
                        if a.get("attack_id") != breach["attack_id"]]
    return out


def _structural(golden):
    """A bundle the SCHEMA ACCEPTS and the reader refuses.

    An episode's `objective_set_hash` moved to another well-formed 16-hex value.
    Every field is individually valid - which is why the schema passes - and the
    defect exists only BETWEEN the episode and the manifest that locks it. Two
    arms under two rulers: a reader cannot determine which Objective Set the
    figures were measured against, so the figures are unreadable.
    """
    out = copy.deepcopy(golden)
    out["episodes"][0]["objective_set_hash"] = "0123456789abcdef"
    return out


def _exit_code(structural_reasons):
    """The expression `campaign.py` runs, evaluated here rather than described.

    Re-stating the rule as `1 if reasons else 0` would be a second opinion about
    the exit code and would pass while the real line did the wrong thing.
    """
    return 0 if not structural_reasons else C.EXIT_BUNDLE_INVALID


# ==========================================================================
# PART 1 - the exit code splits
# ==========================================================================

def test_a_structural_defect_the_schema_accepts_still_exits_non_zero(
        golden, tmp_path, capsys):
    """RED BEFORE THE FIX. The schema passes, so the old `write_bundle` returned
    an empty error list and the campaign exited 0 on a bundle nothing can
    read."""
    damaged = _structural(golden)
    assert B.validate_bundle(damaged) == [], (
        "this fixture must be SCHEMA-VALID or it proves nothing the old code "
        "did not already catch")

    reasons, _path = B.write_bundle(damaged, str(tmp_path / "run-01.c6.json"))
    assert reasons, "a structural defect must reach the caller"
    assert _exit_code(reasons) == C.EXIT_BUNDLE_INVALID
    assert "E_EPISODE_STAMP_DISAGREES" in " ".join(reasons)
    assert "OFFLINE READER: REJECTS" in capsys.readouterr().out


def test_a_measurement_only_defect_is_rejected_by_the_reader_and_exits_zero(
        golden, tmp_path, capsys):
    """THE HALF THAT IS EASY TO GET WRONG IN THE OTHER DIRECTION.

    The reader REFUSES this bundle and the campaign still exits 0, because a
    correct record of a bad run IS the job done and a batch of legitimately
    excluded runs must not look like a crash.
    """
    damaged = _measurement(golden)
    assert B.validate_bundle(damaged) == []
    report = I.verify_bundle(damaged)
    assert {d.code for d in report.defects} == {"E_AUTOPSY_MISSING_FOR_BREACH"}, (
        "this fixture must produce the MEASUREMENT code and nothing else")

    reasons, _path = B.write_bundle(damaged, str(tmp_path / "run-02.c6.json"))
    assert reasons == [], (
        "a measurement defect must NOT reach the exit code: %r" % (reasons,))
    assert _exit_code(reasons) == 0

    printed = capsys.readouterr().out
    assert "OFFLINE READER: REJECTS" in printed
    # The exit code says 0 and the bundle is refused, so the run MUST say both
    # out loud or the pair reads as a contradiction nobody can resolve.
    assert "MEASUREMENT defect(s)" in printed


def test_a_clean_bundle_exits_zero_and_the_reader_accepts_it(
        golden, tmp_path, capsys):
    """The control. Inverting the partition CANNOT break this case - there are
    no defects to classify - so it is asserted on the VERDICT as well as the
    exit code, which is the part that can still be wrong."""
    reasons, path = B.write_bundle(copy.deepcopy(golden),
                                   str(tmp_path / "run-03.c6.json"))
    assert reasons == []
    assert _exit_code(reasons) == 0
    assert "OFFLINE READER: ACCEPTS" in capsys.readouterr().out

    record = V.read_verdict(path)
    assert record["verdict"] == V.ACCEPTS
    assert record["exit_class"] == V.CLEAN
    assert record["defect_count"] == 0


def test_the_partition_can_be_inverted_and_the_suite_notices(
        golden, tmp_path, monkeypatch):
    """PROOF THAT THE THREE TESTS ABOVE MEASURE THE PARTITION.

    CONVENTIONS section 8 rule 2: a check that cannot fail is not measuring
    anything. A classification table that put every code on one side would still
    satisfy whichever of the cases above it happened to agree with. So the table
    is flipped wholesale and both damaged cases must swap exit codes.
    """
    flipped = {code: (V.MEASUREMENT if cls == V.STRUCTURAL else V.STRUCTURAL)
               for code, cls in V.CLASSIFICATION.items()}
    monkeypatch.setattr(V, "CLASSIFICATION", flipped)

    reasons, _ = B.write_bundle(_structural(golden),
                                str(tmp_path / "inv-01.c6.json"))
    assert reasons == [], (
        "inverted, the structural case must exit 0 - if it does not, the "
        "structural test above is passing for some reason other than the "
        "partition")

    reasons, _ = B.write_bundle(_measurement(golden),
                                str(tmp_path / "inv-02.c6.json"))
    assert reasons, (
        "inverted, the measurement case must exit non-zero - if it does not, "
        "the measurement test above is passing for some reason other than the "
        "partition")


def test_structural_wins_when_both_classes_fired(golden):
    """A bundle we cannot read tells us nothing about the run inside it, so
    there is no honest way to report the measurement half of it."""
    both = _structural(_measurement(golden))
    codes = {d.code for d in I.verify_bundle(both).defects}
    assert "E_AUTOPSY_MISSING_FOR_BREACH" in codes
    assert "E_EPISODE_STAMP_DISAGREES" in codes
    assert V.exit_class(codes) == V.STRUCTURAL


# ==========================================================================
# PART 1b - the table is complete, and stays complete
# ==========================================================================

def test_every_defect_code_the_reader_can_emit_is_classified():
    """THE BACKSTOP IS NOT THE MECHANISM.

    `classify` defaults an unknown code to STRUCTURAL so a code nobody thought
    about cannot exit 0. That default must never fire in production, and the way
    to keep it from firing is to fail HERE the day a new check is added - not to
    trust that whoever adds it remembers a table in another file.

    Reads `integrity.py` as TEXT on purpose. Importing it and inspecting would
    only see codes on paths this test happens to execute, and every one of these
    lives inside a branch that fires on damaged input.
    """
    source = (REPO / "crucible" / "replay" / "integrity.py").read_text(
        encoding="utf-8")
    emittable = set(re.findall(r'"(E_[A-Z0-9_]+)"', source))
    assert len(emittable) > 40, (
        "the scan found %d codes, which is too few to be this module - the "
        "regex has stopped matching and this check has stopped measuring"
        % len(emittable))
    missing = sorted(c for c in emittable if c not in V.CLASSIFICATION)
    assert missing == [], (
        "ruling 60 needs every reader code on one side of the partition. "
        "Unclassified, and therefore silently STRUCTURAL: %s" % ", ".join(missing))


def test_the_two_examples_ruling_60_names_land_where_it_puts_them():
    """The spine names four codes across the two classes. If the table ever
    disagrees with CONVENTIONS, CONVENTIONS wins and the table is the defect."""
    assert V.classify("E_NOT_CANONICALIZABLE") == V.STRUCTURAL
    assert V.classify("E_SCHEMA") == V.STRUCTURAL
    assert V.classify("E_EXCLUSION_CEILING_RUN") == V.MEASUREMENT
    assert V.classify("E_AUTOPSY_MISSING_FOR_BREACH") == V.MEASUREMENT


def test_every_classified_code_carries_the_reason_it_was_classified():
    """A partition with no recorded reason is a partition nobody can review, and
    the next person to touch it will move a row by feel."""
    missing = sorted(c for c in V.CLASSIFICATION if not V.REASONS.get(c))
    assert missing == [], missing


def test_an_unknown_code_fails_closed_to_structural():
    """The direction of the default IS the ruling. A code nobody classified
    exiting 0 is the defect ruling 60 closes, arriving through a new check
    instead of through an old one."""
    assert V.classify("E_SOMETHING_NOBODY_HAS_WRITTEN_YET") == V.STRUCTURAL
    assert V.exit_class(["E_SOMETHING_NOBODY_HAS_WRITTEN_YET"]) == V.STRUCTURAL
    _s, _m, unclassified = V.partition(["E_SOMETHING_NOBODY_HAS_WRITTEN_YET"])
    assert unclassified == ["E_SOMETHING_NOBODY_HAS_WRITTEN_YET"], (
        "failing closed silently is only half the job - the artifact has to "
        "SAY a code was unclassified or the conservatism is invisible")


# ==========================================================================
# PART 2 - the verdict artifact
# ==========================================================================

def test_the_artifact_exists_and_is_correct_after_a_run_that_exits_non_zero(
        golden, tmp_path):
    """THE CASE THE ARTIFACT EXISTS FOR.

    A happy-path-only test would miss it entirely: the file is needed most on
    the run that failed, and the failure path is the one with an early return in
    it.
    """
    path = str(tmp_path / "run-07.c6.json")
    reasons, _ = B.write_bundle(_structural(golden), path)
    assert _exit_code(reasons) != 0

    written = pathlib.Path(V.verdict_path(path))
    assert written.exists(), (
        "the run exited non-zero and left no reader verdict beside it, which is "
        "the exact case ruling 60 wrote this artifact for")
    record = json.loads(written.read_text(encoding="utf-8"))
    assert record["schema"] == V.SCHEMA
    assert record["verdict"] == V.REJECTS
    assert record["exit_class"] == V.STRUCTURAL
    assert "E_EPISODE_STAMP_DISAGREES" in record["structural"]
    assert record["measurement"] == []
    assert record["unclassified"] == []
    assert record["bundle"] == "run-07.c6.json"


def test_the_artifact_is_written_even_when_the_schema_itself_fails(tmp_path):
    """THE EARLIEST RETURN IN THE PRODUCER, and the one a happy-path test never
    reaches. `write_bundle` returns before the offline reader is ever run when
    C6 validation fails, so the artifact has to be written on that branch too or
    the worst bundles are the ones with no verdict."""
    path = str(tmp_path / "run-08.c6.json")
    reasons, _ = B.write_bundle({"bundle_version": 2}, path)
    assert reasons

    record = V.read_verdict(path)
    assert record is not None, "no verdict artifact beside a schema failure"
    assert record["verdict"] == V.REJECTS
    assert record["exit_class"] == V.STRUCTURAL
    assert record["schema_errors"] > 0
    assert record["checks_total"] == 0, (
        "the reader never ran on this path, so the record must not report "
        "checks that did not happen")


def test_the_artifact_records_a_measurement_rejection_as_measurement(
        golden, tmp_path):
    """REJECTS and exit 0 at the same time, which is the shape of the ruling and
    the shape a reader of the batch has to be able to see."""
    path = str(tmp_path / "run-09.c6.json")
    reasons, _ = B.write_bundle(_measurement(golden), path)
    assert _exit_code(reasons) == 0

    record = V.read_verdict(path)
    assert record["verdict"] == V.REJECTS
    assert record["exit_class"] == V.MEASUREMENT
    assert record["measurement"] == ["E_AUTOPSY_MISSING_FOR_BREACH"]
    assert record["structural"] == []


def test_the_artifact_is_one_line_of_lf_so_a_batch_greps_in_one_command(
        golden, tmp_path):
    """The naming and the shape are the point: ruling 60 wants reading a batch
    without consulting it to require IGNORING A FILE SITTING RIGHT THERE.

    One line, LF, beside `run-NN.exitcode` in `night-batch.sh`'s convention.
    Pretty-printed JSON would need a parser per file; CRLF would break the grep
    on the machine this repository is built on.
    """
    path = str(tmp_path / "run-10.c6.json")
    B.write_bundle(copy.deepcopy(golden), path)
    raw = pathlib.Path(V.verdict_path(path)).read_bytes()
    assert b"\r" not in raw, "CRLF in the sidecar the one-command grep reads"
    assert raw.endswith(b"\n")
    assert raw.count(b"\n") == 1, "one record, one line"
    assert V.verdict_path(path).endswith("run-10.reader.json")


def test_a_whole_batch_of_verdicts_reads_in_one_pass(golden, tmp_path):
    """What an aggregate does. Three runs, one of each class."""
    B.write_bundle(copy.deepcopy(golden), str(tmp_path / "run-01.c6.json"))
    B.write_bundle(_measurement(golden), str(tmp_path / "run-02.c6.json"))
    B.write_bundle(_structural(golden), str(tmp_path / "run-03.c6.json"))
    paths = sorted(tmp_path.glob("run-*.c6.json"))
    assert len(paths) == 3

    counts = V.acceptance(paths)
    assert (counts.accepted, counts.rejected, counts.unknown) == (1, 2, 0)
    assert counts.complete

    keep, same = V.accepted_only(paths)
    assert len(keep) == 1
    assert same.total == 3, (
        "the counts describe the POOL, not the survivors - a figure over the "
        "filtered set still has to say what it dropped")


# ==========================================================================
# PART 3 - no figure over a batch without its acceptance count
# ==========================================================================

def test_unknown_acceptance_is_annotated_and_never_folded_into_rejected():
    """A run with no verdict file is a run whose acceptance NOBODY KNOWS.

    Counting it as rejected claims a rejection the reader never made; dropping
    it silently is the defect ruling 60 closes, one level up. Both are wrong in
    the same direction: they make the pool look fully examined.
    """
    unknown = V.Acceptance(accepted=4, rejected=0, unknown=6)
    assert unknown.total == 10
    assert not unknown.complete
    phrase = unknown.phrase()
    assert "UNKNOWN" in phrase
    assert "6" in phrase
    assert "REJECTS 6" not in phrase

    complete = V.Acceptance(accepted=4, rejected=6, unknown=0)
    assert complete.complete
    assert "UNKNOWN" not in complete.phrase()


def test_a_batch_with_no_verdict_files_reports_every_run_as_unknown(tmp_path):
    """The old batches. `evidence/batch-gated-2026-08-27/` and
    `batch-grammar-2026-08-26/` are kept as the record of what happened and are
    not re-run in place, so they carry no verdict artifact - and an aggregate
    pointed at them must say UNKNOWN rather than silently reporting a figure
    over a pool it never checked."""
    for n in range(1, 4):
        (tmp_path / ("run-%02d.c6.json" % n)).write_text("{}", encoding="utf-8")
    paths = sorted(tmp_path.glob("run-*.c6.json"))
    text, counts = V.batch_banner(paths, "bundle")
    assert (counts.accepted, counts.rejected, counts.unknown) == (0, 0, 3)
    assert "UNKNOWN" in text
    assert "no figure here may be read as covering them" in text


def test_a_malformed_verdict_file_is_unknown_and_never_accepted(
        golden, tmp_path):
    """A verdict we cannot parse tells us nothing. Guessing from it would be the
    reader's own defect wearing this module's clothes."""
    path = str(tmp_path / "run-11.c6.json")
    B.write_bundle(copy.deepcopy(golden), path)
    pathlib.Path(V.verdict_path(path)).write_text("{not json", encoding="utf-8")
    assert V.read_verdict(path) is None
    assert V.acceptance([path]).unknown == 1


def test_a_verdict_from_another_schema_is_unknown(golden, tmp_path):
    """A file at the right path with the wrong contract is not a verdict."""
    path = str(tmp_path / "run-12.c6.json")
    B.write_bundle(copy.deepcopy(golden), path)
    pathlib.Path(V.verdict_path(path)).write_text(
        json.dumps({"schema": "something.else.v9", "verdict": "ACCEPTS"}),
        encoding="utf-8")
    assert V.read_verdict(path) is None
    assert V.acceptance([path]).accepted == 0


# --------------------------------------------------------------------------
# THE GUARDRAIL. This is what catches the TENTH aggregate script, which is the
# one nobody in this session will remember to wire.
# --------------------------------------------------------------------------

# Scripts that enumerate a batch directory but compute no figure over evidence.
# NAMED, not pattern-matched: an exemption nobody can name is the thing being
# guarded against, and a regex exemption grows silently.
NOT_AGGREGATES = {
    # A negative control for render-attack-surface. It copies a slice of a batch
    # into a temp directory and MUTATES it; its only figure is over its own
    # injected cases, not over evidence.
    "render-attack-surface-negcheck.py",
}

# Both glob spellings the tree actually uses: `Path.glob("*.c6.json")` and
# `glob.glob(os.path.join(dir, "*.c6.json"))`. Matching only the first is how
# this sweep would have missed `prove-money-clauses-can-fire.py` and reported
# itself clean - which it did, before the floor below was added.
_BATCH_GLOB = re.compile(r'["\'](?:run-\*|\*)\.c6\.json["\']'
                         r'|glob\(\s*[fr]?["\']run-\*\.json["\']')

# THE FLOOR THAT STOPS THE SWEEP PASSING VACUOUSLY. `offenders == []` is
# satisfied just as well by a regex that matches NOTHING, and a sweep that
# matches nothing is a check that cannot fail. Nine scripts aggregate a batch
# today; if the count drops, the pattern has stopped matching rather than the
# tree having got cleaner.
_MIN_AGGREGATES = 9


def test_every_script_that_aggregates_a_batch_reports_acceptance():
    """RULING 60 PART 3, AS AN ENFORCEMENT ARTIFACT RATHER THAN A CONVENTION.

    Nine scripts were wired by hand. A tenth will be written, and a rule that
    lives only in a ruling is a rule that gets forgotten - `CONVENTIONS` says as
    much about every other rule in this repository. So the tree is swept: any
    script that globs a directory of run artifacts must reference
    `crucible.replay.verdict`, and this test is what fails if one does not.

    WHAT IT CANNOT SEE, stated rather than hidden (CONVENTIONS section 8 rule 9):
    a script that assembles its glob pattern at runtime, and a script that
    imports the module and never calls it. The second is why the per-script
    behaviour above is tested separately from this sweep - neither instrument
    covers the other's blind spot.
    """
    offenders, examined = [], []
    for path in sorted((REPO / "scripts").rglob("*.py")):
        if path.name in NOT_AGGREGATES:
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        if not _BATCH_GLOB.search(source):
            continue
        examined.append(path.name)
        if "crucible.replay.verdict" not in source \
                and "replay import verdict" not in source:
            offenders.append(path.name)
    assert len(examined) >= _MIN_AGGREGATES, (
        "the sweep examined only %d script(s) and expects at least %d. It has "
        "stopped matching, and an empty offender list from an empty pool is a "
        "check that cannot fail: %s" % (len(examined), _MIN_AGGREGATES, examined))
    assert offenders == [], (
        "these scripts compute a figure over a batch and never say how many of "
        "those runs the reader accepts, which is the failure ruling 60 closes: "
        "%s" % ", ".join(offenders))


def test_the_sweep_can_fail(tmp_path, monkeypatch):
    """The sweep's own strawman. A sweep aimed only at a tree that is already
    clean has never been shown to detect anything - the same argument
    `crucible/replay/offline_lint.py` makes for keeping strawman sources in the
    tree forever.
    """
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    aggregate = ('import pathlib\n'
                 'paths = sorted(pathlib.Path("evidence").glob("run-*.c6.json"))\n'
                 'print("median 2.5 across %d runs" % len(paths))\n')
    # The pool has to clear the vacuity floor, or the floor fires first and this
    # test passes on the WRONG assertion - which it did, before this line.
    for n in range(_MIN_AGGREGATES):
        (scripts / ("wired-%02d.py" % n)).write_text(
            aggregate + "from crucible.replay import verdict\n", encoding="utf-8")
    (scripts / "innocent-aggregate.py").write_text(aggregate, encoding="utf-8")

    monkeypatch.setattr(
        pathlib.Path, "rglob",
        lambda self, pat: sorted(scripts.glob(pat))
        if self.name == "scripts" else pathlib.Path.rglob(self, pat))
    with pytest.raises(AssertionError) as caught:
        test_every_script_that_aggregates_a_batch_reports_acceptance()
    message = str(caught.value)
    assert "innocent-aggregate.py" in message
    assert "never say how many of those runs the reader accepts" in message, (
        "the sweep failed for the wrong reason - this is the vacuity floor "
        "firing, not the offender check: %s" % message[:200])
    assert "wired-00.py" not in message, "a wired script was reported as an offender"


# ---------------------------------------------------------------------------
# A RUN THAT PRODUCED NO MEASUREMENT IS NOT A RUN WHOSE FIGURES MAY BE QUOTED.
#
# FOUND LIVE, 2026-08-27, evidence/smoke-reader-2026-08-27/run-03. The gate
# halted the campaign before the first episode: gcloud could not launch (exit
# 0xC0000142, STATUS_DLL_INIT_FAILED), so G7/G8 were UNEVALUABLE and the run
# was RUN_INVALID. The campaign was honest about it - it printed "no number
# from this run may be reported, INCLUDING THE ONES THAT LOOK GOOD" and exited
# 2.
#
# THE OFFLINE READER SAID **ACCEPTS, 18/18 CHECKS OK**, and the batch marker
# counted it as an accepted run beside an exit code of 2.
#
# Nothing was wrong with any check. An empty run has no exclusions, so the
# ceiling cannot fire; no breaches, so no autopsy can be missing; no episodes,
# so every per-episode check is vacuously satisfied. THIS IS THE SAME SHAPE AS
# THE CONVERGED ENUM, G4 ITSELF, AND THE ENFORCING NULL: a check that cannot
# fail on empty input is not measuring anything.
#
# CLASS IS MEASUREMENT, NOT STRUCTURAL, AND THE DISCRIMINANT DECIDES IT: the
# producer wrote a faithful document. The fix is a re-run - and, separately, a
# C6 contract that can say RUN_INVALID at all, which today it cannot.
# ---------------------------------------------------------------------------

def _empty_live_run(golden):
    """The golden bundle with its episodes removed and nothing else touched.

    Deliberately NOT hand-built: starting from the golden and emptying one
    array is what proves the emptiness is the defect rather than some other
    difference between a real bundle and a fixture.
    """
    out = copy.deepcopy(golden)
    out["episodes"] = []
    out["round_census"] = []
    out["excluded"] = []
    out["autopsies"] = []
    out["patch_proposals"] = []
    out["execution_provenance"]["mode"] = "live"
    return out


def test_a_live_run_with_no_episodes_is_refused_and_classed_measurement(golden):
    bundle = _empty_live_run(golden)
    record = V.verdict_record(I.verify_bundle(bundle))

    assert record["verdict"] == V.REJECTS, (
        "an empty live run was ACCEPTED. Every per-episode check passes "
        "vacuously on zero episodes, which is exactly why this needs its own "
        "check rather than being caught by one of the others.")
    assert record["exit_class"] == V.MEASUREMENT
    assert "E_NO_MEASUREMENT_IN_RUN" in record["measurement"]
    assert record["structural"] == [], (
        "the producer wrote a faithful document; the RUN is what is invalid")
    assert record["unclassified"] == []


def test_the_check_can_pass_so_it_is_not_always_failing(golden):
    """The control. Without it the assertion above passes on a broken check."""
    record = V.verdict_record(I.verify_bundle(golden))
    assert "E_NO_MEASUREMENT_IN_RUN" not in record["codes"], (
        "the golden bundle has episodes and must not trip the empty-run check")
