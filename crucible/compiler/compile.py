"""compile.py - see the package docstring for why the attach assertion exists.

NOT IMPLEMENTED YET - this is the stub the negative checks run RED against.
"""

from dataclasses import dataclass
from typing import Any


class AttachError(RuntimeError):
    """The plugin cannot be attached in a configuration where it would be
    bypassed. A refusal, never a warning: a sub-agent whose tools skip the
    enforcement point produces a run that looks entirely normal and measures
    nothing."""


@dataclass
class CompiledPolicy:
    engine: Any
    core: Any
    policy_hash: str
    rule_count: int


def compile_policy(policy_document, *, manifest, derived_schema,
                   episode_context=None, compute=None, ledger=None,
                   approval_oracle=None, episode_id="ep_000000000000"):
    """Validate, then build the engine and the enforcement core."""
    raise NotImplementedError("L3 WI-7: compiler not implemented yet")


def assert_agent_tools_propagate_plugins(agent) -> None:
    """Walk an agent's tools and refuse any `AgentTool` with
    `include_plugins is not True`. Recurses into sub-agents."""
    raise NotImplementedError("L3 WI-7: compiler not implemented yet")
