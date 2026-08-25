#!/usr/bin/env python3
"""constrain-arg-survey.py - does any capability class legitimately call for `constrain_arg`?

WHAT THIS ANSWERS
-----------------
CRUCIBLE's policy DSL has three verbs: `deny`, `require_approval`, `constrain_arg`.
Across the live runs to date `constrain_arg` has been proposed zero times.
`crucible/armorer/prompt.py:135-160` already explains why on CAP_MOVES_MONEY, and
that explanation is TRUE: every money band in the sourced authority ladder has a
legitimate above-band path, so `require_approval` correctly dominates there.

The open question is whether the verb has a legitimate home ANYWHERE on this
target. This script measures it. It does not tune anything, it calls no model,
and it reads only artifacts already on disk.

THE TEST
--------
`constrain_arg` is the right verb for a (capability class, arg_path) pair when
all three hold:

  0. EXPRESSIBLE.  `contracts/policy.ebnf` gives the action production as
     `constrain_arg "(" arg_path cmp_op literal ")"` with
     `literal = INTEGER | BOOLEAN | enum_symbol`. There are NO free strings in
     the language, and the action production has no `episode.` form. So an
     argument whose values are opaque identifiers or prose cannot be
     constrained at all - not by policy choice, by grammar.

  1. SEPARATION.  A single literal exists that excludes attack values at ZERO
     cost to the benign population. Two grades are reported:
       FULL    - the constraint excludes every attack value in the class
       PARTIAL - it excludes some attack values and no benign value

  2. NO ESCAPE HATCH.  The class has no legitimate authority that can exceed
     the bound. This is what disqualifies money: escalation is a real
     above-band path, and it acts through the SAME tool after approval.
     Two readings are reported - one computed from the corpus, one cited from
     `docs/refund-policy-research.md`.

FAIL-CLOSED IS WHY THE GUARD COLUMN EXISTS
------------------------------------------
`crucible/policy/engine.py:317-327`: a `constrain_arg` whose path is absent,
null or wrong-typed is treated as VIOLATED and the call is DENIED. A rule
selects a CAPABILITY CLASS, and no argument is carried by every tool in any
class on this target. So a bare rule on `status_to` fires on every
CAP_MUTATES_DURABLE_STATE call, including the refunds that carry no
`status_to`, and denies them. The remedy is ruling 42's `when <arg> is present`
guard. The GUARD column counts how many benign calls a bare rule would kill.

POPULATIONS
-----------
  BENIGN  every call in every trace under `fixtures/benign/` - all of it is
          legitimate work the policy must not break.
  ATTACK  the `scored: true` breach call of every episode under
          `corpus/training/`. The non-scored prefix calls of an attack episode
          are legitimate-shaped setup and are reported separately as
          COLLATERAL, never counted as attack values.

The sealed F4 family is NOT read. Its public counts manifest
(`corpus/F4-MANIFEST.json`) carries no instance content and is used only for the
supplementary reason_code check at the foot of the report.

Usage:  python scripts/constrain-arg-survey.py [--repo <path>]
Exit 0 always. This is a measurement, not a gate.
"""

import argparse
import collections
import json
import pathlib
import sys

# --------------------------------------------------------------------------
# Escape-hatch findings, read out of docs/refund-policy-research.md by hand.
#
# THIS TABLE IS CITED, NOT COMPUTED, and it is kept separate from everything
# else in this file for exactly that reason. Each entry names the section it
# came from so a reader can check it. The computed half of the escape-hatch
# question is done further down, in `policy_band_check`.
# --------------------------------------------------------------------------
ESCAPE_HATCH = {
    "amount_minor": (
        True,
        "B authority ladder + 11",
        "Every band has a named human above it (T1 -> RETURNS_T2 -> Supervisor "
        "-> Duty Manager -> Director) and the approved refund is then issued "
        "through this same tool with this same argument. The above-band path "
        "runs THROUGH the constrained argument, which is precisely the "
        "condition under which a terminal bound is the wrong instrument.",
    ),
    "recommended_amount_minor": (
        True,
        "11 b, 11 c",
        "This argument is a RECOMMENDATION into a human queue, not a "
        "disbursement. Section 11 requires the agent to write the exact amount "
        "and its recommendation on escalation. Bounding it would block the "
        "escalation of large claims - it would suppress the hand-off that "
        "exists to handle exactly those, which is backwards.",
    ),
    "queue": (
        True,
        "11",
        "All four queues are legitimate destinations and the agent is required "
        "to route to each of them in different circumstances. The abuse is "
        "choosing the WRONG queue for the case at hand, which is a relation "
        "between the call and the episode, not a property of the value.",
    ),
    "reason_code": (
        True,
        "0.3, 1, 3, 7",
        "Section 0.3 permits all twelve codes and requires one to be recorded. "
        "Sections 1, 3 and 7 give several of them their own legitimate "
        "handling. No code is illegitimate per se, so excluding any single one "
        "removes legitimate work the policy explicitly provides for.",
    ),
    "specialist_agent": (
        True,
        "11",
        "All three specialists are legitimate delegation targets. Same shape as "
        "queue: the abuse is the wrong destination for this case, not a bad "
        "value.",
    ),
    "currency": (
        False,
        "manifest arg_enums",
        "The manifest declares exactly one currency, so no legitimate authority "
        "can exceed a `== USD` bound. The bound is nevertheless vacuous here - "
        "see the SEP column, no attack value differs either.",
    ),
    "status_to": (
        False,
        "11",
        "Section 11 puts the escalation outcome with the human queue: states "
        "are PENDING / APPROVED / REJECTED, the queue's outcome is 'written "
        "back to the case with a reason', and 'escalation is a human decision, "
        "always. No queue auto-approves and no rule auto-approves on your "
        "behalf.' The approver does not act through the agent's "
        "update_case_notes tool, so removing APPROVED from that tool removes no "
        "legitimate authority. RESIDUAL RISK, stated rather than hidden: if a "
        "deployment makes the agent the SCRIBE that records a granted T2 "
        "outcome, the hatch reappears and the verb becomes wrong here too.",
    ),
}

# Numeric bounds the modeled policy states outright, for the computed half of
# the escape-hatch question. Minor units. Only amount_minor has one.
POLICY_BANDS = {
    "amount_minor": (15000, "B authority ladder, T1 per-order band $150"),
}


def load_json(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def collect(repo):
    """Build the three populations, keyed by (capability_class, arg_path).

    Returns a dict of records plus per-class call totals, which the GUARD
    column needs: a bare constrain_arg rule fires on EVERY call in its class,
    not only on the calls that carry the argument.
    """
    manifest = load_json(repo / "target" / "refund_agent" / "capability_manifest.json")
    tools = {t["tool_fqname"]: t for t in manifest["tools"]}
    arg_enums = manifest.get("arg_enums", {})

    # value lists, keyed (cap, arg) -> list of (slug, value_or_MISSING)
    pops = {"benign": collections.defaultdict(list),
            "attack": collections.defaultdict(list),
            "collateral": collections.defaultdict(list)}
    # calls in class, keyed cap -> list of slugs (one entry per call)
    class_calls = {"benign": collections.Counter(),
                   "attack": collections.Counter(),
                   "collateral": collections.Counter()}
    # benign calls whose EPISODE declares a real approver, keyed (cap, arg)
    approver_bearing = collections.defaultdict(list)

    def walk(globpat, pop_scored, pop_unscored):
        for path in sorted((repo).glob(globpat)):
            episode = load_json(path)
            slug = episode.get("slug", path.stem)
            approver = episode.get("approver")
            has_approver = isinstance(approver, dict)
            for call in episode.get("trace", []):
                bucket = pop_scored if call.get("scored") else pop_unscored
                if bucket is None:
                    continue
                tool = tools.get(call["tool_fqname"])
                if tool is None:
                    raise SystemExit("tool not in manifest: %s" % call["tool_fqname"])
                args = call.get("args", {})
                for cap in tool["capability_classes"]:
                    class_calls[bucket][cap] += 1
                    for arg in tool["arg_paths"]:
                        if arg not in args:
                            continue
                        pops[bucket][(cap, arg)].append((slug, args[arg]))
                        if bucket == "benign" and has_approver:
                            approver_bearing[(cap, arg)].append(
                                (slug, args[arg], approver.get("tier")))

    # benign: every call counts, scored or not - all of it is legitimate work
    walk("fixtures/benign/*.json", "benign", "benign")
    # attack: the scored call is the breach; the prefix is legitimate-shaped
    walk("corpus/training/*.json", "attack", "collateral")

    return manifest, tools, arg_enums, pops, class_calls, approver_bearing


def classify_type(values, arg, arg_enums):
    """EXPRESSIBLE column. What kind of literal, if any, can bound this arg?"""
    if arg in arg_enums:
        return "enum"
    if values and all(isinstance(v, int) and not isinstance(v, bool) for v in values):
        return "int"
    if values and all(isinstance(v, bool) for v in values):
        return "bool"
    return "none"


def best_constraint(kind, benign_vals, attack_vals, arg, arg_enums):
    """Find the single literal that excludes the most attack values at zero
    benign cost.

    Returns (text, attack_hits, attack_total, grade) where grade is
    FULL / PARTIAL / NONE.

    Only the forms the grammar actually admits are considered:
      int  -> `<= max(benign)` and `>= min(benign)`
      enum -> `!= X` for a symbol absent from benign, `== X` when benign is
              a single symbol
    An integer `!= literal` is grammatical but degenerate (it excludes exactly
    one value) and is deliberately not searched - a policy that has to enumerate
    every bad integer is not a bound.
    """
    total = len(attack_vals)
    if total == 0 or not benign_vals:
        return ("-", 0, total, "NONE")

    candidates = []
    if kind == "int":
        hi = max(benign_vals)
        candidates.append(("<= %d" % hi, sum(1 for v in attack_vals if v > hi)))
        lo = min(benign_vals)
        candidates.append((">= %d" % lo, sum(1 for v in attack_vals if v < lo)))
    elif kind == "enum":
        declared = arg_enums.get(arg, [])
        bset = set(benign_vals)
        for sym in declared:
            if sym not in bset:                       # `!= sym` costs no benign
                candidates.append(("!= %s" % sym,
                                   sum(1 for v in attack_vals if v == sym)))
        if len(bset) == 1:                            # `== sym` costs no benign
            only = next(iter(bset))
            candidates.append(("== %s" % only,
                               sum(1 for v in attack_vals if v != only)))
    else:
        return ("not expressible", 0, total, "NONE")

    candidates.sort(key=lambda c: -c[1])
    text, hits = candidates[0]
    if hits == 0:
        return ("-", 0, total, "NONE")
    return (text, hits, total, "FULL" if hits == total else "PARTIAL")


def policy_band_check(arg, benign_pairs, approver_pairs):
    """The COMPUTED half of the escape-hatch question.

    Where the modeled policy states a numeric band, count the benign calls that
    exceed it and check how many of those carry an approver. A benign call above
    the band that carries an approver IS the escape hatch, observed rather than
    argued.
    """
    if arg not in POLICY_BANDS:
        return None
    band, cite = POLICY_BANDS[arg]
    over = [(s, v) for s, v in benign_pairs if isinstance(v, int) and v > band]
    over_with_approver = [(s, v, t) for s, v, t in approver_pairs
                          if isinstance(v, int) and v > band]
    return band, cite, over, over_with_approver


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=None, help="repo root (default: parent of this file)")
    args_cli = ap.parse_args()

    repo = pathlib.Path(args_cli.repo) if args_cli.repo \
        else pathlib.Path(__file__).resolve().parent.parent
    manifest, tools, arg_enums, pops, class_calls, approver_bearing = collect(repo)

    n_benign_files = len(list((repo / "fixtures" / "benign").glob("*.json")))
    n_attack_files = len(list((repo / "corpus" / "training").glob("*.json")))

    print("CRUCIBLE constrain_arg survey")
    print("target       : %s" % manifest["target_id"])
    print("manifest     : %d tools, %d capability classes exercised"
          % (len(manifest["tools"]), len(class_calls["benign"] | class_calls["attack"])))
    # NOTE ON DENOMINATORS. A rule selects ONE capability class, and a tool can
    # carry two, so the table below counts (call, class) PAIRS - a single
    # issue_refund appears once under CAP_MOVES_MONEY and once under
    # CAP_MUTATES_DURABLE_STATE. The ENGINE VERIFICATION section further down
    # counts raw CALLS, because the engine decides once per call. Both counts
    # are printed so neither is mistaken for the other.

    raw = collections.Counter()
    for globpat, sb, ub in (("fixtures/benign/*.json", "benign", "benign"),
                            ("corpus/training/*.json", "attack", "collateral")):
        for path in sorted(repo.glob(globpat)):
            for call in load_json(path).get("trace", []):
                raw[sb if call.get("scored") else ub] += 1
    print("benign        : %d fixture files, %d calls, %d (call,class) pairs"
          % (n_benign_files, raw["benign"], sum(class_calls["benign"].values())))
    print("attack        : %d corpus files, %d scored breach calls, %d pairs"
          % (n_attack_files, raw["attack"], sum(class_calls["attack"].values())))
    print("collateral    : %d non-scored prefix calls in attack episodes, %d pairs"
          % (raw["collateral"], sum(class_calls["collateral"].values())))
    print()

    keys = sorted(set(pops["benign"]) | set(pops["attack"]))
    rows = []
    for cap, arg in keys:
        bpairs = pops["benign"][(cap, arg)]
        apairs = pops["attack"][(cap, arg)]
        bvals = [v for _, v in bpairs]
        avals = [v for _, v in apairs]
        kind = classify_type(bvals + avals, arg, arg_enums)
        text, hits, total, grade = best_constraint(kind, bvals, avals, arg, arg_enums)

        # GUARD: benign calls in this class that do NOT carry the argument.
        # A bare rule denies every one of them (engine.py:317-327).
        guard = class_calls["benign"][cap] - len(bpairs)

        hatch, cite, _why = ESCAPE_HATCH.get(arg, (None, "-", ""))

        if kind == "none":
            verdict = "NOT EXPRESSIBLE"
        elif total == 0:
            verdict = "NO ATTACK DATA"
        elif grade == "NONE":
            verdict = "NO SEPARATION"
        elif hatch:
            verdict = "SEPARABLE, HATCH"
        else:
            verdict = "*** JUSTIFIED ***"

        rows.append((cap, arg, kind, bpairs, apairs, text, hits, total,
                     grade, guard, hatch, cite, verdict))

    def summarize(pairs, kind, width=32):
        """One cell of the table. Long enum sets are truncated here and printed
        in full in the ENUM POPULATIONS section below, so the table stays
        readable without losing anything."""
        vals = [v for _, v in pairs]
        if not vals:
            return "n=0"
        if kind == "int":
            return "n=%d [%d..%d]" % (len(vals), min(vals), max(vals))
        if kind == "enum":
            c = collections.Counter(str(v) for v in vals)
            body = ",".join("%s:%d" % kv for kv in sorted(c.items()))
            head = "n=%d u=%d " % (len(vals), len(c))
            if len(head) + len(body) + 2 > width:
                return head + "(see below)"
            return head + "{%s}" % body
        return "n=%d free-text/id" % len(vals)

    fmt = "%-26s %-25s %-5s %-32s %-32s %-8s %-19s %-6s %-6s %s"
    hdr = fmt % ("CLASS", "ARG_PATH", "TYPE", "BENIGN", "ATTACK(scored)", "SEP",
                 "BEST ZERO-COST", "COVER", "HATCH", "VERDICT")
    print(hdr)
    print("-" * len(hdr))
    for (cap, arg, kind, bp, apr, text, hits, total, grade, guard,
         hatch, cite, verdict) in rows:
        print(fmt % (cap, arg, kind, summarize(bp, kind), summarize(apr, kind),
                     grade if grade != "NONE" else "no", text,
                     "%d/%d" % (hits, total),
                     {True: "yes", False: "no", None: "-"}[hatch],
                     verdict))
    print()

    # ---- full enum populations, since the table truncates them ----------
    print("ENUM POPULATIONS IN FULL (the table truncates the wide ones)")
    print("=" * 78)
    seen = set()
    for (cap, arg, kind, bp, apr, *_rest) in rows:
        if kind != "enum" or arg in seen:
            continue
        seen.add(arg)
        bc = collections.Counter(str(v) for _, v in bp)
        ac = collections.Counter(str(v) for _, v in apr)
        cc = collections.Counter(str(v) for _, v in pops["collateral"][(cap, arg)])
        print("  %-18s declared %s" % (arg, ", ".join(arg_enums.get(arg, []))))
        print("  %-18s benign     %s" % ("", dict(sorted(bc.items())) or "{}"))
        print("  %-18s attack     %s" % ("", dict(sorted(ac.items())) or "{}"))
        print("  %-18s collateral %s" % ("", dict(sorted(cc.items())) or "{}"))
        print()

    # ---- detail on every row that got past separation -------------------
    print("DETAIL - every pair that cleared criterion 1 (separation)")
    print("=" * 78)
    any_detail = False
    for (cap, arg, kind, bp, apr, text, hits, total, grade, guard,
         hatch, cite, verdict) in rows:
        if grade == "NONE":
            continue
        any_detail = True
        print()
        print("%s / %s" % (cap, arg))
        print("  constraint      constrain_arg(%s %s)" % (arg, text))
        print("  attack coverage %d of %d scored breach calls in this class carry the arg"
              % (hits, total))
        print("  benign cost     0 of %d benign calls carrying the arg" % len(bp))
        coll = pops["collateral"][(cap, arg)]
        coll_hit = [s for s, v in coll if _excluded_by(text, v)]
        print("  collateral      %d of %d non-scored prefix calls inside attack"
              % (len(coll_hit), len(coll)))
        print("                  episodes would also be denied")
        if guard > 0:
            print("  GUARD REQUIRED  %d benign calls in %s do not carry `%s` at all."
                  % (guard, cap, arg))
            print("                  A bare rule denies all %d (engine.py:317-327)." % guard)
            print("                  Ruling 42 remedy: `when %s is present`." % arg)
        else:
            print("  guard           not needed, every call in the class carries the arg")
        hatchtxt = ESCAPE_HATCH.get(arg)
        if hatchtxt:
            print("  escape hatch    %s  (refund-policy-research.md section %s)"
                  % ("YES" if hatchtxt[0] else "NO", hatchtxt[1]))
            for line in _wrap(hatchtxt[2], 70):
                print("                  " + line)
        band = policy_band_check(arg, bp, approver_bearing[(cap, arg)])
        if band:
            _, bcite, over, over_appr = band
            print("  computed hatch  %d benign calls exceed the policy band (%s);"
                  % (len(over), bcite))
            print("                  %d of those carry an approver." % len(over_appr))
        print("  attack episodes " + ", ".join(sorted(set(
            s for s, v in apr if _excluded_by(text, v)))))
        print("  verdict         %s" % verdict)
    if not any_detail:
        print("  (none)")
    print()

    # ---- the computed escape hatch on money, shown in full ---------------
    print("COMPUTED ESCAPE HATCH - CAP_MOVES_MONEY / amount_minor")
    print("=" * 78)
    bp = pops["benign"][("CAP_MOVES_MONEY", "amount_minor")]
    apr = pops["attack"][("CAP_MOVES_MONEY", "amount_minor")]
    band, cite, over, over_appr = policy_band_check(
        "amount_minor", bp, approver_bearing[("CAP_MOVES_MONEY", "amount_minor")])
    print("policy band        %d minor units (%s)" % (band, cite))
    print("benign above band  %d of %d benign money calls" % (len(over), len(bp)))
    print("of those, with an approver on the episode: %d" % len(over_appr))
    for slug, val, tier in sorted(over_appr, key=lambda r: -r[1]):
        print("   %8d  %-6s %s" % (val, tier, slug))
    bvals = [v for _, v in bp]
    avals = [v for _, v in apr]
    print("benign max %d, attack max %d - the populations reach the same ceiling,"
          % (max(bvals), max(avals)))
    print("so no threshold separates them. Every benign call above the band is")
    print("above it BECAUSE A HUMAN APPROVED IT, through this same tool and this")
    print("same argument. That is the escape hatch, observed rather than argued.")
    print()

    # ---- run the candidate rules through the REAL engine -----------------
    #
    # Everything above is this script's own arithmetic over the corpus. This
    # section hands three candidate rules to `crucible.policy.engine`, the code
    # that actually enforces policy, and counts what it denies. A survey that
    # only agrees with itself is a check that cannot fail.
    sys.path.insert(0, str(repo))
    from crucible.policy.engine import PolicyEngine, STRICTNESS  # noqa: E402
    from crucible.policy.decision import DENY                    # noqa: E402

    guarded = {
        "rule_id": "r_000000000001", "verb": "constrain_arg",
        "match": {"capability_class": "CAP_MUTATES_DURABLE_STATE",
                  "arg_conditions": [{"path": "status_to", "op": "is_present"}]},
        "action": {"path": "status_to", "op": "ne", "value": "APPROVED"},
    }
    bare = {
        "rule_id": "r_000000000002", "verb": "constrain_arg",
        "match": {"capability_class": "CAP_MUTATES_DURABLE_STATE"},
        "action": {"path": "status_to", "op": "ne", "value": "APPROVED"},
    }
    deny_equiv = {
        "rule_id": "r_000000000003", "verb": "deny",
        "match": {"capability_class": "CAP_MUTATES_DURABLE_STATE",
                  "arg_conditions": [{"path": "status_to", "op": "is_present"},
                                     {"path": "status_to", "op": "eq",
                                      "value": "APPROVED"}]},
    }

    def run_engine(rule):
        """Count DENY decisions over each population, using the real engine."""
        eng = PolicyEngine({"rules": [rule]})
        counts = {"benign": 0, "attack": 0, "collateral": 0}
        totals = {"benign": 0, "attack": 0, "collateral": 0}
        for bucket, globpat, scored_bucket, unscored_bucket in (
                ("benign", "fixtures/benign/*.json", "benign", "benign"),
                ("attack", "corpus/training/*.json", "attack", "collateral")):
            for path in sorted(repo.glob(globpat)):
                episode = load_json(path)
                for call in episode.get("trace", []):
                    tgt = scored_bucket if call.get("scored") else unscored_bucket
                    tool = tools[call["tool_fqname"]]
                    totals[tgt] += 1
                    d = eng.evaluate(tool_handle=tool["tool_handle"],
                                     capability_set=tool["capability_classes"],
                                     args=call.get("args", {}))
                    if d.outcome == DENY:
                        counts[tgt] += 1
        return counts, totals

    print("ENGINE VERIFICATION - candidate rules run through crucible.policy.engine")
    print("=" * 78)
    for label, rule in (("guarded constrain_arg", guarded),
                        ("bare constrain_arg (no `is present` guard)", bare),
                        ("deny + when, the equivalent", deny_equiv)):
        counts, totals = run_engine(rule)
        print("  %s" % label)
        print("     benign denied      %d of %d" % (counts["benign"], totals["benign"]))
        print("     attack denied      %d of %d scored breach calls"
              % (counts["attack"], totals["attack"]))
        print("     collateral denied  %d of %d prefix calls"
              % (counts["collateral"], totals["collateral"]))
    print()
    print("The bare form is what ruling 42 exists to prevent: it denies benign")
    print("calls that never carried the argument. The guarded form and the deny")
    print("form produce identical counts, which is the redundancy noted below.")
    print()

    # ---- is the verb redundant with `deny when ...`? ---------------------
    # Read the strictness table out of the engine rather than restating it.
    print("VERB PRECEDENCE - read from crucible/policy/engine.py")
    print("=" * 78)
    for verb, rank in sorted(STRICTNESS.items(), key=lambda kv: -kv[1]):
        print("   %-18s strictness %d" % (verb, rank))
    print()
    print("engine.py:317-327 gives a VIOLATED constrain_arg the DENY outcome, but")
    print("at its own strictness. `cmp_op` is closed under negation and an")
    print("unevaluable `when` retains the rule fail-closed (engine.py:302-303), so")
    print("   constrain_arg(A op L)   and   deny when A <negated-op> L")
    print("deny exactly the same calls IN ISOLATION. They differ only in")
    print("COMPOSITION: a co-firing require_approval rule outranks a violated")
    print("constrain_arg (%d > %d) and does not outrank a deny (%d < %d)."
          % (STRICTNESS["require_approval"], STRICTNESS["constrain_arg"],
             STRICTNESS["require_approval"], STRICTNESS["deny"]))
    print("That is the verb's one non-redundant property on this grammar.")
    print()

    # ---- supplementary: the sealed family, counts only -------------------
    f4path = repo / "corpus" / "F4-MANIFEST.json"
    if f4path.exists():
        f4 = load_json(f4path)
        print("SUPPLEMENTARY - sealed F4 family (public counts manifest only)")
        print("=" * 78)
        print("smuggled arg_path         %s" % ", ".join(f4.get("smuggled_arg_path", [])))
        print("compared against          %s" % f4.get("episode_field_compared_against"))
        print("reason_code symbols used  %d of %d declared"
              % (len(f4.get("distributions", {}).get("reason_code", {})),
                 len(arg_enums.get("reason_code", []))))
        print()
        print("The sealed family smuggles a DESTINATION IDENTIFIER and the control")
        print("that catches it compares that identifier to an episode context field.")
        print("`constrain_arg` cannot express that: its action production takes a")
        print("literal, and identifiers are not literals in this language. It spans")
        print("nearly the whole reason_code enum, so no single-symbol reason_code")
        print("constraint would have touched it either. No instance content read.")
        print()


def _excluded_by(text, value):
    """Would this value violate the constraint text? Used only for reporting."""
    try:
        op, lit = text.split(" ", 1)
    except ValueError:
        return False
    try:
        lit_v = int(lit)
    except ValueError:
        lit_v = lit
    try:
        if op == "<=":
            return not (value <= lit_v)
        if op == ">=":
            return not (value >= lit_v)
        if op == "!=":
            return not (value != lit_v)
        if op == "==":
            return not (value == lit_v)
    except TypeError:
        return True
    return False


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
