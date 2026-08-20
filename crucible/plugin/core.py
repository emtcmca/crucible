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
     episodes declare no approver and are denied by default.

The enforcement point itself is verified real rather than assumed:
`plugin_manager.run_before_tool_callback` fires at ADK `functions.py:553`, Step
1, BEFORE `agent.canonical_before_tool_callbacks` at `:564`.

NOT IMPLEMENTED YET - this is the stub the negative checks run RED against.
"""

# Ruling 18, frozen as a run-manifest parameter rather than left as prose.
APPROVAL_ORACLE_DEFAULT = "deny_unless_fixture_declares"


def deny_unless_fixture_declares(decision, call):
    """The default APPROVAL_ORACLE. Attack episodes declare no approver.

    Without this sentence the four pairs that rest on approval - including the
    mandated F6 pair - fail open or closed silently and nothing in the gate
    notices.
    """
    raise NotImplementedError("L3 WI-6: approval oracle not implemented yet")


class EnforcementCore:
    """One episode's enforcement state: policy, manifest, stamper, ledger."""

    def __init__(self, *, engine, manifest, stamper, ledger,
                 episode_context=None, approval_oracle=None, role="root_agent"):
        raise NotImplementedError("L3 WI-6: enforcement core not implemented yet")

    def before_tool(self, *, tool_handle, tool_name, tool_args,
                    invocation_id, role=None):
        """Returns `(decision, attempt_event)`. Raises HaltHuman on an
        `episode.*` write attempt."""
        raise NotImplementedError("L3 WI-6: enforcement core not implemented yet")

    def after_tool(self, *, attempt_event, result):
        """Records TOOL_EXECUTED. Only ever called when the call was allowed."""
        raise NotImplementedError("L3 WI-6: enforcement core not implemented yet")

    def on_tool_error(self, *, attempt_event, error):
        """Records TOOL_ERROR and RETURNS NONE, ALWAYS.

        The target's own exception propagates unchanged. Suppressing it would
        let CRUCIBLE convert a crash into a clean non-breach, which would let a
        fragile target render as a hardened one.
        """
        raise NotImplementedError("L3 WI-6: enforcement core not implemented yet")
