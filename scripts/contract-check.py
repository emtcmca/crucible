#!/usr/bin/env python3
"""contract-check.py - the W0 gate on the contract set.

Five passes. Every one of them is designed so that IT CAN FAIL, because
CONVENTIONS.md section 8 rule 2 says a check that cannot fail is not measuring
anything - and this repository has already produced two checks that could not:
a sweep that reported CLEAN on hard-wrapped prose, and a negative test that
appended a newline the normalization exists to absorb.

  1  HASH      every contract file still hashes to MANIFEST.json
  2  FIXTURES  every golden positive VALIDATES and every known-bad FAILS
  3  SWEEP     no dead value is ASSERTED anywhere (strike context exempt)
  4  STATUS    no undated present-tense existence claim   (section 8 rule 12)
  5  TERMS     no contract redefines a bound term         (section 8 rule 11)

Run:  python scripts/contract-check.py
      python scripts/contract-check.py --selftest   # prove each pass can fail

`--selftest` runs ALL FIVE against a throwaway copy of the repository, once
clean and once with a defect authored for that pass, and asserts the pass is
green on the first and names the defect on the second. Until 2026-08-23 it
printed the same promise while covering three of the five and never calling a
pass function at all - see the SELFTEST section for what that could not catch.
"""

import contextlib
import io
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

# The specs carry arrows, em-dashes, and section signs. On Windows the default
# console codec is cp1252 and printing a finding CRASHES THE GATE - which would
# make a failing check look like a broken tool rather than a finding.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    from jsonschema.validators import Draft202012Validator as _D
    from referencing.jsonschema import DRAFT202012 as DRAFT
except Exception:  # pragma: no cover - reported by pass_fixtures instead
    DRAFT = None

REPO = pathlib.Path(__file__).resolve().parent.parent
CONTRACTS = REPO / "contracts"
GOLDEN = CONTRACTS / "golden"
DOCS = REPO / "docs"


def swept_markdown():
    """Every markdown file the SWEEP and STATUS passes police.

    README.md IS IN THIS LIST AND WAS NOT, WHICH IS WHY IT ROTTED. Both passes
    walked `docs/` only, so the single most public file in a public repository
    was the one file nothing checked. On 2026-08-24 it was found asserting
    "nothing has been measured", "No --live run has been executed", that nothing
    had been promoted because the write path had never run against GCS, and -
    worst - that "The spend cap is a frozen parameter at $160, a cap, not an
    alert, so an overrun is a deliberate decision rather than a discovery."
    That last one is backwards: `gcloud billing budgets list` returns a
    notificationsRule with email recipients and three thresholdRules at 50, 90
    and 100 percent. Nothing stops at $160. An overrun is precisely a discovery.

    The lesson is the one this project keeps relearning in new places: a check
    that does not cover the artifact is a check that cannot fail for it.
    """
    seen = set()
    for p in sorted(DOCS.rglob("*.md")):
        seen.add(p)
        yield p
    for name in ("README.md", "CLAUDE.md"):
        p = REPO / name
        if p.exists() and p not in seen:
            yield p

# Which schema validates which fixture prefix.
FIXTURE_SCHEMA = {
    "C1": "tool_event.schema.json",
    "C2": "decision.schema.json",
    "C3a": "capability_manifest.schema.json",
    "C3b": "derived_schema.schema.json",
    "C4": "policy_document.schema.json",
    "C5": "breach_record.schema.json",
    "C6": "evidence_bundle.schema.json",
    "C7": "run_manifest.schema.json",
    "C9": "verdict.schema.json",
    "C10": "objective_set.schema.json",
}

# C8 has no separate fixture: gate_rule.v1.yaml IS the instance, not a schema
# describing one. Logged rather than silently omitted - section 8 rule 9, log
# the drop, because silent truncation reads as "covered everything".
NO_FIXTURE = {"C8": "gate_rule.v1.yaml is itself the instance, not a schema"}

# -----------------------------------------------------------------------------
# Pass 3 - dead values. Two normalization defects were paid for on 2026-08-20
# and both are fixed here; see ruling 20.
# -----------------------------------------------------------------------------
DEAD = {
    "four-hash-locks": r"four\s+hash[-\s]?locks?|all\s+four\s+hashes|the\s+four\s+hashes|carries\s+four\s+hashes",
    "match_mode": r"match_mode",
    "approval-verified": r"approval_record\.verified|derived\.approval_verified",
    "cannot-express": r"structurally\s+cannot\s+express",
    "role-qualifier": r"\brole:[a-z_]+",
    "litt-hackathon": r"litt-hackathon",
    "sdk-570": r"570\.0\.0",
    "no-repo": r"NOT YET A GIT REPOSITORY|there is no repository yet",
}

# A site ASSERTING a dead value and a site STRIKING one are not the same site.
# Without this, every correction note reports itself as drift - the exact defect
# canon-check --selftest already caught once.
EXEMPT = re.compile(
    r"~~|CORRECTED|SUPERSEDED|DELETED|STRUCK|DEAD|RULED|RESOLVED|CLOSED|"
    r"was wrong|read \"|until 2026|DO NOT USE|do not write|MUST BE|must be a parse error|"
    r"must be rejected|KNOWN_BAD|_must_fail_because|no match_mode|is removed|is GONE|"
    r"is DELETED|not\s+EVALUATED|NEVER|"
    # a TRANSITION statement legitimately names the value it is retiring
    r"become[sd]?\s+FIVE|becomes?\s+five|now\s+five|are\s+five|to\s+five|"
    # correction prose QUOTING the dead value back
    r"sites?\s+(?:asserted|said|carry|carrie[ds]|still)|was\s+carrying|"
    r"stated as|wrong\s+in|drifted|stale|this\s+read|it\s+read|previously",
    re.I)

STATUS_CLAIM = re.compile(
    r"(?:does not exist|do not exist|there is no\b|not yet\b|is currently\b|"
    r"still unconfigured|is unconfigured|has not been (?:created|configured|provisioned|run))", re.I)

# A status claim is a claim about an ARTIFACT OR THE ENVIRONMENT - something that
# can be created, deployed, or configured, and that therefore GOES STALE. A claim
# about the DESIGN ("there is no fourth verb", "there is no way to write a rule
# that binds only to a tool") is a CONTRACT statement and stays true for months.
# Only the first kind is checked.
STATUS_SUBJECT = re.compile(
    r"(?:\brepositor(?:y|ies)\b|\bgit repo\b|\bgit init\b|\bcommit signing\b|"
    r"\bservice account\b|\bcrucible-[a-z]+@|\bIAM binding\b|"
    r"\bcrucible-hack-2026\b|\blitt-hackathon\b|\bactive project\b|"
    r"\bcrucible-(?:sealed|policies|evidence)-|\bFirestore database\b|"
    r"\bgcloud SDK\b|\bSDK \d|\bcontracts/\b|\bMANIFEST\.json\b|"
    r"\bworktree\b|\bon disk\b|\bapplication code\b|\bgolden fixture\b)", re.I)

# Self-reference guard: rule 12 and the lane brief DESCRIBE these patterns, in
# backticks, as the things to look for. A checker that flags its own
# specification is the same defect class as a correction note reporting itself
# as drift.
# A contrast marker means the text is DRAWING the distinction, not blurring it.
CONTRAST = re.compile(r"is not\b|are not\b|distinct from|rather than|instead of|"
                      r"never\b|not the\b|vs\.?\b|as opposed to|means\b|"
                      r"neither\b|\bnor\b|counting\b|would let\b|would be\b|"
                      r"NOT\b|false phrasing|do not\b", re.I)

STATUS_SELFREF = re.compile(r"verification date|status claim|STATUS pass|rule 12|"
                            r"present-tense existence", re.I)
DATE = re.compile(r"20\d\d-\d\d-\d\d")


def normalize(raw):
    """Collapse to one line, stripping blockquote leads first, with a line map."""
    flat = raw.replace("\r\n", "\n")
    lines = flat.split("\n")
    chars, lmap = [], []
    for n, line in enumerate(lines, 1):
        stripped = re.sub(r"^[ \t]*(?:>[ \t]*)+", "", line)
        for ch in stripped:
            chars.append(ch); lmap.append(n)
        chars.append(" "); lmap.append(n)
    text, out, omap, prev_ws = "".join(chars), [], [], False
    for ch, ln in zip(text, lmap):
        if ch.isspace():
            if prev_ws:
                continue
            out.append(" "); omap.append(ln); prev_ws = True
        else:
            out.append(ch); omap.append(ln); prev_ws = False
    return "".join(out), omap


def _window(norm, i, w=140):
    return norm[max(0, i - w):i + w]


SWEEP_OK = re.compile(r"<!--\s*sweep-ok")


def _exempt(norm, i, src_lines, line_no):
    """Strike context, judged on the window AND on the whole source line.

    A markdown table row is a SINGLE source line and routinely runs past 400
    characters, so a centred window can sit entirely inside the row without
    ever reaching the `~~` or `CORRECTED` that marks it as a correction. Both
    views are checked; either one exempting is enough.
    """
    lo, hi = max(0, line_no - 2), min(len(src_lines), line_no + 1)
    block = " ".join(src_lines[lo:hi])
    # An EXPLICIT, AUDITABLE exemption beats a widened regex. Heuristics that
    # keep growing until they stop firing end up unable to fail at all, which
    # is the defect this whole gate exists to prevent. `<!-- sweep-ok: why -->`
    # is a decision someone WROTE DOWN, and it shows up in a diff.
    if SWEEP_OK.search(block):
        return True
    if EXEMPT.search(_window(norm, i)):
        return True
    return bool(EXEMPT.search(block))


# -----------------------------------------------------------------------------

def pass_hash():
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "hash-contracts.py"), "--check"],
                       capture_output=True, text=True, cwd=REPO)
    return (r.returncode == 0, [l for l in (r.stdout + r.stderr).strip().split("\n") if l])


def _registry():
    """Resolve every $ref LOCALLY. The contracts carry absolute $id URLs, and
    without this jsonschema tries to FETCH them over the network - which makes
    the gate fail on a machine with no egress. A judge reproducing this build
    must not need internet access to validate a fixture, and CI may have none.
    """
    from referencing import Registry, Resource
    resources = []
    for p in sorted(CONTRACTS.glob("*.schema.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        res = Resource.from_contents(doc, default_specification=DRAFT)
        resources.append((doc["$id"], res))
    return Registry().with_resources(resources)


def pass_fixtures():
    import jsonschema
    fails = []
    if not GOLDEN.exists():
        return False, ["contracts/golden/ does not exist"]
    reg = _registry()
    seen_ids = set()
    for fx in sorted(GOLDEN.glob("*.json")):
        cid = fx.name.split("-")[0]
        seen_ids.add(cid)
        schema_file = FIXTURE_SCHEMA.get(cid)
        if not schema_file:
            fails.append("%s: no schema mapped for %s" % (fx.name, cid)); continue
        schema = json.loads((CONTRACTS / schema_file).read_text(encoding="utf-8"))

        # IS THE SCHEMA ITSELF A VALID SCHEMA? Added 2026-08-20 on L5's report,
        # and it found FIVE MORE instances of the defect L5 found one of.
        #
        # This pass validated fixtures against schemas and never asked whether
        # the schemas were valid. `iter_errors` ignores `$comment` entirely, so
        # SIX OF TEN CONTRACTS carried array-valued `$comment`s -- illegal, the
        # keyword MUST be a string -- and every fixture check stayed green.
        # `jsonschema.validate()`, the standard entry point, raises SchemaError
        # on them BEFORE looking at the instance, so a consumer using the normal
        # API could not validate against those contracts at all.
        #
        # The general shape, again: a check that never inspects its own
        # instrument reports on the instrument's behalf.
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
        except jsonschema.exceptions.SchemaError as e:
            fails.append("%s is NOT A VALID Draft 2020-12 SCHEMA: %s. Every "
                         "fixture check against it is meaningless."
                         % (schema_file, str(e).splitlines()[0][:90]))
            continue

        body = json.loads(fx.read_text(encoding="utf-8"))
        body.pop("_must_fail_because", None)
        body.pop("_note", None)
        validator = jsonschema.Draft202012Validator(schema, registry=reg)
        errs = list(validator.iter_errors(body))
        want_fail = "KNOWN_BAD" in fx.name
        if want_fail and not errs:
            fails.append("%s: KNOWN-BAD fixture VALIDATED - the schema cannot catch it" % fx.name)
        if not want_fail and errs:
            fails.append("%s: valid fixture REJECTED - %s" % (fx.name, errs[0].message[:110]))
    missing = [c for c in FIXTURE_SCHEMA if c not in seen_ids]
    for m in missing:
        fails.append("NO GOLDEN FIXTURE for %s (lanes-spec 10 item 2 requires one per contract)" % m)
    return (not fails), fails


def pass_sweep():
    hits = []
    for p in sorted(swept_markdown()):
        raw = p.read_text(encoding="utf-8", errors="replace")
        src_lines = raw.split("\n")
        norm, lmap = normalize(raw)
        for label, pat in DEAD.items():
            for m in re.finditer(pat, norm, re.I):
                if _exempt(norm, m.start(), src_lines, lmap[m.start()]):
                    continue
                hits.append("%s:%d asserts dead value [%s]" % (
                    p.relative_to(REPO).as_posix(), lmap[m.start()], label))
    return (not hits), hits


def pass_status():
    hits = []
    for p in sorted(swept_markdown()):
        norm, lmap = normalize(p.read_text(encoding="utf-8", errors="replace"))
        for m in STATUS_CLAIM.finditer(norm):
            win = _window(norm, m.start(), 160)
            if DATE.search(win) or EXEMPT.search(win):
                continue
            if not STATUS_SUBJECT.search(win):
                continue   # a design statement, not a status claim
            if STATUS_SELFREF.search(win):
                continue   # this text DESCRIBES the check; it is not a claim
            hits.append("%s:%d undated status claim: %s" % (
                p.relative_to(REPO).as_posix(), lmap[m.start()],
                norm[m.start():m.start() + 62].strip()))
    return (not hits), hits


def pass_terms():
    manifest = json.loads((CONTRACTS / "MANIFEST.json").read_text(encoding="utf-8"))
    bindings = manifest.get("term_bindings", {})
    if not bindings:
        return False, ["MANIFEST.json carries no term_bindings (section 8 rule 11)"]
    hits = []
    for term, spec in bindings.items():
        for banned in spec.get("not", []):
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_. ]*$", banned):
                continue
            pat = r"\b%s\b" % re.escape(banned)
            for p in sorted(CONTRACTS.glob("*.json")):
                if p.name == "MANIFEST.json":
                    continue
                norm, lmap = normalize(p.read_text(encoding="utf-8"))
                for m in re.finditer(pat, norm):
                    win = _window(norm, m.start())
                    if EXEMPT.search(win) or CONTRAST.search(win):
                        continue
                    hits.append("%s:%d uses '%s', which is bound to '%s'" % (
                        p.name, lmap[m.start()], banned, term))
    return (not hits), hits


# THE ONLY TIME-DEPENDENT PASS, AND THAT IS THE POINT. Say it loudly because it
# is unusual: this check can go from OK to FAIL with no commit in between. That
# is not a bug. Staleness IS a function of time, and a freshness check that only
# fired when someone touched the file would be a check that cannot fail for the
# exact case it exists to catch - a file nobody edited while the world moved.
# That is how README.md came to assert "nothing has been measured" and
# "No --live run has been executed" in a public repo during judging, and how it
# came to call the $160 budget a cap when the deployed budget carries only email
# recipients and three alert thresholds.
#
# Eric's standing instruction, 2026-08-25: the README is refreshed nightly until
# submission, together with the Devpost update. `docs/DAILY-UPDATE-CHECKLIST.md`
# is the ritual; this is the part that does not depend on anyone remembering.
README_STALE_DAYS = 2
README_ASOF = re.compile(r"\*\*As of (20\d\d-\d\d-\d\d)")


def pass_freshness():
    import datetime
    text = (REPO / "README.md").read_text(encoding="utf-8", errors="replace")
    m = README_ASOF.search(text)
    if not m:
        return False, ["README.md has no '**As of YYYY-MM-DD' anchor in its "
                       "Status section. That date is what this pass reads; "
                       "without it the file cannot be checked for staleness "
                       "at all, which is worse than being stale."]
    asof = datetime.date.fromisoformat(m.group(1))
    age = (datetime.date.today() - asof).days
    if age > README_STALE_DAYS:
        return False, [
            "README.md Status is dated %s, %d days old (limit %d). Refresh it "
            "with the Devpost update - docs/DAILY-UPDATE-CHECKLIST.md. A public "
            "README is the first thing a judge reads and the last thing anyone "
            "remembers to update." % (m.group(1), age, README_STALE_DAYS)]
    if age < 0:
        return False, ["README.md Status is dated %s, which is in the FUTURE. "
                       "A date nobody can have verified yet is not a "
                       "verification point." % m.group(1)]
    return True, []


PASSES = [("HASH", pass_hash), ("FIXTURES", pass_fixtures), ("SWEEP", pass_sweep),
          ("STATUS", pass_status), ("TERMS", pass_terms),
          ("FRESH", pass_freshness)]


# -----------------------------------------------------------------------------
# SELFTEST. Rewritten 2026-08-23; what it replaced is worth stating.
#
# The old version printed "each pass must report a failure on a deliberately
# broken input" over SEVEN checks that covered THREE of the five passes - HASH
# and TERMS were not exercised at all - and not one of them CALLED A PASS
# FUNCTION. They re-implemented the interesting line of each pass inline
# (`re.search(DEAD[...])`, `jsonschema...iter_errors(bad)`) and asserted the
# regex or the schema behaved. So it measured the primitives while claiming to
# measure the gate, and a pass function could have been deleted, inverted, or
# wired to the wrong global with the selftest still printing PASSED.
#
# That is this repository's own named failure - a check that reports on the
# instrument's behalf - sitting inside the file whose docstring names it.
#
# What replaces it: a THROWAWAY COPY of everything the passes read, one
# deliberate defect per pass, and the real `pass_*()` driven against it. Each
# pass is run TWICE - clean and broken - because a pass that fails on both is
# not detecting the defect, it is just broken, and the old style could not tell
# those apart either.
# -----------------------------------------------------------------------------

_SANDBOX_GLOBALS = ("REPO", "CONTRACTS", "GOLDEN", "DOCS")


@contextlib.contextmanager
def _sandbox():
    """A disposable repository the passes can be pointed at and vandalised.

    The passes read module-level paths, so the sandbox is installed by
    REBINDING THOSE GLOBALS rather than by adding a parameter to five
    signatures. That keeps the selftest driving exactly the code path
    `main()` drives - a pass with a test-only argument is a pass whose tested
    behaviour and shipped behaviour are two different things.

    `docs/CONVENTIONS.md` is copied because `hash-contracts.py` reads
    SPINE_VERSION out of it and refuses to run without it. It is COPIED, never
    written to; the vandalism below only ever touches files under the temp
    directory.
    """
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="contract-check-selftest-"))
    (tmp / "scripts").mkdir()
    shutil.copy2(REPO / "scripts" / "hash-contracts.py", tmp / "scripts")
    shutil.copytree(CONTRACTS, tmp / "contracts")
    (tmp / "docs").mkdir()
    shutil.copy2(REPO / "docs" / "CONVENTIONS.md", tmp / "docs")
    saved = {n: globals()[n] for n in _SANDBOX_GLOBALS}
    globals().update(REPO=tmp, CONTRACTS=tmp / "contracts",
                     GOLDEN=tmp / "contracts" / "golden", DOCS=tmp / "docs")
    try:
        yield tmp
    finally:
        globals().update(saved)
        shutil.rmtree(tmp, ignore_errors=True)


# name -> (pass function, what to break, what the finding should mention)
def _break_hash(tmp):
    """Contract drift: one contract file no longer hashes to MANIFEST.json."""
    p = tmp / "contracts" / "verdict.schema.json"
    p.write_text(p.read_text(encoding="utf-8") + "\nSELFTEST-DRIFT\n",
                 encoding="utf-8")


def _break_fixtures(tmp):
    """A golden POSITIVE that its own schema rejects."""
    (tmp / "contracts" / "golden" / "C9-selftest-empty.valid.json").write_text(
        "{}\n", encoding="utf-8")


def _break_sweep(tmp):
    """A dead value ASSERTED, with no strike or correction marker near it."""
    (tmp / "docs" / "selftest-sweep.md").write_text(
        "# selftest\n\nEvery episode in the run carries four hash-locks.\n",
        encoding="utf-8")


def _break_status(tmp):
    """An undated present-tense claim about an artifact that can be created."""
    (tmp / "docs" / "selftest-status.md").write_text(
        "# selftest\n\nThe service account has not been created.\n",
        encoding="utf-8")


def _break_terms(tmp):
    """A contract using a term MANIFEST.json binds away from it."""
    p = tmp / "contracts" / "verdict.schema.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["$comment"] = "selftest: approver_role"
    p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


BREAKERS = {
    "HASH": (_break_hash, "verdict.schema.json"),
    "FIXTURES": (_break_fixtures, "C9-selftest-empty"),
    "SWEEP": (_break_sweep, "four-hash-locks"),
    "STATUS": (_break_status, "selftest-status.md"),
    "TERMS": (_break_terms, "approver_role"),
}


def selftest():
    """Prove each pass CAN fail, by making it fail. All five, every run."""
    print("SELFTEST - every pass, run clean and run broken, on a throwaway copy\n")
    ok = True
    assert set(BREAKERS) == {n for n, _ in PASSES}, \
        "a pass exists with no deliberate defect authored for it"

    for name, fn in PASSES:
        breaker, expect = BREAKERS[name]

        with _sandbox() as tmp:
            clean_ok, clean_msgs = fn()
        with _sandbox() as tmp:
            breaker(tmp)
            broken_ok, broken_msgs = fn()

        detected = (not broken_ok) and any(expect in m for m in broken_msgs)
        good = clean_ok and detected
        ok &= good
        print("  %-9s %s" % (name, "PASS" if good else "FAIL"))
        if not clean_ok:
            print("      clean sandbox ALREADY FAILS, so the broken run proves "
                  "nothing: %s" % "; ".join(clean_msgs[:3]))
        elif not broken_ok and not detected:
            print("      failed on the broken input but never mentioned %r - "
                  "it found something else: %s"
                  % (expect, "; ".join(broken_msgs[:3])))
        elif broken_ok:
            print("      DID NOT DETECT the deliberate defect. This pass "
                  "cannot fail, and CONVENTIONS 8.2 says that is not a check.")

    # Two SWEEP behaviours that are not a pass/fail of the pass function and
    # would be lost if only the five above were checked. Kept from the old
    # selftest deliberately: both are normalization defects this repo already
    # paid for, and both are invisible at the pass_sweep() level because a
    # correct pass and a blind one both return CLEAN.
    for label, raw, want in (
            ("SWEEP exempts a strike",
             "~~four hash-locks~~ CORRECTED 2026-08-20 to five", False),
            ("SWEEP sees across wrap",
             "so it structurally cannot\nexpress this", True),
            ("SWEEP sees past blockquote",
             "> so it structurally cannot\n> express this", True)):
        norm, _ = normalize(raw)
        pat = DEAD["cannot-express"] if want else DEAD["four-hash-locks"]
        hit = bool(re.search(pat, norm, re.I)) and not EXEMPT.search(norm)
        good = hit == want
        ok &= good
        print("  %-9s %-28s %s" % ("SWEEP", label, "PASS" if good else "FAIL"))

    print("\nSELFTEST %s" % ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    print("contract-check\n")
    failed = 0
    for name, fn in PASSES:
        good, msgs = fn()
        print("  %-9s %s" % (name, "OK" if good else "FAIL (%d)" % len(msgs)))
        if not good:
            failed += 1
            for m in msgs[:25]:
                print("      " + m)
            if len(msgs) > 25:
                print("      ... %d more NOT LISTED (logged, not truncated silently)" % (len(msgs) - 25))
    for cid, why in NO_FIXTURE.items():
        print("\n  NOTE  %s has no golden fixture: %s" % (cid, why))
    print("\n%s" % ("ALL PASSES OK" if not failed else "%d PASS(ES) FAILED" % failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
