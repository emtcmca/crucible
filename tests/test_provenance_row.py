"""The PROVENANCE row must count what it claims.

Found by the C6 producer lane, 2026-08-22, in a file it was not allowed to edit.
`_check_execution_provenance` returned "%d component(s) all real" whenever there
were no DEFECTS - but a stand-in is not a defect. It is a disclosed fact, and
disclosing it is the entire point of `execution_provenance`. So an offline bundle
carrying four stand-ins rendered:

    mode=offline_stand_in, 7 component(s) all real, g7_g8_exercised=false

in the render whose only job is telling a reader which parts of a run were real.
The `mode` field one column to the left said `offline_stand_in` at the same time,
so the row contradicted itself inside a single line.

This is the same defect class as `view.py`'s hardcoded 5% and the four documents
that restated a bound: a sentence that asserts a fact it never computed. The fix
is not better wording, it is making the row derive its claim from the components
it is describing.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from crucible.replay.integrity import _check_execution_provenance

SEVEN = ("target", "red_strategist", "tripwire", "coroner", "armorer",
         "warden", "gate")


def _bundle(stand_ins=(), mode="live"):
    return {"execution_provenance": {
        "mode": mode,
        "components": {
            name: {"implementation":
                   "stand_in" if name in stand_ins else "real"}
            for name in SEVEN},
        "g7_g8_exercised": False,
        "g7_g8_detail": "not exercised",
        "model_calls": 1,
    }}


def test_a_run_with_stand_ins_is_never_described_as_all_real():
    """THE RED CASE. Four stand-ins, no defects, and the row used to say
    "7 component(s) all real"."""
    row = _check_execution_provenance(
        _bundle(stand_ins=("target", "tripwire", "warden", "gate"),
                mode="offline_stand_in"),
        [])
    assert "all real" not in row.note, (
        "the PROVENANCE row describes a bundle carrying stand-ins as all real. "
        "That is the one sentence this row exists to get right: %r" % row.note)
    assert "3 real, 4 STAND-IN" in row.note
    assert row.status == "OK", (
        "a stand-in is a disclosed fact, not a defect - the row must report it "
        "without failing, or an honest offline bundle becomes unrenderable.")


def test_a_genuinely_real_run_still_says_so():
    """THE OTHER DIRECTION. A fix that made the row never say "all real" would
    have passed the test above and destroyed the claim worth making."""
    row = _check_execution_provenance(_bundle(), [])
    assert "7 component(s) all real" in row.note
    assert "STAND-IN" not in row.note


def test_one_stand_in_is_enough_to_lose_the_word():
    """No threshold. The word "all" is a universal claim and one exception
    falsifies it."""
    # `mode` must be offline here: mode=live WITH a stand-in is a real defect
    # (E_MODE_DISAGREES_WITH_COMPONENTS), and a defective row prints its defect
    # count rather than its shape. That is correct, and it caught this test.
    row = _check_execution_provenance(
        _bundle(stand_ins=("gate",), mode="offline_stand_in"), [])
    assert "all real" not in row.note
    assert "6 real, 1 STAND-IN" in row.note
