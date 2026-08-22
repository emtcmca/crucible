"""test_campaign_gate_wiring.py - is the campaign's GATE the real one, or does
`crucible/conductor/real_gate.py` merely exist?

THE PRECISE REGRESSION THIS FILE EXISTS FOR
============================================
`crucible/conductor/real_gate.py` was authored 2026-08-22 with a 30-case test
file, and `campaign.py` line 516 still read:

    promote=lambda c, r: True,

while the banner printed `gate: STAND-IN. No GCS, no IAM. G7/G8 NOT EXERCISED.`
and told the truth. G7 and G8 HAD run - out of band, through
`scripts/probe-g7-g8.py`, 16 assertions and 16 PASS - and had NEVER RUN THROUGH
THE LOOP. That is the same shape `tests/test_campaign_wiring.py` was written for
one component earlier: a correct module, a green suite of its own, and a
conductor wired to a constant function. A per-module suite structurally cannot
see it, because each one tests its module in isolation.

So every test here asserts on `campaign.py` ITSELF - what `run()` hands the
`Conductor` as `promote`, what that callable does when it is called, what the
banner then claims, and what the bundle records. Re-testing `RealGate` would
prove nothing new; `tests/test_real_gate.py` owns that.

WHAT IS STUB-ONLY HERE. READ THIS BEFORE TRUSTING A GREEN RUN.
==============================================================
1. **No gcloud process is started anywhere in this file, and no test here
   evaluates G7 or G8 against anything.** The offline gate is asserted to be
   built with `skip_cloud=True` and to REFUSE; the live gate is asserted to be
   CONSTRUCTED with cloud assertions on and a real counter injected. Whether
   those assertions pass against the live project is `scripts/probe-g7-g8.py`'s
   evidence, not this file's.
2. **`GcsBlobIO` still has never run against GCS.** Nothing here calls it. Its
   create-only `if_generation_match=0`, its 412 benign-duplicate branch and its
   generation-pinned read-back are written from `data-spec.md` 3.1/3.2 and are
   UNVERIFIED. A `--live` run is their first execution. This file asserts only
   that a live build WIRES it and that the bundle SAYS it is untested.
3. **The live path's model client is never constructed.** `--live` is exercised
   only through `build_gate(live=True)`, which touches no model and no network.
4. **The `Conductor` propagation tests use stub collaborators** - a scripted
   red, a canned autopsy and a canned patch. They prove what the LOOP does with
   a gate that raises, which is the thing under test, and they prove nothing
   about the RED_STRATEGIST, the CORONER or the ARMORER.
"""

import json
import pathlib

import pytest

from crucible.conductor import REQUIRED_HASHES
from crucible.conductor import campaign as C
from crucible.conductor import real_gate as rg
from crucible.conductor.conductor import (
    HALT_GATE_REJECTED_TWICE,
    Conductor,
)
from crucible.conductor.hashlocks import load_hash_locks
from crucible.conductor.real_tripwire import resolve_objective_set
from crucible.governor import Budget, BudgetGovernor
from crucible.plugin.adk import ADK_AVAILABLE
from infra.holdout_touch import HoldoutTouchCounter

adk_only = pytest.mark.skipif(not ADK_AVAILABLE, reason="ADK not importable")

ENV = rg.gcp_env(C._REPO)                                   # noqa: SLF001


def _locks():
    return load_hash_locks(resolve_objective_set())


# ---------------------------------------------------------------------------
# 1. The loop drives the REAL gate. THIS IS THE TEST THAT FAILS RED ON THE
#    TREE AS IT STOOD BEFORE THIS LANE.
# ---------------------------------------------------------------------------

class _CapturedConductor:
    """Records what `run()` wired, then runs the real one - the same device
    `test_campaign_wiring.py` uses, for the same reason: the defect lives in the
    CONSTRUCTOR ARGUMENT, and a module that is correct and imported by nobody
    passes every test of itself."""

    captured = None

    def __init__(self, **kwargs):
        _CapturedConductor.captured = kwargs
        self._inner = Conductor(**kwargs)

    def run(self, policy):
        return self._inner.run(policy)


@pytest.fixture
def captured_wiring(monkeypatch, tmp_path):
    """One full offline campaign; hands back `(kwargs, bundle, stdout)`."""
    _CapturedConductor.captured = None
    monkeypatch.setattr(C, "Conductor", _CapturedConductor)
    out = tmp_path / "bundle.json"
    assert C.run(["--out", str(out)]) == 0
    bundle = json.loads(out.read_text(encoding="utf-8"))
    assert _CapturedConductor.captured is not None
    return _CapturedConductor.captured, bundle


@adk_only
def test_the_conductor_is_not_wired_to_the_promote_lambda(captured_wiring):
    """FAILS RED on the tree before this lane, where `promote` was
    `lambda c, r: True`.

    Three separate witnesses, because a richer stand-in could fake any one:
    it is a `RealGate`, it is not a lambda, and it knows the promoter identity -
    which a constant function has no way to know because it never read
    `scripts/gcp-env.sh`.
    """
    kwargs, _bundle = captured_wiring
    gate = kwargs["promote"]
    assert isinstance(gate, rg.RealGate), (
        "the conductor's promote hook is %r, not the real gate" % type(gate))
    assert getattr(gate, "__name__", None) != "<lambda>"
    assert gate.promoted_by == "crucible-gate"


@adk_only
def test_the_wired_gate_reads_its_promoter_from_gcp_env_and_not_from_a_literal(
        captured_wiring):
    """THE IDENTITY THAT AUTHORS A CANDIDATE IS NOT THE IDENTITY THAT PROMOTES
    IT. The name is sourced through `verify_iam.load_env`, so if
    `scripts/gcp-env.sh` ever names the Armorer this fails at construction."""
    kwargs, _bundle = captured_wiring
    gate = kwargs["promote"]
    assert gate.promoted_by == ENV["SA_GATE"]
    assert gate.promoted_by != ENV["SA_ARMORER"]
    assert not gate.promoted_by.startswith("sa-"), "sa-* is dead vocabulary"


def test_campaign_py_never_types_a_bucket_or_project_name_as_a_literal():
    """G7 and G8 grep literal strings. A typo there does not fail loudly - it
    produces an UNEVALUABLE gate, which reads exactly like a passing one
    (`measurement-spec.md:813`). The same rule `real_gate.py` is held to.
    """
    src = (pathlib.Path(C._REPO) / "crucible" / "conductor"      # noqa: SLF001
           / "campaign.py").read_text(encoding="utf-8")
    for literal in ("crucible-sealed-x7", "crucible-policies-x7",
                    "crucible-evidence-x7", "crucible-hack-2026",
                    "crucible-armorer"):
        assert ('"%s"' % literal) not in src and ("'%s'" % literal) not in src, (
            "%s is typed as a literal in campaign.py" % literal)


# ---------------------------------------------------------------------------
# 2. AN OFFLINE RUN CANNOT BE MISTAKEN FOR AN EXERCISED G7/G8.
#    This is the confusion the whole task existed to end.
# ---------------------------------------------------------------------------

@adk_only
def test_an_offline_run_says_G7_G8_were_not_exercised_in_the_banner(tmp_path,
                                                                    capsys):
    """The banner is what a judge reads on camera."""
    assert C.run(["--out", str(tmp_path / "b.json")]) == 0
    banner = capsys.readouterr().out.split("=" * 78)[1]
    line = [ln for ln in banner.splitlines()
            if ln.startswith("  gate         :")]
    assert len(line) == 1, banner
    assert "NOT EXERCISED" in line[0]
    assert "skip_cloud=True" in line[0]
    assert "RUN INVALID, never a promotion" in line[0]
    # And it must not claim to be something it is not.
    assert "EVALUATED AGAINST LIVE GCP" not in line[0]


@adk_only
def test_an_offline_run_says_G7_G8_were_not_exercised_in_the_bundle(
        captured_wiring):
    """The bundle is what survives the demo. `g7_g8_exercised` is the one field
    a reader has to look at, and it is FALSE here."""
    _kwargs, bundle = captured_wiring
    gate = bundle["summary"]["gate"]
    assert gate["g7_g8_exercised"] is False
    assert gate["cloud_assertions"] == "SKIPPED_OFFLINE"
    assert gate["calls"] == 0
    assert gate["reports"] == []
    assert gate["holdout"]["wired"] is False
    assert gate["implementation"] == "crucible.conductor.real_gate.RealGate"
    assert gate["replaces"] == "promote=lambda c, r: True"
    disclaimer = bundle["summary"]["no_result_may_be_quoted_from_this_run"]
    assert "G7/G8 WERE NOT EXERCISED" in disclaimer
    assert "no G7 or G8 claim may be made from this bundle" in disclaimer


def test_g7_g8_exercised_is_derived_from_findings_and_never_from_the_live_flag():
    """The field must be computed from what the gate DID.

    A `--live` run that halts at the ARMORER before the first candidate
    exercised G7 and G8 exactly as little as an offline one, so a field set from
    `args.live` would be a claim about intent printed as a claim about evidence.
    Driven three ways here, including the one that matters.
    """
    class _FakeGate:
        def __init__(self, skip_cloud, reports):
            self.skip_cloud = skip_cloud
            self.reports = reports

    info = {"cloud_assertions": "LIVE"}
    passing = [{"findings": [rg.finding("G8", "x", rg.PASS)]}]
    unevaluable = [{"findings": [rg.finding("G7/G8", "x", rg.UNEVALUABLE)]}]

    # live, and it really evaluated something
    assert C.gate_summary(_FakeGate(False, passing), info)["g7_g8_exercised"]
    # live, but the loop never reached a candidate -> NOT exercised
    assert not C.gate_summary(_FakeGate(False, []), info)["g7_g8_exercised"]
    # live, called, and every seal assertion came back UNEVALUABLE
    assert not C.gate_summary(_FakeGate(False, unevaluable),
                              info)["g7_g8_exercised"]
    # skip_cloud can never be exercised, whatever the reports say
    assert not C.gate_summary(_FakeGate(True, passing), info)["g7_g8_exercised"]


# ---------------------------------------------------------------------------
# 3. The offline gate REFUSES. It does not quietly promote.
# ---------------------------------------------------------------------------

def _candidate():
    return {"envelope_version": 1,
            "hashed_payload": {"policy_schema_version": 1, "rules": []},
            "lineage": {"version": 1, "parent_hash": "0" * 16,
                        "lineage_hash": "0" * 16}}


class _FakeRecord:
    def __init__(self, round_index=1, hashes=None):
        self.round_index = round_index
        self.hashes = dict(hashes or {"manifest_hash": "m" * 16})


@adk_only
def test_the_offline_gate_raises_RUN_INVALID_rather_than_returning_true(
        captured_wiring):
    """The gate the loop holds, called directly.

    An offline run does not reach it today - the ARMORER has no model and round
    one halts at ARMORER_EXHAUSTED first - so this drives the wired callable
    itself. `absent_or_unevaluable: RUN_INVALID` is G7's own contract, and the
    offline gate is therefore STRICTLY STRICTER than the stand-in it replaced:
    the stand-in promoted every candidate, this promotes none.
    """
    kwargs, _bundle = captured_wiring
    with pytest.raises(rg.GateRunInvalid) as ei:
        kwargs["promote"](_candidate(), _FakeRecord())
    assert "skip_cloud=True" in str(ei.value)
    assert "Nothing was inspected" in str(ei.value)


def test_NEGATIVE_CONTROL_the_stand_in_it_replaces_promoted_everything():
    """Without this, the test above is unfalsifiable: it would pass against any
    gate that raised for any reason. `lambda c, r: True` is a constant function
    - the limiting case of a check that cannot fail - and the delta is stated as
    a test rather than as prose so it stays on the record."""
    stand_in = (lambda c, r: True)
    assert stand_in(_candidate(), _FakeRecord()) is True
    assert stand_in(None, None) is True


# ---------------------------------------------------------------------------
# 4. GateRunInvalid AND GateHalt PROPAGATE. They are not swallowed into a bool.
# ---------------------------------------------------------------------------

_HASHES = {name: "%s" % (chr(97 + i) * 16) for i, name in
           enumerate(REQUIRED_HASHES)}

_BENIGN_CLEAN = {"passed": 26, "total": 26, "near_miss_passed": 14,
                 "near_miss_total": 14, "failed_classes": []}


class _Autopsy:
    record = {"autopsy_id": "aut_000000000001", "attack_family_id": "fam_x",
              "breach_episode_ids": ["ep_000000000001"]}


class _Patch:
    ok = True
    repaired = False
    halt = None
    halt_detail = ""
    verbs_used = ["deny"]
    new_rule_ids = ["r_000000000001"]
    hashed_payload = {"policy_schema_version": 1, "rules": []}


class _Red:
    def propose_round(self, seeds, feedback, n):
        return [{"attack_id": "atk_a00000000001", "family_id": "fam_x",
                 "instruction": "stub"} for _ in range(n)]


class _Coroner:
    def autopsy(self, **kwargs):
        return _Autopsy()


class _Armorer:
    def propose(self, autopsy, policy, index, rejection_feedback=None):
        return _Patch()


def _conductor(promote, round_cap=6):
    """A minimal loop whose ONLY interesting collaborator is the gate.

    STUB-ONLY on everything else, deliberately: what is under test is what
    `Conductor.run` does with a gate that raises, and a real RED/CORONER/ARMORER
    would add cost and non-determinism without adding evidence about that.
    """
    governor = BudgetGovernor(Budget(usd_cap=5.0, token_cap=1_000_000,
                                     round_cap=round_cap, call_cap=100))
    return Conductor(
        red=_Red(), coroner=_Coroner(), armorer=_Armorer(), governor=governor,
        run_episode=lambda attack, policy: {"episode_id": "ep_000000000001"},
        score=lambda ep: {"verdict": "BREACH", "breach": True},
        benign_gate=lambda candidate: dict(_BENIGN_CLEAN),
        promote=promote, hashes=_HASHES,
        seeds=[{"seed": 1}], run_id="run_20260822_000000_5100ff",
        attacks_per_round=2)


def test_GateRunInvalid_propagates_out_of_conductor_run_not_a_False():
    """A bool has room for two of the gate's three outcomes and the missing one
    is the one that voids the run.

    Returning `False` for a G8 failure would downgrade "the separation was never
    real" into "try again next round", and the campaign would print a rejection
    line and keep measuring. `Conductor.run` has no `except` around
    `self.promote(...)` and this is the test that keeps it that way.
    """
    boom = rg.GateRunInvalid(
        [rg.finding("G8", "crucible-armorer holds NO storage role", rg.FAIL,
                    invalidates=True,
                    failure_text=rg.G8_FAILURE_TEXT)],
        rg.G8_FAILURE_TEXT)

    def gate(candidate, record):
        raise boom

    with pytest.raises(rg.GateRunInvalid) as ei:
        _conductor(gate).run({"hashed_payload": {"rules": []}})
    assert "the separation was never real" in str(ei.value)
    assert ei.value.findings[0]["gate"] == "G8"


def test_GateHalt_propagates_out_of_conductor_run_not_a_False():
    """`PROMOTION_ASSERT_FAILED` is a human decision, not the next round."""
    def gate(candidate, record):
        raise rg.GateHalt("PROMOTION_ASSERT_FAILED",
                          "wrote it and could not read it back")

    with pytest.raises(rg.GateHalt) as ei:
        _conductor(gate).run({"hashed_payload": {"rules": []}})
    assert ei.value.reason_code == "PROMOTION_ASSERT_FAILED"


def test_POSITIVE_CONTROL_an_ordinary_rejection_still_returns_a_result():
    """Without this the two tests above pass for the trivial reason that the
    harness explodes on anything.

    A gate returning `False` is an ORDINARY REJECTION: the loop records it,
    feeds back counts and classes, and halts on the second one with a STATUS.
    No exception leaves `run`, and that difference is the whole point.
    """
    result = _conductor(lambda c, r: False).run({"hashed_payload": {"rules": []}})
    assert result.status == "halted"
    assert result.halt == HALT_GATE_REJECTED_TWICE
    assert [r.gate_decision for r in result.rounds] == ["REJECT", "REJECT"]
    assert result.summary()["rejections"] == 2


def test_POSITIVE_CONTROL_a_gate_returning_true_promotes_and_returns():
    """The other arm: `True` is a promotion recorded inside a completed run."""
    result = _conductor(lambda c, r: True, round_cap=1).run(
        {"hashed_payload": {"rules": []}})
    assert result.rounds[0].gate_decision == "PROMOTE"
    assert result.summary()["promotions"] == 1


# ---------------------------------------------------------------------------
# 5. The CAMPAIGN reports them distinctly from a rejection.
# ---------------------------------------------------------------------------

def _conductor_that_raises(exc):
    class _Raiser:
        def __init__(self, **kwargs):
            pass

        def run(self, policy):
            raise exc
    return _Raiser


@adk_only
def test_the_campaign_reports_RUN_INVALID_distinctly_from_a_rejection(
        monkeypatch, tmp_path, capsys):
    """Distinct in all three places a reader looks: the exit code, the printed
    status, and the bundle. An ordinary rejection exits 0 and is a `REJECT`
    inside a completed run, because "the candidate was not good enough" is a
    MEASUREMENT. This is not one.
    """
    exc = rg.GateRunInvalid(
        [rg.finding("G7c", "holdout_touch_count == 2", rg.FAIL,
                    "holdout_touch_count is 9, expected 2", invalidates=True)])
    monkeypatch.setattr(C, "Conductor", _conductor_that_raises(exc))
    out = tmp_path / "invalid.json"

    code = C.run(["--out", str(out)])
    assert code == C.EXIT_RUN_INVALID != 0

    printed = capsys.readouterr().out
    assert "  status       : RUN INVALID" in printed
    assert "RUN INVALID IS NOT A REJECTION" in printed
    assert "INCLUDING THE ONES THAT LOOK GOOD" in printed
    assert "G7c" in printed and "FAIL" in printed   # the findings survive

    bundle = json.loads(out.read_text(encoding="utf-8"))
    summary = bundle["summary"]
    assert summary["status"] == "RUN_INVALID"
    assert summary["gate"]["stop"]["kind"] == "RUN_INVALID"
    assert summary["gate"]["stop"]["exception"] == "GateRunInvalid"
    assert summary["gate"]["stop"]["findings"][0]["gate"] == "G7c"
    # A voided bundle still carries the locks and the floor. It is the bundle a
    # reader most needs and would otherwise least have.
    assert set(summary["hash_locks"]["values"]) == set(REQUIRED_HASHES)
    assert summary["benign_floor_at_v0"]["total"] == 26


@adk_only
def test_the_campaign_reports_a_GATE_HALT_with_its_own_status_and_code(
        monkeypatch, tmp_path, capsys):
    exc = rg.GateHalt("PROMOTION_ASSERT_FAILED", "read-back hash mismatch")
    monkeypatch.setattr(C, "Conductor", _conductor_that_raises(exc))
    out = tmp_path / "halt.json"

    code = C.run(["--out", str(out)])
    assert code == C.EXIT_GATE_HALT
    assert C.EXIT_GATE_HALT != C.EXIT_RUN_INVALID

    printed = capsys.readouterr().out
    assert "  status       : GATE HALT" in printed
    assert "PROMOTION_ASSERT_FAILED" in printed
    bundle = json.loads(out.read_text(encoding="utf-8"))
    assert bundle["summary"]["status"] == "GATE_HALT"
    assert bundle["summary"]["gate"]["stop"]["reason_code"] == \
        "PROMOTION_ASSERT_FAILED"


@adk_only
def test_NEGATIVE_CONTROL_an_ordinary_offline_run_exits_zero_and_is_not_invalid(
        captured_wiring):
    """The contrast the two tests above depend on. This run halts at
    ARMORER_EXHAUSTED - a recorded status inside a completed run - and it is not
    a RUN INVALID and not a gate stop."""
    _kwargs, bundle = captured_wiring
    summary = bundle["summary"]
    assert summary["status"] not in ("RUN_INVALID", "GATE_HALT")
    assert "stop" not in summary["gate"]


# ---------------------------------------------------------------------------
# 6. The LIVE build. Construction only - see the stub-only list at the top.
# ---------------------------------------------------------------------------

def test_the_live_build_turns_the_cloud_assertions_on_and_injects_a_counter(
        tmp_path):
    """STUB-ONLY: this constructs the live gate and starts no gcloud process.
    What it proves is the WIRING - that `--live` produces a gate whose cloud
    assertions are ON, whose G7c counter is a real
    `infra.holdout_touch.HoldoutTouchCounter`, and whose blob IO is `GcsBlobIO`
    pointed at the bucket named in `scripts/gcp-env.sh`.
    """
    gate, info = C.build_gate("run_20260822_000000_5100ff", _locks(), live=True,
                              store_root=str(tmp_path / "g"),
                              holdout_expected=7,
                              holdout_since="2026-08-23T00:00:00Z")
    assert isinstance(gate, rg.RealGate)
    assert gate.skip_cloud is False
    assert isinstance(gate.holdout_touch, HoldoutTouchCounter)
    assert gate.holdout_expected == 7
    # Bucket SOURCED, not retyped.
    blobs = gate.blob_writer.__self__
    assert isinstance(blobs, rg.GcsBlobIO)
    assert blobs.bucket_name == \
        ENV["CRUCIBLE_POLICIES_BUCKET"].replace("gs://", "")
    assert gate.blob_reader.__self__ is blobs
    assert info["cloud_assertions"] == "LIVE"
    assert info["holdout"]["expected_for_this_phase"] == 7


def test_the_live_banner_is_rendered_by_the_same_code_that_prints_it(tmp_path):
    """The live banner has to be quotable in a handoff BEFORE anyone spends a
    model budget to see it, so it is rendered by `gate_banner_lines` - the one
    function `run()` prints from. A second copy of banner prose in a report is a
    second source of truth about what the run claimed.

    STUB-ONLY: this renders the line. It does not run a live campaign, and the
    line's factual claim (that G7/G8 were evaluated) is checked at the END of a
    run by `summary.gate.g7_g8_exercised`, not by the banner.
    """
    _gate, info = C.build_gate("run_20260822_000000_5100ff", _locks(),
                               live=True, store_root=str(tmp_path / "g"),
                               holdout_expected=2,
                               holdout_since="2026-08-23T00:00:00Z")
    lines = C.gate_banner_lines(True, info)
    assert lines[0].startswith("  gate         : REAL. RealGate, promoter "
                               "crucible-gate read from scripts/gcp-env.sh.")
    assert "EVALUATED AGAINST LIVE GCP" in lines[0]
    assert "expected_for_this_phase=2" in lines[0]
    assert "NOT EXERCISED" not in lines[0]
    # The untested path is on the banner, not only in the bundle.
    assert "GcsBlobIO HAS NEVER RUN AGAINST GCS" in lines[1]

    offline = C.gate_banner_lines(False, info)
    assert "G7/G8 NOT EXERCISED" in offline[0]
    assert "EVALUATED AGAINST LIVE GCP" not in offline[0]


def test_the_live_build_declares_GcsBlobIO_as_never_run_against_gcs(tmp_path):
    """The one untested thing on the live path, carried into the bundle rather
    than left in a docstring. `local_blob_io` is the exercised path; the GCS one
    is written from `data-spec.md` 3.1/3.2 and no test calls it, including this
    one."""
    _gate, info = C.build_gate("run_20260822_000000_5100ff", _locks(),
                               live=True, store_root=str(tmp_path / "g"),
                               holdout_expected=2,
                               holdout_since="2026-08-23T00:00:00Z")
    joined = " ".join(info["untested_against_live_gcs"])
    assert "GcsBlobIO" in joined
    assert "NO TEST COVERS THEM" in joined


def test_the_offline_build_injects_no_counter_and_skips_the_cloud(tmp_path):
    """`holdout_touch` has NO DEFAULT in `RealGate` precisely so that "nothing
    computed this" cannot be mistaken for "the count was zero". Offline there is
    nothing to count, so nothing is injected - and `skip_cloud` short-circuits
    before G7c is even reached."""
    gate, info = C.build_gate("run_20260822_000000_5100ff", _locks(),
                              live=False, store_root=str(tmp_path / "g"))
    assert gate.skip_cloud is True
    assert gate.holdout_touch is None
    assert info["holdout"]["wired"] is False
    findings = gate.preflight()
    assert [f["status"] for f in findings] == [rg.UNEVALUABLE]


def test_live_without_holdout_expected_refuses_before_any_model_is_built():
    """`contracts/gate_rule.v1.yaml:205` is `holdout_touch_count ==
    expected_for_this_phase`, and the PHASE decides the number.

    `measurement-spec.md`'s absolute ceiling of 2 was the defect: one evaluation
    phase reads 18-24 sealed instances, so a fixed 2 marks the run INVALID the
    first time it is used correctly, and a guard that fires on correct behaviour
    is not a guard. The campaign does not know its own phase count, so it
    refuses rather than inventing one - and it refuses BEFORE the model client
    is constructed, because a precondition checked after six rounds of model
    spend is a precondition checked too late.
    """
    with pytest.raises(SystemExit) as ei:
        C.run(["--live"])
    message = str(ei.value)
    assert "--holdout-expected" in message
    assert "expected_for_this_phase" in message
    assert "NEEDS-ERIC.md item 12" in message


def test_the_wiring_does_not_settle_the_open_canary_question(tmp_path):
    """`docs/NEEDS-ERIC.md` item 12 - whether the counter should exclude
    `families/_probe/canary.txt` - is Eric's ruling to make, and this lane wired
    what exists without touching the scoping.

    So: the campaign passes NO `permitted_principals` and NO custom filter, and
    the counter's permitted set is still exactly what `holdout_touch.py` decides
    on its own. If the wiring had narrowed or widened it, the question would
    have been answered by a side effect.
    """
    gate, _info = C.build_gate("run_20260822_000000_5100ff", _locks(),
                               live=True, store_root=str(tmp_path / "g"),
                               holdout_expected=2,
                               holdout_since="2026-08-23T00:00:00Z")
    counter = gate.holdout_touch
    expected = {"%s@%s.iam.gserviceaccount.com"
                % (ENV["SA_SEALED_EVAL"], ENV["CRUCIBLE_PROJECT"])}
    assert counter.permitted_principals == expected
    assert counter.bucket == ENV["CRUCIBLE_SEALED_BUCKET"]


# ---------------------------------------------------------------------------
# 7. The ledger the gate promotes into is real and carries the five locks.
# ---------------------------------------------------------------------------

def test_the_gate_ledger_opens_the_run_with_the_hash_locks(tmp_path):
    """`Ledger.open_run` refuses a run whose locks are missing, and the ledger's
    column is `target_hash` while the conductor's lock is `target_agent_hash`.
    ONE value, two schemas that both already existed; the mapping is asserted
    here so a rename on either side is loud rather than a `None` in a column.
    """
    locks = _locks()
    gate, info = C.build_gate("run_20260822_000000_5100ff", locks, live=False,
                              store_root=str(tmp_path / "g"))
    row = gate.ledger.get_run("run_20260822_000000_5100ff")
    assert row["target_hash"] == locks.values["target_agent_hash"]
    assert row["manifest_hash"] == locks.values["manifest_hash"]
    assert row["objective_set_hash"] == locks.values["objective_set_hash"]
    assert row["gate_rule_hash"] == locks.values["gate_rule_hash"]
    assert row["derived_schema_hash"] == locks.values["derived_schema_hash"]
    assert info["ledger"].endswith("ledger.sqlite3")
