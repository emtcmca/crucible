"""crucible.gate - the promotion gate's write path. Pure code, no model access.
Owned by L1 FOUNDATION."""

from .promote import PromotionError, compute_policy_hash, object_name, promote

__all__ = ["promote", "PromotionError", "object_name", "compute_policy_hash"]
