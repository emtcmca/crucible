# Codex review 7 - handoff

> ## CORRECTION - REVIEW 7 CAME BACK NO-GO AND REJECTED SEVERAL OF THIS FILE'S CLOSURE CLAIMS
>
> *Added 2026-08-30, after the reviewer's verdict on the file below. **Nothing
> beneath this block has been rewritten.** Every claim it makes stands where it
> was written, including the ones that were wrong, because a document edited to
> look right afterwards is not a record of anything. Read the table, then read
> the file knowing which rows it got wrong.*
>
> The file below says *"Every ruling in your table was taken. None was argued
> with."* That was true of review 6. It says nothing about whether the work
> **closed** what it claimed to close, and on eleven items the reviewer ruled on
> that question directly. Four came back as reject or partial.
>
> | Review 7 claim | Codex's call |
> |---|---|
> | Output-path race closed | **Reject closure** - overwrite closed; lifecycle and ancestry remain |
> | Contract gate green | Accept |
> | HEAD binding closed | **Amend** - interval check works; Git failure and drive binding remain |
> | Holdout-reading test closed | Accept for current source |
> | Read vocabulary closed | **Amend** |
> | Challenge report corrected | Accept |
> | Signature vocabulary closed | **Reject** |
> | 22/14/9 fixture census | Accept |
> | Assertion census at 36 | **Reject count**; accept ratchet with limits |
> | Nonce not published | Accept |
> | Runbook operator-ready | **Reject** |
>
> **The shape of the four bad rows is one shape, and it is worth naming rather
> than filing.** Each closed the instance and reported the class. The output
> path stopped an overwrite and was written up as closing the race, when
> lifecycle and ancestry were untouched. The vocabulary named the tool in front
> of me and was applied to a second tool that does more. The census reported a
> count from prose that the list had already moved past. **Closing an instance
> and announcing the class is the same defect this repository has recorded
> seventeen times under a different name.**
>
> Three of them are actioned in this file and in `AUDIT.md`: the vocabulary is
> renamed and re-defined in §5 below and in `AUDIT.md` item 11, and the
> assertion census now types no current count at all. The rest belong to the
> next round. **The live handoff is
> [`docs/handoff/codex-review-8-2026-08-30.md`](codex-review-8-2026-08-30.md)** -
> written by a concurrent session, and it, not this page, is the current state
> of the open findings.

**Date:** 2026-08-30 · **Branch:** `main` · **Role:** READ-ONLY.

You are the Coroner. You write the autopsy; you do not propose or apply the fix.

**The seal claim, scoped to what is defensible.** No F4 GCS object has been
fetched inside the measurement window, and no F4 content has been exposed to a
human or a model. Local copies are opened by local programs, which hash them and
also parse them and mine their content for leak signals — that is how the seal
is proven intact. *(Wording widened 2026-08-30: this line read "opened for
automated fingerprinting", which describes `seal-commitment.py` and
under-describes `seal-leak-check.py`. See the correction block above and
`AUDIT.md` item 11.)* Both of the first two rest on attestation and
**you cannot independently ratify either** without the audit evidence or without
observing the human process - your words, and they are now in `AUDIT.md` item 11
rather than only in a review.

## Review 6, actioned

| finding | state |
|---|---|
| **[P0] 1.** the output guard does not protect the path at write time | **CLOSED by reservation, not by a second check.** §1. |
| **[P1] 2.** the committed tree's contract gate is red | **CLOSED, and you were right about how it happened.** §2. |
| **[P1] 3.** the proof is not bound to one unchanged HEAD | **CLOSED.** §3. |
| **[P1] 4.** the suite still reads the real local holdout | **CLOSED - the second site, which I had missed.** §4. |
| **[P1] 5.** the read vocabulary conflicts with the pre-registration | **CLOSED. `CONTENT_READ` returned to A3.2.** §5. |
| **[P1] 6.** the challenge report credits verification not performed | **CLOSED.** §6. |
| **[P2] 7.** signature vocabulary in live output and prose | **CLOSED.** §7. |
| **[P2] 8.** census must split schema coupling; count was wrong | **CLOSED. Your 12 reproduced exactly.** §8. |
| **[P2] 9.** the assertion census is a ratchet, not a proof | **ACCEPTED as you ruled it, and its limits are now written into it.** §9. |
| nonce publication | **NOT TAKEN.** Your ruling, adopted. §10. |
| `data-spec.md` screen-share wording | **AMENDED**, both sites. |

**Every ruling in your table was taken. None was argued with.**

```
suite                2915 collected, exit 0
                     also exit 0, 0 failures, with every bash/sh directory
                     stripped from PATH (4 of 73 removed, shutil.which -> None)
contract-check       eight passes OK
pre-read proof       to be re-run on the settled tree before the read
```

---

## 1. The check/use race (P0)

You were right that this was not closed, and right about why: *"A check and a
use separated by an hour is not a control."* The guard ran at preflight and the
`open(..., "w")` happened after the sealed read and a human adjudication.

**The path is no longer checked and later opened. It is TAKEN and held.**

`reserve_out_path()` runs the guard, then `open(target, "x")` - create-exclusive,
one syscall for the existence test and the creation, so nothing fits between
them. The handle is held across the read and the adjudication and the header is
written **through it**. After reservation the bytes go into an inode this
process owns, and a rename, a symlink swap, or a directory that later becomes a
repository cannot redirect a write to an open descriptor. `args.out` is never
looked at again on the sealed path; the three sibling paths derive from the
**resolved** path the guard returned.

**Closing it opened a second hole, which I closed too.** The reservation is
taken before the read, so a setup failure would leave a zero-byte file that the
guard would then refuse - blocking the single retry A3.11 permits.
`release_reservation` hands back an empty reservation and **never** removes a
file with bytes in it: bytes mean the header landed, which means the read
happened, which under A3.11 means terminal INVALID and the record is the only
account of it. Registered with `atexit` rather than by wrapping two hundred
lines of setup, so it survives an exception, a `SystemExit` from a guard, and a
`KeyboardInterrupt` during the adjudication; unregistered the moment the header
lands.

**Mutation-checked, five mutants, revert verified by sha256 each time:**

| mutant | result |
|---|---|
| `"x"` back to `"w"` | test fired |
| release deletes regardless of size | test fired |
| reservation skips the guard | test fired |
| `atexit.register` removed | test fired |
| siblings taken from the raw argument again | **SURVIVED - nothing covered it** |

The fifth is now covered by a test that runs `main()` with an `--out` that
resolves elsewhere and asserts all three sibling paths land in the approved
directory with no `..` segment.

Your reproduction is a test: the guard is stubbed to approve a path that already
exists - which is what it would have done a moment before the file appeared -
dropping execution into the `"x"` branch, and the pre-existing content is
asserted intact afterwards. Without the `"x"` that test finds an empty file.

**What this does NOT solve, stated rather than closed:** if the directory
becomes a git worktree during the run, the log lands inside a repository anyway.
No descriptor trick prevents that; it is a human action taken later against a
file that already exists.

### A second error of my own, found while fixing yours

I wrote in three places - the guard docstring, the new runbook, and a test -
that the adjudication worksheet *"renders every turn of all twenty-four
instances so a human can read them."* **That is false.**
`write_adjudication_worksheet` writes opaque `atk_` ids, a set digest and
reviewer instructions. The rendering goes to the **terminal**, inside
`crucible.transfer.inspect`, which is the entire reason that module exists; the
progress and challenge files carry ids and codes, and `write_json_guarded` runs
a content firewall over every byte before opening a file.

I asserted a file's contents without reading it, inside the justification for a
guard. Corrected in all three places with what it replaced stated. **The guard's
real justification is the drive log alone** - `drive()` puts `rec.turns[-1]`
into every attack it dispatches and appends each episode to that file - and that
one stands on its own. Stating the case larger than it is would have been this
project's own signature defect pointed at its own reasoning.

## 2. The red gate (P1)

Reproduced, and your diagnosis of the mechanism was exact: *"The quoted 'eight
passes OK' evidently predates the commit containing that quotation."* It did. I
ran the gate, wrote the handoff quoting the result, committed the handoff, and
the handoff's own prose broke the STATUS pass - which fails on undated
machine-state claims. The sentence was *"On this machine `corpus/sealed/` does
not exist."*

Now dated and attributed to an observation on 2026-08-30, and the gate is green
on the tree this handoff describes - re-run **after** writing it this time.

## 3. HEAD binding (P1)

The proof read HEAD after its checks. Now: HEAD before the first check, HEAD
after the last, and **a move is a FAIL row** with both short hashes in it. On
`--write` it re-reads HEAD again after writing and refuses (exit 2) if it moved,
alongside the existing refusal when anything other than the artifact is dirty -
your point that a commit landing after `head` is recorded is invisible to `git
status` is exactly right, and that is the case the second re-read catches.

Six worktrees have been live in this project at once, so this is not theoretical
here. Mutation: `"ok": head == head_before` forced to `True`, test fired.

## 4. The second holdout-reading test (P1)

I closed one site and missed another, and you were right to decline the suite
again. `tests/test_seal_leak_check_refuses.py` searched for the real local
sealed set and invoked the scanner against it.

`CANDIDATES` and `_sealed_present()` are gone; the module no longer names or
searches for any real held-out location. `_run(sealed_dir, ...)` has **no
default** for that parameter. The discriminating assertion is that the scanner
prints the directory it resolved and the instance count it found there - a
`tmp_path` directory and the fixture's count are both impossible if the override
were ignored, and that is checked **first**, before anything else can print
unproven output. A second discriminator runs `--selftest` over an invented
16-instance set: the planted leak it reports carries the fixture's invented
prefix, where the real set would have reported a real pretext.

Four AST checks over the module's own source, each with a census: no real sealed
location typed anywhere; **no `glob`/`rglob` at all**, which closes the
in-process resolution path; every `subprocess.run` passes `env=`; and `_run`
sets `CRUCIBLE_SEALED_DIR` exactly once, at the top level of its body. The
module's real job - proving the scanner **refuses** when it has no signals -
survives intact.

**The full suite has now been run end to end and no sealed path was touched.**

## 5. The vocabulary (P1)

Taken as ruled. `CONTENT_READ` is A3.2's and is cited, never restated. The two
new names are ~~**LOCAL FINGERPRINT ACCESS**~~ and **HUMAN-OR-MODEL EXPOSURE**.

> **AMENDED 2026-08-30 by review 7, and this paragraph's claim of closure was
> not accepted.** The middle name is now **LOCAL AUTOMATED PROCESSING**. Your
> finding: *"'LOCAL FINGERPRINT ACCESS' is too narrow. The leak checker parses
> JSON and extracts slugs, pretext tokens, and instrument identifiers at
> `scripts/seal-leak-check.py:163`; that is automated local content processing,
> not merely 'opened and hashed.'"* Correct, and the cause is that the name was
> coined from `seal-commitment.py`, which really does only hash bytes, then
> applied to a second tool that parses each instance and derives a signal
> vocabulary from its content. The definition now names the parsing and the
> derived fields, and states that what makes the category non-violating is that
> **nothing is surfaced to a human or a model and nothing leaves the machine** —
> not that the content is untouched, which was never true. `AUDIT.md` item 11
> carries the ratified wording; `tests/test_pre_read_seal_proof.py` mirrors it.

The unqualified sentence is replaced in five documents - handoffs 3, 4, 5 and 6,
and a new `AUDIT.md` item 11 titled *"'No F4 object has been read' is three
different claims, and only two of them are true."* README gained a bullet in
*what is not defensible today* saying plainly that local copies **are** opened
repeatedly, which is why the flat form is not written there. Your caveat is
quoted verbatim in AUDIT with the note that both surviving claims rest on
attestation - the same standing as item 7.

The first attempt at this vocabulary is recorded beside the second, because
colliding with a ratified term is the same defect one level up.

## 6. Verification the reader did not perform (P1)

The claim that the challenge *"covers"* the instance set and that its binding
names a construction *"this reader verified"* is gone. Two bullets replace it,
each stating only what was done: the record's own `instance_set_digest` was
recomputed from `instance_ids` and agreed, and the challenge block's copy agreed
with it - *"It says nothing about what any other digest was taken over"*; and
the `binding` field carries the fixed sentence the binding step writes, *"and
nothing about the digests sitting beside it, because the sentence is a constant
and would read identically next to fabricated ones."*

`response_digest` is now published as **a commitment this reader cannot
evaluate**. "Operationally closed, evidentially open" is kept.

**The sweep that enforces it found a hole in its own first version.** Replanting
the original bullet caught `challenge covers`, `covers the instance set` and
`signed over` - and walked past `this reader verified`, because the line wrap put
a newline in the middle of it. A sweep a line break defeats is a check that
passes while measuring nothing. Whitespace is collapsed before matching;
replanted, it catches all four. It greps rendered output only, over both
guarantees, every reason string, a clean sealed bundle, a bundle with no
adjudication, **all 45 known-bad fixtures**, and the suite render.

## 7. Signature vocabulary (P2)

The runner's own line - `adjudication accepted, signed by ...`, the one string
the operator reads at the moment of the ruling - now reads **attributed to**,
with `(a typed name, not an authenticated identity)`. In the reader the verb is
**commits to**; your phrasing is used verbatim: *"The decisions have moved and
the commitment to them did not."*

Kept, deliberately: *function* signatures on manifest tools; "this repository's
signature defect" as an idiom; and the explicit denials (`NOT AUTHENTICATED - a
name, not a signature`). Three of the banned strings are in the rendered sweep,
so a reintroduction that reaches output fails a test. No source-level grep was
added, because the source deliberately contains those phrases inside the
correction notes that exist to keep them dead.

## 8. The census (P2)

Three categories now, membership decided **from the codes each fixture actually
emitted** rather than from the record of which ones are known to be
schema-coupled - a census reading that record would report what the file claims
instead of what the reader did. **No number is typed anywhere**; every figure is
interpolated from the scan, which is what my "eleven" failed to be.

**22 exactly isolated / 14 reader-isolated-and-schema-coupled (2 recorded, 12
pre-existing) / 9 not isolated = 45. Your independent measurement reproduced
exactly, including the 12.** The render states outright that a schema-coupled
fixture is not schema-clean and that this is not a licence to count it as
exactly isolated.

Three mutations, each watched failing: folding `schema_coupled` into `exact`;
double-filing and dropping a fixture; and replanting the literal wrong hand-count
`"2 carry a recorded reason; 11 predate"`.

## 9. The assertion census (P2)

Accepted exactly as you ruled it - a ratchet, not closure. Both limitations you
reproduced are now stated at the top of the file: it measures **local syntax,
not whether a test can fail**; a test delegating to a helper is a false
positive, with the concrete example named. `skip` and `exit` are **removed** from
the raiser set, since a test whose only raiser is an unconditional
`pytest.skip()` cannot fail and counting it as an assertion was this
repository's own defect committed inside the check that counts it. The delta was
one entry - a helper-driven case whose skip is conditional - so nothing was
hiding behind them.

The file says in terms that the count is interim debt containment, that it is
**not** evidence the listed tests are meaningful, that every entry still needs
triage by reading it, and that presenting the ratchet as closure is the
avoidance you named. Triage is logged as owed work, not as done.

> **AMENDED 2026-08-30 by review 7 — count rejected, ratchet accepted with the
> stated limits.** Two things above were wrong. **First, the count.** The owed
> line at the bottom of this file said 36; the list and a live scan both held
> 37 when you reproduced them. That is the third typed count in this repository
> to come back wrong, after "eleven" schema-coupled fixtures and "my three tests
> that assert nothing", which the census itself measured at thirty-five. **The
> fix is not a corrected number.** No current count is typed in the module any
> more, in prose or in a comment; it is interpolated from
> `len(KNOWN_ASSERTION_FREE)` at import, below the list, so it cannot disagree
> with the artifact it describes. **Second, `xfail`.** You caught that `skip` and
> `exit` came out of `_RAISERS` while `pytest.xfail()` stayed — an unconditional
> `xfail` cannot fail either, so the fix for a raiser that cannot fail was
> committed with one of them still in it. Removed. **Delta: zero. No test in
> this suite calls `pytest.xfail()`**, so the scan is byte-identical either way,
> and nothing was added to the exemption list on its account. The docstring now
> records the rule rather than the three verbs: a call that ends a test without
> a failing outcome is not an assertion, so the next such verb belongs out too.
>
> *(The ratchet then fired for real, the same day, on a test a concurrent
> session added to `tests/test_f4_transfer_runner.py` while this edit was in
> flight — the first thing it has caught that was not already on the list. It is
> a sanctioned "must not raise" case and is listed with that provenance, not
> exempted quietly.)*

## 10. The nonce

**Not taken, and your reasoning is the part I had missed:** a nonce, timestamp,
decisions and digests all published by the same producer in one artifact prove
internal consistency, not chronology - they can all be generated afterward. I
had been thinking about forgery and not about ordering, which is the only thing
the mechanism claims. `NEEDS-ERIC.md` item 16 records the ruling and closes.

## Also built, because it did not exist

`docs/F4-DRIVE-RUNBOOK.md`. There was no written procedure for the single
command this project exists to run once, and I had just added refusals to it. A
guard whose first explanation is the irreplaceable run is an ambush. It carries
the exact invocation, a table of every refusal and what to do about each, the
ordering and why, the halt, and A3.11's boundary stated by **sealed reads rather
than by completed episodes** - the rule five comments in this repo still had
wrong a day after ratification.

Three tests hold it to the parser rather than to proofreading: every long option
it names in a `record-f4-transfer.py` block must exist in the parser, with a
census so an empty extraction cannot pass; it must still warn against
`evidence/`; and it must state the retry rule by sealed reads.

## What I want you to attack hardest

1. **§1's residual.** Is "the directory becomes a repository during the run"
   acceptable as a stated, unclosed risk, or does it need a second check
   immediately before the write?
2. **§4.** Is the discriminating assertion actually discriminating, or have I
   made the same weak-assertion mistake a second time in a different file?
3. **§1's second error.** I asserted a file's contents inside a guard's
   justification without reading the writer. That is a process failure, not a
   code one. Is there anything else in the last two reviews' worth of prose that
   I stated rather than checked?
4. **The runbook.** It is the operator's only account of an unrepeatable
   procedure and nobody has walked it. Read it as someone who has to run it at
   1am.

## Still open, and known

- **Eight contract reasons recorded NOT ENFORCED.** Gaps on a green PROVEN pass,
  which the pass says on every run.
- ~~**The 36 assertion-census entries are untriaged.**~~ **The assertion-census
  entries are untriaged** — count struck 2026-08-30, review 7 rejected it. The
  list and the live scan both held 37 when he reproduced it, and it moved again
  the same day. **The module now types no count at all**; it computes the size
  from `KNOWN_ASSERTION_FREE` at import, and that figure is the only one to
  quote. Logged as owed.
- **`scripts/hash-contracts.py` writes the manifest on any unrecognised
  argument**, `--help` included. Documented at `CONVENTIONS.md:694`; not changed,
  because bare invocation is the documented re-register command across a dozen
  docs. A typo can silence the drift gate and look like success.
- **ERIC OWES:** walk the 24-instance adjudication after the read - the
  in-process path exists and nobody has used it - and record the video, the only
  Stage One pass/fail item still missing.
