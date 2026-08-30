# The sealed F4 drive - operator runbook

**This command runs once.** There is no second attempt except in the one narrow
case amendment A3.11 names, and everything below exists so that a decision is
never made for the first time at the moment it costs the most.

Written 2026-08-30, after an adversarial review found that the drive's output
path could be redirected or truncated between the guard and the write. Closing
that added refusals the operator had never seen, and there was no document
telling them what any of them meant. **A guard whose first explanation is the
irreplaceable run is not a guard, it is an ambush.**

Authority: `docs/proof/f4-unseal-preregistration-2026-08-25.md` governs the
measurement. This file governs the keystrokes. Where they disagree the
pre-registration wins and this file is the defect.

---

## Before anything

```
python scripts/pre-read-seal-proof.py
```

It must print `VERDICT  PASS`. It refuses on a dirty tree, on a commitment that
no longer recomputes, on a leak in a tracked file, and on HEAD moving while its
own checks run. **A failing proof means the seal does not open today.** Do not
argue with it and do not re-run it hoping for a different answer - every one of
its refusals is about a condition that would make the run unreadable afterwards.

Then commit the artifact:

```
python scripts/pre-read-seal-proof.py --write
```

`--write` refuses if anything other than the artifact it just wrote is dirty,
and if HEAD moved while it was writing.

**Commit that file, and only that file.** Its commit then has the recorded
`head` as its parent, and that parent relationship is the whole of its claim.

**This is not a convention any more - the drive enforces it.** Before the read,
`record-f4-transfer.py` refuses with `E_PROOF_NOT_BOUND` unless the newest
proof records `PASS`, the tree is clean, and the proof's `head` is a parent of
the current `HEAD`. A reviewer showed why: a commit landed between a proof and
a drive during review 7, leaving the tree clean and the proof describing a
commit that was no longer the one about to be driven. If you commit anything
else after the proof, re-run the proof.

## The command

**This machine runs PowerShell.** The first version of this section used Bash
`\` line continuations, which a reviewer pointed out do not work when pasted
into PowerShell - so the "exact invocation" was one that fails on the only
machine that will ever run it. Set the three paths first, then run one line;
that is also how you get to re-read them before committing to anything.

```powershell
$Stamp  = Get-Date -Format "yyyy-MM-dd-HHmm"
$Run    = "$env:USERPROFILE\crucible-f4\$Stamp"
New-Item -ItemType Directory -Force -Path $Run | Out-Null

$Names  = "$Run\object-names.txt"   # you create this; see below
$Adj    = "$Run\adjudication.json"
$Out    = "$Run\drive.jsonl"        # must NOT exist yet

python scripts/record-f4-transfer.py --phase drive --sealed --i-am-opening-the-seal --live --object-names $Names --adjudication $Adj --out $Out
```

`$env:USERPROFILE\crucible-f4\...` is chosen deliberately: outside `C:\dev`,
so outside every git work tree, and not under OneDrive. The guard will refuse
anything else - see the refusal table below - and `$Out` must not exist,
because the run reserves it.

**The three paths are yours to fill and the command cannot supply them.**

| variable | what it is |
|---|---|
| `$Names` | the sealed object-name list, one per line. **You write this file.** It is the declared read set; the preflight asserts against it and it cannot be derived. |
| `$Adj` | where the ruling record is written. It does not exist beforehand - the path only has to be known before the read, so the halt has somewhere to wait. |
| `$Out` | the drive log. Must not exist. |

`--floor` and `--expect-instances` are pre-registered and may not be passed.
`--limit` is refused: a partial holdout is not a smaller experiment, it is a
different one with an undeclared denominator. `--live` is mandatory, because a
replay cannot observe an agent that, refused one route, tries another.

## Where `--out` may point, and why it is fussy

**Outside every git work tree, on a path that does not exist yet.**

The drive log carries the held-out instructions **verbatim** - every episode it
appends contains the instruction that was dispatched. That is what this guard
is for.

Three more files are derived from the same base - the adjudication worksheet,
the progress file and the challenge file - and none of them carries instruction
text. They hold opaque `atk_` ids, digests and reason codes, behind a content
firewall that refuses to write a file containing instance strings. The instances
themselves are rendered to your **terminal** during the review, never to disk.

A path is refused if:

| refusal | meaning | what to do |
|---|---|---|
| **already exists** | the drive opens its output for writing, which truncates. On a one-shot that is destruction, and it is one recalled shell command away | choose a path that does not exist, or move the old record yourself. **Do not delete a record with bytes in it** |
| **inside the git work tree at `<dir>`** | any ancestor holds a `.git`, so the log would land under version control. This catches this repository, every worktree of it, and any clone. A `.gitignore` entry is not the control | write it somewhere outside every repository |
| **under a cloud-sync root** | sealed material there is uploaded to a third party the moment it lands, and deleting it afterwards does not un-upload it | pick a local path |
| **came into existence between the check and the claim** | something created the path after it was approved. **Nothing was truncated - the refusal is the protection working** | choose a different path |

`E_PROOF_NOT_BOUND` is the other refusal you may meet before the read, and it
is about the repository rather than the path:

| refusal | meaning | what to do |
|---|---|---|
| **no pre-read seal proof exists** | nothing under `docs/proof/` proves this tree | run the proof, commit its artifact, re-run |
| **records verdict FAIL** | a failing proof on disk is a record of a refusal, not a licence | fix what it refused; the seal does not open today |
| **the working tree has N modified path(s)** | the proof's claims are about a commit and this tree is not one | commit or stash, then re-run the proof |
| **does not describe the commit about to be driven** | something was committed after the proof | re-run the proof and commit only its artifact |

A working shape, on this machine: a dated directory under the user profile,
outside `C:\dev` entirely. **Do not use `evidence/`.** It is inside the
repository and gitignored, and a gitignore entry is the control this project has
already ruled is not a boundary.

## What happens, in order

1. The pre-registered parameters are checked. Cheapest thing that can be wrong.
2. **The output path is approved and CLAIMED** - created exclusively, and the
   handle is held from here to the end. Nothing that happens to the name
   afterwards can redirect the write.
3. The objective set, the hash locks and the arm policies load. All of these
   read files, all can fail, and none needs the holdout - so all of them happen
   **before** the seal is touched. A failure here costs nothing.
4. **The sealed read.** From this point the attempt is spent.
5. **The run halts and waits for you.** See below.
6. The model is built and the two arms are driven.

Steps 3 through 5 are ordered deliberately. Anything that can fail without the
holdout fails before it.

## The halt, which is yours

The run stops between the read and the first model call and will not continue
until every one of the twenty-four instances has been ruled on. The review is
**in process** - each instance is rendered to your terminal in order with its
frozen context, you answer with ratified codes only, and no instance content is
written to disk.

- A nonce is minted **after** the read and the record must answer it, so a
  decision file written in advance cannot satisfy the gate.
- **You may stop partway, and this is now true rather than aspirational.**
  Type `pause` at any code prompt. The review stops, tells you how many of how
  many are done, and waits at a `resume or abandon>` prompt - so you can
  actually step away. `resume` carries on where you were; `abandon` stops for
  good and the ruling is not recorded.
  - It resumes **in this process**, on the same nonce minted at the read. That
    is the only way it can work: a new invocation would have to read the
    holdout again and would mint a nonce the earlier progress cannot answer.
    **Do not close the terminal.**
  - A typo is neither, and is re-asked. An input that answers nothing five
    times over - a closed stdin, a script - is refused rather than spun on.
  - Until 2026-08-30 this claim was false: `pause` raised, nothing caught it,
    and the process exited. A reviewer found it by typing `pause` in the
    rehearsal.
- The name you give is **attribution, not authentication**. Nothing signs it.
  It is there so the ruling has an owner, and it must not be a component name -
  the runner refuses its own name, which is the point.

### Rehearse it first. Not on the day.

```powershell
python scripts/rehearse-adjudication.py --count 3
```

Rehearse the pause too - it is the part most likely to be needed and least
likely to have been tried:

```powershell
python scripts/rehearse-adjudication.py --count 3 --pause-drill
```

This walks the REAL review loop - the same `inspect.adjudicate`, the same
rendering, the same ratified codes, the same post-read challenge and the same
self-checks - against a **training** family. It reads no sealed object and
spends no attempt, and it cannot be pointed at the holdout: `--family F4` is
refused by the runner's own loader, and this script declares no `--sealed` flag
to begin with.

Do a full pass at least once before the day. Reading `inspect.py` is not the
same as having done the thing, and the failure this prevents is meeting the
loop for the first time with the holdout already in memory and the attempt
already spent.

It keeps nothing unless you pass `--keep <dir>`, and what that writes is an
envelope rather than a record. A rehearsal ruling cannot satisfy the real gate
in any case: the gate derives its id set from the instances that came off the
wire, so a record over stand-in ids will not load against them.

## When something goes wrong

Amendment A3.11 governs, and the boundary is **whether any sealed object was
read**, not how far the run got:

- **Zero sealed reads.** VOID, and **one retry remains**. The reservation from
  the failed attempt is handed back automatically when it is empty, so the
  retry is not blocked by it.
- **One or more sealed reads.** Terminal **INVALID**. No retry, at any stage.
  **A record is always left, and you keep it.** Two mechanisms cover different
  halves of the run and a reviewer found the gap between them on 2026-08-30:

  - a failure *while driving* writes a `crash` row through the open handle
    before the exception propagates;
  - a failure *anywhere between the read and the header* - which is where the
    adjudication sits, and so where an EOF, a declined signature, a provider
    validation failure or a model that will not construct all land - writes a
    `terminal` row naming the stage it reached. That half did not exist until
    2026-08-30, and worse, the empty file was being DELETED, which erased the
    attempt and left a path that looked available for a retry.

  Either way the record states what happened and does **not** rule on it.
  Whether the run is VOID or INVALID is the pre-registration applied to the
  evidence, not a verdict the stopping process writes about itself. The count
  of completed episodes does not change the ruling.

A record with bytes in it is evidence. Nothing in this runbook ever asks you to
delete one.

## After the drive

```
python scripts/record-f4-transfer.py --phase assemble --from <the drive log> --out <bundle path>
```

Assemble may write into the repository - the bundle is the artifact this project
exists to publish, and the guard above deliberately does not apply to it.
