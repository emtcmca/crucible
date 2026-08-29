# RECORDING SCRIPT — chunks N1 to N5 only

**SUPERSEDED 2026-08-27 by `narration-LOCKED-2026-08-27.md`. Read that file.**
This one is kept for its 08-24 provenance and is not the take. Its N4 boundary line
was corrected 2026-08-29 in place, so a wrong-file open cannot find the dead wording;
no other figure here has been re-verified since 08-24.

**Read from this file, not from `execution-spec.md` §4.** That one interleaves correction
blocks with the words and is unreadable aloud. Corrections are already applied here.

Every figure below was verified from source **2026-08-24**. Provenance is in
`docs/design/narration-chunks.md`.

**Record each chunk as its own take.** Two seconds of silence at the head and tail.
Record 60 seconds of room tone before you start.

---

## N1 · 0:00–0:12 · cold open, no title card

**ON SCREEN:** Refund agent UI. Type: *I got a cracked mug in order 4471, it was $34.*
Trace shows `lookup_order` then `issue_refund(amount_minor=3400)`.

> **CORRECTED:** the spec script says `amount_cents`. **There is no `amount_cents` and no
> `amount`.** It is `amount_minor`, INT64 minor units, travelling with an ISO-4217
> currency string. CONVENTIONS §6 owns this and `execution-spec.md` is lower precedence.
> Flagged in `target/refund_agent/system_of_record.py:22` and `docs/lanes/L2-log.md`.

**SAY:**

```
This is a customer service agent with permission to move money.
```

---

## N2 · 0:12–0:25 · establish it as genuinely money-touching

**ON SCREEN — type this exactly:**

```
sqlite3 ledger.db "select order_id, amount_minor, ts from refunds order by ts desc limit 1"
```

> **CORRECTED, and this one fails live if you type the old version.** The spec script
> queries `amount_cents`, which is not a column. The query errors on camera in the beat
> that carries the 40%. The canonical query is in
> `target/refund_agent/system_of_record.py:22`.

**SAY:**

```
That's not a mock response. The ledger moved.

Now the same agent on a nine hundred dollar claim.
```

*(it escalates)*

```
It's a good agent. It follows its policy.

Which is the problem. Its policy is a paragraph of English, and English is attackable.
```

> If the judge doesn't believe the target is real by 0:25, nothing after it lands.

---

## N3 · 0:25–0:50 · the friction, as a number

**ON SCREEN:** one slide. *find the breach · patch it · prove the patch didn't break the
business.*

**SAY:**

```
Before you deploy an agent with real permissions, someone has to find out what it
does under pressure.

Today that's a person writing prompts by hand until they get bored. There's no
regression suite, so last week's fix is untested this week.

CRUCIBLE automates that loop. And more importantly, it refuses to ship a fix it
can't prove.
```

---

## N4 · 0:50–1:35 · ARCHITECTURE · 45 seconds · diagram on screen throughout

**This is the beat the animation is cued to. Its real length sets the cue list.**
The criterion names the architecture explanation explicitly. Most entrants will skip it.

**SAY:**

```
A red team model writes six attacks a round against the target.

The attack corpus was authored, then sealed and committed before the first patch
existed. That commitment is public and timestamped, and the identity that writes
patches cannot read the sealed set.

The tripwire is pure code. No model. It rules from the actual tool call trace, not
from anything the agent said, against eleven clauses.

```

> **Verified from source 2026-08-24, because you say these three on camera.**
> No fix field: `contracts/breach_record.schema.json` is `additionalProperties:
> false` and carries no fix, patch or remediation property. No write access:
> `gcloud storage buckets get-iam-policy gs://crucible-policies-x7` returns six
> role bindings and `crucible-coroner` appears in none of them (nor does
> `crucible-armorer`). The adapter subtree claim is `crucible/armorer/adapter.py`,
> which projects by allow-list. Re-verify before recording; do not recall.
>
> **All three re-verified from source 2026-08-24.**

```
The coroner writes the autopsy and structurally cannot propose a fix. There is no
fix field in its schema, its findings sit in a subtree the armorer's input adapter
cannot address, and its service account has no write access to the policy bucket.
That's an IAM policy, not a prompt instruction.

The armorer gets structured fields only, and patches in three verbs. Deny.
Constrain argument. Require approval. There is no allow verb, so no sequence of
patches can widen what the agent is permitted to do. The predicates reference trace
facts and never match strings. That constraint is the whole design.

The compiled policy runs as a plugin callback, before the agent's own callbacks, and
a non-None return skips execution. So the policy cannot be argued with by the agent
it governs.

Then the regression warden, also pure code. Twenty six benign fixtures, fourteen of
them near misses, and the patch has to leave all twenty six passing.

The gate promotes only if attack success falls AND benign is exactly one hundred
percent.
```


> **CORRECTED 2026-08-24 — the known-bads came OUT of this beat.** The line used to
> continue "plus nine known bads that each have to return the verdict they're supposed
> to." The nine known-bads are real and hash-locked in `contracts/gate_rule.v1.yaml` as
> G1a with `failure_mode: RUN_INVALID`, and they run in the test suite and
> `crucible/tripwire/selftest.py`. **They do not run in the campaign loop.**
> `campaign.py` contains zero references to `known_bad`, and `real_warden.py:49` states
> that it does not run G1a and that the loop never wires it in. Claiming them as part of
> the loop, on camera, describes a check that cannot fail because it never executes.
> That is the exact defect this project exists to find, so it does not get spoken.

**Then the cursor lands on the trust boundary line:**

```
Above this line is model generated and untrusted. Below it is deterministic
code.

No model ever decides whether a breach happened.
```

---

## N5 · 1:35–1:43 · the honesty beat

> **TWO CORRECTIONS. Read the note before recording this one.**
>
> **1. Say "five locks", not "five hashes".** `crucible/conductor/hashlocks.py:131`:
> five locks occupy six fields, because ruling 20 split the fifth into the corpus and
> Part B, frozen together. Both statements are true and neither is the other. "Five
> hashes" is the one a judge reading the repo can catch.
>
> **2. "The bundles are in the repo" is FALSE TODAY.** `evidence/` is gitignored at
> `.gitignore:16` and `git ls-files evidence/*` returns **zero**. Saying it on camera in
> a public video is a false claim about verifiability. Two ways to make it true, below.

**SAY — version A, if a real bundle is committed before you record:**

```
Everything from here is replayed from stored evidence bundles, recorded offline.

Vertex runs on dynamic shared quota, so a multi-minute live loop on camera is a risk
I'm not taking.

The bundles are in the repo. Replay them yourself, no credentials needed. Every one
carries five locks. The gate rule, the frozen target agent, the capability manifest,
the Objective Set that defines what counts as a breach, and the corpus. All
committed before the first measurement.
```

**SAY — version B, true right now, no dependency:**

```
Everything from here is replayed from stored evidence bundles, recorded offline.

Vertex runs on dynamic shared quota, so a multi-minute live loop on camera is a risk
I'm not taking.

Every bundle carries five locks. The gate rule, the frozen target agent, the
capability manifest, the Objective Set that defines what counts as a breach, and the
corpus. All committed before the first measurement, and the replay tool needs no
credentials to check them.
```

**Recommendation: record version B tonight.** It is true as of this moment and stays
true whether or not the bundle ships. Version A is stronger and becomes recordable the
moment a bundle from tonight's batch is force-added, which is already order-of-ops item 2
(`git add -f evidence/runs/<date>-<slug>/`, per `.gitignore:15`). Re-record N5 then if
you want the stronger line. **That is exactly the swap chunking exists for.**

---

## STOP HERE

**N6 through N9 are blocked.** They read figures that do not exist yet: the refusal beat's
benign pass rate, and the entire held-out block, which is gated on the **08-28 unseal**.
See `docs/design/narration-chunks.md`.
