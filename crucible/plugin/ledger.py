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
    anything the plugin says about itself.

NOT IMPLEMENTED YET - this is the stub the negative checks run RED against.
"""

TOOL_ATTEMPT = "TOOL_ATTEMPT"
TOOL_EXECUTED = "TOOL_EXECUTED"
TOOL_ERROR = "TOOL_ERROR"


class EpisodeLedger:
    """Append-only, in-memory, one per episode."""

    def __init__(self, episode_id: str):
        raise NotImplementedError("L3 WI-6: ledger not implemented yet")

    def next_seq(self) -> int:
        raise NotImplementedError("L3 WI-6: ledger not implemented yet")

    def append(self, event: dict) -> dict:
        raise NotImplementedError("L3 WI-6: ledger not implemented yet")

    @property
    def events(self) -> tuple:
        raise NotImplementedError("L3 WI-6: ledger not implemented yet")

    def executed(self) -> tuple:
        """Only TOOL_EXECUTED. What the TRIPWIRE scores on, and the answer to
        "did the blocked tool ever actually run"."""
        raise NotImplementedError("L3 WI-6: ledger not implemented yet")
