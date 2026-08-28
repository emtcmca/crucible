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

SEALED_EVAL = "crucible-sealed-eval@crucible-hack-2026.iam.gserviceaccount.com"

# Scope for read-only object access. Narrower than cloud-platform on purpose:
# the credential this runner holds should not be able to do anything the
# experiment does not require.
_RO = "https://www.googleapis.com/auth/devstorage.read_only"


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


def make_downloader(principal=SEALED_EVAL, client=None):
    """Return ONE callable: `download(uri) -> bytes`.

    `uri` is a full `gs://bucket/path` string. The callable performs exactly one
    `objects.get` per invocation and nothing else.

    `client` is injectable so tests can pass a double without a network or a
    credential. Production passes nothing and gets an impersonated read-only
    client.
    """
    if client is None:
        from google.cloud import storage
        creds = _impersonated_credentials(principal)
        client = storage.Client(credentials=creds,
                                project="crucible-hack-2026")

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
