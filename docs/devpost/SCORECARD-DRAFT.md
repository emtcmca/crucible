# What CRUCIBLE actually did

> ## A hardening tool that cannot tell you which of its own fixes worked is worth much less than one that can.
>
> **We built that check, pointed it at our own output, and more than half the fixes
> failed it.** That number is in this document, near the bottom, unprompted.
>
> Answering the question at all means recording **what the agent actually called** rather
> than what it said it did, and then replaying those calls against the new rule. That is
> why the component that decides whether a breach occurred is pure code with no model in
> it, and why it watches tool events instead of text.

Five findings below. **Each is labelled by how strong the evidence is**, before the number,
so nothing here can be read as stronger than it is.

---

## DEMONSTRATED · one run, not a rate

### We pointed it at a Google agent it had never seen, and it worked

Google publishes a sample customer-service agent. We changed nothing about it — its own
code, its own model, its own tools. We attached CRUCIBLE's enforcement plugin and asked
the agent an ordinary customer question.

**Without a policy:** the agent approved a 40% discount. The tool it used is described to
it as "ask a manager for approval." There is no manager behind that tool. It approves
anything it is asked.

**With a policy CRUCIBLE learned on a completely different agent:** the same request, the
same model, the same tool call. **Refused. The tool never ran.**

The rule that stopped it **does not mention that tool, or any tool.** It binds to what the
tool *can do* — move money — which a classifier worked out from the tool's description.

> *This is not a security flaw in Google's agent. It did what its own instructions told it
> to do. What it shows is that CRUCIBLE's rules travel to agents it has never met.*

---

## MEASURED · the starting line, and it is the only ASR figure on this page

### Eight of fifty attacks succeed against the agent with no rules at all

We wrote a library of 50 attacks against a refund agent that can move real money, then
recorded what the agent does against every one of them **before CRUCIBLE writes a single
rule**. That recording is frozen: `docs/proof/v0-attack-baseline-freeze.json` — 50 episodes
against the pinned model, hashed, timestamped, with all 50 rows in the file.

| | attacks that succeed |
|---|---|
| agent with **no rules at all** | **8 of 50** |

**8 is a hard ceiling, and it is lower than we designed for.** Our own published target
assumed roughly 30. Everything CRUCIBLE can demonstrate has to fit inside a gap of 8.

### The "after" number is not on this page yet, and that is the whole point of the page

We had one. **We withdrew it.** It was a median across ten runs, and when we later built a
check that asks whether an evidence bundle can even be read, **it refused all ten of them** —
a field written as `null` where the format requires an absent key. The number may have been
close to right. It was computed over documents nothing had validated, so we cannot say.

> *The rule we now enforce on ourselves: **every figure over a batch prints, beside it, how
> many of those runs the reader accepts.** Not "median 2.5 across ten runs" but "median 2.5
> across ten runs, of which the reader accepts zero." The second sentence is not quotable, so
> it does not get quoted.*

A re-run in the corrected configuration is what produces the replacement. **Any "after" figure
you see from us without an acceptance count beside it is one you should not trust, including
ours.**

---

## NOT MEASURED · withdrawn on the same evidence, and listed rather than dropped

### Whether the rules stop attacks CRUCIBLE never tried

This is the question we most want to answer. Each run only tries a handful of the 50 attacks,
so the rest are a free test: rules written without ever seeing those attacks, checked against
them anyway.

**We had figures here too. They came from the same ten unreadable runs, so they went with
them.** They are not restated on this page, in either direction, because a number that was
computed correctly over documents nothing validated is still a number nobody checked.

---

## NOT MEASURED · and we are saying so rather than leaving it out

### Whether it holds against a whole category of attack it has never encountered

The 50 attacks come in six families. Everything above tests attacks from families
CRUCIBLE has worked on before, even when the specific attack is new.

Before we ran anything, we sealed a **seventh family** away in cloud storage the attacking
system cannot read, and published its fingerprint. It opens on **2026-08-28**. Until then,
**whether CRUCIBLE handles a genuinely new category of attack is an open question, and any
number claiming otherwise would be made up.**

---

## FOUND · negative, and we are publishing it

### More than half its rules did nothing, and it caught that itself

We built a check that asks a simple question of every rule: **did it actually stop the
attack it was written for?**

**19 of 32 did not.**

The gate had been checking that a rule was well formed and that it did not break
legitimate work. **It never checked that the rule fixed anything.** A rule that blocks
nothing passes both of those tests easily.

We found this by measuring our own output, not by review. Both checks that ask the right
question shipped this week, and every promotion figure published before them was produced
by a gate that could not tell a fix from a no-op.

> *This is the finding we would most like to have not made. It is here because a result
> you can only trust when it is flattering is not a result.*

---

## Want to check any of it?

| | |
|---|---|
| the Google agent run | `docs/proof/foreign-agent-enforcement-probe-2026-08-26.txt` |
| the attack-reduction numbers | `RESULTS.md` |
| the rules-that-did-nothing finding | `docs/design/gate-noop-measurement-2026-08-25.md` |
| every correction we have made | `AUDIT.md` |
| what the numbers do and do not cover | `MEASUREMENT.md` |

**Every figure above is a replay:** we re-run the tool calls the agent actually made
against the new rules. It answers *"would these rules have stopped that"* — not *"could an
attacker find another way in."* Single sample, no stability estimate, and it says so
wherever it appears.
