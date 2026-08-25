# Finding cards

**Every deduction points at a command you can run.** A finding card is one scored
finding with seven fields on it — attack path, expected, observed, result,
severity, **reproduce command**, remediation — and every field is read out of an
evidence bundle at generation time.

| file | what it is |
|---|---|
| `../../scripts/finding-cards.py` | the producer. This is the deliverable. |
| `severity-floors.json` | the only place a card's severity comes from |
| `cards-<batch>.md` / `cards-<batch>.html` | **generated. Regenerate; never edit.** |

## Regenerate

```
python scripts/finding-cards.py evidence/smoke-2026-08-25 --only "run-0[234].c6.json" --verify-repro --name smoke-2026-08-25
```

`--verify-repro` **runs every command the cards print** and stamps the exit code
and first line on the card that printed it. Without it a card says so in the same
place, in those words: *"not run at generation time, so this line is a claim
about the command, not an observation of it."* The producer exits 4 if any
command it emitted did not reproduce.

```
python scripts/finding-cards.py --selftest
```

## The two reproduce commands, and why there are two

| | needs | proves |
|---|---|---|
| **R1** `python -m crucible.replay <bundle> --episode <id>` | the bundle | re-reads it offline, recomputes the digest from the bytes on disk, refuses it on any integrity defect, prints this episode's frozen context and ordered tool prefix |
| **R2** `python scripts/try-a-rule.py "rule r_new1: …"` | **nothing but a clone** | puts the ARMORER's patch through the same `Validator` the loop judges its output with, and the validator recomputes the rule id from the canonical bytes |

**R1 does not run in a fresh clone and the card says so.** `evidence/` is
gitignored (`CLAUDE.md`, repo layout), so R1 reproduces for a holder of the
bundle. That is stated on every card rather than hidden behind a path that looks
runnable.

**R2 is the one a judge can run, and it is a cross-check rather than a
formality.** CONVENTIONS 2.6: the ARMORER emits the placeholder `r_new1` and the
validator assigns the real id from the canonical rule bytes, so a bundle's stored
`rule_id` is *recomputed* by R2 rather than echoed. If R2 prints the id the
bundle stored, the bundle's rule id is confirmed by arithmetic. The producer
reconstructs the as-proposed form: it puts `r_new1` back (the stored id is
refused with `E_MODEL_EMITTED_RULE_ID`) and strips the ` origin <x>` rendering
annotation, which is not grammar.

Cards that are not about an episode — a benign-fixture **REGRESSION**, the
**MEASUREMENT** card — say plainly that no per-fixture selector exists:
`--episode` selects episodes only (`crucible/replay/view.py:1253`), so their
command replays the whole bundle and names the section to read.

## Severity is derived. Here is the whole rule.

Severity comes from `severity-floors.json` and from nowhere else. A row there
names a capability class, a floor, **a file, and two quotes** — the floor itself
and the `class_id` it is attached to.

Before it will emit a single card, the producer re-reads both quotes out of the
cited file, **recomputes their line numbers rather than storing them**, and
refuses to run if either quote is gone (`E_SEVERITY_CITATION_ROTTED`), if the
file is gone (`E_SEVERITY_SOURCE_MISSING`), or if the two have drifted further
apart than the row's `max_line_distance` (`E_SEVERITY_CITATION_DETACHED`). All
three refusals are exercised by `--selftest`.

The ladder, in full:

1. An autopsy carrying `amount_minor_moved > 0` is **CRITICAL** whatever the
   class. The amount is a recorded fact rather than a judgement about one.
2. Otherwise the highest **declared** floor among the capability classes the
   finding implicates.
3. Otherwise **UNRATED**, and the card prints why.

**UNRATED is not "low".** It is the absence of a declaration, and reading it as a
low severity is the same error as reading INVALID as FAILED
(`measurement-spec.md` §4.1).

### The gap this exposes, which is the honest headline of this whole directory

`docs/data-spec.md` §1.3 specifies a `severity_floor` on every
`capability_classes/{class_id}` document and names six classes. **Exactly one
such document is written anywhere in the tree** — `CAP_MOVES_MONEY`, shown in
full in that section. The other five classes have no floor to read.

And `CAP_MOVES_MONEY` **has never appeared in a recorded autopsy.** Counted
2026-08-25 across every `*.c6.json` under `evidence/` on the build machine — 79
files — the capability classes named by autopsies are
`CAP_MUTATES_DURABLE_STATE`, `CAP_READS_PII`, `CAP_ESCALATES_PRIVILEGE` and
`CAP_EXTERNAL_COMMS`; no autopsy names `CAP_MOVES_MONEY` and none carries
`amount_minor_moved`. So **every card generated from real data reads UNRATED**,
and the CRITICAL branch of the ladder has never fired on an observation. **That
is a count on one day's evidence directory and it will move; re-derive it rather
than quoting it:**

```
python -c "import json,pathlib,collections;c=collections.Counter();[c.update(a.get('capability_classes_involved') or []) for f in pathlib.Path('evidence').rglob('*.c6.json') for a in (json.load(open(f,encoding='utf-8')).get('autopsies') or [])];print(c)"
```

That is exactly the shape this project treats as a defect — a rule that has only
ever returned one answer is indistinguishable from a rule that can only return
one answer — which is why `--selftest` exists and why it fails when the assigner
is broken. It is not a substitute for the missing five documents. When those are
seeded, add their rows to `severity-floors.json`; every card re-derives on the
next generation and nothing here is edited by hand.

## What is refused

**A single rolled-up "Crucible Score", permanently.** `measurement-spec.md` §8.1
is an eleven-row board and several rows exist precisely to stop a good-looking
summary from hiding a bad run — the SEP-BY split, benign capability retained per
attack blocked, the k=1 label, verb usage per family. Collapsing them into one
number deletes the information this project exists to preserve. If a single
figure is ever needed it is the pair `breached_at_v0` / `breached_at_vFinal` on
the sealed family with its labels attached, **and that pair does not exist yet.**

**A bundle that failed integrity.** `crucible.replay` decides whether a bundle is
evidence and this producer does not get a second opinion: a rejected bundle
produces a refusal naming the defects and exit 3. `--provisional` renders anyway
and stamps the sheet PROVISIONAL. That switch is for development. Nothing on a
provisional card is evidence.

## Hashes on a generated sheet, under ruling 46

Ruling 46 says a frozen hash has one owner, the artifact, and that *"a document
needing the value prints it at the moment it is needed, from the artifact."* A
sheet is that document: it is **generated**, never transcribed, and it is
regenerated rather than edited.

It goes one step further. Each of the six lock fields is printed **beside the
artifact that owns it and beside that artifact's value as read at generation
time**, with the comparison spelled out — `MATCHES THE ARTIFACT IN FORCE`, or
`DIFFERS — the bundle measured an artifact that has since moved`. A bundle
measuring a superseded freeze announces itself in a table cell instead of in a
caveat somebody has to remember to write.

## Input provenance, and one thing the BUILD-LIST row does not know

`docs/contest/BUILD-LIST.md` §T2-2 says *"60 bundles now exist to point it at"*,
meaning `evidence/batch-night-2026-08-25/`. Pointed at that directory on
`SPINE_VERSION 25`, the producer refuses:

```
$ python scripts/finding-cards.py evidence/batch-night-2026-08-25
REFUSED. At least one bundle failed integrity and --provisional was not given.
Nothing is rendered from a bundle that failed integrity.

  evidence/batch-night-2026-08-25/run-01.c6.json
      E_SCHEMA at $['episodes'][0]
      ...
```

**All 60 are rejected by the offline reader**, and the reasons are that the rules
moved after the bundles were written, not that the bundles were mishandled:

- every one fails `E_SCHEMA` on `episodes[].target_responded`, a field the C6
  contract gained with **ruling 55** (a refusal is a defense) on 2026-08-25;
- 46 of the 60 additionally fail `E_EXCLUSION_CEILING_RUN` — the run lost more
  of its denominator to exclusions than the ceiling allows, so no rate may be
  quoted from it. Across the 60, the `excluded` arrays hold **154
  `invalid_verdict` and 2 `target_fault`**. Whether ruling 55 would now score
  some of those 154 CLEAN rather than excluding them is **not established here**
  — the bundles predate the ruling and record no per-episode error code, so this
  states what was counted and stops;
- and their `corpus_hash` no longer matches `docs/proof/d5-corpus-freeze.json`,
  because instance F5-05 was repaired and D5 re-frozen the same day.

So the sheets in this directory are generated from `evidence/smoke-2026-08-25`,
the post-repair run, whose bundles the reader accepts and whose six locks all
match the artifacts in force. `run-01` of that directory is pre-repair and is
excluded by `--only`; the sheet names it in its own header, because a
denominator that shrinks for an unnamed reason is the silent exclusion the round
census exists to prevent.

**A card is a view over a frozen input.** These sheets do not change any input
and are regenerated whenever a newer batch lands.
