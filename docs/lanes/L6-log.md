# L6 — EVIDENCE · lane log

**Branch:** `lane/L6-evidence` · **Worktree:** `C:\dev\crucible-wt-L6`
**Brief:** `docs/lanes/L6-evidence.md` (coordinator-written; this lane does not edit it).
**Wave:** W3 — the offline replay viewer.

One line per failed iteration, per `CONVENTIONS.md` §6. Status assertions carry the
date they were verified (§8 rule 12); an undated one is `[UNVERIFIED]`.

---

## What this lane is building, in one paragraph

The **judge-reproduction path**. The repository is public, so a stranger must be able
to clone it and replay a run's evidence bundle with **no credentials, no network, and
no GCP project**. If replay needs a credential, the reproduction claim is untestable
and the demo has to fall back to running a multi-minute live loop on camera. The
viewer is therefore the demo instrument, not a nicety.

The second thing it is: **a reader that refuses.** A bundle that renders beautifully
while missing the hash that makes it meaningful is worse than one that fails to open,
because the first looks like evidence.

---

## Iteration log

| # | Date | Work item | Result |
|---|---|---|---|
| 1 | 2026-08-20 | NC-1 (offline replay) and NC-2 (missing hash rejected) written before any implementation | **RED as designed** — 31 failed / 10 passed. `crucible/replay/` was not on disk, so every case needing the real implementation errored at import; the ten that passed are the fixture-integrity and strawman cases, which already discriminate. Captured at `docs/proof/L6-negative-checks-RED-2026-08-20.txt`. |
| 2 | 2026-08-20 | Reader, integrity checks, offline lint | NC-2 flips to 28 passed / 0 failed; NC-1's static half flips with it. Three NC-1 runtime cases stayed red pending `view.py`, named in the commit rather than left to be found. |
| 2a | 2026-08-20 | `test_every_mutation_name_is_real` reported `float_in_payload` as a no-op | **Real defect in the suite.** `412000.0 == 412000` in Python, so `mutated != original` could not see the single most important mutation in the list. Replaced with a type-aware comparison — the same reason `canonical.py` writes `type(node) is float` rather than `isinstance`. |
| 3 | 2026-08-20 | `view.py` + `__main__.py` | Two iterations. First run: six lines ran past the 96-column page width, worst at 122. Notes now wrap into a continuation column instead of being truncated, because the policy-chain row's caveat is the reason that row exists. Second: NC-1's three runtime cases went green. |
| 3a | 2026-08-20 | NC-1 failed under the scrubbed environment with `E_NO_VALIDATOR` | **Not a credential problem.** See F-5. |
| 4 | 2026-08-20 | README with the judge-path block, plus the claim-vocabulary gate over it | green. F-6 found while writing it. |
| 5 | 2026-08-20 | Cold-clone verification of the README, end to end | **Found a real defect.** The page-width check had been green on every run and was green for the wrong reason: the bundle path is a single unbreakable token and this worktree sits at a short path. From a clone in a deep temp directory the header ran to 130 columns. See F-8. Re-verified from a second fresh clone at `docs/proof/L6-cold-clone-2026-08-20.txt`. |

---

## Findings this lane is reporting up, not working around

### F-1 — C6's `policy_chain` cannot be independently recomputed from a bundle alone

`contracts/evidence_bundle.schema.json` → `policy_chain` carries a **16-character**
`policy_hash`. `crucible/ledger/lineage.py` computes

```
lineage_hash_n = SHA256(lineage_hash_{n-1} || ":" || policy_hash_full_n || ":" || uint32_be(n))
```

over the **64-character** `policy_hash_full`. The bundle carries no `policy_hash_full`
and no `hashed_payload`, so neither `policy_hash` nor `lineage_hash` can be recomputed
from the bundle's own bytes. The `$comment` on that property describes
`scripts/verify-chain.py`, which reads the **run ledger** (a SQLite file), not the
bundle.

This is stated rather than routed around. The viewer therefore labels every integrity
row with **how** it was established — `RECOMPUTED` from bytes, `CROSS_CHECKED` between
two independently written fields, or `PRESENT` — and the policy chain is reported as
`CROSS_CHECKED`, never as recomputed. Weakening the claim to fit the data would have
been the other option and it is a stop condition, not a repair (§8 rule 3).

**What a contract change would look like, if the coordinator wants one:** add
`policy_hash_full` (64 hex) to each `policy_chain` entry. That single field makes the
lineage chain recomputable offline, which is the difference between a judge verifying
the chain and a judge reading it. Lanes do not edit `contracts/`, so this is a report.

### F-2 — the C6 schema cannot enforce ruling 17, and the C6 known-bad fixture knows it

`contracts/golden/C6-evidence_bundle.KNOWN_BAD.json` lists four reasons it must fail.
Three are schema failures (23 traces against `minItems: 24`; a missing
`episode_frozen_context`; a missing `derived_schema_hash`). The fourth — `sep_by_split`
absent — is **not**, because `sep_by_split` is not in the schema's `required` list
while ruling 17 makes it a permanent reporting requirement.

So schema validation alone accepts a bundle that ruling 17 forbids. The viewer closes
that gap: `E_SEP_BY_MISSING` is a rejection, not a warning. `tests/test_bundle_reader.py`
pins it with a strawman that validates the schema and nothing else, and that strawman
must keep accepting the bad bundle or the check has stopped measuring.

### F-3 — the lane brief and the dispatch prompt disagree on owned paths

`docs/lanes/L6-evidence.md` §1 lists `docs/adr/` as an L6-owned path. The dispatch
prompt for this session lists `docs/adr/` as **coordinator only**. Conservative reading
taken as of 2026-08-20: **this lane wrote no ADR and touched nothing under `docs/adr/`.**
Reported rather than resolved, because a lane does not edit its own brief.


### F-4 — `crucible/replay/offline_lint.py` deliberately parallels `crucible/tripwire/import_lint.py`

Same technique — an AST walk rather than a grep, for the same two reasons that file
gives — but a different deny set and one extra check the model lint has no reason to
make: **any read of the process environment at all**, rather than a list of credential
variable names, because a rule with an exception list is a rule that acquires exceptions.

`import_lint.py` bakes its deny set and its roots in at module level, so it cannot be
pointed at a different question without editing it, and `crucible/tripwire/` belongs to
another lane. **Whether the two should become one parameterized lint is a coordinator
call.** Recorded here so the duplication is a decision rather than an accident.

### F-5 — "no credentials in the environment" and "no libraries" are different things, and on Windows they are easy to conflate

NC-1 runs the viewer in a child process with the environment stripped. Its first run
failed with `E_NO_VALIDATOR: No module named 'jsonschema'` — which is the viewer
correctly failing closed on a missing validator, and nothing to do with credentials.

Cause: on this machine `jsonschema` is installed under
`%APPDATA%\Roaming\Python\Python311\site-packages`, and CPython finds the per-user
site-packages directory **by reading `APPDATA`**. Scrubbing `APPDATA` broke library
resolution.

**The tempting repair was to put `APPDATA` back, and it was the wrong one.**
`%APPDATA%\gcloud\application_default_credentials.json` is the well-known path an ambient
Google credential lives at, so re-admitting `APPDATA` re-admits the exact thing the check
exists to exclude — and the check would still have passed, which is the dangerous part.
The child is now handed the parent's `sys.path` through `PYTHONPATH` instead: it gets its
libraries and it gets no environment, which is the property under test.

**Generalizable:** an environment scrub written to exclude credentials will also exclude
whatever else the platform happens to resolve through the environment, and on Windows
that includes the import path. A scrub that is quietly widened to fix an unrelated
breakage stops testing what its name says.

### F-6 — the repository has no LICENSE, verified 2026-08-20

No `LICENSE` file, and no license declared anywhere in the tree. Under default copyright
a stranger who clones this repository has **no granted right to use it**, which sits badly
against a public repository whose value proposition is "replay the evidence yourself."

The README says so plainly rather than asserting a license that is not there. A first
draft of that README ended with "Licensed under Apache-2.0" purely because that is what
the author's other repositories say — a fabricated status assertion, caught by checking
before committing rather than by anything mechanical. **Choosing a license is the
builder's call, not a lane's.**

### F-7 — one CONVENTIONS §7 approved claim was left out of the README on purpose

§7 lists as sayable: *"CRUCIBLE found a capability-boundary inconsistency in a published
Google ADK sample: `approve_discount` enforces a cap, `sync_ask_for_approval` does not."*
It is a strong line and it is not in the README, because **this lane has not verified it
against the sample's source** and §8 rule 1 says a claim without an asserted postcondition
is `UNVERIFIED`, not done. It is available for the coordinator to add, with the
`# MOCK API RESPONSE` qualifier §7 attaches to it.

### F-8 — the page-width check passed for the wrong reason for its whole life

Recorded separately from the iteration row because the shape recurs. The check asserted
"no rendered line exceeds 96 columns" and was green on every run. It was green because
the only long token on the page is the bundle's own path, and this worktree sits at
`C:\dev\crucible-wt-L6`. A clone into a deep temporary directory printed a 130-column
line on the first try.

**This is ruling 30's shape in a different field:** a check that reports intact because
it is looking at the part nobody changed. The property claimed is *legible at 1080p for
a stranger who cloned this repository*, and a stranger does not clone it to a path of
the author's choosing — so the author's path was never a valid sample of the input.

The repair that matters is not the hard-split in the wrapper. It is the second test
case, which renders a path longer than the page on purpose. **Fixing only the code would
have left the check exactly as unable to fail as it was**, and the next short-path
checkout would have restored the illusion.

Worth asking of every check in this build, and it is the question ruling 30 asks of
every hash-lock: *what input does this check never actually see?*
