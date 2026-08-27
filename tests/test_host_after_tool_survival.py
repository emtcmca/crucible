"""test_host_after_tool_survival.py - can a CRUCIBLE refusal survive a HOST
agent's own `after_tool_callback`, one CRUCIBLE has never seen?

WHERE THIS CAME FROM. On 2026-08-26 the foreign-agent probe attached
`CruciblePlugin` to Google's UNMODIFIED `adk-samples` customer-service agent and
blocked a `sync_ask_for_approval` call. The block held - 1 TOOL_ATTEMPT, 0
TOOL_EXECUTED - and then the HOST AGENT CRASHED:

    HOST AGENT FAULT  KeyError: 'status'

on both the stub arm and the live arm
(`docs/proof/foreign-agent-enforcement-probe-2026-08-26.txt`, cases A and the
`policy@run_...` live arm). ADK runs the host's own after-tool callbacks
unconditionally after a Step-1 short-circuit, and that sample's callback does a
bare subscript:

    if tool.name == "sync_ask_for_approval":
        if tool_response["status"] == "approved":

(`adk-samples` @ 629310b, `python/agents/customer-service/customer_service/
shared_libraries/callbacks.py:186-187`, and again at `:191-192` for
`approve_discount`.) CRUCIBLE's refusal payload does not carry `status`. A
hardening layer that crashes the thing it hardens has not finished the job.

WHY THE FIX IS NOT IN THE PAYLOAD, which is the part worth being explicit about
because the obvious repair is the dangerous one.

  * The only key that would have satisfied THIS host is `status` - the success
    field. `{"status": "approved"}` is what the sample's UNGUARDED run returns
    (probe case F), so a refusal carrying a `status` the host reads is a refusal
    that can be read as a completed call. That is catastrophically worse than a
    crash: the tool did not run and the agent would be told it did.
  * The next host reads something else. There is no key set that satisfies an
    unknown callback, so "add the key and go home" is unbounded guessing.
  * The host callback is not total over the shapes ADK ITSELF produces. ADK's
    own `FunctionTool.run_async` returns a bare `{'error': <str>}` for a missing
    mandatory argument, for an unconfirmed call and for a rejected call
    (`google/adk/tools/function_tool.py:242,266,272`). Every one of those
    crashes the same sample callback with no CRUCIBLE anywhere in the picture.
    The defect being repaired is therefore NOT "CRUCIBLE's payload is the wrong
    shape."

WHAT THE FIX IS. ADK's documented contract, read at source rather than assumed:
`flows/llm_flows/functions.py:594` runs the plugin after-tool hook (Step 4) and
`:604` runs the host agent's canonical after-tool callbacks (Step 5) ONLY when
Step 4 returned None; `:843`/`:853` are the identical pair on the live path, and
`plugins/base_plugin.py:340-344` states the same contract in prose. So
`CruciblePlugin.after_tool_callback` returns its own `blocked_result` on a
refusal, which stops Step 5 and keeps the host's result-post-processing callback
from being handed something that is not a result. Step 6 then substitutes that
payload for itself, so the model-visible bytes do not change at all.

THE TESTS BELOW, and what each is for:

  1. `test_a_denial_survives_a_host_after_tool_that_reads_a_key_the_refusal_
     lacks` - the regression test. It reproduces the probe's KeyError through a
     REAL `Runner`, and it FAILS before the fix.
  2. `test_a_host_after_tool_error_on_an_ALLOWED_call_still_propagates` - the
     control that makes (1) mean anything. It proves the harness genuinely wires
     the host callback into ADK Step 5 and that ADK does NOT swallow what it
     raises. Without this, (1) could pass because the host callback never ran.
     It doubles as the proof that CRUCIBLE does not silently swallow a host
     fault: on an ALLOWED call the host's exception comes straight back out.
  3. `test_the_refusal_payload_can_never_be_read_as_a_success` - the
     catastrophic case, proved impossible over the WHOLE decision space rather
     than for one example, with its own can-it-fail check.
  4. `test_the_model_sees_the_same_refusal_with_and_without_a_host_after_tool` -
     the fix changed who is handed the refusal, not what the refusal is.
  5. the live-path twin of (1), because this repo does not let a finding on one
     invocation path stand in for the other.
"""

import asyncio
import itertools

import pytest

from crucible.plugin.adk import ADK_AVAILABLE
from crucible.plugin.ledger import TOOL_ATTEMPT
from crucible.policy.decision import (ALLOW, APPROVAL_REQUIRED, DENY, Decision,
                                      REASON_APPROVAL_REQUIRED,
                                      REASON_CONSTRAINT_VIOLATED,
                                      REASON_POLICY_DENY)

from . import l3_fixtures as fx
from .test_adk_invocation_paths import (DENY_RULE, _drain_live,
                                        _function_response_dicts, _make_runner,
                                        _make_tool, _plugin_for)

pytestmark = pytest.mark.skipif(not ADK_AVAILABLE, reason="ADK not importable")

if ADK_AVAILABLE:
    from google.adk.agents.live_request_queue import LiveRequestQueue
    from google.adk.agents.llm_agent import LlmAgent
    from google.adk.agents.run_config import RunConfig
    from google.genai import types

    from .test_adk_invocation_paths import _FnCallLlm


# --------------------------------------------------------------------------
# The foreign host's callback, transcribed rather than imported.
# --------------------------------------------------------------------------

def _sample_shaped_after_tool(tool, args, tool_context, tool_response):
    """The SHAPE of `adk-samples` customer-service `after_tool`, reproduced
    here so this test does not depend on a checkout of somebody else's repo
    being present on the machine.

    Transcribed from `python/agents/customer-service/customer_service/
    shared_libraries/callbacks.py:178-196` @ 629310b: a bare subscript on
    `tool_response["status"]`, guarded only by the tool's NAME. That guard is
    what makes the crash selective - probe case B (`access_cart_information`)
    was blocked by the same plugin and did NOT crash, because this callback
    never subscripts for that tool.

    `_seen` records every call so a test can prove the callback ran at all
    rather than inferring it from the absence of a crash.
    """
    _sample_shaped_after_tool.seen.append(getattr(tool, "name", None))
    if getattr(tool, "name", None) == _HOSTILE_TOOL_NAME:
        if tool_response["status"] == "approved":       # <- KeyError lives here
            return {"result": "discount applied"}
    return None


_sample_shaped_after_tool.seen = []

# The refund fixture tool's ADK name, which is what the host callback keys on.
_HOSTILE_TOOL_NAME = "refund.tools.issue_refund"


def _agent_with_host_after_tool(tool, llm, callback):
    """An `LlmAgent` carrying a HOST-OWNED after-tool callback, wired the way
    the sample wires its own (`customer_service/agent.py:73`,
    `after_tool_callback=after_tool`). ADK resolves it through
    `LlmAgent.canonical_after_tool_callbacks` (`agents/llm_agent.py:761-772`),
    which is what Step 5 iterates."""
    return LlmAgent(name="root_agent", model=llm, tools=[tool],
                    after_tool_callback=callback)


async def _run_async_with_host_callback(amount_minor, plugins, callback):
    tool, calls = _make_tool()
    assert tool.name == _HOSTILE_TOOL_NAME, (
        "the host callback keys on the tool NAME; if the fixture tool is "
        "renamed this test would silently stop exercising the crash path")
    llm = _FnCallLlm(fn_name=tool.name, fn_args={
        "order_id": "ORD-1", "amount_minor": amount_minor,
        "beneficiary_id": "acct_8812"})
    agent = _agent_with_host_after_tool(tool, llm, callback)
    runner = _make_runner(agent, plugins)
    events = [
        e async for e in runner.run_async(
            user_id="u1", session_id="s1",
            new_message=types.Content(
                role="user", parts=[types.Part(text="refund it")]))
    ]
    return events, calls


# --------------------------------------------------------------------------
# 1. THE REGRESSION TEST. Fails before the fix with KeyError: 'status'.
# --------------------------------------------------------------------------

def test_a_denial_survives_a_host_after_tool_that_reads_a_key_the_refusal_lacks():
    """PROVES the defect the foreign-agent probe found is closed: with a HOST
    agent's own `after_tool_callback` attached - one that reads a key
    CRUCIBLE's refusal payload does not and must not carry - a DENY is a
    graceful refusal rather than a `KeyError` out of the runner.

    BEFORE THE FIX THIS RAISES `KeyError: 'status'`, exactly as
    `docs/proof/foreign-agent-enforcement-probe-2026-08-26.txt` case A records.
    ADK Step 4 returned None, Step 5 handed the host's callback CRUCIBLE's
    refusal dict, and the bare subscript blew up.

    Its control is `test_a_host_after_tool_error_on_an_ALLOWED_call_still_
    propagates`: that one proves this harness really does reach the host
    callback and that ADK really does let its exception out, so a pass here is
    "the callback was not given a non-result" and not "the callback never ran."
    """
    _sample_shaped_after_tool.seen.clear()
    plugin, core = _plugin_for(DENY_RULE)

    events, calls = asyncio.run(_run_async_with_host_callback(
        60000, [plugin], _sample_shaped_after_tool))

    # The block itself, unchanged. The fix must not have bought survival by
    # letting the call through.
    assert calls == [], "the wrapped Python function ran despite a DENY"
    attempts = [e for e in core.ledger.events if e["kind"] == TOOL_ATTEMPT]
    assert len(attempts) == 1 and attempts[0]["policy_decision"] == DENY
    assert core.ledger.executed() == (), (
        "a denied call wrote TOOL_EXECUTED")

    # The host's callback was NOT handed the non-result. This is the fix.
    assert _sample_shaped_after_tool.seen == [], (
        "ADK Step 5 still ran the host agent's after-tool callback on a "
        "refusal - CruciblePlugin.after_tool_callback must return a non-None "
        "value on its own denials (functions.py:594 Step 4 / :604 Step 5)")

    # And the refusal still reached the model, unchanged.
    responses = _function_response_dicts(events)
    assert any(r and r.get("error") == "CRUCIBLE_POLICY_BLOCK"
               for r in responses), (
        "the refusal did not reach the model - surviving the host callback "
        "must not cost the model-visible refusal")


# --------------------------------------------------------------------------
# 2. THE CONTROL. Proves the harness reaches Step 5 and that ADK does not
#    swallow what the host raises - and that CRUCIBLE does not either.
# --------------------------------------------------------------------------

def test_a_host_after_tool_error_on_an_ALLOWED_call_still_propagates():
    """PROVES TWO THINGS AT ONCE.

    (a) THE HARNESS IS CAPABLE OF SHOWING THE CRASH. The same host callback,
        the same runner, an amount the policy ALLOWS - the tool runs, returns
        `{"ok": True, ...}`, which carries no `status` either, and the bare
        subscript raises out of `runner.run_async`. Without this, the test
        above could be passing because ADK Step 5 never runs in this harness
        at all, or because the runner swallows exceptions.

    (b) CRUCIBLE DOES NOT SWALLOW A HOST FAULT. The suppression added for
        refusals is scoped to refusals. On an allowed call
        `after_tool_callback` returns None, the host's callback runs, and its
        exception is the HOST's and stays visible. A hardening layer that
        turned every host error into silence would hide exactly the failures a
        pre-deployment harness exists to surface.
    """
    _sample_shaped_after_tool.seen.clear()
    plugin, _core = _plugin_for(DENY_RULE)

    with pytest.raises(KeyError) as excinfo:
        asyncio.run(_run_async_with_host_callback(
            1000, [plugin], _sample_shaped_after_tool))
    assert excinfo.value.args[0] == "status"

    assert _sample_shaped_after_tool.seen == [_HOSTILE_TOOL_NAME], (
        "the host callback did not run on the ALLOWED path - this control "
        "proves nothing if Step 5 is unreachable in this harness")


# --------------------------------------------------------------------------
# 3. THE CATASTROPHIC CASE, proved impossible over the whole decision space.
# --------------------------------------------------------------------------

# Fields a host callback plausibly reads to conclude "the tool ran and here is
# what it returned." A refusal payload carrying ANY of these can be mistaken
# for a completed call by a callback that was never written to expect CRUCIBLE.
# `status` is first because it is the one the probe's host actually read, and
# it is therefore the exact key the tempting-but-wrong fix would have added.
SUCCESS_SHAPED_KEYS = frozenset({
    "status", "result", "results", "response", "output", "data", "value",
    "ok", "success", "succeeded", "approved", "state", "code", "content",
})

# Values that read as "it worked" regardless of the key they hang off.
SUCCESS_TOKENS = frozenset({
    "approved", "ok", "okay", "success", "successful", "succeeded", "done",
    "complete", "completed", "allow", "allowed", "granted", "accepted",
    "true", "yes", "pass", "passed", "applied",
})


def _reads_as_success(payload):
    """Returns a list of reasons `payload` could be read as a completed call.
    Empty list means it cannot be. Used BOTH as the assertion and, against a
    known success payload, as the proof that the assertion can fail."""
    reasons = []
    if not isinstance(payload, dict):
        return ["not a dict"]
    for key in sorted(set(payload) & SUCCESS_SHAPED_KEYS):
        reasons.append("carries success-shaped key %r" % key)
    if payload.get("error") != "CRUCIBLE_POLICY_BLOCK":
        reasons.append("no CRUCIBLE_POLICY_BLOCK error marker")
    for key, value in sorted(payload.items()):
        if isinstance(value, bool) and value is True:
            reasons.append("%r is True" % key)
        if isinstance(value, str) and value.strip().lower() in SUCCESS_TOKENS:
            reasons.append("%r reads as a success token (%r)" % (key, value))
    return reasons


def _blocked_payload_for(outcome, reason_code):
    """Builds the refusal payload through the SAME code path production uses -
    a real `EnforcementCore.before_tool`, from a real compiled policy - with
    only the engine's verdict forced. Building the dict by hand here would test
    a copy of the payload rather than the payload, and a check that derives its
    expectation the same way as the claim cannot catch the claim being wrong."""
    _plugin, core = _plugin_for(DENY_RULE)
    core.engine = _FixedEngine(
        Decision(outcome=outcome, rule_id="r_deadbeefdeadbeef",
                 reason_code=reason_code))
    call = core.before_tool(
        tool_handle=fx.T_REFUND, tool_name="issue_refund",
        tool_args={"order_id": "ORD-1", "amount_minor": 60000,
                   "beneficiary_id": "acct_8812"},
        invocation_id="inv-1")
    assert not call.allowed, (
        "%s/%s did not block, so there is no refusal payload to check"
        % (outcome, reason_code))
    return call.blocked_result


class _FixedEngine:
    """Returns one decision, whatever it is asked. The point of this test is
    the PAYLOAD's shape across the decision space, not how a decision is
    reached, and driving the real engine to each of six states would make the
    test about rule authoring instead."""

    def __init__(self, decision):
        self._decision = decision

    def evaluate(self, **_kwargs):
        return self._decision


def test_the_refusal_payload_can_never_be_read_as_a_success():
    """PROVES the thing that would be worse than the crash is impossible, and
    over the WHOLE space rather than for one sampled case.

    `crucible/policy/decision.py` fixes the space exactly: outcomes are ALLOW,
    DENY, APPROVAL_REQUIRED (`:31-33`) and reason codes are POLICY_DENY,
    CONSTRAINT_VIOLATED, APPROVAL_REQUIRED (`:36-38`). ALLOW never produces a
    refusal payload, so the blocking product is 2 x 3 = 6 and it is enumerated
    below in full.

    Every one of the six must fail `_reads_as_success`. In particular none may
    carry `status` - which is the key that would have made the probe's host
    agent stop crashing, and the reason the repair is NOT in the payload.
    """
    checked = 0
    for outcome, reason_code in itertools.product(
            (DENY, APPROVAL_REQUIRED),
            (REASON_POLICY_DENY, REASON_CONSTRAINT_VIOLATED,
             REASON_APPROVAL_REQUIRED)):
        payload = _blocked_payload_for(outcome, reason_code)
        assert _reads_as_success(payload) == [], (
            "%s/%s produced a refusal a host callback could read as a "
            "completed call: %r -> %s"
            % (outcome, reason_code, payload,
               _reads_as_success(payload)))
        assert payload["outcome"] != ALLOW
        assert "rule_id" not in payload, (
            "the refusal handed to the caller must not name the rule - "
            "core.py's module docstring, and probing would map the policy")
        checked += 1
    assert checked == 6, "the decision space was not covered"


def test_the_success_detector_can_actually_fail():
    """A check that cannot fail is not measuring anything. This runs
    `_reads_as_success` over payloads that ARE success-shaped and asserts each
    is caught - including the exact dict the probe's UNGUARDED run produced
    (`{"status": "approved"}`, case F), and the near-miss where somebody
    "fixes" the crash by adding a benign-looking `status`."""
    must_be_caught = [
        {"status": "approved"},                         # probe case F, verbatim
        {"error": "CRUCIBLE_POLICY_BLOCK", "outcome": DENY,
         "reason_code": REASON_POLICY_DENY, "status": "denied"},  # the wrong fix
        {"error": "CRUCIBLE_POLICY_BLOCK", "outcome": DENY,
         "reason_code": REASON_POLICY_DENY, "ok": True},
        {"outcome": DENY, "reason_code": REASON_POLICY_DENY},     # no marker
        {"result": "I have added and removed the requested items."},
    ]
    for payload in must_be_caught:
        assert _reads_as_success(payload) != [], (
            "the detector passed a success-shaped payload: %r" % (payload,))


# --------------------------------------------------------------------------
# 4. The fix changed WHO is handed the refusal, not WHAT it is.
# --------------------------------------------------------------------------

def test_the_model_sees_the_same_refusal_with_and_without_a_host_after_tool():
    """PROVES the repair is invisible to the measurement. ADK Step 6 replaces
    the function response with whatever Step 4 returned
    (`functions.py:614-616`), and Step 4 now returns the very object Step 1
    produced - so the function-response payload reaching the model is identical
    to a run with no host callback attached at all.

    If this ever fails, the refusal surface the RED_STRATEGIST reads has
    changed shape and every ASR figure taken across the change is measuring two
    different things."""
    _sample_shaped_after_tool.seen.clear()
    plugin_a, _ = _plugin_for(DENY_RULE)
    with_host, _calls_a = asyncio.run(_run_async_with_host_callback(
        60000, [plugin_a], _sample_shaped_after_tool))

    plugin_b, _ = _plugin_for(DENY_RULE)
    without_host, _calls_b = asyncio.run(_run_async_with_host_callback(
        60000, [plugin_b], None))

    a = [r for r in _function_response_dicts(with_host) if r]
    b = [r for r in _function_response_dicts(without_host) if r]
    assert a == b != [], (
        "the model-visible function responses differ depending on whether the "
        "host agent happens to have an after-tool callback: %r vs %r" % (a, b))


# --------------------------------------------------------------------------
# 5. The live path. Same code, different ADK call site - proved, not assumed.
# --------------------------------------------------------------------------

async def _run_live_with_host_callback(amount_minor, plugins, callback,
                                        *, max_events=2,
                                        per_event_timeout=5.0):
    tool, calls = _make_tool()
    llm = _FnCallLlm(fn_name=tool.name, fn_args={
        "order_id": "ORD-1", "amount_minor": amount_minor,
        "beneficiary_id": "acct_8812"})
    agent = _agent_with_host_after_tool(tool, llm, callback)
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


def test_run_live_a_denial_also_survives_a_host_after_tool():
    """The live-path twin of the regression test. ADK reaches the same two
    steps through a different call site - `functions.py:843` Step 4 and `:853`
    Step 5, versus `:594`/`:604` non-live - so this repo proves the finding on
    both paths rather than generalising from one (the same discipline
    `test_adk_invocation_paths.py` applies to its own findings)."""
    _sample_shaped_after_tool.seen.clear()
    plugin, core = _plugin_for(DENY_RULE)

    events, calls = asyncio.run(_run_live_with_host_callback(
        60000, [plugin], _sample_shaped_after_tool))

    assert calls == [], "the tool body ran despite a DENY on the live path"
    attempts = [e for e in core.ledger.events if e["kind"] == TOOL_ATTEMPT]
    assert len(attempts) == 1 and attempts[0]["policy_decision"] == DENY
    assert _sample_shaped_after_tool.seen == [], (
        "ADK Step 5 ran the host agent's after-tool callback on a refusal on "
        "the LIVE path (functions.py:843 Step 4 / :853 Step 5)")
    responses = _function_response_dicts(events)
    assert any(r and r.get("error") == "CRUCIBLE_POLICY_BLOCK"
               for r in responses)
