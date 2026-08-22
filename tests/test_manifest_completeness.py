"""
    # EIGHT as of 2026-08-20, not seven.
    # `delegate_to_specialist` was added BEFORE the D3 freeze because `CAP_INVOKES_AGENT` is one of the six canonical capability classes and NO TOOL CARRIED IT -- so one sixth of the taxonomy could never be exercised, and `measurement-spec.md` mandates that class for both F3 and F5 while the separability proof's P11 and P14 are written against it.
    # Three specified obligations rested on a class the target could not reach.N2 - a tool the agent exposes and the manifest omits is an ERROR, never a default.

Ruling 22 item 6 created this check and nothing required it before:

    New check - manifest completeness at the D3 freeze: every tool the target
    exposes is mapped to a class, or the run reports partial coverage with the
    unmapped tools named. Section 2.2 already required the reporting; nothing
    required the check.

The failure this exists to prevent is quiet. No rule can match a tool nobody
classified, so an unclassified tool is ALWAYS ALLOWED by the policy. That fail-open
is correct - detection is not remediation, and the TRIPWIRE still scores it - but it
must be STATED rather than DISCOVERED. A lookup that returns `[]` for a tool the
manifest never mentions turns "we forgot this tool" into "this tool does nothing",
and every downstream coverage number is then computed over a denominator that
silently shrank.

TWO DIFFERENT FAILURES LIVE HERE AND THEY MUST NOT COLLAPSE INTO ONE:

  UNMAPPED    the agent exposes it, Part A does not mention it.  -> hard error.
  UNCOVERED   Part A maps it, to `UNCLASSIFIED`.                 -> PARTIAL, named.

The first is a build defect: the manifest and the agent disagree about what the
agent is. The second is an honest declaration of ignorance about a tool that IS in
the manifest. Reporting the first as the second is how an omission gets laundered
into a disclosed gap. N3 covers the second.
"""

import json
import pathlib

import pytest

from target.refund_agent import tools
from target.refund_agent.capabilities import (
    Coverage,
    ManifestIncompleteError,
    capability_classes_for,
    coverage_report,
)
from target.refund_agent.manifest import (
    EXPOSED_TOOL_FQNAMES,
    build_manifest,
    manifest_path,
)

REPO = pathlib.Path(__file__).resolve().parent.parent


def _manifest():
    return build_manifest()


# --------------------------------------------------------------------------
# The agent and the manifest must describe the same agent.
# --------------------------------------------------------------------------

def test_the_agent_exposes_exactly_eight_tools():
    """`execution-spec.md` D3 item 1 names seven. A count is only as good as the
    ref it was taken on, so it is taken from the module, not from the doc."""
    assert len(tools.TOOL_FUNCTIONS) == 8
    assert len(EXPOSED_TOOL_FQNAMES) == 8


def test_every_exposed_tool_is_mapped_in_part_a():
    m = _manifest()
    mapped = {t["tool_fqname"] for t in m["tools"]}
    assert mapped == set(EXPOSED_TOOL_FQNAMES)


def test_every_exposed_tool_declares_its_argument_paths():
    """THE SECOND HALF OF COMPLETENESS, ADDED 2026-08-22 WITH V10.

    Part A's schema leaves `arg_paths` optional on purpose - a fail-closed tool's
    argument surface may genuinely be unknown, and forcing an author to INVENT
    one is worse than the gap (the same argument the schema already makes for
    `beneficiary_key`). On the RUNNING target no such excuse exists: every tool
    is a bare Python function whose signature ADK itself reads, so a missing
    declaration is an omission, not ignorance.

    It has to be checked HERE rather than left to C4's validator, and the reason
    is the direction of the failure. V10 treats the union of these declarations
    as the whole admissible vocabulary, so a tool that quietly stopped declaring
    would NARROW what a rule may name - and a rule refused for naming a real
    argument reads as an over-strict ARMORER, not as a manifest defect. Loud in
    the wrong place is still hard to diagnose.
    """
    for tool in _manifest()["tools"]:
        declared = tool.get("arg_paths")
        assert declared, "%s declares no arg_paths" % tool["tool_fqname"]
        assert declared == sorted(set(declared)), (
            "%s: arg_paths are a SET, sorted at construction "
            "(canonicalization restriction 6)" % tool["tool_fqname"])


def test_the_declared_arg_paths_are_the_signature_ADK_reads():
    """NOT A RESTATEMENT OF THE BUILDER - the point is that the declaration and
    the function cannot drift, so it is asserted against `inspect.signature`,
    which is the same object `FunctionTool._get_declaration()` builds the model's
    tool schema from. A renamed parameter moves both or neither.

    The two keys that name ONE argument each - `subject_key`, `beneficiary_key` -
    and the list that names several, `destination_args`, must all be drawn from
    it. Before this, `destination_args: ["recipient"]` on a tool whose parameter
    is `to` would have validated: exactly the r_new6 defect, one field over, in
    the artifact rather than in a rule.
    """
    import inspect

    by_name = {t["tool_fqname"].rsplit(".", 1)[-1]: t for t in _manifest()["tools"]}
    for fn in tools.TOOL_FUNCTIONS:
        entry = by_name[fn.__name__]
        assert entry["arg_paths"] == sorted(inspect.signature(fn).parameters)
        for key in ("subject_key", "beneficiary_key"):
            if key in entry:
                assert entry[key] in entry["arg_paths"], (
                    "%s: %s names %r, which is not one of its arguments"
                    % (fn.__name__, key, entry[key]))
        for dest in entry.get("destination_args", []):
            assert dest in entry["arg_paths"], (
                "%s: destination_args names %r, which is not one of its "
                "arguments. A destination rule aimed at it would never "
                "evaluate." % (fn.__name__, dest))


def test_the_committed_manifest_matches_what_the_code_builds():
    """The freeze hashes the file on disk. If the file and the builder disagree,
    the artifact that gets hashed is not the artifact the agent runs against."""
    on_disk = json.loads(manifest_path().read_text(encoding="utf-8"))
    assert on_disk == _manifest()


# --------------------------------------------------------------------------
# The negative half. An omission must raise, not default.
# --------------------------------------------------------------------------

def test_an_unmapped_tool_raises_rather_than_returning_an_empty_capability_set():
    """THE CHECK. `capability_classes_for` on a tool Part A never mentions must
    raise. Returning `()` would mean "this tool has no capabilities", which is a
    DIFFERENT AND FALSE FACT about a tool that may well move money."""
    m = _manifest()
    with pytest.raises(ManifestIncompleteError):
        capability_classes_for(m, "target.refund_agent.tools.tool_nobody_classified")


def test_the_raised_error_names_the_missing_tool():
    """An incompleteness error that does not name what is missing forces the next
    reader to re-derive the diff by hand, at the moment they are least able to."""
    m = _manifest()
    with pytest.raises(ManifestIncompleteError) as exc:
        capability_classes_for(m, "target.refund_agent.tools.tool_nobody_classified")
    assert "tool_nobody_classified" in str(exc.value)


def test_coverage_report_flags_an_agent_whose_tool_is_absent_from_the_manifest():
    m = _manifest()
    report = coverage_report(m, list(EXPOSED_TOOL_FQNAMES) + [
        "target.refund_agent.tools.tool_nobody_classified"])
    assert report.status is Coverage.INCOMPLETE
    assert report.unmapped == ("target.refund_agent.tools.tool_nobody_classified",)


def test_unmapped_is_not_reported_as_uncovered():
    """The collapse this file exists to prevent. An UNMAPPED tool must not be
    laundered into the UNCOVERED bucket, which reads as a disclosed gap rather
    than as a manifest that does not describe the agent."""
    m = _manifest()
    report = coverage_report(m, list(EXPOSED_TOOL_FQNAMES) + [
        "target.refund_agent.tools.tool_nobody_classified"])
    assert report.uncovered == ()
    assert report.status is not Coverage.PARTIAL


def test_the_real_agent_reports_full_coverage():
    m = _manifest()
    report = coverage_report(m, EXPOSED_TOOL_FQNAMES)
    assert report.status is Coverage.FULL
    assert report.unmapped == ()
    assert report.uncovered == ()


# --------------------------------------------------------------------------
# The strawman half. A check only ever run against the implementation it shipped
# beside cannot tell "correct" from "agrees with itself".
# --------------------------------------------------------------------------

def test_the_defaulting_strawman_is_caught():
    """`defaulting_capability_lookup` is the plausible wrong implementation: a
    `dict.get(fqname, ())`. It must NOT raise on an unmapped tool - and this test
    asserts that it does not, which is what proves the real one's raise is load
    bearing rather than incidental."""
    from tests import strawman_target

    m = _manifest()
    assert strawman_target.defaulting_capability_lookup(
        m, "target.refund_agent.tools.tool_nobody_classified") == ()
    with pytest.raises(ManifestIncompleteError):
        capability_classes_for(m, "target.refund_agent.tools.tool_nobody_classified")
