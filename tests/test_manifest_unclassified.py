"""N3 - `UNCLASSIFIED` is DISTINCT from the empty set.

`CONVENTIONS.md` section 2.2, and `MANIFEST.json`'s term binding for the same word:

    Plus the sentinel `UNCLASSIFIED`, which is distinct from the empty set. The
    empty set means INERT (a pure read of non-personal data). `UNCLASSIFIED` means
    WE DO NOT KNOW, and an agent with any `UNCLASSIFIED` tool is reported as
    partially covered, with the uncovered tools named.

"We know it has no capabilities" and "we do not know what this does" are different
facts. Sharing an encoding costs the run its coverage claim: an agent full of
unknown tools reports as an agent full of harmless ones, and on D9 - an unseen
target, where every tool is unclassified until the manifest maps it - that is the
difference between "no capability boundary was needed" and "no capability boundary
was computed".

THE FIRST VERSION OF THIS FILE COULD NOT FAIL, and that is recorded in
`docs/lanes/L2-log.md` rather than quietly fixed. It asserted that
`coverage_report` names an `UNCLASSIFIED` tool - which passes just as well against
an implementation that collapses `UNCLASSIFIED` into the empty set, because such an
implementation still has the tool's name in hand. The strawman below is the repair:
`collapsing_coverage` in `tests/strawman_target.py` makes exactly that mistake, and
this suite asserts it FAILS the distinction. Same shape as
`tests/strawman_canon.py`, for the same reason.
"""

import pytest

from target.refund_agent.capabilities import (
    CAPABILITY_CLASSES,
    INERT,
    UNCLASSIFIED,
    Coverage,
    coverage_report,
    is_inert,
    is_unclassified,
)
from target.refund_agent.manifest import EXPOSED_TOOL_FQNAMES, build_manifest

from tests import strawman_target


def _manifest_with(tool_fqname, classes):
    m = build_manifest()
    m["tools"] = list(m["tools"]) + [{
        "tool_handle": "tool:t_00000abc",
        "tool_fqname": tool_fqname,
        "capability_classes": list(classes),
        "classified_by": "fail_closed_default",
    }]
    return m


UNKNOWN = "target.refund_agent.tools.unknown_helper"
INERT_TOOL = "target.refund_agent.tools.read_store_hours"


# --------------------------------------------------------------------------
# The vocabulary itself.
# --------------------------------------------------------------------------

def test_the_six_capability_classes_are_the_canonical_strings():
    assert CAPABILITY_CLASSES == (
        "CAP_MOVES_MONEY",
        "CAP_EXTERNAL_COMMS",
        "CAP_MUTATES_DURABLE_STATE",
        "CAP_READS_PII",
        "CAP_ESCALATES_PRIVILEGE",
        "CAP_INVOKES_AGENT",
    )


def test_unclassified_is_not_one_of_the_six():
    """It is a sentinel, not a seventh class. A rule may select any of the six and
    may never select this one (C4 V2)."""
    assert UNCLASSIFIED not in CAPABILITY_CLASSES


def test_the_two_predicates_do_not_answer_the_same_question():
    assert is_unclassified((UNCLASSIFIED,)) is True
    assert is_inert((UNCLASSIFIED,)) is False
    assert is_inert(INERT) is True
    assert is_unclassified(INERT) is False


def test_the_sentinel_never_travels_alongside_a_real_class():
    """"We do not know what this does" and "it moves money" cannot both be true of
    one tool. A mixed set means someone appended the sentinel to a partial
    classification, which reads as covered and is not."""
    with pytest.raises(ValueError):
        is_unclassified(("CAP_MOVES_MONEY", UNCLASSIFIED))


# --------------------------------------------------------------------------
# The reporting consequence, which is where the two facts actually diverge.
# --------------------------------------------------------------------------

def test_an_unclassified_tool_makes_the_agent_partially_covered_and_names_it():
    m = _manifest_with(UNKNOWN, [UNCLASSIFIED])
    report = coverage_report(m, list(EXPOSED_TOOL_FQNAMES) + [UNKNOWN])
    assert report.status is Coverage.PARTIAL
    assert report.uncovered == (UNKNOWN,)


def test_an_inert_tool_does_NOT_make_the_agent_partially_covered():
    """The half that separates the two facts. An inert tool is fully classified -
    we know what it does and it is nothing. Reporting it as a coverage gap would
    mean the report cannot distinguish a known-harmless tool from an unknown one,
    which is the whole distinction."""
    m = _manifest_with(INERT_TOOL, list(INERT))
    report = coverage_report(m, list(EXPOSED_TOOL_FQNAMES) + [INERT_TOOL])
    assert report.status is Coverage.FULL
    assert report.uncovered == ()


def test_the_collapsing_strawman_cannot_tell_them_apart():
    """THE CHECK THAT PROVES THIS SUITE CAN FAIL.

    `collapsing_coverage` treats `UNCLASSIFIED` as "no capabilities" - the exact
    bug. It returns the SAME verdict for the unknown tool and the inert one. The
    real reporter must return different verdicts for those two inputs. If this
    assertion ever passes for the real implementation, the distinction is gone and
    the suite has stopped measuring."""
    unknown_m = _manifest_with(UNKNOWN, [UNCLASSIFIED])
    inert_m = _manifest_with(INERT_TOOL, list(INERT))

    straw_unknown = strawman_target.collapsing_coverage(
        unknown_m, list(EXPOSED_TOOL_FQNAMES) + [UNKNOWN])
    straw_inert = strawman_target.collapsing_coverage(
        inert_m, list(EXPOSED_TOOL_FQNAMES) + [INERT_TOOL])
    assert straw_unknown == straw_inert, (
        "the strawman is supposed to conflate these; if it no longer does, it has "
        "been fixed and has stopped being a strawman")

    real_unknown = coverage_report(unknown_m, list(EXPOSED_TOOL_FQNAMES) + [UNKNOWN]).status
    real_inert = coverage_report(inert_m, list(EXPOSED_TOOL_FQNAMES) + [INERT_TOOL]).status
    assert real_unknown is not real_inert


# --------------------------------------------------------------------------
# Fail-closed. An unknown tool must be MORE restricted, never less.
# --------------------------------------------------------------------------

def test_a_fail_closed_tool_carries_all_six_classes_not_the_sentinel():
    """C3a's own rule: `fail_closed: true` requires six classes. Fail-closed and
    `UNCLASSIFIED` are two different responses to the same ignorance - one
    maximally restricts, one declares the gap. Part A must not let a tool claim to
    do both, because `UNCLASSIFIED` is unselectable by any rule and would make a
    "fail-closed" tool the least restricted thing in the manifest."""
    from target.refund_agent.capabilities import fail_closed_classes

    assert set(fail_closed_classes()) == set(CAPABILITY_CLASSES)
    assert UNCLASSIFIED not in fail_closed_classes()
