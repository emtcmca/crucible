"""ledger.py - the ordered ToolEvent record for one episode. C1.

`contracts/tool_event.schema.json`. This is the ground truth the breach
predicate is evaluated over, so two of its properties are not conveniences:

  * `seq` is MONOTONIC WITHIN THE EPISODE, and it is what lets an aggregate
    window replace a wall clock. KB3's "six transfers in ninety seconds" becomes
    "within one episode" and NO CLOCK ENTERS THE EVALUATOR. `ts_monotonic` is
    recorded for humans and for latency reporting and is never an evaluator
    input - a clock would make the evaluator impure and the TRIPWIRE's boolean
    irreproducible.
  * A DENY produces a TOOL_ATTEMPT WITH NO MATCHING TOOL_EXECUTED. That is
    exactly how enforcement is proven from the record alone, without trusting
    anything the plugin says about itself. It is also why a blocked call is not
    simply omitted: an absent record would be indistinguishable from a call the
    target never made.

APPEND-ONLY, AND THE APPEND VALIDATES. A ToolEvent that does not satisfy C1 is
refused at write time rather than discovered at analysis time, because by
analysis time the run is over and the episode cannot be re-run.
"""

import time

TOOL_ATTEMPT = "TOOL_ATTEMPT"
TOOL_EXECUTED = "TOOL_EXECUTED"
TOOL_ERROR = "TOOL_ERROR"

# C1's required list, read once here rather than restated at each call site.
REQUIRED_FIELDS = (
    "episode_id", "invocation_id", "kind", "tool_name", "tool_handle",
    "capability_classes", "args", "role", "derived_overwrites", "seq",
    "ts_monotonic",
)


class LedgerError(ValueError):
    """A refusal to record. Never a silent drop: an event we could not write is
    a hole in the ground truth, and a hole reads as "the target never did it"."""


class EpisodeLedger:
    """Append-only, in-memory, one per episode."""

    def __init__(self, episode_id: str):
        self.episode_id = episode_id
        self._events = []
        self._seq = 0

    def next_seq(self) -> int:
        s = self._seq
        self._seq += 1
        return s

    def append(self, event: dict) -> dict:
        missing = [f for f in REQUIRED_FIELDS if f not in event]
        if missing:
            raise LedgerError(
                "ToolEvent is missing %s. C1 requires all of %s; an event "
                "written without them is a hole in the record the TRIPWIRE "
                "scores on." % (", ".join(missing), ", ".join(REQUIRED_FIELDS)))
        if event["kind"] == TOOL_ATTEMPT and "policy_decision" not in event:
            raise LedgerError(
                "a TOOL_ATTEMPT must carry the policy decision that was reached "
                "for it - that pairing is what proves enforcement from the "
                "record alone")
        if event.get("policy_decision") in ("DENY", "APPROVAL_REQUIRED") \
                and "denied_by_rule_id" not in event:
            raise LedgerError(
                "a DENY or APPROVAL_REQUIRED must name the rule that produced "
                "it. A decision no rule is accountable for is not auditable.")
        if event["kind"] == TOOL_ERROR and "error_class" not in event:
            raise LedgerError("a TOOL_ERROR must carry error_class")
        self._events.append(event)
        return event

    @property
    def events(self) -> tuple:
        return tuple(self._events)

    def executed(self) -> tuple:
        """Only TOOL_EXECUTED. What the TRIPWIRE scores on, and the answer to
        "did the blocked tool ever actually run"."""
        return tuple(e for e in self._events if e["kind"] == TOOL_EXECUTED)

    def executed_handles(self) -> set:
        return {e["tool_handle"] for e in self.executed()}


def now_monotonic_ns() -> int:
    """Integer nanoseconds. RECORDED, NEVER EVALUATED - see the module
    docstring. It lives here rather than at the call sites so there is exactly
    one place a clock enters this package, and it is not the engine."""
    return time.monotonic_ns()
