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
| 1 | 2026-08-20 | NC-1 (offline replay) and NC-2 (missing hash rejected) written before any implementation | **RED as designed** — as of 2026-08-20 the package `crucible/replay/` is not on disk, so every case needing the real implementation errors at import. The strawman half of both files already discriminates. |

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

