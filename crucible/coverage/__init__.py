"""crucible.coverage - how much of the definition of breach anything touches.

    python -m crucible.coverage
    python -m crucible.coverage --bundle evidence/<run>/bundle.json
    python -m crucible.coverage --json docs/proof/clause-coverage.json

The Objective Set IS the definition of breach. A breach rate is therefore a
measurement of whatever share of it the traces managed to touch, and a reader
handed the rate will assume the share was all of it. This module is the
instrument that says which share it actually was, per source, before a run
exists as well as after one.
"""

from .matrix import (
    CONTEXT_FIELD_MISSING,
    DARK_STATES,
    FIRED,
    NEVER_TRUE,
    PATH_NEVER_PRESENT,
    UNREACHED,
    CoverageMatrix,
    build_matrix,
    load_objective_set,
    probe_episode,
    target_tool_names,
)
from .render import render
from .sources import OFFLINE_SOURCES, SourceEpisode, SourceUnavailable, evidence_bundle

__all__ = [
    "CONTEXT_FIELD_MISSING", "DARK_STATES", "FIRED", "NEVER_TRUE",
    "PATH_NEVER_PRESENT", "UNREACHED", "CoverageMatrix", "OFFLINE_SOURCES",
    "SourceEpisode", "SourceUnavailable", "build_matrix", "evidence_bundle",
    "load_objective_set", "probe_episode", "render", "target_tool_names",
]
