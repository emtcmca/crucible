"""test_handle_resolution.py - the fail-open that made the policy enforce nothing.

FOUND 2026-08-21, the first time the target was driven through a real ADK
`Runner` rather than a hand-called callback.

ADK names a bare-function tool by `fn.__name__` - `issue_refund`. The capability
manifest keys on `tool_fqname` - `target.refund_agent.tools.issue_refund`.
`EnforcementCore.handle_for` looked up only the dotted form, so every real tool
call missed, fell through to the synthetic handle, and `capabilities_for`
returned `UNCLASSIFIED`.

**UNCLASSIFIED IS ALWAYS ALLOWED, BY DELIBERATE DESIGN** (`core.py`:
"The engine FAILS OPEN there, deliberately, and that is correct"). So the policy
would have enforced NOTHING against the real agent - silently, with no exception,
no warning, and a clean-looking run.

WHY THE DESIGNED SAFETY NET DID NOT COVER IT. `capabilities_for` says an
unmapped tool is "the D3 completeness check's job, not this method's." That check
asks whether the MANIFEST is complete. The manifest was complete. The defect was
in the lookup KEY, so the completeness check passed while every runtime
resolution missed - a gap between two correct components rather than a fault in
either.

WHY THE FIRST FIX WAS REVERTED, AND THE FALSE REASON THIS FILE GAVE FOR IT.
The lane that found the bug renamed each `FunctionTool` to the dotted path so the
lookup would hit. It was reverted, and this docstring claimed a real endpoint
would refuse a dotted name because a function-declaration name must match
`^[a-zA-Z0-9_-]{1,64}$`.

THAT CLAIM WAS FALSE AND IT WAS NEVER CHECKED. `^[a-zA-Z0-9_-]{1,64}$` is
OPENAI's constraint. Gemini's own rejection text enumerates dots as legal, and a
live probe on 2026-08-22 against `gemini-3.5-flash-lite` on Vertex ACCEPTED
`target.refund_agent.tools.issue_refund` - see
`docs/proof/gemini-function-name-probe-2026-08-22.txt`. The rename would have
worked. `crucible/conductor/real_target.py:118-126` had hedged correctly all
along ("was NOT checked here") and `tests/test_adk_invocation_paths.py` already
drove a real `Runner` against a dotted name without complaint. The flat claim
outvoted both.

THE CORRECT REASON TO RESOLVE BARE NAMES IS THAT ADK SUPPLIES BARE NAMES. That
reason is sufficient, it is checked, and it never needed a second one. A true fix
propped up by a false justification is still a false claim, and this one was
strong enough to revert working code and reach a public draft.

WHAT THIS FILE STILL PROVES, unchanged: the fail-open itself. ADK names a tool
`fn.__name__`, the manifest keyed the dotted `tool_fqname`, `handle_for` matched
only the dotted one, an unresolved handle is UNCLASSIFIED, and UNCLASSIFIED IS
ALWAYS ALLOWED - so the policy enforced nothing, silently, while every test in
the repo passed.
"""

import json
import pathlib
import re

import pytest

from crucible.plugin.core import UNCLASSIFIED, EnforcementCore

MANIFEST_PATH = (pathlib.Path(__file__).resolve().parent.parent
                 / "target" / "refund_agent" / "capability_manifest.json")

# The name ADK actually supplies for a tool: the bare Python function name.
# NOT a vendor constraint - see the module docstring. This pattern was labelled
# "the constraint a tool name must satisfy to be declarable to the model API",
# which was OpenAI's rule applied to a Gemini target and was never sourced.
ADK_SUPPLIED_LEAF = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _core(manifest):
    return EnforcementCore(manifest=manifest, engine=None, stamper=None,
                           ledger=None)


def _manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_the_bare_function_name_resolves_to_the_same_handle_as_the_dotted_one():
    """The fix. ADK hands over `issue_refund`; the manifest holds the dotted
    path; both must reach the same tool."""
    core = _core(_manifest())
    dotted = core.handle_for("target.refund_agent.tools.issue_refund")
    bare = core.handle_for("issue_refund")
    assert dotted is not None, "manifest lookup by fqname must still work"
    assert bare == dotted, (
        "the bare name ADK actually supplies did not resolve to the same handle "
        "as the dotted name the manifest stores")


def test_a_bare_name_lookup_does_not_return_UNCLASSIFIED():
    """The property that actually matters, stated as the consequence rather than
    the mechanism: an unresolved tool is ALWAYS ALLOWED, so a missed lookup is
    not a logging gap, it is the policy switched off."""
    core = _core(_manifest())
    handle = core.handle_for("issue_refund")
    classes = core.capabilities_for(handle)
    assert UNCLASSIFIED not in classes, (
        "issue_refund resolved to UNCLASSIFIED, which is always allowed - the "
        "policy would enforce nothing against this tool")
    assert "CAP_MOVES_MONEY" in classes


def test_every_manifest_tool_resolves_by_its_bare_name():
    """Not just the one that was noticed. All eight, or the next tool added
    inherits the bug."""
    manifest = _manifest()
    core = _core(manifest)
    unresolved = []
    for tool in manifest["tools"]:
        leaf = tool["tool_fqname"].rsplit(".", 1)[-1]
        if core.handle_for(leaf) != tool["tool_handle"]:
            unresolved.append(leaf)
    assert not unresolved, (
        "%s do not resolve by the name ADK will supply" % unresolved)


def test_every_manifest_leaf_is_the_bare_name_adk_will_supply():
    """Every tool's leaf name is the bare identifier ADK hands the plugin.

    CORRECTED 2026-08-22. This test was `..._is_actually_declarable_to_a_model`
    and additionally asserted `not DECLARABLE.match(tool_fqname)` - a TRUE regex
    fact wrapped in a FALSE inference, namely that a dotted name is therefore not
    declarable. A live probe refuted it (module docstring;
    `docs/proof/gemini-function-name-probe-2026-08-22.txt`).

    The deleted assertion is not replaced by a corrected one. There is nothing
    here to assert about the vendor: what this repo needs is that the manifest's
    leaf matches what ADK supplies, and the vendor's own limits are the vendor's
    to enforce. A test that restates a third party's rule is a second source of
    truth for a fact it cannot check, which is exactly how this one went wrong.
    """
    for tool in _manifest()["tools"]:
        leaf = tool["tool_fqname"].rsplit(".", 1)[-1]
        assert ADK_SUPPLIED_LEAF.match(leaf), (
            "%r is not the shape ADK supplies as fn.__name__" % leaf)


def test_an_unknown_tool_still_returns_None_so_the_gap_is_reportable():
    """Negative control, and the reason it matters: if `handle_for` started
    resolving everything the D3 completeness check would have nothing to report
    and an unmapped tool would look mapped."""
    core = _core(_manifest())
    assert core.handle_for("no_such_tool") is None
    assert core.handle_for("") is None


def test_an_ambiguous_bare_name_is_REFUSED_rather_than_guessed():
    """Two tools in different modules sharing a bare name.

    The leaf index must drop it rather than pick one, because a policy silently
    applied to the WRONG tool is worse than no resolution at all - no resolution
    fails open visibly at the completeness check, while a wrong resolution looks
    enforced and is not.
    """
    manifest = _manifest()
    clash = dict(manifest["tools"][0])
    clash["tool_fqname"] = "some.other.module.issue_refund"
    clash["tool_handle"] = "tool:t_deadbeef"
    manifest = dict(manifest, tools=list(manifest["tools"]) + [clash])

    core = _core(manifest)
    assert core.handle_for("issue_refund") is None, (
        "an ambiguous bare name resolved to one of the candidates instead of "
        "being refused")
    assert "issue_refund" in core._ambiguous_leaves
    # Both dotted names must still resolve - ambiguity costs the shortcut, not
    # the real lookup.
    assert core.handle_for("target.refund_agent.tools.issue_refund") is not None
    assert core.handle_for("some.other.module.issue_refund") == "tool:t_deadbeef"


def test_negative_control_the_pre_fix_behaviour_would_fail_these():
    """Proof this suite can fail: a core whose manifest carries no tools
    resolves nothing, which is what the pre-fix lookup effectively did for every
    bare name."""
    core = _core({"tools": []})
    assert core.handle_for("issue_refund") is None
    assert UNCLASSIFIED in core.capabilities_for(core.handle_for("issue_refund"))
