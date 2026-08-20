"""decision.py - C2. The POLICY_ENGINE's single output.

`contracts/decision.schema.json`. Three outcomes, and the schema enforces the
asymmetry between them: DENY and APPROVAL_REQUIRED must name a rule and a reason
code, and ALLOW must name NEITHER. Default is allow, so a call matching no rule
proceeds and there is nothing to cite.

THE THREE SYNTHESIZED REASON CODES, and this is a seam worth stating out loud
rather than burying.

`policy.ebnf` gives `deny` no reason_code - `action = "deny" | ...` carries no
argument - while C2 REQUIRES a reason_code on every DENY. Only
`require_approval(reason_code)` carries one in the grammar, and the C4 golden
fixture's own `require_approval` rule has no `action` block at all, so it
carries none either. The engine therefore mints fixed enum symbols:

    deny                                     -> POLICY_DENY
    constrain_arg, violated or unevaluable   -> CONSTRAINT_VIOLATED
    require_approval with no declared code   -> APPROVAL_REQUIRED

They are CONSTANTS, not free text, so the no-free-strings bar holds and nothing
here can carry prose. Reported to the coordinator as a contract gap rather than
resolved by a lane, because a lane does not edit `contracts/`.
"""

from dataclasses import dataclass
from typing import Optional

ALLOW = "ALLOW"
DENY = "DENY"
APPROVAL_REQUIRED = "APPROVAL_REQUIRED"

# See the module docstring. Fixed symbols, never free text.
REASON_POLICY_DENY = "POLICY_DENY"
REASON_CONSTRAINT_VIOLATED = "CONSTRAINT_VIOLATED"
REASON_APPROVAL_REQUIRED = "APPROVAL_REQUIRED"


@dataclass(frozen=True)
class Decision:
    outcome: str
    rule_id: Optional[str] = None
    reason_code: Optional[str] = None

    def to_dict(self) -> dict:
        """C2 wire form.

        ALLOW emits neither key. Two reasons, and both are contract-level: the
        schema's `not` clause rejects an ALLOW that names a rule, and a dict
        carrying `rule_id: None` would violate canonicalization rule 5 -
        `null` is forbidden, an absent fact is an absent key.
        """
        if self.outcome == ALLOW:
            return {"outcome": ALLOW}
        return {"outcome": self.outcome, "rule_id": self.rule_id,
                "reason_code": self.reason_code}

    @property
    def blocks(self) -> bool:
        """True when the tool must not run.

        APPROVAL_REQUIRED blocks AT THE POLICY LAYER. Whether the call
        ultimately proceeds is the APPROVAL_ORACLE's call, not the engine's -
        ruling 2 made `escalate` a hand-off to a different authority rather than
        a refusal, and collapsing the two here would make every benign fixture
        that legitimately routes to approval fail.
        """
        return self.outcome != ALLOW
