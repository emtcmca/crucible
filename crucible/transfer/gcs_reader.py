"""gcs_reader.py - one downloader, built once, calibrated and then used.

THE WHOLE POINT OF THIS FILE IS THAT THERE IS ONE CALLABLE
-----------------------------------------------------------------------------
`f4-unseal-preregistration-2026-08-25.md` A3.2 fixes the G7c expected value as a
count of granted `storage.objects.get` entries inside the run's own window, and
requires it be CALIBRATED against the canary through the runner's own read path
rather than assumed. That requirement is only meaningful if the thing calibrated
and the thing used are the same object. Two callables that "both download a
blob" can emit different numbers of audit entries, and the difference is not
visible from the call site.

So: `make_downloader()` returns ONE callable. The calibration passes it the
canary. The run passes it the twenty four sealed objects. Nothing else in the
transfer path is allowed to touch GCS.

**AND THAT WAS AN INSTRUCTION IN A DOCSTRING, WHICH IS WORTH NOTHING ON A RUN
THAT HAPPENS ONCE.** Two `make_downloader()` calls are two callables and the
call site cannot see the difference. `open_calibrated_downloader` at the bottom
of this file builds the client and calibrates it in ONE call, and returns the
`holdout_assert.CalibratedDownloader` that every downstream assertion demands by
type. `make_downloader` remains, because the client has to be built somewhere
and tests inject one - but it is no longer the entry point the transfer run
uses.

WHAT IT DOES NOT DO, EACH FOR A MEASURED REASON
-----------------------------------------------------------------------------
  * **No `exists()`, `reload()`, `get_blob()`, or `blob.size`.** On the wire
    every one of those is `storage.objects.get`, which
    `infra/holdout_touch.classify` counts as a CONTENT_READ. A single
    convenience call before the download doubles the count and fails G7c's exact
    comparison at the END of the run, which under the crash rule is INVALID with
    no retry.
  * **`retry=None`.** `Blob.download_as_bytes` has a retry policy enabled by
    default. A transparently retried GET is a second audit entry that no
    expected value predicted. Better to fail loudly on a transient error before
    any episode has scored than to silently read twice and be refused after
    twenty four episodes have.
  * **No `list_blobs` to discover names.** `storage.objects.list` classifies as
    ENUMERATION and is NOT counted, so listing is actually safe - but the names
    come from the published commitment so that the read set is fixed before the
    network is touched, rather than being whatever the bucket happens to hold.

IMPERSONATION IS NOT OPTIONAL
-----------------------------------------------------------------------------
Section 3 step 0 of the pre-registration: the unseal read runs as
`crucible-sealed-eval`, the sole member of `permitted_principals`. A read
performed as the human operator lands in the audit log as an unattested
intruder read and marks the run INVALID. The operator holds `roles/owner`, so
this is a mistake the credentials permit and only the code prevents.
"""

from __future__ import annotations

import os

from infra import verify_iam


def _repo_root():
    """This file is `<repo>/crucible/transfer/gcs_reader.py`. Three levels up.

    Derived, not passed, so `scripts/gcp-env.sh` can be sourced without every
    caller having to know where the repository is - the same shape
    `infra/holdout_touch._record_path` uses.
    """
    here = os.path.abspath(__file__)
    return os.path.dirname(os.path.dirname(os.path.dirname(here)))


# Scope for read-only object access. Narrower than cloud-platform on purpose:
# the credential this runner holds should not be able to do anything the
# experiment does not require.
_RO = "https://www.googleapis.com/auth/devstorage.read_only"

# THE CANARY OBJECT, AND ITS PATH IS NOT THE ONE THE OLD FIXTURES SHOW.
# `docs/NEEDS-ERIC.md` item 12: Eric ruled 2026-08-22 that the canary be MOVED
# rather than excluded from the counter, and it was executed the same day and
# verified against the live bucket 2026-08-23 (`real_gate.py:512-516`):
#
#     was:  <sealed bucket>/families/_probe/canary.txt
#     now:  <sealed bucket>/_probe/canary.txt
#
# Exclusion was rejected because it would have meant the gate declaring which
# reads do not count, which is self-certification one layer over from what G8
# exists to prevent. Relocation removed the need for the rule. The `families/`
# spelling still appears in `infra/holdout_touch.py`'s docstring and in the live
# test fixture; those record a read that HAPPENED on 2026-08-22, before the
# move, and are correct as history. This constant is where a read performed
# TODAY gets its path.
CANARY_OBJECT = "_probe/canary.txt"


def sealed_eval_principal(env=None, repo_root=None):
    """The one identity permitted to read the holdout, SOURCED not retyped.

    This module carried the fully-qualified email as a literal until 2026-08-29.
    `scripts/gcp-env.sh` is the single source for every infrastructure name, and
    G7/G8 grep these strings literally - so a second copy does not fail loudly
    when it drifts, it produces an unevaluable gate, and an unevaluable gate is
    a check that cannot fail (`measurement-spec.md:813`). Same construction
    `infra/holdout_touch.py` uses for `permitted_principals`, so the identity
    that reads and the identity the counter permits are one derivation.
    """
    env = env or verify_iam.load_env(repo_root or _repo_root())
    return "%s@%s.iam.gserviceaccount.com" % (env["SA_SEALED_EVAL"],
                                              env["CRUCIBLE_PROJECT"])


def canary_uri(bucket):
    """`gs://<sealed bucket>/_probe/canary.txt`, from a SOURCED bucket name."""
    return "%s/%s" % (bucket.rstrip("/"), CANARY_OBJECT)


class GcsReadError(RuntimeError):
    """A sealed read failed. Never swallowed: a missing object is a different
    experiment, not a smaller one."""


def _impersonated_credentials(principal, lifetime=900):
    import google.auth
    from google.auth import impersonated_credentials

    source, _project = google.auth.default()
    return impersonated_credentials.Credentials(
        source_credentials=source,
        target_principal=principal,
        target_scopes=[_RO],
        lifetime=lifetime)


def make_downloader(principal=None, client=None, env=None, repo_root=None):
    """Return ONE callable: `download(uri) -> bytes`.

    `uri` is a full `gs://bucket/path` string. The callable performs exactly one
    `objects.get` per invocation and nothing else.

    `principal` defaults to the SOURCED `crucible-sealed-eval` identity rather
    than to a retyped literal; see `sealed_eval_principal`.

    `client` is injectable so tests can pass a double without a network or a
    credential. Production passes nothing and gets an impersonated read-only
    client.

    **THIS IS NOT THE FUNCTION THE TRANSFER RUN CALLS.** A downloader obtained
    here is uncalibrated, and every second call to this function is a SECOND
    callable - which is how "the calibration and the run used the same read
    path" quietly stops being true. Use `open_calibrated_downloader` below,
    which builds one and calibrates it in a single call that cannot be split.
    """
    if client is None:
        from google.cloud import storage
        env = env or verify_iam.load_env(repo_root or _repo_root())
        principal = principal or sealed_eval_principal(env)
        client = storage.Client(credentials=_impersonated_credentials(principal),
                                project=env["CRUCIBLE_PROJECT"])

    def download(uri):
        if not uri.startswith("gs://"):
            raise GcsReadError("expected a gs:// uri, got %r" % uri)
        rest = uri[len("gs://"):]
        bucket_name, _, blob_path = rest.partition("/")
        if not blob_path:
            raise GcsReadError("uri names no object: %r" % uri)

        # `bucket()` and `blob()` are CONSTRUCTORS. Neither performs a request,
        # which is why they are safe here and `get_blob()` is not.
        blob = client.bucket(bucket_name).blob(blob_path)
        try:
            # THE ONLY REQUEST THIS FUNCTION MAKES.
            return blob.download_as_bytes(retry=None)
        except Exception as exc:                             # noqa: BLE001
            raise GcsReadError(
                "read failed for %s: %s. NOT retried, deliberately: a retry is "
                "a second audit entry and the expected count was fixed before "
                "the run. Halt here, record the touch count, and treat it under "
                "the pre-registration's crash rule." % (uri, exc))

    return download


def open_calibrated_downloader(counter, bucket, principal=None, client=None,
                               env=None, repo_root=None, settle=None,
                               clock=None):
    """Build the read path and calibrate it, in ONE call. Returns the callable.

    THE POINT IS THAT THIS CANNOT BE SPLIT. `make_downloader()` followed later
    by a calibration is two statements, and between them is the gap where a
    second `make_downloader()` gets built and the run reads through a path
    nothing measured. Here the object that is calibrated is the object that is
    returned, and it is the only one that exists.

    `counter` is a `HoldoutTouchCounter` over the CALIBRATION's own window, not
    the run's - the canary read is a granted content read and would otherwise
    sit inside the count this run claims as its own. Open the run window after
    this returns, with `holdout_assert.open_run_window(calibration)`.

    Returns a `holdout_assert.CalibratedDownloader`. Hand that object onward to
    `sealed_io.read_sealed_once`; `holdout_assert.require_calibrated` refuses
    anything else.
    """
    from crucible.transfer.holdout_assert import calibrate_on_canary

    env = env or verify_iam.load_env(repo_root or _repo_root())
    raw = make_downloader(principal=principal, client=client, env=env)
    return calibrate_on_canary(counter, raw, canary_uri(bucket),
                               settle=settle, clock=clock)


__all__ = [
    "CANARY_OBJECT", "GcsReadError", "canary_uri", "make_downloader",
    "open_calibrated_downloader", "sealed_eval_principal",
]
