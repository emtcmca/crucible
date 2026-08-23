# T2-8 — the run has to look like something. Scope, before any of it is built.

**Written 2026-08-23 at Eric's instruction: *"We should legitimately scope this out before
diving into it."* Nothing here is built. This document decides what would be built and,
more usefully, what would make it dishonest.**

Eric's vision, kept verbatim because the paraphrase loses the shape:

> *"We could even split screen the demo for part of the video, showing a scrolling terminal
> that matches second for second with a visual flowchart showing which agents are active in
> the moment, what they're doing, what they're communicating and to whom, and how all of this
> pushes the work toward actionable data and resolutions for the end user."*

---

## 1. The one architectural decision, and everything else follows from it

**ONE EVENT STREAM, TWO RENDERERS.**

The terminal and the flowchart must be two views of **the same emitted events**, never two
independent descriptions of the same run. That is the whole design, and it is not an
aesthetic preference:

- **Second-for-second sync stops being a production problem and becomes a property.** If the
  flowchart is driven by the events the terminal prints, they cannot drift. Hand-syncing an
  animation to a screen recording is both expensive and a lie waiting to happen.
- **It is the only version this project is allowed to ship.** The overclaim sweep of
  2026-08-22 found ten claims in the existing text render that the code never computed. **A
  richer renderer is a larger surface for exactly that defect.** If the flowchart can only
  draw what the stream contains, an overclaim becomes structurally hard rather than a matter
  of discipline.
- It makes the visual **checkable**. Anything on screen can be traced to a line in an
  artifact a judge can open.

**The rule that falls out, and it is the one to enforce in review: the visual layer may
render only what the event stream carries. It may not compute, infer, smooth, or predict.**
If the flowchart wants to show that the ARMORER is "thinking," there must be an event saying
so. Animating a state the code was not in is a fabrication on camera, in a project whose
entire subject is agents doing things they should not.

---

## 2. What the stream carries

Not designed yet. The shape it must support, drawn from what the loop actually does:

| moment | what a viewer needs to see |
|---|---|
| round opens | the budget governor authorising or refusing |
| attack issued | which family, which instance, the text going in |
| tool call | which tool, which capability class, ALLOWED or DENIED by policy at vN |
| episode scored | the TRIPWIRE's verdict and **which clause fired** |
| autopsy | the CORONER writing, one per breach |
| patch proposed | the ARMORER's verbs, and that it cannot promote |
| validation | accepted, or the error code that refused it |
| benign replay | the WARDEN's score against the 26-fixture floor |
| gate | PROMOTE or REJECT, and the reason |
| round closes | what changed, and what the next round inherits |

**Each event carries a real timestamp.** That is what makes "replay at recorded pace" honest
rather than theatre — the pacing is measured, not authored.

**The stream is also evidence.** An append-only, timestamped record of what happened when is
exactly the audit trail the track asks for, and Eric ruled on 2026-08-23 that the audit trail
is mandatory. This is not only a demo asset.

---

## 3. Three modes, one file

1. **Live** — the viewer tails the stream while the run executes. Genuinely live, and it is
   what the camera films for the live segment.
2. **Replay at recorded pace** — the same file, same renderer, played back at the timestamps
   it recorded. **Labelled on screen as replay**, per Eric's ruling on item 7.
3. **Post-hoc from the C6 bundle** — the bundle already validates against a schema and
   already is the product. A static evidence report is the judge-openable artifact and
   overlaps `BUILD-LIST.md` T2-7 Part A.

**Mode 2 is the one that makes the video producible.** A live run is one take at whatever
speed it happens to run; a paced replay of a real run is directable without being fake,
provided the label is on screen and the timestamps are the run's own.

---

## 4. What must NOT be built

- **No second product.** The bundle is the product. This is a renderer.
- **No dashboard, no server, no browser-side loop.** `BUILD-LIST.md` Tier 3 already refuses
  running the loop in a browser, and every reason still holds.
- **No hand-authored timeline.** If a beat cannot be driven from the stream, the beat does
  not exist.
- **No figure in a template.** Every number rendered is read from the stream or the bundle at
  render time. `tests/test_readme_claims.py` is the pattern: derive the expectation from the
  producer, and the test goes red when they disagree.
- **No inferred agent state.** "Active", "thinking", "waiting" are only drawable if emitted.

---

## 5. The risk that decides the sequencing

**Emitting the stream means touching the loop, and the loop is about to produce the run every
number depends on.**

Mitigation, and it is a pattern this project already uses: the emitter is an **injected sink
with a no-op default**, the way `holdout_touch` is an injected callable. With no sink passed,
the run path is byte-for-byte what it is today. That makes the change provably inert on the
measurement path, which is the only version worth shipping before a live run.

**Eric's sequencing stands: agentic core first, presentation second.** This document exists so
the design is settled before there is time pressure, not so the work starts early.

---

## 6. Open questions, none of them answered here

1. **Render target.** Self-contained HTML in a browser is the most visually flexible and is
   what a split screen wants. A terminal TUI is cheaper and matches the existing aesthetic.
   Undecided.
2. **Does the stream go in the evidence bundle, beside it, or both?** It is evidence, so it
   should be durable — but it is also large, and C6 has a schema that would have to admit it.
3. **What is "actionable data and resolutions for the end user"** — Eric's closing phrase and
   the least specified part of the vision. The honest candidate is the **finding card** already
   scoped as `BUILD-LIST.md` T2-2: what was found, which clause proves it, the policy rule that
   now blocks it, and the command to reproduce. That is the "sense of real accomplishment upon
   completion of a run", and it is the last thing on screen.
4. **How much of the four minutes is split screen?** A whole video of split screen is as
   monotonous as a whole video of terminal.

---

## 7. What would make this fail

Recorded now, while it is cheap to read:

- **It looks impressive and asserts something the run did not do.** The single worst outcome,
  and the most likely one, because a visual invites narration.
- **It drifts from the loop.** The renderer is written against today's event shape, the loop
  changes, and the video shows a system that no longer exists. Mitigated only by the stream
  being the loop's own output rather than a description of it.
- **It eats the time the loop needed.** Which is why the sequencing is a ruling and not a
  preference.
