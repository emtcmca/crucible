# The run report — a human-readable postmortem per run

**Eric, 2026-08-22, explicitly spitballing and explicitly after the runs are
dialled in.** Recorded now because the framing at the end is a product decision,
not a formatting one, and it would be lost.

**Not scheduled. No owner. Do not build before the loop reliably completes a run.**

---

## The framing that makes this a product decision

> *"Even if we cannot penetrate an agent, that should be seen as a good result.
> It's a very well built, constructed agent. And the report should reflect that.
> It shouldn't be viewed as a failure of crucible. It should be a feather in the
> cap of the developer who wrote the agent."*

**A zero-breach result is a PASS for the customer, and the report must say so in
those terms.** A red-team tool that frames "we found nothing" as its own failure
teaches its users to distrust a good outcome, and pushes the vendor toward
manufacturing findings.

## THE CONSTRAINT THAT MAKES THAT SAFE, and it is not optional

**A clean run and a broken run both produce zero breaches.** On 2026-08-22 three
runs produced zero: one reached the wrong API, one crashed on the oracle's own
frozen content, and one recorded 36 `TARGET_FAULT`s. A report that congratulated
the developer for any of those would be the worst failure this tool can have -
the one the customer cannot detect.

**So section one answers "WAS THIS A VALID TEST?", before anything about what
happened.** The machinery already exists and was built for exactly this
distinction: `scorable` vs `attempted`, `target_faults`, `invalid`, `excluded[]`
with named instance ids, `round_census.outcome`, `clause_coverage`
(`episodes_fired: 0` is a finding), attack distinctness, and
`execution_provenance` naming all seven components. **Nothing got through** and
**nothing was thrown** must never render the same way.

## Sections — Eric's list, plus four he asked me to add

Eric's: what was tested · how the attacks went · what orchestrated · what the
attacks actually were · what the Coroner found · what the Armorer patched · the
state of the agent after.

Added:

1. **Was this a valid test.** Above. First, always.
2. **What was NOT tested.** Which capability classes were never exercised, which
   invariants never fired, how distinct the attacks actually were. A report that
   omits its own coverage is overclaiming, and `CAP_INVOKES_AGENT` at 2 of 10
   with 0 benign fixtures is the standing example.
3. **What the developer should do next.** The actionable half. **Rejected patches
   are useful even when nothing was promoted** - "here is a fix that stops the
   attack and breaks four of your legitimate workflows" is a finding about the
   agent's design, not a failure of the loop.
4. **Reproducibility.** The six lock values and the run id, so a third party can
   re-derive rather than trust. That is the differentiator against every other
   red-team report, and it costs nothing because the bundle already carries them.

## Why this is cheap when it comes

**C6 already carries almost all of it** after the 2026-08-22 extension: attack
text, autopsies, patch proposals including rejected ones with their DSL, policy
rule text, clause coverage, execution provenance, the exclusion ledger, and the
labels. `crucible/replay/view.py` renders all of it at 17 integrity checks.

**The report is a second renderer over the same bundle, not new measurement.**
Same relationship the replay viewer has, aimed at a customer rather than a judge.

**The blocker is the producer**, not the report: the campaign still writes a shape
with zero key overlap with C6.
