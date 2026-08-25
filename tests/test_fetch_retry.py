"""test_fetch_retry.py - the retry that shipped with no test at all.

WHY THIS FILE EXISTS
====================
Run 10 of the 2026-08-25 overnight batch went RUN_INVALID because a single
`gcloud` invocation failed transiently, and it said nothing about why: the
error interpolated `p.stderr` alone and that exit carried an EMPTY stderr, so
the finding read

    the counter raised: could not read the project IAM policy
    (could not fetch project IAM policy: ), so whether Data Access logging is
    still on is unknown

naming no cause at all. `57f4e94` fixed both halves - bounded retry, and an
error that carries the return code - in `infra/verify_iam.py::gcloud_json`
ONLY. Two other call sites do the same job and were left single-shot, and they
are the two that actually failed:

    infra/holdout_touch.py::gcloud_log_read       G7c, the log read
    crucible/conductor/real_gate.py::_run_capture G7a, all four probe arms

`grep -rn "FETCH_ATTEMPTS" tests/` returned NOTHING before this file. The retry
shipped unproven, which is the same defect as a check that cannot fail wearing
different clothes - the exact sentence that commit message used about the error
text it was replacing.

WHAT IS PROVEN HERE, AND WHAT IS NOT
====================================
PROVEN, against the real functions with an injected runner:
  * a transient failure is retried and the eventual success is returned
  * a PERSISTENT failure RAISES, and never degrades to an empty result
  * the raised message names the return code even when stderr and stdout are
    both empty - the run-10 shape
  * a SEMANTIC answer is returned on the first attempt and is never retried:
    a real 403, a real impersonation refusal, and a successful read
  * exhausting the G7a probe's attempts still classifies UNEVALUABLE, which is
    RUN_INVALID, and never as a boundary that held
  * one retry policy, `verify_iam`'s, read by all three sites

CALIBRATED, which is the part that makes the rest mean anything:
  * `test_CALIBRATION_*` re-runs the transient cases with `FETCH_ATTEMPTS`
    forced to 1 and asserts they FAIL. Without that, "fail then succeed
    returns the success" is satisfiable by a function that never retried and
    got lucky on ordering, and nine straight green runs would be
    indistinguishable from a broken harness.

NOT PROVEN: that gcloud actually fails this way, how often, or why. Section 7
of `docs/design/g7-unevaluable-2026-08-25.md` says the artifact that would have
carried run 10's real cause was overwritten by a racing re-execution and that
it cannot be settled retrospectively. These tests prove the handling, not the
diagnosis.
"""

import json

import pytest

from crucible.conductor import real_gate as rg
from infra import holdout_touch as ht
from infra import verify_iam


class Result:
    """The three fields of `subprocess.CompletedProcess` anything here reads."""

    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def scripted(*results):
    """A runner that hands back `results` in order and records every call.

    The last result repeats, so "always fails" is one entry rather than a list
    sized to whatever FETCH_ATTEMPTS happens to be - a test that hardcodes the
    attempt count in its fixture stops testing the constant.
    """
    calls = []

    def runner(argv):
        calls.append(list(argv))
        return results[min(len(calls) - 1, len(results) - 1)]

    runner.calls = calls
    return runner


def naps():
    slept = []
    return slept, slept.append


# The run-10 shape: a non-zero exit with nothing on either stream. A real API
# denial always writes a message, so this is a process-level or transport-level
# failure and it is the only thing worth asking again.
EMPTY_FAILURE = Result(1, "", "")
DENIAL = Result(1, "", "ERROR: (gcloud.projects.get-iam-policy) PERMISSION_DENIED")


# ===========================================================================
# ONE POLICY, NOT THREE.
# ===========================================================================

def test_all_three_call_sites_read_the_same_retry_policy():
    """Three retry policies for one decision is three sources of truth, and the
    next person to tune one would tune one of three. `holdout_touch` and
    `real_gate` must not declare their own."""
    assert verify_iam.FETCH_ATTEMPTS >= 2
    assert len(verify_iam.FETCH_BACKOFF) >= 1
    assert not hasattr(ht, "FETCH_ATTEMPTS")
    assert not hasattr(ht, "FETCH_BACKOFF")
    assert not hasattr(rg, "FETCH_ATTEMPTS")
    assert not hasattr(rg, "FETCH_BACKOFF")


def test_the_backoff_index_cannot_run_off_the_end():
    """Raising FETCH_ATTEMPTS past the length of FETCH_BACKOFF must not turn a
    transient fetch into an IndexError - a different failure, reported in a way
    nobody would trace back to gcloud."""
    for attempt in range(1, len(verify_iam.FETCH_BACKOFF) + 5):
        assert ht._fetch_backoff(attempt) > 0                # noqa: SLF001


# ===========================================================================
# infra/verify_iam.py::gcloud_json - retried since 57f4e94, untested until now.
# ===========================================================================

def test_gcloud_json_retries_a_transient_failure_and_returns_the_success():
    runner = scripted(EMPTY_FAILURE, Result(0, '{"bindings": []}'))
    slept, sleep = naps()
    out = verify_iam.gcloud_json(["gcloud", "x"], "project IAM policy",
                                 runner=runner, sleep=sleep)
    assert out == {"bindings": []}
    assert len(runner.calls) == 2
    assert slept == [verify_iam.FETCH_BACKOFF[0]]


def test_gcloud_json_RAISES_after_a_persistent_failure_and_never_returns_empty():
    runner = scripted(DENIAL)
    slept, sleep = naps()
    with pytest.raises(RuntimeError) as ei:
        verify_iam.gcloud_json(["gcloud", "x"], "project IAM policy",
                               runner=runner, sleep=sleep)
    assert len(runner.calls) == verify_iam.FETCH_ATTEMPTS
    assert len(slept) == verify_iam.FETCH_ATTEMPTS - 1
    assert "PERMISSION_DENIED" in str(ei.value)
    assert "exit 1" in str(ei.value)


def test_gcloud_json_names_the_return_code_when_BOTH_STREAMS_ARE_EMPTY():
    """THE RUN-10 SHAPE. The old error interpolated stderr alone and rendered
    as `could not fetch project IAM policy: ` - a diagnostic dead end."""
    runner = scripted(EMPTY_FAILURE)
    with pytest.raises(RuntimeError) as ei:
        verify_iam.gcloud_json(["gcloud", "x"], "project IAM policy",
                               runner=runner, sleep=lambda _s: None)
    msg = str(ei.value)
    assert "no stderr and no stdout" in msg
    assert "exit 1" in msg
    assert not msg.rstrip().endswith(":")


def test_gcloud_json_does_not_retry_a_SUCCESS():
    runner = scripted(Result(0, "{}"))
    assert verify_iam.gcloud_json(["gcloud", "x"], "w", runner=runner,
                                  sleep=lambda _s: None) == {}
    assert len(runner.calls) == 1


def test_gcloud_json_does_not_retry_UNPARSEABLE_output_from_a_zero_exit():
    """Malformed JSON from a successful invocation is a semantic answer, not a
    transient. Asking again produces the same bytes and only costs time."""
    runner = scripted(Result(0, "not json"))
    with pytest.raises(RuntimeError):
        verify_iam.gcloud_json(["gcloud", "x"], "w", runner=runner,
                               sleep=lambda _s: None)
    assert len(runner.calls) == 1


def test_CALIBRATION_the_gcloud_json_transient_case_FAILS_without_the_retry(
        monkeypatch):
    """THE CONTROL ON THE TEST ABOVE. With one attempt allowed, the identical
    fail-then-succeed script must RAISE. A retry test that passes with retry
    disabled is measuring nothing."""
    monkeypatch.setattr(verify_iam, "FETCH_ATTEMPTS", 1)
    runner = scripted(EMPTY_FAILURE, Result(0, '{"bindings": []}'))
    with pytest.raises(RuntimeError):
        verify_iam.gcloud_json(["gcloud", "x"], "w", runner=runner,
                               sleep=lambda _s: None)
    assert len(runner.calls) == 1


# ===========================================================================
# infra/holdout_touch.py::gcloud_log_read - G7c. NO retry before 2026-08-25.
# ===========================================================================

ONE_ENTRY = json.dumps([{"timestamp": "2026-08-22T19:31:19.292722382Z",
                         "protoPayload": {"methodName": "storage.objects.get"}}])


def test_log_read_retries_a_transient_failure_and_returns_the_entries():
    runner = scripted(EMPTY_FAILURE, Result(0, ONE_ENTRY))
    slept, sleep = naps()
    out = ht.gcloud_log_read("p", "filt", 10, runner=runner, sleep=sleep)
    assert len(out) == 1
    assert len(runner.calls) == 2
    assert slept == [verify_iam.FETCH_BACKOFF[0]]


def test_log_read_RAISES_after_a_persistent_failure_and_NEVER_returns_empty():
    """An empty list is indistinguishable from a clean seal. That is the whole
    failure `infra/holdout_touch.py` exists to refuse, and a fetch that failed
    is the easiest way to produce one."""
    runner = scripted(EMPTY_FAILURE)
    with pytest.raises(ht.HoldoutTouchUnevaluable) as ei:
        ht.gcloud_log_read("p", "filt", 10, runner=runner,
                           sleep=lambda _s: None)
    assert len(runner.calls) == verify_iam.FETCH_ATTEMPTS
    msg = str(ei.value)
    assert "no stderr and no stdout" in msg
    assert "exit 1" in msg
    assert "seal nobody touched" in msg


def test_log_read_carries_a_stdout_slice_when_only_stderr_is_empty():
    runner = scripted(Result(7, "some diagnostic on stdout", ""))
    with pytest.raises(ht.HoldoutTouchUnevaluable) as ei:
        ht.gcloud_log_read("p", "filt", 10, runner=runner,
                           sleep=lambda _s: None)
    assert "exit 7" in str(ei.value)
    assert "some diagnostic on stdout" in str(ei.value)


def test_log_read_returns_an_empty_list_only_for_a_SUCCESSFUL_empty_result():
    """A zero exit with no output is a real empty log. That one is allowed to be
    empty, and it is the only one."""
    runner = scripted(Result(0, ""))
    assert ht.gcloud_log_read("p", "filt", 10, runner=runner,
                              sleep=lambda _s: None) == []
    assert len(runner.calls) == 1


def test_log_read_refuses_a_JSON_object_that_is_not_a_LIST_of_entries():
    runner = scripted(Result(0, '{"not": "a list"}'))
    with pytest.raises(ht.HoldoutTouchUnevaluable):
        ht.gcloud_log_read("p", "filt", 10, runner=runner,
                           sleep=lambda _s: None)
    assert len(runner.calls) == 1


def test_log_read_passes_the_filter_and_the_cap_through_to_the_command():
    runner = scripted(Result(0, "[]"))
    ht.gcloud_log_read("crucible-hack-2026", "SOME FILTER", 25, runner=runner,
                       sleep=lambda _s: None)
    argv = runner.calls[0]
    assert "SOME FILTER" in argv
    assert "--limit=25" in argv
    assert "--project=crucible-hack-2026" in argv
    assert "--order=asc" in argv


def test_CALIBRATION_the_log_read_transient_case_FAILS_without_the_retry(
        monkeypatch):
    monkeypatch.setattr(verify_iam, "FETCH_ATTEMPTS", 1)
    runner = scripted(EMPTY_FAILURE, Result(0, ONE_ENTRY))
    with pytest.raises(ht.HoldoutTouchUnevaluable):
        ht.gcloud_log_read("p", "filt", 10, runner=runner,
                           sleep=lambda _s: None)
    assert len(runner.calls) == 1


# ===========================================================================
# real_gate::_run_capture - G7a, all four probe arms. NO retry before now.
#
# This is the site where retrying is genuinely dangerous, because the thing it
# is fetching IS the verdict. `is_classifiable` is the guard.
# ===========================================================================

REAL_403 = Result(
    1, "",
    "ERROR: (gcloud.storage.objects.list) [crucible-armorer@crucible-hack-2026"
    ".iam.gserviceaccount.com] does not have permission to access b instance "
    "[crucible-sealed-x7]: Permission 'storage.objects.list' denied")
IMPERSONATION_REFUSAL = Result(
    1, "", "ERROR: Failed to impersonate: Permission "
           "'iam.serviceAccounts.getAccessToken' denied")


def test_a_REAL_403_is_returned_on_the_first_attempt_and_is_NEVER_retried():
    """THE BACKWARDS-WIRING CONTROL. If the retry were wired to ask again on any
    non-zero exit, a deny arm would fire three impersonated gcloud calls per
    probe and get the same answer three times. Retrying a semantic answer costs
    time and buys nothing - the same reason `_promote_with_assertion` refuses to
    retry E_WRONG_PROMOTER. This test fails if that guard is removed."""
    runner = scripted(REAL_403)
    slept, sleep = naps()
    rc, text = rg._run_capture(["gcloud", "x"], runner=runner,  # noqa: SLF001
                               sleep=sleep)
    assert len(runner.calls) == 1
    assert slept == []
    assert rg.classify_probe("deny", rc, text)[0] == rg.PASS


def test_an_IMPERSONATION_refusal_is_returned_on_the_first_attempt():
    """Also semantic. The probe never became that identity, which is a real
    UNEVALUABLE and not a transport failure."""
    runner = scripted(IMPERSONATION_REFUSAL)
    rc, text = rg._run_capture(["gcloud", "x"], runner=runner,  # noqa: SLF001
                               sleep=lambda _s: None)
    assert len(runner.calls) == 1
    assert rg.classify_probe("deny", rc, text)[0] == rg.UNEVALUABLE


def test_a_SUCCESSFUL_read_is_returned_on_the_first_attempt():
    """A FAIL is an answer too: rc 0 on a deny arm means the boundary does not
    exist, and asking again would not make it exist."""
    runner = scripted(Result(0, "_probe/canary.txt\n"))
    rc, text = rg._run_capture(["gcloud", "x"], runner=runner,  # noqa: SLF001
                               sleep=lambda _s: None)
    assert len(runner.calls) == 1
    assert rg.classify_probe("deny", rc, text)[0] == rg.FAIL
    assert rg.classify_probe("allow", rc, text)[0] == rg.PASS


def test_an_UNCLASSIFIABLE_failure_is_retried_and_the_answer_is_returned():
    """The run-10 shape: exit non-zero, nothing on either stream. A denial
    always writes a message, so this produced no answer at all."""
    runner = scripted(EMPTY_FAILURE, Result(0, "_probe/canary.txt\n"))
    slept, sleep = naps()
    rc, text = rg._run_capture(["gcloud", "x"], runner=runner,  # noqa: SLF001
                               sleep=sleep)
    assert len(runner.calls) == 2
    assert slept == [verify_iam.FETCH_BACKOFF[0]]
    assert rg.classify_probe("allow", rc, text)[0] == rg.PASS


def test_exhausting_the_probe_retries_still_reads_UNEVALUABLE_and_names_the_code():
    """It does NOT raise: `seal_probe_findings` wants a (rc, text) it can
    classify, and UNEVALUABLE is RUN_INVALID, which is the honest outcome for a
    probe that produced nothing. What changes is that the finding now carries
    the exit code instead of the empty string run 10 reported."""
    runner = scripted(EMPTY_FAILURE)
    rc, text = rg._run_capture(["gcloud", "x"], runner=runner,  # noqa: SLF001
                               sleep=lambda _s: None)
    assert len(runner.calls) == verify_iam.FETCH_ATTEMPTS
    assert rc == 1
    assert text.strip()
    assert "exited 1" in text
    assert "%d attempts" % verify_iam.FETCH_ATTEMPTS in text
    # THE DIAGNOSTIC MUST NOT LAUNDER ITSELF INTO A CLASSIFIABLE ANSWER. It is
    # appended text, and appended text that happened to contain "403" would
    # score a dead probe as a boundary that held.
    for expect in ("deny", "allow"):
        assert rg.classify_probe(expect, rc, text)[0] == rg.UNEVALUABLE
    assert not rg.is_classifiable(rc, text)


def test_the_diagnostic_reaches_the_G7a_FINDING_and_not_just_the_return_value():
    """End to end through `seal_probe_findings`, which is what the gate calls."""
    # A synthetic env, not the sourced one: this test is about what the finding
    # SAYS when the probe produces nothing, and it must not need a live project
    # or a gcloud on PATH to say it. The "names are sourced, never retyped"
    # assertion has its own test at tests/test_real_gate.py.
    fake_env = {"CRUCIBLE_SEALED_BUCKET": "gs://b", "CRUCIBLE_PROJECT": "p",
                "SA_SEALED_EVAL": "e", "SA_ARMORER": "a", "SA_RED": "r",
                "SA_CORONER": "c"}
    runner = scripted(EMPTY_FAILURE)

    def run(argv):
        return rg._run_capture(argv, runner=runner,          # noqa: SLF001
                               sleep=lambda _s: None)

    findings = rg.seal_probe_findings(fake_env, run=run)
    assert len(findings) == 4
    assert all(f["status"] == rg.UNEVALUABLE for f in findings)
    assert any("exited 1" in f["detail"] for f in findings)


def test_CALIBRATION_the_probe_transient_case_FAILS_without_the_retry(
        monkeypatch):
    """With one attempt allowed, the fail-then-succeed script must come back
    unclassifiable instead of PASS."""
    monkeypatch.setattr(verify_iam, "FETCH_ATTEMPTS", 1)
    runner = scripted(EMPTY_FAILURE, Result(0, "_probe/canary.txt\n"))
    rc, text = rg._run_capture(["gcloud", "x"], runner=runner,  # noqa: SLF001
                               sleep=lambda _s: None)
    assert len(runner.calls) == 1
    assert rg.classify_probe("allow", rc, text)[0] == rg.UNEVALUABLE
