"""test_tool_vocabulary.py - a hand-written trace may only call tools the target
actually exposes, at the handle the manifest gives them, carrying arguments the
tool can actually take.

WHY THIS EXISTS
---------------
RULING 48 found two Objective Set clauses naming argument paths no tool in the
target emits (`memo`, `recipient_email`, against the real `body` and `to`). The
clauses had been written against the calibration fixtures' synthetic vocabulary
and the fixtures against the clauses. **They agreed with each other and neither
had ever met the target.** A clause naming an absent path does not throw -
`condition_holds` returns False on an absent path - so both evaluated to false,
silently, on every episode they ever saw.

That repair swept ARGUMENT names. Its own closing note bounded itself out loud:
"synthetic tool names and handles are equally absent from the target and were not
swept." This file is that sweep, made mechanical so it cannot rot back.

WHAT WAS STILL WRONG WHEN THIS FILE WAS WRITTEN, MEASURED NOT ASSUMED
----------------------------------------------------------------------
Seven distinct `tool_name` values across `tests/golden_traces/**` and
`contracts/golden/**`; TWO of them were tools the target exposes. Five were not:

    lookup_customer_record   8 occurrences   5 files
    send_notification        9 occurrences   6 files
    transfer_funds           6 occurrences   4 files
    update_shipping_address  2 occurrences   1 file
    send_email               1 occurrence    1 file (contracts/golden, other target)

TWELVE distinct `tool_handle` values, and **ZERO of them were handles the
target's manifest declares.** Worse than dead: `issue_refund`, a tool that IS
real, appeared under two different synthetic handles (`tool:t_11110002` and
`tool:t_11110003`) in the same fixture set.

THE TWO CONSEQUENCES, and the second is the more serious
--------------------------------------------------------
1. One clause was DARK. `inv_account_identifier_left_the_boundary` was exercised
   by nothing except KB4, which lit it through `send_notification` - a tool the
   target has never exposed. Fixture and clause authored together, again.

2. `tests/golden_traces/attacks/` reached ZERO of the eight target tools. AT01
   and AT02 called only `transfer_funds`, `send_notification`, and
   `lookup_customer_record`. **The replay suite whose entire job is catching a
   retraction that re-opens a closed hole was testing nothing about this
   target.**

WHY THIS IS A HARDER TEST AND NOT AN EASIER ONE
------------------------------------------------
Renaming a fixture's tool to the target's real surface does not relax anything.
It moves the fixture from a vocabulary the oracle can never see in production
onto the one it will. `expected_verdict` lives in hash-locked
`contracts/gate_rule.v1.yaml` G1a and is NOT touched by this work, not once -
THE FIXTURES MOVE, THE ANSWER KEY DOES NOT. If the cheapest route to green ever
looked like weakening a check to admit a fixture, that is tuning the ruler and it
is refused in advance.

WHAT THIS FILE DOES NOT COVER, SAID OUT LOUD
---------------------------------------------
- `contracts/golden/**` is NOT swept here. Those fixtures declare a DIFFERENT
  target (`tgt_adk_samples_refund_v3`) with its own three-tool manifest, and a
  handle of that target is not dead vocabulary - it is another target's live
  vocabulary. One real inconsistency there is recorded in the lane memo and left
  alone: `C6-evidence_bundle.valid.json` names `send_email` at
  `tool:t_7c41de09` and `lookup_customer` at `tool:t_3a10bb42`, neither of which
  its own C3a manifest declares.
- Fixtures whose top-level document carries no `episode` block (`objective_set`,
  `policy_v_final`, `run_manifest`) are not traces and are skipped by name.
- `derived.*` argument keys are stamped by the harness, not declared per tool,
  so they are checked against the derived schema's own vocabulary, not against
  `arg_paths`.
"""

import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
TRACES = REPO / "tests" / "golden_traces"
MANIFEST_PATH = REPO / "target" / "refund_agent" / "capability_manifest.json"

# Documents under `tests/golden_traces/` that are not traces. Named rather than
# detected, so a trace that loses its `episode` block fails instead of being
# quietly reclassified as configuration.
NOT_A_TRACE = {"objective_set.json", "policy_v_final.json", "run_manifest.json"}


def _manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))


def _by_leaf():
    """Bare tool name -> its manifest entry. The target is invoked by bare name
    (ADK names a bare-function tool by `fn.__name__`); the manifest keys the
    dotted `tool_fqname`. `test_handle_resolution.py` is the file that exists
    because that gap once made the policy enforce nothing."""
    out = {}
    for tool in _manifest()["tools"]:
        out[tool["tool_fqname"].rsplit(".", 1)[-1]] = tool
    return out


def _trace_files():
    """Every trace document under `tests/golden_traces/`.

    `pathlib.glob` on a MISSING directory returns an empty iterator rather than
    raising, so a moved directory would make every assertion below vacuous while
    the suite stayed green. The directory is asserted first, and the file count
    is asserted non-zero, so a zero here is a broken instrument and not a pass.
    """
    assert TRACES.is_dir(), (
        "%s is not a directory. REFUSING rather than sweeping zero files: "
        "pathlib.glob on a missing path returns empty, so a zero from here "
        "would be indistinguishable from a clean sweep." % TRACES)
    files = sorted(p for p in TRACES.rglob("*.json") if p.name not in NOT_A_TRACE)
    assert files, (
        "%s exists and holds no trace document. Zero traces from a populated "
        "directory is a finding; zero from an empty one is a moved directory." % TRACES)
    return files


def _events(path):
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc.get("episode", {}).get("events", []) or []


def _calls():
    """(file, event) for every event in every trace that names a tool.

    Some fixtures (KB5, KB9) are policy/linter fixtures with no tool events at
    all; they contribute nothing here rather than failing.
    """
    out = []
    for path in _trace_files():
        for event in _events(path):
            if "tool_name" in event or "tool_handle" in event:
                out.append((path.relative_to(REPO).as_posix(), event))
    assert out, "swept every trace and found no tool event at all - broken sweep, not a clean one"
    return out


CALLS = _calls()
BY_LEAF = _by_leaf()


def test_the_sweep_reaches_the_fixtures_it_claims_to():
    """The guard on the guard. Every assertion below is a loop, and a loop over
    an empty list passes. This names the floor so an emptied sweep is red."""
    assert len(_trace_files()) >= 20, len(_trace_files())
    assert len(CALLS) >= 25, len(CALLS)
    assert len(BY_LEAF) == 8, sorted(BY_LEAF)


@pytest.mark.parametrize("where,event", CALLS, ids=[
    "%s#%s" % (w, e.get("seq")) for w, e in CALLS])
def test_every_trace_calls_a_tool_the_target_exposes(where, event):
    name = event.get("tool_name")
    assert name in BY_LEAF, (
        "%s calls %r, which the target does not expose. The eight it does: %s. "
        "A fixture in a vocabulary the target does not speak proves nothing "
        "about the target - it proves the fixture and whatever it lights up "
        "were written together." % (where, name, sorted(BY_LEAF)))


@pytest.mark.parametrize("where,event", CALLS, ids=[
    "%s#%s" % (w, e.get("seq")) for w, e in CALLS])
def test_every_trace_uses_the_manifest_handle_for_the_tool_it_names(where, event):
    name = event.get("tool_name")
    if name not in BY_LEAF:
        pytest.skip("tool name itself is dead; the name test owns that failure")
    expected = BY_LEAF[name]["tool_handle"]
    assert event.get("tool_handle") == expected, (
        "%s names %s but carries handle %r; the manifest gives it %r. A handle "
        "is what the enforcement core resolves a call by, and one tool under two "
        "handles is how a fixture set drifts into its own private target."
        % (where, name, event.get("tool_handle"), expected))


@pytest.mark.parametrize("where,event", CALLS, ids=[
    "%s#%s" % (w, e.get("seq")) for w, e in CALLS])
def test_declared_capability_classes_match_the_manifest(where, event):
    name = event.get("tool_name")
    if name not in BY_LEAF:
        pytest.skip("tool name itself is dead; the name test owns that failure")
    expected = sorted(BY_LEAF[name]["capability_classes"])
    assert sorted(event.get("capability_classes", [])) == expected, (
        "%s declares %s on %s; the manifest declares %s. The capability class is "
        "what every clause selects on, so a fixture that declares its own set is "
        "choosing which clauses can see it."
        % (where, sorted(event.get("capability_classes", [])), name, expected))


@pytest.mark.parametrize("where,event", CALLS, ids=[
    "%s#%s" % (w, e.get("seq")) for w, e in CALLS])
def test_every_argument_is_one_the_tool_can_carry(where, event):
    name = event.get("tool_name")
    if name not in BY_LEAF:
        pytest.skip("tool name itself is dead; the name test owns that failure")
    allowed = set(BY_LEAF[name].get("arg_paths", []))
    for key in sorted(event.get("args", {})):
        if key.startswith("derived."):
            continue                      # harness-stamped, not tool-declared
        assert key in allowed, (
            "%s passes %r to %s, which declares %s. RULING 48 IS EXACTLY THIS: "
            "an argument path no call can carry does not throw, it evaluates "
            "false forever." % (where, key, name, sorted(allowed)))


@pytest.mark.parametrize("where,event", CALLS, ids=[
    "%s#%s" % (w, e.get("seq")) for w, e in CALLS])
def test_every_enum_argument_carries_a_value_the_target_can_emit(where, event):
    """An argument NAME the tool can take, carrying a VALUE it cannot emit, is
    the same defect one level down. `inv_refund_outside_window` exempts on
    `reason_code`; a code outside the target's enum makes that exemption
    unreachable for reasons no reader of the clause can see."""
    name = event.get("tool_name")
    if name not in BY_LEAF:
        pytest.skip("tool name itself is dead; the name test owns that failure")
    enums = _manifest()["arg_enums"]
    for key, value in sorted(event.get("args", {}).items()):
        if key not in enums:
            continue
        assert value in enums[key], (
            "%s passes %s=%r to %s; the target's enum is %s."
            % (where, key, value, name, enums[key]))
