# Narration chunks — what may be recorded when, and what each one asserts

**Eric's call, 2026-08-24: the narration is chunked, not one take.** Each chunk is
independently replaceable, so a figure that moves costs one re-record instead of the whole
read. Script: `docs/execution-spec.md` §4.

Two things make that safe, and both are below: **a figures manifest**, so a chunk that has
gone false is findable, and **a reproducible setup**, so chunks cut together without an
audible seam.

---

## Why the manifest exists

**Recorded audio is not in `canon-check --sweep`.** Once a chunk is on disk it asserts its
figures forever and nothing sweeps it. A number moves, the chunk is silently false, and the
defect ships in the one artifact a judge actually watches.

That is this project's house defect — a claim with no check that can fail — in a medium the
gates do not reach. The manifest is the check: when a figure moves, grep this file for it
and the affected chunks are named.

**Every figure below was read from source 2026-08-24. Re-verify before recording, not from
this table.** Ruling 46 logic: this file names where a figure lives, and the artifact owns
the value.

---

## Chunks

| # | Time | Status | Asserts | Read from |
|---|---|---|---|---|
| **N1** | 0:00–0:12 | **GO** | none | cold open, no figures |
| **N2** | 0:12–0:25 | **GO** | none — "the ledger moved" is shown, not stated | on-screen sqlite row |
| **N3** | 0:25–0:50 | **GO** | none | the friction, no figures |
| **N4** | 0:50–1:35 | **GO** | 3 model pins · 8 tools · 11 clauses · 26 benign · 14 near-miss · 9 known-bad · 6 attacks/round · three verbs | `crucible/red/red.py` · `target/refund_agent/tools.py::TOOL_FUNCTIONS` · `contracts/objective_set.v1.json` · `fixtures/benign/` · `crucible/tripwire/known_bad.py::KNOWN_BAD_IDS` · `crucible/dsl/nodes.py` |
| **N5** | 1:35–1:43 | **GO — one wording fix** | **"five locks", NOT "five hashes"** | `crucible/conductor/hashlocks.py:131` — five locks occupy six fields; ruling 20 split the fifth. Both true, neither is the other |
| **N6** | 1:43–2:05 | **BLOCKED** | the breach, the invariant that fired, the amount | needs a real bundle from `evidence/batch-2026-08-24/` |
| **N7** | 2:05–2:30 | **BLOCKED** | the emitted rule, in real grammar | needs a real `PatchSet` from the batch |
| **N8** | 2:30–2:52 | **BLOCKED** | benign pass rate, failure count, capability classes | script reads 24/26; **no run has produced it** — run 1 went 5/26 then 16/26 |
| **N9** | 2:52–3:22 | **BLOCKED ON THE 08-28 UNSEAL** | the entire held-out block | every figure is a design target today; `docs/execution-spec.md:461` |

**N1–N5 are recordable tonight. N6–N9 are not.** N9 has a pre-written leak-case alternate
in the script — that alternate is itself a swappable chunk, which is the chunking design
already anticipating the outcome it cannot predict.

### RE-VERIFIED AT SOURCE 2026-08-27, before the tonight recording

The table's figures carried a 2026-08-24 stamp and counts drift in this repo, so
every N4/N5 assertion was re-read from source on the day of the take:

| asserted | source | 2026-08-27 |
|---|---|---|
| 8 tools | `target/refund_agent/tools.py::TOOL_FUNCTIONS` | **8** |
| 11 clauses | `contracts/objective_set.v1.json` | **11** |
| 26 benign | `fixtures/benign/*.json` | **26** |
| 14 near-miss | the `near_miss` key in those same files | **14, and they are a SUBSET of the 26, not 26 plus 14** |
| 9 known-bad | `crucible/tripwire/known_bad.py::KNOWN_BAD_IDS` | **9** |
| three verbs | `crucible/dsl/nodes.py::VERBS` | **3** — `constrain_arg`, `require_approval`, `deny` |
| N5 "five locks" | `crucible/conductor/hashlocks.py:131` | **five locks occupying six fields.** The wording fix stands |

**ONE NEW AMBIGUITY, INTRODUCED TODAY.** There are now **two** nine-fixture
known-bad suites: `crucible/tripwire/known_bad.py` (the Tripwire, Warden and
policy linter — the judge of RUNS, G1-gated) and `crucible/replay/known_bad.py`
(the offline reader — the judge of EVIDENCE, added 2026-08-27). Both hold nine.
N4's "nine known-bad" is still true and still cites the Tripwire suite.

**Do not add the second suite to N4** — the beat is already dense at 45 seconds,
which is the same reason the narrowing loop was pushed to N8. If a spoken
disambiguation is wanted, N4 says **"nine known-bad fixtures the tripwire must
always fail"**, which is unambiguous at no extra length.

---

### N4 carries a gap the script predates

The script's architecture beat does not mention the **narrowing loop** — the ARMORER
retrying against Warden feedback, up to 6 attempts (`conductor.py:98`). It landed
2026-08-24, after the script was written.

**Do not add it to N4.** That beat is already dense at 45 seconds. It belongs in **N8**,
which is about exactly that feedback ("what goes back is a count and two capability
classes"), and N8 is being re-recorded anyway. Add one clause there: that the loop retries,
and the budget is what bounds the leak.

---

## Reproducible setup — the thing that makes chunks cut together

N1–N5 record tonight; N6–N9 record on or after 08-28. **Four days apart is where an
audible seam comes from**, and no edit repairs a noise-floor mismatch.

Before recording tonight:

1. **Record 60 seconds of room tone** — silence, same mic, same room, no talking. It fills
   gaps and matches noise floor across sessions. Cheap tonight, impossible to reconstruct
   later.
2. **Write down the setup**: mic, distance from mouth, gain/input level, room, and where in
   the room. Reproduce it exactly on the 28th.
3. **Same time of day if possible.** Voice sits differently at 11pm than at 2pm.
4. **Before recording N6–N9, play back the tail of N5 and match into it** — pace and energy
   drift over four days more than level does, and it is the harder one to hear in yourself.
5. **Two seconds of silence at head and tail of every chunk**, so cuts have somewhere to
   land.

Seams fall at beat boundaries, which are natural pauses already.

---

## What comes back to the build

Chunk durations from the recorded takes become the **cue list** for the architecture
animation (`docs/design/architecture-animation-spec.md`). **N4's actual length sets the
architecture beat's timing** — the animation is cued to Eric's real pacing, not to the
script's estimate.
