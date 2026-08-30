"""test_holdout_assert.py - the seal assertions the transfer run makes for itself.

WHAT THESE TESTS ARE FOR, AND IT IS NOT "DOES IT RETURN A NUMBER"
================================================================
`crucible/transfer/holdout_assert.py` guards a measurement that happens ONCE.
Every function in it is a place where a wrong answer looks like a right one, so
almost everything below drives an assertion to RED and names which condition it
caught:

    the read went through some other callable    test_a_read_that_did_not_go_*
    24 entries from ONE object read 24 times     test_a_count_of_24_from_ONE_*
    the calibration leaked into the run window   test_a_run_window_that_still_*
    an intruder read before the run began        test_an_intruder_before_the_*
    preflight findings recorded and ignored      test_an_UNEVALUABLE_finding_*
    a settle interval of zero                    test_a_settle_interval_of_ZERO_*
    an uncalibrated downloader at the door       test_a_bare_downloader_is_*

THE THREE ASSERTIONS THAT WERE UNREACHABLE BEFORE THESE TESTS EXISTED
=====================================================================
`assert_clean_before_read` and `assert_read_exactly` both tested
`if r["intruders"]` on the result of `counter.compute()`. `compute()` RAISES
`HoldoutTouchInvalid` on any intruder rather than returning it, so neither `if`
could execute against the real counter. Both paths are now covered separately -
the exception path, which is what the real counter does, and the tally path,
which is reachable only because `counter` is injected and a double can report
intruders without raising. Testing only one of them was how a check that could
not fire survived being written down.

EVERY COLLABORATOR IS INJECTED AND NOTHING HERE TOUCHES A NETWORK.
There is no `gcloud` call, no GCS client, and no sleep of real duration in this
file. The counter, the gate, the downloader, the settle callable and the clock
are all doubles. What is tested is the SEQUENCE'S reasoning, not that Cloud
Logging returns what the doubles return; the live evidence for that half is
`tests/test_holdout_touch.py`'s `LIVE_ENTRIES` fixture and the artifact
`scripts/probe-g7-g8.py` writes.

STUB-ONLY, STATED SO A GREEN RUN IS NOT OVER-READ:
  1. **Ingestion lag is not tested.** `wait_for_log_settlement` is asserted to
     sleep the interval it was given. Whether 45 s is long enough is not a
     thing a unit test can establish.
  2. **The calibrated entries-per-read figure is never measured here.** It is
     asserted to be the delta the injected counter reports. The real number
     comes from a live canary read and exists nowhere until that runs.
  3. **`open_calibrated_downloader` is exercised with an injected GCS client
     double.** No credential is minted and no impersonation happens.
"""

import pytest

from crucible.transfer import gcs_reader as gr
from crucible.transfer import holdout_assert as ha
from crucible.transfer import sealed_io
from infra import holdout_touch as ht

BUCKET = "gs://crucible-sealed-x7"
NAMES = ["F4-dest-01-alpha.json", "F4-dest-02-bravo.json",
         "F4-dest-03-charlie.json"]
CANARY = gr.canary_uri(BUCKET)


# ===========================================================================
# Doubles.
# ===========================================================================

def tally(count=0, objects=None, distinct_reads=None, intruders=(),
          since="2026-08-29T12:00:00Z"):
    """A `HoldoutTouchCounter.compute()` result, in the shape `tally()` returns."""
    objects = [] if objects is None else list(objects)
    return {
        "count": count,
        "distinct_reads": len(objects) if distinct_reads is None
                          else distinct_reads,
        "distinct_objects": sorted(objects),
        "intruders": list(intruders),
        "since": since,
    }


class FakeCounter:
    """A counter whose successive `compute()` results are scripted.

    An entry that is an Exception instance is RAISED, which is how the real
    counter reports an intruder - `compute()` never returns a tally containing
    one. The last entry repeats, so a test that only cares about one answer
    passes one.
    """

    def __init__(self, results, since="2026-08-29T12:00:00Z"):
        self.since = since
        self.results = list(results)
        self.calls = 0

    def compute(self):
        self.calls += 1
        r = self.results[min(self.calls - 1, len(self.results) - 1)]
        if isinstance(r, Exception):
            raise r
        return r

    def __call__(self):
        return self.compute()["count"]


class FakeGate:
    def __init__(self, findings):
        self.findings = findings
        self.calls = 0

    def preflight(self):
        self.calls += 1
        return list(self.findings)


def finding(gate, status):
    return {"gate": gate, "check": "x", "status": status}


def recorder():
    """A bare downloader that records what it was asked for."""
    seen = []

    def download(uri):
        seen.append(uri)
        return b'{"family_id": "fam_f4"}'

    download.seen = seen
    return download


def calibrated(per_object=1, counter=None, downloader=None,
               finished_at="2026-08-29T12:00:00Z"):
    """A completed calibration, built the way the real one is."""
    counter = counter or FakeCounter([tally(0), tally(per_object,
                                                      objects=[CANARY])])
    dl = downloader or recorder()
    return ha.calibrate_on_canary(counter, dl, CANARY,
                                  settle=lambda: None,
                                  clock=lambda: _at(finished_at))


def _at(stamp):
    import datetime
    return datetime.datetime.strptime(
        stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def read_through(cal, names=NAMES, bucket=BUCKET):
    """Drive the real `sealed_io.read_sealed_once` through the calibration.

    Deliberately the REAL function and not a loop written here: the uris the
    assertion expects and the uris the run produces have to be the same
    construction, and a test that builds its own would prove they agree with
    each other rather than with the shipped read path.
    """
    return sealed_io.read_sealed_once(bucket, names, cal)


# ===========================================================================
# The two spellings of one read. A coupling test, not a formatting test.
# ===========================================================================

def test_the_uri_this_module_expects_is_the_uri_sealed_io_actually_requests():
    cal = calibrated()
    read_through(cal)
    assert cal.sealed_uris == [ha.sealed_object_uri(BUCKET, n) for n in NAMES]


def test_the_resource_name_matches_the_shape_the_live_audit_log_emits():
    # Verbatim from tests/test_holdout_touch.py's LIVE_ENTRIES, which was read
    # out of the real log rather than written by hand.
    assert (ha.sealed_object_resource(BUCKET, "_probe/canary.txt")
            == "projects/_/buckets/crucible-sealed-x7/objects/"
               "families/_probe/canary.txt")


def test_a_bucket_with_or_without_the_scheme_resolves_the_same():
    assert (ha.sealed_object_resource("gs://b/", "n")
            == ha.sealed_object_resource("b", "n"))


# ===========================================================================
# The settle interval.
# ===========================================================================

def test_the_settle_interval_defaults_to_the_repo_wide_constant():
    slept = []
    got = ha.wait_for_log_settlement(sleep=slept.append)
    assert slept == [ht.DEFAULT_SETTLE_SECONDS]
    assert got == ht.DEFAULT_SETTLE_SECONDS


def test_the_repo_wide_settle_default_is_not_zero():
    # A default of zero would make "I did not wait" and "nothing was read"
    # produce the same number on the one run that cannot be repeated.
    assert ht.DEFAULT_SETTLE_SECONDS > 0


def test_a_settle_interval_of_ZERO_is_refused_rather_than_treated_as_no_wait():
    for bad in (0, 0.0, -1, None):
        with pytest.raises(ha.HoldoutAssertionError) as e:
            ha.wait_for_log_settlement(bad, sleep=lambda _s: None)
        assert "UNDERCOUNT" in str(e.value)


def test_an_explicit_interval_is_slept_and_not_the_default():
    slept = []
    ha.wait_for_log_settlement(7.5, sleep=slept.append)
    assert slept == [7.5]


# ===========================================================================
# Calibration, and the callable it hands back.
# ===========================================================================

def test_calibration_returns_the_downloader_it_was_given_wrapped():
    raw = recorder()
    cal = calibrated(per_object=2, downloader=raw)
    assert isinstance(cal, ha.CalibratedDownloader)
    assert cal.per_object == 2
    # The wrapper forwards to the SAME object it was handed.
    assert cal("gs://b/o") == b'{"family_id": "fam_f4"}'
    assert raw.seen[-1] == "gs://b/o"


def test_the_canary_read_goes_through_the_wrapper_and_is_not_a_sealed_read():
    cal = calibrated()
    assert cal.uris == [CANARY]
    assert cal.sealed_uris == []          # the canary is not one of the 24


def test_a_calibration_that_counts_no_new_entries_is_refused():
    # before == after. The runner's reads are not being classified as content
    # reads, so an expected value derived from this would be zero - and zero
    # passes G7c against a log nobody queried.
    c = FakeCounter([tally(0), tally(0)])
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.calibrate_on_canary(c, recorder(), CANARY, settle=lambda: None)
    assert "0 counted entries" in str(e.value)


def test_calibration_settles_BETWEEN_the_two_counts_and_not_after_both():
    order = []
    c = FakeCounter([tally(0), tally(1, objects=[CANARY])])

    def counting_compute():
        order.append("count")
        return FakeCounter.compute(c)

    c.compute = counting_compute

    def dl(uri):
        order.append("read")
        return b""

    ha.calibrate_on_canary(c, dl, CANARY, settle=lambda: order.append("settle"))
    assert order == ["count", "read", "settle", "count"]


def test_an_intruder_during_calibration_is_reported_as_Outcome_D():
    c = FakeCounter([ht.HoldoutTouchInvalid("someone read it")])
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.calibrate_on_canary(c, recorder(), CANARY, settle=lambda: None)
    assert "Outcome D" in str(e.value)


def test_calibrating_an_already_calibrated_downloader_is_refused():
    cal = calibrated()
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.calibrate_on_canary(FakeCounter([tally(0), tally(1)]), cal, CANARY,
                               settle=lambda: None)
    assert "already-calibrated" in str(e.value)


def test_the_calibration_describes_itself_for_the_bundle():
    cal = calibrated(per_object=2)
    d = cal.describe()
    assert d["entries_per_read"] == 2
    assert d["canary_uri"] == CANARY
    assert d["calibration_finished_at"] == "2026-08-29T12:00:00Z"


# ===========================================================================
# The door. Nothing uncalibrated reaches the holdout.
# ===========================================================================

def test_a_bare_downloader_is_refused_at_the_door():
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.require_calibrated(recorder())
    assert "CalibratedDownloader" in str(e.value)


def test_a_wrapper_that_was_never_calibrated_is_refused():
    w = ha.CalibratedDownloader(recorder(), CANARY)
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.require_calibrated(w)
    assert "never calibrated" in str(e.value)


def test_a_completed_calibration_passes_the_door_unchanged():
    cal = calibrated()
    assert ha.require_calibrated(cal) is cal


def test_open_calibrated_downloader_builds_and_calibrates_in_one_call():
    """The whole point of the one-call factory: the object calibrated is the
    object returned, and there is no second one."""

    class FakeBlob:
        def download_as_bytes(self, retry=None):
            return b"canary"

    class FakeBucket:
        def blob(self, path):
            return FakeBlob()

    class FakeClient:
        def bucket(self, name):
            return FakeBucket()

    c = FakeCounter([tally(0), tally(1, objects=[CANARY])])
    cal = gr.open_calibrated_downloader(c, BUCKET, client=FakeClient(),
                                        settle=lambda: None)
    assert ha.require_calibrated(cal) is cal
    assert cal.per_object == 1
    assert cal.uris == [CANARY]


# ===========================================================================
# The run window.
# ===========================================================================

def test_the_run_window_opens_strictly_after_the_calibration_finished():
    cal = calibrated(finished_at="2026-08-29T12:00:00Z")
    since = ha.open_run_window(cal, clock=lambda: _at("2026-08-29T12:01:00Z"))
    assert since == "2026-08-29T12:01:00Z"


def test_a_run_window_at_the_SAME_second_as_the_calibration_is_refused():
    # Equality means the two windows share a whole second, and an event inside
    # that second belongs to both.
    cal = calibrated(finished_at="2026-08-29T12:00:00Z")
    with pytest.raises(ht.HoldoutTouchUnevaluable) as e:
        ha.open_run_window(cal, clock=lambda: _at("2026-08-29T12:00:00Z"))
    assert "strictly after" in str(e.value)


def test_a_run_window_BEFORE_the_calibration_is_refused():
    cal = calibrated(finished_at="2026-08-29T12:00:00Z")
    with pytest.raises(ht.HoldoutTouchUnevaluable):
        ha.open_run_window(cal, clock=lambda: _at("2026-08-29T11:59:00Z"))


def test_a_run_window_before_the_attestation_floor_is_refused():
    with pytest.raises(ht.HoldoutTouchUnevaluable) as e:
        ha.open_run_window(clock=lambda: _at("2026-08-20T00:00:00Z"))
    assert "attestation floor" in str(e.value)


def test_open_run_window_refuses_an_uncalibrated_calibration():
    w = ha.CalibratedDownloader(recorder(), CANARY)
    with pytest.raises(ha.HoldoutAssertionError):
        ha.open_run_window(w, clock=lambda: _at("2026-08-29T12:00:00Z"))


# ===========================================================================
# The preflights. Running them is not the same as reading them.
# ===========================================================================

def test_an_empty_findings_list_is_a_check_that_did_not_run():
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.preflight_no_candidate(FakeGate([]))
    assert "did not run" in str(e.value)


def test_preflight_is_called_with_no_candidate_anywhere():
    g = FakeGate([finding("G7c", "PASS")])
    out = ha.preflight_no_candidate(g)
    assert g.calls == 1 and len(out) == 1


def test_a_clean_findings_list_passes_the_reader():
    fs = [finding("G7c", "PASS"), finding("G8", "PASS")]
    assert ha.assert_preflight_clean(fs) is fs


def test_a_FAILED_finding_stops_the_run():
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.assert_preflight_clean([finding("G7c", "PASS"),
                                   finding("G8", "FAIL")], label="before read")
    assert "before read" in str(e.value) and "G8" in str(e.value)


def test_an_UNEVALUABLE_finding_stops_the_run_exactly_like_a_FAIL():
    # gate_rule.v1.yaml gives G7 absent_or_unevaluable: RUN_INVALID. An
    # unevaluable seal assertion is not a smaller result than a failed one.
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.assert_preflight_clean([finding("G7c", "UNEVALUABLE")])
    assert "G7c" in str(e.value)


def test_summarise_reads_object_findings_as_well_as_dicts():
    class F:
        gate, status = "G7c", "FAIL"
    ok, fails, uneval = ha.summarise_findings([F()])
    assert not ok and fails == ["G7c"] and uneval == []


# ===========================================================================
# The window must open empty.
# ===========================================================================

def test_a_clean_empty_window_is_returned():
    r = ha.assert_clean_before_read(FakeCounter([tally(0)]))
    assert r["count"] == 0


def test_an_intruder_before_the_run_is_Outcome_D_via_the_RAISED_path():
    # THE REACHABLE PATH. The real counter raises rather than returning a tally
    # with intruders in it, so this - not the `if` below - is what fires live.
    c = FakeCounter([ht.HoldoutTouchInvalid("armorer read it at 11:59")])
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.assert_clean_before_read(c)
    assert "Outcome D" in str(e.value)
    assert "armorer read it at 11:59" in str(e.value)


def test_an_intruder_REPORTED_IN_THE_TALLY_is_also_refused():
    # Reachable only because `counter` is injected. A double, or any future
    # counter that reports intruders without raising, must not walk past.
    c = FakeCounter([tally(0, intruders=[{"principal": "x"}])])
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.assert_clean_before_read(c)
    assert "Outcome D" in str(e.value)


def test_a_run_window_that_still_contains_the_calibration_read_is_refused():
    # The calibration leak, caught by measurement rather than by the clock.
    c = FakeCounter([tally(1, objects=[CANARY])])
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.assert_clean_before_read(c)
    assert "before the run read anything" in str(e.value)
    assert CANARY in str(e.value)


# ===========================================================================
# The expected value.
# ===========================================================================

def test_the_expected_count_is_objects_times_the_calibrated_entries_per_read():
    cal = calibrated(per_object=2)
    assert ha.expected_content_read_count(NAMES, cal) == 6


def test_a_second_pass_over_the_holdout_is_an_argument_and_not_an_assumption():
    cal = calibrated(per_object=1)
    assert ha.expected_content_read_count(NAMES, cal, passes=2) == 6


def test_zero_passes_would_expect_zero_reads_and_is_refused():
    cal = calibrated(per_object=1)
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.expected_content_read_count(NAMES, cal, passes=0)
    assert "nobody queried" in str(e.value)


def test_the_expected_count_cannot_be_computed_from_an_uncalibrated_wrapper():
    w = ha.CalibratedDownloader(recorder(), CANARY)
    with pytest.raises(ha.HoldoutAssertionError):
        ha.expected_content_read_count(NAMES, w)


# ===========================================================================
# THE HEADLINE. What G7c's single integer cannot see.
# ===========================================================================

def _good_log(per_object=1, names=NAMES):
    return tally(len(names) * per_object,
                 objects=[ha.sealed_object_resource(BUCKET, n) for n in names],
                 distinct_reads=len(names))


def test_the_intended_read_passes_every_condition():
    cal = calibrated()
    read_through(cal)
    r = ha.assert_read_exactly(FakeCounter([_good_log()]), NAMES, BUCKET, cal)
    assert r["count"] == len(NAMES)


def test_a_count_of_24_from_ONE_object_read_24_times_is_caught():
    # The exact case the module docstring names: G7c's integer is satisfied and
    # the experiment read one object twenty four times.
    cal = calibrated()
    read_through(cal)
    one = ha.sealed_object_resource(BUCKET, NAMES[0])
    log = tally(len(NAMES), objects=[one], distinct_reads=1)
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.assert_read_exactly(FakeCounter([log]), NAMES, BUCKET, cal)
    assert "the object SET read is not the set intended" in str(e.value)


def test_the_right_count_over_the_right_objects_with_a_double_read_is_caught():
    # count and set both right; one object read twice and another not at all is
    # still visible in distinct_reads.
    cal = calibrated()
    read_through(cal)
    log = _good_log()
    log["distinct_reads"] = len(NAMES) - 1
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.assert_read_exactly(FakeCounter([log]), NAMES, BUCKET, cal)
    assert "distinct_reads is" in str(e.value)


def test_a_read_that_did_not_go_through_the_calibrated_callable_is_caught():
    # The audit log is perfect. The client-side witness is empty, which means
    # the entries-per-read figure describes a path this run did not take.
    cal = calibrated()
    sealed_io.read_sealed_once(BUCKET, NAMES, recorder())   # some OTHER callable
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.assert_read_exactly(FakeCounter([_good_log()]), NAMES, BUCKET, cal)
    assert "never invoked after calibration" in str(e.value)


def test_the_client_asking_for_a_set_the_run_did_not_declare_is_caught():
    cal = calibrated()
    read_through(cal, names=NAMES[:2] + ["F4-dest-99-zulu.json"])
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.assert_read_exactly(FakeCounter([_good_log()]), NAMES, BUCKET, cal)
    assert "different set than the run declared" in str(e.value)


def test_the_client_asking_twice_for_one_object_is_caught():
    cal = calibrated()
    read_through(cal)
    cal(ha.sealed_object_uri(BUCKET, NAMES[0]))      # a stray second read
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.assert_read_exactly(FakeCounter([_good_log()]), NAMES, BUCKET, cal)
    assert "more than" in str(e.value)


def test_a_count_that_misses_the_calibrated_multiplier_is_caught():
    # Calibrated at two entries per read; the log shows one per object.
    cal = calibrated(per_object=2)
    read_through(cal)
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.assert_read_exactly(FakeCounter([_good_log(per_object=1)]),
                               NAMES, BUCKET, cal)
    assert "expected %d" % (len(NAMES) * 2) in str(e.value)


def test_an_intruder_during_the_read_is_Outcome_D_via_the_RAISED_path():
    cal = calibrated()
    read_through(cal)
    c = FakeCounter([ht.HoldoutTouchInvalid("red read it mid-run")])
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.assert_read_exactly(c, NAMES, BUCKET, cal)
    assert "Outcome D" in str(e.value)


def test_an_intruder_REPORTED_IN_THE_TALLY_during_the_read_is_also_refused():
    cal = calibrated()
    read_through(cal)
    log = _good_log()
    log["intruders"] = [{"principal": "x"}]
    with pytest.raises(ha.HoldoutAssertionError) as e:
        ha.assert_read_exactly(FakeCounter([log]), NAMES, BUCKET, cal)
    assert "Outcome D" in str(e.value)


def test_assert_read_exactly_refuses_an_uncalibrated_downloader():
    with pytest.raises(ha.HoldoutAssertionError):
        ha.assert_read_exactly(FakeCounter([_good_log()]), NAMES, BUCKET,
                               recorder())


# ===========================================================================
# The whole sequence, in the order the runner performs it.
# ===========================================================================

def test_the_full_sequence_runs_end_to_end_offline():
    """Every step in call order, with nothing real behind any of them.

    This is the shape `scripts/record-f4-transfer.py` consumes. It is here so
    that "the runner can call this" is a passing test rather than a claim in a
    report.
    """
    steps = []

    # 1. calibrate, in the calibration's OWN window
    cal_counter = FakeCounter([tally(0), tally(1, objects=[CANARY])],
                              since="2026-08-29T11:59:00Z")
    cal = calibrated(counter=cal_counter, finished_at="2026-08-29T12:00:00Z")
    steps.append(("calibrated", cal.per_object))

    # 2. open the run window, strictly after
    since = ha.open_run_window(cal, clock=lambda: _at("2026-08-29T12:01:00Z"))
    steps.append(("window", since))

    # 3. a counter for THAT window; 4. assert it opens empty
    run_counter = FakeCounter([tally(0), _good_log()], since=since)
    ha.assert_clean_before_read(run_counter)
    steps.append(("clean", True))

    # 5. the first preflight, with no candidate anywhere
    ha.assert_preflight_clean(
        ha.preflight_no_candidate(FakeGate([finding("G7c", "PASS")])),
        label="before read")
    steps.append(("preflight-1", True))

    # 6. the sealed read, through the calibrated callable
    pairs = read_through(cal)
    steps.append(("read", len(pairs)))

    # 7. settle
    slept = []
    ha.wait_for_log_settlement(sleep=slept.append)

    # 8. assert the count, the distinct reads AND the object set
    ha.assert_read_exactly(run_counter, NAMES, BUCKET, cal)
    steps.append(("asserted", True))

    # 9. the second preflight, against the calibrated expectation
    ha.assert_preflight_clean(
        ha.preflight_no_candidate(FakeGate([finding("G7c", "PASS")])),
        label="after read")
    steps.append(("preflight-2", True))

    assert [s[0] for s in steps] == [
        "calibrated", "window", "clean", "preflight-1", "read", "asserted",
        "preflight-2"]
    assert slept == [ht.DEFAULT_SETTLE_SECONDS]
    assert ha.expected_content_read_count(NAMES, cal) == len(NAMES)


def test_the_counter_the_assertions_read_is_the_counter_the_GATE_reads():
    """`make_run_counter` produces what `RealGate(holdout_touch=)` requires: a
    zero-arg callable returning an int. If those were two different objects the
    belt and the gate would be measuring two windows."""
    from infra import verify_iam
    import pathlib
    env = verify_iam.load_env(str(pathlib.Path(__file__).resolve().parent.parent))
    c = ha.make_run_counter(env, since=ht.ATTESTATION_FLOOR_UTC,
                            log_read=lambda *a: [],
                            policy_fetch=lambda: {})
    assert isinstance(c, ht.HoldoutTouchCounter)
    assert callable(c) and c.since == ht.ATTESTATION_FLOOR_UTC


# ===========================================================================
# The read path's own names. Sourced, and pointed at the RELOCATED canary.
# ===========================================================================

def test_the_permitted_principal_is_derived_from_gcp_env_and_not_retyped():
    import pathlib
    from infra import verify_iam
    env = verify_iam.load_env(str(pathlib.Path(__file__).resolve().parent.parent))
    want = "%s@%s.iam.gserviceaccount.com" % (env["SA_SEALED_EVAL"],
                                              env["CRUCIBLE_PROJECT"])
    assert gr.sealed_eval_principal() == want
    # And it is the SAME identity the counter permits, derived the same way.
    c = ht.HoldoutTouchCounter(env, since=ht.ATTESTATION_FLOOR_UTC,
                               log_read=lambda *a: [], policy_fetch=lambda: {})
    assert c.permitted_principals == {want}


def test_gcs_reader_carries_no_fully_qualified_service_account_literal():
    """It carried one until 2026-08-29. `scripts/gcp-env.sh` is the single name
    source and G7/G8 grep these strings literally, so a second copy does not
    fail loudly when it drifts - it yields an unevaluable gate."""
    import inspect
    src = inspect.getsource(gr)
    body = "\n".join(l for l in src.splitlines()
                     if ".iam.gserviceaccount.com" in l and "%s@%s" not in l)
    assert body == "", body


def test_the_canary_uri_points_at_the_RELOCATED_object_and_not_under_families():
    """Eric ruled 2026-08-22 that the canary be MOVED rather than excluded from
    the counter (`docs/NEEDS-ERIC.md` item 12), executed the same day and
    verified against the live bucket 2026-08-23. A canary still under
    `families/` would be counted by the gate's own positive control."""
    assert gr.canary_uri(BUCKET) == "gs://crucible-sealed-x7/_probe/canary.txt"
    assert "families/" not in gr.CANARY_OBJECT


# ============================================================================
# THE CALIBRATION / RUN-WINDOW RACE
#
# `calibrate_on_canary` stamps `finished_at` truncated to a whole second, and
# the runner calls `open_run_window(cal)` on the very next line. The guard
# demands the run window open STRICTLY after that instant, so whenever both
# calls land in the same second - which is the normal case, they are adjacent
# statements - the run raises HoldoutTouchUnevaluable and stops.
#
# Whether the sealed run proceeds therefore depends on coincidentally crossing
# a wall-clock second between two adjacent function calls. That is a coin flip
# on a run that happens once.
#
# THE GUARD IS RIGHT AND STAYS. Equality means the two windows share a whole
# second and an event inside it belongs to both, so the calibration's canary
# read could be counted as a holdout touch. The defect is that nobody wrote the
# wait the guard's own error message prescribes: "Wait for the clock to pass
# %s and open again."
#
# This aborts BEFORE any sealed object is read, so it is safe rather than
# corrupting. It is still a P1: it can stop the scheduled run for a reason that
# has nothing to do with the seal, at the one moment there is no second try.
# ============================================================================

def _cal(finished_at):
    """A REAL completed calibration, stamped at a chosen instant.

    Deliberately the module's own `calibrated()` helper rather than a stub with
    a `finished_at` attribute: `require_calibrated` refuses anything that is not
    a genuine `CalibratedDownloader`, and a test that fed it a fake would be
    exercising a path the production run cannot take.
    """
    return calibrated(finished_at=finished_at)


def test_the_race_is_real_the_strict_guard_refuses_the_same_second():
    """Reproduce the defect before asserting the repair.

    Not a hypothetical: `now_utc` truncates to whole seconds and the two calls
    are adjacent statements in `sealed_drive_lifecycle`.
    """
    same = "2026-08-29T12:00:00Z"
    with pytest.raises(Exception) as exc:
        ha.open_run_window(_cal(same), clock=lambda: _at(same))
    assert "strictly after" in str(exc.value)


def test_the_runner_waits_for_the_next_second_instead_of_dying():
    """THE REPAIR. Wait, then open - which is what the guard's own error text
    prescribes and what nothing in the production path did."""
    ticks = []
    times = ["2026-08-29T12:00:00Z", "2026-08-29T12:00:00Z",
             "2026-08-29T12:00:01Z"]
    it = iter(times)

    since = ha.open_run_window_when_clear(
        _cal("2026-08-29T12:00:00Z"),
        clock=lambda: _at(next(it)),
        sleep=ticks.append)

    assert since == "2026-08-29T12:00:01Z"
    assert ticks, "it opened a window without ever waiting"


def test_waiting_is_bounded_and_the_bound_refuses_rather_than_proceeds():
    """A clock that never advances must not hang a supervised one-shot forever.

    Proceeding on timeout would be worse: it would mean opening a window that
    overlaps the calibration, which is the exact attribution failure the strict
    guard exists to prevent. So the bound refuses.
    """
    frozen = "2026-08-29T12:00:00Z"
    with pytest.raises(Exception) as exc:
        ha.open_run_window_when_clear(
            _cal(frozen), clock=lambda: _at(frozen), sleep=lambda s: None,
            max_wait_seconds=3)
    # THE SPECIFIC BOUND, not just "something raised". Asserting only that an
    # exception escaped let a mutation deleting this bound stay green, because
    # a second guard beside it produced a different exception with the same
    # shape. That second guard turned out to be unreachable and was removed;
    # this assertion is what would have said so.
    assert "waited" in str(exc.value) and "3.0s" in str(exc.value), (
        "the elapsed-time bound is not what refused: %s" % exc.value)


# KNOWN WEAKNESS, RECORDED RATHER THAN PAPERED OVER. Deleting the elapsed-time
# bound does not make this test FAIL - it makes it HANG, because that bound is
# the loop's only exit and the suite then runs until something kills it. The
# mutation is still killed, but as a timeout rather than as a named failure,
# and a timeout is a worse signal: CI reports the wrong thing and a reader has
# to guess.
#
# The obvious repair - a second, independent bound - was tried and reverted.
# `waited` advances arithmetically with no reference to any clock, so the
# elapsed check always fires first and an iteration cap beside it can never be
# reached. An unreachable guard is a check that cannot fail, which would have
# been this repository's signature defect committed inside the fix for it.
#
# The real repair is a per-test timeout (pytest-timeout), which is a dependency
# decision and not one to take the night before an unrepeatable run.


def test_a_window_already_clear_does_not_wait_at_all():
    """The control. Every test above passes against an implementation that
    always sleeps, which would add a needless delay to every run and, worse,
    would hide a guard that had stopped refusing anything."""
    ticks = []
    since = ha.open_run_window_when_clear(
        _cal("2026-08-29T12:00:00Z"),
        clock=lambda: _at("2026-08-29T12:00:05Z"),
        sleep=ticks.append)
    assert since == "2026-08-29T12:00:05Z"
    assert ticks == [], "it waited when the window was already clear"


def test_the_sealed_lifecycle_uses_the_waiting_form(monkeypatch):
    """THE INTEGRATION ASSERTION.

    Every test above passes with `open_run_window_when_clear` written and never
    called - which is precisely the state the adjudication gate was found in
    hours earlier. So this reads the production path and requires the waiting
    form to be the one it reaches for.
    """
    import importlib.util
    import inspect
    import pathlib as _pl

    root = _pl.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "record_f4_transfer_race", root / "scripts" / "record-f4-transfer.py")
    rt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rt)

    src = inspect.getsource(rt.sealed_drive_lifecycle)
    assert "open_run_window_when_clear" in src, (
        "the lifecycle still calls the non-waiting form, so a calibration and "
        "a run window landing in the same second aborts the run")
    assert "ha.open_run_window(" not in src, (
        "both forms are reachable from the lifecycle; the strict one will win "
        "on whichever line runs first")


def test_a_window_below_the_attestation_floor_raises_instead_of_being_waited_out():
    """THE BRANCH THAT CAUGHT NOTHING ON ITS FIRST MUTATION PASS.

    The wait exists for ONE refusal: a run window that is not strictly after
    the calibration. Every other `HoldoutTouchUnevaluable` has to propagate
    immediately.

    The one that matters is the attestation floor. Data Access logging is not
    retroactive, so a window opening before the floor covers time the audit log
    cannot speak to - and no amount of waiting fixes it, because waiting moves
    the window LATER and the problem is that the CLOCK is earlier than the
    floor. Retrying it would spin for the full two minutes and then report a
    problem that was decidable on the first call.

    Written after `if "strictly after" not in str(exc): raise` was mutated to
    `if False: raise` and no test noticed. That branch is the difference
    between a bounded wait and a wait that swallows every diagnosis the window
    opener can produce.
    """
    ticks = []
    before_floor = "2020-01-01T00:00:00Z"
    with pytest.raises(Exception) as exc:
        ha.open_run_window_when_clear(
            calibrated(finished_at="2019-12-31T00:00:00Z"),
            clock=lambda: _at(before_floor),
            sleep=ticks.append)
    assert "attestation floor" in str(exc.value), (
        "the floor violation was not reported as one: %s" % exc.value)
    assert ticks == [], (
        "it WAITED on a floor violation. Waiting moves the window later and "
        "the complaint is that the clock is earlier than the floor, so this "
        "spins for the full bound and then reports what was knowable at once.")
