"""The sentence that says WHY G7/G8 evaluated nothing.

It is written into two places that a reader treats as evidence - the bundle's
`execution_provenance.g7_g8_detail` and the campaign's RUN INVALID banner - and
until 2026-08-23 both chose it the same wrong way.

`gate_summary` derives `g7_g8_exercised` from the gate's own findings: there are
G7/G8 findings, `skip_cloud` is off, and at least one of them is not
UNEVALUABLE. That is THREE ways to be false. Both callers branched on
`cloud_assertions` alone and folded the other two together, so a `--live` run
whose probes all came back UNEVALUABLE printed *"no candidate ever reached the
gate, so it evaluated nothing"* while `calls` sat at 1 in the same dict - and
the sibling branch two lines above it already read `calls`.

The failure is not cosmetic. UNEVALUABLE is the outcome this repository treats
as worse than a failure, because "all gates passed" and "no gate could decide"
read the same to anyone skimming. A banner that blames the loop sends the reader
looking for a candidate that never came, instead of at credentials that did not
work.
"""

from crucible.conductor.bundle import g7_g8_not_exercised_because


OFFLINE = {"cloud_assertions": "SKIPPED_OFFLINE", "calls": 0,
           "g7_g8_exercised": False}
LIVE_NEVER_CALLED = {"cloud_assertions": "LIVE", "calls": 0,
                     "g7_g8_exercised": False}
LIVE_ALL_UNEVALUABLE = {"cloud_assertions": "LIVE", "calls": 1,
                        "g7_g8_exercised": False}


def test_offline_says_the_gate_made_no_gcloud_call():
    said = g7_g8_not_exercised_because(OFFLINE)
    assert "skip_cloud=True" in said
    assert "NO G7 OR G8 CLAIM MAY BE MADE" in said


def test_a_gate_the_loop_never_called_says_so():
    said = g7_g8_not_exercised_because(LIVE_NEVER_CALLED)
    assert "no candidate ever reached the gate" in said


def test_a_gate_that_was_called_and_could_not_decide_never_claims_it_was_not_called():
    """THE REGRESSION. `calls == 1` and every assertion UNEVALUABLE."""
    said = g7_g8_not_exercised_because(LIVE_ALL_UNEVALUABLE)
    assert "no candidate ever reached the gate" not in said, (
        "the gate WAS reached - calls == 1 - and this sentence tells the "
        "reader it was not. `calls` is in the same dict this function was "
        "handed.")
    assert "UNEVALUABLE" in said
    assert "1 candidate(s)" in said


def test_the_three_reasons_are_three_different_sentences():
    """A reason that cannot distinguish its cases is not a reason. Stated as a
    property rather than as three separate string checks, so a future fourth
    case cannot quietly collapse into an existing one."""
    said = [g7_g8_not_exercised_because(g)
            for g in (OFFLINE, LIVE_NEVER_CALLED, LIVE_ALL_UNEVALUABLE)]
    assert len(set(said)) == 3


def test_both_consumers_use_the_one_producer():
    """`bundle._execution_provenance` and `campaign._disclaimer` must both
    route through this function. Asserted by driving them, not by grepping:
    a second copy of the prose would pass a grep for the import."""
    from crucible.conductor.bundle import _execution_provenance
    from crucible.conductor import campaign as C

    prov = _execution_provenance(live=True, meter=None,
                                 gate_summary=LIVE_ALL_UNEVALUABLE, rounds=[])
    assert prov["g7_g8_detail"] == g7_g8_not_exercised_because(
        LIVE_ALL_UNEVALUABLE)

    class _Locks:
        unfrozen = []

    text = C._disclaimer(
        True, _Locks(), {"in_common": 8, "target_only": [], "manifest_only": []},
        {"passed": 26, "total": 26}, LIVE_ALL_UNEVALUABLE)
    if not isinstance(text, str):
        text = " ".join(text)
    assert "no candidate ever reached the gate" not in text
    assert "UNEVALUABLE" in text
    assert g7_g8_not_exercised_because(LIVE_ALL_UNEVALUABLE) in text
