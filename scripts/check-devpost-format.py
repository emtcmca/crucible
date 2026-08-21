#!/usr/bin/env python3
"""check-devpost-format.py - enforce ADR-0001 mechanically.

ADR-0001 locks the Devpost update format to Update 2. A decision recorded in an
ADR and checked by eye is a decision that holds until the night somebody is
tired, which in this project is the night of a freeze. `CONVENTIONS.md` §8: a
rule restated in a fifth document is not enforced; a rule a script can fail is.

Checks every `docs/devpost/*.md`:

    words          350-500          Update 2 is the ceiling, not the target
    em-dashes      zero             drafted copy carries none
    headings       one ##, 3-4 ###   sentence case, no bold, no numbering
    fenced code    zero             an update is prose, not a README
    links          exactly one      the repo, at the end
    closing        must state what is NOT known yet
    failure        must report something that went wrong

FOUR OF THESE ARE COUNTABLE AND TWO ARE NOT, and pretending otherwise would be
worse than not checking. The last two are matched on a small vocabulary and can
be satisfied by a sentence that says the words without doing the thing. That is
stated here rather than hidden: this catches a draft that FORGOT, never one that
went through the motions. Register is human judgment and no script gets it.

Run:  python scripts/check-devpost-format.py
      python scripts/check-devpost-format.py --selftest
"""

import argparse
import io
import pathlib
import re
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = pathlib.Path(__file__).resolve().parent.parent
DEVPOST = REPO / "docs" / "devpost"

WORDS_MIN, WORDS_MAX = 350, 500
EM_DASH = "—"

# Vocabulary for the two soft checks. Deliberately small: a big list would make
# the check pass on anything and turn into a regex that cannot fail.
NOT_KNOWN = ("no results", "nothing has been", "still no", "not known",
             "no number", "has not been", "no attack has been")
WENT_WRONG = ("failed", "wrong", "defect", "could not fail", "caught",
              "refused", "mistake", "broke", "bug")


def check(path):
    raw = path.read_text(encoding="utf-8")
    body = raw.split("-->", 1)[1] if raw.lstrip().startswith("<!--") else raw
    problems = []

    n = len(body.split())
    if not (WORDS_MIN <= n <= WORDS_MAX):
        problems.append("%d words, outside %d-%d" % (n, WORDS_MIN, WORDS_MAX))

    if EM_DASH in body:
        problems.append("%d em-dash(es); drafted copy carries none"
                        % body.count(EM_DASH))

    h2 = re.findall(r"^## (?!#)", body, re.M)
    h3 = re.findall(r"^### ", body, re.M)
    if len(h2) != 1:
        problems.append("%d level-2 headings, expected exactly 1" % len(h2))
    if not 3 <= len(h3) <= 4:
        problems.append("%d level-3 headings, expected 3 or 4" % len(h3))
    for h in re.findall(r"^#{2,3} (.+)$", body, re.M):
        if h.strip().startswith("**"):
            problems.append("heading is bolded: %r" % h[:48])
        if re.match(r"^\d+[.)]", h.strip()):
            problems.append("heading is numbered: %r" % h[:48])

    if "```" in body:
        problems.append("contains a fenced code block; an update is prose")

    links = re.findall(r"\]\(", body)
    if len(links) != 1:
        problems.append("%d links, expected exactly 1 (the repo, at the end)"
                        % len(links))

    # SCOPED TO THE FINAL SECTION, and the selftest is why. The first version
    # searched the whole body, and Update 2's own TITLE contains "nothing has
    # been measured yet" -- so deleting the entire closing section still passed.
    # A check satisfied by the headline is not checking the closing.
    tail = body.rsplit("### ", 1)[-1].lower() if "### " in body else body.lower()
    if not any(p in tail for p in NOT_KNOWN):
        problems.append("the FINAL section does not state what is NOT known yet")

    low = body.lower()
    if not any(p in low for p in WENT_WRONG):
        problems.append("reports nothing that went wrong; a log that only "
                        "reports wins is the log a reader discounts")

    return problems


def selftest():
    """Mutate a conforming post six ways and require each to be caught.

    A format checker that has only ever seen conforming posts has not been shown
    to check anything.
    """
    src = DEVPOST / "2026-08-20-update-2-contracts-hashed.md"
    if not src.exists():
        print("SELFTEST CANNOT RUN: the canonical instance is missing.")
        return 1
    good = src.read_text(encoding="utf-8")

    import tempfile

    # Each case declares WHICH finding it must produce. Two defects made that
    # necessary, and both surfaced only by running this after an unrelated edit:
    #
    #   "closing removed" SILENTLY BECAME A NO-OP. It replaced an exact sentence
    #   from Update 2, that sentence was later reworded, and .replace() then
    #   changed nothing. A mutation that mutates nothing is a case that cannot
    #   fail, sitting inside the harness whose whole job is proving cases can.
    #
    #   "fenced code block added" was being caught by the WORD COUNT, because the
    #   added fence pushed the post past the ceiling. Caught for a reason
    #   unrelated to the property under test, which would have hidden the fence
    #   check breaking entirely.
    #
    # So: assert the mutation actually changed the text, and assert the finding
    # names the property the case exists to test.
    def _drop_last_section(src):
        i = src.rfind("\n### ")
        return src[:i] + "\n\nThat is all for today.\n" if i > 0 else src

    def _trim_words(src, n):
        """Shorten the body so an ADDITIVE mutation does not trip the word check
        and get credited for the wrong reason."""
        paras = src.split("\n\n")
        for idx in range(len(paras) - 1, -1, -1):
            if paras[idx].startswith(("#", "[", "<!--")):
                continue
            w = paras[idx].split()
            if len(w) > n:
                paras[idx] = " ".join(w[: max(1, len(w) - n)])
                break
        return "\n\n".join(paras)

    cases = [
        ("em-dash inserted", "em-dash",
         good.replace("Today's milestone", "Today" + EM_DASH + "s milestone")),
        ("truncated below the floor", "words",
         "\n".join(good.split("\n")[:8])),
        ("fenced code block added", "fenced code block",
         _trim_words(good, 14) + "\n```\nx\n```\n"),
        ("second link added", "links",
         _trim_words(good, 8) + "\n[a](https://b.invalid)\n"),
        ("heading bolded", "bolded",
         good.replace("### Why post about interfaces",
                      "### **Why post about interfaces**")),
        ("closing removed", "FINAL section", _drop_last_section(good)),
    ]
    bad = 0
    print("SELFTEST - a conforming post mutated six ways\n")
    with tempfile.TemporaryDirectory() as d:
        for label, expect, text in cases:
            if text == good:
                print("  FAIL %-28s THE MUTATION CHANGED NOTHING" % label)
                bad += 1
                continue
            p2 = pathlib.Path(d) / "case.md"
            p2.write_text(text, encoding="utf-8")
            found = check(p2)
            hit = [f for f in found if expect.lower() in f.lower()]
            if hit:
                print("  ok   %-28s %s" % (label, hit[0][:56]))
            else:
                bad += 1
                print("  FAIL %-28s expected a finding naming %r, got %s"
                      % (label, expect, found or "NOTHING"))
        p2 = pathlib.Path(d) / "good.md"
        p2.write_text(good, encoding="utf-8")
        found = check(p2)
        print("  %s %-28s %s" % ("ok  " if not found else "FAIL",
                                 "the unmutated post passes",
                                 "" if not found else found))
        if found:
            bad += 1

    print("\n  %d case(s) failed" % bad)
    if bad:
        print("  THE CHECKER IS BROKEN. A green run means nothing.")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    if not DEVPOST.exists():
        print("no docs/devpost/ yet")
        return 0
    # ADR-0001 governs UPDATE POSTS. It does not govern the Project Story, which
    # is a different artifact with a different job: one long page a judge lands
    # on, versus six short timestamped freeze announcements. Applying the update
    # rules to it produced four false findings the moment it was written.
    #
    # A check with a high false-positive rate is worse than no check, because it
    # gets switched off -- the STATUS pass in contract-check.py started ~90%
    # false and had to be rescoped for exactly this reason. So the scope is
    # narrowed EXPLICITLY and the skip is LOGGED rather than silent: section 8
    # rule 9, because silent truncation reads as "covered everything".
    all_md = sorted(DEVPOST.glob("*.md"))
    posts = [p for p in all_md if "update" in p.name.lower()]
    skipped = [p for p in all_md if p not in posts]
    for s in skipped:
        print("  SKIP %s -- not an update post. ADR-0001 does not govern it."
              % s.name)
    if skipped:
        print("")
    if not posts:
        print("docs/devpost/ is empty. That is not a pass -- there is nothing to "
              "check, and a checker reporting success on an empty set is not "
              "measuring anything.")
        return 1

    print("ADR-0001 - Devpost update format\n")
    failed = 0
    for p in posts:
        problems = check(p)
        print("  %s %s" % ("ok  " if not problems else "FAIL", p.name))
        for problem in problems:
            print("         %s" % problem)
            failed += 1
    print("\n  %d post(s), %d problem(s)" % (len(posts), failed))
    print("  Two checks are soft and say so in the source: a draft can satisfy "
          "them\n  by saying the words without doing the thing. Register is human "
          "judgment.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
