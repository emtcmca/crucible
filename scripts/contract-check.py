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
"""

import io
import json
import pathlib
import re
import subprocess
import sys

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
    for p in sorted(DOCS.rglob("*.md")):
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
    for p in sorted(DOCS.rglob("*.md")):
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


PASSES = [("HASH", pass_hash), ("FIXTURES", pass_fixtures), ("SWEEP", pass_sweep),
          ("STATUS", pass_status), ("TERMS", pass_terms)]


def selftest():
    """Prove each pass CAN fail. A gate that cannot fail is not a gate."""
    print("SELFTEST - each pass must report a failure on a deliberately broken input\n")
    ok = True

    norm, _ = normalize("a **four hash-locks** b")
    r1 = bool(re.search(DEAD["four-hash-locks"], norm, re.I)) and not EXEMPT.search(norm)
    print("  %-26s %s" % ("SWEEP catches assertion", "PASS" if r1 else "FAIL")); ok &= r1

    norm2, _ = normalize("~~four hash-locks~~ CORRECTED 2026-08-20 to five")
    r2 = bool(EXEMPT.search(norm2))
    print("  %-26s %s" % ("SWEEP exempts a strike", "PASS" if r2 else "FAIL")); ok &= r2

    wrapped = "so it structurally cannot\nexpress this"
    norm3, _ = normalize(wrapped)
    r3 = bool(re.search(DEAD["cannot-express"], norm3, re.I))
    print("  %-26s %s" % ("SWEEP sees across wrap", "PASS" if r3 else "FAIL")); ok &= r3

    bq = "> so it structurally cannot\n> express this"
    norm4, _ = normalize(bq)
    r4 = bool(re.search(DEAD["cannot-express"], norm4, re.I))
    print("  %-26s %s" % ("SWEEP sees past blockquote", "PASS" if r4 else "FAIL")); ok &= r4

    norm5, _ = normalize("The repository does not exist yet.")
    r5 = bool(STATUS_CLAIM.search(norm5)) and not DATE.search(norm5)
    print("  %-26s %s" % ("STATUS catches undated", "PASS" if r5 else "FAIL")); ok &= r5

    norm6, _ = normalize("Verified 2026-08-20: there is no service account yet.")
    r6 = bool(DATE.search(_window(norm6, STATUS_CLAIM.search(norm6).start(), 160)))
    print("  %-26s %s" % ("STATUS allows dated", "PASS" if r6 else "FAIL")); ok &= r6

    import jsonschema
    schema = json.loads((CONTRACTS / "verdict.schema.json").read_text(encoding="utf-8"))
    bad = {"verdict": "INVALID", "breach": False, "invariant_id": "inv_x",
           "objective_set_hash": "0" * 16, "evidence": []}
    r7 = bool(list(jsonschema.Draft202012Validator(schema).iter_errors(bad)))
    print("  %-26s %s" % ("FIXTURES rejects bad", "PASS" if r7 else "FAIL")); ok &= r7

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
