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
    G4BaselineUnavailable, G4Unevaluable, decide, load_baseline, paired_scores)
from crucible.dsl.parser import parse_rule                      # noqa: E402
from crucible.dsl.serialize import (                            # noqa: E402
    assign_rule_id, compile_rule, rule_body, sort_rules)
from crucible.replay import verdict as _verdict                 # noqa: E402
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


def backtest_bundle(path, objective_set, baseline=None):
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
        #
        # AND, WHEN IT IS ON DISK, THE FROZEN v0 BASELINE - the 50-instance
        # training slice `measurement-spec.md`:1151 states `b = 30, c = 0`
        # against. THE THRESHOLD IS IDENTICAL IN ALL THREE ARMS; it is read out
        # of the hash-locked contract by `crucible.conductor.g4` and is not
        # spelled here. ONLY THE DENOMINATOR MOVES, which is the entire
        # experiment. Anything else differing between arms would be a defect.
        cumulative = [e for e in episodes
                      if (e.get("round_index") or 0) <= rnd]
        this_round = [e for e in episodes if e.get("round_index") == rnd]
        arms = [("cumulative", cumulative), ("round_only", this_round)]
        if baseline is not None:
            arms.append(("baseline", baseline))
        for label, slice_ in arms:
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

    # WOULD THIS RUN HAVE HALTED. `contracts/gate_rule.v1.yaml` halts on two
    # consecutive rejections, and that is the figure a person deciding whether
    # to turn G4 on actually needs: a rejection costs a round, a HALT costs the
    # run and a human's attention at 2am.
    #
    # ROUND ORDER, NOT `patch_proposals` ORDER. The rows above are appended in
    # the order the bundle lists proposals; a streak counted in that order would
    # be a streak of something other than consecutive rounds.
    #
    # THE SAME CAVEAT AS EVERY OTHER FIGURE HERE, AND IT BITES HARDEST ON THIS
    # ONE: once G4 rejects, the real run DIVERGES. This counts rejections in the
    # recorded history, which is an upper bound on agreement with that history,
    # not a forecast of what a re-run would do.
    halt_after = _halt_after()
    for label in ("cumulative", "round_only", "baseline"):
        streak, halted_at = 0, None
        for row in sorted(out["rows"], key=lambda r: (r["round_index"] or 0)):
            s = row.get(label)
            if not s or "unevaluable" in s:
                continue
            if s["g4_passes"]:
                streak = 0
                continue
            streak += 1
            if streak >= halt_after:
                halted_at = row["round_index"]
                break
        out.setdefault("halt", {})[label] = halted_at
    return out


def _halt_after(path=None):
    """How many consecutive rejections HALT a run, READ off the contract.

    `on:` IS A YAML 1.1 BOOLEAN. PyYAML parses the bare key `on` as `True`, so
    `halt.get("on")` is None - and a None falling through to a default would
    give this backtest a halt rule the contract never stated. Both spellings are
    read; the contract file is hash-locked and is not edited to suit a parser.
    """
    import yaml
    doc = yaml.safe_load(
        pathlib.Path(path or (REPO / "contracts" / "gate_rule.v1.yaml"))
        .read_text(encoding="utf-8"))
    halt = (doc or {}).get("halt") or {}
    on = halt.get("on", halt.get(True))
    known = {"two_consecutive_rejections": 2}
    if on not in known:
        raise SystemExit(
            "E_G4_CONTRACT_UNREADABLE: gate_rule.v1.yaml declares halt.on = %r, "
            "which this script has no reading for. It will not guess how many "
            "rejections stop a run." % (on,))
    return known[on]


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

def totals(results):
    def _pop():
        return {"promotions": 0, "cumulative_pass": 0, "round_only_pass": 0,
                "c_gt_0": 0, "b_lt_3": 0, "b_zero": 0, "unclassified": 0,
                # THE BASELINE ARM. `baseline_seen` is counted separately from
                # `promotions` on purpose: a run without the baseline on disk
                # must report "not measured" rather than a pass rate computed
                # over a denominator of zero.
                "baseline_seen": 0, "baseline_pass": 0, "baseline_b_zero": 0,
                "baseline_b_hist": {},
                # RUNS, not promotions. A rejection costs a round; two in a row
                # cost the run.
                "runs": 0, "halt_cumulative": 0, "halt_round_only": 0,
                "halt_baseline": 0, "halt_baseline_measurable": 0}
    acc = {"bundles": 0, "refused_reconstruction": 0,
           "accepted_pop": _pop(), "refused_pop": _pop()}
    for res in results:
        acc["bundles"] += 1
        if res["refusal"]:
            acc["refused_reconstruction"] += 1
            continue
        pop = acc["accepted_pop"] if res["offline_reader_accepts"] else acc["refused_pop"]
        halt = res.get("halt") or {}
        if res["rows"]:
            pop["runs"] += 1
            if halt.get("cumulative") is not None:
                pop["halt_cumulative"] += 1
            if halt.get("round_only") is not None:
                pop["halt_round_only"] += 1
            if any(r.get("baseline") for r in res["rows"]):
                pop["halt_baseline_measurable"] += 1
                if halt.get("baseline") is not None:
                    pop["halt_baseline"] += 1
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
            bl = row.get("baseline")
            if bl and "unevaluable" not in bl:
                pop["baseline_seen"] += 1
                if bl["g4_passes"]:
                    pop["baseline_pass"] += 1
                if bl["b"] == 0:
                    pop["baseline_b_zero"] += 1
                # THE HISTOGRAM IS THE FINDING, NOT THE RATE. Over the frozen
                # fifty the b distribution is bimodal with almost nothing
                # between - a patch closes nothing or closes the whole PII
                # cluster at once - which is why a rejection here is a patch
                # that did nothing rather than a threshold set too high. A pass
                # rate alone hides that completely.
                pop["baseline_b_hist"][bl["b"]] = (
                    pop["baseline_b_hist"].get(bl["b"], 0) + 1)
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
        print("  r%-2s %-46s v%s->v%s" % (row["round_index"], row["proposal_id"],
                                          row["prior_policy_version"],
                                          row["promoted_policy_version"]))
        arms = [("cumulative", row.get("cumulative") or {}),
                ("round_only", row.get("round_only") or {})]
        if row.get("baseline"):
            arms.append(("baseline", row["baseline"]))
        for label, s in arms:
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
        print("    --- HALT: two consecutive rejections stop the run ---")
        print("    runs with a promotion                    %5d" % p["runs"])
        print("    would HALT (cumulative slice)            %5d" % p["halt_cumulative"])
        print("    would HALT (round-only slice)            %5d" % p["halt_round_only"])
        if p["halt_baseline_measurable"]:
            print("    would HALT (baseline slice)              %5d of %5d"
                  % (p["halt_baseline"], p["halt_baseline_measurable"]))
        if not p["baseline_seen"]:
            print("    [baseline slice] NOT MEASURED - no frozen v0 baseline "
                  "was loaded. Not a zero.")
            continue
        print("    --- THE SAME THRESHOLD OVER THE FROZEN v0 SLICE ---")
        print("    G4 would PASS   (baseline slice)         %5d of %5d"
              % (p["baseline_pass"], p["baseline_seen"]))
        print("    G4 would REJECT (baseline slice)         %5d"
              % (p["baseline_seen"] - p["baseline_pass"]))
        print("      of which b == 0 (closed NOTHING)       %5d"
              % p["baseline_b_zero"])
        print("    b histogram over the baseline            %s"
              % dict(sorted(p["baseline_b_hist"].items())))
        print("      READ THE HISTOGRAM, NOT THE RATE. It is bimodal with "
              "almost nothing between:")
        print("      a patch closes NOTHING or closes the whole PII cluster at "
              "once, so almost")
        print("      every rejection is a patch that did nothing rather than a "
              "threshold set too high.")
    print("\n" + "=" * 74)
    print("THE THRESHOLD IS IDENTICAL IN EVERY ARM - it is read out of the "
          "hash-locked\ncontract by crucible.conductor.g4. ONLY THE DENOMINATOR "
          "MOVES.")
    print("REPLAY, NOT RE-ATTACK. Single-sample, k=1, no stability estimate.")


# ---------------------------------------------------------------------------
# the selftest. A backtest that cannot report a rejection is not measuring.
# ---------------------------------------------------------------------------

def selftest(path, objective_set, baseline=None):
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

    # 5. PASS IS REACHABLE. A suite that can only ever report REJECT has not
    #    measured anything, and this is the check that says otherwise.
    #
    #    IT USED TO ASK ONLY WHETHER THIS BUNDLE'S OWN v_lo -> v_hi CHAIN
    #    PASSES, AND THAT MADE IT BUNDLE-DEPENDENT: on
    #    evidence/batch-night-2026-08-25/run-05.c6.json the whole chain scores
    #    b = 2 over its own slice and the check FAILED - verified against main's
    #    copy of this script on 2026-08-26, so it is not a regression from the
    #    baseline work. A control whose result depends on which argument you
    #    hand it can be made to pass by choosing the input, which is a weaker
    #    control than it looks.
    #
    #    So both pairs available in every bundle are tried and the check passes
    #    if EITHER reaches PASS. `decide` returning True is the property under
    #    test; which recorded chain happens to get there is not. The pair that
    #    succeeded is named in the row, because "PASS is reachable" and "this
    #    run's promotions would have survived" are different claims and only the
    #    first is being made here.
    tried = []
    reachable = False
    real = paired_scores(episodes, policies[lo], policies[hi], objective_set)
    ok, _ = decide(real)
    reachable = reachable or ok
    tried.append("own-chain v%d->v%d b=%d %s"
                 % (lo, hi, real["newly_blocked_b"], "PASS" if ok else "reject"))
    ok, _ = decide(forward)
    reachable = reachable or ok
    tried.append("empty->v%d b=%d %s"
                 % (hi, forward["newly_blocked_b"], "PASS" if ok else "reject"))
    if baseline:
        # THE BASELINE ARM IS WHERE PASS IS ACTUALLY DEMONSTRABLE ON REAL DATA,
        # AND THE REASON IS ITSELF THE FINDING: over a run's own six-to-thirty
        # episodes no recorded chain in these bundles reaches b >= 3 at all.
        # Over the frozen fifty the same final policy closes the whole
        # PII cluster at once.
        bl = paired_scores(baseline, empty, policies[hi], objective_set)
        ok, _ = decide(bl)
        reachable = reachable or ok
        tried.append("baseline empty->v%d b=%d %s"
                     % (hi, bl["newly_blocked_b"], "PASS" if ok else "reject"))
    check("PASS is reachable on real recorded data (%s)" % "; ".join(tried),
          reachable)

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
    ap.add_argument("--no-baseline", action="store_true",
                    help="skip the frozen v0 baseline arm even if it is on "
                         "disk. For reproducing a report taken before the "
                         "baseline existed.")
    args = ap.parse_args(argv)

    objective_set = load_objective_set(OBJECTIVE_SET)

    # THE THIRD ARM, AND ITS ABSENCE IS SAID OUT LOUD RATHER THAN DEFAULTED.
    # A backtest that quietly dropped the baseline arm would print a two-arm
    # report indistinguishable from one where the baseline scored badly.
    baseline = None
    if not args.no_baseline:
        try:
            baseline = load_baseline(objective_set=objective_set).slice()
            print("baseline arm: %d frozen v0 episodes, "
                  "docs/proof/v0-attack-baseline-freeze.json" % len(baseline))
        except G4BaselineUnavailable as exc:
            print("baseline arm: NOT MEASURED. %s" % exc)

    if args.selftest:
        checks = selftest(args.targets[0], objective_set, baseline)
        failed = 0
        for name, ok in checks:
            print("  %s %s" % ("PASS" if ok else "FAIL", name))
            failed += 0 if ok else 1
        print("  %d check(s), %d failed" % (len(checks), failed))
        return 1 if failed else 0

    results = []
    aggregated = []
    for target in args.targets:
        for path in collect(target):
            res = backtest_bundle(path, objective_set, baseline)
            results.append(res)
            aggregated.append(path)
            print_report(res)
    # RULING 60 PART 3. `offline_reader_accepts` is already carried per row and
    # the totals are already split by it; what was missing is the count stated
    # ONCE, above the figures, including the runs that carry no reader verdict
    # at all. A figure printed without its acceptance count is the failure mode
    # returning.
    _verdict.print_batch_banner(aggregated, "bundle")
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
