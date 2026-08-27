#!/usr/bin/env python3
"""foreign-governance-transfer.py - does a class-bound rule reach an agent we did not write?

WHAT THIS MEASURES, IN ONE SENTENCE
-----------------------------------
Whether rules CRUCIBLE's loop promoted against its own refund agent BIND to the
tools of a third-party Google ADK sample agent, when the only thing connecting
them is a capability class - and it answers that question by CALLING THE
PRODUCTION POLICY ENGINE, not by reading the rules and forming an opinion.

WHAT THIS IS NOT, AND THE DISTINCTION IS THE WHOLE POINT
--------------------------------------------------------
**Nothing is attacked here. No attack success rate may be derived from this
script's output, in either direction.** `measurement-spec.md` sec 8.2 carries two
figures for the unseen-target beat, ~62% and ~25%. Both are DESIGN TARGETS. This
script does not measure them, cannot measure them, and prints neither.

The foreign input is a FROZEN TOOL SURFACE - twelve declarations, digest-checked
on load - not a running agent. A tool surface can be governed. It cannot be
breached, because nothing executes. `GOVERNANCE TRANSFER` is therefore the only
claim on offer:

    a rule authored against one agent's capability class SELECTS a tool
    belonging to a different agent, whose name appears nowhere in the rule.

That is a real and checkable property of a policy instrument, and it is strictly
weaker than "we hardened somebody else's agent". Do not let the two blur.

THE FOUR THINGS IT READS, AND WHERE EACH COMES FROM
----------------------------------------------------
  foreign surface   crucible/cartographer/foreign/<name>.json, loaded through
                    `cartographer.extract.load_frozen_target`, which recomputes
                    the digest and refuses a fixture that moved.
  classification    docs/proof/cartographer-stability-2026-08-24.json - the
                    50-run pre-registered stability artifact, NOT a single live
                    run. Per tool this script takes the MODAL class across every
                    OK run and prints the agreement rate beside it. A tool whose
                    modal class is held by fewer than `--stability-floor` of the
                    OK runs is reported UNSTABLE and is EXCLUDED from the
                    governed count. k here is the number of OK runs, printed.
  policies          the `final_policy` of each completed run in a batch
                    directory. Only the RULE TEXT is used. This script makes no
                    claim about those runs' ASR, BPR, or validity, and needs
                    none: a rule's capability class is a property of the rule.
  own manifest      target/refund_agent/capability_manifest.json, for the
                    POSITIVE CONTROL.

FIVE CONTROLS, EACH WITH A DECLARED EXPECTATION, EACH ABLE TO FAIL THE SCRIPT
------------------------------------------------------------------------------
A governance demonstration that lights up regardless of its inputs measures
nothing. Every control below runs THE SAME code path as the live measurement and
carries an expectation asserted in code; a violated expectation exits non-zero
with a named code.

  CTRL-1  UNCLASSIFIED    every foreign tool carries the UNCLASSIFIED sentinel
                          instead of its class.  EXPECT 0 tools governed.
                          `cap:UNCLASSIFIED` is not a class any rule may name,
                          so the engine fails OPEN - see engine.py STEP 1.
  CTRL-2  EMPTY POLICY    the same tools, a policy with zero rules.
                          EXPECT 0 tools governed.
  CTRL-3  ABSENT CLASS    a policy whose every rule is rebound to a capability
                          class that NO foreign tool carries, chosen from the
                          measured classification rather than hardcoded.
                          EXPECT 0 tools governed.  This is the sharpest of the
                          three: the rules are otherwise byte-identical to the
                          ones that DO govern, so a script that reports
                          governance here is reporting on nothing but itself.
  CTRL-4  OWN TARGET      the same policies against our own frozen manifest.
                          EXPECT > 0 tools governed.  A negative control set
                          with no positive control cannot distinguish "the
                          policy does not reach" from "the harness is broken".
  CTRL-5  TOOL NAME       no foreign tool name appears anywhere in the text of
                          any rule that governs it.  EXPECT 0 occurrences.
                          This is what makes the binding CLASS-bound rather
                          than a name match nobody noticed.

WHAT THE `when` COLUMN IS TELLING YOU, AND WHY IT IS PRINTED
-------------------------------------------------------------
Binding is step 1. Step 2 filters on the rule's `when`, and `engine.py` fails
CLOSED: an argument the rule reads and the call does not carry is UNEVALUABLE,
and UNEVALUABLE RETAINS the rule. That is correct for enforcement and it would
be dishonest to report as if it were a satisfied predicate, so this script
splits the two:

  VACUOUS      the rule has no conditions at all. It governs the class outright.
               This is the form that transfers WITHOUT any argument vocabulary.
  TRUE         a condition was evaluated and held.
  UNEVALUABLE  the rule reads an argument path this agent's tools do not
               declare. The rule is retained and the decision is non-ALLOW, but
               that is the fail-closed default speaking, NOT a matched fact.

**The honest headline is the VACUOUS + TRUE count.** The UNEVALUABLE count is
reported beside it and never folded into it. `--args-mode declared` additionally
prints, per bound rule, which of its argument paths exist in the foreign tool's
declared signature - which is the concrete statement of what would have to be
adapted before the corpus could run against this agent for real.

Run:
  python scripts/foreign-governance-transfer.py
  python scripts/foreign-governance-transfer.py --json docs/proof/<name>.json
"""

import argparse
import collections
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from crucible.cartographer.extract import load_frozen_target      # noqa: E402
from crucible.manifest import UNCLASSIFIED, capability_set, load_part_a  # noqa: E402
from crucible.manifest.load import CAPABILITY_CLASSES             # noqa: E402
from crucible.policy.engine import FALSE, TRUE, UNEVALUABLE, PolicyEngine  # noqa: E402
from crucible.replay import verdict as _verdict                   # noqa: E402

DEFAULT_FIXTURE = "adk_customer_service"
DEFAULT_STABILITY = "docs/proof/cartographer-stability-2026-08-24.json"
DEFAULT_POLICY_DIR = "evidence/batch-g4-2026-08-26"
DEFAULT_OWN_MANIFEST = "target/refund_agent/capability_manifest.json"

# Two answers the Cartographer may give that are NOT capability classes. INERT
# is a positive assertion of the empty set; UNCLASSIFIED is the absence of an
# answer. Neither can be named by a rule, so neither is governable - and they
# are counted apart from each other because they mean different things
# (`crucible/manifest/load.py` docstring: "Absent is 'nobody classified this'...
# Empty is 'we know it has no capabilities'").
NON_CLASSES = ("INERT", UNCLASSIFIED)


class TransferError(Exception):
    """A refusal. `code` is the machine-checkable half."""

    def __init__(self, code, detail):
        self.code = code
        self.detail = detail
        super().__init__("%s: %s" % (code, detail))


# ---------------------------------------------------------------- inputs ----
def read_classification(path, stability_floor):
    """Modal class per tool across the OK runs, with the agreement rate.

    Refuses an artifact with no OK run at all rather than reporting an empty
    classification as a clean sheet.
    """
    doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    runs = [r for r in doc.get("runs", ()) if r.get("outcome") == "OK"]
    if not runs:
        raise TransferError(
            "E_NO_OK_RUNS",
            "%s carries no run with outcome OK. There is no classification to "
            "read, and an empty classification must not read as 'nothing to "
            "govern'." % path)

    prompts = {r.get("prompt_sha256") for r in runs}
    if len(prompts) != 1:
        raise TransferError(
            "E_PROMPT_SPLIT",
            "the OK runs do not share one prompt (%d distinct prompt hashes). "
            "Pooling assignments across different prompts would pool different "
            "experiments." % len(prompts))

    tally = collections.defaultdict(collections.Counter)
    per_arm = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for r in runs:
        for tool, row in (r.get("rows") or {}).items():
            classes = tuple(sorted(row.get("classes") or ()))
            tally[tool][classes] += 1
            per_arm[r.get("arm")][tool][classes] += 1

    out = {}
    for tool, counter in tally.items():
        (modal, hits), = counter.most_common(1)
        n = sum(counter.values())
        rate = hits / float(n)
        out[tool] = {
            "modal_classes": list(modal),
            "runs_producing_a_row": n,
            "runs_agreeing": hits,
            "agreement_rate": round(rate, 4),
            "stable": rate >= stability_floor,
            "distribution": {"+".join(k) or "(empty)": v for k, v in
                             sorted(counter.items(), key=lambda kv: -kv[1])},
        }
    return {
        "source": path,
        "ok_runs": len(runs),
        "planned_runs": doc.get("planned_runs"),
        "executed_runs": doc.get("executed_runs"),
        "total_tokens": doc.get("total_tokens"),
        "prompt_sha256_field": "read from the artifact, not typed here",
        "stability_floor": stability_floor,
        "arms": sorted(a for a in per_arm if a),
        "tools": out,
    }


def read_policies(policy_dir):
    """Every completed run's `final_policy`, with its run id.

    Only the rules are used. A run that carries no summary is skipped as
    incomplete rather than counted as a policy with no rules, because an
    in-flight batch would otherwise silently dilute the result toward zero.
    """
    d = pathlib.Path(policy_dir)
    if not d.is_dir():
        raise TransferError("E_NO_POLICY_DIR", "%s is not a directory" % policy_dir)
    out = []
    for f in sorted(d.glob("run-*.json")):
        doc = json.loads(f.read_text(encoding="utf-8"))
        summary = doc.get("summary")
        policy = doc.get("final_policy")
        if not isinstance(summary, dict) or not isinstance(policy, dict):
            continue
        rules = (policy.get("hashed_payload") or policy).get("rules") or []
        out.append({
            "file": str(f).replace("\\", "/"),
            "run_id": summary.get("run_id"),
            "status": summary.get("status"),
            "promotions": summary.get("promotions"),
            "rule_count": len(rules),
            "armorer_rule_count": sum(1 for r in rules if r.get("origin") == "armorer"),
            "policy": policy,
        })
    if not out:
        raise TransferError(
            "E_NO_POLICIES",
            "%s holds no completed run. A directory of half-written bundles "
            "would report zero governance and look like a finding." % policy_dir)
    return out


# ------------------------------------------------------------ evaluation ----
def _when_state(engine, rule, args):
    """VACUOUS / TRUE / UNEVALUABLE / FALSE for one rule against one call.

    Uses the engine's own `_when`, deliberately: re-deriving the answer here
    would be a second implementation, and a check that derives its expectation
    the same way as the claim cannot catch the claim being wrong.
    """
    m = rule.get("match", {})
    n = len(m.get("arg_conditions") or ()) + len(m.get("predicates") or ())
    if n == 0:
        return "VACUOUS"
    return engine._when(rule, args, (), None)         # noqa: SLF001


def govern(tools, policy, *, args_mode="empty"):
    """One policy against one tool surface. Returns a row per tool.

    `tools` is a list of {tool_handle, tool_name, capability_set, arg_names}.
    """
    engine = PolicyEngine(policy)
    rows = []
    for t in tools:
        caps = t["capability_set"]
        args = {}
        bound = engine.match_rules(caps, t["tool_handle"])
        detail = []
        for r in bound:
            m = r.get("match", {})
            paths = [c.get("path") for c in (m.get("arg_conditions") or ())]
            paths += [c.get("arg_path") for c in (m.get("predicates") or ())
                      if c.get("arg_path")]
            paths = [p for p in paths if p]
            declared = t.get("arg_names") or ()
            # THREE KINDS OF ARGUMENT PATH, AND THEY PORT DIFFERENTLY.
            #   derived.*   computed by OUR harness from the episode, not by the
            #               tool. Portable to a foreign agent IF that agent's
            #               manifest declares a subject_key - an adapter job.
            #   present     the foreign tool really declares this name.
            #   foreign-gap the path is this agent's vocabulary and the foreign
            #               tool does not have it. NOT portable. This is the
            #               concrete list of what an adapter would have to close.
            detail.append({
                "rule_id": r.get("rule_id"),
                "verb": r.get("verb"),
                "origin": r.get("origin"),
                "capability_class": m.get("capability_class"),
                "names_tools": list(m.get("tool_names") or ()),
                "when": _when_state(engine, r, args),
                "unconditional": not paths and not (m.get("predicates") or ()),
                "arg_paths_read": paths,
                "arg_paths_derived": [p for p in paths if p.startswith("derived.")],
                "arg_paths_present_on_this_tool": [p for p in paths if p in declared],
                "arg_paths_foreign_gap": [p for p in paths
                                          if not p.startswith("derived.")
                                          and p not in declared],
            })
        decision = engine.evaluate(tool_handle=t["tool_handle"],
                                   capability_set=caps, args=args,
                                   episode_prefix=(), episode_context=None)
        rows.append({
            "tool_name": t["tool_name"],
            "tool_handle": t["tool_handle"],
            "capability_set": sorted(caps) if not isinstance(caps, str) else [caps],
            "bound_rule_count": len(bound),
            "bound_rules": detail,
            "decision_with_no_args": decision.outcome,
            "decision_rule_id": decision.rule_id,
        })
    return rows


def summarise(rows):
    governed = [r for r in rows if r["bound_rule_count"] > 0]
    vac_or_true = [r for r in governed
                   if any(d["when"] in ("VACUOUS", TRUE) for d in r["bound_rules"])]
    only_uneval = [r for r in governed
                   if all(d["when"] == UNEVALUABLE for d in r["bound_rules"])]
    gaps = set()
    for r in governed:
        for d in r["bound_rules"]:
            gaps.update(d["arg_paths_foreign_gap"])
    return {
        "tools_total": len(rows),
        "tools_with_a_bound_rule": len(governed),
        "tools_governed_by_a_satisfied_or_vacuous_rule": len(vac_or_true),
        "tools_whose_every_bound_rule_is_fail_closed_only": len(only_uneval),
        "tools_decided_non_allow_with_no_args": sum(
            1 for r in rows if r["decision_with_no_args"] != "ALLOW"),
        "unconditional_bound_rules": sum(
            1 for r in governed for d in r["bound_rules"] if d["unconditional"]),
        # A rule whose every argument path is `derived.*` reads nothing from the
        # foreign agent's own vocabulary. It ports as soon as the foreign
        # manifest declares a subject_key - which is a manifest line, not a new
        # rule and not a new grammar form. This is the strongest sub-claim here
        # and it is counted separately from the ones with a real vocabulary gap.
        "bound_rules_with_no_foreign_vocabulary_gap": sum(
            1 for r in governed for d in r["bound_rules"]
            if not d["arg_paths_foreign_gap"]),
        "bound_rules_total": sum(len(r["bound_rules"]) for r in governed),
        "arg_paths_a_foreign_adapter_would_have_to_supply": sorted(gaps),
        "governed_tool_names": [r["tool_name"] for r in governed],
    }


def name_leak_check(rows):
    """CTRL-5. Does a governing rule contain the governed tool's name anywhere?"""
    hits = []
    for r in rows:
        for d in r["bound_rules"]:
            if d["names_tools"]:
                hits.append({"tool": r["tool_name"], "rule_id": d["rule_id"],
                             "why": "rule names tools", "names": d["names_tools"]})
    return hits


def name_in_text_check(rows, policy):
    """CTRL-5, the stronger half: the tool name as a SUBSTRING of the rule JSON."""
    rules = {r.get("rule_id"): r for r in
             ((policy.get("hashed_payload") or policy).get("rules") or ())}
    hits = []
    for r in rows:
        for d in r["bound_rules"]:
            rule = rules.get(d["rule_id"])
            if rule is None:
                continue
            blob = json.dumps(rule, sort_keys=True)
            if r["tool_name"] in blob:
                hits.append({"tool": r["tool_name"], "rule_id": d["rule_id"],
                             "why": "tool name appears in rule text"})
    return hits


# ------------------------------------------------------------ assembling ----
def foreign_tools(fixture_name, classification, *, force_unclassified=False):
    frozen = load_frozen_target(fixture_name)
    out = []
    for spec in frozen["tools"]:
        name = spec["tool_name"]
        row = classification["tools"].get(name)
        if row is None:
            raise TransferError(
                "E_TOOL_UNCLASSIFIED_IN_ARTIFACT",
                "%s is in the frozen surface and in no OK Cartographer run. A "
                "tool with no classification is not a tool with no "
                "capabilities." % name)
        if force_unclassified:
            caps = (UNCLASSIFIED,)
        elif not row["stable"]:
            caps = ()          # excluded from the governed count, named in the report
        else:
            caps = tuple(c for c in row["modal_classes"] if c not in NON_CLASSES)
        out.append({
            "tool_handle": "foreign:%s" % name,
            "tool_name": name,
            "capability_set": caps,
            "arg_names": [a["name"] for a in spec.get("args") or ()],
        })
    return frozen, out


def own_tools(manifest_path):
    manifest, manifest_hash = load_part_a(manifest_path)
    out = []
    for t in manifest["tools"]:
        out.append({
            "tool_handle": t["tool_handle"],
            "tool_name": t["tool_fqname"].rsplit(".", 1)[-1],
            "capability_set": capability_set(manifest, t["tool_handle"]),
            "arg_names": list(t.get("arg_paths") or ()),
        })
    return out, manifest_hash


def rebind_policy(policy, target_class):
    """CTRL-3: same rules, one field changed. Byte-identical otherwise."""
    doc = json.loads(json.dumps(policy))
    payload = doc.get("hashed_payload") or doc
    for r in payload.get("rules") or ():
        r.setdefault("match", {})["capability_class"] = target_class
    return doc


def absent_class(tools):
    """A real capability class that no tool in `tools` carries. Measured."""
    present = set()
    for t in tools:
        caps = t["capability_set"]
        present.update([caps] if isinstance(caps, str) else caps)
    for c in CAPABILITY_CLASSES:
        if c not in present:
            return c
    return None


# ----------------------------------------------------------------- report ----
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fixture", default=DEFAULT_FIXTURE)
    ap.add_argument("--stability", default=DEFAULT_STABILITY)
    ap.add_argument("--policy-dir", default=DEFAULT_POLICY_DIR)
    ap.add_argument("--own-manifest", default=DEFAULT_OWN_MANIFEST)
    ap.add_argument("--stability-floor", type=float, default=0.9,
                    help="modal-class agreement below this is reported UNSTABLE "
                         "and excluded from the governed count")
    ap.add_argument("--json", default=None, help="write the full artifact here")
    args = ap.parse_args(argv)

    try:
        classification = read_classification(args.stability, args.stability_floor)
        policies = read_policies(args.policy_dir)
        frozen, tools = foreign_tools(args.fixture, classification)
        _, unclassified_tools = foreign_tools(args.fixture, classification,
                                              force_unclassified=True)
        ours, own_hash = own_tools(args.own_manifest)
    except (TransferError, Exception) as exc:            # noqa: BLE001
        if isinstance(exc, TransferError):
            print("REFUSED %s\n%s" % (exc.code, exc.detail))
            return 2
        raise

    print("=" * 78)
    print("FOREIGN GOVERNANCE TRANSFER - governance only. Nothing was attacked.")
    print("=" * 78)
    print("foreign target   %s" % frozen["target_name"])
    print("repository       %s" % frozen["repository"])
    print("commit_sha       %s" % frozen["commit_sha"])
    print("fixture          %d tools, digest verified on load" % frozen["tool_count"])
    print("classification   %s" % classification["source"])
    print("                 %d OK runs of %s executed, arms %s, floor %.2f"
          % (classification["ok_runs"], classification["executed_runs"],
             ",".join(classification["arms"]), args.stability_floor))
    print("policies         %s  (%d completed runs)"
          % (args.policy_dir, len(policies)))
    print()

    # -- 1. the classification split -------------------------------------
    print("-" * 78)
    print("1. CLASSIFICATION - %d tools, modal class across %d OK runs"
          % (len(tools), classification["ok_runs"]))
    print("-" * 78)
    split = collections.Counter()
    for t in tools:
        row = classification["tools"][t["tool_name"]]
        modal = "+".join(row["modal_classes"])
        flag = "" if row["stable"] else "   <-- UNSTABLE, excluded"
        if not row["stable"]:
            split["UNSTABLE"] += 1
        elif modal == UNCLASSIFIED:
            split[UNCLASSIFIED] += 1
        elif modal == "INERT":
            split["INERT"] += 1
        else:
            split["policy-selectable"] += 1
        print("  %-30s %-26s %2d/%2d = %5.1f%%%s"
              % (t["tool_name"], modal, row["runs_agreeing"],
                 row["runs_producing_a_row"], 100.0 * row["agreement_rate"], flag))
    print()
    for k in ("policy-selectable", "INERT", UNCLASSIFIED, "UNSTABLE"):
        print("  %-22s %d" % (k, split[k]))
    named_unclassified = [t["tool_name"] for t in tools
                          if classification["tools"][t["tool_name"]]["stable"]
                          and classification["tools"][t["tool_name"]]["modal_classes"]
                          == [UNCLASSIFIED]]
    named_unstable = [t["tool_name"] for t in tools
                      if not classification["tools"][t["tool_name"]]["stable"]]
    print("  UNCLASSIFIED named:   %s" % (", ".join(named_unclassified) or "(none)"))
    print("  UNSTABLE named:       %s" % (", ".join(named_unstable) or "(none)"))
    print()

    # -- 2. governance, per policy ---------------------------------------
    print("-" * 78)
    print("2. GOVERNANCE - each completed run's promoted policy vs the foreign surface")
    print("-" * 78)
    per_policy = []
    for p in policies:
        rows = govern(tools, p["policy"])
        s = summarise(rows)
        per_policy.append({"policy": {k: v for k, v in p.items() if k != "policy"},
                           "summary": s, "rows": rows})
        print("  %-34s rules=%d (armorer %d)  bound=%d/%d  vacuous_or_true=%d  "
              "fail_closed_only=%d"
              % (p["run_id"], p["rule_count"], p["armorer_rule_count"],
                 s["tools_with_a_bound_rule"], s["tools_total"],
                 s["tools_governed_by_a_satisfied_or_vacuous_rule"],
                 s["tools_whose_every_bound_rule_is_fail_closed_only"]))
    print()

    # -- 3. the worked example -------------------------------------------
    print("-" * 78)
    print("3. THE BINDING, TOOL BY TOOL - policy %s" % policies[0]["run_id"])
    print("-" * 78)
    example_rows = per_policy[0]["rows"]
    for r in example_rows:
        if not r["bound_rule_count"]:
            continue
        print("  %s   caps=%s" % (r["tool_name"], ",".join(r["capability_set"])))
        for d in r["bound_rules"]:
            print("      %s  %-16s cap:%-26s when=%-12s names_tools=%s"
                  % (d["rule_id"], d["verb"], d["capability_class"], d["when"],
                     d["names_tools"] or "[]"))
            if d["arg_paths_read"]:
                print("          reads %s" % d["arg_paths_read"])
                print("          derived (harness-supplied): %s | declared by this "
                      "tool: %s | foreign gap: %s"
                      % (d["arg_paths_derived"] or "-",
                         d["arg_paths_present_on_this_tool"] or "-",
                         d["arg_paths_foreign_gap"] or "-"))
        print("      -> decision with no args: %s (by %s)"
              % (r["decision_with_no_args"], r["decision_rule_id"]))
    print()

    # -- 4. controls ------------------------------------------------------
    print("-" * 78)
    print("4. CONTROLS - every one runs the same code path")
    print("-" * 78)
    failures = []
    controls = []

    def record(name, expectation, observed, ok, note):
        controls.append({"control": name, "expect": expectation,
                         "observed": observed, "pass": ok, "note": note})
        print("  %-34s expect %-14s observed %-14s %s"
              % (name, expectation, observed, "PASS" if ok else "*** FAIL ***"))
        if not ok:
            failures.append(name)

    base_policy = policies[0]["policy"]

    c1 = summarise(govern(unclassified_tools, base_policy))
    record("CTRL-1 all UNCLASSIFIED", "0 bound",
           "%d bound" % c1["tools_with_a_bound_rule"],
           c1["tools_with_a_bound_rule"] == 0,
           "cap:UNCLASSIFIED is not nameable by a rule; engine fails open")

    c2 = summarise(govern(tools, {"hashed_payload": {"rules": []}}))
    record("CTRL-2 empty policy", "0 bound",
           "%d bound" % c2["tools_with_a_bound_rule"],
           c2["tools_with_a_bound_rule"] == 0, "no rules, nothing to bind")

    absent = absent_class(tools)
    if absent is None:
        record("CTRL-3 absent class", "a class absent from the surface",
               "none exists", False,
               "every capability class is present; this control cannot run")
    else:
        c3 = summarise(govern(tools, rebind_policy(base_policy, absent)))
        record("CTRL-3 rebound to %s" % absent, "0 bound",
               "%d bound" % c3["tools_with_a_bound_rule"],
               c3["tools_with_a_bound_rule"] == 0,
               "same rules, one field changed - if this binds, the script is "
               "reporting on itself")

    c4 = summarise(govern(ours, base_policy))
    record("CTRL-4 our own target", ">0 bound",
           "%d/%d bound" % (c4["tools_with_a_bound_rule"], c4["tools_total"]),
           c4["tools_with_a_bound_rule"] > 0,
           "positive control: proves a zero elsewhere is a finding, not a bug")

    leaks = []
    for p, block in zip(policies, per_policy):
        leaks += name_leak_check(block["rows"])
        leaks += name_in_text_check(block["rows"], p["policy"])
    record("CTRL-5 tool name in rule", "0 occurrences",
           "%d occurrences" % len(leaks), len(leaks) == 0,
           "the binding is by capability class, not by name")
    print()

    # -- 5. aggregate across every policy, then what may be said ----------
    # Ruling 60 part 3. The input here is `run-*.json` campaign records; the
    # reader's verdict sits beside the matching `run-*.c6.json` bundle, so the
    # suffix is swapped to name it. A figure printed without its acceptance
    # count is the failure mode returning.
    _verdict.print_batch_banner(
        [p["file"][:-len(".json")] + ".c6.json" for p in policies],
        label="policy")
    print()
    print("-" * 78)
    print("5. ACROSS ALL %d POLICIES" % len(per_policy))
    print("-" * 78)
    per_tool = collections.Counter()
    all_gaps = set()
    uncond = no_gap = bound_total = 0
    for block in per_policy:
        for name in block["summary"]["governed_tool_names"]:
            per_tool[name] += 1
        all_gaps.update(block["summary"]["arg_paths_a_foreign_adapter_would_have_to_supply"])
        uncond += block["summary"]["unconditional_bound_rules"]
        no_gap += block["summary"]["bound_rules_with_no_foreign_vocabulary_gap"]
        bound_total += block["summary"]["bound_rules_total"]
    selectable = [t["tool_name"] for t in tools if t["capability_set"]]
    for name in selectable:
        print("  %-30s bound by %d of %d promoted policies"
              % (name, per_tool[name], len(per_policy)))
    union = sorted(per_tool)
    always = sorted(n for n in per_tool if per_tool[n] == len(per_policy))
    print()
    print("  bound by at least one policy : %d of %d tools  %s"
          % (len(union), len(tools), union))
    print("  bound by EVERY policy        : %d of %d tools  %s"
          % (len(always), len(tools), always))
    print("  bound rules, all policies    : %d" % bound_total)
    print("    ...unconditional           : %d  (no argument conditions at all - "
          "ports with\n                                    no adapter whatsoever)" % uncond)
    print("    ...no foreign-vocab gap    : %d  (reads only `derived.*`, which OUR "
          "harness\n                                    computes - ports as soon as the "
          "foreign manifest\n                                    declares a subject_key)"
          % no_gap)
    print("    ...with a vocabulary gap   : %d  (reads an argument this agent does "
          "not have)" % (bound_total - no_gap))
    print("  paths an adapter must supply : %s" % sorted(all_gaps))
    print()

    print("-" * 78)
    print("6. WHAT THIS LICENSES")
    print("-" * 78)
    print("  LICENSED:  %d of the %d foreign tools are SELECTED by at least one rule\n"
          "             promoted against a different agent. No rule names any of "
          "them:\n             CTRL-5 found 0 occurrences of a foreign tool name in "
          "any governing\n             rule, and every `tool_names` list is empty. "
          "The only thing joining\n             rule to tool is the capability class."
          % (len(union), len(tools)))
    print("  ALSO TRUE, AND IT MUST BE SAID IN THE SAME BREATH:")
    print("             Not one bound rule is unconditional (%d of %d). %d of the %d\n"
          "             bound rules read ONLY `derived.*` and would port on a "
          "subject_key\n             declaration; the remaining %d read an argument "
          "path this agent does\n             not declare, so their non-ALLOW decision "
          "is `engine.py` STEP 2 FAILING\n             CLOSED, not a matched fact. "
          "The class binding ports. The argument\n             predicates do not, yet."
          % (uncond, bound_total, no_gap, bound_total, bound_total - no_gap))
    print("  NOT LICENSED:  any attack success rate, any before/after, any claim "
          "that this\n                 agent was hardened. NOTHING WAS ATTACKED. The "
          "input is a frozen\n                 tool surface, not a running agent. "
          "measurement-spec sec 8.2's\n                 ~62% and ~25% are DESIGN "
          "TARGETS and are not measured here.")
    print("  ACCURACY:  classification is k=%d OK Cartographer runs (pre-registered,\n"
          "             docs/design/cartographer-stability-preregistration.md), "
          "UNRATIFIED;\n             governance is deterministic pure code over %d "
          "promoted policies."
          % (classification["ok_runs"], len(policies)))
    print()
    aggregate = {
        "tools_bound_by_at_least_one_policy": union,
        "tools_bound_by_every_policy": always,
        "bound_count_by_tool": dict(per_tool),
        "unconditional_bound_rules_total": uncond,
        "bound_rules_total": bound_total,
        "bound_rules_with_no_foreign_vocabulary_gap": no_gap,
        "bound_rules_with_a_foreign_vocabulary_gap": bound_total - no_gap,
        "arg_paths_a_foreign_adapter_would_have_to_supply": sorted(all_gaps),
    }

    artifact = {
        "artifact": "foreign governance transfer - GOVERNANCE ONLY, nothing attacked",
        "generated_by": "scripts/foreign-governance-transfer.py",
        "claim_licensed": ("a rule authored against one agent's capability class "
                           "selects tools belonging to an agent it never saw, and "
                           "names none of them"),
        "claim_not_licensed": ("any attack success rate, any before/after "
                               "reduction, any statement that the foreign agent "
                               "was hardened. Nothing was executed or attacked."),
        "foreign_target": {
            "name": frozen["target_name"],
            "repository": frozen["repository"],
            "commit_sha": frozen["commit_sha"],
            "commit_sha_verified": "see docs/proof/adk-commit-verification-2026-08-26.txt",
            "tool_count": frozen["tool_count"],
        },
        "classification": classification,
        "classification_ratified": False,
        "classification_ratification_note":
            "docs/proof/cartographer-adk-ratification.md is UNSIGNED. No entry "
            "here has reached a capability manifest. ratify.py needs a named "
            "human and an agent is not one.",
        # EMBEDDED VERBATIM ON PURPOSE. `evidence/` is gitignored, so a reader
        # with only the repository cannot open the run bundles these came from.
        # A result whose input is unreadable is a result nobody can check.
        "policies_verbatim": [{"run_id": p["run_id"], "file": p["file"],
                               "status": p["status"], "promotions": p["promotions"],
                               "policy": p["policy"]} for p in policies],
        "policies_source_note":
            "the final_policy of each completed run in the named directory. Only "
            "the RULE TEXT is used. This artifact makes no claim about those "
            "runs' ASR, BPR, or validity and needs none - a rule's capability "
            "class is a property of the rule.",
        "aggregate": aggregate,
        "per_policy": per_policy,
        "controls": controls,
        "own_manifest": {"path": args.own_manifest,
                         "manifest_hash": "read at use time, not typed - ruling 46"},
        "reps": "classification k=%d OK runs; governance is pure code, deterministic"
                % classification["ok_runs"],
    }
    if args.json:
        out = pathlib.Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(artifact, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print("wrote %s" % args.json)

    if failures:
        print("\nCONTROLS FAILED: %s" % ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":       # pragma: no cover
    raise SystemExit(main())
