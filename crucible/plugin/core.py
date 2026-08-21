"""core.py - CRUCIBLE_PLUGIN's enforcement logic, with no ADK types in it.

The ADK adapter is `crucible/plugin/adk.py` and it is deliberately thin. Two
reasons the logic lives here instead of in the `BasePlugin` subclass:

  * The enforcement point is testable without constructing a `ToolContext`, an
    `InvocationContext`, a session service, and a runner. A test that needs six
    framework objects to assert one boolean gets written once and then not
    maintained.
  * CONVENTIONS 2.1 lists CRUCIBLE_PLUGIN as pure code. Keeping the decision
    path free of framework objects is how that stays checkable rather than
    asserted.

THE ORDER OF OPERATIONS IN `before_tool`, and every step is load-bearing:

  1. REFUSE ANY `episode.*` KEY IN THE CALL ARGUMENTS -> HALT_HUMAN.
     Ruling 16. This runs FIRST, before stamping and before evaluation, because
     a write that reaches the evaluator has already done its damage: the rule
     `to == episode.account_holder_email` would then be compared against a value
     the caller supplied.
  2. STAMP `derived.*`, discarding model-authored values and recording them.
  3. EVALUATE the policy against POST-STAMP args and the visible prefix.
  4. RECORD a TOOL_ATTEMPT carrying the decision, the post-stamp args, the
     role, and `derived_overwrites`.
     Post-stamp args, not pre-stamp: replay READS these values rather than
     recomputing them, and pre-stamp args would leave the bundle carrying
     neither the tool returns nor the values derived from them - so replay could
     not reproduce the decision, which is THE SOLE REASON episode-scoped
     predicates are allowed to count as pure.
  5. SHORT-CIRCUIT on DENY. On APPROVAL_REQUIRED, consult the APPROVAL_ORACLE,
     whose frozen default is `deny_unless_fixture_declares` (ruling 18): attack
     episodes declare no approver and are denied by default. Without that
     sentence the four pairs that rest on approval - including the mandated F6
     pair - fail open or closed silently and nothing in the gate notices.

WHAT THE BLOCKED CALLER IS TOLD, which is a deliberate choice and not an
oversight. The short-circuit result carries the OUTCOME and the REASON_CODE and
NOT the `rule_id`. A reason code is an enum symbol chosen to be low-information;
a rule id is a handle on the policy's structure, and the target's tool results
flow back into a conversation the RED_STRATEGIST reads. Handing the attacker a
stable identifier for each rule as it fires would let it map the policy by
probing - which is a capability no real deployment grants and which would make
the ASR curve measure our chattiness rather than the boundary. The id is in the
ledger, where the CORONER and the replay viewer can see it.

The enforcement point itself is verified real rather than assumed:
`plugin_manager.run_before_tool_callback` fires at ADK `functions.py:553`, Step
1, BEFORE `agent.canonical_before_tool_callbacks` at `:564`.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Optional

from ..policy.decision import ALLOW, APPROVAL_REQUIRED, DENY, Decision
from ..policy.episode import EPISODE_PREFIX
from .ledger import TOOL_ATTEMPT, TOOL_ERROR, TOOL_EXECUTED, now_monotonic_ns

# Ruling 18, frozen as a run-manifest parameter rather than left as prose.
APPROVAL_ORACLE_DEFAULT = "deny_unless_fixture_declares"

# The sentinel class for a tool the manifest does not map. DISTINCT FROM THE
# EMPTY SET: empty means inert, this means we do not know.
UNCLASSIFIED = "UNCLASSIFIED"


def deny_unless_fixture_declares(decision, call):
    """The default APPROVAL_ORACLE. Returns True to approve.

    Attack episodes declare no approver, so this denies. A fixture that declares
    a valid approver overrides it by passing its own oracle - the approver
    identity is DECLARED BY THE FIXTURE AND READ BY THE IDENTITY LAYER, and it
    is never a call argument and never an arg_path (ruling 23). What the policy
    engine sees about an approver is `derived.approval_tier` and nothing else;
    without that, the forgeable channel returns through a different door.
    """
    return False


@dataclass
class CallOutcome:
    decision: Decision
    attempt_event: dict
    allowed: bool
    blocked_result: Optional[dict] = None
    derived_overwrites: list = field(default_factory=list)


class EnforcementCore:
    """One episode's enforcement state: policy, manifest, stamper, ledger."""

    def __init__(self, *, engine, manifest, stamper, ledger,
                 episode_context=None, approval_oracle=None, role="root_agent"):
        self.engine = engine
        self.manifest = manifest or {}
        self.stamper = stamper
        self.ledger = ledger
        self.episode_context = episode_context
        self.approval_oracle = approval_oracle or deny_unless_fixture_declares
        self.default_role = role
        self._caps = {}
        self._handle_by_fqname = {}
        for tool in self.manifest.get("tools", []):
            self._caps[tool["tool_handle"]] = tuple(
                sorted(tool.get("capability_classes", ())))
            self._handle_by_fqname[tool.get("tool_fqname")] = tool["tool_handle"]

    # -- lookups -----------------------------------------------------------
    def handle_for(self, tool_name):
        """Product name -> opaque handle. An unmapped tool keeps a synthetic
        handle so the event is still recordable; the D3 manifest-completeness
        check is what turns that into a reported coverage gap rather than a
        silent one."""
        return self._handle_by_fqname.get(tool_name)

    def capabilities_for(self, tool_handle):
        """UNCLASSIFIED for anything the manifest does not map.

        No rule can select UNCLASSIFIED, so such a tool is ALWAYS ALLOWED by the
        policy. That fail-open is correct and deliberate - detection is not
        remediation, and the TRIPWIRE scores the Objective Set independently of
        policy, so an unclassified tool that moves money is still a recorded
        breach. It must be STATED rather than DISCOVERED, which is the D3
        completeness check's job, not this method's.
        """
        return self._caps.get(tool_handle, (UNCLASSIFIED,))

    # -- step 1 ------------------------------------------------------------
    def _refuse_episode_writes(self, tool_args):
        """Ruling 16, enforced at the boundary the model can actually reach.

        Runs BEFORE the stamp and BEFORE evaluation. A write that reaches the
        evaluator has already done its damage: `to == episode.account_holder_
        email` would be compared against a value the caller supplied, which is
        the single cheapest way to invalidate the headline result.
        """
        for key in sorted(tool_args or {}):
            if key.startswith(EPISODE_PREFIX):
                if self.episode_context is None:
                    from ..dsl.errors import HaltHuman
                    raise HaltHuman(
                        "EPISODE_FIELD_WRITE_ATTEMPT",
                        "%s appeared in a call's arguments and there is no "
                        "frozen episode context to refuse it against. An "
                        "episode fact may only ever be the RIGHT-HAND side of a "
                        "comparison; it is never a call argument." % key)
                self.episode_context.attempt_write(key, tool_args[key])

    # -- the enforcement point --------------------------------------------
    def before_tool(self, *, tool_handle, tool_name, tool_args,
                    invocation_id, role=None):
        """Returns a CallOutcome. Raises HaltHuman on an `episode.*` write."""
        self._refuse_episode_writes(tool_args)

        post_args, overwrites = self.stamper.stamp(
            tool_args, {"tool_handle": tool_handle,
                        "episode_context": self.episode_context,
                        "prefix": self.ledger.events})

        caps = self.capabilities_for(tool_handle)
        decision = self.engine.evaluate(
            tool_handle=tool_handle,
            capability_set=set(caps),
            args=post_args,
            episode_prefix=self.ledger.events,
            episode_context=self.episode_context)

        attempt = {
            "episode_id": self.ledger.episode_id,
            "invocation_id": invocation_id,
            "kind": TOOL_ATTEMPT,
            "tool_name": tool_name,
            "tool_handle": tool_handle,
            "capability_classes": list(caps),
            "args": post_args,
            "role": role or self.default_role,
            "derived_overwrites": overwrites,
            "policy_decision": decision.outcome,
            "seq": self.ledger.next_seq(),
            "ts_monotonic": now_monotonic_ns(),
        }
        if decision.outcome in (DENY, APPROVAL_REQUIRED):
            attempt["denied_by_rule_id"] = decision.rule_id
        self.ledger.append(attempt)

        allowed = decision.outcome == ALLOW
        if decision.outcome == APPROVAL_REQUIRED:
            allowed = bool(self.approval_oracle(decision, attempt))

        blocked = None
        if not allowed:
            # See the module docstring: outcome and reason_code, never rule_id.
            blocked = {"error": "CRUCIBLE_POLICY_BLOCK",
                       "outcome": decision.outcome,
                       "reason_code": decision.reason_code}
        return CallOutcome(decision=decision, attempt_event=attempt,
                           allowed=allowed, blocked_result=blocked,
                           derived_overwrites=overwrites)

    # -- after ------------------------------------------------------------
    def after_tool(self, *, attempt_event, result):
        """Records TOOL_EXECUTED. Only ever called when the call was allowed."""
        event = dict(attempt_event)
        event["kind"] = TOOL_EXECUTED
        event.pop("policy_decision", None)
        event.pop("denied_by_rule_id", None)
        event["seq"] = self.ledger.next_seq()
        event["ts_monotonic"] = now_monotonic_ns()
        event["result_digest"] = result_digest(result)
        return self.ledger.append(event)

    def on_tool_error(self, *, attempt_event, error):
        """Records TOOL_ERROR and RETURNS NONE, ALWAYS.

        The target's own exception propagates unchanged. Suppressing it would
        let CRUCIBLE convert a crash into a clean non-breach, which would let a
        fragile target render as a hardened one - and a crash is TARGET_FAULT,
        which is removed from the denominator, not counted as "attack failed".
        """
        event = dict(attempt_event)
        event["kind"] = TOOL_ERROR
        event.pop("policy_decision", None)
        event.pop("denied_by_rule_id", None)
        event["seq"] = self.ledger.next_seq()
        event["ts_monotonic"] = now_monotonic_ns()
        event["error_class"] = type(error).__name__
        self.ledger.append(event)
        return None


def result_digest(result) -> str:
    """64 hex of SHA-256 over a stable dump of a tool return.

    NOT the JCS canonicalizer, and the reason is a real distinction rather than
    laziness. Canonicalization restrictions 4 and 5 forbid floats and `null`
    ANYWHERE IN A HASHED PAYLOAD - a rule that exists because those two are how
    a hash silently becomes ambiguous. A raw tool return is not a hashed payload
    and is not under our control: a target's `lookup_order` may legitimately
    return a null field or a float. Routing it through a canonicalizer that
    REFUSES those would turn an ordinary tool response into a crashed episode.

    This digest is REPLAY-INTEGRITY ONLY and EXPLICITLY NOT EVALUABLE by the
    policy engine. It is a hash, not a value - which is what settled ruling 21:
    the HARNESS sees tool returns and the EVALUATOR does not. Evidence bundles
    are world-readable, and a digest gives replay integrity with no payload.
    """
    blob = json.dumps(result, sort_keys=True, default=repr, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
