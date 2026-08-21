"""bundle.py - reading and writing the C6 evidence bundle, offline.

THE READER REFUSES. That is its whole contract. `read_bundle` either returns a
bundle every check has cleared, or raises `BundleRejected` naming the field and
the episode. It never returns a bundle with a hole in it, because a viewer that
renders a blank where a hash belongs publishes something that LOOKS like
evidence, and looking like evidence is worse than failing to open.

WHY THE DIGEST LIVES IN A SIDECAR AND NOT IN THE BUNDLE
-------------------------------------------------------
The digest of a document cannot live inside the document - adding it changes the
bytes it is a digest of. C6 also sets `additionalProperties: false`, so there is
nowhere to put it even if the arithmetic worked. `write_bundle` therefore writes
two files: the canonical bytes, and `<name>.sha256` beside them. The reader
recomputes the digest FROM THE BYTES IT JUST READ and compares. Reading a stored
digest out of the same file and comparing it to itself would pass on a truncated
write, a partial write, and a corrupted read.

WHY THE FILE IS WRITTEN IN CANONICAL FORM
------------------------------------------
`contracts/canonicalization.md`: UTF-8 with no BOM, keys ordered by UTF-16 code
unit, no whitespace, no trailing newline, integers only, no `null`. Writing the
bundle that way means two runs that produced the same evidence produce the same
bytes and therefore the same digest, on any machine, in any key order the
producing code happened to use. It also means the file cannot be casually
hand-edited without the digest moving, which is the point of having one.

The cost, stated: the file is one very long line and is unpleasant to read in an
editor. That is what the viewer is for, and `--json` prints an indented copy for
anyone who wants to diff it.
"""

import hashlib
import json
import pathlib

from crucible.canon import CanonicalizationError, canonicalize, canonicalize_bytes

from .integrity import BundleRejected, Defect, c6_validator, verify_bundle

SIDECAR_SUFFIX = ".sha256"


def read_bundle_bytes(raw, source="<bytes>"):
    """Parse and verify. Returns `(bundle, report)` or raises `BundleRejected`.

    The parse goes through `canonicalize_bytes` FIRST, before `json.loads`,
    because that is the only path that can see the two failures a Python object
    has already lost: a byte-order mark, and a duplicate key. `json.loads` keeps
    the last duplicate silently, which would let two different documents produce
    identical bytes - a hash collision we manufactured ourselves.
    """
    if isinstance(raw, str):
        raise TypeError("read_bundle_bytes takes bytes; a str has already lost "
                        "the BOM question, which is the one restriction 1 asks")
    try:
        canonicalize_bytes(raw)
    except CanonicalizationError as exc:
        raise BundleRejected([Defect(getattr(exc, "code", "E_CANON"), source, str(exc))])

    try:
        bundle = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:   # pragma: no cover - canon first
        raise BundleRejected([Defect("E_NOT_JSON", source, str(exc))])

    report = verify_bundle(bundle)
    if not report.ok:
        raise BundleRejected(report.defects)
    return bundle, report


def read_bundle(path):
    """Read a bundle from disk. Reads only from disk; opens no socket, reads no
    credential, and consults no environment variable.

    If a `<name>.sha256` sidecar sits beside the file, the digest is RECOMPUTED
    from the bytes just read and must agree with it.
    """
    path = pathlib.Path(path)
    raw = path.read_bytes()
    bundle, report = read_bundle_bytes(raw, source=path.name)

    sidecar = path.with_name(path.name + SIDECAR_SUFFIX)
    if sidecar.exists():
        recorded = sidecar.read_text(encoding="utf-8").split()[0].strip().lower()
        recomputed = hashlib.sha256(canonicalize(bundle)).hexdigest()
        if recorded != recomputed:
            raise BundleRejected([Defect(
                "E_DIGEST_MISMATCH", sidecar.name,
                "the sidecar records %s; the bytes on disk canonicalize to %s. "
                "The digest is recomputed from the bytes rather than read out "
                "of the bundle, because comparing a stored hash to itself "
                "passes on a truncated write, a partial write, and a corrupted "
                "read." % (recorded[:16], recomputed[:16]))])
    return bundle, report


def write_bundle(bundle, path, sidecar=True):
    """Write a bundle in canonical form, plus its digest sidecar.

    Verifies BEFORE writing. Writing an evidence bundle that would not survive
    being read back is how a run ends up with a directory full of files nobody
    can use, discovered on the day of the demo.
    """
    report = verify_bundle(bundle)
    if not report.ok:
        raise BundleRejected(report.defects)

    path = pathlib.Path(path)
    blob = canonicalize(bundle)
    path.write_bytes(blob)
    digest = hashlib.sha256(blob).hexdigest()
    if sidecar:
        path.with_name(path.name + SIDECAR_SUFFIX).write_text(
            "%s  %s\n" % (digest, path.name), encoding="utf-8")
    return digest


__all__ = ["BundleRejected", "c6_validator", "read_bundle", "read_bundle_bytes",
           "write_bundle", "SIDECAR_SUFFIX"]
