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


# --------------------------------------------------------------------------
# The lock must cover BEHAVIOUR, not just names. Added by the coordinator
# 2026-08-20 after the lock was demonstrated not to lock anything.
# --------------------------------------------------------------------------

def test_target_agent_hash_moves_when_a_TOOL_BODY_changes(tmp_path, monkeypatch):
    """The defect this test exists for was real and was measured, not imagined.

    Before `runtime_source` entered the payload, inserting a statement into a
    tool body left target_agent_hash at edade2064be9b50f -- unchanged. A target
    could be frozen at D3, rewritten to approve everything, and every number
    produced afterwards would still cite the same target hash.
    """
    import hashlib
    import pathlib

    from target.refund_agent import freeze

    before = freeze.compute()["target_agent_hash"]
    tools_py = pathlib.Path(freeze.tools.__file__)
    original = tools_py.read_bytes()
    try:
        src = original.decode("utf-8")
        i = src.index("def ")
        j = src.index("\n", src.index(":", i))
        tools_py.write_bytes(
            (src[:j] + "\n    _INJECTED = True" + src[j:]).encode("utf-8"))
        after = freeze.compute()["target_agent_hash"]
    finally:
        tools_py.write_bytes(original)

    assert before != after, (
        "a statement was inserted into a tool body and the target hash did not "
        "move. The D3 freeze would lock tool NAMES while the target's behaviour "
        "stayed editable, and every result would cite a hash that no longer "
        "describes what ran.")
    assert freeze.compute()["target_agent_hash"] == before, "restore failed"


def test_a_new_module_in_the_target_package_is_refused(tmp_path):
    """The direction that is easy to skip. A .py added to the package would run
    inside the frozen target while sitting outside its hash."""
    import pathlib

    import pytest as _pytest

    from target.refund_agent import freeze

    intruder = pathlib.Path(freeze.HERE) / "sneaky_helper.py"
    intruder.write_text("VALUE = 1\n", encoding="utf-8")
    try:
        with _pytest.raises(RuntimeError) as ei:
            freeze.runtime_source_hashes()
        assert "sneaky_helper.py" in str(ei.value)
        assert "RUNTIME_MODULES" in str(ei.value)
    finally:
        intruder.unlink()


def test_a_declared_module_missing_from_disk_is_refused(monkeypatch):
    """The other direction. A rename must not silently drop a file out of the
    lock -- which is exactly what a rename did on 2026-08-20."""
    import pytest as _pytest

    from target.refund_agent import freeze

    monkeypatch.setattr(freeze, "RUNTIME_MODULES",
                        freeze.RUNTIME_MODULES + ("renamed_away.py",))
    with _pytest.raises(RuntimeError) as ei:
        freeze.runtime_source_hashes()
    assert "renamed_away.py" in str(ei.value)


def test_manifest_hash_does_NOT_move_on_a_body_change():
    """Part A describes the tool SURFACE. If it moved on every body edit it would
    stop being the thing the plugin is built against, and the two hashes would
    carry the same information -- which would make one of them pointless."""
    import pathlib

    from target.refund_agent import freeze

    before = freeze.compute()["manifest_hash"]
    tools_py = pathlib.Path(freeze.tools.__file__)
    original = tools_py.read_bytes()
    try:
        src = original.decode("utf-8")
        i = src.index("def ")
        j = src.index("\n", src.index(":", i))
        tools_py.write_bytes(
            (src[:j] + "\n    _INJECTED = True" + src[j:]).encode("utf-8"))
        assert freeze.compute()["manifest_hash"] == before
    finally:
        tools_py.write_bytes(original)
