"""test_transfer_contract_registration.py - C11 is IN the hashed registry.

WHY THIS EXISTS
----------------
`contracts/transfer_evidence.schema.json` shipped outside
`scripts/hash-contracts.py::CONTRACT_FILES`. `contract-check.py` reported every
pass green, and it did so PRECISELY BECAUSE the schema sat outside the registry:
nothing hashed it, so its shape and its semantics could move without any
contract id or frozen digest moving with them. That is this repository's own
named failure - a check that does not cover the artifact is a check that cannot
fail for it - sitting one directory away from the file whose docstring names it.

The 132 tests around `crucible/transfer/` are strong local coverage. THEY ARE
NOT A CONTRACT IDENTITY. A test pins behaviour; a manifest entry pins bytes, and
only the second one lets a reader say which shape it is looking at.

WHAT IS ASSERTED HERE, AND WHAT DELIBERATELY IS NOT
---------------------------------------------------
The registry invariants, and the fixture pair passing through whatever the
schema currently says. NOT the schema's contents: `transfer_evidence.schema.json`
is owned elsewhere and is under active edit, and a test that pinned its current
field set would be this project's other named failure - a test that pins a claim
rather than a fact, and then keeps passing after the claim goes false.

So `test_the_positive_fixture_validates` is deliberately written to BREAK when
the schema changes in a way the fixture no longer satisfies. That is the alarm
working, not a flaky test.

AMENDED 2026-08-29, AFTER AN INDEPENDENT REVIEW
------------------------------------------------
The paragraph above was also used to justify NOT mapping a declared reason to a
specific constraint, on the grounds that such a mapping would pin field names in
a file owned elsewhere. That reasoning left a hole. The reviewer reduced
`transfer_evidence.schema.json` in memory to a single `bundle_kind` const: the
valid fixture still produced zero errors, the known-bad still produced one, and
the whole fixture gate stayed green while every other C11 constraint had
vanished. Eight promised reasons, one demonstrated failure, and any surviving
failure masking the loss of the others.

The reason-to-constraint bindings now live in
`contracts/golden/proof/must-fail-bindings.json` and are enforced by
`contract-check.py::pass_proven`. The tests below assert them for C11 and assert
the reviewer's mutation now turns the gate RED.

No hash value appears in this file (ruling 46: a frozen hash has exactly one
owner, the artifact). The manifest is checked by re-deriving it, never by
comparing against a copied digest.
"""

import importlib.util
import io
import json
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
CONTRACTS = REPO / "contracts"
GOLDEN = CONTRACTS / "golden"

CONTRACT_ID = "C11"
SCHEMA_FILE = "transfer_evidence.schema.json"


def _load(script_name, module_name):
    """Import a hyphenated script under `scripts/` without running `main()`.

    `contract-check.py` rebinds `sys.stdout` at module level, wrapping
    `sys.stdout.buffer` so a finding containing a section sign does not crash
    the gate on a cp1252 console. That is correct for the gate and destructive
    here: the wrapper closes the buffer it wrapped when it is collected, and the
    buffer under pytest is pytest's own capture file, so the whole session dies
    at teardown with `I/O operation on closed file`.

    The import is therefore run against a `StringIO`, which has no `.buffer`
    attribute, so the module's own `hasattr` guard declines to rebind anything.
    The gate's behaviour is untouched - this only changes what it sees at the
    moment it is imported as a library rather than run as a script.
    """
    path = REPO / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    saved = sys.stdout
    sys.stdout = io.StringIO()
    try:
        spec.loader.exec_module(module)
    finally:
        sys.stdout = saved
    return module


@pytest.fixture(scope="module")
def hasher():
    return _load("hash-contracts.py", "_hash_contracts")


@pytest.fixture(scope="module")
def checker():
    return _load("contract-check.py", "_contract_check")


@pytest.fixture(scope="module")
def manifest():
    return json.loads((CONTRACTS / "MANIFEST.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- registration

def test_the_transfer_schema_is_in_CONTRACT_FILES(hasher):
    """The defect this file was written for, stated as one assertion."""
    assert hasher.CONTRACT_FILES.get(CONTRACT_ID) == [SCHEMA_FILE]


def test_every_schema_under_contracts_is_registered_somewhere(hasher):
    """THE GENERAL FORM, AND THE HALF THAT PREVENTS THE NEXT ONE.

    `hash-contracts.py` walks an explicit list, never a directory - which is
    correct, because three contracts are not JSON at all and a directory walk
    would sweep in instances like `objective_set.v1.json` that C10 deliberately
    does not hash. The cost of an explicit list is that a new schema can simply
    be forgotten, silently, which is exactly what happened. This closes that
    without changing the walk: a `*.schema.json` on disk and absent from the
    registry is an error, so the next unhashed contract fails here on the day it
    lands rather than after a measurement is taken against it.
    """
    registered = {fn for files in hasher.CONTRACT_FILES.values() for fn in files}
    on_disk = {p.name for p in CONTRACTS.glob("*.schema.json")}
    assert not (on_disk - registered), (
        "these schemas are under contracts/ and hashed by nothing: %s"
        % sorted(on_disk - registered))


def test_every_registered_file_exists(hasher):
    """The other direction. A registry entry naming a file that is not there is
    a contract nobody can validate against, and `build()` raises on it - but it
    raises at manifest-write time, which is not where anyone is looking."""
    missing = [fn for files in hasher.CONTRACT_FILES.values() for fn in files
               if not (CONTRACTS / fn).exists()]
    assert not missing, missing


def test_every_contract_id_has_an_owner_row(hasher):
    """`build()` does `OWNERS[cid]` with no guard, so a CONTRACT_FILES entry
    with no OWNERS row is a KeyError from a script, not a finding."""
    assert set(hasher.CONTRACT_FILES) == set(hasher.OWNERS)


def test_the_owner_row_names_a_producer_and_a_consumer(hasher):
    row = hasher.OWNERS[CONTRACT_ID]
    assert row["produced_by"]
    assert row["consumed_by"]


def test_the_manifest_on_disk_carries_the_contract(manifest):
    assert CONTRACT_ID in manifest["contracts"]
    assert SCHEMA_FILE in manifest["contracts"][CONTRACT_ID]["files"]


def test_the_manifest_count_is_computed_not_typed(hasher, manifest):
    assert manifest["contract_count"] == len(hasher.CONTRACT_FILES)


def test_the_manifest_still_re_derives(hasher):
    """`hash-contracts.py --check` as the subprocess it is, so this asserts the
    committed manifest against the file bytes on disk rather than against a
    digest copied into a test. If the schema is edited and the manifest is not
    regenerated, this is where it surfaces."""
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "hash-contracts.py"), "--check"],
        capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stdout + r.stderr


# --------------------------------------------------------------- golden pair

def test_the_contract_is_mapped_to_a_fixture_prefix(checker):
    assert checker.FIXTURE_SCHEMA.get(CONTRACT_ID) == SCHEMA_FILE


def test_every_mapped_id_has_both_halves_of_a_golden_pair(checker):
    """A HALF REGISTRATION FAILS THE GATE, so it must fail here first.

    `pass_fixtures` requires a golden fixture per mapped id and refuses a
    KNOWN-BAD that validates. Both halves are required: a fixture set with no
    known-bads cannot tell a working validator from one that returns True.
    """
    names = {p.name for p in GOLDEN.glob("*.json")}
    for cid in checker.FIXTURE_SCHEMA:
        positives = [n for n in names
                     if n.split("-")[0] == cid and "KNOWN_BAD" not in n]
        negatives = [n for n in names
                     if n.split("-")[0] == cid and "KNOWN_BAD" in n]
        assert positives, "no positive golden fixture for %s" % cid
        assert negatives, "no KNOWN-BAD golden fixture for %s" % cid


def _validate(checker, body):
    import jsonschema
    schema = json.loads((CONTRACTS / SCHEMA_FILE).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema, registry=checker._registry())
    return list(validator.iter_errors(body))


def _fixture(name):
    body = json.loads((GOLDEN / name).read_text(encoding="utf-8"))
    body.pop("_must_fail_because", None)
    body.pop("_note", None)
    return body


def test_the_positive_fixture_validates(checker):
    errs = _validate(checker, _fixture("C11-transfer_evidence.valid.json"))
    assert not errs, [
        "%s: %s" % (list(e.absolute_path), e.message[:120]) for e in errs[:8]]


def test_the_known_bad_fixture_is_refused(checker):
    errs = _validate(checker, _fixture("C11-transfer_evidence.KNOWN_BAD.json"))
    assert errs, ("the KNOWN-BAD fixture VALIDATED, so the schema cannot catch "
                  "any of the defects it declares")


def test_the_known_bad_names_every_reason_it_fails():
    """The doctrine `contracts/golden/` runs on: a negative fixture names the
    exact rule it violates, so a lane that makes it pass knows what it broke."""
    body = json.loads(
        (GOLDEN / "C11-transfer_evidence.KNOWN_BAD.json").read_text(encoding="utf-8"))
    reasons = body.get("_must_fail_because")
    assert isinstance(reasons, list) and reasons
    assert all(isinstance(r, str) and r.strip() for r in reasons)


KNOWN_BAD_NAME = "C11-transfer_evidence.KNOWN_BAD.json"


def _c11_binding(checker):
    doc = json.loads(checker.BINDINGS.read_text(encoding="utf-8"))
    return doc["fixtures"][KNOWN_BAD_NAME]


def test_every_declared_reason_is_bound_to_a_named_constraint(checker):
    """WHAT THIS REPLACED, AND WHY THE REPLACEMENT IS NOT OPTIONAL.

    The test that stood here counted: N declared reasons had to produce at least
    N distinct error PATHS. Its docstring argued that matching a reason to a
    specific constraint "would pin the schema's current field names, and that
    file is owned elsewhere and under active edit."

    That reasoning is what left the hole. An independent reviewer reduced
    `transfer_evidence.schema.json` in memory to a single `bundle_kind` const;
    the valid fixture still produced zero errors, the known-bad still produced
    one, and `contract-check.py::pass_fixtures` stayed GREEN with essentially
    every other C11 constraint gone. A count cannot tell eight promises kept
    from one promise kept eight times.

    The coupling the old docstring feared is real and is now the alarm working,
    exactly as `test_the_positive_fixture_validates` is already documented to be.
    """
    reasons = json.loads((GOLDEN / KNOWN_BAD_NAME).read_text(
        encoding="utf-8"))["_must_fail_because"]
    bound = _c11_binding(checker)["reasons"]
    assert len(bound) == len(reasons)
    for pos, (spec, text) in enumerate(zip(bound, reasons)):
        assert spec["index"] == pos
        assert spec["claim"] in text, (
            "reason %d was rewritten and its binding was not: the binding quotes "
            "%r, which is no longer in the reason." % (pos, spec["claim"]))
        assert "evidence" in spec, (
            "reason %d claims a rejection C11 does not perform. C11 is the one "
            "contract whose known-bad demonstrates every reason it declares; a "
            "new `unenforced` record here is a regression, not bookkeeping."
            % pos)


def test_every_bound_reason_is_a_failure_that_actually_happens(checker):
    """THE ASSERTION THE OLD COUNT COULD NOT MAKE."""
    errs = _validate(checker, _fixture(KNOWN_BAD_NAME))
    missing = []
    for spec in _c11_binding(checker)["reasons"]:
        for ev in spec["evidence"]:
            triple = checker._triple(ev)
            if not any(checker._matches(triple, e) for e in errs):
                missing.append((spec["index"], triple))
    assert not missing, (
        "these reasons promise a failure the schema does not produce: %s" % missing)


def test_no_two_reasons_stand_on_the_same_failure(checker):
    """N reasons must be N failures. Two reasons resting on one error means the
    surviving error masks the loss of the other constraint, which is the shape
    of the whole finding."""
    seen = {}
    for spec in _c11_binding(checker)["reasons"]:
        for ev in spec["evidence"]:
            triple = checker._triple(ev)
            assert triple not in seen, (
                "reasons %d and %d both rest on %s"
                % (seen[triple], spec["index"], triple))
            seen[triple] = spec["index"]


def test_the_known_bad_fails_for_no_reason_it_does_not_declare(checker):
    """The other direction, and the ruling-43 shape. A fixture that acquires an
    undeclared failure sends a lane red after it has repaired every listed
    reason, with nothing to tell it why."""
    entry = _c11_binding(checker)
    claimed = [checker._triple(ev) for spec in entry["reasons"]
               for ev in spec.get("evidence", [])]
    recorded = [checker._triple(u) for u in entry.get("unexplained_errors", [])]
    stray = [(checker._pointer(e.absolute_path) or "(root)", e.validator)
             for e in _validate(checker, _fixture(KNOWN_BAD_NAME))
             if not any(checker._matches(t, e) for t in claimed + recorded)]
    assert not stray, (
        "the fixture fails at %s and its _must_fail_because names no such "
        "reason." % stray)


def test_the_gate_goes_red_when_the_schema_is_reduced_to_one_constraint(checker):
    """THE REVIEWER'S OWN MUTATION, AS A TEST.

    Reduce `transfer_evidence.schema.json` to nothing but the `bundle_kind`
    const inside a throwaway copy of the repository, then drive the real
    `pass_fixtures` and the real `pass_proven` against it.

    `pass_fixtures` must stay GREEN. That is not a defect in this test - it is
    the finding, stated as an assertion so it cannot quietly stop being true:
    the fixture pass structurally cannot see this, and anyone who deletes
    `pass_proven` believing FIXTURES covers it will fail here.
    """
    gutted = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {"bundle_kind": {"const": "transfer_evidence"}},
    }
    with checker._sandbox() as tmp:
        path = tmp / "contracts" / SCHEMA_FILE
        gutted["$id"] = json.loads(path.read_text(encoding="utf-8"))["$id"]
        path.write_text(json.dumps(gutted, indent=2) + "\n", encoding="utf-8")

        fixtures_ok, _ = checker.pass_fixtures()
        proven_ok, findings = checker.pass_proven()

    assert fixtures_ok, (
        "pass_fixtures went red on the reduced schema. If that is now real "
        "coverage, say so here - but the finding this file documents is that it "
        "cannot see the reduction at all.")
    assert not proven_ok, (
        "THE SCHEMA WAS REDUCED TO ONE CONSTRAINT AND THE GATE STAYED GREEN. "
        "That is the defect, back.")
    lost = [m for m in findings
            if m.startswith("P4_UNDEMONSTRATED") and KNOWN_BAD_NAME in m]
    assert len(lost) == 7, (
        "expected the seven constraints the reduction destroys to be named one "
        "by one; got %d: %s" % (len(lost), lost))


def test_the_binding_gate_rejects_its_own_strawman_set(checker):
    """`contracts/golden/proof/selftest/` ships three known-bad fixtures and a
    DELIBERATELY DEFECTIVE binding file, one wrong way per rule. Same doctrine as
    the nine known-bads the tripwire ships and the seven strawmen the boot
    self-test ships: a check that cannot fail is not measuring anything, and
    that applies to this check too.

    Driven through the real `pass_proven` by rebinding the same globals
    `_sandbox()` rebinds, so it exercises the shipped code path rather than a
    re-implementation of its interesting line.
    """
    straw = checker.PROOF / "selftest"
    saved = {n: getattr(checker, n) for n in ("GOLDEN", "BINDINGS")}
    checker.GOLDEN = straw
    checker.BINDINGS = straw / "strawman-bindings.json"
    try:
        ok, findings = checker.pass_proven()
    finally:
        for name, value in saved.items():
            setattr(checker, name, value)

    assert not ok, "the deliberately defective binding set was ACCEPTED"
    expected = ("P0_MALFORMED", "P1_NO_BINDING", "P2_COUNT", "P3_CLAIM_DRIFT",
                "P4_UNDEMONSTRATED", "P4_UNENFORCED_STALE",
                "P5_DUPLICATE_EVIDENCE", "P6_EXTERNAL_MISSING",
                "P6_EXTERNAL_STALE", "P7_UNEXPLAINED", "P7_UNEXPLAINED_STALE",
                "P8_ORPHAN")
    missed = [c for c in expected if not any(m.startswith(c) for m in findings)]
    assert not missed, "these rules did not fire on their own strawman: %s" % missed
    # A checker that flags everything is as useless as one that flags nothing.
    assert not any("C9-strawman.KNOWN_BAD.json reason 0" in m for m in findings), (
        "the one CORRECTLY bound reason in the strawman set was flagged")


def test_the_positive_fixture_is_not_a_run():
    """It carries synthetic ids and a denominator below the pre-registered
    floor, so no rate can be quoted off it even by accident. `contracts/golden/`
    holds hand-authored instances; they exercise the schema and prove nothing
    about a run."""
    body = json.loads(
        (GOLDEN / "C11-transfer_evidence.valid.json").read_text(encoding="utf-8"))
    arithmetic = body["transfer_arithmetic"]
    assert arithmetic["breached_at_v0"] < arithmetic["floor"]
    assert body["execution_provenance"]["mode"] != "live"
    assert body["execution_provenance"]["model_calls"] == 0


# ------------------------------------------------------------------- repo norm

@pytest.mark.parametrize("rel", [
    "scripts/hash-contracts.py",
    "scripts/contract-check.py",
    "contracts/MANIFEST.json",
    "contracts/golden/C11-transfer_evidence.valid.json",
    "contracts/golden/C11-transfer_evidence.KNOWN_BAD.json",
])
def test_no_carriage_returns(rel):
    """LF, repo-wide. The contract normalizer absorbs CRLF before hashing, which
    means a CRLF file hashes identically and the defect is invisible exactly
    where it would be most confusing."""
    assert b"\r" not in (REPO / rel).read_bytes()
