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
vanished. Every promised reason but one, all resting on a single demonstrated
failure, with that survivor masking the loss of the rest. The number of promises
is not written here - it is read off the binding artifact by the tests below,
because a count beside a list is a second source of truth for the length of the
list, and this file already had one go stale.

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
import re
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

    # DERIVED, NOT TYPED. This assertion read `== 7` until 2026-08-29 and went
    # red the moment C11 gained a reason - a test failing for growth rather than
    # for a defect, which is how a real alarm gets edited into silence. The
    # reduced schema keeps exactly one constraint, so every bound triple EXCEPT
    # the `bundle_kind` const must be reported lost, and that is computed from
    # the binding artifact here for the same reason the gate's own summary is
    # computed rather than written down.
    survives = ("/bundle_kind", "const", "")
    expected = [checker._triple(ev) for spec in _c11_binding(checker)["reasons"]
                for ev in spec.get("evidence", [])
                if checker._triple(ev) != survives]
    assert len(lost) == len(expected), (
        "the reduction destroys %d bound constraints and PROVEN named %d of "
        "them. Each one must be reported by itself: a single finding standing "
        "in for several is the masking this pass exists to catch. Got: %s"
        % (len(expected), len(lost), lost))


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


# ------------------------------------------------------ the adjudication block
#
# `transfer_evidence.schema.json` gained an optional top-level `adjudication`
# property and the golden pair did not exercise it. A contract clause no fixture
# instantiates is a clause nothing can tell a working validator from a broken
# one about - the same hole the reason bindings above were written to close, one
# property along.

VALID_NAME = "C11-transfer_evidence.valid.json"


def _adjudication():
    return json.loads(
        (GOLDEN / VALID_NAME).read_text(encoding="utf-8"))["adjudication"]


def test_the_valid_fixture_exercises_the_adjudication_block():
    """A positive fixture that omits an optional block proves nothing about it.

    Deliberately an assertion about PRESENCE. The contents are checked by
    re-deriving them below and by the schema; what this catches is the block
    quietly disappearing from the fixture, which no other test would notice
    because everything else about the fixture would still validate.
    """
    body = json.loads((GOLDEN / VALID_NAME).read_text(encoding="utf-8"))
    assert "adjudication" in body, (
        "the valid fixture carries no adjudication block, so every constraint "
        "in that subschema is unexercised by the golden pair")
    assert body["adjudication"]["record_kind"] == "f4_adjudication"


def test_the_fixtures_adjudication_re_derives_from_its_own_inputs():
    """THE TWO DIGESTS AND THE FIVE COUNTS ARE NOT TYPED VALUES.

    `scripts/make-golden.py` writes them out so the generator stays stdlib-only,
    which is what lets it run in a checkout with no application package. That
    makes them a copy, and a copy needs an owner: this rebuilds the whole record
    with `crucible.transfer.adjudication.build_adjudication`, feeding it nothing
    but the fixture's OWN `adjudicated_by`, `adjudicated_on`, `instance_ids` and
    `decisions`. No input is restated here, so there is no second source of
    truth to drift - a changed digit, a recount, or a decision edited without
    re-deriving fails by name.
    """
    from crucible.transfer.adjudication import build_adjudication

    block = _adjudication()
    rebuilt = build_adjudication(
        adjudicated_by=block["adjudicated_by"],
        adjudicated_on=block["adjudicated_on"],
        instance_ids=block["instance_ids"],
        decisions={i: {"codes": list(d["codes"])}
                   for i, d in block["decisions"].items()})
    assert rebuilt == block, (
        "the committed adjudication block is not what build_adjudication() "
        "emits for its own inputs. Whichever is right, a digest or a count in "
        "the fixture has been typed rather than derived.")


def test_the_fixtures_adjudication_is_accepted_by_the_loader():
    """Schema-valid is not reader-valid, and this block has both halves.

    `load_adjudication` re-derives the instance-set digest, the decisions digest
    and every count, and refuses on any disagreement. A fixture that satisfied
    the schema and would be rejected by the only code path that reads the record
    would be teaching a lane the wrong shape.
    """
    from crucible.transfer.adjudication import load_adjudication

    block = _adjudication()
    ledger = load_adjudication(block, block["instance_ids"])
    assert ledger.counts() == block["counts"]


def test_the_fixtures_adjudication_separates_the_union_from_the_sum():
    """The one arithmetic property this block exists to make checkable.

    `failing_v1_or_v2` is a UNION, not a total: an instance failing both
    criteria is counted under each part and once in the union. A fixture whose
    parts happened to add up to the union could not tell a correct
    implementation from one that adds, so this fixture is authored with an
    instance that fails both.
    """
    from crucible.transfer.adjudication import V1_CODES, V2_CODES

    block = _adjudication()
    # BOTH HALVES, and the first is the one that matters. Asserting only the
    # arithmetic tests the `counts` object; asserting only that some instance
    # carries codes from both families tests the `decisions`. The property is
    # that the two agree, so a mutation to either side has to be caught.
    both = [i for i, d in block["decisions"].items()
            if set(d["codes"]) & set(V1_CODES) and set(d["codes"]) & set(V2_CODES)]
    assert both, (
        "no instance in this fixture carries both a V1 and a V2 code, so the "
        "union and the sum agree and the fixture cannot distinguish them")
    counts = block["counts"]
    assert (counts["failing_v1"] + counts["failing_v2"]
            > counts["failing_v1_or_v2"]), (
        "%s fail both criteria and the counts still add up to the union, so "
        "the counts are not derived from these decisions" % both)


def test_the_known_bad_carries_a_defective_adjudication_bound_like_every_other(
        checker):
    """Every C11 promise is bound and demonstrated, and the new ones are no
    exception. Asserted specifically because a block added to the POSITIVE
    fixture alone would exercise the happy path and leave every refusal in that
    subschema unproven - which is the shape of the hole, not a fix for it."""
    errs = _validate(checker, _fixture(KNOWN_BAD_NAME))
    bound = _c11_binding(checker)["reasons"]
    adjudication_triples = [
        checker._triple(ev) for spec in bound for ev in spec.get("evidence", [])
        if checker._triple(ev)[0].startswith("/adjudication")]
    assert adjudication_triples, (
        "the known-bad declares no adjudication defect, so the closed-object "
        "and closed-vocabulary rules on that block are unexercised")
    for triple in adjudication_triples:
        assert any(checker._matches(triple, e) for e in errs), (
            "%s is promised and the schema does not produce it" % (triple,))


# ---------------------------------------------------- reasons are not triples
#
# THE 2026-08-29 ACCOUNTING DEFECT, FOUND BY AN INDEPENDENT REVIEWER.
# `pass_proven` incremented one counter per evidence TRIPLE and then printed it
# as a count of REASONS. Several reasons in this repository carry more than one
# triple, so 41 schema-bound reasons were reported as 45, the summary totalled
# 62 against 58 declared - and that 62 went into a handoff to an outside
# reviewer as a fact about this repository.
#
# A counting bug inside the gate that exists to stop counting bugs is the worst
# place for one, so the arithmetic is asserted here rather than printed and
# trusted. Every figure below is read from the gate's derived `PROVEN_COUNTS`;
# no expected value is typed into this file.


@pytest.fixture()
def proven_counts(checker):
    """The gate's own derived figures, from a real run against this repo."""
    ok, findings = checker.pass_proven()
    assert ok, "PROVEN is red, so its counts describe nothing: %s" % findings[:5]
    return dict(checker.PROVEN_COUNTS)


def test_every_declared_reason_lands_in_exactly_one_bucket(proven_counts):
    """The identity that makes the total mean anything. A reason is
    schema-bound, reader-bound, or recorded unenforced; there is no fourth kind
    and none is in two. If the three do not add back up to the declaration, the
    summary line about to be printed is wrong about this repository."""
    c = proven_counts
    assert (c["schema_reasons"] + c["reader_reasons"] + c["unenforced_reasons"]
            == c["declared_reasons"]), c
    assert c["accounted_reasons"] == c["declared_reasons"], c


def test_triples_are_counted_apart_from_the_reasons_they_demonstrate(
        proven_counts):
    """A reason needs at least one triple and may carry several, so the triple
    count is a floor on the reason count and never the same quantity."""
    c = proven_counts
    assert c["schema_triples"] >= c["schema_reasons"], c


def test_this_repository_actually_has_a_reason_with_more_than_one_triple(
        checker, proven_counts):
    """WITHOUT THIS, THE TEST ABOVE PASSES ON A REPOSITORY THAT CANNOT TELL THE
    TWO NUMBERS APART.

    `triples >= reasons` holds trivially when every reason carries exactly one
    triple, and that is true of almost every reason here - which is precisely
    what kept the defect invisible. What made it real is the handful that carry
    several. So the binding set itself must contain that case, and this says so
    out loud rather than leaving the consistency test unable to fail.
    """
    doc = json.loads(checker.BINDINGS.read_text(encoding="utf-8"))
    multi = [(name, r["index"], len(r["evidence"]))
             for name, entry in doc["fixtures"].items()
             for r in entry.get("reasons", []) if len(r.get("evidence", [])) > 1]
    assert multi, (
        "no reason in the binding set carries more than one evidence triple, "
        "so reasons and triples are numerically indistinguishable here and the "
        "consistency test above cannot fail for the defect it was written for")
    assert proven_counts["schema_triples"] > proven_counts["schema_reasons"], (
        "%s carry several triples each and the gate still reports the same "
        "number for both" % (multi,))


def test_the_summary_prints_reasons_and_triples_as_distinct_labelled_numbers(
        checker, proven_counts):
    """The half the reviewer actually read. The figures can be right internally
    and still be reported under the wrong noun, which is exactly what
    happened."""
    notes = " ".join(checker.PROVEN_NOTES)
    c = proven_counts
    assert "%d declared reasons" % c["declared_reasons"] in notes, notes
    assert "%d bound to schema validation" % c["schema_reasons"] in notes, notes
    assert "%d named error" % c["schema_triples"] in notes, notes
    assert c["schema_reasons"] != c["schema_triples"], (
        "the two numbers are equal in this run, so the summary cannot show "
        "that they are different quantities")


def test_the_summary_says_a_green_pass_is_not_a_claim_that_anything_is_enforced(
        checker, proven_counts):
    """Printed on EVERY run rather than recorded in a document nobody re-opens.
    A green PROVEN means every declared promise is ACCOUNTED FOR; an unenforced
    reason is accounted for by writing down that nothing keeps it, and it is
    still a gap."""
    notes = " ".join(checker.PROVEN_NOTES)
    assert "ACCOUNTED FOR" in notes, notes
    assert "NOT MEAN EVERY PROMISE IS ENFORCED" in notes, notes
    assert "%d reasons are recorded as gaps" \
        % proven_counts["unenforced_reasons"] in notes, notes


# A CARDINAL DIRECTLY QUANTIFYING "reasons", near the word "unenforced". The
# adjacency is what keeps it honest: a first version allowed any number within
# 120 characters and reported "`unenforced` is the one escape ... it records a
# reason" as a written-down count. A check with that false-positive rate gets
# switched off within a day, and then it is not a check.
_CARDINAL = (r"(?:\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven"
             r"|twelve)\b|\b\d+\b)")
_N_REASONS = _CARDINAL + r"\s+(?:[A-Za-z-]+\s+){0,2}reasons?\b"
UNENFORCED_COUNT_IN_PROSE = re.compile(
    _N_REASONS + r".{0,120}?\bunenforced\b"
    r"|\bunenforced\b.{0,140}?" + _N_REASONS, re.I | re.S)


def _prose(rel):
    """Every sentence a human wrote in a file, and none of its code.

    PROSE ONLY, ON PURPOSE. A first version scanned raw bytes and reported
    `schema_reasons += 1 ... elif "unenforced" in reason` as a written-down
    count - a hit on the implementation of the very thing being derived. A check
    with that false-positive rate gets switched off within a day, and then it is
    not a check. Comments and docstrings for Python; the document-level prose
    block for the binding artifact, which is where the stale SEVEN sat.
    """
    path = REPO / rel
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return " ".join(json.loads(text).get("_what_this_is", []))
    import ast
    import tokenize

    chunks = [c.string.lstrip("#") for c in
              tokenize.generate_tokens(io.StringIO(text).readline)
              if c.type == tokenize.COMMENT]
    tree = ast.parse(text)
    for node in [tree] + [n for n in ast.walk(tree) if isinstance(
            n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]:
        doc = ast.get_docstring(node)
        if doc:
            chunks.append(doc)
    return " ".join(" ".join(c.split()) for c in chunks)


@pytest.mark.parametrize("rel", [
    "scripts/contract-check.py",
    "contracts/golden/proof/must-fail-bindings.json",
])
def test_the_unenforced_count_is_written_down_nowhere(rel):
    """THE SAME DEFECT IN ITS DOCUMENTARY FORM.

    Both of these files said SEVEN unenforced reasons while the gate derived
    eight. Neither was edited when the eighth landed - they went stale by
    standing still, which no edit-time check can catch. The fix is not to
    correct the number in two places; it is that the number belongs in neither.

    This test file is deliberately not scanned: it holds the pattern, and a
    checker that flags its own specification is the failure mode this repository
    already has a ruling about.
    """
    hit = UNENFORCED_COUNT_IN_PROSE.search(_prose(rel))
    assert not hit, (
        "%s writes down how many reasons are unenforced: %r. That count has "
        "exactly one owner - the list itself - and pass_proven derives it on "
        "every run." % (rel, hit.group(0)[:140]))


def test_that_scan_can_still_find_a_written_down_count():
    """A NEGATIVE CASE FOR THE CHECK ABOVE, because a regex nothing exercises is
    a regex that could be a typo matching forever - and both green rows above
    are indistinguishable from that. This is the sentence the two files actually
    carried."""
    # Verbatim, both of them, off the two files as they stood before this fix.
    assert UNENFORCED_COUNT_IN_PROSE.search(
        "SEVEN REASONS ACROSS FOUR CONTRACTS ARE RECORDED `unenforced`.")
    assert UNENFORCED_COUNT_IN_PROSE.search(
        "WHY `unenforced` IS AN ESCAPE AND WHY IT IS NOT A RUBBER STAMP. Seven "
        "reasons across four contracts describe rejections their schema does "
        "not perform.")
    # And the shape that must stay quiet, or the check gets switched off.
    assert not UNENFORCED_COUNT_IN_PROSE.search(
        "Some declared reasons describe rejections their schema does not "
        "perform. The figure is derived by pass_proven and printed every run.")
    assert not UNENFORCED_COUNT_IN_PROSE.search(
        "`unenforced` is the one escape and it is policed in BOTH directions. "
        "It records a reason the schema does not actually enforce.")
