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
  G4   attack reduction - `crucible.conductor.g4`, paired replay of the run's
       recorded attack episodes at policy@vN and at the candidate. ADDED
       2026-08-26; see the block below for what its absence had been costing.
  CLOSURE  originating-breach closure - `crucible.conductor.closure`. Does this
       candidate close THE BREACH IT WAS WRITTEN FOR, on that breach's own
       recorded trace. **NOT a cheaper G4 and not implied by it**: the measured
       `b` histogram is bimodal, so a patch can close its originating breach
       without reaching `b >= 3` (G4 rejects it) and can reach `b >= 3` on other
       episodes while doing nothing to the trace that provoked it (G4 promotes
       it). Two questions, two criteria, two modes. It is NOT a lettered gate in
       `contracts/gate_rule.v1.yaml`, which is hash-locked and says nothing
       about it; it is filed under the id `CLOSURE` rather than borrowing a
       G-number the frozen contract has not assigned.

NOT EVALUATED HERE, and each already has an owner:
  G1   calibration + oracle freeze -> `crucible.warden.run_known_bad_suite`,
       `crucible.tripwire.known_bad`. Evaluated at round start, not at the gate.
  G3   benign floor -> the `benign_gate` hook. `Conductor.run_round` already
       computes `passed` from it and only calls this function when it holds.
  G5   rule hygiene -> `crucible.dsl.validator`, before a candidate exists.
  G6   provenance -> the Armorer's citation of this round's autopsy.
Bolting any of them on here would put a second evaluator behind the same bool.

G4 IS THE ONE THAT MOVED, AND WHY IT BELONGS HERE RATHER THAN IN THE CONDUCTOR
------------------------------------------------------------------
This list used to read "G4 attack reduction -> the conductor's paired scoring
across rounds". No such scoring existed. `scripts/gate-census.py`:103-106 has
filed G4 as ABSENT with the words "Nothing computes b or c" for as long as the
census has run, and a grep for `newly_blocked` returned that census line and
nothing else. **A criterion whose `failure_mode` is REJECT had never been
evaluated once**, so `contracts/gate_rule.v1.yaml`'s promotion rule and the
running promotion rule were two different rules.

WHAT THAT COST, MEASURED, NOT ARGUED. `docs/design/gate-noop-measurement-
2026-08-25.md` section 4: of 31 promoted rules across the 14 bundles the
shipped offline reader accepts, **18 do not close the breach they were written
for**. A rule that fires on nothing cannot fail a benign floor - it is the
EASIEST candidate to promote - so the loop's only gradient pointed straight at
it. G4 is the check that asks the other question.

It goes here and not in the conductor because it is a PROMOTION CONDITION. The
conductor's job is to hand the gate a candidate and read a decision; a
promotion condition evaluated in the caller is a condition the gate cannot be
said to have applied. `crucible.conductor.g4` holds the arithmetic and this
file holds the decision, the same split as `infra.verify_iam` and the IAM
findings above.

G4 UNEVALUABLE REJECTS. IT DOES NOT INVALIDATE THE RUN, AND IT DOES NOT PASS.
The route is read off the contract rather than invented: G7 declares
`absent_or_unevaluable: RUN_INVALID` explicitly and G4 declares no such key,
declaring only `failure_mode: REJECT`. So a candidate whose attack reduction
could not be measured is not promoted and the run stays valid. Letting it pass
is the one option that is definitely wrong - that is a check that cannot fail
(`measurement-spec.md`:813), which is what G4 already was.

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

import os
import subprocess
import time

from infra import holdout_touch as ht
from infra import verify_iam
from ..canon import canonicalize
from ..gate import PromotionError, object_name, promote
from ..tripwire.objective_set import load_objective_set
from . import closure as closuremod
from . import g4 as g4mod

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

RECORDED = "RECORDED"
"""THE CRITERION WAS SCORED AND WAS NOT ENFORCED. A fourth status, and the only
one that is neither a pass nor a rejection.

It exists because the alternative is to spell "scored but not binding" as PASS,
and a PASS that is not a pass is exactly the conflation that produced
`ALLOW`/`allow` and `outcome`/`target_fault`. A reader of a findings list - or
of the banner, or of the bundle six weeks from now - must be able to see that
enforcement did not happen without knowing which flags the run was started with.

A RECORDED finding carries `would_have`, the status the same measurement would
have produced under ENFORCING. So the counterfactual is in the artifact, not
recoverable only by re-running."""

# `contracts/gate_rule.v1.yaml` G8 `failure_text`, quoted exactly once.
G8_FAILURE_TEXT = "the separation was never real"


def finding(gate, check, status, detail="", invalidates=False,
            failure_text="", rejects_if_unevaluable=False, would_have=None):
    """`invalidates` is carried EXPLICITLY, per finding, and is never inferred
    from the gate id.

    `rejects_if_unevaluable` is the same discipline applied to the OTHER
    default. UNEVALUABLE routes to RUN INVALID here because G7 says so in
    `absent_or_unevaluable: RUN_INVALID`; G4 declares no such key and only
    `failure_mode: REJECT`, so an unmeasurable G4 is a rejection rather than a
    voided run. Carrying that as a per-finding field keeps the decision where
    the contract can be read beside it, instead of teaching `__call__` a second
    list of gate ids.

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
    out = {"gate": gate, "check": check, "status": status, "detail": detail,
           "invalidates": bool(invalidates), "failure_text": failure_text,
           "rejects_if_unevaluable": bool(rejects_if_unevaluable)}
    if would_have is not None:
        # ONLY ON A `RECORDED` FINDING. Writing it unconditionally would put a
        # "what enforcement would have said" field on findings that WERE
        # enforced, where it is either a tautology or a second, drifting copy of
        # `status`.
        out["would_have"] = would_have
    return out


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
    # THE OUTPUT TRAVELS WITH THE VERDICT. Run 10 of the 2026-08-25 batch put
    # all four arms in this branch and the finding named no cause, because this
    # detail string was fixed text and the probe's own output was discarded
    # here. A finding that reports nothing is a diagnostic dead end, which is
    # the same defect as a check that cannot fail wearing different clothes.
    tail = " ".join((output or "").split())[:300] or "(no output on either stream)"
    return (UNEVALUABLE,
            "failed for a reason that is not a storage permission denial, so "
            "the storage boundary was not exercised. exit %s; output: %s"
            % (returncode, tail))


# THE PROBE PREFIX. It is DELIBERATELY NOT the prefix the corpus lives under,
# and re-unifying the two would break the positive control. Read this before
# "tidying" it.
#
# Eric's ruling on `docs/NEEDS-ERIC.md` item 12, executed 2026-08-22: the canary
# was MOVED, not excluded.
#
#     was:  gs://crucible-sealed-x7/families/_probe/canary.txt
#     now:  gs://crucible-sealed-x7/_probe/canary.txt
#     gs://crucible-sealed-x7/families/  is now EMPTY
#
# An exclusion would have been a permanent named hole, and it would mean THE
# GATE DECLARES WHICH READS DO NOT COUNT - self-certification, one layer over
# from the thing G8 exists to prevent. Relocation removes the need for the rule.
#
# The consequence for this file is not cosmetic. `families/**` now matches ZERO
# objects, so the permitted identity's probe would exit 0 having listed nothing
# - and `classify_probe` files that as UNEVALUABLE, which is RUN INVALID. The
# positive control would have stopped proving anything while still looking
# green in three of its four lines.
#
# WHY ONE PREFIX FOR ALL FOUR ARMS, INCLUDING THE DENIALS. `crucible-sealed-eval`
# holds `roles/storage.objectViewer` BUCKET-WIDE with no IAM condition, and
# uniform bucket-level access is ON, so there are no per-prefix grants to
# distinguish: a `storage.objects.list` denial on any prefix of this bucket is
# the same denial. Probing the empty `families/**` for the deny arms would add
# no evidence and would put the gate's own probe back inside the corpus
# namespace for no gain.
_PROBE_PREFIX = "_probe/**"


def _probe_argv(env, sa_name):
    """The read-only G7a command.

    NOTE, and this is a real defect in the contract rather than a preference:
    `contracts/gate_rule.v1.yaml` G7a and `measurement-spec.md`:836 both write
    the probe as

        gcloud storage objects list gs://crucible-sealed-$SUFFIX/families/

    Run against the live bucket on 2026-08-22 by the PROJECT OWNER, that exact
    form exits 0 and prints nothing, while `gcloud storage ls -r` on the same
    prefix listed the canary. A trailing-slash prefix is not a match pattern to
    `objects list`. So the specified command CANNOT SUCCEED for a permitted
    identity, which means it has no positive control - and a 403 with no
    positive control is the uninformative shape `infra/prove-armorer-403.sh`
    exists to refuse. The `**` suffix here is the form that actually lists, and
    it is what makes the positive control possible.

    The PREFIX moved 2026-08-22 for a second and separate reason: see
    `_PROBE_PREFIX` above. Two different things are wrong with the contract's
    one-line form and they are fixed independently.
    """
    return ["gcloud", "storage", "objects", "list",
            "%s/%s" % (env["CRUCIBLE_SEALED_BUCKET"], _PROBE_PREFIX),
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


def is_classifiable(returncode, output):
    """Did this invocation produce an ANSWER, as opposed to nothing at all?

    An answer is semantic and must be returned unchanged on the first attempt:

      rc == 0                      the read succeeded. PASS for the allow arm,
                                   FAIL for a deny arm. Both are results.
      _IMPERSONATION_LAYER matched the identity was genuinely refused at IAM.
                                   UNEVALUABLE, and a real one.
      _STORAGE_LAYER matched       a real 403 from GCS. PASS for a deny arm.

    Anything else is a non-zero exit with nothing to classify, which is what
    run 10 of the 2026-08-25 batch produced on all four arms at once: an empty
    stderr, which a denial never has. That is the only shape worth asking again.
    """
    if returncode == 0:
        return True
    low = (output or "").lower()
    return (any(m in low for m in _IMPERSONATION_LAYER)
            or any(m in low for m in _STORAGE_LAYER))


def _run_capture(argv, runner=None, sleep=None):
    """The G7a probe invocation. RETRIED ONLY WHEN IT ANSWERED NOTHING.

    `57f4e94` gave `verify_iam.gcloud_json` a bounded retry and left this call
    site - the one that failed on all four probe arms simultaneously - a bare
    single-shot `subprocess.run`. It reuses `verify_iam.FETCH_ATTEMPTS` and
    `FETCH_BACKOFF` rather than declaring its own, because three retry policies
    for one decision is three sources of truth.

    **THIS CANNOT LAUNDER A DENIAL INTO A PASS, AND THE GUARD IS THE POINT.**
    `is_classifiable` returns True for every semantic outcome, so a real 403,
    a real impersonation refusal, and a successful read are each returned on
    attempt one and never asked again - the same reason
    `_promote_with_assertion` refuses to retry `E_WRONG_PROMOTER`. Retrying a
    semantic answer produces the same answer three times and only costs time.
    A FAIL is an answer too.

    Exhausting the attempts returns the LAST result with a diagnostic appended,
    so `classify_probe` files it UNEVALUABLE - RUN_INVALID - carrying the exit
    code instead of the empty string run 10 reported. The appended text
    deliberately contains no substring `classify_probe` keys on, and
    `tests/test_fetch_retry.py` asserts that it still classifies UNEVALUABLE.
    """
    if runner is None:
        exe = verify_iam._gcloud_exe()                      # noqa: SLF001
        if argv and argv[0] == "gcloud":
            argv = [exe] + list(argv[1:])

        def runner(argv_):
            return subprocess.run(argv_, capture_output=True, text=True)
    sleep = sleep or time.sleep
    attempts = verify_iam.FETCH_ATTEMPTS
    backoff = verify_iam.FETCH_BACKOFF
    rc, text = 1, ""
    for attempt in range(1, attempts + 1):
        p = runner(argv)
        rc = p.returncode
        text = (p.stdout or "") + (p.stderr or "")
        if is_classifiable(rc, text):
            return rc, text
        if attempt < attempts:
            sleep(backoff[min(attempt - 1, len(backoff) - 1)])
    return rc, text + (
        "\n[crucible] the probe exited %d on all %d attempts and produced "
        "nothing to classify. An exit with no output is a process-level or "
        "transport-level failure, not an API answer: a refusal always writes a "
        "message. Reported as unevaluable, which is RUN INVALID, and NOT as a "
        "boundary that held." % (rc, attempts))


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
    """**EXECUTED AGAINST LIVE GCS SINCE 2026-08-24. UNTESTED, WHICH IS A
    DIFFERENT THING.** Every line below is written from `data-spec.md` 3.1/3.2
    and NO TEST EXERCISES IT; the evidence that it works is live runs, not the
    suite. The policy store has been written by many runs (count is
    verify-on-use: `gcloud storage ls gs://crucible-policies-x7/runs/`).

    **CORRECTED 2026-08-28.** This docstring said the module "has never been
    executed against the real API", and the live run banner said the same
    sentence, and both stayed false for four days while runs wrote objects. A
    caveat that goes stale is worse than no caveat, because it is read as
    current. The honest split is EXECUTION, which happened, against TEST
    COVERAGE, which has not.

    It is kept separate from `local_blob_io` and labelled rather than blended
    into one backend, because a backend that tests green through a double and
    has never been called is the exact shape that passes a suite and fails on
    the first live call. That risk is now retired by execution rather than by
    testing, and the distinction is the point of this paragraph.

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
                 probe_run=None, clock=None, sleep=None, skip_cloud=False,
                 objective_set_path=None, g4_mode=None, g4_record_only_reason="",
                 g4_slice=None, closure_mode=None,
                 closure_record_only_reason=""):
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
        # G4. The path is a parameter so a test can point it at a different
        # Objective Set - a criterion whose subject cannot be varied cannot be
        # shown to fail, which is the same argument `refusal_licence` is a
        # parameter for one file over.
        self.objective_set_path = (
            objective_set_path
            or os.path.join(self.repo_root, "contracts", "objective_set.v1.json"))
        self._objective_set = None
        # Every G4 measurement this gate made, in order, so the bundle can carry
        # b and c without recomputing them.
        self.g4_scores = []
        # THE MODE IS RESOLVED AT CONSTRUCTION, NOT AT THE FIRST CANDIDATE. A
        # gate built with a misspelled mode, or with an unexplained
        # RECORD_ONLY, is not a gate that misbehaves in round three; it is a
        # gate that should never have been built. Same argument as
        # `promoted_by`, which is resolved two lines up for the same reason.
        self.g4_mode, self.g4_record_only_reason = g4mod.resolve_mode(
            g4_mode, g4_record_only_reason)
        # WHICH SLICE b AND c ARE PAIRED OVER. `run` is the default and is the
        # behaviour that shipped: the conductor's accumulated scorable attack
        # episodes. `baseline` is the frozen fifty of
        # `docs/proof/v0-attack-baseline-freeze.json`.
        #
        # RESOLVED AT CONSTRUCTION FOR THE SAME REASON THE MODE IS. A gate built
        # with `baseline` when no baseline exists is not a gate that rejects in
        # round three - it is a gate that should never have been built, and
        # finding that out after six rounds of model spend is finding it out too
        # late. `load_baseline` runs here, once, and every refusal it can raise
        # propagates out of the constructor.
        self.g4_slice = g4mod.DEFAULT_SLICE if g4_slice is None else str(g4_slice)
        if self.g4_slice not in g4mod.SLICES:
            raise g4mod.G4SliceError(
                "%r is not a G4 slice. The slices are %s."
                % (self.g4_slice, ", ".join(g4mod.SLICES)))
        self._g4_baseline = None
        if self.g4_slice == g4mod.SLICE_BASELINE:
            self._g4_baseline = g4mod.load_baseline(
                objective_set=self.objective_set())
        # ORIGINATING-BREACH CLOSURE. Its own mode, resolved at construction for
        # the same reason G4's is, and its own list of measurements for the same
        # reason `g4_scores` exists.
        #
        # A SEPARATE MODE FROM G4'S, DELIBERATELY. They are two criteria and
        # they answer two questions; one switch for both would mean a run that
        # wanted to observe attack reduction without enforcing it also stopped
        # enforcing closure, silently, and the bundle would say `mode:
        # RECORD_ONLY` once for two suppressions. The VOCABULARY is shared -
        # `closure.ENFORCING` is `g4.ENFORCING`, re-exported, never re-declared.
        self.closure_scores = []
        self.closure_mode, self.closure_record_only_reason = \
            closuremod.resolve_mode(closure_mode, closure_record_only_reason)
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

    def objective_set(self):
        """The Objective Set G4 scores through, loaded ONCE per gate.

        One load, for the same reason `real_warden` caches the benign suite and
        `campaign` builds `local_blob_io` exactly once: two loads of the same
        artifact agree today and are a place for them to disagree later.
        """
        if self._objective_set is None:
            self._objective_set = load_objective_set(self.objective_set_path)
        return self._objective_set

    def g4_finding(self, candidate, record):
        """G4, ATTACK REDUCTION. `contracts/gate_rule.v1.yaml`:129-137.

        The arithmetic is `crucible.conductor.g4`; what this method owns is the
        finding and, through it, the route. `scores` is stashed on the record so
        the bundle can print b and c beside the decision rather than recompute
        them - ruling 37.1's lesson, one criterion over: a number with no
        producer is a number nobody can audit afterwards.
        """
        ops = {"gte": ">=", "gt": ">", "eq": "==", "lte": "<=", "lt": "<"}
        check = ("newly_blocked_b %s %d and newly_breached_c %s %d "
                 "over the %s slice"
                 % (ops.get(g4mod.B_OP, g4mod.B_OP), g4mod.B_MIN,
                    ops.get(g4mod.C_OP, g4mod.C_OP), g4mod.C_MAX,
                    self.g4_slice))
        # THE MODE IS STAMPED ON THE RECORD BEFORE ANYTHING IS SCORED, so a
        # round that raises mid-measurement still says which mode was in force.
        record.g4_mode = self.g4_mode
        record.g4_record_only_reason = self.g4_record_only_reason
        # THE SLICE IS STAMPED FOR THE SAME REASON, AND IT TRAVELS WITH b AND c
        # EVERYWHERE THEY GO. `b >= 3` over the run's six episodes and `b >= 3`
        # over the frozen fifty are different demands, and two runs reporting
        # b = 5 measured the same thing only if both slices were the same slice.
        # A denominator whose PROVENANCE is not recorded is the same defect as a
        # threshold printed without its denominator, one level out.
        record.g4_slice = self.g4_slice
        episodes = (self._g4_baseline.slice()
                    if self._g4_baseline is not None
                    else getattr(record, "training_slice", None))
        try:
            scores = g4mod.paired_scores(
                episodes,
                getattr(record, "policy_in_force", None),
                candidate, self.objective_set())
        except g4mod.G4Unevaluable as exc:
            return self._g4_verdict(check, UNEVALUABLE, str(exc))
        passes, detail = g4mod.decide(scores)
        detail = "%s [slice=%s]" % (detail, self.g4_slice)
        record.newly_blocked_b = scores["newly_blocked_b"]
        record.newly_breached_c = scores["newly_breached_c"]
        record.g4_paired_n = scores["n"]
        record.g4_unpairable = len(scores["unpairable"])
        self.g4_scores.append(dict(
            scores, round_index=getattr(record, "round_index", None),
            mode=self.g4_mode, record_only_reason=self.g4_record_only_reason,
            slice=self.g4_slice))
        return self._g4_verdict(check, PASS if passes else FAIL, detail)

    def _g4_verdict(self, check, status, detail):
        """The ONE place the mode turns a measurement into a finding.

        THE MEASUREMENT IS IDENTICAL IN BOTH MODES and is already finished by
        the time this is called: `paired_scores` has no opinion about
        enforcement, and `decide` reads the contract's thresholds and nothing
        else. The mode changes exactly one thing - whether the verdict is
        allowed to stop a promotion. That is why the switch lives here and is
        not threaded through the scorer, where it would become a second way of
        computing b and c and the two would eventually disagree.
        """
        if self.g4_mode == g4mod.ENFORCING:
            return finding("G4", check, status, detail,
                           rejects_if_unevaluable=(status == UNEVALUABLE))
        # RECORD_ONLY. `RECORDED` EVEN WHEN THE CRITERION PASSED - the status
        # answers "was this enforced", not "was it satisfied", and `would_have`
        # answers the second. A PASS emitted here would be indistinguishable
        # from a run that really was gated, which is the one thing a reader six
        # weeks out must never have to guess about.
        return finding("G4", check, RECORDED,
                       "%s [RECORD_ONLY: %s. NOT ENFORCED - this criterion did "
                       "not gate the promotion. Under ENFORCING it would have "
                       "been %s.]"
                       % (detail, self.g4_record_only_reason, status),
                       would_have=status)

    def closure_finding(self, candidate, record):
        """ORIGINATING-BREACH CLOSURE. Did the patch close the breach it was
        written for?

        A DISTINCT CRITERION FROM G4 AND NOT A CHEAPER SPELLING OF IT. G4 asks
        whether the candidate blocks at least three attacks it did not before,
        across a slice; this asks whether it closes THE ONE BREACH THE ARMORER
        was handed. The measured `b` histogram is bimodal, so the two come
        apart in both directions: a patch can close its originating breach
        without reaching `b >= 3`, and a patch can reach `b >= 3` on other
        episodes while doing nothing to the trace that provoked it.

        The arithmetic is `crucible.conductor.closure`; what this method owns is
        the finding and, through it, the route - the same split as `g4_finding`
        above and `infra.verify_iam` below it.
        """
        check = ("the originating clause no longer fires on the recorded trace "
                 "of the breach this patch answers")
        # THE MODE IS STAMPED ON THE RECORD BEFORE ANYTHING IS SCORED, so a
        # round that raises mid-measurement still says which mode was in force.
        record.closure_mode = self.closure_mode
        record.closure_record_only_reason = self.closure_record_only_reason
        try:
            scores = closuremod.closure_scores(
                getattr(record, "originating_autopsy", None),
                getattr(record, "originating_episode", None),
                getattr(record, "policy_in_force", None),
                candidate, self.objective_set())
        except closuremod.ClosureUnevaluable as exc:
            # THE CODE IS CARRIED ONTO THE RECORD EVEN WHEN NOTHING WAS
            # MEASURED. `closure_closed = None` and a named code is a different
            # statement from `closure_closed = False`, and a bundle that could
            # not tell them apart would read every unwired producer as a patch
            # that closed nothing.
            record.closure_code = exc.code
            record.closure_closed = None
            return self._closure_verdict(check, UNEVALUABLE, str(exc))
        passes, detail = closuremod.decide(scores)
        record.closure_closed = scores["closed"]
        record.closure_clause_id = scores["originating_clause_id"]
        record.closure_episode_still_breaches = scores["episode_still_breaches"]
        record.closure_code = None if passes else closuremod.E_NOT_CLOSED
        self.closure_scores.append(dict(
            scores, round_index=getattr(record, "round_index", None),
            mode=self.closure_mode,
            record_only_reason=self.closure_record_only_reason))
        return self._closure_verdict(check, PASS if passes else FAIL, detail)

    def _closure_verdict(self, check, status, detail):
        """The ONE place the closure mode turns a measurement into a finding.

        Identical in shape to `_g4_verdict`, and identical for the same reason:
        the measurement is already finished by the time this is called, and the
        mode changes exactly one thing - whether the verdict is allowed to stop
        a promotion.

        `rejects_if_unevaluable` is TRUE. An unevaluable closure check makes the
        candidate unpromotable and never reads as a closed breach. The route is
        read off `contracts/gate_rule.v1.yaml` rather than invented: G7 declares
        `absent_or_unevaluable: RUN_INVALID` explicitly, G4 declares only
        `failure_mode: REJECT`, and closure is a statement about the candidate
        rather than about the instrument. Letting it PASS is the one option that
        is definitely wrong.
        """
        if self.closure_mode == closuremod.ENFORCING:
            return finding("CLOSURE", check, status, detail,
                           rejects_if_unevaluable=(status == UNEVALUABLE))
        # RECORD_ONLY. `RECORDED` EVEN WHEN THE CRITERION PASSED, same argument
        # as `_g4_verdict`: the status answers "was this enforced", not "was it
        # satisfied", and `would_have` answers the second.
        return finding("CLOSURE", check, RECORDED,
                       "%s [RECORD_ONLY: %s. NOT ENFORCED - this criterion did "
                       "not gate the promotion. Under ENFORCING it would have "
                       "been %s.]"
                       % (detail, self.closure_record_only_reason, status),
                       would_have=status)

    def __call__(self, candidate, record):
        # THE ENVELOPE IS CHECKED BEFORE ANY CRITERION READS IT, and the check
        # HALTS rather than rejecting.
        #
        # This used to live inside `_promote_with_assertion`, at the end. That
        # was safe while every criterion above it was about the cloud
        # boundaries and ignored the candidate entirely; G4 reads the
        # candidate's rules, and a candidate with no `hashed_payload` looks to
        # it exactly like a policy with no rules - so a MALFORMED candidate came
        # back as an ordinary G4 rejection. That is the downgrade this file's
        # header names: "try again next round" standing in for a structural
        # fault. A malformed candidate is a HALT no matter which criterion
        # happens to notice it first, so it is decided once, here, before
        # anything downstream can mistake it for a measurement.
        if candidate is None or candidate.get("hashed_payload") is None:
            raise GateHalt("PROMOTION_ASSERT_FAILED",
                           "the candidate carries no hashed_payload")
        findings = self.preflight()
        # G4 IS CANDIDATE-DEPENDENT, so it cannot live in `preflight`, which is
        # a statement about the cloud boundaries and is the same answer for
        # every candidate in the round.
        #
        # CLOSURE COMES FIRST OF THE TWO CANDIDATE-DEPENDENT CRITERIA, and the
        # order is an argument rather than a habit: closure replays ONE episode
        # and G4 replays an accumulating slice through both arms, so closure is
        # the cheaper question, and it is also the question the patch was
        # written to answer. Both are evaluated on every call regardless -
        # short-circuiting would put b and c out of the bundle for exactly the
        # rounds a reader most wants them.
        findings = findings + [self.closure_finding(candidate, record),
                               self.g4_finding(candidate, record)]
        report = {"round_index": getattr(record, "round_index", None),
                  "findings": findings}
        self.reports.append(report)

        # `RECORDED` IS EXCLUDED HERE AND NOWHERE ELSE, and it is named rather
        # than expressed as a scattered `!= PASS and != RECORDED`. It is the
        # only status that is neither a pass nor a rejection; every other
        # non-PASS status still stops the promotion, including a G4 that was
        # measured and failed under ENFORCING.
        bad = [f for f in findings if f["status"] not in (PASS, RECORDED)]
        # G7's contract: `failure_mode: REJECT`, `absent_or_unevaluable:
        # RUN_INVALID`. So an UNEVALUABLE anything voids the run, as does any
        # finding carrying `invalidates` - which is decided where the assertion
        # is built, never inferred from the gate id here.
        invalidating = [f for f in bad
                        if (f["status"] == UNEVALUABLE
                            and not f.get("rejects_if_unevaluable"))
                        or f["invalidates"]]
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
        # `__call__` already refused a candidate with no `hashed_payload`, and
        # it must stay refused HERE TOO: this method is reachable from a test
        # or a future caller that does not go through `__call__`, and a guard
        # that only exists at one entry point is a guard that a second entry
        # point silently removes.
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
    """One line per assertion, for the campaign banner and the evidence bundle.

    A RECORDED row prints as `RECORDED(WOULD_FAIL)`, not as a bare `RECORDED`.
    "This criterion was not enforced" and "this criterion was not enforced AND
    it would have rejected this candidate" are different facts, and the second
    is the one a reader scanning a banner needs to see without opening a bundle.
    """
    def status_of(f):
        if f["status"] == RECORDED and f.get("would_have"):
            return "%s(WOULD_%s)" % (RECORDED, f["would_have"])
        return f["status"]

    return "\n".join(
        "  %-11s %-5s %s%s" % (status_of(f), f["gate"], f["check"],
                               ("\n              " + f["detail"]) if f["detail"] else "")
        for f in findings)


__all__ = ["RealGate", "build_real_gate", "GateRunInvalid", "GateHalt",
           "RECORDED",
           "GcsBlobIO", "local_blob_io", "iam_findings", "seal_probe_findings",
           "classify_probe", "promoter_identity", "gcp_env", "render",
           "object_name", "PASS", "FAIL", "UNEVALUABLE", "finding"]
