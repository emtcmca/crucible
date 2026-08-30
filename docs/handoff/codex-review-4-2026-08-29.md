# Codex review 4 - handoff

**Date:** 2026-08-29 late · **Branch:** `main` · **Role:** READ-ONLY.

You are the Coroner. You write the autopsy; you do not propose or apply the fix.
Everything below happened with the seal shut. **No F4 object has been read.**

## Your third verdict is fully actioned

| finding | state |
|---|---|
| Outcome B unreachable | **CLOSED.** A3.10 appended, seal-shut, row NOT deleted. Both your arguments reproduced independently and are now executable checks. |
| adjudication gate never invoked | **CLOSED.** `await_adjudication` sits between the read and the model. |
| segmented identifier grammar | **CLOSED.** Your exact three fragments reproduced at 0 defects, now 6. |
| calibration/run-window race | **IN FLIGHT as you read this.** Reproduced; fix being written. |
| C11 negative fixture proves nothing | **CLOSED**, and it was worse than you found - see below. |
| A3.9 non-executable | **OPEN. Unstarted.** See the question at the end. |
| stale registration prose | **CLOSED.** |
| suite not reproducible | **CLOSED and measured.** |

Also closed since: `validate_instance` on the sealed path, assembly-lock
ordering, and the hardcoded stand-in label.

## The two things I most want an outside read on

### 1. The grammar residuals, which are declared rather than closed

The fix constrains toward the measured legitimate value space rather than away
from suspicious strings: the longest alphabetic token in 125 real corpus
identifier values is FOUR characters and your shortest fragment was six, so the
grammar admits at most two four-character tokens. Then a 24-token vocabulary
bound across the whole bundle (corpus uses 9, real run 7), and a 2048-letter
budget over DISTINCT values.

**Four residuals are stated in the commit rather than implied closed**, and I
want your judgement on whether they are acceptable to publish behind:

1. **24 tokens is itself an alphabet.** Nothing stops a producer choosing 24
   meaningful tokens and encoding in the ORDER they appear across calls. At
   ~200 calls that is on the order of a hundred characters to a determined
   decoder.
2. **The email grammar is untouched and is now the widest per-value channel.**
   `please.send.money@evil.invalid` publishes verbatim. The corpus maxes out at
   two local segments so tightening is available and was DELIBERATELY NOT TAKEN:
   trading a stated residual for an unquantified risk of digesting the F4
   destinations, the night before a run that happens once, looked like the wrong
   trade. Tell me if that is wrong. It is a one-line change.
3. 2048 letters is ~340 words against a real run's projected 267. 7.7x headroom,
   chosen for the unrepeatable run rather than for tightness.
4. Digits are unbounded for content and no per-value rule can separate an
   encoded payload from an order number.

### 2. Did the repairs introduce more instances?

**Two did, and they were caught by the repair's own mutation pass and reported
rather than fixed quietly** - instances sixteen and seventeen, both tests of
mine that stayed green under mutation.

**A third was found afterwards and is the one worth your attention**, because it
is a new SHAPE. The shell-free fix landed, and five tests kept skipping with a
reason ending *"the shell-free fix belongs in infra/verify_iam.py"* - a premise
repaired an hour earlier in the same session. The guard asked
`shutil.which("bash")`, which was a correct proxy for exactly one day. **A guard
on a dependency that probes the WORLD rather than the DEPENDENCY goes stale
silently and keeps reporting green.** I have fixed that instance. I have not
swept for others, and I suspect there are others.

## What changed, with the commits

`9a243cc` adjudication gate + A3.10 · `bec4024` grammar + contract gate + shell
· `a713fb9` shell-free reader + recording deck · `99af969` seal label ·
`6120b9e` sealed validation + ordering. Full diff: `git diff a0c9971..HEAD`.

## Findings you should see, that came out of your C11 item

Making the gate prove each promised reason turned up far more than C11. **62
declared reasons across ten known-bad fixtures: 45 proven by a named schema
failure, 9 by reader code, 8 NOT ENFORCED AT ALL.**

- **C3a's fixture disables its own first defect.** It sets `fail_closed: true`
  for reason 1, which is precisely the escape clause that stops reason 0's
  conditional from reaching its `then`.
- **C3b** - the fixture itself calls one of its defects *"the leak that looks
  exactly like success"*, and `max_predictive_accuracy` is an unbounded number.
- **C9** fails for a third undeclared reason.
- **C4** promises two defects the fixture never instantiates.
- **C1** states one failure twice as two reasons.

The eight unenforced ones carry the constraint that WOULD enforce them and the
triple it would produce, and the gate asserts that triple does not fire today -
so closing a gap turns the record stale and the gate red.

## Measured, not asserted

- Suite: 2738 collected, exit 0.
- **With every `bash.exe`/`sh.exe` directory stripped from PATH: 2738 collect,
  no collection errors, exit 0, two skips.** Previously four modules died at
  collection. `RealGate` can now be constructed without a shell, which it could
  not before - that was production, not test scaffolding.
- `contract-check.py`: eight passes, `PROVEN` among them.

## THE QUESTION I ACTUALLY NEED ANSWERED

**A3.9 is open, unstarted, and I do not think it can be built well in the time
left.** Your finding stands in full: the durable header is written after the
sealed read returns, the crash handler wraps `drive()` and not the read, the
counter assertions cover one window rather than an interrupted-plus-retry pair,
duplicate client reads are categorically rejected, and "a halt during the sealed
read" is broader than a transport interruption.

So the amendment describes evidence the runner cannot produce and a retry the
accounting cannot accept.

**Is the honest move to NARROW A3.9 before the unseal rather than to build the
machinery?** Concretely: amend it to say a partial sealed read is VOID with NO
retry, which the runner can actually honour today, and record the lost
allowance as a cost rather than shipping a permission the code cannot execute.

An amendment that promises a retry we cannot perform is worse than no amendment,
and it would be discovered at the only moment it matters. But narrowing it costs
the run its only recovery from a network hiccup. **I would rather you rule on
that than have me choose it under deadline.**

Secondary: the bundle still has no top-level `adjudication` block. Outcome C
requires those counts. Design review welcome on the shape before I build it.

## Standing constraints

- **Never read anything under `corpus/sealed/` or `gs://crucible-sealed-x7/families/`.**
- No `gcloud` reads against the sealed bucket.
- Read-only. Report; do not patch.
