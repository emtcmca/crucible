# The pre-pass result, and how it is told

**Canonical framing. Written 2026-08-22 at Eric's instruction, to be cited rather than
retyped.** Every judge-facing surface — the Devpost project description, the architecture
write-up, the portfolio case study, coming Devpost updates, the demo narration — draws this
story from here. **Do not restate the numbers in those documents; cite this file and read
them off the source named below at the moment of writing.** Ruling 46: a fact copied into a
fifth document is a fact that will disagree with itself by Thursday.

---

## 1. The measurement

**Verify on use. Do not recall these.** The pre-pass is
`crucible/cartographer/prepass.py`; the foreign agent is the ADK `customer-service` sample
pinned at a verified upstream commit. Both figures were measured 2026-08-22:

- On **our own** target agent, the deterministic pre-pass resolves **6 of 8** tools.
- On an agent **we did not write**, it resolves **0 of 12**.

The reason is not subtle. Every rule keys on *our* argument vocabulary — `amount` plus
`currency`, a `to` documented as an email address, `status_to`, `*_agent`, `queue`. The
foreign agent takes `phone_number`, `discount_type`, `value`, `customer_id`, `items_to_add`,
`delivery_method`. No overlap, so no rule fires.

---

## 2. Why this is a finding rather than a failure

**Deterministic capability classification does not transfer across agents.**

That sentence is the result, and it is the thing a fleet-scale cataloging story has to
answer. It is also the justification for having a model in the loop at all. Without the
measurement, *"we use a model to classify tools"* is an unjustified design choice and a
judge is entitled to ask why a string comparison would not do. With it, the choice is
**measured**: we built the cheap layer first, ran it, and it did not generalise.

The ordering was deliberate and predates the result. `docs/decisions-pending/gemma-scope.md`
§6, written before the pre-pass existed: *"Build the pre-pass, see what is genuinely left,
and only then decide whether a model is warranted at all... It is possible the pre-pass
resolves so much that the Cartographer is not worth building. **That is a real outcome and it
should be allowed to happen**, rather than discovered after the GPU is standing."*

The stop condition it named did not fire. **Its mirror image did**, and that is reported
rather than glossed — see §3.

---

## 3. The tension, stated rather than buried

`gemma-scope.md` §6 also says: *"A model asked to classify everything is doing work a `str`
comparison should have done, and its mistakes are then indistinguishable from its
judgments."*

**At 0 of 12, the model is classifying everything on this agent.** The pre-pass-first
architecture is real and enforced in code (`split_residue()`), and on this particular target
it is currently buying nothing.

**So the pre-pass is not carrying the load. The ratification gate is.** That is why the gate
is built the way it is, and why it is the part worth reading:

- Every proposed capability class must cite **an argument that tool itself declares**, or a
  span **verbatim** from its own docstring.
- A name borrowed from a sibling tool is rejected. A paraphrase of the same true claim is
  rejected.
- **A fabricated citation is a parse failure, not something a reviewer has to catch.**
- Nothing enters a capability manifest without a **named human** signing against a digest.

A judge who spots something we glossed will trust nothing else in the write-up. Stating this
tension costs nothing and buys the rest of the document.

---

## 4. What we refused to do, and why it belongs in the story

**We did not improve the pre-pass to make the number look better.**

With only those twelve tools visible, any rule added now is measured against the same twelve.
That is tuning to the fixture, and it is the same defect as tuning a prompt until a
measurement flatters it — which this project refused elsewhere on the same day, leaving a
`constrain_arg` paragraph byte-identical and pinned by a regression test rather than
weakening it to unstick a loop.

**Eric's ruling, 2026-08-22, and it is a project principle rather than a one-off:**

> *"If we need to make numbers look better anywhere in this project, we do the work to make
> the numbers better legitimately. We do not tune the ruler or skirt the real work to
> artificially inflate numbers."*

Rules keyed on structural signals that genuinely transfer — an argument whose type is a
currency amount, a docstring naming an external recipient — are a real improvement and an
honest roadmap item. **Naming that as future work is honest. Doing it tonight and reporting
the improved figure is not.**

---

## 5. The paragraph, for a judge-facing surface

Adapt the voice to the surface; do not change the claims. **Read the two figures off §1's
sources at the moment of writing.**

> We built the deterministic pass first and measured it before adding a model. On the agent we
> wrote, it resolves six of eight tools. On an agent we didn't, it resolves zero of twelve —
> its rules encode our vocabulary, not a general one. That result is why the model tier exists,
> and why every proposal it makes must cite the tool's own declaration and be ratified by a
> named human before it enters a manifest.

---

## 6. What may NOT be claimed, on any surface

Binding, from `gemma-scope.md` §7 and the cartographer lane's own report:

- **No accuracy figure.** Nothing has been measured against a labelled set.
- The classification is a **proposal**. Never authoritative.
- **Gemma did not generate the attack corpus.** Withdrawn by `ADR-0018`; the corpus is
  hand-authored and carries no generator provenance on any instance.
- This is **not a fleet-scale catalog**. It classifies one foreign agent's tools.
- Track requirement **R3 moves toward MEET, not to MEET.**
- Until the Cartographer has actually run, **no Cartographer classification exists** and the
  write-up says so.

---

## 7. Why this is a differentiator rather than a liability

Almost nobody publishes a negative measurement about their own component. In a track named
**The Fortified Enterprise Fleet**, where the subject is systems that can be trusted with real
permissions, a project that measures its own layer, finds it contributes nothing on a novel
target, and says so — then shows the structural control that carries the load instead — is
making the track's own argument with evidence.

**The practical point, which is the one that decides it:** the result is visible either way.
`prepass.py` is 319 lines in a public repository. If the write-up omits it, a judge finds it
and asks what it contributed, and the answer becomes *"nothing, and they didn't say so."*
The only variable is whether we said it first.
