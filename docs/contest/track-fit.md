# Track fit — The Fortified Enterprise Fleet

**Written 2026-08-21, by Lane I, on Eric's instruction to meet the gap head-on rather than
route around it.** `docs/contest/CONTEST.md` §3 already names this as an open question. This
document is the deeper answer: what the track asks for, quoted; where CRUCIBLE meets it,
partially meets it, or does not; the strongest honest argument for the framing we should use;
what we will explicitly refuse to claim; and draft submission language.

Nothing below is a result. As of 2026-08-21, no attack loop has been run and no ASR/BPR figure
exists — see `docs/what-crucible-is.md`. This document is positioning, not measurement.

---

## 1. What the track asks for, quoted exactly

From `docs/contest/CONTEST.md` §3, which is the single source for this text — do not
re-quote the rules page directly, cite this section:

> "Build a scalable network of institutional agents that hook into official enterprise
> infrastructure… demonstrate how agents are cataloged for cross-department use, how they
> safely maintain context across weeks of asynchronous operations, and how they interact with
> production data without violating enterprise compliance, data sovereignty, or security
> policies."

Broken into five distinct, separately-checkable requirements:

- **R1 — scalable network of institutional agents.**
- **R2 — hooks into official enterprise infrastructure.**
- **R3 — agents are cataloged for cross-department use.**
- **R4 — safely maintains context across weeks of asynchronous operations.**
- **R5 — interacts with production data without violating enterprise compliance, data
  sovereignty, or security policies.**

Stage Two's own criteria (also `CONTEST.md` §3–§4) add three more, scored independently of the
track paragraph above, under **Architectural Discipline & Tech Stack (30%)**:

- **S1 — The Multi-Agent Nexus:** "Is there a clear, strictly enforced separation of concerns
  between agents? Is the inter-agent routing logic failure-tolerant (e.g., how does the system
  recover if a worker agent loops or returns a hallucination)?"
- **S2 — The Continuous Action Engine:** "Are the tools properly isolated and scoped for
  security?"
- **S3 — "Unlikely Hero":** "Did they build this for an 'Unlikely Hero' outside of standard
  corporate roles?"

---

## 2. Requirement by requirement, brutal

| # | Requirement | Verdict | What we do instead / evidence |
|---|---|---|---|
| R1 | Scalable network of institutional agents | **PARTIAL** | CRUCIBLE's own loop is a real multi-agent network — see §3 for the count — but it is not "institutional" in the sense the track means (deployed across an org, doing business work) and it has never been run at scale: one target, one run, eleven days. It is a network that tests institutional agents, not one that is itself institutional. |
| R2 | Hooks into official enterprise infrastructure | **MEET (narrow reading), PARTIAL (broad reading)** | The `CRUCIBLE_PLUGIN` attaches at the ADK plugin layer with **zero modification to the target** (`architecture-spec.md` §3.1, `ADR-0005`) — that is a real hook into a real agent framework's own extension surface, not a wrapper or a proxy. But CRUCIBLE is not itself deployed *as* enterprise infrastructure (no ticketing system, ERP, or CRM integration exists) — it hooks into the *agent*, not into the enterprise systems the agent talks to. |
| R3 | Agents cataloged for cross-department use | **PARTIAL** | The capability manifest (`architecture-spec.md` §4) classifies every tool on the target into one of six capability classes, ratified by a human before any run — that is real cataloging discipline. But it catalogs **tools on one agent**, not **agents across departments**. Scaling the same discipline to a fleet is the "what this becomes" argument (§3 below), not a built capability. |
| R4 | Safely maintains context across weeks of asynchronous operations | **DOES NOT MEET — by design, stated in our own specs before this document existed** | `docs/CONVENTIONS.md` Ruling 7: "an episode is one attack attempt, so cross-conversation abuse is out of scope, and that must be stated rather than omitted." `episode.*` is frozen before the first turn and unwritable after (`ADR-0013`). `docs/separability-proof.md` row P24 — agent-shopping, the exact cross-conversation abuse pattern the track language describes — is marked **"NOT A PAIR — spans conversations — out of scope"** and was never written. We do not have a workaround to cite here; this is the real gap. |
| R5 | Interacts with production data without violating compliance, sovereignty, or security policy | **STRONG MEET — this is the product** | The whole harness exists to answer this question empirically rather than by policy document: a target moving money against a real ledger, attacked, with the boundary enforced in IAM where it can be (Armorer holds no role on the sealed-attack bucket at all, captured as a 403 with a positive control — `docs/proof/armorer-403.txt`) and in pure code elsewhere, named honestly as convention-plus-check where IAM cannot express it (`CONVENTIONS.md` §7, "Enforcement claims — real vs. convention"). |

**Stage Two sub-criteria:**

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| S1 | Multi-Agent Nexus — separation of concerns, failure-tolerant routing | **STRONG MEET** | Separation is structural, not descriptive: the Coroner's inability to propose a fix is enforced by output schema plus a modal/imperative-token lint, not a prompt instruction (`ADR-0004`); the Armorer cannot promote its own patch (`ADR-0006`); the gate re-reads a promoted rule from disk and recomputes its hash before trusting it durably landed. Failure-tolerance is answered directly — README §"What happens when an agent loops, lies, or returns nothing" names six mechanisms, each pure code, each tied to a specific named failure (a worker claiming a success it did not have, a patch accepted but never durably written, the Armorer exhausting the DSL and halting to a human). |
| S2 | Tools isolated and scoped for security | **STRONG MEET** | The capability manifest plus the three-verb policy DSL (`deny`, `constrain_arg`, `require_approval`, no `allow` verb — no patch sequence can widen access) is exactly this. |
| S3 | "Unlikely Hero" | **DOES NOT MEET** | No named persona exists anywhere in the project as of 2026-08-21. This document does not invent one — that is a scope decision for Eric, not a positioning fix. |

---

## 3. The strongest honest argument

Three candidate framings were on the table. Testing each against what is actually built:

**Framing A — lean toward the fleet the harness protects.** Describe the target agent as a
stand-in for one member of an enterprise fleet, and CRUCIBLE as the thing that hardens each
member before it joins. Honest, but thin on its own — it says nothing about R1's "network of
agents" language, which is where real points are available.

**Framing B — the fleet CRUCIBLE runs IS the institutional network.** Count the agents:
`RED_STRATEGIST` and `CORONER` and `ARMORER` are the three model-bearing agents the
architecture spec's own one-sentence summary names as "propose, diagnose, and repair"
(`architecture-spec.md` §0); `CAPABILITY_CARTOGRAPHER` is a fourth model-bearing component,
running once at attach rather than in the round loop; `TARGET_AGENT` is a fifth model-bearing
agent, but it is the system under test, not part of CRUCIBLE's own fleet. Wrapping those is a
set of pure-code components — the plugin, the policy engine, the tripwire, the warden, the
gate, the conductor, the budget governor, the ledger — each with a stated blindness boundary
and a stated reason for it. That is a genuine multi-agent network with delegation and
structural separation of concerns. It is honest to claim for **S1**, where the criterion is
about architecture, not about enterprise deployment. It is a stretch to claim for **R1**,
because these agents do adversarial-testing work, not enterprise business work, and the word
"institutional" does not fit a harness that has run zero times against a live enterprise
system.

**Framing C — CRUCIBLE is the thing you run BEFORE you have a fleet.** This reframes the
product category rather than forcing the built system into R1's shape. It is supported by
language already in the repo, not invented for this document: `docs/what-crucible-is.md`
states the one-line description as *"the adversarial quality gate an autonomous agent has to
survive before it goes to production,"* and its closing section names the roadmap explicitly
as *"continuous adversarial assurance in CI"* — a gate a fleet passes through before and
during operation, not a fleet itself.

**Verdict: Framing C is honest, not a dodge — conditionally.** It is honest specifically
because it is paired with an explicit admission that R4 and the "institutional" half of R1 are
not met, rather than used to talk around them. A framing that says "we test the fleet" without
also saying "we do not maintain state across the fleet's operating weeks" would be exactly the
overclaim `CONVENTIONS.md` §7 warns against ("production-ready," "enterprise-grade" are banned
for the same reason: eleven days, one target, solo). Stated together, the two halves are a
true sentence. Stated alone, the first half is a dodge.

**Recommended combination:** lead the track-fit narrative with Framing C (the harness that
gates a fleet, not a fleet itself) for R1/R2/R4, where honesty requires naming the gap. Lead
the Stage Two Architectural Discipline narrative with Framing B (the loop is itself a real
multi-agent network) for S1/S2, where the criterion is about the architecture we actually
built and Framing B holds up entirely on its own. These are two different sections of the
submission answering two different questions — they do not need to reconcile into one
sentence.

---

## 4. What we will NOT claim

- **Cross-episode or cross-conversation memory.** Explicitly out of scope by
  `CONVENTIONS.md` Ruling 7 and unwritten as `separability-proof.md` row P24. This is a
  stated limitation, not a discovered one — the specs said so before this document did.
- **Weeks of asynchronous operation.** CRUCIBLE runs bounded campaigns of a few rounds each
  (round cap named in `CONVENTIONS.md`, not restated here); nothing in the system has ever
  run continuously for a stretch measured in weeks, and there is no persistence layer designed
  for that horizon.
- **A deployed, cross-department institutional fleet.** One target agent, one modeled policy
  domain (refund handling), one person, eleven days. No second target has been attacked as of
  2026-08-21.
- **That any of the above is coming later on a committed timeline.** The roadmap language in
  `docs/what-crucible-is.md` ("continuous adversarial assurance in CI") is a direction, not a
  promise with a date.
- **Anything implying Google reviewed, endorsed, or responded to this project** —
  `CONVENTIONS.md` §7, restated here because it applies directly to any track-fit claim that
  cites Google's own rubric language back at them.

---

## 5. Recommended submission-text language

> **Two defects were removed from these drafts by the coordinator on 2026-08-21, and both are
> worth knowing about because they are the kind that survive into a submission.**
>
> The full variant ended *"...so every claim we do make is one we measured."* **Nothing has
> been measured.** That sentence would have put the single claim this project has been most
> careful never to make into the one document a judge reads first — and it would have done it
> inside a paragraph about honesty. Replaced with *"stated as such before anyone asks,"* which
> is true today and stays true whatever the loop produces.
>
> The short variant said *"four pure-code arbiters."* Defensible — tripwire, warden, gate,
> budget governor — but a **count**, in submission text, and counts here are verify-on-use and
> have drifted in every direction. Replaced with the property itself: *every component that
> decides anything is pure code with no model in it.* That is stronger than the number, and it
> cannot go stale.

Two variants — a track-framing sentence for wherever the submission addresses "why this
track," and a shorter version for a tight word count.

**Full (two sentences, track framing — pairs Framing C with the honest limit):**

> CRUCIBLE is the adversarial hardening harness a single institutional agent has to survive
> before it earns real permissions inside a fortified enterprise fleet, not the fleet itself —
> it attaches to one agent's real tool-call lifecycle, attacks it, and produces an
> enforceable policy plus a sealed, hash-locked holdout proof rather than a report. We do not
> claim cross-department cataloging at fleet scale or memory across weeks of asynchronous
> operation; those are out of scope by design, and stated as such before anyone asks.

**Short (one sentence, for a tight field):**

> CRUCIBLE is the pre-deployment adversarial gate an agent has to pass before it belongs in a
> fortified enterprise fleet — a structurally-separated multi-agent network in which every
> component that DECIDES anything is pure code with no model in it, enforcing its trust
> boundary in IAM rather than in a prompt.

**For the Architectural Discipline / Multi-Agent Nexus section specifically (Framing B, no
hedge needed — this is what was built):**

> Three model-bearing agents propose, diagnose, and repair; the separation between them is
> enforced by output schema, IAM, and code, not by instruction — the component that writes the
> autopsy has no field in its own output schema a fix could occupy, and the component that
> writes the patch cannot read the fixture suite that will grade it.
