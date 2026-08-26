#!/usr/bin/env python3
"""g4-backtest.py - what would G4 have decided about the promotions already made?

WHY THIS EXISTS. `crucible/conductor/g4.py` turns on a promotion condition that
has never run. A gate criterion that changes the promotion rate is a metric
moving right before a deadline, and a metric that moves must be EXPECTED rather
than DISCOVERED. This script answers "how much" off the bundles already on disk,
so the answer is measured rather than guessed.

IT IMPORTS THE PRODUCTION SCORER. `crucible.conductor.g4.paired_scores` and
`.decide` are the same functions the live gate calls - there is no second
implementation here to agree with itself. What this script owns is only the
BACKTEST HARNESS: recovering the two policy versions and the executed slice out
of a recorded C6 bundle, which the live gate gets handed by the conductor.

    python scripts/g4-backtest.py <bundle-or-directory> [...]
    python scripts/g4-backtest.py <bundle> --json out.json
    python scripts/g4-backtest.py <bundle> --selftest

THE LIMIT, AND IT IS THE SAME ONE `gate-noop-measurement.py` PRINTS. This is a
replay of recorded calls, not a re-attack. It says what the policies would have
done to the exact calls the run recorded. It cannot say what a live agent would
have done when handed a refusal it had never received before.

A SECOND LIMIT THAT IS SPECIFIC TO A BACKTEST. The slice a round would have had
under a live G4 is not exactly the slice reconstructed here: once G4 rejects a
candidate, the run diverges - a different policy stays in force, the target
faces a different world, and every later round records different episodes. So
these figures are the decision G4 would have made AT THE MOMENT OF EACH RECORDED
PROMOTION, holding the recorded history fixed. They are not a simulation of the
counterfactual run, and the promotion-rate estimate they support is an upper
bound on agreement with the recorded loop, not a forecast of a re-run.
"""

import argparse
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from crucible.conductor.g4 import (                             # noqa: E402
    G4Unevaluable, decide, paired_scores)
from crucible.dsl.parser import parse_rule                      # noqa: E402
from crucible.dsl.serialize import (                            # noqa: E402
    assign_rule_id, compile_rule, rule_body, sort_rules)
from crucible.replay.bundle import read_bundle                  # noqa: E402
from crucible.replay.integrity import BundleRejected            # noqa: E402
from crucible.tripwire.objective_set import load_objective_set  # noqa: E402

OBJECTIVE_SET = REPO / "contracts" / "objective_set.v1.json"


# ---------------------------------------------------------------------------
# reading the bundle - the shipped reader first, every time
# ---------------------------------------------------------------------------

def open_bundle(path):
    """`(bundle, reader_accepted)`. Same two-population split, same reason, as
    `scripts/gate-noop-measurement.py`:104-126: the ruling-55 `target_responded`
    schema field was added AFTER most bundles were written and has no bearing on
    what a policy does to a recorded call. Refused bundles are a DIFFERENT
    POPULATION and are never pooled with the accepted ones."""
    try:
        bundle, _report = read_bundle(path)
        return bundle, True
    except BundleRejected:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8")), False


class PolicyReconstructionRefused(Exception):
    """The DSL text in the bundle did not rebuild the rule the bundle names."""


def _parseable(dsl_text):
    """The bundle renders `origin armorer`; the grammar demands
    `origin armorer:<round>`. The round number lives outside the hashed rule
    body, which the id assertion below proves rather than this comment."""
    if re.search(r"origin armorer$", dsl_text):
        return dsl_text + ":0"
    return dsl_text


def executable_rule(entry):
    """REFUSES rather than degrades. A rule rebuilt from text that does not hash
    back to the recorded id is a DIFFERENT RULE, and measuring a different rule
    under the recorded id is the defect shape this project keeps meeting."""
    parsed = parse_rule(_parseable(entry["dsl_text"]))
    recomputed = assign_rule_id(rule_body(parsed))
    if recomputed != entry["rule_id"]:
        raise PolicyReconstructionRefused(
            "E_POLICY_RECONSTRUCTION: the DSL text recorded for %s rebuilds to "
            "a rule with a different canonical id." % entry["rule_id"])
    return compile_rule(parsed)


def build_policies(bundle):
    out = {}
    for entry in bundle.get("policy_chain") or []:
        rules = [executable_rule(r) for r in entry.get("rules") or []]
        out[entry["version"]] = {"rules": sort_rules(rules)}
    return out


# ---------------------------------------------------------------------------
# the slice, reconstructed
# ---------------------------------------------------------------------------

def scorable_episodes(bundle):
    """Attack episodes the round's denominator kept, in recorded order.

    `RoundRecord.scorable` (conductor.py:301-306) drops TARGET_FAULT and
    INVALID, once, so no consumer has to remember to. The same two are dropped
    here and for the same reason - an episode with no measurement cannot be one
    half of a paired measurement."""
    out = []
    for ep in bundle.get("episodes") or []:
        v = ep.get("verdict") or {}
        if v.get("target_fault") or v.get("verdict") == "INVALID":
            continue
        out.append(ep)
    return out


def backtest_bundle(path, objective_set):
    path = pathlib.Path(path)
    bundle, accepted = open_bundle(path)
    out = {"bundle": str(path),
           "run_id": (bundle.get("run_manifest") or {}).get("run_id"),
           "offline_reader_accepts": accepted,
           "rows": [], "refusal": None}
    try:
        policies = build_policies(bundle)
    except PolicyReconstructionRefused as exc:
        out["refusal"] = str(exc)
        return out

    episodes = scorable_episodes(bundle)
    chain_ids = {x["version"]: {r["rule_id"] for r in x.get("rules") or []}
                 for x in bundle.get("policy_chain") or []}
    autopsies = {a.get("autopsy_id"): a for a in bundle.get("autopsies") or []}
    ep_by_key = {(e.get("attack_id"), e.get("round_index")): e
                 for e in bundle.get("episodes") or []}
    promoting = {g.get("round_index") for g in bundle.get("gate_decisions") or []
                 if g.get("decision") == "PROMOTE"}

    for pp in bundle.get("patch_proposals") or []:
        if not pp.get("accepted"):
            continue
        rnd = pp.get("round_index")
        if rnd not in promoting:
            continue
        aut = autopsies.get(pp.get("autopsy_id")) or {}
        ep = ep_by_key.get((aut.get("attack_id"), rnd))
        new_ids = [r.get("rule_id_assigned") for r in pp.get("rules") or []]
        row = {"proposal_id": pp.get("proposal_id"), "round_index": rnd,
               "promoted_rule_ids": new_ids, "code": None}
        if ep is None:
            row["code"] = "E_NO_EPISODE_FOR_AUTOPSY"
            out["rows"].append(row)
            continue
        prior_v = ep.get("policy_version")
        landed = [v for v in sorted(chain_ids)
                  if v > (prior_v if prior_v is not None else -1)
                  and set(new_ids) <= chain_ids[v]]
        if not new_ids or not landed:
            row["code"] = "E_RULE_NOT_IN_POLICY_CHAIN"
            out["rows"].append(row)
            continue
        new_v = landed[0]
        if prior_v not in policies or new_v != prior_v + 1:
            row["code"] = "E_VERSION_SKEW"
            out["rows"].append(row)
            continue
        row["prior_policy_version"] = prior_v
        row["promoted_policy_version"] = new_v

        # THE SLICE AS THE LIVE GATE WOULD HAVE HELD IT: every scorable attack
        # episode recorded up to and including this round. Also computed for
        # this round alone, because "does the slice accumulate" is the one
        # design choice in the wiring and a reader should not have to take it
        # on trust.
        cumulative = [e for e in episodes
                      if (e.get("round_index") or 0) <= rnd]
        this_round = [e for e in episodes if e.get("round_index") == rnd]
        for label, slice_ in (("cumulative", cumulative),
                              ("round_only", this_round)):
            try:
                sc = paired_scores(slice_, policies[prior_v],
                                   policies[new_v], objective_set)
            except G4Unevaluable as exc:
                row[label] = {"unevaluable": str(exc)}
                continue
            passes, detail = decide(sc)
            row[label] = {"b": sc["newly_blocked_b"], "c": sc["newly_breached_c"],
                          "n": sc["n"], "slice_n": sc["slice_n"],
                          "unpairable": len(sc["unpairable"]),
                          "g4_passes": passes, "detail": detail}
        out["rows"].append(row)
    return out


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

def totals(results):
    acc = {"bundles": 0, "refused_reconstruction": 0,
           "accepted_pop": {"promotions": 0, "cumulative_pass": 0,
                            "round_only_pass": 0, "c_gt_0": 0, "b_lt_3": 0,
                            "b_zero": 0, "unclassified": 0},
           "refused_pop": {"promotions": 0, "cumulative_pass": 0,
                           "round_only_pass": 0, "c_gt_0": 0, "b_lt_3": 0,
                           "b_zero": 0, "unclassified": 0}}
    for res in results:
        acc["bundles"] += 1
        if res["refusal"]:
            acc["refused_reconstruction"] += 1
            continue
        pop = acc["accepted_pop"] if res["offline_reader_accepts"] else acc["refused_pop"]
        for row in res["rows"]:
            pop["promotions"] += 1
            cum = row.get("cumulative")
            if not cum or "unevaluable" in cum:
                pop["unclassified"] += 1
                continue
            if cum["g4_passes"]:
                pop["cumulative_pass"] += 1
            if cum["c"] > 0:
                pop["c_gt_0"] += 1
            if cum["c"] == 0 and cum["b"] < 3:
                pop["b_lt_3"] += 1
            if cum["b"] == 0:
                pop["b_zero"] += 1
            ro = row.get("round_only") or {}
            if ro.get("g4_passes"):
                pop["round_only_pass"] += 1
    return acc


def print_report(res):
    tag = "ACCEPTED" if res["offline_reader_accepts"] else "REFUSED-BY-READER"
    print("\n%s  [%s]" % (res["bundle"], tag))
    if res["refusal"]:
        print("  REFUSED: %s" % res["refusal"])
        return
    if not res["rows"]:
        print("  no promoted patch in this bundle")
        return
    for row in res["rows"]:
        if row["code"]:
            print("  r%-2s %-46s %s" % (row["round_index"],
                                        row["proposal_id"], row["code"]))
            continue
        cum, ro = row.get("cumulative") or {}, row.get("round_only") or {}
        print("  r%-2s %-46s v%s->v%s" % (row["round_index"], row["proposal_id"],
                                          row["prior_policy_version"],
                                          row["promoted_policy_version"]))
        for label, s in (("cumulative", cum), ("round_only", ro)):
            if "unevaluable" in s:
                print("       %-11s UNEVALUABLE %s" % (label, s["unevaluable"][:70]))
                continue
            print("       %-11s b=%-3d c=%-3d n=%-3d %s"
                  % (label, s["b"], s["c"], s["n"],
                     "G4 PASS" if s["g4_passes"] else "G4 REJECT"))


def print_totals(acc):
    print("\n" + "=" * 74)
    print("TOTALS. Two populations, never pooled - the reader's refusal of a "
          "bundle\nis a statement about a schema field ruling 55 added after "
          "it was written,\nnot about what a policy does to a recorded call.")
    for name, key in (("A - offline reader ACCEPTS", "accepted_pop"),
                      ("B - offline reader REFUSES", "refused_pop")):
        p = acc[key]
        if not p["promotions"]:
            continue
        print("\n  Population %s" % name)
        print("    promotions the loop made                 %5d" % p["promotions"])
        print("    G4 would PASS   (cumulative slice)       %5d" % p["cumulative_pass"])
        print("    G4 would REJECT (cumulative slice)       %5d"
              % (p["promotions"] - p["cumulative_pass"] - p["unclassified"]))
        print("      of which c > 0  (a re-opened attack)   %5d" % p["c_gt_0"])
        print("      of which c == 0 and b < 3              %5d" % p["b_lt_3"])
        print("        of which b == 0 (closed NOTHING)     %5d" % p["b_zero"])
        print("    not classified                           %5d" % p["unclassified"])
        print("    [reference] G4 would PASS on a ROUND-ONLY slice %5d"
              % p["round_only_pass"])
    print("\n" + "=" * 74)


# ---------------------------------------------------------------------------
# the selftest. A backtest that cannot report a rejection is not measuring.
# ---------------------------------------------------------------------------

def selftest(path, objective_set):
    """Four checks, each naming a change the harness must notice.

    The point is the same as `gate-noop-measurement.py --selftest`: a reader
    that can only produce one answer has not measured anything. These drive the
    scorer to PASS and to both REJECT shapes on real recorded data."""
    checks = []

    def check(name, ok):
        checks.append((name, bool(ok)))

    bundle, _accepted = open_bundle(path)
    policies = build_policies(bundle)
    episodes = scorable_episodes(bundle)
    versions = sorted(policies)
    check("the bundle rebuilds at least two policy versions", len(versions) >= 2)
    if len(versions) < 2:
        return checks

    lo, hi = versions[0], versions[-1]
    empty = {"rules": []}

    # 1. b moves. The run's OWN final policy against an empty one must block
    #    attacks an empty policy lets through. Real rules from this bundle -
    #    a hand-written control rule would test the harness against a rule
    #    shape no run ever produced.
    forward = paired_scores(episodes, empty, policies[hi], objective_set)
    check("the run's final policy against an empty policy yields b > 0",
          forward["newly_blocked_b"] > 0)

    # 2. c moves, and it is the SAME pair inverted. A regression is not a
    #    special input shape; it is the same measurement run backwards.
    backward = paired_scores(episodes, policies[hi], empty, objective_set)
    check("the inverted pair yields c > 0, so c is reachable",
          backward["newly_breached_c"] > 0)
    check("the inverted pair's c equals the forward pair's b",
          backward["newly_breached_c"] == forward["newly_blocked_b"] > 0)

    # 3. the decision rule refuses a regression REGARDLESS of b.
    rigged = dict(backward)
    rigged["newly_blocked_b"] = 999
    passes, detail = decide(rigged)
    check("c > 0 rejects even at b = 999", (not passes) and "REGARDLESS" in detail)

    # 4. a no-op candidate - the same policy on both arms - scores b = 0 and is
    #    rejected. This is the 18-of-31 shape from the noop measurement.
    same = paired_scores(episodes, policies[hi], policies[hi], objective_set)
    passes, _ = decide(same)
    check("an identical-policy pair scores b = 0 and is REJECTED",
          same["newly_blocked_b"] == 0 and same["newly_breached_c"] == 0
          and not passes)

    # 5. a real promotion in this bundle PASSES, so PASS is reachable too.
    real = paired_scores(episodes, policies[lo], policies[hi], objective_set)
    passes, _ = decide(real)
    check("the run's own v%d -> v%d chain PASSES G4 (b=%d c=%d), so PASS is "
          "reachable" % (lo, hi, real["newly_blocked_b"],
                         real["newly_breached_c"]), passes)

    # 6. a missing slice is UNEVALUABLE, not b = 0.
    try:
        paired_scores(None, policies[lo], policies[hi], objective_set)
        check("a missing slice raises G4Unevaluable rather than scoring 0", False)
    except G4Unevaluable:
        check("a missing slice raises G4Unevaluable rather than scoring 0", True)
    return checks


def collect(target):
    p = pathlib.Path(target)
    if p.is_dir():
        return sorted(p.glob("*.c6.json"))
    return [p]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("targets", nargs="+")
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    objective_set = load_objective_set(OBJECTIVE_SET)

    if args.selftest:
        checks = selftest(args.targets[0], objective_set)
        failed = 0
        for name, ok in checks:
            print("  %s %s" % ("PASS" if ok else "FAIL", name))
            failed += 0 if ok else 1
        print("  %d check(s), %d failed" % (len(checks), failed))
        return 1 if failed else 0

    results = []
    for target in args.targets:
        for path in collect(target):
            res = backtest_bundle(path, objective_set)
            results.append(res)
            print_report(res)
    print_totals(totals(results))
    print("\nREPLAY, NOT RE-ATTACK, AND NOT A COUNTERFACTUAL RUN. See this "
          "file's docstring:\nthese are the decisions G4 would have made at "
          "each recorded promotion with the\nrecorded history held fixed. A "
          "live G4 changes the history after the first\nrejection, so no "
          "figure here is a forecast of a re-run.")
    if args.json:
        pathlib.Path(args.json).write_text(
            json.dumps({"results": results, "totals": totals(results)},
                       indent=2), encoding="utf-8")
        print("wrote %s" % args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
