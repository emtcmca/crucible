"""real_gate.py - a drop-in for `campaign.py`'s gate stand-in, `lambda c, r: True`.

`campaign.py`'s own header says it plainly:

    * **the GATE.** No GCS, no IAM, no `objectCreator` boundary. G7 and G8 are
      not exercised and cannot be.

`lambda c, r: True` is not a weak gate. It is the ABSENCE of one: it returns
PROMOTE for every candidate, unconditionally, having inspected nothing. G7
(SEAL INTEGRITY) and G8 (NON-SELF-APPROVAL) are the two strongest architectural
claims in this project and the two whose failure mode is RUN INVALID - and
neither had ever run against anything. **A check that cannot fail is not
measuring anything** (`measurement-spec.md:813`), and a gate that is a constant
function is the limiting case of that.

WHAT THIS FILE REUSES RATHER THAN REBUILDS
------------------------------------------------------------------
Same discipline as `real_warden.py`: the real pieces, wired, not reimplemented.

  * `crucible.gate.promote` - L1's real promotion write path, INCLUDING its
    read-back-and-recompute-from-bytes assertion. This file does not re-derive a
    single hash; it injects `blob_writer`/`blob_reader` and lets `promote` do
    what it already does. `object_name` is likewise imported, never re-spelled -
    the object path is a string two places would eventually disagree about.
  * `infra.verify_iam` - the G7/G8 IAM predicates, which already exist as pure
    functions over a policy dict, each already driven to red by that module's
    `--selftest`. Restating any of them here would create a second source of
    truth for the boundary whose whole point is that it has exactly one.
  * `scripts/gcp-env.sh`, read through `verify_iam.load_env`, for every project,
    bucket, and service-account name. **Nothing in this file types a bucket name
    or an SA name as a literal.** G7 and G8 grep those strings, so a typo does
    not fail loudly - it produces an unevaluable gate, which reads exactly like a
    passing one (`CONVENTIONS.md` 10a, and `verify_iam.py`'s own header).

THE THREE OUTCOMES ARE NOT INTERCHANGEABLE, AND THE RETURN TYPE HIDES TWO
------------------------------------------------------------------
`contracts/gate_rule.v1.yaml`:

    REJECT      the candidate was not good enough. The RUN is fine.
    RUN INVALID the INSTRUMENT is untrustworthy. NO NUMBER FROM THIS RUN MAY BE
                REPORTED, INCLUDING THE ONES THAT LOOK GOOD.
    HALT        a human decides.

`Conductor` calls `self.promote(candidate, record)` and reads a BOOL. A bool has
room for two of those three, and the missing one is the one that voids the run.
So: **RUN INVALID and HALT are raised, never returned.** `GateRunInvalid` and
`GateHalt` propagate straight out of `Conductor.run` - there is no `except` in
that loop, deliberately. Returning `False` for a G8 failure would silently
downgrade "the separation was never real" into "try again next round", and the
campaign would print a rejection line and keep measuring. That downgrade is the
exact shape this project keeps finding and killing.

WHAT THIS GATE EVALUATES, AND WHAT IT DOES NOT
------------------------------------------------------------------
EVALUATED HERE:
  G7a  impersonation probe, with its positive control      (read-only gcloud)
  G7b  committed grant assertion, sealed bucket            (read-only gcloud)
  G7b2 no CRUCIBLE identity holds a project-level BASIC role - filed as
       `G7b2/G8`, because BOTH gates assert it and G8's failure mode wins
  G7c  holdout touch count == expected for this phase      (INJECTED, see below)
  G8   the Armorer<->Gate separation on the policies bucket, objectCreator-only
       on the promoter, retention present and UNLOCKED, versioning ON
  G2   policy read-back - `crucible.gate.promote`'s recompute-from-bytes

NOT EVALUATED HERE, and each already has an owner:
  G1   calibration + oracle freeze -> `crucible.warden.run_known_bad_suite`,
       `crucible.tripwire.known_bad`. Evaluated at round start, not at the gate.
  G3   benign floor -> the `benign_gate` hook. `Conductor.run_round` already
       computes `passed` from it and only calls this function when it holds.
  G4   attack reduction -> the conductor's paired scoring across rounds.
  G5   rule hygiene -> `crucible.dsl.validator`, before a candidate exists.
  G6   provenance -> the Armorer's citation of this round's autopsy.
Bolting any of them on here would put a second evaluator behind the same bool.

G7c IS INJECTED, AND WITHOUT IT THE RUN IS INVALID. THAT IS NOT A BUG.
------------------------------------------------------------------
`holdout_touch_count` is derived from Cloud Audit Logs DATA ACCESS reads on the
sealed holdout, exported and counted (`measurement-spec.md`:946, expected value
**2**). G7's contract says `absent_or_unevaluable: RUN_INVALID`, so this gate
takes `holdout_touch` as an injected callable with NO DEFAULT and, with none
supplied, reports G7c UNEVALUABLE and raises. It does not default to zero and it
does not skip the assertion. Defaulting to zero would print a green G7c computed
from a log nobody read - a gate reporting a boundary it did not inspect, which
is the one thing `verify_iam.py` was written to prevent.

**STATUS CORRECTED 2026-08-22, and the old text had already reached an
artifact.** This paragraph used to end "the live project returns no
`auditConfigs` block at all - Data Access audit logging is not enabled, so the
number does not exist to be read", and `_holdout_finding` said the same thing in
a string that `scripts/probe-g7-g8.py` prints into the G7/G8 proof file. Both
halves are now false:

  * Data Access logging IS enabled. `gcloud projects get-iam-policy
    crucible-hack-2026 --format=json` carries an `auditConfigs` entry for
    `storage.googleapis.com` with `logType: DATA_READ`, applied 2026-08-22.
  * The counter EXISTS: `infra/holdout_touch.py`, wired in
    `scripts/probe-g7-g8.py`. It queries `gcloud logging read` over the sealed
    bucket and refuses to return 0 for any reason other than "nothing read the
    holdout in this window" - a canary query over the whole attestable window
    must match at least one entry before any count is trusted, so a misspelled
    bucket is UNEVALUABLE rather than a clean seal.

What has NOT changed: the log is not retroactive. It attests from
`holdout_touch.ATTESTATION_FLOOR_UTC` forward and says nothing about the seal's
earlier lifetime. Enabling the audit config was a MUTATING project-level change
and was made by the coordinator, not by this module.

G7c NOW HAS TWO FAILURE SHAPES AND THEY ARE NOT THE SAME FINDING
------------------------------------------------------------------
`holdout_touch.HoldoutTouchInvalid` means the instrument WORKED and caught
something: a granted read of the sealed holdout by a principal outside the
permitted set. `measurement-spec.md`:946 - "Any read from another SA ... marks
the run INVALID." That is a FAIL carrying `invalidates`, not an UNEVALUABLE.
Everything else the counter raises is UNEVALUABLE: the instrument declined to
guess. Both route to RUN INVALID, and filing them as one status would throw away
the interesting half - the same shape as `ALLOW`/`allow`, one level up.

WHAT IS STUB-ONLY IN THE TESTS, STATED HERE TOO
------------------------------------------------------------------
`GcsBlobIO` has NEVER RUN AGAINST GCS from this lane - writing an object is a
cloud mutation and this lane is read-only by contract. Its create-only
precondition (`if_generation_match=0`), its 412-benign-duplicate handling, and
its generation-pinned read-back are written from `data-spec.md` 3.1/3.2 and are
UNVERIFIED. `local_blob_io` is the fully-exercised path. A fix that only holds
where the test double is looser than the real API is not a fix; that is why the
two are separated and labelled rather than blended into one "storage backend"
that tests green and has never been called.
"""

import subprocess
import time

from infra import holdout_touch as ht
from infra import verify_iam
from ..canon import canonicalize
from ..gate import PromotionError, object_name, promote

# --------------------------------------------------------------------------
# Outcomes. Two of the three cannot travel through the conductor's bool.
# --------------------------------------------------------------------------


class GateRunInvalid(RuntimeError):
    """`failure_mode: RUN_INVALID`. The instrument is untrustworthy.

    NOT a rejection. `gate_rule.v1.yaml`: "INVALID IS NOT FAILED. FAILED means
    the system under test behaved badly, and that is a measurement - publish it.
    INVALID means there is no measurement."
    """

    def __init__(self, findings, detail=""):
        self.findings = list(findings)
        self.detail = detail
        lines = ["%s %s: %s" % (f["status"], f["gate"], f["check"])
                 + (" -- " + f["detail"] if f["detail"] else "")
                 for f in self.findings]
        super().__init__(
            "RUN INVALID. No number from this run may be reported, including "
            "the ones that look good.%s\n  %s"
            % (("  " + detail) if detail else "", "\n  ".join(lines)))


class GateHalt(RuntimeError):
    """`data-spec.md` 3.2. A promotion assertion that failed its retries, a
    lineage break, or a policy-id collision. A human decides; the next attack
    round does not fire. An automatic resume past a failed assertion is exactly
    the fabrication the assertion exists to prevent."""

    def __init__(self, reason_code, detail):
        self.reason_code = reason_code
        self.detail = detail
        super().__init__("%s: %s" % (reason_code, detail))


PASS, FAIL, UNEVALUABLE = "PASS", "FAIL", "UNEVALUABLE"

# `contracts/gate_rule.v1.yaml` G8 `failure_text`, quoted exactly once.
G8_FAILURE_TEXT = "the separation was never real"


def finding(gate, check, status, detail="", invalidates=False,
            failure_text=""):
    """`invalidates` is carried EXPLICITLY, per finding, and is never inferred
    from the gate id.

    The first version of this file decided RUN INVALID by testing whether the
    gate id started with "G8". That is prefix-matching on an identifier to
    recover a semantic, and it got two cases wrong immediately:

      * **G7b2** is an assertion of BOTH gates. `gate_rule.v1.yaml` G8 lists
        "no CRUCIBLE service account holds a project-level BASIC role # 10a,
        same as G7b2", and `measurement-spec.md`:886 says it is "required here
        for the identical reason" - a basic role makes the Armorer a
        projectEditor on the POLICIES bucket, handing the author of a candidate
        the ability to promote it. Filed under a G7 id, it would have been
        scored a rejection.
      * **G7c** above its expected value: "Any read from another SA, or any
        count above 2, marks the run INVALID" (`measurement-spec.md`:946).

    Both are RUN INVALID and neither is spelled "G8". Two spellings of one
    value is how `ALLOW`/`allow` and `outcome`/`target_fault` both happened;
    this is the same shape one level up, so the semantic is a field.
    """
    return {"gate": gate, "check": check, "status": status, "detail": detail,
            "invalidates": bool(invalidates), "failure_text": failure_text}


def _from_predicate(gate, check, problem, invalidates=False, failure_text=""):
    """A `verify_iam` predicate returns None for OK, or a string naming the
    problem. UNEVALUABLE is carried in that string by the predicates that can
    detect it (`check_ubla_and_pap`, `check_versioning_on`), and is kept
    distinct from FAIL here because G7's contract treats "unevaluable" as RUN
    INVALID even where a plain failure would only REJECT."""
    if problem is None:
        return finding(gate, check, PASS, invalidates=invalidates,
                       failure_text=failure_text)
    status = UNEVALUABLE if "UNEVALUABLE" in problem else FAIL
    return finding(gate, check, status, problem, invalidates=invalidates,
                   failure_text=failure_text)


# --------------------------------------------------------------------------
# Names. Sourced, never retyped.
# --------------------------------------------------------------------------

_ENV_CACHE = {}


def gcp_env(repo_root):
    """`scripts/gcp-env.sh`, read once per root through the ONE reader that
    already exists (`verify_iam.load_env`, which asks bash to source the file so
    there is exactly one parser of it as well as one copy of it)."""
    key = str(repo_root)
    if key not in _ENV_CACHE:
        _ENV_CACHE[key] = verify_iam.load_env(key)
    return _ENV_CACHE[key]


# `crucible.gate.promote` refuses any `promoted_by` that is not this literal.
# That literal and `scripts/gcp-env.sh`'s `SA_GATE` are two spellings of one
# fact, which is the shape this repo has been bitten by twice. They are not
# merged here (promote.py belongs to L1); they are ASSERTED EQUAL at
# construction, which converts a silent divergence into a loud one.
PROMOTER_EXPECTED_BY_PROMOTE_PY = "crucible-gate"


def promoter_identity(repo_root):
    """The one identity permitted to promote. Read from `gcp-env.sh`.

    Raises if it is the Armorer, if it is empty, or if it disagrees with the
    literal `crucible/gate/promote.py` enforces. THE IDENTITY THAT AUTHORS A
    CANDIDATE IS NOT THE IDENTITY THAT PROMOTES IT: the promoter is
    `crucible-gate`, never `sa-warden`, and never `crucible-armorer`.
    """
    env = gcp_env(repo_root)
    gate = (env.get("SA_GATE") or "").strip()
    armorer = (env.get("SA_ARMORER") or "").strip()
    if not gate:
        raise GateRunInvalid(
            [finding("G8", "promoter identity", UNEVALUABLE,
                     "scripts/gcp-env.sh defines no SA_GATE. The gate cannot "
                     "name its own promoter, so nothing here is evaluable.")])
    if armorer and gate == armorer:
        raise GateRunInvalid(
            [finding("G8", "promoter identity", FAIL,
                     "SA_GATE and SA_ARMORER are the same identity (%r). "
                     "G8's own failure text applies: the separation was never "
                     "real." % gate)])
    if gate != PROMOTER_EXPECTED_BY_PROMOTE_PY:
        raise GateRunInvalid(
            [finding("G8", "promoter identity", UNEVALUABLE,
                     "scripts/gcp-env.sh SA_GATE is %r but crucible/gate/"
                     "promote.py enforces %r. Two spellings of one fact have "
                     "diverged; which one the IAM binding was made against is "
                     "no longer knowable from the repo."
                     % (gate, PROMOTER_EXPECTED_BY_PROMOTE_PY))])
    return gate


# --------------------------------------------------------------------------
# G7b / G7b2 / G8 - the IAM assertions, over live policy documents.
# --------------------------------------------------------------------------

def iam_findings(env, fetch=None):
    """Every IAM assertion G7 and G8 make, as a findings list.

    `fetch(args, what) -> dict` is injected so the whole thing is drivable
    offline. A FETCH FAILURE IS A FINDING, never an empty policy: an empty
    policy passes every "holds nothing" predicate, so swallowing a fetch error
    would turn a broken gate into a clean boundary. `verify_iam.gcloud_json`
    already raises rather than returning `{}` for the same reason.
    """
    fetch = fetch or verify_iam.gcloud_json
    project = env["CRUCIBLE_PROJECT"]

    def sa(name):
        return "serviceAccount:%s@%s.iam.gserviceaccount.com" % (name, project)

    all_sas = [sa(n) for n in env["CRUCIBLE_ALL_SAS"].split()]
    gate, armorer, red = sa(env["SA_GATE"]), sa(env["SA_ARMORER"]), sa(env["SA_RED"])
    policies = env["CRUCIBLE_POLICIES_BUCKET"]
    sealed = env["CRUCIBLE_SEALED_BUCKET"]

    out = []
    try:
        proj_pol = fetch(["gcloud", "projects", "get-iam-policy", project,
                          "--format=json"], "project IAM policy")
        pol_pol = fetch(["gcloud", "storage", "buckets", "get-iam-policy",
                         policies, "--format=json"], policies)
        sea_pol = fetch(["gcloud", "storage", "buckets", "get-iam-policy",
                         sealed, "--format=json"], sealed)
        pol_meta = fetch(["gcloud", "storage", "buckets", "describe", policies,
                          "--format=json"], policies)
        sea_meta = fetch(["gcloud", "storage", "buckets", "describe", sealed,
                          "--format=json"], sealed)
    except Exception as e:                                  # noqa: BLE001
        return [finding("G7/G8", "fetch live IAM and bucket metadata",
                        UNEVALUABLE,
                        "%s. This gate did not inspect the boundary and must "
                        "not be read as a pass." % e)]

    # G8 assertions: failure_mode RUN_INVALID, so `invalidates=True` on all.
    out.append(_from_predicate(
        "G8", "crucible-gate holds objectCreator on %s" % policies,
        verify_iam.check_gate_can_create(pol_pol, gate), invalidates=True, failure_text=G8_FAILURE_TEXT))
    out.append(_from_predicate(
        "G8", "crucible-gate holds NO overwrite/delete role on %s" % policies,
        verify_iam.check_gate_cannot_overwrite(pol_pol, gate), invalidates=True, failure_text=G8_FAILURE_TEXT))
    out.append(_from_predicate(
        "G8", "crucible-armorer holds NO storage role on %s" % policies,
        verify_iam.check_member_absent(pol_pol, armorer, policies),
        invalidates=True, failure_text=G8_FAILURE_TEXT))
    out.append(_from_predicate(
        "G8", "policies retention EXISTS and is NOT locked",
        verify_iam.check_retention_present_and_unlocked(pol_meta, policies),
        invalidates=True, failure_text=G8_FAILURE_TEXT))
    out.append(_from_predicate(
        "G8", "policies object versioning is ON",
        verify_iam.check_versioning_on(pol_meta, policies), invalidates=True, failure_text=G8_FAILURE_TEXT))
    out.append(_from_predicate(
        "G8", "UBLA on and PAP enforced: %s" % policies,
        verify_iam.check_ubla_and_pap(pol_meta, policies), invalidates=True, failure_text=G8_FAILURE_TEXT))
    # G7 assertions: failure_mode REJECT, absent_or_unevaluable RUN_INVALID.
    out.append(_from_predicate(
        "G7b", "crucible-armorer holds NOTHING on %s" % sealed,
        verify_iam.check_member_absent(sea_pol, armorer, sealed)))
    out.append(_from_predicate(
        "G7b", "crucible-red holds NOTHING on %s" % sealed,
        verify_iam.check_member_absent(sea_pol, red, sealed)))
    out.append(_from_predicate(
        "G7b", "crucible-armorer holds no project-level storage/bigquery role",
        verify_iam.check_no_storage_or_bq_at_project(proj_pol, armorer)))
    # G7b2 is asserted by BOTH gates, and G8 is the one whose failure mode wins.
    out.append(_from_predicate(
        "G7b2/G8", "no CRUCIBLE identity holds a project-level BASIC role",
        verify_iam.check_no_basic_roles(proj_pol, all_sas), invalidates=True, failure_text=G8_FAILURE_TEXT))
    out.append(_from_predicate(
        "G7", "UBLA on and PAP enforced: %s" % sealed,
        verify_iam.check_ubla_and_pap(sea_meta, sealed)))
    return out


# --------------------------------------------------------------------------
# G7a - the impersonation probe. READ-ONLY: `objects list`, never a write.
# --------------------------------------------------------------------------

# A refusal at the IMPERSONATION layer is not a result about the bucket. The
# probe never became that identity, so the run says NOTHING about its access.
# `infra/prove-armorer-403.sh` learned this the hard way: its first version
# matched on the word "permission", and "Permission
# 'iam.serviceAccounts.getAccessToken' denied" matched it, scoring a failure to
# even assume the identity as PASS-refused. Two convincing green lines about a
# boundary that had not been tested.
_IMPERSONATION_LAYER = ("failed to impersonate",
                        "iam.serviceaccounts.getaccesstoken")

# A denial must name the STORAGE permission. Anything broader credits a refusal
# from the wrong layer.
_STORAGE_LAYER = ("storage.objects.list", "403")


def classify_probe(expect, returncode, output):
    """Pure. `expect` is "allow" or "deny". Returns (status, detail).

    Driven to red and green by `tests/test_real_gate.py`; no I/O, so every
    branch is reachable offline.
    """
    low = (output or "").lower()
    if any(m in low for m in _IMPERSONATION_LAYER):
        return (UNEVALUABLE,
                "refused at the IMPERSONATION layer, not the storage layer. "
                "The probe never became this identity, so this result says "
                "NOTHING about the bucket. An unevaluable G7 assertion is "
                "RUN INVALID, not a pass.")
    if expect == "allow":
        if returncode == 0 and output.strip():
            return (PASS, "the positive control read the prefix, so the path "
                          "is real and the 403s below mean something")
        if returncode == 0:
            return (UNEVALUABLE,
                    "the positive control exited 0 and listed NOTHING. A "
                    "misspelled prefix looks exactly like this. Every denial "
                    "in this probe is uninformative.")
        # UNEVALUABLE, not FAIL. A dead positive control does not mean the
        # boundary is broken - it means this probe measured nothing, and G7's
        # contract sends `absent_or_unevaluable` to RUN INVALID precisely so a
        # probe that proved nothing cannot be scored as a probe that passed.
        return (UNEVALUABLE,
                "THE POSITIVE CONTROL DID NOT READ, so every denial in this "
                "probe is uninformative: a misspelled bucket, a deleted bucket, "
                "and a project the caller cannot see all return 403, because "
                "GCS refuses to distinguish 'you may not' from 'it is not "
                "there'.")
    if returncode == 0:
        return (FAIL, "THE READ SUCCEEDED. The boundary does not exist.")
    if any(m in low for m in _STORAGE_LAYER):
        return (PASS, "refused at the storage layer")
    return (UNEVALUABLE,
            "failed for a reason that is not a storage permission denial, so "
            "the storage boundary was not exercised")


def _probe_argv(env, sa_name):
    """The read-only G7a command.

    NOTE, and this is a real defect in the contract rather than a preference:
    `contracts/gate_rule.v1.yaml` G7a and `measurement-spec.md`:836 both write
    the probe as

        gcloud storage objects list gs://crucible-sealed-$SUFFIX/families/

    Run against the live bucket on 2026-08-22 by the PROJECT OWNER, that exact
    form exits 0 and prints nothing, while `gcloud storage ls -r` on the same
    prefix lists `families/_probe/canary.txt`. A trailing-slash prefix is not a
    match pattern to `objects list`. So the specified command CANNOT SUCCEED for
    a permitted identity, which means it has no positive control - and a 403
    with no positive control is the uninformative shape
    `infra/prove-armorer-403.sh` exists to refuse. The `**` suffix here is the
    form that actually lists, and it is what makes the positive control possible.
    """
    return ["gcloud", "storage", "objects", "list",
            "%s/families/**" % env["CRUCIBLE_SEALED_BUCKET"],
            "--impersonate-service-account=%s@%s.iam.gserviceaccount.com"
            % (sa_name, env["CRUCIBLE_PROJECT"]),
            "--format=value(name)"]


def seal_probe_findings(env, run=None):
    """G7a for all four identities, positive control first.

    The positive control is the half that makes the negatives mean something.
    """
    run = run or _run_capture
    plan = [(env["SA_SEALED_EVAL"], "allow"),
            (env["SA_ARMORER"], "deny"),
            (env["SA_RED"], "deny"),
            (env["SA_CORONER"], "deny")]
    out = []
    for sa_name, expect in plan:
        try:
            rc, text = run(_probe_argv(env, sa_name))
        except Exception as e:                              # noqa: BLE001
            out.append(finding("G7a", "impersonation probe: %s (%s)"
                               % (sa_name, expect), UNEVALUABLE,
                               "the probe could not be executed: %s" % e))
            continue
        status, detail = classify_probe(expect, rc, text)
        out.append(finding("G7a", "impersonation probe: %s (%s)"
                           % (sa_name, expect), status, detail))
    return out


def _run_capture(argv):
    exe = verify_iam._gcloud_exe()                          # noqa: SLF001
    if argv and argv[0] == "gcloud":
        argv = [exe] + list(argv[1:])
    p = subprocess.run(argv, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


# --------------------------------------------------------------------------
# Storage back ends for `crucible.gate.promote`'s injected blob_writer/reader.
# --------------------------------------------------------------------------

def local_blob_io(root):
    """Filesystem. THE FULLY EXERCISED PATH. Used by the tests and usable for a
    dry run; the bytes really round-trip through a file, so `promote`'s
    recompute-from-bytes assertion is doing real work rather than reading back a
    dict it still holds a reference to."""
    import pathlib
    root = pathlib.Path(root)

    def writer(name, data):
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def reader(name):
        return (root / name).read_bytes()

    return writer, reader


class GcsBlobIO:
    """**UNVERIFIED AGAINST LIVE GCS.** Writing an object is a cloud mutation and
    the lane that wrote this module is read-only by contract, so every line below
    is written from `data-spec.md` 3.1/3.2 and has never been executed against
    the real API. It is kept separate from `local_blob_io` and labelled rather
    than blended into one backend, because a backend that tests green through a
    double and has never been called is the exact shape that passes a suite and
    fails on the first live call.

    What it implements, from data-spec 3.1:
      step 3  create-only precondition `if_generation_match=0`
      step 4  settle before reading, so the read is not the write's own ack
      step 5  read back PINNED TO THE GENERATION step 3 returned
      3.2     a 412 whose existing object carries the same name is a BENIGN
              DUPLICATE - the object name contains the content hash, so a
              same-name collision with different bytes is impossible by
              construction and the read-back decides either way.
    """

    def __init__(self, bucket_uri, settle_seconds=0.25, client=None,
                 sleep=None):
        self.bucket_name = bucket_uri.replace("gs://", "").rstrip("/")
        self.settle_seconds = settle_seconds
        self._client = client
        self._sleep = sleep or time.sleep
        self.generations = {}

    def _bucket(self):
        if self._client is None:
            try:
                from google.cloud import storage
            except ImportError as e:
                raise GateRunInvalid(
                    [finding("G8", "policies bucket write path", UNEVALUABLE,
                             "google-cloud-storage is not importable (%s), so "
                             "no policy version can be created and G8 cannot "
                             "be exercised. NOTE: this package is not pinned "
                             "in requirements.txt." % e)]) from None
            self._client = storage.Client()
        return self._client.bucket(self.bucket_name)

    def writer(self, name, data):
        blob = self._bucket().blob(name)
        try:
            blob.upload_from_string(data, content_type="application/json",
                                    if_generation_match=0)
        except Exception as e:                              # noqa: BLE001
            # 412 == the object already exists. Its name carries the hash of its
            # own contents, so this is a benign idempotent retry. Anything else
            # re-raises: a write failure must never be swallowed into a
            # read-back that then reports a boundary it did not cross.
            if "412" not in str(e) and "PreconditionFailed" not in type(e).__name__:
                raise
            blob = self._bucket().get_blob(name)
        self.generations[name] = getattr(blob, "generation", None)
        self._sleep(self.settle_seconds)

    def reader(self, name):
        gen = self.generations.get(name)
        blob = self._bucket().blob(name, generation=gen)
        return blob.download_as_bytes(if_generation_match=gen)


# --------------------------------------------------------------------------
# The drop-in.
# --------------------------------------------------------------------------

class RealGate:
    """Callable with the gate stand-in's exact signature:

        gate(candidate, record) -> bool          # True == PROMOTE

    Same shape as `promote=lambda c, r: True`, so it drops straight into
    `Conductor(..., promote=gate)`. What changes is that it looks at something.
    """

    def __init__(self, ledger, run_id, blob_writer, blob_reader, repo_root,
                 holdout_touch=None, holdout_expected=2, iam_fetch=None,
                 probe_run=None, clock=None, sleep=None, skip_cloud=False):
        """`holdout_touch` is a zero-arg callable returning the current
        `holdout_touch_count`. There is NO DEFAULT: see the module docstring.

        `skip_cloud=True` runs the promotion write path with G7/G8 recorded as
        UNEVALUABLE and RAISES anyway. It exists only so a caller can obtain the
        findings list without a network; it never returns a promotion.
        """
        self.ledger = ledger
        self.run_id = run_id
        self.blob_writer = blob_writer
        self.blob_reader = blob_reader
        self.repo_root = str(repo_root)
        self.holdout_touch = holdout_touch
        self.holdout_expected = holdout_expected
        self.iam_fetch = iam_fetch
        self.probe_run = probe_run
        self.clock = clock or _utc_now
        self.sleep = sleep or time.sleep
        self.skip_cloud = skip_cloud
        self.reports = []
        # Fail at CONSTRUCTION, not at the first write. A gate built with the
        # wrong promoter is not a gate that rejects later; it is a gate that
        # should never have been built.
        self.promoted_by = promoter_identity(self.repo_root)
        self.env = gcp_env(self.repo_root)

    # -- the gates ---------------------------------------------------------

    def preflight(self):
        """G7 + G8, every assertion, as one findings list."""
        if self.skip_cloud:
            return [finding("G7/G8", "live IAM and seal assertions", UNEVALUABLE,
                            "skip_cloud=True. Nothing was inspected.")]
        out = list(iam_findings(self.env, fetch=self.iam_fetch))
        out.extend(seal_probe_findings(self.env, run=self.probe_run))
        out.append(self._holdout_finding())
        return out

    def _holdout_finding(self):
        """G7c. Absent => UNEVALUABLE => RUN INVALID. Never defaulted to 0."""
        check = "holdout_touch_count == %d" % self.holdout_expected
        if self.holdout_touch is None:
            return finding(
                "G7c", check, UNEVALUABLE,
                "no holdout_touch counter was injected. The count is derived "
                "from Cloud Audit Logs DATA ACCESS reads on the sealed holdout "
                "(measurement-spec.md:946), and infra/holdout_touch.py now "
                "reads them - but NOTHING WAS WIRED IN HERE, so this gate did "
                "not look. Defaulting it to 0 would print a green G7c computed "
                "from a log nobody queried.")
        try:
            count = int(self.holdout_touch())
        except ht.HoldoutTouchInvalid as e:
            # NOT unevaluable. The counter worked and caught a granted read of
            # the sealed holdout by an identity outside the permitted set.
            # measurement-spec.md:946 - "Any read from another SA ... marks the
            # run INVALID." That is a measurement, so it is a FAIL that
            # invalidates, and it must not be filed as "we could not tell".
            return finding("G7c", check, FAIL, str(e), invalidates=True)
        except Exception as e:                              # noqa: BLE001
            return finding("G7c", check, UNEVALUABLE,
                           "the counter raised: %s" % e)
        if count == self.holdout_expected:
            return finding("G7c", check, PASS)
        # INVALID, not REJECT: `measurement-spec.md`:946 - "Any read from
        # another SA, or any count above 2, marks the run INVALID."
        return finding("G7c", check, FAIL,
                       "holdout_touch_count is %d, expected %d. Any read from "
                       "another SA, or any count above the expected value, "
                       "marks the run INVALID." % (count, self.holdout_expected),
                       invalidates=True)

    # -- the call ----------------------------------------------------------

    def __call__(self, candidate, record):
        findings = self.preflight()
        report = {"round_index": getattr(record, "round_index", None),
                  "findings": findings}
        self.reports.append(report)

        bad = [f for f in findings if f["status"] != PASS]
        # G7's contract: `failure_mode: REJECT`, `absent_or_unevaluable:
        # RUN_INVALID`. So an UNEVALUABLE anything voids the run, as does any
        # finding carrying `invalidates` - which is decided where the assertion
        # is built, never inferred from the gate id here.
        invalidating = [f for f in bad
                        if f["status"] == UNEVALUABLE or f["invalidates"]]
        if invalidating:
            report["decision"] = "RUN_INVALID"
            texts = [f["failure_text"] for f in invalidating if f["failure_text"]]
            raise GateRunInvalid(bad, texts[0] if texts else "")
        if bad:
            report["decision"] = "REJECT"
            return False

        result = self._promote_with_assertion(candidate, record)
        report["decision"] = "PROMOTE"
        report["promotion"] = result
        return True

    def _promote_with_assertion(self, candidate, record):
        """`crucible.gate.promote` plus data-spec 3.2's retry ladder.

        The read-back lives inside `promote` and recomputes the hash FROM THE
        BYTES; this method only owns what to do when that assertion fails.
        Retrying is safe because `promote` appends to the ledger only after the
        assertion holds - there is no partial state to clean up.
        """
        payload = candidate.get("hashed_payload")
        if payload is None:
            raise GateHalt("PROMOTION_ASSERT_FAILED",
                           "the candidate carries no hashed_payload")
        manifest_hash = (getattr(record, "hashes", None) or {}).get("manifest_hash")
        if not manifest_hash:
            raise GateRunInvalid(
                [finding("G1c", "manifest_hash present on the round record",
                         UNEVALUABLE,
                         "ruling 20: a policy version written without a "
                         "manifest_hash cannot say which manifest its rules "
                         "were learned against.")])

        payload_bytes = canonicalize(payload)
        backoff = (0.25, 1.0, 4.0)
        last = None
        for attempt, wait in enumerate(backoff, start=1):
            try:
                return promote(self.ledger, self.run_id, payload_bytes,
                               self.promoted_by, self.clock(), manifest_hash,
                               self.blob_writer, self.blob_reader)
            except PromotionError as e:
                if e.code in ("E_WRONG_PROMOTER", "E_NOT_CANONICALIZABLE",
                              "E_CONVERGED", "E_NAME_HASH_MISMATCH"):
                    # None of these are transient. E_CONVERGED is the
                    # convergence signal, not a fault; E_WRONG_PROMOTER is G8
                    # tripping in code. Retrying any of them three times just
                    # produces the same answer three times.
                    raise
                last = e
                if attempt < len(backoff):
                    self.sleep(wait)
        raise GateHalt(
            "PROMOTION_ASSERT_FAILED",
            "%s after %d attempts. HALT semantics are absolute: the next attack "
            "round does not fire, and an automatic resume past a failed "
            "assertion is exactly the fabrication the assertion exists to "
            "prevent." % (last, len(backoff)))


def _utc_now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def build_real_gate(**kwargs):
    """Factory, matching `real_target.build_real_target`'s shape. Returns the
    callable `(candidate, record) -> bool` the conductor wants."""
    return RealGate(**kwargs)


def render(findings):
    """One line per assertion, for the campaign banner and the evidence bundle."""
    return "\n".join(
        "  %-11s %-5s %s%s" % (f["status"], f["gate"], f["check"],
                               ("\n              " + f["detail"]) if f["detail"] else "")
        for f in findings)


__all__ = ["RealGate", "build_real_gate", "GateRunInvalid", "GateHalt",
           "GcsBlobIO", "local_blob_io", "iam_findings", "seal_probe_findings",
           "classify_probe", "promoter_identity", "gcp_env", "render",
           "object_name", "PASS", "FAIL", "UNEVALUABLE", "finding"]
