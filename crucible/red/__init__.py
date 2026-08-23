"""crucible.red - the RED_STRATEGIST. Owned by L5 LOOP.

Contains a model (`gemini-3.6-flash`, `thinking_level: low`, CONVENTIONS 3.1).
~6 calls per round: moderate judgment, needs invention.

WHAT IT IS BLIND TO, AND WHY EACH ONE MATTERS
----------------------------------------------
* **The sealed family.** Real IAM: the red-team service account holds no GCS or
  BigQuery role and the sealed family exists only there. This is the ONE
  blindness in the build that may be called structural, and the 403 in
  `docs/proof/armorer-403.txt` is what proves it. Nothing in this package has a
  code path to the sealed set either, which is the cheapest half of the
  enforcement: nothing to leak.
* **The policy.** The RED_STRATEGIST attacks the TARGET, not the POLICY. Handing
  it the current rule set would turn the loop into a search for a gap in a
  document rather than a search for a capability path in an agent, and the ASR
  curve would then measure how well one model reverse-engineers another model's
  output. What it gets instead is what an attacker would actually have: which of
  its own attempts got through.
* **The benign fixtures.** Same reason the ARMORER is blind to them, from the
  other side.

WHAT IT DOES SEE: its own attack seeds, and per-family outcome COUNTS from
previous rounds. Counts, never contents - the same feedback discipline the
rejected-round path uses.
"""

from .red import (
    ATTACK_MODES,
    RED_MODEL,
    RED_THINKING_LEVEL,
    AttackSeed,
    RedStrategist,
    RoundFeedback,
)

__all__ = ["RedStrategist", "AttackSeed", "RoundFeedback", "RED_MODEL",
           "RED_THINKING_LEVEL", "ATTACK_MODES"]
