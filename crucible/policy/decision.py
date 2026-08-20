"""decision.py - C2. The POLICY_ENGINE's single output.

`contracts/decision.schema.json`. Three outcomes, and the schema enforces the
asymmetry between them: DENY and APPROVAL_REQUIRED must name a rule and a reason
code, and ALLOW must name NEITHER. Default is allow, so a call matching no rule
proceeds and there is nothing to cite.

THE TWO SYNTHESIZED REASON CODES, and this is a seam worth stating out loud.
`policy.ebnf` gives `deny` no reason_code - `action = "deny" | ...` carries no
argument - while C2 REQUIRES a reason_code on every DENY. Only
`require_approval(reason_code)` carries one in the grammar. The engine therefore
mints a fixed enum symbol for the two verbs that cannot carry one:

    deny            -> POLICY_DENY
    constrain_arg   -> CONSTRAINT_VIOLATED

They are constants, not free text, so the no-free-strings bar holds. Reported to
the coordinator as a contract gap rather than resolved by a lane, because a lane
does not edit `contracts/`.
"""

from dataclasses import dataclass
from typing import Optional

ALLOW = "ALLOW"
DENY = "DENY"
APPROVAL_REQUIRED = "APPROVAL_REQUIRED"

# See the module docstring. Fixed symbols, never free text.
REASON_POLICY_DENY = "POLICY_DENY"
REASON_CONSTRAINT_VIOLATED = "CONSTRAINT_VIOLATED"


@dataclass(frozen=True)
class Decision:
    outcome: str
    rule_id: Optional[str] = None
    reason_code: Optional[str] = None

    def to_dict(self) -> dict:
        """C2 wire form. ALLOW emits neither key - the schema's `not` clause
        rejects an ALLOW that names a rule, and a dict carrying `rule_id: None`
        would also fail rule 5 of canonicalization (null is forbidden)."""
        raise NotImplementedError("L3 WI-4: decision not implemented yet")

    @property
    def blocks(self) -> bool:
        """True when the tool must not run. APPROVAL_REQUIRED blocks at the
        policy layer; whether it ultimately proceeds is the APPROVAL_ORACLE's
        call, not the engine's."""
        raise NotImplementedError("L3 WI-4: decision not implemented yet")
