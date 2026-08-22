#!/usr/bin/env python3
"""holdout_touch.py - G7(c). The number that did not exist until this file.

`contracts/gate_rule.v1.yaml` G7c is one line:

    check: holdout_touch_count == expected_for_this_phase

and `measurement-spec.md`:946 says where the number comes from: "The F4
collection's Cloud Audit Logs data-access reads are exported and counted ...
Expected value 2. Any read from another SA, or any count above 2, marks the run
INVALID."

G7's failure mode is REJECT but its `absent_or_unevaluable` is **RUN INVALID**,
so for as long as nothing computed this number, no scored run was possible.
Two separate things had to be true and only the first was done first:

  1. Data Access audit logging had to be ENABLED. It now is - the project IAM
     policy carries an `auditConfigs` entry for `storage.googleapis.com` with
     `logType: DATA_READ`, applied 2026-08-22. Verify with
     `gcloud projects get-iam-policy crucible-hack-2026 --format=json`.
  2. Something had to READ it. Nothing did. `scripts/probe-g7-g8.py` passed
     `holdout_touch=None`, hardcoded, so enabling the log was necessary and not
     sufficient. That is this module.

THE FAILURE THIS MODULE IS MOST LIKELY TO COMMIT, AND WHAT STOPS IT
------------------------------------------------------------------
**A counter that always returns 0 is indistinguishable from a seal nobody
touched, and it scores G7c PASS while measuring nothing.** Every way this
query can quietly return zero is a way to fabricate a clean seal:

    a misspelled bucket name          -> filter matches nothing -> 0
    audit logging silently disabled   -> log is empty           -> 0
    the wrong logName                 -> filter matches nothing -> 0
    a window before the log existed   -> nothing to match       -> 0
    a result truncated at --limit     -> an UNDERcount, not 0

So this counter never returns a bare number it has not first proved it could
have seen. Before any count is returned:

  * `since` must be at or after `ATTESTATION_FLOOR_UTC` (below), or the window
    covers time the log cannot speak to and the answer is UNEVALUABLE.
  * the project policy must still carry the storage `DATA_READ` auditConfig.
    A binding removed after this file was written is invisible to a check that
    ran earlier - the same reason `verify_iam.py` re-asserts every run.
  * **the canary query must return at least one entry** over the whole
    attestable window. That is the positive control, and it is what makes a
    zero in the *run* window mean "nobody touched the seal" instead of "this
    query has never seen anything." One real read is recorded in the log
    permanently (2026-08-22T19:31:19Z, `crucible-sealed-eval` reading
    `families/_probe/canary.txt`), so this control holds from now on without
    anyone having to re-touch the holdout.
  * a result at the cap is a truncation, and a truncated count is UNEVALUABLE
    rather than "at least N". G7 does not have an "at least" outcome.

None of those return 0. They all raise.

WHAT THE LOG ACTUALLY CONTAINS - MEASURED, NOT ASSUMED
------------------------------------------------------------------
Run against the live project 2026-08-22, with DATA_READ enabled:

  * **Object LISTING and object CONTENT READ both emit `DATA_READ` entries.**
    This was the open question and the answer is "both". `gcloud storage ls -r`
    on `gs://crucible-sealed-x7/families/` produced FOUR entries
    (`storage.objects.list` x3 plus one `storage.objects.get` on the PREFIX
    `.../objects/families/`); `gcloud storage cat` on one object produced TWO
    (`storage.objects.get` on the object, plus `storage.buckets.getStorageLayout`).
  * **So an entry is not a touch.** One logical read produced two to four log
    lines. Counting raw entries would make `== 2` unreachable by construction.
    `classify` below therefore counts exactly one kind - a GRANTED
    `storage.objects.get` naming a real object path - and files listings,
    bucket-metadata calls, and prefix probes separately where they can be seen
    but cannot inflate the number.
  * **Even after that narrowing, one `cat` is TWO content reads.** Measured:
    `gcloud storage cat` on `families/_probe/canary.txt` emitted two granted
    `storage.objects.get` entries on the same object, 1.08 s apart - the
    metadata fetch and the media download. So `count` and "how many times a
    human asked for that file" are still different numbers. `tally` therefore
    reports BOTH `count` (granted content-read entries, the literal reading of
    "data-access reads ... are exported and counted") and `distinct_reads`
    (distinct principal x object), and neither is silently preferred.
  * **One entry was `granted: true` AND `status.code: 5`** - a NOT_FOUND on the
    prefix `.../objects/families/`. Authorization succeeded; the read did not.
    `is_granted` keys on the status code first for exactly this shape, because
    a permission check that passed is not a byte that moved.

A SPEC CONTRADICTION THIS MODULE CANNOT RESOLVE AND WILL NOT PAPER OVER
------------------------------------------------------------------
`measurement-spec.md`:946 gives the expected value as **2**. No count derived
from this log can be 2 for a run that evaluates a 24-episode sealed holdout:
reading 24 objects produces at least 24 granted `storage.objects.get` entries
and 24 distinct objects. The **2** is plainly a count of EVALUATION PASSES - the
v0 arm and the vFinal arm - which is a grouping the audit log does not carry and
this module does not invent. Whoever owns `measurement-spec.md` must either
restate the unit or restate the expected value; `holdout_expected` is a
`RealGate` constructor argument precisely so that decision is made where the
phase is known and not smuggled in here.

The same line also calls the holdout "the F4 COLLECTION", which is Firestore
vocabulary, while G7 as rewritten 2026-08-20 says the holdout is "a GCS bucket
plus a BigQuery dataset, not a Firestore collection". This module reads GCS,
per the rewrite. The BigQuery half is NOT read here and is stated as a gap
below rather than quietly folded in.
  * **A DENIED read is logged too**, with `status.code: 7`. That is useful and
    it is NOT a touch: the bytes never moved. Denials are tallied separately.
  * The earlier `iamcredentials.googleapis.com` `GenerateAccessToken` entries
    also live in `cloudaudit.googleapis.com%2Fdata_access`. They are
    impersonation events, not bucket reads, and a filter that keys only on the
    log name counts them. Hence `serviceName` and `resource.labels.bucket_name`
    are both pinned in the filter.

WHAT THIS CANNOT ATTEST TO. STATED HERE BECAUSE IT WILL BE QUOTED.
------------------------------------------------------------------
  * **There is no history.** Data Access logging was enabled 2026-08-22 and the
    log is not retroactive. A G7a impersonation probe run at 18:27:30Z that day
    - a loggable event, since denials are logged - produced NO entry, while the
    read at 19:31:10Z did. So coverage demonstrably did not exist at 18:27:30Z
    and demonstrably did at 19:31:10Z. `ATTESTATION_FLOOR_UTC` is the later of
    those two, because it is the earliest instant coverage has been SHOWN, not
    the earliest it was plausibly configured. G7c attests from there forward and
    says nothing about the seal's earlier lifetime.
  * **The operator holds `roles/owner` and can read everything, including this
    log.** No control here defends against the trust root. What this does add is
    that an operator read of the sealed bucket now leaves a record it did not
    leave yesterday, and `permitted_principals` does not exempt the human - an
    owner read raises `HoldoutTouchInvalid` exactly like any other.
  * Cloud Logging ingestion lags the event. Every entry above was visible
    within ~30 s, but a read seconds before the gate queries can be missed, and
    a missed read is an UNDERCOUNT that looks like a pass. `settle_seconds`
    exists for that and defaults to 0 so tests are not slow; a live caller
    should set it.
  * **The BigQuery half of the holdout is not read.** `data-spec.md` places a
    sealed BigQuery dataset alongside the sealed bucket. Its data-access reads
    live under `bigquery.googleapis.com` with a different auditConfig, which is
    NOT enabled - the live policy names `storage.googleapis.com` only. So this
    counter attests to the sealed BUCKET and to nothing else, and a run that
    reads the sealed DATASET would be counted as zero touches. That gap is
    named here rather than covered by silence; closing it is a mutating change
    (a second auditConfig entry) and belongs to the coordinator.

READ-ONLY. The only command this module runs is `gcloud logging read`, plus
`gcloud projects get-iam-policy` through `verify_iam.gcloud_json`. It creates,
deletes, and binds nothing.
"""

import json
import subprocess
import time

from infra import verify_iam

# --------------------------------------------------------------------------
# The attestation floor.
# --------------------------------------------------------------------------

# The earliest instant at which storage DATA_READ coverage has been OBSERVED,
# not the earliest at which it was configured. Provenance, both halves:
#
#   2026-08-22T18:27:30Z  a G7a impersonation probe (crucible-coroner,
#                         gcloud.storage.objects.list against the sealed
#                         bucket) ran and produced NO audit entry. Denials are
#                         logged, so this is evidence of ABSENCE of coverage.
#   2026-08-22T19:31:10Z  the first storage DATA_READ entry that exists.
#
# A `since` earlier than this is a window the log cannot speak to, and the
# honest answer for such a window is UNEVALUABLE, not 0.
ATTESTATION_FLOOR_UTC = "2026-08-22T19:31:10Z"

DATA_ACCESS_LOG = "cloudaudit.googleapis.com%2Fdata_access"
STORAGE_SERVICE = "storage.googleapis.com"

# Above this, a result is assumed truncated rather than complete.
DEFAULT_CAP = 1000


class HoldoutTouchError(RuntimeError):
    """Base. Never raised directly."""


class HoldoutTouchUnevaluable(HoldoutTouchError):
    """The MECHANISM could not produce a trustworthy number.

    G7 `absent_or_unevaluable: RUN_INVALID`. This is not a statement about the
    seal; it is a statement that this counter declines to guess. It exists so
    that no path through this module can return 0 for a reason other than
    "nothing read the holdout in this window".
    """


class HoldoutTouchInvalid(HoldoutTouchError):
    """A GRANTED read of the sealed holdout by a principal outside the
    permitted set.

    `measurement-spec.md`:946 - "Any read from another SA ... marks the run
    INVALID." Both this and `HoldoutTouchUnevaluable` route to RUN INVALID, and
    they are kept as two types anyway: one says the instrument is untrustworthy,
    the other says the instrument worked and caught something. Collapsing them
    would be two spellings of one value with the interesting half thrown away.
    """


# --------------------------------------------------------------------------
# The filter. One place, because a typo here returns 0 rather than failing.
# --------------------------------------------------------------------------

def bucket_name(bucket_uri):
    """`gs://crucible-sealed-x7` -> `crucible-sealed-x7`.

    The URI form comes from `scripts/gcp-env.sh` and is never retyped here;
    `resource.labels.bucket_name` in the log carries the bare name.
    """
    return bucket_uri.replace("gs://", "").rstrip("/")


def build_filter(project, bucket_uri, since):
    """The Cloud Logging filter, assembled from sourced names only.

    Every clause is load-bearing:

      logName            the Data Access audit log specifically. ADMIN_ACTIVITY
                         is a different log and is always on; reading it would
                         count bucket configuration, not reads.
      serviceName        `cloudaudit...%2Fdata_access` ALSO carries
                         `iamcredentials.googleapis.com` GenerateAccessToken
                         entries - one per impersonation. Without this clause a
                         G7a probe run inflates the seal touch count.
      resource.type      pinned so `bucket_name` is read off the shape it
                         belongs to.
      bucket_name        EXACT match, not the `:` substring operator. A
                         substring match on a name like `crucible-sealed-x7`
                         would also match a bucket that merely contains it.
      timestamp          the window. Always explicit, because `gcloud logging
                         read` otherwise applies its own `--freshness` default
                         and the window becomes a CLI default nobody chose.
    """
    return (
        'logName="projects/%s/logs/%s"'
        ' AND protoPayload.serviceName="%s"'
        ' AND resource.type="gcs_bucket"'
        ' AND resource.labels.bucket_name="%s"'
        ' AND timestamp>="%s"'
        % (project, DATA_ACCESS_LOG, STORAGE_SERVICE,
           bucket_name(bucket_uri), since)
    )


def gcloud_log_read(project, filter_text, cap):
    """`gcloud logging read` -> list of entry dicts. READ-ONLY.

    A non-zero exit RAISES. It must never degrade to `[]`: an empty list is
    indistinguishable from a clean seal, which is the whole failure this file
    exists to refuse.
    """
    exe = verify_iam._gcloud_exe()                            # noqa: SLF001
    argv = [exe, "logging", "read", filter_text,
            "--project=%s" % project,
            "--limit=%d" % cap,
            "--order=asc",
            "--format=json"]
    p = subprocess.run(argv, capture_output=True, text=True)
    if p.returncode != 0:
        raise HoldoutTouchUnevaluable(
            "gcloud logging read exited %d: %s. A failed fetch is not an empty "
            "log; returning 0 here would report a seal nobody touched."
            % (p.returncode, (p.stderr or "").strip()[:300]))
    text = (p.stdout or "").strip()
    if not text:
        return []
    try:
        entries = json.loads(text)
    except json.JSONDecodeError as e:
        raise HoldoutTouchUnevaluable(
            "unparseable log output: %s" % e) from None
    if not isinstance(entries, list):
        raise HoldoutTouchUnevaluable(
            "expected a JSON array of log entries, got %s"
            % type(entries).__name__)
    return entries


# --------------------------------------------------------------------------
# Classification. Pure functions over one entry dict, so every branch is
# reachable offline and each is driven to red in tests/test_holdout_touch.py.
# --------------------------------------------------------------------------

CONTENT_READ = "content_read"
ENUMERATION = "enumeration"
OTHER = "other"


def is_granted(entry):
    """True when the request SUCCEEDED - authorized AND not an error.

    Two signals, and the stricter of the two wins, because THEY DISAGREE in the
    live log. Both shapes were observed 2026-08-22:

        granted: false, status.code 7   armorer denied on canary.txt
        granted: TRUE,  status.code 5   sealed-eval, NOT_FOUND on the prefix
                                        `.../objects/families/`

    The second is the one a single-signal implementation gets wrong. Reading
    only `authorizationInfo[].granted` counts it as a read of the holdout; the
    permission check passed and no byte moved. An entry with NEITHER signal is
    treated as granted - the conservative direction, since over-counting a touch
    fails G7c loudly while under-counting passes a gate that measured nothing.
    """
    p = entry.get("protoPayload") or {}
    code = (p.get("status") or {}).get("code")
    if code:
        return False
    auth = p.get("authorizationInfo") or []
    if auth and not all(a.get("granted") for a in auth):
        return False
    return True


def classify(entry):
    """One entry -> `{kind, granted, principal, method, resource}`.

    THE COUNTING RULE, and it is narrower than "a DATA_READ entry" on purpose.
    Measured live 2026-08-22: one `gcloud storage cat` emits two entries and one
    `ls -r` emits four, so "entries" and "touches" are different units and
    `holdout_touch_count == 2` is unreachable if they are conflated.

    CONTENT_READ  `storage.objects.get` naming a real object under
                  `/objects/`. THE ONLY KIND COUNTED. These are the requests in
                  which sealed bytes actually leave the bucket.
    ENUMERATION   `storage.objects.list`, any `storage.buckets.*`, and - the
                  case that would otherwise be miscounted - an
                  `storage.objects.get` whose resource ends in `/`. That is
                  gcloud asking whether a PREFIX is an object while listing, and
                  it moves no sealed content. Counting it made a bare `ls` look
                  like two reads.
    OTHER         anything else, kept visible rather than dropped, because a
                  method this module has never seen is not evidence of nothing.
    """
    p = entry.get("protoPayload") or {}
    method = p.get("method_name") or p.get("methodName") or ""
    resource = p.get("resource_name") or p.get("resourceName") or ""
    principal = ((p.get("authenticationInfo") or {}).get("principalEmail")
                 or (p.get("authentication_info") or {}).get("principalEmail")
                 or "")
    granted = is_granted(entry)

    if method == "storage.objects.get":
        if "/objects/" in resource and not resource.endswith("/"):
            kind = CONTENT_READ
        else:
            kind = ENUMERATION
    elif method == "storage.objects.list" or method.startswith("storage.buckets."):
        kind = ENUMERATION
    else:
        kind = OTHER

    return {"kind": kind, "granted": granted, "principal": principal,
            "method": method, "resource": resource,
            "timestamp": entry.get("timestamp", "")}


def tally(entries, permitted_principals):
    """Classified entries -> a structured tally. Pure.

    `count` is the number G7c compares. Everything else is there so the finding
    can say WHO and WHAT rather than only how many - "any read from another SA"
    is a statement about principals, and a bare integer cannot carry it.
    """
    rows = [classify(e) for e in entries]
    reads = [r for r in rows if r["kind"] == CONTENT_READ and r["granted"]]
    intruders = [r for r in reads if r["principal"] not in permitted_principals]
    # `distinct_reads` collapses the metadata-fetch + media-download pair that
    # one `cat` produces. Reported ALONGSIDE `count`, never instead of it: which
    # unit `holdout_touch_count` means is a measurement-spec question, and this
    # module refuses to answer it by picking one and hiding the other.
    distinct = sorted({(r["principal"], r["resource"]) for r in reads})
    return {
        "count": len(reads),
        "distinct_reads": len(distinct),
        "distinct_objects": sorted({r["resource"] for r in reads}),
        "reads": reads,
        "intruders": intruders,
        "denied": [r for r in rows if not r["granted"]],
        "enumerations": [r for r in rows
                         if r["kind"] == ENUMERATION and r["granted"]],
        "other": [r for r in rows if r["kind"] == OTHER],
        "entries": len(rows),
        "principals": sorted({r["principal"] for r in rows if r["principal"]}),
    }


# --------------------------------------------------------------------------
# The audit-config precondition.
# --------------------------------------------------------------------------

def storage_data_read_enabled(project_policy):
    """None when the policy enables storage DATA_READ; a problem string otherwise.

    Pure, over the same `gcloud projects get-iam-policy --format=json` document
    `verify_iam` already fetches. Re-asserted every call for the reason
    `verify_iam.py`'s header gives: a config REMOVED after this module was
    written is invisible to a check that ran earlier, and its symptom is a log
    that quietly stops filling - a zero that looks like a clean seal.
    """
    configs = project_policy.get("auditConfigs")
    if not configs:
        return ("the project IAM policy carries NO auditConfigs block, so "
                "Data Access logging is off and holdout_touch_count does not "
                "exist to be read")
    for cfg in configs:
        if cfg.get("service") != STORAGE_SERVICE:
            continue
        for log_cfg in cfg.get("auditLogConfigs") or []:
            if log_cfg.get("logType") == "DATA_READ":
                if log_cfg.get("exemptedMembers"):
                    return ("storage DATA_READ logging exempts %s. An exempted "
                            "principal reads the seal without leaving a record, "
                            "so the count is not a count of reads"
                            % ", ".join(log_cfg["exemptedMembers"]))
                return None
        return ("auditConfigs names %s but with no DATA_READ logType"
                % STORAGE_SERVICE)
    return ("auditConfigs exists but names no entry for %s" % STORAGE_SERVICE)


# --------------------------------------------------------------------------
# The counter.
# --------------------------------------------------------------------------

def _iso_ge(a, b):
    """Compare two `...Z` RFC3339 instants as strings.

    Lexicographic comparison is exact for fixed-width UTC `Z` timestamps, which
    is what `gcp-env`-driven callers and Cloud Logging both produce. A value
    that is not in that shape is rejected rather than silently mis-ordered - a
    `since` that sorts wrong would silently widen the window past the floor.
    """
    for v in (a, b):
        if not (isinstance(v, str) and v.endswith("Z") and len(v) >= 20
                and v[4] == "-" and v[10] == "T"):
            raise HoldoutTouchUnevaluable(
                "timestamp %r is not RFC3339 UTC (YYYY-MM-DDTHH:MM:SSZ). This "
                "counter will not compare a window boundary it cannot order."
                % (v,))
    return a >= b


class HoldoutTouchCounter:
    """Zero-arg callable returning `holdout_touch_count` for a window.

    Drops into `RealGate(holdout_touch=...)`, which takes a callable with NO
    DEFAULT precisely so that "nothing computed this" cannot be mistaken for
    "the count was zero".

        counter = HoldoutTouchCounter(env, since=run_started_at)
        gate = RealGate(..., holdout_touch=counter, holdout_expected=2)

    Every collaborator is injected so the whole thing runs offline in tests:
    `log_read(project, filter_text, cap) -> [entry]` and
    `policy_fetch() -> project IAM policy dict`.
    """

    def __init__(self, env, since, permitted_principals=None,
                 cap=DEFAULT_CAP, log_read=None, policy_fetch=None,
                 floor=ATTESTATION_FLOOR_UTC, settle_seconds=0.0, sleep=None):
        self.env = env
        self.project = env["CRUCIBLE_PROJECT"]
        self.bucket = env["CRUCIBLE_SEALED_BUCKET"]
        self.since = since
        self.floor = floor
        self.cap = cap
        self.settle_seconds = settle_seconds
        self._sleep = sleep or time.sleep
        self._log_read = log_read or (
            lambda project, filt, cap_: gcloud_log_read(project, filt, cap_))
        self._policy_fetch = policy_fetch or self._default_policy_fetch
        # The one identity permitted to read the holdout. Sourced, never typed.
        # The human operator is DELIBERATELY NOT in this set: they hold
        # roles/owner and can read everything, and the honest response to that
        # is to record it, not to exempt it.
        if permitted_principals is None:
            permitted_principals = {
                "%s@%s.iam.gserviceaccount.com"
                % (env["SA_SEALED_EVAL"], self.project)}
        self.permitted_principals = set(permitted_principals)
        self.last_tally = None

    def _default_policy_fetch(self):
        return verify_iam.gcloud_json(
            ["gcloud", "projects", "get-iam-policy", self.project,
             "--format=json"], "project IAM policy")

    # -- the read command, exposed so the proof artifact can quote it ------

    def filter_text(self, since=None):
        return build_filter(self.project, self.bucket, since or self.since)

    def command(self, since=None):
        """The exact read-only command behind the number, as a display string.

        Printed into the proof artifact. A number whose provenance is a
        paraphrase is a number a judge cannot re-derive.
        """
        return ("gcloud logging read '%s' --project=%s --limit=%d --order=asc "
                "--format=json" % (self.filter_text(since), self.project,
                                   self.cap))

    # -- the preconditions -------------------------------------------------

    def _check_window(self):
        if not _iso_ge(self.since, self.floor):
            raise HoldoutTouchUnevaluable(
                "the requested window starts at %s, before the attestation "
                "floor %s. Data Access logging was enabled 2026-08-22 and is "
                "not retroactive: a probe at 18:27:30Z that day left no entry "
                "while a read at 19:31:10Z did. G7c can attest from the floor "
                "forward and NOT before it, and reporting 0 for time the log "
                "never covered would be a clean seal invented out of missing "
                "data." % (self.since, self.floor))

    def _check_audit_config(self):
        try:
            policy = self._policy_fetch()
        except Exception as e:                                # noqa: BLE001
            raise HoldoutTouchUnevaluable(
                "could not read the project IAM policy (%s), so whether Data "
                "Access logging is still on is unknown" % e) from None
        problem = storage_data_read_enabled(policy)
        if problem:
            raise HoldoutTouchUnevaluable(problem)

    def _check_canary(self):
        """THE POSITIVE CONTROL. Without it every guard above still leaves one
        way to fabricate a clean seal: a filter that matches nothing.

        A misspelled bucket, a renamed log, a changed `resource.type` and a
        genuinely untouched seal all return the same empty list. So before any
        count is trusted, this asserts the query CAN see something, by running
        the same filter over the whole attestable window - where at least one
        entry is known to exist and cannot be removed (Cloud Logging entries are
        not deletable by the project owner; only the whole bucket's retention
        expires).
        """
        entries = self._log_read(self.project,
                                 self.filter_text(self.floor), 1)
        if not entries:
            raise HoldoutTouchUnevaluable(
                "THE CANARY QUERY RETURNED NOTHING. Over the entire attestable "
                "window (%s -> now) this filter matches zero entries, and at "
                "least one read is known to be recorded there. A misspelled "
                "bucket, a renamed log, and a seal nobody touched all look "
                "exactly like this, so no count from this filter can be "
                "trusted. Filter: %s" % (self.floor, self.filter_text(self.floor)))

    # -- the number --------------------------------------------------------

    def compute(self):
        """Full structured result. `__call__` returns only `['count']`."""
        self._check_window()
        self._check_audit_config()
        if self.settle_seconds:
            # Cloud Logging ingestion lags the event. A read seconds before this
            # query can be invisible, and a missed read is an UNDERCOUNT that
            # reads as a pass.
            self._sleep(self.settle_seconds)
        self._check_canary()

        entries = self._log_read(self.project, self.filter_text(), self.cap)
        if len(entries) >= self.cap:
            raise HoldoutTouchUnevaluable(
                "the log query returned %d entries at its cap of %d, so the "
                "result is truncated and the true count is unknown. G7 has no "
                "'at least N' outcome." % (len(entries), self.cap))

        result = tally(entries, self.permitted_principals)
        result["since"] = self.since
        result["filter"] = self.filter_text()
        result["command"] = self.command()
        self.last_tally = result

        if result["intruders"]:
            who = sorted({r["principal"] for r in result["intruders"]})
            raise HoldoutTouchInvalid(
                "the sealed holdout was READ by %d request(s) from outside the "
                "permitted set: %s. measurement-spec.md:946 - any read from "
                "another SA marks the run INVALID. Permitted: %s"
                % (len(result["intruders"]), ", ".join(who),
                   ", ".join(sorted(self.permitted_principals))))
        return result

    def __call__(self):
        return self.compute()["count"]


def render_tally(result):
    """Human-readable, for the proof artifact and the demo UI."""
    lines = [
        "  window since : %s   (attestation floor %s)"
        % (result.get("since"), ATTESTATION_FLOOR_UTC),
        "  command      : %s" % result.get("command", ""),
        "  entries      : %d matched" % result["entries"],
        "  COUNT        : %d granted object-content reads  <- holdout_touch_count"
        % result["count"],
        "  distinct     : %d distinct principal x object (one `cat` emits two "
        "entries: metadata + media)" % result["distinct_reads"],
        "  enumerations : %d granted (listings / bucket metadata / prefix probes"
        " - NOT counted)" % len(result["enumerations"]),
        "  denied       : %d (logged, and not a touch: no bytes moved)"
        % len(result["denied"]),
        "  principals   : %s" % (", ".join(result["principals"]) or "(none)"),
    ]
    for r in result["reads"]:
        lines.append("    READ   %s  %s  %s"
                     % (r["timestamp"], r["principal"], r["resource"]))
    for r in result["denied"]:
        lines.append("    DENIED %s  %s  %s"
                     % (r["timestamp"], r["principal"], r["resource"]))
    if result["other"]:
        for r in result["other"]:
            lines.append("    OTHER  %s  %s  %s"
                         % (r["timestamp"], r["method"], r["resource"]))
    return "\n".join(lines)


__all__ = [
    "ATTESTATION_FLOOR_UTC", "CONTENT_READ", "ENUMERATION", "OTHER",
    "DEFAULT_CAP", "HoldoutTouchCounter", "HoldoutTouchError",
    "HoldoutTouchInvalid", "HoldoutTouchUnevaluable", "bucket_name",
    "build_filter", "classify", "gcloud_log_read", "is_granted",
    "render_tally", "storage_data_read_enabled", "tally",
]
