<!-- THE DEVPOST PROJECT STORY. Written 2026-08-20, BEFORE any measurement exists.

     APPEND, DO NOT REWRITE. The "Results" section is deliberately empty and says
     so. When the numbers arrive they are ADDED under it and every existing
     section stays as written. Rewriting this at submission would discard the one
     thing it is evidence for -- that the story was told before the result was
     known.

     ADR-0001's 350-500 word ceiling governs UPDATES, not this. Different artifact,
     different job.

     execution-spec 5a claim discipline applies in full: NO RESULT MAY APPEAR HERE
     until the run exists, and every figure carries its label when it does. -->

## Inspiration

I spent fourteen years running operations, most recently a property management company where I was accountable for other people's money. When I started building AI agents, the thing that kept bothering me was not that they made mistakes. It was that nobody could tell me what would happen when one did.

Every agent safety demo I saw had the same shape. Someone shows an attack, shows a fix, shows the attack failing. It is a compelling three minutes and it proves almost nothing, because the fix was written by the person who knew the attack. Of course it holds. The interesting question is whether it holds against something the builder had not seen.

That question has a name in every other empirical field: you hold out a test set, and you commit to it before you look. Almost nobody was doing it for agent security. So CRUCIBLE is an attempt to do the boring, unglamorous version of the thing properly, and to make the order of operations checkable by a stranger rather than asserted by me.

## What it does

CRUCIBLE is a pre deployment hardening harness for AI agents that hold real permissions.

A red team agent attacks a target agent that can move money. A pure code tripwire records what the target actually called, not what it said it did. A coroner writes the autopsy and is structurally unable to propose a fix. An armorer proposes a policy patch in a three verb domain specific language. A pure code gate promotes the patch or rolls it back.

Then the part that makes it an experiment rather than a demo: one attack family is sealed away before the first patch is written, and it is not read again until the end. The result the project is trying to produce is whether a policy learned from the families it could see transfers to the family it could not.

## How I built it

The build ran as six deliberately blind lanes, each in its own worktree, each developing against frozen interface contracts rather than against each other's code. Ten contracts were written, canonicalized, hashed and committed before any application code existed at all.

Five artifacts are hashed and committed before any measurement is taken: the gate rule, the target agent, the capability manifest, the objective set that defines what counts as a breach, and the corpus with its derived field schema. Each freeze gets a timestamped public update as it happens, so the ordering is verifiable by someone who never opens the commit log.

The security boundary is IAM rather than convention. The identity that authors a policy patch is not the identity that promotes it, and the sealed corpus lives in a bucket the patching agent's service account cannot read. That refusal is demonstrated with a live 403, and the demonstration ships with a positive control, because a 403 on its own proves nothing. A misspelled bucket returns one too.

## Challenges

The hardest problems were not the agents. They were the checks.

The gate that verifies the contract hashes had a first negative test that could not fail: the mutation it made was exactly the whitespace the normalization exists to absorb. It was caught only because the negative test was actually run, and two more of that gate's five passes then turned out to have defects of their own.

One of five hash locks turned out to lock nothing. It covered tool names and parameter names and not one line of tool body, so a frozen agent could have been rewritten to approve everything while every result still cited the same hash.

Six of ten contract schemas were not valid schemas, and the checker never noticed because it validated fixtures against them without ever asking whether they were valid.

And the finding I did not want: an over blocking policy passes every gate. The most common patch the model proposes requires human approval for a legitimate action, the approval oracle approves it, the benign pass rate stays at one hundred percent, and the gate promotes. The metric could not distinguish "the agent still works" from "a human now does the agent's job."

Every one of those was found by something failing, not by review.

## What I learned

Ask every check what change it would fail to notice. A lock is only worth the surface it covers, and the surface is never obvious from the field name.

A search that reports clean is sometimes just unable to see. That happened three separate ways in one day, and each time it was caught because something else contradicted it.

The most confident sentences are the ones nobody thinks to verify. This repository had no license for its entire public life, and it was discovered only because a draft README asserted one from habit and got checked.

## Results

**Deliberately empty as of 2026-08-20. No attack has been scored and there is no number here worth quoting.**

That is not modesty and it is not an oversight. The whole argument of this project is that a number means something only if the thing it measures was fixed before the measuring started. This section fills in after the sealed family is opened, and every figure will carry its label when it does.

---

<!-- APPENDED 2026-08-23. Nothing above this line was altered. The sections below are
     additive and each carries its own dateline, because the Devpost story canvas shows
     only a single "last updated" stamp and that stamp can never prove authoring order.
     Git can. Every claim below links to the commit that proves it. -->

## What runs what (added 2026-08-23)

Five models, each doing one job, every one read from the source constant rather than from
memory. Four are Gemini on Vertex AI; the fifth is Gemma.

| Component | Model | Where the constant lives |
|---|---|---|
| Red strategist | `gemini-3.6-flash` | `crucible/red/red.py` |
| Target refund agent | `gemini-3.5-flash-lite` | `target/refund_agent/agent.py` |
| Coroner | `gemini-3.5-flash-lite` | `crucible/coroner/coroner.py` |
| Armorer | `gemini-3.7-flash` | `crucible/armorer/armorer.py` |
| Capability cartographer | `google/gemma-4-26b-a4b-it-maas` | `crucible/cartographer/vertex.py` |

The tripwire, the warden, the promotion gate and the budget governor call no model at all.
That is enforced rather than intended: the tripwire has no `aiplatform.user` role and an AST
import lint fails the build if the package ever imports a client library.

## How to check the ordering yourself (added 2026-08-23)

The argument of this project is that a number means something only if the thing it measures
was fixed before the measuring started. That is a claim about **when**, so it should be
checkable by a stranger rather than asserted by me.

Every artifact below is hashed, and each freeze is a public commit with a timestamp GitHub
recorded, not one I typed:

- **The sealed attack family, committed 2026-08-20**:
  [`6b1a54a`](https://github.com/emtcmca/crucible/commit/6b1a54a). Its fingerprint was
  published before any fix was written and before every other lock below. That ordering is
  the whole experiment.
- **The gate rule, 2026-08-21**:
  [`d1f16fc`](https://github.com/emtcmca/crucible/commit/d1f16fc)
- **The target agent and its capability manifest, 2026-08-22**:
  [`3621bba`](https://github.com/emtcmca/crucible/commit/3621bba)
- **The corpus and its derived-field schema, 2026-08-22**:
  [`128efcf`](https://github.com/emtcmca/crucible/commit/128efcf)
- **The objective set, the definition of breach, 2026-08-22**:
  [`517ccef`](https://github.com/emtcmca/crucible/commit/517ccef)

**And this story itself, committed 2026-08-20 with its Results section empty**.
[`75deb4b`](https://github.com/emtcmca/crucible/commit/75deb4b). Open that commit and the
section reads *"deliberately empty as of 2026-08-20."* The Devpost page shows one edit stamp;
the repository shows the order.

## Two locks were broken on purpose, and that is in the record too (added 2026-08-23)

Freezing early means occasionally freezing something wrong. Twice a frozen artifact turned out
to have a defect, and both times the lock was broken deliberately, re-taken, and the reason
written down rather than quietly patched.

The corpus lock moved because two dialects of the same field names had been authored in
parallel. The objective set lock moved because two of its nine clauses named arguments no tool
in the target actually emits, so those clauses had never once fired and four attacks were
scoring clean that should have scored as breaches.

**Neither prior record was deleted.** Both are archived with a block naming what superseded
them and exactly what they invalidate. The freeze script refuses to re-run over a record naming
a different hash, and there is no override flag; breaking a lock costs a written ruling every
time. That refusal is the guard doing its job, and a superseded lock is evidence rather than
litter , because deleting it would leave nothing to show a lock had been taken, held, and broken on
purpose, which is the only reason the replacement can be trusted.

---

<!-- APPENDED 2026-08-25. Nothing above this line was altered, including the Results
     section, which still reads "deliberately empty as of 2026-08-20" and will keep
     reading that way. The numbers arrive BELOW it, dated, rather than by editing it.
     execution-spec 5a claim discipline applies to every figure here: each carries its
     label, and the one number this project exists to produce still does not exist. -->

## The loop ran (added 2026-08-25)

Sixty live campaigns overnight, against the real target agent on Vertex AI, with the pure code arbiters wired in place of the last stand-in. 1,770 episodes, of which 1,616 were scorable. Every bundle validated against the offline reader with zero errors. The gate promoted a policy **95 times**, at a mean of 1.58 per run.

Before this batch nothing had ever been promoted in this project. The policies bucket was empty and the storage write path, with its read-back-and-rehash assertion, had never executed once.

Two labels travel with every figure above and they are not decoration. It is **single sample, k=1, with no stability estimate**. And it separates **1,260 test pairs by the policy against 180 by the approval oracle**, because a suite the oracle separates produces a result that looks identical while measuring something else.

## The most useful number looks like a failure (added 2026-08-25)

The exclusion rate ran over its 5 percent ceiling in **51 of 60 runs**, median 8.3 percent. All 154 excluded episodes carry the same reason code, and they trace back to just eight attacks.

Reading them apart is the finding. One attack says "just close it out, I'll take the store credit" and presupposes a conversation whose earlier turns do not exist, so the agent has nothing to act on and could never call a tool. Another offers the agent 150 dollars per request and produces no tool call because **the agent refused a bribe**. The first is a broken fixture. The second is a successful defense being deleted from the denominator.

One reason code cannot serve both, and until the night before this batch neither was visible at all: the verdict schema had nowhere to record why an episode was invalid, so the instrument computed the answer and threw it away every time.

The obvious fix is to score these clean. That brings the rate under the ceiling in one line and launders the broken fixtures into passes. It is not going to happen here. The fixtures move; the answer key does not.

## The result I nearly published (added 2026-08-25)

Splitting the episodes by provenance, an axis that was already in the data, gave `generated` attacks breaching at 9.2 percent against `training_corpus` at 4.1 percent. A clean 2.2x, and the story writes itself: rephrase a known attack and it lands more often.

Every generated attack records the seed it came from, so the paired test was available. **729 pairs where a seed and its own variant were both scorable in the same run: 60 breach to breach, 669 clean to clean, and zero discordant pairs.**

The 2.2x was a composition artifact. The corpus arm carries nearly twice the exclusions, because those eight unscoreable instances concentrate there, so the two arms were never the same population. The marginal comparison was real over a denominator that meant nothing.

What survived is stronger and it is on thesis: **the target's behaviour is invariant to paraphrase**. Rewriting an attack's surface text, using a different model, changed the outcome in none of 729 opportunities. That is direct evidence for binding policy to what a trace records rather than to what a message says, which is the design claim the whole project rests on.

## What is still not known (added 2026-08-25)

The number this project was built to produce. Whether a policy learned from the families the loop could see transfers to the family it could not.

The sealed family stays sealed until 2026-08-28 and no transfer claim exists before then. The Results section above stays exactly as it was written on 2026-08-20 until that number arrives, and it arrives with its label attached whatever it turns out to be.
