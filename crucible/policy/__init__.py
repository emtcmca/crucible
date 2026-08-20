"""crucible.policy - the POLICY_ENGINE and the episode freeze. Owned by L3.

CONVENTIONS 2.1 lists POLICY_ENGINE as "contains a model? no". That is not a
note about what we happened to build; it is the property the whole measurement
rests on, and it is why ruling 19 refuses any model-computed `derived.*` field.
A model-computed INPUT ARGUMENT launders a model into the pure-code path without
touching the component - the same argument that keeps the TRIPWIRE model-free.
"""

from .decision import (
    ALLOW,
    APPROVAL_REQUIRED,
    DENY,
    REASON_CONSTRAINT_VIOLATED,
    REASON_POLICY_DENY,
    Decision,
)
from .engine import PolicyEngine, evaluate
from .episode import EpisodeContext, HaltHuman

__all__ = [
    "Decision", "ALLOW", "DENY", "APPROVAL_REQUIRED",
    "REASON_POLICY_DENY", "REASON_CONSTRAINT_VIOLATED",
    "PolicyEngine", "evaluate",
    "EpisodeContext", "HaltHuman",
]
