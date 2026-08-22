"""test_corpus_schema.py - the shape a corpus instance must have.

This shape is L2's, not a contract. `contracts/` freezes data that crosses a
BLINDNESS boundary (ruling 27); a corpus instance on disk crosses no such
boundary before it is loaded, so it gets a validator rather than a hash. What IS
hashed is the corpus at D5, and this validator is what stands between a
malformed instance and that hash.

Two decisions worth naming, because both are the same doctrine applied twice:

1. **The author never writes the instance ID.** `atk_<sha256(canonical(body))[:12]>`
   is content-addressed (`CONVENTIONS.md` section 2.5), and section 2.6's general
   rule is *never ask a model - or a person - to perform a deterministic
   computation.* The loader computes it. An author-supplied ID is refused rather
   than checked, because a checked ID is a second copy of a derived value.

2. **Exactly one call in the trace is the scored call, and it says so.** Taking
   "the last one" is positional, and a positional convention breaks silently the
   first time an instance ends with a confirmation email.
"""

import pytest

from tests import corpus_synthetic as syn

from corpus.errors import CorpusError  # noqa: E402
from corpus.model import load_part_a  # noqa: E402
from corpus.schema import instance_id, validate_instance  # noqa: E402

MANIFEST = load_part_a()


def ok(doc):
    return validate_instance(doc, manifest=MANIFEST)


def test_a_minimal_attack_validates():
    ok(syn.instance("a", "attack"))


def test_a_minimal_benign_fixture_validates():
    ok(syn.instance("b", "benign"))


def test_a_minimal_known_bad_validates():
    ok(syn.instance("k", "known_bad"))


@pytest.mark.parametrize("key", ["slug", "capability_classes", "tool_fqname",
                                 "scored_features", "scenario", "trace"])
def test_every_required_key_is_required(key):
    doc = syn.instance("a", "attack")
    del doc[key]
    with pytest.raises(CorpusError) as e:
        ok(doc)
    assert e.value.code == "E_MISSING_FIELD"
    assert key in e.value.detail


@pytest.mark.parametrize("kind", [None, "attack_", "fixture", 7])
def test_kind_is_checked_before_anything_else(kind):
    """`kind` is not on the list above because it is not merely required - it
    SELECTS the required list, and it selects the ID prefix. A missing or
    unknown kind is refused first and by its own code, because every later
    message would otherwise be written about the wrong kind of instance."""
    doc = syn.instance("a", "attack")
    if kind is None:
        del doc["kind"]
    else:
        doc["kind"] = kind
    with pytest.raises(CorpusError) as e:
        ok(doc)
    assert e.value.code == "E_UNKNOWN_KIND"


def test_an_author_supplied_instance_id_is_refused():
    with pytest.raises(CorpusError) as e:
        ok(syn.instance("a", "attack", instance_id="atk_deadbeef1234"))
    assert e.value.code == "E_AUTHOR_SUPPLIED_ID"


def test_the_instance_id_is_content_addressed_and_stable():
    doc = syn.instance("a", "attack")
    first = instance_id(doc)
    assert first.startswith("atk_") and len(first) == 16
    assert instance_id(dict(reversed(list(doc.items())))) == first


def test_a_benign_fixture_gets_a_different_id_prefix():
    assert instance_id(syn.instance("b", "benign")).startswith("fx_")


def test_an_unknown_capability_class_is_refused():
    with pytest.raises(CorpusError) as e:
        ok(syn.instance("a", "attack", capability_classes=["CAP_MOVES_CASH"]))
    assert e.value.code == "E_UNKNOWN_CAPABILITY_CLASS"


def test_unclassified_is_not_a_class_an_instance_may_claim():
    """Section 2.2: UNCLASSIFIED means *we do not know what this tool does*. An
    instance claiming it would be an attack against a tool nobody classified,
    which is a manifest defect wearing a corpus instance's clothes."""
    with pytest.raises(CorpusError) as e:
        ok(syn.instance("a", "attack", capability_classes=["UNCLASSIFIED"]))
    assert e.value.code == "E_UNKNOWN_CAPABILITY_CLASS"


def test_a_tool_the_manifest_does_not_declare_is_refused():
    with pytest.raises(CorpusError) as e:
        ok(syn.instance("a", "attack", tool_fqname="target.refund_agent.tools.wire"))
    assert e.value.code == "E_TOOL_NOT_IN_MANIFEST"


def test_the_declared_classes_must_match_part_a():
    """An instance that claims CAP_READS_PII against `issue_refund` would be
    scored against a class the tool does not carry, and ruling 22's membership
    match means the rule that was supposed to fire never does."""
    with pytest.raises(CorpusError) as e:
        ok(syn.instance("a", "attack", capability_classes=["CAP_READS_PII"]))
    assert e.value.code == "E_CLASS_NOT_ON_TOOL"


def test_a_training_family_must_be_one_of_the_six():
    with pytest.raises(CorpusError) as e:
        ok(syn.instance("a", "attack", family="F8"))
    assert e.value.code == "E_UNKNOWN_FAMILY"


def test_F4_may_not_appear_in_the_training_set():
    """F4 is the sealed family. An F4 instance with `sealed: false` is a
    held-out family instance sitting in the training corpus - the loop would
    learn on the very set the transfer claim says it never saw."""
    with pytest.raises(CorpusError) as e:
        ok(syn.instance("a", "attack", family="F4", sealed=False))
    assert e.value.code == "E_SEALED_FAMILY_IN_TRAINING"


def test_a_sealed_instance_of_a_training_family_is_refused():
    with pytest.raises(CorpusError) as e:
        ok(syn.instance("a", "attack", family="F1", sealed=True))
    assert e.value.code == "E_TRAINING_FAMILY_SEALED"


def test_exactly_one_call_must_be_marked_scored():
    doc = syn.instance("a", "attack")
    doc["trace"][0]["scored"] = True
    with pytest.raises(CorpusError) as e:
        ok(doc)
    assert e.value.code == "E_SCORED_CALL_COUNT"


def test_no_scored_call_is_refused():
    doc = syn.instance("a", "attack")
    doc["trace"][-1]["scored"] = False
    with pytest.raises(CorpusError) as e:
        ok(doc)
    assert e.value.code == "E_SCORED_CALL_COUNT"


def test_an_empty_trace_is_refused():
    with pytest.raises(CorpusError) as e:
        ok(syn.instance("a", "attack", trace=[]))
    assert e.value.code == "E_EMPTY_TRACE"


def test_a_trace_call_against_an_undeclared_tool_is_refused():
    doc = syn.instance("a", "attack")
    doc["trace"][0]["tool_fqname"] = "target.refund_agent.tools.wire"
    with pytest.raises(CorpusError) as e:
        ok(doc)
    assert e.value.code == "E_TOOL_NOT_IN_MANIFEST"


def test_a_scored_feature_using_an_undeclared_enum_value_is_refused():
    """`reason_code` is a Part A enum. A typo'd value is a feature no rule can
    name, so the pair it was supposed to separate separates on nothing."""
    doc = syn.instance("a", "attack",
                       scored_features={"reason_code": "DEFECTIV"})
    with pytest.raises(CorpusError) as e:
        ok(doc)
    assert e.value.code == "E_UNDECLARED_ENUM_VALUE"


def test_a_benign_fixture_must_declare_the_call_it_requires():
    """measurement-spec section 3.1: a benign fixture asserts a POSITIVE, not an
    absence. An agent that refuses everything must score zero on the benign
    floor, not a clean sweep of it, and that is only checkable if the fixture
    names the call that has to fire.

    No denominator is written here on purpose. This docstring said `0/24, not
    24/24` until 2026-08-22, a day after ruling 43 moved the floor to 26 - and a
    docstring is exactly the kind of restatement nothing can fail on. The number
    lives in `corpus/model.py::BENIGN_TOTAL`.
    """
    doc = syn.instance("b", "benign")
    del doc["required_call"]
    with pytest.raises(CorpusError) as e:
        ok(doc)
    assert e.value.code == "E_NO_REQUIRED_CALL"


def test_a_benign_fixture_must_say_whether_it_is_a_near_miss():
    doc = syn.instance("b", "benign")
    del doc["near_miss"]
    with pytest.raises(CorpusError) as e:
        ok(doc)
    assert e.value.code == "E_MISSING_FIELD"


def test_a_known_bad_must_declare_its_expected_verdict():
    """Not `must_fail: true`. Only five of the nine are breach fixtures - KB5
    expects REJECT, KB6 INVALID, KB8 **CLEAN**, KB9 a linter verdict - so a
    blanket boolean fails on KB8 BY DESIGN. The spine calls the "all nine must
    fail" phrasing FALSE, and a schema that admits a boolean invites it back."""
    doc = syn.instance("k", "known_bad")
    del doc["expected_verdict"]
    with pytest.raises(CorpusError) as e:
        ok(doc)
    assert e.value.code == "E_MISSING_FIELD"


def test_a_known_bad_may_expect_CLEAN():
    ok(syn.instance("k", "known_bad", expected_verdict="CLEAN"))


def test_must_fail_as_a_boolean_is_refused_by_name():
    doc = syn.instance("k", "known_bad", must_fail=True)
    with pytest.raises(CorpusError) as e:
        ok(doc)
    assert e.value.code == "E_MUST_FAIL_BOOLEAN"


def test_episode_fields_are_not_authored_on_the_instance():
    """Ruling 16: `episode.*` is FROZEN AT EPISODE START from the scenario's
    order/account record. An instance that writes them directly is an instance
    that can disagree with its own scenario, and the disagreement is invisible -
    which is one half of the single cheapest way to invalidate the headline."""
    doc = syn.instance("a", "attack")
    doc["episode"] = {"account_holder_email": "attacker@example.invalid"}
    with pytest.raises(CorpusError) as e:
        ok(doc)
    assert e.value.code == "E_EPISODE_FIELDS_AUTHORED"


def test_derived_fields_are_not_authored_on_the_instance():
    """Same doctrine on the other namespace. The plugin stamps `derived.*` in
    `before_tool`, overwriting anything the model wrote under that prefix
    (ruling 21). An authored value in the corpus would be a third writer."""
    doc = syn.instance("a", "attack")
    doc["trace"][-1]["args"]["derived.approval_tier"] = "T4"
    with pytest.raises(CorpusError) as e:
        ok(doc)
    assert e.value.code == "E_DERIVED_ARG_AUTHORED"
