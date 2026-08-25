# G7 UNEVALUABLE: what actually happened, and what is still broken

**Written 2026-08-25. Diagnosis and plan only. No GCP mutation was performed.**
Every gcloud call below is `list`, `get-iam-policy`, `describe`, or `logging read`.

---

## 0. The premise this investigation was given is FALSE, and the correction matters more than the repair

The brief said G7 reports UNEVALUABLE **on every one of 60 live runs**. It does not.

`UNEVALUABLE` appears in **exactly one file** in the entire batch evidence directory, and
that file is a console capture, not a record:

```
$ grep -rl "UNEVALUABLE" evidence/batch-night-2026-08-25/
./run-10.console.txt
```

Counted per run, the G7 block is printed in one console log out of sixty:

```
$ for f in run-*.console.txt; do echo "$f g7a=$(grep -c G7a $f)"; done
run-01.console.txt g7a=0
...
run-10.console.txt g7a=4      <- the only one
...
run-60.console.txt g7a=0
```

The G7 findings do not live in the console. They live in `summary.gate.reports` inside each
campaign record. Aggregated across all 60 records:

```
files with G7a: 52          (8 runs never reached the gate with a candidate)
95 gate calls, 16 assertions each, 1520 assertions total

95 ('G8',      'crucible-gate holds objectCreator on gs://crucible-policies-x7',        'PASS')
95 ('G8',      'crucible-gate holds NO overwrite/delete role on gs://crucible-policies-x7','PASS')
95 ('G8',      'crucible-armorer holds NO storage role on gs://crucible-policies-x7',   'PASS')
95 ('G8',      'policies retention EXISTS and is NOT locked',                           'PASS')
95 ('G8',      'policies object versioning is ON',                                      'PASS')
95 ('G8',      'UBLA on and PAP enforced: gs://crucible-policies-x7',                   'PASS')
95 ('G7b',     'crucible-armorer holds NOTHING on gs://crucible-sealed-x7',             'PASS')
95 ('G7b',     'crucible-red holds NOTHING on gs://crucible-sealed-x7',                 'PASS')
95 ('G7b',     'crucible-armorer holds no project-level storage/bigquery role',         'PASS')
95 ('G7b2/G8', 'no CRUCIBLE identity holds a project-level BASIC role',                 'PASS')
95 ('G7',      'UBLA on and PAP enforced: gs://crucible-sealed-x7',                     'PASS')
95 ('G7a',     'impersonation probe: crucible-sealed-eval (allow)',                     'PASS')
95 ('G7a',     'impersonation probe: crucible-armorer (deny)',                          'PASS')
95 ('G7a',     'impersonation probe: crucible-red (deny)',                              'PASS')
95 ('G7a',     'impersonation probe: crucible-coroner (deny)',                          'PASS')
95 ('G7c',     'holdout_touch_count == 0',                                              'PASS')

UNEVALUABLE findings in any surviving record: 0
```

**One gate evaluation in one run went UNEVALUABLE. The other 95 all passed.** The rate is
one voided run in roughly sixty, not sixty in sixty.

### Why the brief got it wrong, and why that is the interesting part

`run-10.console.txt` is **two processes writing to one file**. Line 47 ends mid-word and
line 48 belongs to a different stream:

```
$ sed -n '46,50p' evidence/batch-night-2026-08-25/run-10.console.txt | cat -A
  OFFLINE READER: REJECTS, 1 defect(s). ...$
    E_EXCLUSION_CEILING_RUN at round_census: ... degrades to at mos$
  six lock fields present: True$
boundary and must not be read as a pass.$
  UNEVALUABLE G7a   impersonation probe: crucible-sealed-eval (allow)$
```

That is the race already recorded in `8ea4830`: two copies of `night-batch.sh` iterating
1..60 against one directory because a harness `run_in_background` status reported KILLED on
a batch that was still alive. Run 10 is exactly where the overlap started
(`run_20260825_044815_5100ff-gate` and `run_20260825_044830_5100ff-gate`, fifteen seconds
apart). One execution went RUN_INVALID; the other re-executed the same run number and
**overwrote `run-10.json`, `run-10.c6.json`, and `run-10.exitcode`**.

```
$ python -c "...; print('G7a in run-10.json:', 'G7a' in s)"
G7a in run-10.json: False
UNEVALUABLE count: 0
```

So the only surviving trace of a real RUN_INVALID is a console file that a second process
was corrupting at the same moment. **A reader who greps the consoles sees one loud
UNEVALUABLE block and no G7 lines anywhere else, and concludes the gate never evaluates.**
That reading is exactly backwards, and it is a seventh instance of the project's standing
lesson: a reported status is not evidence. Assert the artifact. The artifacts are the
campaign records, and they say PASS 1520 times.

The block itself is the RUN_INVALID handler at `crucible/conductor/campaign.py:1313`
printing `every assertion this gate evaluated`, not a per-run banner.

---

## 1. Live re-evaluation today, against the same live project

Run just now, read-only, through the same class the campaign runs
(`scripts/probe-g7-g8.py` calls `RealGate.preflight()`):

```
$ python scripts/probe-g7-g8.py --holdout-expected 0
  PASS        G8    crucible-gate holds objectCreator on gs://crucible-policies-x7
  PASS        G8    crucible-gate holds NO overwrite/delete role on gs://crucible-policies-x7
  PASS        G8    crucible-armorer holds NO storage role on gs://crucible-policies-x7
  PASS        G8    policies retention EXISTS and is NOT locked
  PASS        G8    policies object versioning is ON
  PASS        G8    UBLA on and PAP enforced: gs://crucible-policies-x7
  PASS        G7b   crucible-armorer holds NOTHING on gs://crucible-sealed-x7
  PASS        G7b   crucible-red holds NOTHING on gs://crucible-sealed-x7
  PASS        G7b   crucible-armorer holds no project-level storage/bigquery role
  PASS        G7b2/G8 no CRUCIBLE identity holds a project-level BASIC role
  PASS        G7    UBLA on and PAP enforced: gs://crucible-sealed-x7
  PASS        G7a   impersonation probe: crucible-sealed-eval (allow)
              the positive control read the prefix, so the path is real and the 403s below mean something
  PASS        G7a   impersonation probe: crucible-armorer (deny)
              refused at the storage layer
  PASS        G7a   impersonation probe: crucible-red (deny)
              refused at the storage layer
  PASS        G7a   impersonation probe: crucible-coroner (deny)
              refused at the storage layer
  FAIL        G7c   holdout_touch_count == 0
              the sealed holdout was READ by 7 request(s) from outside the permitted set: eric@erictetzlaff.com
16 assertions, 15 PASS, 1 not PASS
```

Artifact written: `docs/proof/L3-real-gate-G7-G8-2026-08-25.txt` (71111 bytes). This is a
side effect of running the probe; it is new and uncommitted, and the coordinator decides
whether it is kept. Section 5 below explains why its G7c line is red and will stay red.

---

## 2. G7a, the positive control: NOT BROKEN. Root cause was a transient gcloud fetch, already half fixed

### 2.1 The boundary is live and correct

Positive control, reproduced by hand:

```
$ gcloud storage objects list "gs://crucible-sealed-x7/_probe/**" \
    --impersonate-service-account=crucible-sealed-eval@crucible-hack-2026.iam.gserviceaccount.com \
    --format="value(name)"
WARNING: This command is using service account impersonation. ...
_probe/canary.txt
RC=0
```

The service account exists and holds a read role, bucket-wide, with no condition:

```
$ gcloud storage buckets get-iam-policy gs://crucible-sealed-x7 --format=json
roles/storage.legacyBucketOwner  -> ['projectEditor:...', 'projectOwner:...']
roles/storage.legacyBucketReader -> ['projectViewer:...']
roles/storage.legacyObjectOwner  -> ['projectEditor:...', 'projectOwner:...']
roles/storage.legacyObjectReader -> ['projectViewer:...']
roles/storage.objectCreator      -> ['serviceAccount:crucible-sealed-eval@crucible-hack-2026.iam.gserviceaccount.com']
roles/storage.objectViewer       -> ['serviceAccount:crucible-sealed-eval@crucible-hack-2026.iam.gserviceaccount.com']
```

`crucible-armorer`, `crucible-red`, and `crucible-coroner` appear nowhere on that bucket.
All eleven `crucible-*` service accounts exist and none is disabled
(`gcloud iam service-accounts list`).

### 2.2 The deny arms produce a genuine storage-layer 403

```
$ gcloud storage objects list "gs://crucible-sealed-x7/_probe/**" \
    --impersonate-service-account=crucible-armorer@crucible-hack-2026.iam.gserviceaccount.com
ERROR: (gcloud.storage.objects.list) [crucible-armorer@...] does not have permission to
access b instance [crucible-sealed-x7] (or it may not exist): ... does not have
storage.objects.list access to the Google Cloud Storage bucket. Permission
'storage.objects.list' denied on resource
'//storage.googleapis.com/projects/_/buckets/crucible-sealed-x7' (or it may not exist).
RC=1
```

Identical shape for `crucible-red` and `crucible-coroner`. `classify_probe` matches
`storage.objects.list` in `_STORAGE_LAYER` and returns PASS, "refused at the storage layer".
That is what all 95 recorded gate calls saw.

### 2.3 Root cause of the one failure

Not IAM, not naming, not the probe prefix. On run 10 **every gcloud invocation in that gate
evaluation failed at once**: four G7a probes plus the project IAM fetch. The IAM fetch
error carried an empty cause:

```
UNEVALUABLE G7c   holdout_touch_count == 0
   the counter raised: could not read the project IAM policy
   (could not fetch project IAM policy: ), so whether Data Access logging is still on is unknown
```

An empty interpolation means gcloud exited non-zero **with no stderr at all**. That is a
process-level or transport-level failure, not an API denial: a denial always writes a
message. The three deny arms landed in `classify_probe`'s final branch, "failed for a
reason that is not a storage permission denial", for the same reason. The identical
commands succeeded on the next manual invocation.

**A correlated failure of five independent gcloud calls in one window is not five
independent transients.** The strongest available explanation is contention: run 10 is the
first run of the overlap, and two `night-batch.sh` copies were spawning gcloud concurrently
against a shared `%APPDATA%\gcloud` config and credential store on Windows. That is a
correlation across one event, not a proof, and section 7 says what would settle it.

### 2.4 What has already been repaired, and what has not

`57f4e94` ("fix: a transient IAM fetch invalidated a whole run, and said nothing about
why") fixed both defects **in `infra/verify_iam.py:gcloud_json` only**:

- the error now carries the return code plus a slice of stdout, and says
  "no stderr and no stdout" explicitly;
- three attempts with 0.5s and 2.0s backoff.

That covers the G7b, G7b2, G8, UBLA/PAP, and G7c policy-fetch call sites. **It does not
cover the two call sites that broke loudest.**

| Call site | Used by | Retries? | Diagnostic on empty stderr? |
|---|---|---|---|
| `infra/verify_iam.py:gcloud_json` | G7, G7b, G7b2, G8, G7c policy fetch | **yes, 3x** | **yes** |
| `crucible/conductor/real_gate.py:_run_capture` (line 508) | **G7a, all four arms** | **no** | n/a, output goes to `classify_probe` |
| `infra/holdout_touch.py:gcloud_log_read` (line 246) | **G7c log read** | **no** | **no**, interpolates `p.stderr` alone |

`_run_capture` is a bare `subprocess.run`. `gcloud_log_read` reproduces the exact
diagnostic dead end that `57f4e94` removed from `gcloud_json`:

```python
raise HoldoutTouchUnevaluable(
    "gcloud logging read exited %d: %s. ..." % (p.returncode, (p.stderr or "").strip()[:300]))
```

An exit-1 with empty stderr renders as `gcloud logging read exited 1: .`

**A fix that lands on one of three call sites has fixed one third of the failure surface,
and the two left out are the two that actually failed.**

### 2.5 Repair

**Code change, no GCP mutation, no cost, no risk to the boundary.** Give both remaining
call sites the same bounded retry and the same non-empty error, reusing
`verify_iam.FETCH_ATTEMPTS` and `verify_iam.FETCH_BACKOFF` so there is one policy and not
three.

1. `crucible/conductor/real_gate.py`, replace `_run_capture` with a retrying form.
   Retry **only** when the invocation produced no classifiable output, meaning the combined
   stdout plus stderr matches neither `_IMPERSONATION_LAYER` nor `_STORAGE_LAYER` and the
   return code is non-zero. A real 403 must return on the first attempt and must never be
   retried, for the same reason `real_gate._promote_with_assertion` refuses to retry
   `E_WRONG_PROMOTER`: retrying a semantic answer produces the same answer three times and
   only costs time. A `PASS` and a `FAIL` are both semantic answers here.

2. `infra/holdout_touch.py:gcloud_log_read`, same bounded retry, and copy the
   `gcloud_json` error construction verbatim so an empty stderr reports the return code and
   a stdout slice.

**This cannot launder a denial.** The deny arms still classify from real gcloud output, and
a permission denial is classified on attempt one. The only behaviour that changes is that a
call which produced nothing to classify gets asked again.

3. **Add the tests, because none exist.** `57f4e94` shipped the `gcloud_json` retry with no
   test driving it. `grep -rn "FETCH_ATTEMPTS" tests/` returns nothing, and there is no
   `tests/test_verify_iam.py`. A retry nothing exercises is a check that cannot fail wearing
   different clothes, which is the exact sentence in that commit message. The three sites
   need an injected runner (`gcloud_json(args, what, runner=...)`, `gcloud_log_read(...,
   runner=...)`, `seal_probe_findings` already accepts `run=`) and cases proving:
   fail-then-succeed returns the success; three failures raise with a non-empty cause; a
   storage 403 is classified on the first call and the runner is invoked exactly once.

**Deliverable before 2026-08-28: yes, comfortably.** It is a local code change plus tests,
no infrastructure, no spend, no model calls.

### 2.6 The contract is still wrong, and it is worth closing separately

`contracts/gate_rule.v1.yaml` G7a and `measurement-spec.md:836` both specify the probe as

```
gcloud storage objects list gs://crucible-sealed-$SUFFIX/families/
```

`real_gate._probe_argv`'s docstring records that this form exits 0 and prints nothing for a
permitted identity, because a trailing-slash prefix is not a match pattern to `objects
list`. The code uses `_probe/**`. So **the specified command has no positive control and the
implemented command does**, and the two documents disagree with the code that is actually
run. Nothing scored depends on this, but a judge who runs the documented command gets an
uninformative result and no warning. Fixing the contract text is a doc edit, and the
contract is hash-locked, so it needs the coordinator. Flagged, not actioned.

---

## 3. Naming: the probe sources correctly. No second copy of any name exists

Checked, because the brief asked. `real_gate.gcp_env` calls `verify_iam.load_env`, which
asks bash to source the file rather than parsing it:

```python
subprocess.run(["bash", "-c", '. "%s/scripts/gcp-env.sh" && env | grep -E "^(CRUCIBLE_|SA_|SUFFIX)"' % repo_root], ...)
```

One copy of the names, one parser of the file. `_probe_argv` interpolates
`env["CRUCIBLE_SEALED_BUCKET"]` and `env["CRUCIBLE_PROJECT"]`; `seal_probe_findings` reads
`env["SA_SEALED_EVAL"]`, `env["SA_ARMORER"]`, `env["SA_RED"]`, `env["SA_CORONER"]`. No
bucket name, project id, or service-account name is typed in `real_gate.py`. There is a test
for exactly this: `tests/test_real_gate.py:500
test_the_probe_command_never_types_a_bucket_or_project_name`.

`promoter_identity` reads `SA_GATE` and asserts it equals `promote.py`'s literal
`crucible-gate`, converting a silent divergence into a loud one. **A typo is not the cause
here and could not have been.**

One residual: `load_env` requires `bash` on PATH and uses `check=True`. On a machine without
Git Bash the whole gate reports UNEVALUABLE at `real_gate.py:649`. That is correct
behaviour, and it is one more single-shot external dependency in the chain.

---

## 4. G7c: Data Access logging IS enabled. The build-list note saying otherwise is stale

The brief says the live project has no `auditConfigs` block. It has one:

```
$ gcloud projects get-iam-policy crucible-hack-2026 --format=json
top keys: ['auditConfigs', 'bindings', 'etag', 'version']
auditConfigs: [
  {
    "auditLogConfigs": [ { "logType": "DATA_READ" } ],
    "service": "storage.googleapis.com"
  }
]
```

Applied 2026-08-22, and `infra/holdout_touch.py` was wired the same day. **Nothing needs to
be enabled and nothing needs to be paid for.** The count exists, is derived from a live log,
and printed a real number today:

```
window since : 2026-08-22T19:31:10Z   (attestation floor)
entries      : 624 matched
COUNT        : 11 granted object-content reads   <- holdout_touch_count
enumerations : 165 granted (listings / prefix probes, NOT counted)
denied       : 448 (logged, and not a touch: no bytes moved)
```

Cloud Logging Data Access log ingestion is free of charge; retention beyond the default
free tier is what costs. No estimate is offered here because none is needed: the config is
already on and the batch already ran under it. **No action required for G7c enablement.**

The action item that remains on this line belongs elsewhere: `docs/contest/BUILD-LIST.md`
records the opposite, and another lane owns that file. **The stale row needs correcting by
its owner, and this document does not touch it.**

---

## 5. G7c has TWO real defects, and neither is the one the brief named

### 5.1 The proof artifact's G7c line is now permanently red, and it will stay red forever

`scripts/probe-g7-g8.py` defaults `--holdout-since` to
`holdout_touch.ATTESTATION_FLOOR_UTC`. That window contains seven reads of the sealed bucket
by `eric@erictetzlaff.com` on 2026-08-22, from the session that established the canary. The
human operator is deliberately not in `permitted_principals`, so `compute()` raises
`HoldoutTouchInvalid`, and the artifact prints:

```
FAIL  G7c  holdout_touch_count == 0
      the sealed holdout was READ by 7 request(s) from outside the permitted set:
      eric@erictetzlaff.com
```

Cloud Logging entries cannot be deleted by the project owner. **Every future regeneration of
this artifact reports a red G7c for a boundary that is intact**, and a judge reading
`docs/proof/` on 2026-08-30 sees a FAIL on the project's most load-bearing gate. Inside a
campaign this does not arise: `since` is the run start, and all 95 gate calls read PASS.

**Repair, code and doc only.** Change `--holdout-since`'s default in
`scripts/probe-g7-g8.py` from the attestation floor to the probe's own start instant, and
print the floor-window tally underneath as clearly labelled provenance rather than as a
scored assertion. The out-of-run comparison is already documented as not meaningful in that
file's own docstring; the fix is to stop scoring it. **Do not add the operator to
`permitted_principals`.** Exempting the human is the self-certification move the whole
design refuses, and the current behaviour of recording the operator read is correct. What is
wrong is scoring a window in which no run happened.

Cost: none. Risk: none to the boundary; it removes a scored comparison that the file already
says is not meaningful. Before 08-28: yes.

### 5.2 The log query is at 62 percent of its truncation cap, and the cap raises UNEVALUABLE

`DEFAULT_CAP = 1000` (`infra/holdout_touch.py:172`). `compute()` raises
`HoldoutTouchUnevaluable` when `len(entries) >= cap`, correctly, because a truncated result
has no "at least N" outcome. The floor window matched **624 entries today**, against 1000.

Each gate call adds roughly four entries: one granted enumeration by `crucible-sealed-eval`
plus three denials. The overnight batch's 95 gate calls account for most of the 624. **There
is headroom for about ninety more gate calls before the floor-window query truncates.** One
more batch of this size crosses the cap, and then `scripts/probe-g7-g8.py` at its current
default goes UNEVALUABLE, which is RUN_INVALID semantics inside the artifact that exists to
demonstrate the gate works.

Fixing 5.1 also fixes this, because a probe-scoped window matches almost nothing. If the
floor tally is kept as printed provenance, its read needs its own higher cap and an explicit
truncation note. **Do not silently raise `DEFAULT_CAP`**: the in-run cap is a real guard and
the two windows want different values.

Cost: none. Before 08-28: yes.

---

## 6. The 2026-08-28 unseal: a scheduling hazard that will void a run if it is not sequenced

Stated here because it follows directly from how G7c counts, and it is not written down
anywhere else I found.

`permitted_principals` is `{crucible-sealed-eval@...}` and nothing else. On 08-28 the
held-out family gets opened. **If that read is performed by `eric@erictetzlaff.com` while a
campaign is running, the campaign's G7c window contains an intruder read and the run goes
RUN_INVALID**, with the correct and unhelpful message that the seal was touched from outside
the permitted set.

Two ways to avoid it, both free, neither requiring an IAM change:

1. **Perform the unseal read under impersonation**, exactly as the G7a probe does:
   `gcloud storage cat gs://crucible-sealed-x7/... --impersonate-service-account=crucible-sealed-eval@crucible-hack-2026.iam.gserviceaccount.com`.
   That principal is in the permitted set, so the read is recorded and permitted. It is also
   the honest form: the identity that is supposed to be able to read the holdout is the one
   that reads it.
2. **Or run no campaign across the unseal window**, and start any post-unseal run after the
   last unseal read, so `since` excludes it.

Recommend (1), with (2) as belt and braces. Note that (1) makes the unseal itself an entry in
the audit trail under a named principal, which is a stronger artifact than an operator read.

---

## 7. What I could not determine, and what would settle it

1. **Whether concurrency caused run 10's gcloud failure, or something else did.** The
   evidence is one correlated event, the timing coincidence with the start of the runner
   overlap, and an empty stderr. The artifact that would have carried the real cause was
   overwritten by the racing re-execution, so **there is no gcloud diagnostic log for that
   invocation**. What would settle it: the retry landing with an error that names the return
   code, then either the failure never recurring under the single-runner lock from `8ea4830`,
   or recurring with a cause attached. It cannot be settled retrospectively.

2. **The `$0.0057` and `$0.0677` spend figures in `run-10.console.txt`.** Two streams wrote
   that file and the lines cannot be reliably attributed. `$0.0677` sits in the normal range
   for the batch and `$0.0057` is an outlier, which suggests but does not prove that the
   RUN_INVALID execution is the one that spent `$0.0677`. **Do not quote either figure.**
   Per-run spend should be read from the campaign records, not the consoles.

3. **Whether the 1520 PASSes are 1520 independent observations.** They are 95 gate
   evaluations from a single machine, a single gcloud install, and a single operator
   credential, inside one eleven-hour window. That is the accuracy boundary this project
   already states about k=1, and it applies here too: the boundary has been asserted many
   times, not many ways.

4. **Whether `gcloud logging read` has ever failed in a live run.** It has no retry and its
   error is uninformative on empty stderr, so if it had failed transiently the record would
   look exactly like run 10's IAM fetch. No such failure appears in the surviving records.
   Absence of a failure in 95 calls is a weak bound, not a clean sheet.

---

## 8. Summary of the repair plan

| # | Item | Kind | GCP mutation | Cost | Before 08-28 |
|---|---|---|---|---|---|
| 1 | Bounded retry plus non-empty error in `real_gate._run_capture` (G7a), retrying only unclassifiable output | code | none | none | yes |
| 2 | Bounded retry plus non-empty error in `holdout_touch.gcloud_log_read` (G7c) | code | none | none | yes |
| 3 | Tests driving all three retry paths, with an injected runner. None exist today | test | none | none | yes |
| 4 | `probe-g7-g8.py --holdout-since` defaults to probe start; floor tally printed as provenance, not scored | code | none | none | yes |
| 5 | Sequence the 08-28 unseal read under `crucible-sealed-eval` impersonation | procedure | none | none | yes |
| 6 | Correct the contract and measurement-spec G7a command to the form that has a positive control | doc, hash-locked | none | none | coordinator's call |
| 7 | Correct the stale "no auditConfigs" row in `docs/contest/BUILD-LIST.md` | doc | none | none | its owner's call |

**No IAM binding needs to be added, removed, or changed. No audit sink needs to be created.
No retention policy is proposed for locking. `crucible-armorer` holds no storage role on the
policies bucket and nothing here widens that.**

The seal boundary itself was verified live today and it holds: the positive control reads
the canary, and `crucible-armorer`, `crucible-red`, and `crucible-coroner` each get a genuine
`storage.objects.list` denial on `gs://crucible-sealed-x7`.
