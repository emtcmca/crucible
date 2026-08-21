"""governor.py - the BUDGET_GOVERNOR. Pure code, no model.

Four ceilings, four refusal codes:

    usd_cap     $160     CONVENTIONS section 4. A CAP, NOT AN ALERT. Eric holds
                         further credit, and the cap stays where it is precisely
                         so an overrun is a DELIBERATE DECISION RATHER THAN A
                         DISCOVERY.
    token_cap   40M      cut list auto-triggers at 32M
    round_cap   6        ruling 10, raised from 4. At a cap of 4 with
                         three-consecutive-dry convergence only round one could
                         be productive - a formality, not a criterion.
    call_cap    -        a belt-and-braces stop on a loop that is spinning
                         cheaply. Cost is not the only way a run goes wrong.

IT ANSWERS, IT DOES NOT RAISE
-----------------------------
`authorize` returns a `GovernorVerdict`. It never raises, and
`crucible/governor/strawman.py` keeps the version that does, permanently, as the
proof that the test can fail.

The reason is not style. The abort is a RESULT OF THE RUN: it belongs in the
round outcome, in the RUN LEDGER and in the evidence bundle, because "stopped at
the spend cap after three rounds" and "converged after three rounds" produce
identical artifacts if the first one leaves as a traceback. CONVENTIONS 2.4 draws
the same line between INVALID and FAILED - the absence of a measurement is itself
something that has to be recorded.

THE ESTIMATE IS CHECKED BEFORE THE CALL, THE ACTUAL IS RECORDED AFTER
---------------------------------------------------------------------
`authorize(role, estimated_usd)` then `record(role, usd, tokens)`. Two methods
rather than one because a model call's real cost is not known until it returns,
and a governor that only counted actuals would authorize the call that breaks the
cap. The estimate is deliberately pessimistic; the spike measured the ARMORER at
$0.0146/call at `thinking_level: medium`, with THINKING TOKENS RUNNING 48x OUTPUT
TOKENS and billing at the output rate. Thinking tokens are the cost, not the
answer.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

HALT_BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
HALT_TOKEN_CEILING = "TOKEN_CEILING"
HALT_ROUND_CAP = "ROUND_CAP"
HALT_CALL_CAP = "CALL_CAP"

# CONVENTIONS section 4. Named here so a caller that wants the real thing does
# not retype them - a second copy of a frozen number is a second source of truth.
SPEND_CAP_USD = 160.00
TOKEN_CEILING = 40_000_000
CUT_LIST_TRIGGER_TOKENS = 32_000_000
ROUND_CAP = 6


@dataclass(frozen=True)
class Budget:
    """The four ceilings. Frozen: a budget that can be edited mid-run is not a
    budget, and the whole value of the cap is that raising it is an act."""
    usd_cap: float = SPEND_CAP_USD
    token_cap: int = TOKEN_CEILING
    round_cap: int = ROUND_CAP
    call_cap: int = 400


@dataclass(frozen=True)
class GovernorVerdict:
    """The answer. Data, because it has to reach the ledger.

    `allowed` is the decision; `code` is None on an allow and one of the four
    HALT_* constants on a refusal. FOUR CEILINGS, FOUR CODES: one generic HALT
    would leave the evidence bundle unable to say which limit ended the run,
    which is the same defect as not recording it at all.
    """
    allowed: bool
    code: Optional[str] = None
    detail: str = ""
    spent_usd: float = 0.0
    tokens_used: int = 0
    rounds_opened: int = 0
    calls_made: int = 0


@dataclass(frozen=True)
class GovernorEvent:
    """One line of the governor's own log. `kind` is AUTHORIZE, CHARGE, ROUND or
    ABORT."""
    kind: str
    role: str
    code: Optional[str] = None
    usd: float = 0.0
    tokens: int = 0
    detail: str = ""


@dataclass
class BudgetGovernor:
    budget: Budget = field(default_factory=Budget)
    spent_usd: float = 0.0
    tokens_used: int = 0
    calls_made: int = 0
    rounds_opened: int = 0
    events: List[GovernorEvent] = field(default_factory=list)

    def __init__(self, budget=None, *, spent_usd=0.0, tokens_used=0):
        self.budget = budget or Budget()
        self.spent_usd = float(spent_usd)
        self.tokens_used = int(tokens_used)
        self.calls_made = 0
        self.rounds_opened = 0
        self.events = []

    # -- the state a verdict carries --------------------------------------
    def _snapshot(self):
        return dict(spent_usd=round(self.spent_usd, 6),
                    tokens_used=self.tokens_used,
                    rounds_opened=self.rounds_opened,
                    calls_made=self.calls_made)

    def _refuse(self, role, code, detail):
        verdict = GovernorVerdict(allowed=False, code=code, detail=detail,
                                  **self._snapshot())
        self.events.append(GovernorEvent(kind="ABORT", role=role, code=code,
                                         detail=detail))
        return verdict

    def _allow(self, role, kind, usd=0.0, tokens=0):
        verdict = GovernorVerdict(allowed=True, **self._snapshot())
        self.events.append(GovernorEvent(kind=kind, role=role, usd=usd,
                                         tokens=tokens))
        return verdict

    # -- the two entry points ---------------------------------------------
    def authorize(self, role, estimated_usd, estimated_tokens=0) -> GovernorVerdict:
        """May this billable call fire? Returns; never raises."""
        estimated_usd = float(estimated_usd)
        estimated_tokens = int(estimated_tokens)

        if self.calls_made + 1 > self.budget.call_cap:
            return self._refuse(
                role, HALT_CALL_CAP,
                "call %d would exceed the cap of %d"
                % (self.calls_made + 1, self.budget.call_cap))
        if self.spent_usd + estimated_usd > self.budget.usd_cap:
            return self._refuse(
                role, HALT_BUDGET_EXHAUSTED,
                "$%.4f spent plus an estimated $%.4f exceeds the $%.2f cap"
                % (self.spent_usd, estimated_usd, self.budget.usd_cap))
        if self.tokens_used + estimated_tokens > self.budget.token_cap:
            return self._refuse(
                role, HALT_TOKEN_CEILING,
                "%d tokens plus an estimated %d exceeds the %d ceiling"
                % (self.tokens_used, estimated_tokens, self.budget.token_cap))
        return self._allow(role, "AUTHORIZE", estimated_usd, estimated_tokens)

    def record(self, role, usd, tokens=0) -> None:
        """Book the actual cost of a call that has returned."""
        self.spent_usd += float(usd)
        self.tokens_used += int(tokens)
        self.calls_made += 1
        self.events.append(GovernorEvent(kind="CHARGE", role=role,
                                         usd=float(usd), tokens=int(tokens)))

    def open_round(self, role="ROUND_CONDUCTOR") -> GovernorVerdict:
        """May another round start? The round cap is SIX (ruling 10)."""
        if self.rounds_opened + 1 > self.budget.round_cap:
            return self._refuse(
                role, HALT_ROUND_CAP,
                "round %d would exceed the cap of %d"
                % (self.rounds_opened + 1, self.budget.round_cap))
        self.rounds_opened += 1
        return self._allow(role, "ROUND")

    # -- reporting ---------------------------------------------------------
    @property
    def cut_list_triggered(self) -> bool:
        """CONVENTIONS section 4: the cut list auto-triggers at 32M tokens, which
        is BELOW the 40M ceiling on purpose. A trigger that fires at the ceiling
        fires when it is already too late to cut anything."""
        return self.tokens_used >= CUT_LIST_TRIGGER_TOKENS

    def halt(self) -> Optional[Tuple[str, str]]:
        """The first refusal, or None. This is what the round outcome carries."""
        for event in self.events:
            if event.kind == "ABORT":
                return event.code, event.detail
        return None

    def summary(self) -> dict:
        return dict(self._snapshot(),
                    usd_cap=self.budget.usd_cap,
                    token_cap=self.budget.token_cap,
                    round_cap=self.budget.round_cap,
                    call_cap=self.budget.call_cap,
                    cut_list_triggered=self.cut_list_triggered,
                    aborts=[e.code for e in self.events if e.kind == "ABORT"])
