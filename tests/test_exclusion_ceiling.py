"""The exclusion ceiling, its floor, and the two denominators it is a share of.

WHAT WAS BROKEN
---------------
`measurement-spec.md` 5.1 puts the ceiling at 5% of what a round attempted, and
`attacks_per_round` is FROZEN AT 6. The smallest non-zero share a round can
express is therefore 1/6 = 16.7%, which is 3.3x the ceiling, so the per-round
rate test was satisfiable ONLY at exactly zero exclusions. One target crash
marked the round INCOMPLETE and demanded a re-run.

This repository already has the rule that names that defect - a check that cannot
fail is not measuring anything (`measurement-spec.md:813`, CONVENTIONS 8.2) - and
a check that can only fail is the same instrument with the wires crossed.

WHY THE OLD PREDICATE IS TRANSCRIBED INTO THIS FILE
---------------------------------------------------
`_old_per_round_rule` below is the exact expression this lane removed. Without it
"this case used to pass and now fails" is a sentence in a commit message, which
is to say an unchecked claim about code nobody can run any more. With it, both
directions of the change are ASSERTED: every case that swapped verdict says so
in an assertion, and if someone later re-tightens the rule back to where it was,
these tests fail rather than quietly agreeing with themselves.

A test suite that only proves the new code agrees with itself proves nothing.
"""

import copy
import json
import pathlib

import pytest

from crucible.conductor.conductor import RoundRecord
from crucible.replay.integrity import (
    EXCLUSION_CEILING_PCT,
    EXCLUSION_RATE_MIN_N,
    EXCLUSION_SUBFLOOR_ALLOWANCE,
    REPORTED_OUTCOME,
    _check_exclusions,
    exclusion_ceiling_exceeded,
    exclusion_rate_applicable,
    verify_bundle,
)

REPO = pathlib.Path(__file__).resolve().parent.parent
GOLDEN = REPO / "contracts" / "golden" / "C6-evidence_bundle.valid.json"

# The frozen round size (CONVENTIONS section 4). Named rather than spelled 6 in
# forty places, and asserted against the conductor's own default below.
FROZEN_ATTACKS_PER_ROUND = 6


def _old_per_round_rule(excluded, attempted, outcome):
    """THE PREDICATE THIS LANE REPLACED, transcribed verbatim.

    `crucible/replay/integrity.py:736-738` at 9844dd6:

        if attempted and dropped is not None \
                and dropped * 100 > attempted * EXCLUSION_CEILING_PCT \
                and row.get("outcome") != "INCOMPLETE":

    Per round, no floor, no run-level denominator, and INCOMPLETE the only
    outcome that exempted a row. The `5` is written out because this is a
    transcription of a dead line, not a second use of the live constant - if the
    ceiling ever moves, this function must keep saying what the old one did.
    """
    return bool(attempted) and excluded * 100 > attempted * 5 \
        and outcome != "INCOMPLETE"


# --------------------------------------------------------------------------
# Calling the checker with only what it reads.
# --------------------------------------------------------------------------

def check(rows):
    """`rows` is a list of (round_index, attempted, scorable, excluded, outcome).

    The named ledger is GENERATED from the census counts, so these cases exercise
    the ceiling rather than tripping E_EXCLUSION_LEDGER_SHORT on the way to it.
    """
    census, ledger = [], []
    for idx, attempted, scorable, dropped, outcome in rows:
        census.append({"round_index": idx, "attempted": attempted,
                       "scorable": scorable, "excluded": dropped,
                       "outcome": outcome})
        for k in range(dropped):
            ledger.append({"instance_id": "atk_r%02dn%02d" % (idx, k),
                           "round_index": idx, "reason": "target_fault"})
    defects = []
    row = _check_exclusions({"round_census": census, "excluded": ledger},
                            defects)
    return row, defects


def codes(defects):
    return [d.code for d in defects]


def full_run(excluded_by_round, outcome=REPORTED_OUTCOME):
    """Six SCORED rounds of six - a run that reached the frozen round cap."""
    return [(i + 1, FROZEN_ATTACKS_PER_ROUND,
             FROZEN_ATTACKS_PER_ROUND - e, e, outcome)
            for i, e in enumerate(excluded_by_round)]


# --------------------------------------------------------------------------
# THE TWO CONSTANTS AND WHERE THEY COME FROM
# --------------------------------------------------------------------------

def test_the_floor_is_the_smallest_denominator_that_survives_one_exclusion():
    """EXCLUSION_RATE_MIN_N is DERIVED - ceil(100 / ceiling) - and this is the
    property it is derived FOR, asserted rather than restated."""
    assert EXCLUSION_RATE_MIN_N == -(-100 // EXCLUSION_CEILING_PCT) == 20
    n = EXCLUSION_RATE_MIN_N
    assert 1 * 100 <= n * EXCLUSION_CEILING_PCT, (
        "one exclusion at the floor must NOT be past the ceiling")
    assert 1 * 100 > (n - 1) * EXCLUSION_CEILING_PCT, (
        "one exclusion one below the floor must be, or the floor is too high")


def test_the_subfloor_allowance_is_the_ceilings_own_value_at_the_floor():
    """The piecewise rule is CONTINUOUS AT THE JOIN. At exactly n = the floor the
    rate test and the count substitute must return the same verdict for every
    count, or the fix has introduced a discontinuity of its own."""
    assert EXCLUSION_SUBFLOOR_ALLOWANCE == 1
    n = EXCLUSION_RATE_MIN_N
    for e in range(0, n + 1):
        rate = e * 100 > n * EXCLUSION_CEILING_PCT
        count = e > EXCLUSION_SUBFLOOR_ALLOWANCE
        assert rate == count, "the two rules disagree at n=%d, e=%d" % (n, e)


def test_the_frozen_round_size_sits_below_the_floor_which_is_the_whole_defect():
    """Not an incidental fact. It is the reason the per-round rate test could
    never be satisfied, and it is why the substitute below the floor exists
    instead of a bare INAPPLICABLE: 6 can never grow into 20."""
    assert FROZEN_ATTACKS_PER_ROUND < EXCLUSION_RATE_MIN_N
    assert not exclusion_rate_applicable(FROZEN_ATTACKS_PER_ROUND)
    assert _old_per_round_rule(1, FROZEN_ATTACKS_PER_ROUND, "SCORED"), (
        "the old rule fired on ONE exclusion in a frozen round - that is the "
        "tripwire this lane was opened to remove")


def test_the_conductors_default_round_size_is_the_one_reasoned_about():
    """If `attacks_per_round` ever leaves 6, the sentence above stops being true
    and this file must be re-derived rather than re-read."""
    import inspect

    from crucible.conductor.conductor import Conductor
    default = inspect.signature(Conductor.__init__) \
        .parameters["attacks_per_round"].default
    assert default == FROZEN_ATTACKS_PER_ROUND


# --------------------------------------------------------------------------
# PER ROUND - the two cases that changed verdict
# --------------------------------------------------------------------------

def test_one_crash_in_a_round_of_six_no_longer_invalidates_the_round():
    """FAILED UNDER THE OLD RULE, PASSES NOW. The headline case: a single target
    fault used to force a re-run of the whole round."""
    assert _old_per_round_rule(1, 6, "SCORED"), "old rule must have fired"

    row, defects = check([(1, 6, 5, 1, "SCORED")])
    assert codes(defects) == []
    assert row.status == "OK"


def test_a_scored_round_that_hides_five_scorable_episodes_is_refused():
    """PASSED UNDER THE OLD RULE, FAILS NOW.

    Zero exclusions, so the old ceiling test never looked at this row at all -
    and the old code had no other opinion about a census row's outcome. Under the
    pooled run-level ceiling this is the DODGE: relabel a round and its
    denominator leaves the pool the run rate is computed over. It is refused at
    the row, so the exemption cannot be bought with a label.
    """
    assert not _old_per_round_rule(0, 6, "UNSCORED"), (
        "the old rule was silent here, which is the point")

    row, defects = check([(1, 6, 6, 0, "UNSCORED")])
    assert codes(defects) == ["E_CENSUS_OUTCOME_DISAGREES"]
    assert "INCOMPLETE" in str(defects[0]), (
        "the message must send the reader to the outcome that DOES mean "
        "'not reported', rather than only refusing this one")


def test_an_empty_round_that_calls_itself_scored_is_refused():
    """ALSO PASSED UNDER THE OLD RULE. `if attempted and ...` skipped every row
    with a zero denominator, so a round that attempted nothing and declared
    itself SCORED contributed an empty population to the reported figures."""
    assert not _old_per_round_rule(0, 0, "SCORED")

    row, defects = check([(1, 0, 0, 0, "SCORED")])
    assert codes(defects) == ["E_CENSUS_OUTCOME_DISAGREES"]


def test_two_crashes_in_a_round_of_six_are_still_past_the_ceiling():
    """The substitute is a CHECK, not an amnesty. Both rules fire here, and the
    message has to say which denominator it fired on.

    BOTH CODES, and that is not redundancy. Amended 2026-08-22 when the pooled
    ceiling gained the same sub-floor substitute as the per-round one. On a
    one-round bundle the round and the run are the same six episodes, so the two
    tests read the same numbers - but they carry DIFFERENT VERDICTS. Per round:
    this ROUND is INCOMPLETE and must be re-run. Pooled: no rate may be quoted
    from the RUN at all. Collapsing them would lose the second sentence.
    """
    assert _old_per_round_rule(2, 6, "SCORED")

    row, defects = check([(1, 6, 4, 2, "SCORED")])
    assert codes(defects) == ["E_EXCLUSION_CEILING", "E_EXCLUSION_CEILING_RUN"]
    text = str(defects[0])
    assert "PER-ROUND DENOMINATOR" in text
    assert "below the n=%d floor" % EXCLUSION_RATE_MIN_N in text
    assert "at most %d exclusion" % EXCLUSION_SUBFLOOR_ALLOWANCE in text
    assert row.status == "FAIL"


def test_at_or_above_the_floor_the_rate_test_is_the_one_that_runs():
    """A denominator that can resolve a rate gets the rate, and the message says
    so - a reader must never have to guess which of the two fired."""
    row, defects = check([(1, 24, 23, 1, "SCORED")])
    assert codes(defects) == [], "1 of 24 is 4.2%, inside the ceiling"

    # A single round of 24 IS the whole reported run here, so the pooled test
    # fires alongside the per-round one - correctly, and on its own denominator.
    row, defects = check([(1, 24, 22, 2, "SCORED")])
    assert codes(defects) == ["E_EXCLUSION_CEILING", "E_EXCLUSION_CEILING_RUN"]
    text = str(defects[0])
    assert "PER-ROUND DENOMINATOR" in text
    assert "at or above the n=%d floor" % EXCLUSION_RATE_MIN_N in text
    assert "POOLED RUN DENOMINATOR" in str(defects[1])


@pytest.mark.parametrize("outcome", ["INCOMPLETE", "UNSCORED", "INVALID"])
def test_a_round_that_already_reports_nothing_is_exempt(outcome):
    """All three mean "no figure is taken from this round", which is what the
    ceiling is trying to force. UNSCORED here carries 0 scorable, so it is not
    the relabelling dodge - it is a round where nothing survived."""
    row, defects = check([(1, 6, 0, 6, outcome)])
    assert codes(defects) == []


def test_an_all_crash_run_is_still_readable():
    """36 attempted, 36 lost, every round UNSCORED - which this build has already
    produced once. It must not become a bundle the viewer REFUSES TO OPEN: the
    census and the named ledger are exactly the evidence a reader needs, and
    there is no rate in it to protect."""
    row, defects = check(full_run([6] * 6, outcome="UNSCORED"))
    assert codes(defects) == []


# --------------------------------------------------------------------------
# POOLED ACROSS THE RUN - what the loosened per-round test gives back
# --------------------------------------------------------------------------

def test_one_exclusion_in_a_full_run_passes_and_two_fail():
    """The resolution claim, checked rather than asserted in prose: six SCORED
    rounds pool to 36 attempted, where 1/36 = 2.8% is inside a 5% ceiling and
    2/36 = 5.6% is outside it."""
    row, defects = check(full_run([1, 0, 0, 0, 0, 0]))
    assert codes(defects) == []

    row, defects = check(full_run([1, 1, 0, 0, 0, 0]))
    assert codes(defects) == ["E_EXCLUSION_CEILING_RUN"]
    text = str(defects[0])
    assert "POOLED RUN DENOMINATOR" in text
    assert "2 of 36" in text


def test_flakiness_spread_one_to_a_round_clears_every_round_and_fails_the_run():
    """THE CASE THE POOLED TEST EXISTS FOR, and the reason loosening the
    per-round test does not simply hand the ceiling away. Five rounds losing one
    instance each are individually inside the sub-floor allowance and pool to
    5/30 = 16.7%."""
    rows = full_run([1, 1, 1, 1, 1, 0])
    for _, attempted, _, dropped, outcome in rows:
        assert not exclusion_ceiling_exceeded(dropped, attempted), (
            "no round may trip on its own, or this proves nothing")

    row, defects = check(rows)
    assert codes(defects) == ["E_EXCLUSION_CEILING_RUN"]
    assert "5 of 36" in str(defects[0])


def test_the_pooled_denominator_is_the_reported_one():
    """A round that says it reports nothing contributes no denominator. Here two
    INCOMPLETE rounds carry five exclusions between them and the run's four
    reported rounds are clean - the run's figures rest on 24 attempted, which is
    the population a reader is being asked to believe."""
    rows = full_run([0, 0, 0, 0])
    rows += [(5, 6, 3, 3, "INCOMPLETE"), (6, 6, 4, 2, "INCOMPLETE")]
    row, defects = check(rows)
    assert codes(defects) == []
    assert "run pooled 0/24 over 4 reported round(s)" in row.note
    assert "2 marked INCOMPLETE" in row.note, (
        "the withheld rounds must still be visible in the row, or dropping them "
        "from the denominator is the silent exclusion this ledger prevents")


def test_the_pooled_test_is_inapplicable_below_the_floor_and_prints_that():
    """A run that halted early has fewer than 20 reported instances and no
    resolvable rate. INAPPLICABLE IS PRINTED. A check that quietly stops running
    is how a boundary rots."""
    row, defects = check(full_run([0, 0]))            # 12 attempted
    assert codes(defects) == []
    assert "INAPPLICABLE below n=%d" % EXCLUSION_RATE_MIN_N in row.note
    assert "counts may be quoted from this run, a rate may not" in row.note


def test_three_rounds_losing_one_each_is_now_caught_by_the_pooled_subfloor():
    """THIS TEST WAS WRITTEN THE OTHER WAY UP, AND SAID SO.

    The lane that built the piecewise rule applied the floor to the pooled test
    but not the sub-floor SUBSTITUTE, leaving three reported rounds at one
    exclusion each - 3 of 18, 16.7% - firing nothing: each round sat inside the
    per-round allowance and the run pool sat below the floor. It pinned that gap
    as the widest in the rule and named this test as the one that must change if
    a coordinator ever closed it.

    Closed 2026-08-22. The lane's own argument for refusing a bare INAPPLICABLE
    per round is that a check which can never fire is the same defect wearing
    the other mask; a run that halts short sits below the floor for exactly the
    same reason a round does, and PARTIAL and halted runs are both explicitly
    publishable. So the pooled test degrades the same way, to the same derived
    allowance - CONTINUOUS with the rate test rather than a second threshold,
    because the rate test permits exactly one exclusion everywhere from n=20 to
    n=39 and only reaches two at n=40.
    """
    row, defects = check(full_run([1, 1, 1]))
    assert codes(defects) == ["E_EXCLUSION_CEILING_RUN"]
    text = str(defects[0])
    assert "3 exclusion(s) across 18 attempted" in text
    assert "below the rate floor of %d" % EXCLUSION_RATE_MIN_N in text
    assert "at most %d" % EXCLUSION_SUBFLOOR_ALLOWANCE in text
    assert row.status == "FAIL"


def test_the_loosest_the_rule_gets_is_pinned_here_rather_than_left_to_be_found():
    """A KNOWN LIMIT, ASSERTED SO IT CANNOT DRIFT INTO A SURPRISE.

    With the pooled sub-floor in place the widest surviving gap is a run of ONE
    reported round that lost one instance: 1 of 6, 16.7%, and nothing fires.

    THIS ONE IS NOT CLOSEABLE AT n=6, and that is the honest statement rather
    than an oversight. The allowance is derived - it is the number of exclusions
    the rate test itself permits at the floor - and lowering it to zero restores
    the original defect exactly: a single crash anywhere invalidates the run.
    The rate is only unresolvable here because `attacks_per_round` is frozen at
    6, three times below the floor a 5% rate needs. Raising the round size is
    the only thing that would shrink this gap, and it is frozen into the D2 run
    manifest.

    What stops it being silent is the row, which prints the pooled figure beside
    the word INAPPLICABLE.
    """
    row, defects = check(full_run([1]))
    assert codes(defects) == []
    assert "run pooled 1/6 over 1 reported round(s)" in row.note
    assert "INAPPLICABLE below n=%d" % EXCLUSION_RATE_MIN_N in row.note


def test_the_per_round_inapplicability_is_printed_too():
    """Both halves of the piecewise rule are named in the row, with how many
    rounds each covers."""
    row, defects = check(full_run([0] * 6))
    assert "per-round rate test applies to 0 of 6 round(s)" in row.note
    assert "INAPPLICABLE below n=%d on the other 6" % EXCLUSION_RATE_MIN_N \
        in row.note


def test_the_old_checks_still_bite():
    """The census arithmetic, the named-instance requirement and the orphan check
    were not what was broken, and nothing here may have loosened them."""
    census = [{"round_index": 1, "attempted": 6, "scorable": 6, "excluded": 1,
               "outcome": "SCORED"}]
    defects = []
    _check_exclusions({"round_census": census,
                       "excluded": [{"instance_id": "atk_a", "round_index": 4,
                                     "reason": "quota_abort"}]}, defects)
    assert set(codes(defects)) == {"E_CENSUS_ARITHMETIC",
                                   "E_EXCLUSION_LEDGER_SHORT",
                                   "E_EXCLUSION_ORPHAN"}


# --------------------------------------------------------------------------
# THE PRODUCER - INCOMPLETE is reachable now, and by the SAME rule
# --------------------------------------------------------------------------

def record_with(faults=0, invalid=0, breaches=0, clean=None, n=6):
    """A RoundRecord carrying `n` verdicts of the requested kinds."""
    clean = n - faults - invalid - breaches if clean is None else clean
    verdicts = []
    verdicts += [{"verdict": "CLEAN", "target_fault": True}] * faults
    verdicts += [{"verdict": "INVALID"}] * invalid
    verdicts += [{"verdict": "BREACH", "breach": True}] * breaches
    verdicts += [{"verdict": "CLEAN"}] * clean
    return RoundRecord(round_index=1, verdicts=verdicts)


def test_the_conductor_and_the_checker_read_one_copy_of_the_rule():
    """Not "they agree today" - they are the same function. The bug being fixed
    is that the conductor carried an outcome whose defining test lived in another
    file and had never been evaluated against a denominator."""
    for n in range(0, 41):
        for e in range(0, n + 1):
            record = record_with(faults=e, n=n)
            assert record.attempted == n
            assert record.excluded == e
            assert record.ceiling_exceeded == exclusion_ceiling_exceeded(e, n)


def test_a_round_that_loses_two_of_six_is_INCOMPLETE_at_the_producer():
    """INCOMPLETE has been a legal value of `RoundRecord.outcome` since the file
    was written and no code path could reach it. This is the path."""
    result = run_campaign([["fault", "fault", None, None, None, None]])
    assert result.rounds[0].outcome == "INCOMPLETE"
    assert result.rounds[0].excluded == 2
    assert result.rounds[0].attempted == 6


def test_a_round_that_loses_one_of_six_is_SCORED():
    """The other side of the same wire. If this reads INCOMPLETE the producer has
    the tripwire the checker just lost."""
    result = run_campaign([["fault", None, None, None, None, None]])
    assert result.rounds[0].outcome == "SCORED"


def test_a_round_that_loses_everything_is_UNSCORED_not_INCOMPLETE():
    """PRECEDENCE, and it is an argument rather than an ordering: UNSCORED is the
    stronger statement about the same fact. INCOMPLETE means "there are figures
    here and you may not report them"; a round with nothing scorable has no
    figures to withhold."""
    result = run_campaign([["fault"] * 6])
    assert result.rounds[0].outcome == "UNSCORED"


def test_an_incomplete_round_does_not_count_toward_convergence():
    """A round that must be RE-RUN, NOT REPORTED may not be counted toward the
    three consecutive dry rounds that declare a campaign converged - otherwise
    flakiness ENDS the campaign, which is the strongest available form of
    "turns flakiness into apparent hardening"."""
    plan = [["fault", "fault", None, None, None, None]] * 3
    result = run_campaign(plan)
    assert [r.outcome for r in result.rounds] == ["INCOMPLETE"] * 6
    assert not any(r.dry for r in result.rounds)
    assert result.status == "PARTIAL", (
        "three INCOMPLETE rounds with no breach must not read as converged")


def test_three_clean_rounds_with_one_fault_each_still_converge():
    """And the loosening is real at the producer too: one crash a round no longer
    stops the campaign from reaching the dry streak it earned."""
    plan = [["fault", None, None, None, None, None]] * 3
    result = run_campaign(plan)
    assert all(r.outcome == "SCORED" for r in result.rounds)
    assert result.status == "converged"


def run_campaign(plan):
    """A campaign whose rounds are MIXED - two crashes and four clean episodes in
    the same round is the case the frozen round size makes interesting, and the
    stubs in `tests/test_conductor_loop.py` drive whole rounds at a time.

    The collaborators are imported from that file rather than re-declared: they
    are the conductor's test doubles, and a second set would be testing a
    slightly different conductor.
    """
    from crucible.governor import Budget, BudgetGovernor
    from tests.test_conductor_loop import (
        HASHES,
        PASS,
        SEEDS,
        StubArmorer,
        StubCoroner,
        StubRed,
        episode_for,
        scorer,
    )
    from crucible.conductor import Conductor

    state = {"episodes": 0}

    def run_episode(attack, policy):
        idx, pos = divmod(state["episodes"], 6)
        state["episodes"] += 1
        kind = plan[min(idx, len(plan) - 1)][pos]
        return episode_for(attack, breach=(kind == "breach"),
                           fault=(kind == "fault"), invalid=(kind == "invalid"))

    return Conductor(
        red=StubRed(), coroner=StubCoroner(), armorer=StubArmorer(),
        governor=BudgetGovernor(Budget(usd_cap=160.0, token_cap=10 ** 9,
                                       round_cap=6, call_cap=1000)),
        run_episode=run_episode, score=scorer,
        benign_gate=lambda c: PASS, promote=lambda c, r: True,
        hashes=HASHES, seeds=SEEDS,
        run_id="run_20260822_120000_abc123").run({})


# --------------------------------------------------------------------------
# END TO END - the whole reader, on a real bundle
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def golden():
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_the_c6_golden_bundle_is_accepted_and_its_row_states_both_denominators(
        golden):
    report = verify_bundle(golden)
    assert report.ok, [str(d) for d in report.defects]
    row = [r for r in report.rows if r.check == "EXCLUSIONS"][0]
    assert row.status == "OK"
    assert "run pooled 0/12 over 2 reported round(s)" in row.note
    assert "INAPPLICABLE" in row.note


def test_the_whole_reader_refuses_a_run_that_pooled_past_the_ceiling(golden):
    """The fixture's own round 3 carries two exclusions and is marked INCOMPLETE.
    Spread those two across two SCORED rounds of a full six-round run and no
    round trips on its own, while the run does."""
    damaged = copy.deepcopy(golden)
    damaged["round_census"] = [
        {"round_index": i + 1, "attempted": 6, "scorable": 6 - e,
         "excluded": e, "outcome": "SCORED"}
        for i, e in enumerate([1, 1, 0, 0, 0, 0])]
    for entry, idx in zip(damaged["excluded"], (1, 2)):
        entry["round_index"] = idx

    report = verify_bundle(damaged)
    assert "E_EXCLUSION_CEILING_RUN" in codes(report.defects), \
        [str(d) for d in report.defects]
    assert not report.ok
