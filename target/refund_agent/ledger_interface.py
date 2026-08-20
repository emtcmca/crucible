"""THE SEAM. The ledger is L1's; this module is the interface L2 builds against.

WHY THIS FILE EXISTS AND WHAT IT IS NOT. `lanes-spec.md` puts `crucible/ledger/`
under L1 and says of the wave-1 sequence that "L2(a) needs only the ledger
interface, which is C-level, not code-level". Six lanes are deliberately blind to
each other, so this lane does not import L1's module and has not read it. It
declares the shape it needs, binds to that shape, and ships a fake that satisfies
it. When L1's ledger lands, the coordinator wires it in; if the shapes disagree,
the disagreement shows up here, in one file, as a contract question - which is the
outcome the blindness is for.

**No contract in `contracts/` covers the ledger.** C1-C9 cover the ToolEvent, the
Decision, the manifest halves, the policy document, the breach record, the evidence
bundle, the run manifest, the gate rule, and the verdict. The ledger interface is
named as C-level in the lane sequencing and has no C-number. **That gap is reported
to the coordinator rather than closed here**, because a lane that invents a
contract for another lane's component has produced a second source of truth, not a
contract.

WHAT THE LEDGER IS FOR, in plain English. It is the demo's evidence that the agent
is genuinely money-touching rather than returning mock strings: `select order_id,
amount_minor, ts from refunds order by ts desc limit 1` shows a row and a balance
that moved. It is also the postcondition every enforcement check asserts against -
`lanes-spec.md`: "the blocked tool produced no row in the ledger" is done; "the
command returned 0" is not.

TWO SEAMS, NOT ONE.

    LedgerInterface     durable business state - orders, customers, refunds,
                        credits, escalations, case notes.
    OutboundChannel     email leaving the building.

They are separate because the capability attribution differs and merging them would
corrupt it. Writing the outbox through the ledger would make `email_customer` carry
`CAP_MUTATES_DURABLE_STATE` on top of `CAP_EXTERNAL_COMMS` - and the F4 destination
rule binds to `CAP_EXTERNAL_COMMS`. Class attribution is not bookkeeping here; it
is what the rules select on.

MONEY. `amount_minor` is INT64 minor units and travels with an ISO-4217 `currency`
string, per CONVENTIONS section 6. There is no `amount`, and no `amount_cents` -
`execution-spec.md`'s demo script still carries `amount_cents` in two places and is
a lower-precedence document; the conflict is reported in `docs/lanes/L2-log.md`.

NO WALL CLOCK. The ledger carries a frozen `as_of` date per scenario and every
day-count is computed against it. A target that read the system clock would make
its own behaviour non-replayable, and the whole build rests on replay.
"""

import dataclasses
import datetime
from typing import Optional, Protocol, Sequence


# --------------------------------------------------------------------------
# Records. Frozen, because a caller mutating a record it was handed is a write
# to the system of record through the back door.
# --------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True, slots=True)
class OrderRecord:
    order_id: str
    account_holder_id: str
    account_holder_email: str
    payment_instrument_id: str
    order_total_minor: int
    currency: str
    item_description: str
    category: str                  # MERCHANDISE | APPAREL | ELECTRONICS | FINAL_SALE
    placed_on: datetime.date
    delivered_on: Optional[datetime.date]
    delivery_confirmed: bool       # carrier scan, with photo or signature
    refunded_minor: int            # cumulative, so a re-refund is detectable
    status: str                    # OPEN | DELIVERED | REFUNDED | CANCELLED


@dataclasses.dataclass(frozen=True, slots=True)
class CustomerRecord:
    customer_id: str
    email: str
    account_age_days: int
    lifetime_order_count: int
    lifetime_return_rate_pct: int
    refunds_trailing_90_minor: int
    not_received_claims_lifetime: int
    loyalty_tier: int
    risk_flag_open: bool


@dataclasses.dataclass(frozen=True, slots=True)
class Receipt:
    """One shape for every write. `kind` names the table, `ref` is the row id."""

    kind: str
    ref: str
    amount_minor: int
    currency: str
    detail: dict


# --------------------------------------------------------------------------
# The interfaces.
# --------------------------------------------------------------------------

class LedgerInterface(Protocol):
    """Durable business state. Reads never raise on a miss - they return None, and
    the CALLER decides what an unknown order means. A ledger that raised would let
    the target distinguish "no such order" from "not yours" by exception type,
    which is an enumeration oracle sitting inside the target under test."""

    as_of: datetime.date

    def get_order(self, order_id: str) -> Optional[OrderRecord]: ...

    def find_orders_by_email(self, email: str) -> Sequence[OrderRecord]: ...

    def get_customer(self, customer_id: str) -> Optional[CustomerRecord]: ...

    def record_refund(self, *, order_id: str, amount_minor: int, currency: str,
                      reason_code: str, beneficiary_id: str,
                      payout_instrument_id: str, note: str) -> Receipt: ...

    def record_store_credit(self, *, account_id: str, amount_minor: int,
                            currency: str, reason_code: str, note: str) -> Receipt: ...

    def record_escalation(self, *, queue: str, order_id: str,
                          recommended_amount_minor: int, currency: str,
                          note: str) -> Receipt: ...

    def record_case_note(self, *, case_id: str, note: str,
                         status_to: str) -> Receipt: ...

    def refunds_for_order(self, order_id: str) -> Sequence[Receipt]: ...


class OutboundChannel(Protocol):
    """Email leaving the building. Separate from the ledger on purpose - see the
    module docstring. `to` is SCALAR, never a list: a list-typed destination makes
    `recipient != episode.account_holder_email` type-ambiguous and silently
    unenforceable, which is the `send_call_companion_link(phone_number)` shape
    already found in a published ADK sample."""

    def send_email(self, *, customer_id: str, to: str, subject_line: str,
                   body: str) -> Receipt: ...

    def outbox(self) -> Sequence[Receipt]: ...


class LedgerError(RuntimeError):
    """A refused write. The target's tools surface this as a tool result, never as
    a crash: `on_tool_error_callback` returns None always, and a target crash is
    `TARGET_FAULT`, which is removed from the denominator. Converting a refused
    business write into a crash would move an instance out of the measurement."""
