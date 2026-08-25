# The architecture beat — animation specification

**Owner:** coordinator. **Set by Eric 2026-08-24.** These three rules are the spec, not
suggestions. Anything the animation does that is not one of these three is decoration and
gets cut.

The beat is **0:50–1:35 of the demo video, 45 seconds**, diagram on screen the whole time
(`docs/execution-spec.md:566`). `docs/contest/CONTEST.md:163` makes a clean architecture
diagram a named sub-test of the 30% Demo & Documentation criterion.

**No conflict with the unedited-execution rule.** `CONTEST.md:160` governs beats where the
agent runs. This beat is explanation.

---

## Rule 1 — Spotlight, never build-on

The full topology is visible from frame one. A judge sees the whole system immediately;
they do not watch it assemble. The named component brightens, everything else drops to a
dimmed state.

**Sequence gets shown without hiding the shape.** A build-on animation withholds the
architecture for 45 seconds and delivers it only at the end, which is precisely backwards
for a judge scoring whether the architecture is legible.

## Rule 2 — Blindness is the move nobody else has

When a component lights, **the things it cannot see go visibly dark in the same beat.**

For the ARMORER that is: the attacker's payload text, the benign suite, the Warden report
contents, the held-out family. Four things going dark in one beat is a two-second visual
for a claim that takes twenty seconds to narrate.

The blind list is not invented for the animation. It is
`docs/architecture-spec.md` §1.1 and it must be read from there at build time, never
recalled. **The Objective Set is on RED's blind list, not the ARMORER's** — that
distinction has already been got wrong once.

This is the most distinctive claim the project makes and no other entrant will have it.

## Rule 3 — The trust boundary resolves last

The boundary line is drawn the entire time, not revealed. On the closing line, everything
left of it desaturates while the right stays full colour.

Left of the line is model-generated and untrusted. Right of it is deterministic code.
**No model ever decides whether a breach happened.**

One move, and the thesis lands visually before the sentence finishes.

---

## Build constraints that follow from the three rules

- **Colour carries semantics, never decoration.** Brass `#9A6B12` = contains a model =
  untrusted. Verdigris `#2C6355` = pure code = deterministic. Rust `#94371F` = a refusal
  or rejection path. Palette is the project's own, from
  `docs/devpost/crucible-explainer.html`.
- **The cue list is data, not code** — a timestamp-to-node-state file. When narration
  timing shifts, timestamps get edited, not animation.
- **The cue list holds pointers into the diagram, so it needs a check that can fail.**
  Every cue id must resolve to a node that exists; every component node must appear in at
  least one cue. Add a component and forget to narrate it, the check fails. This is the
  ARMORER dangling-pointer defect (ruling 51 work, 2026-08-24) in a new medium — it has
  already cost this project one bad live run.
- **Narrate first, then cue to the recorded audio.** Reading to a machine's clock produces
  stilted delivery. Eric's pacing sets the timestamps.

## What must NOT be in the diagram

**Deployment status.** Ruled 2026-08-24. A status baked into an image has no owner and goes
stale silently — `docs/diagrams/architecture.md` carried "Cloud Run NOT DEPLOYED — 0
services" and "no cartographer module exists" for days after both became false, and it
nearly reached a judge. Ruling 46 in a different medium.
