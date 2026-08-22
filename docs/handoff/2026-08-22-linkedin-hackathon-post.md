# Handoff to the `/linkedin` session — hackathon post + image

**Prepared by the `/crucible` session, 2026-08-22. This is a BRIEF, not a draft.**
Per Eric's ruling 2026-08-22, `/crucible` prepares prompts and image briefs; `/linkedin`
owns the draft, the render, the critic loop, the queue and the post. Nothing here is post
copy and none of it should be treated as approved phrasing.

---

## 1. THE HARD REQUIREMENT — this is the whole reason the post exists

**The post MUST contain the literal string `#AllThingsAgenticHackathon`.**

This is not a preference and not a growth tactic. It is a **scored bonus condition** in the
Google "All Things Agentic" hackathon: *a public social post on X, LinkedIn, Instagram or
Facebook carrying that hashtag is worth +0.2.* Final scores run 1 to 6. **+0.2 is 4% of the
maximum, and nothing Eric has posted anywhere has ever carried that string.**

If the critic loop or a voice rule would strip the hashtag, **the hashtag wins and the post
gets restructured around it.** A post that reads perfectly and omits the tag scores zero on
the only criterion it was written for. Flag it back to `/crucible` rather than dropping it.

Recommend also including a plain sentence saying the project was built for the hackathon.
That is a *different* bonus's requirement and it costs nothing here, but it is optional on
this surface.

**Note on the existing reply-policy rule:** Eric's canon says no hashtags in *replies*. This
is a post, not a reply, and the rule does not reach it.

---

## 2. RECOMMENDED ANGLE — the comment stripper

Lead with this. It needs no measured number, which matters — see section 4.

**What happened, verified from source today:**

CRUCIBLE has a component called the ARMORER whose only job is to write a policy patch closing
the capability path an attacker used. It gets four things and nothing else: the grammar, the
capability manifest, the current policy, and one breach record. It is deliberately blind to
the attacker's text and to every test fixture.

On the first live run of the loop it reached for the same blunt verb every time, a flat
`deny`. The gate rejected its patch twice for blocking legitimate work, then halted for a
human.

The frozen grammar contract **already says** which verb is usually right in that situation.
It is written in the contract, in plain English, directly beside the production it governs.

The function that hands the grammar to the model strips comments. Mechanically. As designed,
and correctly, because those comments cite internal rulings and corpus material the component
is not allowed to see.

**So the rule the contract states had never once reached the component that needed it.**
Measured: the handout is 1,577 characters and contains none of the three phrases carrying
that steer.

**The thought worth landing:** documentation a tool strips is documentation that does not
exist. The contract was right, the stripper was right, and the rule was still invisible.

**Why this angle:** concrete, happened today, needs no metric, and reads as real engineering
rather than a launch announcement. It also puts Eric in the sentence doing something, which
the voice canon asks for.

---

## 3. ALTERNATE ANGLE, if the critic loop rejects the first

**Three layers of the same stale hash.** A hash-locked value was frozen four times in one day.
A published post carries the first freeze. Every internal document written to *correct* that
post carries the second. The artifact in force is the fourth. **Every document that corrected
the drift was itself stale**, because a correction that copies a moving value inherits the
defect it was written to repair. The fix was to stop restating the value in prose anywhere,
including in the spine document that owns the project's frozen numbers.

Weaker than section 2 for a general audience, stronger for an engineering one.
`/linkedin`'s call.

---

## 4. ACCURACY BOUNDARY — read before drafting, and treat as blocking

**Post NO measured result. None.** Specifically forbidden in this post:

- Any ASR, breach-rate, transfer, or convergence figure.
- The first live run's breach counts. They were measured against **six hand-authored attack
  seeds, not the project's 50-instance hash-locked corpus** — a gap `/crucible` found today
  and is actively fixing. Any number from that run needs a caveat longer than the post.
- Any G7 or G8 claim. Those gates have not been exercised in a run that produced a promotion.
- Anything implying the loop has hardened an agent end to end. **Nothing has been promoted
  yet.** The gate has only ever rejected.
- Anything implying the project has won, placed, or been evaluated. It has not been submitted.

**Safe to say:** the project exists, what it is for, what the architecture separates and why,
and the comment-stripper story in section 2, which is a build anecdote rather than a result.

**If the draft needs a fact not in this brief, return `BLOCKED: <what you need>` to
`/crucible`.** Do not reconstruct a CRUCIBLE fact from memory or from an older post. Several
numbers in this project have moved four times in a single day.

---

## 5. VOICE

`/linkedin` owns this entirely. `voice.md` and `voice-calibration.md` govern, the checker
gates, and nothing in this brief overrides either. Two notes only, both about this brief's
content rather than about voice canon:

- The phrase "documentation a tool strips is documentation that does not exist" is **offered
  as a thought, not as approved copy.** It has the shape of an aphoristic hinge, which the
  canon watches for. If it reads as a manufactured closing line, cut it and state the thing
  plainly instead.
- Resist making the comment stripper sound like a villain. It is doing its job correctly, and
  the fact that both halves were right is the actual point.

---

## 6. IMAGE BRIEF

Hand this to the render loop. It is a design direction, not a prompt to paste verbatim.
`/linkedin` owns the final prompt.

**Subject.** A single technical document, rendered as a tall column of monospaced text, seen
straight on. Roughly a third of the lines are present and legible as texture. The rest have
been **removed** — not blacked out, not redacted, not censored. Removed, leaving clean empty
space where the line used to sit, so the column reads as sparse rather than damaged.

**The point the image must carry.** Nothing was destroyed. Something is simply not there, and
the page looks orderly enough that the absence is easy to miss. A viewer should have to look
twice to notice how much is gone.

**Explicitly avoid.** Redaction bars, black rectangles, censorship imagery, shredded paper,
torn edges, fire, glitch effects, error-red highlights. All of those say *damage*, and the
subject is **silent omission**. Also avoid: robots, brains, glowing neural networks, padlocks,
shields, hooded figures, and any depiction of an AI as a face or an entity.

**Treatment.** Calm and clinical. Flat, even light. No drama, no vignette, no lens flare. It
should look like a screenshot of something real rather than an illustration about technology.

**Palette.** Restrained and near-neutral. Paper-white or a very light warm grey ground, ink
nearer to charcoal than to pure black. At most one low-saturation accent, used once, and only
if it earns its place. No gradient, no duotone, no neon.

**Composition.** Single column, generous margins, plenty of empty space. Must stay legible as
a feed thumbnail: the sparse-column silhouette has to survive being 400 pixels wide.

**Text in the image.** None, or near none. If characters appear they should read as plausible
technical text at a glance and must not be legible enough to assert anything. **No real
hashes, no real file paths, no real code from the repo.**

---

## 7. WHAT `/crucible` OWES BACK

Ping `/crucible` if any of these come up:

- The draft needs a fact not in section 2 or section 3.
- The critic loop wants to cut the hashtag.
- `/linkedin` wants to include a number of any kind.

`/crucible` does not review the draft, does not approve the copy, and does not queue anything.
