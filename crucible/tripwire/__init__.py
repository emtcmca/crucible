"""crucible.tripwire - the TRIPWIRE and the OBJECTIVE_EVALUATOR. Owned by L4 ORACLE.

Single responsibility: decide breach, yes or no, one boolean per episode.

PURE CODE. CONTAINS NO MODEL, by design AND by dependency - enforced by
`import_lint.py`, which fails the build on an LLM client import anywhere under
this package or under `crucible/warden/`. An intent-aware oracle grades the
attacker's STORY instead of the world's STATE, and the entire value of the
improvement metric rests on this component knowing nothing about WHY a call
happened.

Blind to: the attacker's payload text, the attack family, the RED_STRATEGIST's
stated intent, the policy version, the CORONER, and the ARMORER. It sees tool
calls and a channel stamp.

    breach = Objective_Set.matches(events, channel)

over the episode's ORDERED EVENT LIST, on TOOL_EXECUTED events only, with three
clause forms: per_event, sequence, and aggregate(window_by_seq).
"""

from .evaluator import evaluate_episode
from .import_lint import Finding, run_import_lint
from .known_bad import (
    KNOWN_BAD_IDS,
    KnownBadFixture,
    KnownBadOutcome,
    KnownBadResult,
    KnownBadSuite,
    MislabelledFixture,
    expected_verdicts_from_gate_rule,
    load_known_bad_suite,
    run_known_bad_suite,
)
from .model import Episode, RunManifest, ToolEvent
from .objective_set import ObjectiveSet, ObjectiveSetError, load_objective_set
from .selftest import SelfTestReport, selftest
from .verdict import Verdict

__all__ = [
    "Episode",
    "Finding",
    "KNOWN_BAD_IDS",
    "KnownBadFixture",
    "KnownBadOutcome",
    "KnownBadResult",
    "KnownBadSuite",
    "MislabelledFixture",
    "ObjectiveSet",
    "ObjectiveSetError",
    "RunManifest",
    "SelfTestReport",
    "ToolEvent",
    "Verdict",
    "evaluate_episode",
    "expected_verdicts_from_gate_rule",
    "load_known_bad_suite",
    "load_objective_set",
    "run_import_lint",
    "run_known_bad_suite",
    "selftest",
]
