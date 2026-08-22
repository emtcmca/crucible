# Gemma, scoped: `CAPABILITY_CARTOGRAPHER` against an agent we did not write

**Prepared 2026-08-21 by the coordinator, for Eric's decision.** `ADR-0018`
withdrew the false Gemma-generates-the-corpus claim and deliberately left open
whether Gemma gets a real job. This is the concrete proposal.

---

## 1. The role already exists and was specified before Gemma was assigned to it

`architecture-spec.md:138` — `CAPABILITY_CARTOGRAPHER`, and note how tightly it
is already drawn:

| | |
|---|---|
| **Single responsibility** | Propose a capability class set for each tool the deterministic pre-pass could not resolve |
| **Input** | Tool name, description/docstring, argument JSON schema, declaring agent name, transport (function / MCP / AgentTool / LongRunningFunctionTool), any MCP annotations |
| **Output** | `{tool_name, proposed_classes[], confidence, evidence_per_class[]}` — one evidence string per class, **each citing a schema field or a docstring span** |
| **Blind to** | The attack corpus, the policy, the Tripwire. It runs before any round exists |
| **Never final** | Output is a **proposal**. Not written to the manifest until a human ratifies. **It cannot approve its own classification** |

That is not a slot invented to hold a model. It is a role with a stated blindness
boundary and a stated inability to self-approve — the same two properties that
make the Coroner and the Armorer defensible.

## 2. The problem with running it on our own target, stated first

**All eight tools in `target/refund_agent/capability_manifest.json` are already
classified. Zero `UNCLASSIFIED`.** Pointed at our own agent, the Cartographer has
nothing to resolve, and a component with no work is exactly the decorative
integration `BUILD-LIST` T1-5 refuses.

So the honest scope is not our agent. It is **an agent we did not write.**

## 3. What that unlocks, and it is more than a bonus point

### It is the persona's literal situation

`docs/contest/unlikely-hero.md` names the buyer as **the operations lead who
inherits an agent somebody else built.** That person's first problem is not
attacking it. It is **not knowing what its tools can do to the world.** The
Cartographer is the component that answers that, and it is currently the one
piece of the persona's story with no implementation behind it.

### It moves a track requirement that is currently PARTIAL

`docs/contest/track-fit.md` grades **R3 — "agents are cataloged for
cross-department use"** as PARTIAL, because the capability manifest catalogs
tools on **one** agent, hand-classified. A Cartographer that classifies a
**foreign** agent's tools is cataloging in the sense the track means. That is a
graded requirement moving on evidence rather than on wording.

### We have already done this once, by hand, and it found something

`CONVENTIONS.md:1753` carries an approved claim:

> *"CRUCIBLE found a capability-boundary inconsistency in a published Google ADK
> sample"* — `send_call_companion_link(phone_number)` takes no `customer_id`, and
> the guard gated on a key the tool does not take (`build-spec.md:425`).

**That was a human reading a foreign agent's tool signatures and noticing the
capability boundary did not hold.** The Cartographer is that pass, automated,
with evidence strings citing the schema field that gave it away. The finding is
already the proof the method works.

## 4. Why the reproducibility argument is TRUE here and was false for the corpus

`ADR-0009` argued an open-weights model pinned by version and seed makes the
artifact reproducible by a third party, and `ADR-0018` withdrew that for the
corpus — the corpus was hand-authored, and pre-registration rests on the
commitment hash, which does not care about provenance.

**For the Cartographer the argument holds, and this is the part worth being
precise about.** A classification is a *judgment* that shapes the taxonomy every
later rule binds to. "Why is `issue_store_credit` in `CAP_MOVES_MONEY`?" is a
question a skeptical reader can only re-examine if they can regenerate the
proposal and get the same answer. A commitment hash proves nobody changed the
answer afterwards; it does not let anyone check the answer.

So Gemma-pinned-by-seed buys something real here that it did not buy for the
corpus. **Same mechanism, different artifact, genuinely different value.** Say it
that way rather than reviving the withdrawn sentence.

## 5. The cost decision, which is the actual fork

`ADR-0009` §3.3 ruled Cloud Run + NVIDIA L4, `min-instances=0`, ~$0.34 for a
30-minute generation burst, and rejected the Vertex Model Garden managed API as
**"fallback only — you control neither the container nor the weights, which
weakens the reproducibility claim."**

That ruling was made for **corpus generation**, where the artifact was going to be
hash-locked and the reproducibility bar was absolute. **The Cartographer's output
is ratified by a human before it enters the manifest**, so the bar is lower by
design: a proposal a person checks does not need to be byte-reproducible to be
trustworthy, because the person is the check.

| Option | Cost | Reproducibility | Days |
|---|---|---|---|
| **A — Cloud Run + L4, `min-instances=0`** | ~$0.34/burst, GPU service to stand up and tear down | Full: pinned weights, pinned seed, third party can regenerate | Real work. 1–2 days with the deploy already proven |
| **B — Vertex Model Garden managed Gemma** | per-call, no infra | Partial: pinned model name and seed, not the container | Hours |
| **C — do not build it** | 0 | n/a | 0 |

**Recommendation: B, and say exactly what B does and does not give.** The +0.2
counts either way; the architectural story counts either way; and the difference
between A and B is a reproducibility claim we can state honestly in one sentence
rather than a claim we need a GPU to earn. **A is the better engineering and B is
the better use of nine days**, and `min-instances=0` on a GPU service is a
standing $193 risk if the annotation is ever wrong (`ADR-0009` says so itself).

If A is chosen, the one rule from `ADR-0009` survives unchanged: **verify
`min-instances=0` by reading the annotation after deploy, never by trusting the
deploy output.** That rule was written before today's Cloud Run deploy proved,
three separate times, that a healthy-looking deploy log says nothing about what
is running.

## 6. What must be true before this is worth starting

- **A target agent we did not write.** A published ADK sample is the obvious
  candidate and has precedent above. It must be one whose tools are genuinely
  unclassified — pointing it at something already mapped repeats §2's mistake.
- **The deterministic pre-pass must exist first**, or the Cartographer has no
  defined input: its job is only the tools the pre-pass *could not* resolve.
  **CHECKED 2026-08-21: it does not exist.** No classifier, no pre-pass, nothing
  matching `classify_tool` anywhere under `crucible/` or `target/`. The eight
  tools in our manifest were classified by hand.

  So **task one is pure code and has no model in it**: a deterministic pass that
  resolves what it can from the tool signature and marks the rest
  `UNCLASSIFIED`. That ordering is not incidental — it is what keeps the
  Cartographer's job small and its output checkable. **A model asked to classify
  everything is doing work a `str` comparison should have done, and its mistakes
  are then indistinguishable from its judgments.** Build the pre-pass, see what
  is genuinely left, and only then decide whether a model is warranted at all.

  It is possible the pre-pass resolves so much that the Cartographer is not worth
  building. **That is a real outcome and it should be allowed to happen**, rather
  than discovered after the GPU is standing.
- **A ratification step**, matching the existing pattern in
  `docs/proof/sealed-family-ratification.md` and `benign-retirement-ratification.md`.
  The Cartographer proposing straight into the manifest would break the one
  property that makes it defensible.

## 7. What we will not claim

- That Gemma generated the attack corpus. Withdrawn, `ADR-0018`.
- That the classification is authoritative. It is a **proposal**; a human ratifies.
- Any accuracy figure for the classification. Nothing has been measured.
- That this makes CRUCIBLE a fleet-scale catalog. It classifies one foreign
  agent's tools. `track-fit.md` R3 moves from PARTIAL toward MEET, not to MEET.
