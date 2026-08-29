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

Above the line is model-generated and untrusted. Below it is deterministic code.
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

---

# PRODUCTION SPEC — added 2026-08-24

The three rules above are the intent. This half is what a builder needs so nothing
below gets invented on the fly.

## Frame

**1920x1080, 16:9.** The diagram must be legible in full at frame one (rule 1), so nothing
may depend on zooming or panning. Type floor: no text below 16px at 1920 width.

## The node set is FROZEN at what `docs/diagrams/_loop.mmd` contains

18 nodes, ids exactly as they appear there: `GOV RED TGT PLG ENG LED TW DRY CONV COR ADP
ARM VAL FLOOR NARROW WAR GATE NEXT`. Three bands: PROVOKE, RULE, REPAIR.

**Adding a node after the cue list is written is the failure this spec exists to prevent.**
If the architecture changes, the node set is re-frozen and the cue list is re-validated
first. Never the other way round.

## Colour carries semantics, and only semantics

| Token | Hex | Means |
|---|---|---|
| brass | `#9A6B12` / fill `#E9DCBD` | contains a model. UNTRUSTED |
| verdigris | `#2C6355` | pure code. DETERMINISTIC |
| rust | `#94371F` | a refusal or rejection path |
| ground / ink | `#F1F3EF` / `#14181B` | everything else |

No node gets a colour for emphasis, contrast, or variety. Palette source:
`docs/devpost/crucible-explainer.html`.

## The trust boundary is a real line at a real coordinate

Drawn from frame one, not revealed. Every `[M]` node sits on one side, every `[C]` node on
the other. If the layout cannot place them cleanly on two sides, **the layout is wrong** -
do not compromise the line, which is rule 3 and the closing thesis.

## Cue list

A data file, `docs/diagrams/loop-cues.json`. Cued to Eric's RECORDED narration, not to the
script's estimates - N4's real duration sets the timeline.

```json
{
  "beat": "N4", "duration_ms": 45000, "svg": "loop.svg",
  "cues": [
    {"t_ms": 0,     "spotlight": [],      "dim": [], "note": "full topology visible"},
    {"t_ms": 3200,  "spotlight": ["RED"], "dim": []},
    {"t_ms": 18000, "spotlight": ["ARM"], "dim": ["RED_PAYLOAD","BENIGN","WARDEN_REPORT","HELDOUT"]},
    {"t_ms": 41000, "boundary": "resolve"}
  ]
}
```

`spotlight` brightens; everything not listed dims. `dim` names blindness targets (rule 2).
`boundary: "resolve"` fires rule 3 exactly once, last.

## The validator is the point, not a nicety

`scripts/check-loop-cues.py`, exit non-zero on any of:

1. a cue id that resolves to no element in the SVG **(the dangling pointer - this is the
   ARMORER defect that cost a live run, in a new medium)**
2. a node in the SVG named by no cue **(a component nobody narrates)**
3. `boundary: "resolve"` appearing zero times or more than once
4. any `t_ms` beyond `duration_ms`, or out of order

**Write one deliberately-broken fixture the validator must always reject**, the same reason
the eval harness ships known-bads: a check that cannot fail is not measuring anything.

## Blindness targets

Read the per-component blind lists from `docs/architecture-spec.md` §1.1 at build time.
**Do not recall them.** The known trap: **the Objective Set is on RED's blind list, NOT the
ARMORER's** - that has been got wrong once already.

## Capture

Playwright drives the page and records. Each beat is one unbroken take; cuts fall between
beats, never inside one. This beat is explanation rather than execution, so it sits outside
the unedited-execution criterion either way.
