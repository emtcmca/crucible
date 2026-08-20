"""adk.py - the thin ADK adapter. Everything it knows lives in `core.py`.

ADK 2.1.0 is pinned and verified installed. `BasePlugin`'s thirteen hooks all
exist and their signatures match. We use three of them:

    before_tool_callback(*, tool, tool_args, tool_context) -> Optional[dict]
    after_tool_callback(*, tool, tool_args, tool_context, result) -> Optional[dict]
    on_tool_error_callback(*, tool, tool_args, tool_context, error) -> Optional[dict]

Returning a dict from `before_tool_callback` SHORT-CIRCUITS the tool: the dict
becomes the tool result and the tool body never runs. That is the enforcement
mechanism, and it is one of the four things CONVENTIONS 7 permits us to call
STRUCTURAL rather than conventional.

If ADK is not importable, this module still imports and `CruciblePlugin` is
`None`; `core.EnforcementCore` is unaffected. The point of the split is that the
enforcement logic does not depend on the framework being present, so a missing
dependency degrades the ADAPTER and not the MEASUREMENT.

NOT IMPLEMENTED YET - this is the stub the negative checks run RED against.
"""

try:
    from google.adk.plugins.base_plugin import BasePlugin
    ADK_AVAILABLE = True
except ImportError:                                     # pragma: no cover
    BasePlugin = object
    ADK_AVAILABLE = False


class CruciblePlugin(BasePlugin):
    """CONVENTIONS 2.1 calls this component `CRUCIBLE_PLUGIN`. Pure code."""

    def __init__(self, core, *, name: str = "crucible"):
        raise NotImplementedError("L3 WI-6: ADK adapter not implemented yet")

    async def before_tool_callback(self, *, tool, tool_args, tool_context):
        raise NotImplementedError("L3 WI-6: ADK adapter not implemented yet")

    async def after_tool_callback(self, *, tool, tool_args, tool_context, result):
        raise NotImplementedError("L3 WI-6: ADK adapter not implemented yet")

    async def on_tool_error_callback(self, *, tool, tool_args, tool_context, error):
        raise NotImplementedError("L3 WI-6: ADK adapter not implemented yet")
