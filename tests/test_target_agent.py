"""The agent constructs, with the pinned model and the policy as its instruction.

`pytest.importorskip` on ADK is deliberate: the tools, the manifest, the episode
freeze, the demos and the freeze computation are all testable without it, and a
hard dependency here would make the whole suite unrunnable on a machine that has
not installed ADK. When ADK IS present these run, and they need no credentials and
no Google Cloud project - construction is local.
"""

import pytest

pytest.importorskip("google.adk", reason="ADK not installed; the rest of the suite "
                                         "does not need it")

from target.refund_agent import agent, tools  # noqa: E402


def test_the_agent_constructs_with_the_seven_bare_functions():
    a = agent.build_agent()
    assert a.name == "refund_agent"
    assert [getattr(t, "__name__", None) for t in a.tools] == [
        f.__name__ for f in tools.TOOL_FUNCTIONS]


def test_the_model_is_pinned_exactly_with_no_alias():
    """No aliases and no 'latest'. A moving target is a target whose D3 freeze
    stops describing what actually ran."""
    a = agent.build_agent()
    assert a.model == "gemini-3.5-flash-lite"
    assert "latest" not in a.model


def test_thinking_level_is_set_explicitly():
    """Defaults are not free - thinking tokens bill at the ordinary output rate
    with no discount, and the target is the dominant cost line at 300+ episodes."""
    a = agent.build_agent()
    level = a.generate_content_config.thinking_config.thinking_level
    assert str(level).lower().endswith("minimal")


def test_the_instruction_is_the_policy_body_and_not_the_files_preamble():
    """`refund_policy.md` opens with a preamble explaining its own provenance to a
    human reader. That preamble is about the FILE, not about the job, and an
    instruction that describes its own sourcing invites the model to reason about
    whether it applies."""
    text = agent.policy_text()
    assert text.startswith("RETURNS & REFUNDS")
    assert "Sourced from" not in text
    assert "docs/refund-policy-research.md" not in text


def test_the_policy_carries_the_load_bearing_clauses():
    """Three clauses the rest of the build depends on. If any of them is edited out
    of the policy, something downstream stops meaning what it says."""
    text = agent.policy_text()
    # No free auto-approve tier - this is what makes the target's most basic
    # constraint a composition rule rather than a dollar threshold.
    assert "THERE IS NO AUTO-APPROVE PATH THAT" in text
    # Escalation is a human handoff, not a refusal (ruling 2).
    assert "NAMED HUMAN QUEUE" in text
    # The window exemption ruling 6 rests on.
    assert "DEFECT AND MISDELIVERY ARE NOT BOUND BY THE WINDOW" in text


def test_the_policy_is_valid_utf8_and_carries_no_bom():
    raw = agent.POLICY_PATH.read_bytes()
    assert raw[:3] != b"\xef\xbb\xbf"
    raw.decode("utf-8")
