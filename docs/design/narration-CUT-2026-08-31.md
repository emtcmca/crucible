# RECORDING SCRIPT — the cut that fits

**Written 2026-08-31.** This is the script to read. It **supersedes**
`narration-LOCKED-2026-08-27.md` (N1–N5) and
`narration-N6-N9-2026-08-30.md` (N6a–N9) as the read-from copy. Both survive
unchanged as history and as the source of every claim below.

## Why it exists

The full script ran **988 spoken words — 6:35 at a natural 150 wpm** against a
**hard 4:00 cap**, which leaves 237 seconds for speech after the title card.
It was 2:38 over. Nobody had added it up; the cue file had recorded its own
version of the problem since it was written — *"263 words does not fit 45000
ms. That is 350 wpm"* — but that note was about N4 alone.

**Nothing here is a new claim.** Every sentence is a shortened form of one that
was already verified from source. What was cut is elaboration, second examples,
and the third and fourth ways of saying a thing that had already landed.

## What was deliberately NOT cut, and why

These survive because removing them would turn a narrow true statement into a
wider false one, which is this project's most-recorded defect:

| kept | because |
|---|---|
| *"no model ever decides whether a breach happened"* | the thesis. Everything else is support |
| **five locks**, never "five hashes" | five locks occupy six fields (CONVENTIONS ruling 20); "five hashes" is the version a judge reading a bundle can catch |
| the batches **disagree** | the replication pre-registration requires the disagreement to travel *with* the pooled figure, not sit under it |
| *"twenty of twenty"* | the figures ruling makes the reader-acceptance count part of the claim |
| Gemma **classifies** | ADR-0018 withdrew the corpus-generation claim in terms. Classification, never generation |
| *no users · not reviewed by Google · still sealed* | the honesty floor. Cutting the caveats to save eight seconds is the one cut that would cost the submission its argument |

**The denominators moved from speech to the card.** N7's card shows `70/520`
and `56/725` and all three rows at once, so the spoken line does not recite
them. The claim as published still carries them — that is what the ruling
requires — it is just read rather than heard.

---

## N1 · cold open

**SAY:**

```
This is a customer service agent with permission to move money.
```

---

## N2 · it really moves money

**SAY:**

```
That's not a mock response. The ledger moved.

Same agent, nine hundred dollars. It escalates instead — it follows its
policy. Which is the problem. That policy is a paragraph of English, and
English is attackable.
```

---

## N3 · the friction

**SAY:**

```
Before you deploy an agent with real permissions, someone has to find out what
it does under pressure.

Today that's a person writing prompts by hand, with no regression suite. Last
week's fix is untested this week.

CRUCIBLE automates that loop, and refuses to ship a fix it can't prove.
```

---

## N4 · architecture

**The longest beat, and still the longest after the cut.** The animation
retimes to whatever this take runs — do not rush it to hit a number.

**SAY:**

```
A red team model writes six attacks a round, from a corpus sealed before the
first patch existed.

The tripwire is pure code. It rules from the actual tool-call trace, not from
anything the agent said.

The coroner writes the autopsy and structurally cannot propose a fix. No fix
field in its schema, and no write access to the policy bucket. That's IAM, not
a prompt.

The armorer patches in three verbs. Deny. Constrain argument. Require
approval. No allow verb, so no patch can widen what the agent may do.

Then a pure-code warden replays twenty-six benign fixtures. All must pass.
```

*(the cursor lands on the boundary line)*

```
Above this line is model generated and untrusted. Below it is deterministic
code.

No model ever decides whether a breach happened.
```

---

## N5 · the honesty beat

**The five locks are LISTED ON THE CARD.** They were in the spoken line too,
which is the same list twice and cost thirty seconds against a hard cap. The
card names all five; the voice says how many and what they mean. **Say "five
locks", never "five hashes"** - five locks occupy six fields, and "five hashes"
is the version a judge reading a bundle can catch.

**SAY:**

```
Everything from here is replayed from stored evidence bundles.

Every bundle carries five locks, all committed before the first measurement.
The replay tool needs no credentials to check them.
```

---

## N6a · the Google Cloud proof

**SAY, over the four frames:**

```
Cloud Run, serving, under its own service account — not the default one.

Vertex AI, where every model call in the loop goes. Three buckets: evidence,
policies, and the sealed holdout the attacking identity cannot read.

And Gemma, on Vertex Model Garden. It's the capability cartographer — it
classifies every tool the target agent holds, before any attack runs.
```

---

## N6b · what that produced

**SAY:**

```
Two batches. Twenty runs each, identical configuration, one pre-registered as
a replication of the other before it ran. The offline reader accepts twenty of
twenty bundles in both.

That reader takes no credentials. It re-derives every lock from the bundle
bytes.
```

---

## N7 · the figure

**ON SCREEN: all three rows.** The spoken line no longer recites the
denominators because the card carries them.

**SAY:**

```
Pooled across both batches, attack success falls from thirteen and a half
percent against the bare agent to seven point seven at the final policy.

And the two batches disagree. A replication that contradicts the first batch
doesn't retire the first batch. It retires the claim that one batch was
enough.

One target agent. One sample per episode. No stability estimate.
```

---

## N8 · the negative finding

**SAY:**

```
The most substantive thing we measured is negative, and it's about the harness
not the agent.

Thirty-two rules promoted. Thirteen closed the breach they were written for.
Nineteen were no-ops.

The gate promoted all nineteen. It checked the patch was well formed and that
benign traffic survived. It never checked that it closed the breach.

We found it by recounting a number we'd already published. It got worse.
```

---

## N9a · what this is not

**STATE CHECK BEFORE THE TAKE.** The sealed line is a claim about machine state
and it expires. Re-verify immediately before recording:

```
python scripts/pre-read-seal-proof.py     # must print VERDICT PASS
```

**SAY:**

```
What this is not. Eleven days, one person, one target agent. No users. Not
reviewed or endorsed by Google. The held-out family is still sealed. I
won't describe a result I don't have.
```

---

## N9b · the close

**ON SCREEN:** the close card.

**SAY:**

```
Every boundary in here is a component deliberately blind to something. The
coroner can't propose a fix. The armorer has no allow verb.

That's not a prompt. It's a schema, an IAM policy, and a grammar.
```

---

## STOP

Do not improvise a result from the sealed family. It has not been run.
