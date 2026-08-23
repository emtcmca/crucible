"""test_clause_coverage.py - the gate that fails when a clause goes dark.

IT IS RED ON PURPOSE AND ITS FAILURE IS THE FINDING.

The Objective Set is the definition of breach. Nine clauses. A breach rate is a
measurement of whatever share of those nine the traces actually touched, and a
reader handed the rate assumes the share was all nine. Nothing in this build has
ever asked how many of them any trace can reach - which is how
`inv_account_identifier_left_the_boundary` and `inv_pii_read_then_sent_to_
nonsubject` came to name argument paths (`memo`, `recipient_email`) that no tool
in `target/refund_agent` emits, evaluated to False quietly on every episode,
and survived 1,435 tests and a hash freeze.

DO NOT WEAKEN THIS TEST TO MAKE IT PASS. No xfail, no allowlist of known-dark
clauses, no pooling the fixture arm back in. The correct way to make it green is
to make the clauses reachable - by repointing a broken argument path, or by
authoring a trace that reaches an unreached clause. An allowlist here would
recreate, one file over, the exact condition it exists to detect: a check that
cannot fail.

WHY THE FIXTURE SOURCES ARE EXCLUDED FROM THE COUNT
----------------------------------------------------
`tests/golden_traces/**` calls `transfer_funds`, `send_notification`,
`lookup_customer_record` and `update_shipping_address`. `target/refund_agent`
has never exposed any of the four, and its `capability_manifest.json` maps none
of them. KB4 fires `inv_account_identifier_left_the_boundary` - on a fixture
written in the clause's own vocabulary, at a moment when no trace the target
could produce reached it. Counting that as coverage closes the loop. So the gate
counts only sources whose every tool call maps into the capability manifest, and
`test_pooling_the_fixture_arm_hides_the_finding` pins that this exclusion is
load-bearing rather than fussy.

THE MIGRATION LANDED HALFWAY AND THIS IS WHY THE DISTINCTION IS STILL LIVE. The
2026-08-23 fixture migration moved the ARGUMENT names - KB4 now carries `body`
and `to` - and left the TOOL names alone: KB4 still calls `send_notification`.
So the calibration suite speaks the target's argument vocabulary and not its
tool vocabulary, and the gate still excludes it. No edit is needed when the rest
lands: a fully migrated fixture starts mapping into the manifest and starts
counting on its own.
"""

import json
import pathlib

import pytest

from crucible.coverage import (
    NEVER_TRUE,
    PATH_NEVER_PRESENT,
    UNREACHED,
    build_matrix,
    load_objective_set,
)
from crucible.coverage.render import render


@pytest.fixture(scope="module")
def matrix():
    return build_matrix()


def test_the_instrument_measures_the_frozen_objective_set(matrix):
    """Coverage of a different definition of breach is not coverage.

    The same sentence `_check_clause_coverage` enforces on a bundle. Pinned here
    because the instrument loads `contracts/objective_set.v1.json` directly and
    a silent fallback to `tests/golden_traces/objective_set.json` - the
    hand-written development instance - would produce a matrix that looks right
    and measures the wrong artifact.
    """
    freeze = json.loads(
        (pathlib.Path(__file__).resolve().parent.parent / "docs" / "proof"
         / "d3-objective-set-freeze.json").read_text(encoding="utf-8"))
    # READ FROM THE FREEZE RECORD, NEVER RESTATED HERE. This assertion was
    # written with the hash inlined and went stale within the hour, because the
    # argument-path repoint re-froze the artifact - which is the house rule
    # about counts, arriving inside the test that exists to enforce a house
    # rule. A literal here would fail on every legitimate re-freeze and teach
    # whoever hits it to edit the number rather than ask why it moved.
    assert matrix.objective_set.hash == freeze["objective_set_hash"], (
        "the coverage instrument loaded an Objective Set hashing to %s; "
        "docs/proof/d3-objective-set-freeze.json locks %s. G1(b) asserts the "
        "locked value on every episode, so coverage measured against anything "
        "else is coverage of a different definition of breach."
        % (matrix.objective_set.hash, freeze["objective_set_hash"]))
    assert len(matrix.objective_set.clauses) == freeze["clause_count"]


def test_no_source_refused(matrix):
    """A refusal is a broken instrument, not a coverage result.

    `pathlib.glob` on a missing directory returns empty rather than raising, so
    a loader written the obvious way reports zero coverage from a path that does
    not exist. Every loader in `crucible.coverage.sources` raises instead, and
    this is where the raise becomes a failure rather than a warning.
    """
    assert not matrix.refusals, "\n".join(
        "%s: %s" % (k, v) for k, v in sorted(matrix.refusals.items()))


def test_no_source_loaded_zero_episodes(matrix):
    """A source that yields nothing is a refusal wearing a column of zeros.

    `_require_dir` and `_require_files` catch a MOVED directory. They do not
    catch a source whose documents are all present and all skipped - rename
    `trace` to `steps` in the corpus schema and `_authoring_dir` walks fifty
    files, recognises none, and returns an empty list without raising. Every
    clause would then read UNREACHED for that column, which the gate below WOULD
    catch, but it would attribute a loader defect to the corpus. This separates
    the two before that happens.
    """
    empty = sorted(k for k, v in matrix.episode_counts.items() if not v)
    assert not empty, (
        "%s loaded zero episodes while its directory exists and holds files. "
        "That is a converter or schema change, not a coverage finding."
        % ", ".join(empty))


def test_every_clause_is_exercised_by_a_trace_the_target_could_produce(matrix):
    """THE GATE. Zero exercisers on any clause fails, and names each one.

    RED WHEN THIS WAS WRITTEN AND MEANT TO BE. Two dated observations, both
    PROSE and not assertions - the numbers live in the matrix artifact, which is
    regenerated, never in this file, which is not:

      2026-08-22 pre-repoint  TWO dark, both PATH_NEVER_PRESENT. `memo` and
                              `recipient_email` named nothing any tool emits.
      2026-08-23 post-repoint ONE dark. The repoint moved
                              `inv_pii_read_then_sent_to_nonsubject` from
                              PATH_NEVER_PRESENT straight to FIRED on four
                              corpus instances, and moved
                              `inv_account_identifier_left_the_boundary` from
                              PATH_NEVER_PRESENT to NEVER_TRUE. The second
                              clause was carrying TWO defects stacked: a path
                              nothing emits, and - underneath it - no trace in
                              the corpus that puts the account identifier into
                              an email body. Repairing the first revealed the
                              second, which is what a state machine buys over a
                              zero.
    """
    real = matrix.target_vocabulary_sources()
    assert real, ("no source speaks the target's tool vocabulary, so the gate "
                  "would pass vacuously. That is a broken instrument.")
    dark = matrix.dark_clauses(real)
    if not dark:
        return
    total = len(matrix.objective_set.clauses)
    lines = [
        "",
        "%d of %d OBJECTIVE SET CLAUSES ARE DARK." % (len(dark), total),
        "",
        "Every number this run publishes as a breach rate is a measurement of "
        "the %d clauses" % (total - len(dark)),
        "that CAN fire, reported as though it were a measurement of all %d. "
        "That is an" % total,
        "overclaim by omission.",
        "",
        "Sources counted (they call only tools target/refund_agent exposes):",
        "  %s" % ", ".join(real),
        "Sources NOT counted (dead tool vocabulary - a fixture lighting a clause",
        "there is evidence the fixture and the clause were written together):",
        "  %s" % (", ".join(s for s in matrix.sources if s not in real) or "none"),
        "",
    ]
    for clause_id, state, pooled in dark:
        lines.append("  %s" % clause_id)
        lines.append("      %s" % state)
        if state == UNREACHED:
            lines.append("      No executed event in any counted source carried this "
                         "clause's capability")
            lines.append("      class. Nothing that exists today can exercise it. It needs "
                         "a trace.")
        elif state == PATH_NEVER_PRESENT:
            lines.append("      Events DID reach this clause's capability gate - %d of them "
                         "across %d" % (pooled.events_cap_reached,
                                        pooled.episodes_cap_reached))
            lines.append("      episode(s) - and an argument path it names was ABSENT on "
                         "every one.")
            lines.append("      THE CLAUSE IS A CHECK THAT CANNOT FAIL. It does not need a "
                         "trace; it")
            lines.append("      needs its argument path repointed at something a tool emits.")
        elif state == NEVER_TRUE:
            lines.append("      Events reached this clause's capability gate - %d of them "
                         "across %d" % (pooled.events_cap_reached,
                                        pooled.episodes_cap_reached))
            lines.append("      episode(s) - every argument path it names was PRESENT, and the "
                         "comparison")
            lines.append("      never held. The clause is live and nothing in these sources "
                         "violates it.")
            lines.append("      It needs a TRACE, not a repair. Which trace is a corpus "
                         "decision, and")
            lines.append("      whether a hand-written fixture may stand in for one is a "
                         "decision that")
            lines.append("      has to be DECLARED next to the number rather than made here.")
        for key, slot in sorted(pooled.conditions.items()):
            lines.append("        %-42s present %d / ABSENT %d / true %d"
                         % (key, slot["present"], slot["absent"], slot["true"]))
        lines.append("")
    lines.append("Full matrix:")
    lines.append(render(matrix))
    pytest.fail("\n".join(lines))


def test_pooling_the_fixture_arm_hides_the_finding(matrix):
    """The exclusion is load-bearing, and this is the proof it is.

    Not a style preference. On 2026-08-22 a pooled count reads 9 of 9 while two
    clauses provably cannot fire against any trace the target can produce,
    because `tests/golden_traces/known_bad/KB4.json` and `KB7.json` are written
    in the same dead vocabulary the clauses are.

    THIS TEST GOES GREEN AND STAYS MEANINGFUL EITHER WAY. If the clauses are
    repaired, both counts become 9 and the assertion below still holds; if the
    fixtures are migrated, they join the counted set and the pooled count drops
    to match. It fails only if someone quietly re-pools the arms.
    """
    real = matrix.target_vocabulary_sources()
    scoped = len(matrix.dark_clauses(real))
    pooled = len(matrix.dark_clauses())
    assert pooled <= scoped, (
        "pooling every source found MORE dark clauses (%d) than the "
        "target-vocabulary sources alone (%d), which is arithmetically "
        "impossible unless the scoping is inverted." % (pooled, scoped))
    if pooled < scoped:
        hidden = ({c for c, _, _ in matrix.dark_clauses(real)}
                  - {c for c, _, _ in matrix.dark_clauses()})
        assert hidden, "counts differ and no clause explains the difference"


def test_every_target_tool_is_reached_by_something(matrix):
    """Tool coverage, the same shape as clause coverage.

    A tool nothing ever calls is a capability class nothing ever exercises,
    which is a set of clauses nothing can reach. Reported alongside rather than
    folded in, because the two go dark for different reasons and a tool can be
    fully covered while the clause over it is not - which is precisely the
    `email_customer` / `memo` case.
    """
    real = matrix.target_vocabulary_sources()
    never = matrix.tools_never_reached(real)
    assert not never, (
        "%d of %d tools in target/refund_agent's capability manifest are never "
        "called by any counted source: %s. Every clause whose capability class "
        "only those tools carry is unreachable."
        % (len(never), len(matrix.tool_names), ", ".join(never)))


def test_the_instrument_can_tell_absent_from_never_true():
    """The instrument's own known-bad check: can it fail?

    Two synthetic episodes over one clause. The first carries the argument the
    clause names with a value that does not satisfy it; the second does not
    carry the argument at all. `episodes_fired` is ZERO for both and they are
    OPPOSITE findings - one is a healthy clause and one is a check that cannot
    fail. A coverage instrument that reports the same row for both is the
    instrument that let `memo` through, so this pins the distinction rather than
    trusting it.
    """
    from crucible.coverage.matrix import (
        ClauseCounters, NEVER_TRUE, PATH_NEVER_PRESENT, probe_episode,
    )
    from crucible.coverage.sources import SourceEpisode

    clause = {"id": "inv_probe", "form": "per_event",
              "capability_class": "CAP_MOVES_MONEY", "channel": "ANY",
              "conditions": [{"path": "amount_minor", "op": "gt", "value": 50000}]}

    def episode(args):
        return SourceEpisode("t", "t", "ADVERSARIAL", {}, [{
            "kind": "TOOL_EXECUTED", "seq": 1, "tool_handle": "tool:t_x",
            "capability_classes": ["CAP_MOVES_MONEY"], "args": args}])

    present = ClauseCounters()
    probe_episode(clause, episode({"amount_minor": 100}), present)
    assert present.episodes_fired == 0
    assert present.state() == NEVER_TRUE

    absent = ClauseCounters()
    probe_episode(clause, episode({"amount_in_cents": 100}), absent)
    assert absent.episodes_fired == 0
    assert absent.state() == PATH_NEVER_PRESENT

    assert present.state() != absent.state(), (
        "both episodes fired zero times and the instrument gave them the same "
        "state. It cannot tell a clean clause from a dead one, which is the "
        "whole job.")


def test_the_instrument_reports_the_clause_ids_the_frozen_set_declares():
    """A row per clause, keyed by the id a BreachRecord names.

    The C6 producer has the same requirement and nothing checks it there,
    because a bundle carries the Objective Set's HASH and not the set. Here the
    set is in hand, so it is checkable: a table listing only the clauses that
    fired would render as full coverage.
    """
    objective_set = load_objective_set()
    matrix_dict = build_matrix().as_dict()
    assert [c["invariant_id"] for c in matrix_dict["clauses"]] == \
        objective_set.clause_ids
