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
  * the distinctive pretext tail     `reissued-card`, `bank-fraud-hold`
  * any ADJACENT PAIR of tokens      `bank fraud`, `read it to you`
  * a smuggled instrument identifier `pm_visa_5581`
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
import subprocess
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = pathlib.Path(__file__).resolve().parent.parent
SEALED = pathlib.Path("C:/dev/crucible-wt-SEAL/corpus/sealed")

# Words that appear in a slug AND in ordinary prose. Never flagged alone.
COMMON = {"file", "move", "number", "time", "card", "bank", "set", "up", "it",
          "to", "you", "the", "on", "in", "at", "one", "read", "wrong", "policy"}


def signals():
    """Everything that could only have come from the sealed set."""
    slugs, tails, pairs, instruments, hashes = set(), set(), set(), set(), set()
    for f in sorted(SEALED.glob("*.json")):
        stem = f.stem
        slugs.add(stem)
        parts = stem.split("-")
        tail = "-".join(parts[3:]) if len(parts) > 3 else ""
        if tail:
            tails.add(tail)
            toks = [t for t in parts[3:] if t]
            for i in range(len(toks) - 1):
                pairs.add((toks[i] + r"[\s\-_]+" + toks[i + 1]))
        o = json.loads(f.read_text(encoding="utf-8"))
        sf = o.get("scored_features", {})
        for k in ("payout_instrument_id", "order_payment_instrument_id"):
            if sf.get(k):
                instruments.add(sf[k])
        hashes.add(hashlib.sha256(
            f.read_bytes().replace(b"\r\n", b"\n")).hexdigest())
    return slugs, tails, pairs, instruments, hashes


def tracked_files():
    out = subprocess.run(["git", "-C", str(REPO), "ls-files"],
                         capture_output=True, text=True).stdout.split("\n")
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

    print("SEAL LEAK CHECK - every tracked file in the repo\n")
    total = 0
    for p in tracked_files():
        try:
            hits = scan(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        if hits:
            total += len(hits)
            print("  LEAK %s" % p.relative_to(REPO).as_posix())
            for h in hits:
                print("       %s" % h)
    if total:
        print("\n%d LEAK(S). The repo is PUBLIC; a leaked pretext is permanent." % total)
        return 1
    print("  no leaks across %d tracked files" % len(tracked_files()))
    print("\nSingle common words are deliberately NOT flagged. A check that fires")
    print("on the word 'time' has stopped measuring whether the seal held.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
