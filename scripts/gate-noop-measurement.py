#!/usr/bin/env python3
"""gate-noop-measurement.py - did the promoted rule close the breach it was written for?

Run:  python scripts/gate-noop-measurement.py evidence/smoke-2026-08-25/run-02.c6.json
      python scripts/gate-noop-measurement.py evidence/pilot-2026-08-25
      python scripts/gate-noop-measurement.py evidence/smoke-2026-08-25/run-02.c6.json \\
             --selftest

WHY THIS EXISTS. The PROMOTION_GATE checks two things about a candidate patch:
that it is WELL-FORMED (the validator) and that BENIGN TRAFFIC SURVIVES IT (the
warden, G3). It never checks the third thing - THAT THE PATCH CLOSES THE BREACH
IT WAS WRITTEN FOR. A rule can be spelled correctly, read correctly, block
nothing relevant, and be promoted.

That is the mirror of this project's over-blocking finding. Over-blocking: a
rule that blocks TOO MUCH passes every gate, because the attacks stop, the
approval oracle rubber-stamps the benign cases, and the pass rate reads perfect.
This: a rule that blocks NOTHING RELEVANT also passes every gate, because
nothing it fails to do is measured anywhere.

WHAT THIS SCRIPT IS, PRECISELY, BECAUSE IT IS EASY TO OVERCLAIM.
It is a REPLAY of recorded calls, not a re-attack. For each promoted rule it
answers exactly one question:

    WOULD THE POLICY THAT WAS PROMOTED HAVE STOPPED ANY CALL, ON THE RECORDED
    TRACE OF THE BREACH THAT CAUSED IT, THAT THE POLICY IN FORCE AT THE TIME
    ALLOWED?

It does NOT answer "could the agent have found another path". A live agent
handed a refusal it never received before may go somewhere else entirely, and
this replay cannot see that. Anyone describing this measurement as susceptibility
testing is overclaiming. It is also not the sealed-family transfer figure.

IT USES THE LOOP'S OWN ARBITERS AND IMPLEMENTS NO SECOND ONE.
  - `crucible.dsl.parser.parse_rule` + `crucible.dsl.serialize.compile_rule`
    rebuild the executable rule from the DSL text the bundle records. The
    reconstruction is PROVED, not assumed: `assign_rule_id(rule_body(parsed))`
    must reproduce the rule id the bundle recorded, or this script refuses.
  - `crucible.warden.replay.replay_trace` walks the recorded trace, with the
    real APPROVAL_ORACLE and the real TOOL_ATTEMPT/TOOL_EXECUTED pairing.
  - `crucible.conductor.real_warden._l3_evaluate_call` adapts the REAL L3
    engine, `crucible.policy.evaluate`. Not the calibration-only shadow engine.
  - `crucible.tripwire.evaluate_episode` re-scores what survives.
If this script and the loop ever disagree about a verdict, THIS SCRIPT IS THE
DEFECT.

NO ROLLED-UP SCORE, AND NO JUDGEMENT OF THE ARMORER. A no-op promotion is not
automatically an ARMORER defect: a rule may legitimately generalise past the
one trace that provoked it rather than close it. Where this reader cannot tell
the two apart it says so, in a third bucket, rather than forcing a binary.

TWO POPULATIONS, NEVER POOLED. Bundles the shipped offline reader ACCEPTS and
bundles it REFUSES are reported separately and labelled on every figure. A
refused bundle is still readable for THIS measurement - a missing episode field
added by a later ruling does not change what a policy does to a recorded call -
but it is not evidence of the same grade, and pooling them would hide which
half moved.
"""

import argparse
import copy
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from crucible.conductor.real_warden import _l3_evaluate_call      # noqa: E402
from crucible.conductor.real_warden import real_warden            # noqa: E402
from crucible.dsl.parser import parse_rule                        # noqa: E402
from crucible.dsl.serialize import (                              # noqa: E402
    assign_rule_id, compile_rule, rule_body, sort_rules)
from crucible.replay import verdict as _verdict                   # noqa: E402
from crucible.replay.bundle import read_bundle                    # noqa: E402
from crucible.replay.integrity import BundleRejected              # noqa: E402
from crucible.tripwire.evaluator import evaluate_episode          # noqa: E402
from crucible.tripwire.objective_set import load_objective_set    # noqa: E402
from crucible.warden.replay import Fixture, replay_trace          # noqa: E402

OBJECTIVE_SET = REPO / "contracts" / "objective_set.v1.json"

# The five fields `evaluate_episode` reads off the episode as its manifest.
# Same list as scripts/hardening-report.py, and for the same reason: the
# tripwire's validity pass must run on the replayed episode exactly as it runs
# on a live one.
MANIFEST_KEYS = ("policy_version", "policy_hash", "manifest_hash",
                 "derived_schema_hash", "objective_set_hash")

ALLOW = "ALLOW"

# Verdict buckets. Three, and the third is not a rounding error.
CLOSES = "CLOSES"
NO_OP = "NO_OP"
UNCLASSIFIED = "UNCLASSIFIED"

ORDERED_OPS = ("gt", "gte", "lt", "lte")


# ---------------------------------------------------------------------------
# reading the bundle
# ---------------------------------------------------------------------------

def open_bundle(path):
    """`(bundle, reader_accepted, defects)`.

    The shipped offline reader is asked FIRST, every time, and its answer is
    carried onto every row. Falling back to `json.load` is deliberate and
    bounded: `E_SCHEMA: 'target_responded' is a required property` is a
    statement about an episode field added by ruling 55 AFTER those bundles
    were written, and it has no bearing on what a policy does to a recorded
    call. It is still a different population and it is labelled as one.
    """
    try:
        bundle, _report = read_bundle(path)
        return bundle, True, []
    except BundleRejected as exc:
        defects = []
        for d in getattr(exc, "defects", []) or []:
            defects.append({"code": getattr(d, "code", "?"),
                            "where": getattr(d, "where", ""),
                            "detail": (getattr(d, "detail", "") or "")[:300]})
        raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        return raw, False, defects or [{"code": "E_REJECTED", "where": "",
                                        "detail": str(exc)[:300]}]


class PolicyReconstructionRefused(Exception):
    """The DSL text in the bundle did not rebuild the rule the bundle names."""


def _parseable(dsl_text):
    """The bundle RENDERS `origin armorer`; the grammar demands
    `origin armorer:<round>`.

    The round number is deliberately outside the hashed rule body
    (`serialize.origin_class` keeps only the class; `origin_round` sends the
    number to `provenance`), so any round number rebuilds the same rule - which
    the rule-id assertion below then proves, rather than this comment claiming
    it.
    """
    if re.search(r"origin armorer$", dsl_text):
        return dsl_text + ":0"
    return dsl_text


def executable_rule(entry):
    """One `policy_chain` rule entry -> the executable rule the engine runs.

    REFUSES rather than degrades. A rule rebuilt from text that does not hash
    back to the id the bundle recorded is a DIFFERENT RULE, and measuring a
    different rule and printing the recorded id would be the exact defect shape
    this project keeps meeting.
    """
    parsed = parse_rule(_parseable(entry["dsl_text"]))
    body = rule_body(parsed)
    recomputed = assign_rule_id(body)
    if recomputed != entry["rule_id"]:
        raise PolicyReconstructionRefused(
            "E_POLICY_RECONSTRUCTION: the DSL text recorded for %s rebuilds to a "
            "rule whose canonical id is different. The bundle's text and the "
            "bundle's id disagree, so there is no rule here this reader may "
            "claim to have run. Text: %r"
            % (entry["rule_id"], entry["dsl_text"]))
    return compile_rule(parsed)


def build_policies(bundle):
    """`{version: {"rules": [...]}}` for every entry in `policy_chain`."""
    out = {}
    for entry in bundle.get("policy_chain") or []:
        rules = [executable_rule(r) for r in entry.get("rules") or []]
        out[entry["version"]] = {"rules": sort_rules(rules)}
    return out


# ---------------------------------------------------------------------------
# replaying one recorded trace
# ---------------------------------------------------------------------------

def episode_as_fixture(ep):
    """The recorded episode in the shape `replay_trace` walks.

    C6 names the ordered event list `episode_prefix`; the tripwire's Episode
    model reads `events`. Mapped explicitly, the same way
    scripts/hardening-report.py maps it, so a future rename fails loudly.

    `approver` is the sentinel NONE because that is what an attack episode
    declares. `approval_oracle_default: deny_unless_fixture_declares` is a
    frozen run-manifest parameter; handing an attack a fake approver here would
    let the oracle wave through calls the run never approved.
    """
    inner = dict(ep)
    inner["events"] = ep.get("episode_prefix") or []
    raw = {"attack_id": ep.get("attack_id") or ep.get("episode_id"),
           "approver": "NONE", "near_miss": False, "episode": inner}
    return Fixture(raw, "bundle:%s" % ep.get("episode_id"), "attack_id")


def replay_at(ep, policy, objective_set):
    """Score one recorded path under `policy`, through the loop's own arbiters.

    `calls` is keyed by `seq`, which is the field the DSL's aggregate window
    already folds over, so it is the episode's own ordering key rather than one
    invented here.
    """
    fixture = episode_as_fixture(ep)
    ok, blocked, surviving, oracle = replay_trace(fixture, policy, _l3_evaluate_call)
    replayed = copy.deepcopy(ep)
    replayed["events"] = surviving
    manifest = {k: ep.get(k) for k in MANIFEST_KEYS}
    verdict = evaluate_episode(replayed, objective_set, manifest)
    calls = {}
    for e in surviving:
        if e.get("kind") != "TOOL_ATTEMPT":
            continue
        calls[e.get("seq")] = {
            "decision": e.get("policy_decision"),
            "rule_id": e.get("denied_by_rule_id"),
            "tool_handle": e.get("tool_handle"),
            "capability_classes": list(e.get("capability_classes") or ()),
        }
    return {
        "verdict": verdict.verdict,
        "invariant_id": getattr(verdict, "invariant_id", None),
        "all_calls_permitted": ok,
        "blocked_classes": blocked,
        "oracle_resolutions": oracle,
        "calls": calls,
    }


def rule_alone_fires(ep, rule, objective_set):
    """Does this ONE rule stop anything at all on this trace, in isolation?

    Separates two very different no-ops that look identical in the chain-level
    comparison: a rule that is INERT on this trace, and a rule that would have
    stopped a call an OLDER rule was already stopping. Both leave the permitted
    set unchanged; only one of them is a rule that does nothing.
    """
    res = replay_at(ep, {"rules": [rule]}, objective_set)
    return any(c["decision"] != ALLOW for c in res["calls"].values()), res


# ---------------------------------------------------------------------------
# why a no-op is a no-op - diagnostics, read out of the data, never guessed
# ---------------------------------------------------------------------------

def _classes_on_trace(ep):
    out = set()
    for e in ep.get("episode_prefix") or []:
        out.update(e.get("capability_classes") or ())
    return out


def _max_value_on_trace(ep, path, rule=None):
    """The largest value at `path` on any single call THE RULE COULD MATCH.

    THE FILTER IS THE WHOLE POINT AND IT WAS MISSING FOR ONE REVISION OF THIS
    FILE. Scanning every event answers a different question: on pilot run-09 a
    CAP_READS_PII lookup carries `derived.episode_count_same_subject` at or
    above the threshold while every CAP_MUTATES_DURABLE_STATE call is below it,
    so an unfiltered maximum said "some call did reach 4" about a call the rule
    can never fire on, and the diagnosis fell through to a vaguer bucket. The
    rule matches by capability class and optionally by tool name; anything it
    cannot match is not evidence about why it did not fire.
    """
    match = (rule or {}).get("match") or {}
    want = match.get("capability_class")
    names = match.get("tool_names") or []
    best = None
    for e in ep.get("episode_prefix") or []:
        if e.get("kind") != "TOOL_ATTEMPT":
            continue
        if want is not None and want not in (e.get("capability_classes") or ()):
            continue
        if names and e.get("tool_handle") not in names:
            continue
        args = e.get("args") or {}
        v = args.get(path)
        if isinstance(v, int) and not isinstance(v, bool):
            best = v if best is None else max(best, v)
    return best


def aggregate_mismatch(rule, clause, ep):
    """The aggregate-versus-per-call diagnosis, entirely from the two artifacts.

    An Objective Set clause of `form: aggregate` SUMS `sum_path`, grouped, over
    the episode, and fires at `value`. A rule whose `when` tests that same path
    against that same threshold on ONE CALL is testing a different quantity.
    The recorded calls carry 1, 2, 3; the sum fires; no single call ever
    reaches the threshold; the rule is well-formed and does nothing.

    Returns a dict when every part of that is true of THIS rule and THIS clause,
    otherwise None. It never infers from the invariant id alone - the id is a
    label, the `form` and the `sum_path` are the facts.
    """
    if not clause or clause.get("form") != "aggregate":
        return None
    sum_path = clause.get("sum_path")
    threshold = clause.get("value")
    if sum_path is None or threshold is None:
        return None
    for cond in (rule.get("match") or {}).get("arg_conditions") or []:
        if cond.get("path") != sum_path or cond.get("op") not in ORDERED_OPS:
            continue
        observed = _max_value_on_trace(ep, sum_path, rule)
        if observed is None or observed >= threshold:
            continue
        return {
            "clause_form": "aggregate",
            "clause_sum_path": sum_path,
            "clause_op": clause.get("op"),
            "clause_threshold": threshold,
            "rule_op": cond.get("op"),
            "rule_threshold": cond.get("value"),
            "max_single_call_value_on_trace": observed,
        }
    return None


def diagnose_noop(ep, rule, fires_alone, clause):
    """A NAMED cause, or `UNKNOWN`. Never a story."""
    agg = aggregate_mismatch(rule, clause, ep)
    if agg:
        return "AGGREGATE_CLAUSE_TESTED_PER_CALL", agg
    if fires_alone:
        return "SUBSUMED_BY_A_RULE_ALREADY_IN_FORCE", {}
    cls = (rule.get("match") or {}).get("capability_class")
    if cls not in _classes_on_trace(ep):
        return "CLASS_ABSENT_FROM_THIS_TRACE", {"capability_class": cls}
    return "CONDITION_NEVER_HELD_ON_THIS_TRACE", {"capability_class": cls}


# ---------------------------------------------------------------------------
# the measurement
# ---------------------------------------------------------------------------

def _promoting_rounds(bundle):
    return {g.get("round_index") for g in bundle.get("gate_decisions") or []
            if g.get("decision") == "PROMOTE"}


def measure_bundle(path, objective_set, clauses):
    path = pathlib.Path(path)
    bundle, accepted, defects = open_bundle(path)
    out = {
        "bundle": str(path),
        "run_id": (bundle.get("run_manifest") or {}).get("run_id"),
        "offline_reader_accepts": accepted,
        "reader_defects": defects,
        "rows": [],
        "refusal": None,
    }
    try:
        policies = build_policies(bundle)
    except PolicyReconstructionRefused as exc:
        out["refusal"] = str(exc)
        return out

    episodes = {}
    for e in bundle.get("episodes") or []:
        episodes[(e.get("attack_id"), e.get("round_index"))] = e
    autopsies = {a.get("autopsy_id"): a for a in bundle.get("autopsies") or []}
    chain_ids = {x["version"]: {r["rule_id"] for r in x.get("rules") or []}
                 for x in bundle.get("policy_chain") or []}
    by_id = {}
    for v, pol in policies.items():
        for r in pol["rules"]:
            by_id.setdefault(r["rule_id"], r)
    promoting = _promoting_rounds(bundle)

    for pp in bundle.get("patch_proposals") or []:
        if not pp.get("accepted"):
            continue
        rnd = pp.get("round_index")
        aut = autopsies.get(pp.get("autopsy_id")) or {}
        new_ids = [r.get("rule_id_assigned") for r in pp.get("rules") or []]
        row = {
            "proposal_id": pp.get("proposal_id"),
            "round_index": rnd,
            "autopsy_id": pp.get("autopsy_id"),
            "attack_id": aut.get("attack_id"),
            "verbs": list(pp.get("verbs") or ()),
            "promoted_rule_ids": new_ids,
            "verdict": None,
            "code": None,
        }

        if rnd not in promoting:
            row["verdict"], row["code"] = UNCLASSIFIED, "E_ROUND_DID_NOT_PROMOTE"
            out["rows"].append(row)
            continue
        ep = episodes.get((aut.get("attack_id"), rnd))
        if ep is None:
            row["verdict"], row["code"] = UNCLASSIFIED, "E_NO_EPISODE_FOR_AUTOPSY"
            out["rows"].append(row)
            continue
        prior_v = ep.get("policy_version")
        # THE VERSION MUST COME AFTER THE BREACH, AND `min(all versions holding
        # this rule)` IS NOT THAT. A rule promoted, retracted during a later
        # narrowing, and re-proposed carries an id that also appears EARLIER in
        # the chain; taking the first match dated the promotion before the
        # episode it answers. On batch-night run-45 that produced prior v2 ->
        # new v1, which is not a promotion, and the reader called it skew
        # rather than measuring backwards. Anchored to the episode's own
        # recorded `policy_version` instead.
        landed = [v for v in sorted(chain_ids)
                  if v > (prior_v if prior_v is not None else -1)
                  and set(new_ids) <= chain_ids[v]]
        if not new_ids or not landed:
            row["verdict"], row["code"] = UNCLASSIFIED, "E_RULE_NOT_IN_POLICY_CHAIN"
            out["rows"].append(row)
            continue
        new_v = landed[0]
        row["prior_policy_version"] = prior_v
        row["promoted_policy_version"] = new_v
        row["live_verdict"] = (ep.get("verdict") or {}).get("verdict")
        row["live_invariant_id"] = (ep.get("verdict") or {}).get("invariant_id")
        if prior_v not in policies:
            row["verdict"], row["code"] = UNCLASSIFIED, "E_PRIOR_VERSION_NOT_IN_CHAIN"
            out["rows"].append(row)
            continue
        if new_v != prior_v + 1:
            row["verdict"], row["code"] = UNCLASSIFIED, "E_VERSION_SKEW"
            out["rows"].append(row)
            continue

        before = replay_at(ep, policies[prior_v], objective_set)
        after = replay_at(ep, policies[new_v], objective_set)
        row["replay_prior_verdict"] = before["verdict"]
        row["replay_prior_invariant_id"] = before["invariant_id"]
        row["replay_promoted_verdict"] = after["verdict"]
        row["replay_promoted_invariant_id"] = after["invariant_id"]

        # THE REPLAY MUST REPRODUCE THE BREACH BEFORE IT MAY JUDGE THE FIX.
        # If the recorded trace, re-scored at the policy that was in force, is
        # not the breach the autopsy is about, then "did the patch close it" is
        # a question about something this reader never reproduced, and a no-op
        # answer would be uninterpretable rather than negative.
        if before["verdict"] != "BREACH":
            row["verdict"], row["code"] = UNCLASSIFIED, "E_PRIOR_REPLAY_NOT_A_BREACH"
            out["rows"].append(row)
            continue
        if row["live_invariant_id"] and before["invariant_id"] != row["live_invariant_id"]:
            row["verdict"], row["code"] = UNCLASSIFIED, "E_PRIOR_REPLAY_DIFFERENT_INVARIANT"
            out["rows"].append(row)
            continue

        newly_stopped, newly_permitted = [], []
        for seq, b4 in sorted(before["calls"].items(), key=lambda kv: (kv[0] is None, kv[0])):
            af = after["calls"].get(seq)
            if af is None:
                continue
            if b4["decision"] == ALLOW and af["decision"] != ALLOW:
                newly_stopped.append({"seq": seq, "decision": af["decision"],
                                      "stopped_by": af["rule_id"],
                                      "tool_handle": af["tool_handle"]})
            elif b4["decision"] != ALLOW and af["decision"] == ALLOW:
                newly_permitted.append({"seq": seq, "was": b4["decision"],
                                        "tool_handle": af["tool_handle"]})
        row["newly_stopped"] = newly_stopped
        row["newly_permitted"] = newly_permitted
        row["stopped_by_the_promoted_rule"] = sorted(
            {s["stopped_by"] for s in newly_stopped if s["stopped_by"] in new_ids})

        if newly_stopped:
            row["verdict"] = CLOSES
            row["invariant_still_reached"] = after["verdict"] == "BREACH"
        else:
            row["verdict"] = NO_OP
            row["invariant_still_reached"] = after["verdict"] == "BREACH"
            causes = []
            for rid in new_ids:
                rule = by_id.get(rid)
                if rule is None:
                    causes.append({"rule_id": rid, "cause": "E_RULE_BODY_UNAVAILABLE"})
                    continue
                fires, _ = rule_alone_fires(ep, rule, objective_set)
                clause = clauses.get(before["invariant_id"])
                cause, detail = diagnose_noop(ep, rule, fires, clause)
                causes.append({"rule_id": rid, "cause": cause, "detail": detail,
                               "fires_in_isolation": fires})
            row["noop_causes"] = causes
        out["rows"].append(row)

    # Breaches that produced an autopsy and never produced a promoted patch at
    # all. Not part of the CLOSES/NO_OP/UNCLASSIFIED denominator - there is no
    # promoted rule to judge - but a reader who is not told this exists will
    # read the denominator as "every breach".
    patched = {r["autopsy_id"] for r in out["rows"]}
    out["autopsies_with_no_accepted_patch"] = sorted(
        a for a in autopsies if a not in patched)
    out["autopsy_count"] = len(autopsies)
    return out


# ---------------------------------------------------------------------------
# the sibling question: what happened to the rules the gate REJECTED
# ---------------------------------------------------------------------------

def rejected_candidates(path, objective_set):
    """Every candidate the narrowing loop threw away, re-measured.

    `conductor.py` rejects a candidate when the benign floor OR the near-miss
    floor is short - `passed == total and near_miss_passed == near_miss_total`.
    The bundle's `warden_result` string records only the first of those two, so
    a candidate rejected on near-misses leaves a record that reads like a pass.
    This re-runs the REAL benign suite (`real_warden`) against prior-policy +
    the rejected rule and prints both floors, so the reason is visible rather
    than inferred.
    """
    bundle, accepted, _defects = open_bundle(path)
    policies = build_policies(bundle)
    episodes = {(e.get("attack_id"), e.get("round_index")): e
                for e in bundle.get("episodes") or []}
    autopsies = {a.get("autopsy_id"): a for a in bundle.get("autopsies") or []}
    rows = []
    for pp in bundle.get("patch_proposals") or []:
        if pp.get("accepted"):
            continue
        aut = autopsies.get(pp.get("autopsy_id")) or {}
        ep = episodes.get((aut.get("attack_id"), pp.get("round_index")))
        prior_v = ep.get("policy_version") if ep else None
        if prior_v not in policies:
            continue
        for r in pp.get("rules") or []:
            try:
                rule = executable_rule({"rule_id": r["rule_id_assigned"],
                                        "dsl_text": r["dsl_text"]})
            except PolicyReconstructionRefused as exc:
                rows.append({"proposal_id": pp.get("proposal_id"),
                             "rule_id": r.get("rule_id_assigned"),
                             "error": str(exc)})
                continue
            candidate = {"rules": sort_rules(policies[prior_v]["rules"] + [rule])}
            report = real_warden(candidate)
            closed = None
            if ep is not None:
                before = replay_at(ep, policies[prior_v], objective_set)
                after = replay_at(ep, candidate, objective_set)
                closed = any(
                    before["calls"][s]["decision"] == ALLOW
                    and after["calls"].get(s, {}).get("decision", ALLOW) != ALLOW
                    for s in before["calls"])
            rows.append({
                "proposal_id": pp.get("proposal_id"),
                "round_index": pp.get("round_index"),
                "rule_id": r.get("rule_id_assigned"),
                "dsl_text": r.get("dsl_text"),
                "benign": "%s/%s" % (report["passed"], report["total"]),
                "near_miss": "%s/%s" % (report["near_miss_passed"],
                                        report["near_miss_total"]),
                "approval_masked": report["benign_passes_requiring_approval"],
                "would_have_closed_the_trace": closed,
            })
    return {"bundle": str(path), "offline_reader_accepts": accepted, "rows": rows}


# ---------------------------------------------------------------------------
# selftest - a reader that returns the same answer regardless of input is not
# measuring anything, so this proves the reader can fail in both directions
# ---------------------------------------------------------------------------

def _rule_entry(dsl_body):
    """Build a `policy_chain` rule entry whose id is the id its bytes earn.

    The id inside the text is not what the id is computed from - `rule_body`
    strips it - so a placeholder is written, the true id computed, and the text
    rewritten with it. Exactly what the validator does to the ARMORER's
    `r_new1` (CONVENTIONS 2.6).
    """
    text = "rule r_new1: %s origin armorer:9" % dsl_body
    parsed = parse_rule(text)
    rid = assign_rule_id(rule_body(parsed))
    return {"rule_id": rid, "verb": parsed.action.verb,
            "dsl_text": "rule %s: %s origin armorer" % (rid, dsl_body),
            "origin": "armorer"}


def _promoted_class(bundle, proposal_id):
    """The capability class the ARMORER actually bound this promotion to.

    Read out of the bundle, never defaulted. A hardcoded fallback here would
    make the flip-to-CLOSES check pass on a bundle where it should not, which
    is a selftest that cannot fail wearing a selftest's clothes.
    """
    pp = next(p for p in bundle["patch_proposals"] if p["proposal_id"] == proposal_id)
    rid = pp["rules"][0]["rule_id_assigned"]
    for chain in bundle["policy_chain"]:
        for r in chain["rules"]:
            if r["rule_id"] == rid and r.get("capability_class"):
                return r["capability_class"]
    raise SystemExit(
        "E_SELFTEST_CANNOT_RUN: %s promotes %s and no policy_chain entry records "
        "its capability class, so the flip-to-CLOSES check has nothing to bind a "
        "deny to." % (proposal_id, rid))


def _swap_promoted_rule(bundle, proposal_id, dsl_body):
    """Replace the rule one accepted proposal promoted, everywhere it appears."""
    b = copy.deepcopy(bundle)
    pp = next(p for p in b["patch_proposals"] if p["proposal_id"] == proposal_id)
    old_id = pp["rules"][0]["rule_id_assigned"]
    entry = _rule_entry(dsl_body)
    pp["rules"][0] = {"rule_id_assigned": entry["rule_id"],
                      "dsl_text": entry["dsl_text"],
                      "rule_id_as_proposed": "r_new1"}
    for chain in b["policy_chain"]:
        chain["rules"] = [entry if r["rule_id"] == old_id else r
                          for r in chain["rules"]]
    return b


def selftest(path, objective_set, clauses):
    """Four checks. Each names a change the reader MUST notice."""
    raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    results = []

    def check(name, ok, detail):
        results.append((name, bool(ok), detail))

    def verdicts(bundle):
        tmp = pathlib.Path(path).with_suffix(".selftest.tmp.json")
        tmp.write_bytes(json.dumps(bundle).encode("utf-8"))
        try:
            m = measure_bundle(tmp, objective_set, clauses)
        finally:
            tmp.unlink(missing_ok=True)
        return m, {r["proposal_id"]: (r["verdict"], r.get("code")) for r in m["rows"]}

    base, base_v = verdicts(raw)
    check("the unmodified bundle yields at least one verdict",
          bool(base_v), json.dumps(base_v))

    noops = [p for p, (v, _c) in base_v.items() if v == NO_OP]
    closes = [p for p, (v, _c) in base_v.items() if v == CLOSES]
    check("the unmodified bundle produces BOTH verdicts, so neither is the "
          "reader's only answer",
          bool(noops) and bool(closes),
          "NO_OP=%s CLOSES=%s" % (noops, closes))

    # 1. A rule that plainly DOES close: an unconditional deny on the class the
    #    breaching calls carry. If the reader still says NO_OP it is not reading
    #    the policy at all.
    if noops:
        target = noops[0]
        cls = _promoted_class(raw, target)
        doctored = _swap_promoted_rule(raw, target,
                                       "cap:%s => deny" % cls)
        _m, v = verdicts(doctored)
        check("a NO_OP flips to CLOSES when the promoted rule is replaced by one "
              "that plainly stops the trace",
              v.get(target, (None, None))[0] == CLOSES,
              "%s -> %s" % (target, v.get(target)))

    # 2. A rule that plainly does NOT close: bound to a capability class no
    #    recorded call carries. If the reader still says CLOSES it is not
    #    comparing anything.
    if closes:
        target = closes[0]
        doctored = _swap_promoted_rule(
            raw, target, "cap:CAP_INVOKES_AGENT => deny")
        _m, v = verdicts(doctored)
        check("a CLOSES flips to NO_OP when the promoted rule is replaced by one "
              "bound to a class the trace never carries",
              v.get(target, (None, None))[0] == NO_OP,
              "%s -> %s" % (target, v.get(target)))

    # 3. The trace disappears. The reader must refuse to classify, not default.
    if closes:
        target = closes[0]
        aut = next(r["autopsy_id"] for r in base["rows"]
                   if r["proposal_id"] == target)
        atk = next(a["attack_id"] for a in raw["autopsies"]
                   if a["autopsy_id"] == aut)
        rnd = next(r["round_index"] for r in base["rows"]
                   if r["proposal_id"] == target)
        doctored = copy.deepcopy(raw)
        doctored["episodes"] = [e for e in doctored["episodes"]
                                if not (e.get("attack_id") == atk
                                        and e.get("round_index") == rnd)]
        _m, v = verdicts(doctored)
        check("with the breaching episode removed the reader UNCLASSIFIES rather "
              "than defaulting to a verdict",
              v.get(target) == (UNCLASSIFIED, "E_NO_EPISODE_FOR_AUTOPSY"),
              "%s -> %s" % (target, v.get(target)))

    # 4. The reconstruction guard. Corrupt one rule's text so it no longer
    #    hashes to the id beside it; the reader must refuse the whole bundle.
    doctored = copy.deepcopy(raw)
    for chain in doctored["policy_chain"]:
        for r in chain["rules"]:
            r["dsl_text"] = r["dsl_text"].replace("=> deny", "=> require_approval(X)")
    m, _v = verdicts(doctored)
    check("a rule whose DSL text no longer hashes to its recorded id makes the "
          "reader REFUSE the bundle rather than measure a different rule",
          (m.get("refusal") or "").startswith("E_POLICY_RECONSTRUCTION"),
          (m.get("refusal") or "no refusal")[:120])

    print("SELFTEST")
    bad = 0
    for name, ok, detail in results:
        print("  %-4s %s" % ("PASS" if ok else "FAIL", name))
        print("        %s" % detail)
        if not ok:
            bad += 1
    print("  %d check(s), %d failed" % (len(results), bad))
    return 0 if bad == 0 else 1


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------

METHOD_LIMIT = (
    "METHOD LIMIT, STATED ON THE ARTIFACT AND NOT ONLY IN THE README. This is a "
    "REPLAY of recorded calls, not a re-attack. It answers WOULD THIS POLICY HAVE "
    "DENIED THESE EXACT CALLS. It does NOT answer COULD THE AGENT HAVE FOUND "
    "ANOTHER PATH - a live agent handed a refusal it never received before may go "
    "somewhere else entirely, and nothing here can see that. Describing this as "
    "susceptibility testing is overclaiming.")


def print_report(measurements):
    for m in measurements:
        print("=" * 78)
        print("bundle : %s" % m["bundle"])
        print("run_id : %s" % m["run_id"])
        print("reader : %s" % ("ACCEPTS" if m["offline_reader_accepts"]
                               else "REFUSES - %s" % ", ".join(
                                   d["code"] for d in m["reader_defects"])))
        if m["refusal"]:
            print("REFUSED: %s" % m["refusal"])
            continue
        print("autopsies %d, of which %d produced no accepted patch"
              % (m["autopsy_count"], len(m["autopsies_with_no_accepted_patch"])))
        for r in m["rows"]:
            print("  %-38s round %-2s %-13s %s"
                  % (r["proposal_id"], r["round_index"], r["verdict"],
                     r.get("code") or ""))
            print("      rules %s  v%s -> v%s  invariant %s"
                  % (r["promoted_rule_ids"], r.get("prior_policy_version"),
                     r.get("promoted_policy_version"),
                     r.get("replay_prior_invariant_id")))
            if r["verdict"] == CLOSES:
                print("      newly stopped: %s" % json.dumps(r["newly_stopped"]))
                print("      invariant still reached at the promoted policy: %s"
                      % r["invariant_still_reached"])
            if r["verdict"] == NO_OP:
                for c in r.get("noop_causes") or []:
                    print("      %s  %s  %s"
                          % (c["rule_id"], c["cause"], json.dumps(c.get("detail") or {})))
            if r.get("newly_permitted"):
                print("      NEWLY PERMITTED (the promotion also softened "
                      "something): %s" % json.dumps(r["newly_permitted"]))


def totals(measurements):
    acc = {True: {}, False: {}}
    for m in measurements:
        pop = acc[bool(m["offline_reader_accepts"])]
        pop.setdefault("bundles", 0)
        pop["bundles"] += 1
        if m["refusal"]:
            pop["refused_bundles"] = pop.get("refused_bundles", 0) + 1
            continue
        for r in m["rows"]:
            pop[r["verdict"]] = pop.get(r["verdict"], 0) + 1
            if r["verdict"] == UNCLASSIFIED:
                pop.setdefault("codes", {})
                pop["codes"][r["code"]] = pop["codes"].get(r["code"], 0) + 1
            if r["verdict"] == NO_OP:
                for c in r.get("noop_causes") or []:
                    pop.setdefault("noop_causes", {})
                    pop["noop_causes"][c["cause"]] = \
                        pop["noop_causes"].get(c["cause"], 0) + 1
            if r["verdict"] == CLOSES and r.get("invariant_still_reached"):
                pop["closes_but_invariant_still_reached"] = \
                    pop.get("closes_but_invariant_still_reached", 0) + 1
        pop["autopsies"] = pop.get("autopsies", 0) + m["autopsy_count"]
        pop["autopsies_with_no_accepted_patch"] = (
            pop.get("autopsies_with_no_accepted_patch", 0)
            + len(m["autopsies_with_no_accepted_patch"]))
    return acc


def print_totals(acc):
    print("=" * 78)
    print("TOTALS. TWO POPULATIONS, NEVER POOLED.")
    for accepted, label in ((True, "bundles the OFFLINE READER ACCEPTS"),
                            (False, "bundles the OFFLINE READER REFUSES - "
                                    "read with json.load, separate population")):
        pop = acc[accepted]
        if not pop:
            continue
        print("\n  %s" % label)
        n = pop.get(CLOSES, 0) + pop.get(NO_OP, 0) + pop.get(UNCLASSIFIED, 0)
        print("    bundles                 %d" % pop.get("bundles", 0))
        print("    promoted patches judged %d" % n)
        print("      CLOSES                %d" % pop.get(CLOSES, 0))
        print("        of which the invariant is STILL reached  %d"
              % pop.get("closes_but_invariant_still_reached", 0))
        print("      NO_OP                 %d" % pop.get(NO_OP, 0))
        for cause, k in sorted((pop.get("noop_causes") or {}).items()):
            print("        %-42s %d" % (cause, k))
        print("      UNCLASSIFIED          %d" % pop.get(UNCLASSIFIED, 0))
        for code, k in sorted((pop.get("codes") or {}).items()):
            print("        %-42s %d" % (code, k))
        print("    autopsies                              %d" % pop.get("autopsies", 0))
        print("      with no accepted patch at all        %d"
              % pop.get("autopsies_with_no_accepted_patch", 0))
    print()
    print(METHOD_LIMIT)


def collect(target):
    target = pathlib.Path(target)
    if target.is_dir():
        return sorted(target.glob("*.c6.json"))
    return [target]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", help="a .c6.json evidence bundle, or a directory of them")
    ap.add_argument("--json", help="write the full per-row measurement here")
    ap.add_argument("--rejected", action="store_true",
                    help="also re-measure the candidates the narrowing loop threw "
                         "away, with both benign floors")
    ap.add_argument("--selftest", action="store_true",
                    help="prove this reader can fail, in both directions")
    args = ap.parse_args(argv)

    objective_set = load_objective_set(OBJECTIVE_SET)
    clauses = {c["id"]: c for c in
               json.loads(OBJECTIVE_SET.read_text(encoding="utf-8"))["clauses"]}

    if args.selftest:
        return selftest(args.path, objective_set, clauses)

    paths = collect(args.path)
    if not paths:
        raise SystemExit("E_NO_BUNDLES: %s matched no *.c6.json" % args.path)
    measurements = [measure_bundle(p, objective_set, clauses) for p in paths]
    print_report(measurements)
    # RULING 60 PART 3. This script already splits ACCEPTS from REFUSES by
    # verifying each bundle live, which is the stronger instrument. The banner
    # adds the population that split cannot see - a bundle with no reader
    # verdict on disk at all - and states the count in one sentence above the
    # totals rather than only per row. A figure printed without its acceptance
    # count is the failure mode returning.
    _verdict.print_batch_banner(paths, "bundle")
    print_totals(totals(measurements))

    if args.rejected:
        print("=" * 78)
        print("CANDIDATES THE NARROWING LOOP REJECTED, RE-MEASURED")
        for p in paths:
            rej = rejected_candidates(p, objective_set)
            for row in rej["rows"]:
                print("  %s" % json.dumps(row))

    if args.json:
        out = pathlib.Path(args.json)
        out.write_bytes(json.dumps(
            {"measurements": measurements, "method_limit": METHOD_LIMIT},
            indent=1).encode("utf-8"))
        print("\nwrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
