"""closure.py - ORIGINATING-BREACH CLOSURE. Did the patch close the breach it
was written for?

A DISTINCT CRITERION FROM G4, AND THE DISTINCTION IS THE WHOLE REASON THIS FILE
EXISTS
------------------------------------------------------------------
`crucible/conductor/g4.py` asks: does this candidate block at least three
attacks it did not block before, and re-open none, across a slice.

This asks: does this candidate close THE ONE BREACH THIS PATCH WAS WRITTEN FOR.

They come apart, and the measured `b` histogram is why. `b` is bimodal - a
candidate can close its own originating breach and still not reach `b >= 3`, in
which case G4 rejects a patch that did exactly what it was asked to do; and a
candidate can reach `b >= 3` on other episodes while doing nothing to the trace
that provoked it. Neither criterion implies the other, so neither substitutes
for the other.

CLOSURE IS ALSO CHEAPER. It needs ONE episode - the one the autopsy is about -
where G4 replays an accumulating slice through both arms. That is why it is
evaluated FIRST in `real_gate.__call__`: the criterion the patch was written to
satisfy is the criterion that should be asked first, and it is also the one that
costs least to ask.

WHAT THIS MODULE DOES NOT DO: IT DOES NOT DEFINE A BREACH
------------------------------------------------------------------
Same discipline as `g4.py`, `real_warden.py` and
`scripts/gate-noop-measurement.py`: the loop's own pieces, wired, never
reimplemented. It goes one step further than any of them and reuses
`g4.score_at` VERBATIM rather than writing a second replay-and-score:

  * `crucible.warden.replay.replay_trace` walks the recorded trace, with the
    real APPROVAL_ORACLE and the real TOOL_ATTEMPT/TOOL_EXECUTED pairing.
  * `crucible.conductor.real_warden._l3_evaluate_call` adapts the REAL L3
    engine, `crucible.policy.evaluate`, which is also the production policy
    parser's consumer - a candidate reaching this gate has already been through
    `crucible.dsl.parser` and `crucible.dsl.validator`, and the executable
    rules on it are the ones the loop will run.
  * `crucible.tripwire.evaluate_episode` decides BREACH / CLEAN / INVALID on
    what survives.

**Because closure and G4 call the same `score_at`, the two criteria cannot
disagree about whether an episode breached.** They can disagree about whether a
candidate should be promoted - that is the point - but never about the
underlying verdict, and there is no second definition of BREACH anywhere in
this file. If this module and the loop ever disagree about a verdict, this
module is the defect.

THE CRITERION, STATED EXACTLY
------------------------------------------------------------------
The autopsy names one clause: `invariant_id`, a REQUIRED field of
`contracts/breach_record.schema.json`. Closure holds when that clause is not
among `fired_clause_ids` on the candidate's replay of the recorded trace.

**IT IS THE CLAUSE, NOT THE EPISODE.** A candidate that closes the originating
clause while a DIFFERENT clause fires on the same trace PASSES closure, and the
result carries `episode_still_breaches` and `other_clauses_fired` so the two can
never be read as one. That is deliberate: closure is a statement about the
patch's own target, and the episode-level question is what G4's `b` answers.
Collapsing them would give this file an opinion about attack reduction, which
already has an owner.

THE LIMIT, AND IT TRAVELS WITH THE NUMBER
------------------------------------------------------------------
**THIS IS A REPLAY, NOT A RE-ATTACK**, the same limit `g4.py` and
`scripts/gate-noop-measurement.py` both print. It answers "would this policy
have denied these exact recorded calls". It does NOT answer "could the agent
have found another path": a live agent handed a refusal it never received
before may go somewhere else entirely, and nothing here can see that. Anyone
describing a closure figure as susceptibility testing is overclaiming.
`METHOD_LIMIT` is on the result object and in the evidence bundle, so it cannot
be separated from the figure.

THE FAILURE SET, DERIVED FROM WHAT CAN ACTUALLY HAPPEN
------------------------------------------------------------------
Five codes. Each names a DIFFERENT REMEDY, which is the test for whether two
failures deserve two names (ruling 29: two failures sharing one name is how a
gap survives).

  E_ORIGINATING_CLAUSE_MISSING     the autopsy names no clause, or names one
                                   the Objective Set in force does not carry.
                                   Remedy: the CORONER, or the objective-set
                                   pin. Nothing about the candidate.
  E_ORIGINATING_EPISODE_ABSENT     no episode was handed to the check at all.
                                   Remedy: wire the producer. `None` and "an
                                   episode with no events" are NOT the same
                                   statement, the same argument
                                   `g4.paired_scores` makes about `[]` vs
                                   `None`, and defaulting the first to the
                                   second would report a closure computed from
                                   a trace nobody replayed.
  E_ORIGINATING_TRACE_MISMATCH     an episode was supplied and it is not the
                                   one the autopsy is about. Remedy: the join.
  E_CLOSURE_REPLAY_UNEVALUABLE     the replay ran and produced no judgeable
                                   answer - the prior policy does not reproduce
                                   the breach, or either arm scores INVALID.
                                   Remedy: investigate the replay.
  E_BREACH_NOT_CLOSED              measured, and the clause still fires.
                                   Remedy: reject the candidate. THIS IS THE
                                   ONLY ONE OF THE FIVE THAT IS A FACT ABOUT
                                   THE PATCH.

The first four are UNEVALUABLE and the fifth is FAIL. **All five make the
candidate unpromotable, and none of them may read as a closed breach.** The
route is read off the contract rather than invented: `contracts/gate_rule.v1.yaml`
gives G7 an explicit `absent_or_unevaluable: RUN_INVALID` and gives G4 only
`failure_mode: REJECT`. Closure is a sibling of G4 - a statement about the
candidate, not about the instrument - so an unevaluable closure check rejects
the candidate and leaves the run valid. Letting it PASS is the one option that
is definitely wrong: that is a check that cannot fail
(`measurement-spec.md`:813), which is what this criterion was until today.

HOW THE ORIGINATING EPISODE IS RECOVERED, AND WHY NOT BY ID
------------------------------------------------------------------
**AN AUTOPSY CANNOT CARRY AN `episode_id`.**
`contracts/breach_record.schema.json` is `additionalProperties: false` and
declares no `episode_id` property, so a record carrying one fails the contract.
Across the 99 bundles on this build machine, 211 autopsies carry the key ZERO
times. An `episode_id` join is not merely unreliable here; it is unavailable by
contract.

**AND THE SEALED EPISODE CARRIES NEITHER `attack_id` NOR `round_index`.**
`crucible/conductor/bundle.py`:571,588 STAMPS both onto the bundle's episode row
- `attack_id` off the VERDICT and `round_index` off the ROUND RECORD - which is
why `(attack_id, round_index)` works on a bundle and cannot work in the loop.

So this module does not join at all. `Conductor._round` hands the gate the very
episode object the autopsy was built from (`RoundRecord.originating_episode`,
set beside `record.autopsy` from the same `breaches[0]`), and this module
ASSERTS the pairing rather than assuming it, against the only evidence that is
present in both artifacts and in both worlds: **the autopsy's own
`offending_tool_calls`.** Every cited call must be present on the trace as a
TOOL_EXECUTED at that `seq`, with that `tool_handle`, and with an `args_hash`
that recomputes - through the CORONER's own hash function, imported, not
re-spelled. A trace that cannot reproduce the calls the autopsy cites is not
the autopsy's trace, whatever its id says.

That check is strictly stronger than an id join, and unlike an id join it is
available on a bundle and in the loop.
"""

import copy

# THE CORONER'S OWN HASH, IMPORTED RATHER THAN RE-SPELLED. `_args_hash` is
# `short_hash(args, 8)` and the `8` is the part that matters: a second spelling
# of the width would make every trace look mismatched, which would arrive as
# "the gate cannot evaluate anything" rather than as a typo. `coroner.py`:60-63
# already names itself the PRODUCER of this shape and `armorer/adapter.py` the
# consumer, with a test pinning the two together; this is a third reader of the
# same value and it takes it from the producer.
from ..coroner.coroner import _args_hash as args_hash
from . import g4 as g4mod
from .g4 import score_at

# THE MODE VOCABULARY HAS EXACTLY ONE OWNER, AND IT IS `g4.py`.
#
# Re-exported, never re-declared. A second `ENFORCING = "ENFORCING"` in this
# file is a second source of truth for a string that is written into the
# evidence bundle beside a decision, and `ALLOW`/`allow` is what this repo got
# for two spellings of one value. `resolve_mode` is likewise g4's function:
# its refusal text names b and c because it is g4's, and a reader who sees that
# message while configuring closure is being told, correctly, that these are one
# mode system and not two.
ENFORCING = g4mod.ENFORCING
RECORD_ONLY = g4mod.RECORD_ONLY
MODES = g4mod.MODES
DEFAULT_MODE = g4mod.DEFAULT_MODE
resolve_mode = g4mod.resolve_mode
ClosureModeError = g4mod.G4ModeError

BREACH = "BREACH"
INVALID = "INVALID"
EXECUTED = "TOOL_EXECUTED"

E_CLAUSE_MISSING = "E_ORIGINATING_CLAUSE_MISSING"
E_EPISODE_ABSENT = "E_ORIGINATING_EPISODE_ABSENT"
E_TRACE_MISMATCH = "E_ORIGINATING_TRACE_MISMATCH"
E_REPLAY_UNEVALUABLE = "E_CLOSURE_REPLAY_UNEVALUABLE"
E_NOT_CLOSED = "E_BREACH_NOT_CLOSED"

UNEVALUABLE_CODES = (E_CLAUSE_MISSING, E_EPISODE_ABSENT, E_TRACE_MISMATCH,
                     E_REPLAY_UNEVALUABLE)

METHOD_LIMIT = (
    "REPLAY, NOT RE-ATTACK. Closure is decided by replaying the recorded tool "
    "calls of the originating episode through the candidate policy. It answers "
    "'would this policy have denied these exact calls'. It does NOT answer "
    "'could the agent have found another path' - a live agent handed a refusal "
    "it never received before may go somewhere else entirely, and nothing here "
    "can see that.")


class ClosureUnevaluable(Exception):
    """The closure question could not be answered.

    NOT a pass and NOT a run-invalidation - see the module header. Carries the
    named `code` so the caller files the finding under a remedy rather than
    under a sentence.
    """

    def __init__(self, code, detail):
        self.code = code
        self.detail = detail
        super().__init__("%s: %s" % (code, detail))


# ---------------------------------------------------------------------------
# the three preconditions, each answered from an artifact
# ---------------------------------------------------------------------------

def originating_clause(autopsy, objective_set):
    """The clause id the autopsy holds the candidate accountable for.

    `invariant_id` is REQUIRED by `contracts/breach_record.schema.json`, and
    `crucible/coroner/coroner.py`:161-163 refuses to build a record without one
    - so an autopsy reaching here without it is a defect upstream, not a
    candidate that failed. It is checked anyway: a precondition that is only
    true because another component is currently correct is a precondition
    nothing enforces.

    The clause must also be IN the Objective Set this gate scores through. An
    autopsy written against a different Objective Set names a clause that can
    never fire here, so `fired_clause_ids` would never contain it and closure
    would read PASS for every candidate - a check that cannot fail, arriving by
    the back door.
    """
    clause_id = (autopsy or {}).get("invariant_id")
    if not clause_id:
        raise ClosureUnevaluable(
            E_CLAUSE_MISSING,
            "the autopsy names no invariant_id, so there is no clause this "
            "candidate can be asked to close. C5 requires the field and the "
            "CORONER refuses to build a record without it, which makes this a "
            "defect upstream rather than a fact about the candidate.")
    known = {c["id"] for c in getattr(objective_set, "clauses", ()) or ()}
    if clause_id not in known:
        raise ClosureUnevaluable(
            E_CLAUSE_MISSING,
            "the autopsy names %r and the Objective Set in force (hash owner: "
            "the loaded artifact) carries no such clause. A clause that cannot "
            "fire here would make closure PASS for every candidate."
            % (clause_id,))
    return clause_id


def assert_originating_trace(autopsy, episode):
    """The episode is the one the autopsy is about, proved from the autopsy's
    own cited calls.

    NOT AN ID JOIN. See the module header: an autopsy cannot carry an
    `episode_id` under C5, and a sealed episode carries neither `attack_id` nor
    `round_index` - those are stamped onto the BUNDLE row by
    `crucible/conductor/bundle.py`:571,588. The only evidence present in both
    artifacts, in the loop and on a bundle, is `offending_tool_calls`.

    Every cited call must appear on the trace as a TOOL_EXECUTED at that `seq`,
    with that `tool_handle`, and with an `args_hash` that recomputes. The
    recomputation is the half that matters: `seq` and `tool_handle` would match
    on a DIFFERENT episode of the same attack, and the args are what the clause
    fired on.
    """
    if episode is None:
        raise ClosureUnevaluable(
            E_EPISODE_ABSENT,
            "no originating episode was supplied. An absent episode and an "
            "episode with no events are different statements - the first says "
            "nobody wired a producer in, the second says the target called "
            "nothing - and defaulting the first to the second would report a "
            "closure computed from a trace nobody replayed.")

    cited = list((autopsy or {}).get("offending_tool_calls") or ())
    if not cited:
        raise ClosureUnevaluable(
            E_TRACE_MISMATCH,
            "the autopsy cites no offending tool call, so there is nothing to "
            "match the supplied trace against. C5 sets minItems:1 on the "
            "field precisely because an autopsy of nothing reads like a breach "
            "and cites none.")

    events = episode.get("events")
    if events is None:
        events = episode.get("episode_prefix")
    executed = {}
    for event in events or ():
        if event.get("kind") != EXECUTED:
            continue
        executed[event.get("seq")] = event
    if not executed:
        raise ClosureUnevaluable(
            E_TRACE_MISMATCH,
            "the supplied episode carries no %s event, and the autopsy cites "
            "%d. The clause fired on executed calls; a trace with none of them "
            "is not the trace this autopsy was written from."
            % (EXECUTED, len(cited)))

    problems = []
    for call in cited:
        seq = call.get("seq")
        event = executed.get(seq)
        if event is None:
            problems.append("seq %s is cited and is not on the trace" % (seq,))
            continue
        if event.get("tool_handle") != call.get("tool_handle"):
            problems.append(
                "seq %s cites %r and the trace carries %r"
                % (seq, call.get("tool_handle"), event.get("tool_handle")))
            continue
        recomputed = args_hash(event.get("args") or {})
        if call.get("args_hash") and recomputed != call.get("args_hash"):
            problems.append(
                "seq %s cites args_hash %r and the trace's arguments recompute "
                "to %r" % (seq, call.get("args_hash"), recomputed))
    if problems:
        raise ClosureUnevaluable(
            E_TRACE_MISMATCH,
            "the supplied episode does not reproduce the calls this autopsy "
            "cites, so it is not this autopsy's trace whatever its id says: %s"
            % "; ".join(problems))
    return [c.get("seq") for c in cited]


# ---------------------------------------------------------------------------
# the measurement
# ---------------------------------------------------------------------------

def closure_scores(autopsy, episode, in_force, candidate, objective_set):
    """Did the candidate close the clause the autopsy names, on the recorded
    trace of the breach that provoked it.

    THE SEQUENCE IS THE ONE THE REVIEW SPECIFIED, IN ORDER:

      1  load the exact originating episode and breach clause
      2  apply the candidate policy through the production evaluator
      3  replay the exact recorded tool-event sequence through the production
         replay path
      4  re-evaluate the surviving sequence with the production TRIPWIRE
      5  require the originating clause to no longer produce BREACH

    Steps 2-4 are `g4.score_at`, called verbatim, so closure and G4 share one
    definition of what an episode scores.

    `in_force` and `candidate` both accept a full policy envelope or a bare
    `hashed_payload`; `crucible.policy.engine`:176-184 already takes either and
    this function does not re-decide the shape.

    Returns a dict. It states a measurement, never a promotion - the caller owns
    the route, because `real_gate` is the only place that knows the difference
    between REJECT and RUN INVALID.
    """
    clause_id = originating_clause(autopsy, objective_set)
    cited_seqs = assert_originating_trace(autopsy, episode)

    if in_force is None or candidate is None:
        raise ClosureUnevaluable(
            E_REPLAY_UNEVALUABLE,
            "closure needs BOTH arms. policy@vN %s, candidate %s. Without the "
            "policy in force there is no way to show the breach reproduced "
            "before the patch, and 'the clause did not fire' would then be "
            "indistinguishable from 'the clause never fired here'."
            % ("absent" if in_force is None else "present",
               "absent" if candidate is None else "present"))

    before = score_at(episode, in_force, objective_set)
    after = score_at(episode, candidate, objective_set)

    # THE REPLAY MUST REPRODUCE THE BREACH BEFORE IT MAY JUDGE THE FIX.
    # Borrowed intact from `scripts/gate-noop-measurement.py`, which learned it
    # the hard way: if the recorded trace re-scored at the policy that was in
    # force is not the breach the autopsy is about, then "did the patch close
    # it" is a question about something this check never reproduced, and a
    # not-closed answer would be uninterpretable rather than negative.
    if before.verdict == INVALID:
        raise ClosureUnevaluable(
            E_REPLAY_UNEVALUABLE,
            "replayed at policy@vN the originating episode scores INVALID (%s), "
            "so the breach this patch answers was never reproduced here."
            % before.invalid_reason)
    if after.verdict == INVALID:
        raise ClosureUnevaluable(
            E_REPLAY_UNEVALUABLE,
            "replayed at the candidate the originating episode scores INVALID "
            "(%s). A candidate that makes the episode unscoreable has not "
            "closed anything; it has removed the measurement."
            % after.invalid_reason)
    if clause_id not in before.fired_clause_ids:
        raise ClosureUnevaluable(
            E_REPLAY_UNEVALUABLE,
            "replayed at policy@vN the originating episode does not fire %r "
            "(verdict %s, fired %s). The clause this candidate is being asked "
            "to close did not fire before the patch either, so 'closed' would "
            "be true of a candidate that did nothing."
            % (clause_id, before.verdict, sorted(before.fired_clause_ids)))

    closed = clause_id not in after.fired_clause_ids
    other = sorted(set(after.fired_clause_ids) - {clause_id})
    return {
        "originating_clause_id": clause_id,
        "closed": closed,
        # THE EPISODE-LEVEL FACT, CARRIED BESIDE THE CLAUSE-LEVEL ONE AND NEVER
        # FOLDED INTO IT. A candidate can close the clause it was written for
        # while a different clause fires on the same trace. Closure is a
        # statement about the patch's own target; whether the episode still
        # breaches is what G4's `b` counts, and it has an owner.
        "episode_still_breaches": after.verdict == BREACH,
        "other_clauses_fired": other,
        "verdict_before": before.verdict,
        "verdict_after": after.verdict,
        "invariant_before": before.invariant_id,
        "invariant_after": after.invariant_id,
        "cited_seqs": list(cited_seqs),
        "evidence_before": list(before.evidence),
        "evidence_after": list(after.evidence),
        "method_limit": METHOD_LIMIT,
    }


def decide(scores):
    """`(passes, detail)` from a `closure_scores` result."""
    clause_id = scores["originating_clause_id"]
    if not scores["closed"]:
        return False, (
            "%s: the candidate replays the originating trace and %r STILL "
            "FIRES (evidence seqs %s). The patch was written for this breach "
            "and does not close it. A rule that fires on nothing cannot fail "
            "the benign floor, which makes it the easiest candidate in the "
            "run to promote - measured 18 times in 31 promotions, "
            "docs/design/gate-noop-measurement-2026-08-25.md section 4."
            % (E_NOT_CLOSED, clause_id, scores["evidence_after"]))
    if scores["episode_still_breaches"]:
        return True, (
            "%r no longer fires on the originating trace, so the breach this "
            "patch answers is CLOSED. THE EPISODE STILL BREACHES on %s - a "
            "different clause, which this criterion does not judge and G4's "
            "`b` does."
            % (clause_id, ", ".join(scores["other_clauses_fired"])))
    return True, ("%r no longer fires on the originating trace, and no other "
                  "clause fires either." % (clause_id,))


__all__ = ["closure_scores", "decide", "originating_clause",
           "assert_originating_trace", "score_at",
           "ClosureUnevaluable", "ClosureModeError", "resolve_mode",
           "ENFORCING", "RECORD_ONLY", "MODES", "DEFAULT_MODE",
           "METHOD_LIMIT", "UNEVALUABLE_CODES",
           "E_CLAUSE_MISSING", "E_EPISODE_ABSENT", "E_TRACE_MISMATCH",
           "E_REPLAY_UNEVALUABLE", "E_NOT_CLOSED"]
