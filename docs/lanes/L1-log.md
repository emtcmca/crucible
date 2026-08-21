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

---

## Work item 2 — service accounts, IAM, and the 403. Iterations: 3 failed.

| # | What failed | Why it mattered |
|---|---|---|
| 1 | `429 RESOURCE_EXHAUSTED` on the sixth service account — "Service accounts created per minute per project", `retryDelay: 60s` | Not a defect, but it would be invisible in a teardown-and-recreate at demo time. The tempting fix — drop back to seven accounts — would have silently reintroduced the four-name gap that had just been closed. Fixed with backoff in `infra/create-service-accounts.sh` |
| 2 | `verify_iam.py` reported **four FAILs against correct infrastructure** | It read the GCS **JSON-API** shape (`iamConfiguration.uniformBucketLevelAccess.enabled`); `gcloud storage buckets describe --format=json` emits a **different, snake_case** shape (`uniform_bucket_level_access`). `data-spec.md` §4.3's commands are written against the first. **The direction of that error was luck.** A predicate phrased the other way — flag only if the key says something bad — reads the same missing key and prints PASS on a bucket it never inspected. `MISSING` is now a third outcome that collapses into neither verdict |
| 3 | `prove-armorer-403.sh` scored **PASS — refused** twice for the wrong reason | The verdict matched on the word `permission`, and *"Permission `iam.serviceAccounts.getAccessToken` denied"* matched it. The probe had failed to **become** the Armorer at all, and reported the bucket boundary as proven. Two convincing green lines about a boundary that was never tested. **Caught only because the positive control failed in the same run and made the pattern visible** |

### The 403 has a positive control, and that is the whole design

A 403 alone proves nothing. A misspelled bucket returns 403; a deleted bucket
returns 403; a project the caller cannot see returns 403 — GCS refuses to
distinguish *"you may not"* from *"it is not there"*, because leaking existence
is itself a leak. So a recording of one red 403 is **compatible with the sealed
corpus sitting wide open at a slightly different path.**

`infra/prove-armorer-403.sh` reads the **same object, same path, same command**
as three identities. `crucible-sealed-eval` **must succeed**; `crucible-armorer`
and `crucible-red` **must be refused at the storage layer specifically**. If the
control fails, the script says every 403 in the run is uninformative rather than
reporting a boundary it did not demonstrate.

Result: **3/3**, `docs/proof/armorer-403.txt`.

### Stated limits, so the claim stays exactly true

- The operator holds `roles/owner` and can read everything. **You are the trust
  root and no control here defends against you** (`data-spec.md` §4.1 row 12).
- The canary object is **not sealed material**; the script wrote it.
- Impersonation needed `roles/iam.serviceAccountTokenCreator` granted to the
  operator **on those three service accounts**. That lets the operator act as
  them; it grants them nothing.
- **`roles/datastore.user` is held by the Armorer**, and Firestore has no
  per-collection IAM (`data-spec.md` A2). Blindness to the *fixtures* is
  therefore convention plus a code check, **never enforcement**. Blindness to the
  *sealed family* is real, because that data lives where the Armorer holds no
  role at all. The two must never be described in the same breath.

### Not bound, each for a stated reason

`run.invoker` — the Cloud Run services do not exist. `bigquery.*` — the datasets
do not exist. A binding against a non-existent principal or resource is the
failure that looks like success. The `data-spec.md` §4.3 layer-3 IAM **Deny**
policy is still open, pending assumption A3.

---

## Work item 3 — ledger, lineage chain, promotion gate. Iterations: 2 failed.

| # | What failed | Why it mattered |
|---|---|---|
| 1 | `sqlite3.OperationalError: near "'lineage chain exists to detect...'"` | SQLite has **no adjacent-string-literal concatenation**. Two quoted strings side by side are a syntax error, not one string |
| 2 | `sqlite3.OperationalError: near "||"` | The obvious fix for (1) is also wrong: **`RAISE(ABORT, ...)` takes a string LITERAL, not an expression**, so `\|\|` is rejected inside it. Hence the long single-line literals. **Wrapping them breaks the trigger, and a trigger that fails to create leaves the table silently mutable** — the failure mode is a store that looks append-only and is not |

### `data-spec.md` §2.3 is ambiguous about the chain's operand types, and it is pinned

`||` is concatenation, but §2.3 never says what type each operand is.
`policy_hash_full` is *defined* as `hex(SHA256(...))`, so text. `":"` is text.
`uint32_be(n)` is explicitly binary. `lineage_hash_{n-1}` is SHA-256's output,
which is raw bytes unless something hexes it. And the **stored** field is 16 hex
characters, a truncation of neither operand form without saying so.

**Three self-consistent readings exist and they produce different chains.** Left
unpinned, two implementations agree on every other test and disagree here — and
the disagreement surfaces as `lineage_ok: false` on a chain nobody tampered with.

Pinned in `crucible/ledger/lineage.py`, each operand in the form the spec
literally gives it, and frozen by vectors in `tests/test_ledger_gate.py`.
**Reported as a contract clarification; a lane does not edit `data-spec.md`.**

### The read-back is the exit criterion, and it was verified red first

`test_a_deliberately_corrupted_readback_is_caught` corrupts one digit of one
threshold. The payload still parses, still validates, still looks like a policy —
and enforces a **different rule** than the one promoted.

Swapping in the naive gate (`recomputed = policy_hash_full`, i.e. compare the
stored hash to itself) produced:

```
E       Failed: DID NOT RAISE <class 'crucible.gate.promote.PromotionError'>
FAILED tests/test_ledger_gate.py::test_a_deliberately_corrupted_readback_is_caught
FAILED tests/test_ledger_gate.py::test_a_readback_that_returns_the_wrong_object_is_caught
```

The real gate: 20/20. **That is what "recomputing from bytes is the point" buys,
and the naive version passes on a truncated write, a partial write, and a
corrupted read alike, because it compares a value to a copy of itself.**

### The census could not see finished work — and it is trivially gameable

`conformance-sweep.py` reported **0 built** while all four L1 checks existed. It
greps `tests/` for a check token, and the tests never mentioned the tokens. Same
shape as the W0 finding, inverted: **a search that reports a gap may simply be
unable to see the thing that fills it.**

Fixed by `tests/conformance_map.py`, which maps each token to a **resolvable
reference** — module plus callable — and `test_conformance_map.py`, which imports
each one and fails if the name does not exist.

**The weakness is stated rather than hidden:** writing `# L1-neg4` in any comment
still turns the census green. The map narrows that to "a check is reported built
and no code by that name exists." It cannot judge whether the referenced test is
any good, and nothing mechanical can. **Census now reads 4 built of 35.**

---

## Work item 4 — the manifest loader. **A contract gap, found by the loader.**

`derived_schema_hash` is one of the five hash-locks. **Part B could not be
hashed at all**, because `contracts/golden/C3b-derived_schema.valid.json`
carries `blindness_check.max_predictive_accuracy: 0.61`, and
`canonicalization.md` restriction 4 forbids floats in a hashed payload.

**The rule that resolves it already exists, twice, and nothing implemented it.**

- `canonicalization.md` restriction 4, frozen: *"Confidences and rates live
  **outside** the hashed payload."*
- `derived_schema.schema.json:79`, on the field itself: *"Reported outside the
  hashed payload (floats are forbidden inside one)."*

Both statements are true. Neither is machine-readable, and no code stripped the
field, so the artifact the run manifest is supposed to hash-lock was
un-hashable. **A frozen contract that says a thing twice in prose and nowhere in
a form a program can act on is not enforced** — it is the same shape as
`§8 rule 12`, one layer down.

**Handled, not routed around.** `HASH_EXCLUSIONS` in `crucible/manifest/load.py`
is an **enumerated** list, one entry, carrying its own justification. It is
tested in both directions:

- changing the excluded rate must **not** re-identify Part B;
- removing a `derived.*` field **must**, or the exclusion has quietly grown into
  "hash almost nothing";
- **any float not on the list is still refused**, and the error says *"this is a
  SECOND offending value, not the known one"* — so the next person removes it
  rather than appending to the exclusion list.

Part A has **no exclusions and needs none.** It freezes with the target; a
carve-out there would mean the target was frozen against something other than
what it is built from.

### For the coordinator

The exclusion is currently expressed in a `$comment` on one field, which no
program reads. **Proposal: a machine-readable marker in the schema** (e.g.
`x-hash-excluded: true`) so the loader derives the list from the contract
instead of restating it. Restating it in code is a second source of truth, and
that is the defect this repo has caught four times now. **Not done here — lanes
never edit `contracts/`.**
