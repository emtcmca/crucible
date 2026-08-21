"""crucible.replay - the offline replay viewer. Owned by L6 EVIDENCE.

The judge-reproduction path. The repository is PUBLIC, so a stranger clones it
and replays a run's evidence bundle with no credentials, no network, and no GCP
project. That is why the demo can say "the bundles are in the repo, replay them
yourself" instead of running a multi-minute live loop on camera.

Two properties, and this package's tests exist to make both falsifiable:

  IT NEEDS NOTHING.   `offline_lint` refuses network transports, cloud SDKs,
                      `subprocess`, and any read of the process environment,
                      by AST walk over every module here.
  IT REFUSES.         `integrity` decides whether a bundle is evidence, and
                      `bundle.read_bundle` raises rather than render a blank
                      where a hash belongs.
"""

from .bundle import (
    SIDECAR_SUFFIX,
    read_bundle,
    read_bundle_bytes,
    write_bundle,
)
from .integrity import (
    BundleRejected,
    CROSS_CHECKED,
    Defect,
    IntegrityReport,
    PRESENT,
    RECOMPUTED,
    Row,
    c6_validator,
    verify_bundle,
)
from .offline_lint import (
    Finding,
    run_offline_lint,
    scan_offline_source,
)

__all__ = [
    "BundleRejected", "Defect", "Finding", "IntegrityReport", "Row",
    "CROSS_CHECKED", "PRESENT", "RECOMPUTED", "SIDECAR_SUFFIX",
    "c6_validator", "read_bundle", "read_bundle_bytes", "run_offline_lint",
    "scan_offline_source", "verify_bundle", "write_bundle",
]
