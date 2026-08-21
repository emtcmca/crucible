#!/usr/bin/env bash
# Create the eleven CRUCIBLE service accounts. Idempotent: skips any that exist.
#
# Names come from scripts/gcp-env.sh and are NEVER retyped here. G7 and G8 grep
# these literal strings out of an IAM policy, so a typo does not fail loudly --
# it produces an unevaluable gate, and an unevaluable gate is a check that
# cannot fail (measurement-spec.md:813).
#
# THIS SCRIPT GRANTS NOTHING. Creation and binding are deliberately separate
# steps in separate files, because the failure this project cares most about is
# a grant made in the wrong direction, and a grant buried inside a create loop
# is a grant nobody reads. Bindings live in infra/bind-iam.sh, one explicit line
# each, with the reasoning attached.
#
# Run:  bash infra/create-service-accounts.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
. "$HERE/scripts/gcp-env.sh"

# data-spec.md 4.1, rows 1-11. The description is the ROLE, not the grant --
# it shows up in the console next to an identity somebody may later be tempted
# to widen, and the thing they need to see there is what it is FOR.
describe() {
  case "$1" in
    crucible-orchestrator) echo "Conductor. Dispatches episodes, writes the ledger. Cannot create a policy version." ;;
    crucible-red)          echo "Red Strategist. Attacker. Deliberately holds NO Firestore, GCS or BQ role." ;;
    crucible-target)       echo "Target agent under test. Money-moving tools are simulated." ;;
    crucible-tripwire)     echo "Tripwire, pure code. Holds NO aiplatform.user: it cannot call a model." ;;
    crucible-coroner)      echo "Coroner. Writes autopsies. No GCS: cannot write a policy version." ;;
    crucible-armorer)      echo "Armorer. Emits policy patches. NO storage.* and NO bigquery.* of any kind." ;;
    crucible-warden)       echo "Regression Warden, pure code. No aiplatform.user: the fixture judge cannot call a model." ;;
    crucible-gate)         echo "Promotion Gate, pure code. The ONLY identity that may create a policy version." ;;
    crucible-sealed-eval)  echo "Sealed Evaluator. Reads the sealed family. Cannot write to policies." ;;
    crucible-bq-writer)    echo "Telemetry sink. No sealed dataset, no Firestore write." ;;
    crucible-ui)           echo "Demo UI. Read-only everywhere. No sealed bucket or dataset." ;;
    *)                     echo "CRUCIBLE component" ;;
  esac
}

# GCP rate-limits service-account creation PER MINUTE PER PROJECT, and eleven in
# a loop trips it -- observed 2026-08-20 on the sixth account:
#
#   429 RESOURCE_EXHAUSTED "Service accounts created per minute per project"
#   RetryInfo retryDelay: 60s
#
# Recorded here because the failure is invisible in a teardown-and-recreate at
# demo time, and because the naive fix (drop back to seven accounts) would have
# silently reintroduced the four-name gap this file's inputs just closed.
create_with_backoff() {
  local sa="$1" attempt=1 delay=65 err
  while :; do
    if err="$(gcloud iam service-accounts create "$sa" \
                --project="$CRUCIBLE_PROJECT" \
                --display-name="CRUCIBLE ${sa#crucible-}" \
                --description="$(describe "$sa")" 2>&1 >/dev/null)"; then
      return 0
    fi
    case "$err" in
      *RESOURCE_EXHAUSTED*|*429*)
        if [ "$attempt" -ge 4 ]; then
          echo "$err" >&2
          return 1
        fi
        printf "  wait    %s rate-limited, retrying in %ss (attempt %d)\n" \
               "$sa" "$delay" "$attempt"
        sleep "$delay"
        attempt=$((attempt + 1))
        ;;
      *) echo "$err" >&2; return 1 ;;
    esac
  done
}

echo "project: $CRUCIBLE_PROJECT"
CREATED=0
SKIPPED=0
for sa in $CRUCIBLE_ALL_SAS; do
  email="$(sa_email "$sa")"
  if gcloud iam service-accounts describe "$email" \
        --project="$CRUCIBLE_PROJECT" >/dev/null 2>&1; then
    printf "  skip    %s\n" "$sa"
    SKIPPED=$((SKIPPED + 1))
  else
    create_with_backoff "$sa"
    printf "  created %s\n" "$sa"
    CREATED=$((CREATED + 1))
  fi
done

echo ""
echo "created=$CREATED skipped=$SKIPPED"
echo ""

# --- POSTCONDITION. Read every one back individually. -----------------------
# A gcloud exit code is not evidence. It has printed success while throwing.
echo "read-back:"
MISSING=0
for sa in $CRUCIBLE_ALL_SAS; do
  email="$(sa_email "$sa")"
  got="$(gcloud iam service-accounts describe "$email" \
          --project="$CRUCIBLE_PROJECT" --format='value(email)' 2>/dev/null || true)"
  if [ "$got" = "$email" ]; then
    printf "  ok      %s\n" "$got"
  else
    printf "  MISSING %s\n" "$email"
    MISSING=$((MISSING + 1))
  fi
done

if [ "$MISSING" -ne 0 ]; then
  echo "" >&2
  echo "FAILED: $MISSING service account(s) do not exist after creation." >&2
  exit 1
fi
echo ""
echo "ALL 11 PRESENT. No roles granted by this script -- see infra/bind-iam.sh."
