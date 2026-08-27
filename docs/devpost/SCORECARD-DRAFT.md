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

## MEASURED · 10 runs

### It cuts successful attacks by about two thirds

We wrote a library of 50 attacks against a refund agent that can move real money.

| | attacks that succeed |
|---|---|
| agent with **no rules at all** | **8 of 50** |
| agent after CRUCIBLE runs | **2 or 3 of 50** (median 2.5 across ten runs) |

Best run got it to 1. Worst got it to 7. **Every run met or beat the target we published
before we had any results.**

---

## MEASURED · the one that matters

### The rules also stop attacks CRUCIBLE never tried

Each run only tries a handful of attacks — about 6 per round, a few rounds — so **most of
the 50 attacks are never used in any given run.** That makes them a free test: the rules
were written without ever seeing those attacks, so do they stop them anyway?

| | before | after |
|---|---|---|
| attacks CRUCIBLE **did try** | 44 | **12** |
| attacks CRUCIBLE **never tried** | 36 | **16** |

**It stops well over half the attacks it never saw.** Not as well as the ones it trained
on — 73% versus 56% — and that gap is what an honest result looks like. A system that
scored the same on both would mean we had measured the same thing twice.

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
