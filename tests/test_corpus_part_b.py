"""test_corpus_part_b.py - C3 Part B, and the gate that stands in front of its freeze.

Ruling 20 split the capability manifest into two artifacts with two freeze dates
because ruling 19 asked for two things one artifact cannot do: the `derived.*`
definitions must be hashed into a manifest that locks at D3 WITH THE TARGET, and
they must survive a mechanical blindness check over a corpus that does not exist
until D5.

  PART A  capability_manifest.json   D3, with the target      manifest_hash
  PART B  derived_schema.json        D5, with the corpus      derived_schema_hash
                                     **GATED ON THE BLINDNESS CHECK PASSING**

"Gated on" is the load-bearing phrase and it is the thing this file makes
structural. If the builder can produce a Part B document while holding a FAILING
blindness report, then the gate is a sentence in a schema comment - and a
sentence is what gets skipped at 1am on the day the corpus finally builds.

**No Part B document is written to disk by this lane yet, and that is
deliberate.** The schema requires a `blindness_check` block with a real
`result`, and there is no corpus to run the check over. Writing one now would
mean fabricating either a PASS or a measurement, and `CONVENTIONS.md` section 8
rule 12 is exactly about status assertions that were true of nothing.
"""

import pytest

from tests import corpus_synthetic as syn

from corpus.blindness import run_blindness_check  # noqa: E402
from corpus.errors import CorpusError  # noqa: E402
from corpus.part_b import build_part_b  # noqa: E402
from crucible.manifest.load import load_part_b  # noqa: E402


def _report(leak=False):
    return run_blindness_check(syn.labelled_corpus(leak=leak))


def test_a_passing_report_produces_a_document():
    doc = build_part_b(_report())
    assert doc["schema_version"] == 1
    assert len(doc["episode_fields"]) == 3
    # SEVEN until 2026-08-23. `derived.risk_hold_open` is the eighth.
    assert len(doc["derived_fields"]) == 8
    assert doc["blindness_check"]["result"] == "PASS"
    assert doc["blindness_check"]["run_at"] == "D5_before_freeze"
    assert doc["blindness_check"]["labels_withheld"] is True


def test_a_failing_report_refuses_to_produce_a_document():
    """The gate, made structural. The remedy for a failing check is to REMOVE
    the leaking field and re-run - a pre-run repair, which is ordinary. Freezing
    anyway is the mid-run weakening section 8 rule 3 forbids."""
    with pytest.raises(CorpusError) as e:
        build_part_b(_report(leak=True))
    assert e.value.code == "E_BLINDNESS_FAILED"
    assert "derived.account_age_days" in e.value.detail


def test_a_document_built_without_any_report_at_all_is_refused():
    with pytest.raises(CorpusError) as e:
        build_part_b(None)
    assert e.value.code == "E_NO_BLINDNESS_REPORT"


def test_part_b_hashes_through_the_real_loader():
    """`derived_schema_hash` is one of the five hash-locks. This asserts the
    document L2 produces is one `crucible.manifest` can actually hash, rather
    than one that merely looks right - the float in `max_predictive_accuracy`
    is refused inside a canonical payload and is stripped by an ENUMERATED
    exclusion, not by "strip whatever fails to canonicalize"."""
    import json
    import pathlib
    import tempfile

    doc = build_part_b(_report())
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "derived_schema.json"
        p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8",
                     newline="\n")
        loaded, digest = load_part_b(str(p))
    assert len(digest) == 16
    assert int(digest, 16) >= 0


def test_the_hash_does_not_move_when_only_the_measured_accuracy_moves():
    """Two runs whose FIELDS are identical and whose measured accuracy differs
    are the same schema. If the hash moved, the identity of Part B would depend
    on a measurement rather than on a definition, and every learned rule would
    be flagged `needs_revalidation` by a number that changed nothing."""
    import json
    import pathlib
    import tempfile

    a = build_part_b(_report())
    b = build_part_b(_report())
    b["blindness_check"]["max_predictive_accuracy"] = 0.5001

    digests = []
    with tempfile.TemporaryDirectory() as d:
        for i, doc in enumerate((a, b)):
            p = pathlib.Path(d) / ("pb%d.json" % i)
            p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8",
                         newline="\n")
            digests.append(load_part_b(str(p))[1])
    assert digests[0] == digests[1]


def test_the_hash_DOES_move_when_a_field_is_removed():
    """The other direction, and it is the half that gets skipped. A lock that
    never moves is indistinguishable from a lock that is not looking - ruling 30
    found exactly that in `target_agent_hash`, which covered tool NAMES and not
    tool BODIES, so a target could be rewritten to approve everything and still
    cite the hash it was frozen at."""
    import json
    import pathlib
    import tempfile

    a = build_part_b(_report())
    b = build_part_b(_report())
    b["derived_fields"] = b["derived_fields"][:-1]

    digests = []
    with tempfile.TemporaryDirectory() as d:
        for i, doc in enumerate((a, b)):
            p = pathlib.Path(d) / ("pb%d.json" % i)
            p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8",
                         newline="\n")
            digests.append(load_part_b(str(p))[1])
    assert digests[0] != digests[1]


# The `separates_pair` convention IS enforced in code - by the test below, and
# by nothing else. Two documents written on 2026-08-23 asserted the opposite
# ("nothing enforces this in code - I grepped, there is no check"), so the
# suspension arrives here as a NAMED ALLOW-LIST rather than as a deleted
# assertion. A deleted assertion would also let the NEXT unjustified field
# through, which is the whole reason the convention exists.
PAIRLESS_BY_RULING = {
    # 2026-08-23. Exists because the frozen clause
    # `inv_escalated_to_a_queue_that_cannot_act` scored FOUR ordinary benign
    # fixtures as breaches and no `exempt_when` the grammar can express
    # separates `ORD-08` and `ORD-11` from the attacks - measured, not
    # sampled. It separates no AUTHORED PAIR because the pairs are about
    # policy predicates and the approval oracle, not about Objective Set
    # clauses. See docs/decisions-pending/returns-t2-false-positive-2026-08-23.
    "derived.risk_hold_open",
}


def test_every_derived_field_names_a_pair_it_exists_to_separate():
    """The Part B schema says it in a comment: *a field separating NO pair
    should not exist*. `derived.refunds_in_trailing_90_days` is the named
    example - legal under the bright line, unnecessary, and the strongest
    candidate in the set to fail the blindness check."""
    doc = build_part_b(_report())
    for f in doc["derived_fields"]:
        if f["name"] in PAIRLESS_BY_RULING:
            assert f["separates_pair"] == [], (
                "%s is on the pairless allow-list and now names a pair. Take it "
                "off the list rather than leaving a stale exemption standing."
                % f["name"])
            continue
        assert f["separates_pair"], f["name"]


def test_the_pairless_allow_list_is_exactly_one_entry_long():
    """THE GUARD ON THE GUARD. An allow-list is a hole, and a hole that can be
    widened by adding a line is not a suspension of a convention - it is the
    end of one. A second entry has to be a deliberate edit to this number, in a
    commit somebody reviews."""
    assert len(PAIRLESS_BY_RULING) == 1, sorted(PAIRLESS_BY_RULING)


def test_no_refused_field_can_be_in_the_document():
    doc = build_part_b(_report())
    names = {f["name"] for f in doc["derived_fields"]}
    assert "derived.memo_contains_pii" not in names
    assert "derived.refunds_in_trailing_90_days" not in names
    assert "approval_record.verified" not in names
