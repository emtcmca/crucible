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

THREE MORE, FOUND 2026-08-29 WHILE MAKING THE ABOVE CALLABLE
-----------------------------------------------------------------------------

**THREE. THE FIRST VERSION OF THIS FILE WAS NEVER CALLED FROM ANYWHERE.** Four
carefully written helpers, zero call sites. A helper nobody calls is a check
that cannot fail wearing the most convincing costume available - it reads as
work already done. The library shape below (a named function per step, in the
order the runner performs them, every collaborator injected) exists so the
runner can consume it without inventing the sequence, and so the sequence itself
is testable offline.

**FOUR. TWO INTRUDER BRANCHES IN THIS FILE COULD NOT EXECUTE.**
`assert_clean_before_read` and `assert_read_exactly` both did
`r = counter.compute()` and then tested `if r["intruders"]`. But `compute()`
RAISES `HoldoutTouchInvalid` on any intruder before it returns, so neither `if`
could ever be true - and the message the operator would have seen was the
counter's, not Outcome D's. Both now catch the exception, which is the reachable
path, and both keep the `if` for the case that made it reachable in the first
place: `counter` is INJECTED, and a double or a future counter that reports
intruders in its tally without raising must not slip past.

**FIVE. THE CALIBRATION AND THE RUN CANNOT SHARE A WINDOW.** The canary read is
a granted content read like any other, so it lands inside any G7c window open at
the time. If that is the run's own window, then the run's expected count is short
by exactly the calibration's entries and its object set carries a canary that was
never part of the corpus. So calibration runs against its OWN window and the run
window is opened afterwards, strictly later - `open_run_window` refuses to return
one that is not, and `assert_clean_before_read` catches a leak the clock did not.

WHY CALIBRATION IS A FUNCTION HERE AND NOT A NUMBER IN A DOCUMENT
-----------------------------------------------------------------------------
The expected count depends on how many audit entries ONE read emits through the
client the runner actually uses. Measured through `gcloud storage cp` it is one
per object. The runner uses the Python client, which is a different path, and
`Blob.download_as_bytes` has a retry policy enabled by default. So the number is
measured, against the canary, through the same callable the run will use, before
any sealed object is touched. `f4-unseal-preregistration-2026-08-25.md` A3.2
fixes this as the method and A3.1 records why.

**"THE SAME CALLABLE" IS ENFORCED, NOT REQUESTED.** A comment asking the caller
to reuse the calibrated downloader is worth nothing on a one-shot run.
`calibrate_on_canary` takes the downloader and RETURNS IT, wrapped in a
`CalibratedDownloader` that is itself the callable to pass onward. That wrapper
records every uri it is asked for, so `assert_read_exactly` can compare what the
client asked for against what the audit log recorded - two independent witnesses
to the same read set, one of which is not ours. A read performed through some
other callable leaves the wrapper's list empty and is refused by name.
"""

from __future__ import annotations

import time

from infra.holdout_touch import (DEFAULT_SETTLE_SECONDS, HoldoutTouchInvalid,
                                 HoldoutTouchUnevaluable, make_counter,
                                 now_utc, open_audit_window)


class HoldoutAssertionError(RuntimeError):
    """A seal assertion failed. Raised, never returned, and never downgraded to
    a warning: every condition below is one the pre-registration treats as
    voiding the run."""


# ===========================================================================
# Step 0 vocabulary. Object names -> the two spellings of the same read.
# ===========================================================================

def _bare_bucket(bucket):
    """`gs://crucible-sealed-x7/` -> `crucible-sealed-x7`."""
    return bucket.replace("gs://", "").rstrip("/")


def sealed_object_uri(bucket, name):
    """What the DOWNLOADER is asked for. Mirrors `sealed_io.read_sealed_once`,
    which builds `"%s/families/%s" % (bucket.rstrip('/'), name)`."""
    return "%s/families/%s" % (bucket.rstrip("/"), name)


def sealed_object_resource(bucket, name):
    """What the AUDIT LOG records. Measured shape, from the live fixture in
    `tests/test_holdout_touch.py`: `projects/_/buckets/<bucket>/objects/<path>`.

    Two spellings of one read, and keeping both is the point - the uri is what
    this process asked for and the resource is what Google recorded. An
    assertion that only ever compares one of them against itself is comparing a
    number to its own source.
    """
    return "projects/_/buckets/%s/objects/families/%s" % (_bare_bucket(bucket),
                                                          name)


# ===========================================================================
# Step: the settle interval. A parameter with a default, not a magic sleep.
# ===========================================================================

def wait_for_log_settlement(seconds=DEFAULT_SETTLE_SECONDS, sleep=None):
    """Block for `seconds` so Cloud Logging ingestion can catch up. Returns it.

    THE DEFAULT IS `infra.holdout_touch.DEFAULT_SETTLE_SECONDS` (45.0), sourced
    rather than retyped, and it is the value `campaign.py` and
    `scripts/probe-g7-g8.py` already use. It is a default and not a guarantee:
    no test can establish that any delay is long enough, and the measured
    observation behind it is only that every entry seen on 2026-08-22 was
    visible within about thirty seconds.

    ZERO IS REFUSED. Ingestion lag makes a just-performed read invisible, and a
    missed read is an UNDERCOUNT - the single error direction that reads as a
    pass. On a run that opens the seal once, "I did not wait" and "nothing was
    read" must not produce the same number. Tests inject `sleep` and keep the
    real interval; they do not pass zero.
    """
    if seconds is None or seconds <= 0:
        raise HoldoutAssertionError(
            "a settle interval of %r was requested. Cloud Logging ingestion "
            "lags the event, so counting immediately UNDERCOUNTS, and an "
            "undercount is the error direction that looks like a pass. Pass a "
            "positive interval; inject `sleep` if the wait is what you are "
            "trying to avoid." % (seconds,))
    (sleep or time.sleep)(seconds)
    return seconds


# ===========================================================================
# Step: calibration, and the callable it hands back.
# ===========================================================================

class CalibratedDownloader:
    """The ONE callable. Calibrated on the canary, then used on the holdout.

    It is a transparent pass-through - `__call__` forwards to the downloader it
    wraps and returns its bytes unchanged - so it is a witness rather than a
    behaviour change. What it adds is a record: `uris`, every object this
    process asked for, in order. That list is the client-side half of the
    read-set assertion, and it is the half that does not come from Google.

    Constructed only by `calibrate_on_canary`. An instance whose `per_object` is
    still None was never calibrated, and every assertion below refuses it.
    """

    def __init__(self, downloader, canary_uri):
        if isinstance(downloader, CalibratedDownloader):
            raise HoldoutAssertionError(
                "refusing to calibrate an already-calibrated downloader. Two "
                "calibrations of one callable produce two entries-per-read "
                "figures for one read path, and the second measurement would "
                "silently include the first calibration's own canary read.")
        self._downloader = downloader
        self.canary_uri = canary_uri
        self.uris = []
        self.per_object = None
        self.baseline_count = None
        self.calibration_since = None
        self.finished_at = None
        self._at_calibration = None

    # -- the callable ---------------------------------------------------

    def __call__(self, uri):
        self.uris.append(uri)
        return self._downloader(uri)

    # -- what it witnessed ----------------------------------------------

    @property
    def reads(self):
        """Every invocation, calibration included."""
        return len(self.uris)

    @property
    def sealed_uris(self):
        """Invocations AFTER calibration finished - the run's own reads.

        Sliced rather than counted from zero, so the canary read that produced
        the calibration cannot be mistaken for one of the twenty four.
        """
        if self._at_calibration is None:
            return []
        return self.uris[self._at_calibration:]

    @property
    def calibrated(self):
        return self.per_object is not None

    def _complete(self, per_object, baseline_count, calibration_since,
                  finished_at):
        self.per_object = per_object
        self.baseline_count = baseline_count
        self.calibration_since = calibration_since
        self.finished_at = finished_at
        self._at_calibration = len(self.uris)

    def describe(self):
        """The calibration, as a dict, for the transfer bundle."""
        return {
            "entries_per_read": self.per_object,
            "canary_uri": self.canary_uri,
            "calibration_window_since": self.calibration_since,
            "calibration_finished_at": self.finished_at,
            "baseline_count_in_calibration_window": self.baseline_count,
            "reads_through_this_callable": self.reads,
            "sealed_reads_through_this_callable": len(self.sealed_uris),
        }


def require_calibrated(downloader):
    """Return `downloader` if it is a completed calibration; raise otherwise.

    The guard for any code path that is about to touch the holdout. It refuses a
    bare callable, a half-built wrapper, and anything else handed to it, so
    "reuse the calibrated downloader" stops being an instruction in a comment
    and becomes a condition that fails loudly at the door.
    """
    if not isinstance(downloader, CalibratedDownloader):
        raise HoldoutAssertionError(
            "the sealed read was handed a %s, not the CalibratedDownloader that "
            "`calibrate_on_canary` returned. The entries-per-read figure the "
            "expected count is built from was measured through a DIFFERENT "
            "callable, so it describes a read path this run does not perform."
            % type(downloader).__name__)
    if not downloader.calibrated:
        raise HoldoutAssertionError(
            "the downloader was wrapped but never calibrated: `per_object` is "
            "still unset. An uncalibrated wrapper is a bare downloader with "
            "better manners.")
    return downloader


def _count_now(counter, phase):
    """`counter.compute()['count']`, with the intruder exception named.

    `compute()` RAISES `HoldoutTouchInvalid` rather than returning a tally with
    intruders in it. Letting that propagate raw would report the counter's
    message during a phase the pre-registration has its own name for.
    """
    try:
        return counter.compute()["count"]
    except HoldoutTouchInvalid as exc:
        raise HoldoutAssertionError(
            "an unattested read of the sealed holdout was recorded during %s. "
            "Outcome D applies: the seal is reported broken, with when and by "
            "whom, and no transfer claim of any kind is made. %s"
            % (phase, exc)) from None


def calibrate_on_canary(counter, downloader, canary_uri, settle=None,
                        clock=None):
    """Measure entries-per-read for THIS downloader, on the canary, before any
    sealed object is touched. Returns the downloader, wrapped and calibrated.

    `counter` MUST be a counter over the CALIBRATION's own window, never the
    run's. The canary read is a granted content read and lands in whatever G7c
    window is open; inside the run's window it would make the run's expected
    count short by exactly these entries and put a canary in the object set.
    Open the run window afterwards, with `open_run_window(calibration)`, which
    refuses a window that is not strictly later.

    `settle` is a zero-arg callable; the default is `wait_for_log_settlement`
    with its documented interval. Counting before ingestion catches up measures
    zero entries per read, which is refused below - so a missing settle shows up
    as a loud calibration failure rather than as a quiet expected value of zero.

    RAISES if the delta is not a positive whole number, because a fractional or
    zero calibration means the runner's reads are not being classified as
    content reads at all - in which case an expected value of zero would PASS
    G7c while measuring nothing, which is the exact failure this whole module is
    built around.
    """
    wrapped = CalibratedDownloader(downloader, canary_uri)
    settle = settle or (lambda: wait_for_log_settlement())

    before = _count_now(counter, "the calibration baseline")
    wrapped(canary_uri)
    settle()
    after = _count_now(counter, "the calibration read")

    delta = after - before
    if delta <= 0:
        raise HoldoutAssertionError(
            "calibration read produced %d counted entries (%d -> %d in window "
            "%s). The runner's read path is not being classified as a content "
            "read, so an expected count derived from it would be meaningless "
            "and an expected count of zero would pass G7c while measuring "
            "nothing." % (delta, before, after, getattr(counter, "since", "?")))

    wrapped._complete(per_object=delta, baseline_count=before,   # noqa: SLF001
                      calibration_since=getattr(counter, "since", None),
                      finished_at=now_utc(clock))
    return wrapped


# ===========================================================================
# Step: the run's own window, and the counter over it.
# ===========================================================================

def open_run_window(calibration=None, clock=None):
    """Open the run's G7c window. Returns the `since` instant.

    `calibration` is the object `calibrate_on_canary` returned. Its
    `finished_at` is the boundary the run window must start strictly after, and
    `open_audit_window` refuses anything that does not - the calibration's
    entries must fall OUTSIDE the window whose count this run will claim as its
    own.

    Passing nothing is permitted and is the shape a run with no calibration
    phase uses; it still refuses a window before the attestation floor.
    """
    after = None
    if calibration is not None:
        after = require_calibrated(calibration).finished_at
    return open_audit_window(clock=clock, after=after)


def open_run_window_when_clear(calibration=None, clock=None, sleep=None,
                               max_wait_seconds=120, poll_seconds=0.25,
                               announce=None):
    """`open_run_window`, but wait for the boundary instead of dying on it.

    THE DEFECT THIS FIXES. `calibrate_on_canary` stamps `finished_at` truncated
    to a whole second, and `sealed_drive_lifecycle` opened the run window on the
    next line. `open_audit_window` demands STRICTLY after, so the normal case -
    two adjacent statements inside one second - raised
    `HoldoutTouchUnevaluable` and stopped the run. Whether the sealed drive
    proceeded depended on coincidentally crossing a wall-clock second between
    two adjacent calls. That is a coin flip on a run that happens once.

    THE STRICT GUARD IS CORRECT AND IS NOT RELAXED. Equality means the two
    windows share a whole second, and an event inside that second belongs to
    both - so the calibration's own canary read could be counted as a holdout
    touch, and the run's expected count would be short by exactly that. What
    was missing is the wait that the guard's own error text prescribes: "Wait
    for the clock to pass %s and open again."

    WHY IT REFUSES ON TIMEOUT RATHER THAN OPENING ANYWAY. Proceeding would mean
    opening a window that overlaps the calibration, which is the attribution
    failure the guard exists to prevent. A clock that will not advance is a
    broken instrument, and a broken instrument is a reason to stop rather than
    a reason to guess. This costs nothing at the moment it fires: no sealed
    object has been read yet.

    `clock` and `sleep` are injected so the whole wait runs offline in tests.
    """
    sleep = sleep or time.sleep
    waited = 0.0
    last = None
    # ONE BOUND, and there was briefly a second one that had to come back out.
    #
    # `waited` advances by `poll_seconds` on every pass, arithmetically, with
    # no reference to any clock. So the elapsed check below ALWAYS fires after
    # exactly `max_wait_seconds / poll_seconds` passes, and a belt-and-braces
    # iteration cap beside it could never be reached. An unreachable guard is
    # a check that cannot fail, which is the defect this repository exists to
    # catch, and shipping one inside the wait would have been that defect in
    # the file written to fix another one.
    #
    # It was added because a mutation run hung instead of going red. That hang
    # was real and had a different cause: an EARLIER mutation had been left in
    # the file by a run that timed out, so the elapsed check was already
    # disabled when the second mutation removed its replacement. The lesson is
    # about verifying a revert, not about needing two bounds.
    while True:
        try:
            return open_run_window(calibration, clock=clock)
        except HoldoutTouchUnevaluable as exc:
            # ONLY THE BOUNDARY CASE IS WAITED OUT. A window below the
            # attestation floor is not something the clock will fix by
            # advancing a second, and retrying it would spin for two minutes
            # before reporting a problem that was decidable immediately.
            if "strictly after" not in str(exc):
                raise
            last = exc
            if waited >= max_wait_seconds:
                raise HoldoutTouchUnevaluable(
                    "waited %.1fs for the audit-log clock to pass the "
                    "calibration boundary and it never did. The last refusal "
                    "was: %s. A clock that does not advance is a broken "
                    "instrument, and no sealed object has been read yet."
                    % (waited, last))
            if announce and waited == 0.0:
                announce("  waiting for the run window to clear the "
                         "calibration boundary")
            sleep(poll_seconds)
            waited += poll_seconds


def make_run_counter(env, since, **kwargs):
    """The zero-arg callable for this run's window. `RealGate(holdout_touch=)`.

    A one-line re-export of `infra.holdout_touch.make_counter`, so the runner
    imports its whole holdout vocabulary from one module and the counter the
    assertions read is provably the counter the gate reads.
    """
    return make_counter(env, since, **kwargs)


# ===========================================================================
# Step: the preflights.
# ===========================================================================

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


def assert_preflight_clean(findings, label="preflight"):
    """Raise unless every finding passed. Returns the findings.

    THE STEP THAT WAS MISSING AND IS THE WHOLE POINT OF RUNNING THE PREFLIGHT.
    `preflight()` only RETURNS findings - it does not raise, and it does not
    append to `gate.reports` (`f4-unseal-preregistration-2026-08-25.md` A3.8.5
    says so in as many words). A runner that records the two lists and never
    reads them has executed the gate and ignored it, which scores the same as
    not running it and looks better in the bundle.

    UNEVALUABLE IS TREATED AS FAILURE, not as a shrug. `gate_rule.v1.yaml` gives
    G7 `absent_or_unevaluable: RUN_INVALID`, and the run this exists for is the
    one that cannot be repeated.
    """
    ok, fails, uneval = summarise_findings(findings)
    if not ok:
        raise HoldoutAssertionError(
            "%s: %d finding(s) FAILED (%s) and %d were UNEVALUABLE (%s) across "
            "%d finding(s). G7's absent_or_unevaluable outcome is RUN INVALID, "
            "so an unevaluable seal assertion is not a smaller result than a "
            "failed one." % (label, len(fails), ", ".join(fails) or "-",
                             len(uneval), ", ".join(uneval) or "-",
                             len(findings)))
    return findings


# ===========================================================================
# Step: the assertions on the count itself.
# ===========================================================================

def assert_clean_before_read(counter):
    """Before ANY sealed object is read, the run window must be empty and the
    trail must be clean.

    A run that starts with reads already inside its own window cannot later
    attribute its count to itself, and an intruder present before the run
    started is a seal breach that predates the experiment.

    THIS IS ALSO THE CALIBRATION-LEAK CONTROL. If the run window was opened too
    early and still contains the canary read, the count is non-zero here and the
    run stops before it has spent anything. That is why the clock check in
    `open_run_window` is not the only guard: a clock is a claim about when
    something happened, and this is a measurement of what the log holds.
    """
    try:
        r = counter.compute()
    except HoldoutTouchInvalid as exc:
        # THE REACHABLE PATH. `compute()` raises on intruders rather than
        # returning them, so the `if` below cannot fire against the real
        # counter - it fired against nothing for as long as it was the only
        # check here.
        raise HoldoutAssertionError(
            "an unattested read of the sealed bucket was recorded before this "
            "run began. Outcome D applies: the seal is reported broken, with "
            "when and by whom, and no transfer claim of any kind is made. %s"
            % exc) from None
    if r.get("intruders"):
        # KEPT, AND REACHABLE FOR ONE REASON: `counter` is injected. A double,
        # or any future counter that reports intruders in its tally instead of
        # raising, must not walk past this function.
        raise HoldoutAssertionError(
            "%d intruder read(s) on the sealed bucket before this run began. "
            "Outcome D applies: the seal is reported broken, with when and by "
            "whom, and no transfer claim of any kind is made."
            % len(r["intruders"]))
    if r["count"]:
        raise HoldoutAssertionError(
            "%d content read(s) already inside this run's G7c window (since %s) "
            "before the run read anything. The window must open on an empty "
            "count or the expected value cannot be attributed to this run's own "
            "reads. A calibration read that leaked into the run window looks "
            "exactly like this. Objects: %s"
            % (r["count"], r.get("since"), r.get("distinct_objects")))
    return r


def expected_content_read_count(expected_names, calibration, passes=1):
    """`entries_per_read x objects x passes`, per A3.2.

    `passes` DEFAULTS TO 1 AND THAT IS NOT THE SAME NUMBER A3.2 USES. A3.2
    writes the formula as `reads_per_object x 24 x passes` with two evaluation
    passes, but `sealed_io.read_sealed_once` loads the corpus ONCE and both arms
    are driven from the parsed instances in memory - it refuses a second read of
    the same object by name. So the count of AUDIT ENTRIES is over one load,
    while the count of EVALUATION PASSES is two. They are different units and
    this module will not silently pick one; the caller passes the number of
    times the holdout is actually read.
    """
    cal = require_calibrated(calibration)
    if passes < 1:
        raise HoldoutAssertionError(
            "passes=%r. A holdout read zero times produces an expected count of "
            "zero, and an expected count of zero passes G7c against a log "
            "nobody queried." % (passes,))
    return len(expected_names) * cal.per_object * passes


def assert_read_exactly(counter, expected_names, bucket, calibration,
                        passes=1):
    """After the single corpus load and the log settle interval.

    `calibration` is the `CalibratedDownloader` the read went through. Every
    condition below is asserted separately so a failure names which one broke
    rather than reporting a wrong integer, and they are asserted against TWO
    independent witnesses:

      CLIENT SIDE  `calibration.sealed_uris` - what this process asked for.
      LOG SIDE     `count`, `distinct_reads`, `distinct_objects` - what Google
                   recorded.

    Agreement between them is the assertion. The client-side half is what
    catches a read performed through some other callable: the wrapper's list is
    then empty while the log's is full, and the calibrated entries-per-read
    figure describes a path this run did not take.
    """
    cal = require_calibrated(calibration)
    expected_names = list(expected_names)
    expected_count = expected_content_read_count(expected_names, cal, passes)

    want_uris = [sealed_object_uri(bucket, n) for n in expected_names]
    want_res = {sealed_object_resource(bucket, n) for n in expected_names}

    # ---- witness one: the client ------------------------------------
    got_uris = list(cal.sealed_uris)
    if not got_uris:
        raise HoldoutAssertionError(
            "the calibrated downloader was never invoked after calibration, so "
            "the sealed read did not go through it. The entries-per-read figure "
            "behind the expected count of %d was measured on a callable this "
            "run did not use, and nothing here describes the read that "
            "happened." % expected_count)
    # DUPLICATES FIRST, then the set. Reversed, a repeated read reports as a
    # set mismatch with `missing=0 extra=0` - technically true and useless,
    # which is the failure text a one-shot run cannot afford to be handed.
    if len(set(got_uris)) != len(got_uris):
        dupes = sorted({u for u in got_uris if got_uris.count(u) > 1})
        raise HoldoutAssertionError(
            "the calibrated downloader was asked for %d object(s) more than "
            "once: %s. A duplicate read makes G7c's integer right for the wrong "
            "reason." % (len(dupes), dupes[:3]))
    if set(got_uris) != set(want_uris):
        missing = sorted(set(want_uris) - set(got_uris))
        extra = sorted(set(got_uris) - set(want_uris))
        raise HoldoutAssertionError(
            "the calibrated downloader was asked for a different set than the "
            "run declared. asked=%d declared=%d missing=%d %s extra=%d %s"
            % (len(got_uris), len(want_uris), len(missing), missing[:3],
               len(extra), extra[:3]))

    # ---- witness two: the audit log ---------------------------------
    try:
        r = counter.compute()
    except HoldoutTouchInvalid as exc:
        raise HoldoutAssertionError(
            "an unattested read of the sealed holdout was recorded during the "
            "transfer read. Outcome D applies. %s" % exc) from None
    if r.get("intruders"):
        # Same reason the twin in `assert_clean_before_read` is kept.
        raise HoldoutAssertionError(
            "%d intruder read(s) during the transfer read. Outcome D."
            % len(r["intruders"]))

    if r["count"] != expected_count:
        raise HoldoutAssertionError(
            "content read count is %d, expected %d (%d objects x %d calibrated "
            "entries per read x %d pass(es)). G7c would compare the same "
            "integer and this names the discrepancy before the run spends "
            "anything further."
            % (r["count"], expected_count, len(expected_names), cal.per_object,
               passes))

    got_res = set(r["distinct_objects"])
    if got_res != want_res:
        missing = sorted(want_res - got_res)
        extra = sorted(got_res - want_res)
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


__all__ = [
    "CalibratedDownloader", "DEFAULT_SETTLE_SECONDS", "HoldoutAssertionError",
    "assert_clean_before_read", "assert_preflight_clean", "assert_read_exactly",
    "calibrate_on_canary", "expected_content_read_count", "make_run_counter",
    "open_run_window", "preflight_no_candidate", "require_calibrated",
    "sealed_object_resource", "sealed_object_uri", "summarise_findings",
    "wait_for_log_settlement",
]
