"""test_ledger_gate.py - the lineage chain, the append-only ledger, and the
promotion gate's read-back.

The centrepiece is `test_a_deliberately_corrupted_readback_is_caught`, which is
an L1 exit criterion. Everything else here exists so that test cannot pass for
an uninteresting reason.
"""

import json

import pytest

from crucible.canon import canonicalize
from crucible.gate import PromotionError, compute_policy_hash, promote
from crucible.ledger import Ledger, LineageError, build, genesis, lineage, step, stored, verify

RUN = "run_20260820_120000_abc123"
NOW = "2026-08-20T12:00:00Z"
LOCKS = {"manifest_hash": "m" * 16, "objective_set_hash": "o" * 16,
         "gate_rule_hash": "g" * 16, "target_hash": "t" * 16}


def payload(n_rules=1, threshold=50000):
    return {
        "policy_schema_version": 1,
        "target_manifest_hash": LOCKS["manifest_hash"],
        "rules": [{"rule_id": "r_%012d" % i, "verb": "deny",
                   "cap_selector": "CAP_MOVES_MONEY",
                   "when": [{"path": "amount_minor", "op": "gt",
                             "value": threshold + i}]}
                  for i in range(n_rules)],
    }


def blob_store():
    """An in-memory blob store plus the two injected callables the gate uses."""
    blobs = {}

    def writer(name, data):
        blobs[name] = data

    def reader(name):
        if name not in blobs:
            raise KeyError(name)
        return blobs[name]

    return blobs, writer, reader


@pytest.fixture()
def led():
    with Ledger(":memory:") as l:
        l.open_run(RUN, NOW, LOCKS)
        yield l


# --------------------------------------------------------------------------
# Lineage. The operand-type ambiguity in data-spec 2.3 is pinned by these.
# --------------------------------------------------------------------------

def test_genesis_is_domain_separated_and_run_specific():
    a, b = genesis(RUN), genesis(RUN + "x")
    assert len(a) == 32 and a != b
    assert genesis(RUN) == a, "genesis must be deterministic"


def test_step_is_order_sensitive():
    """The chain's whole job is catching out-of-order promotion. If the version
    number did not enter the digest, two promotions could be swapped silently."""
    g = genesis(RUN)
    h1, h2 = "a" * 64, "b" * 64
    assert step(g, h1, 1) != step(g, h1, 2)
    assert step(step(g, h1, 1), h2, 2) != step(step(g, h2, 1), h1, 2)


def test_step_rejects_a_hash_that_is_not_full_length():
    """The stored lineage_hash is TRUNCATED to 16 chars. Feeding a truncated
    policy hash back into the chain is the most likely way to build two
    implementations that disagree, so it is refused rather than accepted."""
    with pytest.raises(LineageError) as ei:
        step(genesis(RUN), "a" * 16, 1)
    assert ei.value.code == "E_BAD_POLICY_HASH"


def test_stored_form_is_sixteen_hex_chars():
    assert len(stored(genesis(RUN))) == 16


def test_verify_accepts_a_well_formed_chain():
    hashes = ["%064x" % i for i in (1, 2, 3)]
    chain = build(RUN, hashes)
    versions = [
        {"version": n, "policy_hash_full": hashes[n - 1],
         "parent_hash": None if n == 1 else hashes[n - 2][:16],
         "lineage_hash": chain[n][2]}
        for n in (1, 2, 3)]
    rep = verify(RUN, versions, head_lineage_hash=chain[3][2])
    assert [r["status"] for r in rep] == ["OK"] * 3


def test_verify_catches_an_edited_version():
    """The failure the chain exists for: somebody rewrote v2."""
    hashes = ["%064x" % i for i in (1, 2, 3)]
    chain = build(RUN, hashes)
    versions = [
        {"version": n, "policy_hash_full": hashes[n - 1],
         "parent_hash": None if n == 1 else hashes[n - 2][:16],
         "lineage_hash": chain[n][2]}
        for n in (1, 2, 3)]
    versions[1]["policy_hash_full"] = "%064x" % 99      # v2 rewritten
    with pytest.raises(LineageError) as ei:
        verify(RUN, versions)
    assert ei.value.code == "E_LINEAGE_MISMATCH"
    assert ei.value.version == 2


def test_verify_catches_a_version_gap():
    """A gap between v2 and v4 is exactly what a silently failed promotion looks
    like. Making it loud is half the reason the chain is here."""
    hashes = ["%064x" % i for i in (1, 2, 3)]
    chain = build(RUN, hashes)
    versions = [
        {"version": 1, "policy_hash_full": hashes[0], "parent_hash": None,
         "lineage_hash": chain[1][2]},
        {"version": 3, "policy_hash_full": hashes[2],
         "parent_hash": hashes[1][:16], "lineage_hash": chain[3][2]},
    ]
    with pytest.raises(LineageError) as ei:
        verify(RUN, versions)
    assert ei.value.code == "E_VERSION_GAP"


def test_verify_catches_a_head_that_does_not_match_the_chain():
    hashes = ["%064x" % 1]
    chain = build(RUN, hashes)
    versions = [{"version": 1, "policy_hash_full": hashes[0],
                 "parent_hash": None, "lineage_hash": chain[1][2]}]
    with pytest.raises(LineageError) as ei:
        verify(RUN, versions, head_lineage_hash="0" * 16)
    assert ei.value.code == "E_HEAD_MISMATCH"


# --------------------------------------------------------------------------
# The ledger is append-only, and it is enforced.
# --------------------------------------------------------------------------

def test_a_run_cannot_open_without_its_hash_locks():
    with Ledger(":memory:") as l:
        with pytest.raises(Exception) as ei:
            l.open_run(RUN, NOW, dict(LOCKS, target_hash=""))
        assert "target_hash" in str(ei.value)


def test_update_and_delete_on_policy_versions_are_refused(led):
    _, w, r = blob_store()
    promote(led, RUN, json.dumps(payload()).encode(), "crucible-gate", NOW,
            LOCKS["manifest_hash"], w, r)
    with pytest.raises(Exception) as ei:
        led.db.execute("UPDATE policy_versions SET policy_hash='x'")
    assert "append-only" in str(ei.value)
    with pytest.raises(Exception) as ei:
        led.db.execute("DELETE FROM policy_versions")
    assert "append-only" in str(ei.value)


def test_out_of_order_append_is_refused(led):
    with pytest.raises(Exception) as ei:
        led.append_version(RUN, 2, "a" * 64, None, "b" * 16,
                           LOCKS["manifest_hash"], "crucible-gate", NOW, b"{}")
    assert "out-of-order" in str(ei.value)


# --------------------------------------------------------------------------
# The gate.
# --------------------------------------------------------------------------

def test_only_the_gate_may_promote(led):
    _, w, r = blob_store()
    with pytest.raises(PromotionError) as ei:
        promote(led, RUN, json.dumps(payload()).encode(), "crucible-armorer",
                NOW, LOCKS["manifest_hash"], w, r)
    assert ei.value.code == "E_WRONG_PROMOTER"


def test_promotion_writes_canonical_bytes_and_names_them_by_hash(led):
    blobs, w, r = blob_store()
    res = promote(led, RUN, json.dumps(payload()).encode(), "crucible-gate",
                  NOW, LOCKS["manifest_hash"], w, r)
    assert res["version"] == 1
    name = res["object"]
    assert res["policy_hash"] in name and RUN in name
    assert blobs[name] == canonicalize(payload()), "the stored bytes are canonical"
    assert compute_policy_hash(blobs[name]) == res["policy_hash_full"]


def test_key_order_in_the_submitted_payload_does_not_change_the_hash(led):
    """Two spellings of one policy must promote to one hash, or convergence
    detection reports progress forever."""
    _, w, r = blob_store()
    a = promote(led, RUN, json.dumps(payload()).encode(), "crucible-gate", NOW,
                LOCKS["manifest_hash"], w, r)
    reordered = json.dumps(payload(), sort_keys=True, indent=4).encode()
    assert compute_policy_hash(reordered) == a["policy_hash_full"]


def test_promoting_the_same_policy_twice_is_the_convergence_signal(led):
    _, w, r = blob_store()
    promote(led, RUN, json.dumps(payload()).encode(), "crucible-gate", NOW,
            LOCKS["manifest_hash"], w, r)
    with pytest.raises(PromotionError) as ei:
        promote(led, RUN, json.dumps(payload()).encode(), "crucible-gate", NOW,
                LOCKS["manifest_hash"], w, r)
    assert ei.value.code == "E_CONVERGED"


def test_chain_across_three_real_promotions_verifies(led):
    _, w, r = blob_store()
    for i in (1, 2, 3):
        promote(led, RUN, json.dumps(payload(n_rules=i)).encode(),
                "crucible-gate", NOW, LOCKS["manifest_hash"], w, r)
    rows = led.versions(RUN)
    rep = verify(RUN, rows, head_lineage_hash=led.get_run(RUN)["head_lineage_hash"])
    assert [x["status"] for x in rep] == ["OK", "OK", "OK"]


# --------------------------------------------------------------------------
# THE EXIT CRITERION.
# --------------------------------------------------------------------------

def test_a_deliberately_corrupted_readback_is_caught(led):
    """L1 exit criterion. The read-back must recompute FROM THE BYTES.

    The corruption below is deliberately small and semantically real: one digit
    of one threshold. The payload still parses, still validates, still looks like
    a policy, and enforces a DIFFERENT rule than the one that was promoted.

    A gate that read back the stored `policy_hash` field and compared it to the
    field it had just written would pass this. It would be comparing a value to
    itself, which is a check that cannot fail wearing the costume of integrity
    verification.
    """
    blobs, w, r = blob_store()

    def corrupting_reader(name):
        raw = blobs[name].decode()
        assert "50000" in raw, "the fixture must actually contain the value it corrupts"
        return raw.replace("50000", "50001").encode()

    with pytest.raises(PromotionError) as ei:
        promote(led, RUN, json.dumps(payload()).encode(), "crucible-gate", NOW,
                LOCKS["manifest_hash"], w, corrupting_reader)
    assert ei.value.code == "E_READBACK_HASH_MISMATCH"
    assert led.head(RUN) is None, (
        "a promotion whose read-back failed must not appear in the ledger")


def test_a_readback_that_returns_the_wrong_object_is_caught(led):
    """Corruption is not the only way bytes and name diverge. A read that lands
    on a DIFFERENT valid object returns perfectly well-formed content whose hash
    does not match the name it was fetched under."""
    blobs, w, _ = blob_store()
    promote(led, RUN, json.dumps(payload(n_rules=1)).encode(), "crucible-gate",
            NOW, LOCKS["manifest_hash"], w, lambda n: blobs[n])
    first = canonicalize(payload(n_rules=1))

    with pytest.raises(PromotionError) as ei:
        promote(led, RUN, json.dumps(payload(n_rules=2)).encode(),
                "crucible-gate", NOW, LOCKS["manifest_hash"], w,
                lambda n: first)          # reads v1's bytes under v2's name
    assert ei.value.code == "E_READBACK_HASH_MISMATCH"


def test_a_readback_that_fails_outright_is_not_a_promotion(led):
    def missing(name):
        raise KeyError(name)

    with pytest.raises(PromotionError) as ei:
        promote(led, RUN, json.dumps(payload()).encode(), "crucible-gate", NOW,
                LOCKS["manifest_hash"], lambda n, d: None, missing)
    assert ei.value.code == "E_READBACK_FAILED"
    assert led.head(RUN) is None


def test_a_payload_that_cannot_canonicalize_never_reaches_the_blob_store(led):
    """A float in a policy must be refused BEFORE the write, not after. A
    rejected candidate that already wrote an object leaves a version in the
    store that the ledger has no row for."""
    blobs, w, r = blob_store()
    bad = json.dumps(dict(payload(), confidence=0.9)).encode()
    with pytest.raises(PromotionError) as ei:
        promote(led, RUN, bad, "crucible-gate", NOW, LOCKS["manifest_hash"], w, r)
    assert ei.value.code == "E_NOT_CANONICALIZABLE"
    assert blobs == {}, "nothing may be written for a payload that was refused"
