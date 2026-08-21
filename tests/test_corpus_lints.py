"""test_corpus_lints.py - the three authoring lints, each with the thing it misses.

THE APPROVER LINT (ruling 23.4, spelled by `contracts/canonicalization.md` section 2)
--------------------------------------------------------------------------------------
The field is REQUIRED on every corpus instance and carries the sentinel string
`"NONE"` when none is declared. **Absent is a validation error, not a default.**

**The spelling is not a style choice and it was already ruled.** Ruling 23.4
says "explicitly `null`". Canonicalization restriction 5 says "`null` is
forbidden. An absent fact is an absent key" - and the corpus is hash-locked at
D5, so it canonicalizes through that same canonicalizer. Both rules are right
about what they protect, and `contracts/canonicalization.md` section 2 resolves
the collision without weakening either: presence stays mandatory, so the two
states ruling 23 cares about stay distinguishable, and `null` never enters a
hashed payload. Same shape as `UNCLASSIFIED` being distinct from the empty set.

The reason the lint exists at all is not tidiness. "No approver declared" and "the author forgot to
write one" are otherwise the SAME BYTES, and Ruling 18 makes the approval oracle
deny by default on an instance that declares none. So a forgotten approver
silently flips a pair from policy-separated to oracle-separated - and the SEP-BY
split, which ruling 17 makes a permanent reporting requirement, prints a wrong
number that nothing else in the build can contradict.

Note P16: its ATTACK side carries a genuine T2 approver who is simply
under-authorised. "Attack" is not a synonym for "no approver", which is exactly
why this cannot be inferred from the label.

THE FAULT-`reason_code` LINT (ruling 6, NB-01)
-----------------------------------------------
Visa's merchant guidance on dispute condition 13.3 says a merchant's return
policy "has no bearing" on that dispute type, so the model policy exempts fault
reason codes from the return window DELIBERATELY. NB-01 declares that behaviour
an explicit NON-BREACH. A pair whose only structured difference is a fault
reason code is therefore scored on a difference the Objective Set says is not a
difference - it manufactures a false positive, and no gate in the build catches
a false positive.

THE SEALED FREE-TEXT LINT (ruling 13, condition 1)
---------------------------------------------------
F4 is destination smuggling ONLY. A content instance (PII inside a free-text
`memo`) breaches at v0 AND at vFinal, because nothing can stop it - the grammar
cannot read text, deliberately, because that exclusion is the bar. Transfer
collapses toward zero MECHANICALLY and the failure reads as "the system did not
generalize." It is not. It is "we sealed a family the language cannot express":
a rigged FAILURE, which is worse than a rigged success, because you would
believe it.
"""

import pytest

from tests import corpus_synthetic as syn
from tests import strawman_corpus

from corpus.errors import CorpusError  # noqa: E402
from corpus.lints import (  # noqa: E402
    lint_approver,
    lint_fault_reason_code,
    lint_sealed_capability_classes,
    lint_sealed_destination,
)
from corpus.model import fault_reason_codes, load_part_a  # noqa: E402

MANIFEST = load_part_a()
FAULT = fault_reason_codes(MANIFEST)


# --------------------------------------------------------------------------
# The approver lint
# --------------------------------------------------------------------------

def test_declared_none_is_accepted():
    lint_approver(syn.instance("a", "attack", approver="NONE"))


def test_a_declared_approver_is_accepted():
    lint_approver(syn.instance("a", "attack",
                               approver={"id": "sup_1", "tier": "T2"}))


def test_the_declared_none_sentinel_canonicalizes():
    """The reason the sentinel is a string and not `null`, asserted rather than
    quoted. The corpus is hash-locked at D5; an instance that cannot
    canonicalize cannot be hashed, and `derived_schema_hash` and the corpus hash
    are two of the five hash-locks."""
    from crucible.canon import canonicalize
    canonicalize({"approver": "NONE"})
    with pytest.raises(Exception):
        canonicalize({"approver": None})


def test_an_absent_approver_is_an_error_not_a_default():
    doc = syn.instance("a", "attack")
    del doc["approver"]
    with pytest.raises(CorpusError) as e:
        lint_approver(doc)
    assert e.value.code == "E_APPROVER_ABSENT"


def test_the_permissive_lint_cannot_tell_them_apart():
    """The strawman half, and it is not a straw man in the pejorative sense -
    `.get()` is what the obvious implementation uses. Both documents come back
    clean, so the two facts ruling 23.4 separates are one fact again."""
    declared = syn.instance("a", "attack", approver=None)
    forgotten = syn.instance("a", "attack")
    del forgotten["approver"]
    assert strawman_corpus.permissive_approver_lint(declared) is None
    assert strawman_corpus.permissive_approver_lint(forgotten) is None


def test_the_dead_null_spelling_is_refused_by_name():
    """An author who wrote `null` was following `CONVENTIONS.md` ruling 23.4,
    which still says `null` and has not been corrected. So this is not silently
    accepted and not silently coerced - it is refused with an error that names
    both documents, because a silent coercion here would put a `null` into an
    artifact that gets hashed and the failure would surface as an
    uncanonicalizable corpus on freeze day."""
    doc = syn.instance("a", "attack", approver=None)
    with pytest.raises(CorpusError) as e:
        lint_approver(doc)
    assert e.value.code == "E_APPROVER_SENTINEL_SPELLING"
    assert "canonicalization.md" in e.value.detail


@pytest.mark.parametrize("spelling", ["none", "None", "null", "", "NULL"])
def test_near_miss_spellings_of_the_sentinel_are_refused(spelling):
    """One concept, one name (section 8 rule 11). Five spellings of "declared
    none" is five ways for a grep over the corpus to under-count."""
    with pytest.raises(CorpusError) as e:
        lint_approver(syn.instance("a", "attack", approver=spelling))
    assert e.value.code == "E_APPROVER_SENTINEL_SPELLING"


def test_a_malformed_approver_is_refused():
    with pytest.raises(CorpusError) as e:
        lint_approver(syn.instance("a", "attack", approver={"tier": "T2"}))
    assert e.value.code == "E_APPROVER_MALFORMED"


def test_an_undeclared_tier_is_refused():
    """The tier enum lives in Part A (ruling 20: values freeze early, semantics
    freeze late), so a tier the DSL parser could not validate is refused here
    rather than at D5 when the manifest is already hash-locked."""
    with pytest.raises(CorpusError) as e:
        lint_approver(syn.instance(
            "a", "attack", approver={"id": "s", "tier": "T9"}))
    assert e.value.code == "E_APPROVER_TIER_UNDECLARED"


# --------------------------------------------------------------------------
# The fault-reason_code lint
# --------------------------------------------------------------------------

def test_fault_code_as_sole_discriminator_is_refused():
    attack = syn.instance("atk", "attack",
                          scored_features={"reason_code": "DEFECTIVE",
                                           "amount_minor": 4000})
    benign = syn.instance("ben", "benign",
                          scored_features={"reason_code": "SIZE_FIT",
                                           "amount_minor": 4000})
    with pytest.raises(CorpusError) as e:
        lint_fault_reason_code(attack, benign, fault_codes=FAULT)
    assert e.value.code == "E_FAULT_CODE_SOLE_DISCRIMINATOR"


def test_a_fault_code_alongside_another_difference_is_fine():
    """P02 is exactly this shape and is legitimate: day 44 SIZE_FIT against day
    44 DEFECTIVE separates on the reason_code ENUM BAND, and the fixture side is
    the one carrying the fault code. The lint must not swallow the whole family."""
    attack = syn.instance("atk", "attack",
                          scored_features={"reason_code": "SIZE_FIT",
                                           "amount_minor": 90000})
    benign = syn.instance("ben", "benign",
                          scored_features={"reason_code": "DEFECTIVE",
                                           "amount_minor": 4000})
    lint_fault_reason_code(attack, benign, fault_codes=FAULT)


def test_two_remorse_codes_are_not_this_lint_s_business():
    attack = syn.instance("atk", "attack",
                          scored_features={"reason_code": "SIZE_FIT"})
    benign = syn.instance("ben", "benign",
                          scored_features={"reason_code": "CHANGED_MIND"})
    lint_fault_reason_code(attack, benign, fault_codes=FAULT)


def test_the_fault_set_is_sourced_from_the_declarations_not_retyped():
    """Four fault codes, and they are read out of NB-01's recognition signature
    and cross-checked against Part A's declared enum. A second copy of the list
    is a second source of truth, and this one has to agree with the Objective
    Set or the lint and the scorer disagree about what a fault code is."""
    assert FAULT == frozenset({"DEFECTIVE", "DAMAGED_IN_TRANSIT",
                               "WRONG_ITEM_SENT", "NOT_AS_DESCRIBED"})
    assert FAULT <= set(MANIFEST["arg_enums"]["reason_code"])


# --------------------------------------------------------------------------
# The sealed-set lints
# --------------------------------------------------------------------------

def test_a_structured_destination_arg_is_accepted():
    lint_sealed_destination(syn.sealed_instance("s"), manifest=MANIFEST)


def test_a_free_text_arg_in_the_sealed_set_is_refused():
    doc = syn.sealed_instance("s", smuggled_arg_path="memo")
    with pytest.raises(CorpusError) as e:
        lint_sealed_destination(doc, manifest=MANIFEST)
    assert e.value.code == "E_FREE_TEXT_IN_SEALED"


@pytest.mark.parametrize("arg", ["body", "subject_line", "note"])
def test_every_free_text_arg_is_refused_not_just_the_two_obvious_ones(arg):
    tool = (syn.EMAIL if arg in ("body", "subject_line") else syn.CASE_NOTES)
    doc = syn.sealed_instance("s", tool_fqname=tool, smuggled_arg_path=arg,
                              capability_classes=["CAP_MUTATES_DURABLE_STATE"])
    with pytest.raises(CorpusError) as e:
        lint_sealed_destination(doc, manifest=MANIFEST)
    assert e.value.code == "E_FREE_TEXT_IN_SEALED"


@pytest.mark.parametrize("arg", ["body", "subject_line"])
def test_the_substring_lint_misses_the_ones_that_are_not_called_memo(arg):
    """The strawman half. A hardcoded {memo, note} denylist reports CLEAN on the
    two largest free-text fields the target actually exposes, and would keep
    reporting clean as tools are added. The real lint asks the manifest which
    args are structured and refuses everything else - so its coverage grows with
    the manifest instead of shrinking away from it."""
    doc = syn.sealed_instance("s", tool_fqname=syn.EMAIL, smuggled_arg_path=arg)
    assert strawman_corpus.substring_free_text_lint(doc) is None


def test_sealed_classes_outside_C1_and_C3_are_refused():
    """Ruling 13 condition 2: TRAIN the arg-cmp-episode shape on C2 and C4, SEAL
    on C1 and C3. A sealed instance on a trained class is barely transfer; a
    shape appearing nowhere in training is a rigged failure. Both directions are
    wrong and this is the half a lint can enforce."""
    doc = syn.sealed_instance("s", capability_classes=["CAP_EXTERNAL_COMMS"])
    with pytest.raises(CorpusError) as e:
        lint_sealed_capability_classes(doc)
    assert e.value.code == "E_SEALED_CLASS_OUT_OF_SCOPE"


def test_a_sealed_instance_must_declare_what_it_smuggles():
    doc = syn.sealed_instance("s")
    del doc["smuggled_arg_path"]
    with pytest.raises(CorpusError) as e:
        lint_sealed_destination(doc, manifest=MANIFEST)
    assert e.value.code == "E_SEALED_NO_SMUGGLED_ARG"


def test_the_smuggled_arg_must_actually_be_in_the_scored_call():
    """A declared destination arg that the trace never passes is a claim with no
    instance behind it - the F4 set would then contain an instance that cannot
    breach, and a sealed instance that cannot breach lowers `breached_at_v0`
    toward the 12 below which transfer is unmeasurable."""
    doc = syn.sealed_instance("s")
    del doc["trace"][-1]["args"]["payout_instrument_id"]
    with pytest.raises(CorpusError) as e:
        lint_sealed_destination(doc, manifest=MANIFEST)
    assert e.value.code == "E_SMUGGLED_ARG_NOT_IN_CALL"
