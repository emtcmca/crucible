"""conftest.py - the shared test helpers, and the one that must not need a shell.

WHY THIS FILE EXISTS
====================
`tests/test_holdout_touch.py` injects every collaborator it has: the log
reader, the project-policy fetch, the clock, the sleep. Not one of its 69 tests
needs a configured machine. It still could not be COLLECTED on a Windows host
without a working Git Bash, because its line 67 called
`infra.verify_iam.load_env`, and that function runs

    bash -c '. <repo>/scripts/gcp-env.sh && env | grep -E "^(CRUCIBLE_|SA_|SUFFIX)"'

at MODULE IMPORT TIME - during pytest collection, before a single test runs.

REPRODUCED 2026-08-29, deterministically. Every PATH directory holding
`bash.exe` was removed and the file was collected:

    pytest tests/test_holdout_touch.py --collect-only -q
    tests\\test_holdout_touch.py:67: in <module>
        ENV = verify_iam.load_env(str(REPO))
    infra\\verify_iam.py:72: in load_env
        out = subprocess.run(
    E   FileNotFoundError: [WinError 2] The system cannot find the file specified

An independent reviewer hit the same line a different way: Git Bash present but
unable to create its signal pipe, so the fork failed rather than the lookup.
Missing bash and broken bash are the same dependency, and a test that injects
its seams has no business having that dependency at all. THE SEAM WAS IN THE
WRONG PLACE: the names were reachable only through a function that shells out.

WHAT THIS DOES INSTEAD, AND WHY IT IS NOT A SECOND SOURCE OF TRUTH
=================================================================
`load_gcp_env` reads `scripts/gcp-env.sh` directly, in pure Python, and expands
its `${VAR}` references itself. **The names still come from that one file.** The
property `scripts/gcp-env.sh` exists to hold - one place for a bucket name, so a
retyped literal cannot produce an unevaluable gate - is untouched: nothing here
types `crucible-sealed-x7`, and `test_the_filter_is_built_from_gcp_env_and_not_
from_retyped_literals` still fails red if anything ever does.

What IS duplicated is the PARSING, and a second parser can disagree with bash
about what the file says. That is guarded, not assumed, and in two directions:

  1. **A partial parse raises.** `require=` names the keys the caller depends on
     and a missing one is a `GcpEnvError`, never a `KeyError` three frames later
     and never a silently absent name that compiles into a filter matching
     nothing. An unexpandable `${VAR}` raises for the same reason: an empty
     expansion would produce `gs://crucible-sealed-` and a query that returns
     zero, and zero is exactly what this repository's signature defect looks
     like.
  2. **A differential test in `tests/test_holdout_touch.py` runs BOTH readers and
     asserts they agree**, wherever bash can actually run. On a host where bash
     is missing or cannot fork, that one test SKIPS with a reason naming bash -
     and it is the only thing that skips. Collection, and the other 69 tests,
     no longer depend on the shell either way.

This does NOT fix the other four test modules that reach `load_env` during
collection (`test_real_gate.py`, `test_campaign_gate_wiring.py`,
`test_closure_gate.py`, `test_g4.py`), nor the production call sites in
`crucible/transfer/gcs_reader.py` and `crucible/conductor/real_gate.py`. The fix
that covers all of them is a shell-free `load_env` in `infra/verify_iam.py`,
which is outside this change's ownership and is reported rather than made.
"""

import os
import sys


# THE PARSER MOVED TO PRODUCTION. It lives at `infra/gcp_env.py` now, because
# the shell dependency it replaces was never only a test problem: `RealGate`
# reached the same call, so the gate could not be built on a host without bash.
# Re-exported here rather than re-implemented - a second copy would be a second
# parser, which is the thing this whole change was about.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infra.gcp_env import (GcpEnvError, load_gcp_env, repo_root,  # noqa: E402,F401
                           _expand, _unquote, _EXPORT, _KEPT, _REF)
