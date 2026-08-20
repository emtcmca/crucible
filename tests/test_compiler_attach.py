"""test_compiler_attach.py - the ADK plugin compiler and the attach assertion.

THE ASSERTION REPLACED A MUCH LARGER MECHANISM AND THAT IS THE POINT. ADK issue
#2809 - a nested Runner not inheriting the parent's plugins - is FIXED in 2.1.0:
`agent_tool.py:117-133, 238-250` propagates the parent's plugins when
`include_plugins` is True, and True is the default. The whole `OPAQUE` union
mechanism the architecture spec designed around that bug is obsolete, and the
correct replacement is one line. The architecture spec anticipated exactly this.

It is still an assertion rather than nothing, because `include_plugins` is a
constructor argument anybody can pass False, and False there means every tool
call made by that sub-agent BYPASSES THE ENFORCEMENT POINT ENTIRELY while the
run looks completely normal: a full episode, a clean ledger, and an ASR that
measures a boundary which was never applied. SILENCE IS THE FAILURE MODE, so the
check refuses rather than warns.

These tests use REAL `AgentTool` objects rather than fakes with an
`include_plugins` attribute, because the thing under test is a real flag on a
real class and a fake would keep passing after ADK renamed it.
"""

import copy

import pytest

from crucible.compiler import (
    AttachError,
    assert_agent_tools_propagate_plugins,
    compile_policy,
)
from crucible.dsl.errors import ValidationError
from crucible.plugin.adk import ADK_AVAILABLE

from . import l3_fixtures as fx
from .test_plugin_enforcement import _compute, _document


class Holder:
    """A minimal agent-shaped object: a name, tools, and sub-agents.

    `BaseAgent` has no `tools` attribute in 2.1.0 and `LlmAgent` wants a model,
    so the WALK is exercised against this while the FLAG being read is the real
    one on a real `AgentTool`.
    """

    def __init__(self, name, tools=(), sub_agents=()):
        self.name = name
        self.tools = list(tools)
        self.sub_agents = list(sub_agents)


def _agent_tool(include_plugins=True, name="inner"):
    from google.adk.agents.base_agent import BaseAgent
    from google.adk.tools.agent_tool import AgentTool
    return AgentTool(agent=BaseAgent(name=name, description="d"),
                     include_plugins=include_plugins)


pytestmark = pytest.mark.skipif(not ADK_AVAILABLE, reason="ADK not importable")


def test_the_default_is_true_and_passes():
    """If the default were False this assertion would fail everywhere and get
    disabled, so the default is worth asserting rather than assuming."""
    tool = _agent_tool()
    assert tool.include_plugins is True
    assert_agent_tools_propagate_plugins(Holder("root", tools=[tool]))


def test_include_plugins_false_is_refused():
    with pytest.raises(AttachError) as ei:
        assert_agent_tools_propagate_plugins(
            Holder("root", tools=[_agent_tool(False, "delegate")]))
    assert "delegate" in str(ei.value) and "include_plugins=False" in str(ei.value)


def test_a_sub_agent_two_levels_down_is_still_found():
    """A bypass hidden behind one level of delegation is the same bypass. The
    walk recurses through `sub_agents` and through each `AgentTool`'s own
    agent."""
    deep = Holder("deep", tools=[_agent_tool(False, "buried")])
    with pytest.raises(AttachError) as ei:
        assert_agent_tools_propagate_plugins(
            Holder("root", sub_agents=[Holder("mid", sub_agents=[deep])]))
    assert "buried" in str(ei.value)


def test_a_cycle_does_not_hang_the_walk():
    """Agent graphs are authored by hand and by models. A cycle here would turn
    an attach check into a hang, which reads as a stuck run rather than as a bad
    configuration."""
    a = Holder("a")
    b = Holder("b", sub_agents=[a])
    a.sub_agents.append(b)
    assert_agent_tools_propagate_plugins(a)


def test_a_truthy_non_boolean_does_not_pass():
    """`is not True`, not `not x`. A `1` or a `"yes"` would satisfy a falsy
    check while meaning something nobody intended - and this flag decides
    whether an entire sub-agent is enforced."""
    tool = _agent_tool()
    object.__setattr__(tool, "include_plugins", 1)
    with pytest.raises(AttachError):
        assert_agent_tools_propagate_plugins(Holder("root", tools=[tool]))


def test_ordinary_tools_without_the_attribute_are_ignored():
    """A plain function tool has no `include_plugins` and never needed one. A
    check that refused those would refuse every real agent."""
    assert_agent_tools_propagate_plugins(
        Holder("root", tools=[object(), _agent_tool()]))


# --------------------------------------------------------------------------
# The compiler refuses what the validator refuses.
# --------------------------------------------------------------------------

def test_compile_refuses_a_document_the_validator_refuses():
    """"A hand-written patch COMPILES" is an exit criterion, and a compiler that
    accepted a document the validator would refuse makes the first third of that
    sentence mean nothing."""
    doc = copy.deepcopy(fx.POLICY_DOC_VALID)
    doc["hashed_payload"]["rules"][0]["match"]["match_mode"] = "all_of"
    with pytest.raises(ValidationError) as ei:
        compile_policy(doc, manifest=fx.MANIFEST_A, derived_schema=fx.DERIVED_B,
                       compute=_compute)
    assert ei.value.code == "E_MATCH_MODE"


def test_compile_reports_a_stable_policy_hash():
    """Sixteen hex over the hashed payload, and `run_id` is deliberately outside
    it - inside, the same policy hashed differently in two runs, which breaks
    convergence-by-hash-equality and the resume key at the same time."""
    doc = _document(copy.deepcopy(fx.POLICY_DOC_VALID["hashed_payload"]))
    a = compile_policy(doc, manifest=fx.MANIFEST_A, derived_schema=fx.DERIVED_B,
                       compute=_compute)
    b = compile_policy(doc, manifest=fx.MANIFEST_A, derived_schema=fx.DERIVED_B,
                       compute=_compute)
    assert a.policy_hash == b.policy_hash and len(a.policy_hash) == 16
    assert a.rule_count == 2
