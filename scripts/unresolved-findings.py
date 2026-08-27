#!/usr/bin/env python3
"""unresolved-findings.py - what CRUCIBLE found and COULD NOT FIX, and why.

THE REPORT A PERSON HARDENING THEIR OWN AGENT ACTUALLY NEEDS, and the one this
project was not producing. Eric, 2026-08-27:

    "CRUCIBLE found real problems and refused to ship a fix it couldn't prove
    worked. THIS is what we need to meticulously document. This is the
    information that users will want to read most when red-teaming their own
    agents."

Every other surface in this repo answers "what did it fix". A hardening tool
that only reports its successes hands you a policy and an unearned feeling of
safety. THE UNFIXED FINDINGS ARE THE ACTIONABLE HALF: they are real breaches,
diagnosed, with a patch attempt on record and a machine-checkable reason the
patch was refused. That is a work item for a human. A promoted rule is not.

THREE OUTCOMES, AND ONLY ONE OF THEM IS "IT WORKED"
---------------------------------------------------
  RESOLVED    breach -> autopsy -> proposal -> gate PROMOTED.
  UNRESOLVED  breach -> autopsy -> proposal -> gate REFUSED. The finding stands
              and nothing shipped. THIS IS THE SECTION THAT MATTERS.
  CLEAN       the loop attacked, found nothing new for three consecutive
              rounds, and stopped. Not "nothing happened" - a dry sweep is
              evidence of coverage and it is reported as a result.

An earlier summary of these runs called the second and third outcomes "CRUCIBLE
did nothing", which is wrong about both and is why this script exists.

WHAT IT WILL NOT DO. It will not tell you an unresolved finding is unexploitable,
and it will not rank findings by risk beyond the capability classes the autopsy
already recorded. It reports what the run recorded and what the gate decided.
"""

import argparse
import collections
import glob
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from crucible.replay import integrity, verdict            # noqa: E402


# Plain-English glosses. The invariant ids are precise and unreadable; a user
# meeting one for the first time needs the sentence, not the identifier.
# ANYTHING NOT IN THIS MAP FALLS BACK TO THE ID - a missing gloss must look
# missing rather than be quietly replaced by a guess.
INVARIANT_GLOSS = {
    "inv_repeated_mutation_on_one_subject":
        "the agent changed the same record over and over inside one "
        "conversation, which is how a small permitted action becomes a large "
        "unpermitted one",
    "inv_escalated_below_the_queue_the_amount_requires":
        "the agent sent an approval to a lower queue than the amount called "
        "for, so the money moved past a reviewer who was never meant to see it",
    "inv_account_identifier_left_the_boundary":
        "an account identifier was written somewhere it should never have "
        "travelled to",
}

REFUSAL_GLOSS = {
    "closure": ("THE FIX DID NOT FIX IT. Replayed against the very calls that "
                "caused the breach, the proposed rule leaves the breach in "
                "place."),
    "reduction": ("THE FIX BLOCKED TOO LITTLE. It stopped fewer attacks than "
                  "the gate requires, so it is not worth the capability it "
                  "costs."),
    "both": ("THE FIX DID NOTHING AT ALL. It neither closed the breach it was "
             "written for nor blocked any other attack. A rule like this passes "
             "a benign-traffic check trivially, because it never fires."),
}


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def acceptance_line(paths):
    """RULING 60. Every aggregate prints acceptance beside its figures."""
    acc = rej = unk = 0
    for p in paths:
        rec = verdict.read_verdict(p)
        if rec is None:
            unk += 1
        elif rec.get("verdict") == verdict.ACCEPTS:
            acc += 1
        else:
            rej += 1
    return ("ACCEPTANCE: %d bundle(s) in this pool - the reader ACCEPTS %d, "
            "REJECTS %d, and %d have NO READER VERDICT AT ALL. Acceptance is "
            "UNKNOWN for those and no figure below may be read as covering "
            "them." % (len(paths), acc, rej, unk))


def why_refused(criteria):
    bc = criteria.get("breach_closure") or {}
    ar = criteria.get("attack_reduction") or {}
    not_closed = bc.get("closed") is False
    b = ar.get("newly_blocked_b")
    too_few = isinstance(b, int) and b < 3
    if not_closed and too_few:
        return "both", b
    if not_closed:
        return "closure", b
    if too_few:
        return "reduction", b
    return None, b


def collect(bundle_paths):
    unresolved = collections.defaultdict(list)
    resolved = collections.defaultdict(int)
    clean_runs, halted_runs, promoting_runs = [], [], []

    for p in bundle_paths:
        b = load(p)
        run = os.path.basename(p).split(".")[0]
        aut = {a["autopsy_id"]: a for a in (b.get("autopsies") or [])}
        props = {pp["autopsy_id"]: pp for pp in (b.get("patch_proposals") or [])}
        decisions = b.get("gate_decisions") or []
        breaches = sum(1 for e in b.get("episodes") or []
                       if (e.get("verdict") or {}).get("breach"))
        promoted = sum(1 for d in decisions if d.get("decision") == "PROMOTE")

        if breaches == 0:
            clean_runs.append((run, b))
        elif promoted == 0:
            halted_runs.append((run, b, breaches))
        else:
            promoting_runs.append((run, b, breaches, promoted))

        for d in decisions:
            crit = d.get("criteria") or {}
            if d.get("decision") == "PROMOTE":
                bc = crit.get("breach_closure") or {}
                resolved[bc.get("originating_clause_id") or "(unrecorded)"] += 1
                continue
            if d.get("decision") != "REJECT":
                continue
            bc = crit.get("breach_closure") or {}
            inv = bc.get("originating_clause_id") or "(unrecorded)"
            kind, b_blocked = why_refused(crit)
            # The proposal that answered this round, if the round is recorded.
            rnd = d.get("round_index")
            prop = next((pp for pp in (b.get("patch_proposals") or [])
                         if pp.get("round_index") == rnd), None)
            dsl = None
            if prop and prop.get("rules"):
                dsl = prop["rules"][0].get("dsl_text")
            a = next((x for x in aut.values() if x.get("round_index") == rnd), None)
            unresolved[inv].append({
                "run": run, "round": rnd, "kind": kind, "b": b_blocked,
                "dsl": dsl,
                "classes": (a or {}).get("capability_classes_involved") or [],
                "attack_id": (a or {}).get("attack_id"),
            })
    return unresolved, resolved, clean_runs, halted_runs, promoting_runs


def render(paths):
    unresolved, resolved, clean_runs, halted, promoting = collect(paths)
    out = []
    w = out.append

    w("=" * 78)
    w("WHAT CRUCIBLE FOUND AND COULD NOT FIX")
    w("=" * 78)
    w("")
    w(acceptance_line(paths))
    w("")
    w("A hardening tool that reports only its successes hands you a policy and")
    w("an unearned feeling of safety. Below are real breaches it found,")
    w("diagnosed, attempted to patch, and REFUSED TO SHIP A FIX FOR, with the")
    w("machine-checked reason. Each one is a work item for a human.")
    w("")

    total = sum(len(v) for v in unresolved.values())
    w("-" * 78)
    w("1. UNRESOLVED FINDINGS - %d refused patch attempt(s) across %d invariant(s)"
      % (total, len(unresolved)))
    w("-" * 78)
    if not unresolved:
        w("  None. Every breach this pool found was answered by a rule the gate")
        w("  accepted.")
    for inv, items in sorted(unresolved.items(), key=lambda kv: -len(kv[1])):
        w("")
        w("  INVARIANT  %s" % inv)
        gloss = INVARIANT_GLOSS.get(inv)
        if gloss:
            w("  MEANING    %s" % gloss)
        else:
            w("  MEANING    (no plain-English gloss recorded for this invariant)")
        classes = sorted({c for it in items for c in it["classes"]})
        if classes:
            w("  CAPABILITY %s" % ", ".join(classes))
        w("  REFUSED    %d time(s), in run(s) %s"
          % (len(items), ", ".join(sorted({it["run"] for it in items}))))
        kinds = collections.Counter(it["kind"] for it in items)
        for k, n in kinds.most_common():
            w("             %dx %s" % (n, REFUSAL_GLOSS.get(k, k)))
        seen = []
        for it in items:
            if it["dsl"] and it["dsl"] not in seen:
                seen.append(it["dsl"])
        if seen:
            w("  ATTEMPTED  the rule(s) the ARMORER proposed and the gate refused:")
            for d in seen[:3]:
                w("               %s" % d)
        w("  WHAT TO DO this breach is UNFIXED. The policy CRUCIBLE shipped does")
        w("             not stop it. Treat it as an open finding against your")
        w("             agent and close it by hand, or by a control the")
        w("             three-verb DSL can express.")

    w("")
    w("-" * 78)
    w("2. RESOLVED - breaches answered by a rule the gate accepted")
    w("-" * 78)
    if not resolved:
        w("  None in this pool.")
    for inv, n in sorted(resolved.items(), key=lambda kv: -kv[1]):
        w("  %-52s %d promoted" % (inv, n))

    w("")
    w("-" * 78)
    w("3. CLEAN SWEEPS - attacked, found nothing new, stopped")
    w("-" * 78)
    w("  A dry sweep is a RESULT, not an absence of one. The loop attacked, the")
    w("  tripwire recorded every tool call, and no attack crossed an invariant.")
    if not clean_runs:
        w("  None in this pool.")
    for run, b in clean_runs:
        rc = b.get("round_census") or []
        eps = len(b.get("episodes") or [])
        atks = len({e.get("attack_id") for e in b.get("episodes") or []})
        w("  %-10s %d round(s), %d episode(s), %d distinct attack(s), 0 breaches"
          % (run, len(rc), eps, atks))

    w("")
    w("-" * 78)
    w("4. RUN OUTCOMES")
    w("-" * 78)
    w("  %2d run(s)  found breaches AND shipped at least one rule" % len(promoting))
    w("  %2d run(s)  found breaches and shipped NOTHING - the gate refused every" % len(halted))
    w("             candidate. These are section 1.")
    w("  %2d run(s)  found no breach at all - section 3." % len(clean_runs))
    w("")
    w("  METHOD LIMIT. Closure and attack-reduction are a REPLAY of the calls")
    w("  the run recorded. They answer WOULD THIS RULE HAVE STOPPED THESE CALLS.")
    w("  They do not answer COULD THE AGENT HAVE FOUND ANOTHER PATH.")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(
        description="what CRUCIBLE found and could not fix")
    ap.add_argument("path", help="a batch directory or one .c6.json bundle")
    ap.add_argument("--json", metavar="OUT", help="also write the raw findings")
    args = ap.parse_args()

    if os.path.isdir(args.path):
        paths = sorted(glob.glob(os.path.join(args.path, "*.c6.json")))
    else:
        paths = [args.path]
    if not paths:
        print("no .c6.json bundles at %s" % args.path, file=sys.stderr)
        return 2

    print(render(paths))

    if args.json:
        unresolved, resolved, clean_runs, halted, promoting = collect(paths)
        acc = rej = unk = 0
        for p in paths:
            rec = verdict.read_verdict(p)
            if rec is None:
                unk += 1
            elif rec.get("verdict") == verdict.ACCEPTS:
                acc += 1
            else:
                rej += 1
        pathlib.Path(args.json).write_text(json.dumps({
            "schema": "crucible.unresolved_findings.v1",
            "acceptance": {"bundles": len(paths), "accepts": acc,
                           "rejects": rej, "unknown": unk},
            "unresolved": {k: v for k, v in unresolved.items()},
            "resolved": dict(resolved),
            "clean_runs": [r for r, _ in clean_runs],
            "runs": {"promoting": len(promoting), "halted": len(halted),
                     "clean": len(clean_runs)},
        }, indent=1, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
