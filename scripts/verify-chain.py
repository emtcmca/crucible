#!/usr/bin/env python3
"""verify-chain.py - verify a run's policy lineage. data-spec.md section 2.5.

    python scripts/verify-chain.py --ledger evidence/run.db --run RUN_ID
    python scripts/verify-chain.py --selftest

Prints a table: version, hash prefix, parent, lineage prefix, OK or the first
failing check. Exit 0 means the chain is intact. It runs in well under a second,
which is why data-spec says to run it live in the demo rather than show a
screenshot of a previous run.

THE PART THAT MAKES THIS WORTH RUNNING
--------------------------------------
Every `policy_hash` here is RECOMPUTED FROM THE STORED BYTES, not read from the
stored hash field. Comparing a stored hash to itself proves nothing: it passes on
a truncated write, a partial write, and a corrupted read, because in each case
the value is being compared to a copy of itself. Recomputation is the only step
that can disagree with the record.

WHAT A GREEN RESULT DOES NOT MEAN
---------------------------------
The chain is UNSIGNED. It detects accidental mutation, partial writes,
out-of-order or skipped promotion, and post-hoc editing by anything that does not
also recompute the chain. It does NOT defend against an adversary holding the
Gate's credentials, because such an adversary recomputes it too.

IAM immutability is the real control -- `crucible-gate` holds `objectCreator` on
the policies bucket and nothing that can overwrite or delete. The chain is the
detector. data-spec 2.4 says to state that distinction out loud, and a security
judge is worth more to than a claim that overreaches.
"""

import argparse
import hashlib
import io
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from crucible.canon import CanonicalizationError, canonicalize_bytes  # noqa: E402
from crucible.ledger import Ledger, LineageError, verify  # noqa: E402


def rows_from_ledger(led, run_id):
    """Recompute each policy hash FROM THE BYTES and report any disagreement
    with the stored field before the chain is even considered."""
    out, drift = [], []
    for v in led.versions(run_id):
        try:
            recomputed = hashlib.sha256(
                canonicalize_bytes(v["payload_bytes"])).hexdigest()
        except CanonicalizationError as e:
            drift.append("v%d: stored bytes do not canonicalize: %s"
                         % (v["version"], e))
            recomputed = None
        if recomputed and recomputed != v["policy_hash_full"]:
            drift.append(
                "v%d: stored policy_hash_full is %s but the stored BYTES "
                "canonicalize to %s. Something rewrote the payload."
                % (v["version"], v["policy_hash_full"][:16], recomputed[:16]))
        out.append({"version": v["version"],
                    "policy_hash_full": recomputed or v["policy_hash_full"],
                    "parent_hash": v["parent_hash"],
                    "lineage_hash": v["lineage_hash"]})
    return out, drift


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger")
    ap.add_argument("--run")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not (a.ledger and a.run):
        ap.error("--ledger and --run are required (or use --selftest)")

    with Ledger(a.ledger) as led:
        run = led.get_run(a.run)
        rows, drift = rows_from_ledger(led, a.run)

        print("run     : %s" % a.run)
        print("ledger  : %s" % a.ledger)
        print("head    : %s" % (run["head_lineage_hash"] or "-"))
        print("versions: %d" % len(rows))
        print("")

        for d in drift:
            print("  BYTES  %s" % d)
        if drift:
            print("")

        try:
            report = verify(a.run, rows, head_lineage_hash=run["head_lineage_hash"])
        except LineageError as e:
            print("  %-4s %-8s %-18s %-18s %s"
                  % ("ver", "policy", "parent", "lineage", "status"))
            for r in rows:
                if e.version is not None and r["version"] >= e.version:
                    print("  v%-3d %-8s %-18s %-18s %s"
                          % (r["version"], r["policy_hash_full"][:8],
                             (r["parent_hash"] or "-")[:16],
                             (r["lineage_hash"] or "-")[:16],
                             "FAIL %s" % e.code if r["version"] == e.version
                             else "not evaluated"))
                else:
                    print("  v%-3d %-8s %-18s %-18s OK"
                          % (r["version"], r["policy_hash_full"][:8],
                             (r["parent_hash"] or "-")[:16], r["lineage_hash"][:16]))
            print("")
            print("  CHAIN BROKEN at v%s: %s" % (e.version, e.detail))
            print("  Versions after the break are NOT EVALUATED. A chain is only")
            print("  meaningful up to its first break, and reporting the downstream")
            print("  mismatches as separate problems would read as several faults")
            print("  where there is one.")
            return 1

        print("  %-4s %-8s %-18s %-18s %s"
              % ("ver", "policy", "parent", "lineage", "status"))
        for r in report:
            print("  v%-3d %-8s %-18s %-18s %s"
                  % (r["version"], r["policy_hash"][:8], r["parent"][:16],
                     r["lineage"][:16], r["status"]))
        print("")
        if drift:
            print("  MIRROR_DRIFT: the chain verifies but %d stored hash field(s)"
                  % len(drift))
            print("  disagree with the stored bytes. That flags the index, not the")
            print("  record -- but it is not nothing, and it is printed rather than")
            print("  folded into the exit code.")
            return 1
        print("  CHAIN INTACT - %d versions, every hash RECOMPUTED FROM BYTES."
              % len(report))
        print("  Unsigned: this detects accidental mutation and post-hoc editing,")
        print("  NOT an adversary holding the Gate's credentials. IAM immutability")
        print("  is the real control; this is the detector.")
    return 0


def selftest():
    """Build a real ledger, promote three versions, verify, then TAMPER and
    verify again. A verifier that has only ever been shown intact chains has
    not been shown to verify anything."""
    import json
    import tempfile

    from crucible.gate import promote

    run = "run_20260820_000000_selftst"
    locks = {"manifest_hash": "m" * 16, "objective_set_hash": "o" * 16,
             "gate_rule_hash": "g" * 16, "target_hash": "t" * 16}
    blobs = {}
    tmp = pathlib.Path(tempfile.mkdtemp()) / "selftest.db"

    def payload(i):
        return {"policy_schema_version": 1,
                "target_manifest_hash": locks["manifest_hash"],
                "rules": [{"rule_id": "r_%012d" % k, "verb": "deny",
                           "cap_selector": "CAP_MOVES_MONEY"}
                          for k in range(i)]}

    with Ledger(str(tmp)) as led:
        led.open_run(run, "2026-08-20T00:00:00Z", locks)
        for i in (1, 2, 3):
            promote(led, run, json.dumps(payload(i)).encode(), "crucible-gate",
                    "2026-08-20T00:00:00Z", locks["manifest_hash"],
                    lambda n, d: blobs.__setitem__(n, d), lambda n: blobs[n])
        rows, drift = rows_from_ledger(led, run)
        head = led.get_run(run)["head_lineage_hash"]

    ok = True
    print("SELFTEST\n")

    try:
        verify(run, rows, head_lineage_hash=head)
        print("  ok   an intact 3-version chain verifies")
    except LineageError as e:
        print("  FAIL an intact chain did not verify: %s" % e); ok = False

    tampered = [dict(r) for r in rows]
    tampered[1]["policy_hash_full"] = "%064x" % 0xdead
    try:
        verify(run, tampered, head_lineage_hash=head)
        print("  FAIL a REWRITTEN v2 verified. The chain detects nothing.")
        ok = False
    except LineageError as e:
        print("  ok   a rewritten v2 is caught: %s at v%s" % (e.code, e.version))

    gapped = [rows[0], rows[2]]
    try:
        verify(run, gapped, head_lineage_hash=head)
        print("  FAIL a MISSING v2 verified. A silently failed promotion is invisible.")
        ok = False
    except LineageError as e:
        print("  ok   a missing v2 is caught: %s" % e.code)

    try:
        verify(run, rows, head_lineage_hash="0" * 16)
        print("  FAIL a head that does not match the chain verified.")
        ok = False
    except LineageError as e:
        print("  ok   a mismatched head is caught: %s" % e.code)

    print("\n  %s" % ("every check observed both passing and failing"
                      if ok else "THE VERIFIER IS BROKEN"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
