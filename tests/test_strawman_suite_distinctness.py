"""Seven strawmen must be seven DESIGNS, not seven names.

THE ROOT CAUSE THIS CLOSES, found by the strawman-repair lane 2026-08-23 and
generalised here.

`selftest.py` decides a strawman is caught with:

    caught = all(not outcome.ok for kb in must_fail)

That asks only whether a strawman is WRONG. It never asks whether it is wrong
**for the reason its own docstring claims**. An always-CLEAN oracle satisfies
every `*_MUST_FAIL` in the file, so a strawman can quietly collapse into a copy
of another one and the boot self-test keeps reporting "all seven caught."

That is exactly what happened. A migration re-authored the golden traces into
the target's real tool vocabulary, `tool_identity_only` kept keying on a name
that no longer existed, and it became **verdict-identical to
`empty_objective_set` on 18 of 18 traces**. The suite shipped seven strawmen and
demonstrated six distinct wrong designs, and nothing failed.

The repair lane pinned that ONE pair. This file pins ALL of them, because the
next collapse will not be the pair we already looked at. If two strawmen agree
on every input the harness can produce, they are one strawman counted twice,
whatever their docstrings say.
"""
import itertools

import pytest

from crucible.tripwire import strawman

from tests.test_strawman_tool_identity import _episodes, _wire_trace_paths


def _verdict_vectors():
    """name -> tuple of verdicts, one per trace, in a fixed order."""
    objective_set, episodes = _episodes()
    vectors = {}
    for name, (fn, _must_fail) in sorted(strawman.STRAWMEN.items()):
        vectors[name] = tuple(
            fn(episode, objective_set).verdict for _stem, episode in episodes)
    return vectors, len(episodes)


def test_the_suite_has_traces_to_distinguish_anything_at_all():
    """THE FLOOR. Every assertion below is a comparison over a list, and a
    comparison over an empty list proves nothing. Without this the whole file
    goes green by looking at zero traces."""
    assert len(_wire_trace_paths()) >= 18
    _vectors, n = _verdict_vectors()
    assert n >= 15, "only %d traces carry an episode; too few to separate seven designs" % n


def test_every_strawman_is_registered_with_its_own_answer_key():
    """A strawman missing from the registry is invisible to every check here,
    which is the cheapest way for this file to stop measuring."""
    assert len(strawman.STRAWMEN) == 7, sorted(strawman.STRAWMEN)


@pytest.mark.parametrize(
    "left,right",
    sorted(itertools.combinations(sorted(strawman.STRAWMEN), 2)))
def test_no_two_strawmen_are_the_same_function(left, right):
    """21 pairs. Each must disagree on at least ONE trace.

    This is the generalisation of the defect: `tool_identity_only` and
    `empty_objective_set` agreed on all 18. Nothing noticed, because being
    wrong was the whole bar.
    """
    vectors, n = _verdict_vectors()
    assert vectors[left] != vectors[right], (
        "%s and %s return identical verdicts on all %d traces. They are ONE "
        "strawman counted twice, and the self-test's 'all seven caught' is a "
        "count of names rather than of designs. Either one of them has "
        "degenerated - check whether it keys on vocabulary the corpus no longer "
        "carries - or the pair was never two designs."
        % (left, right, n))


def test_the_distinctness_check_can_fail(monkeypatch):
    """THE NEGATIVE CONTROL ON THIS FILE ITSELF.

    Without it, `test_no_two_strawmen_are_the_same_function` could be passing
    because of a bug in `_verdict_vectors` rather than because the suite is
    healthy - a check that cannot fail, inside the file written to end a
    check that cannot fail.
    """
    monkeypatch.setitem(
        strawman.STRAWMEN, "prose_reader",
        (strawman.empty_objective_set, strawman.PROSE_MUST_FAIL))
    vectors, _n = _verdict_vectors()
    assert vectors["prose_reader"] == vectors["empty_objective_set"], (
        "the falsifier did not take: aliasing one strawman to another still "
        "produced different verdict vectors, so this file is not measuring "
        "what it claims")
