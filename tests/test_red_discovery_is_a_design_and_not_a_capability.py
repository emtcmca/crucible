"""The discovery design exists, is well formed, and IS NOT SHIPPED.

WHY A TEST GUARDS A DOCUMENT THAT DESCRIBES NOTHING.

`docs/design/red-discovery-capability.md` describes a RED capability that
authors an attack the corpus does not hold. On 2026-08-23 nothing in this tree
does that. The risk is not that the design is wrong - it is that the design
QUIETLY BECOMES A CLAIM: a fourth `attack_mode` value slipped into an enum, a
`red_authored` provenance nobody can emit, a bundle able to assert a capability
the build does not have. On a judged submission that reads as shipped.

So the honest state is asserted mechanically in both directions:

  1  the design and its draft schema EXIST and the schema is a valid JSON Schema
     that a real validator will compile - a design nobody can run is not a
     design, it is a paragraph
  2  the draft is NOT under `contracts/`, NOT in `contracts/MANIFEST.json`, and
     NOT reachable by `contract-check`
  3  no enum anywhere in the shipped contract set admits a value only discovery
     could produce
  4  the strategist still has no path that authors an attack

(3) and (4) are the ones that go red the day someone half-implements this, and
they are deliberately phrased as claims about the CURRENT tree rather than as
opinions about the design. When discovery ships, these tests are the checklist
of what has to change with it: they should FAIL, be read, and be rewritten - not
deleted quietly.
"""

import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
DESIGN = REPO / "docs" / "design" / "red-discovery-capability.md"
DRAFT = REPO / "docs" / "design" / "red-discovery-attack-spec.schema.json"
CONTRACTS = REPO / "contracts"


# ---------------------------------------------------------------------------
# 1  IT EXISTS AND IT COMPILES
# ---------------------------------------------------------------------------

def test_the_design_and_its_draft_schema_are_both_on_disk():
    assert DESIGN.exists(), DESIGN
    assert DRAFT.exists(), DRAFT


def test_the_draft_schema_is_one_a_real_validator_will_compile():
    """A draft contract that does not compile is prose in JSON clothing, and it
    would be discovered at the moment someone tried to implement it rather than
    now."""
    from jsonschema.validators import Draft202012Validator

    schema = json.loads(DRAFT.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False, (
        "the draft admits extra keys, so the fields it deliberately OMITS - "
        "attack_id, family_id, scored_features, sealed - could be smuggled in "
        "beside it, which is the entire defect the shape exists to prevent")


def test_the_draft_omits_every_field_the_author_is_forbidden_to_write():
    """CONVENTIONS 2.6 (never ask a model to perform a deterministic
    computation), ruling 16 (`episode.*` frozen at episode start from the
    scenario), ruling 21 (`derived.*` has exactly one writer), and
    `corpus/schema.py`'s refusal of an author-supplied `instance_id`."""
    props = json.loads(DRAFT.read_text(encoding="utf-8"))["properties"]
    for forbidden in ("attack_id", "instance_id", "family_id",
                      "scored_features", "sealed", "episode", "derived"):
        assert forbidden not in props, (
            "the draft lets RED author %r. Every field in this list is derived "
            "by code or frozen by a ruling; a model writing one of them is a "
            "second writer to a value whose whole design is that it has exactly "
            "one." % forbidden)


def test_the_capability_class_enum_matches_the_manifest_module():
    """WRITTEN AFTER THE DRAFT SHIPPED WITH FOUR INVENTED CLASS NAMES.

    On 2026-08-24 this file's enum read `CAP_MUTATES_RECORD`,
    `CAP_SENDS_EXTERNAL`, `CAP_READS_SENSITIVE` and `CAP_CLOSES_CASE` - none of
    which exist - and omitted `CAP_INVOKES_AGENT`, which does. Four of six
    wrong, committed and pushed.

    The file's own `$comment` had already named the hazard: the values were
    "restated here ONLY because this file is not yet wired to
    `crucible.manifest.load.CAPABILITY_CLASSES`". **Naming a drift site is not
    guarding it.** Nothing compared the two lists, so the restatement was free
    to be wrong from the moment it was typed, and it was.

    What caught it was not a test. It was a live run: the round-1 patch the
    benign floor rejected named `CAP_MUTATES_DURABLE_STATE` and
    `CAP_INVOKES_AGENT` in its own failure text, and neither string appeared in
    this schema. A restated enum with no check is the same defect as a count
    taken on the wrong ref.
    """
    from crucible.manifest.load import CAPABILITY_CLASSES

    enum = json.loads(DRAFT.read_text(encoding="utf-8"))[
        "properties"]["target_capability_class"]["enum"]
    assert set(enum) == set(CAPABILITY_CLASSES), (
        "the draft's capability classes and the manifest module disagree. "
        "draft-only: %s | module-only: %s"
        % (sorted(set(enum) - set(CAPABILITY_CLASSES)),
           sorted(set(CAPABILITY_CLASSES) - set(enum))))


def test_the_draft_requires_the_world_and_not_only_the_payload():
    """THE CENTRAL DESIGN CLAIM, pinned so a later simplification cannot quietly
    reduce this back to `architecture-spec` 1.1's payload-only `AttackSpec`.

    An episode runs against an order/account record. `CorpusSeeds.world_for`
    builds one PER INSTANCE and refuses to fall back to a shared one. A spec
    with no `scenario` produces episodes the target has nothing to act on, which
    is the `F2-02` / `CUS-9142` shape - two corpus instances whose traces name an
    account their own scenarios do not state, and two of the five episodes live
    run 2 lost on 2026-08-23.
    """
    required = json.loads(DRAFT.read_text(encoding="utf-8"))["required"]
    assert "scenario" in required, required
    assert "turns" in required, required


# ---------------------------------------------------------------------------
# 2  IT IS NOT SHIPPED
# ---------------------------------------------------------------------------

def test_the_draft_is_not_a_contract_and_is_not_in_the_manifest():
    """Physically outside `contracts/`, and absent from the manifest that
    `contract-check` pass 1 hashes. Both halves matter: a file inside
    `contracts/` but missing from `CONTRACT_FILES` would be an unhashed contract,
    which is worse than either."""
    assert not (CONTRACTS / DRAFT.name).exists(), (
        "a copy of the draft has appeared under contracts/. A contract file the "
        "manifest does not hash is a contract with no freeze.")
    manifest = json.loads((CONTRACTS / "MANIFEST.json").read_text(encoding="utf-8"))
    named = {fn for entry in manifest["contracts"].values() for fn in entry["files"]}
    assert DRAFT.name not in named, named
    # ELEVEN since 2026-08-29, and the move was READ rather than deleted, which
    # is what the docstring above asks for. C11 is NOT discovery: it is
    # `contracts/transfer_evidence.schema.json`, which had been shipping OUTSIDE
    # the hashed registry - so `contract-check` reported every pass green
    # precisely because nothing hashed it. Registering it moved this number.
    #
    # The count stays pinned deliberately. It is a PROXY - it fires on any new
    # contract, not only on a discovery one - and the two assertions above are
    # the direct facts. The proxy is kept because its job is to make somebody
    # open this file whenever the contract set grows, and a self-updating count
    # would do nothing at all.
    assert manifest["contract_count"] == 11, (
        "the contract count moved. If discovery landed, this file is the "
        "checklist of what else had to move with it - read it, do not delete it.")


def test_no_shipped_enum_admits_a_value_only_discovery_could_produce():
    """The quiet-claim guard. `attack_mode` and both `provenance` enums are the
    three places a discovery capability would surface first, and a bundle able
    to assert one is a bundle able to overstate the build."""
    from crucible.red import ATTACK_MODES

    assert "discovery" not in ATTACK_MODES, ATTACK_MODES
    c6 = json.loads(
        (CONTRACTS / "evidence_bundle.schema.json").read_text(encoding="utf-8"))
    assert set(c6["properties"]["attack_mode"]["enum"]) == set(ATTACK_MODES)
    for where, node in (
            ("episodes[]", c6["properties"]["episodes"]["items"]["properties"]),
            ("attacks[]", c6["properties"]["attacks"]["items"]["properties"])):
        enum = node["provenance"]["enum"]
        assert set(enum) == {"training_corpus", "generated"}, (where, enum)


def test_the_strategist_still_has_no_path_that_authors_an_attack():
    """`vary()` preserves the seed's `attack_id` and `family_id` on ALL FOUR of
    its paths and rewrites only `instruction`. That is what makes `generated` a
    rephrasing rather than discovery, and it is load-bearing beyond the claim:
    `CorpusSeeds.world_for` joins on `attack_id`, so minting a new id would make
    every episode run against a world that is not the one the instance names.
    """
    import inspect

    from crucible.red import red as R

    src = inspect.getsource(R)
    assert "AttackSeed(" not in src.split("def vary", 1)[-1].split("\n    def ", 1)[0], (
        "`vary()` now constructs an AttackSeed. If it mints an id, the world "
        "join breaks; if it reuses one, the authored attack is not new.")
    assert "def author" not in src, (
        "crucible/red/red.py has grown an authoring entry point. Read "
        "docs/design/red-discovery-capability.md sections 4, 5 and 6 before "
        "this ships: scored-only by default, code-derived scored_features, and "
        "the sealed-collision check that RED must never be able to run.")
