#!/usr/bin/env python3
"""seal-leak-check.py - does any public artifact leak the sealed family?

The commitment publishes ONE hash and withholds the filenames, because each name
describes its attack's pretext. This checks that the withholding actually held,
across every tracked file in the repo rather than only the file that was meant to
withhold them.

WHY THIS IS A SCRIPT AND NOT THE ONE-LINER IT REPLACES
------------------------------------------------------
The first version split each filename on "-" and flagged any token over three
characters. Run against the commitment it reported four hits -- `file`, `move`,
`number`, `time` -- every one of them ordinary English sitting in the
explanatory prose: "Per-file hashes", "nothing moved", "one number",
"commit timestamp". Zero were leaks.

**A leak check with a 100% false-positive rate is worse than no leak check**,
because the next person reads four hits, confirms they are noise, and stops
reading it. That is the same failure the STATUS pass in `contract-check.py` had
to be rescoped for.

So the signal is narrowed to things that can only have come from the sealed set:

  * a full instance slug             `F4-dest-16-reissued-card`
  * the distinctive pretext tail     (examples withheld, for the obvious reason)
  * any ADJACENT PAIR of pretext tokens
  * a smuggled instrument identifier (example withheld -- an earlier
    version of this docstring named a real one, which is the leak it exists
    to catch)
  * any instance's full hash

Single common words are deliberately NOT flagged. A check that fires on the word
"time" has stopped measuring whether the seal held.

Run:  python scripts/seal-leak-check.py
      python scripts/seal-leak-check.py --selftest
"""

import argparse
import hashlib
import io
import json
import pathlib
import re
import os
import subprocess
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = pathlib.Path(__file__).resolve().parent.parent
def _sealed_dir():
    """WHERE THE SEALED SET IS - RESOLVED, NOT TYPED.

    This was `pathlib.Path("C:/dev/crucible-wt-SEAL/corpus/sealed")`, a
    hardcoded absolute path into a DIFFERENT WORKTREE, until 2026-08-22.

    On this machine that path exists, so the check ran and looked right. On a
    clone, a CI box, or a judge's machine it does not - and `pathlib.glob` over
    a missing directory RETURNS EMPTY RATHER THAN RAISING. Every signal set
    came back empty, nothing was compared against anything, and the script
    printed "no leaks across N tracked files" and exited 0.

    A CHECK THAT CANNOT FAIL, STANDING BEHIND A SECURITY CLAIM ABOUT A PUBLIC
    REPOSITORY. `offline_lint.py:202-206` guards this exact class by name.
    """
    # AN EXPLICIT OVERRIDE IS AUTHORITATIVE. If CRUCIBLE_SEALED_DIR is set and
    # does not resolve, this returns None rather than quietly falling through
    # to a different directory - an override that silently picks somewhere else
    # is the same defect this function was written to fix, one level up.
    override = os.environ.get("CRUCIBLE_SEALED_DIR")
    if override is not None:
        path = pathlib.Path(override)
        return path if path.is_dir() and any(path.glob("*.json")) else None
    for candidate in (REPO / "corpus" / "sealed",
                      pathlib.Path("C:/dev/crucible-wt-SEAL/corpus/sealed")):
        if candidate.is_dir() and any(candidate.glob("*.json")):
            return candidate
    return None


SEALED = _sealed_dir()

# Words that appear in a slug AND in ordinary prose. Never flagged alone.
COMMON = {"file", "move", "number", "time", "card", "bank", "set", "up", "it",
          "to", "you", "the", "on", "in", "at", "one", "read", "wrong", "policy"}

_SOURCE_TOKENS = None


def source_tokens():
    """Every word appearing in the documents the pretexts were NAMED OUT OF.

    THE FOURTH FALSE-POSITIVE CLASS, found 2026-08-21 when the corpus merged into
    this worktree and the check went from 0 leaks to 5. Three of the five were the
    pair `gift card`, in a training attack, a benign fixture, and a ratification
    doc. Neither token is in COMMON, so the all-common guard below did not fire,
    and the pair looked distinctive. It is not: `gift card` is a tender type named
    in the refund policy, and a refund agent's corpus discusses tender constantly.

    The two SOURCE_VOCABULARY files are already exempted BY NAME as the documents
    the pretexts were drawn from. The exemption was applied to the files and not to
    the vocabulary, which is the bug: the causality runs from the policy to the
    pretext, so a pair drawn ENTIRELY from the policy's own words identifies
    nothing. Matching it back fires forever and means nothing.

    Note what stays flagged. A pair is skipped only when BOTH tokens come from the
    source. One distinctive token beside a policy term is still a signal, because
    the distinctive half is what a pretext contributes.
    """
    global _SOURCE_TOKENS
    if _SOURCE_TOKENS is None:
        toks = set()
        for rel in SOURCE_VOCABULARY:
            p = REPO / rel
            if p.exists():
                toks |= set(re.findall(r"[a-z]+",
                                       p.read_text(encoding="utf-8",
                                                   errors="replace").lower()))
        _SOURCE_TOKENS = toks
    return _SOURCE_TOKENS


def signals():
    """Everything that could only have come from the sealed set."""
    slugs, tails, pairs, instruments, hashes = set(), set(), set(), set(), set()
    for f in (sorted(SEALED.glob("*.json")) if SEALED else []):
        stem = f.stem
        slugs.add(stem)
        parts = stem.split("-")
        tail = "-".join(parts[3:]) if len(parts) > 3 else ""
        # A SINGLE-TOKEN TAIL IS NOT A SIGNAL. `20-estate` yields the tail
        # "estate", which is an ordinary English word appearing in unrelated
        # fixtures -- 40 hits on its own. One word cannot identify an instance.
        #
        # This is the THIRD false-positive class this check has shed: single
        # tokens, then all-common pairs, now single-token tails. Each narrowing
        # was correct and each revealed the next. Worth noticing that the
        # instinct "make the check broader so it cannot miss anything" produces
        # a check that catches everything and therefore means nothing.
        if tail and len(parts[3:]) >= 2:
            tails.add(tail)
            toks = [t for t in parts[3:] if t]
            for i in range(len(toks) - 1):
                a, b = toks[i], toks[i + 1]
                # AT LEAST ONE TOKEN MUST BE DISTINCTIVE. The first version
                # flagged every adjacent pair, and `23-read-it-to-you` yields
                # "it to" -- which appears in ordinary English constantly and
                # produced 124 hits across the repo on its own.
                #
                # That is the SAME defect this file was written to fix, one
                # level down: I narrowed single tokens and left pairs wide, so
                # the check went from useless-loud to useless-louder.
                if a in COMMON and b in COMMON:
                    continue
                # ... and neither may a pair drawn entirely from the refund
                # policy's own vocabulary. See source_tokens().
                src = source_tokens()
                if a in src and b in src:
                    continue
                pairs.add(a + r"[\s\-_]+" + b)
        o = json.loads(f.read_text(encoding="utf-8"))
        sf = o.get("scored_features", {})
        # THE SMUGGLED DESTINATION ONLY. The first version also flagged
        # `order_payment_instrument_id`, which is not what the seal protects and
        # collides with ordinary test data -- `pm_visa_4242` is the classic
        # generic test card and appears in public tests for reasons that have
        # nothing to do with this corpus. It produced 45 hits on its own.
        #
        # What the seal protects is WHERE THE MONEY WAS REDIRECTED TO. An order
        # instrument is a property of a plausible order; a payout instrument in
        # a public file is the answer key.
        if sf.get("payout_instrument_id"):
            instruments.add(sf["payout_instrument_id"])
        hashes.add(hashlib.sha256(
            f.read_bytes().replace(b"\r\n", b"\n")).hexdigest())
    return slugs, tails, pairs, instruments, hashes


# The SOURCE documents the pretexts were drawn FROM. The causality runs the
# wrong way here: the sealed instances were named out of this vocabulary, so
# matching them back against it fires forever and means nothing. "gift card" in
# a refund policy is a refund policy doing its job.
#
# Exempted BY NAME rather than by widening the matcher, because an explicit
# exemption shows up in a diff and a widened regex ends up unable to fail.
SOURCE_VOCABULARY = {
    "docs/refund-policy-research.md",
    "target/refund_agent/refund_policy.md",
}

# This file necessarily discusses what a leak looks like.
SELF = {"scripts/seal-leak-check.py"}

EXEMPT = SOURCE_VOCABULARY | SELF


def tracked_files():
    """Every tracked file, or a refusal. NEVER an empty population on failure.

    THE SAME FAIL-OPEN THE PRE-READ PROOF HAD, with a worse consequence.

    `.stdout.split()` discarded the return code, so a git that could not run
    yielded an empty list - and this scanner would then compare its signals
    against NOTHING, find no leaks, and print a clean result. "I scanned zero
    files and found zero leaks" and "I scanned the repository and it is clean"
    were the same output.

    This file already refuses to run when it has no SIGNALS, for exactly this
    reasoning - "a green light nobody earned". Having no FILES is the same
    failure from the other side, and it was not guarded.
    """
    try:
        proc = subprocess.run(["git", "-C", str(REPO), "ls-files"],
                              capture_output=True, text=True)
    except OSError as exc:
        # git ABSENT, not merely unhappy. `returncode` never exists in this
        # case, so a check that only looked at it would let the exception
        # propagate as a traceback - or, worse, be caught somewhere upstream
        # and turned back into an empty list.
        raise SystemExit(
            "REFUSING TO RUN: git could not be executed (%s).%s" % (
                exc,
                chr(10) + "  With no file list this scan compares the sealed "
                "signals against an empty population, finds nothing, and "
                "reports a clean repository. That is not a clean repository - "
                "it is no scan at all, wearing the same words."))
    if proc.returncode != 0:
        raise SystemExit(
            "REFUSING TO RUN: git ls-files exited %d (%s).%s"
            % (proc.returncode, (proc.stderr or "").strip()[:200] or "no stderr",
               chr(10) + "  With no file list this scan compares the sealed "
               "signals against an empty population, finds nothing, and reports "
               "a clean repository. That is not a clean repository - it is no "
               "scan at all, wearing the same words."))
    out = proc.stdout.split("\n")
    keep = []
    for rel in out:
        rel = rel.strip()
        if not rel:
            continue
        p = REPO / rel
        if p.suffix.lower() in {".png", ".jpg", ".gif", ".ico"} or not p.exists():
            continue
        keep.append(p)
    return keep


def scan(text):
    slugs, tails, pairs, instruments, hashes = signals()
    hits = []
    low = text.lower()
    for s in slugs:
        if s.lower() in low:
            hits.append("full instance slug %r" % s)
    for t in tails:
        if t.lower() in low and t.lower() not in COMMON:
            hits.append("pretext tail %r" % t)
    for pat in pairs:
        if re.search(pat, low):
            hits.append("adjacent pretext tokens %r" % pat.replace(r"[\s\-_]+", " "))
    for i in instruments:
        if i.lower() in low:
            hits.append("instrument identifier %r" % i)
    for h in hashes:
        if h in text or h[:16] in text:
            hits.append("per-instance hash %s" % h[:16])
    return hits


def selftest():
    """Plant each leak kind and require it caught; plant prose and require silence."""
    slugs, tails, pairs, instruments, hashes = signals()
    one_slug = sorted(slugs)[15]
    one_tail = sorted(tails)[0]
    one_instr = sorted(instruments)[0]
    one_hash = sorted(hashes)[0]

    cases = [
        ("a full instance slug", "see %s for detail" % one_slug, True),
        ("a pretext tail", "the %s instance" % one_tail, True),
        ("an instrument identifier", "routed to %s" % one_instr, True),
        ("a per-instance hash", "sha %s" % one_hash[:16], True),
        # PROVES THE 2026-08-21 NARROWING DID NOT BLIND THE PAIR MATCHER.
        # source_tokens() removed a whole class of pair from the signal set, and a
        # narrowing that removes too much looks exactly like a narrowing that
        # removed the right amount: both print "no leaks". This case takes a pair
        # that SURVIVED the narrowing and requires it still caught.
        ("an adjacent pretext pair that survived the narrowing",
         "the request came in %s"
         % sorted(pairs)[0].replace(r"[\s\-_]+", " "), True),
        # ... and the specific string that forced the narrowing must be silent.
        ("domain vocabulary that TRIPPED the check on 2026-08-21",
         "Original tender was a gift card, so store credit is the only "
         "permitted form under section 5.", False),
        ("ordinary prose that TRIPPED the old check",
         "Per-file hashes are withheld. Nothing moved. The claim needs one "
         "number, published with a commit timestamp.", False),
        ("the real commitment file",
         (REPO / "docs/proof/sealed-family-commitment.json").read_text(
             encoding="utf-8"), False),
    ]
    print("SELFTEST\n")
    bad = 0
    for label, text, must_hit in cases:
        hits = scan(text)
        ok = bool(hits) == must_hit
        bad += 0 if ok else 1
        print("  %s %-42s %s" % ("ok  " if ok else "FAIL", label,
                                 (hits[0][:44] if hits else "clean")))
    print("\n  %d case(s) failed" % bad)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    # REFUSE RATHER THAN REPORT CLEAN. Both halves are checked: a directory
    # existing is not the same as it holding anything, and either emptiness
    # produces the identical silent pass.
    if SEALED is None:
        print("REFUSING TO RUN: no sealed set found.")
        print("  Looked at $CRUCIBLE_SEALED_DIR, %s, and the SEAL worktree."
              % (REPO / "corpus" / "sealed").as_posix())
        print("  With no sealed set there are NO SIGNALS, so every file would")
        print("  compare clean against nothing and this script would print")
        print("  'no leaks' having proved exactly nothing. That is worse than")
        print("  not running: it is a green light nobody earned.")
        return 2

    sig = signals()
    if not any(sig):
        print("REFUSING TO RUN: the sealed set at %s yielded NO SIGNALS."
              % SEALED.as_posix())
        print("  A directory that exists and contributes nothing fails exactly")
        print("  like one that is absent, and looks exactly like a clean run.")
        return 2

    print("SEAL LEAK CHECK - every tracked file in the repo")
    print("  sealed set: %s -- %d instance(s), %d signal(s)"
          % (SEALED.as_posix(), len(list(SEALED.glob("*.json"))),
             sum(len(x) for x in sig)))
    print("")
    total = 0
    skipped = 0
    unreadable = []
    for p in tracked_files():
        rel = p.relative_to(REPO).as_posix()
        if rel in EXEMPT:
            skipped += 1
            print("  SKIP %s -- %s" % (
                rel, "source vocabulary the pretexts were drawn from"
                if rel in SOURCE_VOCABULARY else "this checker's own prose"))
            continue
        try:
            hits = scan(p.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            # NAMED, NOT SWALLOWED. A bare `continue` left the file in the
            # denominator of "no leaks across N tracked files" while never
            # having been read - an unscanned file counted as a clean one.
            unreadable.append((p.relative_to(REPO).as_posix(),
                               type(exc).__name__))
            continue
        if hits:
            total += len(hits)
            print("  LEAK %s" % p.relative_to(REPO).as_posix())
            for h in hits:
                print("       %s" % h)
    if total:
        print("\n%d LEAK(S). The repo is PUBLIC; a leaked pretext is permanent." % total)
        return 1
    scanned = len(tracked_files()) - skipped - len(unreadable)
    print("  no leaks across %d file(s) ACTUALLY SCANNED "
          "(%d exempt, %d unreadable)" % (scanned, skipped, len(unreadable)))
    for rel, kind in unreadable:
        print("  UNREAD %s -- %s" % (rel, kind))
    if unreadable:
        print("")
        print("%d FILE(S) WERE NOT READ. They are not evidence of anything."
              % len(unreadable))
        return 1
    print("\nSingle common words are deliberately NOT flagged. A check that fires")
    print("on the word 'time' has stopped measuring whether the seal held.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
