"""The target agent. Assembled here; frozen at D3.

WHAT THIS IS. A customer-service refund agent with eight bare-function tools, four
(corrected 2026-08-22: this said SEVEN. delegate_to_specialist was added pre-D3
to make CAP_INVOKES_AGENT instantiable and this line never moved. Fixed in the
same re-freeze that pins the provider, because a hash-locked file is only cheap
to correct while its hash is already moving.)
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

PROVIDER AND ENDPOINT ARE PINNED IN CODE, NOT READ FROM THE SHELL. Vertex AI, on
`global`, both named in `target_descriptor()` and both consumed by
`_pinned_model()`. Until 2026-08-22 `crucible/armorer/client.py:79` pinned
`vertexai=True` and this file passed a BARE MODEL STRING, so the target's provider
was whatever `GOOGLE_GENAI_USE_VERTEXAI` happened to say - and the D3 freeze could
not see the difference. `assert_provider_matches_descriptor()` covers the part of
ADK a client pin cannot reach.

IMPORTING ADK IS DEFERRED TO `build_agent()`. The tools, the manifest, the episode
freeze, and the demo transcripts are all testable without a model, a project, or
credentials, and a module-level ADK import would make the whole test suite depend
on all three. `python -m pytest tests/` must stay runnable on a machine with no
egress - a judge reproducing this build should not need a Google Cloud project to
run the checks.
"""

import os
import pathlib

# Pinned exactly. `gemini-2.5-*` and `gemini-3.1-*` are dead vocabulary here: the
# 2.5 line retires and none of it qualifies, and 3.1-pro is BELOW the contest's
# 3.5 floor despite the higher-looking number. The Flash line is at 3.7 and the
# newest Pro is 3.1 - the two lines are genuinely non-parallel, which is not a typo.
TARGET_MODEL = "gemini-3.5-flash-lite"
TARGET_THINKING_LEVEL = "minimal"
TARGET_AGENT_NAME = "refund_agent"

# WHICH API THE TARGET TALKS TO. Vertex AI, on the `global` endpoint. Both are in
# `target_descriptor()` and therefore inside `target_agent_hash`.
#
# `TARGET_ENDPOINT` was a bare string literal inside `target_descriptor()` until
# 2026-08-22 and nothing in the code read it - the endpoint was decided by
# `GOOGLE_CLOUD_LOCATION`, and the ADK Cloud Run image baked a REGION into that
# variable, so the deployed agent resolved its model somewhere other than the
# frozen record said (`deploy/RUNBOOK.md`, the 404 on 08-21). `TARGET_PROVIDER`
# did not exist at all, and the provider was decided by `GOOGLE_GENAI_USE_VERTEXAI`
# - unset on 08-22, which sent 72 calls at the Gemini Developer API and produced 72
# `ValueError: No API key was provided`.
#
# BOTH ARE NOW READ BY THE CODE THAT BUILDS THE CLIENT (`_pinned_model`). The
# freeze describes what decides the call rather than a claim sitting beside it.
TARGET_PROVIDER = "vertex"
TARGET_ENDPOINT = "global"

# The variable that used to decide, and still decides the half of ADK a client pin
# cannot reach. See `assert_provider_matches_descriptor`.
PROVIDER_ENV_VAR = "GOOGLE_GENAI_USE_VERTEXAI"

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


class ProviderMismatch(RuntimeError):
    """The environment contradicts the frozen target descriptor.

    RAISED, NEVER REPAIRED. Setting the variable from in here would make a
    misconfigured run look correct, which is the failure this class exists to
    stop - the same reason `--holdout-expected` refuses to invent a phase number
    rather than defaulting one.
    """


def env_provider(env=None):
    """Which provider ADK's ENV-READING code paths will use: `vertex` or
    `developer_api`.

    THE PREDICATE IS COPIED FROM `google.adk.utils.env_utils.is_env_enabled`
    EXACTLY, INCLUDING THE ABSENCE OF `.strip()`. ADK reads
    `os.environ.get(name, '0').lower() in ['true', '1']`, and `google.genai`'s
    own client reads the identical expression (`_api_client.py:602-610`). So
    `GOOGLE_GENAI_USE_VERTEXAI=" 1"` is DISABLED for both of them. A predicate
    here that stripped whitespace would answer "vertex", ADK would build the
    developer-API surface, and the check would have manufactured the exact
    disagreement it was written to detect. A predicate is only useful if it is
    the same predicate.
    """
    raw = (os.environ if env is None else env).get(PROVIDER_ENV_VAR, "0")
    return "vertex" if str(raw).lower() in ("true", "1") else "developer_api"


def assert_provider_matches_descriptor(env=None):
    """Refuse to run when the environment disagrees with the frozen descriptor.

    WHY THIS EXISTS WHEN `_pinned_model()` ALREADY PINS THE CLIENT, which is the
    obvious objection and the whole reason both halves are here.

    `_pinned_model()` reaches the CLIENT. It cannot reach the TOOL DECLARATIONS.
    `google.adk.tools.base_tool.BaseTool._api_variant` calls
    `get_google_llm_variant()`, which reads `GOOGLE_GENAI_USE_VERTEXAI` DIRECTLY
    off the environment and never consults the model or its client - so does
    `tools/_gemini_schema_util.py`. The declaration built for each tool then
    branches on it: `tools/_automatic_function_calling_util.py:406` returns early
    for the Gemini API variant and omits the response schema that the Vertex
    variant attaches.

    MEASURED, NOT ARGUED, on this target's own `issue_refund`, ADK 2.1.0, offline:

        unset  -> ['description', 'name', 'parameters_json_schema']
        =1     -> ['description', 'name', 'parameters_json_schema',
                   'response_json_schema']

    All eight tools return `dict`, so all eight differ. A client pin alone would
    therefore trade a LOUD failure (72 `ValueError: No API key was provided`) for
    a SILENT one: the same auth, a different payload, and a `target_agent_hash`
    that matches perfectly either way. That is the `deploy/RUNBOOK.md` shape
    exactly - the thing that was hashed is not the thing that decides - and the
    answer is to pin what can be pinned and refuse what cannot.
    """
    actual = env_provider(env)
    if actual != TARGET_PROVIDER:
        from . import tools
        raise ProviderMismatch(
            "%s resolves to provider %r; the frozen target descriptor says %r.\n"
            "  Set %s=1 before running against the real target.\n"
            "  This is not only an auth setting. ADK reads this variable "
            "directly when it builds TOOL DECLARATIONS "
            "(google/adk/tools/base_tool.py:154, "
            "_automatic_function_calling_util.py:406), so the wrong value sends "
            "a different payload for all %d tools while target_agent_hash stays "
            "identical. Nothing was called."
            % (PROVIDER_ENV_VAR, actual, TARGET_PROVIDER, PROVIDER_ENV_VAR,
               len(tools.TOOL_FUNCTIONS)))
    return actual


_PINNED_MODEL_CLASS = None


def _pinned_model_class():
    """A `Gemini` subclass whose client is pinned, not inherited from the shell.

    THE VENDOR-DOCUMENTED HOOK, not a hack: `google/adk/models/google_llm.py:98-110`
    tells you to subclass `Gemini` and override `api_client` to set exactly these
    options (`Client(vertexai=True, location="global")`). Stock ADK builds
    `Client()` with no arguments and lets `google.genai` read the environment.

    TWO REJECTED ALTERNATIVES, recorded so they are not re-derived:

    * **The Vertex long model name.** `supported_models()` accepts
      `projects/<p>/locations/global/publishers/google/models/gemini...`, and
      `api_client` sets `vertexai=True` on its own when the id starts with
      `projects/` - a one-string fix with no subclass. REJECTED because it puts a
      PROJECT ID inside `TARGET_MODEL`, which is hashed. The freeze would then be
      reproducible only inside `crucible-hack-2026`, and the exit criterion is
      that a judge recomputes it from a clean checkout.
    * **Setting the environment variable from in here.** One line, and it reaches
      the tool-declaration path a client pin cannot. REJECTED because it mutates
      shared process state from inside the thing under test, and because it
      silently repairs a misconfigured run instead of stopping it.

    `cached_property`, matching the base class, so one client is built per model
    instance rather than one per access. Construction stays credential-free:
    nothing here runs until the first actual call, which is why `build_agent()`
    still constructs on a machine with no project and no ADC.

    `project` is passed only when `GOOGLE_CLOUD_PROJECT` is set; otherwise
    `google.genai` resolves it the way it always has. `GOOGLE_CLOUD_LOCATION` is
    NOT consulted - `TARGET_ENDPOINT` is, and it is in the hash.
    """
    global _PINNED_MODEL_CLASS
    if _PINNED_MODEL_CLASS is not None:
        return _PINNED_MODEL_CLASS

    from functools import cached_property

    from google.adk.models import Gemini

    class _VertexPinnedGemini(Gemini):
        """`Gemini`, with the provider and endpoint taken out of the shell."""

        @cached_property
        def api_client(self):
            from google.genai import Client

            kwargs = {"vertexai": True, "location": TARGET_ENDPOINT}
            project = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
            if project:
                kwargs["project"] = project
            return Client(**kwargs)

    _PINNED_MODEL_CLASS = _VertexPinnedGemini
    return _PINNED_MODEL_CLASS


def build_agent():
    """Construct the ADK agent. Imports ADK; needs no credentials to construct.

    `model` is a `BaseLlm` INSTANCE, not the bare `TARGET_MODEL` string it was
    until 2026-08-22. `LlmAgent.model` is typed `Union[str, BaseLlm]`
    (`google/adk/agents/llm_agent.py:208`), and the string form is the form that
    lets the environment choose the provider and the endpoint. The pinned id is
    still `TARGET_MODEL`, now reachable as `agent.model.model`.
    """
    from google.adk.agents import LlmAgent
    from google.genai import types

    from . import tools

    return LlmAgent(
        name=TARGET_AGENT_NAME,
        model=_pinned_model_class()(model=TARGET_MODEL),
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

    `provider` WAS ADDED 2026-08-22 AND IT MOVED THE HASH. Before it, this
    descriptor recorded WHERE (`endpoint: global`) and never WHICH API, while the
    thing that actually decided which API was an unhashed environment variable.
    `target_agent_hash` could therefore match to the character across two runs
    that reached different services, under different auth, different quota and
    different billing - which is the one thing a hash-lock exists to make
    impossible. A freeze that omits the field that decides is not cheaper than one
    that includes it; it is weaker, and silently.
    """
    return {
        "target_id": "tgt_crucible_refund_v1",
        "agent_name": TARGET_AGENT_NAME,
        "model": TARGET_MODEL,
        "thinking_level": TARGET_THINKING_LEVEL,
        "provider": TARGET_PROVIDER,
        "endpoint": TARGET_ENDPOINT,
        "temperature_x100": 20,   # INT: no floats in a hashed payload
        "tool_binding": "bare_functions",
        "adk_version": "2.1.0",
    }
