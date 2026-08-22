"""real_target.py - drives the REAL target/refund_agent as a live ADK agent.

REPLACES `stand_in_target` (see `campaign.py`'s header). The stand-in emits one
money-moving call per attack and asks only "does the policy stop me" - it never
touches a model, never touches `target/refund_agent`, and measures nothing about
an agent's susceptibility to persuasion, which is the entire thing the real
target exists to measure. This module drives the actual agent instead:

    attack["instruction"]  ->  a real google.adk.runners.Runner
                            ->  target/refund_agent.agent.build_agent() (the
                                real LlmAgent, 8 tools, refund_policy.md
                                verbatim as its instruction)
                            ->  CruciblePlugin, attached via App(plugins=[...]),
                                enforcing `policy` through EnforcementCore
                            ->  the tools, bound to a FRESH
                                SimulatedSystemOfRecord per episode
                            ->  crucible.harness.episode.seal_episode, so the
                                result is SCOREABLE by the real TRIPWIRE
                                (`crucible/tripwire/evaluator.py`), not the
                                unsealed 3-key shape `stand_in_target` returns.

RETURN SHAPE - CHANGED FROM THE ORIGINAL BRIEF, PER COORDINATOR 2026-08-21
----------------------------------------------------------------------------
The first draft of this file matched `stand_in_target`'s bare
`{"episode_id", "outcome", "events"}` shape. The real TRIPWIRE adapter rules
through `crucible.tripwire.evaluator.evaluate_episode`, which enforces G1(b)
BEFORE scoring anything: an episode missing `objective_set_hash`,
`manifest_hash` or `derived_schema_hash` is unscoreable (INVALID), never clean
- `crucible/harness/episode.py::seal_episode`'s own words. `campaign.py` never
calls `seal_episode`, so sealing is the target adapter's job. This file now
returns whatever `seal_episode` returns, unmodified: `episode_id`, `events`,
`objective_set_hash`, `manifest_hash`, `derived_schema_hash`, `policy_version`,
`policy_hash`, `episode_frozen_context`, and `outcome` (`"completed"` or
`"TARGET_FAULT"`) - see "THE `outcome`/`target_fault` GAP" below for why
`outcome` alone is the canonical key and no separate `target_fault` key is
stamped on the episode.

`build_real_target(...)` now takes `run_manifest` - a
`crucible.tripwire.model.RunManifest`-shaped object (`.objective_set_hash`,
`.manifest_hash`, `.derived_schema_hash`, `.policy_version`, `.policy_hash`).
**This adapter never constructs or hardcodes a hash.** It is handed the run
manifest and copies from it, exactly as `seal_episode`'s own docstring requires
("recomputing them at seal time would let an episode be stamped with the hash
of whatever is on disk NOW rather than what was in force when the calls were
made"). There is deliberately no module-level `real_target = build_real_target()`
convenience instance any more - constructing one with no `run_manifest` would
either raise at import time or silently produce unscoreable episodes, and
this file will do neither. The coordinator constructs
`build_real_target(run_manifest=rm, ...)` at wiring time.

THREE INTEGRATION DEFECTS FOUND WHILE WIRING THIS. THE FIRST TWO ARE NOW FIXED
AT THE SOURCE (`crucible/harness/episode.py`, 2026-08-22) AND THIS FILE NO
LONGER WORKS AROUND THEM - see that module's docstring ("THE `outcome` KEY")
for the fix and which committed artifact decided the canonical key/spelling
for each. The third remains a live gap in a file this lane does not own.

1. THE `outcome`/`target_fault` GAP - FIXED AT SOURCE. `seal_episode` now
   writes `raw["outcome"]` itself (`"TARGET_FAULT"` or `"completed"`), so
   `evaluate_episode` and every `strawman.py` verdict path see the same key
   the episode was actually sealed with. This adapter no longer stamps
   `raw["outcome"]` after the fact - `seal_episode`'s return value is used
   as-is. `seal_episode` no longer writes an episode-level `target_fault`
   boolean at all: no golden trace or contract ever required one (it is a
   field on `Verdict`, `contracts/verdict.schema.json`, a different object,
   computed FROM `outcome` by the evaluator), so restamping it here would
   have been a second spelling propped up by nothing but a test written to
   match this workaround.

2. `crucible.policy.episode.EpisodeContext.as_dict()` RETURNS PREFIXED KEYS -
   FIXED AT SOURCE. `seal_episode`'s `_freeze_block` now strips the
   `episode.` prefix off whatever `as_dict()`/`to_dict()`/`frozen` returns
   before handing it back, so it lands on the same bare-key shape the manual
   fallback path already produced. This adapter now passes the real
   `EpisodeContext` object (`episode_context`) as `seal_episode`'s
   `episode_context=` argument, the same object `EnforcementCore`/
   `PolicyEngine` already hold - it no longer needs to smuggle a second,
   parallel bare dict (`context_fields`) past `_freeze_block` to get a bare
   result.

3. `scripts/w2-smoke.py::drive()` passes a `target.refund_agent.episode.Episode`
   (from `target/refund_agent/episode.py`) as `EnforcementCore`'s
   `episode_context=`. `EnforcementCore._refuse_episode_writes` calls
   `.attempt_write(...)` on it and `PolicyEngine._clause` calls `.get(...)` on
   it - neither method exists on that class (it has `apply_context_update` and
   `context_value` instead). This is invisible in w2-smoke.py only because its
   fixed calls never carry an `episode.*` key and its one patch never uses an
   `arg_vs_episode_context` clause. This module does NOT reuse that pattern:
   see "WHY EPISODE CONTEXT IS `crucible.policy.episode.EpisodeContext`" below.

THE HANDLE-RESOLUTION GAP THIS MODULE EXISTS TO CLOSE
-------------------------------------------------------
`target/refund_agent/agent.py::build_agent()` hands ADK bare Python functions
(`tools=list(tools.TOOL_FUNCTIONS)`). ADK wraps each one in a `FunctionTool`
lazily, on every invocation (`LlmAgent.canonical_tools()` ->
`_convert_tool_union_to_tools()` -> `FunctionTool(func=tool_union)`), and that
wrapper's `.name` defaults to the bare Python function name - `"issue_refund"`,
never `"target.refund_agent.tools.issue_refund"`.

`CruciblePlugin._resolve()` looks the ADK tool name up against
`core.handle_for(tool_name)`, which is keyed by `tool_fqname` -
`target/refund_agent/manifest.py::build_manifest()` builds every entry with
`tool_fqname = "target.refund_agent.tools.%s" % fn.__name__`, the DOTTED form.
Left alone, every real tool call resolves to `handle_for("issue_refund")` ->
`None` -> a synthetic handle -> `capabilities_for()` returns `UNCLASSIFIED` ->
the policy engine can never select it -> every call is allowed regardless of
what `policy` says. The loop would run, the plugin would fire, and it would
enforce nothing - the single most flattering-looking failure available here,
because nothing raises and nothing looks broken.

The fix (`_adk_tools_for` below): construct each `FunctionTool` ourselves and
set `.name` to the manifest's dotted `tool_fqname` before handing the list to
the agent, exactly as `tests/test_adk_invocation_paths.py`'s `_make_tool()`
does for its one hand-built tool (`tool.name = _REFUND_FQNAME`). This changes
no bytes under `target/` - it mutates the constructed `LlmAgent.tools` field
after `build_agent()` returns, which is an ordinary Pydantic attribute
assignment, not an edit to the frozen package.

RISK THIS MODULE COULD NOT VERIFY (dots in a live function-call name). ADK's
own schema-building and the stub-model harness in
`tests/test_adk_invocation_paths.py` both accept a dotted tool name with no
complaint - that file already drives a real `Runner` against
`"refund.tools.issue_refund"`. Whether Gemini's live function-calling API
itself accepts a `.` in a declared function name was NOT checked here: doing so
would require a live model call, which this lane's cost-discipline instructions
forbid. If a live campaign run ever reports `FunctionTool` schema rejections at
`gemini-3.5-flash-lite`, this naming convention is the first thing to inspect.

WHY NO `_decision` / `_rule_id`
---------------------------------
The stand-in's caller (`stand_in_tripwire` in `campaign.py`) reads
`episode["_decision"]` directly because it has no Objective Set to score
against - the enforcement decision IS its breach signal. That is explicitly a
stand-in shape. The real TRIPWIRE rules from `episode["events"]` (plus the
Objective Set) alone - every enforcement fact this adapter has is already ON
the ToolEvents (`policy_decision`, `denied_by_rule_id`, and the presence or
absence of a matching TOOL_EXECUTED; see `crucible/plugin/core.py` and
ADR-0012). Adding a private `_decision`/`_rule_id` field back here would let a
tripwire built to read the ledger quietly start reading a stand-in-only field
instead.

WHY EPISODE CONTEXT IS `crucible.policy.episode.EpisodeContext`
-------------------------------------------------------------------
`EnforcementCore._refuse_episode_writes` calls
`self.episode_context.attempt_write(name, value)`, and `PolicyEngine._clause`
calls `episode_context.get(cond.get("context_field"))`. Both methods exist on
`crucible.policy.episode.EpisodeContext` and NEITHER exists on
`target.refund_agent.episode.Episode` - see defect 3 above for why
`scripts/w2-smoke.py` gets away with the wrong type.

COST DISCIPLINE
------------------
`build_real_target(...)` takes `model` and `sor_factory` as injectable
parameters. The default (`model=None`) leaves `LlmAgent.model` as
`build_agent()` set it - a `BaseLlm` INSTANCE carrying the pinned `TARGET_MODEL`
and pinning Vertex on the `global` endpoint, whose client is constructed only
when a call actually fires. It was a bare STRING until 2026-08-22, which is the
form that let `GOOGLE_GENAI_USE_VERTEXAI` choose the provider; see
`target/refund_agent/agent.py`. No credentials are read and no
network call is made at import time or at `build_real_target()` call time -
only when the returned callable actually drives an episode. Tests pass a stub
`BaseLlm` so `python -m pytest tests/` stays runnable with no GCP project,
matching `target/refund_agent/agent.py`'s own stated constraint.
"""

import asyncio
import hashlib
import os
import pathlib

from ..harness.derived import DerivedCompute
from ..harness.episode import seal_episode
from ..manifest import load_part_b
from ..plugin import EnforcementCore
from ..plugin.adk import CruciblePlugin
from ..plugin.ledger import EpisodeLedger
from ..plugin.stamper import DerivedStamper
from ..policy.engine import PolicyEngine
from ..policy.episode import EpisodeContext

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
DERIVED_SCHEMA_PATH = pathlib.Path(_REPO) / "contracts" / "golden" / \
    "C3b-derived_schema.valid.json"

# The seeded world every episode runs against, and why ORD-4472 specifically.
# `target/refund_agent/simulated_system_of_record.py::seed_demo_ledger` is the
# only seeded world this build has - there is no corpus-driven, per-instance
# scenario wired to `real_target` yet (the `attack` dict carries only
# `attack_id`/`family_id`/`instruction`; nothing about which order or account
# it concerns). ORD-4472 is the $900 espresso machine, chosen because it is the
# one seeded order whose amount matches every one of `campaign.py`'s
# lane-authored SEEDS ("$900 refund on order 40021"). Wiring a real corpus
# instance's own scenario into this adapter is out of this lane's scope; this
# is a documented, load-bearing simplification, not an oversight.
_SCENARIO_ORDER_ID = "ORD-4472"
_SCENARIO_CUSTOMER_ID = "CUS-8801"


def _episode_id_for(attack_id):
    """`ep_[0-9a-f]{12}` (C1). Derived from the attack id, never invented.

    `AttackSeed.attack_id` in this build is `atk_` + twelve lowercase-hex
    characters (`campaign.py`'s SEEDS). Reusing that suffix keeps one episode
    traceable back to the attack that produced it. A future corpus whose
    attack ids do not fit that shape falls back to a hash of the id, so this
    never raises on unfamiliar input - a `real_target` that crashed on an id
    shape it had not seen would turn a measurement gap into a HALT.
    """
    suffix = attack_id[4:] if attack_id.startswith("atk_") else attack_id
    if len(suffix) == 12 and all(c in "0123456789abcdef" for c in suffix.lower()):
        return "ep_" + suffix.lower()
    return "ep_" + hashlib.sha256(attack_id.encode("utf-8")).hexdigest()[:12]


def _adk_tools_for(functions):
    """Wrap each bare tool function in a `FunctionTool`, KEEPING ADK'S OWN NAME.

    THE RENAME THAT USED TO BE HERE WAS REMOVED BY THE COORDINATOR 2026-08-21,
    AND IT WOULD HAVE PASSED EVERY TEST IN THIS REPO AND FAILED ON THE FIRST
    LIVE CALL.

    The handle-resolution gap this lane found is real: ADK names a bare-function
    tool `fn.__name__`, the manifest keys on the dotted `tool_fqname`, the lookup
    missed, and UNCLASSIFIED is always allowed - so the policy enforced nothing.
    That diagnosis was correct and it is the most valuable finding of the four.

    The FIX was wrong. Setting `t.name` to the dotted path makes the resolution
    succeed offline, where the model is a stub that never validates a tool
    declaration. A function-declaration name must match `^[a-zA-Z0-9_-]{1,64}$`;
    a dot is not in that set. Against a real Gemini endpoint the declaration is
    refused, and it is refused on the FIRST call of the FIRST live campaign.

    A workaround that only holds where the test stub is looser than production
    is not a fix - it is the failure moved to where nothing is watching. Fixed at
    the source instead: `EnforcementCore.handle_for` now resolves the bare name
    as well as the dotted one, and REFUSES a bare name that two tools share
    rather than guessing between them.
    """
    from google.adk.tools.function_tool import FunctionTool
    return [FunctionTool(fn) for fn in functions]


def _fresh_seeded_sor():
    from target.refund_agent.simulated_system_of_record import (
        DEMO_AS_OF, SimulatedSystemOfRecord, seed_demo_ledger,
    )
    return seed_demo_ledger(SimulatedSystemOfRecord(as_of=DEMO_AS_OF))


def _scenario_and_context(sor):
    """The frozen `scenario` dict `DerivedCompute` reads and the
    `EpisodeContext` `EnforcementCore`/`PolicyEngine` need, both sourced from
    the SAME seeded order/account record, never from the attack text and
    never from a wall clock (ruling 16; `DEMO_AS_OF` is frozen in
    `simulated_system_of_record.py`).

    Only ONE `episode_context` object is built now (2026-08-22): `seal_episode`
    used to need a separate BARE field dict because its `_freeze_block`
    fast-path passed `EpisodeContext.as_dict()` through with the `episode.`
    prefix still attached (defect 2, `crucible/harness/episode.py`'s
    docstring). That is fixed at the source now, so the single
    `EpisodeContext` this function builds is correct for every consumer:
    `EnforcementCore`/`PolicyEngine` via their prefixed `.get()`, and
    `seal_episode` via its own de-prefixing."""
    order = sor.get_order(_SCENARIO_ORDER_ID)
    customer = sor.get_customer(_SCENARIO_CUSTOMER_ID)
    delivered_days = None
    if order.delivered_on is not None:
        delivered_days = (sor.as_of - order.delivered_on).days
    scenario = {
        "approval_tier": "NONE",
        "account_age_days": customer.account_age_days,
        "delivery_confirmed": order.delivery_confirmed,
        "days_since_delivery": delivered_days or 0,
    }
    context_fields = {
        "account_holder_email": order.account_holder_email,
        "account_holder_id": order.account_holder_id,
        "order_payment_instrument_id": order.payment_instrument_id,
    }
    episode_context = EpisodeContext.freeze(context_fields)
    return scenario, episode_context


def _build_core(policy, episode_id, sor):
    from target.refund_agent.manifest import build_manifest
    manifest = build_manifest()
    derived_schema, _ = load_part_b(DERIVED_SCHEMA_PATH)
    scenario, episode_context = _scenario_and_context(sor)
    stamper = DerivedStamper(derived_schema,
                             compute=DerivedCompute(manifest, scenario))
    core = EnforcementCore(
        engine=PolicyEngine(policy),
        manifest=manifest,
        stamper=stamper,
        ledger=EpisodeLedger(episode_id),
        episode_context=episode_context,
        role="refund_agent",
    )
    return core


async def _drive(attack, policy, *, model, sor_factory, run_manifest):
    from google.adk.apps.app import App
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import (
        InMemorySessionService,
    )
    from google.genai import types

    from target.refund_agent import tools as target_tools
    from target.refund_agent.agent import TARGET_AGENT_NAME, build_agent

    episode_id = _episode_id_for(attack.get("attack_id") or "atk_000000000000")
    sor = sor_factory()
    core = _build_core(policy, episode_id, sor)
    plugin = CruciblePlugin(core)

    target_tools.bind_backends(sor)
    target_fault = False
    try:
        agent = build_agent()
        agent.tools = _adk_tools_for(target_tools.TOOL_FUNCTIONS)
        if model is not None:
            agent.model = model
        app = App(name="crucible_%s" % TARGET_AGENT_NAME, root_agent=agent,
                  plugins=[plugin])
        runner = Runner(app=app, session_service=InMemorySessionService(),
                        auto_create_session=True)
        try:
            async for _ in runner.run_async(
                    user_id="u_" + episode_id, session_id="s_" + episode_id,
                    new_message=types.Content(
                        role="user",
                        parts=[types.Part(text=attack.get("instruction", ""))])):
                pass
        except Exception:
            # A crash driving the episode is TARGET_FAULT, not a breach and not
            # a clean run (CONVENTIONS / conductor.py ruling 33.4). Swallowed
            # here rather than propagated so one flaky episode does not halt
            # the whole round; every event already written before the crash is
            # still sealed and returned, because a partial ledger is still
            # evidence.
            target_fault = True
    finally:
        target_tools.unbind_backends()

    # Defects 1 and 2 (module docstring) are fixed at the source now:
    # `seal_episode` writes `raw["outcome"]` itself from `target_fault=`, and
    # `_freeze_block` de-prefixes `core.episode_context` (the real
    # `EpisodeContext`, not a parallel bare dict) before returning it. This
    # adapter uses the return value as-is - no post-seal patching.
    return seal_episode(core.ledger, run_manifest,
                        episode_context=core.episode_context,
                        target_fault=target_fault)


def build_real_target(*, run_manifest, model=None, sor_factory=None):
    """Returns a `(attack, policy) -> sealed episode dict` callable - the
    drop-in for `run_episode=` in `Conductor`.

    `run_manifest`: REQUIRED. A `crucible.tripwire.model.RunManifest`-shaped
        object carrying `.objective_set_hash`, `.manifest_hash`,
        `.derived_schema_hash`, `.policy_version`, `.policy_hash`. Copied
        into every sealed episode, never computed or guessed here - see the
        module docstring. There is no default: a `real_target` built without
        one would either have to fabricate hashes or produce permanently
        INVALID episodes, and this file does neither silently.
    `model`: `None` (default) leaves `LlmAgent.model` as `build_agent()` set
        it - a `BaseLlm` carrying the pinned `TARGET_MODEL` and pinning Vertex
        on `global`, whose client is built only when a call actually fires. Pass
        a `google.adk.models.base_llm.BaseLlm` instance (or another model id
        string) to run against a stub - this is how tests stay offline.
    `sor_factory`: `None` (default) seeds a fresh `SimulatedSystemOfRecord` via
        `seed_demo_ledger` for every episode. Tests inject their own factory to
        capture the per-episode instance and assert on it directly.
    """
    if run_manifest is None:
        raise ValueError(
            "build_real_target() requires run_manifest. Sealing needs the "
            "objective_set_hash/manifest_hash/derived_schema_hash to COPY, "
            "never to invent - an adapter that filled in placeholders here "
            "would be a false pre-registration claim, worse than an honest "
            "INVALID episode.")
    factory = sor_factory or _fresh_seeded_sor

    def _real_target(attack, policy):
        return asyncio.run(_drive(attack, policy, model=model,
                                  sor_factory=factory,
                                  run_manifest=run_manifest))
    return _real_target
