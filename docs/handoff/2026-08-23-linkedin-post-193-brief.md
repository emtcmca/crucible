# Brief for `/linkedin` — draft 193 needs to be post ONE, not post THREE

**This is a brief, not a draft.** Authored by the crucible session, which does not draft,
renumber, render, or queue posts. The prose is `/linkedin`'s to write.

---

## The diagnosis, and Eric got there first

Eric's read is the structural one and it is correct: *"my followers need to be introduced to
crucible before we dive straight into build notes and specs."*

Draft 193 is a **post-three post in the post-one slot.** It opens on a comment stripper, a
prompt assembler, and a verb-selection defect. All of that is real and worth telling. None of
it means anything to a reader who does not yet know what CRUCIBLE is, what the Armorer is, or
why a policy patch has verbs at all. The reader has to hold four unfamiliar nouns before the
story pays off, and most will not.

**The two-sentence orientation the draft does give is doing the work of a whole post.** It
sits in paragraph two, is stated flatly, and never returns.

### Three further problems, once the first is fixed

1. **The bug's consequence is never stated.** The draft says round one rejected, round two
   rejected, halted for a human. It never says *why* — that the component kept reaching for a
   verb its own contract told it not to use, because the sentence telling it so was deleted in
   transit. That causal link is the entire story and it is left for the reader to assemble.
2. **The best idea is buried and flat.** *"I still think the stripper is right"* is the
   interesting turn: **both halves of the design were correct, and correct plus correct
   produced a silent failure.** That is a transferable idea about building with models. It is
   the second-to-last paragraph and it is stated rather than landed.
3. **It ends on a to-do.** *"I'm marking that contract now"* is a plan, not a finding. And it
   is behind the build: the steer has since been restored to the assembled prompt from
   `policy.ebnf`. **Verify current state before writing — do not take this sentence as fact.**

---

## What post one should do

**Job: make a stranger want post two.** One idea, one concrete proof it is real, one honest
statement of what is not yet known.

### The idea, in the order it should arrive

- Companies are handing agents real authority: refund money, close a case, email a customer.
- That authority gets tested by writing a list of nasty prompts — **written by the same person
  who built the agent**, so it tests the failures they already imagined.
- Worse: when they write a fix and re-run the tests, the tests pass, **because the fix was
  written after seeing the tests.** That number answers a question asked after the answer was
  known.
- CRUCIBLE attacks the agent, records what it actually *called*, writes a rule, checks the rule
  did not break legitimate work, and promotes or rolls it back.
- **One attack family is sealed away before any fix is written, and its fingerprint was
  published in advance**, so a stranger can check the ordering rather than take his word.

That last beat is the distinctive one. It is also the one nobody else in this hackathon is
likely doing, and it is what makes a follower want the result.

### The concrete detail that proves it is real

Pick ONE. Both are single sentences and both are checkable in the public repo:

- **There is no `allow` verb.** The patching component has exactly three: `deny`,
  `constrain_arg`, `require_approval`. **No sequence of patches it writes can enlarge what the
  agent is permitted to do.** That is a structural guarantee, not a policy, and a non-technical
  reader gets it instantly.
- **The identity that writes a patch is not the identity that promotes it**, enforced in cloud
  IAM rather than in code. The patching agent has no write access to the policy store at all.

`allow` is the stronger opener for a first post. IAM is the stronger one for a technical crowd.

---

## Facts available, all verified 2026-08-23 unless noted

**Read every count off the source named. Do not recall any of these, and do not restate a hash
anywhere — ruling 46.**

| Fact | Source |
|---|---|
| 8 tools across 6 capability classes | `target/refund_agent/capability_manifest.json`, counted at source 2026-08-21 |
| Three verbs, no `allow` | `README.md` "The loop" table |
| Six lock fields frozen before measurement | `docs/proof/*-freeze.json`, one record each |
| Sealed family fingerprint published in advance | `docs/proof/sealed-family-commitment.json` |
| Rules bind to capability classes, never tool names or payload strings | `README.md` |
| Per-agent models | read the four constants at source; they have drifted before |

### What may NOT be claimed, on any surface

- **No result exists.** No attack-success rate, no benign pass rate, no transfer figure, no
  convergence result. Nothing has been promoted.
- The first comment's honesty about this is **the strongest thing in the current draft** and
  should survive whatever the body becomes.
- Nothing about Gemma's classification quality — no accuracy figure has been measured, and the
  ratification sheet is unsigned.

---

## Where the stripper story goes

**Post three or four, once the reader knows what the Armorer is and why its input is
restricted.** It lands much harder there, and it needs three changes:

1. State the cost: the component burned two rounds reaching for a verb its own contract ruled
   against, because the guidance was stripped on the way in.
2. Land the turn: both halves were correct. The failure came from the seam between them, and
   nothing tested the seam.
3. End on the finding, not the to-do — **the prompt a model receives is not the file you
   wrote.** There is an assembly step in between, and nobody tests assembly steps.

---

## Mechanical

- `#AllThingsAgenticHackathon` must survive into whatever ships. It is the bonus tag and
  nothing carrying it has been published yet.
- Both variants (full and tight) and both through `voice-check.mjs`, per standing rule.
- The current image was made for the stripper thesis. **If the body becomes post one, the image
  brief changes too** — it should carry the sealed-holdout or the three-verbs idea, not a
  prompt-assembly diagram.
