"""test_real_gate.py - the real GATE, not `lambda c, r: True`.

`crucible.conductor.real_gate.RealGate` is a drop-in for `campaign.py`'s gate
stand-in: same call signature `(candidate, record) -> bool`, same place in
`Conductor(..., promote=...)`. What changes is that it looks at something. The
stand-in returns PROMOTE for every candidate having inspected nothing, so **G7
and G8 - the two gates whose failure mode is RUN INVALID - had never run.**

WHICH ASSERTIONS HERE ARE STUB-ONLY. READ THIS BEFORE TRUSTING A GREEN RUN.
==========================================================================
This lane is READ-ONLY against GCP by contract, so nothing below mutates a
bucket, an IAM binding, or an object. That splits the suite in two:

REAL, and exercised against the real thing:
  * the promoter identity, read from the REAL `scripts/gcp-env.sh` through the
    REAL `verify_iam.load_env`. `test_the_promoter_is_the_gate_*` genuinely
    fails red if that file ever names the Armorer.
  * the IAM predicates, which are `infra.verify_iam`'s own, already driven to
    red and green by its 35-case `--selftest`.
  * the promotion write path end to end through `local_blob_io`: the bytes
    really round-trip through a real file on disk, so `crucible.gate.promote`'s
    recompute-from-bytes assertion is doing real work.
  * the ledger, a real (in-memory) SQLite `Ledger`.

STUB-ONLY. The double is looser than the real API and these prove less than
they look like they prove:
  1. **The GCS backend (`GcsBlobIO`) is not exercised at all.** No test here
     touches it. Its `if_generation_match=0` create-only precondition, its
     412-benign-duplicate branch, and its generation-pinned read-back are
     written from `data-spec.md` 3.1/3.2 and have never been executed against
     the real API. A fix that only holds where the double is looser than the
     real API is not a fix - so it is not stubbed, it is simply UNTESTED and
     said so.
  2. **Every live IAM document is a synthetic dict** passed through `iam_fetch`.
     These prove the WIRING (which predicate is asked which question, and what
     the gate does with each answer). They prove nothing about the live project.
     The live assertion is `python infra/verify_iam.py`, which is a separate
     command against real GCP.
  3. **Every impersonation probe is a fake subprocess.** `classify_probe` is a
     pure function and is genuinely tested; whether `gcloud` actually returns
     those strings is evidence from the live run, recorded in the report, not
     from here.
  4. **G7c is injected in every test HERE**, as a bare lambda. The tested
     behaviour in this file is what the GATE does with a count: that an absent
     counter invalidates the run rather than defaulting to zero, and that a
     count above the expected value invalidates rather than rejects.
     CORRECTED 2026-08-22: this paragraph used to say "the live project has no
     `auditConfigs` block, so the number does not exist yet." Data Access
     logging is now enabled and `infra/holdout_touch.py` reads it;
     `tests/test_holdout_touch.py` drives that counter against entries copied
     out of the real audit log. The stale sentence is left visible here as the
     correction it is, because it also reached the G7/G8 proof artifact.
"""

import pathlib

import pytest

from crucible import gate as gate_pkg
from crucible.conductor import real_gate as rg
from crucible.ledger import Ledger

REPO = pathlib.Path(__file__).resolve().parent.parent
RUN = "run_20260822_120000_abc123"
NOW = "2026-08-22T12:00:00Z"
LOCKS = {"manifest_hash": "m" * 16, "objective_set_hash": "o" * 16,
         "gate_rule_hash": "g" * 16, "target_hash": "t" * 16}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

class FakeRecord:
    """The two attributes `RealGate` reads off a `conductor.RoundRecord`."""

    def __init__(self, round_index=1, hashes=None):
        self.round_index = round_index
        self.hashes = dict(hashes if hashes is not None else LOCKS)


def candidate(threshold=50000, n_rules=1):
    return {
        "envelope_version": 1,
        "hashed_payload": {
            "policy_schema_version": 1,
            "target_manifest_hash": LOCKS["manifest_hash"],
            "rules": [{"rule_id": "r_%012d" % i, "verb": "deny",
                       "cap_selector": "CAP_MOVES_MONEY",
                       "when": [{"path": "amount_minor", "op": "gt",
                                 "value": threshold + i}]}
                      for i in range(n_rules)],
        },
        "lineage": {"version": 1, "parent_hash": "0" * 16,
                    "lineage_hash": "0" * 16},
    }


ENV = rg.gcp_env(REPO)


def sa(name):
    return "serviceAccount:%s@%s.iam.gserviceaccount.com" % (
        name, ENV["CRUCIBLE_PROJECT"])


GOOD_BUCKET_META = {
    "iamConfiguration": {"uniformBucketLevelAccess": {"enabled": True},
                         "publicAccessPrevention": "enforced"},
    "versioning": {"enabled": True},
    "retentionPolicy": {"retentionPeriod": "1209600"},
}


def fake_fetch(*, policies_bindings=None, sealed_bindings=None,
               project_bindings=None, policies_meta=None, sealed_meta=None,
               explode=None):
    """A synthetic replacement for `verify_iam.gcloud_json`. STUB-ONLY: it
    proves which question the gate asks of which document, not what the live
    project contains."""
    def _fetch(args, what):
        if explode:
            raise RuntimeError(explode)
        if args[1] == "projects":
            return {"bindings": list(project_bindings or [])}
        if args[3] == "get-iam-policy":
            if ENV["CRUCIBLE_POLICIES_BUCKET"] in args:
                return {"bindings": list(policies_bindings or [])}
            return {"bindings": list(sealed_bindings or [])}
        if ENV["CRUCIBLE_POLICIES_BUCKET"] in args:
            return dict(policies_meta or GOOD_BUCKET_META)
        return dict(sealed_meta or GOOD_BUCKET_META)
    return _fetch


CLEAN_POLICIES = [{"role": "roles/storage.objectCreator",
                   "members": [sa(ENV["SA_GATE"])]},
                  {"role": "roles/storage.objectViewer",
                   "members": [sa(ENV["SA_GATE"])]}]
CLEAN_PROJECT = [{"role": "roles/owner", "members": ["user:eric@example.invalid"]},
                 {"role": "roles/aiplatform.user",
                  "members": [sa(ENV["SA_ARMORER"])]}]

CLEAN_FETCH = fake_fetch(policies_bindings=CLEAN_POLICIES,
                         project_bindings=CLEAN_PROJECT)


def clean_probe_run(argv):
    """Every identity behaves as the boundary requires. STUB-ONLY.

    The listed path moved 2026-08-22 with the canary itself - see
    `test_the_probe_prefix_is_deliberately_not_the_corpus_prefix`.
    """
    joined = " ".join(argv)
    if ENV["SA_SEALED_EVAL"] in joined:
        return 0, "_probe/canary.txt\n"
    return 1, ("ERROR: does not have storage.objects.list access to the Google "
               "Cloud Storage bucket. Permission 'storage.objects.list' denied")


def build(tmp_path, ledger, **over):
    writer, reader = rg.local_blob_io(tmp_path / "policies")
    kwargs = dict(ledger=ledger, run_id=RUN, blob_writer=writer,
                  blob_reader=reader, repo_root=REPO,
                  holdout_touch=lambda: 2, iam_fetch=CLEAN_FETCH,
                  probe_run=clean_probe_run, clock=lambda: NOW,
                  sleep=lambda _s: None)
    kwargs.update(over)
    return rg.build_real_gate(**kwargs)


@pytest.fixture()
def led():
    with Ledger(":memory:") as l:
        l.open_run(RUN, NOW, LOCKS)
        yield l


# ---------------------------------------------------------------------------
# THE GRANT DIRECTION. This is the test that must fail red if it ever inverts.
# ---------------------------------------------------------------------------

def test_the_promoter_is_the_gate_and_is_read_from_gcp_env_not_typed_here():
    """REAL, not stub: this reads `scripts/gcp-env.sh` through the same reader
    every other gate script uses.

    THE IDENTITY THAT AUTHORS A CANDIDATE IS NOT THE IDENTITY THAT PROMOTES IT.
    If `SA_GATE` in that file ever becomes the Armorer, or `sa-warden`, or
    anything other than what `crucible/gate/promote.py` enforces, this fails.
    """
    promoter = rg.promoter_identity(REPO)
    assert promoter == "crucible-gate"
    assert promoter == ENV["SA_GATE"]
    assert promoter != ENV["SA_ARMORER"]
    assert not promoter.startswith("sa-"), "sa-* is dead vocabulary"
    assert promoter != "sa-warden", "the promoter is NEVER sa-warden"


def test_promoter_identity_fails_red_when_the_gate_and_armorer_are_one_identity(
        monkeypatch):
    """NEGATIVE CONTROL for the check above: drive it to red.

    A check that has only ever been observed passing is not a check. This is the
    inverted grant direction, which `data-spec.md` records as having already
    been proposed backwards once.
    """
    monkeypatch.setitem(rg._ENV_CACHE, "SENTINEL",
                        dict(ENV, SA_GATE="crucible-armorer",
                             SA_ARMORER="crucible-armorer"))
    with pytest.raises(rg.GateRunInvalid) as ei:
        rg.promoter_identity("SENTINEL")
    assert "the separation was never real" in str(ei.value)


def test_promoter_identity_fails_red_on_a_silent_rename(monkeypatch):
    """`gcp-env.sh` SA_GATE and `promote.py`'s literal are two spellings of one
    fact. Diverging them must be loud, not silently unpromotable."""
    monkeypatch.setitem(rg._ENV_CACHE, "SENTINEL2",
                        dict(ENV, SA_GATE="sa-warden"))
    with pytest.raises(rg.GateRunInvalid) as ei:
        rg.promoter_identity("SENTINEL2")
    assert "diverged" in str(ei.value)


def test_a_gate_built_with_the_wrong_promoter_never_gets_built(monkeypatch, led,
                                                               tmp_path):
    """Construction time, not first-write time. A gate built with the wrong
    promoter is not a gate that rejects later."""
    monkeypatch.setitem(rg._ENV_CACHE, str(tmp_path),
                        dict(ENV, SA_GATE="crucible-armorer",
                             SA_ARMORER="crucible-armorer"))
    with pytest.raises(rg.GateRunInvalid):
        build(tmp_path, led, repo_root=tmp_path)


def test_the_object_name_is_imported_from_l1_not_respelled():
    """The GCS object path is a string two modules would eventually disagree
    about. There is one of it."""
    assert rg.object_name is gate_pkg.object_name


# ---------------------------------------------------------------------------
# The drop-in contract
# ---------------------------------------------------------------------------

def test_the_signature_is_the_stand_ins_signature(led, tmp_path):
    """`campaign.py` wires `promote=lambda c, r: True`. This must slot in
    unchanged: two positional arguments, a bool out."""
    gate = build(tmp_path, led)
    out = gate(candidate(), FakeRecord())
    assert out is True


def test_a_promotion_really_round_trips_bytes_through_a_file(led, tmp_path):
    """REAL: the ledger row, the object on disk, and the hash in the object's
    NAME all have to agree, and the hash is recomputed from the bytes read back
    off the file rather than from the dict still in memory."""
    gate = build(tmp_path, led)
    assert gate(candidate(), FakeRecord()) is True

    versions = led.versions(RUN)
    assert len(versions) == 1
    v = versions[0]
    assert v["version"] == 1
    assert v["promoted_by"] == "crucible-gate"
    assert v["manifest_hash"] == LOCKS["manifest_hash"]

    name = rg.object_name(RUN, 1, v["policy_hash_full"])
    on_disk = (tmp_path / "policies" / name)
    assert on_disk.exists(), "no object was written"
    assert rg.__dict__["object_name"](RUN, 1, v["policy_hash_full"]) == name
    assert v["policy_hash_full"][:16] in name

    from crucible.gate import compute_policy_hash
    assert compute_policy_hash(on_disk.read_bytes()) == v["policy_hash_full"]


def test_the_gate_records_a_findings_report_per_call(led, tmp_path):
    gate = build(tmp_path, led)
    gate(candidate(), FakeRecord(round_index=3))
    assert len(gate.reports) == 1
    report = gate.reports[0]
    assert report["round_index"] == 3
    assert report["decision"] == "PROMOTE"
    gates = {f["gate"] for f in report["findings"]}
    assert gates >= {"G7a", "G7b", "G7b2/G8", "G7c", "G8"}
    assert all(f["status"] == rg.PASS for f in report["findings"])


# ---------------------------------------------------------------------------
# G8. RUN INVALID, never a rejection.
# ---------------------------------------------------------------------------

def test_the_inverted_grant_direction_invalidates_the_run(led, tmp_path):
    """STUB-ONLY on the document, REAL on the consequence: the Armorer holding
    ANY role on the policies bucket is `RUN INVALID`, with G8's own failure
    text, and it must NOT come back as `False`.

    Returning False would downgrade "the separation was never real" into "try
    again next round" and the campaign would keep measuring.
    """
    fetch = fake_fetch(
        policies_bindings=CLEAN_POLICIES + [
            {"role": "roles/storage.objectCreator",
             "members": [sa(ENV["SA_ARMORER"])]}],
        project_bindings=CLEAN_PROJECT)
    gate = build(tmp_path, led, iam_fetch=fetch)
    with pytest.raises(rg.GateRunInvalid) as ei:
        gate(candidate(), FakeRecord())
    assert "the separation was never real" in str(ei.value)
    assert led.versions(RUN) == [], "nothing may be promoted on an invalid run"


def test_a_read_only_grant_to_the_armorer_is_still_invalid(led, tmp_path):
    """`objectViewer` is not write access, and it is still a role on that bucket.
    The assertion is NO storage role, not no WRITE role."""
    fetch = fake_fetch(
        policies_bindings=CLEAN_POLICIES + [
            {"role": "roles/storage.objectViewer",
             "members": [sa(ENV["SA_ARMORER"])]}],
        project_bindings=CLEAN_PROJECT)
    with pytest.raises(rg.GateRunInvalid):
        build(tmp_path, led, iam_fetch=fetch)(candidate(), FakeRecord())


def test_the_promoter_holding_overwrite_rights_invalidates_the_run(led, tmp_path):
    """objectCreator is CREATE ONLY. objectAdmin would make the immutability
    claim convention wearing an IAM costume."""
    fetch = fake_fetch(
        policies_bindings=CLEAN_POLICIES + [
            {"role": "roles/storage.objectAdmin",
             "members": [sa(ENV["SA_GATE"])]}],
        project_bindings=CLEAN_PROJECT)
    with pytest.raises(rg.GateRunInvalid):
        build(tmp_path, led, iam_fetch=fetch)(candidate(), FakeRecord())


def test_a_locked_retention_policy_is_a_failure_not_a_stronger_pass(led, tmp_path):
    """G8 asserts the policy EXISTS, never that it is locked. A locked policy
    cannot be shortened or removed by anyone including the project owner, and
    blocks the data-spec 7.3 teardown for 14 days past the last write."""
    meta = dict(GOOD_BUCKET_META,
                retentionPolicy={"retentionPeriod": "1209600", "isLocked": True})
    fetch = fake_fetch(policies_bindings=CLEAN_POLICIES,
                       project_bindings=CLEAN_PROJECT, policies_meta=meta)
    with pytest.raises(rg.GateRunInvalid) as ei:
        build(tmp_path, led, iam_fetch=fetch)(candidate(), FakeRecord())
    assert "LOCKED" in str(ei.value)


def test_versioning_off_on_the_policies_bucket_invalidates_the_run(led, tmp_path):
    """G8's fourth assertion, which nothing checked until 2026-08-22."""
    meta = dict(GOOD_BUCKET_META, versioning={"enabled": False})
    fetch = fake_fetch(policies_bindings=CLEAN_POLICIES,
                       project_bindings=CLEAN_PROJECT, policies_meta=meta)
    with pytest.raises(rg.GateRunInvalid) as ei:
        build(tmp_path, led, iam_fetch=fetch)(candidate(), FakeRecord())
    assert "versioning is OFF" in str(ei.value)


def test_a_project_level_basic_role_invalidates_the_run(led, tmp_path):
    """CONVENTIONS 10a - the case the bucket grep structurally cannot see.
    Every bucket carries default legacy projectViewer/projectEditor bindings, so
    `roles/viewer` at the project level grants READ on the sealed bucket with no
    binding that names it, and the bucket-scoped grep returns 0 the whole time.
    """
    fetch = fake_fetch(
        policies_bindings=CLEAN_POLICIES,
        project_bindings=CLEAN_PROJECT + [
            {"role": "roles/viewer", "members": [sa(ENV["SA_ARMORER"])]}])
    with pytest.raises(rg.GateRunInvalid) as ei:
        build(tmp_path, led, iam_fetch=fetch)(candidate(), FakeRecord())
    assert "BASIC role" in str(ei.value)


def test_a_failed_fetch_is_unevaluable_and_never_an_empty_policy(led, tmp_path):
    """The failure `verify_iam.py` was written to prevent: an empty policy
    passes every 'holds nothing' predicate, so a misspelled bucket and a clean
    boundary produce the same output."""
    fetch = fake_fetch(explode="bucket does not exist")
    gate = build(tmp_path, led, iam_fetch=fetch)
    with pytest.raises(rg.GateRunInvalid) as ei:
        gate(candidate(), FakeRecord())
    assert "must not be read as a pass" in str(ei.value)


# ---------------------------------------------------------------------------
# G7a. The impersonation probe, classified. `classify_probe` is a pure function
# and this block is the REAL half of the probe testing.
# ---------------------------------------------------------------------------

_STORAGE_DENIAL = ("ERROR: Permission 'storage.objects.list' denied on resource "
                   "'//storage.googleapis.com/projects/_/buckets/crucible-sealed-x7'")
_IMPERSONATION_DENIAL = (
    "ERROR: PERMISSION_DENIED: Failed to impersonate "
    "[crucible-coroner@crucible-hack-2026.iam.gserviceaccount.com]. Permission "
    "'iam.serviceAccounts.getAccessToken' denied on resource")


@pytest.mark.parametrize("expect,rc,out,want", [
    ("allow", 0, "_probe/canary.txt\n", rg.PASS),
    ("allow", 0, "", rg.UNEVALUABLE),            # listed nothing: no control
    ("allow", 1, _STORAGE_DENIAL, rg.UNEVALUABLE),   # control dead: proves nothing
    ("deny", 1, _STORAGE_DENIAL, rg.PASS),
    ("deny", 0, "_probe/canary.txt\n", rg.FAIL),   # boundary absent
    ("deny", 1, "ERROR: connection reset by peer", rg.UNEVALUABLE),
    ("deny", 1, _IMPERSONATION_DENIAL, rg.UNEVALUABLE),
    ("allow", 1, _IMPERSONATION_DENIAL, rg.UNEVALUABLE),
])
def test_classify_probe_every_branch(expect, rc, out, want):
    status, detail = rg.classify_probe(expect, rc, out)
    assert status == want, detail


def test_an_impersonation_layer_refusal_is_never_scored_as_a_refused_boundary():
    """THE BUG `infra/prove-armorer-403.sh` ALREADY PAID FOR, and the live state
    that makes it live rather than historical.

    Probed read-only on 2026-08-22, `crucible-coroner` - which
    `contracts/gate_rule.v1.yaml` G7a names in `repeat_for` - fails at the
    IMPERSONATION layer, because the operator holds
    `roles/iam.serviceAccountTokenCreator` on sealed-eval, armorer and red but
    NOT on coroner. A classifier that credits any non-zero exit would print a
    green line for a boundary it never reached.
    """
    status, detail = rg.classify_probe("deny", 1, _IMPERSONATION_DENIAL)
    assert status == rg.UNEVALUABLE
    assert "never became this identity" in detail


def test_a_probe_positive_control_that_cannot_read_makes_every_denial_useless(
        led, tmp_path):
    """A misspelled bucket, a deleted bucket, and a project the caller cannot
    see all return 403. Without the positive control, a screen recording of one
    red 403 is compatible with the sealed corpus sitting wide open."""
    def broken(argv):
        return 1, _STORAGE_DENIAL          # even sealed-eval is refused
    gate = build(tmp_path, led, probe_run=broken)
    with pytest.raises(rg.GateRunInvalid) as ei:
        gate(candidate(), FakeRecord())
    assert "uninformative" in str(ei.value)


def test_the_seal_probe_covers_all_four_identities_including_the_coroner():
    """`repeat_for: [crucible-red, crucible-coroner]` plus the Armorer, plus the
    positive control. `prove-armorer-403.sh` probes only three and has never
    probed the Coroner."""
    seen = []

    def spy(argv):
        seen.append(" ".join(argv))
        return clean_probe_run(argv)

    findings = rg.seal_probe_findings(ENV, run=spy)
    assert len(findings) == 4
    for name in (ENV["SA_SEALED_EVAL"], ENV["SA_ARMORER"], ENV["SA_RED"],
                 ENV["SA_CORONER"]):
        assert any(name in cmd for cmd in seen), name
    assert all(f["status"] == rg.PASS for f in findings)


def test_the_probe_prefix_is_deliberately_not_the_corpus_prefix():
    """Eric's ruling on `docs/NEEDS-ERIC.md` item 12, executed 2026-08-22: the
    canary was MOVED out of `families/`, not excluded from the count.

        was:  gs://crucible-sealed-x7/families/_probe/canary.txt
        now:  gs://crucible-sealed-x7/_probe/canary.txt
        gs://crucible-sealed-x7/families/  is now EMPTY

    An exclusion would have been a permanent named hole and would have meant the
    gate declares which reads do not count - self-certification, one layer over
    from the thing G8 exists to prevent.

    THE FAILURE THIS TEST GUARDS IS SILENT AND GREEN-LOOKING. Left at
    `families/**` the probe matches ZERO objects, so the PERMITTED identity
    exits 0 having listed nothing, `classify_probe` files it UNEVALUABLE, and
    `absent_or_unevaluable: RUN_INVALID` voids the run - while three of the four
    probe lines still read PASS. Measured read-only against the live bucket
    2026-08-22: `families/**` -> rc=0, zero objects listed; `_probe/**` -> rc=0,
    `_probe/canary.txt`.

    So the probe prefix and the counted namespace differ ON PURPOSE, and
    re-unifying them "for consistency" reintroduces the exact defect. Pinned
    here rather than left to the comment in `real_gate._PROBE_PREFIX`, because a
    comment cannot fail.
    """
    argv = rg._probe_argv(ENV, ENV["SA_SEALED_EVAL"])          # noqa: SLF001
    target = argv[4]
    assert target.endswith("/_probe/**"), target
    assert "/families/" not in target, (
        "the probe is back inside the corpus prefix, which is now empty - the "
        "positive control lists nothing and every denial becomes uninformative")
    # All four arms use the one prefix. `crucible-sealed-eval` holds
    # objectViewer BUCKET-WIDE with no IAM condition and UBLA is ON, so there is
    # no per-prefix grant for a second prefix to exercise.
    for name in (ENV["SA_ARMORER"], ENV["SA_RED"], ENV["SA_CORONER"]):
        assert rg._probe_argv(ENV, name)[4] == target          # noqa: SLF001


def test_the_probe_command_never_types_a_bucket_or_project_name():
    """G7 and G8 grep literal strings; a typo produces an unevaluable gate, and
    an unevaluable gate is a check that cannot fail."""
    argv = rg._probe_argv(ENV, ENV["SA_ARMORER"])
    assert ENV["CRUCIBLE_SEALED_BUCKET"] in " ".join(argv)
    assert ENV["CRUCIBLE_PROJECT"] in " ".join(argv)
    src = (REPO / "crucible" / "conductor" / "real_gate.py").read_text(
        encoding="utf-8")
    for literal in ("crucible-sealed-x7", "crucible-policies-x7",
                    "crucible-evidence-x7", "crucible-hack-2026"):
        assert ('"%s"' % literal) not in src and ("'%s'" % literal) not in src, (
            "%s is typed as a literal in real_gate.py" % literal)


# ---------------------------------------------------------------------------
# G7c. Absent is not zero.
# ---------------------------------------------------------------------------

def test_a_missing_holdout_counter_invalidates_the_run_rather_than_defaulting(
        led, tmp_path):
    """`absent_or_unevaluable: RUN_INVALID`. Defaulting to 0 would print a green
    G7c computed from a log nobody queried. Note this is about the GATE, not
    about the log: since 2026-08-22 the log exists and `infra/holdout_touch.py`
    reads it, and a gate that was not wired to it must still say so."""
    gate = build(tmp_path, led, holdout_touch=None)
    with pytest.raises(rg.GateRunInvalid) as ei:
        gate(candidate(), FakeRecord())
    assert "G7c" in str(ei.value)
    assert "Defaulting it" in str(ei.value)


def test_a_holdout_count_above_the_expected_value_fails(led, tmp_path):
    """Any read from another SA, or any count above 2, marks the run INVALID."""
    gate = build(tmp_path, led, holdout_touch=lambda: 3)
    with pytest.raises(rg.GateRunInvalid):
        gate(candidate(), FakeRecord())


def test_a_holdout_counter_that_raises_is_unevaluable_not_absent(led, tmp_path):
    def boom():
        raise RuntimeError("bigquery dataset crucible_sealed not found")
    gate = build(tmp_path, led, holdout_touch=boom)
    with pytest.raises(rg.GateRunInvalid) as ei:
        gate(candidate(), FakeRecord())
    assert "the counter raised" in str(ei.value)


# ---------------------------------------------------------------------------
# G2 / the read-back. NEGATIVE CONTROLS on the promotion assertion itself.
# ---------------------------------------------------------------------------

def test_a_deliberately_corrupted_readback_halts_after_its_retries(led, tmp_path):
    """THE CHECK THE WHOLE WRITE PATH EXISTS FOR, driven to red.

    `crucible.gate.promote` recomputes the hash FROM THE BYTES it reads back.
    Hand it a reader that returns different bytes and it must refuse - three
    times, per `data-spec.md` 3.2 - and then HALT. It must NOT come back as a
    rejection, and nothing may reach the ledger.
    """
    writer, _reader = rg.local_blob_io(tmp_path / "policies")
    attempts = []

    def corrupt_reader(name):
        attempts.append(name)
        return b'{"rules":[]}'

    gate = build(tmp_path, led, blob_writer=writer, blob_reader=corrupt_reader)
    with pytest.raises(rg.GateHalt) as ei:
        gate(candidate(), FakeRecord())
    assert ei.value.reason_code == "PROMOTION_ASSERT_FAILED"
    assert len(attempts) == 3, "data-spec 3.2 retries the whole promotion x3"
    assert led.versions(RUN) == []


def test_a_readback_that_cannot_read_at_all_also_halts(led, tmp_path):
    """"wrote it but could not read it back" - the named hazard: a create API
    can return 200 and fail asynchronously."""
    writer, _reader = rg.local_blob_io(tmp_path / "policies")

    def absent_reader(name):
        raise FileNotFoundError(name)

    gate = build(tmp_path, led, blob_writer=writer, blob_reader=absent_reader)
    with pytest.raises(rg.GateHalt):
        gate(candidate(), FakeRecord())


def test_convergence_is_not_retried_and_is_not_a_halt_loop(led, tmp_path):
    """Hash equality with the head IS the convergence signal. Retrying it three
    times produces the same answer three times."""
    gate = build(tmp_path, led)
    same = candidate()
    assert gate(same, FakeRecord(round_index=1)) is True
    from crucible.gate import PromotionError
    with pytest.raises(PromotionError) as ei:
        gate(same, FakeRecord(round_index=2))
    assert ei.value.code == "E_CONVERGED"


def test_a_second_distinct_candidate_promotes_to_v2_and_chains(led, tmp_path):
    """The positive control for the two tests above: the write path really does
    work when nothing is wrong, so their red is about the corruption and not
    about the harness."""
    gate = build(tmp_path, led)
    assert gate(candidate(threshold=50000), FakeRecord(round_index=1)) is True
    assert gate(candidate(threshold=60000), FakeRecord(round_index=2)) is True
    versions = led.versions(RUN)
    assert [v["version"] for v in versions] == [1, 2]
    assert versions[1]["parent_hash"] == versions[0]["policy_hash"]


def test_a_round_record_without_a_manifest_hash_invalidates_the_run(led, tmp_path):
    """Ruling 20. A policy version written without a manifest_hash cannot say
    which manifest its rules were learned against."""
    gate = build(tmp_path, led)
    with pytest.raises(rg.GateRunInvalid) as ei:
        gate(candidate(), FakeRecord(hashes={}))
    assert "manifest_hash" in str(ei.value)


def test_a_candidate_without_a_hashed_payload_halts(led, tmp_path):
    gate = build(tmp_path, led)
    with pytest.raises(rg.GateHalt):
        gate({"envelope_version": 1}, FakeRecord())


# ---------------------------------------------------------------------------
# The stand-in it replaces
# ---------------------------------------------------------------------------

def test_the_stand_in_it_replaces_returns_true_for_everything():
    """Stated as a test so the delta is on the record rather than in prose. The
    campaign's gate hook is `lambda c, r: True`: a constant function, the
    limiting case of a check that cannot fail."""
    stand_in = (lambda c, r: True)
    assert stand_in(None, None) is True
    assert stand_in({"anything": "at all"}, None) is True
