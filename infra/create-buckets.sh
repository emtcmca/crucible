#!/usr/bin/env bash
# Creates the three CRUCIBLE GCS buckets. Idempotent: skips any that exist.
# The buckets were created and read back 2026-08-20, so this now serves as the
# executable record of their configuration and as the recreate path after the
# data-spec 7.3 teardown.
#
# Run:  bash infra/create-buckets.sh
#
# Names come from scripts/gcp-env.sh and are never retyped here. G7 and G8 grep
# those literal strings, and a wrong name does not fail loudly -- it produces an
# unevaluable gate, which is a check that cannot fail (measurement-spec.md:813).
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
. "$HERE/scripts/gcp-env.sh"

# --- Guard. Any attempt to pass a lock flag through this script dies here.
# A locked GCS retention policy cannot be removed or shortened by anyone, ever,
# including the project owner. data-spec.md 7.3 tears these buckets down, and a
# locked 14d policy would block that for two weeks past the last write on a
# hackathon ending 2026-08-31. G8 asserts the policy EXISTS, not that it is
# locked. Immutability of promoted versions comes from objectCreator-without-
# overwrite plus versioning; retention is the belt to that suspenders.
for arg in "$@"; do
  case "$arg" in
    *lock-retention*)
      echo "REFUSED: --lock-retention-period is unrecoverable and would block the" >&2
      echo "         data-spec 7.3 teardown for 14 days." >&2
      exit 2 ;;
  esac
done

make_bucket () {
  local uri="$1"; shift
  if gcloud storage buckets describe "$uri" --format="value(name)" >/dev/null 2>&1; then
    echo "EXISTS  $uri  (skipping create)"
  else
    echo "CREATE  $uri"
    gcloud storage buckets create "$uri" \
      --project="$CRUCIBLE_PROJECT" \
      --location="$CRUCIBLE_REGION" \
      --uniform-bucket-level-access \
      --public-access-prevention \
      "$@"
  fi
}

# Uniform bucket-level access is ON for all three deliberately. With it OFF, an
# object ACL is a second grant path the gates' get-iam-policy grep cannot see --
# the check passes while the boundary leaks.

# Sealed: the G7 seal-integrity boundary.
make_bucket "$CRUCIBLE_SEALED_BUCKET"

# Policies: the G8 non-self-approval boundary. Retention + versioning give the
# IAM-enforced immutability Firestore cannot provide.
make_bucket "$CRUCIBLE_POLICIES_BUCKET" --retention-period=14d
gcloud storage buckets update "$CRUCIBLE_POLICIES_BUCKET" --versioning

# Evidence: transcripts and the final Firestore export. Not gated.
make_bucket "$CRUCIBLE_EVIDENCE_BUCKET"

echo
echo "=== POSTCONDITIONS (asserted, not assumed) ==="
for uri in "$CRUCIBLE_SEALED_BUCKET" "$CRUCIBLE_POLICIES_BUCKET" "$CRUCIBLE_EVIDENCE_BUCKET"; do
  gcloud storage buckets describe "$uri" \
    --format="value[separator='  |  '](name, location, uniform_bucket_level_access, public_access_prevention, retention_policy.retentionPeriod, retention_policy.isLocked, versioning_enabled)"
done
echo
echo "NOTE: isLocked must read empty or False. If it ever reads True, the"
echo "      policies bucket cannot be torn down until 14d past its last write."
