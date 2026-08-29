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


def test_the_known_bad_is_refused_at_least_once_per_declared_reason(checker):
    """A DECLARED REASON THAT DOES NOT FIRE IS DECORATION.

    Counted rather than matched one-to-one on purpose: the mapping from a
    declared reason to a validator error path would pin the schema's current
    field names, and that file is owned elsewhere and under active edit. The
    count is the part that stays true - it catches the case where reasons were
    added to the prose and never to the JSON.
    """
    reasons = json.loads(
        (GOLDEN / "C11-transfer_evidence.KNOWN_BAD.json").read_text(
            encoding="utf-8"))["_must_fail_because"]
    errs = _validate(checker, _fixture("C11-transfer_evidence.KNOWN_BAD.json"))
    paths = {tuple(e.absolute_path) for e in errs}
    assert len(paths) >= len(reasons), (
        "%d declared reasons but only %d distinct error locations: %s"
        % (len(reasons), len(paths), sorted(map(str, paths))))


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
