"""crucible.warden - the REGRESSION_WARDEN. Owned by L4 ORACLE.

PURE CODE. CONTAINS NO MODEL - enforced by `crucible/tripwire/import_lint.py`,
which fails the build on an LLM client import anywhere under this package, and
proven by a test that plants such an import here and requires the lint to fail.
Not by this sentence.

The benign floor is computed by REPLAY of recorded v0 traces, never by re-running
live episodes (ruling 11). The shadow policy engine is INJECTED: L3 owns the real
one, and `reference_engine.py` is a bounded calibration stand-in so that six blind
lanes never have to wait on each other.
"""

from .lexicon_lint import LintResult, lexicon_lint
from .replay import (
    APPROVER_SENTINEL_NONE,
    Fixture,
    approval_oracle,
    load_attack_archive,
    load_benign_suite,
    replay_trace,
    surviving_episode,
)
from .warden import WardenConfig, WardenReport, run_warden
from . import reference_engine

__all__ = [
    "APPROVER_SENTINEL_NONE",
    "Fixture",
    "LintResult",
    "WardenConfig",
    "WardenReport",
    "approval_oracle",
    "lexicon_lint",
    "load_attack_archive",
    "load_benign_suite",
    "reference_engine",
    "replay_trace",
    "run_warden",
    "surviving_episode",
]
