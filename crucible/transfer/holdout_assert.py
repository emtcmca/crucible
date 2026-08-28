"""holdout_assert.py - the seal assertions the transfer run makes for itself.

TWO DEFECTS THIS MODULE EXISTS TO CLOSE, BOTH FOUND BY ADVERSARIAL REVIEW ON
2026-08-28 AND NEITHER VISIBLE FROM INSIDE THE CODE THAT HAS THEM
-----------------------------------------------------------------------------

**ONE. G7 AND G8 ONLY RUN WHEN A PATCH CANDIDATE EXISTS.** `RealGate.preflight()`
holds every G7 and G8 assertion, but its only production call site is inside
`RealGate.__call__(candidate, record)`, which raises `GateHalt` at the top when
`candidate is None`. `contracts/gate_rule.v1.yaml:166` says G7 is evaluated
`at_round_start`. It is not. It is evaluated when something asks to be promoted.

The transfer phase **forbids the Armorer and produces no candidate at all**
(`f4-unseal-preregistration-2026-08-25.md` section 3 step 2, section 4 item 6).
So a transfer run reusing the ordinary gate path would execute the seal
integrity check **zero times, during the one run whose entire subject is the
seal.** That is this repository's recurring defect - a check that cannot fail
because it never runs - in its seventh costume and its worst location.

So this module calls `preflight()` DIRECTLY, twice, with no candidate anywhere.
`scripts/probe-g7-g8.py:112` already does this, so the entry point is public and
exercised; nothing in `real_gate.py` needs to change.

**TWO. G7c COMPARES AN INTEGER AND THROWS AWAY THE ANSWER IT ALREADY HAS.**
`HoldoutTouchCounter.compute()` returns `count`, `distinct_reads` AND
`distinct_objects`. `__call__` returns only `['count']`, and G7c compares that
one integer for exact equality. So `count == 24` is satisfied by:

    the same object read 24 times
    23 sealed objects plus one canary
    one object missed and one unrelated permitted read making up the difference

An unauthorised principal still invalidates correctly. But **the integer alone
cannot tell you that the twenty four objects you meant to read are the twenty
four that were read**, and for a one-shot experiment that is not good enough.

So the assertions here are made on the STRUCTURED result, not the integer:
count, distinct_reads, the exact resource set, intruders, and the recomputed
fingerprint. G7c still runs and still gates. This is a belt beside it, and the
belt is the one that knows which objects.

WHY CALIBRATION IS A FUNCTION HERE AND NOT A NUMBER IN A DOCUMENT
-----------------------------------------------------------------------------
The expected count depends on how many audit entries ONE read emits through the
client the runner actually uses. Measured through `gcloud storage cp` it is one
per object. The runner uses the Python client, which is a different path, and
`Blob.download_as_bytes` has a retry policy enabled by default. So the number is
measured, against the canary, through the same callable the run will use, before
any sealed object is touched. `f4-unseal-preregistration-2026-08-25.md` A3.2
fixes this as the method and A3.1 records why.
"""

from __future__ import annotations


class HoldoutAssertionError(RuntimeError):
    """A seal assertion failed. Raised, never returned, and never downgraded to
    a warning: every condition below is one the pre-registration treats as
    voiding the run."""


def preflight_no_candidate(gate):
    """Run G7 and G8 with NO candidate in existence.

    Returns the findings list. The caller decides what to do with it; this
    function's whole job is that the assertions EXECUTE, which is the thing the
    ordinary path does not guarantee.
    """
    findings = gate.preflight()
    if not findings:
        raise HoldoutAssertionError(
            "preflight() returned no findings at all. An empty findings list "
            "is not a pass, it is a check that did not run, and this module "
            "exists because that distinction was already missed once.")
    return findings


def summarise_findings(findings):
    """`(ok, failures, unevaluable)` from a findings list, by status."""
    fails, uneval = [], []
    for f in findings:
        status = getattr(f, "status", None) or (
            f.get("status") if isinstance(f, dict) else None)
        name = getattr(f, "gate", None) or (
            f.get("gate") if isinstance(f, dict) else "?")
        if status == "FAIL":
            fails.append(name)
        elif status == "UNEVALUABLE":
            uneval.append(name)
    return (not fails and not uneval), fails, uneval


def assert_clean_before_read(counter):
    """Before ANY sealed object is read, the run window must be empty and the
    trail must be clean.

    A run that starts with reads already inside its own window cannot later
    attribute its count to itself, and an intruder present before the run
    started is a seal breach that predates the experiment.
    """
    r = counter.compute()
    if r["intruders"]:
        raise HoldoutAssertionError(
            "%d intruder read(s) on the sealed bucket before this run began. "
            "Outcome D applies: the seal is reported broken, with when and by "
            "whom, and no transfer claim of any kind is made."
            % len(r["intruders"]))
    if r["count"]:
        raise HoldoutAssertionError(
            "%d content read(s) already inside this run's G7c window before "
            "the run read anything. The window must open on an empty count or "
            "the expected value cannot be attributed to this run's own reads."
            % r["count"])
    return r


def assert_read_exactly(counter, expected_names, bucket, per_object=1):
    """After the single corpus load and the log settle interval.

    `per_object` is the CALIBRATED entries-per-read for the runner's own client
    path, not an assumption. Every condition below is asserted separately so a
    failure names which one broke rather than reporting a wrong integer.
    """
    r = counter.compute()
    expected_count = len(expected_names) * per_object
    want = {"projects/_/buckets/%s/objects/families/%s"
            % (bucket.rstrip("/").replace("gs://", ""), n)
            for n in expected_names}

    if r["intruders"]:
        raise HoldoutAssertionError(
            "%d intruder read(s) during the transfer read. Outcome D."
            % len(r["intruders"]))

    if r["count"] != expected_count:
        raise HoldoutAssertionError(
            "content read count is %d, expected %d (%d objects x %d calibrated "
            "entries per read). G7c would compare the same integer and this "
            "names the discrepancy before the run spends anything further."
            % (r["count"], expected_count, len(expected_names), per_object))

    got = set(r["distinct_objects"])
    if got != want:
        missing = sorted(want - got)
        extra = sorted(got - want)
        raise HoldoutAssertionError(
            "the object SET read is not the set intended, which is the "
            "condition G7c's integer cannot see. missing=%d %s extra=%d %s"
            % (len(missing), missing[:3], len(extra), extra[:3]))

    if r["distinct_reads"] != len(expected_names):
        raise HoldoutAssertionError(
            "distinct_reads is %d against %d objects. The count and the set "
            "can both be right while an object was read twice and another "
            "not at all."
            % (r["distinct_reads"], len(expected_names)))
    return r


def calibrate_on_canary(counter, downloader, canary_uri, settle):
    """Measure entries-per-read for THIS downloader, on the canary, before any
    sealed object is touched.

    Returns the integer. Raises if it is not a positive whole number, because a
    fractional or zero calibration means the filter did not classify the
    runner's reads as content reads at all - in which case an expected value of
    zero would PASS G7c while measuring nothing, which is the exact failure this
    whole module is built around.
    """
    before = counter.compute()["count"]
    downloader(canary_uri)
    settle()
    after = counter.compute()["count"]
    delta = after - before
    if delta <= 0:
        raise HoldoutAssertionError(
            "calibration read produced %d counted entries. The runner's read "
            "path is not being classified as a content read, so an expected "
            "count derived from it would be meaningless and an expected count "
            "of zero would pass G7c while measuring nothing." % delta)
    return delta
