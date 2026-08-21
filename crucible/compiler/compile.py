"""compile.py - see the package docstring for why the attach assertion exists.

Two jobs: turn a stored policy document into a live enforcement point, and
refuse to attach it in any configuration where it would be silently bypassed.
"""

from dataclasses import dataclass
from typing import Any

from ..canon.hashing import policy_hash
from ..dsl.validator import validate_policy_document
from ..plugin.core import EnforcementCore
from ..plugin.ledger import EpisodeLedger
from ..plugin.stamper import DerivedStamper
from ..policy.engine import PolicyEngine


class AttachError(RuntimeError):
    """The plugin cannot be attached in a configuration where it would be
    bypassed. A REFUSAL, never a warning: a sub-agent whose tools skip the
    enforcement point produces a run that looks entirely normal, completes, and
    measures nothing. Silence is the failure mode, so it has to be loud."""


@dataclass
class CompiledPolicy:
    engine: Any
    core: Any
    policy_hash: str
    rule_count: int


def compile_policy(policy_document, *, manifest, derived_schema,
                   episode_context=None, compute=None, ledger=None,
                   approval_oracle=None, episode_id="ep_000000000000",
                   role="root_agent"):
    """Validate, then build the engine and the enforcement core.

    Validation is not optional here and not a convenience. "A hand-written patch
    COMPILES, registers, and the blocked tool never appears in the ledger" is an
    exit criterion, and a compiler that accepts a document the validator would
    refuse makes the first third of that sentence mean nothing.
    """
    validate_policy_document(policy_document)

    payload = policy_document.get("hashed_payload", policy_document)
    engine = PolicyEngine(payload)
    core = EnforcementCore(
        engine=engine,
        manifest=manifest,
        stamper=DerivedStamper(derived_schema, compute=compute),
        ledger=ledger if ledger is not None else EpisodeLedger(episode_id),
        episode_context=episode_context,
        approval_oracle=approval_oracle,
        role=role,
    )
    return CompiledPolicy(engine=engine, core=core,
                          policy_hash=policy_hash(payload),
                          rule_count=len(payload.get("rules", [])))


def assert_agent_tools_propagate_plugins(agent) -> None:
    """Walk an agent's tools and refuse any `AgentTool` with
    `include_plugins is not True`. Recurses into sub-agents.

    THIS ONE ASSERTION REPLACED THE WHOLE `OPAQUE` UNION MECHANISM. ADK issue
    #2809 - a nested Runner not inheriting the parent's plugins - is FIXED in
    2.1.0: `agent_tool.py:117-133, 238-250` propagates the parent's plugins when
    `include_plugins` is True, and True is the default. The architecture spec
    anticipated exactly this and said the mechanism could be deleted if the bug
    landed fixed.

    It is still an assertion rather than nothing, because `include_plugins` is a
    constructor argument anybody can pass False, and False there means every
    tool call made by that sub-agent BYPASSES THE ENFORCEMENT POINT ENTIRELY
    while the run looks completely normal - a full episode, a clean ledger, and
    an ASR that measures a boundary which was never applied.

    `is not True` and not `not x`: a truthy non-boolean (a string, a 1) would
    pass a falsy check while meaning something nobody intended.
    """
    seen = set()
    offenders = []

    def walk(node, path):
        if node is None or id(node) in seen:
            return
        seen.add(id(node))
        for tool in getattr(node, "tools", ()) or ():
            flag = getattr(tool, "include_plugins", None)
            if flag is not None and flag is not True:
                offenders.append("%s -> %s (include_plugins=%r)"
                                 % (path, getattr(tool, "name", tool), flag))
            inner = getattr(tool, "agent", None)
            if inner is not None:
                walk(inner, "%s/%s" % (path, getattr(inner, "name", "agent")))
        for sub in getattr(node, "sub_agents", ()) or ():
            walk(sub, "%s/%s" % (path, getattr(sub, "name", "agent")))

    walk(agent, getattr(agent, "name", "root"))
    if offenders:
        raise AttachError(
            "every AgentTool must have include_plugins is True or its tool "
            "calls bypass CRUCIBLE_PLUGIN entirely, producing a run that looks "
            "normal and measures nothing. Offenders: %s" % "; ".join(offenders))
