"""crucible.compiler - policy document to a live ADK enforcement point. L3.

Two jobs, and the second is the interesting one.

  1. Compile a stored policy document into a `PolicyEngine` plus a configured
     `EnforcementCore`, refusing anything the validator refuses. A patch that
     will not validate must not become a plugin - "compiles" is the exit
     criterion, and a compiler that accepts a bad policy makes the criterion
     meaningless.

  2. THE ATTACH ASSERTION. Every `AgentTool` on the target must have
     `include_plugins is True`, or the attach is REFUSED.

     Why this replaced a much larger mechanism: ADK issue #2809 - a nested
     Runner not inheriting the parent's plugins - is FIXED in 2.1.0.
     `agent_tool.py:117-133, 238-250` propagates the parent's plugins when
     `include_plugins` is True, and True is the default. The whole `OPAQUE`
     union mechanism the architecture spec designed around that bug is
     therefore obsolete, and the correct replacement is one assertion.

     It is still an assertion rather than nothing, because the flag is a
     constructor argument anybody can pass False, and a False there means every
     tool call made by a sub-agent BYPASSES THE ENFORCEMENT POINT ENTIRELY while
     the run looks completely normal. Silence is the failure mode, so the check
     refuses rather than warns.

NOT IMPLEMENTED YET - this is the stub the negative checks run RED against.
"""

from .compile import (  # noqa: F401
    AttachError,
    CompiledPolicy,
    assert_agent_tools_propagate_plugins,
    compile_policy,
)

__all__ = [
    "compile_policy", "CompiledPolicy",
    "assert_agent_tools_propagate_plugins", "AttachError",
]
