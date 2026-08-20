"""The D3 target freeze recomputes identically, including from a CRLF checkout.

**The freeze itself is NOT run by this lane and not by this suite.** `--write` is
the project owner's command on the scheduled date. These tests exercise the
computation so that when the owner runs it, there is nothing left to discover.

The exit criterion for scope (a) is that THE FREEZE HASH RECOMPUTES IDENTICALLY
FROM A CLEAN CHECKOUT. That is the one property a freeze has to have and the one
that is easiest to lose without noticing, because it fails on somebody else's
machine.
"""

import hashlib

from target.refund_agent import freeze


def test_the_freeze_is_deterministic_across_calls():
    assert freeze.compute() == freeze.compute()


def test_the_freeze_carries_the_five_things_it_is_supposed_to_pin():
    r = freeze.compute()
    assert set(r) == {"target_id", "manifest_hash", "target_agent_hash",
                      "policy_sha256", "canonical_bytes"}
    assert r["target_id"] == "tgt_crucible_refund_v1"
    assert len(r["manifest_hash"]) == 16
    assert len(r["target_agent_hash"]) == 16


def test_the_model_tier_is_inside_the_hashed_payload():
    """The target's tier flatters or deflates every downstream number, so it has to
    be recoverable from the frozen record rather than from somebody's memory. A
    payload that omitted it would let the tier change without the hash moving."""
    payload = freeze.freeze_payload()
    assert payload["target_descriptor"]["model"] == "gemini-3.5-flash-lite"
    assert payload["target_descriptor"]["thinking_level"] == "minimal"


def test_the_payload_carries_no_wall_clock_and_no_run_id():
    """A timestamp or a run id inside the payload makes the same target hash
    differently on two machines, which is the defect `policy_hash` already refuses
    for `run_id`."""
    import json
    blob = json.dumps(freeze.freeze_payload())
    for forbidden in ("run_id", "timestamp", "generated_at", "frozen_at"):
        assert forbidden not in blob


def test_policy_hash_is_identical_from_an_LF_and_a_CRLF_checkout():
    """THE CHECK THAT CAUGHT A REAL DEFECT. Verified 2026-08-20: `core.autocrlf` is
    true in this repository and `.gitattributes` does not cover `target/**`, so a
    fresh clone on Windows receives CRLF where this working copy holds LF. Hashing
    raw bytes gave two different answers for the same file, which would have broken
    the recompute-from-a-clean-checkout criterion on the judge's machine and not on
    ours."""
    raw = freeze.POLICY_PATH.read_bytes()
    as_lf = raw.replace(b"\r\n", b"\n")
    as_crlf = as_lf.replace(b"\n", b"\r\n")

    # The hazard is real: the two checkouts genuinely differ on disk.
    assert hashlib.sha256(as_lf).hexdigest() != hashlib.sha256(as_crlf).hexdigest()

    # And the freeze is blind to it.
    normalize = lambda b: hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()
    assert normalize(as_lf) == normalize(as_crlf) == freeze.policy_sha256()


def test_a_bom_on_the_policy_is_refused_rather_than_stripped(tmp_path, monkeypatch):
    """Restriction 1's reasoning, applied here: stripping a BOM would make the file
    that arrives differ from the file that was hashed."""
    import pytest

    bommed = tmp_path / "refund_policy.md"
    bommed.write_bytes(b"\xef\xbb\xbf" + freeze.POLICY_PATH.read_bytes())
    monkeypatch.setattr(freeze, "POLICY_PATH", bommed)
    with pytest.raises(RuntimeError):
        freeze.policy_sha256()


def test_tool_signatures_pin_parameter_names_in_source_order():
    """A parameter renamed after the freeze breaks every arg-path rule silently -
    `payout_instrument_id` becoming `instrument_id` would make the F4 destination
    rule stop firing while still validating."""
    sigs = {s["tool_name"]: s["params"] for s in freeze.tool_signatures()}
    assert sigs["issue_refund"] == ["order_id", "amount_minor", "currency",
                                    "reason_code", "beneficiary_id",
                                    "payout_instrument_id", "note"]
    assert sigs["email_customer"] == ["customer_id", "to", "subject_line", "body"]
    assert list(sigs) == sorted(sigs), "tools sorted at construction"


def test_renaming_a_tool_parameter_moves_the_freeze_hash():
    """Proves the signature half of the payload is load-bearing rather than
    decorative. If this passes with the hashes equal, the freeze is not pinning
    what it says it pins."""
    before = freeze.compute()["target_agent_hash"]
    payload = freeze.freeze_payload()
    for s in payload["tool_signatures"]:
        if s["tool_name"] == "issue_refund":
            s["params"] = ["order_id", "amount_minor", "currency", "reason_code",
                           "beneficiary_id", "instrument_id", "note"]
    from crucible.canon import hash_full
    assert hash_full(payload)[:16] != before
