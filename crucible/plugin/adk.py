"""adk.py - the thin ADK adapter. Everything it knows lives in `core.py`.

ADK 2.1.0 is pinned and verified installed. `BasePlugin`'s thirteen hooks all
exist and their signatures match the architecture spec. We use three:

    before_tool_callback(*, tool, tool_args, tool_context) -> Optional[dict]
    after_tool_callback(*, tool, tool_args, tool_context, result) -> Optional[dict]
    on_tool_error_callback(*, tool, tool_args, tool_context, error) -> Optional[dict]

RETURNING A DICT FROM `before_tool_callback` SHORT-CIRCUITS THE TOOL: the dict
becomes the tool result and the tool body never runs. That is the enforcement
mechanism, and it is one of the four things CONVENTIONS 7 permits us to call
STRUCTURAL rather than conventional. Returning None lets the call proceed.

The ordering is verified rather than assumed:
`plugin_manager.run_before_tool_callback` fires at `functions.py:553`, Step 1,
BEFORE `agent.canonical_before_tool_callbacks` at `:564`. A plugin that ran
after the agent's own callbacks would be enforcing on arguments the agent had
already had a chance to rewrite.

`on_tool_error_callback` RETURNS NONE ALWAYS. Returning a dict there would
suppress the target's exception and hand it a synthetic success, which would let
CRUCIBLE convert a crash into a clean non-breach - a fragile target rendering as
a hardened one.

RETURNING A DICT FROM `after_tool_callback` SUPPRESSES THE HOST AGENT'S OWN
`after_tool_callback`, and on a REFUSAL that is the point. Same file, Steps 4-6:

    :594  Step 4  plugin_manager.run_after_tool_callback(...)   (non-live)
    :604  Step 5  `if altered_function_response is None:` ->
                  `for callback in agent.canonical_after_tool_callbacks`
    :843/:853     the identical pair on the live path

so a non-None plugin return means the host's own after-tool callbacks are never
reached, and Step 6 substitutes what the plugin returned. We return the SAME
`blocked_result` object `before_tool_callback` already returned, so what the
model sees is byte-identical either way: the mechanism changes who is handed the
refusal, not what the refusal is.

WHY THAT IS NECESSARY, found 2026-08-26 by attaching this plugin to Google's
UNMODIFIED `adk-samples` customer-service agent
(`docs/proof/foreign-agent-enforcement-probe-2026-08-26.txt`). ADK runs the
host's after-tool callbacks unconditionally after a Step-1 short-circuit. The
sample's own `after_tool` does `tool_response["status"]` on a bare subscript
(`customer_service/shared_libraries/callbacks.py:187,192`). A refusal payload
does not carry `status`, so the block held and the host agent then raised
`KeyError: 'status'` - a crash instead of a graceful refusal, on both the stub
and the live arm of that probe.

NO PAYLOAD SHAPE CAN FIX THAT, AND ATTEMPTING ONE IS THE DANGEROUS ROAD. The
host callback is not total over the result shapes ADK can hand it: ADK's own
`FunctionTool.run_async` returns a bare `{'error': <str>}` for a missing
mandatory argument, for an unconfirmed call, and for a rejected call
(`google/adk/tools/function_tool.py:242,266,272`), and every one of those
crashes that same sample callback with no CRUCIBLE in the picture at all. There
is no key set that satisfies an unknown host, and the only key that would have
satisfied THIS host is `status` - i.e. the success field whose presence would
let a refusal be read as a completed call. That is the one thing a refusal must
never do, so the fix cannot live in the payload. It lives in not handing a
result-post-processing callback something that is not a result.

WHAT IT COSTS, stated rather than discovered: on a CRUCIBLE refusal the host's
after-tool callbacks do not run, and neither do the after-tool callbacks of any
plugin registered after this one (`plugin_manager._run_callbacks` early-exits on
the first non-None return). A host that audits every call from its after-tool
hook loses that record for blocked calls. It keeps the ledger's TOOL_ATTEMPT,
which is the record enforcement is proven from, and it keeps its process.
ALLOWED calls are untouched: this returns None there, the host's callbacks run,
and an exception they raise propagates unchanged - a host fault stays a host
fault and stays visible.

IF ADK IS NOT IMPORTABLE this module still imports and `ADK_AVAILABLE` is False;
`core.EnforcementCore` is unaffected. The split exists so that a missing
dependency degrades the ADAPTER and not the MEASUREMENT.
"""

try:
    from google.adk.plugins.base_plugin import BasePlugin
    ADK_AVAILABLE = True
except ImportError:                                     # pragma: no cover
    ADK_AVAILABLE = False

    class BasePlugin:                                   # minimal stand-in
        def __init__(self, name="crucible"):
            self.name = name


class CruciblePlugin(BasePlugin):
    """CONVENTIONS 2.1 calls this component `CRUCIBLE_PLUGIN`. Pure code.

    It holds no policy logic of its own: every decision comes from
    `EnforcementCore`, and this class only translates ADK's objects into the
    core's arguments and the core's answer into ADK's return protocol.
    """

    def __init__(self, core, *, name: str = "crucible"):
        super().__init__(name=name)
        self.core = core
        # Keyed by ADK's invocation id + tool name so `after_tool` can find the
        # attempt its result belongs to. An episode is single-threaded through
        # the runner, but keying on identity rather than on "the last attempt"
        # means a future parallel tool call does not silently pair the wrong
        # result with the wrong attempt.
        self._pending = {}
        # Keyed the same way, and DISJOINT FROM `_pending` BY CONSTRUCTION:
        # every write to either one clears the other under that key, so a call
        # is either pending-executed or refused and never both. Holds the exact
        # `blocked_result` dict handed back from `before_tool_callback`, so
        # `after_tool_callback` can return that same object rather than rebuild
        # a second copy of it - a second construction site for the refusal
        # payload is a second thing to keep in step.
        self._refused = {}

    # -- helpers ----------------------------------------------------------
    def _key(self, tool, tool_context):
        return (getattr(tool_context, "invocation_id", None),
                getattr(tool, "name", None))

    def _resolve(self, tool):
        """ADK gives us a product tool name; the policy speaks in handles."""
        name = getattr(tool, "name", None)
        handle = self.core.handle_for(name)
        if handle is None:
            # Not in the manifest. A synthetic handle keeps the event
            # recordable; `capabilities_for` will return UNCLASSIFIED and the
            # D3 completeness check is what reports the gap.
            handle = "tool:t_%s" % ("0" * 8)
        return name, handle

    # -- hooks ------------------------------------------------------------
    async def before_tool_callback(self, *, tool, tool_args, tool_context):
        name, handle = self._resolve(tool)
        outcome = self.core.before_tool(
            tool_handle=handle, tool_name=name, tool_args=tool_args,
            invocation_id=getattr(tool_context, "invocation_id", "inv-unknown"),
            role=getattr(getattr(tool_context, "agent", None), "name", None))
        key = self._key(tool, tool_context)

        if not outcome.allowed:
            # A dict here means the tool body NEVER RUNS. This is the
            # short-circuit, and it is what makes a DENY leave a TOOL_ATTEMPT
            # with no matching TOOL_EXECUTED.
            #
            # NOTHING IS STORED IN `_pending` ON A DENIAL, AND THAT LINE IS THE
            # WHOLE FIX. Corrected 2026-08-21, after the first probe that drove
            # this adapter through a real `Runner` instead of calling it by hand.
            #
            # ADK runs `after_tool_callback` UNCONDITIONALLY, including after a
            # Step-1 short-circuit (`flows/llm_flows/functions.py:556` non-live,
            # `:800` live). The old code stored the attempt before checking
            # `allowed`, so `after_tool_callback` found it, popped it, and called
            # `core.after_tool` - which appends TOOL_EXECUTED for a tool that
            # never ran.
            #
            # It is worse than a spurious event. `core.after_tool` pops
            # `policy_decision` and `denied_by_rule_id` from the payload
            # (`core.py:206-207`), so the record it wrote was INDISTINGUISHABLE
            # FROM A REAL EXECUTION. The denial evidence was stripped on the way
            # out. The TRIPWIRE rules from the ledger and nothing else, so a
            # blocked attack could be scored as a breach - the measurement
            # inverted, silently, in the direction that flatters nothing and
            # corrupts everything.
            #
            # `core.after_tool`'s own docstring already stated the precondition:
            # "Only ever called when the call was allowed." The core was right;
            # the adapter broke its contract. That precondition is now ENFORCED
            # there rather than documented, so this cannot regress quietly.
            #
            # The `pop` clears any stale entry under this key from an earlier
            # call, so a denial can never inherit a previous attempt's event.
            self._pending.pop(key, None)
            # Recorded so `after_tool_callback` can return this exact payload
            # and thereby keep ADK from handing a non-result to the HOST
            # agent's own after-tool callbacks. See the module docstring for
            # why that cannot be fixed inside the payload instead.
            self._refused[key] = outcome.blocked_result
            return outcome.blocked_result

        self._refused.pop(key, None)
        self._pending[key] = outcome.attempt_event

        # The stamped arguments are written back so the tool executes against
        # the SAME values the policy was evaluated on. Without this the engine
        # judges one call and the target makes another.
        if isinstance(tool_args, dict):
            tool_args.clear()
            tool_args.update(outcome.attempt_event["args"])
        return None

    async def after_tool_callback(self, *, tool, tool_args, tool_context, result):
        key = self._key(tool, tool_context)

        refusal = self._refused.pop(key, None)
        if refusal is not None:
            # THE TOOL DID NOT RUN, SO THERE IS NO RESULT TO POST-PROCESS.
            # Returning non-None here stops ADK Step 5, so the host agent's own
            # after-tool callbacks are never handed this non-result. Returning
            # the SAME dict keeps the model-visible payload byte-identical to
            # what Step 1 already produced: Step 6 substitutes it for itself.
            #
            # No TOOL_EXECUTED is written and none must be - `core.after_tool`
            # raises `E_AFTER_TOOL_ON_DENIED_CALL` if it is ever handed a denied
            # attempt, and nothing is stored in `_pending` on a denial anyway.
            return refusal

        attempt = self._pending.pop(key, None)
        if attempt is not None:
            self.core.after_tool(attempt_event=attempt, result=result)
        # None ON THE ALLOWED PATH, ALWAYS. The host's after-tool callbacks run
        # normally and may alter the result; if one of them raises, that
        # exception is the HOST's and propagates unchanged. CRUCIBLE suppresses
        # the host's hook only where it refused the call itself.
        return None

    async def on_tool_error_callback(self, *, tool, tool_args, tool_context, error):
        key = self._key(tool, tool_context)
        # A refused call cannot reach Step 3, so it cannot raise a tool error.
        # Clearing anyway means a stale refusal can never be returned against a
        # LATER call that happens to land on the same key.
        self._refused.pop(key, None)
        attempt = self._pending.pop(key, None)
        if attempt is not None:
            self.core.on_tool_error(attempt_event=attempt, error=error)
        return None                       # ALWAYS. See the module docstring.
