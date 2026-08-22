# Product shape — two decisions taken 2026-08-22

Not hackathon-scored. Recorded because a decision that lives only in a transcript
is gone at the next `/clear`, and both of these change what CRUCIBLE *is* rather
than what it does this week.

---

## 1. Exploratory runs, and why the mode separation is load-bearing

**Eric's framing, which is the one to keep:** exploratory runs *"help a user model
his test model, to clear up low hanging attack vectors and gaps prior to the full
official non-human-interveneable runs."*

That is not a lesser mode. **It is how an agent becomes worth measuring.** A
measured run whose result is dominated by gaps anyone could have found by hand is
a weak result; clearing those first makes the official number mean something.

**Two modes, structurally separated, mode stamped into the evidence bundle:**

| | exploratory | measured |
|---|---|---|
| human may interrupt, steer, retry | **yes — that is the point** | **structurally impossible** |
| may produce a quotable number | **never** | yes |

**Why intervention must be impossible in a measured run, in Eric's words:** *"we
can't allow that. It defeats the entire purpose of the project."* A human who can
steer mid-run is a human who can steer the result. That is G8's non-self-approval
logic applied to the operator instead of the Armorer, and today the project would
fail it. It also hands a hostile reader the one question we currently have a
perfect answer to: *how do we know you didn't nudge it?*

**The codebase already thinks in this shape** and the precedent should be
followed rather than reinvented: `RUN INVALID is not a rejection`,
`g7_g8_exercised` derived from gate reports rather than from `--live`, `stand_ins`
listed in the bundle. It consistently separates *this ran* from *this counts*.
Exploratory mode is that distinction one level up.

**Deliberately deferred past the hackathon.** It is not scored, and getting the
mode separation wrong under deadline pressure is exactly how the integrity story
springs a leak. The observer hook it would build on IS justified now, for a
reason independent of any of this: a long sweep going wrong is currently
invisible until it ends, and **you cannot kill a run you cannot see.**

---

## 2. CAPABILITY_CARTOGRAPHER — approved in principle

**Eric: yes.** The one agent worth adding, and the reason is not that the project
needs more agents — he opened with *"not big on having agents just for the sake of
having more agents,"* which is the right instinct and was held.

**Every other candidate was refused, and the refusal is structural.** The
tripwire, warden, gate and governor are pure code precisely so *"no model ever
decides whether a breach happened"* is a fact rather than a claim. Adding a model
to the judging path would weaken the strongest thing the project has — already a
recorded Tier 3 refusal: *"swapping one fallible judge for another is not a
separation of powers."*

**The cartographer is different because it is not in the judging path.** It
classifies an *unseen* agent's tools into capability classes, which is the
difference between *"we hardened our agent"* and *"point it at yours."* The
deterministic pre-pass (`crucible/cartographer/prepass.py`) already resolves most
of it; the residual a model genuinely does better is mutation-verb classification
and PII-in-return-schema.

Scope and evidence: `docs/decisions-pending/gemma-scope.md`. Timing was already
set at D5-D7 by `docs/NEEDS-ERIC.md` item 10, on the reasoning that deferring
costs nothing while a false claim in a shooting script cost five days.
