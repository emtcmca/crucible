#!/usr/bin/env python3
"""contract-check.py - the W0 gate on the contract set.

Eight passes. Every one of them is designed so that IT CAN FAIL, because
CONVENTIONS.md section 8 rule 2 says a check that cannot fail is not measuring
anything - and this repository has already produced two checks that could not:
a sweep that reported CLEAN on hard-wrapped prose, and a negative test that
appended a newline the normalization exists to absorb.

  1  HASH      every contract file still hashes to MANIFEST.json
  2  FIXTURES  every golden positive VALIDATES and every known-bad FAILS
  3  PROVEN    every reason a known-bad DECLARES is a failure it DEMONSTRATES
  4  SWEEP     no dead value is ASSERTED anywhere (strike context exempt)
  5  STATUS    no undated present-tense existence claim   (section 8 rule 12)
  6  CLAIM     no overclaim SHAPE is asserted anywhere    (section 7)
  7  TERMS     no contract redefines a bound term         (section 8 rule 11)
  8  FRESH     README.md's Status anchor is not stale

FIXTURES and PROVEN are different jobs and both are needed. FIXTURES asks
whether a known-bad produced ANY error. PROVEN asks whether it produced THE
errors it promised, one per declared reason. The gap between them was found by
an independent reviewer on 2026-08-29, and it is this repository's signature
defect in its fifteenth instance: reduce transfer_evidence.schema.json in
memory to a single `bundle_kind` const and FIXTURES stays GREEN, because the
valid fixture still validates and the known-bad still produces one error, while
essentially every other C11 constraint has silently disappeared. Multiple
claimed checks represented by one document, where any surviving failure masks
the loss of the others.

SWEEP and CLAIM are different jobs and both are needed. SWEEP catches a value
that USED TO BE TRUE - a number that moved. CLAIM catches a sentence that was
NEVER TRUE - a shape the evidence cannot support at any value. A dead-value
sweep would never have caught "writes its own attacks", because no version of
that sentence was ever correct.

Run:  python scripts/contract-check.py
      python scripts/contract-check.py --selftest   # prove each pass can fail

`--selftest` runs ALL SEVEN against a throwaway copy of the repository, once
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

# REPO is REBOUND by `_sandbox()`. SOURCE_REPO never is, so anything that has to
# import the application package (the PROVEN pass reaches the replay reader for
# C6's reader-side reasons) resolves against the real tree rather than against a
# temp directory that holds contracts and nothing else.
SOURCE_REPO = pathlib.Path(__file__).resolve().parent.parent

# The reason-to-failure bindings the PROVEN pass reads. Under `contracts/golden/
# proof/` rather than beside the fixtures because `pass_fixtures` globs
# `contracts/golden/*.json` and treats every file it finds as an instance
# needing a mapped schema. Both golden globs are non-recursive, so a
# subdirectory is invisible to them.
PROOF = GOLDEN / "proof"
BINDINGS = PROOF / "must-fail-bindings.json"


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
    # The judge-facing set. README.md was split on 2026-08-26 into four
    # top-level documents so the first screen could answer a judge's five
    # questions; every one of them is named here in the same breath, because
    # the whole reason README.md rotted is that it lived outside this walk.
    # A split that moved the rigor out of the checked file and into unchecked
    # ones would have made the coverage hole four times bigger.
    for name in ("README.md", "CLAUDE.md",
                 "AUDIT.md", "MEASUREMENT.md", "ARCHITECTURE.md", "RESULTS.md"):
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
    "C11": "transfer_evidence.schema.json",
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
    # markdown emphasis around the number broke every one of these until
    # 2026-08-25: `become **FIVE**` flagged while `become FIVE` exempted, so a
    # correction document that BOLDED the number reported itself as drift. A
    # check with a high false-positive rate gets switched off, which is the
    # reason the STATUS pass had to be rescoped once already.
    r"become[sd]?\s+[*`_]*FIVE|becomes?\s+[*`_]*five|now\s+[*`_]*five|"
    r"are\s+[*`_]*five|to\s+[*`_]*five|"
    # prose citing a NUMBERED RULING as the source of the change is correction
    # prose by construction. Narrow on purpose: it requires the ruling number.
    r"since\s+ruling\s+\d|per\s+ruling\s+\d|"
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


# -----------------------------------------------------------------------------
# Pass 3 - PROVEN. A declared reason must be a demonstrated failure.
#
# `_must_fail_because` is prose, and prose cannot be checked. The binding file
# is the machine-checkable half: per declared reason, the JSON Pointer and the
# schema keyword that must fire there. Twelve findings, and each one is a way
# the old check stayed green while measuring less than it claimed:
#
#   P0_MALFORMED           a reason declaring no mechanism at all
#   P1_NO_BINDING          a known-bad on disk with no entry - how the hole reopens
#   P2_COUNT               fewer bindings than reasons; the remainder is decoration
#   P3_CLAIM_DRIFT         the reason was rewritten and the binding was not
#   P4_UNDEMONSTRATED      the promised failure does not happen. THE CENTRAL ONE.
#   P4_UNENFORCED_STALE    a recorded gap that has quietly closed
#   P5_DUPLICATE_EVIDENCE  two reasons, one failure. N reasons must be N failures
#   P6_EXTERNAL_MISSING    a reader-side code that never fires
#   P6_EXTERNAL_STALE      a not_reachable escape that does fire
#   P7_UNEXPLAINED         the ruling-43 shape: a failure the list does not name
#   P7_UNEXPLAINED_STALE   a recorded unexplained error that no longer happens
#   P8_ORPHAN              a binding for a fixture nobody wrote
#
# WHY THE ERROR POOL IS `iter_errors` AND NOT ITS `context` DESCENDANTS. A
# `oneOf` reports one error at the parent with the branch failures underneath
# it. C6 reason 4 promises exactly that parent - "the episode names NEITHER
# attack_id NOR fixture_id" IS the oneOf - and pulling the children into the
# pool would make them unexplained errors nobody can honestly claim. The pool is
# the failures a consumer sees, which is what a promise is about.
#
# WHY `unenforced` IS AN ESCAPE AND WHY IT IS NOT A RUBBER STAMP. Seven reasons
# across four contracts describe rejections their schema does not perform. Those
# fixtures are generated by `scripts/make-golden.py` and validated against
# schemas owned by other lanes, so the honest record is the gap itself: what the
# reason claims, what constraint would enforce it, and `would_be` - the evidence
# triple the reason WOULD produce. The gate asserts that triple does NOT match
# today. A gap that closes makes its own record stale and turns the gate RED,
# which is how the record gets promoted rather than living here forever. Same
# doctrine as `<!-- sweep-ok: why -->` in the SWEEP pass: an explicit, auditable
# decision that shows up in a diff, never a widened heuristic.
# -----------------------------------------------------------------------------

PROVEN_NOTES = []


def _pointer(path):
    """RFC 6901 pointer for a jsonschema `absolute_path`. Root is ''."""
    return "".join("/" + str(part) for part in path)


def _triple(spec):
    return (spec.get("path", ""), spec.get("keyword", ""), spec.get("detail", ""))


def _matches(triple, err):
    path, keyword, detail = triple
    if _pointer(err.absolute_path) != path or err.validator != keyword:
        return False
    return (not detail) or (detail in err.message)


def _reader_codes(body):
    """Defect codes the offline replay reader emits for this instance.

    Imported here rather than at module scope: the gate must run on a checkout
    with no application package importable, and a missing reader has to be a
    FINDING rather than a crash or, worse, a silent skip.
    """
    if str(SOURCE_REPO) not in sys.path:
        sys.path.insert(0, str(SOURCE_REPO))
    from crucible.replay import verify_bundle
    return {d.code for d in verify_bundle(body).defects}


def pass_proven():
    import jsonschema
    del PROVEN_NOTES[:]
    fails = []
    if not BINDINGS.exists():
        return False, ["%s does not exist. Without it the fixture pass asks only "
                       "whether a known-bad produced SOME error, which is the "
                       "state an independent reviewer broke on 2026-08-29 by "
                       "reducing a schema to one constraint."
                       % BINDINGS.name]
    doc = json.loads(BINDINGS.read_text(encoding="utf-8"))
    entries = doc.get("fixtures", {})
    reg = _registry()

    on_disk = sorted(p for p in GOLDEN.glob("*.json") if "KNOWN_BAD" in p.name)
    for p in on_disk:
        if p.name not in entries:
            fails.append("P1_NO_BINDING  %s has no entry in %s. Its declared "
                         "reasons are unchecked prose." % (p.name, BINDINGS.name))
    for name in sorted(entries):
        if not (GOLDEN / name).exists():
            fails.append("P8_ORPHAN  %s is bound in %s and is not on disk."
                         % (name, BINDINGS.name))

    demonstrated = unenforced_total = external_total = 0

    for fx in on_disk:
        entry = entries.get(fx.name)
        if entry is None:
            continue
        cid = fx.name.split("-")[0]
        schema_file = FIXTURE_SCHEMA.get(cid)
        if not schema_file:
            fails.append("P0_MALFORMED  %s: no schema mapped for %s" % (fx.name, cid))
            continue

        body = json.loads(fx.read_text(encoding="utf-8"))
        declared = body.pop("_must_fail_because", None)
        body.pop("_note", None)
        if isinstance(declared, str):          # C10 states its single reason as prose
            declared = [declared]
        if not isinstance(declared, list) or not declared:
            fails.append("P0_MALFORMED  %s declares no _must_fail_because list"
                         % fx.name)
            continue

        schema = json.loads((CONTRACTS / schema_file).read_text(encoding="utf-8"))
        errs = list(jsonschema.Draft202012Validator(
            schema, registry=reg).iter_errors(body))

        reasons = entry.get("reasons", [])
        if len(reasons) != len(declared):
            fails.append(
                "P2_COUNT  %s declares %d reasons and %s binds %d. The unbound "
                "remainder is decoration: nothing asks whether it fires."
                % (fx.name, len(declared), BINDINGS.name, len(reasons)))
            continue

        claimed = []        # triples any reason claims, for the coverage half
        seen = {}           # triple -> first reason index that claimed it
        for pos, reason in enumerate(reasons):
            if reason.get("index") != pos:
                fails.append("P0_MALFORMED  %s reason %d carries index %r; the "
                             "list is positional" % (fx.name, pos, reason.get("index")))
                continue
            text = declared[pos]
            claim = reason.get("claim", "")
            if not claim or claim not in text:
                fails.append(
                    "P3_CLAIM_DRIFT  %s reason %d: the binding quotes %r, which "
                    "is not in the reason it is bound to. The reason moved and "
                    "the binding did not." % (fx.name, pos, claim[:70]))
                continue

            mechanisms = [k for k in ("evidence", "external", "unenforced")
                          if k in reason]
            if len(mechanisms) != 1:
                fails.append(
                    "P0_MALFORMED  %s reason %d declares %d mechanisms (%s). "
                    "Exactly one of evidence / external / unenforced."
                    % (fx.name, pos, len(mechanisms), ", ".join(mechanisms) or "none"))
                continue

            if "evidence" in reason:
                for spec in reason["evidence"]:
                    triple = _triple(spec)
                    if triple in seen:
                        fails.append(
                            "P5_DUPLICATE_EVIDENCE  %s reasons %d and %d both "
                            "claim %s. Two reasons, one failure: the surviving "
                            "error stands in for both, which is the masking this "
                            "pass exists to catch."
                            % (fx.name, seen[triple], pos, triple))
                        continue
                    seen[triple] = pos
                    claimed.append(triple)
                    if not any(_matches(triple, e) for e in errs):
                        fails.append(
                            "P4_UNDEMONSTRATED  %s reason %d promises %s and no "
                            "such error is produced. The fixture claims a "
                            "rejection the schema does not perform: %s"
                            % (fx.name, pos, triple, text[:90]))
                    else:
                        demonstrated += 1

            elif "unenforced" in reason:
                gap = reason["unenforced"]
                if not gap.get("needs") or not gap.get("why_now"):
                    fails.append("P0_MALFORMED  %s reason %d is recorded "
                                 "unenforced with no `needs`/`why_now`"
                                 % (fx.name, pos))
                    continue
                would = _triple(gap.get("would_be", {}))
                if any(_matches(would, e) for e in errs):
                    fails.append(
                        "P4_UNENFORCED_STALE  %s reason %d is recorded as not "
                        "enforced, and %s now fires. The gap closed. Promote the "
                        "record to `evidence`." % (fx.name, pos, would))
                else:
                    unenforced_total += 1
                    PROVEN_NOTES.append(
                        "UNENFORCED  %s reason %d: %s  -> needs: %s"
                        % (fx.name, pos, claim[:56], gap["needs"][:110]))

            else:
                ext = reason["external"]
                code = ext.get("code", "")
                try:
                    codes = _reader_codes(body)
                except Exception as exc:                     # noqa: BLE001
                    fails.append(
                        "P6_EXTERNAL_MISSING  %s reason %d names reader code %r "
                        "and the reader could not be run: %s. An unrunnable "
                        "check is not a passing one."
                        % (fx.name, pos, code, str(exc)[:80]))
                    continue
                if ext.get("not_reachable"):
                    if code in codes:
                        fails.append(
                            "P6_EXTERNAL_STALE  %s reason %d records %s as not "
                            "reachable in this fixture and it fires. The escape "
                            "is stale." % (fx.name, pos, code))
                    else:
                        external_total += 1
                elif code not in codes:
                    fails.append(
                        "P6_EXTERNAL_MISSING  %s reason %d promises reader code "
                        "%s and the reader does not emit it for this fixture."
                        % (fx.name, pos, code))
                else:
                    external_total += 1

        # The other direction. A failure the list does not name is the ruling-43
        # shape: a lane repairing every declared reason still sees red with
        # nothing to tell it why.
        recorded = [(_triple(u), u) for u in entry.get("unexplained_errors", [])]
        for triple, spec in recorded:
            if not any(_matches(triple, e) for e in errs):
                fails.append(
                    "P7_UNEXPLAINED_STALE  %s records %s as an unexplained "
                    "error and it no longer fires. A record that excuses nothing "
                    "reads as coverage." % (fx.name, triple))
            if not spec.get("why"):
                fails.append("P0_MALFORMED  %s records %s with no `why`"
                             % (fx.name, triple))
        for e in errs:
            if any(_matches(t, e) for t in claimed):
                continue
            if any(_matches(t, e) for t, _ in recorded):
                continue
            fails.append(
                "P7_UNEXPLAINED  %s fails at %s on `%s` and its "
                "_must_fail_because names no such reason: %s"
                % (fx.name, _pointer(e.absolute_path) or "(root)", e.validator,
                   e.message.replace("\n", " ")[:90]))

    PROVEN_NOTES.append(
        "%d reasons demonstrated by a named schema failure, %d by a reader code, "
        "%d recorded as NOT ENFORCED by the schema."
        % (demonstrated, external_total, unenforced_total))
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


# -----------------------------------------------------------------------------
# Pass 6 - CLAIM. Overclaim SHAPES, not dead values.
#
# SWEEP catches a value that used to be true. This catches a sentence that was
# never true. Every pattern below is a mistake THIS PROJECT MADE in the week
# before it was written, which is the only justification for a prose lint: a
# generic marketing-adjective filter is theatre, and it gets switched off the
# first time it fires on something harmless.
#
# The eight shapes, and where each came from:
#
#   red-authors-attacks   RED discovery is a DESIGN. Nothing in the tree authors
#                         an attack; `vary()` preserves the seed's attack_id.
#                         "CRUCIBLE writes its own attacks" is the single most
#                         attractive false sentence available to this project.
#   zero-regressions      The benign floor is a BOUND. 26/26 bounds the
#                         unobserved regression rate at ~11.5% by the rule of
#                         three. "Zero regressions" is the phrasing CONVENTIONS
#                         section 7 forbids by name.
#   vendor-adjectives     "Production-ready" / "enterprise-grade". Eleven days,
#                         one person, one target agent. CONVENTIONS section 7.
#   promotion-is-fix      A promotion is a gate outcome, not a remediation. A
#                         rule can promote and close nothing at all, and this
#                         repository has measured exactly that.
#   unexercised-defence   A clause that has never fired defends nothing yet. The
#                         money invariants are the live instance: they exist, and
#                         "protected by five money invariants" would be a claim
#                         about a capability no run has exercised.
#   seeded-batch-coverage A fixed-seed batch samples. A batch that sampled part
#                         of the corpus is not "full coverage", and the gap
#                         between instances-existing and instances-reached is
#                         exactly what a coverage word hides.
#   replay-is-reattack    The Warden REPLAYS recorded traces against a candidate
#                         policy. It does not attack anything: nothing is
#                         persuaded, no model is called, no target runs.
#   fixture-is-evidence   `contracts/golden/` holds hand-authored instances with
#                         synthetic run ids. They exercise the schema and the
#                         viewer. They are not runs and prove nothing about one.
#
# HOW A LEGITIMATE MENTION ESCAPES. Exactly the way it does in SWEEP, through
# `_exempt`: a strike (`~~...~~`), a correction marker (CORRECTED, NEVER, "do
# not write", DEAD...), or the explicit, auditable `<!-- sweep-ok: why -->`
# comment on the line above. That handling is REUSED rather than reinvented so
# there is one exemption rule in this file, not two that can drift apart. It is
# why CONVENTIONS section 7's own "Never say this" list does not report itself,
# and why a LANDMINES table quoting a dead phrase to retire it stays clean - the
# defect a previous version of this gate shipped.
#
# The patterns themselves live HERE, in Python, and `swept_markdown()` walks
# markdown only, so this list cannot flag itself. That is structure, not luck,
# and it is the reason the list is not restated in a doc.
# -----------------------------------------------------------------------------
CLAIM = {
    "red-authors-attacks": (
        r"(?:writes?|authors?|generates?|invents?|discovers?|synthesi[sz]es?)\s+"
        r"(?:its|their|our|his|her)\s+own\s+(?:novel\s+|new\s+)?attacks?"
        r"|autonomous\w*\s+(?:\w+\s+){0,2}?"
        r"(?:writ\w+|author\w+|generat\w+|discover\w+|invent\w+)\s+"
        r"(?:new\s+|novel\s+|its\s+own\s+)?attacks?"
        r"|attack\s+discovery\s+is\s+(?:shipped|built|working|live|implemented)"),
    # The harness context is IN the pattern, both orders, because "no
    # regression suite" is a description of the problem this project exists
    # inside and "zero regressions" about a test-count migration is a different
    # sentence about a different thing. Only a regression claim about the
    # POLICY or the BENIGN floor is the claim CONVENTIONS section 7 forbids.
    "zero-regressions": (
        r"\b(?:zero|no)\s+regressions?\b(?![-\s]*(?:suite|test|harness|floor))"
        r"[^.]{0,80}?\b(?:polic|benign|fixture|promot|rule|capabilit|agent)"
        r"|\b(?:polic\w+|benign|fixtures?|promot\w+|rules?)\b[^.]{0,80}?"
        r"\b(?:zero|no)\s+regressions?\b(?![-\s]*(?:suite|test|harness|floor))"
        r"|\bregression[-\s]free\b"
        r"|\bwithout\s+(?:any\s+|a\s+single\s+)?regressions?\b"),
    "vendor-adjectives": r"\benterprise[-\s]grade\b|\bproduction[-\s]ready\b",
    "promotion-is-fix": (
        r"\bpromot\w+\s+(?:rules?|polic\w+|patch\w*)[^.]{0,80}?"
        r"\b(?:closed|fixed|remediat\w+|eliminat\w+)\b"
        r"|\bpromotion\b[^.]{0,50}?\b(?:proves|means|shows|demonstrates|"
        r"is\s+evidence)\b[^.]{0,50}?\b(?:fix\w*|remediat\w+|closed|hardened)\b"
        r"|\b\d+\s+(?:rules?|patches)\s+(?:were\s+)?promoted[^.]{0,60}?"
        r"\b(?:so|therefore|hence|which\s+means)\b[^.]{0,60}?"
        r"\b(?:fixed|closed|safe|hardened|remediat\w+)\b"),
    "unexercised-defence": (
        r"\bmoney\s+(?:invariants?|clauses?)\b[^.]{0,60}?"
        r"\b(?:defend|protect|prevent|block|stop)\w*"
        r"|\b(?:defended|protected|guarded|covered)\s+by\s+"
        r"(?:five|\d+)\s+(?:money\s+)?(?:invariants?|clauses?)"
        r"|\b(?:all\s+)?(?:five|\d+)\s+money\s+(?:invariants?|clauses?)\s+"
        r"(?:hold|are\s+enforced|are\s+in\s+force|protect\w*)"),
    "seeded-batch-coverage": (
        r"\b(?:full|complete|exhaustive|comprehensive|broad|total)\s+"
        r"(?:corpus\s+|attack\s+|instance\s+)?coverage\b"
        r"|\bcover(?:s|ed|ing)?\s+the\s+(?:whole|entire|full)\s+corpus\b"
        r"|\bevery\s+(?:attack\s+|corpus\s+)?instance\s+(?:was|is|has\s+been)\s+"
        r"(?:run|attempted|exercised|attacked|reached)\b"),
    # ASSERTION GRAMMAR, not proximity. The first alternative used to be
    # `repla\w+ [^.]{0,50} re-?attack`, which fired on the honest sentence
    # "a REPLAY of recorded calls, not a re-attack" and on this repository's own
    # description of this pattern. Naming the two words near each other is what
    # DRAWING the distinction looks like; only a copula asserts it.
    "replay-is-reattack": (
        r"\brepla\w+\s+(?:is|was|are|were|acts?\s+as)\s+(?:a\s+)?re-?attack"
        r"|\brepla\w+\s+(?:the\s+|each\s+|every\s+)?attacks?\s+(?:against|at|on)\s+"
        r"(?:the\s+)?(?:target|agent)\b"
        r"|\b(?:warden|replay)\w*\s+(?:re-?)?attacks?\s+the\s+(?:target|agent)\b"),
    "fixture-is-evidence": (
        r"\bgolden\s+(?:\w+\s+){0,2}?fixtures?\b[^.]{0,60}?"
        r"\bis\s+(?:a\s+)?(?:real\s+)?(?:run|result|measurement|evidence)\b"
        r"|\b(?:evidence|proof|results?)\s+from\s+(?:the\s+|a\s+)?golden\s+"
        r"(?:\w+\s+){0,2}?fixtures?\b"
        r"|\bC6-evidence_bundle\.valid\.json\b[^.]{0,60}?"
        r"\b(?:is|was)\s+(?:a\s+)?(?:real\s+)?run\b"),
}


# PER-PATTERN GUARDS. A guard is not a general exemption. It names the ONE
# neighbouring construction that turns this particular shape from an assertion
# into a denial, a distinction, or a mention, and it is written per label
# rather than widened into the shared EXEMPT regex - because a widening that
# helps one pattern and blinds the other seven is how a check stops being able
# to fail at all.
#
# The disclaimer case is not hypothetical. `docs/devpost/findings-and-learnings.md`
# records the ancestor of this pass failing on exactly it: "When the README grew
# a section stating, correctly, 'Not production-ready. Not enterprise-grade,'
# all three sentences tripped the same gate built to ban those phrases, because
# it was matching the words, not the assertion." A quoted phrase and a negated
# phrase are both MENTIONS. Only an assertion is a claim.
CLAIM_GUARD = {
    "vendor-adjectives": re.compile(
        r"\bnot\s+(?:production|enterprise)"
        r"|\bban(?:s|ned)?\b|\bwarns?\s+against\b|\btripp?ed\b"
        r"|[\"'`\u201c\u201d]\s*(?:production[-\s]ready|enterprise[-\s]grade)", re.I),
    "zero-regressions": re.compile(
        r"\bregressions?\s+(?:suite|test|harness|floor)\b"
        r"|\bupper\s+bound\b|\brule\s+of\s+three\b|\bbounds?\s+the\b", re.I),
    "replay-is-reattack": re.compile(
        r"\b(?:not|never)\s+(?:a\s+)?re-?attack"
        r"|\brather\s+than\s+(?:a\s+)?(?:re-?attack|attacking)", re.I),
    "fixture-is-evidence": re.compile(
        r"\b(?:not|never)\s+(?:a\s+)?(?:run|result|measurement|evidence)\b", re.I),
    "promotion-is-fix": re.compile(
        r"\bclosed\s+nothing\b|\bno-?ops?\b|\bdid\s+not\s+close\b"
        # "USD per breach closed" NAMES A RATIO. `closed` there is part of the
        # metric's name, not a predicate asserting that anything was closed.
        r"|\bper\s+(?:breach|attack|rule)\s+(?:closed|fixed|remediated)\b", re.I),
}


# CLAIM'S ONE DEVIATION FROM THE SHARED EXEMPTION VOCABULARY, and it is a
# deviation of CASE rather than of vocabulary.
#
# EXEMPT is case-insensitive, and for SWEEP it must be: "was wrong", "stale" and
# "previously" mark a correction in ordinary lowercase prose. But two of its
# tokens are SHOUTED MARKERS in this repository - `CLOSED`, `RESOLVED` - and in
# lowercase they are ordinary English verbs. "the promoted rules closed the
# breaches" is the exact sentence `promotion-is-fix` exists to catch, and
# EXEMPT's case-insensitive `CLOSED` silences it. A guard that silences a
# pattern on every sentence it was written for is not a guard.
#
# So CLAIM reuses EXEMPT WHOLESALE - the strike, the `<!-- sweep-ok -->` escape,
# the whole correction vocabulary - and re-imposes case on exactly those two.
# Subtracting two named tokens is auditable and shows up in a diff. Writing a
# second exemption vocabulary would be two rules that drift apart, which is the
# thing this repository has a ruling about.
_AMBIGUOUS_MARKERS = re.compile(r"\b(?:closed|resolved)\b", re.I)
_AMBIGUOUS_SHOUTED = re.compile(r"\b(?:CLOSED|RESOLVED)\b")


def _claim_exempt(norm, i, src_lines, line_no):
    """`_exempt`, with the two ambiguous markers re-cased. Same two views."""
    lo, hi = max(0, line_no - 2), min(len(src_lines), line_no + 1)
    block = " ".join(src_lines[lo:hi])
    if SWEEP_OK.search(block):
        return True
    for text in (_window(norm, i), block):
        if _AMBIGUOUS_SHOUTED.search(text):
            return True
        if EXEMPT.search(_AMBIGUOUS_MARKERS.sub(" ", text)):
            return True
    return False


def pass_claim():
    """A sentence that was NEVER true, as opposed to one that stopped being true.

    Reported with the pattern label AND the matched text, because "overclaim in
    README.md:412" without the sentence sends the reader hunting, and a finding
    that is expensive to act on is a finding that gets ignored.
    """
    hits = []
    for p in sorted(swept_markdown()):
        raw = p.read_text(encoding="utf-8", errors="replace")
        src_lines = raw.split("\n")
        norm, lmap = normalize(raw)
        for label, pat in CLAIM.items():
            guard = CLAIM_GUARD.get(label)
            for m in re.finditer(pat, norm, re.I):
                if guard and guard.search(_window(norm, m.start(), 110)):
                    continue
                if _claim_exempt(norm, m.start(), src_lines, lmap[m.start()]):
                    continue
                hits.append("%s:%d overclaim [%s]: %r" % (
                    p.relative_to(REPO).as_posix(), lmap[m.start()], label,
                    norm[m.start():m.start() + 70].strip()))
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


PASSES = [("HASH", pass_hash), ("FIXTURES", pass_fixtures),
          ("PROVEN", pass_proven), ("SWEEP", pass_sweep),
          ("STATUS", pass_status), ("CLAIM", pass_claim), ("TERMS", pass_terms),
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

_SANDBOX_GLOBALS = ("REPO", "CONTRACTS", "GOLDEN", "DOCS", "PROOF", "BINDINGS")


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
    # README.md is COPIED for the same reason CONVENTIONS.md is: `pass_freshness`
    # reads it off REPO, so without it here the pass raises in the sandbox instead
    # of failing cleanly, and NO BREAKER COULD BE WRITTEN FOR IT. That is exactly
    # why FRESH shipped 2026-08-25 with no selftest entry and why `--selftest` has
    # been exiting 1 ever since: the assertion below caught it, and nothing ran it.
    shutil.copy2(REPO / "README.md", tmp / "README.md")
    saved = {n: globals()[n] for n in _SANDBOX_GLOBALS}
    globals().update(REPO=tmp, CONTRACTS=tmp / "contracts",
                     GOLDEN=tmp / "contracts" / "golden", DOCS=tmp / "docs",
                     PROOF=tmp / "contracts" / "golden" / "proof",
                     BINDINGS=(tmp / "contracts" / "golden" / "proof"
                               / "must-fail-bindings.json"))
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


def _break_proven(tmp):
    """THE REVIEWER'S OWN MUTATION, run as the deliberate defect.

    `transfer_evidence.schema.json` is reduced to a single `bundle_kind` const.
    FIXTURES stays green through this - the valid fixture still validates and
    the known-bad still produces one error - which is precisely the finding. The
    C11 known-bad promises eight distinct failures; after the reduction it can
    demonstrate one, and PROVEN must name the other seven.

    Chosen over an easier defect (deleting a binding, misquoting a claim) on
    purpose: those would prove the bookkeeping rules fire. This proves the pass
    detects the thing it was written for, on the exact input that exposed it.
    """
    p = tmp / "contracts" / "transfer_evidence.schema.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    p.write_text(json.dumps({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": doc["$id"],
        "type": "object",
        "properties": {"bundle_kind": {"const": "transfer_evidence"}},
    }, indent=2) + "\n", encoding="utf-8")


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


def _break_claim(tmp):
    """A sentence that was never true, asserted with no strike or correction.

    Deliberately a NOVELTY claim rather than a banned adjective. An adjective
    breaker would prove only that a literal string match works, and a literal
    string match is the one thing about this pass nobody doubts. The novelty
    shape is the one with a real grammar behind it, so it is the one worth
    proving fires. The other seven are exercised by the per-pattern matrix in
    `selftest()`, positive AND negative, so no pattern here is unproven.
    """
    (tmp / "docs" / "selftest-claim.md").write_text(
        "# selftest\n\nCRUCIBLE writes its own attacks, round after round.\n",
        encoding="utf-8")


def _break_terms(tmp):
    """A contract using a term MANIFEST.json binds away from it."""
    p = tmp / "contracts" / "verdict.schema.json"
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["$comment"] = "selftest: approver_role"
    p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _break_fresh(tmp):
    """A README Status anchor backdated past the staleness limit.

    Backdated rather than deleted, deliberately. Deleting the anchor also fails
    the pass, but by the OTHER branch, so it would prove the pass notices a
    missing anchor and prove nothing at all about whether it notices STALENESS,
    which is the thing the pass exists for.
    """
    import datetime
    p = tmp / "README.md"
    stale = datetime.date.today() - datetime.timedelta(days=README_STALE_DAYS + 5)
    text = README_ASOF.sub("**As of %s" % stale.isoformat(),
                           p.read_text(encoding="utf-8", errors="replace"), count=1)
    p.write_text(text, encoding="utf-8")


BREAKERS = {
    "HASH": (_break_hash, "verdict.schema.json"),
    "FIXTURES": (_break_fixtures, "C9-selftest-empty"),
    "PROVEN": (_break_proven, "P4_UNDEMONSTRATED"),
    "SWEEP": (_break_sweep, "four-hash-locks"),
    "STATUS": (_break_status, "selftest-status.md"),
    "CLAIM": (_break_claim, "red-authors-attacks"),
    "TERMS": (_break_terms, "approver_role"),
    "FRESH": (_break_fresh, "days old"),
}


def selftest():
    """Prove each pass CAN fail, by making it fail. All six, every run."""
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

    # EVERY CLAIM PATTERN, BOTH DIRECTIONS. The breaker above proves the pass
    # can fail; it exercises one pattern of eight, and a pattern nothing
    # exercises is a pattern that could be a typo'd regex matching nothing
    # forever - the SWEEP defect of 2026-08-20 with a new label.
    #
    # The NEGATIVE half is the one that earns its place. Each row's second
    # string is a correction note QUOTING THE SAME DEAD PHRASE IN ORDER TO
    # RETIRE IT, which is what a LANDMINES table and a superseded ADR both look
    # like. A gate that reports those as findings gets switched off within a
    # day, and then it is not a gate. Both halves must hold for the row to pass.
    for label, overclaim, correction in (
            ("red-authors-attacks",
             "The red strategist writes its own attacks each round.",
             "~~writes its own attacks~~ CORRECTED: RED discovery is a design."),
            ("zero-regressions",
             "The promoted policy shipped with zero regressions.",
             "Never write \"zero regressions\": the benign floor is a bound."),
            ("vendor-adjectives",
             "An enterprise-grade, production-ready hardening harness.",
             "\"Production-ready\" is DEAD vocabulary here - eleven days, one person."),
            ("promotion-is-fix",
             "The 31 promoted rules closed the breaches they were written for.",
             "~~promoted rules closed the breaches~~ STRUCK: 18 of 31 closed nothing."),
            ("unexercised-defence",
             "The money invariants prevent every unauthorised transfer.",
             "Do not write that the money invariants prevent anything: none has fired."),
            ("seeded-batch-coverage",
             "The batch gave us full corpus coverage.",
             "\"full corpus coverage\" was wrong: the batch reached part of the corpus."),
            ("replay-is-reattack",
             "The warden replays the attacks against the target.",
             "It is NEVER true that the warden replays the attacks against the target."),
            ("fixture-is-evidence",
             "The golden bundle fixture is a real run of the loop.",
             "~~the golden fixture is a real run~~ CORRECTED: its run_id is synthetic."),
    ):
        pat, guard = CLAIM[label], CLAIM_GUARD.get(label)

        def _flags(text):
            """Exactly what `pass_claim` does to one line, and nothing else.

            Not a re-implementation of the interesting line - that is the
            defect this whole SELFTEST section replaced. Same pattern, same
            guard, same `_claim_exempt`.
            """
            norm, _ = normalize(text)
            m = re.search(pat, norm, re.I)
            if m is None:
                return False
            if guard and guard.search(_window(norm, m.start(), 110)):
                return False
            return not _claim_exempt(norm, m.start(), [text], 1)

        fires, quiet = _flags(overclaim), not _flags(correction)
        good = fires and quiet
        ok &= good
        print("  %-9s %-24s %s%s" % (
            "CLAIM", label, "PASS" if good else "FAIL",
            "" if good else ("   (fires=%s on the overclaim, quiet=%s on the "
                             "correction note)" % (fires, quiet))))

    # THE SHIPPED STRAWMAN SET. The sandbox breaker above proves PROVEN detects
    # the reviewer's schema reduction; it exercises ONE of twelve findings. The
    # other eleven are bookkeeping rules, and a bookkeeping rule that stopped
    # firing would be invisible - which is how the hole reopens without anyone
    # deciding to reopen it.
    #
    # `contracts/golden/proof/selftest/` holds three known-bad fixtures and a
    # DELIBERATELY DEFECTIVE binding file, one wrong way per rule. The REAL
    # `pass_proven()` is pointed at them by rebinding the same globals
    # `_sandbox()` rebinds, so this drives the shipped code path rather than a
    # re-implementation of its interesting line - the defect that the whole of
    # this SELFTEST section replaced.
    straw_dir = PROOF / "selftest"
    saved = {n: globals()[n] for n in ("GOLDEN", "BINDINGS")}
    globals().update(GOLDEN=straw_dir,
                     BINDINGS=straw_dir / "strawman-bindings.json")
    try:
        straw_ok, straw_msgs = pass_proven()
    finally:
        globals().update(saved)

    expected_codes = ("P0_MALFORMED", "P1_NO_BINDING", "P2_COUNT",
                      "P3_CLAIM_DRIFT", "P4_UNDEMONSTRATED",
                      "P4_UNENFORCED_STALE", "P5_DUPLICATE_EVIDENCE",
                      "P6_EXTERNAL_MISSING", "P6_EXTERNAL_STALE",
                      "P7_UNEXPLAINED", "P7_UNEXPLAINED_STALE", "P8_ORPHAN")
    print()
    for code in expected_codes:
        caught = any(m.startswith(code) for m in straw_msgs)
        ok &= caught
        print("  %-9s %-24s %s" % ("PROVEN", code, "PASS" if caught else
                                   "FAIL   (the strawman for it was not named)"))
    # A checker that flags everything is as useless as one that flags nothing.
    # C9-strawman reason 0 is bound CORRECTLY and must be quiet.
    quiet = not any("C9-strawman.KNOWN_BAD.json reason 0" in m for m in straw_msgs)
    ok &= quiet
    print("  %-9s %-24s %s" % ("PROVEN", "correct binding is quiet",
                               "PASS" if quiet else "FAIL"))
    if straw_ok:
        print("      THE STRAWMAN BINDING SET WAS ACCEPTED. Every rule in this "
              "pass is unproven.")
        ok = False

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
    # PRINTED EVERY RUN, GREEN OR RED. A gap that is only visible when the gate
    # is already failing is a gap nobody reads.
    for note in PROVEN_NOTES:
        print("  NOTE  " + note)
    print("\n%s" % ("ALL PASSES OK" if not failed else "%d PASS(ES) FAILED" % failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
