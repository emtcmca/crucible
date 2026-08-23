"""test_strawman_tool_identity.py - the strawman that stopped being wrong.

WHY THIS FILE EXISTS, AND IT IS NOT ABOUT ONE TUPLE

`crucible/tripwire/strawman.py` ships seven deliberately-wrong oracles and
`--selftest` reports "all seven caught" on every boot. `caught` is computed as
`all(not outcome.ok for kb in must_fail)` - THE ANSWER KEY ONLY ASKS A STRAWMAN
TO BE WRONG. It never asks it to be wrong FOR THE REASON ITS DOCSTRING CLAIMS.

So an oracle that returns CLEAN unconditionally is "caught" by every expectation
in the suite, and it is caught for exactly the same reason `empty_objective_set`
is caught: it says CLEAN where the key says BREACH. The two are then the same
strawman under two names, and one of the seven has stopped measuring anything
while the boot self-test keeps printing that it works.

That is what happened to `tool_identity_only` on 2026-08-23. Its denylist named
`transfer_funds`, a tool from the pre-migration synthetic vocabulary. The
vocabulary migration re-authored every golden trace into the target's real tool
names, `transfer_funds` left the corpus, and the denylist went from matching
three executed events to matching zero - silently, because the only question
anyone asked it was "is it still wrong?"

THE THREE PROPERTIES THIS FILE PINS, none of which the answer key can express:

  1  IT FIRES. `tool_identity_only` returns BREACH on at least one REAL executed
     event - an event in the target's own vocabulary, from a trace the target
     could produce. A judge that fires on nothing is not a judge.
  2  IT IS NOT `empty_objective_set`. Its verdicts differ from the always-CLEAN
     strawman on at least one trace. Two strawmen that agree everywhere are one
     strawman.
  3  IT STILL MISSES WHAT IT MUST MISS. Every fixture in
     `TOOL_IDENTITY_MUST_FAIL` is still got wrong. THE FIXTURES MOVE, THE ANSWER
     KEY DOES NOT: property 1 is not allowed to buy itself a weakened
     expectation.

Plus the drift guard itself, and a proof that each guard can fail - because a
guard added to catch a check that could not fail is worth nothing if it cannot
fail either.
"""

import json
import pathlib

import pytest

from crucible.tripwire import strawman
from crucible.tripwire.model import Episode, bind_at_load
from crucible.tripwire.objective_set import _frozen_declarations, load_objective_set

REPO = pathlib.Path(__file__).resolve().parent.parent
GOLDEN = REPO / "tests" / "golden_traces"
OBJECTIVE_SET = REPO / "contracts" / "objective_set.v1.json"


def _wire_trace_paths():
    """Every wire-shape trace document in the repo, by explicit glob.

    `pathlib.glob` ON A MISSING DIRECTORY RETURNS EMPTY RATHER THAN RAISING, so
    a renamed directory would make every loop below pass over nothing and this
    whole file would go green by looking at zero traces. `test_the_trace_loader_
    reaches_the_traces_it_claims_to` is the floor that makes that fail instead.
    """
    return sorted(
        list((GOLDEN / "benign").glob("BF*.json"))
        + list((GOLDEN / "attacks").glob("AT*.json"))
        + list((GOLDEN / "known_bad").glob("KB*.json"))
        + list(GOLDEN.glob("T*.json")))


def _episodes():
    """(stem, Episode) for every trace that carries one.

    KB5 and KB9 carry no `episode` block at all - they are known-bads for the
    WARDEN and the LINTER - and are skipped by absence, not by name.
    """
    objective_set = load_objective_set(OBJECTIVE_SET)
    out = []
    for path in _wire_trace_paths():
        raw = bind_at_load(json.loads(path.read_text(encoding="utf-8")),
                           objective_set.hash)
        if "episode" not in raw:
            continue
        out.append((path.stem, Episode.from_dict(raw["episode"])))
    return objective_set, out


def test_the_trace_loader_reaches_the_traces_it_claims_to():
    """The floor under every loop in this file. A loop over an empty list passes."""
    paths = _wire_trace_paths()
    assert len(paths) >= 18, (
        "the trace loader found %d documents under %s. Every other assertion in "
        "this file is a loop, and a loop over an empty list PASSES."
        % (len(paths), GOLDEN))
    _objective_set, episodes = _episodes()
    assert len(episodes) >= 16, [stem for stem, _ in episodes]


# ---------------------------------------------------------------------------
# 1  IT FIRES
# ---------------------------------------------------------------------------

def test_tool_identity_only_fires_on_a_real_executed_event():
    """RED ON `main` @ 4c6bfe3: zero of 18 traces returned BREACH.

    `FORBIDDEN_TOOL_NAMES` named `transfer_funds`, which no trace in the repo
    contains any more. The oracle could not reach BREACH from any input the
    harness can produce, and `--selftest` reported it caught anyway.
    """
    objective_set, episodes = _episodes()
    fired = [stem for stem, episode in episodes
             if strawman.tool_identity_only(episode, objective_set).verdict == "BREACH"]
    assert fired, (
        "tool_identity_only returned BREACH on NONE of the %d traces in the "
        "repo. Its docstring claims it 'keys on which tool ran'; a denylist that "
        "matches no tool any trace runs demonstrates nothing, and it is caught by "
        "the answer key for the same reason empty_objective_set is."
        % len(episodes))


def test_the_fire_guard_can_fail(monkeypatch):
    """Point the denylist at a DECLARED but never-executed tool and the guard
    above must go red. Without this the fire guard is itself unfalsifiable."""
    declared = {t["tool_fqname"].rsplit(".", 1)[-1] for t in _frozen_declarations().tools}
    assert "lookup_order" in declared
    monkeypatch.setattr(strawman, "FORBIDDEN_TOOL_NAMES", ("lookup_order",))
    objective_set, episodes = _episodes()
    fired = [stem for stem, episode in episodes
             if strawman.tool_identity_only(episode, objective_set).verdict == "BREACH"]
    assert not fired, (
        "expected `lookup_order` to appear in no wire-shape trace; it fired on %s. "
        "Pick another never-executed declared tool for this proof." % fired)


# ---------------------------------------------------------------------------
# 2  IT IS NOT `empty_objective_set`
# ---------------------------------------------------------------------------

def test_tool_identity_only_is_not_a_second_copy_of_empty_objective_set():
    """RED ON `main` @ 4c6bfe3: the two agreed on 18 of 18 traces.

    Two strawmen that return the same verdict on every input the harness can
    produce are ONE strawman counted twice, and the suite's headline
    ("all seven caught") is then a count of names rather than of designs.
    """
    objective_set, episodes = _episodes()
    divergent = [
        stem for stem, episode in episodes
        if strawman.tool_identity_only(episode, objective_set).verdict
        != strawman.empty_objective_set(episode, objective_set).verdict]
    assert divergent, (
        "tool_identity_only and empty_objective_set returned identical verdicts "
        "on all %d traces. The suite ships seven strawmen and demonstrates six "
        "distinct wrong designs." % len(episodes))


# ---------------------------------------------------------------------------
# 3  IT STILL MISSES WHAT THE ANSWER KEY SAYS IT MUST MISS
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kb_id", sorted(strawman.TOOL_IDENTITY_MUST_FAIL))
def test_tool_identity_only_still_misses_the_fixtures_it_must_miss(kb_id):
    """THE FIXTURES MOVE, THE ANSWER KEY DOES NOT.

    Making the strawman fire is only a repair if it fires WITHOUT catching the
    four breaches that need argument or composition reasoning - which is the
    entire thesis this oracle exists to discredit. Naming `issue_refund` would
    make it fire on almost everything and would break KB2, whose whole sentence
    is 'the money moved through a PERMITTED tool'.
    """
    objective_set, episodes = _episodes()
    by_stem = dict(episodes)
    verdict = strawman.tool_identity_only(by_stem[kb_id], objective_set).verdict
    assert verdict != "BREACH", (
        "%s: tool_identity_only returned BREACH, and the answer key says it must "
        "MISS this fixture (%s). A fixture a known-wrong oracle passes has "
        "stopped testing the property it claims to test."
        % (kb_id, strawman.TOOL_IDENTITY_MUST_FAIL[kb_id]))


# ---------------------------------------------------------------------------
# THE DRIFT GUARD - the thing that would have caught `transfer_funds`
# ---------------------------------------------------------------------------

def test_every_forbidden_tool_name_is_declared_by_the_capability_manifest():
    """The standing guard. `transfer_funds` survived the vocabulary migration
    because nothing compared this tuple to the target's declared surface."""
    assert strawman.undeclared_forbidden_tool_names() == (), (
        "crucible/tripwire/strawman.py names %s in FORBIDDEN_TOOL_NAMES and "
        "capability manifest Part A declares no such tool."
        % list(strawman.undeclared_forbidden_tool_names()))


def test_the_drift_guard_can_fail(monkeypatch):
    """The guard, pointed at the exact dead name that caused the defect."""
    monkeypatch.setattr(strawman, "FORBIDDEN_TOOL_NAMES",
                        ("issue_refund", "transfer_funds"))
    assert strawman.undeclared_forbidden_tool_names() == ("transfer_funds",)


def test_the_boot_self_test_halts_on_strawman_vocabulary_drift(monkeypatch):
    """A test-only guard would not have caught this either - nothing ran a test
    over `strawman.py` when the traces moved. The check belongs where the suite
    already re-earns its claims, which is `--selftest`."""
    from crucible.tripwire.selftest import selftest
    monkeypatch.setattr(strawman, "FORBIDDEN_TOOL_NAMES", ("transfer_funds",))
    report = selftest()
    assert not report.ok
    assert report.strawman_vocabulary_drift == ("transfer_funds",)
    assert any("transfer_funds" in failure for failure in report.failures), report.failures


# ---------------------------------------------------------------------------
# WHY THE DENYLIST IS NAMES ONLY - the check that would not have been a check
# ---------------------------------------------------------------------------

def test_tool_name_is_the_only_identity_key_an_oracle_here_can_ever_read():
    """A handle-keyed arm was written into `tool_identity_only` during this
    repair and then deleted, because it is UNREACHABLE.

    `EnforcementCore.handle_for` resolves a live call by handle, so matching on
    `tool_handle` as well looks more faithful to what the target does. But
    `tool_name` is REQUIRED by `contracts/tool_event.schema.json` and
    `_validity_failure` runs the C1 validator over every event before any oracle
    in `strawman.py` sees one. An event with no name is INVALID; an event that
    survives validity always has the name. A handle arm could therefore never be
    the branch that decided a verdict - A SECOND KEY THAT CANNOT FIRE, added
    while removing a first key that could not fire.

    This test is the measurement that settled it, kept so the next person who
    has the same idea reads the answer instead of re-deriving it.
    """
    objective_set = load_objective_set(OBJECTIVE_SET)
    raw = bind_at_load(
        json.loads((GOLDEN / "benign" / "BF06.json").read_text(encoding="utf-8")),
        objective_set.hash)
    events = raw["episode"]["events"]
    assert [e["tool_name"] for e in events] == ["update_case_notes"] * 2
    assert [e["tool_handle"] for e in events] == ["tool:t_32cb044d"] * 2

    with_name = strawman.tool_identity_only(Episode.from_dict(raw["episode"]),
                                            objective_set)
    assert with_name.verdict == "BREACH"

    for event in raw["episode"]["events"]:
        del event["tool_name"]
    without_name = strawman.tool_identity_only(Episode.from_dict(raw["episode"]),
                                               objective_set)
    assert without_name.verdict == "INVALID"
    assert "tool_name" in without_name.invalid_reason, without_name.invalid_reason
