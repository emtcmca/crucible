"""episode.py - sealing a recorded episode into the object the evaluator scores.

THE SECOND SEAM W2 FOUND WITH NO OWNER, and it is the same shape as the first.

`crucible.plugin.EpisodeLedger` records C1 ToolEvents. It knows the episode id
and the calls, and it knows nothing about which policy version was in force or
which Objective Set defines breach -- correctly, because the enforcement point
must not depend on the evaluator.

`crucible.tripwire.evaluate_episode` refuses to score an episode that does not
carry `objective_set_hash`, `manifest_hash` and `derived_schema_hash`. Also
correctly: an episode not stamped with the hash of the definition of breach
cannot be scored, because nothing afterward could say WHICH RULER it was
measured with, and a breach count whose definition is unrecoverable is not a
measurement. That is G1(b).

Both sides are right and neither can do this. The first end-to-end run returned
`E_MISSING_OBJECTIVE_SET_HASH` on all four episodes, which read like a bug in
the evaluator and was actually a missing component.

WHY THE HASHES ARE COPIED FROM THE RUN MANIFEST AND NEVER RECOMPUTED HERE
-------------------------------------------------------------------------
Recomputing them at seal time would let an episode be stamped with the hash of
whatever is on disk NOW rather than what was in force when the calls were made.
The two differ exactly when something changed mid-run, which is the one case the
stamp exists to detect. So this copies, and the evaluator then checks the copy
against the Objective Set it actually loaded -- two independent values that must
agree, rather than one value compared to itself.

THE `outcome` KEY, FIXED 2026-08-22
------------------------------------
`target_fault=True` used to write ONLY `raw["target_fault"] = True`.
`crucible.tripwire.evaluator.evaluate_episode` and every `strawman.py` verdict
path read `episode.outcome == "TARGET_FAULT"` -- a DIFFERENT key -- to decide
the same question. The two never rendezvoused: an episode sealed the obvious
way scored as an ordinary CLEAN/BREACH, silently. `crucible.conductor.real_target`
found this while wiring the real target and worked around it there, stamping
`raw["outcome"]` itself after calling this function.

`outcome` is the key every committed artifact actually agrees on --
`tests/golden_traces/T1-*`, `T2-*` stamp `"outcome": "completed"` and
`tests/golden_traces/T3-target-fault-is-neither-breach-nor-non-breach.json`
stamps `"outcome": "TARGET_FAULT"` with NO `target_fault` boolean key present
at all. `crucible.tripwire.model.Episode.outcome` reads `raw.get("outcome")`.
`crucible.conductor.campaign`'s stand-in target already stamps
`"outcome": "completed"` on its own episodes for the same reason. The episode-
level `target_fault` boolean was never part of C1/C6 or any golden trace --
the field of that name in `contracts/verdict.schema.json` belongs to the
VERDICT the evaluator produces, a different object entirely, computed FROM
`outcome` by `evaluate_episode`. So this writes `outcome` directly and does
not also write a second, uncommitted `target_fault` key -- one mechanism,
matching the artifacts that already existed, rather than two spellings that
can drift apart again the way `ALLOW`/`allow` did.
"""

from ..policy.episode import EPISODE_PREFIX


class EpisodeSealError(ValueError):
    pass


def seal_episode(ledger, run_manifest, *, episode_context=None,
                 target_fault=False, target_responded=None):
    """Return the raw episode dict `crucible.tripwire.Episode` accepts.

    `target_fault` marks an episode the target crashed in. It is NEITHER breach
    nor non-breach: it is removed from the denominator and logged. Counting a
    crash as "attack failed" would let a FRAGILE target render as a HARDENED
    one, which is the most flattering error available in this build.

    `target_responded` IS THREE-VALUED AND `None` IS NOT `False`. It is the
    stamped harness fact behind the `E_NO_EVENTS` split (Eric's ruling
    2026-08-25; `docs/design/e-no-events-split-design-2026-08-25.md`): did the
    target produce a substantive text reply. `True`/`False` are written; `None`
    LEAVES THE KEY ABSENT, because "the record does not say" must have exactly
    one spelling on disk and a defaulted `False` would print "the target said
    nothing" off a record that never looked. That is the overclaim
    `tests/test_overclaim.py` exists to catch, and it is why
    `crucible.tripwire.evaluator` has a third code,
    `E_NO_EVENTS_REPLY_UNRECORDED`, rather than two.

    IT IS A BOOLEAN AND NEVER THE TEXT. The reply itself is not written here
    and must not be: `crucible.tripwire.model.Episode.transcript` is documented
    PRESENT AND NEVER READ, and the whole claim of this project is that policy
    binds to what a trace RECORDS, not what a message SAYS. The caller decides
    what "substantive" means once, at the moment it observes the events, the
    same shape C6 already demands of `channel` -- "a HARNESS fact, stamped --
    never inferred from the transcript". A non-boolean is refused rather than
    coerced: a stamp that is not a stamp is not evidence.
    """
    for attr in ("objective_set_hash", "manifest_hash", "derived_schema_hash"):
        if not getattr(run_manifest, attr, None):
            raise EpisodeSealError(
                "the run manifest carries no %s, so this episode cannot be "
                "scored. An episode without it is unscoreable rather than "
                "clean -- G1(b)." % attr)

    raw = {
        "episode_id": ledger.episode_id,
        "events": list(ledger.events),
        "objective_set_hash": run_manifest.objective_set_hash,
        "manifest_hash": run_manifest.manifest_hash,
        "derived_schema_hash": run_manifest.derived_schema_hash,
        "policy_version": getattr(run_manifest, "policy_version", None),
        "policy_hash": getattr(run_manifest, "policy_hash", None),
        # See "THE `outcome` KEY" above: this is the one key every consumer
        # and every golden trace actually reads. "completed" is not load-
        # bearing for anything except != "TARGET_FAULT"; it is written for
        # the same reason campaign.py's stand-in writes it -- an episode
        # dict a human is looking at should never have to leave this field
        # absent to mean "fine".
        "outcome": "TARGET_FAULT" if target_fault else "completed",
    }
    if isinstance(target_responded, bool):
        # `isinstance` and not truthiness. `"yes"` is truthy in Python and would
        # become a silent True; a stamp the harness never took must stay absent.
        raw["target_responded"] = target_responded
    if episode_context is not None:
        # Ruling 16 and C6: the FROZEN episode.* block travels with the episode.
        # Without it the episode-scoped predicates cannot be replayed, and
        # replay soundness is what makes them count as pure.
        raw["episode_frozen_context"] = _freeze_block(episode_context)
    return raw


def _freeze_block(ctx):
    for attr in ("as_dict", "to_dict", "frozen"):
        fn = getattr(ctx, attr, None)
        if callable(fn):
            return _debare(fn())
        if isinstance(fn, dict):
            return _debare(dict(fn))
    if isinstance(ctx, dict):
        return _debare(dict(ctx))
    out = {}
    for name in ("account_holder_email", "account_holder_id",
                 "order_payment_instrument_id"):
        v = getattr(ctx, name, None)
        if v is None and hasattr(ctx, "context"):
            v = getattr(ctx.context, name, None)
        if v is not None:
            # BARE NAME, NOT PREFIXED. C10's schema says the prefix "is the only
            # thing it could be, and a prefix that is always the same is a second
            # place to make a typo" -- and the evaluator and every trace fixture
            # read bare names. This wrote "episode.account_holder_email" and the
            # mismatch was invisible until an Objective Set clause reached for
            # the block, at which point a CORRECT episode scored INVALID and the
            # error blamed the recorder for the reader's key.
            out[name] = v
    if not out:
        raise EpisodeSealError(
            "could not read the frozen episode.* block off %r. It must travel "
            "with the episode or the episode-scoped predicates cannot be "
            "replayed." % type(ctx).__name__)
    return out


def _debare(fields):
    """Strip the `episode.` prefix, so every caller lands on the same shape
    the manual fallback path above already produces.

    `crucible.policy.episode.EpisodeContext.as_dict()` returns keys PREFIXED
    (`"episode.account_holder_email"`) -- correct for that class, whose own
    `.get()` accepts either spelling and whose write-refusal path matches
    against `EPISODE_PREFIX`-prefixed call arguments. But
    `crucible.tripwire.objective_set._context()` and every
    `episode_frozen_context` in the golden traces (`tests/golden_traces/
    objective_set.json`, `T1`-`T3`) read BARE keys, because `context_field` on
    a compiled clause is bare (`crucible/dsl/parser.py` never qualifies it).
    Passing the `as_dict()` result straight through reintroduced the exact
    prefixed/bare mismatch the fallback path below was written to fix, for
    any `episode_context` object that happens to expose `as_dict()`/`to_dict()`/
    `frozen`. Idempotent: a dict that is already bare passes through
    unchanged, so this is safe to apply unconditionally rather than only when
    a prefix is detected."""
    return {
        (k[len(EPISODE_PREFIX):] if k.startswith(EPISODE_PREFIX) else k): v
        for k, v in fields.items()
    }
