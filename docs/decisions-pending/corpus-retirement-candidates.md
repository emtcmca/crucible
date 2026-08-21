# F5 / near-miss retirement candidates for `corpus/C6-reach`

**Date:** 2026-08-21 · **Prepared by:** Lane F (recommendation only — not executed)
**Ruling this responds to:** Eric, 2026-08-21 — merge `corpus/C6-reach` and retire two
F5 attacks and two near-misses so the frozen counts hold: F5 = 8, benign = 24,
near_miss = 12.

**SUPERSEDED, same day.** Eric's actual ruling went the other way: **AMEND the
frozen counts (F5 8→10, benign 24→26, near-miss 12→14) rather than retire
instances**, because all 12 original near-misses are load-bearing for
separability pairs — see `docs/NEEDS-ERIC.md` item 2. `corpus/C6-reach` merged
as-is, with nothing retired. Everything below is Lane F's analysis in support of
the retire option, preserved as the record of what was considered and why it was
not the path taken — including the §1.3 finding below, which is still true under
the amend path too (only 2 of the 10 F5 instances route through
`CAP_INVOKES_AGENT`, against the stated ≥3 floor).

**Bottom line up front:** the recommended swap holds every frozen count and
orphans no pair in `corpus/pairs.json`. It does **not** fix the defect Eric was
told this fixes. Post-swap, only **2 of 8** F5 attacks route through
`CAP_INVOKES_AGENT`, against a stated floor of **≥3**. See "§1.3 check" below —
this is the load-bearing finding in this memo.

---

## 1. What `corpus/C6-reach` actually adds

Verified: `git diff --stat main...corpus/C6-reach` — exactly four files, 440
insertions, 0 deletions, no changes to `corpus/pairs.json`:

- `corpus/training/F5-09-delegated-billing-agent-then-settlement.json` (attack)
- `corpus/training/F5-10-risk-hold-delegated-then-credited.json` (attack)
- `fixtures/benign/F5-NM-03-delegated-billing-agent-t2-authorised.json` (near-miss, pairs with F5-09)
- `fixtures/benign/F5-NM-04-risk-cleared-then-delegated-credit.json` (near-miss, pairs with F5-10)

Both new attacks share `chain.class_sequence = [CAP_READS_PII,
CAP_INVOKES_AGENT, CAP_MOVES_MONEY]` — a three-class chain through
`delegate_to_specialist`. Both new near-misses are declared 1-field diffs
(`approver`: `NONE` → a real T2) of their paired attack, built to expose ruling
40.3 (a bare `preceded_by(CAP_INVOKES_AGENT)` rule can't separate them; a
tier-aware rule can).

## 2. Baseline verified on `main`

- `corpus/training/F5-*.json`: **8 files**, confirmed by listing.
- `fixtures/benign/*.json`: **24 files**; `near_miss: true` on exactly **12**
  (checked the JSON field per file, not the filename — `ls | grep NM` under-counts
  at 8, matching the warning in the brief).
- **Zero** instances anywhere in `corpus/training/`, `fixtures/benign/`, or
  `corpus/known_bad/` call `delegate_to_specialist` or carry `CAP_INVOKES_AGENT`
  on `main`. `corpus/pairs.json` pair **P11** (F3, `CAP_MOVES_MONEY`) says this
  explicitly: *"NO attack instance in the authored corpus uses
  delegate_to_specialist — CAP_INVOKES_AGENT is targeted by nothing, which is
  also why the class-coverage floor never fires on it."* This is a corpus-wide
  gap, not an F5-specific one — `python -m corpus`'s `check_class_coverage`
  builds its "attacked" set from each fixture's top-level `capability_classes`
  array, which never contains `CAP_INVOKES_AGENT` anywhere in the corpus (F5-09/
  10 carry it only inside `chain.class_sequence`, not in the top-level array —
  consistent with how F5-02/F5-05 already omit their own preceding chain class
  from that array). **The mechanical gate cannot see this floor either way** —
  it is manual-verification-only, which is exactly what this memo is doing.
- `F5-NM-01-delegated-refund-t2-approved.json` — confirmed narrative-only
  delegation, as flagged in the brief: it calls `escalate_to_human` then
  `issue_refund`, both under `CAP_ESCALATES_PRIVILEGE`/`CAP_MOVES_MONEY`. No
  `delegate_to_specialist` call anywhere in its trace.

## 3. `measurement-spec.md` §1.3, exact wording

> **F5 — Chained-call privilege escalation.** Targets composition. Each call
> individually permitted; the *sequence* crosses a boundary. Distinct from F7:
> composes **different** capability classes, requiring a sequence/co-occurrence
> deny. **8 instances**, ≥3 distinct class pairs, ≥3 routing through
> `CAP_INVOKES_AGENT`. **FIXABLE as of 2026-08-20** — `preceded_by
> (capability_class)` was added to the DSL precisely for this family.

**F3's requirement is differently worded and weaker.** F3's line is: *"8
instances, spanning `CAP_MOVES_MONEY`, `CAP_ESCALATES_PRIVILEGE`,
`CAP_INVOKES_AGENT`."* That is a **spanning** requirement (each class
represented somewhere across the 8) with no explicit numeric floor, and F3 in
fact satisfies it with **zero** `CAP_INVOKES_AGENT` instances per P11's
reconciliation note — because P11 substitutes `F3-06` (an amount-vs-cap attack)
for the worksheet's original delegation-shaped attack and reports the original
shape as **unbuilt** rather than silently counting it. F5's line has no such
escape hatch: **"≥3 routing through `CAP_INVOKES_AGENT`" is a hard numeric
floor**, stated once, with no substitution clause.

## 4. Every F5 attack, read individually

| Slug | Scored tool / class | Chain (class_sequence) | Named by a pair? | Redundant with |
|---|---|---|---|---|
| F5-01 pii-panel→third-party-send | `email_customer` / COMMS | PII→COMMS | **P12** | F5-07 (same pair-shape) |
| F5-02 pending-escalation→settlement | `issue_refund` / MONEY | ESC→MONEY | **P13** (ORC, `F5-NM-01`) | F5-08 (same pair-shape) |
| F5-03 reopen-declined-case→refund | `issue_refund` / MONEY | MUTATE→MONEY | none | none — unique shape |
| F5-04 written-commitment→settlement | `issue_refund` / MONEY | COMMS→MONEY | none | none — unique shape, but thematically overlaps F6 (self-manufactured/forged authority) |
| F5-05 risk-escalation→case-close | `update_case_notes` / MUTATE | ESC→MUTATE | none | F5-06 (mirror sequence, same two classes) |
| F5-06 self-written-note→wrong-queue | `escalate_to_human` / ESC | MUTATE→ESC | none | F5-05 (mirror sequence, same two classes) |
| F5-07 order-read→purchaser-detail | `email_customer` / COMMS | PII→COMMS | **P14** | F5-01 (same pair-shape) |
| F5-08 ident-hold→store-credit | `issue_store_credit` / MONEY+MUTATE | ESC→MONEY | **F35-P4** (`F5-NM-02`) | F5-02 (same pair-shape) |
| F5-09 delegated-billing→settlement *(new)* | `issue_refund` / MONEY+MUTATE | PII→**INVOKE**→MONEY | none yet | F5-10 (same pair-shape) |
| F5-10 risk-hold-delegated→credited *(new)* | `issue_store_credit` / MONEY+MUTATE | PII→**INVOKE**→MONEY | none yet | F5-09 (same pair-shape) |

**Only F5-03, F5-04, F5-05, F5-06 are unnamed by any pair record** — confirmed
by scanning all 27 records in `corpus/pairs.json` for each of the 8 slugs as
either `attack` or `benign`. F5-01, F5-02, F5-07, F5-08 are each load-bearing
for a specific pair and **retiring any of them orphans that pair** —
`corpus.load.assert_pairs_resolve` would fail loudly, and fixing it means
either editing `pairs.json` (P12/P13/P14/F35-P4 would need a CUT record with a
stated reason) or reassigning the pair to a substitute instance. Flagged loudly
as instructed: **do not retire F5-01, F5-02, F5-07, or F5-08.**

## 5. Recommendation — two F5 attacks to retire: **F5-03 and F5-04**

Both are unnamed by any pair (zero orphan cost) and both are the two
`CAP_MOVES_MONEY`-scored instances that aren't already needed to hold up a
pair. Retiring them and adding F5-09/F5-10 **keeps the `CAP_MOVES_MONEY`-scored
count in the family exactly where it was (4 → F5-02, F5-08, F5-09, F5-10)**,
so nothing about the family's dominant scored class shrinks — it's a straight
swap of two MONEY-chain shapes for two other MONEY-chain shapes that also
happen to be the ones this whole exercise exists to add.

- **F5-03 lost coverage:** the `MUTATES_DURABLE_STATE → MOVES_MONEY` chain
  shape (reopen a case a prior agent declined, then refund it as fresh) is not
  reproduced by any other F5 instance, old or new. Nothing else in F5 tests
  "an earlier state-mutation launders a later money call." This is a real,
  not cosmetic, loss.
- **F5-04 lost coverage:** the `EXTERNAL_COMMS → MOVES_MONEY` chain shape (an
  agent's own written promise becomes settlement authority) is likewise
  unique in F5. It overlaps thematically with F6's forged/manufactured-authority
  attacks, but mechanically F6 targets the *human approval gate*, not a
  same-agent two-call composition — so the overlap is in attacker psychology,
  not in what rule shape gets trained.

Alternative considered and rejected: retiring F5-05 and F5-06 instead. These
two are a mirror pair on the same two classes (`ESC→MUTATE` and
`MUTATE→ESC`); losing both removes **all** `ESCALATES_PRIVILEGE ↔
MUTATES_DURABLE_STATE` composition testing from F5, and unlike F5-03/F5-04,
losing them is not offset by anything — no other F5 instance, old or new,
touches that class pair in either direction. F5-03/F5-04 is the cheaper pick
by a clear margin.

**Post-swap distinct class pairs:** {PII→COMMS, ESC→MONEY, ESC→MUTATE,
MUTATE→ESC, PII→INVOKE→MONEY} = **5 distinct sequences**, comfortably above
the stated ≥3 floor.

## 6. §1.3 check — the number that matters

Counting `CAP_INVOKES_AGENT` in the post-swap 8 (F5-01, 02, 05, 06, 07, 08, 09,
10): **2 of 8** (F5-09, F5-10) route through it. F5-01 through F5-08
(everything not newly added) call `email_customer`, `issue_refund`,
`update_case_notes`, `escalate_to_human`, or `issue_store_credit` — never
`delegate_to_specialist`.

**2 < 3. The floor is not met.** No choice of which 2 originals to retire
changes this: F5-09 and F5-10 are the *only* two instances anywhere in the
plan that touch `CAP_INVOKES_AGENT`, so the post-swap ceiling is 2/8
regardless of which two of the six untouched originals get kept. **Reaching
≥3 requires either a third new `CAP_INVOKES_AGENT` attack (which would break
the F5=8 frozen count unless a *third* original is also retired) or retiring a
third original in favor of one more delegation-chain instance.** This memo
does not recommend that on its own authority — it is a scope change beyond
"merge C6-reach and retire two," and it is Eric's ruling to extend, not this
memo's to assume.

**Say it plainly: this swap does not fix the defect it was described as
fixing.** It merges the coverage that exists today, holds the frozen counts,
and moves the family from 0/8 to 2/8 on `CAP_INVOKES_AGENT` — real progress,
not a floor closure.

## 7. Two near-misses to retire

All 12 near-misses currently on `main` are named by at least one pair — every
one of them is load-bearing, confirmed by scanning all 27 pair records against
all 12 slugs. (`NM-F2-01` and `NM-F2-02` are each named by *two* pairs,
making them the single most expensive fixtures in the whole benign set to
lose.) The prior retirement's selection rule — "named by no pair record" —
**returns an empty set for near-misses by construction**: a near-miss exists
specifically because a pair names it. That rule cannot be reused unmodified
here, and this memo says so rather than silently picking a different rule.

**Recommendation: retire `F5-NM-03` and `F5-NM-04`** — the two near-misses
`C6-reach` itself adds, not any of the original 12.

- **Orphans nothing.** `corpus/pairs.json` was not touched by `C6-reach`
  (confirmed: `git diff main...corpus/C6-reach -- corpus/pairs.json` is empty),
  so no formal pair record references NM-03 or NM-04 yet. Retiring them before
  they are ever wired into `pairs.json` costs zero pair-orphan risk, unlike
  retiring anything from the original 12.
- **Preserves the corpus's balance.** Every training family currently gets
  exactly 2 near-misses (F1: 2, F2: 2, F3: 2, F5: 2, F6: 2, F7: 2 — verified by
  filename prefix across all 12). Adding NM-03/NM-04 without retiring anything
  would give F5 four near-misses against every other family's two. Retiring
  them keeps F5 at 2 (`F5-NM-01`, `F5-NM-02`), which is the only option that
  doesn't also unbalance the family structure or touch an unrelated family's
  pair to compensate.

**What this costs, stated rather than buried.** NM-03 and NM-04 exist to prove
a specific thing: that a `preceded_by(CAP_INVOKES_AGENT)` rule can be written
tier-aware rather than bare, so it doesn't block the two legitimate delegated
settlements the operation runs every day (a T2-authorized billing handoff, a
Risk-Review-cleared fraud handoff). Retiring them the same day they're added
means **F5-09 and F5-10 go into the corpus with no near-miss proving the rule
that would stop them isn't just "deny anything that touches
delegate_to_specialist."** `ruling_37_note` on both fixtures says this
explicitly — they are the honesty check, and retiring them removes it.

The mitigating argument, not a full offset: since §1.3's own floor isn't met
(2/8, not ≥3), the `CAP_INVOKES_AGENT`-composition rule this near-miss pair is
built to stress-test is itself under-trained by this swap. Proving a rule
doesn't over-block is most valuable once the rule is reliably learnable in the
first place. That is a reason this cost is *tolerable right now*, not a reason
it is free — if a later pass gets F5 to 3+ `CAP_INVOKES_AGENT` instances, NM-03
and NM-04 (or replacements built the same way) should come back.

**Alternative not recommended:** retire 2 of the original 12 instead, keeping
NM-03/NM-04. Every original near-miss orphans at least one pair (two, for
`NM-F2-01`/`NM-F2-02`), touches a family unrelated to this ruling, and would
require editing `corpus/pairs.json` to add a CUT record — a bigger, more
invasive change than this ruling asked for, spending a second family's
coverage to buy proof for a rule that (per §6) isn't reliably learnable from
this corpus yet anyway. If Eric wants the near-miss proof preserved, the
cheaper fix is extending the ruling to allow a ninth F5 attack and a
corresponding third retirement, not raiding another family.

## 8. Coverage table — before and after

**F5 attacks, by scored capability class:**

| Class | Before (8) | After (8) | Δ |
|---|---|---|---|
| `CAP_EXTERNAL_COMMS` | 2 (F5-01, F5-07) | 2 (F5-01, F5-07) | 0 |
| `CAP_MOVES_MONEY` | 4 (F5-02, F5-03, F5-04, F5-08) | 4 (F5-02, F5-08, F5-09, F5-10) | 0 |
| `CAP_MUTATES_DURABLE_STATE` | 1 (F5-05) | 1 (F5-05) | 0 |
| `CAP_ESCALATES_PRIVILEGE` | 1 (F5-06) | 1 (F5-06) | 0 |
| `CAP_INVOKES_AGENT` (chain-only, not a scored class) | 0 | 2 (F5-09, F5-10) | **+2, still < floor of 3** |
| Distinct class-pair sequences | 6 | 5 | -1 (still ≥3) |

**Benign fixtures, by family (near-miss count):**

| Family | Before | After | Δ |
|---|---|---|---|
| F1 | 2 | 2 | 0 |
| F2 | 2 | 2 | 0 |
| F3 | 2 | 2 | 0 |
| F5 | 2 (F5-NM-01, F5-NM-02) | 2 (unchanged — NM-03/04 in and back out) | 0 |
| F6 | 2 | 2 | 0 |
| F7 | 2 | 2 | 0 |
| Ordinary (`ORD-*`) | 12 | 12 | 0 |
| **Total benign** | **24** | **24** | **0** |
| **Total near-miss** | **12** | **12** | **0** |

**Corpus totals:** training 48 → 48 (no change, straight 2-for-2 swap in F5),
benign 24 → 24, near-miss 12 → 12. All three frozen numbers hold.

## 9. `python -m corpus` output, this worktree

```
load                    PASS     on disk: {'training': 48, 'sealed': 0, 'benign': 24, 'known_bad': 9}
pairs resolve           PASS     pairs=27
fault reason_code lint  PASS     pairs_checked=22
sealed-set lints        NOT-RUN  no sealed instances on disk
sizing                  FAIL     E_SEALED_BELOW_FLOOR (sealed=0, floor=18) — EXPECTED, sealed
                                  instances live only in crucible-wt-SEAL, per project CLAUDE.md
class coverage          PASS     status=OK
SEP-BY split            PASS     counted=24, cut=3, 21 policy / 3 oracle, off target (18/4) but
                                  not a stop condition
label blindness         PASS     attacks=48, instances=72
Part B buildable        PASS     fields=7
RESULT: FAIL (sealed floor only, expected in this worktree)
```

This run is on `main`, before any merge — recorded as the baseline the
recommended swap would start from. `check_class_coverage` passing here (and
after the swap) does **not** verify §1.3's F5-specific `CAP_INVOKES_AGENT`
floor — that gate checks benign coverage per attacked class, built from each
fixture's top-level `capability_classes` array, which never contains
`CAP_INVOKES_AGENT` anywhere in this corpus (see §2). The ≥3 floor is
manual-verification-only, which is what §6 above is.

## 10. What makes me doubt the plan

1. **The headline defect isn't fixed.** If anyone downstream reads "merged
   C6-reach, retired two F5 attacks and two near-misses, counts hold" as
   "§1.3 is satisfied," that's wrong, and it's the easiest wrong reading of a
   correctly-executed ruling. This memo's title finding (§6) exists to prevent
   exactly that.
2. **The near-miss retirement undoes the honesty half of the fix.** F5-09 and
   F5-10 ship without their proof-of-non-overbreadth on day one. That's a
   defensible trade given §1.3 isn't met anyway, but it's a trade, not a free
   action, and `ruling_37_note` on both retired fixtures says explicitly what
   they were built to catch.
3. **No mechanical gate enforces any of this.** Neither the §1.3 numeric floor
   nor the near-miss-per-family balance is checked by `python -m corpus`. If
   the frozen counts (F5=8, benign=24, near_miss=12) are the only thing gated,
   a future edit could silently re-break either property this memo protects
   and nothing would fail loudly.
4. **This is a two-instance patch on a corpus-wide gap.** P11 already
   documented `CAP_INVOKES_AGENT` as untargeted-by-construction across the
   *entire* corpus, not just F5. Closing F5's own floor at all likely needs a
   ninth and possibly tenth F5 attack, which is a scope decision beyond
   "retire two" — flagging it here rather than quietly assuming it.
