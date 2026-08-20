# L1 FOUNDATION — lane log

One line per failed iteration (`CONVENTIONS.md` §6), plus findings that belong to
the coordinator rather than to this lane. A lane never edits `contracts/` or
`CONVENTIONS.md`; it reports and keeps working.

---

## Work item 1 — the canonicalizer (C7). Iterations: 1 failed, then green.

| # | What failed | Why it mattered |
|---|---|---|
| 1 | `test_strawman_fails_the_vector_it_is_supposed_to_fail[V09]` — the strawman **passed** V09 | The suite's own meta-check caught a **false claim written by this lane**. `tests/strawman_canon.py` declared that `json.dumps(sort_keys=True)` would fail V09 (string escaping). It does not: Python's encoder already emits the shortest escape form. V09 was therefore discriminating against nothing any test could demonstrate — a vector asserting a property with no evidence it can detect its own violation, which is the exact object §8 rule 2 exists to eliminate |

**Fix taken, and the one rejected.** The comfortable fix was to demote V09 to
"unproven" and move on. Rejected: that converts a live check into a decorative
one and leaves the tree looking greener than it is. Instead a **second strawman**
was added — `long_escape`, which is correct everywhere the first is wrong and
wrong in exactly one branch: it escapes control characters as `\u00xx` instead of
the short forms RFC 8785 §3.2.2.2 mandates. That is not a contrived error. It is
what almost every hand-rolled JSON string writer does, and it produces valid JSON
that parses to the identical value and hashes differently.

The suite now also carries `test_every_vector_is_killed_by_at_least_one_strawman`,
which forces the six vectors no strawman fails to be **declared** in
`UNPROVEN_BY_DESIGN` rather than discovered later. All six are cases Python's own
`json` module happens to get right — notably **V06**, where arbitrary-precision
ints mean a Python strawman *cannot* reproduce the 2^53 float trap at all. A
JavaScript implementation fails V06 immediately. That asymmetry is worth keeping
visible: **the vector is sound, our ability to prove it here is not.**

---

## Open for the coordinator — three items. Not worked around.

### 1. ~~Two refusals have no contract vector~~ — **RULED 2026-08-20. Both accepted as V16 and V17.**

The coordinator added them at `d59c187`. `canonicalization.md` §3 says
"**≥12** fixtures", so the table is a minimum and the additions are compatible
with the frozen contract — no edit to `canonicalization.md`, no `SPINE_VERSION`
bump, no contract hash change. The fifteen existing vectors regenerated to
byte-identical files, verified by hash on read-back.

Picking the ruling up broke two of this lane's guards, **which is the guards
working**: `test_fixture_set_is_intact` refused the new count and
`test_every_vector_is_killed_by_at_least_one_strawman` refused to let V16/V17
enter the tree without a declared discriminator. Neither could have been added
silently. Original report follows.



`crucible/canon/canonical.py` refuses two more things than
`contracts/canonicalization.md` §3 enumerates. Both are pinned by tests in
`tests/test_canonicalization.py` so they cannot drift while the question is open,
but neither has a golden vector, and a refusal with no fixture is a behaviour
nobody outside this lane has agreed to.

| Code | Trigger | Why it is a refusal and not a repair |
|---|---|---|
| `E_SURROGATE` | an unpaired surrogate, reachable from a `\uD800`-style escape in a source document | Not representable in UTF-8. Without the explicit refusal it surfaces later as a `UnicodeEncodeError` **naming the wrong cause**, several layers from where it was introduced |
| `E_TOO_DEEP` | nesting beyond 64 levels | A model authors payloads that reach this function. A `RecursionError` inside a hashing path reads as a harness crash — `TARGET_FAULT`-shaped noise in a run that is supposed to be measuring something else |

**Proposal:** add them as V16 and V17. Coordinator's call; this lane will not
touch `contracts/`.

### 2. `.gitattributes` now pins the vector bytes

Added in the coordinator commit that created the vectors, recorded here because
it is load-bearing and invisible: `contracts/golden/canonicalization/** -text`.
V10 asserts a UTF-8 BOM and V02/V03 assert exact UTF-8 sequences. An end-of-line
conversion on a fresh clone would make the judge's hashes disagree with ours and
**it would read as a canonicalizer bug rather than as a checkout artifact.**

### 3. `E_FLOAT` is raised from two places and that is deliberate

`_parse` catches floats at the parser hook; `_emit` catches them again on the
in-memory path, which has no parser to hook. Deleting either one leaves a live
hole: `canonicalize_bytes` is not the only entry point, and `rule_id()` reaches
`_emit` directly with a dict that was never JSON text.

**Honest caveat on the eight naive-strawman entries.** For a NEGATIVE vector the
bar is low: any output at all already diverges from a required refusal. That is
real discrimination -- "produces bytes where the contract says refuse" is exactly
the bug -- but it is weaker evidence than a positive vector, where the strawman
must produce different *correct-looking* bytes. Recorded so nobody later reads
eight entries as eight equally strong results.
