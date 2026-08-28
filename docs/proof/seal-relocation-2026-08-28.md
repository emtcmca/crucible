# Seal relocation to GCS, 2026-08-28

**Authorised in advance by `f4-unseal-preregistration-2026-08-25.md` Amendment A3.1, which
was committed BEFORE this operation ran.** This document records what happened, in order,
with the verification either side of it.

---

## 1. Why the seal moved

`gs://crucible-sealed-x7` contained exactly one object, `_probe/canary.txt`. The 24 F4
instances lived only in the local worktree `crucible-wt-SEAL/corpus/sealed` on branch
`freeze/D5-corpus`.

**So `holdout_touch_count` and G7c were attesting to reads of a canary, not to reads of the
holdout.** The counter could have returned a clean zero forever while the sealed set was read
freely from local disk, because the sealed set was never behind the boundary the counter
watches. That is the fifth instance in this repository of a check that passes while measuring
nothing.

The blindness itself was real and remains real. It was enforced by CODE STRUCTURE, by there
being no path from the harness to `corpus/sealed/` and by `E_SEALED_FAMILY_REACHED`, and not
by the IAM boundary that `sealed-family-commitment.json` `_limits` names as a control. After
this relocation both are true.

## 2. What ran, in order

| # | Step | Identity | Result |
|---|---|---|---|
| 1 | `scripts/seal-commitment.py --verify` from the worktree | operator, read-only | **SEAL INTACT**, 24 instances, recorded == recomputed |
| 2 | `gcloud storage cp` of 24 `*.json` to `gs://crucible-sealed-x7/families/` | **`crucible-sealed-eval`** | exit 0, 24 objects present |
| 3 | `gcloud storage cp` of the 24 back out to a scratch directory | **`crucible-sealed-eval`** | exit 0, 24 files |
| 4 | `seal_commitment.fingerprint()` over the downloaded bytes | local | see section 3 |

**The upload and the readback were both performed as `crucible-sealed-eval`**, the only
identity holding `roles/storage.objectCreator` and `roles/storage.objectViewer` on that
bucket. No operator identity touched the bucket during this operation, so no new attestation
entry is owed. `crucible-armorer` holds no binding on it and did not.

## 3. Verification either side of the move

The same function computed all three values: `fingerprint()` in `scripts/seal-commitment.py`,
imported and called rather than reimplemented, because a second implementation of a hash is a
second answer.

```
published commitment : (docs/proof/sealed-family-commitment.json)
worktree recompute   : equal to the published value
GCS READBACK compute : equal to the published value
```

**All three equal. 24 instances, classes `{CAP_MOVES_MONEY: 24, CAP_MUTATES_DURABLE_STATE: 24}`.**
Per ruling 46 the value itself is not copied here; read it from the commitment file and
recompute with `python scripts/seal-commitment.py --verify`.

**The bytes in the bucket are the bytes committed to.** A3.1 fixed the failure branch in
advance: had the readback disagreed, the upload would have been reverted and Outcome D would
apply. It did not disagree.

## 4. An upload is not a touch, and the audit trail stayed clean

`infra/holdout_touch.py` counts only granted `storage.objects.get` naming a real object.
`storage.objects.create` classifies as `OTHER`. Measured after the operation, over the full
window from `ATTESTATION_FLOOR_UTC`:

```
content reads       35   (was 11 before the upload)
distinct objects    26   (was 2: the two canary paths)
INTRUDERS            0
unattested_reads     0
attestation_problem  None
raw entries         40 / cap 1000
```

The delta of exactly **24 content reads for 24 objects** is the readback in section 2 step 3,
performed by the permitted principal. Intruders and unattested reads both remain zero, so the
relocation introduced no accountability gap.

## 5. The calibration, and how it actually happened

A3.2 fixed `expected_for_this_phase` as a count of granted content reads inside the run's own
window, and specified calibrating it by reading the canary once through the runner's code
path.

**That is not where the number came from, and saying so matters more than tidiness.** The
authorised readback in step 3 read all 24 real instances and produced a delta of exactly 24
content-read entries. **One content read per object**, measured on the actual objects rather
than inferred from a canary. That is stronger evidence than the method A3.2 described, and it
was a by-product of a step A3.1 already required.

**Two consequences for the transfer run:**

1. **The runner reads the 24 instances ONCE and evaluates both passes from memory.** Two
   passes over the corpus does not mean two reads of it. Fewer touches of the seal is strictly
   better, and it makes the expected count deterministic.
2. **`--holdout-expected` is therefore `24`**, subject to one confirmation: the figure above
   was measured through `gcloud storage cp`, and the runner reads through the Python client.
   **Before the transfer run fires, the runner's own read path is calibrated against the
   canary object, and if it emits more than one entry per object the expected value is
   restated here before the run rather than after it.**

## 6. What this does not change

Sections 1 to 4 of the pre-registration are untouched. The six forbidden moves still bind. The
outcome table is unchanged, and Outcome E remains the pre-registered likely classification for
the reasons given in A3.5, which was committed before this relocation ran.
