"""test_adk_invocation_paths.py - does the enforcement point actually fire?

`deploy/RUNBOOK.md` says the non-streaming path is "already answered" by
`tests/test_plugin_enforcement.py` and `tests/test_compiler_attach.py`, and
that what remains open is whether `CruciblePlugin.before_tool_callback` fires
on the streaming/live path ADK issue #4704 is about. `ADR-0012` records a
decision to use non-live `run_async` only, on the premise that the live path
is untrustworthy.

BOTH HALVES OF THAT PREMISE ARE WEAKER THAN THE RUNBOOK THINKS, and this file
is the empirical check rather than a re-read of the same claim.

1. `test_plugin_enforcement.py` calls `CruciblePlugin.before_tool_callback`
   DIRECTLY (`asyncio.run(plugin.before_tool_callback(...))`, e.g. line 304 as
   of this writing). There is no `Runner`, no `run_async`, and no ADK
   `functions.py` in that file - `grep -n "Runner|run_async|run_live"
   tests/test_plugin_enforcement.py` returns nothing. That test proves the
   ADAPTER's return-protocol translation (dict short-circuits, None passes
   through) against `EnforcementCore`. It proves NOTHING about whether ADK's
   `Runner` ever actually calls `before_tool_callback` on a real invocation.
   So "the local half is already answered" was not accurate: neither
   invocation path had ever been driven through a real `Runner`.

2. As installed (`google-adk==2.1.0`), the live path DOES call the plugin
   hook, on the same protocol as the non-live path:

     `flows/llm_flows/functions.py:556`  handle_function_calls_async ->
         `plugin_manager.run_before_tool_callback(...)`  (non-live)
     `flows/llm_flows/functions.py:800`  handle_function_calls_live ->
         `plugin_manager.run_before_tool_callback(...)`  (live)

   and `base_llm_flow.py:1102` is the only call site of
   `handle_function_calls_live`, reached from `Runner.run_live` via
   `_exec_with_plugin(..., is_live_call=True)` -> `execute()` ->
   `ctx.agent.run_live(ctx)` -> `_postprocess_live`. `functions.py` is the
   ONLY file in the installed package that calls
   `plugin_manager.run_before_tool_callback` (`grep -rn
   run_before_tool_callback google/adk` - two hits, both in this file). There
   is no separate, unguarded tool-call path for live mode. This directly
   contradicts the ADR-0012 premise ("before_tool_callback ... reported not to
   fire during live ... execution") for THIS ADK version - the tests below are
   what turn that source-reading into a checked fact instead of a second
   claim resting on the same kind of trust ADR-0012's premise did.

The tests below drive a real `google.adk.runners.Runner`, with `CruciblePlugin`
registered the way `docs/architecture-spec.md` says it is registered (via
`App(plugins=[...])`), against a REAL `google.adk.tools.function_tool.
FunctionTool` wrapping a real Python function - through BOTH `run_async` and
`run_live` - with no real model and no network call. The model is a
deterministic stub `BaseLlm` that always emits the same function call; ADK's
plugin machinery does not know or care what produced the function call, so a
canned model is sufficient to answer "does the hook fire, and does it block."

Each scenario asserts TWO things, kept separate on purpose:
  * FIRING - the ledger shows a `TOOL_ATTEMPT` (the callback ran at all).
  * BLOCKING - the wrapped Python function's own side-effect list stayed
    empty (the tool body never ran), not just that the ledger says DENY.
A test that only checked the ledger could pass against a plugin that logs a
denial and then lets the call through anyway; asserting the raw Python
side-effect is what rules that out.

Every blocking scenario is paired with two negative controls, per this repo's
testing convention (each test names what it proves and includes a check that
would fail if the mechanism silently stopped working):
  * an ALLOW-amount call through the same harness, proving the harness does
    not just always report "blocked" regardless of policy;
  * the identical DENY-amount call run with NO plugin registered, proving the
    harness genuinely reaches and executes the tool on its own - so a
    "blocked" result under (1) is attributable to CruciblePlugin, not to some
    other reason the fake tool never got called.
"""

import asyncio
import contextlib

import pytest

from crucible.plugin.adk import ADK_AVAILABLE, CruciblePlugin
from crucible.plugin.ledger import TOOL_ATTEMPT

from . import l3_fixtures as fx
from .test_plugin_enforcement import _build

pytestmark = pytest.mark.skipif(not ADK_AVAILABLE, reason="ADK not importable")

if ADK_AVAILABLE:
    from google.adk.agents.live_request_queue import LiveRequestQueue
    from google.adk.agents.llm_agent import LlmAgent
    from google.adk.agents.run_config import RunConfig
    from google.adk.apps.app import App
    from google.adk.models.base_llm import BaseLlm
    from google.adk.models.base_llm_connection import BaseLlmConnection
    from google.adk.models.llm_response import LlmResponse
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.adk.tools.function_tool import FunctionTool
    from google.genai import types

# fx.T_REFUND's tool_fqname in fx.MANIFEST_A - the manifest maps THIS product
# name to CAP_MOVES_MONEY, so a real FunctionTool must be named to match it
# for CruciblePlugin's `handle_for` lookup to resolve.
_REFUND_FQNAME = "refund.tools.issue_refund"

DENY_RULE = ("rule r_new1: cap:CAP_MOVES_MONEY when amount_minor >= 50000 "
             "=> deny\n")


# --------------------------------------------------------------------------
# Claim check - turns the module docstring's first finding into an assertion
# that stays true rather than stays remembered.
# --------------------------------------------------------------------------

def test_plugin_enforcement_dot_py_calls_the_callback_directly_not_via_a_runner():
    """PROVES the premise this file was written to check: as of this writing,
    `tests/test_plugin_enforcement.py` never constructs a `Runner` and never
    calls `run_async`/`run_live`. It calls
    `CruciblePlugin.before_tool_callback` as a plain coroutine.

    If this ever fails, it means someone added a real `Runner`-driven
    invocation to that file - which would be good news, but it also means the
    file's docstring and `deploy/RUNBOOK.md`'s "already answered" framing
    should be re-read, since the thing this repo previously relied on to
    justify that framing would have changed shape.
    """
    import pathlib
    src = (pathlib.Path(__file__).resolve().parent
           / "test_plugin_enforcement.py").read_text(encoding="utf-8")
    assert "Runner(" not in src
    assert "run_async(" not in src
    assert "run_live(" not in src
    # Negative control: the string IS present here, in THIS file, proving the
    # search itself is capable of matching when the thing being searched for
    # actually exists.
    this_src = pathlib.Path(__file__).read_text(encoding="utf-8")
    assert "Runner(" in this_src


# --------------------------------------------------------------------------
# Harness - a real Runner, a real FunctionTool, a canned model.
# --------------------------------------------------------------------------

def _plugin_for(rule_text):
    """The real pipeline (parse -> validate -> document -> compile), reused
    from `test_plugin_enforcement._build` rather than re-implemented, so this
    file cannot silently drift from how the rest of L3 builds a policy."""
    compiled = _build(rule_text)
    return CruciblePlugin(compiled.core), compiled.core


def _make_tool():
    """A REAL `google.adk.tools.function_tool.FunctionTool` wrapping a REAL
    Python function. `calls` is the ground-truth side effect: if the plugin's
    DENY genuinely short-circuits ADK's tool-call path, this list stays
    empty no matter what the ledger says."""
    calls = []

    def issue_refund(order_id: str, amount_minor: int,
                      beneficiary_id: str) -> dict:
        """Refund fixture tool, wired to a real ADK FunctionTool."""
        calls.append({"order_id": order_id, "amount_minor": amount_minor,
                      "beneficiary_id": beneficiary_id})
        return {"ok": True, "order_id": order_id}

    tool = FunctionTool(issue_refund)
    # FunctionTool defaults .name to the Python function's __name__; override
    # it to the manifest's tool_fqname so CruciblePlugin's handle_for() (and
    # ADK's own tools_dict lookup by function-call name) both resolve it.
    tool.name = _REFUND_FQNAME
    return tool, calls


def _already_has_function_response(llm_request) -> bool:
    for content in llm_request.contents or ():
        for part in content.parts or ():
            if part.function_response is not None:
                return True
    return False


class _FnCallLlm(BaseLlm):
    """A deterministic stub model. No network call, no credentials, no real
    model weights: it always emits the SAME function call on the first turn,
    then a plain text reply once a function response is already in the
    request (which is what lets `run_async`'s loop terminate normally).

    ADK's plugin hook fires (or does not) based on what the AGENT does with a
    function call the model produced, not on how that function call was
    produced - so a canned model is sufficient evidence either way.
    """

    model: str = "fake-crucible-probe"
    fn_name: str
    fn_args: dict

    async def generate_content_async(self, llm_request, stream: bool = False):
        if _already_has_function_response(llm_request):
            yield LlmResponse(content=types.Content(
                role="model", parts=[types.Part(text="done")]))
            return
        yield LlmResponse(content=types.Content(
            role="model",
            parts=[types.Part(function_call=types.FunctionCall(
                name=self.fn_name, args=dict(self.fn_args)))]))

    @contextlib.asynccontextmanager
    async def connect(self, llm_request):
        yield _FnCallConnection(self.fn_name, dict(self.fn_args))


class _FnCallConnection(BaseLlmConnection):
    """The live-mode counterpart. `receive()` yields exactly one function-call
    response on its first call. On any later call (ADK's `run_live` reconnect
    loop calls `receive()` again after a generator ends) it blocks on an
    `asyncio.Event` that is never set, rather than returning immediately -
    that keeps the reconnect loop from spinning once the one canned turn has
    been delivered. The probe tears the outer generator down explicitly
    (`agen.aclose()`, under a timeout) once it has the events it needs; it
    does not rely on this connection ever closing itself.
    """

    def __init__(self, fn_name, fn_args):
        self._fn_name = fn_name
        self._fn_args = fn_args
        self._delivered = False

    async def send_history(self, history):
        return None

    async def send_content(self, content):
        return None

    async def send_realtime(self, blob):
        return None

    async def close(self):
        return None

    async def receive(self):
        if not self._delivered:
            self._delivered = True
            yield LlmResponse(content=types.Content(
                role="model",
                parts=[types.Part(function_call=types.FunctionCall(
                    name=self._fn_name, args=dict(self._fn_args)))]))
        await asyncio.Event().wait()
        yield  # pragma: no cover - unreachable; keeps this an async generator


def _make_runner(agent, plugins):
    app = App(name="crucible_probe_app", root_agent=agent,
               plugins=list(plugins))
    return Runner(app=app, session_service=InMemorySessionService(),
                  auto_create_session=True)


def _function_response_dicts(events):
    """Every `function_response.response` dict carried by any event - this is
    what the model (and, transitively, the RED_STRATEGIST in the real system)
    actually SEES as the tool's result, whether that result came from the
    real tool or from CruciblePlugin's short-circuit."""
    out = []
    for event in events:
        if not event.content or not event.content.parts:
            continue
        for part in event.content.parts:
            if part.function_response is not None:
                out.append(part.function_response.response)
    return out


# --------------------------------------------------------------------------
# run_async
# --------------------------------------------------------------------------

async def _run_async_scenario(amount_minor, plugins):
    tool, calls = _make_tool()
    llm = _FnCallLlm(fn_name=tool.name, fn_args={
        "order_id": "ORD-1", "amount_minor": amount_minor,
        "beneficiary_id": "acct_8812"})
    agent = LlmAgent(name="root_agent", model=llm, tools=[tool])
    runner = _make_runner(agent, plugins)
    events = [
        e async for e in runner.run_async(
            user_id="u1", session_id="s1",
            new_message=types.Content(
                role="user", parts=[types.Part(text="refund it")]))
    ]
    return events, calls


def test_run_async_blocks_the_real_tool_call_when_the_plugin_denies():
    """PROVES: driven through an actual `Runner.run_async` call - not a
    direct call to `before_tool_callback` - `CruciblePlugin` fires and its
    DENY stops ADK from ever invoking the wrapped Python `issue_refund`
    function. This is the non-live half of the open question, proved rather
    than assumed from `test_plugin_enforcement.py`.

    Negative controls: `test_run_async_executes_the_real_tool_call_when_the_
    plugin_allows` (same harness, allowed amount, tool DOES run) and
    `test_without_the_plugin_the_attack_call_executes_through_run_async`
    (same attack amount, no plugin, tool DOES run) - together they rule out
    both "this always reports blocked" and "the harness never really reaches
    the tool at all."
    """
    plugin, core = _plugin_for(DENY_RULE)
    events, calls = asyncio.run(_run_async_scenario(60000, [plugin]))

    # GROUND TRUTH for blocking: the wrapped Python function's own
    # side-effect list. This is the assertion that cannot be fooled by the
    # ledger's bookkeeping (see the KNOWN_ISSUE test below for why the
    # ledger itself is NOT trustworthy evidence of blocking when driven
    # through a real Runner).
    assert calls == [], (
        "the wrapped Python function executed despite a DENY - the plugin "
        "fired but did not block")
    attempts = [e for e in core.ledger.events if e["kind"] == TOOL_ATTEMPT]
    assert len(attempts) == 1, "before_tool_callback did not fire at all"
    assert attempts[0]["policy_decision"] == "DENY"

    responses = _function_response_dicts(events)
    assert any(r and r.get("error") == "CRUCIBLE_POLICY_BLOCK"
               for r in responses), (
        "no CRUCIBLE_POLICY_BLOCK function response reached the model - the "
        "short-circuit protocol did not make it back through ADK's own "
        "event-building path")


def test_run_async_a_denied_call_writes_no_tool_executed_event():
    """UNEXPECTED FINDING, not something this probe was sent to look for.

    `core.py`'s own `after_tool` docstring says "Only ever called when the
    call was allowed," and `test_plugin_enforcement.py`'s exit-criterion-1
    test asserts a DENY leaves `core.ledger.executed() == ()` - "a DENY
    produces an ATTEMPT with no matching EXECUTED... exactly how enforcement
    is proven from the record alone" (ledger.py's own module docstring says
    the same). Both of those are true ONLY because the hand-written tests
    call `after_tool_callback` themselves, and only on the ALLOW branch.

    A REAL ADK `Runner` does not skip `after_tool_callback` on a DENY.
    `functions.py`'s `_execute_single_function_call_async` runs Step 4
    ("plugin after_tool_callback") UNCONDITIONALLY after Steps 1-3, passing
    whatever `function_response` already is - which, on a DENY, is
    `CruciblePlugin`'s own `blocked_result` dict, since Step 1 already set
    it. `CruciblePlugin.after_tool_callback` (`crucible/plugin/adk.py`) does
    not check `outcome.allowed` before calling `core.after_tool(...)`; it
    just pops `_pending` and records whatever `result` ADK handed it.

    The observable effect: a DENY produces a TOOL_ATTEMPT *and* a
    TOOL_EXECUTED, with `result_digest` computed over the BLOCKED dict, and
    the denied tool's handle appears in `core.ledger.executed_handles()`
    even though `calls == []` proves the tool body never ran (see the test
    above). L3 exit criterion 1's headline claim - "the blocked tool never
    appears in the ledger [as executed]" - does not hold once the plugin is
    driven by a real Runner instead of called directly.

    This test asserts the CURRENT, real behavior (so it fails loudly if
    someone fixes it without also updating this test), not the behavior the
    rest of the repo currently assumes. It is named KNOWN_ISSUE rather than
    silently adjusted around, because the fix belongs in
    `crucible/plugin/adk.py::CruciblePlugin.after_tool_callback` (skip
    `core.after_tool` when the popped attempt was itself a denial), which is
    out of scope for this file to touch.
    """
    plugin, core = _plugin_for(DENY_RULE)
    events, calls = asyncio.run(_run_async_scenario(60000, [plugin]))
    assert calls == [], "the tool body must not run"

    assert core.ledger.executed() == (), (
        "A DENIED CALL WROTE TOOL_EXECUTED. This is the defect described "
        "above, and it inverts the measurement: core.after_tool strips "
        "policy_decision and denied_by_rule_id, so the record is "
        "indistinguishable from a real execution, and the TRIPWIRE rules from "
        "this ledger alone. Fix is in CruciblePlugin.before_tool_callback - do "
        "not store a pending attempt on a denial.")
    assert fx.T_REFUND not in core.ledger.executed_handles(), (
        "the blocked tool's handle is in executed_handles()")

    # The other half of L3 exit criterion 1, and the reason "no events at all"
    # would be the wrong fix: the ATTEMPT must survive. An absent record is
    # indistinguishable from a call the target never made, and the whole value
    # of the ledger is proving the block without trusting the plugin's account
    # of itself.
    attempts = [e for e in core.ledger.events if e["kind"] == TOOL_ATTEMPT]
    assert len(attempts) == 1, "the DENY must still leave a TOOL_ATTEMPT"


def test_run_async_executes_the_real_tool_call_when_the_plugin_allows():
    """Negative control for the test above: the identical harness, an amount
    under the rule's threshold. If this failed, the DENY test would be
    meaningless - it could be passing because the harness blocks everything,
    not because CruciblePlugin evaluated the policy."""
    plugin, core = _plugin_for(DENY_RULE)
    events, calls = asyncio.run(_run_async_scenario(1000, [plugin]))

    assert len(calls) == 1 and calls[0]["amount_minor"] == 1000
    assert fx.T_REFUND in core.ledger.executed_handles()
    responses = _function_response_dicts(events)
    assert any(r and r.get("ok") is True for r in responses)


def test_without_the_plugin_the_attack_call_executes_through_run_async():
    """Negative control for the harness itself: the SAME attack-amount call
    as the DENY test above, with NO plugins registered on the Runner. The
    tool executes. This is what proves the DENY test's empty `calls` list
    means 'the plugin blocked it' rather than 'this fake tool never gets
    reached by this harness for some unrelated reason.'"""
    events, calls = asyncio.run(_run_async_scenario(60000, []))
    assert len(calls) == 1 and calls[0]["amount_minor"] == 60000
    responses = _function_response_dicts(events)
    assert any(r and r.get("ok") is True for r in responses)


# --------------------------------------------------------------------------
# run_live
# --------------------------------------------------------------------------

async def _drain_live(agen, *, max_events, per_event_timeout):
    events = []
    try:
        while len(events) < max_events:
            event = await asyncio.wait_for(agen.__anext__(),
                                            timeout=per_event_timeout)
            events.append(event)
    except (StopAsyncIteration, asyncio.TimeoutError):
        pass
    finally:
        try:
            await asyncio.wait_for(agen.aclose(), timeout=per_event_timeout)
        except (asyncio.TimeoutError, RuntimeError):
            # A live session that will not close within the budget does not
            # invalidate what was already collected; it is reported, not
            # silently swallowed - see the probe's proof file.
            pass
    return events


async def _run_live_scenario(amount_minor, plugins, *, max_events=2,
                              per_event_timeout=5.0):
    """`max_events=2` matches exactly what the fake connection's single
    canned turn produces (the model-response event carrying the function
    call, then the function-response event) - draining stops the instant
    both have arrived instead of idling out `per_event_timeout` waiting on a
    third event that this harness never sends."""
    tool, calls = _make_tool()
    llm = _FnCallLlm(fn_name=tool.name, fn_args={
        "order_id": "ORD-1", "amount_minor": amount_minor,
        "beneficiary_id": "acct_8812"})
    agent = LlmAgent(name="root_agent", model=llm, tools=[tool])
    runner = _make_runner(agent, plugins)

    queue = LiveRequestQueue()
    queue.send_content(types.Content(
        role="user", parts=[types.Part(text="refund it")]))
    run_config = RunConfig(response_modalities=["TEXT"])

    agen = runner.run_live(user_id="u1", session_id="s1",
                            live_request_queue=queue, run_config=run_config)
    try:
        events = await _drain_live(agen, max_events=max_events,
                                    per_event_timeout=per_event_timeout)
    finally:
        queue.close()
    return events, calls


def test_run_live_blocks_the_real_tool_call_when_the_plugin_denies():
    """PROVES the question `deploy/RUNBOOK.md` and `ADR-0012` left open:
    driven through an actual `Runner.run_live` call - the same path
    `adk web` uses for bidirectional streaming - does `CruciblePlugin` still
    fire and still block?

    Answer, empirically, for `google-adk==2.1.0` as installed: YES on both
    counts. See the module docstring for the source citation
    (`functions.py:800`, reached from `base_llm_flow.py:1102`) that this test
    turns into a checked fact.

    Negative controls mirror the run_async section: `test_run_live_executes_
    the_real_tool_call_when_the_plugin_allows` and
    `test_without_the_plugin_the_attack_call_executes_through_run_live`.
    """
    plugin, core = _plugin_for(DENY_RULE)
    events, calls = asyncio.run(
        _run_live_scenario(60000, [plugin]))

    # GROUND TRUTH for blocking - see the run_async section's KNOWN_ISSUE
    # test for why `core.ledger.executed()` is not trustworthy evidence here.
    assert calls == [], (
        "the wrapped Python function executed despite a DENY on the live "
        "path - the plugin fired but did not block")
    attempts = [e for e in core.ledger.events if e["kind"] == TOOL_ATTEMPT]
    assert len(attempts) == 1, (
        "before_tool_callback never fired on the live path - if this test "
        "starts failing, ADR-0012's premise (the callback does not fire "
        "under live/streaming) would be TRUE again for whatever ADK version "
        "is installed, and the demo must not show adk web on camera")
    assert attempts[0]["policy_decision"] == "DENY"

    responses = _function_response_dicts(events)
    assert any(r and r.get("error") == "CRUCIBLE_POLICY_BLOCK"
               for r in responses), (
        "no CRUCIBLE_POLICY_BLOCK function response reached the model on "
        "the live path")


def test_run_live_a_denied_call_writes_no_tool_executed_event():
    """The live-path counterpart to the run_async KNOWN_ISSUE test above -
    same root cause (`functions.py`'s live handler also runs the plugin's
    `after_tool_callback` Step unconditionally at `:800`+, and
    `CruciblePlugin.after_tool_callback` does not check `outcome.allowed`
    before recording). See that test's docstring for the full explanation;
    this one exists so the finding is proven on BOTH invocation paths rather
    than assumed to generalize from one."""
    plugin, core = _plugin_for(DENY_RULE)
    events, calls = asyncio.run(_run_live_scenario(60000, [plugin]))
    assert calls == [], "the tool body must not run on the live path either"

    assert core.ledger.executed() == (), (
        "A DENIED CALL WROTE TOOL_EXECUTED ON THE LIVE PATH. Same defect as "
        "the run_async twin; ADK reaches after_tool_callback through a "
        "different call site (functions.py:800 rather than :556), so both are "
        "asserted rather than one being assumed to generalize.")
    assert fx.T_REFUND not in core.ledger.executed_handles()
    assert len([e for e in core.ledger.events
                if e["kind"] == TOOL_ATTEMPT]) == 1, (
        "the DENY must still leave a TOOL_ATTEMPT")


def test_run_live_executes_the_real_tool_call_when_the_plugin_allows():
    """Negative control: same live harness, an amount under the rule's
    threshold. The tool runs. Rules out 'run_live always reports blocked.'"""
    plugin, core = _plugin_for(DENY_RULE)
    events, calls = asyncio.run(_run_live_scenario(1000, [plugin]))

    assert len(calls) == 1 and calls[0]["amount_minor"] == 1000
    assert fx.T_REFUND in core.ledger.executed_handles()
    responses = _function_response_dicts(events)
    assert any(r and r.get("ok") is True for r in responses)


def test_without_the_plugin_the_attack_call_executes_through_run_live():
    """Negative control for the live harness itself: the identical
    attack-amount call, no plugin registered. The tool executes - proving the
    DENY test's blocked result is attributable to CruciblePlugin and not to
    some unrelated reason the fake tool never gets reached on the live
    path."""
    events, calls = asyncio.run(_run_live_scenario(60000, []))
    assert len(calls) == 1 and calls[0]["amount_minor"] == 60000
    responses = _function_response_dicts(events)
    assert any(r and r.get("ok") is True for r in responses)


def test_core_after_tool_refuses_a_denied_attempt_outright():
    """The guard added alongside the fix, and proof that it can fail.

    Fixing `CruciblePlugin` stops the bad call from being MADE. This asserts the
    callee now refuses it if some future caller makes it anyway - a different
    adapter, a replay path, a refactor that reorders the branches back.

    `core.after_tool`'s docstring has said "Only ever called when the call was
    allowed" since it was written, and the precondition was violated for the
    entire life of the adapter without anything noticing, because a docstring is
    not a check. The two tests above prove the caller behaves; this one proves
    the boundary holds without trusting the caller.

    THE ATTEMPT EVENT IS TAKEN FROM A REAL RUN rather than hand-built. The first
    draft of this test built one by hand and the ledger refused it - C1 requires
    eleven fields and the synthetic dict had seven. That refusal was correct, and
    writing the missing fields in by hand would have put a second copy of C1's
    field list in a test file, where it would rot. Take a real event instead.
    """
    import pytest as _pytest

    plugin, core = _plugin_for(DENY_RULE)
    asyncio.run(_run_async_scenario(1000, [plugin]))        # under threshold: ALLOWED
    real = [e for e in core.ledger.events if e["kind"] == TOOL_ATTEMPT]
    assert len(real) == 1, "harness precondition: one allowed attempt"
    base = dict(real[0])

    denied = dict(base, policy_decision="DENY", denied_by_rule_id="r_test")
    with _pytest.raises(ValueError, match="E_AFTER_TOOL_ON_DENIED_CALL"):
        core.after_tool(attempt_event=denied, result={"blocked": True})

    # Negative control. The same event on the allow branch must still be
    # written, or the guard would be "passing" by rejecting everything - which
    # is the failure mode a guard is most likely to have and least likely to
    # show.
    allowed = dict(base, policy_decision="ALLOW")
    allowed.pop("denied_by_rule_id", None)
    written = core.after_tool(attempt_event=allowed, result={"status": "ok"})
    assert written["kind"] != TOOL_ATTEMPT, "an ALLOW must still record executed"
    assert "policy_decision" not in written, (
        "after_tool strips policy_decision - the behaviour that made the "
        "original defect invisible in the record")
