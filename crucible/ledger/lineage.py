"""lineage.py - the policy-version hash chain. data-spec.md sections 2.3 and 2.5.

    lineage_hash_0 = SHA256("crucible/lineage/v1|" || run_id)
    lineage_hash_n = SHA256(lineage_hash_{n-1} || ":" || policy_hash_full_n
                            || ":" || uint32_be(n))

WHAT THE CHAIN IS FOR, AND WHAT IT IS NOT
-----------------------------------------
It converts "someone rewrote v3" from undetectable to detectable in one pass, and
it catches out-of-order or skipped promotions. A gap between v2 and v4 is exactly
what a silently-failed async write looks like, and the chain is what makes that
gap loud.

It is UNSIGNED. It does not defend against an adversary holding the Gate's
credentials, because such an adversary recomputes it. **IAM immutability is the
real control; the chain is the detector.** data-spec 2.4 says to state that
distinction out loud rather than claim more than we have, and this module's
docstring is where it lives so nobody has to go looking.

THE AMBIGUITY IN THE SPEC, AND HOW IT IS PINNED HERE
-----------------------------------------------------
`||` is concatenation, but data-spec 2.3 does not say what type each operand is.
`policy_hash_full` is DEFINED as `hex(SHA256(...))`, so it is text. `":"` is
text. `uint32_be(n)` is explicitly binary. `lineage_hash_{n-1}` is the output of
SHA256, which is raw bytes unless something hexes it. And the STORED field is
16 hex characters ("b18c94ff2ad60e51"), which is a truncation of neither operand
form without saying so.

Three self-consistent readings exist and they produce different chains. Left
unpinned, two implementations agree on every other test and disagree here, and
the disagreement surfaces as `lineage_ok: false` on a chain nobody tampered with.

**Pinned, with the reasoning:** each operand is used in the form the spec
literally gives it.

    lineage_hash_n   RAW 32 BYTES internally      (SHA256's own output)
    policy_hash_full 64-char ASCII hex            (defined as hex(...))
    ":"              one ASCII byte
    uint32_be(n)     4 raw big-endian bytes       (defined as binary)
    stored/display   hex(lineage_hash)[0:16]      (matches the spec's examples)

Reported to the coordinator as a contract clarification, and frozen by the
vectors in tests/test_lineage.py so a second implementation cannot drift.
"""

import hashlib
import struct

LINEAGE_DOMAIN = b"crucible/lineage/v1|"
STORED_LEN = 16


class LineageError(ValueError):
    """A chain defect. Carries `code`, `version`, and what was expected."""

    def __init__(self, code, detail, version=None):
        self.code = code
        self.version = version
        self.detail = detail
        super().__init__("%s%s: %s" % (
            code, "" if version is None else " at v%d" % version, detail))


def genesis(run_id: str) -> bytes:
    """lineage_hash_0. Domain-separated so a lineage digest can never collide
    with a policy digest computed over bytes that happen to look like a run id."""
    if not run_id:
        raise LineageError("E_NO_RUN_ID", "the chain is rooted in the run id")
    return hashlib.sha256(LINEAGE_DOMAIN + run_id.encode("utf-8")).digest()


def step(prev: bytes, policy_hash_full: str, n: int) -> bytes:
    """One link. `n` is the policy version number, from 1."""
    if len(prev) != 32:
        raise LineageError("E_BAD_PREV", "previous link is %d bytes, not 32"
                           % len(prev), n)
    if len(policy_hash_full) != 64 or not all(
            c in "0123456789abcdef" for c in policy_hash_full):
        raise LineageError("E_BAD_POLICY_HASH",
                           "expected 64 lowercase hex chars, got %r"
                           % (policy_hash_full[:20],), n)
    if n < 1 or n > 0xFFFFFFFF:
        raise LineageError("E_BAD_VERSION", "version %r out of range" % (n,), n)
    return hashlib.sha256(
        prev + b":" + policy_hash_full.encode("ascii") + b":"
        + struct.pack(">I", n)).digest()


def stored(link: bytes) -> str:
    """The 16-hex-char form written to the ledger and to `head_lineage_hash`."""
    return link.hex()[:STORED_LEN]


def build(run_id: str, policy_hashes) -> list:
    """Whole chain from genesis. Returns [(version, link_bytes, stored_str), ...]
    with version 0 as genesis and version n as the nth promotion."""
    out = [(0, genesis(run_id), stored(genesis(run_id)))]
    prev = out[0][1]
    for i, ph in enumerate(policy_hashes, start=1):
        prev = step(prev, ph, i)
        out.append((i, prev, stored(prev)))
    return out


def verify(run_id: str, versions, head_lineage_hash=None):
    """Verify a chain and return a per-version report.

    `versions` is an ordered sequence of dicts, each carrying at least:
        version            int, from 1
        policy_hash_full   64 hex chars, RECOMPUTED FROM BYTES by the caller
        parent_hash        the previous version's policy_hash (16 or 64 hex)
        lineage_hash       the stored 16-hex-char link

    Raises LineageError on the FIRST defect, naming the version and the check.
    Returning a list of problems instead was considered and rejected: a chain is
    only meaningful up to its first break, and reporting five downstream
    mismatches caused by one edited version reads as five problems.
    """
    if not versions:
        raise LineageError("E_EMPTY", "no policy versions to verify")

    prev_link = genesis(run_id)
    prev_policy = None
    report = []

    for i, v in enumerate(versions):
        n = v["version"]
        expected_n = i + 1
        if n != expected_n:
            # A gap between v2 and v4 is what a silently-failed async write looks
            # like. Making that loud is half the reason the chain exists.
            raise LineageError(
                "E_VERSION_GAP",
                "expected version %d, found %d - a gap is what a silently "
                "failed promotion looks like" % (expected_n, n), n)

        if prev_policy is not None:
            got_parent = v.get("parent_hash") or ""
            if not prev_policy.startswith(got_parent) or not got_parent:
                raise LineageError(
                    "E_PARENT_MISMATCH",
                    "parent_hash %r does not match v%d's policy hash %r"
                    % (got_parent, n - 1, prev_policy[:16]), n)
        elif v.get("parent_hash"):
            raise LineageError("E_ROOT_HAS_PARENT",
                               "v1 declares a parent", n)

        link = step(prev_link, v["policy_hash_full"], n)
        want = stored(link)
        if v.get("lineage_hash") != want:
            raise LineageError(
                "E_LINEAGE_MISMATCH",
                "stored lineage_hash %r, recomputed %r. Something rewrote this "
                "version without recomputing the chain"
                % (v.get("lineage_hash"), want), n)

        report.append({"version": n, "policy_hash": v["policy_hash_full"][:16],
                       "parent": v.get("parent_hash") or "-", "lineage": want,
                       "status": "OK"})
        prev_link = link
        prev_policy = v["policy_hash_full"]

    if head_lineage_hash is not None and head_lineage_hash != stored(prev_link):
        raise LineageError(
            "E_HEAD_MISMATCH",
            "run head_lineage_hash %r, chain ends at %r"
            % (head_lineage_hash, stored(prev_link)), versions[-1]["version"])

    return report
