#!/usr/bin/env bash
# Grant the CRUCIBLE IAM bindings. data-spec.md section 4.1 is the map.
#
# READ THIS BEFORE CHANGING ANY LINE BELOW
# ----------------------------------------
# Two grants in this file are the difference between a real security claim and
# theatre, and BOTH have been proposed backwards at least once already:
#
#   crucible-gate     -> roles/storage.objectCreator on the POLICIES bucket.
#                        CREATE ONLY. Not objectAdmin, not objectUser. Those
#                        would let the promoter overwrite or delete a promoted
#                        version, and the immutability claim would be convention
#                        wearing an IAM costume.
#
#   crucible-armorer  -> NOTHING on any bucket. No storage.*, no bigquery.*, at
#                        any level, ever. THE IDENTITY THAT AUTHORS A CANDIDATE
#                        IS NOT THE IDENTITY THAT PROMOTES IT. Grant the Armorer
#                        write on the policies bucket and G8's own failure text
#                        applies: "the separation was never real", failure mode
#                        RUN INVALID.
#
# The promoter is crucible-gate. It is not sa-warden, and there is no sa-* here.
#
# Names come from scripts/gcp-env.sh and are never retyped.
# Idempotent: add-iam-policy-binding is a no-op if the binding exists.
#
# Run:  bash infra/bind-iam.sh
#       bash infra/bind-iam.sh --dry-run     print what would be granted
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
. "$HERE/scripts/gcp-env.sh"

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

# --- Refuse to grant a basic role from this script, whatever is asked ---------
# CONVENTIONS.md 10a: a project-level BASIC role (viewer/editor/owner) grants
# READ on the sealed bucket through the default legacy projectViewer/
# projectEditor bindings, WITH NO BINDING THAT NAMES THAT BUCKET. G7(b) and
# G8's bucket greps cannot see it. So this script must be structurally unable
# to create one -- a comment saying "do not grant basic roles" cannot fail.
assert_not_basic() {
  case "$1" in
    roles/viewer|roles/editor|roles/owner|roles/browser)
      echo "REFUSED: $1 is a project-level BASIC role." >&2
      echo "         It grants READ on the sealed bucket through the default" >&2
      echo "         legacy projectViewer/projectEditor bindings, with no" >&2
      echo "         binding naming that bucket. G7 and G8 cannot see it." >&2
      exit 2 ;;
  esac
}

proj_bind() {  # proj_bind <sa> <role>
  local sa="$1" role="$2"
  assert_not_basic "$role"
  if [ "$DRY" = 1 ]; then
    printf "  DRY  project  %-22s %s\n" "$sa" "$role"; return
  fi
  gcloud projects add-iam-policy-binding "$CRUCIBLE_PROJECT" \
    --member="serviceAccount:$(sa_email "$sa")" \
    --role="$role" --condition=None --quiet >/dev/null
  printf "  ok   project  %-22s %s\n" "$sa" "$role"
}

bucket_bind() {  # bucket_bind <sa> <role> <gs://bucket>
  local sa="$1" role="$2" bucket="$3"
  assert_not_basic "$role"
  # Hard guard: the Armorer never receives a bucket grant, from any call site.
  if [ "$sa" = "$SA_ARMORER" ]; then
    echo "REFUSED: $SA_ARMORER must hold NO storage role on any bucket." >&2
    echo "         The identity that authors a candidate is not the identity" >&2
    echo "         that promotes it. See G8." >&2
    exit 2
  fi
  if [ "$DRY" = 1 ]; then
    printf "  DRY  %-28s %-22s %s\n" "$bucket" "$sa" "$role"; return
  fi
  gcloud storage buckets add-iam-policy-binding "$bucket" \
    --member="serviceAccount:$(sa_email "$sa")" \
    --role="$role" --quiet >/dev/null
  printf "  ok   %-28s %-22s %s\n" "$bucket" "$sa" "$role"
}

echo "project: $CRUCIBLE_PROJECT"
echo ""
echo "PROJECT-LEVEL ROLES (data-spec 4.1)"

# aiplatform.user -- may call a model. Deliberately ABSENT from tripwire,
# warden, and gate: that absence is what makes "the judge is code" structural
# rather than a claim about our intentions.
for sa in "$SA_ORCHESTRATOR" "$SA_RED" "$SA_TARGET" "$SA_CORONER" \
          "$SA_ARMORER" "$SA_SEALED_EVAL"; do
  proj_bind "$sa" roles/aiplatform.user
done

# datastore.user -- Firestore read+write. NOTE data-spec A2: Firestore IAM has
# NO per-collection granularity, so every holder can write every collection.
# "Only the Gate writes gate_decisions" is therefore CONVENTION, not
# enforcement, and must never be claimed as enforcement on camera.
# crucible-red is deliberately absent: an attacker agent holding database
# credentials is an own-goal.
for sa in "$SA_ORCHESTRATOR" "$SA_TRIPWIRE" "$SA_CORONER" "$SA_ARMORER" \
          "$SA_WARDEN" "$SA_GATE" "$SA_SEALED_EVAL"; do
  proj_bind "$sa" roles/datastore.user
done

proj_bind "$SA_UI" roles/datastore.viewer          # read-only, no write anywhere
proj_bind "$SA_UI" roles/bigquery.jobUser

for sa in "$SA_ORCHESTRATOR" "$SA_TRIPWIRE" "$SA_WARDEN" "$SA_GATE"; do
  proj_bind "$sa" roles/cloudtrace.agent
done
proj_bind "$SA_UI" roles/cloudtrace.user

echo ""
echo "POLICIES BUCKET -- the G8 boundary"
# The ONLY objectCreator on this bucket, and the reason G8 can assert anything.
bucket_bind "$SA_GATE" roles/storage.objectCreator "$CRUCIBLE_POLICIES_BUCKET"
bucket_bind "$SA_GATE" roles/storage.objectViewer  "$CRUCIBLE_POLICIES_BUCKET"
# Readers. None of these can create a version.
bucket_bind "$SA_ORCHESTRATOR" roles/storage.objectViewer "$CRUCIBLE_POLICIES_BUCKET"
bucket_bind "$SA_TARGET"       roles/storage.objectViewer "$CRUCIBLE_POLICIES_BUCKET"
bucket_bind "$SA_UI"           roles/storage.objectViewer "$CRUCIBLE_POLICIES_BUCKET"
echo "  --   $CRUCIBLE_POLICIES_BUCKET   $SA_ARMORER            NO ROLE (asserted == 0 by verify-iam.sh)"

echo ""
echo "SEALED BUCKET -- the G7 boundary"
# One reader, and it runs once, at the end, after runs.status leaves running.
bucket_bind "$SA_SEALED_EVAL" roles/storage.objectViewer  "$CRUCIBLE_SEALED_BUCKET"
bucket_bind "$SA_SEALED_EVAL" roles/storage.objectCreator "$CRUCIBLE_SEALED_BUCKET"
echo "  --   $CRUCIBLE_SEALED_BUCKET     $SA_ARMORER            NO ROLE"
echo "  --   $CRUCIBLE_SEALED_BUCKET     $SA_RED                NO ROLE"

echo ""
echo "EVIDENCE BUCKET -- not gated"
bucket_bind "$SA_BQ_WRITER"    roles/storage.objectViewer  "$CRUCIBLE_EVIDENCE_BUCKET"
bucket_bind "$SA_ORCHESTRATOR" roles/storage.objectCreator "$CRUCIBLE_EVIDENCE_BUCKET"

echo ""
echo "NOT BOUND HERE, and each for a stated reason:"
echo "  run.invoker      the Cloud Run services do not exist yet. A binding"
echo "                   against a non-existent principal or resource is the"
echo "                   failure that looks like success."
echo "  bigquery.*       datasets crucible_telemetry / crucible_sealed are not"
echo "                   created yet. Same reason."
echo "  IAM Deny policy  data-spec 4.3 layer 3, pending assumption A3. Belt to"
echo "                   these suspenders, not a substitute -- see"
echo "                   infra/deny-armorer.sh."
echo ""
echo "Bindings applied. THIS SCRIPT'S EXIT CODE IS NOT THE EVIDENCE."
echo "Run: bash infra/verify-iam.sh"
