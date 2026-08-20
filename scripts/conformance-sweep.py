#!/usr/bin/env python3
"""conformance-sweep.py - the NEGATIVE-CHECK CENSUS. W0 item 3, second half.

CONVENTIONS.md section 8 rule 2: a check that cannot fail is not measuring
anything, and every lane's FIRST work item is its negative check. That rule is
worth exactly as much as our ability to say, at any moment, WHICH negative
checks are required and WHICH ones exist.

This script answers that question and nothing else. It does NOT run lane tests -
lane code does not exist during W0, and a census that silently reported zero
required checks would itself be a check that cannot fail.

  REQUIRED   every negative check declared in a contract or a lane brief
  PRESENT    whether a test asserting it exists yet
  STATUS     REQUIRED-NOT-YET-BUILT during W0; a lane turns it green

Run:  python scripts/conformance-sweep.py
      python scripts/conformance-sweep.py --strict   # exit 1 on any gap
"""

import io
import pathlib
import re
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = pathlib.Path(__file__).resolve().parent.parent
CONTRACTS = REPO / "contracts"
LANES = REPO / "docs" / "lanes"
TESTS = REPO / "tests"

# A negative check is declared in one of three shapes across the frozen set.
DECL = [
    # contracts/policy.ebnf carries an explicit N1..N7 block
    (re.compile(r"^\s*(N\d)\s+(.{10,140})", re.M), "C4:policy.ebnf"),
]

MUSTFAIL = re.compile(r"(?:MUST BE A PARSE ERROR|MUST BE REJECTED|MUST MATCH|"
                      r"must be a parse error|must be rejected|must match|"
                      r"must FAIL|must be caught|assert the build \*\*fails\*\*|"
                      r"must be \*\*rejected\*\*)", re.I)


def from_ebnf():
    out = []
    txt = (CONTRACTS / "policy.ebnf").read_text(encoding="utf-8")
    block = txt.split("NEGATIVE CHECKS")[-1]
    for m in re.finditer(r"^\s+(N\d)\s+(.+?)(?=^\s+N\d|\Z)", block, re.M | re.S):
        desc = " ".join(m.group(2).split())
        out.append(("C4", m.group(1), desc[:150]))
    return out


def from_briefs():
    out = []
    for p in sorted(LANES.glob("L?-*.md")):
        lane = p.name.split("-")[0]
        body = p.read_text(encoding="utf-8")
        if "## 4. Your FIRST work item" not in body:
            continue
        section = body.split("## 4. Your FIRST work item")[1].split("## 5.")[0]
        n = 0
        for line in section.split("\n"):
            s = line.strip()
            if s.startswith(("- ", "* ", "1.", "2.", "3.", "4.")) and len(s) > 20:
                n += 1
                out.append((lane, "%s-neg%d" % (lane, n), " ".join(s.lstrip("-*0123456789. ").split())[:150]))
    return out


def from_golden():
    out = []
    g = CONTRACTS / "golden"
    for p in sorted(g.glob("*KNOWN_BAD*.json")):
        cid = p.name.split("-")[0]
        out.append((cid, p.name, "known-bad fixture MUST fail validation"))
    return out


def evidence_exists(token):
    """Does any test file mention this check? During W0 the answer is always no."""
    if not TESTS.exists():
        return False
    for p in TESTS.rglob("*.py"):
        if token.lower() in p.read_text(encoding="utf-8", errors="replace").lower():
            return True
    return False


def main():
    strict = "--strict" in sys.argv
    rows = from_ebnf() + from_golden() + from_briefs()

    by_owner = {}
    for owner, ident, desc in rows:
        by_owner.setdefault(owner, []).append((ident, desc))

    print("NEGATIVE-CHECK CENSUS\n")
    total = built = 0
    for owner in sorted(by_owner):
        print("  %s" % owner)
        for ident, desc in by_owner[owner]:
            total += 1
            has = evidence_exists(ident)
            built += 1 if has else 0
            print("    [%s] %-22s %s" % ("x" if has else " ", ident, desc[:96]))
        print()

    print("  %d required · %d built · %d NOT YET BUILT" % (total, built, total - built))
    if total == 0:
        print("\n  *** CENSUS FOUND ZERO REQUIRED CHECKS. That is itself a failure:")
        print("  *** a census that can only report success is not measuring anything.")
        return 1
    if not TESTS.exists():
        print("\n  tests/ does not exist yet (W0) - every check is REQUIRED-NOT-YET-BUILT,")
        print("  which is the correct state before any lane opens. A lane turns its own green.")
    if strict and built < total:
        print("\n  --strict: %d gap(s)" % (total - built))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
