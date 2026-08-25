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
  * **the canary query must return at least one GRANTED CONTENT READ** over the
    whole attestable window. That is the positive control, and it is what makes
    a zero in the *run* window mean "nobody touched the seal" instead of "this
    query has never seen anything." One real read is recorded in the log
    permanently (2026-08-22T19:31:19Z, `crucible-sealed-eval` reading
    `families/_probe/canary.txt`), so this control holds from now on without
    anyone having to re-touch the holdout.
  * a result at the cap is a truncation, and a truncated count is UNEVALUABLE
    rather than "at least N". G7 does not have an "at least" outcome.

None of those return 0. They all raise.

TWO SERVER-SIDE NARROWINGS WERE ADDED 2026-08-25, AND THEY BOTH REINTRODUCE
THE FAILURE ABOVE IN A NEW PLACE
------------------------------------------------------------------
The base filter matched 624 entries against a cap of 1000 that raises
UNEVALUABLE, growing about four per gate call: one more batch the size of the
2026-08-25 one and G7c goes dark on the run that matters. So the count query now
drops the methods `classify` already refuses to count, and the intruder query
additionally excludes the permitted principals in the filter (624 -> 14 -> 9,
all measured). **A filter that asks the server for only the bad entries returns
zero when the filter is wrong, and zero looks exactly like a clean seal.**

What stops that, and both halves are mandatory:

  * `_check_canary` runs THE SAME CONSTRUCTION, both narrowings included,
    excluding a SENTINEL principal that cannot exist. The known-present read has
    to survive the whole compiled filter or nothing is trusted.
  * the exclusion is a BOUND, NEVER THE DECISION. `compute()` re-applies
    `principal not in permitted_principals` in Python to both result sets and
    unions them. The server narrows what travels; this file decides what it
    means.

ATTESTED READS. WHAT THEY ARE, AND THE TWO THINGS THEY ARE NOT
------------------------------------------------------------------
Seven operator reads from 2026-08-22 sit permanently inside the attestation
window, and Cloud Logging cannot delete them, so the proof artifact's G7c line
was red forever for an intact boundary. They are handled by ATTESTATION, from
the dated record at `docs/proof/holdout-attested-reads-2026-08-22.md`:

  * NOT by moving the window forward. That hides the reads, and a control that
    stops looking is not a control that passed.
  * NOT by adding the operator to `permitted_principals`. Exempting the human is
    the self-certification move G8 exists to prevent, and it would forgive every
    future operator read too.

An attestation key is an INSTANT - timestamp, principal, method, object - so it
can only ever match a read that has already happened and been explained. An
attested read is COUNTED and SHOWN, moved out of `intruders` and into
`attested_reads` with its reason. An unexplained read still marks the run
INVALID.

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
import os
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

# --------------------------------------------------------------------------
# THE CAP HAD A COUNTDOWN ON IT. What this narrowing is and what it is not.
# --------------------------------------------------------------------------
# Measured against the live project 2026-08-25, window = ATTESTATION_FLOOR_UTC:
#
#   base filter, every clause below except these         624 entries / cap 1000
#     of which storage.objects.list                      606
#     of which storage.buckets.getStorageLayout            4
#     of which storage.objects.get                        14
#
# `compute()` raises UNEVALUABLE at the cap, correctly, because a truncated
# result has no "at least N" outcome. 624 of 1000 with roughly four entries
# added per gate call is about ninety gate calls of headroom: ONE MORE BATCH
# THE SIZE OF THE 2026-08-25 ONE AND G7c GOES DARK on the run that matters.
#
# The population that blows up is NOT reads. It is `storage.objects.list`, and
# 606 of those 624 are the G7a impersonation probe's own four arms - one granted
# listing by the permitted evaluator plus three denials - firing on every gate
# call. `classify` below already files every one of them as ENUMERATION and
# refuses to count them. So this is a PUSHDOWN of a rule the module already
# applies client-side, not a new exclusion: the server stops shipping entries
# this file was going to throw away anyway. 624 -> 14, measured.
#
# WHAT IS DELIBERATELY *NOT* DROPPED, because the reason matters more than the
# saving:
#   * `storage.objects.get` on a PREFIX (resource ends in `/`) is still
#     retrieved, and still filed as ENUMERATION client-side. The narrowing is by
#     METHOD only, so the prefix-probe branch stays reachable against live data.
#   * a DENIED get is still retrieved, so the tally can still show the boundary
#     refusing someone.
#   * an UNRECOGNISED method is still retrieved, because "a method this module
#     has never seen is not evidence of nothing" (see `classify`). This is why
#     the narrowing is written as NOT-a-touch exclusions rather than as an
#     `methodName="storage.objects.get"` inclusion: an inclusion filter would
#     have silently deleted the OTHER branch.
#
# THE COST, STATED: a GRANTED `storage.objects.list` by an unpermitted principal
# is no longer retrieved. It was never counted as a touch either, and the
# boundary it would evidence is the one G7a's impersonation probe tests
# DIRECTLY, on every gate call, against all four identities. Naming the gap
# rather than covering it.
#
# These two tuples MUST stay in step with `classify`'s ENUMERATION-by-method
# branches. `tests/test_holdout_touch.py` asserts that coupling rather than
# trusting it.
NOT_A_TOUCH_METHODS = ("storage.objects.list",)
NOT_A_TOUCH_METHOD_PREFIXES = ("storage.buckets.",)

# The canary reads the EARLIEST entries in the attestable window (`--order=asc`)
# and the read it is looking for happened at the floor itself, so a small cap is
# sufficient and a large one would only cost latency. It is a DIFFERENT constant
# from `DEFAULT_CAP` on purpose: the two windows want different values and
# raising one to fix the other is the move `docs/design/g7-unevaluable-
# 2026-08-25.md` section 5.2 refuses.
CANARY_CAP = 25

# The dated record of operator reads that are ACCOUNTED FOR. Single source of
# truth; see `load_attested_reads`.
ATTESTED_READS_RECORD = "docs/proof/holdout-attested-reads-2026-08-22.md"


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


def build_filter(project, bucket_uri, since,
                 drop_non_touch_methods=False, exclude_principals=()):
    """The Cloud Logging filter, assembled from sourced names only.

    TWO OPTIONAL NARROWINGS, AND THE SECOND ONE IS THE DANGEROUS KIND.

    `drop_non_touch_methods` pushes `classify`'s ENUMERATION-by-method rule to
    the server. See NOT_A_TOUCH_METHODS above for the measurement and for what
    is deliberately still retrieved.

    `exclude_principals` asks the server for only the entries whose principal is
    NOT in the permitted set - the INTRUDER query. It bounds that query by the
    number of UNATTESTED reads instead of by all reads.

    **A FILTER THAT ASKS FOR ONLY THE BAD ENTRIES RETURNS ZERO WHEN THE FILTER
    IS WRONG, AND ZERO LOOKS EXACTLY LIKE A CLEAN SEAL.** That is the single
    failure this module exists to refuse, and adding a NOT-clause reintroduces
    it in a new place. Two things stop it, and both are mandatory:

      1. `_check_canary` runs THIS SAME CONSTRUCTION - both narrowings included -
         over the attestable window, excluding a SENTINEL principal that cannot
         exist, and requires it to still see a real granted content read. An
         over-broad NOT-clause blanks that query and is caught there.
      2. The exclusion is a BOUND, NEVER THE DECISION. `compute()` re-applies
         `principal not in permitted_principals` in Python to both result sets
         and takes the UNION. The server narrows what travels; this file decides
         what it means.

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
    clauses = [
        'logName="projects/%s/logs/%s"' % (project, DATA_ACCESS_LOG),
        'protoPayload.serviceName="%s"' % STORAGE_SERVICE,
        'resource.type="gcs_bucket"',
        'resource.labels.bucket_name="%s"' % bucket_name(bucket_uri),
        'timestamp>="%s"' % since,
    ]
    if drop_non_touch_methods:
        for method in NOT_A_TOUCH_METHODS:
            clauses.append('NOT protoPayload.methodName="%s"' % method)
        for prefix in NOT_A_TOUCH_METHOD_PREFIXES:
            clauses.append('NOT protoPayload.methodName:"%s"' % prefix)
    # SORTED, so the filter string is deterministic and the `command()` printed
    # into the proof artifact is the command a judge can paste back.
    principals = sorted(p for p in (exclude_principals or ()) if p)
    if principals:
        clauses.append(
            'NOT protoPayload.authenticationInfo.principalEmail=(%s)'
            % " OR ".join('"%s"' % p for p in principals))
    return " AND ".join(clauses)


def _fetch_backoff(attempt):
    """Seconds to wait before attempt+1. ONE POLICY, `verify_iam`'s.

    Indexed defensively so raising `FETCH_ATTEMPTS` past the length of
    `FETCH_BACKOFF` cannot turn a retry into an IndexError, which would convert
    a transient fetch failure into a crash - a different failure, reported in a
    way nobody would connect back to gcloud.
    """
    backoff = verify_iam.FETCH_BACKOFF
    return backoff[min(attempt - 1, len(backoff) - 1)]


def gcloud_log_read(project, filter_text, cap, runner=None, sleep=None):
    """`gcloud logging read` -> list of entry dicts. READ-ONLY.

    A non-zero exit RAISES. It must never degrade to `[]`: an empty list is
    indistinguishable from a clean seal, which is the whole failure this file
    exists to refuse.

    RETRIED, BOUNDED, AND THE ERROR NOW SAYS SOMETHING. `57f4e94` fixed exactly
    these two defects in `verify_iam.gcloud_json` and left this call site - one
    of the two that actually failed - untouched. Run 10 of the 2026-08-25
    overnight batch was invalidated by a transient gcloud failure whose stderr
    was EMPTY, and this function reproduced that dead end verbatim: it
    interpolated `p.stderr` alone, so an exit-1 with no stderr rendered as
    `gcloud logging read exited 1: .`

    `FETCH_ATTEMPTS` and `FETCH_BACKOFF` are IMPORTED from `verify_iam` rather
    than redeclared. Three call sites with three retry policies is three sources
    of truth for one decision.

    RETRYING CANNOT LAUNDER A FAILURE INTO A PASS. Only a non-zero exit is
    retried, and exhausting the attempts RAISES. A permission denial simply
    returns the same non-zero exit three times and still ends UNEVALUABLE. A
    zero exit is returned on the first attempt, parsed or refused; malformed
    JSON is a semantic answer and is not retried.

    `runner` and `sleep` are injected so `tests/test_fetch_retry.py` can drive
    the retry without a network. `57f4e94` shipped the `gcloud_json` retry with
    no test at all, and a retry nothing exercises is a check that cannot fail
    wearing different clothes.
    """
    if runner is None:
        exe = verify_iam._gcloud_exe()                        # noqa: SLF001

        def runner(argv_):
            return subprocess.run(argv_, capture_output=True, text=True)
    else:
        exe = "gcloud"
    argv = [exe, "logging", "read", filter_text,
            "--project=%s" % project,
            "--limit=%d" % cap,
            "--order=asc",
            "--format=json"]
    sleep = sleep or time.sleep
    last = None
    for attempt in range(1, verify_iam.FETCH_ATTEMPTS + 1):
        p = runner(argv)
        if p.returncode == 0:
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
        # The diagnostic run 10 did not get. An error that reports nothing is a
        # diagnostic dead end; the return code and a stdout slice travel with it.
        out = (p.stdout or "").strip()
        err = (p.stderr or "").strip()[:300] or (
            "no stderr; stdout was %r" % out[:120] if out
            else "no stderr and no stdout")
        last = "exit %d, %s" % (p.returncode, err)
        if attempt < verify_iam.FETCH_ATTEMPTS:
            sleep(_fetch_backoff(attempt))
    raise HoldoutTouchUnevaluable(
        "gcloud logging read failed on all %d attempts (%s). A failed fetch is "
        "not an empty log; returning 0 here would report a seal nobody touched."
        % (verify_iam.FETCH_ATTEMPTS, last))


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


# --------------------------------------------------------------------------
# ATTESTATION. Named reads that are ACCOUNTED FOR - never a principal exemption.
# --------------------------------------------------------------------------

def attestation_key(row):
    """The identity of one read: nanosecond timestamp, principal, method, object.

    ALL FOUR, AND THE TIMESTAMP IS WHY THIS IS NOT AN EXEMPTION. Attesting a
    PRINCIPAL would hand the human operator a permanent hole in the one control
    that records what the trust root did, which is the self-certification move
    G8 exists to prevent. Attesting an INSTANT attests a past event: it can
    never match a read that has not happened yet, because that read carries a
    different timestamp. A new operator read is unexplained by construction and
    still fails.
    """
    return (row.get("timestamp", ""), row.get("principal", ""),
            row.get("method", ""), row.get("resource", ""))


def _record_path(path=None):
    if path is not None:
        return path
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(repo_root, *ATTESTED_READS_RECORD.split("/"))


def load_attested_reads(path=None):
    """The dated record -> `{attestation_key: reason}`. One source of truth.

    The record is a MARKDOWN document carrying a single fenced ```json block.
    One file, so the prose a judge reads and the keys the code matches cannot
    drift apart - a second copy of a fact is a second source of truth, and this
    fact is "which reads of the sealed holdout are explained".

    THE TWO FAILURE DIRECTIONS ARE DELIBERATELY DIFFERENT:

      record MISSING     -> attest NOTHING, and report the problem. Fails SAFE:
                            every operator read stays unexplained and G7c stays
                            red. A missing file must never widen what is
                            forgiven.
      record UNPARSEABLE -> RAISE. The file exists and the control is broken.
                            Attesting nothing would be the safe direction and
                            also a silent one, and a broken instrument is
                            exactly what UNEVALUABLE is for.
    """
    p = _record_path(path)
    if not os.path.exists(p):
        return {}, ("the attestation record %s IS MISSING, so NO read is "
                    "treated as explained. Nothing is forgiven by a file that "
                    "is not there." % ATTESTED_READS_RECORD)
    with open(p, "r", encoding="utf-8") as fh:
        text = fh.read()
    start = text.find("```json")
    if start < 0:
        raise HoldoutTouchUnevaluable(
            "%s carries no ```json block. The record exists and cannot be read, "
            "which is a broken control rather than an empty one."
            % ATTESTED_READS_RECORD)
    body_start = text.index("\n", start) + 1
    end = text.find("```", body_start)
    if end < 0:
        raise HoldoutTouchUnevaluable(
            "%s has an unterminated ```json block." % ATTESTED_READS_RECORD)
    try:
        doc = json.loads(text[body_start:end])
    except json.JSONDecodeError as e:
        raise HoldoutTouchUnevaluable(
            "%s does not parse: %s" % (ATTESTED_READS_RECORD, e)) from None
    attested = {}
    for row in doc.get("attested_reads") or []:
        missing = [f for f in ("timestamp", "principal", "method", "resource",
                               "why") if not row.get(f)]
        if missing:
            raise HoldoutTouchUnevaluable(
                "%s has an attested read missing %s. A read attested without a "
                "reason is an exemption with better manners."
                % (ATTESTED_READS_RECORD, ", ".join(missing)))
        attested[(row["timestamp"], row["principal"], row["method"],
                  row["resource"])] = row["why"]
    return attested, None


def tally(entries, permitted_principals, attested=None):
    """Classified entries -> a structured tally. Pure.

    `count` is the number G7c compares. Everything else is there so the finding
    can say WHO and WHAT rather than only how many - "any read from another SA"
    is a statement about principals, and a bare integer cannot carry it.

    `attested` maps `attestation_key` -> reason. An attested read is COUNTED and
    SHOWN, never excluded: it moves out of `intruders` and into
    `attested_reads`, still inside `count`, still printed with its object and
    its reason. Hiding it would remove the only record that the trust root
    touched the seal, which is the record's entire value.
    """
    attested = attested or {}
    rows = [classify(e) for e in entries]
    reads = [r for r in rows if r["kind"] == CONTENT_READ and r["granted"]]
    outside = [r for r in reads if r["principal"] not in permitted_principals]
    attested_reads = []
    intruders = []
    for r in outside:
        why = attested.get(attestation_key(r))
        if why:
            r = dict(r, attested_why=why)
            attested_reads.append(r)
        else:
            intruders.append(r)
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
        "attested_reads": attested_reads,
        "outside_permitted": len(outside),
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
                 floor=ATTESTATION_FLOOR_UTC, settle_seconds=0.0, sleep=None,
                 attested=None, attested_path=None):
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
        # THE CANARY'S SENTINEL. A principal that cannot exist, excluded by the
        # SAME construction the intruder query uses, so the control exercises
        # the NOT-clause rather than merely the clauses around it. Built from
        # the SOURCED project id; nothing here is a retyped name.
        self.canary_sentinel = (
            "crucible-canary-control-never-exists@%s.iam.gserviceaccount.com"
            % self.project)
        if attested is None:
            attested, self.attestation_problem = load_attested_reads(
                attested_path)
        else:
            self.attestation_problem = None
        self.attested = dict(attested)
        self.last_tally = None

    def _default_policy_fetch(self):
        return verify_iam.gcloud_json(
            ["gcloud", "projects", "get-iam-policy", self.project,
             "--format=json"], "project IAM policy")

    # -- the read command, exposed so the proof artifact can quote it ------

    def filter_text(self, since=None):
        """THE COUNT QUERY. Every touch candidate in the window, from anyone.

        No principal exclusion: `holdout_touch_count` is a count of reads, not a
        count of intrusions, and the permitted evaluator's reads are exactly what
        `expected_for_this_phase` is about.
        """
        return build_filter(self.project, self.bucket, since or self.since,
                            drop_non_touch_methods=True)

    def intruder_filter_text(self, since=None, exclude=None):
        """THE INTRUDER QUERY. Bounded by unattested reads, not by all reads.

        `exclude` defaults to the permitted set. `_check_canary` passes the
        sentinel instead, which is what makes this construction falsifiable.
        """
        exclude = self.permitted_principals if exclude is None else exclude
        return build_filter(self.project, self.bucket, since or self.since,
                            drop_non_touch_methods=True,
                            exclude_principals=exclude)

    def command(self, since=None):
        """The exact read-only command behind the number, as a display string.

        Printed into the proof artifact. A number whose provenance is a
        paraphrase is a number a judge cannot re-derive.
        """
        return ("gcloud logging read '%s' --project=%s --limit=%d --order=asc "
                "--format=json" % (self.filter_text(since), self.project,
                                   self.cap))

    def intruder_command(self, since=None):
        return ("gcloud logging read '%s' --project=%s --limit=%d --order=asc "
                "--format=json" % (self.intruder_filter_text(since),
                                   self.project, self.cap))

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

        IT RUNS THE INTRUDER CONSTRUCTION, NOT THE BASE ONE, and that is the
        half added 2026-08-25. The count query and the intruder query now carry
        two server-side narrowings that did not exist when this control was
        written - a method exclusion and a principal exclusion - and either one,
        written wrong, blanks the result. A control that exercises only the
        clauses those narrowings were added around would pass while the
        narrowings returned nothing. So the canary excludes a SENTINEL principal
        that cannot exist: the known-present read must survive the whole
        compiled filter, NOT-clause included.

        AND IT NOW REQUIRES A GRANTED CONTENT READ, not merely an entry. The
        earliest entry in the attestable window is a `granted: true` /
        `status.code: 5` prefix probe, which `is_granted` correctly refuses to
        count - so "at least one entry" could be satisfied by a shape that can
        never produce a non-zero count. The control asserts the whole pipeline,
        filter through `classify`, can yield the number it exists to produce.
        `--order=asc` puts the known read (2026-08-22T19:31:19Z) among the
        earliest entries in the window, so CANARY_CAP does not have to grow.
        """
        filt = self.intruder_filter_text(self.floor,
                                         exclude={self.canary_sentinel})
        # THE CONTROL MUST CONTAIN THE CLAUSE IT EXISTS TO CONTROL. Found by
        # running this against the live project 2026-08-25: `build_filter` drops
        # empty principals, so a `canary_sentinel` that was ever None or "" would
        # compile to a filter with NO exclusion clause, the canary would pass on
        # the clauses around the new one, and the control would look green while
        # testing nothing. A control that can be silently switched off is a check
        # that cannot fail.
        if "NOT protoPayload.authenticationInfo.principalEmail" not in filt:
            raise HoldoutTouchUnevaluable(
                "the canary filter compiled WITHOUT its exclusion clause "
                "(sentinel %r), so it would not exercise the NOT-clause the "
                "intruder query depends on. Refusing to treat that as a passing "
                "control. Filter: %s" % (self.canary_sentinel, filt))
        entries = self._log_read(self.project, filt, CANARY_CAP)
        rows = [classify(e) for e in entries]
        reads = [r for r in rows if r["kind"] == CONTENT_READ and r["granted"]]
        if not entries:
            raise HoldoutTouchUnevaluable(
                "THE CANARY QUERY RETURNED NOTHING. Over the entire attestable "
                "window (%s -> now) this filter matches zero entries, and at "
                "least one read is known to be recorded there. A misspelled "
                "bucket, a renamed log, an over-broad method or principal "
                "exclusion, and a seal nobody touched all look exactly like "
                "this, so no count from this filter can be trusted. Filter: %s"
                % (self.floor, filt))
        if not reads:
            raise HoldoutTouchUnevaluable(
                "THE CANARY QUERY MATCHED %d ENTRIES AND NOT ONE OF THEM IS A "
                "GRANTED CONTENT READ. A known granted read of the holdout is "
                "recorded in this window, so the filter is reaching the log and "
                "the pipeline from filter to classify cannot produce a non-zero "
                "count. A counter that can only ever answer 0 is a check that "
                "cannot fail. Filter: %s" % (len(entries), filt))

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
                "the count query returned %d entries at its cap of %d, so the "
                "result is truncated and the true count is unknown. G7 has no "
                "'at least N' outcome." % (len(entries), self.cap))

        # THE INTRUDER QUERY. A SECOND, INDEPENDENTLY BOUNDED PATH TO THE SAME
        # VERDICT. Its cap is a real guard on its own terms: a result at the cap
        # is a truncated list of unattested reads, which is the one list that
        # must never be shortened by an accident of paging.
        intruder_entries = self._log_read(
            self.project, self.intruder_filter_text(), self.cap)
        if len(intruder_entries) >= self.cap:
            raise HoldoutTouchUnevaluable(
                "the INTRUDER query returned %d entries at its cap of %d. A "
                "truncated list of unattested reads is not a shorter list of "
                "unattested reads. Raising the cap silently would be the same "
                "defect wearing a bigger number." % (len(intruder_entries),
                                                     self.cap))

        result = tally(entries, self.permitted_principals, self.attested)
        result["since"] = self.since
        result["filter"] = self.filter_text()
        result["command"] = self.command()
        result["intruder_filter"] = self.intruder_filter_text()
        result["intruder_command"] = self.intruder_command()
        result["intruder_entries"] = len(intruder_entries)
        result["attestation_problem"] = self.attestation_problem
        result["attestation_record"] = ATTESTED_READS_RECORD

        # THE SERVER NARROWS; THIS FILE DECIDES. The exclusion clause is a bound
        # on what travels, never the verdict, so the same Python predicate is
        # re-applied to the intruder query's own rows and the two paths are
        # UNIONED. A NOT-clause written wrong can then only over-report - which
        # raises loudly - and the direction it could under-report in is the one
        # `_check_canary` refuses.
        server = tally(intruder_entries, self.permitted_principals,
                       self.attested)
        seen = {attestation_key(r) for r in result["intruders"]}
        only_server = [r for r in server["intruders"]
                       if attestation_key(r) not in seen]
        if only_server:
            result["intruders"] = result["intruders"] + only_server
            result["found_only_by_intruder_query"] = len(only_server)
        result["unattested_reads"] = len(result["intruders"])
        self.last_tally = result

        if result["intruders"]:
            who = sorted({r["principal"] for r in result["intruders"]})
            extra = ""
            if self.attestation_problem:
                extra = " NOTE: %s" % self.attestation_problem
            raise HoldoutTouchInvalid(
                "the sealed holdout was READ by %d UNATTESTED request(s) from "
                "outside the permitted set: %s. measurement-spec.md:946 - any "
                "read from another SA marks the run INVALID. Permitted: %s. "
                "Attested and explained in %s: %d read(s).%s"
                % (len(result["intruders"]), ", ".join(who),
                   ", ".join(sorted(self.permitted_principals)),
                   ATTESTED_READS_RECORD, len(result["attested_reads"]), extra))
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
        "  UNATTESTED   : %d granted read(s) from outside the permitted set "
        "and not named in %s  <- the assertion"
        % (len(result.get("intruders") or []), ATTESTED_READS_RECORD),
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
    if result.get("intruder_command"):
        lines.append("  intruder cmd : %s" % result["intruder_command"])
        lines.append("  intruder qry : %d entries (bounded by UNATTESTED reads, "
                     "not by all reads)" % result.get("intruder_entries", 0))
    lines.append(
        "  NOT RETRIEVED: %s and %s* entries. `classify` files every one of "
        "them as ENUMERATION and never counts them; the server now stops "
        "shipping what this file was going to discard. 624 -> 14 on the "
        "attestation window, measured 2026-08-25. A GRANTED listing by an "
        "unpermitted principal is therefore not shown here - G7a's "
        "impersonation probe tests that boundary directly, every gate call."
        % (", ".join(NOT_A_TOUCH_METHODS),
           ", ".join(NOT_A_TOUCH_METHOD_PREFIXES)))
    if result.get("attestation_problem"):
        lines.append("  ATTESTATION  : %s" % result["attestation_problem"])
    for r in result["reads"]:
        lines.append("    READ   %s  %s  %s"
                     % (r["timestamp"], r["principal"], r["resource"]))
    for r in result.get("attested_reads") or []:
        lines.append("    ATTESTED %s  %s  %s"
                     % (r["timestamp"], r["principal"], r["resource"]))
        lines.append("             why: %s" % r.get("attested_why", ""))
    for r in result["denied"]:
        lines.append("    DENIED %s  %s  %s"
                     % (r["timestamp"], r["principal"], r["resource"]))
    if result["other"]:
        for r in result["other"]:
            lines.append("    OTHER  %s  %s  %s"
                         % (r["timestamp"], r["method"], r["resource"]))
    return "\n".join(lines)


__all__ = [
    "ATTESTATION_FLOOR_UTC", "ATTESTED_READS_RECORD", "CANARY_CAP",
    "CONTENT_READ", "ENUMERATION", "OTHER",
    "DEFAULT_CAP", "NOT_A_TOUCH_METHODS", "NOT_A_TOUCH_METHOD_PREFIXES",
    "HoldoutTouchCounter", "HoldoutTouchError",
    "HoldoutTouchInvalid", "HoldoutTouchUnevaluable", "attestation_key",
    "bucket_name", "build_filter", "classify", "gcloud_log_read", "is_granted",
    "load_attested_reads", "render_tally", "storage_data_read_enabled", "tally",
]
