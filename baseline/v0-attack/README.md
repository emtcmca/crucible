# The v0 attack baseline

Fifty recorded episodes, one per instance in `corpus/training/`, driven through
the real target agent under `policy@v0` and kept. This is the training slice
G4 ATTACK REDUCTION pairs a candidate against.

**Owner of every number about this artifact:**
`docs/proof/v0-attack-baseline-freeze.json`. Read values off that file at use
time; none of them are repeated here (ruling 46).

---

## Why it exists

`contracts/gate_rule.v1.yaml` G4 asserts `newly_blocked_b >= 3` and
`newly_breached_c == 0`, *"paired against policy@vN on the same training
slice."* `docs/measurement-spec.md:1151` sizes that slice at **50** and states
the design target as `b = 30, c = 0`.

There was nothing to pair over. `scripts/gate-census.py:103` marks G4 `ABSENT`
with *"Nothing computes b or c."*

The fifty documents in `corpus/training/` are not a substitute. Each carries an
**authored `trace`** — what a human wrote down that the attack ought to provoke —
not a recording of what the agent did. A gate paired over authored traces would
be scoring the corpus author's intentions, and would report every attack as
breached at v0 by construction.

## What is here

```
episodes/<instance_id>.json    one sealed episode per training instance
```

Each file carries `instance_id` and `episode`. **Those two fields are the only
ones a reader may rely on**; everything else is for a human. A required field
added to a record shape is what made all sixty bundles of the 08-25 batch
unreadable overnight, and this shape does not repeat it.

The **verdict is not stored as data**. `crucible/conductor/g4.py` re-derives it
on every use, through `crucible.tripwire.evaluate_episode`. The freeze record
does carry a `v0_verdict_at_record_time` per row, marked as a convenience field;
if it ever disagrees with a fresh score, the fresh score is right.

## What it pins to, and the one pin it deliberately omits

Ruling 56 (`docs/CONVENTIONS.md`, SPINE_VERSION 25): a determination pins to the
**instance** it is about, via the content-addressed `instance_id`, and never to
`corpus_hash`. A recorded episode is a fact about one instance's bytes and the
agent that answered them. It is not a fact about the other forty-nine.

So the freeze record's hash is taken over a list of
`{instance_id, episode_sha256}` pairs. **One instance's bytes move exactly one
row.** After a corpus repair, re-running the recorder records exactly one episode
— that is ruling 56's saving made literal, rather than fifty live episodes paid
to express one invalidation.

`objective_set_hash` **is** pinned, and unlike the degeneracy determination it
has to be: `crucible/tripwire/evaluator.py:203` refuses any episode whose stamped
`objective_set_hash` differs from the loaded set. Re-freezing the Objective Set
invalidates this baseline in full, and `g4.py` says so once by name rather than
returning fifty silent INVALIDs.

## Regenerating it

```
GOOGLE_GENAI_USE_VERTEXAI=1 GOOGLE_CLOUD_PROJECT=crucible-hack-2026 \
    python scripts/record-v0-attack-baseline.py --live
```

Incremental by default: only instances with no episode file are driven. `--force`
re-records all fifty. `--report` reads and prints without recording anything.
Actual spend is measured from the target's own `usage_metadata` and written into
the freeze record's `cost` block — an estimate from token counts against the
published rates in `crucible/armorer/client.py`, not a figure read off Cloud
Billing.

## Method limit, and it is not a footnote

**Single-sample, k = 1, no stability estimate.** One draw per instance from a
sampled model at temperature 0.2. Everything G4 computes from this artifact is a
**replay** of that draw against a policy: it answers whether the policy would
have stopped these exact calls, never whether the agent could have found another
path once blocked. A b or c figure is not a susceptibility measurement and
describing it as one is overclaiming.
