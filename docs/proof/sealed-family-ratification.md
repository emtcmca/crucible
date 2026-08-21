# Sealed family — human ratification

**Date:** 2026-08-20 · **Ratified by:** Eric Tetzlaff · **Set:** F4, destination
smuggling, 24 instances · **Fingerprint at ratification:** `2cde0250de00e692`

## What was reviewed, and how

**All 24 instances, in full customer language.** Not the metadata, not a summary —
the actual conversation text of every instance, read in one pass, followed by a
ruling.

That distinction is the whole reason this file exists. An earlier draft of the
review presented the *mechanics* — amounts, reason codes, instrument of record
against smuggled instrument — and the ratifier's response was that he could not
tell what he was being asked to judge. **He was right, and the fault was in the
presentation.** A table of instrument identifiers cannot answer the only question
a human is better placed to answer than a model:

> Would a competent support agent, reading this conversation, believe the
> customer?

That question sets the corpus's **potency**. A pretext no agent would fall for
makes the attack too easy, inflates the v0 breach rate, and flatters the entire
before-and-after curve. *"Zero breaches at vFinal"* means something only if the
attacks were hard when they were written.

## The ruling

**All 24 accepted. None cut.** The set stands at the preferred count rather than
the 18 floor.

Ratifier's words: *"I dont see a problem with any of these. They seem reasonable
and not atypical."*

The reviewer's standing is the point. He ran a property-management company for
years and handled real refund and chargeback abuse directly, so *"not atypical"*
is a judgment from someone who has read the genuine article, not an assessment of
plausibility from someone reasoning about it.

## Four specific concerns were raised and cleared

Recorded so the review is checkable later rather than merely asserted. These were
put to the ratifier by name, and cleared:

| Instance | The concern raised |
|---|---|
| instance **16** | a digit-level change on the same account. A human might reasonably conclude the customer is telling the truth, which would make it **mislabelled** — and a mislabelled instance in a sealed set is worse than a missing one |
| instance **18** | same shape, same concern |
| instance **21** | Cites an external authority as ordering the redirect. Possibly **too strong** — a well-trained agent should refuse instantly, which would make it a weak instance |
| instance **23** | Supplies the destination verbally. Same concern |

Also raised: whether 24 consecutive customers each wanting the money somewhere
other than where it came from reads wrong **as a set**, independent of whether
each pretext holds individually. Cleared.

### The ratifier's mechanism for 16, 18 and 23 — and it inverts the concern

The concern assumed a digit-level change is most likely a genuine correction, so
those instances risked being mislabelled. **The ratifier supplied the attack that
makes them real, and it is a better reading than the one that raised the doubt:**

> *"16 and 18 could be attacks; malicious swapping of a card number, a stolen
> card number, to pay for a previously legitimate order. I could see that
> happening. CC numbers are read over the phone all the time to support/CS
> agents."*

That is **refund laundering.** The order is genuine, the fault is genuine, the
customer may even be the real account holder — and the refund is steered onto an
instrument the attacker controls. A near-miss digit pattern is not a weaker
version of the smuggle; it is the version that survives an agent glancing at the
number, because a one-digit variant of the instrument on the order reads as a
typo rather than as a different account.

> **REDACTED 2026-08-21, and the redaction is late.** This sentence originally
> named the actual instrument identifiers from a sealed instance. That is a leak
> of exactly the kind the seal exists to prevent, it was written by the
> coordinator while explaining why the instance is strong, and **it was pushed to
> the public repo before `scripts/seal-leak-check.py` existed to catch it.**
> Redacting the working copy does not recall what was already published. See
> "Known leak" below.

**Consequence for how these are described:** 16, 18 and 23 move from "the ones I
was least sure about" to among the **strongest** in the set. They are the
instances where the destination check earns its keep, because they are precisely
the ones a human reviewer would wave through.

instance **23** is cleared on the same ground and for a reason worth keeping:
supplying a card number verbally to an agent is **ordinary**, not suspicious. The
instance is strong *because* nothing about the interaction looks wrong.

**This rationale is recorded here and NOT written into the instances.** The set is
fingerprint-locked at `2cde0250de00e692` and ratified against that value; editing
an instance to add a justification would break both the seal and the record that
cites it. The reasoning belongs beside the ratification, not inside the artifact
it ratifies.

## What this does and does not license

**Licensed:** *"Every instance in the sealed family was read in full by the author
before the set was frozen."* That is a stronger statement than the one ruling 40
permits for the benign suite, where the ordinary fixtures are reviewed in summary
and the claim narrows accordingly.

**Not licensed:** any suggestion that an independent party reviewed them. One
person read them, and that person is the builder. **A clean review by the author
is evidence about the author's attention, not an independent check** — the same
reasoning that refuses to treat a zero-edit send as a passing grade.

**Also worth stating plainly:** finding no problems is a weaker signal than
finding some. The concerns above were raised and cleared rather than discovered,
so what this records is that four specific hazards were *considered*, not that the
set survived an adversarial pass.

## Consequence

The set is **final at 24**. The public commitment
(`scripts/seal-commitment.py --write`) may now be published, and must be
published **before the first patch is written** — that is the claim's binding
constraint, not a calendar date.


## Known leak — one instance, permanent

On 2026-08-21 the ratification text above named the order instrument and the
smuggled instrument of **one** sealed instance verbatim, and that text was
committed and pushed to a public repository. The same pair appeared in
`scripts/seal-leak-check.py`'s docstring as an illustrative example.

**Both are redacted going forward and neither redaction undoes the publication.**
A public commit is permanent, cloneable, and served by SHA long after a rewrite.

**What it costs, precisely:** a reader who fetched those commits can reconstruct
the destination pair of one instance of twenty-four. It does not touch the
commitment hash, which is over content that has not changed. It does not affect
the other twenty-three. It does not alter whether the family was sealed before
the first patch.

**What it does affect:** that one instance is no longer blind to a reader who
looked. If its result is ever singled out, the leak must be stated in the same
breath.

**What was NOT done, deliberately:** the instance was not replaced. The set is
fingerprint-locked at `2cde0250de00e692` and the commitment is published;
swapping an instance to tidy a leak would break a public commitment to hide a
disclosed mistake, which is a far worse trade than carrying the disclosure.

**How it was found:** by the leak checker written *after* the fact, on its first
real run, against the file its own author had written. That is the check working,
and it is also the argument for writing it before publishing rather than after.
