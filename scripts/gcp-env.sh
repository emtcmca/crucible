#!/usr/bin/env bash
# CRUCIBLE -- canonical GCP resource names.
# Provisioned and read back 2026-08-20. Source this; do not retype names.
#   source scripts/gcp-env.sh
#
# SUFFIX is never defined in the spec set. "x7" appears only as an illustrative
# literal in data-spec.md example URIs; it was adopted as the real suffix so
# those examples are literally true rather than a second thing to reconcile.

export CRUCIBLE_PROJECT="crucible-hack-2026"
export CRUCIBLE_PROJECT_NUMBER="752793770087"
export CRUCIBLE_REGION="us-central1"
export SUFFIX="x7"

# Firestore -- (default), Native mode, us-central1, freeTier true. LOCATION IS PERMANENT.
export CRUCIBLE_FIRESTORE_DB="(default)"

# GCS. All three: uniform bucket-level access ON, public access prevention ENFORCED.
export CRUCIBLE_SEALED_BUCKET="gs://crucible-sealed-${SUFFIX}"
export CRUCIBLE_POLICIES_BUCKET="gs://crucible-policies-${SUFFIX}"
export CRUCIBLE_EVIDENCE_BUCKET="gs://crucible-evidence-${SUFFIX}"

# policies additionally: object versioning ON, retention 1209600s (14d), NOT locked.
# Unlocked is deliberate -- a locked retention policy cannot be shortened or removed,
# and the bucket could not be torn down for 14 days after the last write.

# --- NOT YET DONE, deliberately -------------------------------------------
# No IAM bindings exist on any bucket beyond the GCS defaults. Service accounts
# do not exist yet; a binding against a non-existent principal is the failure
# that looks like success. Bind when the SAs are created.
#
# HAZARD for G8: every new bucket carries default legacy bindings for
# projectViewer:/projectEditor:. Any principal granted a project-level BASIC role
# (roles/viewer, roles/editor, roles/owner) silently inherits READ on the sealed
# bucket through them. Verified 2026-08-20: no CRUCIBLE service account holds a
# basic role, and the default compute SA does NOT hold roles/editor here.
# The G8 verification script must assert that and not merely assert the absence
# of a named sa-redteam binding.

# --- Service accounts (not yet created; names are canonical) ----------------
# Named crucible-*, never sa-*. The sa-* prefix is dead vocabulary from the
# pre-review drafts and naming the promoter "sa-warden" was the original G8
# defect the adversarial pass caught.
export SA_ARMORER="crucible-armorer"
export SA_GATE="crucible-gate"
export SA_RED="crucible-red"
export SA_CORONER="crucible-coroner"
export SA_WARDEN="crucible-warden"
export SA_TRIPWIRE="crucible-tripwire"
export SA_SEALED_EVAL="crucible-sealed-eval"

export BQ_TELEMETRY="crucible_telemetry"
export BQ_SEALED="crucible_sealed"

# --- GRANT DIRECTION ON THE POLICIES BUCKET --------------------------------
# Bind these when the service accounts exist. Getting the direction backwards
# silently destroys G8, whose failure mode is RUN INVALID with the text
# "the separation was never real." It has already been proposed backwards once.
#
#   crucible-gate     -> roles/storage.objectCreator on $CRUCIBLE_POLICIES_BUCKET
#                        CREATE ONLY. Not objectAdmin, not objectUser -- it must
#                        not be able to overwrite or delete a promoted version.
#   crucible-armorer  -> NO storage role on that bucket. Asserted == 0 by the
#                        same grep -c form as G7(b).
#
# THE IDENTITY THAT AUTHORS A CANDIDATE IS NOT THE IDENTITY THAT PROMOTES IT.
# The promoter is crucible-gate. It is NOT sa-warden.
