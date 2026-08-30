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
  * The names in the filter come from the REAL `scripts/gcp-env.sh`.
    `test_the_filter_*` fails red if a bucket name is ever retyped instead of
    sourced. They are read by `tests/conftest.py:load_gcp_env`, which parses
    that file in PURE PYTHON rather than by asking bash to source it - see the
    NO SHELL section at the bottom of this file for why, and for the
    differential test that holds the two readers in step.
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

import os
import pathlib
import shutil
import subprocess
import sys

import pytest

from infra import holdout_touch as ht
from infra import verify_iam
from tests.conftest import load_gcp_env

REPO = pathlib.Path(__file__).resolve().parent.parent

# NO SHELL AT IMPORT TIME. This line used to be
# `ENV = verify_iam.load_env(str(REPO))`, which runs `bash -c '. gcp-env.sh
# && env | grep ...'` during COLLECTION - before a single test runs, in a file
# where every collaborator is injected and nothing needs a configured machine.
# On a host with no working Git Bash the file could not even be collected.
# `load_gcp_env` reads the same one file in pure Python. See the NO SHELL
# section at the bottom for the reproduction and the differential test.
ENV = load_gcp_env(str(REPO), require=("CRUCIBLE_PROJECT",
                                       "CRUCIBLE_SEALED_BUCKET",
                                       "SA_SEALED_EVAL", "SA_ARMORER"))

# --------------------------------------------------------------------------
# THE ONE THING IN THIS FILE THAT STILL NEEDS A SHELL, AND IT IS NOT THIS FILE.
#
# `crucible.conductor.real_gate.RealGate.__init__` -> `promoter_identity()` ->
# `gcp_env()` -> `verify_iam.load_env()` -> `bash -c '. gcp-env.sh && env |
# grep ...'` (`crucible/conductor/real_gate.py:313`). The four tests below that
# construct a `RealGate` therefore reach bash no matter what this file does; the
# fix for them is a shell-free reader in `infra/verify_iam.py`, which is not
# this change's to make.
#
# Until then those four SKIP with the reason, rather than erroring with a
# FileNotFoundError out of `subprocess` that reads like a code defect. The probe
# is LAZY on purpose: running it at module scope would put the subprocess back
# into collection, which is the whole defect being removed here.
# --------------------------------------------------------------------------

BASH = shutil.which("bash") or shutil.which("bash.exe")

_BASH_ENV = {}


def bash_env_or_problem():
    """Run `verify_iam.load_env` once, or say why it cannot run. NEVER raises.

    An environmental failure comes back as a reason string so the caller decides
    whether it is a skip or a finding. Both shapes are covered: bash absent, and
    bash present but unable to fork - the second is what an independent reviewer
    hit on 2026-08-29, a Git Bash signal-pipe failure.
    """
    if not _BASH_ENV:
        if BASH is None:
            _BASH_ENV.update(env=None, problem="no `bash` on PATH")
        else:
            try:
                _BASH_ENV.update(env=verify_iam.load_env(str(REPO)),
                                 problem=None)
            except (OSError, subprocess.SubprocessError) as e:
                _BASH_ENV.update(
                    env=None,
                    problem="`bash` resolved to %s but could not be run to "
                            "completion (%s: %s)" % (BASH, type(e).__name__, e))
    return _BASH_ENV["env"], _BASH_ENV["problem"]


def skip_without_a_working_bash(unmeasured):
    """Skip with a reason that names what is missing AND what goes unchecked.

    A bare `pytest.skip()` is a check that passes while measuring nothing, which
    is this repository's signature defect - fifteen recorded instances. The
    reason text has to be readable as a gap, not as a pass.
    """
    env, problem = bash_env_or_problem()
    if problem:
        pytest.skip(
            "%s, and `infra.verify_iam.load_env` runs `bash -c '. "
            "scripts/gcp-env.sh && env | grep -E \"^(CRUCIBLE_|SA_|SUFFIX)\"'`. "
            "UNMEASURED HERE: %s. Install a working Git Bash to run this check. "
            "The shell-free fix belongs in infra/verify_iam.py."
            % (problem, unmeasured))
    return env


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
    """A counter with both cloud calls injected.

    THREE queries now run, and the stub dispatches the way a reader would:

      canary    `cap == ht.CANARY_CAP`, and its filter excludes the SENTINEL
      intruder  carries a principal-exclusion clause, `cap == self.cap`
      count     no exclusion clause

    The stub deliberately does NOT apply either server-side narrowing. That is
    the honest shape for a double: it returns a SUPERSET, which is what an
    under-broad filter would do live, and it forces the counter's own Python
    predicate to be the thing that decides. If the counter ever started trusting
    the server filter as the verdict, every happy-path test here would go red
    because the stub hands the intruder query the permitted principal's reads
    as well.
    """
    entries = LIVE_ENTRIES if entries is None else entries
    canary = over.pop("canary_entries", entries)

    calls = []
    EXCLUSION = "NOT protoPayload.authenticationInfo.principalEmail"

    def log_read(project, filter_text, cap):
        kind = ("canary" if cap == ht.CANARY_CAP
                else "intruder" if EXCLUSION in filter_text else "count")
        calls.append({"project": project, "filter": filter_text, "cap": cap,
                      "kind": kind})
        if kind == "canary":
            return list(canary)[:ht.CANARY_CAP]
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
    canary_call = [x for x in c.calls if x["kind"] == "canary"][0]
    run_call = [x for x in c.calls if x["kind"] == "count"][0]
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
    skip_without_a_working_bash(
        "that an UNEVALUABLE counter surfaces at G7c as UNEVALUABLE rather "
        "than as a zero. `RealGate.__init__` reads SA_GATE through bash")
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
    skip_without_a_working_bash(
        "that an intruding read surfaces at G7c as a FAIL that invalidates the "
        "run. `RealGate.__init__` reads SA_GATE through bash")
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
    skip_without_a_working_bash(
        "that G7c still reports ABSENT when no counter is injected. "
        "`RealGate.__init__` reads SA_GATE through bash")
    from crucible.conductor import real_gate as rg
    gate = rg.RealGate(ledger=None, run_id="t", blob_writer=None,
                       blob_reader=None, repo_root=REPO, skip_cloud=True,
                       holdout_touch=None)
    f = gate._holdout_finding()                              # noqa: SLF001
    assert f["status"] == rg.UNEVALUABLE
    assert "no holdout_touch counter was injected" in f["detail"]


# ===========================================================================
# THE CAP HAD A COUNTDOWN ON IT (2026-08-25).
#
# Measured live that day, window = ATTESTATION_FLOOR_UTC: the base filter
# matched 624 entries against a cap of 1000, and `compute()` raises UNEVALUABLE
# AT the cap. Roughly four entries per gate call is about ninety gate calls of
# headroom, so one more batch the size of the 2026-08-25 one and G7c goes dark.
#
# The population that grows is NOT reads. 606 of the 624 were
# `storage.objects.list` - the G7a probe's own four arms firing every gate call
# - and `classify` already refuses to count every one of them. The narrowing
# pushes that existing rule to the server. 624 -> 14, measured.
#
# The tests below hold the two halves of the fix together: the narrowing must
# match what `classify` discards, and the exclusion must never become the
# verdict.
# ===========================================================================

def test_the_count_query_drops_the_methods_classify_already_discards():
    c = counter()
    f = c.filter_text()
    assert 'NOT protoPayload.methodName="storage.objects.list"' in f
    assert 'NOT protoPayload.methodName:"storage.buckets."' in f
    # And it does NOT exclude any principal: holdout_touch_count is a count of
    # READS, and the permitted evaluator's reads are what the expected value is
    # about.
    assert "NOT protoPayload.authenticationInfo.principalEmail" not in f


def test_the_pushed_down_methods_are_exactly_what_classify_calls_ENUMERATION():
    """THE COUPLING, ASSERTED RATHER THAN TRUSTED. If `classify` ever starts
    counting one of these as a touch, the server would already have thrown it
    away and the count would silently drop. Two files, one rule."""
    for method in ht.NOT_A_TOUCH_METHODS:
        row = ht.classify(entry(method, BUCKET_RES, EVAL_SA))
        assert row["kind"] == ht.ENUMERATION, method
    for prefix in ht.NOT_A_TOUCH_METHOD_PREFIXES:
        row = ht.classify(entry(prefix + "getStorageLayout", BUCKET_RES, EVAL_SA))
        assert row["kind"] == ht.ENUMERATION, prefix
    # The inverse: a content read must NOT be in the dropped set, or the
    # narrowing would delete the only thing that counts.
    assert ht.classify(entry("storage.objects.get", OBJ, EVAL_SA))["kind"] \
        == ht.CONTENT_READ
    for method in ht.NOT_A_TOUCH_METHODS:
        assert method != "storage.objects.get"


def test_an_unrecognised_method_is_still_retrieved_by_the_narrowed_filter():
    """The narrowing is written as NOT-a-touch exclusions on purpose. An
    `methodName="storage.objects.get"` inclusion would have been shorter and
    would have silently deleted `classify`'s OTHER branch, whose whole reason
    for existing is that a method this module has never seen is not evidence of
    nothing."""
    f = counter().filter_text()
    assert "storage.objects.get" not in f


def test_the_intruder_query_excludes_the_permitted_set_in_the_filter():
    """The bound. Its population is unattested reads, not all reads."""
    c = counter()
    f = c.intruder_filter_text()
    assert 'NOT protoPayload.authenticationInfo.principalEmail=("%s")' % EVAL_SA in f
    assert 'NOT protoPayload.methodName="storage.objects.list"' in f


def test_the_canary_excludes_a_SENTINEL_and_never_the_permitted_set():
    """THE CONTROL ON THE NEW CLAUSE. A filter that asks the server for only the
    bad entries returns zero when the filter is wrong, and zero looks exactly
    like a clean seal. So the canary runs the SAME construction, NOT-clause
    included, against a principal that cannot exist - the known-present read has
    to survive the whole compiled filter. Excluding the permitted set here would
    remove the very entry the control looks for and the control would fail
    always; excluding nothing would test the clauses AROUND the new one."""
    c = counter()
    c()
    canary = [x for x in c.calls if x["kind"] == "canary"][0]
    assert c.canary_sentinel in canary["filter"]
    assert EVAL_SA not in canary["filter"]
    assert 'NOT protoPayload.authenticationInfo.principalEmail' in canary["filter"]
    assert 'NOT protoPayload.methodName="storage.objects.list"' in canary["filter"]


def test_a_canary_that_sees_entries_but_no_GRANTED_READ_is_UNEVALUABLE():
    """The earliest entry in the real attestable window is a `granted: true` /
    `status.code: 5` prefix probe, which `is_granted` correctly refuses. "At
    least one entry" is therefore satisfiable by a shape that can never produce
    a non-zero count, and a counter that can only ever answer 0 is a check that
    cannot fail."""
    dead = [entry("storage.objects.get", PREFIX, EVAL_SA, granted=True, code=5)]
    c = counter(entries=[], canary_entries=dead)
    with pytest.raises(ht.HoldoutTouchUnevaluable) as ei:
        c()
    assert "NOT ONE OF THEM IS A GRANTED CONTENT READ" in str(ei.value)


def test_the_intruder_query_at_its_own_cap_is_UNEVALUABLE():
    """A truncated list of unattested reads is not a shorter list of unattested
    reads. Raising the cap silently would be the same defect wearing a bigger
    number."""
    rogue = [entry("storage.objects.get", OBJ, ARMORER_SA, granted=True,
                   ts="2026-08-22T20:0%d:00.000000000Z" % i) for i in range(5)]

    def log_read(project, filt, cap):
        if cap == ht.CANARY_CAP:
            return list(LIVE_ENTRIES)
        if "NOT protoPayload.authenticationInfo.principalEmail" in filt:
            return list(rogue)
        return []          # count query is empty; only the intruder query fills

    c = counter(log_read=log_read, cap=5)
    with pytest.raises(ht.HoldoutTouchUnevaluable) as ei:
        c()
    assert "INTRUDER query" in str(ei.value)


def test_an_intruder_seen_only_by_the_intruder_query_is_still_caught():
    """THE SERVER NARROWS; THIS FILE DECIDES. The two paths are unioned, so a
    read that reaches only one of them still raises. A filter cannot become the
    verdict by being the only thing that saw something."""
    rogue = entry("storage.objects.get", OBJ, ARMORER_SA, granted=True,
                  ts="2026-08-22T20:30:00.000000000Z")

    def log_read(project, filt, cap):
        if cap == ht.CANARY_CAP:
            return list(LIVE_ENTRIES)
        if "NOT protoPayload.authenticationInfo.principalEmail" in filt:
            return [rogue]
        return list(LIVE_ENTRIES)      # count query does NOT see it

    c = counter(log_read=log_read)
    with pytest.raises(ht.HoldoutTouchInvalid) as ei:
        c()
    assert ARMORER_SA in str(ei.value)
    assert c.last_tally["found_only_by_intruder_query"] == 1


# ===========================================================================
# ATTESTATION. Named reads that are ACCOUNTED FOR - never a principal exemption.
#
# `scripts/probe-g7-g8.py` defaults its window to the attestation floor, which
# permanently contains seven operator reads from 2026-08-22 that Cloud Logging
# cannot delete. The artifact's G7c line was red forever for an intact boundary.
# Moving the window forward would have HIDDEN them, and a control that stops
# looking is not a control that passed.
# ===========================================================================

ATTESTED, ATTESTED_PROBLEM = ht.load_attested_reads()


def _one_attested_entry():
    """A log entry whose key matches a row in the real record on disk."""
    ts, principal, method, resource = sorted(ATTESTED)[0]
    return entry(method, resource, principal, granted=True, ts=ts)


def test_the_record_on_disk_parses_and_names_the_seven_operator_reads():
    """Measured against the live log 2026-08-25: eight `storage.objects.get`
    entries by the operator in the attestation window, of which SEVEN are
    granted content reads. The eighth carries `status.code: 5` (NOT_FOUND on the
    copy destination) - authorization passed, no byte moved - so `is_granted`
    never counts it and it is deliberately NOT in the record."""
    assert ATTESTED_PROBLEM is None, ATTESTED_PROBLEM
    assert len(ATTESTED) == 7
    assert {k[1] for k in ATTESTED} == {"eric@erictetzlaff.com"}
    assert {k[2] for k in ATTESTED} == {"storage.objects.get"}
    assert all(why.strip() for why in ATTESTED.values())
    # The entry that is NOT a read must not have been swept in with the rest.
    assert not any(k[0] == "2026-08-22T20:18:02.046086366Z" for k in ATTESTED)


def test_an_attested_read_is_COUNTED_AND_SHOWN_and_does_not_raise():
    """Counted and shown, never excluded. Hiding it would remove the only
    record that the trust root touched the seal, which is the record's entire
    value."""
    e = _one_attested_entry()
    rows = LIVE_ENTRIES + [e]
    c = counter(entries=rows, canary_entries=rows)
    assert c() == 3                                   # 2 permitted + 1 attested
    t = c.last_tally
    assert t["intruders"] == []
    assert len(t["attested_reads"]) == 1
    assert t["attested_reads"][0]["attested_why"]
    assert t["unattested_reads"] == 0
    assert "ATTESTED" in ht.render_tally(t)


def test_the_SAME_principal_at_a_DIFFERENT_instant_is_NOT_attested():
    """THE NEGATIVE CONTROL ON THE WHOLE RECORD. An attestation key is an
    INSTANT, not a principal. Attesting a principal would hand the trust root a
    permanent hole in the one control that records what it did. A read that has
    not happened yet carries a timestamp no row names, so it is unexplained by
    construction."""
    ts, principal, method, resource = sorted(ATTESTED)[0]
    later = entry(method, resource, principal, granted=True,
                  ts="2026-08-30T00:00:00.000000000Z")
    rows = LIVE_ENTRIES + [later]
    c = counter(entries=rows, canary_entries=rows)
    with pytest.raises(ht.HoldoutTouchInvalid) as ei:
        c()
    assert principal in str(ei.value)
    assert "UNATTESTED" in str(ei.value)


def test_a_different_object_at_an_attested_instant_is_NOT_attested():
    """All four fields key the attestation. Timestamp alone would forgive
    anything that happened in the same nanosecond."""
    ts, principal, method, _resource = sorted(ATTESTED)[0]
    other = entry(method,
                  "projects/_/buckets/crucible-sealed-x7/objects/families/f4/"
                  "instance-001.json", principal, granted=True, ts=ts)
    rows = LIVE_ENTRIES + [other]
    c = counter(entries=rows, canary_entries=rows)
    with pytest.raises(ht.HoldoutTouchInvalid):
        c()


def test_a_MISSING_record_attests_nothing_and_says_so():
    """Fails SAFE. Every operator read stays unexplained and G7c stays red. A
    file that is not there must never widen what is forgiven."""
    attested, problem = ht.load_attested_reads(
        str(REPO / "docs" / "proof" / "no-such-attestation-record.md"))
    assert attested == {}
    assert problem and "IS MISSING" in problem


def test_an_UNPARSEABLE_record_RAISES_rather_than_forgiving_nothing_quietly(tmp_path):
    """Different direction from missing, on purpose. The file exists and the
    control is broken; attesting nothing would be safe and also silent, and a
    broken instrument is exactly what UNEVALUABLE is for."""
    bad = tmp_path / "rec.md"
    bad.write_text("# record\n\nFENCEjson\n{not json at all,,,}\nFENCE\n"
                   .replace("FENCE", "`" * 3), encoding="utf-8")
    with pytest.raises(ht.HoldoutTouchUnevaluable):
        ht.load_attested_reads(str(bad))
    nofence = tmp_path / "rec2.md"
    nofence.write_text("# record with prose and no block\n", encoding="utf-8")
    with pytest.raises(ht.HoldoutTouchUnevaluable):
        ht.load_attested_reads(str(nofence))


def test_an_attested_read_with_no_REASON_is_refused(tmp_path):
    """A read attested without a reason is an exemption with better manners."""
    bad = tmp_path / "rec.md"
    body = ('{"attested_reads": [{"timestamp": "2026-08-22T20:18:01.984616894Z",'
            ' "principal": "eric@erictetzlaff.com", "method": '
            '"storage.objects.get", "resource": "x"}]}')
    bad.write_text("# r\n\n%sjson\n%s\n%s\n" % ("`" * 3, body, "`" * 3),
                   encoding="utf-8")
    with pytest.raises(ht.HoldoutTouchUnevaluable) as ei:
        ht.load_attested_reads(str(bad))
    assert "why" in str(ei.value)


def test_a_canary_whose_SENTINEL_went_empty_is_refused_as_a_control():
    """FOUND BY RUNNING THE NEGATIVE CONTROL AGAINST THE LIVE PROJECT,
    2026-08-25, not by reading the code. `build_filter` drops empty principals,
    so a `canary_sentinel` of None or "" compiles to a filter with NO exclusion
    clause: the canary would then pass on the clauses AROUND the new one, look
    green, and test nothing. A control that can be silently switched off is a
    check that cannot fail."""
    for dud in (None, ""):
        c = counter()
        c.canary_sentinel = dud
        with pytest.raises(ht.HoldoutTouchUnevaluable) as ei:
            c()
        assert "WITHOUT its exclusion clause" in str(ei.value)


def test_an_exclusion_clause_that_blanks_the_query_is_caught_by_the_canary():
    """THE FAILURE THE SENTINEL EXISTS FOR. An over-broad NOT-clause returns
    zero, and zero looks exactly like a clean seal. The canary's known-present
    read has to survive the whole compiled filter, so a clause that removes
    everything removes the control's own evidence and raises."""

    def log_read(project, filt, cap):
        if cap == ht.CANARY_CAP:
            return []          # what an over-broad exclusion returns live
        return list(LIVE_ENTRIES)

    c = counter(log_read=log_read)
    with pytest.raises(ht.HoldoutTouchUnevaluable) as ei:
        c()
    assert "CANARY QUERY RETURNED NOTHING" in str(ei.value)
    assert "over-broad" in str(ei.value)


# ===========================================================================
# THE WINDOW AND THE FACTORY, added 2026-08-29.
#
# `RealGate(holdout_touch=)` takes a zero-arg callable with no default, and the
# transfer runner has to build one for a window it opened for itself. Both of
# those were left to the call site, and both have a failure that returns a
# number rather than raising:
#
#   a window opened before the attestation floor  -> a count over uncovered time
#   a window that still holds the calibration read -> the run's own count is
#                                                     short by that read
#
# `now_utc` / `open_audit_window` / `make_counter` are those two steps written
# down once. Everything below drives them to red.
# ===========================================================================

def _at(stamp, micros=0):
    import datetime
    t = datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
    return t.replace(microsecond=micros, tzinfo=datetime.timezone.utc)


def test_now_utc_truncates_to_the_whole_second_and_never_rounds_up():
    """DOWN, NOT UP, and the direction is the decision. Rounding up pushes the
    boundary into the future and a read in that sliver is never counted - an
    UNDERCOUNT, the one error direction that looks like a clean seal."""
    assert ht.now_utc(lambda: _at("2026-08-29T12:00:00Z", micros=999999)) \
        == "2026-08-29T12:00:00Z"


def test_now_utc_produces_the_shape_the_window_comparator_accepts():
    # `_iso_ge` refuses anything it cannot order, so a formatter that drifted
    # would turn every window check into UNEVALUABLE.
    assert ht._iso_ge(ht.now_utc(lambda: _at("2026-08-29T12:00:00Z")), FLOOR)


def test_a_window_opened_before_the_attestation_floor_is_refused_at_the_door():
    """Refused HERE as well as inside `compute()`, so the run stops before it
    has spent anything rather than after the gate is queried."""
    with pytest.raises(ht.HoldoutTouchUnevaluable) as e:
        ht.open_audit_window(clock=lambda: _at("2026-08-20T00:00:00Z"))
    assert "attestation floor" in str(e.value)


def test_a_window_at_the_floor_itself_is_inside_the_attestable_period():
    got = ht.open_audit_window(
        clock=lambda: _at(FLOOR[:19] + "Z"))
    assert got == FLOOR[:19] + "Z"


def test_a_window_that_is_not_strictly_after_the_previous_phase_is_refused():
    """Equality means the two windows share a whole second, and an event inside
    that second belongs to both. The calibration read would then sit in the run's
    own window and its count could not be attributed to its own reads."""
    with pytest.raises(ht.HoldoutTouchUnevaluable) as e:
        ht.open_audit_window(clock=lambda: _at("2026-08-29T12:00:00Z"),
                             after="2026-08-29T12:00:00Z")
    assert "strictly after" in str(e.value)


def test_a_window_before_the_previous_phase_is_refused():
    with pytest.raises(ht.HoldoutTouchUnevaluable):
        ht.open_audit_window(clock=lambda: _at("2026-08-29T11:00:00Z"),
                             after="2026-08-29T12:00:00Z")


def test_a_window_strictly_after_the_previous_phase_is_returned():
    assert ht.open_audit_window(clock=lambda: _at("2026-08-29T12:00:01Z"),
                                after="2026-08-29T12:00:00Z") \
        == "2026-08-29T12:00:01Z"


def test_the_factory_returns_the_zero_arg_callable_the_gate_requires():
    skip_without_a_working_bash(
        "that `make_counter`'s product satisfies `RealGate(holdout_touch=)` and "
        "reaches G7c as PASS. `RealGate.__init__` reads SA_GATE through bash")
    from crucible.conductor import real_gate as rg

    c = ht.make_counter(ENV, since=AFTER_FLOOR,
                        log_read=lambda p, f, cap: (
                            [] if cap != ht.CANARY_CAP else list(LIVE_ENTRIES)),
                        policy_fetch=lambda: LIVE_POLICY,
                        sleep=lambda _s: None)
    gate = rg.RealGate(ledger=None, run_id="r", blob_writer=None,
                       blob_reader=None, repo_root=str(REPO),
                       holdout_touch=c, holdout_expected=0)
    f = gate._holdout_finding()                                # noqa: SLF001
    assert f["status"] == rg.PASS


def test_the_factory_does_not_sleep_per_compute_by_default():
    """The transfer sequence calls `compute()` four times and settles ONCE, at
    the point that needs it. Four sleeps would be three minutes of nothing and
    would not settle the read that matters any better."""
    slept = []
    c = ht.make_counter(ENV, since=AFTER_FLOOR,
                        log_read=lambda p, f, cap: list(LIVE_ENTRIES),
                        policy_fetch=lambda: LIVE_POLICY, sleep=slept.append)
    c.compute()
    assert slept == []


def test_the_factory_still_accepts_an_explicit_settle_interval():
    slept = []
    c = ht.make_counter(ENV, since=AFTER_FLOOR, settle_seconds=3.0,
                        log_read=lambda p, f, cap: list(LIVE_ENTRIES),
                        policy_fetch=lambda: LIVE_POLICY, sleep=slept.append)
    c.compute()
    assert slept == [3.0]


def test_the_repo_wide_settle_default_exists_and_is_not_zero():
    # Zero settlement makes "I did not wait" and "nothing was read" the same
    # number on the run that cannot be repeated.
    assert ht.DEFAULT_SETTLE_SECONDS > 0


# ===========================================================================
# NO SHELL. Added 2026-08-29, after an independent reviewer could not reproduce
# the claimed green on a Windows host.
#
# Every test above injects its collaborators. Not one needs gcloud, a network,
# or a configured project. The file still could not be COLLECTED without a
# working Git Bash, because line 67 read
#
#     ENV = verify_iam.load_env(str(REPO))
#
# and `infra/verify_iam.py:72` implements that as
#
#     bash -c '. <repo>/scripts/gcp-env.sh && env | grep -E "^(CRUCIBLE_|SA_|SUFFIX)"'
#
# Reproduced deterministically by removing every PATH directory holding
# `bash.exe` and running `pytest tests/test_holdout_touch.py --collect-only`:
# `FileNotFoundError: [WinError 2]` raised from that subprocess call, at import
# time, so all 69 tests errored as one collection failure. The reviewer's
# machine reached the same line with bash present but unable to create its
# signal pipe. Missing bash and broken bash are one dependency failing two ways.
#
# The fix is not a skip. The seam was in the wrong place: the names were
# reachable only through a function that shells out, so `tests/conftest.py`
# reads `scripts/gcp-env.sh` in pure Python. The names still come from that one
# file - nothing here retypes `crucible-sealed-x7`, and
# `test_the_filter_is_built_from_gcp_env_and_not_from_retyped_literals` above
# still catches it if anything ever does.
#
# What a second reader CAN do is disagree with bash about what the file says.
# That is the one thing this section exists to falsify.
#
# `BASH`, `bash_env_or_problem` and `skip_without_a_working_bash` are defined at
# the top of this file, because the four `RealGate` tests in the middle of it
# need them: `RealGate.__init__` reaches the same bash call through
# `crucible/conductor/real_gate.py:313`, which this change does not own.
# ===========================================================================


def test_reading_gcp_env_needs_no_subprocess_at_all():
    """THE REGRESSION GUARD ON COLLECTION. Not "does it work here" - this box
    has bash. `subprocess.Popen` is replaced by something that raises, and the
    pure-Python reader must still return the same names. Restore the
    `verify_iam.load_env` call at the top of this file and this goes red with
    the exact error a machine without Git Bash produces."""
    real_popen = subprocess.Popen

    def no_processes(*a, **k):
        raise AssertionError(
            "a test that injects every collaborator it has just spawned a "
            "process: %r. That is the dependency that made this file "
            "uncollectable on a host without Git Bash." % (a[0] if a else k))

    subprocess.Popen = no_processes
    try:
        env = load_gcp_env(str(REPO), require=("CRUCIBLE_PROJECT",
                                               "CRUCIBLE_SEALED_BUCKET",
                                               "SA_SEALED_EVAL", "SA_ARMORER"))
    finally:
        subprocess.Popen = real_popen
    assert env["CRUCIBLE_PROJECT"] == PROJECT
    assert env["CRUCIBLE_SEALED_BUCKET"] == SEALED


def test_the_pure_python_reader_agrees_with_bash_name_for_name():
    """THE DIFFERENTIAL. Two readers of one file is two chances to be wrong
    about it, so wherever bash can actually run, both run and the FULL key sets
    are compared - not a sampled few, which would let a dropped name through.

    SKIPPED, with a reason, only where bash cannot be executed at all. What goes
    unmeasured then is named in the skip text: the parser still sources every
    name from `scripts/gcp-env.sh`, so no literal is retyped either way; what is
    not checked is that its expansion matches bash's."""
    from_bash = skip_without_a_working_bash(
        "that the pure-Python reader in tests/conftest.py expands "
        "scripts/gcp-env.sh the same way bash does. Still true either way: "
        "every name comes from that one file and none is retyped")

    from_python = load_gcp_env(str(REPO))
    # `load_env` greps the whole process environment, so a variable already
    # exported into this shell with one of those prefixes appears in its result
    # and not in the file's. Compare on the file's keys and report any extra.
    assert set(from_python) <= set(from_bash), (
        "the pure-Python reader invented names bash does not produce: %s"
        % sorted(set(from_python) - set(from_bash)))
    missed = {k: from_bash[k] for k in set(from_bash) - set(from_python)}
    assert not missed, (
        "the pure-Python reader DROPPED names bash produces: %s. A dropped name "
        "does not fail loudly; it compiles into a filter that matches nothing."
        % sorted(missed))
    for k in sorted(from_python):
        assert from_python[k] == from_bash[k], (
            "%s: pure-Python read %r, bash read %r"
            % (k, from_python[k], from_bash[k]))


def test_this_file_collects_on_a_machine_without_bash():
    """THE ACTUAL FINDING, ASSERTED. The test above proves `load_gcp_env` spawns
    nothing; it says nothing about whether THIS MODULE still reaches the shell at
    import time, and that is what an independent reviewer could not get past.
    Restoring `ENV = verify_iam.load_env(str(REPO))` at the top of this file
    leaves every other test in it green on a host that has Git Bash, so only a
    collection run with bash genuinely gone can catch it.

    So: a child pytest, `--collect-only`, with every PATH directory holding
    `bash.exe` or `sh.exe` removed. Exit 0 and no collection error, or red."""
    stripped = []
    for d in os.environ.get("PATH", "").split(os.pathsep):
        try:
            names = {n.lower() for n in os.listdir(d)}
        except OSError:
            stripped.append(d)
            continue
        if {"bash.exe", "sh.exe", "bash", "sh"} & names:
            continue
        stripped.append(d)
    child = dict(os.environ)
    child["PATH"] = os.pathsep.join(stripped)
    assert shutil.which("bash", path=child["PATH"]) is None, (
        "could not construct a bash-free PATH, so this control would pass "
        "without testing anything")

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(pathlib.Path(__file__).name),
         "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=str(REPO / "tests"), capture_output=True, text=True, env=child)
    assert proc.returncode == 0, (
        "this file cannot be COLLECTED without bash, which is the defect "
        "reported on 2026-08-29: every test in it is lost as one collection "
        "error before a single one runs.\n%s\n%s"
        % (proc.stdout[-3000:], proc.stderr[-1500:]))
    assert "error" not in proc.stdout.lower(), proc.stdout[-3000:]


def test_the_shell_skip_fires_only_when_the_shell_is_actually_broken():
    """A HELPER THAT ALWAYS SKIPS IS A CHECK THAT PASSES WHILE MEASURING
    NOTHING - this repository's signature defect, fifteen recorded instances,
    and adding a skip helper is a fresh way to author the sixteenth. So the
    predicate is asserted to track the shell's real state rather than being a
    constant: where bash runs, `bash_env_or_problem` must report NO problem, and
    the four `RealGate` tests and the differential above therefore really ran."""
    env, problem = bash_env_or_problem()
    if BASH is None:
        pytest.skip(
            "no `bash` on PATH, so there is no working shell here whose healthy "
            "state the predicate could be checked against. UNMEASURED HERE: "
            "that `bash_env_or_problem` returns no problem on a host where bash "
            "works, and therefore that the five skips above are conditional "
            "rather than permanent.")
    assert problem is None, (
        "bash works here, so the skip predicate must not be reporting a "
        "problem; every bash-gated test in this file would be skipping while "
        "looking green. Reported: %s" % problem)
    assert env and env.get("CRUCIBLE_PROJECT") == PROJECT
    # AND THE WRAPPER, not only the predicate underneath it. A
    # `skip_without_a_working_bash` that skipped unconditionally would leave the
    # four `RealGate` tests and the differential reporting green and empty, and
    # a skip cannot fail a test by itself - so it is caught here and converted
    # into a failure.
    try:
        got = skip_without_a_working_bash("the self-check on this helper")
    except pytest.skip.Exception as e:
        raise AssertionError(
            "`skip_without_a_working_bash` skipped on a host where bash works, "
            "so every test that calls it is skipping while the run looks green. "
            "Reason it gave: %s" % e) from None
    assert got == env


def test_a_name_the_caller_depends_on_going_missing_RAISES(tmp_path):
    """A partial parse must never return a partial dict. An absent bucket name
    expands to `resource.labels.bucket_name=""`, which matches nothing, and a
    filter that matches nothing is this repository's signature defect."""
    from tests.conftest import GcpEnvError
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "gcp-env.sh").write_text(
        'export CRUCIBLE_PROJECT="p"\n', encoding="utf-8")
    with pytest.raises(GcpEnvError) as ei:
        load_gcp_env(str(root), require=("CRUCIBLE_SEALED_BUCKET",))
    assert "CRUCIBLE_SEALED_BUCKET" in str(ei.value)


def test_an_unexpandable_reference_RAISES_rather_than_expanding_to_nothing(tmp_path):
    """`gs://crucible-sealed-${SUFFIX}` with SUFFIX unset is
    `gs://crucible-sealed-`, which is a real-looking bucket name for a bucket
    that does not exist, and a query against it returns zero."""
    from tests.conftest import GcpEnvError
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "gcp-env.sh").write_text(
        'export CRUCIBLE_PROJECT="p"\n'
        'export CRUCIBLE_SEALED_BUCKET="gs://crucible-sealed-${SUFFIX}"\n',
        encoding="utf-8")
    with pytest.raises(GcpEnvError) as ei:
        load_gcp_env(str(root))
    assert "$SUFFIX" in str(ei.value)


def test_the_reader_expands_the_suffix_rather_than_returning_it_literally():
    """The one substitution the sealed bucket name actually depends on."""
    assert ENV["SUFFIX"]
    assert "${" not in ENV["CRUCIBLE_SEALED_BUCKET"]
    assert ENV["CRUCIBLE_SEALED_BUCKET"].endswith(ENV["SUFFIX"])
