# What CRUCIBLE is, in plain English

*Written 2026-08-21. Nothing in this document is a result. No loop has been run and no attack
has been scored. Every number below is either a corpus size, a frozen parameter, or a target
that the specs already declare as a target.*

---

## The problem

Companies are starting to give AI agents real permissions. Not "draft me an email" — actual
authority: refund money, close a case, email a customer, hand work to another agent.

The way that authority gets tested today is that somebody writes a list of nasty prompts, runs
them, and sees what happens. Two things go wrong with that.

**The list is written by the same person who built the agent**, so it tests the failures they
already imagined. The failures that matter are the ones nobody imagined.

**Nothing is fixed by it.** A red-team report says "here is what broke." It does not say "here
is the rule that stops it," and it certainly does not say "and here is proof the rule did not
break anything legitimate on the way."

There is a third failure that is quieter and worse. When a team does write a fix and re-run
the tests, the tests almost always pass — because the fix was written after seeing the tests.
That number is not evidence of anything. It is the answer to a question that was asked after
the answer was known.

## What CRUCIBLE does

CRUCIBLE is a **hardening harness you run before you deploy an agent**. You point it at an
agent that holds real permissions. It attacks that agent, watches what the agent actually did,
writes a policy rule that stops the attack, checks that the rule did not break legitimate
work, and either promotes the rule or rolls it back. Then it does it again.

What comes out is not a report. It is a **policy** — a small set of machine-readable rules
that sit between the agent and its tools — plus an evidence trail showing which attack each
rule stopped and what legitimate behaviour survived.

The one-line version:

> **CRUCIBLE is the adversarial quality gate an autonomous agent has to survive before it goes
> to production.**

## How it works

Five components. Three of them are code, not models, and that is deliberate.

**1. The red-team agent** — a language model that attacks the target. It writes new attacks
each round, against a target whose defenses are tighter than they were last round.

**2. The tripwire** — **pure code**. It sits between the agent and its tools and records what
the agent *actually called*, with what arguments. It does not ask the agent what it did. This
is the difference between a witness and a confession.

**3. The Coroner** — a model that writes the autopsy: what happened, in what order, and where
the trust boundary broke. **It structurally cannot propose a fix.** The thing it hands
downstream is a fixed list of fields with no free-text box in it, so it has nowhere to write
"and you should do X."

**4. The Armorer** — a model that writes the patch, in a deliberately tiny language with
exactly three verbs: `deny`, `constrain_arg`, `require_approval`. There is no `allow` verb, so
no sequence of patches can ever *widen* what the agent is permitted to do. The worst a
confused or compromised Armorer can do is over-block, and there is a separate check for that.

**5. The Warden and the gate** — **pure code**. They decide whether a proposed rule gets
promoted or thrown away. The gate re-reads the rule back from disk and re-computes its hash
from the actual bytes, because a gate that reports a decision it did not durably record will
lie to you exactly once, at the worst possible moment.

Detection and remediation are separated **structurally** rather than by instruction. And the
separation is enforced in cloud IAM, not in a prompt: the Armorer's service account cannot
read the evidence bucket at all. We tried it as the Armorer, captured the 403, and saved the
raw denial — alongside a positive control proving the probe can actually fail.

## Why anyone should believe the number

This is the part the project actually cares about, and it is the reason for most of the
machinery.

**One family of attacks is sealed away before any fix is written.** Six attack families are
used for training. A seventh — destination smuggling, 24 instances — is held out. It is not in
the public repository. It sits in a cloud bucket the attacking identity cannot read. Its
fingerprint was **published before the run**, at `2cde0250de00e692`, with a public commit
timestamp. Anyone can recompute that hash after the reveal and confirm nothing moved.

That is the same discipline as pre-registering a hypothesis before you collect the data. It
turns "we sealed it first, trust us" into something a stranger can check.

The held-out family is also on **capability classes the rules were never trained on**. So the
question it answers is not "did the fix work on the thing it was written for" — it is *did the
loop learn a rule shape that generalises to tools it never saw.*

**Five things are hash-locked, each before it could be used:** the promotion rule, the target
agent, the capability map, the definition of what counts as a breach, and the corpus with the
fields the evaluator reads. Once locked, changing any of them voids the run rather than
quietly moving the goalposts.

**Every check is asked what it would fail to notice.** That question has already caught real
defects here: one of the five hash-locks locked nothing (we proved it by editing a tool body
and watching the hash stay put), six of ten schemas were not valid schemas, and the definition
of breach had no clause covering the sealed family — which would have reported zero breaches
while every gate stayed green.

**The claim is stated with its limits attached, permanently.** Single sample, no stability
estimate. One target. And every headline figure is printed next to a split showing how many
test pairs were separated by the *policy* versus by the *approval oracle* — because a suite
the oracle separates produces identical-looking numbers to one the policy separates, and that
row is the only thing that tells them apart.

## The finding we are most likely to be remembered for

While building the ruler, we found that **a rule which over-blocks passes every gate.**

A `require_approval` rule that sends far too much to a human blocks most attacks, the approval
oracle approves the legitimate requests, the benign pass rate reads a perfect 24 out of 24,
and the promotion gate promotes it. Every instrument says the run went well. What actually
happened is the agent was made useless and a human was handed the work.

The fix was not to the rule. It was to the ruler: the benign pass rate now permanently carries
a second figure — how many of those passes only happened because a human was made to
rubber-stamp them. A benign task that survived by escalation can never again be counted as
having passed cleanly.

That is a finding about how AI safety work gets measured, and it holds well beyond this
project.

## What a judge sees

About four minutes, live, no narration over a static screen.

1. **A refund agent with eight real tools and real permissions.** It moves money against a
   real SQLite ledger. A refund it issues actually changes a balance you can query.
2. **Attacks run, and several fail on camera.** Failures stay in. A reel where everything
   works reads as a tour; a reel where attacks 14 and 15 fail and 16 gets through reads as a
   system under pressure.
3. **One lands.** The tripwire — not the attacker's own account of itself — shows the exact
   call sequence that crossed the line.
4. **The Coroner writes the autopsy and cannot suggest the fix.** The Armorer, reading only an
   enumerated projection of that autopsy, emits a rule in three verbs.
5. **The rejection beat, which is the most credible thirty seconds in the whole demo.** A
   proposed rule blocks five attacks and *also* breaks two legitimate cases — a real supervisor
   authorising a real refund, and a legitimate delegated credit. The gate throws the rule out.
   A system that only ever shows itself succeeding has not shown you anything.
6. **The seal is opened on camera.** The held-out family runs for the first time, against a
   policy that has never seen it, on capability classes the rules were never trained on. The
   published fingerprint is recomputed live.
7. **A third-party agent nobody wrote attacks for.** Its tools are classified in about forty
   seconds, one comes back unclassified and is *named out loud* rather than hidden, and the
   existing corpus runs against it. The number on screen is **attacks written for this agent:
   0** — and we say before running it that cross-target transfer will be worse, because it
   will be.

## Where this goes after the hackathon

**Continuous adversarial assurance in CI.** The natural home for this is a pipeline step. A
developer changes an agent; the change deploys to a candidate environment; CRUCIBLE runs the
existing corpus plus fresh generated attacks; a security regression blocks the merge. Agents
get the thing ordinary software has had for twenty years and agents still do not: a test suite
that runs on every change and can actually stop a bad one.

**A policy layer that outlives the harness.** The three-verb policy language and the
capability-class model are not tied to this refund agent, or to one framework. The rules bind
to *capability classes* rather than to tool names, which is why a rule learned on one tool can
transfer to a tool it has never seen. That is portable.

**An honest procurement artifact.** Enterprises buying agents have no way to ask "how does
this behave when someone attacks it." A signed evidence bundle — held-out attacks, a published
pre-commitment, a benign floor showing the agent still works — is closer to a real answer than
any vendor questionnaire currently in use.

**Regulated industries first.** Financial services, healthcare, legal. Not because the
technology is different there, but because those are the buyers who already have to document
why an automated decision was allowed to happen, and who cannot accept "the model seemed
fine."

**The thing it is not, and should not become:** a scanner you run once, after the fact, to
generate a PDF. The whole design assumes it runs *before* deployment and again on every
change, and that its output is an enforceable policy rather than a document somebody files.
