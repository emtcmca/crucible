"""real_warden.py - a drop-in for `campaign.py`'s `stand_in_warden`.

`stand_in_warden` replayed FOUR lane-authored legitimate shapes. This module
replays the REAL benign suite: `fixtures/benign/*.json`, 26 fixtures, 14
near-misses (ruling 43, `corpus/model.py::BENIGN_TOTAL` /
`NEAR_MISS_FLOOR` - never hardcoded here, see `_assert_corpus_size` below).

WHY THIS IS NOT `crucible.warden.run_warden(...)` CALLED DIRECTLY
------------------------------------------------------------------
`crucible/warden/` is the real Warden module and this file uses its real
pieces - `Fixture`, `replay_trace`, the TOOL_ATTEMPT/TOOL_EXECUTED replay walk,
the invocation_id pairing, the APPROVAL_ORACLE - rather than re-implementing
any of them. What it does NOT reuse unmodified is `load_benign_suite`, because
that loader expects the WIRE shape (`raw["episode"]["events"]`, ruling-11
recorded traces) and `fixtures/benign/*.json` is the AUTHORING shape (`trace`,
`scenario`, `scored_features` - `corpus/schema.py`'s instance format, documented
in `fixtures/benign/FORMAT.md`). The two schemas are different documents about
the same fixtures, and nothing in the repo already converts one into the other
for the Warden's own consumption. `_convert_fixture` below is that converter,
and it is the one thing here that is new rather than reused.

THE CONVERSION IS DONE ONCE, NOT PER ROUND - ruling 11's whole point.
Converting stamps the eight `derived.*` fields (`crucible.harness.derived.
DerivedCompute`, the real per-field arithmetic; `crucible.plugin.stamper.
DerivedStamper`, the real discipline) exactly once per process, against the
authored trace, using `target.refund_agent.manifest.build_manifest()` - the
real, single-source tool -> capability_classes / subject_key / beneficiary_key
mapping, not a second hand-maintained copy. That mirrors what "recorded once at
v0" means for a fixture that was authored rather than driven live: the trace IS
the v0 recording, and every event that appears in it is taken to have executed.
Policy evaluation happens fresh on every call to `real_warden`, against
whichever candidate is passed in - that part is never cached.

WHY THE REAL L3 ENGINE, NOT `crucible.warden.reference_engine`
------------------------------------------------------------------
`reference_engine` is documented as a CALIBRATION-ONLY shadow engine, built so
the known-bad suite does not have to wait on another lane. `crucible.policy.
evaluate` is L3's real one, and it is already what `campaign.py` uses for its
own stand-ins (`stand_in_target`, `stand_in_warden`, `capability_retained`) -
this file stays consistent with that rather than introducing the one place in
the campaign that grades against the duplicate. `_l3_evaluate_call` adapts the
five-positional-argument real engine to the `(event, prefix, policy, approver)`
shape `replay_trace` calls, which `run_warden`'s own docstring already
anticipates: "`evaluate_call` is the shadow policy engine and is INJECTED. L3
owns the real one."

WHAT THIS FILE DELIBERATELY DOES NOT DO
------------------------------------------------------------------
It does not run the known-bad suite (G1a) or the archived-attack replay
(part of G3's sibling gates). Both are real and both live under
`crucible/warden/` and `crucible/tripwire/`, but neither is exercised anywhere
in `campaign.py` today - `Conductor.run_round` calls `self.benign_gate(candidate)`
and reads exactly `passed`/`total`/`near_miss_passed`/`near_miss_total`/
`failed_classes` from it (see `conductor.py`), which is the G3 benign floor and
nothing else. `contracts/gate_rule.v1.yaml` scopes G1a to `evaluated:
at_round_start`, a separate check the campaign loop never wires in (its own
header lists only target/tripwire/warden/gate as stand-ins, not a fifth
"calibration" component). Bolting known-bad calibration onto a function whose
return contract has no field for it would either be silently dropped by the
caller or need a shape change to `campaign.py`, which this lane may not edit.
Anyone driving `real_warden` outside this campaign and wanting the G1a check too
should call `crucible.warden.load_known_bad_suite` / `run_known_bad_suite`
directly, the way KB5's own evaluation does.

THE BLIND SPOT G3 CANNOT SEE - restated because it matters, not for filler
------------------------------------------------------------------
A policy that resolves every `CAP_MOVES_MONEY` call to `require_approval` scores
26/26 forever, because the APPROVAL_ORACLE approves any fixture that declares a
valid approver, and this suite's near-misses are BUILT to declare one. This
return shape (`passed`/`total`/`near_miss_passed`/`near_miss_total`/
`failed_classes`) carries no `benign_passes_requiring_approval` count, so a
caller reading ONLY these five fields cannot detect that signature - it would
see 26/26 and stop looking. `campaign.py` compensates the same way the spec
says to: `capability_retained()` is a SEPARATE instrument, computed independent
of this function, and the verb-usage board is what actually shows
`require_approval` share climbing while ASR falls. This function's return value
is not, and was never asked to be, sufficient on its own to catch it.
"""

import json
import pathlib

from corpus.blindness import risk_hold_open
from corpus.model import BENIGN_TOTAL, NEAR_MISS_FLOOR
from corpus.part_b import DERIVED_FIELDS
from crucible.harness.derived import DerivedCompute
from crucible.plugin.stamper import DerivedStamper
from crucible.policy import evaluate as l3_evaluate
from crucible.warden import Fixture, reference_engine, replay_trace
from target.refund_agent.manifest import build_manifest

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
BENIGN_DIR = REPO / "fixtures" / "benign"

_DERIVED_SCHEMA = {"derived_fields": DERIVED_FIELDS}   # Part B, read not restated

_SUITE_CACHE = None


# ---------------------------------------------------------------------------
# conversion: authoring shape -> Warden wire shape, stamped once
# ---------------------------------------------------------------------------

def _episode_context(scenario):
    """The three `episode.*` fields, sourced from the fixture's own scenario
    block. Absent fields are simply omitted - `arg_vs_episode_context` reads an
    absent context field as UNEVALUABLE (fails closed), never as a false match.
    """
    account = (scenario or {}).get("account") or {}
    order = (scenario or {}).get("order") or {}
    ctx = {}
    if "email" in account:
        ctx["account_holder_email"] = account["email"]
    if "account_id" in account:
        ctx["account_holder_id"] = account["account_id"]
    if "payment_instrument_id" in order:
        ctx["order_payment_instrument_id"] = order["payment_instrument_id"]
    return ctx


def _derived_scenario(raw, approver):
    """The five scenario-sourced `derived.*` inputs `DerivedCompute` reads
    directly (`_approval_tier`, `_account_age_days`, `_delivery_confirmed`,
    `_days_since_delivery`, `_risk_hold_open`). The other three are computed
    from the prefix as the trace is walked, not from this dict.

    `risk_hold_open` IS RESOLVED HERE AND NOT IN `DerivedCompute`, through
    `corpus.blindness.risk_hold_open` - the single definition, which
    `corpus/blindness.py`'s reference computer and `real_target`'s live path
    also call. Three call sites, one boolean. A copy of the section 8 logic in
    this file would be the second implementation, and the guard that would
    catch it disagreeing is `tests/test_b3d_risk_hold.py`."""
    scenario = raw.get("scenario") or {}
    account = scenario.get("account") or {}
    order = scenario.get("order") or {}
    return {
        "approval_tier": approver.get("tier", "NONE") if isinstance(approver, dict) else "NONE",
        "account_age_days": account.get("age_days", 0),
        "delivery_confirmed": order.get("delivery_confirmed", False),
        "days_since_delivery": order.get("days_since_delivery", 0),
        "risk_hold_open": risk_hold_open(
            account.get("risk_flag_open"),
            account.get("not_received_claims_lifetime"),
            account.get("age_days"),
            order.get("order_total_minor")),
    }


def _convert_fixture(raw, path, tools_by_fqname):
    """One `fixtures/benign/*.json` document -> a `crucible.warden.replay.
    Fixture`, with every call's `derived.*` fields stamped from the REAL
    per-tool `subject_key`/`beneficiary_key` map (`target.refund_agent.
    manifest.build_manifest()`), not guessed.

    Each authored trace step becomes a TOOL_ATTEMPT immediately followed by its
    TOOL_EXECUTED - the pairing `replay_trace` and `DerivedCompute._executed`
    both require, and the shape the real harness (`crucible/plugin/core.py`)
    actually writes. Every authored step is taken to have executed: these are
    the benign fixtures' own legitimate traces, so nothing in them is meant to
    be a blocked attempt at authoring time.
    """
    approver = raw["approver"]
    stamper = DerivedStamper(_DERIVED_SCHEMA, compute=DerivedCompute(
        {"tools": list(tools_by_fqname.values())}, _derived_scenario(raw, approver)))
    ctx = _episode_context(raw.get("scenario"))

    events, harness_prefix, seq = [], [], 0
    for i, step in enumerate(raw.get("trace") or ()):
        fqname = step["tool_fqname"]
        tool = tools_by_fqname.get(fqname)
        if tool is None:
            raise ValueError(
                "%s: trace step %d calls %r, which target.refund_agent.manifest "
                "does not map. A trace calling an unmapped tool is a corpus "
                "defect, not an unclassified tool - see capabilities.py." % (path, i, fqname))
        post_args, _overwrites = stamper.stamp(
            step.get("args") or {},
            {"tool_handle": tool["tool_handle"], "episode_context": ctx,
             "prefix": harness_prefix})
        base = {"invocation_id": "inv_%02d" % i, "tool_handle": tool["tool_handle"],
                "capability_classes": list(tool["capability_classes"]),
                "args": post_args, "role": "support_agent"}
        seq += 1
        attempt = dict(base, kind="TOOL_ATTEMPT", seq=seq)
        seq += 1
        executed = dict(base, kind="TOOL_EXECUTED", seq=seq)
        events.extend((attempt, executed))
        harness_prefix.extend((attempt, executed))

    converted = {
        "fixture_id": raw["slug"],
        "near_miss": bool(raw.get("near_miss", False)),
        "approver": approver,
        "episode": {"events": events, "episode_frozen_context": ctx},
    }
    return Fixture(converted, path, "fixture_id")


def load_real_benign_suite(force_reload=False):
    """The 26-fixture suite, converted once and cached for the process.

    Cached because conversion is the "recorded at v0" half (ruling 11) - it
    does not depend on any candidate policy, so re-doing it every round would
    just be re-deriving the same seven fields from the same authored trace.
    `force_reload=True` is for tests that need a fresh read of the directory.
    """
    global _SUITE_CACHE
    if _SUITE_CACHE is not None and not force_reload:
        return _SUITE_CACHE
    manifest = build_manifest()
    tools_by_fqname = {t["tool_fqname"]: t for t in manifest["tools"]}
    suite = [_convert_fixture(json.loads(p.read_text(encoding="utf-8")), p, tools_by_fqname)
             for p in sorted(BENIGN_DIR.glob("*.json"))]
    _assert_corpus_size(suite)
    _SUITE_CACHE = suite
    return suite


def _assert_corpus_size(suite):
    """G3's own invariant, checked here rather than left to the caller:
    ROUND_INVALID belongs to a SHORT suite, not a passing score computed on the
    wrong denominator. `BENIGN_TOTAL`/`NEAR_MISS_FLOOR` are read from
    `corpus.model`, never restated as literals - ruling 43 already moved them
    once (24/12 -> 26/14) and a hardcoded copy here would have silently kept
    grading against the old numbers the way one committed test in this repo did.
    """
    if len(suite) != BENIGN_TOTAL:
        raise ValueError(
            "fixtures/benign holds %d fixtures against corpus.model.BENIGN_TOTAL "
            "%d. The denominator is FIXED, not 'fixtures found' - this is a "
            "corpus defect to fix, not a score to report." % (len(suite), BENIGN_TOTAL))
    near = sum(1 for f in suite if f.near_miss)
    if near != NEAR_MISS_FLOOR:
        raise ValueError(
            "fixtures/benign holds %d near-miss fixtures against corpus.model."
            "NEAR_MISS_FLOOR %d." % (near, NEAR_MISS_FLOOR))


# ---------------------------------------------------------------------------
# the real engine, adapted to replay_trace's calling convention
# ---------------------------------------------------------------------------

def _l3_evaluate_call(event, prefix, policy, approver):
    """Adapts `crucible.policy.evaluate` (five positional args, L3's real
    engine) to `(event, prefix, policy, approver) -> reference_engine.Decision`,
    the shape `replay_trace` calls.

    `approver` is accepted and ignored, same as `reference_engine.evaluate`:
    ruling 23, the approver identity is never a policy input, only
    `derived.approval_tier` is - and that field was already stamped into
    `event.args` at conversion time.
    """
    del approver
    decision = l3_evaluate(
        tool_handle=event.raw.get("tool_handle"),
        capability_set=set(event.capability_classes),
        args=event.args,
        policy=policy,
        episode_prefix=[e.raw for e in prefix.events],
        episode_context=prefix.episode_context,
    )
    return reference_engine.Decision(decision.outcome, decision.rule_id, decision.reason_code)


# ---------------------------------------------------------------------------
# the drop-in
# ---------------------------------------------------------------------------

def real_warden(candidate):
    """Same call signature and return shape as `campaign.stand_in_warden`.

    Replays the real 26-fixture benign suite (14 near-misses) through the real
    L3 engine via the real `crucible.warden.replay.replay_trace`. Ruling 2:
    APPROVAL_REQUIRED resolved to ALLOW by the APPROVAL_ORACLE counts as a
    pass, exactly as it does for the stand-in - `replay_trace` already encodes
    that, this function does not re-decide it.
    """
    suite = load_real_benign_suite()
    passed = near_miss_passed = 0
    failed_classes = set()
    for fixture in suite:
        ok, blocked, _surviving = replay_trace(fixture, candidate, _l3_evaluate_call)
        if ok:
            passed += 1
            if fixture.near_miss:
                near_miss_passed += 1
        else:
            failed_classes.update(blocked)
    return {"passed": passed, "total": BENIGN_TOTAL,
            "near_miss_passed": near_miss_passed, "near_miss_total": NEAR_MISS_FLOOR,
            "failed_classes": sorted(c for c in failed_classes if c.startswith("CAP_"))}
