"""crucible.harness - the layer between the lanes.

Created 2026-08-20 during W2 INTEGRATION I, for work that belongs to no lane
because it sits exactly on a seam between two. The `derived.*` arithmetic is the
first tenant: L3 owns the stamping discipline and left the computation
injectable on purpose, L2 declares the fields in Part B, and nothing computed
them. It surfaced the first time an episode ran end to end.

COORDINATOR-OWNED. A lane that needs something here asks rather than adding it,
for the same reason lanes never edit contracts/: a shared module that any lane
may extend is a shared module that drifts in six directions.
"""

from .derived import DerivedCompute
from .episode import EpisodeSealError, seal_episode

__all__ = ["DerivedCompute", "seal_episode", "EpisodeSealError"]
