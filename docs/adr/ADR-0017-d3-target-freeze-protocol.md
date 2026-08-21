# ADR-0017 — the D3 target freeze protocol

**Status:** Accepted · **Date:** backfilled 2026-08-21, decision dated 2026-08-20
(`CONVENTIONS.md` ruling 30). **The protocol executes Sat 2026-08-22.**
**Referenced at:** `docs/execution-spec.md:795` (risk register row 5, which assigns this to
**ADR-002** — see *Note on numbering*), `:236-292` (Day 3), `:270-272`, `:277`, `:285`, `:657`,
`:97`, `:828`, `docs/measurement-spec.md:898-901` (the five hash-locks), `:978-982` (guard 4),
`:1211` (the D3 row) *(measurement-spec is being edited in a parallel session; anchor on the
guard text, not the line)*, `docs/CONVENTIONS.md:45-49` (SPINE_VERSION 4 note), `:1292-1322`
(ruling 30), `docs/data-spec.md:855-890` (§2.1-2.2, canonicalization),
`target/refund_agent/freeze.py`, `target/refund_agent/manifest.py`, `crucible/manifest/load.py`,
`crucible/canon/hashing.py` (`hash_full`), `crucible/canon/canonical.py`, `tests/test_target_freeze.py`, `scripts/freeze-d2-gate-rule.py`
(the sibling protocol, and the one this one is measured against)

## Context

The builder authored the target. Without a freeze, the cheapest path to a falling attack-success
curve is quietly making the refund agent more cautious, and **it would be invisible in every
metric** (`measurement-spec.md:978-982`, guard 4). The target freeze is the primary structural
defence against self-grading, and it is one of the five hash-locks the whole measurement rests on
(`measurement-spec.md:898-901`).

It is dated because it must be. `execution-spec.md:657` puts the target, `manifest_hash`, and the
Objective Set on the same Saturday, before a single corpus instance is written, so that *the
definition of breach was fixed before any breach was measured.* The cost is stated rather than
discovered: **anything the agent does on camera must be true by Sat 08-22**
(`execution-spec.md:97`, `:828`).

Risk register row 5 (`execution-spec.md:795`) names the failure this document prevents — *"you
catch yourself on Day 8 thinking I'll just tweak the escalation message"* — and requires that the
rule be **external to your Day-10 self**. It was never written. This is it, on the day before it
runs.

**And the freeze already failed once, silently.** Ruling 30 (`CONVENTIONS.md:1292-1322`):
`target_agent_hash` covered the capability manifest, the target descriptor, the policy hash, and
`tool_signatures()` — tool **names** plus **parameter names**. It covered **not one line of tool
body**. Proven rather than argued: a statement inserted into a tool body left the hash at
`edade2064be9b50f`, unchanged. A target could be frozen at D3, rewritten to approve everything,
and every result produced afterwards would still cite the same target hash. *A check that reports
intact because it is looking at the part nobody changed* is the exact shape this project exists to
demonstrate.

## Decision

### What is hashed

`target/refund_agent/freeze.py::freeze_payload()` builds exactly one object, with five members and
nothing else:

| Member | Source | Why it is in |
|---|---|---|
| `capability_manifest` | `manifest.build_manifest()`, Part A, **built from `tools.TOOL_FUNCTIONS`, never hand-maintained** | The tool surface and its capability classes. The plugin cannot make a decision without it |
| `target_descriptor` | `agent.target_descriptor()` — `target_id`, `agent_name`, `model`, `thinking_level`, `endpoint`, `temperature_x100`, `tool_binding`, `adk_version` | **The tier flatters or deflates every number downstream**, so it must be recoverable from the frozen record rather than from memory. `temperature_x100` is an integer on purpose |
| `policy_sha256` | SHA-256 of `refund_policy.md`, **LF-normalized**, BOM refused | The system prompt **is** the attack surface. Without it the target's instructions could move between the v0 arm and the vFinal arm |
| `tool_signatures` | name + **ordered** parameter names per tool; tools sorted by name, parameters in **source order** | A parameter renamed after the freeze breaks every arg-path rule **silently** — the rule keeps validating and stops firing |
| `runtime_source` | SHA-256 of each of the **nine** `RUNTIME_MODULES`' bytes, LF-normalized, BOM refused | Ruling 30's fix. Without it the lock locks names, not behaviour |

`RUNTIME_MODULES` is `__init__.py`, `agent.py`, `capabilities.py`, `episode.py`, `freeze.py`,
`manifest.py`, `simulated_system_of_record.py`, `system_of_record.py`, `tools.py`.

### By what algorithm, in what order

- Arrays are **sorted at construction, never at hash time** (`data-spec.md` §2.2 restriction 6):
  tools sorted by name in `tool_signatures()`, `capability_classes` sorted in `build_manifest()`,
  `runtime_source` keys emitted in sorted order. Each tool's own parameter list keeps **source
  order**, because order is meaning there.
- The payload is canonicalized per **RFC 8785 (JCS)** with the project's restrictions
  (`data-spec.md` §2.2): UTF-8, no BOM, NFC, key order by UTF-16 code unit, no whitespace,
  **integers only — floats forbidden**, no nulls, lowercase booleans. Key order at hash time is
  therefore the canonicalizer's, not the dict's.
- `hash_full()` is SHA-256 over those canonical bytes; the recorded values are the **first 16 hex
  characters**.
- `compute()` emits `target_id`, `manifest_hash` (`hash_full(capability_manifest)[:16]`),
  `target_agent_hash` (`hash_full(whole payload)[:16]`), `policy_sha256` (full 64 hex), and
  `canonical_bytes`.

**Two hashes, two surfaces, and that separation is deliberate and tested.** `manifest_hash` is
Part A — the tool **surface** — and it **does not move on a tool-body change**
(`tests/test_target_freeze.py::test_manifest_hash_does_NOT_move_on_a_body_change`). If it moved on
every body edit the two hashes would carry the same information and one of them would be
pointless.

**The module list is asserted in BOTH directions, and that is the half that gets skipped.** A
module named in `RUNTIME_MODULES` and absent from disk raises, so **a rename cannot silently drop
a file out of the lock** — which is exactly what a rename had just done. A `.py` on disk in the
package and absent from `RUNTIME_MODULES` **also** raises, so a new module cannot be added outside
the lock. One direction alone gives a lock that shrinks quietly. Both directions have their own
test.

### What is deliberately excluded, and why

1. **Timestamps, `run_id`, and filesystem paths.** A payload carrying any of them hashes
   differently on two machines, and the recompute-from-a-clean-checkout exit criterion
   (`execution-spec.md:285`) is the whole point. Asserted by
   `test_the_payload_carries_no_wall_clock_and_no_run_id`.
2. **The fake ledger's contents and the three demo transcripts** (`target/refund_agent/demo/*.json`).
   The ledger is a stand-in for L1's component and is not the target's behaviour under test; the
   demos are a rehearsal script. Hashing either would move the target freeze whenever a demo line
   was reworded. *(Note that `simulated_system_of_record.py` — the fake's **code**, including its
   seeded scenarios — **is** inside `runtime_source`. What is excluded is the JSON under `demo/`.)*
3. **Floats, everywhere.** `data-spec.md` §2.2 restriction 4 forbids them inside a hashed payload,
   which is why the model temperature is carried as `temperature_x100`.
4. **Part B, `derived_schema.json`.** It freezes at **D5** with the corpus, gated on the
   label-blindness check, under its own `derived_schema_hash` (`crucible/manifest/load.py`). One
   hash over both halves would mean the D5 corpus freeze **retroactively changed the identity of
   the thing the D3 target was frozen against**, and every D3-D5 result would cite a manifest hash
   that no longer exists.
5. **Inside Part B only, one enumerated field:** `blindness_check.max_predictive_accuracy`, in
   `crucible/manifest/load.py::HASH_EXCLUSIONS`. It is a rate, and restriction 4 puts rates
   outside the hashed payload. The reason is stated on the entry: *two runs whose fields are
   identical and whose measured accuracy differs are the **same schema**, so including it would
   make the identity of Part B depend on a measurement rather than on a definition.* **The list is
   enumerated and each entry names why; it must never become "strip whatever fails to
   canonicalize."** That is weakening a gate, which `CONVENTIONS.md` §8 rule 3 makes a stop
   condition rather than a repair. Any float **not** on the list is still refused, and there is a
   test for exactly that. **`HASH_EXCLUSIONS` has no entry for Part A, so nothing is stripped from
   the D3 freeze.**

### The LF normalization is not cosmetic

`policy_sha256` and `runtime_source` both hash **after** `\r\n` → `\n`. Verified 2026-08-20: this
repository runs `core.autocrlf=true` and `.gitattributes` does not cover `target/**`, so the
working copy holds LF while a fresh Windows clone gets CRLF. The raw-bytes policy hash differs —
`ae3cb4c93f86ad8a…` here against `2060b712f63a6e6c…` from a CRLF checkout. Without the
normalization the freeze looks correct on the machine that made it and **fails for the judge who
clones it**, which is the worst available failure. A BOM is **refused rather than stripped**: a
stripped BOM makes the file that arrives differ from the file that was hashed.

### Who may run it

**The project owner, and only the owner, runs `--write`.** `freeze.py`'s own docstring says so:
*"This lane does not run `--write`."* It is a dated, irreversible commitment about the thing under
test, so it is the owner's call and not a lane's. Any party may run the dry run and `--check`;
both are read-only.

### The protocol, as an executable sequence

Run from the repository root, on Sat 2026-08-22, **before any corpus instance is written**.

```
 0.  git status --porcelain            # MUST be empty for target/ and contracts/.
                                       # freeze.py does NOT check this. See below.
 1.  python -m pytest tests/test_target_freeze.py tests/test_manifest.py \
             tests/test_manifest_completeness.py tests/test_target_tools.py -q
 2.  python -m target.refund_agent.freeze          # dry run. Record all four values.
 3.  git add target/refund_agent && git commit     # the target as frozen, committed FIRST
 4.  python -m target.refund_agent.freeze --write  # OWNER ONLY. Writes FROZEN.json,
                                                   # re-reads it, returns 2 if it did not
                                                   # read back as written.
 5.  python -m target.refund_agent.freeze --check  # MUST print "MATCHES the committed
                                                   # freeze" and exit 0.
 6.  git clone . /tmp/crucible-cold && cd /tmp/crucible-cold \
       && python -m target.refund_agent.freeze --check
                                       # THE REAL EXIT CRITERION. This is the CRLF trap.
 7.  git add target/refund_agent/FROZEN.json && git commit && git tag <freeze tag>
 8.  Copy target_agent_hash and manifest_hash into the RunManifest before round 1.
```

**Postcondition, asserted from the artifact and never from an exit code:** `FROZEN.json` exists,
carries the four recorded values, reads back byte-identical to what was written, and **step 6
reproduces `target_agent_hash` from a clean clone.** `execution-spec.md:285`: *if it doesn't, your
canonicalizer is wrong and Day 1 lied to you.*

**Values recorded from the dry run on 2026-08-21** (the day before the freeze — historical, and
**not** the value to be frozen; the target may still legitimately move today):

```
target_id          tgt_crucible_refund_v1
manifest_hash      d2e9f5f435b5acfe
target_agent_hash  e53c73daa1dadefb
policy_sha256      ae3cb4c93f86ad8a6b8fe2a7b2e5c861988cee9e00af928a32696baf18092c75
canonical bytes    4543
```

`manifest_hash` was cross-checked the same day against the **other** implementation —
`crucible.manifest.load.load_part_a()` reading the committed `capability_manifest.json` — and both
paths return `d2e9f5f435b5acfe`, with the committed file equal to `build_manifest()`.

### What breaks the freeze afterwards

Any edit to one of the nine runtime modules, to `refund_policy.md`, to a tool name or parameter
name, to `TOOL_SPECS`, or to the target descriptor. `--check` then exits 2 with **MISMATCH — the
target moved after the freeze.**

The consequence is fixed in advance and is not negotiable at 11pm: **any change after the freeze
invalidates all prior rounds and requires a full re-baseline** (`measurement-spec.md:979-980`).
`execution-spec.md:795`: after the hash, *the only legitimate change is one that breaks the hash
and re-scopes every prior result — a decision, not a tweak.* A manifest change additionally flags
every learned rule `needs_revalidation` (`execution-spec.md:272`).

## The alternative that was rejected, and why

**Freezing the target's interface only — the manifest, the descriptor, the policy, and the tool
signatures.** It is not a hypothetical: **it is what was implemented, and it was measured to lock
nothing.** Ruling 30 inserted a statement into a tool body and `target_agent_hash` did not move.

Rejected because the freeze exists so a number can name the thing it was measured against, and a
lock on names is not that. The interface-only payload permits precisely the manipulation guard 4
is aimed at: freeze at D3, quietly make the worker more cautious on D6, and cite the same target
hash on every result. It would have looked exactly like a working control.

A second alternative — **`.gitattributes` instead of in-code LF normalization** — was rejected in
`freeze.py`'s own docstring on two grounds: the repo already hashes `contracts/**` after LF
normalization, so this follows the convention it set; and `.gitattributes` is shared configuration
five lanes depend on. The general form is stated there and is worth keeping: **`.gitattributes` is
comfort rather than control** — the hasher must hold on any clone whatever its config.

## Where the code and the prose disagree

Named rather than silently reconciled, with both sides cited.

1. **`execution-spec.md:277` describes the payload that was proven inert.** It says: *"Canonicalize
   agent definition + prompt + tool signatures + capability manifest."* That is the four-member
   pre-ruling-30 payload — the one `CONVENTIONS.md:1292-1322` demonstrated does not move on a body
   edit. The code carries **five** members, and the fifth is the fix
   (`target/refund_agent/freeze.py`, `RUNTIME_MODULES` / `runtime_source_hashes()`).
   **`CONVENTIONS.md` outranks `execution-spec.md`, so the execution spec is the defect.** The
   code is correct; the sentence is stale.

2. **`measurement-spec.md:978` says "tool set, tool descriptions, and system prompt."** Tool
   descriptions — the ADK docstrings — are **not** a field of Part A and not a field of
   `tool_signatures()`. They are covered, but transitively, as bytes of `tools.py` inside
   `runtime_source`. True today, and true only because ruling 30's fix landed; under the payload
   the same sentence was written against, tool descriptions were **not** covered at all.

3. **`measurement-spec.md:979` says every episode records `target_hash`.** The field is
   `target_agent_hash` everywhere in the code and in the contracts
   (`contracts/run_manifest.schema.json:35`, `:48`; the C6 and C7 golden fixtures).
   `CONVENTIONS.md:1304` also writes `target_hash` in prose. One concept, two spellings; the
   schema's is the operative one.

4. **`CONVENTIONS.md:45-49` and `:1310` quote `target_agent_hash` as `74116412b733db47`.** The dry
   run on 2026-08-21 reads `e53c73daa1dadefb`. **Neither is wrong.** The target legitimately moved
   after ruling 30 — `delegate_to_specialist` was added before the freeze precisely because that
   was the only window in which it was cheap (`execution-spec.md:242`). The ruling's values are
   **historical illustrations of a hash that moves**, not the value to be frozen. Any document
   citing a target hash before Sat 08-22 is citing a moving number; only `FROZEN.json` will be
   authoritative, and only after step 4.

## Consequences

- The demo agent is final on Saturday. If a phrasing bothers you on recording day, you ship it
  awkward. `execution-spec.md:795` requires the three demo conversations to be rehearsed **on Day
  3, before the freeze**, with throwaway captures, so that the objection surfaces while it is
  still free.
- Part A must be complete before step 4. `assert_manifest_covers()` makes that testable rather
  than asserted: a tool the agent can call and Part A does not declare is an error, never an empty
  capability set, because **the run would report a clean sheet on a surface it never inspected.**
- The freeze produces two of the five hash-locks. The other three are the gate rule (D2, already
  ready), the Objective Set (D3, same day, **separate**), and the corpus plus
  `derived_schema_hash` (D5).

## What this check would still fail to notice

Ruling 30's standing question, asked of the fixed version. Each of these is a real gap, and
none of them is closed by this ADR.

1. **A dirty working tree, or a disk-versus-HEAD difference.** `freeze.py` imports no `subprocess`
   and runs no git command. Its sibling `scripts/freeze-d2-gate-rule.py` refuses on four
   conditions — uncommitted changes to the artifact, disk differing from HEAD, a hash disagreeing
   with `contracts/MANIFEST.json`, and overwriting an existing record with a different hash —
   on the stated grounds that *"freezing a file that only exists on one laptop is not a freeze;
   the public commit timestamp IS the evidence."* **The D3 freeze has none of those four
   refusals.** Step 0 and step 3 of the protocol above are the manual substitute, and a manual
   step is exactly the kind that gets skipped at hour seven of the heaviest day in the plan.
2. **`FROZEN.json` carries no date and no commit SHA.** Its five fields are an id, three hashes,
   and a byte count — nothing that dates the act. The claim
   *"frozen before the corpus was written"* therefore rests entirely on git history, and there is
   **no `docs/proof/d3-target-freeze.json`** analogous to the D2 record.
3. **A `.py` added in a subdirectory of the target package.** `runtime_source_hashes()` globs
   `HERE.glob("*.py")` — **non-recursive**. Nine modules sit flat in the package today and
   `target/refund_agent/demo/` holds only JSON, so the gap is latent rather than live. A module
   added under a subdirectory would import as a namespace subpackage, run inside the frozen
   target, and be invisible to **both** directions of the assertion.
4. **A change to `capability_manifest.json` on disk.** The freeze hashes `build_manifest()`, not
   the committed file. The two were verified equal on 2026-08-21, and a test asserts it — but the
   freeze itself would not notice a stale committed artifact, and the committed file is the one a
   reviewer opens.
5. **The real system of record.** `simulated_system_of_record.py` is inside the lock, and its own
   docstring says *"nothing here should ever appear in a demo or a measured run"* — the real one
   is L1's SQLite ledger. The target's observable behaviour depends on the ledger it is bound to
   at run time, and **the freeze does not cover that ledger or its seed data.**
6. **The served model behind `gemini-3.5-flash-lite`.** The descriptor pins the model name, the
   thinking level, the endpoint, and the ADK version. A provider-side change to what those names
   resolve to moves no hash. This one cannot be fixed from inside the repository and should be
   said out loud rather than implied away.

## What this does not decide

- **The Objective Set freeze.** It is the same day and the same hard stop
  (`execution-spec.md:275`, hard stop 4b) and it is a **different artifact**: hashed by
  `ObjectiveSet.__init__` as `hash_full(strip_annotations(raw))[:16]`, asserted by G1(b), stamped
  on every episode. `freeze.py` does not touch it, and **no script produces an
  `objective_set_hash` freeze record** the way `scripts/freeze-d2-gate-rule.py` does for the gate
  rule. That gap is named here and is not filled here.
- **The D5 corpus freeze**, Part B, and the label-blindness gate.
- **The name of the D3 git tag.** `execution-spec.md:277` says *"Hash, commit, tag"* and never
  names it; the only tag the specs name anywhere is `freeze-day9` (`execution-spec.md:420`,
  `:691`). The coordinator picks it at step 7.
- What may change after the freeze. Nothing may, short of a re-baseline. That rule is
  `measurement-spec.md:979-980` and it outranks this document.

## Note on numbering

`docs/execution-spec.md:795` says *"Write the freeze protocol into ADR-002."* **`ADR-002` was
already assigned** — to the evidence-bundle schema, at `docs/execution-spec.md:766`, and written
as `docs/adr/ADR-0002-evidence-bundle-schema.md`. The collision is why the freeze protocol went
unwritten until the day before it executes: the number it was filed under already had a different
decision in it.

**This file is the protocol `execution-spec.md:795` requires, under the number ADR-0017.** Nothing
about the decision changed; only the number it lives at.
