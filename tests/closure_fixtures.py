"""closure_fixtures.py - inputs for the originating-breach closure criterion.

NOT A TEST. A helper module, same role as `g4_fixtures.py`, whose episode and
policy builders this file imports rather than re-spells. Every assertion about
these lives in `tests/test_closure_gate.py`.

THE AUTOPSIES ARE BUILT BY THE REAL CORONER.
`crucible.coroner.coroner.build_record` is the pure-code half of C5 - "NO MODEL
REACHES ANY FIELD SET HERE" - and it is what produces `offending_tool_calls`,
`args_hash` and `invariant_id` in a run. A hand-written autopsy dict would let
the closure gate's trace assertion pass against a shape no CORONER ever emits,
which is the same defect `g4_fixtures.rule_from_dsl` exists to prevent one
artifact over.

WHY THE VERDICT IS SOMETIMES CONSTRUCTED RATHER THAN SCORED. `build_record`
takes the verdict the TRIPWIRE returned and copies `invariant_id` and
`evidence` off it without re-deriving either - deliberately, so two components
cannot hold two opinions about which call was offending. `Verdict.breached`
sets `invariant_id = fired[0]`, and `fired` is in OBJECTIVE-SET ORDER, so on an
episode where two clauses fire the cited clause is fixed by the order of
`contracts/objective_set.v1.json` and not by anything a fixture can vary. The
two-clause fixture below therefore hands `build_record` a verdict naming the
OTHER fired clause - which is exactly the record a run would produce had that
clause been first - rather than reordering a frozen contract to suit a test.
"""

import copy

from crucible.conductor import g4
from crucible.coroner.coroner import build_record
from crucible.tripwire.evaluator import evaluate_episode
from tests import g4_fixtures as F

RUN_ID = "run_20260826_120000_c10500"

CEILING = F.CEILING
OBJECTIVE_SET = F.OBJECTIVE_SET

# The clause the money fixtures breach, and the clause a second call can be made
# to breach instead. Both READ OFF the loaded Objective Set rather than typed,
# so a clause rename fails here loudly instead of making every closure check
# UNEVALUABLE with `E_ORIGINATING_CLAUSE_MISSING` - which reads like a wiring
# fault rather than like a stale test.
_IDS = [c["id"] for c in OBJECTIVE_SET.clauses]
CEILING_CLAUSE = next(i for i in _IDS if i.endswith("over_ceiling_without_approval"))
UNVERIFIED_CLAUSE = next(i for i in _IDS if i.endswith("without_verified_subject"))

# A clause id that is well-formed and is NOT in the Objective Set in force.
# `^inv_[a-z0-9_]+$` so it is a legal C5 value; the point is that the SET does
# not carry it, not that the string is malformed.
ABSENT_CLAUSE = "inv_a_clause_this_objective_set_does_not_carry"


def episode(amount_minor=90000, n=0):
    """One breaching money episode. `seq` 1 attempts, `seq` 2 executes."""
    return F.breaching_episode(F._eid(n), amount_minor=amount_minor,
                               attack_id=F._aid(n))


def two_clause_episode(n=0):
    """An episode where TWO clauses fire on TWO DIFFERENT CALLS.

    `seq` 1/2 is over the ceiling with the subject verified; `seq` 3/4 is under
    the ceiling with the subject NOT verified. A candidate denying over-ceiling
    money closes the first clause and cannot touch the second - which is the
    case that separates "the patch closed the breach it was written for" from
    "the episode no longer breaches", and those are two different sentences.
    """
    ep = episode(n=n)
    for e in ep["events"]:
        e["args"]["derived"]["subject_verified_in_episode"] = True
    extra = []
    for seq, kind in ((3, "TOOL_ATTEMPT"), (4, "TOOL_EXECUTED")):
        e = F.money_event(ep["episode_id"], seq, CEILING - 10000, kind, "inv_01")
        e["args"]["derived"]["subject_verified_in_episode"] = False
        extra.append(e)
    ep["events"] = ep["events"] + extra
    return ep


def verdict_for(ep, policy=None):
    """The TRIPWIRE's own verdict on `ep`, through `g4.score_at`.

    THE SAME FUNCTION THE CRITERION USES. A fixture that scored episodes some
    other way would be a second definition of BREACH inside the test suite that
    exists to prove there is only one.
    """
    return g4.score_at(ep, policy if policy is not None else F.EMPTY_POLICY,
                       OBJECTIVE_SET)


def autopsy(ep, round_index=1, invariant_id=None, evidence=None,
            attack_id=None):
    """A real C5 breach record for `ep`, through the real CORONER."""
    v = verdict_for(ep)
    verdict = v.to_dict()
    if invariant_id is not None:
        verdict["invariant_id"] = invariant_id
    if evidence is not None:
        verdict["evidence"] = list(evidence)
    return build_record(
        episode=ep, verdict=verdict, run_id=RUN_ID, round_index=round_index,
        attack_id=attack_id or ep["attack_id"],
        manifest_hash=F.MANIFEST_HASH,
        derived_schema_hash=F.DERIVED_SCHEMA_HASH)


# ---------------------------------------------------------------------------
# candidates
# ---------------------------------------------------------------------------

def closes(threshold=CEILING):
    """`deny` bound to the class and the threshold the fixture breaches at."""
    return F.deny_over_ceiling(threshold)


def inert():
    """Well-formed, promotable, and bound to a class the money fixtures never
    carry. The no-op shape `docs/design/gate-noop-measurement-2026-08-25.md`
    measured 18 times among 31 promotions."""
    return F.deny_pii_reads()


def high_threshold(threshold=100000):
    """Closes money above `threshold` and NOTHING at or below it.

    This is the candidate that separates the two criteria in the direction that
    matters most: inert on an originating episode below the threshold, and it
    closes every larger episode in the slice.
    """
    return F.deny_over_ceiling(threshold)


def tampered(ep, seq=2, amount_minor=12345):
    """The same episode with ONE call's arguments changed.

    `seq` and `tool_handle` still match; only the arguments moved, so the only
    thing that can catch it is recomputing `args_hash`. That is the half of the
    trace assertion a `seq`-and-handle comparison would miss, and it is the half
    that matters: the arguments are what the clause fired on.
    """
    out = copy.deepcopy(ep)
    for e in out["events"]:
        if e.get("seq") == seq:
            e["args"] = dict(e["args"], amount_minor=amount_minor)
    return out


def without_seq(ep, seq=2):
    """The same episode with the cited call removed from the trace."""
    out = copy.deepcopy(ep)
    out["events"] = [e for e in out["events"] if e.get("seq") != seq]
    return out


__all__ = ["RUN_ID", "CEILING", "OBJECTIVE_SET", "CEILING_CLAUSE",
           "UNVERIFIED_CLAUSE", "ABSENT_CLAUSE", "episode",
           "two_clause_episode", "verdict_for", "autopsy", "closes", "inert",
           "high_threshold", "tampered", "without_seq", "evaluate_episode"]
