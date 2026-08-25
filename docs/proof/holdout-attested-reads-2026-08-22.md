# Attested operator reads of the sealed holdout

**Window covered: 2026-08-22T20:18:01Z to 2026-08-22T20:18:38Z. Written
2026-08-25. READ-ONLY: every command behind this document is `gcloud logging
read`.**

This file is the single source of truth for which reads of
`gs://crucible-sealed-x7` are ACCOUNTED FOR. `infra/holdout_touch.py` parses the
fenced `json` block below at the bottom of this document; the prose and the keys
the code matches live in one file so they cannot drift apart.

---

## What this is, and the two things it is deliberately not

G7c counts granted object-content reads of the sealed holdout and marks a run
INVALID when one comes from a principal outside `permitted_principals`. The
permitted set holds exactly one identity, `crucible-sealed-eval`. The human
operator is **deliberately not in it**: they hold `roles/owner`, they can read
everything, and the honest response to that is to record it rather than exempt
it.

On 2026-08-22 the operator read the sealed bucket seven times. Cloud Logging
entries cannot be deleted by the project owner, so those seven reads sit
permanently inside the attestation window, and
`scripts/probe-g7-g8.py`, whose `--holdout-since` defaults to that window,
printed:

```
FAIL  G7c  holdout_touch_count == 0
      the sealed holdout was READ by 7 request(s) from outside the permitted
      set: eric@erictetzlaff.com
```

That line is **true and misleading at the same time**: the boundary is intact,
the reads are explained, and a judge reading `docs/proof/` sees a red line on
the project's most load-bearing gate.

**This is not fixed by moving the window forward.** Moving the window would hide
the reads, and a control that stops looking is not a control that passed. It is
also not fixed by adding the operator to `permitted_principals` - exempting the
human is the self-certification move G8 exists to prevent, and it would forgive
every future operator read as well as these seven.

It is fixed by ATTESTING them. Each read below is named by its exact
nanosecond timestamp, principal, method, and object, with the command that made
it and why. `infra/holdout_touch.py::tally` moves an attested read out of
`intruders` and into `attested_reads`. **It is still counted in
`holdout_touch_count` and still printed with its object and its reason.** The
record removes the alarm, not the evidence.

**An attestation key is an INSTANT, never a principal.** A read that has not
happened yet carries a timestamp no row here names, so it is unexplained by
construction and still marks the run INVALID. Nothing in this file makes
`eric@erictetzlaff.com` a permitted reader of the holdout.

---

## Provenance: the log named the command itself

None of this is reconstructed from memory. The Data Access audit entries carry
`protoPayload.requestMetadata.callerSuppliedUserAgent`, which gcloud stamps with
the subcommand and an invocation id. Re-derive with:

```
gcloud logging read \
  'logName="projects/crucible-hack-2026/logs/cloudaudit.googleapis.com%2Fdata_access"
   AND protoPayload.serviceName="storage.googleapis.com"
   AND resource.type="gcs_bucket"
   AND resource.labels.bucket_name="crucible-sealed-x7"
   AND timestamp>="2026-08-22T19:31:10Z"
   AND protoPayload.authenticationInfo.principalEmail="eric@erictetzlaff.com"' \
  --project=crucible-hack-2026 --order=asc --format=json
```

Every one of the eighteen operator entries in that window carries
`gcloud/581.0.0` from caller IP `23.244.109.49`, and the subcommands, in order,
are: `ls`, `ls`, `cp`, `cp`, `cp`, `cp`, `ls`, `cat`, `cat`, `cat`, `cat`,
`cat`, `cat`, `rm`, `ls`, `ls`, `ls`.

**That sequence is a canary MOVE, and the move is already recorded in the
codebase.** `crucible/conductor/real_gate.py::_PROBE_PREFIX` documents it:

> Eric's ruling on `docs/NEEDS-ERIC.md` item 12, executed 2026-08-22: the canary
> was MOVED, not excluded.
>
>     was:  gs://crucible-sealed-x7/families/_probe/canary.txt
>     now:  gs://crucible-sealed-x7/_probe/canary.txt
>     gs://crucible-sealed-x7/families/  is now EMPTY

The seven reads are the source-read half of that copy, the verification `cat`s
of the old and new paths, and the pre-delete read of the old object. The
objects touched are `_probe/canary.txt` and `families/_probe/canary.txt` and
nothing else. **No sealed attack instance was read**: `families/` held only the
probe canary at that moment, and the log names every resource it touched.

### One entry in that burst is NOT attested here, because it is not a read

`2026-08-22T20:18:02.046086366Z`, `storage.objects.get` on
`.../objects/_probe/canary.txt`, from the same `cp` invocation, carries
`authorizationInfo[].granted: true` **and** `status.code: 5`
(`No such object`). It is `cp` checking whether the destination already exists.
Authorization passed; no byte moved. `is_granted` keys on the status code first
for exactly this shape, so it never reaches the count and needs no attestation.
Attesting it anyway would have quietly widened the record past the reads it
describes.

---

## The seven

| # | timestamp (UTC) | gcloud subcommand | invocation id | object |
|---|---|---|---|---|
| 1 | 2026-08-22T20:18:01.984616894Z | `gcloud.storage.cp` | `998f637e5615433588281e69553c482b` | `families/_probe/canary.txt` |
| 2 | 2026-08-22T20:18:04.437501494Z | `gcloud.storage.cp` | `998f637e5615433588281e69553c482b` | `families/_probe/canary.txt` |
| 3 | 2026-08-22T20:18:26.359513436Z | `gcloud.storage.cat` | `1527aae95ac94d0eb14fd5e4eb90b4e8` | `families/_probe/canary.txt` |
| 4 | 2026-08-22T20:18:26.654634479Z | `gcloud.storage.cat` | `1527aae95ac94d0eb14fd5e4eb90b4e8` | `families/_probe/canary.txt` |
| 5 | 2026-08-22T20:18:28.564743427Z | `gcloud.storage.cat` | `1aeacce459d0474ba6dc9cb70b345c7b` | `_probe/canary.txt` |
| 6 | 2026-08-22T20:18:28.859308711Z | `gcloud.storage.cat` | `1aeacce459d0474ba6dc9cb70b345c7b` | `_probe/canary.txt` |
| 7 | 2026-08-22T20:18:37.670749751Z | `gcloud.storage.rm` | `77ee755875a54553abdbeda942e2bf6f` | `families/_probe/canary.txt` |

Pairs 1/2, 3/4 and 5/6 are the metadata fetch and the media download of a single
logical read - the same doubling `render_tally` reports as `distinct` beside
`COUNT`, measured on this bucket 2026-08-22.

## What this record does NOT establish

* **It rests on the operator's own attestation of intent.** The log proves which
  commands ran, from which IP, against which objects, at which instant. It
  cannot prove *why*, and the person who ran them is the person who wrote this
  file. That is the same accuracy boundary this project already states about a
  sealed set reviewed by one person who is also the builder. The corroboration
  that exists is external to this file: `_PROBE_PREFIX`'s comment recorded the
  move before this record was written, and the command sequence in the log
  matches it.
* **It says nothing about the bucket before 2026-08-22T19:31:10Z.** Data Access
  logging is not retroactive and `ATTESTATION_FLOOR_UTC` is the earliest instant
  coverage has been SHOWN.
* **These entries expire when Cloud Logging's retention expires.** The `_Default`
  bucket's retention is finite. When the canary read ages out, `_check_canary`
  will find no granted content read and G7c becomes UNEVALUABLE, which is
  RUN_INVALID. That is the correct behaviour - the control declines to guess -
  and it is a scheduled hazard, not a surprise.

---

```json
{
  "record_version": 1,
  "written": "2026-08-25",
  "bucket": "gs://crucible-sealed-x7",
  "attested_reads": [
    {
      "timestamp": "2026-08-22T20:18:01.984616894Z",
      "principal": "eric@erictetzlaff.com",
      "method": "storage.objects.get",
      "resource": "projects/_/buckets/crucible-sealed-x7/objects/families/_probe/canary.txt",
      "why": "gcloud.storage.cp invocation 998f637e5615433588281e69553c482b - source read of the canary MOVE from families/_probe/canary.txt to _probe/canary.txt, executed 2026-08-22 per Eric's ruling on docs/NEEDS-ERIC.md item 12 and recorded in real_gate._PROBE_PREFIX."
    },
    {
      "timestamp": "2026-08-22T20:18:04.437501494Z",
      "principal": "eric@erictetzlaff.com",
      "method": "storage.objects.get",
      "resource": "projects/_/buckets/crucible-sealed-x7/objects/families/_probe/canary.txt",
      "why": "gcloud.storage.cp invocation 998f637e5615433588281e69553c482b - the media half of the same copy; one cp emits a metadata fetch and a media download of the same object."
    },
    {
      "timestamp": "2026-08-22T20:18:26.359513436Z",
      "principal": "eric@erictetzlaff.com",
      "method": "storage.objects.get",
      "resource": "projects/_/buckets/crucible-sealed-x7/objects/families/_probe/canary.txt",
      "why": "gcloud.storage.cat invocation 1527aae95ac94d0eb14fd5e4eb90b4e8 - verifying the OLD canary path still read correctly before deleting it."
    },
    {
      "timestamp": "2026-08-22T20:18:26.654634479Z",
      "principal": "eric@erictetzlaff.com",
      "method": "storage.objects.get",
      "resource": "projects/_/buckets/crucible-sealed-x7/objects/families/_probe/canary.txt",
      "why": "gcloud.storage.cat invocation 1527aae95ac94d0eb14fd5e4eb90b4e8 - media half of the same cat."
    },
    {
      "timestamp": "2026-08-22T20:18:28.564743427Z",
      "principal": "eric@erictetzlaff.com",
      "method": "storage.objects.get",
      "resource": "projects/_/buckets/crucible-sealed-x7/objects/_probe/canary.txt",
      "why": "gcloud.storage.cat invocation 1aeacce459d0474ba6dc9cb70b345c7b - verifying the NEW canary path read correctly, which is what makes G7a's positive control real."
    },
    {
      "timestamp": "2026-08-22T20:18:28.859308711Z",
      "principal": "eric@erictetzlaff.com",
      "method": "storage.objects.get",
      "resource": "projects/_/buckets/crucible-sealed-x7/objects/_probe/canary.txt",
      "why": "gcloud.storage.cat invocation 1aeacce459d0474ba6dc9cb70b345c7b - media half of the same cat."
    },
    {
      "timestamp": "2026-08-22T20:18:37.670749751Z",
      "principal": "eric@erictetzlaff.com",
      "method": "storage.objects.get",
      "resource": "projects/_/buckets/crucible-sealed-x7/objects/families/_probe/canary.txt",
      "why": "gcloud.storage.rm invocation 77ee755875a54553abdbeda942e2bf6f - the read gcloud performs on the old object before removing it, completing the move. gs://crucible-sealed-x7/families/ has been empty since."
    }
  ]
}
```
