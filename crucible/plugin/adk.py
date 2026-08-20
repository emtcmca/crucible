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
        self._pending[self._key(tool, tool_context)] = outcome.attempt_event

        if not outcome.allowed:
            # A dict here means the tool body NEVER RUNS. This is the
            # short-circuit, and it is the reason a DENY leaves a TOOL_ATTEMPT
            # with no matching TOOL_EXECUTED.
            return outcome.blocked_result

        # The stamped arguments are written back so the tool executes against
        # the SAME values the policy was evaluated on. Without this the engine
        # judges one call and the target makes another.
        if isinstance(tool_args, dict):
            tool_args.clear()
            tool_args.update(outcome.attempt_event["args"])
        return None

    async def after_tool_callback(self, *, tool, tool_args, tool_context, result):
        attempt = self._pending.pop(self._key(tool, tool_context), None)
        if attempt is not None:
            self.core.after_tool(attempt_event=attempt, result=result)
        return None

    async def on_tool_error_callback(self, *, tool, tool_args, tool_context, error):
        attempt = self._pending.pop(self._key(tool, tool_context), None)
        if attempt is not None:
            self.core.on_tool_error(attempt_event=attempt, error=error)
        return None                       # ALWAYS. See the module docstring.
