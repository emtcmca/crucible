#!/usr/bin/env python3
"""gate-census.py - which of G1-G8 can actually be evaluated today.

The sibling of `conformance-sweep.py`. That one asks which negative checks
exist; this one asks which PROMOTION GATES exist, because a gate rule is
hash-locked at D2 and a gate nobody implemented is not a gate -- it is a
sentence in a YAML file that the run will silently skip.

The failure this exists to prevent is specific and it is the project's own
thesis pointed inward. `measurement-spec.md:813`: an unevaluable gate is a check
that cannot fail. A run that reports "all gates passed" while three of them were
never wired reads exactly like a run where all gates passed.

HOW THIS AVOIDS BEING THE THING IT MEASURES
--------------------------------------------
`conformance-sweep.py` answers its question by grepping `tests/` for a token,
which is gameable by writing the token in a comment -- and it read 0 built while
four checks existed, because they never mentioned the tokens. Both directions of
that failure are real.

So the map below is hand-maintained and every entry names a RESOLVABLE
reference: an importable module attribute or a file that must exist. The census
imports each one and fails if it is absent. A claim here is checkable by reading
two files instead of by trusting a comment.

**It still cannot judge whether an implementation is CORRECT.** Nothing
mechanical can. It removes the case where a gate is reported wired and no code
by that name exists.

Run:  python scripts/gate-census.py
      python scripts/gate-census.py --strict     exit 1 if any gate is unwired
"""

import argparse
import importlib
import io
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = pathlib.Path(__file__).resolve().parent.parent

WIRED, PARTIAL, ABSENT = "WIRED", "PARTIAL", "ABSENT"


def _benign_on_disk():
    """(count, near_misses, target_count, target_near, target_count, target_count).

    G3's note used to TYPE all six. Both the observed half and the target half
    then went stale - the observed half because fixtures kept landing, the target
    half because ruling 43 moved the denominator 24 -> 26 and nothing here
    noticed. A census that misreports which gate is evaluable is precisely the
    failure it was written to detect (`measurement-spec.md:813`), so it counts.

    Falls back to the target on a read error rather than raising: an
    unreadable fixture directory is a corpus problem, and the census's job is
    to report gate wiring, not to die on someone else's defect.
    """
    from corpus.model import BENIGN_TOTAL, NEAR_MISS_FLOOR
    count = near = 0
    try:
        for p in sorted((REPO / "fixtures" / "benign").glob("*.json")):
            count += 1
            if json.loads(p.read_text(encoding="utf-8")).get("near_miss"):
                near += 1
    except (OSError, ValueError):
        count, near = BENIGN_TOTAL, NEAR_MISS_FLOOR
    return (count, near, BENIGN_TOTAL, NEAR_MISS_FLOOR,
            BENIGN_TOTAL, BENIGN_TOTAL)


BENIGN_ON_DISK = _benign_on_disk()

# gate -> (status, [module:attr or path, ...], what is still missing)
GATES = {
    "G1a": (WIRED, ["crucible.tripwire:KnownBadSuite",
                    "crucible.tripwire:load_known_bad_suite"],
            "Nine known-bads with per-fixture expected verdicts. The check is "
            "`python -m crucible.tripwire --selftest`; THIS CENSUS DOES NOT RUN "
            "IT and reports only that the suite loader resolves."),
    "G1b": (WIRED, ["crucible.harness:seal_episode",
                    "crucible.tripwire:RunManifest"],
            "Episodes carry objective_set_hash / manifest_hash / "
            "derived_schema_hash. Built during W2 -- nothing stamped them."),
    "G2": (WIRED, ["crucible.gate:promote", "crucible.gate:compute_policy_hash"],
           "Read-back recomputes the hash FROM THE BYTES. A deliberately "
           "corrupted read-back is caught, verified red against a naive gate."),
    "G3": (PARTIAL, ["crucible.warden:load_benign_suite",
                     "crucible.warden:WardenConfig"],
           "Replay machinery exists and runs. THE SUITE ON DISK IS %d FIXTURES "
           "WITH %d NEAR-MISSES, against the %d with %d the hash-locked gate "
           "rule pins as bpr == \"%d/%d\". Both halves of that sentence are "
           "COUNTED, not typed: it read \"6 fixtures with 3 near-misses, not 24 "
           "with 12\" on 2026-08-22, a day after ruling 43 moved the "
           "denominator, and a census that reports the wrong target is the "
           "unevaluable-gate failure it exists to detect. A suite of the wrong "
           "size is ROUND_INVALID, never a lower score." % BENIGN_ON_DISK),
    "G4": (WIRED, ["crucible.conductor.g4:paired_scores",
                   "crucible.conductor.g4:decide",
                   "crucible.conductor.real_gate:RealGate"],
           "Attack reduction (newly_blocked_b >= 3, newly_breached_c == 0), "
           "paired against policy@vN by replaying the run's recorded attack "
           "episodes through both policies. **THIS ROW READ `ABSENT / Nothing "
           "computes b or c` UNTIL 2026-08-26**, and it was correct for as long "
           "as it stood: a criterion whose failure_mode is REJECT had never "
           "once been evaluated. `docs/design/gate-noop-measurement-2026-08-25."
           "md` measured what that cost - 18 of 31 promoted rules do not close "
           "the breach they answer. WHAT THIS ROW DOES NOT SAY: the paired "
           "slice is the episodes THE RUN RECORDED, not the 50-instance corpus "
           "training slice the `b >= 3` threshold was calibrated against - "
           "`corpus/training/*.json` carries an authored trace, not a scoreable "
           "episode. `scripts/g4-backtest.py` measures the difference that "
           "makes to the promotion rate."),
    "G5": (PARTIAL, ["crucible.dsl:validate_policy_document",
                     "crucible.dsl:Validator"],
           "Verb, capability-binding and cap:UNCLASSIFIED assertions are in the "
           "validator. **V7, the >=8-token corpus-payload substring check, is "
           "NOT implemented** -- it needs the D5 corpus to have anything to "
           "compare against."),
    "G6": (ABSENT, [],
           "Provenance: every rule must cite >= 1 breach episode ID from THIS "
           "round's autopsy. Needs the L5 coroner and the round loop."),
    "G7": (WIRED, ["infra/verify_iam.py", "infra/prove-armorer-403.sh",
                   "docs/proof/armorer-403.txt"],
           "The assertions are implemented, including G7(b2)'s project-level "
           "basic-role check -- CONVENTIONS 10a, the case the bucket grep "
           "structurally cannot see. The G7a impersonation result recorded in "
           "docs/proof/armorer-403.txt is DATED EVIDENCE FROM THE DAY IT RAN; "
           "THIS CENSUS MAKES NO gcloud CALL and cannot say it still holds. An "
           "IAM grant made later is invisible to a check that ran earlier."),
    "G8": (WIRED, ["infra/verify_iam.py"],
           "Grant direction is asserted both ways in the script -- crucible-gate "
           "holding objectCreator and no overwrite/delete role, crucible-armorer "
           "holding nothing -- and retention is asserted PRESENT AND UNLOCKED, "
           "where locked is a FAILURE and not a stronger pass. THIS CENSUS "
           "RESOLVES THE SCRIPT, NOT ITS RESULT: run infra/verify_iam.py for "
           "that, and read the date on what it prints."),
}


def resolve(ref):
    """Import an attribute or stat a file. Absence is the answer, not an error."""
    if ":" in ref:
        mod, attr = ref.split(":", 1)
        try:
            return getattr(importlib.import_module(mod), attr, None) is not None
        except Exception:
            return False
    return (REPO / ref).exists()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()

    print("GATE CENSUS - G1..G8, and whether anything can evaluate them\n")

    counts = {WIRED: 0, PARTIAL: 0, ABSENT: 0}
    broken = []

    for gate in sorted(GATES, key=lambda g: (g[:2], g)):
        status, refs, note = GATES[gate]
        missing = [r for r in refs if not resolve(r)]
        if missing:
            # The claim named something that does not exist. That is worse than
            # ABSENT: ABSENT is honest, this is a census reporting a gate wired
            # when nothing by that name is there.
            broken.append("%s claims %s and it does not resolve"
                          % (gate, ", ".join(missing)))
            status = "BROKEN"
        else:
            counts[status] += 1
        print("  %-8s %s" % (status, gate))
        for line in _wrap(note, 68):
            print("           %s" % line)
        print("")

    total = len(GATES)
    print("  %d gates: %d WIRED, %d PARTIAL, %d ABSENT"
          % (total, counts[WIRED], counts[PARTIAL], counts[ABSENT]))

    if broken:
        print("\n  CENSUS BROKEN:")
        for b in broken:
            print("    %s" % b)
        return 1

    if counts[ABSENT] or counts[PARTIAL]:
        print("\n  A PARTIAL OR ABSENT GATE DOES NOT MAKE A RUN FAIL. It makes")
        print("  the run UNEVALUABLE, which is a different and worse thing:")
        print("  'all gates passed' reads identically whether a gate passed or")
        # COUNTED, not typed. "Both remaining" was a literal beside the very
        # number it was describing, and it stops being true the moment one of
        # them is wired or a third goes absent.
        absent = sorted(g for g in GATES if GATES[g][0] == ABSENT)
        print("  was never wired. The %d ABSENT gate(s) -- %s -- need the corpus"
              % (len(absent), ", ".join(absent) or "none"))
        print("  and the round loop, so none is a surprise -- but none may")
        print("  be silently skipped on D8 either.")

    if a.strict and (counts[ABSENT] or counts[PARTIAL]):
        return 1
    return 0


def _wrap(text, width):
    out, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > width:
            out.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line:
        out.append(line)
    return out


if __name__ == "__main__":
    sys.exit(main())
