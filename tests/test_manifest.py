"""test_manifest.py - Part A / Part B loading and the completeness check.

Runs against the frozen golden fixtures, so a manifest change that breaks the
loader shows up here rather than at D3 when the target freezes.
"""

import json
import pathlib

import pytest

from crucible.manifest import (
    UNCLASSIFIED,
    ManifestError,
    assert_manifest_covers,
    capability_set,
    load_part_a,
    load_part_b,
)

GOLDEN = pathlib.Path(__file__).resolve().parent.parent / "contracts" / "golden"
PART_A = GOLDEN / "C3a-capability_manifest.valid.json"
PART_B = GOLDEN / "C3b-derived_schema.valid.json"


def test_part_a_loads_and_hashes():
    doc, h = load_part_a(PART_A)
    assert len(h) == 16 and doc["tools"]


def test_part_b_loads_and_hashes():
    doc, h = load_part_b(PART_B)
    assert len(h) == 16 and doc["schema_version"] == 1


def test_the_two_parts_hash_SEPARATELY():
    """Ruling 20. They freeze on different days -- D3 with the target, D5 with
    the corpus. One hash over both would mean the D5 corpus freeze retroactively
    changed the identity of the thing the D3 target was frozen against, and every
    result in between would cite a manifest hash that no longer exists."""
    _, a = load_part_a(PART_A)
    _, b = load_part_b(PART_B)
    assert a != b


def test_hash_is_stable_across_reformatting(tmp_path):
    """The manifest is hash-locked. Reindenting it must not re-identify it, or
    the D3 freeze breaks the first time somebody opens the file in an editor."""
    doc, h = load_part_a(PART_A)
    p = tmp_path / "reformatted.json"
    p.write_bytes(json.dumps(doc, indent=8, sort_keys=True).encode())
    _, h2 = load_part_a(p)
    assert h == h2


def test_fail_closed_tool_carries_every_class():
    """'We do not know what this does' encodes as EVERY class, never none."""
    doc, _ = load_part_a(PART_A)
    fc = [t for t in doc["tools"] if t.get("fail_closed")]
    assert fc, "the fixture must contain a fail_closed tool or this is inert"
    for t in fc:
        assert len(t["capability_classes"]) == 6


def test_a_fail_closed_tool_missing_one_class_is_refused(tmp_path):
    doc, _ = load_part_a(PART_A)
    for t in doc["tools"]:
        if t.get("fail_closed"):
            t["capability_classes"] = t["capability_classes"][:-1]
    p = tmp_path / "m.json"
    p.write_bytes(json.dumps(doc).encode())
    with pytest.raises(ManifestError) as ei:
        load_part_a(p)
    assert ei.value.code == "E_FAIL_CLOSED_NOT_MAXIMAL"


def test_a_tool_with_NO_capability_classes_key_is_refused(tmp_path):
    """Absent is not the empty set. Defaulting one to the other makes a tool the
    policy cannot constrain look like a tool that needs no constraint."""
    doc, _ = load_part_a(PART_A)
    doc["tools"][0].pop("capability_classes")
    p = tmp_path / "m.json"
    p.write_bytes(json.dumps(doc).encode())
    with pytest.raises(ManifestError) as ei:
        load_part_a(p)
    assert ei.value.code == "E_NO_CAPABILITY_CLASSES"


def test_UNCLASSIFIED_cannot_be_declared_as_a_tools_class(tmp_path):
    """It is a sentinel for an unclassified CALL, never a class a tool declares."""
    doc, _ = load_part_a(PART_A)
    doc["tools"][0]["capability_classes"] = [UNCLASSIFIED]
    p = tmp_path / "m.json"
    p.write_bytes(json.dumps(doc).encode())
    with pytest.raises(ManifestError) as ei:
        load_part_a(p)
    assert ei.value.code == "E_UNKNOWN_CAPABILITY_CLASS"


def test_duplicate_tool_handle_is_refused(tmp_path):
    doc, _ = load_part_a(PART_A)
    doc["tools"].append(dict(doc["tools"][0]))
    p = tmp_path / "m.json"
    p.write_bytes(json.dumps(doc).encode())
    with pytest.raises(ManifestError) as ei:
        load_part_a(p)
    assert ei.value.code == "E_DUPLICATE_HANDLE"


def test_an_undeclared_callable_tool_is_an_error_not_an_empty_set():
    """The completeness check L2's exit criteria require."""
    doc, _ = load_part_a(PART_A)
    handles = [t["tool_handle"] for t in doc["tools"]]
    assert assert_manifest_covers(doc, handles)["callable"] == len(handles)
    with pytest.raises(ManifestError) as ei:
        assert_manifest_covers(doc, handles + ["tool:t_00000000"])
    assert ei.value.code == "E_MANIFEST_INCOMPLETE"


def test_capability_set_returns_the_sentinel_for_an_unknown_tool():
    """Not the empty set. The empty set would make every membership rule miss it
    silently, which is the failure the sentinel exists to prevent."""
    doc, _ = load_part_a(PART_A)
    known = doc["tools"][0]["tool_handle"]
    assert isinstance(capability_set(doc, known), frozenset)
    assert capability_set(doc, "tool:t_00000000") == UNCLASSIFIED
    assert capability_set(doc, "tool:t_00000000") != frozenset()


# --------------------------------------------------------------------------
# The hashed-payload exclusion. Enumerated, never "strip whatever fails".
# --------------------------------------------------------------------------

def test_part_b_excludes_only_the_declared_rate(tmp_path):
    """Changing the measured accuracy must NOT re-identify the schema. Two runs
    whose fields are identical and whose measured accuracy differs are the same
    schema, and Part B's identity is a definition, not a measurement."""
    raw = json.loads(PART_B.read_text(encoding="utf-8"))
    _, h1 = load_part_b(PART_B)

    raw["blindness_check"]["max_predictive_accuracy"] = 0.42
    p = tmp_path / "b.json"
    p.write_bytes(json.dumps(raw).encode())
    _, h2 = load_part_b(p)
    assert h1 == h2, "the excluded rate leaked into the hash"


def test_removing_a_derived_field_DOES_re_identify_part_b(tmp_path):
    """The other half of the exclusion test. If nothing changes the hash, the
    exclusion has quietly grown into 'hash almost nothing'."""
    raw = json.loads(PART_B.read_text(encoding="utf-8"))
    _, h1 = load_part_b(PART_B)
    raw["derived_fields"] = raw["derived_fields"][:-1]
    p = tmp_path / "b.json"
    p.write_bytes(json.dumps(raw).encode())
    _, h2 = load_part_b(p)
    assert h1 != h2


def test_a_float_that_is_NOT_on_the_exclusion_list_is_still_refused(tmp_path):
    """The exclusion must never generalize into 'strip whatever fails to
    canonicalize'. That is weakening a gate, which CONVENTIONS section 8 rule 3
    makes a stop condition rather than a repair."""
    raw = json.loads(PART_B.read_text(encoding="utf-8"))
    raw["derived_fields"][0]["some_other_rate"] = 0.75
    p = tmp_path / "b.json"
    p.write_bytes(json.dumps(raw).encode())
    with pytest.raises(ManifestError) as ei:
        load_part_b(p)
    assert ei.value.code == "E_NOT_CANONICALIZABLE"
    assert "SECOND offending value" in ei.value.detail, (
        "the error must distinguish a new float from the known excluded one, or "
        "the next person adds it to the exclusion list instead of removing it")


def test_part_a_has_no_exclusions_and_needs_none(tmp_path):
    """Part A freezes with the TARGET. A carve-out there would mean the target
    was frozen against something other than what it is built from."""
    from crucible.manifest.load import HASH_EXCLUSIONS
    assert "A" not in HASH_EXCLUSIONS
    load_part_a(PART_A)   # canonicalizes whole, with every restriction enforced
