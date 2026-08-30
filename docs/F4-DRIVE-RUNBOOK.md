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

**Commit that file, and only that file.** The drive checks THREE properties,
not one, and the instruction above satisfies all three at once:

| the drive requires | why |
|---|---|
| HEAD has **exactly one parent** | any second parent imports a tree the proof never scanned, through a side the check does not examine. Merges are the loudest case, not the whole of it |
| that parent **is** the proven commit | equality, not membership |
| the commit changes **that artifact and nothing else** | a single-parent commit can still carry the proof PLUS code edited after `--write` returned, and everything under it would be unscanned |

The third is the proof document's own claim about itself - `git show --stat` on
its commit lists only that file - verified from the other end instead of
trusted. **This section used to call the parent relationship "the whole of its
claim", which was true when it was written and became false when the other two
landed.**

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

## The ancestry residual is yours, and it is not closed by code

Read this once before you choose the directory, because the guard cannot do
this part for you and the runbook is the only place that says so.

**The code checks ancestry twice, and neither check is a lock.** Verified
2026-08-30 against `scripts/record-f4-transfer.py`:

1. `assert_out_path_is_offtree` runs when the path is approved, before the
   seal is touched. It refuses an existing target, any path with a `.git`
   ancestor, and any path naming a cloud-sync root.
2. `assert_directory_still_offtree` runs again immediately before the first
   content-bearing byte, on the reserved path. It re-runs the two ancestry
   refusals only - the existence refusal cannot be re-run, because after the
   reservation the target always exists.

The second check narrows an interval. It does not close it. In the reviewer's
own words:

The second check narrows the interval in which a repository appearing before
the first write goes unnoticed. It does not prevent the ancestor from becoming
a repository or synchronized location **after the header lands, during the
drive, or while the completed file remains there.** The held file handle
protects write destination identity. It does not preserve the directory's
security classification. **This is acceptable only as an explicitly owned
operational assumption using an isolated directory with no concurrent mutation
- not as a code-enforced no-exposure guarantee.**

**The held handle protects where the bytes go, not what the directory
becomes.** `open(..., "x")` creates the file and holds the descriptor across
the read, the adjudication and the whole drive, so a rename, a symlink swap or
a junction laid over the name afterwards cannot redirect a single byte: the
write goes to the inode reserved before the seal was touched. That is the
entire guarantee. It says nothing about the classification of the directory
the inode lives in. Run `git init` in a parent after the header lands, drop the
folder into a sync root while the drive is running, or move the finished log
into one a week later, and the sealed instructions are in version control or at
a vendor - and no file descriptor was ever in a position to stop it.

**The exposure window does not close when the process exits.** The drive log
carries the held-out instructions verbatim and stays sealed material for as
long as the file exists. The last check the code will ever run on that
directory happens before the first episode is written. Everything after that
is you.

### What you are agreeing to own

By choosing the directory you take these four, explicitly:

1. **Isolation.** A directory created for this run and used by nothing else.
   No editor project root, no scratch folder somebody else writes to, no
   backup agent walking it.
2. **Local disk.** Not a network share, not a removable volume, not a folder
   any sync client watches. Cloud sync uploads the file the moment it lands,
   and deleting it afterwards does not un-upload it.
3. **No classification change, during or after.** You do not run `git init`
   there, you do not open the parent as a repository in an editor that might,
   and you do not add the folder to a sync root - not during the drive, and not
   after the run finishes.
4. **No relocation.** You do not move or copy the directory while the run is
   in progress. Move the finished record later, deliberately, to somewhere you
   have applied the same three rules.

### A concrete safe location on this machine

The command block above already builds one:

```powershell
$Stamp = Get-Date -Format "yyyy-MM-dd-HHmm"
$Run   = "$env:USERPROFILE\crucible-f4\$Stamp"
New-Item -ItemType Directory -Force -Path $Run | Out-Null
```

That resolves to something like `C:\Users\tetzl\crucible-f4\2026-08-30-0142`.
What makes it safe is four properties, and you should be able to name all four
before you press enter:

- **It is on the local `C:` volume**, so nothing uploads it and nothing
  detaches with it.
- **It is outside `C:\dev`**, so it is outside this repository, outside every
  worktree of it including `crucible-wt-SEAL`, and outside every other clone on
  the machine. The ancestry refusal fires on a `.git` in any parent, so this
  keeps you clear of it by construction rather than by luck.
- **It is outside both OneDrive roots** - `C:\Users\tetzl\OneDrive` and
  `C:\Users\tetzl\OneDrive - p2phoamgt.com`. Note the trap the guard catches
  only by accident of naming: with OneDrive folder redirection switched on,
  `Documents`, `Desktop` and `Pictures` physically live under the OneDrive
  root, so `%USERPROFILE%\Documents` is a sync root wearing an innocent name.
  The guard resolves the real path and refuses it. Do not rely on that - just
  do not put it there.
- **It is stamped and fresh per run**, so nothing else has any reason to be in
  it, which is what makes the isolation assumption in point 1 above credible
  rather than hopeful.

## What happens, in order

1. The pre-registered parameters are checked. Cheapest thing that can be wrong.
2. **The output path is approved and CLAIMED** - created exclusively, and the
   handle is held from here to the end. Nothing that happens to the name
   afterwards can redirect the write. It can still change what the directory
   holding it counts as - see "The ancestry residual is yours" above, which is
   the one thing in this run you own rather than the code.
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
  Verified 2026-08-30 against `crucible/transfer/inspect.py`. Type `pause` at
  any code prompt. The review stops, tells you how many of how many are done,
  and waits at a `resume or abandon>` prompt - so you can actually step away.
  `resume` carries on where you were; `abandon` stops for good and nothing is
  recorded.
  - **The same word means different things at the two prompts, and this is the
    one place to be awake.** At a code prompt, `pause` `stop` `quit` `q` `exit`
    all pause. At the `resume or abandon>` prompt, `stop` `quit` `q` `exit`
    `abort` `n` `no` all **abandon**, which is terminal. To carry on, type
    `resume` - or `continue`, `carry on`, `go`, `y`, `yes`. **`r` is not a
    resume word**; one prompt earlier it means "show me that instance again",
    and a letter with two meanings is how a resume becomes an abandon.
  - On resume it prints how many of how many were already ruled on in this
    read, and **it does not show those instances again**. You pick up at the
    next unruled one.
  - It resumes **in this process**, on the same nonce minted at the read. That
    is the only way it can work: a new invocation would have to read the
    holdout again and would mint a nonce the earlier progress cannot answer.
    **Do not close the terminal.**
  - A typo is neither `resume` nor `abandon`, and is re-asked - but it counts.
    Five unrecognised answers in a row end the review with
    `E_RESUME_UNANSWERED`, because a prompt nobody can answer would otherwise
    hold an unrepeatable read open forever. A genuinely closed stdin does not
    wait for five: it ends immediately with `E_REVIEW_INPUT_EXHAUSTED`.
  - **Declining is not pausing.** If you reach the summary and then refuse at
    the `Type ACCEPT to commit to this adjudication>` prompt, that is terminal
    - the review does not re-open, and nothing is written. Pausing is the
    reversible one.
  - Until 2026-08-30 this claim was false: `pause` raised, nothing caught it,
    and the process exited. A reviewer found it by typing `pause` in the
    rehearsal.
- **A resumed ruling that disagrees with one already on record is REFUSED.**
  Landed 2026-08-30 in `crucible/transfer/inspect.py`; this bullet describes
  what the module does, not what it is going to do.

  - A resumed ruling naming an instance outside the set under review is
    refused with `E_RESUME_WRONG_SET`.
  - A resumed ruling naming an instance already on record, carrying
    **different** codes, stops the review with `E_RESUME_CONFLICT`. It names
    the instance id and both code sets and never quotes instance content. The
    two sources disagree about one instance and you decide which is right -
    the process is asking, not overruling.
  - Re-submitting the **same** ruling is legal and keeps the RECORDED tuple.
    Codes are compared as **sets**, so agreeing with yourself in a different
    order is still agreeing. This matters more than it looks: every ordinary
    pause re-submits every ruling already made, because `adjudicate` hands
    `paused.decided` straight back as `resume_from`. An order-sensitive
    comparison would have refused an operator who agreed with themselves, at
    the cost of a read.

  **This bullet said the opposite until 2026-08-30.** Superseded text, struck
  rather than deleted: ~~the in-memory value is re-validated and then
  overwrites the stored one, silently~~ / ~~the implementation has not caught
  up~~. It had. For a one-shot procedure a stale warning is not a
  documentation defect, it is an operational one: it teaches the operator to
  expect a silent overwrite and to distrust a refusal that is working
  correctly.
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

Amendment A3.11 governs. Its boundary is the number of sealed CONTENT reads -
zero is VOID and retryable once, one or more is terminal INVALID with no retry
at any stage - and **not** how far the run got.

**The record states facts. The pre-registration applies the ruling to them.**
Nothing the stopping process writes about itself is a verdict, and you should
not read one out of it.

### Superseded on 2026-08-30, and left visible

The paragraph above used to end: *"Either way the record states what happened
and does not rule on it."* That was true of the sentence and false of the
record. The record it described carried a field named `ruling`, whose text
read *"A3.11: one or more sealed reads makes the attempt terminal INVALID, at
any stage, with no retry"* - a verdict, in a field introduced by a claim that
no verdict was being given. A reviewer found the contradiction inside one
dictionary.

The same record carried a single boolean, `sealed_read_completed: true`. That
flag is set **before** the download is attempted, deliberately, so it read
`completed` on an attempt where the first object failed and nothing ever
arrived - stating the wrong side of the one boundary A3.11 turns on.

Both are replaced, in `scripts/record-f4-transfer.py` as of 2026-08-30. The
old strings are quoted here rather than deleted, because if you are holding an
older record you need to know what its words were worth.

### The three facts the record carries

The terminal record distinguishes three things that were one boolean until
2026-08-30. They are not interchangeable:

| fact | what it attests | what it does NOT attest |
|---|---|---|
| **read attempted** | the downloader was about to be called | that any object was fetched |
| **read returned** | the download call returned and objects are in the process's memory | how many objects, or that the audit log agrees |
| **run completed** | the footer is durable and the drive returned cleanly | nothing further; this one says what it means |

**A conservative flag set BEFORE the read is not evidence that a read
occurred.** `read attempted` is set early on purpose: it is the reason a spent
attempt's reservation is never deleted, and buying that protection means the
flag is also true in the cases where nothing came back at all. Treat it as
"deletion is now refused", never as "the holdout was read".

`run completed` exists for a defect found the same day: without it the exit
hook could not tell a run that stopped from a run that finished, and stamped a
terminal row onto a clean drive - `header`, `footer`, `terminal`, with the last
row contradicting the one above it.

### The authoritative instrument is the holdout counter, not the runner's flag

A3.11 turns on sealed CONTENT reads, and those are counted in the Cloud
Logging data-access record for the sealed bucket - the same counter the run
itself asserts against, and the pre-registered instrument. Read it:

**$Since is `audit_window.opened_at` from the drive log**, and it is carried
by BOTH the header and the terminal record, so it survives a failure at any
stage. Copy it; do not reconstruct it.

```powershell
# Read it out of whichever record the run left behind. Angle-bracket
# placeholders are NOT usable here: PowerShell parses `<` as a redirection
# operator and the line fails on paste, which is how this block was
# originally written.
$Row    = Get-Content $Out | ForEach-Object { $_ | ConvertFrom-Json } |
          Where-Object { $_.audit_window } | Select-Object -First 1
$Since  = $Row.audit_window.opened_at
python scripts/probe-g7-g8.py --holdout-since $Since
```

**That command writes into `docs/proof/`, which is committed to a PUBLIC
repository, and sealed object names are redacted out of it by default.** Each
name becomes a stable `sha256-8:` digest, so the record still says how many
distinct objects were touched and an auditor holding the bucket can match every
line to an object - it just does not print the slug, which is what describes
the attack.

**This is a live disclosure question and it is not settled.** The
pre-registration requires the failure record to be audit-recoverable - *"what
was read, when, by which identity, how far the run got, and where it
stopped"* - and the runner refuses to publish the sealed object names on the
grounds that they describe each attack's pattern. Those two are in tension the
moment a terminal failure has to be published.

`--reveal-sealed-names` writes them verbatim. **Do not pass it without a
recorded ruling.** The question, the two defensible readings, and what each
costs are in `docs/design/DECISION-recovery-disclosure-2026-08-30.md`. The
default withholds, so that the choice is made deliberately rather than by
whichever way the script happened to be written.

**Do NOT substitute either of the two timestamps that look like it.** Both are
wrong, in opposite directions, and each breaks A3.11 the other way:

| tempting substitute | what it does |
|---|---|
| the time the process started | precedes the calibration canary, so the canary's own read falls inside the window. A clean attempt counts one read and **forfeits the retry** A3.11 permits |
| the header's `driven_at` | stamped **after** the sealed read and after the adjudication, so the window opens after the thing it measures. A one-or-more attempt reads as zero and **manufactures a retry** that is not allowed. It also does not exist at all if the run stopped before the header |

**This section named `driven_at` as the instant the attempt began until
2026-08-30.** It is not: the run's audit window opens strictly after the
calibration and long before the header is written. The record now carries the
window itself for exactly this reason.

Read the tally it prints, not its exit code. Two cautions, each of which
changes what the number means:

- **One object read emits more than one granted entry.** A metadata fetch and
  a media download are both `storage.objects.get`. The count is granted audit
  entries, not objects. That is sufficient for A3.11, which asks zero or
  nonzero, and it is wrong for any per-object arithmetic.
- **The window is yours to set.** Start it at the attempt. The default floor
  covers everything the audit log can speak to, which includes every earlier
  read of that bucket.

The probe writes its report under `docs/proof/`, inside this repository. That
is allowed and deliberate: it carries counts, principals and methods, and no
instance content.

### Then apply the amendment yourself

- **Zero sealed reads.** VOID, and **one retry remains**. An empty reservation
  is handed back automatically when the read was never attempted, so the retry
  is not refused by the guard that protects it.
- **One or more sealed reads.** Terminal **INVALID**. No retry, at any stage,
  whether the failure landed in the read, in validation, in the adjudication,
  in model setup or in scoring. Publish the failure record. **No rate and no
  transfer conclusion of any kind may be reported from it.**

The count of completed episodes does not move that boundary in either
direction.

### A record is always left, and you keep it

Two mechanisms cover different halves of the run, and a reviewer found the gap
between them on 2026-08-30:

- a failure *while driving* writes a `crash` row through the open handle before
  the exception propagates;
- a failure *anywhere between the read and the header* - which is where the
  adjudication sits, and so where an EOF, a declined commitment, a provider
  validation failure or a model that will not construct all land - writes a
  `terminal` row naming the stage it reached. That half was added 2026-08-30;
  before it, the empty file was being DELETED, which erased a spent attempt and
  left a path that looked available for a retry that is not allowed.

A record with bytes in it is evidence. Nothing in this runbook ever asks you to
delete one.

## After the drive

```
python scripts/record-f4-transfer.py --phase assemble --from <the drive log> --out <bundle path>
```

Assemble may write into the repository - the bundle is the artifact this project
exists to publish, and the guard above deliberately does not apply to it.
