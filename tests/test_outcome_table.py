"""Outcome B is unreachable, and this file is what keeps it from coming back.

THE FINDING. An independent adversarial review ruled Outcome B a dead row:
"B is not rare; it is mathematically empty. The preregistration currently
advertises coverage it does not possess."

Outcome B's condition is *"run VALID, exclusion over ceiling but the reader
ACCEPTS the bundle."* Two independent arguments say no bundle can satisfy it,
and both are reproduced below as executable checks rather than as prose,
because a ruling that lives only in a document is a ruling nobody runs.

WHY A TEST AND NOT ONLY AN AMENDMENT. The amendment (A3.10) is the honest
record and it is what a reader is owed. But an outcome table is a branch table,
and the failure mode that put us here is a branch nobody could take being
carried for days as if it could. If someone later widens the run-level ceiling,
or makes the run test advisory, B becomes reachable again and the amendment
silently becomes wrong. These tests fail on that day.

Nothing here reads the sealed corpus. The arithmetic is over invented counts.
"""

import itertools
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from crucible.transfer.reader import (ACCEPTS, exclusion_ceiling_exceeded,  # noqa: E402
                                      verdict_record)

HOLDOUT_N = 24

PREREG = ROOT / "docs" / "proof" / "f4-unseal-preregistration-2026-08-25.md"


# ----------------------------------------------------- argument one: the sets
def test_an_arm_over_the_ceiling_forces_the_run_over_it_too():
    """THE FIRST ARGUMENT, and it is set containment plus monotonicity.

    The run-level unit is the INSTANCE, and an instance counts as excluded when
    it is excluded in EITHER arm, because the comparison is paired. So the
    run's excluded set is `E_v0 | E_vfinal`, which contains each arm's set:

        |E_v0 | E_vf| >= |E_v0|   and   |E_v0 | E_vf| >= |E_vf|

    Both tests use the same denominator, 24, and the same threshold function.
    That function is monotone in the excluded count, so a count that trips it
    for an arm also trips it for any count at least as large. Therefore
    whenever an arm exceeds, the union exceeds, the reader emits
    E_EXCLUSION_CEILING_RUN, and the run is Outcome C rather than B.

    Exhaustive over every arm pair a 24-instance holdout admits. The
    combinatorics are small enough that sampling would be the weaker choice.
    """
    for n_v0, n_vf in itertools.product(range(HOLDOUT_N + 1), repeat=2):
        arm_exceeded = (exclusion_ceiling_exceeded(n_v0, HOLDOUT_N)
                        or exclusion_ceiling_exceeded(n_vf, HOLDOUT_N))
        if not arm_exceeded:
            continue
        # The union is at least the larger arm, and is at most the whole
        # holdout. EVERY size the union could actually take must also exceed,
        # or B would have a foothold at that size.
        smallest_possible_union = max(n_v0, n_vf)
        for union in range(smallest_possible_union, HOLDOUT_N + 1):
            assert exclusion_ceiling_exceeded(union, HOLDOUT_N), (
                "arm exclusions (%d, %d) exceed the ceiling but a run-level "
                "union of %d does not. Outcome B would be reachable here."
                % (n_v0, n_vf, union))


def test_the_ceiling_test_is_monotone_which_is_what_the_argument_rests_on():
    """The property the argument above uses, asserted on its own.

    Stated separately because the first test would still pass if the threshold
    function were monotone by accident over the range that matters. A ceiling
    that is not monotone in the excluded count is a ceiling that can be escaped
    by excluding MORE, which would be a defect in its own right regardless of
    what it means for the outcome table.
    """
    tripped = False
    for k in range(HOLDOUT_N + 1):
        now = exclusion_ceiling_exceeded(k, HOLDOUT_N)
        if tripped:
            assert now, ("the ceiling un-trips at %d of %d: excluding more "
                         "instances made the run acceptable again" % (k, HOLDOUT_N))
        tripped = tripped or now
    assert tripped, "no exclusion count of 24 trips the ceiling at all"


# ------------------------------------------- argument two: the accept verdict
def test_accepts_requires_zero_defects_so_a_ceiling_defect_forbids_it():
    """THE SECOND ARGUMENT, and it is independent of the first.

    Outcome B needs the reader to ACCEPT a bundle whose exclusions are over the
    ceiling. But ACCEPTS is defined as the absence of defects, and a ceiling
    violation IS a defect. B therefore fails on the accept clause even before
    the union argument is reached - which matters, because two independent
    reasons mean closing one of them does not revive the row.
    """
    class _Report(object):
        def __init__(self, defects):
            self.defects = defects

    class _Defect(object):
        def __init__(self, code):
            self.code = code

    clean = verdict_record(_Report([]))
    assert clean["verdict"] == ACCEPTS

    with_ceiling = verdict_record(_Report([_Defect("E_EXCLUSION_CEILING")]))
    assert with_ceiling["verdict"] != ACCEPTS
    assert with_ceiling["defect_count"] == 1

    with_run_ceiling = verdict_record(_Report([_Defect("E_EXCLUSION_CEILING_RUN")]))
    assert with_run_ceiling["verdict"] != ACCEPTS


# ------------------------------------------------- the document must say so
def test_the_preregistration_records_b_as_unreachable_before_the_unseal():
    """The claims artifact has to carry the ruling, and carry it as an
    AMENDMENT rather than as an edit.

    This checks a claims document, which is a different thing from grepping
    source text to stand in for behaviour: the two tests above are what prove
    the property, and this one proves the published record agrees with them.
    A correct implementation beside a document that still advertises Outcome B
    is exactly the drift this repository keeps paying for.

    The pre-registration's own rule is that amendments are APPENDED and never
    rewritten, so the original table must still be present with B in it.
    """
    text = PREREG.read_text(encoding="utf-8")
    assert "A3.10" in text, "the Outcome B ruling is not in the pre-registration"
    assert "UNREACHABLE" in text, "A3.10 does not say what it ruled"
    # The original row survives. Deleting it would rewrite history rather than
    # amend it, and section 4 forbids exactly that.
    assert "| **B. Valid but partial**" in text, (
        "Outcome B's original row was deleted rather than amended. The "
        "pre-registration is append-only.")
