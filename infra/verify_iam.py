#!/usr/bin/env python3
"""verify_iam.py - the pre-flight IAM gate. G7, G8, and CONVENTIONS section 10a.

data-spec.md section 4.3: "Run this as a pre-flight gate before every run and print
the result in the UI. An access-control claim you re-verify on every run is worth
more than one you configured once."

WHY THIS IS PYTHON AND NOT THE TWO-LINE gcloud|grep FROM THE SPEC
-----------------------------------------------------------------
`gcloud ... | grep -c crucible-armorer   # MUST print 0` is correct and it is
also a check that cannot fail in the one way that matters: if the bucket name is
misspelled, gcloud errors, grep counts 0, and the gate reports the boundary
HOLDS. A misspelled resource and a clean boundary are the same output.
measurement-spec.md:813 names this exact failure -- an unevaluable gate is a
check that cannot fail.

So: fetch and PARSE, fail loudly if a fetch fails, and separate every predicate
from its data source so `--selftest` can drive each one to red with a synthetic
policy. A gate that has never been observed failing is not a gate.

Run:  python infra/verify_iam.py
      python infra/verify_iam.py --selftest     prove each check can fail
      python infra/verify_iam.py --json         machine-readable, for the UI
"""

import argparse
import io
import json
import re
import subprocess
import time
import sys


def _force_utf8_stdout():
    """Windows consoles die on the non-ASCII this file prints.

    MOVED OUT OF MODULE SCOPE 2026-08-22 and into `main()`. It used to run on
    import, which was harmless while this file was only ever a CLI and became a
    hazard the moment its predicates were imported:
    `crucible/conductor/real_gate.py` reuses them rather than restating them,
    and rebinding `sys.stdout` as a side effect of an import reaches into
    whatever already wrapped it - pytest's capture, most obviously. Behaviour on
    the command line is unchanged; `main()` calls this first.
    """
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace")

# --------------------------------------------------------------------------
# Names. Sourced from scripts/gcp-env.sh, never retyped -- G7 and G8 grep these
# literal strings and a typo produces an unevaluable gate rather than a failure.
# --------------------------------------------------------------------------

BASIC_ROLES = {"roles/viewer", "roles/editor", "roles/owner", "roles/browser"}

# Roles that let the holder OVERWRITE or DELETE an object. The promoter must
# hold none of them: objectCreator-without-overwrite is what makes a promoted
# policy version immutable by IAM rather than by convention.
MUTATING_STORAGE_ROLES = {
    "roles/storage.objectAdmin",
    "roles/storage.objectUser",
    "roles/storage.admin",
    "roles/storage.legacyBucketOwner",
    "roles/storage.legacyBucketWriter",
    "roles/storage.legacyObjectOwner",
}


def load_env(repo_root):
    """Read scripts/gcp-env.sh by asking bash, so there is exactly one source."""
    out = subprocess.run(
        ["bash", "-c", '. "%s/scripts/gcp-env.sh" && env | grep -E '
                       '"^(CRUCIBLE_|SA_|SUFFIX)"' % repo_root],
        capture_output=True, text=True, check=True).stdout
    env = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k] = v
    return env


def _gcloud_exe():
    """On Windows gcloud is `gcloud.cmd`, and subprocess without shell=True does
    not apply PATHEXT itself. Resolving it here rather than letting the call fail
    matters more than it looks: an unresolved executable raises FileNotFoundError
    from deep inside subprocess, which is a stack trace about the file system and
    not about IAM. The one thing this gate must never do is report a fetch
    problem in a way that could be read as a clean boundary."""
    import shutil
    for cand in ("gcloud", "gcloud.cmd", "gcloud.exe"):
        found = shutil.which(cand)
        if found:
            return found
    raise RuntimeError(
        "gcloud is not on PATH. This gate cannot be evaluated, which is NOT the "
        "same as passing -- an unevaluable gate is a check that cannot fail "
        "(measurement-spec.md:813).")


GCLOUD = None


FETCH_ATTEMPTS = 3
FETCH_BACKOFF = (0.5, 2.0)


def gcloud_json(args, what):
    """Fetch and parse. A failed fetch is a FAILED CHECK, never an empty result.

    RETRIED, BOUNDED, AND IT CANNOT LAUNDER A REAL DENIAL. Run 10 of the
    2026-08-25 overnight batch went RUN_INVALID because this call failed once;
    every G7/G8 assertion went UNEVALUABLE and the run produced no measurement.
    The same command succeeded on the next manual invocation, so it was
    transient. At roughly one run in ten that is six wasted runs in a batch of
    sixty.

    Retrying is safe here for the reason `real_gate` already retries a
    PromotionError: the predicates still run against a REAL policy document or
    against nothing at all. A permission denial simply returns the same answer
    three times and still ends as UNEVALUABLE. Nothing is converted into a pass.

    THE ERROR NOW SAYS SOMETHING. It used to interpolate `p.stderr` alone, and
    run 10 exited non-zero with an EMPTY stderr, so the failure read
    "could not fetch project IAM policy: " and named no cause at all. An error
    that reports nothing is a diagnostic dead end, which is the same defect as a
    check that cannot fail wearing different clothes. The return code and a
    slice of stdout travel with it now.
    """
    global GCLOUD
    if GCLOUD is None:
        GCLOUD = _gcloud_exe()
    if args and args[0] == "gcloud":
        args = [GCLOUD] + list(args[1:])
    last = None
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        p = subprocess.run(args, capture_output=True, text=True)
        if p.returncode == 0:
            try:
                return json.loads(p.stdout)
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    "unparseable policy for %s: %s" % (what, e)) from None
        err = p.stderr.strip()[:300] or (
            "no stderr; stdout was %r" % p.stdout.strip()[:120] if p.stdout.strip()
            else "no stderr and no stdout")
        last = "exit %d, %s" % (p.returncode, err)
        if attempt < FETCH_ATTEMPTS:
            time.sleep(FETCH_BACKOFF[attempt - 1])
    raise RuntimeError("could not fetch %s after %d attempts: %s"
                       % (what, FETCH_ATTEMPTS, last))


# --------------------------------------------------------------------------
# PREDICATES. Pure functions over a policy dict. Every one is driven to red by
# --selftest. No I/O in here on purpose.
# --------------------------------------------------------------------------

def members_of(policy, role):
    for b in policy.get("bindings", []):
        if b.get("role") == role:
            return set(b.get("members", []))
    return set()


def roles_held_by(policy, member):
    return {b["role"] for b in policy.get("bindings", [])
            if member in b.get("members", [])}


def check_gate_can_create(policy, gate_member):
    """G8: the Gate holds objectCreator on the policies bucket."""
    if gate_member in members_of(policy, "roles/storage.objectCreator"):
        return None
    return ("the promoter holds no objectCreator on the policies bucket, so "
            "nothing can create a policy version and G8 is unevaluable")


def check_gate_cannot_overwrite(policy, gate_member):
    """G8: objectCreator ONLY. Overwrite/delete would make immutability a costume."""
    bad = roles_held_by(policy, gate_member) & MUTATING_STORAGE_ROLES
    if not bad:
        return None
    return ("the promoter holds %s on the policies bucket. objectCreator cannot "
            "overwrite or delete a promoted version; these can. The immutability "
            "claim would be convention wearing an IAM costume"
            % ", ".join(sorted(bad)))


def check_member_absent(policy, member, where):
    """G7/G8: this identity holds NOTHING on this bucket."""
    held = roles_held_by(policy, member)
    if not held:
        return None
    return ("%s holds %s on %s. THE IDENTITY THAT AUTHORS A CANDIDATE IS NOT THE "
            "IDENTITY THAT PROMOTES IT -- G8's own failure text applies: the "
            "separation was never real. Failure mode: RUN INVALID"
            % (member, ", ".join(sorted(held)), where))


def check_no_basic_roles(project_policy, crucible_members):
    """CONVENTIONS 10a. THE CHECK THE BUCKET GREPS STRUCTURALLY CANNOT MAKE.

    Every new GCS bucket ships with default legacy projectViewer:/projectEditor:
    bindings. A principal holding a project-level BASIC role therefore inherits
    READ on the sealed bucket THROUGH THEM, with no binding that names that
    bucket. G7(b)'s filter tests role =~ "storage|bigquery", which a basic role
    never matches. So the 403 demonstrated on camera is one roles/viewer grant
    away from being theatre, and nothing else here would notice.
    """
    offenders = []
    for role in sorted(BASIC_ROLES):
        for m in members_of(project_policy, role) & set(crucible_members):
            offenders.append("%s holds %s" % (m, role))
    if not offenders:
        return None
    return ("project-level BASIC role held by a CRUCIBLE identity: %s. This "
            "grants READ on the sealed bucket through the default legacy "
            "projectViewer/projectEditor bindings, with NO binding naming that "
            "bucket" % "; ".join(offenders))


def check_no_storage_or_bq_at_project(project_policy, member):
    """data-spec 4.3 layer 2, second command."""
    bad = sorted(r for r in roles_held_by(project_policy, member)
                 if re.search(r"storage|bigquery", r))
    if not bad:
        return None
    return "%s holds project-level %s" % (member, ", ".join(bad))


MISSING = object()


def _pick(meta, *paths):
    """Read the first path that EXISTS, and report MISSING if none does.

    `gcloud storage buckets describe --format=json` and the GCS JSON API return
    DIFFERENT SHAPES for the same facts:

        JSON API   iamConfiguration.uniformBucketLevelAccess.enabled : bool
        gcloud     uniform_bucket_level_access                       : bool
        JSON API   iamConfiguration.publicAccessPrevention           : str
        gcloud     public_access_prevention                          : str
        JSON API   retentionPolicy                                   : object
        gcloud     retention_policy                                  : object

    data-spec.md 4.3's check commands are written against one shape; the CLI on
    this machine emits the other. Reading only one and treating a missing key as
    "off" was the first version of this file, and on 2026-08-20 it reported four
    FAILs against infrastructure that was correct.

    The direction of that error was lucky. A predicate phrased the other way --
    "flag only if the key says something bad" -- would have read the same missing
    key and printed PASS on a bucket it had never actually inspected. So MISSING
    is a distinct outcome here and never collapses into either verdict.
    """
    for path in paths:
        cur = meta
        ok = True
        for key in path.split("."):
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break
        if ok:
            return cur
    return MISSING


def check_retention_present_and_unlocked(bucket_meta, name):
    """G8 asserts the policy EXISTS. It must NOT assert that it is locked.

    A locked GCS retention policy cannot be removed or shortened by anyone ever,
    including the project owner. data-spec 7.3 tears these buckets down, and a
    locked 14d policy blocks that for two weeks past the last write on a contest
    ending 08-31. So "locked" is a FAILURE here, not a stronger pass.
    """
    rp = _pick(bucket_meta, "retentionPolicy", "retention_policy")
    if rp is MISSING:
        rp = {}
    if not isinstance(rp, dict):
        return "%s: retention policy is %r, which this gate cannot read" % (name, rp)
    period = _pick(rp, "retentionPeriod", "retention_period")
    if period is MISSING or not period:
        return "%s has no retention policy" % name
    locked = _pick(rp, "isLocked", "is_locked")
    if locked is not MISSING and locked:
        return ("%s retention policy is LOCKED. It cannot be removed or shortened "
                "by anyone including the project owner, and it blocks the "
                "data-spec 7.3 teardown for 14 days past the last write" % name)
    return None


def check_versioning_on(bucket_meta, name):
    """G8's fourth assertion, which nothing in this file checked until
    2026-08-22: "bucket retention policy (14d) EXISTS and object versioning is
    ON" (`contracts/gate_rule.v1.yaml` G8, `measurement-spec.md`:891).

    Retention was covered; versioning was not. The two are the belt and the
    braces of the same claim - `data-spec.md`:1031 calls them "belt-and-suspenders"
    for "a promoted version is immutable" - and half a belt-and-braces claim,
    silently, is worse than knowing you only have one.

    Same MISSING discipline as `check_ubla_and_pap`: a key absent from BOTH the
    JSON-API shape and the gcloud shape means this gate did not inspect the
    setting, and that is not a pass.
    """
    v = _pick(bucket_meta, "versioning.enabled", "versioning_enabled")
    if v is MISSING:
        return ("%s: UNEVALUABLE - no versioning field in either the JSON-API "
                "(`versioning.enabled`) or the gcloud (`versioning_enabled`) "
                "shape. This gate did not inspect the setting and must not be "
                "read as a pass" % name)
    if not v:
        return ("%s: object versioning is OFF. With objectCreator-only the "
                "promoter cannot overwrite a version, but versioning is the "
                "half of that claim that survives a role being widened later"
                % name)
    return None


def check_ubla_and_pap(bucket_meta, name):
    """UBLA off means an object ACL is a second grant path the get-iam-policy
    grep cannot see -- the check passes while the boundary leaks."""
    problems = []
    ubla = _pick(bucket_meta,
                 "iamConfiguration.uniformBucketLevelAccess.enabled",
                 "uniform_bucket_level_access")
    pap = _pick(bucket_meta,
                "iamConfiguration.publicAccessPrevention",
                "public_access_prevention")

    if ubla is MISSING:
        problems.append("UNEVALUABLE: no uniform-bucket-level-access field in "
                        "either the JSON-API or the gcloud shape. This gate did "
                        "not inspect the setting and must not be read as a pass")
    elif not ubla:
        problems.append("uniform bucket-level access is OFF, so an object ACL is "
                        "a second grant path no IAM-policy check can see")

    if pap is MISSING:
        problems.append("UNEVALUABLE: no public-access-prevention field in either "
                        "shape")
    elif pap != "enforced":
        problems.append("public access prevention is %r, not 'enforced'" % pap)

    return "%s: %s" % (name, "; ".join(problems)) if problems else None


# --------------------------------------------------------------------------
# SELFTEST. Every predicate driven to RED with a synthetic policy.
# --------------------------------------------------------------------------

def selftest():
    GATE = "serviceAccount:crucible-gate@p.iam.gserviceaccount.com"
    ARM = "serviceAccount:crucible-armorer@p.iam.gserviceaccount.com"
    cases = []

    def case(name, got, must_fail):
        ok = (got is not None) if must_fail else (got is None)
        cases.append((ok, name, got))

    clean_policies = {"bindings": [
        {"role": "roles/storage.objectCreator", "members": [GATE]},
        {"role": "roles/storage.objectViewer", "members": [GATE]},
    ]}
    case("gate_can_create / PASSES on a correct policy",
         check_gate_can_create(clean_policies, GATE), False)
    case("gate_can_create / FAILS when the grant is missing",
         check_gate_can_create({"bindings": []}, GATE), True)

    case("gate_cannot_overwrite / PASSES on objectCreator only",
         check_gate_cannot_overwrite(clean_policies, GATE), False)
    for role in sorted(MUTATING_STORAGE_ROLES):
        case("gate_cannot_overwrite / FAILS on %s" % role,
             check_gate_cannot_overwrite(
                 {"bindings": [{"role": role, "members": [GATE]}]}, GATE), True)

    case("member_absent / PASSES when the armorer holds nothing",
         check_member_absent(clean_policies, ARM, "policies"), False)
    case("member_absent / FAILS on the INVERTED grant direction",
         check_member_absent(
             {"bindings": [{"role": "roles/storage.objectCreator",
                            "members": [ARM]}]}, ARM, "policies"), True)
    case("member_absent / FAILS even on a read-only grant",
         check_member_absent(
             {"bindings": [{"role": "roles/storage.objectViewer",
                            "members": [ARM]}]}, ARM, "policies"), True)

    crucible = [GATE, ARM]
    case("no_basic_roles / PASSES when only a human holds owner",
         check_no_basic_roles(
             {"bindings": [{"role": "roles/owner",
                            "members": ["user:eric@example.invalid"]}]},
             crucible), False)
    for role in sorted(BASIC_ROLES):
        case("no_basic_roles / FAILS on %s -- THE CASE THE BUCKET GREP CANNOT SEE"
             % role,
             check_no_basic_roles(
                 {"bindings": [{"role": role, "members": [ARM]}]}, crucible), True)

    case("no_storage_or_bq_at_project / PASSES on aiplatform+datastore",
         check_no_storage_or_bq_at_project(
             {"bindings": [{"role": "roles/aiplatform.user", "members": [ARM]},
                           {"role": "roles/datastore.user", "members": [ARM]}]},
             ARM), False)
    case("no_storage_or_bq_at_project / FAILS on project-level storage",
         check_no_storage_or_bq_at_project(
             {"bindings": [{"role": "roles/storage.objectViewer",
                            "members": [ARM]}]}, ARM), True)
    case("no_storage_or_bq_at_project / FAILS on project-level bigquery",
         check_no_storage_or_bq_at_project(
             {"bindings": [{"role": "roles/bigquery.dataViewer",
                            "members": [ARM]}]}, ARM), True)

    case("retention / PASSES when present and unlocked",
         check_retention_present_and_unlocked(
             {"retentionPolicy": {"retentionPeriod": "1209600"}}, "b"), False)
    case("retention / FAILS when absent",
         check_retention_present_and_unlocked({}, "b"), True)
    case("retention / FAILS when LOCKED -- locked is a failure, not a stronger pass",
         check_retention_present_and_unlocked(
             {"retentionPolicy": {"retentionPeriod": "1209600",
                                  "isLocked": True}}, "b"), True)

    case("versioning / PASSES on the JSON-API shape",
         check_versioning_on({"versioning": {"enabled": True}}, "b"), False)
    case("versioning / PASSES on the gcloud snake_case shape",
         check_versioning_on({"versioning_enabled": True}, "b"), False)
    case("versioning / FAILS when OFF",
         check_versioning_on({"versioning": {"enabled": False}}, "b"), True)
    case("versioning / FAILS as UNEVALUABLE when NEITHER shape is present",
         check_versioning_on({"someOtherApiVersion": {}}, "b"), True)

    good_cfg = {"iamConfiguration": {
        "uniformBucketLevelAccess": {"enabled": True},
        "publicAccessPrevention": "enforced"}}
    case("ubla_pap / PASSES on the JSON-API shape",
         check_ubla_and_pap(good_cfg, "b"), False)
    # The shape `gcloud storage buckets describe` actually emits on this machine.
    # Reading only the JSON-API shape produced four FAILs against correct
    # infrastructure on 2026-08-20.
    case("ubla_pap / PASSES on the gcloud snake_case shape",
         check_ubla_and_pap({"uniform_bucket_level_access": True,
                             "public_access_prevention": "enforced"}, "b"), False)
    case("ubla_pap / FAILS as UNEVALUABLE when NEITHER shape is present",
         check_ubla_and_pap({"someOtherApiVersion": {}}, "b"), True)
    case("ubla_pap / FAILS on the gcloud shape with UBLA off",
         check_ubla_and_pap({"uniform_bucket_level_access": False,
                             "public_access_prevention": "enforced"}, "b"), True)
    case("retention / PASSES on the gcloud snake_case shape",
         check_retention_present_and_unlocked(
             {"retention_policy": {"retentionPeriod": "1209600"}}, "b"), False)
    case("retention / FAILS when LOCKED in the gcloud shape",
         check_retention_present_and_unlocked(
             {"retention_policy": {"retentionPeriod": "1209600",
                                   "is_locked": True}}, "b"), True)
    case("ubla_pap / FAILS when UBLA is off",
         check_ubla_and_pap({"iamConfiguration": {
             "uniformBucketLevelAccess": {"enabled": False},
             "publicAccessPrevention": "enforced"}}, "b"), True)
    case("ubla_pap / FAILS when PAP is inherited",
         check_ubla_and_pap({"iamConfiguration": {
             "uniformBucketLevelAccess": {"enabled": True},
             "publicAccessPrevention": "inherited"}}, "b"), True)

    print("SELFTEST - every predicate driven to red and to green\n")
    bad = 0
    for ok, name, got in cases:
        print("  %s %s" % ("ok  " if ok else "FAIL", name))
        if not ok:
            bad += 1
            print("       returned: %r" % (got,))
    print("\n  %d cases, %d failed" % (len(cases), bad))
    if bad:
        print("\n  THE GATE ITSELF IS BROKEN. Do not trust a green run.")
        return 1
    print("  Every check has now been observed both passing and failing.")
    return 0


# --------------------------------------------------------------------------
# LIVE RUN.
# --------------------------------------------------------------------------

def run_live(repo_root, as_json):
    env = load_env(repo_root)
    project = env["CRUCIBLE_PROJECT"]

    def sa(name):
        return "serviceAccount:%s@%s.iam.gserviceaccount.com" % (name, project)

    all_sas = [sa(n) for n in env["CRUCIBLE_ALL_SAS"].split()]
    gate, armorer, red = sa(env["SA_GATE"]), sa(env["SA_ARMORER"]), sa(env["SA_RED"])
    policies = env["CRUCIBLE_POLICIES_BUCKET"]
    sealed = env["CRUCIBLE_SEALED_BUCKET"]
    evidence = env["CRUCIBLE_EVIDENCE_BUCKET"]

    findings = []

    def add(gate_id, label, problem):
        findings.append({"gate": gate_id, "check": label,
                         "status": "FAIL" if problem else "PASS",
                         "detail": problem or ""})

    proj_pol = gcloud_json(
        ["gcloud", "projects", "get-iam-policy", project, "--format=json"],
        "project IAM policy")
    pol_pol = gcloud_json(
        ["gcloud", "storage", "buckets", "get-iam-policy", policies, "--format=json"],
        policies)
    sea_pol = gcloud_json(
        ["gcloud", "storage", "buckets", "get-iam-policy", sealed, "--format=json"],
        sealed)

    def meta(b):
        return gcloud_json(["gcloud", "storage", "buckets", "describe", b,
                            "--format=json"], b)

    add("G8", "gate holds objectCreator on %s" % policies,
        check_gate_can_create(pol_pol, gate))
    add("G8", "gate holds NO overwrite/delete role on %s" % policies,
        check_gate_cannot_overwrite(pol_pol, gate))
    add("G8", "armorer holds NOTHING on %s" % policies,
        check_member_absent(pol_pol, armorer, policies))
    add("G7", "armorer holds NOTHING on %s" % sealed,
        check_member_absent(sea_pol, armorer, sealed))
    add("G7", "red holds NOTHING on %s" % sealed,
        check_member_absent(sea_pol, red, sealed))
    add("G7b2", "no CRUCIBLE identity holds a project-level BASIC role",
        check_no_basic_roles(proj_pol, all_sas))
    add("G7", "armorer holds no project-level storage/bigquery role",
        check_no_storage_or_bq_at_project(proj_pol, armorer))
    policies_meta = meta(policies)
    add("G8", "policies retention exists and is NOT locked",
        check_retention_present_and_unlocked(policies_meta, policies))
    add("G8", "policies object versioning is ON",
        check_versioning_on(policies_meta, policies))
    for b in (policies, sealed, evidence):
        add("G7/G8", "UBLA on and PAP enforced: %s" % b, check_ubla_and_pap(meta(b), b))

    failed = [f for f in findings if f["status"] == "FAIL"]
    if as_json:
        print(json.dumps({"project": project, "findings": findings,
                          "failed": len(failed)}, indent=2))
    else:
        print("IAM PRE-FLIGHT - project %s\n" % project)
        for f in findings:
            print("  %-4s %-6s %s" % (f["status"], f["gate"], f["check"]))
            if f["detail"]:
                print("         %s" % f["detail"])
        print("\n  %d checks, %d failed" % (len(findings), len(failed)))
        if failed:
            print("\n  RUN INVALID. An invalid run publishes no numbers, "
                  "including the ones that look good.")
    return 1 if failed else 0


def main():
    _force_utf8_stdout()
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--repo-root", default=None)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    import pathlib
    root = a.repo_root or str(pathlib.Path(__file__).resolve().parent.parent)
    return run_live(root, a.json)


if __name__ == "__main__":
    sys.exit(main())
