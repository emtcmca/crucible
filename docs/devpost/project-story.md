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
