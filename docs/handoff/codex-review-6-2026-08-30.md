# Codex review 6 - handoff

**Date:** 2026-08-30 · **Branch:** `main` · **Role:** READ-ONLY.

You are the Coroner. You write the autopsy; you do not propose or apply the fix.
**The seal is intact and no F4 object has been read** - and finding 8 of your
review 5 made me define what that sentence means, so see §6 before you take it
at face value.

## Review 5, actioned

| finding | state |
|---|---|
| **[P0] 1.** the ordering channel sinks the confidentiality claim | **CLAIM NARROWED, exactly as you specified.** Not closed - it cannot be. See §1. |
| **[P0] 2.** `--out` can place raw sealed material anywhere | **CLOSED, structurally.** §2. |
| **[P1] 3.** the public reader accepts system self-approval | **CLOSED.** Plus the code name that asserted a signature is gone. §3. |
| **[P1] 4.** post-read freshness disappears from published evidence | **CLOSED as far as it honestly can be**, and the residual is now printed. §4. |
| **[P1] 5.** `sealed_run` is not the structural authority described | **CLOSED.** Required, emitted, refused by the producer. §5. |
| **[P1] 6.** the proof cannot preserve its own clean-HEAD claim | **CLOSED by changing the claim, then enforcing it.** §7. |
| **[P2] 7.** only four of six adjudication fixtures are isolated | **CLOSED, and a census now reports it for all 45.** §8. |
| **[P2] 8.** the test suite reads the local sealed corpus | **CLOSED. You were right and the docstring was a lie.** §6. |
| **[P2] 9.** operational prose still states A3.4 | **CLOSED - five sites, not the two you found.** §9. |

**Suite: 2892 collected, exit 0** (2829 at your last look). **Green again with
every `bash`/`sh` directory stripped from `PATH`** - 4 of 73 entries removed,
`shutil.which` returns `None` for both, 0 failures. `contract-check.py`: all
eight passes OK, **61 reasons - 44 schema-bound, 9 reader-bound, 8 recorded NOT
ENFORCED**, matching your live count rather than my stale 58.

---

## 1. The ordering channel: I took your ruling, I did not argue with it

You said the artifact is publishable only behind *"selected argument values are
bounded or redacted; call-order confidentiality is not provided."* That is now
the claim, and it is written where a reader of the repository will hit it rather
than only where a reader of a bundle will:

**`AUDIT.md` item 10**, in the section headed *What this does not prove*. It
states that disclosure is not confidentiality, that the reader accepts the
document while annotating the channel, that the producer still chose to publish
the order, and it names the forbidden sentence - *"sealed content cannot escape
the published evidence"* - as false so it cannot be reached for later. It also
states why the channel is not capped: a cap on trace length is a cap on what the
TARGET did, and refusing to publish because the agent under test was talkative
files a run fact as a producer defect.

I did not touch `argument_surface_guarantee()`; it already said ORDERING OPEN.
**What was missing was that no reader of the repo ever saw it.** Swept every
`.md` and `.py` for a broad confidentiality claim; the two hits are
`data-spec.md:1046` and `:1444` - *"a screen-share cannot leak the sealed
prompts"*, about the demo UI holding no sealed read path. Narrower subject,
different surface, and I left them. **Tell me if you disagree.**

## 2. `--out` (P0)

`assert_out_path_is_offtree()`, `scripts/record-f4-transfer.py`, called from
`main()` before anything opens a file, **drive phase only** - assemble writes
the bundle, which is the artifact this project exists to publish and must be
allowed in the repo. Three refusals, all `E_SEALED_OUT_PATH`:

1. **the target already exists** - the drive opens `"w"`, which truncates, and
   on a one-shot that is destruction one shell-history keystroke away;
2. **any ancestor contains `.git`** - the load-bearing one. It refuses a path
   for being under version control rather than for being on a list, so it
   catches this repo, the SEAL worktree, and any clone nobody thought of.
   `.exists()` not `.is_dir()`: a worktree's `.git` is a **file**;
3. **any component names a cloud-sync root** - weaker, and stated as weaker.

It refuses; it never relocates. Path is `resolve()`d first, so a symlink out of
a temp directory into a repo is caught. **Seven tests, and I mutated the guard
to `return` and watched all six refusal tests fail, then reverted and verified
the revert by sha256 rather than by grep.**

Your sentence *"the tests' choice to use an external temporary directory is
convention, not enforcement"* is quoted in the guard's docstring, next to this
project's own precedent for the distinction - the `.gitignore` entry on
`corpus/sealed` that is documented as explicitly NOT the boundary.

## 3. Self-approval, and a code name that lied (P1)

`_check_adjudication` imports `_NOT_A_HUMAN` from
`crucible.transfer.adjudication` - imported, never retyped - and applies
`_clean_human`'s exact normalisation. Your `adjudicated_by = "runner"` mutation
is now a named fixture, **TKB37**, which also made TKB37 isolated (it previously
tripped `E_TRANSFER_SCHEMA` too, because `" "` fails `minLength`).

Your second sentence mattered more than the first: *"this remains named
attribution rather than authenticated identity; it should not be presented as a
cryptographic signature."* So:

- every description of the field, in the docstring, the defect text, the reason
  table and the rendered report, now says **named attribution, not
  authenticated identity**;
- **`E_ADJUDICATION_UNSIGNED` is renamed `E_ADJUDICATION_UNATTRIBUTED`.**
  Nothing signs that field, and a code whose name asserts a signature was doing
  the overclaiming in the one string a reader of the report actually sees. It
  appeared in no contract, registry or committed artifact, so the rename was
  cheap - which it will not be next week.

## 4. The post-read challenge, and where I was wrong (P1)

`AdjudicationLedger` now carries `post_read_challenge` through
`load_adjudication` and `to_record()` re-emits it **byte-identical after
canonicalisation** - a test asserts that, because a ledger that rebuilt a digest
from its own state would still pass a field-by-field check. Absent stays absent;
it is never emitted as `null` (the canonical form admits none). Schema:
required, closed, five fields.

**I briefed the reader work with a claim that was false and had to retract it
mid-flight.** I told the agent that `response_digest` recomputes offline from
`decisions`. It does not - it covers the raw nonce, and only `nonce_digest` is
published. I had also written that false claim into the schema's own `$comment`,
where it sat in a published contract for several hours. Both are corrected, and
the correction says what it replaced.

**Exactly one field is checkable offline:** `instance_set_digest`, which must
agree in three places - the challenge block, the record's own top-level field,
and a fresh derivation from `instance_ids`. That catches a challenge minted over
one set and stapled to a ruling about another. `binding` is a constant string
and is compared against one obtained by *calling* `attach_challenge`, not
transcribed.

`adjudication_guarantee()` prints on every run beside the argument-surface one:
`response_digest`, `nonce_digest` and `minted_at` are **recorded and not
verified here**, and it closes with your phrase - **operationally closed,
evidentially open**. Tests assert the reader makes no "AFTER the read" claim in
any emitted string.

**An option I did NOT take, and want your ruling on.** Publishing the raw nonce
*after* the adjudication is committed would make `response_digest` verifiable by
anyone. The record is already published in the same bundle, so I do not think it
buys an attacker anything. It is a change to the security argument on the day
before the run, so I am not making it unilaterally. **Is it worth taking?**

## 5. `sealed_run` (P1)

You asked for one required machine authority with prose derived from it. That is
what exists:

- `execution_provenance.required` includes `sealed_run`;
- `crucible/transfer/bundle.py` raises `BundleError` if it is absent or
  non-boolean - **the producer fails, at the moment it assembles**, ruling 60,
  rather than leaving it to whoever validates later;
- the assembler emits `bool(raw["sealed"])` at `record-f4-transfer.py:1522` and
  derives the label from **the same value** at `:1500` via
  `seal_status_label()`. Two statements, one source;
- the reader takes the flag as authority; absent is its own defect and falls
  back to the label **only in the direction of more checking**, which the
  comment states;
- the disagreement refusal is kept verbatim.

Fixtures **TKB42** (flag deleted) and three builder tests, including the
over-blocking control that both boolean values build.

## 6. The suite read the sealed corpus, and the module said it did not

**You were right, the docstring was false, and finding it by declining to run
the suite is the version of this that costs least.**

`test_the_script_runs_end_to_end_and_returns_a_real_exit_code` ran the real
proof, which shells to `seal-commitment.py` and `seal-leak-check.py`, both of
which open and parse every sealed JSON. On this machine `corpus/sealed/` does
not exist, so resolution fell through to the SEAL worktree - so an ordinary
`pytest` run opened the holdout. `"Nothing here reads the sealed corpus."` was
literally false.

**Your demand that the methodology separate the two is met, and I did it by
citing rather than restating.** The module docstring now names three things that
were all being called "a read":

- **BUCKET DATA ACCESS** - a granted `storage.objects.get` naming a real object,
  inside the run's window. **The only unit the pre-registration defines** (A3.1,
  A3.2). Not restated in the test; that document owns it.
- **LOCAL FINGERPRINTING** - bytes in, digest out, nothing surfaced. This is how
  the seal is *proven* intact; forbidding it would forbid the proof.
- **A CONTENT READ** - sealed text reaching a human's eyes or a model's context.

`"no F4 object has been read"` is the first, and it survives untouched. The test
now points `CRUCIBLE_SEALED_DIR` at an invented fixture set, **and asserts the
commitment check DISAGREED** - because my first attempt asserted only `not
said_pass`, which the dirty tree satisfies whether or not the override was
honoured. That was a check that passes while measuring nothing, written into the
fix for checks that pass while measuring nothing. The comment says so.

A second test walks this module's AST and requires every `subprocess.run`
launching the script to pass an explicit `env=`, with a census so it cannot pass
over an empty list.

**The PASS branch is no longer exercised in CI, and cannot honestly be** -
reproducing it means reading the holdout on every commit. It is exercised by the
operator immediately before the read. Say if you want that differently.

## 7. The proof's clean-HEAD claim (P1)

You were right that it cannot be simultaneously new, committed, HEAD-bound and
clean. **So it no longer claims to be.** The artifact carries an explicit
`_the_ordering_OF_THIS_ARTIFACT` block stating a SEQUENCE: clean at the commit
named in `head`; this artifact then the only path that changed; the commit
carrying it therefore has `head` as its **parent**. A reader checks that against
the repository - `git log -1 --format=%P` and `git show --stat` - without
trusting the file.

The middle link is enforced, not described: `--write` re-runs `git status
--porcelain` afterwards and **refuses (exit 2) if anything other than the
artifact is dirty**. Extracted as `stray_dirty_paths()` so it is testable -
inline, its only execution would have been inside `--write`, which is another
check nobody had watched fire. Three mutants, all killed, revert verified by
sha256.

## 8. Fixture isolation (P2)

TKB37 fixed as above. **TKB41**'s four codes came from appending an exclusion
row for an instance the bundle still scored; it now rules the instance the
golden already excludes. One key, one code.

`run_suite()` rows carry `isolated` / `extra_codes` / `schema_coupled`, and
`isolation_census()` prints for all 45 fixtures: **22 isolated**. Pre-existing
non-isolated fixtures were **not** changed and are **not** asserted on - they
are reported, which is the point. TKB36-41, 44, 45 are all isolated.
`SCHEMA_COUPLED_FIXTURES` records TKB42/43: deleting a contract-required field
is necessarily visible to both instruments.

**One observation to rule on:** eleven pre-existing non-isolated rows fire *only*
`E_TRANSFER_SCHEMA` alongside their named code - reader-isolated, with the
contract seeing the same single mutation. That is a different kind of
non-isolation from TKB5's five codes. Should the census separate them?

## 9. Stale operational prose (P2)

Five sites, not two. `record-f4-transfer.py`'s crash comment stated A3.4's
scored-episode boundary; execution reaches it only after the sealed objects are
in memory, so under **A3.11 every crash there is terminal INVALID** and the
completed-episode count does not change that. The comment now says what it
replaced and notes the count still governs a stand-in drive. Four more in
`adjudication.py`: the module docstring, `decisions_digest`, `to_record` (the
one you cited) and `build_adjudication` - all four asserted the old
committed-before-the-unseal protection, which no longer exists.

---

## What I want you to attack hardest

1. **§1.** Is `AUDIT.md` item 10 the narrowed claim you ruled for, or is it
   still doing work the evidence does not support?
2. **§4.** The nonce-publication question. I would rather you ruled.
3. **§6.** Is the three-way vocabulary the right cut, and does `"no F4 object
   has been read"` still stand as written on the README and in three handoffs?
4. **The new debt I created.** `tests/test_assertion_census.py` is new: a
   ratchet over test functions with no `assert`, no `raise` and no
   `pytest.raises`. An open thread had carried this as *"my three tests that
   assert nothing"* for two sessions. **The census found thirty-five.** They are
   listed by name, the ratchet fails on a new one AND on a stale exemption, and
   it ships two deliberately broken fixtures plus a false-positive control for
   `pytest.raises`. I did not rewrite the thirty-five - three people were
   holding files the day before an unrepeatable run. **Is a ratchet the right
   call here, or is it a way of not doing the work?**

## Still open, and known

- **Eight contract reasons recorded NOT ENFORCED.** Still gaps on a green
  PROVEN pass, which the pass says on every run.
- **`scripts/hash-contracts.py --help` writes the manifest** - any unrecognised
  argument does. Already documented at `CONVENTIONS.md:694`, and bare invocation
  is the documented way to re-register across a dozen docs, so I did not change
  the CLI on deadline day. Flagging that a typo can silence the drift gate and
  look like success.
- **ERIC OWES:** adjudicate 24 instances after the read and before the first
  model call - the in-process path exists and nobody has walked it. And record
  the video, the only Stage One pass/fail item still missing.
