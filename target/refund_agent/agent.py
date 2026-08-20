"""The target agent. Assembled here; frozen at D3.

WHAT THIS IS. A customer-service refund agent with seven bare-function tools, four
of which touch money, external communications, durable state, or PII. Its
instruction is `refund_policy.md`, loaded verbatim. It is a competent agent that
follows its written policy - and the written policy is English, which is what the
harness attacks.

MODEL: `gemini-3.5-flash-lite` at `thinking_level: minimal`, pinned exactly, no
alias and no "latest".

WHY THAT TIER IS A DESIGN DECISION AND NOT ONLY A COST ONE, which is the
second-level question an engineer asks first: a weaker target is easier to attack,
which inflates the v0 baseline and flatters the entire improvement curve. The
honest handling is to pin it, hash it into the D3 target freeze, and NAME THE TIER
EVERY TIME THE NUMBERS ARE REPORTED. `3.5-flash-lite` is both the cheapest option
and the defensible one, provided it is disclosed. The target is also the dominant
cost line in the whole run - roughly 300+ episodes - which is why the expensive
model sits on the ARMORER, at about 24 calls, instead.

WHY `thinking_level` IS SET EXPLICITLY. Defaults are not free: thinking tokens bill
at the ordinary output rate with no discount. Every call in this build sets it.

WHY THE `global` ENDPOINT. Non-global carries a flat 10% premium.

IMPORTING ADK IS DEFERRED TO `build_agent()`. The tools, the manifest, the episode
freeze, and the demo transcripts are all testable without a model, a project, or
credentials, and a module-level ADK import would make the whole test suite depend
on all three. `python -m pytest tests/` must stay runnable on a machine with no
egress - a judge reproducing this build should not need a Google Cloud project to
run the checks.
"""

import pathlib

# Pinned exactly. `gemini-2.5-*` and `gemini-3.1-*` are dead vocabulary here: the
# 2.5 line retires and none of it qualifies, and 3.1-pro is BELOW the contest's
# 3.5 floor despite the higher-looking number. The Flash line is at 3.7 and the
# newest Pro is 3.1 - the two lines are genuinely non-parallel, which is not a typo.
TARGET_MODEL = "gemini-3.5-flash-lite"
TARGET_THINKING_LEVEL = "minimal"
TARGET_AGENT_NAME = "refund_agent"

POLICY_PATH = pathlib.Path(__file__).resolve().parent / "refund_policy.md"

# The policy file carries a preamble explaining its provenance to a human reader.
# The agent gets the fenced block and nothing else - the preamble is about the
# file, not about the job, and an instruction that describes its own sourcing
# invites the model to reason about whether it applies.
_FENCE = "```"


def policy_text() -> str:
    """The system prompt: the fenced block inside `refund_policy.md`, verbatim."""
    raw = POLICY_PATH.read_text(encoding="utf-8")
    try:
        start = raw.index(_FENCE) + len(_FENCE)
        end = raw.rindex(_FENCE)
    except ValueError:
        raise RuntimeError(
            "refund_policy.md has lost its fenced policy block. The agent's "
            "instruction is that block; without it the agent would silently run "
            "with a preamble as its policy.")
    body = raw[start:end].lstrip("\n")
    if "AGENT OPERATING POLICY" not in body:
        raise RuntimeError("the fenced block is not the policy body")
    return body


def build_agent():
    """Construct the ADK agent. Imports ADK; needs no credentials to construct."""
    from google.adk.agents import LlmAgent
    from google.genai import types

    from . import tools

    return LlmAgent(
        name=TARGET_AGENT_NAME,
        model=TARGET_MODEL,
        instruction=policy_text(),
        # BARE FUNCTIONS. See `tools.py` for why, and for why the old reason
        # (plugins not firing inside AgentTool) is no longer true at ADK 2.1.0.
        tools=list(tools.TOOL_FUNCTIONS),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,
            thinking_config=types.ThinkingConfig(
                thinking_level=TARGET_THINKING_LEVEL),
        ),
    )


def target_descriptor() -> dict:
    """What the D3 freeze records about the model side of the target.

    Separate from the manifest on purpose: the manifest describes the TOOLS, this
    describes the MODEL BINDING. Both are hashed at D3, and the tier has to be
    recoverable from the frozen record or the disclosure obligation above rests on
    somebody's memory.
    """
    return {
        "target_id": "tgt_crucible_refund_v1",
        "agent_name": TARGET_AGENT_NAME,
        "model": TARGET_MODEL,
        "thinking_level": TARGET_THINKING_LEVEL,
        "endpoint": "global",
        "temperature_x100": 20,   # INT: no floats in a hashed payload
        "tool_binding": "bare_functions",
        "adk_version": "2.1.0",
    }
