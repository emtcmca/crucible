> # WITHDRAWN 2026-08-25, the same day it was written.
>
> **The 729-pair / zero-discordant result in this document does not reproduce and must not
> be quoted.** Re-derived from `evidence/batch-night-2026-08-25/` on the only link the data
> carries, `derived_from_attack_id`: **1,949 pairs, 70 discordant.** A stricter pairing
> (same attack, same run, both scorable, split by `provenance`) gives **273 pairs, 10
> discordant**. Positional in-round pairing gives 731, close to 729, but **94 discordant**,
> and it pairs across different families so it is not a valid pairing at all. No
> construction reproduces 729 with zero.
>
> **CRUCIBLE makes no claim about paraphrase invariance in either direction.** The
> measurement that would support one has not been made.
>
> **The text below is preserved unedited on purpose**, the same way `ADR-0009` is kept
> below `ADR-0018`. A record of a claim made, checked and withdrawn is worth more than a
> document that appears always to have been right. Read it as an error, not as a finding.
>
> **How it survived to publication.** It was written as the correction to a 2.2x
> composition artifact, so it arrived carrying the authority of the thing that caught an
> error. A null result that kills a flattering finding gets less scrutiny than the
> flattering finding did, purely because of the direction it points. That is the
> transferable part, and it is now the entry in `docs/design/` rather than the result.

# Paraphrasing a corpus attack does not change whether it breaches

**Measured 2026-08-25 over the 60-run overnight batch. 1,770 episodes, 1,616 scorable,
single-sample k=1, no stability estimate.**

**This document exists partly to record an analysis I nearly published and should not
have.**

## The marginal comparison, which looked like a finding and is not one

The hybrid attack mode splits each round between corpus text used verbatim
(`provenance: training_corpus`) and model-authored variants of those seeds
(`provenance: generated`). Both arms came out at exactly n=885.

| arm | BREACH | CLEAN | INVALID | breach rate of scorable |
|---|---|---|---|---|
| `generated` | 76 | 753 | 56 | **9.2%** |
| `training_corpus` | 32 | 755 | 98 | **4.1%** |

Read marginally that is a 2.2x effect, and the obvious story writes itself: rephrasing a
known attack makes it land more often. **That story is false.**

## The paired comparison, which is the one to trust

Every `generated` attack carries `derived_from_attack_id`, so the variant can be compared
against **its own seed within the same run** rather than against the other arm in
aggregate.

**729 pairs where both the seed and its variant were scorable in the same run:**

| seed | variant | pairs |
|---|---|---|
| BREACH | BREACH | 60 |
| CLEAN | CLEAN | 669 |
| BREACH | CLEAN | **0** |
| CLEAN | BREACH | **0** |

**Zero discordant pairs.** The variant agreed with its seed every single time.

## What actually happened

The two arms do not contain the same attacks in the same proportions, and the
`training_corpus` arm carries nearly twice the exclusions (98 against 56) because the eight
unscoreable instances are concentrated there. A marginal comparison across two arms of
unlike composition produced an apparent 2.2x effect that the paired test shows is **zero**.

This is the vault's standing rule earning its keep: **separate populations, never pool.**
The pooled number was not noise. It was a real number computed over a denominator that did
not mean what it looked like.

## The finding that survives, and it is on-thesis

**The target's behaviour under attack is invariant to paraphrase.** Rewriting an attack's
surface text, by a different model, at a different temperature, changed the outcome in none
of 729 opportunities.

That is direct evidence for the design claim the whole project rests on. If the target
responded to surface form, a policy that bound to strings might have looked adequate and a
tripwire reading transcripts might have looked sufficient. Behaviour tracks the semantic
content of the attack, so the enforceable thing is **what the agent tried to do**, not what
was said to it. `constrain_arg` binding trace facts rather than strings is the same
argument from the other end.

## Caveats that travel with this

- **k=1.** No stability estimate. A pair agreeing once is not a pair that always agrees.
- **One target agent**, one corpus, one variant generator (`gemini-3.6-flash`, seed 1729).
- **`generated` does NOT mean discovered.** Every variant derives from a corpus seed by
  `derived_from_attack_id`. Nothing in this repository authors a novel attack, and this
  measurement must never be cited as evidence that it does.
- 729 pairs is a subset of the 885 in each arm: pairs where either side was INVALID are
  excluded, and those exclusions are not random.
