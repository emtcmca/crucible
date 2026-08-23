"""test_coverage_in_bundle.py - THE HONEST ZERO, IN THE RUN OF RECORD.

WHAT THIS FILE IS ABOUT, IN ONE SENTENCE

`clause_coverage.clauses[].episodes_fired` is one integer, and one integer
CANNOT TELL A CLAUSE NOTHING EVER REACHED FROM A CLAUSE REACHED EIGHTY-SEVEN
TIMES AND NEVER TRUE. Those are opposite findings with opposite repairs: the
first says the corpus has no trace of that shape, the second says the shape
occurs and the condition is wrong. Collapsing them is how
`inv_account_identifier_left_the_boundary` named `memo` - an argument path no
tool in `target/refund_agent` emits - and stayed at zero through 1,435 tests and
a hash freeze while four episodes scored CLEAN that should have scored BREACH
(ruling 48).

The instrument that separates them already exists (`crucible/coverage/`). It
measures the corpus, the offline script, the fixtures and the benign floor
BEFORE a run. This file is about the other half: the run of record itself, which
is the only artifact a judge or a customer ever opens, and which until now
carried the collapsed integer.

WHY THE ASSERTIONS RUN AGAINST A REAL CAMPAIGN AND NOT A HAND-BUILT DICT
------------------------------------------------------------------------
`tests/test_c6_producer.py` states the reason and it is the same reason here: a
test that validated a hand-built dict against the schema would prove that the
schema parses. Worse for this lane specifically -
`crucible.coverage.sources.evidence_bundle` HAD NEVER READ A REAL BUNDLE. It was
written from the C6 schema and the golden fixture, which is the same standing
caveat `crucible.conductor.real_gate.GcsBlobIO` carries. A function that has
only ever run against hand-authored input is a function nobody has tested, so
the live arm is exercised here against a bundle a campaign actually wrote.

THE CROSS-CHECK THAT MATTERS MOST IS `test_the_two_arms_agree_on_a_real_bundle`.
The producer counts firings while assembling the bundle, from
`verdict["_episode"]`. The instrument counts them afterwards, from
`episodes[].episode_prefix`. Those are two different code paths reading two
different serialisations of the same run, and if they disagree, one of them is
describing a run that did not happen.
"""

import copy
import json
import pathlib

import pytest

from crucible.conductor import bundle as B
from crucible.conductor import campaign as C
from crucible.coverage.matrix import (
    FIRED,
    NEVER_TRUE,
    UNREACHED,
    build_matrix,
)
from crucible.coverage.sources import evidence_bundle
from crucible.plugin.adk import ADK_AVAILABLE
from crucible.replay.integrity import verify_bundle
from crucible.replay.view import render

adk_only = pytest.mark.skipif(not ADK_AVAILABLE, reason="ADK not importable")

REPO = pathlib.Path(__file__).resolve().parent.parent


def _read(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    """ONE offline campaign, written to disk, reused by every test below.

    Offline: no model call leaves the process and no gcloud process starts. The
    target is a scripted model replaying each corpus instance's own recorded
    trace, so NOTHING HERE MEASURES PERSUASION - it measures whether the run of
    record can say which clauses were reached, which is a property of the
    bundle and not of the model.
    """
    out = tmp_path_factory.mktemp("cov") / "bundle.json"
    code = C.run(["--out", str(out)])
    c6 = pathlib.Path(C.c6_path(str(out)))
    return {"code": code, "c6": c6, "bundle": _read(c6)}


# ---------------------------------------------------------------------------
# 1. THE HONEST ZERO
# ---------------------------------------------------------------------------

@adk_only
def test_a_zero_row_says_WHICH_KIND_of_zero_it_is(run):
    """The whole lane, in one assertion.

    A row reading `episodes_fired: 0` must also say whether anything ever
    reached the clause. UNREACHED and NEVER_TRUE are the two zeros, and a reader
    handed only the integer cannot tell which repair the row is asking for.
    """
    clauses = run["bundle"]["clause_coverage"]["clauses"]
    zeros = [c for c in clauses if not c["episodes_fired"]]
    assert zeros, "no clause was dark in this run, so this test proved nothing"
    for row in zeros:
        assert "state" in row, (
            "%s reads zero and does not say which kind of zero. That is the "
            "collapsed integer this lane exists to end." % row["invariant_id"])
        assert row["state"] != FIRED
    states = {row["state"] for row in zeros}
    assert states & {UNREACHED, NEVER_TRUE}, (
        "every dark clause is in an exotic state (%s); the ordinary two are "
        "what the field is for" % sorted(states))


@adk_only
def test_the_two_zeros_are_actually_distinguished_in_this_run(run):
    """NOT A TAUTOLOGY CHECK. The offline run reaches the money clauses and
    never reaches the two `CAP_EXTERNAL_COMMS` ones, so a correct producer emits
    BOTH zeros - and a producer that stamped one constant state on every dark
    row would pass the test above and fail this one.
    """
    clauses = run["bundle"]["clause_coverage"]["clauses"]
    zeros = {c["invariant_id"]: c["state"] for c in clauses
             if not c["episodes_fired"]}
    assert len(set(zeros.values())) >= 2, (
        "every dark clause in this run carries the same state %s. Either the "
        "run is degenerate or the producer is stamping a constant."
        % sorted(set(zeros.values())))


@adk_only
def test_every_row_carries_the_three_counters_and_they_are_monotone(run):
    """fired <= evaluated <= reached <= in scope.

    True by construction in the producer, which is exactly why it is worth
    asserting: a violation means the row was assembled by something other than
    the instrument, and the three columns are then not three views of one
    measurement.
    """
    for row in run["bundle"]["clause_coverage"]["clauses"]:
        scope = row["episodes_in_scope"]
        reached = row["episodes_cap_reached"]
        evaluated = row["episodes_paths_resolvable"]
        fired = row["episodes_fired"]
        assert fired <= evaluated <= reached <= scope, (
            "%s: fired %d, evaluated %d, reached %d, in scope %d"
            % (row["invariant_id"], fired, evaluated, reached, scope))


@adk_only
def test_by_source_sums_to_the_pooled_row(run):
    """A source column that does not add up is a column that was dropped.

    The pooled row is what a reader quotes. If the per-source breakdown can
    disagree with it, the breakdown is decoration.
    """
    for row in run["bundle"]["clause_coverage"]["clauses"]:
        by_source = row["by_source"]
        for field in ("episodes_in_scope", "episodes_cap_reached",
                      "episodes_paths_resolvable", "episodes_fired"):
            assert sum(cell[field] for cell in by_source.values()) == row[field], (
                "%s: by_source %s does not sum to the pooled row"
                % (row["invariant_id"], field))


# ---------------------------------------------------------------------------
# 2. THE LIVE ARM OF THE INSTRUMENT, AGAINST A REAL BUNDLE
# ---------------------------------------------------------------------------

@adk_only
def test_the_instrument_reads_a_bundle_a_campaign_actually_wrote(run):
    """`evidence_bundle()` had never been run against a real bundle.

    It was written from the C6 schema and the golden fixture. Same caveat class
    as `GcsBlobIO`, which has also never executed. This closes it.
    """
    episodes, skipped = evidence_bundle(run["c6"])
    scoreable = [e for e in run["bundle"]["episodes"]
                 if e["verdict"]["verdict"] != "INVALID"]
    assert len(episodes) == len(scoreable), (
        "the reader found %d episodes in a bundle carrying %d scoreable ones"
        % (len(episodes), len(scoreable)))
    assert len(skipped) == len(run["bundle"]["episodes"]) - len(scoreable)
    # It read EVENTS, not just episode envelopes. A reader that returned the
    # right number of empty episodes would satisfy the count above and measure
    # nothing.
    assert sum(len(e.events) for e in episodes) > 0


@adk_only
def test_the_two_arms_agree_on_a_real_bundle(run):
    """THE CROSS-CHECK. Producer counts from `verdict["_episode"]` while
    assembling; instrument counts from `episodes[].episode_prefix` afterwards.
    Two code paths, two serialisations, one run. Disagreement means one of them
    is describing a run that did not happen.
    """
    episodes, skipped = evidence_bundle(run["c6"])
    matrix = build_matrix(source_list=(),
                          extra=[("evidence_bundle", episodes, skipped)])
    producer = {c["invariant_id"]: c for c in run["bundle"]["clause_coverage"]["clauses"]}
    for clause in matrix.objective_set.clauses:
        cell = matrix.cells[clause["id"]]["evidence_bundle"]
        row = producer[clause["id"]]
        assert cell.episodes_fired == row["episodes_fired"], clause["id"]
        assert cell.state() == row["state"], (
            "%s: instrument says %s, bundle says %s"
            % (clause["id"], cell.state(), row["state"]))
        assert cell.episodes_cap_reached == row["episodes_cap_reached"], clause["id"]


# ---------------------------------------------------------------------------
# 3. THE INTEGRITY READER
# ---------------------------------------------------------------------------

@adk_only
def test_a_real_bundle_still_passes_every_integrity_check(run):
    report = verify_bundle(run["bundle"])
    assert report.defects == [], "\n".join(str(d) for d in report.defects)
    assert all(r.status == "OK" for r in report.rows), \
        [r.name for r in report.rows if r.status != "OK"]


@adk_only
def test_the_reader_REFUSES_a_bundle_that_collapses_coverage_to_one_integer(run):
    """RED-BEFORE-GREEN, PERMANENTLY. This is the exact bundle shape the project
    shipped until today, and the reader must now name it as a defect rather than
    render it as evidence.
    """
    bundle = copy.deepcopy(run["bundle"])
    for row in bundle["clause_coverage"]["clauses"]:
        for key in ("state", "episodes_in_scope", "episodes_cap_reached",
                    "episodes_paths_resolvable", "episodes_exempted",
                    "episodes_context_missing", "events_cap_reached",
                    "by_source", "conditions"):
            row.pop(key, None)
    defects = verify_bundle(bundle).defects
    assert any(d.code == "E_COVERAGE_COLLAPSED" for d in defects), \
        [d.code for d in defects]


@adk_only
def test_the_reader_catches_a_state_that_contradicts_its_own_counters(run):
    """The state is RECOMPUTABLE FROM THE ROW, so a producer that stamps a
    flattering state on an unflattering row is caught. This is the strongest
    check available here, and section 4 of the memo says why it is not strong
    enough on its own.
    """
    bundle = copy.deepcopy(run["bundle"])
    row = next(c for c in bundle["clause_coverage"]["clauses"]
               if c["state"] == UNREACHED)
    row["state"] = NEVER_TRUE          # a clause nothing reached, called healthy
    defects = verify_bundle(bundle).defects
    assert any(d.code == "E_COVERAGE_STATE_DISAGREES" for d in defects), \
        [d.code for d in defects]


@adk_only
def test_the_reader_catches_counters_that_are_not_nested(run):
    """fired <= evaluated <= reached <= in scope holds BY CONSTRUCTION, which is
    exactly why it is checked: a violation cannot be a run, so it is two arms
    writing four numbers that did not come from one measurement.

    Written because E_COVERAGE_NOT_MONOTONE would otherwise be a defect code no
    test has ever seen fire - a check nobody has proved can fail.
    """
    bundle = copy.deepcopy(run["bundle"])
    row = next(c for c in bundle["clause_coverage"]["clauses"]
               if c["state"] == UNREACHED)
    row["episodes_paths_resolvable"] = row["episodes_cap_reached"] + 1
    defects = verify_bundle(bundle).defects
    assert any(d.code == "E_COVERAGE_NOT_MONOTONE" for d in defects), \
        [d.code for d in defects]


@adk_only
def test_the_reader_catches_a_source_column_that_does_not_add_up(run):
    bundle = copy.deepcopy(run["bundle"])
    row = next(c for c in bundle["clause_coverage"]["clauses"] if c["by_source"])
    cell = next(iter(row["by_source"].values()))
    cell["episodes_cap_reached"] += 1
    defects = verify_bundle(bundle).defects
    assert any(d.code == "E_COVERAGE_SOURCES_DISAGREE" for d in defects), \
        [d.code for d in defects]


def test_the_reader_derives_the_state_the_same_way_the_instrument_does():
    """TWO IMPLEMENTATIONS, PINNED MECHANICALLY RATHER THAN BY COMMENT.

    `crucible.coverage.matrix.ClauseCounters.state` owns the rule.
    `crucible.replay.integrity._coverage_state` restates it, because
    `crucible/replay` is the judge's reproduction path and its documented
    property is that IT NEEDS NOTHING - importing the coverage package would
    pull `crucible.tripwire.objective_set` and a capability-manifest read into
    an offline viewer, and `offline_lint` walks only `crucible/replay`, so it
    would not see the coupling arrive.

    A restatement guarded by a comment is a restatement that drifts.
    `BENIGN_DENOMINATOR` carried 24 for a day after ruling 43 moved it and the
    whole suite stayed green, because nothing compared it to anything. So this
    drives BOTH implementations over every combination that can reach each of
    the five states, including the orderings where two branches compete.
    """
    from crucible.coverage.matrix import ClauseCounters
    from crucible.replay.integrity import _coverage_state

    seen = set()
    for scope in (0, 3):
        for reached in (0, 2):
            for evaluated in (0, 1):
                for struck in (0, 1):
                    for ctx in (0, 1):
                        counters = ClauseCounters()
                        counters.episodes_in_scope = scope
                        counters.episodes_cap_reached = reached
                        counters.episodes_paths_resolvable = evaluated
                        counters.episodes_fired = struck
                        counters.episodes_context_missing = ctx
                        row = {
                            "episodes_in_scope": scope,
                            "episodes_cap_reached": reached,
                            "episodes_paths_resolvable": evaluated,
                            "episodes_fired": struck,
                            "episodes_context_missing": ctx,
                        }
                        assert _coverage_state(row) == counters.state(), row
                        seen.add(counters.state())
    assert seen == {"FIRED", "NEVER_TRUE", "PATH_NEVER_PRESENT",
                    "CONTEXT_FIELD_MISSING", "UNREACHED"}, (
        "the sweep never reached %s, so agreement there is untested"
        % sorted({"FIRED", "NEVER_TRUE", "PATH_NEVER_PRESENT",
                  "CONTEXT_FIELD_MISSING", "UNREACHED"} - seen))


# ---------------------------------------------------------------------------
# 4. THE RENDER
# ---------------------------------------------------------------------------

@adk_only
def test_the_render_makes_a_dark_clause_impossible_to_skip_past(run):
    """A reader scanning for a breach rate must not be able to slide past the
    fact that a clause never fired. The state goes ON THE ROW, and the count of
    dark clauses is stated in the same block as the coverage fraction.
    """
    text = render(run["bundle"], verify_bundle(run["bundle"]))
    dark = [c for c in run["bundle"]["clause_coverage"]["clauses"]
            if not c["episodes_fired"]]
    assert dark, "this run had no dark clause, so the render proved nothing"
    for row in dark:
        assert row["invariant_id"] in text
        assert row["state"] in text, (
            "%s is dark and its state %s is nowhere in the render"
            % (row["invariant_id"], row["state"]))
    assert "NEVER FIRED" in text


@adk_only
def test_the_render_prints_the_reach_NUMBERS_and_not_only_the_word(run):
    """`fired 0` next to `reached 5` is a different sentence from `fired 0` next
    to `reached 0`, and the render has to print BOTH NUMBERS for the sentence to
    exist at all.

    THIS TEST WAS FIRST WRITTEN AS `assert "reached" in text` AND IT PASSED
    AGAINST THE OLD RENDERER, because the section heading has always read
    "which clauses were ever reached". A check that greps for a word the prose
    already contains is a check that cannot fail - the house defect, arriving
    inside the file written to end a different instance of it. So the assertion
    is on the clause's OWN ROW carrying its OWN counters.
    """
    text = render(run["bundle"], verify_bundle(run["bundle"]))
    row = next(c for c in run["bundle"]["clause_coverage"]["clauses"]
               if not c["episodes_fired"] and c["episodes_cap_reached"])
    candidates = [ln for ln in text.splitlines()
                  if row["invariant_id"] in ln and row["state"] in ln]
    assert candidates, \
        "%s has no line in the render carrying its state" % row["invariant_id"]
    # ANY of them, not the first. The clause's name and state also appear in the
    # integrity report's NEVER FIRED note, which is a different sentence in a
    # different section - a `next()` here read that line and reported the table
    # as missing a number the table prints.
    assert any(str(row["episodes_cap_reached"]) in ln.split()
               for ln in candidates), (
        "%s was reached %d time(s) and no line of the render prints the "
        "number:\n%s" % (row["invariant_id"], row["episodes_cap_reached"],
                         "\n".join(candidates)))


# ---------------------------------------------------------------------------
# 5. THE GOLDEN FIXTURES
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["C6-evidence_bundle.valid.json",
                                  "C6-evidence_bundle.NOTHING_TO_SAY.json"])
def test_the_golden_bundles_carry_the_new_shape(name):
    """A golden fixture in the old shape is a second definition of the field,
    and the one a reader is likelier to copy."""
    bundle = _read(REPO / "contracts" / "golden" / name)
    for row in bundle["clause_coverage"]["clauses"]:
        assert "state" in row, row["invariant_id"]
        assert "by_source" in row, row["invariant_id"]
        assert row["episodes_fired"] <= row["episodes_paths_resolvable"] \
            <= row["episodes_cap_reached"] <= row["episodes_in_scope"]
    assert B.validate_bundle(bundle) == []
