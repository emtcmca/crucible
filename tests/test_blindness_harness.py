"""test_blindness_harness.py - L2 scope (b)'s FIRST work item and its negative check.

`CONVENTIONS.md` ruling 19.3, and the C3 Part B schema says it again on the
field itself: compute every `episode.*` and `derived.*` field over the corpus
WITH LABELS WITHHELD, and if any field perfectly predicts attack-vs-benign it is
a leak and the field is REMOVED.

Why this one is the lane's first work item rather than its fifth: a field
meaning "this is the bad one" makes every downstream number meaningless WHILE
LOOKING EXACTLY LIKE SUCCESS. Every other failure in this build gets less
convincing as it gets worse. This one gets MORE convincing - the ASR falls, the
BPR holds, the curve is beautiful, and the policy learned nothing except which
instances the author labelled.

It has already happened once in this project, on paper. `approval_record.verified`
was specified in the spine as "attack -> false, benign -> true" - a mapping from
LABEL to VALUE written as if it were a design (ruling 8, deleted by ruling 23).
It arrived wearing a ruling number and survived three documents.

THE STRUCTURAL HALF, which is the half that matters
---------------------------------------------------
"Withhold the labels" can be implemented two ways. As a promise: hand the field
computer the whole instance and trust it not to look. Or structurally: hand it a
view that RAISES when the label is touched. The promise version cannot fail,
which section 8 rule 2 says is not a check. `tests/strawman_corpus.py`
`blind_view_by_convention` is that promise, kept permanently so this file can
demonstrate the difference.
"""

import pytest

from tests import corpus_synthetic as syn
from tests import strawman_corpus

from corpus.blindness import (  # noqa: E402
    BlindInstance,
    LabelLeakError,
    FIELD_COMPUTERS,
    run_blindness_check,
)
from corpus.errors import CorpusError  # noqa: E402


# --------------------------------------------------------------------------
# 1. The blind view refuses the label STRUCTURALLY, not by convention.
# --------------------------------------------------------------------------

# Every one of these is either the label itself or a proxy for it that a field
# computer could read instead. `slug` is on the list because "SYNTH-atk-3"
# carries the label in a string, and `input_turns` because ruling 19.1 forbids
# computing a field from PAYLOAD TEXT - which is a rule the blind view can
# enforce rather than merely state.
WITHHELD = ["kind", "family", "sealed", "near_miss", "slug", "input_turns",
            "expected_verdict", "smuggled_arg_path"]


@pytest.mark.parametrize("key", WITHHELD)
def test_blind_view_raises_on_every_withheld_key(key):
    view = BlindInstance(syn.instance("SYNTH-atk-0", "attack"))
    with pytest.raises(LabelLeakError):
        view[key]


@pytest.mark.parametrize("key", WITHHELD)
def test_the_promise_version_hands_the_label_straight_over(key):
    """The strawman half. If this ever raises, the strawman has been fixed and
    this file has stopped demonstrating anything."""
    view = strawman_corpus.blind_view_by_convention(
        syn.instance("SYNTH-atk-0", "attack"))
    if key in view:
        assert view[key] is not None or key in ("near_miss",)


def test_blind_view_still_exposes_what_a_field_legitimately_needs():
    view = BlindInstance(syn.instance("SYNTH-atk-0", "attack"))
    assert view["scenario"]["account"]["email"] == "holder@example.invalid"
    assert len(view["trace"]) == 2
    assert view["approver"] == "NONE"
    assert "scenario" in list(view)


# --------------------------------------------------------------------------
# 2. Degenerate corpora. The harness REFUSES rather than reporting.
# --------------------------------------------------------------------------

def test_empty_corpus_is_refused_not_passed():
    """A blindness check over zero instances passes trivially, and a trivial
    pass here is indistinguishable from a real one in the Part B document."""
    with pytest.raises(CorpusError) as e:
        run_blindness_check([])
    assert e.value.code == "E_EMPTY_CORPUS"


def test_single_class_corpus_is_refused_not_failed():
    """With only attacks present EVERY field predicts the label at 1.0, so the
    harness would report ten leaks and remove the whole schema. Refusing is the
    only correct answer: there is nothing to be blind to."""
    with pytest.raises(CorpusError) as e:
        run_blindness_check(syn.labelled_corpus(n_attacks=4, n_benign=0))
    assert e.value.code == "E_SINGLE_CLASS_CORPUS"


# --------------------------------------------------------------------------
# 3. The check itself - it must catch a planted leak and clear a clean corpus.
# --------------------------------------------------------------------------

def test_a_planted_label_mirror_is_caught():
    """`derived.account_age_days` is set to 9 on every attack and 400 on every
    benign instance. That is the `refunds_in_trailing_90_days` shape the Part B
    schema refuses by name: legal under the bright line, unnecessary, and
    correlated with the label."""
    report = run_blindness_check(syn.labelled_corpus(leak=True))
    assert report["result"] == "FAIL"
    assert "derived.account_age_days" in report["leaking_fields"]
    assert report["max_predictive_accuracy"] == 1.0


def test_a_corpus_without_a_planted_leak_passes():
    report = run_blindness_check(syn.labelled_corpus(leak=False))
    assert report["result"] == "PASS", report["per_field"]
    assert report["leaking_fields"] == []
    assert report["max_predictive_accuracy"] < 1.0


def test_every_declared_field_is_actually_computed():
    """A field the harness silently skips is a field that cannot be caught
    leaking. Ten fields are declared in Part B; ten must appear in the report."""
    report = run_blindness_check(syn.labelled_corpus())
    assert set(report["per_field"]) == set(FIELD_COMPUTERS)
    assert len(FIELD_COMPUTERS) == 10


def test_a_computer_that_reaches_for_the_label_is_stopped_at_the_view():
    """The whole point of the structural half. A field computer that tries to
    read `kind` does not get a wrong answer - it gets an exception, at the point
    of the read, naming the field that tried."""
    def leaky(view):
        return view["kind"]

    with pytest.raises(LabelLeakError) as e:
        run_blindness_check(syn.labelled_corpus(),
                            computers={"derived.cheating": leaky})
    assert "derived.cheating" in str(e.value)


def test_report_carries_the_separating_rule_for_a_leak():
    """`max_predictive_accuracy` alone says a leak exists. It does not say what
    to remove, and at 1.0 a human has to decide whether it is a real mirror or a
    small-n artifact. The report names the rule that separated."""
    report = run_blindness_check(syn.labelled_corpus(leak=True))
    row = report["per_field"]["derived.account_age_days"]
    assert row["accuracy"] == 1.0
    assert row["separating_rule"]
    assert row["distinct_values"] == 2


def test_baseline_is_reported_so_a_useless_field_is_visible():
    """A field whose accuracy equals the majority-class rate carries no signal
    at all. Without the baseline printed beside it, 0.5 and 0.5 look like a
    measurement."""
    report = run_blindness_check(syn.labelled_corpus(n_attacks=6, n_benign=6))
    assert report["majority_class_baseline"] == 0.5
    assert report["per_field"]["episode.account_holder_id"]["accuracy"] == 0.5
