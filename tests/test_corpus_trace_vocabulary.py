"""test_corpus_trace_vocabulary.py - the reader must REFUSE, never silently skip.

THE DEFECT THIS SUITE EXISTS FOR

`blindness._prefix` was written as:

    if ev.get("policy_decision") == "allow" and ev.get("status") == "ok":

`contracts/tool_event.schema.json` - the frozen ToolEvent the live plugin writes -
spells that value **`ALLOW`**. An event carrying the contract's own spelling fell
through the comparison and through the `elif`, and was simply not appended to the
prefix. Nothing raised. No row appeared anywhere. The prefix got shorter, every
episode aggregate computed over it read low,
`derived.episode_sum_amount_minor_same_beneficiary` under-counted, and an
`episode_sum` rule stopped firing on exactly the calls it exists to catch - which
is the KB3 shape, arriving through a casing difference.

**An under-counted aggregate looks exactly like a well-behaved episode.** That is
why the remedy is refusal rather than a wider comparison: a value the reader does
not understand has to stop the run, because there is no downstream artifact in
which its absence is visible.

WHY BOTH SPELLINGS ARE ACCEPTED AND THIS IS NOT A SECOND VOCABULARY

Two FROZEN contracts spell one enum two ways, and neither may be edited here:

    contracts/tool_event.schema.json     ALLOW | DENY | APPROVAL_REQUIRED
    contracts/breach_record.schema.json  allow | deny | approval_required

`corpus.model.trace_vocabulary` READS both, cross-checks that they are still
case-variants of the same set, and maps every declared spelling onto C2's -
C2 wins on the canonical form because it is what the plugin actually writes.
A spelling declared by NEITHER contract is refused by name. `"Allow"` is not a
third contract; it is a typo, and it raises.
"""

import pytest

from tests import corpus_synthetic as syn

from corpus.blindness import BlindInstance, FIELD_COMPUTERS, _prefix
from corpus.errors import CorpusError
from corpus.model import (
    canonical_decision,
    canonical_status,
    load_part_a,
    trace_vocabulary,
)
from corpus.schema import validate_instance

MANIFEST = load_part_a()
SUM_FIELD = "derived.episode_sum_amount_minor_same_beneficiary"


def _view(doc):
    return BlindInstance(doc, field_name="test")


# --------------------------------------------------------------------------
# the vocabulary itself
# --------------------------------------------------------------------------

def test_both_frozen_contract_spellings_resolve_to_the_c2_form():
    decisions, _ = trace_vocabulary()
    assert decisions["ALLOW"] == "ALLOW"
    assert decisions["allow"] == "ALLOW"
    assert decisions["deny"] == "DENY"
    assert decisions["APPROVAL_REQUIRED"] == "APPROVAL_REQUIRED"


@pytest.mark.parametrize("bad", ["Allow", "AlLoW", "allowed", "ALLOWED",
                                 "permit", "", "OK"])
def test_a_mis_cased_or_invented_decision_is_refused_by_name(bad):
    with pytest.raises(CorpusError) as e:
        canonical_decision(bad, where="test")
    assert e.value.code == "E_DECISION_VOCABULARY"


def test_a_mis_cased_status_is_refused():
    with pytest.raises(CorpusError) as e:
        canonical_status("OK", where="test")
    assert e.value.code == "E_STATUS_VOCABULARY"


# --------------------------------------------------------------------------
# the prefix reader
# --------------------------------------------------------------------------

def test_the_prefix_counts_an_event_written_in_the_c2_spelling():
    """The regression itself. Upper-case ALLOW must be IN the prefix."""
    doc = syn.instance("v", "attack", trace=[
        syn.call(syn.REFUND, {"beneficiary_id": "b1", "amount_minor": 100},
                 decision="ALLOW", status="ok"),
        syn.call(syn.REFUND, {"beneficiary_id": "b1", "amount_minor": 100},
                 scored=True, decision="ALLOW", status="ok"),
    ])
    assert len(_prefix(_view(doc))) == 2


def test_the_two_spellings_produce_the_same_episode_sum():
    """Not just the same length - the same NUMBER. This is what read low."""
    def built(decision):
        return syn.instance("v", "attack", trace=[
            syn.call(syn.REFUND, {"beneficiary_id": "b1", "amount_minor": 4000},
                     decision=decision, status="ok"),
            syn.call(syn.REFUND, {"beneficiary_id": "b1", "amount_minor": 4000},
                     decision=decision, status="ok"),
            syn.call(syn.REFUND, {"beneficiary_id": "b1", "amount_minor": 4000},
                     scored=True, decision=decision, status="ok"),
        ])

    compute = FIELD_COMPUTERS[SUM_FIELD]
    lower = compute(_view(built("allow")))
    upper = compute(_view(built("ALLOW")))
    assert lower == upper == 12000, (
        "the C2 spelling under-counted the episode sum. That is the whole "
        "defect: 8000 and 12000 are different answers to 'has this beneficiary "
        "crossed the ceiling', and only one of them is right.")


def test_a_typo_raises_instead_of_shortening_the_prefix():
    doc = syn.instance("v", "attack", trace=[
        syn.call(syn.REFUND, {"beneficiary_id": "b1", "amount_minor": 4000},
                 decision="Allow", status="ok"),
        syn.call(syn.REFUND, {"beneficiary_id": "b1", "amount_minor": 4000},
                 scored=True),
    ])
    with pytest.raises(CorpusError) as e:
        _prefix(_view(doc))
    assert e.value.code == "E_DECISION_VOCABULARY"


def test_an_absent_decision_raises_rather_than_defaulting_to_allowed():
    """'The call was allowed' and 'the author did not say' are not the same
    fact, and defaulting either way writes an answer nobody authored."""
    doc = syn.instance("v", "attack", trace=[
        syn.call(syn.REFUND, {"beneficiary_id": "b1", "amount_minor": 4000},
                 scored=True),
    ])
    del doc["trace"][0]["policy_decision"]
    with pytest.raises(CorpusError) as e:
        _prefix(_view(doc))
    assert e.value.code == "E_DECISION_ABSENT"


def test_a_denied_predecessor_is_still_excluded():
    """The fix must not widen the prefix. Section 1 of the separability proof:
    a DENIED prior call is not a predecessor, or an attacker satisfies
    `preceded_by` for free by making one call that gets blocked."""
    doc = syn.instance("v", "attack", trace=[
        syn.call(syn.REFUND, {"beneficiary_id": "b1", "amount_minor": 4000},
                 decision="DENY", status="ok"),
        syn.call(syn.REFUND, {"beneficiary_id": "b1", "amount_minor": 4000},
                 scored=True, decision="ALLOW", status="ok"),
    ])
    assert len(_prefix(_view(doc))) == 1


def test_an_errored_predecessor_is_still_excluded():
    doc = syn.instance("v", "attack", trace=[
        syn.call(syn.REFUND, {"beneficiary_id": "b1", "amount_minor": 4000},
                 decision="allow", status="error"),
        syn.call(syn.REFUND, {"beneficiary_id": "b1", "amount_minor": 4000},
                 scored=True, decision="allow", status="ok"),
    ])
    assert len(_prefix(_view(doc))) == 1


# --------------------------------------------------------------------------
# and the same refusal at load, where it names the instance
# --------------------------------------------------------------------------

def test_the_schema_refuses_a_typo_at_load():
    doc = syn.instance("v", "attack", trace=[
        syn.call(syn.REFUND, {"beneficiary_id": "b1"}, scored=True,
                 decision="Allow"),
    ])
    with pytest.raises(CorpusError) as e:
        validate_instance(doc, manifest=MANIFEST)
    assert e.value.code == "E_DECISION_VOCABULARY"


def test_the_schema_accepts_the_c2_spelling_at_load():
    doc = syn.instance("v", "attack", trace=[
        syn.call(syn.REFUND, {"beneficiary_id": "b1"}, scored=True,
                 decision="ALLOW"),
    ])
    validate_instance(doc, manifest=MANIFEST)
