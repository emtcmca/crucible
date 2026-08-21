"""test_sepby_split.py - ruling 17's split, and the refusal that makes it mean something.

Every attack/fixture pair is separated in exactly one of two ways:

  POL   the rule's predicate DIFFERS on the two sides. The policy tells them apart.
  ORC   the predicate is IDENTICAL on both sides; the APPROVAL_ORACLE decides.
  CUT   unseparable. Recorded, never counted (measurement-spec section 3.5).

**A suite the oracle separates produces IDENTICAL headline numbers to one the
policy separates.** Same ASR, same BPR, same curve - and only one of them is
evidence that a POLICY learned a capability boundary. Nothing else on the metric
board tells them apart, which is why ruling 17 makes printing the ratio a
permanent requirement rather than a nicety.

Target split: 18 policy / 4 oracle. Authoring gate: **if oracle-separated pairs
reach parity with policy-separated ones, STOP AND RE-AUTHOR.** At parity, half
the headline is a statement about a scripted oracle the builder wrote, wearing
the policy's name.

No real pairs exist yet - the 26-pair worksheet is a design instrument and the
instances are the project owner's authoring pass. So this machinery is built and
proven on synthetic input, and the one behaviour that matters most on an empty
corpus is that it REFUSES to report rather than reporting health.
"""

import pytest

from tests import corpus_synthetic as syn
from tests import strawman_corpus

from corpus.errors import CorpusError  # noqa: E402
from corpus.sepby import TARGET_ORACLE, TARGET_POLICY, split  # noqa: E402


def test_an_empty_pair_set_is_refused():
    """`scripts/conformance-sweep.py` states the pattern: a census that silently
    reported zero required checks would itself be a check that cannot fail. A
    split over zero pairs is the same object - it satisfies every threshold."""
    with pytest.raises(CorpusError) as e:
        split([])
    assert e.value.code == "E_NO_PAIRS"


def test_the_naive_split_reports_health_on_nothing():
    """The strawman half. 0 oracle-separated pairs never reach parity with 0
    policy-separated ones, so the naive version returns OK - a green light
    computed over an empty set, printed next to an ASR figure."""
    assert strawman_corpus.naive_sepby_split([])["status"] == "OK"


def test_the_target_split_is_reported_as_met():
    report = split(syn.pairs(18, 4))
    assert (report["policy"], report["oracle"]) == (18, 4)
    assert report["status"] == "OK"
    assert report["on_target"] is True
    assert (TARGET_POLICY, TARGET_ORACLE) == (18, 4)


def test_parity_is_a_stop_condition_not_a_warning():
    with pytest.raises(CorpusError) as e:
        split(syn.pairs(4, 4))
    assert e.value.code == "E_ORACLE_PARITY"


def test_oracle_majority_is_also_refused():
    with pytest.raises(CorpusError) as e:
        split(syn.pairs(3, 7))
    assert e.value.code == "E_ORACLE_PARITY"


def test_off_target_is_reported_but_does_not_stop():
    """17/4 is not the target and is not a stop condition. Conflating "not the
    number we planned" with "the result is invalid" trains people to route
    around the stop condition that is real."""
    report = split(syn.pairs(17, 4))
    assert report["status"] == "OK"
    assert report["on_target"] is False
    assert "17" in report["note"] and "18" in report["note"]


def test_cut_pairs_are_listed_and_excluded_from_the_denominator():
    """P21, P22, P23 were authored, found unseparable, and removed for a stated
    reason. A corpus that lists only what survived reads as though nothing was
    ever hard - and counting them in the split would make the ratio a statement
    about pairs no rule ever sees."""
    report = split(syn.pairs(18, 4, n_cut=3))
    assert report["policy"] == 18 and report["oracle"] == 4
    assert report["cut"] == 3
    assert len(report["cut_pairs"]) == 3


def test_a_cut_pair_must_say_why_it_was_cut():
    bad = syn.pairs(18, 4)
    bad.append(syn.pair("P99", "a", "b", "CUT"))
    with pytest.raises(CorpusError) as e:
        split(bad)
    assert e.value.code == "E_CUT_WITHOUT_REASON"


def test_a_pair_with_no_sep_by_label_is_refused():
    bad = syn.pairs(18, 4)
    del bad[0]["sep_by"]
    with pytest.raises(CorpusError) as e:
        split(bad)
    assert e.value.code == "E_SEP_BY_ABSENT"


def test_an_unknown_sep_by_label_is_refused():
    bad = syn.pairs(18, 4)
    bad[0]["sep_by"] = "policy"
    with pytest.raises(CorpusError) as e:
        split(bad)
    assert e.value.code == "E_SEP_BY_UNKNOWN"


def test_duplicate_pair_ids_are_refused():
    """Two pairs with one ID means one of them is invisible to the count, and
    the split is the only instrument that can see the difference between the two
    kinds of suite. It cannot be allowed to silently under-count."""
    bad = syn.pairs(18, 4)
    bad[1]["pair_id"] = bad[0]["pair_id"]
    with pytest.raises(CorpusError) as e:
        split(bad)
    assert e.value.code == "E_DUPLICATE_PAIR_ID"


def test_the_report_carries_the_sentence_that_must_be_printed():
    """Ruling 17 requires the ratio next to any ASR or BPR figure, with the same
    permanence as the k=1 label. Returning the sentence from the counter means
    the number and its caveat cannot be separated by a copy-paste."""
    report = split(syn.pairs(18, 4))
    assert "18" in report["reporting_line"] and "4" in report["reporting_line"]
    assert "oracle" in report["reporting_line"]
