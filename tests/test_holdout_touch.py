"""test_holdout_touch.py - G7(c), the counter that must be able to be non-zero.

`infra.holdout_touch` closes the one G7 assertion that had no implementation.
Until it landed, `scripts/probe-g7-g8.py` passed `holdout_touch=None`, G7c
reported UNEVALUABLE, and `absent_or_unevaluable: RUN_INVALID` meant no scored
run was possible.

WHAT THESE TESTS ARE ACTUALLY FOR
=================================
Not "does it return a number". **A counter that always returns 0 is
indistinguishable from a seal nobody touched, and it scores G7c PASS while
measuring nothing.** That is this project's signature failure mode and the fix
for it is the likeliest place to reintroduce it. So the majority of what
follows drives the counter to UNEVALUABLE - every route by which this query
could quietly answer 0 for a reason other than "nobody read the holdout":

    a window the log never covered      test_a_window_before_the_floor_*
    audit logging off / removed         test_*_audit_config_*
    a filter that matches nothing       test_the_canary_*     <- the big one
    a failed fetch                      test_a_failed_log_read_*
    a truncated result                  test_a_result_at_the_cap_*

and one drives it to RUN INVALID by catching a real intrusion
(`test_a_granted_read_from_an_unpermitted_principal_*`).

WHICH ASSERTIONS HERE ARE STUB-ONLY. READ BEFORE TRUSTING A GREEN RUN.
======================================================================
REAL, and exercised against the real thing:
  * `LIVE_ENTRIES` is NOT synthetic. It is the verbatim (field-trimmed) result
    of `gcloud logging read` against `crucible-hack-2026` on 2026-08-22,
    recording one impersonated `ls -r` and one `cat` by `crucible-sealed-eval`
    plus one denied `cat` by `crucible-armorer` on the sealed bucket. Every
    classification test below runs against the shapes GCS actually emits,
    including the two that a plausible implementation gets wrong: a
    `granted: true` entry carrying `status.code: 5`, and an `objects.get` whose
    resource is a PREFIX rather than an object.
  * The names in the filter come from the REAL `scripts/gcp-env.sh` through the
    REAL `verify_iam.load_env`. `test_the_filter_*` fails red if a bucket name
    is ever retyped instead of sourced.
  * `storage_data_read_enabled` is exercised against the REAL live policy shape
    (`LIVE_AUDIT_CONFIGS`, copied from `gcloud projects get-iam-policy`).

STUB-ONLY, and these prove less than they look like they prove:
  1. **`gcloud_log_read` is never executed.** Every test injects `log_read`.
     What is tested is the counter's REASONING about results, not that gcloud
     returns them. The live evidence for that is the transcript that produced
     `LIVE_ENTRIES` and the artifact `scripts/probe-g7-g8.py` writes.
  2. **The `--limit` cap semantics are stubbed.** `test_a_result_at_the_cap_*`
     proves the counter refuses a full page; whether Cloud Logging pages
     exactly this way at 1000 has not been observed.
  3. **Ingestion lag is not tested.** `settle_seconds` is passed to an injected
     sleep and asserted to be called. Whether any particular delay is long
     enough is not a thing a unit test can establish, and the docstring says so.
  4. **The BigQuery half of the holdout is not covered at all**, by this module
     or these tests. `bigquery.googleapis.com` has no auditConfig on the live
     project.
"""

import pathlib

import pytest

from infra import holdout_touch as ht
from infra import verify_iam

REPO = pathlib.Path(__file__).resolve().parent.parent
ENV = verify_iam.load_env(str(REPO))

PROJECT = ENV["CRUCIBLE_PROJECT"]
SEALED = ENV["CRUCIBLE_SEALED_BUCKET"]
EVAL_SA = "%s@%s.iam.gserviceaccount.com" % (ENV["SA_SEALED_EVAL"], PROJECT)
ARMORER_SA = "%s@%s.iam.gserviceaccount.com" % (ENV["SA_ARMORER"], PROJECT)

FLOOR = ht.ATTESTATION_FLOOR_UTC
AFTER_FLOOR = "2026-08-22T20:00:00Z"
BEFORE_FLOOR = "2026-08-22T18:00:00Z"


def entry(method, resource, principal, granted=True, code=None,
          ts="2026-08-22T19:31:10.000000000Z"):
    """One audit entry in the shape Cloud Logging actually returns."""
    payload = {
        "methodName": method,
        "resourceName": resource,
        "authenticationInfo": {"principalEmail": principal},
        "authorizationInfo": [{"permission": method, "granted": granted}],
        "status": ({"code": code} if code else {}),
    }
    return {"timestamp": ts, "protoPayload": payload}


OBJ = "projects/_/buckets/crucible-sealed-x7/objects/families/_probe/canary.txt"
PREFIX = "projects/_/buckets/crucible-sealed-x7/objects/families/"
BUCKET_RES = "projects/_/buckets/crucible-sealed-x7"

# ---------------------------------------------------------------------------
# THE LIVE FIXTURE. Not written by hand - read out of the real log.
#
#   gcloud logging read '<the filter build_filter() produces>' \
#     --project=crucible-hack-2026 --limit=50 --order=asc --format=json
#
# produced these eight entries on 2026-08-22, from exactly three commands:
#   1. `gcloud storage ls -r gs://crucible-sealed-x7/families/` as sealed-eval
#      -> the prefix probe + three objects.list
#   2. `gcloud storage cat .../canary.txt` as sealed-eval
#      -> TWO objects.get on the same object (metadata, then media) + one
#         buckets.getStorageLayout
#   3. `gcloud storage cat .../canary.txt` as ARMORER -> denied, code 7
#
# Fields irrelevant to classification (insertId, oauth token prefixes, caller
# IP, user agent) are trimmed. Nothing that classification reads is altered.
# ---------------------------------------------------------------------------
LIVE_ENTRIES = [
    # granted: TRUE, and status.code 5. Authorization passed; the read did not.
    entry("storage.objects.get", PREFIX, EVAL_SA, granted=True, code=5,
          ts="2026-08-22T19:31:10.161877882Z"),
    entry("storage.objects.list", BUCKET_RES, EVAL_SA,
          ts="2026-08-22T19:31:10.229366445Z"),
    entry("storage.objects.list", BUCKET_RES, EVAL_SA,
          ts="2026-08-22T19:31:10.304419626Z"),
    entry("storage.objects.list", BUCKET_RES, EVAL_SA,
          ts="2026-08-22T19:31:10.382765741Z"),
    entry("storage.objects.get", OBJ, EVAL_SA,
          ts="2026-08-22T19:31:19.292722382Z"),
    entry("storage.buckets.getStorageLayout", BUCKET_RES, EVAL_SA,
          ts="2026-08-22T19:31:19.804935541Z"),
    entry("storage.objects.get", OBJ, EVAL_SA,
          ts="2026-08-22T19:31:20.375218265Z"),
    entry("storage.objects.get", OBJ, ARMORER_SA, granted=False, code=7,
          ts="2026-08-22T19:31:46.713927765Z"),
]

# Verbatim from `gcloud projects get-iam-policy crucible-hack-2026
# --format=json` on 2026-08-22, after Data Access logging was enabled.
LIVE_AUDIT_CONFIGS = [
    {"auditLogConfigs": [{"logType": "DATA_READ"}],
     "service": "storage.googleapis.com"},
]
LIVE_POLICY = {"auditConfigs": LIVE_AUDIT_CONFIGS, "bindings": []}


def counter(entries=None, policy=None, **over):
    """A counter with both cloud calls injected. `entries` is what the RUN
    window query returns; the canary query returns the same list unless
    `canary_entries` overrides it."""
    entries = LIVE_ENTRIES if entries is None else entries
    canary = over.pop("canary_entries", entries)

    calls = []

    def log_read(project, filter_text, cap):
        calls.append({"project": project, "filter": filter_text, "cap": cap})
        if cap == 1:                       # the canary query asks for one
            return list(canary)[:1]
        return list(entries)

    kwargs = dict(env=ENV, since=AFTER_FLOOR,
                  log_read=over.pop("log_read", log_read),
                  policy_fetch=lambda: (LIVE_POLICY if policy is None else policy),
                  sleep=lambda _s: None)
    kwargs.update(over)
    c = ht.HoldoutTouchCounter(**kwargs)
    c.calls = calls
    return c


# ===========================================================================
# THE FILTER. Names are sourced; a typo here returns 0 rather than failing.
# ===========================================================================

def test_the_filter_is_built_from_gcp_env_and_not_from_retyped_literals():
    f = ht.build_filter(PROJECT, SEALED, AFTER_FLOOR)
    assert ht.bucket_name(SEALED) in f
    assert PROJECT in f
    # The bucket name is matched EXACTLY, not with the `:` substring operator.
    # `bucket_name:"crucible-sealed"` would also match `crucible-sealed-old`.
    assert 'resource.labels.bucket_name="%s"' % ht.bucket_name(SEALED) in f
    assert 'resource.labels.bucket_name:' not in f


def test_the_filter_pins_the_storage_service():
    """`cloudaudit...%2Fdata_access` ALSO carries iamcredentials
    GenerateAccessToken entries - one per impersonation. A filter keyed only on
    the log name counts a G7a probe as a seal touch."""
    f = ht.build_filter(PROJECT, SEALED, AFTER_FLOOR)
    assert 'protoPayload.serviceName="storage.googleapis.com"' in f
    assert ht.DATA_ACCESS_LOG in f
    assert 'timestamp>="%s"' % AFTER_FLOOR in f


def test_the_filter_names_the_data_access_log_and_not_admin_activity():
    """ADMIN_ACTIVITY is always on and records bucket CONFIGURATION, not reads.
    Counting it would report a boundary that was configured, not one that held."""
    f = ht.build_filter(PROJECT, SEALED, AFTER_FLOOR)
    assert "data_access" in f
    assert "activity" not in f


def test_bucket_name_strips_the_scheme():
    assert ht.bucket_name("gs://crucible-sealed-x7") == "crucible-sealed-x7"
    assert ht.bucket_name("gs://crucible-sealed-x7/") == "crucible-sealed-x7"


# ===========================================================================
# CLASSIFICATION, against the shapes GCS actually emits.
# ===========================================================================

def test_a_content_read_of_a_real_object_is_the_thing_that_counts():
    r = ht.classify(entry("storage.objects.get", OBJ, EVAL_SA))
    assert r["kind"] == ht.CONTENT_READ
    assert r["granted"] is True
    assert r["principal"] == EVAL_SA


def test_an_objects_get_on_a_PREFIX_is_not_a_content_read():
    """NEGATIVE CONTROL on the counting rule. `gcloud storage ls -r` asks
    whether `families/` is an object. Counting it makes a bare listing look
    like a read of sealed material. Delete the `endswith('/')` guard in
    `classify` and this test goes red."""
    r = ht.classify(entry("storage.objects.get", PREFIX, EVAL_SA))
    assert r["kind"] == ht.ENUMERATION


def test_object_listing_is_logged_but_is_not_counted_as_a_touch():
    """Listing DOES emit a DATA_READ entry - measured, not assumed. It is
    excluded by policy, not by absence."""
    r = ht.classify(entry("storage.objects.list", BUCKET_RES, EVAL_SA))
    assert r["kind"] == ht.ENUMERATION


def test_bucket_metadata_calls_are_enumeration():
    r = ht.classify(entry("storage.buckets.getStorageLayout", BUCKET_RES, EVAL_SA))
    assert r["kind"] == ht.ENUMERATION


def test_an_unrecognised_method_is_kept_visible_rather_than_dropped():
    """A method this module has never seen is not evidence of nothing."""
    r = ht.classify(entry("storage.objects.compose", OBJ, EVAL_SA))
    assert r["kind"] == ht.OTHER


def test_a_denied_read_is_not_granted():
    assert ht.is_granted(entry("storage.objects.get", OBJ, ARMORER_SA,
                               granted=False, code=7)) is False


def test_granted_true_with_a_nonzero_status_code_is_NOT_a_read():
    """THE SHAPE A SINGLE-SIGNAL IMPLEMENTATION GETS WRONG, and it is in the
    live fixture: authorization succeeded (`granted: true`) and the request
    still failed (`status.code: 5`, NOT_FOUND). A permission check that passed
    is not a byte that moved. Read only `authorizationInfo[].granted` and this
    counts as a read of the holdout."""
    assert ht.is_granted(entry("storage.objects.get", PREFIX, EVAL_SA,
                               granted=True, code=5)) is False


def test_an_entry_with_neither_signal_is_treated_as_granted():
    """Conservative direction on purpose: over-counting fails G7c loudly,
    under-counting passes a gate that measured nothing."""
    assert ht.is_granted({"protoPayload": {"methodName": "storage.objects.get"}}) is True


# ===========================================================================
# TALLY, over the live fixture.
# ===========================================================================

def test_the_live_fixture_tallies_to_two_content_reads_from_one_cat():
    """Eight entries, three commands, and the number that matters is 2 - the
    metadata fetch and the media download of ONE `cat`. Everything else is a
    listing, a prefix probe, a bucket-metadata call, or a denial."""
    t = ht.tally(LIVE_ENTRIES, {EVAL_SA})
    assert t["entries"] == 8
    assert t["count"] == 2
    assert t["distinct_reads"] == 1          # one principal, one object
    assert len(t["enumerations"]) == 4       # 3 x list + getStorageLayout
    assert len(t["denied"]) == 2             # the armorer 403 + the code-5 probe
    assert t["intruders"] == []
    assert t["principals"] == sorted({EVAL_SA, ARMORER_SA})


def test_distinct_reads_collapses_the_metadata_plus_media_pair():
    t = ht.tally(LIVE_ENTRIES, {EVAL_SA})
    assert t["count"] != t["distinct_reads"]
    assert t["distinct_objects"] == [OBJ]


def test_a_granted_read_by_an_unpermitted_principal_is_an_intruder():
    rogue = entry("storage.objects.get", OBJ, ARMORER_SA, granted=True)
    t = ht.tally([rogue], {EVAL_SA})
    assert t["count"] == 1
    assert [r["principal"] for r in t["intruders"]] == [ARMORER_SA]


def test_a_DENIED_read_by_an_unpermitted_principal_is_not_an_intruder():
    """A 403 is the boundary working. It is logged, it is reported, and it is
    not a touch - no sealed byte moved."""
    t = ht.tally([entry("storage.objects.get", OBJ, ARMORER_SA,
                        granted=False, code=7)], {EVAL_SA})
    assert t["count"] == 0
    assert t["intruders"] == []
    assert len(t["denied"]) == 1


# ===========================================================================
# THE AUDIT-CONFIG PRECONDITION.
# ===========================================================================

def test_the_live_audit_config_shape_passes():
    assert ht.storage_data_read_enabled(LIVE_POLICY) is None


def test_no_auditconfigs_block_at_all_is_a_problem():
    """The state the project was in until 2026-08-22, and the state
    `real_gate.py`'s docstring described until this lane corrected it."""
    p = ht.storage_data_read_enabled({"bindings": []})
    assert p and "NO auditConfigs" in p


def test_an_auditconfig_for_a_different_service_does_not_count():
    p = ht.storage_data_read_enabled({"auditConfigs": [
        {"service": "bigquery.googleapis.com",
         "auditLogConfigs": [{"logType": "DATA_READ"}]}]})
    assert p and "no entry for storage.googleapis.com" in p


def test_a_storage_auditconfig_without_DATA_READ_does_not_count():
    p = ht.storage_data_read_enabled({"auditConfigs": [
        {"service": "storage.googleapis.com",
         "auditLogConfigs": [{"logType": "DATA_WRITE"}]}]})
    assert p and "no DATA_READ" in p


def test_an_exempted_member_breaks_the_count():
    """An exempted principal reads the seal without leaving a record, so the
    number stops being a count of reads. This is the quiet version of turning
    logging off and it would otherwise pass every other check here."""
    p = ht.storage_data_read_enabled({"auditConfigs": [
        {"service": "storage.googleapis.com",
         "auditLogConfigs": [{"logType": "DATA_READ",
                              "exemptedMembers": ["serviceAccount:x@y"]}]}]})
    assert p and "exempts" in p


# ===========================================================================
# THE COUNTER. Every route to a fabricated zero.
# ===========================================================================

def test_the_happy_path_returns_the_count():
    c = counter()
    assert c() == 2
    assert c.last_tally["intruders"] == []


def test_a_zero_in_the_run_window_is_reachable_and_is_a_real_zero():
    """The point of the canary. An empty RUN window returns 0 - honestly - only
    because the same filter demonstrably matches entries over the attestable
    window. Without that control this 0 and a misspelled bucket are the same
    output."""
    c = counter(entries=[], canary_entries=LIVE_ENTRIES)
    assert c() == 0


def test_the_canary_returning_nothing_is_UNEVALUABLE_and_never_zero():
    """THE HEADLINE TEST. A filter that matches nothing is the one remaining way
    to score G7c PASS while measuring nothing: a misspelled bucket, a renamed
    log, a changed resource.type, and a seal nobody touched all return []."""
    c = counter(entries=[], canary_entries=[])
    with pytest.raises(ht.HoldoutTouchUnevaluable) as ei:
        c()
    assert "CANARY QUERY RETURNED NOTHING" in str(ei.value)


def test_a_window_before_the_attestation_floor_is_UNEVALUABLE():
    """Data Access logging is not retroactive. A probe at 18:27:30Z on
    2026-08-22 left no entry while a read at 19:31:10Z did, so coverage
    demonstrably did not exist before the floor. Reporting 0 for that time
    would be a clean seal invented out of missing data."""
    c = counter(since=BEFORE_FLOOR)
    with pytest.raises(ht.HoldoutTouchUnevaluable) as ei:
        c()
    assert "before the attestation floor" in str(ei.value)


def test_the_floor_itself_is_inside_the_attestable_window():
    c = counter(since=FLOOR)
    assert c() == 2


def test_a_missing_audit_config_is_UNEVALUABLE_and_never_zero():
    """Re-asserted every call: a config REMOVED after this module was written is
    invisible to a check that ran earlier, and its symptom is a log that quietly
    stops filling."""
    c = counter(policy={"bindings": []})
    with pytest.raises(ht.HoldoutTouchUnevaluable) as ei:
        c()
    assert "NO auditConfigs" in str(ei.value)


def test_an_unreadable_project_policy_is_UNEVALUABLE_and_never_zero():
    def boom():
        raise RuntimeError("could not fetch project IAM policy: 403")
    c = counter(policy_fetch=boom)
    with pytest.raises(ht.HoldoutTouchUnevaluable) as ei:
        c()
    assert "whether Data Access logging is still on is unknown" in str(ei.value)


def test_a_failed_log_read_is_UNEVALUABLE_and_never_an_empty_log():
    def boom(project, filt, cap):
        raise ht.HoldoutTouchUnevaluable("gcloud logging read exited 1: nope")
    c = counter(log_read=boom)
    with pytest.raises(ht.HoldoutTouchUnevaluable):
        c()


def test_a_result_at_the_cap_is_UNEVALUABLE_because_it_is_truncated():
    """An undercount, not a zero - and G7 has no 'at least N' outcome."""
    many = [entry("storage.objects.get", OBJ, EVAL_SA) for _ in range(5)]
    c = counter(entries=many, canary_entries=many, cap=5)
    with pytest.raises(ht.HoldoutTouchUnevaluable) as ei:
        c()
    assert "truncated" in str(ei.value)


def test_a_granted_read_from_an_unpermitted_principal_raises_INVALID_not_a_count():
    """measurement-spec.md:946 - any read from another SA marks the run INVALID.
    A distinct exception type from UNEVALUABLE: one says the instrument is
    untrustworthy, the other says the instrument worked and caught something."""
    rogue = LIVE_ENTRIES + [entry("storage.objects.get", OBJ, ARMORER_SA,
                                  granted=True,
                                  ts="2026-08-22T20:00:00.000000000Z")]
    c = counter(entries=rogue, canary_entries=rogue)
    with pytest.raises(ht.HoldoutTouchInvalid) as ei:
        c()
    assert ARMORER_SA in str(ei.value)


def test_the_human_operator_is_not_exempt_from_the_permitted_set():
    """The operator holds roles/owner and can read everything. The honest
    response is to record it, not to exempt it - so an owner read of the seal
    raises exactly like any other unpermitted principal."""
    op = [entry("storage.objects.get", OBJ, "eric@erictetzlaff.com")]
    c = counter(entries=op, canary_entries=op)
    with pytest.raises(ht.HoldoutTouchInvalid) as ei:
        c()
    assert "eric@erictetzlaff.com" in str(ei.value)


def test_the_canary_query_uses_the_floor_and_the_run_query_uses_since():
    c = counter(since=AFTER_FLOOR)
    c()
    canary_call = [x for x in c.calls if x["cap"] == 1][0]
    run_call = [x for x in c.calls if x["cap"] != 1][0]
    assert FLOOR in canary_call["filter"]
    assert AFTER_FLOOR in run_call["filter"]


def test_settle_seconds_is_slept_before_the_query():
    """Ingestion lags the event; a read seconds before the gate queries can be
    missed, and a missed read is an undercount that reads as a pass. STUB-ONLY:
    this proves the sleep happens, not that any duration is sufficient."""
    slept = []
    c = counter(settle_seconds=3.0, sleep=slept.append)
    c()
    assert slept == [3.0]


def test_the_command_string_is_the_command_that_was_run():
    """A number whose provenance is a paraphrase is a number a judge cannot
    re-derive, so the proof artifact prints this verbatim."""
    c = counter()
    cmd = c.command()
    assert cmd.startswith("gcloud logging read '")
    assert "--project=%s" % PROJECT in cmd
    assert ht.bucket_name(SEALED) in cmd


def test_a_malformed_timestamp_is_refused_rather_than_mis_ordered():
    """A `since` that sorts wrong would silently widen the window past the
    floor, which is the failure the floor exists to prevent."""
    c = counter(since="2026-08-22 20:00:00")
    with pytest.raises(ht.HoldoutTouchUnevaluable) as ei:
        c()
    assert "not RFC3339 UTC" in str(ei.value)


def test_render_tally_names_the_count_and_the_command():
    c = counter()
    c()
    text = ht.render_tally(c.last_tally)
    assert "holdout_touch_count" in text
    assert "gcloud logging read" in text
    assert EVAL_SA in text


# ===========================================================================
# WIRED INTO THE GATE. G7c is no longer absent.
# ===========================================================================

def test_the_counter_satisfies_the_gate_injection_contract():
    """`RealGate` wants a zero-arg callable returning an int, with NO default."""
    c = counter()
    assert isinstance(c(), int)


def test_an_unevaluable_counter_reaches_the_gate_as_UNEVALUABLE():
    from crucible.conductor import real_gate as rg
    gate = rg.RealGate(ledger=None, run_id="t", blob_writer=None,
                       blob_reader=None, repo_root=REPO, skip_cloud=True,
                       holdout_touch=counter(entries=[], canary_entries=[]))
    f = gate._holdout_finding()                              # noqa: SLF001
    assert f["status"] == rg.UNEVALUABLE
    assert "CANARY" in f["detail"]


def test_an_intruding_read_reaches_the_gate_as_a_FAIL_that_INVALIDATES():
    """Not UNEVALUABLE. The instrument worked; it caught something. G7c's own
    line: any read from another SA marks the run INVALID."""
    from crucible.conductor import real_gate as rg
    rogue = [entry("storage.objects.get", OBJ, ARMORER_SA, granted=True)]
    gate = rg.RealGate(ledger=None, run_id="t", blob_writer=None,
                       blob_reader=None, repo_root=REPO, skip_cloud=True,
                       holdout_touch=counter(entries=rogue, canary_entries=rogue))
    f = gate._holdout_finding()                              # noqa: SLF001
    assert f["status"] == rg.FAIL
    assert f["invalidates"] is True
    assert ARMORER_SA in f["detail"]


def test_the_gate_still_reports_G7c_absent_when_nothing_is_injected():
    """Unchanged, and it must stay that way: `holdout_touch` has no default so
    that "nothing computed this" cannot be mistaken for "the count was zero"."""
    from crucible.conductor import real_gate as rg
    gate = rg.RealGate(ledger=None, run_id="t", blob_writer=None,
                       blob_reader=None, repo_root=REPO, skip_cloud=True,
                       holdout_touch=None)
    f = gate._holdout_finding()                              # noqa: SLF001
    assert f["status"] == rg.UNEVALUABLE
    assert "no holdout_touch counter was injected" in f["detail"]
