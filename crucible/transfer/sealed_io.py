"""sealed_io.py - the ONLY path from this repository to the sealed holdout.

WHY THIS IS A SEPARATE MODULE AND NOT A FLAG ON THE TRAINING LOADER
-------------------------------------------------------------------
`crucible/conductor/corpus_seeds.py` hardcodes `TRAINING_LAYOUT` to the training
bucket alone and raises `E_SEALED_FAMILY_REACHED` on any instance whose family is
the sealed one. Those two guards are the reason a training run cannot reach F4,
and **neither is touched here.** A flag on that loader would make the guards
conditional, and a conditional guard is one bad argument away from being no
guard. So the transfer path is a different module with a different door, and the
training loader keeps refusing F4 forever.

THE READ DISCIPLINE, AND EVERY CLAUSE OF IT IS LOAD-BEARING
-------------------------------------------------------------------
G7c compares a count of granted `storage.objects.get` audit entries against an
expected value, with EXACT equality, and a mismatch sets `invalidates=True` at
the END of a run - after episodes have scored, which under the unseal
pre-registration's crash rule is INVALID with no retry. So every avoidable read
is a way to lose the single attempt.

  * ONE `download_as_bytes` per object. Nothing else.
  * `retry=None`. The client's default retry policy can re-issue a GET, and a
    retried read is a second audit entry that no expected value predicted.
  * NO `exists()`, NO `reload()`, NO `get_blob()`, NO `blob.size`. Every one of
    those is ALSO `storage.objects.get` on the wire. `list_blobs` is
    `storage.objects.list`, which `infra/holdout_touch.classify` files as
    ENUMERATION and does not count - so listing is safe and reading metadata is
    not, which is the opposite of the intuition.
  * The object names are computed from the commitment, not discovered by
    listing, so the read set is decided before the network is touched.

WHAT THIS MODULE REFUSES TO DO
-------------------------------------------------------------------
It does not score, evaluate, drive a model, or write a bundle. It hands back
bytes and a fingerprint. A module that both opens the seal and judges what came
out is the coroner/armorer separation collapsed into one object, and this
repository has one rule about that.
"""

from __future__ import annotations

import hashlib
import json
import re

# The commitment is the source of truth for HOW MANY and WHICH. Never a listing.
COMMITMENT = "docs/proof/sealed-family-commitment.json"

# `seal-commitment.py` documents the algorithm and owns it. This module
# reproduces it over bytes fetched from GCS rather than off a directory, and the
# two are asserted equal by the caller. A second implementation of a hash is a
# second answer, so this one exists only because the bytes never land on disk.
_ALGORITHM = ("sha256 over, for each file sorted by name: the UTF-8 filename "
              "bytes, then the file bytes with CRLF normalized to LF")

_SAFE_NAME = re.compile(r"^F4-dest-\d{2}-[a-z0-9-]+\.json$")


class SealedReadError(RuntimeError):
    """Raised instead of returning partial content. There is no partial read of
    a holdout: 23 of 24 objects is not a smaller experiment, it is a different
    one with an undeclared denominator."""


def expected_object_names(instance_ids):
    """The exact object names this run will read, decided before any network
    call so the assertion set is fixed in advance rather than fitted to what
    came back."""
    names = sorted(instance_ids)
    for n in names:
        if not _SAFE_NAME.match(n):
            raise SealedReadError(
                "refusing to read %r: it does not match the sealed instance "
                "name shape. A name that reached here from anywhere but the "
                "commitment is a path this module will not walk." % n)
    return names


def fingerprint_from_bytes(pairs):
    """`pairs` is an ordered sequence of (name, raw_bytes), sorted by name.

    Mirrors `scripts/seal-commitment.py:fingerprint` exactly, over bytes rather
    than over a directory. The caller asserts this equals the published value.
    """
    h = hashlib.sha256()
    for name, raw in pairs:
        h.update(name.encode("utf-8"))
        h.update(raw.replace(b"\r\n", b"\n"))
    return h.hexdigest()


def read_sealed_once(bucket, names, downloader):
    """Read each named object EXACTLY once and return `[(name, bytes), ...]`.

    `downloader` is injected rather than constructed here, for the same reason
    `RealGate` takes `holdout_touch` with no default: a module that builds its
    own client is a module whose read path cannot be calibrated against the
    canary before it is pointed at the holdout. The caller passes the SAME
    callable it calibrated with, or the calibration measured a different thing
    than the run performs.

    Returns pairs sorted by name. Raises rather than returning a short read.
    """
    seen = {}
    for name in names:
        if name in seen:
            raise SealedReadError(
                "duplicate read attempted for %s. The expected audit count is "
                "one entry per object; a second read of the same object makes "
                "G7c's integer right for the wrong reason." % name)
        raw = downloader("%s/families/%s" % (bucket.rstrip("/"), name))
        if not isinstance(raw, (bytes, bytearray)):
            raise SealedReadError(
                "downloader returned %s for %s, expected bytes. Decoding before "
                "hashing would normalise the bytes the commitment covers."
                % (type(raw).__name__, name))
        seen[name] = bytes(raw)
    missing = [n for n in names if n not in seen]
    if missing:
        raise SealedReadError("short read: %d object(s) never arrived: %s"
                              % (len(missing), missing[:3]))
    return [(n, seen[n]) for n in sorted(seen)]


def parse_instances(pairs):
    """Bytes to instance dicts, with the family assertion the training loader
    would have made. An object that is not F4 has no business in this read."""
    out = []
    for name, raw in pairs:
        try:
            inst = json.loads(raw.decode("utf-8"))
        except Exception as exc:                             # noqa: BLE001
            raise SealedReadError("%s is not readable JSON: %s" % (name, exc))
        fam = inst.get("family_id") or inst.get("family")
        if fam not in ("fam_f4", "F4"):
            raise SealedReadError(
                "%s declares family %r. This module reads the sealed family "
                "and nothing else; a non-F4 instance here means the read set "
                "was wrong before the network was touched." % (name, fam))
        out.append(inst)
    return out
