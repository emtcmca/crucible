"""crucible.conductor - the ROUND_CONDUCTOR. Owned by L5 LOOP.

PURE CODE, NO MODEL. It sequences components that have models; it holds none.
Every model-bearing collaborator arrives as a constructor argument, so "does the
conductor call a model" is answered by reading its `__init__`.

Everything it decides is arithmetic over recorded outcomes: whether the round was
dry, whether three dry rounds have passed, whether two rejections have stacked up,
whether the round cap is reached. Those are exactly the decisions that must be
reproducible from the evidence bundle, and a model in this seat would make the
shape of a run depend on a sample.
"""

from .conductor import (
    CONVERGENCE_DRY_ROUNDS,
    HALT_GATE_REJECTED_TWICE,
    REQUIRED_HASHES,
    CampaignResult,
    Conductor,
    RoundRecord,
)

__all__ = ["Conductor", "CampaignResult", "RoundRecord", "REQUIRED_HASHES",
           "CONVERGENCE_DRY_ROUNDS", "HALT_GATE_REJECTED_TWICE"]
