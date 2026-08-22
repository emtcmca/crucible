"""WHICH API THE TARGET TALKS TO, and why one pin was not enough.

THE FAILURE THIS FILE IS ABOUT. A live run on 2026-08-22 died 72 times with
`ValueError: No API key was provided. Please pass a valid API key.`
`GOOGLE_GENAI_USE_VERTEXAI` was unset, so ADK built the target's client against
the Gemini Developer API instead of Vertex. Exporting the variable cleared it.

THAT IS THE SHALLOW READING AND IT IS THE WRONG ONE. The defect was an asymmetry
plus a blind freeze:

    crucible/armorer/client.py:79   genai.Client(vertexai=True, ...)  PINNED
    target/refund_agent/agent.py    model=TARGET_MODEL                a bare string

and `target_descriptor()` hashed `"endpoint": "global"` - a claim about WHERE -
while WHETHER THE CALL REACHED VERTEX AT ALL was decided by an environment
variable no hash covers. So `target_agent_hash` could match to the character
across two runs that reached different services, under different auth, quota and
billing. Same shape as `deploy/RUNBOOK.md`'s 08-21 finding, where ADK baked a
REGION into the Cloud Run image while the code pinned `global`: the thing that was
hashed is not the thing that decides.

WHAT IS ASSERTED HERE, in the order the tests run:

  1. RED ON TODAY'S TREE. `--live` refuses when the variable does not resolve to
     Vertex, before any client is built and before a cent is spent.
  2. THE PIN IS REAL. The target's own model class asks `google.genai` for
     `vertexai=True, location="global"` even when the environment says otherwise -
     with stock ADK, under the identical environment, as the negative control.
  3. THE FROZEN DESCRIPTOR AND THE CLIENT AGREE, field by field, rather than by
     eye.
  4. WHY BOTH HALVES EXIST. A client pin cannot reach ADK's tool-declaration
     path, which reads the variable directly. Measured on this target's own
     tools, not argued.

WHAT REMAINS UNPROVEN WITHOUT A LIVE CALL - stated here rather than left for a
reader to discover, because a passing offline suite is exactly what the 08-22 run
already had:

  * NO TEST IN THIS FILE MAKES A NETWORK CALL. `google.genai.Client` is replaced
    with a recorder. So these prove WHAT THE TARGET ASKS FOR, never what the
    wire did with it. That `Client(vertexai=True, location="global")` in fact
    resolves to `aiplatform.googleapis.com` on the global endpoint is the SDK's
    behaviour and is taken on trust.
  * CREDENTIAL RESOLUTION IS NOT EXERCISED. The recorder never calls
    `google.auth.default()`, so nothing here proves ADC is present, that the
    project is billable, or that `crucible-target` holds `aiplatform.user`.
  * THE DECLARATION TEST COMPARES ADK'S OWN OUTPUT UNDER TWO ENVIRONMENTS. It
    proves the payload differs. It does NOT prove the model behaves differently
    on the two payloads - that needs a live A/B nobody has run.
  * ADK 2.1.0 ONLY. The line numbers cited in `agent.py` are that version's, and
    `adk_version` is in the frozen descriptor for exactly this reason.
"""

import os

import pytest

pytest.importorskip("google.adk", reason="ADK not installed; the rest of the suite "
                                         "does not need it")

from target.refund_agent import agent, tools  # noqa: E402


# ---------------------------------------------------------------------------
# A recorder in place of the real client. Constructing a real
# `google.genai.Client(vertexai=True, ...)` resolves credentials, and this lane
# is forbidden a network call - so the assertion is on the ARGUMENTS, which is
# also the only place the pin can be observed without egress.
# ---------------------------------------------------------------------------

class _RecordingClient:
    def __init__(self, **kwargs):
        self.kwargs = dict(kwargs)
        self.vertexai = kwargs.get("vertexai")


@pytest.fixture
def record_client(monkeypatch):
    """Capture every `google.genai.Client(...)` construction.

    Patches the attribute on the `google.genai` MODULE, because both ADK's
    `api_client` and this target's override resolve it with `from google.genai
    import Client` at call time. Patching the class object itself would miss it.
    """
    import google.genai as genai

    calls = []

    def _factory(**kwargs):
        client = _RecordingClient(**kwargs)
        calls.append(client)
        return client

    monkeypatch.setattr(genai, "Client", _factory)
    return calls


@pytest.fixture(autouse=True)
def _forget_the_pinned_class():
    """`agent._PINNED_MODEL_CLASS` is memoised at module scope. Left alone it
    would carry a `cached_property` client built under a previous test's
    environment into the next test, and the suite would be asserting on a stale
    object while looking like it passed."""
    agent._PINNED_MODEL_CLASS = None
    yield
    agent._PINNED_MODEL_CLASS = None


# ---------------------------------------------------------------------------
# 1. RED ON TODAY'S TREE: the run refuses.
# ---------------------------------------------------------------------------

def test_the_predicate_matches_adks_own_including_the_missing_strip():
    """`env_provider` must be the SAME predicate ADK uses, not a reasonable one.

    `google/adk/utils/env_utils.py:59` is
    `os.environ.get(name, '0').lower() in ['true', '1']` with NO `.strip()`, and
    `google/genai/_api_client.py:602-610` is the identical expression. So `" 1"`
    is DISABLED for both. A predicate here that stripped whitespace would report
    Vertex, ADK would build the developer-API surface, and the check would have
    manufactured the disagreement it exists to catch.
    """
    assert agent.env_provider({}) == "developer_api"
    assert agent.env_provider({"GOOGLE_GENAI_USE_VERTEXAI": "1"}) == "vertex"
    assert agent.env_provider({"GOOGLE_GENAI_USE_VERTEXAI": "true"}) == "vertex"
    assert agent.env_provider({"GOOGLE_GENAI_USE_VERTEXAI": "TRUE"}) == "vertex"
    assert agent.env_provider({"GOOGLE_GENAI_USE_VERTEXAI": "0"}) == "developer_api"
    assert agent.env_provider({"GOOGLE_GENAI_USE_VERTEXAI": "false"}) == "developer_api"
    # The one that matters, and the one a hand-written predicate gets wrong.
    assert agent.env_provider({"GOOGLE_GENAI_USE_VERTEXAI": " 1"}) == "developer_api"

    from google.adk.utils.env_utils import is_env_enabled
    for value in ("1", "true", "TRUE", "0", "false", " 1", "yes", ""):
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = value
        adk_says = "vertex" if is_env_enabled("GOOGLE_GENAI_USE_VERTEXAI") \
            else "developer_api"
        assert agent.env_provider() == adk_says, value
    os.environ.pop("GOOGLE_GENAI_USE_VERTEXAI", None)


def test_the_assertion_refuses_when_the_environment_says_developer_api():
    """FAILS RED ON THE TREE AS IT STOOD ON 2026-08-22: there was no assertion,
    the run started, and it produced 72 identical auth errors."""
    with pytest.raises(agent.ProviderMismatch) as exc:
        agent.assert_provider_matches_descriptor({})
    message = str(exc.value)
    assert "GOOGLE_GENAI_USE_VERTEXAI" in message
    assert "developer_api" in message and "vertex" in message
    # It has to say WHY this is not merely an auth setting, or the next reader
    # exports the variable, moves on, and never learns the payload changed too.
    assert "TOOL DECLARATIONS" in message
    assert "Nothing was called." in message


def test_the_assertion_passes_when_the_environment_agrees():
    """NEGATIVE CONTROL for the test above. Without it, an implementation that
    raised unconditionally would pass every other assertion in this file."""
    assert agent.assert_provider_matches_descriptor(
        {"GOOGLE_GENAI_USE_VERTEXAI": "1"}) == "vertex"


def test_live_refuses_before_anything_is_built(monkeypatch):
    """The wiring, not just the helper. `--live` stops in the preflight block,
    beside `--holdout-expected`, BEFORE `build_validator()` and before
    `make_call_model()`."""
    from crucible.conductor import campaign

    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)

    tripped = []
    monkeypatch.setattr(campaign, "build_validator",
                        lambda: tripped.append("build_validator") or (_ for _ in ()).throw(
                            AssertionError("reached build_validator")))

    with pytest.raises(agent.ProviderMismatch):
        campaign.run(["--live", "--holdout-expected", "2"])
    assert tripped == [], "the refusal came too late to be a precondition"


def test_offline_runs_are_not_gated_on_the_variable(monkeypatch):
    """NEGATIVE CONTROL, and it is load-bearing. `python -m pytest tests/` must
    stay runnable on a machine with no egress and no environment, and an offline
    run sends no declaration anywhere - so gating it would be a check that fires
    on correct behaviour."""
    from crucible.conductor import campaign

    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    reached = []
    monkeypatch.setattr(campaign, "build_validator",
                        lambda: reached.append(True) or (_ for _ in ()).throw(
                            RuntimeError("stop here, deliberately")))

    with pytest.raises(RuntimeError, match="stop here, deliberately"):
        campaign.run([])
    assert reached == [True]


# ---------------------------------------------------------------------------
# 2. THE PIN IS REAL, and stock ADK under the same environment is the control.
# ---------------------------------------------------------------------------

def test_the_target_asks_for_vertex_even_when_the_environment_says_otherwise(
        record_client, monkeypatch):
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "crucible-hack-2026")
    # The variable the RUNBOOK's 08-21 404 came through. The pin must ignore it.
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "us-central1")

    model = agent._pinned_model_class()(model=agent.TARGET_MODEL)
    client = model.api_client

    assert client.kwargs["vertexai"] is True
    assert client.kwargs["location"] == "global"
    assert client.kwargs["project"] == "crucible-hack-2026"
    assert "us-central1" not in repr(client.kwargs)


def test_stock_adk_under_the_identical_environment_does_not_ask_for_vertex(
        record_client, monkeypatch):
    """THE NEGATIVE CONTROL THAT MAKES THE TEST ABOVE MEAN SOMETHING. If stock
    `Gemini` already pinned Vertex, the pin would be decoration and the test
    above would pass for free.

    Stock ADK passes `vertexai=None`, which is `google.genai`'s "read the
    environment" sentinel (`_api_client.py:600`). With the variable unset that
    resolves to the Developer API - which is the 08-22 failure, reproduced.
    """
    from google.adk.models import Gemini

    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)

    client = Gemini(model=agent.TARGET_MODEL).api_client
    assert client.kwargs.get("vertexai") is None
    assert "location" not in client.kwargs


def test_build_agent_hands_adk_a_model_object_not_a_bare_string(record_client):
    """The bare string IS the defect: `LlmAgent.model` typed `Union[str, BaseLlm]`
    means the string form delegates the whole binding to the shell."""
    from google.adk.models.base_llm import BaseLlm

    a = agent.build_agent()
    assert isinstance(a.model, BaseLlm)
    assert not isinstance(a.model, str)
    assert a.model.model == agent.TARGET_MODEL
    # Still credential-free to construct: nothing asked for a client yet.
    assert record_client == []


# ---------------------------------------------------------------------------
# 3. THE FROZEN DESCRIPTOR AND THE ACTUAL CLIENT AGREE.
# ---------------------------------------------------------------------------

def test_the_frozen_descriptor_carries_the_provider():
    d = agent.target_descriptor()
    assert d["provider"] == "vertex"
    assert d["endpoint"] == "global"
    # Both must be the constants the client code reads, not literals that agree
    # today. A second spelling of one value is the drift this repo has rulings
    # about.
    assert d["provider"] is agent.TARGET_PROVIDER
    assert d["endpoint"] is agent.TARGET_ENDPOINT


def test_the_client_configuration_matches_the_frozen_descriptor_field_by_field(
        record_client, monkeypatch):
    """The agreement check the brief asked for, asserted rather than eyeballed."""
    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    descriptor = agent.target_descriptor()
    client = agent.build_agent().model.api_client

    observed_provider = "vertex" if client.kwargs.get("vertexai") else "developer_api"
    assert observed_provider == descriptor["provider"]
    assert client.kwargs.get("location") == descriptor["endpoint"]
    assert agent.build_agent().model.model == descriptor["model"]


def test_the_agreement_check_can_fail(record_client, monkeypatch):
    """NEGATIVE CONTROL for the agreement test. A comparison that cannot come out
    unequal is not a comparison. Here the descriptor is moved and the same
    reasoning must reject the client that was fine a line earlier."""
    monkeypatch.setattr(agent, "TARGET_ENDPOINT", "us-central1")
    moved = agent.target_descriptor()
    assert moved["endpoint"] == "us-central1"

    agent._PINNED_MODEL_CLASS = None
    client = agent.build_agent().model.api_client
    # The client is built from the SAME constant, so it moved with it - which is
    # the property under test. What must NOT hold is agreement with the value the
    # freeze actually records.
    assert client.kwargs["location"] == "us-central1"
    assert client.kwargs["location"] != "global"


# ---------------------------------------------------------------------------
# 4. WHY THE REFUSAL EXISTS ALONGSIDE THE PIN. Measured, not argued.
# ---------------------------------------------------------------------------

def test_the_variable_changes_the_tool_declarations_a_client_pin_cannot_reach(
        monkeypatch):
    """THE REASON OPTION A ALONE WOULD HAVE BEEN WORSE THAN THE BUG IT FIXED.

    `google/adk/tools/base_tool.py:154` reads `get_google_llm_variant()`, which
    reads `GOOGLE_GENAI_USE_VERTEXAI` off the environment and never consults the
    model or its client. `_automatic_function_calling_util.py:406` then returns
    early for the Gemini API variant, omitting the response schema.

    So a client pin with the variable still unset would have traded 72 loud auth
    errors for a silent payload difference, under a `target_agent_hash` that
    matches either way.
    """
    from google.adk.tools.function_tool import FunctionTool

    def declaration_keys(fn):
        decl = FunctionTool(fn)._get_declaration()
        return sorted(decl.model_dump(exclude_none=True).keys())

    monkeypatch.delenv("GOOGLE_GENAI_USE_VERTEXAI", raising=False)
    as_developer_api = {f.__name__: declaration_keys(f)
                        for f in tools.TOOL_FUNCTIONS}

    monkeypatch.setenv("GOOGLE_GENAI_USE_VERTEXAI", "1")
    as_vertex = {f.__name__: declaration_keys(f) for f in tools.TOOL_FUNCTIONS}

    assert as_developer_api != as_vertex
    # ALL EIGHT, not one. Every tool on this target returns `dict`, so every tool
    # loses its response schema on the wrong provider.
    assert len(tools.TOOL_FUNCTIONS) == 8
    for name in as_vertex:
        assert "response_json_schema" in as_vertex[name], name
        assert "response_json_schema" not in as_developer_api[name], name
