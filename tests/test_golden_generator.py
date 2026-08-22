"""test_golden_generator.py - `scripts/make-golden.py` must reproduce the goldens
that are committed, byte for byte.

WHY THIS EXISTS
----------------
`contracts/golden/` is what decouples the lanes: every lane develops against
these fixtures instead of against another lane's code, and `lanes-spec.md`
section 10 calls writing them "the single highest-leverage hour in the whole
build". Regenerating them is a documented one-command operation.

So a generator that has fallen behind the committed fixtures is not a stale
script. IT IS A LOADED GUN. Running the documented command silently reverts
whatever ruling last amended a fixture by hand, and hands every lane a fixture
that disagrees with the contract it is supposed to demonstrate.

That has happened TWICE, both found on 2026-08-22 and neither by anyone reading
the file:

  RULING 38 (`3f6ea1f`)  normalized C4's stored `origin` to the CLASS
                         ("armorer", not "armorer:3") and moved the round out
                         to an unhashed top-level `provenance` block. The
                         generator was never updated, so re-running it put
                         `"armorer:3"` back and deleted `provenance`.

  RULING 43 (`ec64a25`)  moved `benign_floor` to "26/26" and `near_miss_floor`
                         to "14/14" in both C7 fixtures by hand. The generator
                         was never updated, so re-running it emitted "24/24" -
                         and because those two fields are `const` in
                         `contracts/run_manifest.schema.json`, the regenerated
                         "valid" fixture FAILS ITS OWN SCHEMA. The KNOWN_BAD
                         fixture was worse: it would have failed for a SIXTH
                         reason its `_must_fail_because` list does not name, so
                         a lane fixing all five listed reasons would still see
                         red with nothing to tell it why.

Neither was visible to the test suite, because the suite reads the fixtures on
disk and never asks whether the thing that claims to produce them still does.

WHAT IT DOES NOT COVER, SAID OUT LOUD (section 8 rule 9)
--------------------------------------------------------
`make-golden.py` emits eight contracts' fixtures. `contracts/golden/` holds ten
pairs. C6 (evidence bundle) and C10 (objective set) are HAND-MAINTAINED and have
no generator at all, so this check cannot protect them - the second assertion
below names them rather than letting the gap pass as coverage.
"""

import importlib.util
import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
GOLDEN = REPO / "contracts" / "golden"
GENERATOR = REPO / "scripts" / "make-golden.py"

# Hand-maintained, no generator entry. Named so the hole is a declaration rather
# than a silence.
NOT_GENERATED = {"C6-evidence_bundle", "C10-objective_set"}


def _load_generator():
    """Import the generator as a module without running `main()`.

    Executing the script would WRITE the goldens, which would make this test
    pass by overwriting the very files it is checking - a check that repairs the
    thing it measures is not measuring anything.
    """
    spec = importlib.util.spec_from_file_location("_make_golden", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generated():
    return _load_generator().F


def test_the_generator_and_the_committed_goldens_are_the_same_bytes(generated):
    """The serialization here is copied from the generator's `main()` on
    purpose: `json.dumps(body, indent=2, ensure_ascii=False) + "\\n"`, written
    with LF. If that ever diverges this test is comparing a different question
    and should be updated to match the writer, not the other way round.
    """
    mismatches = []
    for name, body in sorted(generated.items()):
        path = GOLDEN / name
        if not path.exists():
            mismatches.append("%s: the generator emits it, the repo does not "
                              "carry it" % name)
            continue
        expected = json.dumps(body, indent=2, ensure_ascii=False) + "\n"
        actual = path.read_text(encoding="utf-8")
        if expected != actual:
            mismatches.append(
                "%s: re-running `python scripts/make-golden.py` would CHANGE "
                "this committed fixture. Whichever is right, the two must not "
                "disagree - the documented regeneration command silently "
                "reverts hand-edits." % name)
    assert not mismatches, "\n".join(mismatches)


def test_every_committed_golden_is_either_generated_or_declared_hand_written(generated):
    """A generator that quietly stopped covering a contract looks exactly like a
    contract that never had a generator. This makes the difference a
    declaration."""
    on_disk = {p.name for p in GOLDEN.glob("*.json")}
    covered = set(generated)
    uncovered = sorted(n for n in on_disk - covered
                       if n.rsplit(".", 2)[0] not in NOT_GENERATED)
    assert not uncovered, (
        "these goldens are on disk with no generator entry and are not on the "
        "declared hand-written list: %s. Add them to the generator or to "
        "NOT_GENERATED with the reason." % uncovered)


def test_the_c7_fixtures_carry_the_ruling_43_denominators(generated):
    """The specific regression. `benign_floor` and `near_miss_floor` are `const`
    in C7, so a stale value here does not make a weaker fixture - it makes a
    "valid" fixture that fails its own schema, and a KNOWN_BAD that fails for an
    undeclared reason."""
    contract = json.loads(
        (REPO / "contracts" / "run_manifest.schema.json").read_text(encoding="utf-8"))
    props = contract["properties"]["frozen_parameters"]["properties"]
    for name in ("C7-run_manifest.valid.json", "C7-run_manifest.KNOWN_BAD.json"):
        frozen = generated[name]["frozen_parameters"]
        for field in ("benign_floor", "near_miss_floor"):
            assert frozen[field] == props[field]["const"], (
                "%s emits %s=%r against the C7 const %r"
                % (name, field, frozen[field], props[field]["const"]))
