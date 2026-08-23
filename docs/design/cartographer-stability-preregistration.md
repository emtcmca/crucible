# Pre-registration: does the Cartographer give a stable answer?

**Written 2026-08-23, BEFORE any of the 50 runs. Committed before the first call is made,
which is the only thing that makes it a pre-registration rather than a description.** Eric's
design; the decision rule below is fixed here so the outcome cannot be chosen after the fact.

**Nothing in this file may be edited once the runs begin.** If it has to change, both arms
restart and the change is recorded as a new revision with its reason.

---

## 1. Why this exists

On 2026-08-22 the Cartographer classified the ADK sample's `generate_qr_code` as
`CAP_MOVES_MONEY`. On 2026-08-23, after **one prompt change** (adding `INERT`), it classified
the same tool as `INERT`, **citing the identical docstring span both times.** The tool takes a
float `discount_value`. The second reading is wrong, and wrong in the **under-calling**
direction.

**We cannot currently tell what that was.** Sampling variance, prompt sensitivity, or a
systematic bias are three different diagnoses with three different fixes, and **n=1 across a
prompt change distinguishes none of them.**

The candidate fix — a structural check refusing `INERT` for a tool declaring a money-shaped
argument — would be **written immediately after watching it fail once, on a corpus of twelve.**
`docs/narrative/prepass-and-gemma.md` §4 already refuses that shape of reasoning by name. So
the fix waits for evidence, and this document says what evidence would justify it.

---

## 2. The two arms, and they answer different questions

| arm | design | question |
|---|---|---|
| **A** | **25 runs, same prompt, same seed** (`20260822`, the seed the 08-23 artifact used) | Is the serving stack deterministic? |
| **B** | **25 runs, same prompt, 25 distinct seeds** | Does the class assignment vary under sampling? |

**Arm B is the one that speaks to `generate_qr_code`.** Arm A cannot: the observed flip
happened across a prompt change, not across seeds.

**Arm B seeds are fixed here so they cannot be selected after the fact:**
`20260901` through `20260925` inclusive, in order, one per run.

**Neither arm's prompt may change. Not one word, not one whitespace character.** The prompt
bytes are hashed before arm A begins and the hash is asserted before every single call. If it
differs, the run aborts and both arms restart.

---

## 3. What is recorded, per run

Every run, no exceptions and no filtering:

- the full twelve-row class assignment
- the `proposal_set_digest`
- the citation for each row, and whether it is byte-identical to the previous run's
- the `confidence` value on every row
- HTTP status, `finish_reason`, and the full `usage` block
- whether the validator accepted or rejected each proposal, and any `E_*` code

**Runs are not discarded.** A failed call, a non-200, or a malformed response is a data point
and is reported with the others. **There is no "we re-ran that one."**

---

## 4. The decision rule, fixed before any data exists

**Primary measure:** the proportion of **arm B** runs in which `generate_qr_code` receives any
class other than `CAP_MOVES_MONEY`.

| result | ruling |
|---|---|
| **0 of 25** | **Do NOT build the contradiction check.** The 08-23 reading could not be reproduced under a fixed prompt, so the single observation is attributable to the prompt change and there is no measured basis for a structural rule. Report n=25, zero recurrence, and leave the check as declared future work. |
| **1 or more of 25** | **Build the contradiction check**, and report the observed rate beside it. |

**Why any recurrence at all is enough, stated now rather than argued later.** The severity is
asymmetric. An under-called money-mover is the dangerous direction — it is the shape that puts
an unpoliceable label on a tool that can move funds. A spurious refusal costs a rejected
proposal that a human can override in the ratification step that already exists. **A rule whose
false negatives are dangerous and whose false positives are cheap does not need a high bar.**

**Secondary measures, reported regardless of what the primary shows:**

1. **Every tool's class stability**, not only row 12. Reporting only the tool we already
   suspected is measuring the fixture, which is the trap this whole document exists to avoid.
2. **Arm A determinism.** If any of the 25 same-seed runs differ from each other, that is a
   finding in its own right — it would mean the `seed` parameter is accepted but not honoured —
   and it is reported whatever arm B shows.
3. **Whether `confidence` ever varies.** It has been `1.0` on every row of every run so far,
   including a row that was wrong. If it is 1.0 across all 50, that is a reportable fact about
   a field that carries no information.
4. **Whether `CAP_READS_PII` or `CAP_INVOKES_AGENT` ever appear.** Neither has, in two runs.

---

## 5. Stopping and integrity rules

- **All 50 runs execute.** No early stopping, including on a favourable result. A run stopped
  when the answer looked good is not a measurement.
- **No prompt edit, no model change, no parameter change** across the 50. Model id, host,
  location, temperature and `max_tokens` are fixed at the 08-23 artifact's values.
- **The analysis is written against this document's decision rule**, not against the numbers.
- **Cost cap: if measured spend exceeds $5.00, stop and report.** Two prior runs used ~4,800
  tokens each, so 50 runs is on the order of 240,000 tokens. Dollars are **`[UNVERIFIED]`** —
  Google publishes no Gemma MaaS price line and third-party aggregators disagree by 2x, so the
  spend is reported in **tokens**, which are measured, and in dollars only with the range and
  the disagreement stated.

---

## 5b. Sequencing, and the single signature. Eric's ruling, 2026-08-23.

**The 50 runs execute AFTER the live run, not in parallel with it.** They touch nothing the
loop touches, so parallel would be safe — but the live run is the measurement everything else
waits on, and adding 50 model calls to that window buys nothing.

**Ratification waits for the runs, and the sheet is signed ONCE, at the end.** A sheet signed
today would be superseded by a run the write-up would rather cite, and a stack of signed sheets
reads badly. Until then `docs/proof/cartographer-adk-ratification.md` stays UNSIGNED and the
claim *"nothing has entered a manifest"* stays true, which is the honest state and also the
useful one.

**The order:** live run → 50 diagnostic runs under this pre-registration → report the stability
figures → the ruling in §4 fires → **then** the ratifier amends and signs once, against the run
the write-up points at.

**Two things already known that the ratifier will still have to decide**, and neither is
changed by the runs:

- **Row 12 as it stands is wrong.** `generate_qr_code` proposed `INERT` while declaring a float
  discount value. A human catches it. That is the gate working and it is the finding, not a
  defect to be quietly repaired before signing.
- **Row 5 cannot be accepted as proposed.** `access_cart_information` came back `UNCLASSIFIED`,
  and `to_manifest_entries` does not resolve that — it yields the literal `("UNCLASSIFIED",)`,
  which `manifest/load.py` refuses by name. It fails closed and loudly, which is arguably
  correct: it forces a human to rule on a tool nobody could classify.

---

## 6. What this cannot answer

- **It measures reproducibility, not correctness.** Twenty-five runs agreeing on a wrong class
  measure a stable error. The ground truth for these twelve tools is a human reading, n=1, one
  rater, and it is not a labelled set.
- **n=25 separates "never" from "often". It cannot separate 4% from 12%.** The decision rule
  above is built to need only the first distinction.
- **It is one foreign agent's twelve tools.** Nothing here generalises to a fleet, and the
  write-up must not say it does.
