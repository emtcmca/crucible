"""test_l3_negative_checks.py - L3's FIRST work item, and it is the negative half.

Two files drive `tests/l3_checks.py`:

    this one              the ten checks against `crucible`. All must PASS.
    test_l3_strawmen.py   the same ten against deliberately-wrong code, where a
                          NAMED set must FAIL.

Both halves are required and the second one is the one that matters. A suite
that only ever runs against the implementation it was written alongside cannot
tell "correct" from "agrees with itself", and the way you find that out is that
it was green the whole time.

WRITTEN AND RUN RED BEFORE THE IMPLEMENTATION EXISTED. `CONVENTIONS.md` section
8 rule 2, and `docs/lanes/L3-enforcement.md` section 4 states the reason in the
specific: on 2026-08-20 the contract gate's own first negative test COULD NOT
FAIL - it appended a trailing newline, which is exactly the mutation the
normalization exists to absorb. It was caught only because somebody actually ran
it. A test written after the code, that has never been red, is not evidence
about the code; it is evidence that the test agrees with whatever was there when
it was written.
"""

import pytest

from . import l3_checks

CHECK_IDS = sorted(l3_checks.CHECKS)


@pytest.fixture(scope="module")
def impl():
    return l3_checks.real_impl()


@pytest.mark.parametrize("check_id", CHECK_IDS)
def test_negative_check(check_id, impl):
    l3_checks.CHECKS[check_id](impl)


def test_the_eight_mandated_checks_are_all_present():
    """`L3-enforcement.md` section 4 mandates eight by name - four semantics and
    four from C4's negative-check list. N5 and N6 are the two more that section
    7 and `policy.ebnf` require. A census, so a check cannot quietly disappear
    when a file is refactored: deleting one would otherwise just make the suite
    smaller and greener.
    """
    mandated = {"S1", "S2", "S3", "S4", "N1", "N2", "N3", "N4"}
    assert mandated <= set(l3_checks.CHECKS), (
        "missing mandated checks: %s" % sorted(mandated - set(l3_checks.CHECKS)))
    assert {"N5", "N6"} <= set(l3_checks.CHECKS)
    assert len(l3_checks.CHECKS) == 10


def test_every_check_has_a_docstring_naming_what_it_defends():
    """A negative check whose failure message does not say what broke gets
    deleted by the next person under deadline, because it reads as noise."""
    for cid, fn in l3_checks.CHECKS.items():
        assert fn.__doc__ and len(fn.__doc__.strip()) > 120, (
            "%s has no substantive docstring" % cid)
