"""promote.py - the promotion gate's write path, with read-back.

A promotion is not complete when the write returns. It is complete when the
bytes are READ BACK and the hash is RECOMPUTED FROM THOSE BYTES.

WHY RECOMPUTING FROM BYTES IS THE ENTIRE POINT
-----------------------------------------------
data-spec.md 2.5 step 3, parenthetically and correctly: *"recomputing from bytes
is the point - comparing a stored hash to itself proves nothing."*

The tempting version of this function writes the payload, reads back the stored
`policy_hash` field, compares it to the `policy_hash` field it just wrote, and
reports OK. That check passes on a truncated write, on a partial write, on a
write that landed in the wrong object, and on a corrupted read - because in every
one of those cases it is comparing a value to itself. It is a check that cannot
fail, dressed as integrity verification.

So: read the BYTES back, canonicalize them, hash them, and compare that to the
name and to the field. The three must agree.

The gate is PURE CODE and holds no model access, by IAM (`crucible-gate` has no
`aiplatform.user`). It cannot reason; it can only evaluate.
"""

import hashlib

from ..canon import CanonicalizationError, canonicalize_bytes
from ..ledger import lineage


class PromotionError(RuntimeError):
    def __init__(self, code, detail):
        self.code = code
        self.detail = detail
        super().__init__("%s: %s" % (code, detail))


def object_name(run_id, version, policy_hash_full):
    """The GCS object path. `run_id` lives HERE, outside the hashed payload -
    so the same policy authored in two runs still hashes identically, which is
    what convergence-by-hash-equality and the resume key both depend on."""
    return "runs/%s/policy/v%03d-%s.json" % (run_id, version, policy_hash_full[:16])


def compute_policy_hash(payload_bytes):
    """Canonicalize, then hash. Never hash the bytes as they arrived: two
    equivalent spellings of the same policy must produce one hash, which is the
    only reason a hash can detect a real change."""
    return hashlib.sha256(canonicalize_bytes(payload_bytes)).hexdigest()


def promote(store, run_id, payload_bytes, promoted_by, promoted_at,
            manifest_hash, blob_writer, blob_reader):
    """Promote one policy version.

    `blob_writer(name, data)` and `blob_reader(name) -> bytes` are injected so
    this is testable offline and so the same code path runs against GCS and
    against a local directory. The gate does not know which it is talking to,
    which is what lets a corrupted read-back be tested at all.
    """
    if promoted_by != "crucible-gate":
        # The identity that authors a candidate is not the identity that
        # promotes it. This is the code half of the boundary G8 asserts in IAM;
        # neither half is sufficient alone, and the IAM half is the real one.
        raise PromotionError(
            "E_WRONG_PROMOTER",
            "%r attempted a promotion. The promoter is crucible-gate. If the "
            "author can promote, the separation was never real." % promoted_by)

    try:
        canonical = canonicalize_bytes(payload_bytes)
    except CanonicalizationError as e:
        raise PromotionError("E_NOT_CANONICALIZABLE", str(e)) from None

    policy_hash_full = hashlib.sha256(canonical).hexdigest()
    version = store.next_version(run_id)
    head = store.head(run_id)
    parent_hash = head["policy_hash"] if head else None

    if head and head["policy_hash_full"] == policy_hash_full:
        # Not an error. Hash equality with the head IS the convergence signal -
        # the Armorer proposed a policy identical to the one already in force.
        raise PromotionError(
            "E_CONVERGED",
            "the proposed policy hashes identically to v%d. This is the "
            "convergence signal, not a failure: there is nothing left to add."
            % head["version"])

    prev_link = (lineage.genesis(run_id) if head is None
                 else bytes.fromhex(_full_link(store, run_id)))
    link = lineage.step(prev_link, policy_hash_full, version)

    name = object_name(run_id, version, policy_hash_full)

    # --- write ------------------------------------------------------------
    blob_writer(name, canonical)

    # --- READ BACK. The write's return value is not evidence. --------------
    try:
        got = blob_reader(name)
    except Exception as e:
        raise PromotionError(
            "E_READBACK_FAILED",
            "wrote %s but could not read it back: %s. A write whose result was "
            "never observed is not a promotion." % (name, e)) from None

    recomputed = compute_policy_hash(got)

    if recomputed != policy_hash_full:
        raise PromotionError(
            "E_READBACK_HASH_MISMATCH",
            "wrote %s expecting %s, but the bytes on the far side canonicalize "
            "to %s. Comparing the stored hash field to itself would have passed "
            "here - that is why this recomputes from the bytes."
            % (name, policy_hash_full[:16], recomputed[:16]))

    if recomputed[:16] not in name:
        raise PromotionError(
            "E_NAME_HASH_MISMATCH",
            "the object name %r does not carry the hash of its own contents "
            "(%s). The name is an index; if it disagrees with the bytes, one of "
            "them is a lie and a reader has no way to tell which."
            % (name, recomputed[:16]))

    store.append_version(
        run_id=run_id, version=version, policy_hash_full=policy_hash_full,
        parent_hash=parent_hash, lineage_hash=lineage.stored(link),
        manifest_hash=manifest_hash, promoted_by=promoted_by,
        promoted_at=promoted_at, payload_bytes=canonical)

    _remember_link(store, run_id, link)
    return {"version": version, "policy_hash_full": policy_hash_full,
            "policy_hash": policy_hash_full[:16],
            "lineage_hash": lineage.stored(link), "object": name}


# The stored lineage_hash is TRUNCATED to 16 hex chars (data-spec 2.3's own
# examples), but the chain step needs the full 32-byte digest. Rebuilding the
# chain from genesis on every promotion is O(n) in versions and n is capped at
# the round limit of 6, so it is cheaper than carrying a second stored field
# that could disagree with the first. A second copy of a hash is a second source
# of truth.
_LINKS = {}


def _remember_link(store, run_id, link):
    _LINKS[(id(store), run_id)] = link.hex()


def _full_link(store, run_id):
    cached = _LINKS.get((id(store), run_id))
    if cached:
        return cached
    chain = lineage.build(run_id, [v["policy_hash_full"]
                                   for v in store.versions(run_id)])
    return chain[-1][1].hex()
