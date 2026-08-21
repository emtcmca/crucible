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
"""


class EpisodeSealError(ValueError):
    pass


def seal_episode(ledger, run_manifest, *, episode_context=None,
                 target_fault=False):
    """Return the raw episode dict `crucible.tripwire.Episode` accepts.

    `target_fault` marks an episode the target crashed in. It is NEITHER breach
    nor non-breach: it is removed from the denominator and logged. Counting a
    crash as "attack failed" would let a FRAGILE target render as a HARDENED
    one, which is the most flattering error available in this build.
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
    }
    if episode_context is not None:
        # Ruling 16 and C6: the FROZEN episode.* block travels with the episode.
        # Without it the episode-scoped predicates cannot be replayed, and
        # replay soundness is what makes them count as pure.
        raw["episode_frozen_context"] = _freeze_block(episode_context)
    if target_fault:
        raw["target_fault"] = True
    return raw


def _freeze_block(ctx):
    for attr in ("as_dict", "to_dict", "frozen"):
        fn = getattr(ctx, attr, None)
        if callable(fn):
            return fn()
        if isinstance(fn, dict):
            return dict(fn)
    if isinstance(ctx, dict):
        return dict(ctx)
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
