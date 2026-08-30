# Handoff to Claude Design — the CRUCIBLE architecture plate

**Date:** 2026-08-29 · **Repo:** `C:\dev\crucible` (public, Apache-2.0) ·
**Deadline:** the submission closes **2026-08-31 17:00 PT**, so this is a
one-pass job with no second review cycle.

## The ask, in one line

Two skeletons exist. **Both are factually correct and neither is beautiful.**
Take one and make it a piece of design.

## What CRUCIBLE is, briefly, so the design has something to be about

A pre-deployment hardening harness for AI agents that hold real permissions —
agents that can move money, email customers, or call other agents. A red-team
model attacks a target agent. A pure-code tripwire records what the target
actually *called*, not what it said. A Coroner writes the autopsy and is
structurally incapable of proposing a fix. An Armorer writes policy rules in a
three-verb language with no `allow` verb, so no sequence of patches can widen
what the agent may do. A pure-code gate promotes or rolls back.

**The through-line is blindness.** Every component is deliberately prevented
from seeing something, and several of those boundaries are enforced in Cloud
IAM rather than in an instruction. That is the idea the plate has to carry, and
it is the thing the current hero plate buries.

## The two candidates

Both at `docs/diagrams/directions/`. Both 1920x1080, self-contained SVG, dark
ground, verified to parse and to carry no external references.

### `A-cast.svg` — the cast of characters

Nine components as cards. Each says who it is in plain English, what it does,
and **what it is not allowed to see**. A left column for the agent under test
with its eight tools grouped by capability; six numbered cast cards in a 2x3
grid; a full-width sealed-set band across the foot. Blindness is marked per
`(component, target)` pair with a filled dot for IAM-enforced and a hollow ring
for convention-plus-code-check, which is a distinction the repo insists on and
which must survive any redesign.

Three type sizes: 24 / 26 / 40.

### `B-journey.svg` — follow one attack

Nine numbered beats in three acts. A real poisoned-note attack from the corpus,
traced from the sentence that triggered it to the rule that stops it, ending on
the sealed family. Concrete tool calls with real argument values on the plate,
so a non-engineer can see that the *argument* is what crossed the line and not
the agent's words. Its near miss differs from the attack in exactly one
argument, which is what makes the "did the fix break ordinary customers" beat
show rather than assert.

Four type sizes: 24 / 25 / 30 / 54.

### Which to pick

**Your call.** They solve different halves of the same problem: A explains the
system, B explains what happens. A is closer to what was asked for (each agent,
what it is, what the tool calls are). B is more likely to hold a stranger's
attention. Merging them is allowed and probably worse than committing to one.

## LOCKED — do not change any of this

The repository has a hard claims discipline and a documented history of
fabricated statements reaching public surfaces. **Every factual assertion on
both plates was verified against a named source file.** Treat all of it as
frozen copy.

- **No percentage, rate, pass rate, transfer figure, or convergence result may
  appear.** None are quotable. There is no number on either plate that is a
  result, and none may be added. Counts of things that exist are fine.
- **Red-team attack discovery is a DESIGN, not a shipped capability.** Nothing
  in the tree originates an attack. Selection is deterministic from an authored
  corpus and the model only varies the wording, so any phrasing that credits
  the system with producing attacks of its own is false. Both plates already
  word this carefully.

  *(The claim gate pattern-matches for the false sentence and cannot tell a
  prohibition from an assertion, so this rule is stated without spelling the
  banned phrasing out. That is the right outcome twice over: a handoff that
  wrote the sentence in full would also be a place someone could copy it from.)*
- **Three verbs — `deny`, `constrain_arg`, `require_approval`. There is no
  `allow` verb.** This is the load-bearing claim of the whole architecture.
- Capability class names are exact: `CAP_MOVES_MONEY`, `CAP_EXTERNAL_COMMS`,
  `CAP_MUTATES_DURABLE_STATE`, `CAP_READS_PII`, `CAP_ESCALATES_PRIVILEGE`,
  `CAP_INVOKES_AGENT`, plus the sentinel `UNCLASSIFIED`.
- Model pins are exact. Any `gemini-2.5-*`, `gemini-3.1-*`, or bare
  `gemini-3-*` id is dead for this project.
- **Never print a hash value.** A frozen hash has exactly one owner, the
  artifact. Both plates cite the path instead; keep it that way.
- **The IAM-versus-convention distinction may not be flattened.** Drawing a
  convention boundary as though it were enforced is the precise defect this
  project exists to catch, and doing it on the plate that explains the project
  would be the worst possible place to do it.
- **The sealed held-out set stays prominent.** It is the most distinctive claim
  CRUCIBLE makes and it is a hard requirement from the project owner. A's band
  is roughly 14% of the plate; B gives it the terminal position and the widest
  element. Either is acceptable. Shrinking it is not.
- A's sealed band carries a **disclosed leak footnote**. That disclosure ships.
  It is not a blemish to tidy away; publishing the worst fact unprompted is the
  house style and it is what buys belief in the rest.

If you believe a claim is wrong, **say so and stop** — do not correct it. Every
one of them traces to a file, and changing the words changes what the project
is asserting in public.

## FREE — this is the actual job

Everything visual. Typography, scale, weight, colour, texture, composition,
grid, whitespace, rhythm, the reading path, iconography, how a card is drawn,
how an edge is drawn, how emphasis is made. The skeletons are structurally
sound and visually plain; assume nothing about their layout is precious except
where it serves a locked item above.

Specific weaknesses worth attacking:

- **The eye has no obvious entry point.** Neither plate makes it unmistakable
  where to start reading.
- **Everything has the same visual weight.** The blindness markers are the
  idea, and they read as footnotes.
- **The type scale is functional, not expressive.** Three or four sizes doing
  every job.
- **No texture, no depth, no material.** Flat fills and hairlines throughout.
- **The sealed set is prominent by size, not by design.** It is bigger. It is
  not more interesting.

The audience is a contest judge who is not necessarily an engineer, reading
quickly, on a laptop, having already looked at many submissions. Three seconds
to understand what kind of thing they are looking at.

## Technical constraints, all hard

- **One self-contained SVG.** No external fonts, no CDN, no remote `<image>`,
  no JavaScript, no `@import`. Web-safe font stacks with real fallbacks.
- **Presentation attributes, not a `<style>` block.** GitHub strips `<style>`
  from SVG rendered in markdown, and this plate ships in a README. Both current
  files already comply; keep it.
- **1920x1080 with `viewBox` set.** It goes on screen in a video at that size.
- **It must also read at 900px wide**, which is README width. That is a 0.469
  scale, so 24px on the plate is 11.25px to a reader. **Treat 24px as the
  floor** unless you are confident a smaller size survives, and check rather
  than assume.
- **Dark ground.** Both plates inherit the palette of the existing hero
  (`docs/diagrams/loop.svg`) so they read as siblings. A light version is a
  defensible choice only if you also say what happens to the existing plate.
- `<title>` and a `<desc>` that works for a screen reader. Both have them.
- Plain ASCII in code and comments. Display text may use typographic
  characters; `A-cast.svg` currently uses four em-dashes and eight middots,
  `B-journey.svg` uses HTML entities. Either convention is fine, one of them.

## Where it ships — three placements, one asset

1. **The README hero.** This is the one that scores. The contest's Demo &
   Production Readiness criterion is 30% of the weighted total and asks
   literally: *"Does the public GitHub repository feature a clean architecture
   diagram?"* Note that the current hero plate is referenced by **nothing** —
   not the README, not any Devpost update, not the gallery.
2. **The video, beat N4**, roughly 45 to 105 seconds of narration over it.
   There is a working animation player at `docs/diagrams/loop-player.html`
   driven by a cue list, and a Playwright capture harness at `capture/`. Both
   currently target `loop.svg`. If the new plate replaces it, the cue list
   needs re-pointing and its validator will say so.
3. **The Devpost gallery**, which currently holds one image.

## Reference material

- `docs/what-crucible-is.md` — the plain-language description
- `docs/architecture-spec.md` §1.1 — the per-component blind lists, verbatim.
  **The known trap: the Objective Set is on RED_STRATEGIST's blind list, NOT
  the ARMORER's.** That has been got wrong once already.
- `docs/diagrams/architecture.md` — six Mermaid diagrams, and §2a/§2b are what
  classify a boundary as IAM-enforced or convention
- `docs/diagrams/loop.svg` — the current hero, for palette
- `docs/devpost/crucible-explainer.html` — the light palette, if you argue for it
- `docs/design/narration-LOCKED-2026-08-27.md` §N4 — the words a viewer hears
  while looking at this
- `README.md`, including its *"what is not defensible today"* section

## Do not

- Read anything under `corpus/sealed/`, or run any `gcloud` command against
  `gs://crucible-sealed-x7`. That set opens exactly once and an unattested read
  voids an unrepeatable measurement.
- Commit, stage, or push. Leave the file in the working tree and report.
- Edit `docs/diagrams/loop.svg`, `loop-cues.json`, or `loop-player.html`. Those
  belong to the animation and have a validator that diffs them.

## Deliverable

One SVG at `docs/diagrams/directions/`, named for the direction you took.
Report which candidate you started from, what you changed and why, your
smallest effective type size at 900px, and anything in the locked list you
believe is wrong.

---

# AMENDMENT, 2026-08-29 — the second pass came back worse, and it was my brief

Eric's verdict on the revision: **"too cramped, too hard to follow."** He is
right, and the cause is upstream of any design decision.

## The measurement

| plate | text nodes | words | type sizes |
|---|---|---|---|
| `A-cast.svg` | 95 | **476** | 3 |
| `A-cast-blind-by-design.svg` | 97 | **476** | 4 |
| `B-journey.svg` | 94 | **420** | 4 |

A 1920x1080 plate that a judge reads in three seconds carries **80 to 150
words**. These carry three to five times that. **The second pass kept every one
of the 476 words and added visual weight to them**, which is the only thing that
could have made it worse rather than better.

**This is not a design failure. It is a brief failure, and it is mine.** I
handed over a wall of locked facts and asked for beauty on top of it. Design
cannot cut content it has been told is frozen, so it did the only thing left and
made the container heavier.

## The new hard budget. These are limits, not targets.

- **160 words maximum on the plate.** Count them. If you are at 200, you are not
  close.
- **40 text nodes maximum.**
- **At least five distinct type sizes.** Three sizes over 95 nodes is why
  nothing has hierarchy: everything is either "big" or "small" and the reader
  has no path.
- **At least 35% of the plate is empty.** Whitespace is the deliverable here,
  not a leftover.

## What the plate MUST carry. Nothing else is required.

1. **The target agent**, and that it holds real permissions - it moves money in
   a real ledger.
2. **The loop, in order**: an attacker, the target, the tripwire, the coroner,
   the armorer, the gate. Six things.
3. **Which of those contain a model and which are pure code.** This is the
   single most important distinction on the plate and it should be readable
   from across a room.
4. **Two blindness facts, not nine.** Pick the two that are enforced in Cloud
   IAM, because those are the ones a judge can verify and the ones that are not
   a promise: the Coroner cannot write to the policy bucket, and the Armorer
   cannot read the sealed corpus.
5. **The sealed held-out family.** Unchanged from the original brief - Eric's
   hard requirement and the most distinctive claim here.

That is roughly six nodes, one band, and a legend. At fifteen words each it
lands near 110 and leaves room to breathe.

## What to CUT. All of it. This is the list, and it is permission, not a hint.

- **The eight tool names.** "It can move money and send email" is the point; the
  function names are not.
- **The six `CAP_*` class names.** They were locked because they must be exact
  IF PRESENT. They do not have to be present.
- **The model version pins.** A judge does not check `gemini-3.7-flash` off a
  diagram.
- **Seven of the nine blindness rows**, and the enforcement-class legend that
  goes with them once only IAM-enforced ones remain.
- **The fixture counts** (26 benign, 14 near-miss, 9 known-bad).
- **The leak footnote.** This is NOT being hidden: it lives in `README.md`
  under *"what is not defensible today"*, which is where a reader looking for
  the accuracy boundary goes. A diagram is not the accuracy boundary and never
  was; putting it there cost the plate a line and bought nothing.
- **Every second sentence in every card.** If a card has two lines, one of them
  is doing the other's job.

**Everything cut here stays true and stays published elsewhere.** The locked
list in the original brief governs what may be SAID, not what must be SHOWN. A
fact that is not on the plate is not a fact that has been retracted.

## The test to run before you hand it back

1. Print it, or view it at 900px wide.
2. Look for three seconds. Can you say what kind of system this is?
3. Look for fifteen. Can you name the loop's order and say which parts are
   models?
4. Count the words. Over 160 and it goes back regardless of how it looks.

If you cannot do 2 and 3, the answer is to cut more, not to restyle. Every
previous pass has answered a legibility problem with more design, and that is
the move that produced a worse plate from a better-looking one.

## Which to start from

**`B-journey.svg`**, and cut it to five beats instead of nine. It has the
strongest reason to exist - a reader follows a story without a glossary - and
beats are easier to delete than a topology is to thin. `A-cast` has to keep
every component to remain a cast, which is exactly the constraint that
overloaded it.
