"""crucible.governor - the BUDGET_GOVERNOR. Owned by L5 LOOP.

Pure code, no model. Holds the spend cap, the token ceiling, the round cap and
the call cap, and answers one question before every billable call: may this fire.

IT ANSWERS. IT DOES NOT RAISE. An abort that arrives as a traceback is not a
round outcome - it cannot be written to the ledger, it cannot be scored, and the
run ends looking like a crash rather than like a decision. CONVENTIONS 2.4 draws
the same line for `INVALID` versus `FAILED`: the absence of a measurement is
itself a thing that must be recorded.
"""

from .governor import (
    Budget,
    BudgetGovernor,
    GovernorEvent,
    GovernorVerdict,
    HALT_BUDGET_EXHAUSTED,
    HALT_CALL_CAP,
    HALT_ROUND_CAP,
    HALT_TOKEN_CEILING,
)

__all__ = [
    "Budget", "BudgetGovernor", "GovernorEvent", "GovernorVerdict",
    "HALT_BUDGET_EXHAUSTED", "HALT_TOKEN_CEILING", "HALT_ROUND_CAP",
    "HALT_CALL_CAP",
]
