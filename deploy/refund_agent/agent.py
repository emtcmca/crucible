"""Cloud Run deploy entry point for the target refund agent.

WHY THIS IS A SEPARATE FILE AND NOT A LINE IN `target/refund_agent/agent.py`.

`adk deploy cloud_run <AGENT_PATH>` requires a package whose `agent` module
exposes a module-level name `root_agent`. `target/refund_agent/agent.py` has no
such name - it has `build_agent()`, a function - and adding one there would
construct an `LlmAgent` at IMPORT time. Three things import that module without
wanting an agent: the D3 freeze, the capability manifest builder, and the test
suite. Import-time construction would make all three depend on ADK being
installed and on credentials resolving.

The stronger reason is the freeze. `target/refund_agent/freeze.py` hashes the
source of every module in `RUNTIME_MODULES`, and `agent.py` is one of them. After
the D3 freeze on 2026-08-22 that file is unchangeable without voiding the run, so
**deployment scaffolding must not live inside the thing being frozen.** A shim
that sits outside the freeze boundary can be edited on Day 9 when the deploy
needs a flag nobody anticipated; a line inside `agent.py` cannot.

This file therefore adds no behaviour. It calls the same `build_agent()` the
harness calls, so the deployed agent and the measured agent are the same object
built by the same code path. If that ever stops being true, the Cloud Run demo
stops being evidence about the thing we measured.
"""

from target.refund_agent.agent import build_agent

# Constructed at import, which is what ADK's loader expects. Safe HERE and not in
# the target package: nothing imports this module except the deploy.
root_agent = build_agent()
