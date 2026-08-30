# DECISION OWED — what the published failure record may name

**Raised by:** Codex adversarial review 9, finding P2.
**Status:** OPEN. Eric's to rule on.
**Deadline pressure:** this only fires *after* a terminal failure on the F4
drive, so it can be ruled on after the seal opens — but it must be ruled on
**before** the recovery procedure is run, and the repo locks 2026-08-31 17:00 PT.

---

## The two claims, and they contradict each other

**Claim A — the failure record must say what was read.**
`docs/proof/f4-unseal-preregistration-2026-08-25.md`, the ruling section:

> **Publish the failure record.** It must be audit-recoverable: what was read,
> when, by which identity, how far the run got, and where it stopped.

**Claim B — the sealed object names are withheld because they leak the family.**
`scripts/record-f4-transfer.py`, at the point the read set is supplied:

> the object names are withheld from the published manifest on purpose — the
> commitment's own `_withheld` says the instance names describe each attack's
> pattern, so publishing them would leak the family this seal exists to hold
> back.

`F4-MANIFEST.json` publishes `atk_` instance ids. The bucket holds objects named
for what they do. Those are different things on purpose.

## The mechanism that puts them in contact

`infra/holdout_touch.py` → `render_tally()` prints each matched audit entry's
**full resource name**, which for a sealed read includes the object name.

`scripts/probe-g7-g8.py` writes that text to
`docs/proof/L3-real-gate-G7-G8-<date>.txt` — a **tracked path in a public
repository**.

The recovery procedure in `docs/F4-DRIVE-RUNBOOK.md` tells the operator to run
exactly that probe, because it is the authoritative instrument for A3.11.

## It has not fired, and the reason is the reason it will

Verified 2026-08-30: no tracked file under `docs/` contains a sealed object
name. The two committed `L3-real-gate-*.txt` files are clean.

They are clean because **no sealed read has ever happened**, so
`result["reads"]` has always been empty. The leak fires the first time there is
something to leak — a recovery run after a terminal failure — which is the one
moment nobody will be proofreading a proof file.

This is the same shape as the 2026-08-21 incident, where a ratification document
named a sealed instrument verbatim and was pushed public. A public commit is
served by SHA forever.

## What has been done already, and what it deliberately does not decide

`probe-g7-g8.py` now redacts sealed object names **out of the file it writes**,
by default. Each distinct object becomes a stable `sha256-8:` digest.

- The record still carries **timestamp, principal, and one distinct token per
  object** — so "what was read, when, by which identity" survives, and the count
  of distinct objects survives.
- What it stops carrying is the slug, which is the part that describes the
  attack.
- `--reveal-sealed-names` writes them verbatim. It defaults to off.

**That is not the ruling. It is the default that makes the ruling deliberate
instead of accidental.** A script that published by default would decide this
question by omission, in the direction that cannot be undone.

## The two defensible readings

**(1) Publish the names in full.** The pre-registration says *what was read*,
and a digest is arguably a paraphrase. Once the attempt is terminal INVALID the
seal has been spent, the measurement is dead, and the confidentiality it bought
has already been consumed. Full disclosure is the maximally auditable answer and
this project's stated bias is to publish the worst thing unprompted.

*Costs:* the F4 family's attack patterns become public permanently, so the
family can never be reused as a holdout, and anyone building against CRUCIBLE
afterwards has the answer key. The withholding rationale in the commitment was
not scoped to "until the run ends" — it was about what the names reveal.

**(2) Publish digests, withhold slugs.** Everything the pre-registration
enumerates — what, when, by whom, how far, where it stopped — is preserved,
including how many distinct objects were touched and which line is which. An
auditor with bucket access can match every line to an object; an auditor without
it could not verify a name anyway.

*Costs:* a reader must take on trust that the digest corresponds to a real
object, and it is a narrower disclosure than the plain words "what was read"
suggest. It is also an interpretation made *after* the situation arose, which is
the thing pre-registration exists to prevent — that objection is real and should
be recorded in the ruling rather than argued away.

## Recommendation

**(2), with the interpretation stated out loud in the published record**, in
these terms or close to them:

> The sealed object names are withheld and shown as stable digests. This is a
> narrower reading of "what was read" than the pre-registration's plain words,
> adopted after the fact, and it is recorded here rather than presented as what
> the pre-registration required. The names describe the attack patterns and the
> withholding rationale was never scoped to the life of one run.

Ruling (2) silently, or presenting it as what the pre-registration meant all
along, would be the widened-claim defect this project keeps catching in itself.

## If you rule (1)

Pass `--reveal-sealed-names`, and say in the same breath that the F4 family is
now burned as a holdout. Do not leave that implication for a reader to work out.
