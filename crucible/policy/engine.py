"""engine.py - the POLICY_ENGINE. Pure code, no model, no I/O, no clock.

    evaluate(tool_handle, capability_set, args, policy, episode_prefix) -> Decision

FIVE arguments. `role` was removed from this signature by ruling 25: no rule may
bind to it, so passing it would leave an input in the signature that nothing
reads - and an input nobody reads is an input nobody audits.

The four steps, from `contracts/decision.schema.json` `$defs/EVALUATION_CONTRACT`:

  STEP 1  MATCH, BY MEMBERSHIP, NEVER BY SET EQUALITY.
          A tool carries a SET. A rule names ONE class. The rule matches when
          its class is a MEMBER of the call's set. Under set equality a rule
          binding CAP_EXTERNAL_COMMS silently stops firing on exactly the tools
          that carry it alongside CAP_READS_PII - which are the tools that
          matter most - the F4 destination rule never fires on the tools it
          exists for, and THE SEALED RESULT READS "did not generalize". That is
          a real number produced by a matcher bug, which is the worst kind.

  STEP 2  FILTER on the `when`. AN UNEVALUABLE CLAUSE RETAINS THE RULE.
          Fail closed: an absent, null, or wrong-typed argument means we do not
          know that the rule is inapplicable, and "we do not know" must not read
          as "allow". This is why predicate evaluation is TRI-STATE and not
          boolean - a boolean forces unevaluable to collapse into one of the two
          answers, and it always collapses into the wrong one.

  STEP 3  RESOLVE BY STRICTNESS, NEVER BY FILE ORDER.
          deny > require_approval > constrain_arg > implicit ALLOW.
          Ties within a class resolve by LOWEST rule_id. File order is never
          consulted, so a patch cannot change behaviour by insertion position -
          which is what makes `rules` sortable by rule_id without loss, which is
          in turn what makes the canonical form unambiguous.

  STEP 4  RETURN exactly one Decision naming the rule that produced it.

  DEFAULT IS ALLOW. The instrument is SUBTRACTIVE ONLY. There is no `allow`
  verb, so no sequence of patches can widen the target's blast radius; the worst
  a compromised or confused ARMORER can do is over-block, and the benign floor
  is what catches that.

TWO PREFIX SEMANTICS THAT SILENTLY DISABLE THE PREDICATE THEY BELONG TO:

  * `preceded_by` and `episode_sum` read ONLY events that actually happened -
    `kind == TOOL_EXECUTED` and a policy decision of ALLOW. Otherwise AN
    ATTACKER SATISFIES `preceded_by` FOR FREE WITH ONE BLOCKED CALL: make the
    PII read, let the policy deny it, and the composition rule downstream now
    believes the read happened.
  * `episode_sum` INCLUDES THE PENDING CALL. Otherwise the call that first
    crosses the threshold is the one that executes, and the rule only ever fires
    one call late - which is exactly one call too late for F7.

NOT IMPLEMENTED YET - this is the stub the negative checks run RED against.
"""

from .decision import Decision  # noqa: F401

# Strictness, ascending. Resolution takes the maximum; ties break on lowest
# rule_id. This tuple is the ONLY place order is encoded - there is deliberately
# no path by which array position could reach a comparison.
STRICTNESS = {"constrain_arg": 1, "require_approval": 2, "deny": 3}

# Tri-state predicate result. UNEVALUABLE is not a third truth value in the
# logic - it is a statement about our knowledge, and it retains the rule.
TRUE, FALSE, UNEVALUABLE = "TRUE", "FALSE", "UNEVALUABLE"


class PolicyEngine:
    """Holds one policy. `evaluate` is a pure function of its arguments."""

    def __init__(self, policy):
        """`policy` is a full policy document or a bare `hashed_payload`."""
        raise NotImplementedError("L3 WI-4: engine not implemented yet")

    def evaluate(self, *, tool_handle, capability_set, args,
                 episode_prefix=(), episode_context=None) -> Decision:
        raise NotImplementedError("L3 WI-4: engine not implemented yet")

    def visible_prefix(self, episode_prefix):
        """The events `preceded_by` and `episode_sum` are allowed to see."""
        raise NotImplementedError("L3 WI-4: engine not implemented yet")


def evaluate(tool_handle, capability_set, args, policy, episode_prefix=(),
             episode_context=None) -> Decision:
    """The five-argument form C2 names. Positional, in the contract's order."""
    raise NotImplementedError("L3 WI-4: engine not implemented yet")
