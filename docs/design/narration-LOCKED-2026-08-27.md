# LOCKED RECORDING SCRIPT — N1 to N5

**Locked 2026-08-27 evening. Every figure re-verified from source that day**, not
carried from the 08-24 stamp. Provenance: `docs/design/narration-chunks.md`.

**N6 to N9 are not here and are not recordable.** N6 to N8 read figures from a
run; N9 is the held-out block and is gated on the **2026-08-28 unseal**.

## How to record

- **One take per chunk.** They cut together; a fluffed line costs one chunk.
- **Two seconds of silence** at the head and tail of every take.
- **60 seconds of room tone** before you start anything.
- Read at a normal pace. The timings below are targets, not constraints — if a
  chunk runs long, that is the cue list's problem, not yours.

## Changes from the previous draft, and why

1. **N4 says "nine known-bad fixtures the tripwire must always fail."** There are
   now two nine-fixture known-bad suites in the tree — the tripwire's and the
   offline reader's, added 2026-08-27. The old wording was ambiguous. The new
   wording disambiguates at no extra length.
2. **N5 is version B, and version B only.** "The bundles are in the repo" is
   false today: `evidence/` is gitignored and `git ls-files evidence/*` returns
   zero. Version B is true right now and stays true whether or not a bundle ships.
3. Everything else is unchanged from the corrected 08-24 script.

## Amendment, 2026-08-29 — N4's boundary line, and nothing else

**"Left of this line" became "Above this line", and "Right of it" became
"Below it".** Eric's call, made before the take.

The words and the picture disagreed. `loop.svg` draws the trust boundary
HORIZONTALLY: its own `<desc>` reads *"a horizontal trust boundary separates the
four model-bearing components above it from the thirteen pure-code components
below it."* The line was written against an earlier left/right composition and
was never re-read against the plate that replaced it.

This is the whole amendment. The claim is identical, the length is identical,
and every figure in this file stands as verified on 08-27. **Nothing else in
N1 to N5 changes**, and this file remains locked verbatim.

Corrected in the same pass: `narration-print.html` (the read-from copy),
`narration-tonight.md` (the superseded 08-24 draft, which carried the dead
wording where a wrong-file open would find it), and the conflict note in
`docs/diagrams/loop-cues.json`, which recorded the disagreement rather than
resolving it because resolving it was not the cue file's call to make.

---

## N1 · 0:00–0:12 · cold open, no title card

**ON SCREEN:** refund agent UI. Type: *I got a cracked mug in order 4471, it was
$34.* Trace shows `lookup_order` then `issue_refund(amount_minor=3400)`.

**SAY:**

```
This is a customer service agent with permission to move money.
```

---

## N2 · 0:12–0:25 · establish that it really moves money

**ON SCREEN — type exactly this. The old `amount_cents` version errors live:**

```
sqlite3 ledger.db "select order_id, amount_minor, ts from refunds order by ts desc limit 1"
```

**SAY:**

```
That's not a mock response. The ledger moved.

Now the same agent on a nine hundred dollar claim.
```

*(let it escalate on screen)*

```
It's a good agent. It follows its policy.

Which is the problem. Its policy is a paragraph of English, and English is
attackable.
```

---

## N3 · 0:25–0:50 · the friction

**ON SCREEN:** one slide — *find the breach · patch it · prove the patch didn't
break the business.*

**SAY:**

```
Before you deploy an agent with real permissions, someone has to find out what
it does under pressure.

Today that's a person writing prompts by hand until they get bored. There's no
regression suite, so last week's fix is untested this week.

CRUCIBLE automates that loop. And more importantly, it refuses to ship a fix it
can't prove.
```

---

## N4 · 0:50–1:35 · architecture · diagram on screen throughout

**The animation is cued to this beat. Its real length sets the cue list.**

**Three claims in this beat are said on camera and were verified from source on
2026-08-24 and again on 2026-08-27.** No fix field:
`contracts/breach_record.schema.json` is `additionalProperties: false` and
carries no fix, patch or remediation property. No write access:
`gcloud storage buckets get-iam-policy gs://crucible-policies-x7` returns six
role bindings and `crucible-coroner` appears in none of them. The adapter
subtree claim is `crucible/armorer/adapter.py`, which projects by allow-list.
**Re-verify before recording; do not recall.**

**SAY:**

```
A red team model writes six attacks a round against the target.

The attack corpus was authored, then sealed and committed before the first
patch existed. That commitment is public and timestamped, and the identity that
writes patches cannot read the sealed set.

The tripwire is pure code. No model. It rules from the actual tool call trace,
not from anything the agent said, against eleven clauses.
```

**The next three sentences were verified from source 2026-08-27. Re-verify
before recording; do not recall.** No fix field:
`contracts/breach_record.schema.json` is `additionalProperties: false`. No write
access: `crucible-coroner` appears in none of the six role bindings on
`gs://crucible-policies-x7`. The subtree claim is `crucible/armorer/adapter.py`,
which projects by allow-list.

**SAY, continuing without a pause** (all three claims verified from source 2026-08-27):

```
The coroner writes the autopsy and structurally cannot propose a fix. There is
no fix field in its schema, its findings sit in a subtree the armorer's input
adapter cannot address, and its service account has no write access to the
policy bucket. That's an IAM policy, not a prompt instruction.

The armorer gets structured fields only, and patches in three verbs. Deny.
Constrain argument. Require approval. There is no allow verb, so no sequence of
patches can widen what the agent is permitted to do. The predicates reference
trace facts and never match strings. That constraint is the whole design.

The compiled policy runs as a plugin callback, before the agent's own callbacks,
and a non-None return skips execution. So the policy cannot be argued with by
the agent it governs.

Then the regression warden, also pure code. Twenty six benign fixtures, fourteen
of them near misses, and the patch has to leave all twenty six passing.

The gate promotes only if attack success falls AND benign is exactly one hundred
percent.
```

**Then the cursor lands on the trust boundary line:**

```
Above this line is model generated and untrusted. Below it is
deterministic code.

No model ever decides whether a breach happened.
```

---

## N5 · 1:35–1:43 · the honesty beat

**Say "five locks", never "five hashes".** Five locks occupy six fields —
ruling 20 split the fifth into the corpus and Part B, frozen together. Both are
true and neither is the other, and "five hashes" is the one a judge reading the
repo can catch.

**SAY:**

```
Everything from here is replayed from stored evidence bundles, recorded
offline.

Vertex runs on dynamic shared quota, so a multi-minute live loop on camera is a
risk I'm not taking.

Every bundle carries five locks. The gate rule, the frozen target agent, the
capability manifest, the Objective Set that defines what counts as a breach,
and the corpus. All committed before the first measurement, and the replay tool
needs no credentials to check them.
```

---

## STOP HERE

N6 through N9 are blocked. Do not improvise them.
