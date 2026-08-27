#!/usr/bin/env python3
"""closure-backtest.py - what would the closure criterion have decided about the
promotions already made, and where does it disagree with G4?

WHY THIS EXISTS. `crucible/conductor/closure.py` turns on a promotion condition
that has never run. A gate criterion that changes the promotion rate is a metric
moving right before a deadline, and a metric that moves must be EXPECTED rather
than DISCOVERED. This answers "how much" off the bundles already on disk.

IT ALSO ANSWERS THE QUESTION THAT MATTERS MORE THAN EITHER RATE: **on the same
candidate, where do closure and G4 disagree?** Two criteria that always agree
are one criterion with two names, and one of them should be deleted. The
disagreement table is printed on every run, both directions, with the proposal
ids named.

IT IMPORTS THE PRODUCTION SCORERS. `crucible.conductor.closure.closure_scores`
and `.decide` are the same functions the live gate calls, and so are
`crucible.conductor.g4.paired_scores` and `.decide`. There is no second
implementation here to agree with itself. What this script owns is only the
BACKTEST HARNESS, and even that is not re-spelled: the bundle reader, the policy
reconstruction and the scorable-episode filter are loaded out of
`scripts/g4-backtest.py`, which already owns them.

    python scripts/closure-backtest.py <bundle-or-directory> [...]
    python scripts/closure-backtest.py <bundle> --json out.json
    python scripts/closure-backtest.py <bundle> --selftest

THE LIMIT, THE SAME ONE `g4-backtest.py` AND `gate-noop-measurement.py` PRINT.
This is a replay of recorded calls, not a re-attack. It says what the policies
would have done to the exact calls the run recorded. It cannot say what a live
agent would have done when handed a refusal it had never received before.

A SECOND LIMIT SPECIFIC TO A BACKTEST. Once either criterion rejects, the run
DIVERGES: a different policy stays in force and every later round records
different episodes. These are the decisions each criterion would have made AT
THE MOMENT OF EACH RECORDED PROMOTION, holding the recorded history fixed. They
bound agreement with that history; they do not forecast a re-run.

A THIRD LIMIT, AND IT IS NEW TODAY. **Ruling 58 (2026-08-26) gave `episode_sum`
a grouping key.** Every bundle on disk was written before that, when the DSL
could not express the one aggregate clause the ARMORER kept being asked to
close - so the 18 measured no-ops of
`docs/design/gate-noop-measurement-2026-08-25.md` were a language gap, not a
choice. **Figures from these bundles may not be pooled with any post-ruling-58
run**, and no hash distinguishes the two populations; the ruling and the date
carry the separation.
"""

import argparse
import importlib.util
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from crucible.conductor import closure as cl                    # noqa: E402
from crucible.conductor.g4 import G4Unevaluable                 # noqa: E402
from crucible.conductor.g4 import decide as g4_decide           # noqa: E402
from crucible.conductor.g4 import paired_scores                 # noqa: E402
from crucible.replay import verdict as _verdict                 # noqa: E402
from crucible.tripwire.objective_set import load_objective_set  # noqa: E402

OBJECTIVE_SET = REPO / "contracts" / "objective_set.v1.json"


def _load_g4_backtest():
    """The harness half of `scripts/g4-backtest.py`, loaded rather than copied.

    `open_bundle`, `build_policies` and `scorable_episodes` encode three
    decisions each with a written argument - the two-population split, the
    refuse-rather-than-degrade rule-id assertion, and dropping TARGET_FAULT and
    INVALID once. A second copy here would be a second owner of all three, and
    the copy is what drifts. The filename has a hyphen, so it is loaded by path;
    that is the only reason this is not a plain import.
    """
    path = REPO / "scripts" / "g4-backtest.py"
    spec = importlib.util.spec_from_file_location("_g4_backtest", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


G4B = _load_g4_backtest()

CLOSED = "CLOSED"
NOT_CLOSED = "NOT_CLOSED"
UNEVALUABLE = "UNEVALUABLE"


def backtest_bundle(path, objective_set):
    """Every accepted patch the loop promoted, judged by BOTH criteria."""
    path = pathlib.Path(path)
    bundle, accepted = G4B.open_bundle(path)
    out = {"bundle": str(path),
           "run_id": (bundle.get("run_manifest") or {}).get("run_id"),
           "offline_reader_accepts": accepted,
           "rows": [], "refusal": None}
    try:
        policies = G4B.build_policies(bundle)
    except G4B.PolicyReconstructionRefused as exc:
        out["refusal"] = str(exc)
        return out

    episodes = G4B.scorable_episodes(bundle)
    chain_ids = {x["version"]: {r["rule_id"] for r in x.get("rules") or []}
                 for x in bundle.get("policy_chain") or []}
    autopsies = {a.get("autopsy_id"): a for a in bundle.get("autopsies") or []}
    # THE JOIN A BUNDLE MAKES POSSIBLE AND THE LOOP DOES NOT. `attack_id` and
    # `round_index` are stamped onto the bundle's episode row by
    # `crucible/conductor/bundle.py`:571,588 - off the VERDICT and off the ROUND
    # RECORD. Neither is on the sealed episode, and C5 forbids an `episode_id`
    # on the autopsy. So this key exists only because the bundle producer wrote
    # it down. In the loop the gate is handed the episode object itself.
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
               "autopsy_id": pp.get("autopsy_id"),
               "attack_id": aut.get("attack_id"),
               "invariant_id": aut.get("invariant_id"),
               "promoted_rule_ids": new_ids, "code": None,
               "closure": None, "g4": None}
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

        # CLOSURE. One episode: the one the autopsy is about.
        try:
            sc = cl.closure_scores(aut, ep, policies[prior_v], policies[new_v],
                                   objective_set)
        except cl.ClosureUnevaluable as exc:
            row["closure"] = {"verdict": UNEVALUABLE, "code": exc.code,
                              "detail": exc.detail[:300], "passes": False}
        else:
            passes, detail = cl.decide(sc)
            row["closure"] = {
                "verdict": CLOSED if sc["closed"] else NOT_CLOSED,
                "code": None if passes else cl.E_NOT_CLOSED,
                "passes": passes,
                "episode_still_breaches": sc["episode_still_breaches"],
                "other_clauses_fired": sc["other_clauses_fired"],
                "detail": detail[:300]}

        # G4. The accumulating slice, which is `g4.DEFAULT_SLICE` - the same
        # arm `g4-backtest.py` calls `cumulative`. Only one arm is scored here
        # because this script's subject is the DISAGREEMENT, and comparing
        # closure against three G4 denominators would produce three
        # disagreement tables nobody asked for. The slice question has an owner.
        cumulative = [e for e in episodes if (e.get("round_index") or 0) <= rnd]
        try:
            g4sc = paired_scores(cumulative, policies[prior_v],
                                 policies[new_v], objective_set)
        except G4Unevaluable as exc:
            row["g4"] = {"verdict": UNEVALUABLE, "detail": str(exc)[:300],
                         "passes": False}
        else:
            g4passes, g4detail = g4_decide(g4sc)
            row["g4"] = {"verdict": "PASS" if g4passes else "FAIL",
                         "b": g4sc["newly_blocked_b"],
                         "c": g4sc["newly_breached_c"],
                         "n": g4sc["n"], "passes": g4passes,
                         "detail": g4detail[:300]}
        out["rows"].append(row)
    return out


# ---------------------------------------------------------------------------
# reporting. TWO POPULATIONS, NEVER POOLED.
# ---------------------------------------------------------------------------

def _pop():
    return {"promotions": 0, "closure_pass": 0, "closure_not_closed": 0,
            "closure_unevaluable": 0, "closure_codes": {},
            "closure_closed_but_episode_still_breaches": 0,
            "g4_pass": 0, "g4_fail": 0, "g4_unevaluable": 0,
            "both_pass": 0, "both_reject": 0,
            "closure_pass_g4_reject": 0, "g4_pass_closure_reject": 0,
            "unclassified": 0,
            "disagreements": []}


def totals(results):
    acc = {"bundles": 0, "refused_reconstruction": 0,
           "accepted_pop": _pop(), "refused_pop": _pop()}
    for res in results:
        acc["bundles"] += 1
        if res["refusal"]:
            acc["refused_reconstruction"] += 1
            continue
        pop = (acc["accepted_pop"] if res["offline_reader_accepts"]
               else acc["refused_pop"])
        for row in res["rows"]:
            pop["promotions"] += 1
            cl_r, g4_r = row.get("closure"), row.get("g4")
            if cl_r is None or g4_r is None:
                pop["unclassified"] += 1
                continue
            if cl_r["verdict"] == CLOSED:
                pop["closure_pass"] += 1
                if cl_r.get("episode_still_breaches"):
                    pop["closure_closed_but_episode_still_breaches"] += 1
            elif cl_r["verdict"] == NOT_CLOSED:
                pop["closure_not_closed"] += 1
            else:
                pop["closure_unevaluable"] += 1
                code = cl_r.get("code") or "?"
                pop["closure_codes"][code] = pop["closure_codes"].get(code, 0) + 1
            pop["g4_%s" % {"PASS": "pass", "FAIL": "fail",
                           UNEVALUABLE: "unevaluable"}[g4_r["verdict"]]] += 1
            if cl_r["passes"] and g4_r["passes"]:
                pop["both_pass"] += 1
            elif not cl_r["passes"] and not g4_r["passes"]:
                pop["both_reject"] += 1
            elif cl_r["passes"]:
                pop["closure_pass_g4_reject"] += 1
                pop["disagreements"].append(
                    {"proposal_id": row["proposal_id"], "bundle": res["bundle"],
                     "direction": "closure PASS / G4 REJECT",
                     "invariant_id": row["invariant_id"],
                     "b": g4_r.get("b"), "n": g4_r.get("n")})
            else:
                pop["g4_pass_closure_reject"] += 1
                pop["disagreements"].append(
                    {"proposal_id": row["proposal_id"], "bundle": res["bundle"],
                     "direction": "G4 PASS / closure REJECT",
                     "invariant_id": row["invariant_id"],
                     "closure_code": cl_r.get("code"),
                     "b": g4_r.get("b"), "n": g4_r.get("n")})
    return acc


def print_report(results):
    for res in results:
        print("=" * 78)
        print("bundle : %s" % res["bundle"])
        print("reader : %s" % ("ACCEPTS" if res["offline_reader_accepts"]
                               else "REFUSES - separate population"))
        if res["refusal"]:
            print("REFUSED: %s" % res["refusal"])
            continue
        for row in res["rows"]:
            cl_r, g4_r = row.get("closure") or {}, row.get("g4") or {}
            print("  %-40s round %-2s  closure %-12s  G4 %-11s %s"
                  % (row["proposal_id"], row["round_index"],
                     cl_r.get("verdict") or row.get("code") or "-",
                     g4_r.get("verdict") or "-",
                     ("b=%s n=%s" % (g4_r.get("b"), g4_r.get("n"))
                      if "b" in g4_r else "")))
            if cl_r.get("code"):
                print("      %s" % cl_r["code"])


def print_totals(acc):
    print("=" * 78)
    print("TOTALS. TWO POPULATIONS, NEVER POOLED.")
    for key, label in (("accepted_pop", "bundles the OFFLINE READER ACCEPTS"),
                       ("refused_pop", "bundles the OFFLINE READER REFUSES - "
                                       "read with json.load, separate "
                                       "population, never pooled")):
        pop = acc[key]
        if not pop["promotions"]:
            continue
        print("\n  %s" % label)
        print("    recorded promotions judged      %d" % pop["promotions"])
        print("    CLOSURE would have PROMOTED     %d" % pop["closure_pass"])
        print("      of which the EPISODE still breaches on another clause  %d"
              % pop["closure_closed_but_episode_still_breaches"])
        print("    CLOSURE would have REJECTED     %d"
              % (pop["closure_not_closed"] + pop["closure_unevaluable"]))
        print("      E_BREACH_NOT_CLOSED           %d" % pop["closure_not_closed"])
        print("      unevaluable                   %d" % pop["closure_unevaluable"])
        for code, n in sorted(pop["closure_codes"].items()):
            print("        %-38s %d" % (code, n))
        print("    G4 would have PROMOTED          %d" % pop["g4_pass"])
        print("    G4 would have REJECTED          %d"
              % (pop["g4_fail"] + pop["g4_unevaluable"]))
        print()
        print("    WHERE THE TWO DISAGREE, on the same candidate")
        print("      both promote                  %d" % pop["both_pass"])
        print("      both reject                   %d" % pop["both_reject"])
        print("      closure PROMOTES, G4 REJECTS  %d"
              % pop["closure_pass_g4_reject"])
        print("      G4 PROMOTES, closure REJECTS  %d"
              % pop["g4_pass_closure_reject"])
        if pop["unclassified"]:
            print("      unclassified rows             %d" % pop["unclassified"])
        for d in pop["disagreements"][:20]:
            print("        %-40s %s  %s"
                  % (d["proposal_id"], d["direction"], d.get("invariant_id")))
        if len(pop["disagreements"]) > 20:
            print("        ... %d more" % (len(pop["disagreements"]) - 20))
    print()
    print(cl.METHOD_LIMIT)
    print()
    print("RULING 58 (2026-08-26) GAVE `episode_sum` A GROUPING KEY. Every "
          "bundle read here predates it, so these figures may not be pooled "
          "with any post-ruling-58 run. No hash distinguishes the two.")


# ---------------------------------------------------------------------------
# selftest - a backtest that returns the same answer regardless of input is not
# measuring anything
# ---------------------------------------------------------------------------

def selftest(path, objective_set):
    """Four checks, each naming a change this harness MUST notice."""
    import copy
    raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    results = []

    def check(name, ok, detail):
        results.append((name, bool(ok), detail))

    def rows_of(bundle):
        tmp = pathlib.Path(path).with_suffix(".closure-selftest.tmp.json")
        tmp.write_bytes(json.dumps(bundle).encode("utf-8"))
        try:
            return backtest_bundle(tmp, objective_set)
        finally:
            tmp.unlink(missing_ok=True)

    base = rows_of(raw)
    verdicts = {r["proposal_id"]: (r.get("closure") or {}).get("verdict")
                for r in base["rows"]}
    check("the unmodified bundle yields at least one closure verdict",
          any(v for v in verdicts.values()), json.dumps(verdicts))

    # 1. The autopsy loses its clause. Every row must become UNEVALUABLE with
    #    the clause code - NOT closed, and not silently skipped.
    doctored = copy.deepcopy(raw)
    for a in doctored.get("autopsies") or []:
        a.pop("invariant_id", None)
    res = rows_of(doctored)
    codes = {(r.get("closure") or {}).get("code") for r in res["rows"]}
    check("an autopsy with no clause makes every row UNEVALUABLE rather than "
          "closed",
          codes and codes <= {cl.E_CLAUSE_MISSING},
          str(sorted(c for c in codes if c)))

    # 2. The trace is tampered with. The harness must refuse the pairing rather
    #    than measure a different episode under the recorded proposal id.
    doctored = copy.deepcopy(raw)
    touched = 0
    for ep in doctored.get("episodes") or []:
        for e in ep.get("episode_prefix") or []:
            if e.get("kind") == "TOOL_EXECUTED":
                e["args"] = dict(e.get("args") or {}, _selftest_marker=1)
                touched += 1
    res = rows_of(doctored)
    codes = {(r.get("closure") or {}).get("code") for r in res["rows"]}
    check("a trace whose arguments moved is refused rather than measured",
          touched and cl.E_TRACE_MISMATCH in codes,
          "touched %d executed calls, codes %s"
          % (touched, sorted(c for c in codes if c)))

    # 3. THE ONE THAT PROVES IT IS NOT ALWAYS-REJECT. Replace every promoted
    #    rule with an unconditional deny on the class the autopsy names, and the
    #    same rows must flip to CLOSED.
    doctored = copy.deepcopy(raw)
    flipped = _install_blanket_denies(doctored)
    res = rows_of(doctored) if flipped else None
    after = ({r["proposal_id"]: (r.get("closure") or {}).get("verdict")
              for r in res["rows"]} if res else {})
    check("a NOT_CLOSED row flips to CLOSED when the promoted rule is replaced "
          "by one that plainly stops the trace",
          flipped and any(v == CLOSED for v in after.values()),
          "flipped %d rule(s); %s" % (flipped, json.dumps(after)))

    print("SELFTEST")
    bad = 0
    for name, ok, detail in results:
        print("  %-4s %s" % ("PASS" if ok else "FAIL", name))
        print("        %s" % detail)
        if not ok:
            bad += 1
    print("  %d check(s), %d failed" % (len(results), bad))
    return 0 if bad == 0 else 1


def _install_blanket_denies(bundle):
    """Replace every promoted rule with `cap:<class> => deny`.

    The class is READ OFF THE AUTOPSY (`capability_classes_involved`), never
    defaulted: a hardcoded fallback would make this check pass on a bundle where
    it should not, which is a selftest that cannot fail wearing a selftest's
    clothes. Same argument as `gate-noop-measurement.py::_promoted_class`.
    """
    from crucible.dsl.parser import parse_rule
    from crucible.dsl.serialize import assign_rule_id, rule_body

    autopsies = {a.get("autopsy_id"): a for a in bundle.get("autopsies") or []}
    flipped = 0
    for pp in bundle.get("patch_proposals") or []:
        if not pp.get("accepted") or not pp.get("rules"):
            continue
        aut = autopsies.get(pp.get("autopsy_id")) or {}
        classes = aut.get("capability_classes_involved") or []
        if not classes:
            continue
        body = "cap:%s => deny" % classes[0]
        text = "rule r_new1: %s origin armorer:9" % body
        rid = assign_rule_id(rule_body(parse_rule(text)))
        entry = {"rule_id": rid, "verb": "deny",
                 "dsl_text": "rule %s: %s origin armorer" % (rid, body),
                 "origin": "armorer"}
        old = pp["rules"][0]["rule_id_assigned"]
        pp["rules"][0] = {"rule_id_assigned": rid,
                          "dsl_text": entry["dsl_text"],
                          "rule_id_as_proposed": "r_new1"}
        for chain in bundle.get("policy_chain") or []:
            chain["rules"] = [entry if r["rule_id"] == old else r
                              for r in chain["rules"]]
        flipped += 1
    return flipped


def collect(target):
    target = pathlib.Path(target)
    if target.is_dir():
        return sorted(target.glob("*.c6.json"))
    return [target]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", nargs="+",
                    help="a .c6.json evidence bundle, or a directory of them")
    ap.add_argument("--json", help="write every row here")
    ap.add_argument("--quiet", action="store_true",
                    help="totals only, no per-promotion rows")
    ap.add_argument("--selftest", action="store_true",
                    help="prove this harness can fail, in both directions")
    args = ap.parse_args(argv)

    objective_set = load_objective_set(OBJECTIVE_SET)
    if args.selftest:
        return selftest(args.path[0], objective_set)

    paths = [p for t in args.path for p in collect(t)]
    if not paths:
        raise SystemExit("E_NO_BUNDLES: nothing matched *.c6.json")
    results = [backtest_bundle(p, objective_set) for p in paths]
    if not args.quiet:
        print_report(results)
    # RULING 60 PART 3. Every figure over a batch prints its acceptance beside
    # it. This script already splits accepted from refused bundles by verifying
    # each one LIVE, which is the stronger instrument; the banner adds the third
    # population that split cannot see - a bundle with no reader verdict on disk
    # at all. A figure printed without its acceptance count is the failure mode
    # returning.
    _verdict.print_batch_banner(paths, "bundle")
    print_totals(totals(results))
    if args.json:
        out = pathlib.Path(args.json)
        out.write_bytes(json.dumps(
            {"results": results, "method_limit": cl.METHOD_LIMIT},
            indent=1).encode("utf-8"))
        print("\nwrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
