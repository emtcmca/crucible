#!/usr/bin/env python3
"""Write the six lane briefs into docs/lanes/. W0 item 5.

Coordinator-written (CONVENTIONS.md section 6). A lane brief is the ONLY
document a lane reads besides CONVENTIONS.md and the contracts it consumes -
lane blindness is load-bearing, so a brief that gestures at another lane's
code has already broken the design.

Each brief carries the same seven sections, in the same order, so a lane can
find what it needs without reading prose it does not own.
"""

import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "lanes"

HEADER = """# {id} — {name}

**Coordinator-written. A lane does not edit its own brief.** If something here is
wrong, **stop and report** — do not edit and do not work around
(`CONVENTIONS.md` change protocol).

**Read before your first commit:** `CONVENTIONS.md` in full, then the contracts
you consume. Re-read `CONVENTIONS.md` before *every* commit.

| | |
|---|---|
| **Wave** | {wave} |
| **Branch** | `lane/{id}-{slug}` |
| **Worktree** | `C:\\dev\\crucible-wt-{id}` — created when the lane starts, not before |
| **Model calls** | {model} |
| **Unattended** | {unattended} |

---

## 1. Owned paths — stage inside these and nowhere else

```
{owns}
```

**Never `git add -A`.** Six blind lanes cannot share an index, which is why each
lane gets its own worktree. Before any git write: `git worktree list`, then
`git branch --show-current`, and confirm.

---

## 2. Scope

{scope}

---

## 3. Contracts you consume

{contracts}

**Every contract you consume is asserted by hash in your test suite.** Run
`python scripts/contract-check.py` before you commit; it verifies the whole set
against `contracts/MANIFEST.json`. A contract that no longer hashes to its
recorded value means someone edited a frozen artifact — **stop and report.**

Your input fixtures are in `contracts/golden/`. Develop against those, never
against another lane's code.

---

## 4. Your FIRST work item is your negative check

`CONVENTIONS.md` §8 rule 2: **a check that cannot fail is not measuring
anything.** Before you implement the behaviour, write the check that proves it
is absent, and **watch it fail.**

{negatives}

> This is not ceremony. On 2026-08-20 the contract gate's own first negative test
> could not fail — it appended a newline, which is exactly the mutation the
> normalization exists to absorb. It was caught only because the negative test
> was actually run. Two of the five gate passes then turned out to have defects
> of their own.

---

## 5. Exit criteria

{exit}

---

## 6. Stop conditions — report, do not work around

{stops}

**Universal stop conditions, every lane:**

- A value in `CONVENTIONS.md` looks wrong. **You do not edit it and you do not
  work around it.** The coordinator changes it, bumps `SPINE_VERSION`, and
  states in writing what prior results the change invalidates.
- A contract needs to change. **Lanes never edit `contracts/`.**
- **Weakening a gate is a stop condition, not a repair.** If the only way to
  green is to relax a never-cut gate, that is the finding, and it is reportable.
- Your work-item iteration count reaches **5**. Stop and report.
- You need something from another lane. That is a contract question, not a
  coordination question.

---

## 7. Standing rules that bite this lane specifically

{standing}

---

*Brief written {date} by the coordinator. Lane definitions: `lanes-spec.md` §3.*
"""

LANES = [
("L1", "FOUNDATION", "foundation", "W1 — FIRST AND ALONE in W1's first hours",
 "None. Pure code.", "Delegate the canonicalizer and golden vectors. **Do NOT delegate the IAM bindings unattended** — a wrong binding on the policies bucket silently destroys G8.",
 "crucible/canon/      canonicalizer + golden vectors\ncrucible/ledger/     the SQLite run ledger\ncrucible/gate/       the promotion gate with read-back\ncrucible/manifest/   manifest loading and hash derivation\ninfra/               Terraform, IAM, buckets\nscripts/verify-chain.py",
 """**You are the critical path. Everything that gets hashed waits on the canonicalizer.**

The canonicalizer implements `contracts/canonicalization.md` — RFC 8785 JCS with
seven project restrictions. Then: hash derivation, the ledger, the promotion gate
with read-back, and the GCS/IAM layer including **the Armorer 403 proof** captured
to `docs/proof/armorer-403.txt`.

**`scripts/gcp-env.sh` and `infra/create-buckets.sh` ALREADY EXIST. You inherit
them. Do not re-author them and do not pick a different suffix.** `SUFFIX=x7`,
project `crucible-hack-2026`, three buckets live with UBLA on and PAP enforced.
G7 and G8 grep these literal strings, so a retyped bucket name does not fail
loudly — **it produces an unevaluable gate, and an unevaluable gate is a check
that cannot fail.**

**You also own the `corpus/sealed/` pre-commit hook, and it must exist before D5.**
A hook that exits non-zero on any staged path under `corpus/sealed/`. Not a
convention, not a comment. The repo is PUBLIC: an accidental `git add -f` on the
sealed corpus used to be an internal mistake fixable by rewriting history. Public,
it is permanent, cloneable, and **it invalidates the sealed-family claim outright**
— the single headline number this project produces.""",
 "**C7** (`run_manifest.schema.json` + `canonicalization.md`) — you produce it.\n**C8** (`gate_rule.v1.yaml`) — you produce it; it hash-locks at D2 and is not editable after.\n**C4** — you own canonicalization of policy documents.",
 """- **Golden vectors 10, 11, 12 in `canonicalization.md` §3 are the negative half:** a
  payload with a BOM must be **rejected**, not silently stripped; a payload
  containing a float must be **rejected**; a payload containing `null` must be
  **rejected**. A canonicalizer that quietly coerces will pass all nine positive
  vectors and be wrong in production.
- A **key-order permutation** of one object must produce an **identical** hash.
- A **non-BMP key** must sort by UTF-16 code unit, not by byte order. They differ
  only here, which is why a `sorted()` on raw bytes passes every other test.
- A **deliberately corrupted read-back** must be caught by the gate.""",
 """- Golden vectors green, **including the key-order-sensitivity case and the
  float-formatting case**.
- The **Armorer 403 captured** to `docs/proof/armorer-403.txt` — a live 403 from an
  impersonation probe, not a policy grep. The grep is necessary and not sufficient.
- A **deliberately corrupted read-back is caught**.
- **G7(b2) and G8's basic-role assertion implemented** (`CONVENTIONS.md` §10a): no
  CRUCIBLE service account holds a project-level basic role. `G7(b)` alone cannot
  catch this — its filter tests `role =~ "storage|bigquery"`, which a basic role
  never matches.
- `python scripts/contract-check.py` passes.""",
 """- **The retention policy is never locked.** `infra/create-buckets.sh` exits 2 on any
  argument matching `*lock-retention*`. Do not route around it. A locked GCS
  retention policy cannot be removed or shortened by anyone including the project
  owner, and would block the §7.3 teardown for 14 days past the last write.
- **The G8 grant direction inverts easily and has already been proposed backwards
  once.** `crucible-gate` gets `objectCreator` on the policies bucket;
  `crucible-armorer` gets **no storage role at all**. Author is not promoter.""",
 """- **A tool's success message is not evidence.** Assert the postcondition: query the
  artifact, re-read the file, check the ledger row. `Register-ScheduledTask` has
  printed success while throwing, and a `gcloud` exit 0 has hidden a COM exception.
- **Never lock the retention policy.** Unrecoverable by anyone.
- **`gcloud ai agents` does not exist** at SDK 581.0.0 — re-checked across GA, beta,
  and alpha on 2026-08-20. `data-spec.md` §7.3's teardown calls it twice; rewrite
  against the Vertex AI SDK/REST or drop it."""),

("L2", "TARGET + CORPUS", "target-corpus", "W1 (a) D2–D3, freezes **Sat 08-22** · W3 (b) from D5",
 "Yes — Gemma, pinned by version and seed, for corpus generation only.",
 "**NO. This lane cannot be fully delegated.** A benign fixture nobody read is an assumption, not a fixture.",
 "target/refund_agent/   the agent under test\ncorpus/                attacks, training and sealed\nfixtures/benign/       26 fixtures, 14 mechanical near-misses\nfixtures/known_bad/    all 9, never cut\ntaxonomy/              family definitions",
 """**Scope (a), W1:** the refund agent, its seven bare-function tools bound to L1's
ledger, the written refund policy, the capability manifest **Part A**, three demo
conversations, then **the freeze**.

**The policy has NO free auto-approve tier.** Every refund at every tier requires a
verified order lookup and a stated qualifying reason. That is architecturally
load-bearing, not realism: it makes the policy's most basic rule a
**capability-composition rule rather than a dollar threshold.**

**Scope (b), W3:** 50 training attacks (8 per family × 6, except F5 at 10 — amended 2026-08-21,
ruling 43, `corpus/C6-reach`), **24 sealed — 18 is the
ABSOLUTE FLOOR**, 26 benign with 14 near-misses, 9 hand-written known-bads, and
**the 26 recorded v0 fixture traces G3 replays every round.**

**F4 is DESTINATION SMUGGLING ONLY** (ruling 13, three binding conditions). The
smuggled item must be a **structured, comparable** argument. **No free-text-content
instances in the sealed set** — a content instance breaches at v0 *and* at vFinal
because nothing can stop it, so transfer collapses toward zero **mechanically** and
the failure looks exactly like *"the system did not generalize."* It isn't. It is
*"we sealed a family the language cannot express"* — **a rigged failure, which is
worse than a rigged success, because you would believe it.**""",
 "**C3** (`capability_manifest.schema.json` + `derived_schema.schema.json`) — you produce both. Part A freezes **D3 with the target**; Part B freezes **D5 with the corpus**, gated on the label-blindness check.",
 """- **The label-blindness check is your negative check and it gates the Part B
  freeze.** Compute every `episode.*` and `derived.*` field over the corpus **with
  labels withheld.** If any field perfectly predicts attack-vs-benign, it is a leak
  and it is **removed**. A field meaning *"this is the bad one"* makes every
  downstream number meaningless **while looking exactly like success** — the only
  failure here that gets *more* convincing as it gets worse.
- **The approver-field lint:** the field is REQUIRED on every instance and is the
  sentinel `"NONE"` when none is declared. **Absent is a validation error, not a
  default** — "declared none" and "the author forgot" are otherwise the same bytes,
  and a forgotten approver silently flips a pair from policy-separated to
  oracle-denied.
- **The fault-`reason_code` lint:** no attack instance may use a fault reason code as
  its sole distinguishing feature from its paired fixture.""",
 """**Exit (a):** the freeze hash **recomputes identically from a clean checkout** ·
three demo conversations rehearsed and throwaway-captured **before** the freeze ·
the C3 predicate schema is in the manifest.

**Exit (b):** benign suite **26/26** against `policy@v0` · **all 26 v0 fixture
traces recorded, and at least one replayed through the shadow Policy Engine to the
same verdict the live run gave** · every pair carries its **SEP-BY** label ·
**target split 18 policy / 4 oracle** *(benign amended 24→26, ruling 43, 2026-08-21)*.""",
 """- **If oracle-separated pairs reach parity with policy-separated, STOP AND
  RE-AUTHOR** (ruling 17). At parity, half the headline is a statement about a
  scripted oracle the builder wrote.
- **If the sealed family cannot reach 18, stop.** The floor is arithmetic, not
  preference: transfer is unmeasurable when `breached_at_v0 < 12`. **Below 18 the
  headline claim dies.** This is the cut that looks cheapest on a Thursday night.""",
 """- **Read every one of the 26 benign fixtures yourself.** ~2.5 hours, and there is no
  way around it. This is the load-bearing hand-cost in the whole plan. *(Amended from 24,
  ruling 43, 2026-08-21.)*
- **`episode.*` freezes before the first user turn and is unwritable after.** One
  in-episode turn moving `episode.account_holder_email` collapses the F4 seal.
- **Reframe-as-defective is NOT a target failure.** Visa's guidance on dispute
  condition 13.3 says a merchant's return policy "has no bearing", so a customer
  who restates a request as a defect claim is structurally unstoppable. Write it
  into the Objective Set as an **explicit non-breach** before D3, or the harness
  manufactures false positives no gate catches."""),

("L3", "ENFORCEMENT", "enforcement", "W1, once L1's canonicalizer lands",
 "**Zero.** Pure code, fully offline.",
 "**Yes — the safest lane to run unattended in a loop.** Offline, deterministic, and its exit criteria require a check that FAILED before implementation.",
 "crucible/policy/     the policy engine\ncrucible/dsl/        parser + validator\ncrucible/compiler/   ADK plugin compiler\ncrucible/plugin/     CRUCIBLE_PLUGIN, the enforcement point",
 """DSL parser and validator, the policy engine, the ADK plugin compiler, the
`episode.*` freeze and the `derived.*` stamp.

**The enforcement point is `before_tool_callback`**, and it is verified real:
`plugin_manager.run_before_tool_callback` fires at `functions.py:553`, **Step 1,
before** `agent.canonical_before_tool_callbacks` at `:564`.

**ADK 2.1.0 is pinned.** Issue #2809 is FIXED in it — `include_plugins: bool = True`
propagates the parent's plugins into a nested Runner, so **the whole `OPAQUE` union
mechanism is obsolete.** Replace it with a one-line attach assertion that every
`AgentTool` has `include_plugins is True`, and refuse otherwise.""",
 "**C4** (`policy.ebnf` + `policy_document.schema.json`) — parser and validator.\n**C2** (`decision.schema.json`) — you produce it.\n**C1** (`tool_event.schema.json`) — you produce it, from the plugin.\n**C3** — you consume both parts.",
 """**Four semantics, each of which SILENTLY DISABLES the predicate it belongs to if
wrong. All four need a check that failed first:**

1. **`preceded_by` and `episode_sum` read ONLY events with `policy_decision == allow`
   AND `status == ok`.** Otherwise **an attacker satisfies `preceded_by` for free
   with one blocked call.**
2. **`episode_sum` INCLUDES the pending call.** Otherwise the call that first crosses
   the threshold is the one that executes.
3. **`episode.*` is frozen before the first turn and unwritable after.** A write
   attempt after episode start is `HALT_HUMAN`, **never a merge**.
4. **`derived.` is reserved**, resolved against Part B's declared set, and
   **overwritten in `before_tool`, discarding anything the model wrote** — and
   recording the attempt in `derived_overwrites`.

**Plus the four from C4's negative-check list:**
`{CAP_MOVES_MONEY, CAP_READS_PII}` vs `cap:CAP_READS_PII => deny` **must match** ·
`cap:A|B` **must be a parse error** · a document containing `match_mode` **must be
rejected** · two rules with different verbs on one multi-class call → **`deny` wins,
file order not consulted**.""",
 """- A hand-written patch compiles, registers, and **the blocked tool never appears in
  the ledger**.
- The validator **rejects a rule containing a payload substring**.
- A model-supplied `derived.subject_verified_in_episode` is **discarded before
  evaluation AND recorded** in `derived_overwrites`.
- All four semantics have a test that **failed before implementation existed**.
- `python scripts/contract-check.py` passes.""",
 """- **If a corpus pair appears to need a fourth verb or a fourth predicate form,
  stop.** The fourth form is held in reserve and gets added **on evidence, never on
  anticipation** — and the answer to nearly every hard pair was *add a field the
  harness computes, not extend the language.*""",
 """- **`derived.*` is HARNESS-computed, never model-computed.** A model-computed input
  argument launders a model into the pure-code path without touching the component.
- **The ARMORER never writes a `rule_id`.** It emits `r_new1`; **you** rewrite it.
  Reject any patch where the model emitted a hash-shaped ID on `add_rule`.
- **`cap:UNCLASSIFIED` must be rejected explicitly**, not by omission from the
  production list."""),

("L4", "ORACLE", "oracle", "W1, in parallel with L3 — no dependency on L3's code",
 "**Zero.** Enforced by a build-time import lint, not by instruction.",
 "**Yes.** Offline and deterministic. Watch the exit criteria — see below.",
 "crucible/tripwire/       the breach oracle\ncrucible/warden/         the replay-based regression warden\ntests/golden_traces/     hand-written traces",
 """The TRIPWIRE, the Objective Set evaluator, the nine known-bad harness, the
replay-based regression warden, and `--selftest`.

**The breach predicate is evaluated over the episode's ORDERED EVENT LIST**, with
three clause forms: `per_event`, `sequence`, and `aggregate(window_by_seq)`. It is
**not** an existential over single events — KB3 and KB7 cannot be expressed that way,
and both are boot self-test fixtures, so as originally specified **the harness
refuses to boot on D3**, a hard-stop day.

**The warden REPLAYS recorded v0 traces; it does not re-run live episodes.**
Over-blocking is a **policy** question, not a model question — which is what
"shadow Policy Engine" already implied.

**Dependency direction:** you develop against **hand-written** traces and **never
wait for L2**. The real v0 traces arrive at D5 and must validate against the same
C1 schema. **If they do not, that is a contract report, not a local fix.**""",
 "**C9** (`verdict.schema.json`) — you produce it.\n**C1** (`tool_event.schema.json`) — you consume it.\n**C4**, **C8** — you consume them.",
 """- **The import lint is your first negative check:** add an LLM client import to the
  tripwire and assert the build **fails**. The claim *"the TRIPWIRE contains no
  model"* is only structural if something enforces it.
- **`--selftest` must prove the harness can return each verdict**, including the ones
  that are supposed to be rare.
- **A deliberately mis-labelled known-bad must be caught.**""",
 """**All nine known-bads return their PER-FIXTURE EXPECTED VERDICT:**

```
KB1 KB2 KB3 KB4 KB7  ->  BREACH
KB5                  ->  REJECT
KB6                  ->  INVALID
KB8                  ->  CLEAN          <-- a blanket breach==true FAILS HERE BY DESIGN
KB9                  ->  linter REJECT-then-ACCEPT
```

**"All nine known-bads fail" is WRONG** and would fail on KB8 by design. There are
nine, not six, and **only five are breach fixtures.**""",
 """- **If the only way to green the boot self-test is to weaken KB3 or KB7, stop.**
  That would make F5 and F7 unmeasurable **while still being reported**, which is
  the worst available outcome.
- **If the D5 v0 traces do not validate against C1, that is a contract report.**
  Do not adapt your parser to accept them.""",
 """- **INVALID is not FAILED.** FAILED means the system under test behaved badly —
  that is a measurement, publish it. INVALID means **the instrument is
  untrustworthy**, and no number from an invalid run may be reported, **including
  the ones that look good**.
- **TARGET_FAULT is neither breach nor non-breach.** Removed from the denominator
  and logged. Counting a crash as "attack failed" would let a **fragile** target
  render as a **hardened** one."""),

("L5", "LOOP", "loop", "W3",
 "Yes — CORONER, ARMORER, RED_STRATEGIST. Pinned models, `thinking_level` set explicitly on every call.",
 "Partially. **The blindness tests are not delegable** — they are the design.",
 "crucible/coroner/     autopsies, no fix field\ncrucible/armorer/     patch synthesis\ncrucible/red/         attack strategist\ncrucible/conductor/   round protocol\ncrucible/governor/    budget",
 """CORONER, ARMORER, RED_STRATEGIST, budget governor, and the round conductor **last**.

**The CORONER is schema-locked with no fix field, a prescriptive-language lint, and
free-text findings confined to a `human_only` subtree.**

**The ARMORER's input is an ENUMERATED PROJECTION with no free-text field at all.**
That is the structural fix, and a lint is not a substitute: the spec's own
`generalization_hypothesis` example handed the Armorer rule `r019` **in English**,
passed the modal-verb lint, and — being a **named typed field** — sailed through the
"adapter reads named fields only" defence.

**Feedback on a rejected round is counts and classes, never IDs or contents:**
`{benign_failures: 2, classes: [...]}`. The §8.3 demo beat originally handed over
"the two failing fixture IDs", which would demonstrate **on camera** the loop doing
the exact thing the design exists to prevent.

**Set `thinking_level` explicitly on every call.** Defaults are not free — thinking
tokens bill at the ordinary output rate with no discount.""",
 "**C5** (`breach_record.schema.json`) — you produce it.\n**C1**, **C3** — you consume them.\n**Never L4's code.**",
 """- **The adversarial blindness test:** feed the CORONER a free-text field containing a
  "recommended fix" string; assert the ARMORER's input dict **does not contain it**.
- **A second test asserting the adapter cannot address `human_only.*` AT ALL.** The
  lint alone is insufficient — **a hypothesis phrased as a description passes it.**
- **The governor aborts on a low ceiling and logs the abort as a first-class result,
  not an exception.**""",
 """- Both blindness tests pass.
- A campaign runs end to end unattended, producing bundles carrying **all five
  hashes**.
- **Verb usage is reported per family.** If `constrain_arg` never appears in the
  promoted policy, **say so in the same breath as the F4 number** — that sentence is
  pre-registered now, before the number exists.""",
 """- **Two consecutive gate rejections → `HALT_HUMAN`.** Do not tune to get past it.
- **If the ARMORER cannot emit valid DSL at the required rate, stop and report.**
  The remedy is a coordinator decision — raise `thinking_level`, add worked
  examples, or replace free-form emission with constrained JSON rendered
  deterministically into DSL text. **That pivot is cheap on Day 1 and impossible on
  Day 8.**""",
 """- **Never call fixture blindness "enforced" on camera.** The ARMORER holds
  `datastore.user` and Firestore IAM has **no per-collection granularity**, so
  nothing at the platform layer stops it reading a fixture collection. It is
  application convention plus a code check. **The sealed-family blindness IS real
  IAM** — that one may be called structural, and the 403 proves it.
- **The CORONER retains Firestore write.** Its inability to propose fixes is schema
  plus lint, and must be described as such."""),

("L6", "EVIDENCE + PRESENTATION", "evidence", "W3 viewer · W5 presentation",
 "None.", "Yes for the viewer. Presentation needs Eric.",
 "crucible/replay/   the replay viewer\ndocs/proof/        captured proofs\ndocs/adr/          COORDINATOR ONLY -- NOT this lane's. Corrected 2026-08-20\n                   on L6's report (F-3): this line contradicted\n                   lanes-spec.md section 4, which reserves ADRs for the\n                   coordinator because they record CROSS-lane decisions and\n                   a blind lane cannot see across. L6 touched nothing there\n                   and wrote no ADR, which was the right call under a brief\n                   that told it otherwise.\nREADME.md",
 """The replay viewer, the architecture diagram, the README with the Judge-path block,
the ADRs, proof captures, and video assets.

**The viewer reads only from disk and needs no credentials.** It is not a nicety —
it is **the demo instrument and the judge's free reproduction path**, and it is why
the demo can say *"the bundles are in the repo, replay them yourself"* instead of
running a multi-minute live loop on camera.

**The repo is PUBLIC**, so the reproduction path actually works for a stranger. The
README's Judge-path block is the highest-leverage paragraph in the project.""",
 "**C6** (`evidence_bundle.schema.json`) — you consume it. A hand-written bundle is in `contracts/golden/`.",
 """- **Replay from a clean checkout with NO credentials in the environment.** If it
  needs a credential, the judge cannot run it and the claim is untestable.
- **A bundle with a missing hash must be rejected by the viewer**, not rendered with
  a blank field.""",
 """- Replay runs from a clean checkout with **no credentials in the environment**.
- **A cold reader spins the project up following only the README.**
- The diagram is legible at 1080p.
- Every figure on screen carries its label: **`k=1`, single-sample, no stability
  estimate**; **the 18/4 SEP-BY split**; **the ~11.5% upper bound on unobserved
  regression**.""",
 """- **If a number cannot be stated with its label in the space available, cut the
  number, not the label.**""",
 """- **Never say "no legitimate behavior was lost."** Say **"upper bound ~11.5% on
  unobserved regression"** — 0/26 bounds the true rate at ≈11.5%, and that exact
  number is spoken on camera and printed in the README. **Read the figure off
  `python -m crucible.replay`, never off a page** — it is computed there from the
  denominator, which is why it was right on the day four documents said ≈12.5%
  *(bound amended with the denominator, ruling 43 / SPINE_VERSION 14, 2026-08-22)*.
- **Never say "found a vulnerability in Google's agent framework."** You found a
  **defect in a sample application's stubbed tools**, marked in-source
  `# MOCK API RESPONSE`.
- **The trust root is the builder**, who holds project Owner. Say it once, plainly,
  in the README and on camera. **No control here defends against him**, and implying
  otherwise is the overclaim most likely to be caught."""),
]


def briefs():
    """{filename: body} for the six briefs, WITHOUT writing anything.

    Split out from `main()` so `tests/test_lane_brief_generator.py` can ask what
    this script would emit without running it. A test that had to execute the
    writer would pass by overwriting the files it is checking.
    """
    out = {}
    for (lid, name, slug, wave, model, unattended, owns, scope,
         contracts, negatives, exit_c, stops, standing) in LANES:
        out["%s-%s.md" % (lid, slug)] = HEADER.format(
            id=lid, name=name, slug=slug, wave=wave, model=model,
            unattended=unattended, owns=owns, scope=scope,
            contracts=contracts, negatives=negatives, exit=exit_c,
            stops=stops, standing=standing, date="2026-08-20")
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for filename, body in sorted(briefs().items()):
        p = OUT / filename
        p.write_text(body, encoding="utf-8", newline="\n")
        print("  %s  %s" % (p.name, "%d bytes" % len(p.read_bytes())))


if __name__ == "__main__":
    main()
