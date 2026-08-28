# Scope lock — what is in the 2026-08-30 submission

**Locked 2026-08-27 evening.** Everything not on the IN list is roadmap, and
roadmap is a strength in this submission rather than an omission: §6 of
`docs/devpost/the-contribution.md` is written entirely from findings this build
produced.

**The rule from here: no new capability enters the submission.** Work that
improves a number we already report is allowed. Work that adds a thing to report
is not.

---

## 1. The headline

> # Crash-test your AI agent before you trust it with money.
>
> **CRUCIBLE attacks it, writes the rules that stop the attacks, and refuses to
> ship a rule it can't prove works. More than half of ours didn't — and it
> caught that itself.**

**Chosen by Eric 2026-08-27, replacing a two-clause version that failed the only
test that matters here: a careless judge, two hundred submissions in, does not
parse a compound sentence about carrying learned policies.**

**Headline does one job: the category, instantly.** "Crash test" is universally
understood to mean *deliberately break it in a lab so it does not break in the
world.* Nobody needs the domain to get it.

**Subhead does the other: the differentiator.** Three verbs, then the hook. The
self-indictment in the last clause is the credibility move, because nobody fakes
a number in that direction.

**It also earns the project name.** A crucible is where you apply extreme heat
to find out what something really is. *"Put your agent in the crucible"* closes
the video for the same reason.

**Why not lead with "it hardens agents".** The honest version of that sentence is
"attack success fell from 11.3% to 6.2% on one agent, single-sample" — true,
small, and indistinguishable from every other entry claiming an improvement. It
is our weakest strong material and it must not lead.

**The Google-agent demonstration is the PROOF, not the headline.** It is what a
judge sees at 0:30, not what they read first.

## 2. The four proof points, in the order a judge should meet them

**1 · PORTABILITY — DEMONSTRATED, one run per arm.** Google publishes a customer
service agent as an ADK sample. Unmodified — its own code, model, tools and
callbacks. We attached CRUCIBLE's plugin. With no policy its own Gemini approved
a 40% discount. Under a policy **learned on a completely different agent**, the
same call was DENIED — **by a rule that names no tool**, binding a capability
class assigned by a classifier reading the tool's own description.

*This is the beat that separates us. It is not a claim about safety, it is a
demonstration that enforcement is portable, and it is only possible because
enforcement lives in a plugin at the ADK `before_tool` boundary rather than in a
fork of one agent.* It is **not** a breach and the write-up says so first: the
sample obeyed its own prompt.

**2 · THE GATE THAT REFUSES.** 18 refused patch attempts in the measurement
batch, each with the invariant, the attempted rule, and the machine-checked
reason. Earlier, before those gates existed, **19 of 32 promoted rules had closed
nothing** — found by measuring our own output, not by review.

**3 · THE NUMBERS, WITH THEIR ACCEPTANCE.** 20 runs, **the reader accepts 20 of
20**. A replication at identical configuration is running for the first stability
estimate this project has ever had. Every figure prints its acceptance count
beside it because a rule requires it.

**4 · WHAT IT COULD NOT FIX.** `scripts/unresolved-findings.py` — the three
invariant classes it reliably finds and cannot close, in plain English, with the
rules it tried. Plus the clean sweeps, with **every attack vector listed
verbatim**, because "we attacked and found nothing" is unfalsifiable without
them.

## 3. Answering "is this a real platform, on ADK, that adds real value"

A judge scanning hundreds of entries is asking three questions. The answers have
to be checkable in under a minute each.

| the question | the answer, and where it is checked |
|---|---|
| **Is it really on ADK?** | Enforcement is `class CruciblePlugin(BasePlugin)` at `crucible/plugin/adk.py`, on `before_tool`. Not a wrapper around ADK — a plugin *in* it, which is why it attached to Google's own sample unchanged. `google-adk==2.1.0` pinned. |
| **Is it really on Google Cloud?** | Vertex AI at the `global` endpoint for four pinned Gemini models plus Gemma via MaaS; Cloud Run deployed and serving; GCS for the sealed corpus, the policy store and evidence; **IAM is the blindness boundary** — the identity that authors patches holds no read on the sealed bucket, and the identity that promotes is not the identity that authors. |
| **Does it add real value?** | It hands a user three things: a policy, **a list of what it could not fix**, and evidence of what it attacked and found nothing on. Most tooling reports only the first, which is a policy plus an unearned feeling of safety. |

## 4. IN — the submitted scope

- The harness: red strategist, pure-code tripwire, coroner, armorer, pure-code
  warden and promotion gate.
- The ADK enforcement plugin, and the foreign-agent demonstration.
- The three-verb DSL with **no `allow` verb**.
- The offline reader, its acceptance gate, and its nine known-bad fixtures.
- The tripwire's nine known-bad calibration fixtures (G1-gated).
- The 20-run measurement batch, its replication, and the unseal result.
- `unresolved-findings.py`, the hardening report, the replay viewer.
- `AUDIT.md`, the pre-registrations, and every withdrawn claim.

## 5. OUT — built or designed, deliberately not claimed

Each of these is named in the submission as roadmap, with the finding that
motivates it. **Naming them is worth more than shipping them half-done.**

| out | status | why it stays out |
|---|---|---|
| **Phase-two attacker memory** | built, committed, **default OFF, never run live** | changes what every number means; needs its own pre-registration and a separate directory |
| **Free attack discovery** | not built, and **not a timing call** | dissolves the denominator every rate depends on, and makes the loop circular: find X, patch X, declare hardened. The fixed corpus is what keeps the attack set independent of the patches |
| **Powering the degeneracy census** | census covers 50 of 50, none powered | ~65 runs; catches a *regression* into degeneracy, which nothing currently can |
| **Closing the three invariant classes** | diagnosed at source, not fixed | the largest needs a coordinator ruling on whether the armorer may see the clause's shape |
| **`benign_passes_requiring_approval`** | not built | the fix is to the ruler, so it cannot be rushed |
| **A C6 field for `RUN_INVALID`** | not built | contract bump |
| **Hosted judge-testable URL** | service is authenticated | "highly encouraged", not mandatory |

## 6. What can still improve a number tonight

Only two things, and both are already moving:

1. **The replication batch**, which converts "k=1, no stability estimate" — the
   most-repeated caveat in the repository — into a reported spread.
2. **The unseal**, 2026-08-28, whose most likely outcome is pre-registered as a
   sub-floor denominator and no quotable rate. **The apparatus is the deliverable
   there, not the number**, and that framing is fixed before opening it rather
   than after.
