"""armorer-grouping-probe.py - PROBE SCAFFOLDING. NOT A CHANGE TO SHIP.

THIS FILE IS NOT PART OF THE LOOP AND NOTHING IMPORTS IT. It exists to answer
one question that no offline measurement can answer:

    Given a grammar in which the grouped aggregate IS expressible, does the
    real ARMORER (`gemini-3.7-flash`, pinned, CONVENTIONS 3.1) actually EMIT
    the grouped form on the one autopsy where the grouped form is the correct
    rule?

WHAT IT DOES NOT TOUCH. `contracts/policy.ebnf` is READ, never written. Arm B
writes a MODIFIED COPY into a scratch directory and points
`crucible.armorer.prompt.POLICY_EBNF` at the copy for the duration of the arm.
The parser, the validator, the engine and the serializer are UNCHANGED, so a
grouped emission in arm B is expected to FAIL the real parser - that is not the
measurement. The measurement is what the model wrote.

WHY IT REPRODUCES `Armorer.propose`'s FIRST ATTEMPT RATHER THAN CALLING IT.
`propose` fires ONE REPAIR when the parser refuses, and in arm B the parser
refuses by construction (the parser was deliberately not extended). Every arm-B
sample would therefore spend a second call producing a rule written in response
to a parse error, and someone reading the transcript would count that fallback
as the model's choice. So this calls the SAME functions `propose` calls -
`adapter.project`, `prompt.build_user_message`, `prompt.SYSTEM_INSTRUCTION`,
`Armorer._fire`, `Armorer._try` - and stops before the repair branch. Every
sample is an independent first emission.

Run:
    python scripts/probes/armorer-grouping-probe.py --dry-run   # assemble, no call
    python scripts/probes/armorer-grouping-probe.py --score     # offline warden scores
    python scripts/probes/armorer-grouping-probe.py --live --samples 6 --arms A,B,C

Findings and the full transcript:
    docs/proof/armorer-grouping-probe-2026-08-26.md
    docs/proof/armorer-grouping-probe-2026-08-26.json
"""

import argparse
import json
import os
import re
import sys
import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)

from crucible.armorer import prompt as prompt_mod                    # noqa: E402
from crucible.armorer.adapter import project                         # noqa: E402
from crucible.armorer.armorer import Armorer, ARMORER_MODEL, ARMORER_THINKING_LEVEL, strip_fences  # noqa: E402
from crucible.armorer.experiment import build_seed_policy            # noqa: E402
from crucible.conductor.campaign import build_validator              # noqa: E402
from crucible.conductor.real_tripwire import resolve_objective_set   # noqa: E402
from crucible.dsl import parse_policy                                # noqa: E402

# `evidence/` is gitignored, so it exists only in the tree that produced the run.
# A worktree checkout does not carry it; PROBE_BUNDLE points at the real one.
BUNDLE = os.environ.get("PROBE_BUNDLE") or os.path.join(
    _REPO, "evidence", "smoke-2026-08-25", "run-02.c6.json")
ROUND = 3

# The round-1 patch that was promoted before round 3 opened. Copied verbatim
# out of `policy_chain[1]` of the bundle; recompiled through the REAL validator
# here rather than pasted as stored JSON, so the rule_id is computed and not
# transcribed (CONVENTIONS 2.6 applies to humans too).
ROUND1_PROMOTED_DSL = (
    "rule r_new1: cap:CAP_MUTATES_DURABLE_STATE when "
    "derived.episode_count_same_subject >= 4 => deny origin armorer:1")

# ---------------------------------------------------------------------------
# ARM B's grammar edit. ONE PRODUCTION, OPTIONAL SO EVERY EXISTING RULE STILL
# PARSES. Shape taken from docs/design/dsl-grouping-gap-scope-2026-08-25.md
# section 2.2, which rejected `group_by=` because `=` is deliberately not a
# token (crucible/dsl/parser.py:68-69).
# ---------------------------------------------------------------------------
ARM_A_PRODUCTION = '              | "episode_sum" "(" arg_path ")" cmp_op INTEGER'
ARM_B_PRODUCTION = ('              | "episode_sum" "(" arg_path [ "group_by" arg_path ] ")" '
                    "cmp_op INTEGER")


def arm_b_ebnf(scratch_dir):
    """Write the modified EBNF to scratch. contracts/ is opened READ-ONLY."""
    with open(prompt_mod.POLICY_EBNF, encoding="utf-8") as fh:
        text = fh.read()
    if ARM_A_PRODUCTION not in text:
        raise SystemExit("the episode_sum production is not where this probe "
                         "expected it; re-read contracts/policy.ebnf before "
                         "trusting any arm-B number.")
    out = os.path.join(scratch_dir, "policy.armB.ebnf")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text.replace(ARM_A_PRODUCTION, ARM_B_PRODUCTION, 1))
    return out


_REAL_HANDOUT = prompt_mod.grammar_handout


class use_ebnf(object):
    """Point `build_user_message` at a different grammar file for one block.

    `grammar_handout(path=POLICY_EBNF)` binds its default at DEFINITION time, so
    reassigning `prompt_mod.POLICY_EBNF` does nothing - the first version of this
    probe did exactly that and produced two byte-identical prompts, which would
    have read as "the model ignored the new production" when in fact the model
    was never shown one. The name `grammar_handout` IS looked up at call time
    inside the module, so that is the seam.
    """

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        prompt_mod.grammar_handout = lambda path=None: _REAL_HANDOUT(self.path)
        return self

    def __exit__(self, *exc):
        prompt_mod.grammar_handout = _REAL_HANDOUT
        return False


def load_autopsy():
    with open(BUNDLE, encoding="utf-8") as fh:
        bundle = json.load(fh)
    hits = [a for a in bundle["autopsies"] if a["round_index"] == ROUND]
    if len(hits) != 1:
        raise SystemExit("expected exactly one round-%d autopsy, got %d"
                         % (ROUND, len(hits)))
    return hits[0]


def build_round3_policy(validator):
    """policy@v1 - the seed floor plus the rule round 1 promoted."""
    policy = build_seed_policy(validator)
    payload = validator.validate_patch(parse_policy(ROUND1_PROMOTED_DSL), policy)
    return {"envelope_version": 1, "hashed_payload": payload,
            "lineage": {"version": 1, "parent_hash": "0" * 16,
                        "lineage_hash": "0" * 16}}


# ---------------------------------------------------------------------------
# CLASSIFYING ONE EMISSION. Text-level and deliberately crude: the point is to
# count shapes, and every raw string is written to the transcript so the
# classification can be checked by eye rather than trusted.
# ---------------------------------------------------------------------------
_GROUPED = re.compile(r"episode_sum\s*\(\s*[\w.]+\s+group_by\s+[\w.]+\s*\)")
_UNGROUPED_SUM = re.compile(r"episode_sum\s*\(\s*[\w.]+\s*\)")
_PER_CALL = re.compile(r"(?<!episode_sum\()\bderived\.episode_count_same_subject\s*(>=|>|==)")


def classify(text):
    if _GROUPED.search(text):
        return "GROUPED"
    if _UNGROUPED_SUM.search(text):
        return "UNGROUPED_SUM"
    if "episode_count_same_subject" in text:
        return "PER_CALL"
    return "OTHER"


def run_arm(name, ebnf_path, samples, autopsy, validator, manifest_a,
            derived_b, policy, objective_set, call_model, extra_rules=None,
            jsonl=None):
    original_rules = prompt_mod.VALIDATOR_RULES
    if extra_rules:
        prompt_mod.VALIDATOR_RULES = original_rules + extra_rules
    try:
        armorer = Armorer(validator, manifest_a, derived_b, call_model,
                          objective_set=objective_set)
        projected = project(autopsy, objective_set=objective_set)
        from crucible.armorer.armorer import render_current
        with use_ebnf(ebnf_path):
            user_text = prompt_mod.build_user_message(
                projected_record=projected, manifest_a=manifest_a,
                derived_schema_b=derived_b, policy_text=render_current(policy),
                round_index=ROUND)
        system_text = prompt_mod.SYSTEM_INSTRUCTION

        results = []
        for i in range(samples):
            attempts = []
            attempt = armorer._fire(system_text, user_text, attempts, "initial")
            outcome = armorer._try(attempt, policy)
            text = strip_fences(attempt.raw_text)
            results.append({
                "arm": name, "sample": i + 1,
                "raw_text": attempt.raw_text,
                "patch_text": text,
                "shape": classify(text),
                "parsed": attempt.parsed,
                "validated": attempt.validated,
                "error_code": attempt.error_code,
                "error_detail": attempt.error_detail[:400],
                "usd": attempt.usd,
                "tokens": attempt.tokens,
                "latency_ms": attempt.latency_ms,
                "accepted_by_real_parser": outcome is not None,
            })
            # WRITTEN AS IT LANDS. A probe that only persists at the end loses
            # every sample it paid for if the last call hangs, and the first
            # attempt at this run did exactly that.
            if jsonl:
                with open(jsonl, "a", encoding="utf-8", newline="\n") as fh:
                    fh.write(json.dumps(results[-1]) + "\n")
            print("  [%s %d/%d] %s  %s" % (name, i + 1, samples,
                                           results[-1]["shape"],
                                           text.replace("\n", " | ")[:150]),
                  flush=True)
        return {"arm": name, "ebnf": ebnf_path, "user_message": user_text,
                "system_message": system_text, "samples": results}
    finally:
        prompt_mod.VALIDATOR_RULES = original_rules


# ARM C's added line. DESCRIPTIVE, NOT PRESCRIPTIVE, on purpose: it states what
# the two forms of `episode_sum` compute and stops. It does not mention the
# invariant, does not say "use group_by", and does not name `case_id`. A line
# that told the model which rule to write would measure the instruction rather
# than the model, and the arm would answer nothing.
GUIDANCE_LINE = """\
V10 `episode_sum(path)` sums that path over EVERY visible call in the episode.
    It does not group. `episode_sum(path group_by key)` sums it only within the
    bucket of calls sharing the same value of `key`, and a call carrying no
    `key` is in no bucket. The two are different numbers whenever an episode
    touches more than one value of `key`.
"""


# ---------------------------------------------------------------------------
# `--score`: what the arm-A emissions are worth on the REAL benign floor.
# OFFLINE, no model call. Only the three shapes today's grammar admits can be
# scored here - the grouped form does not parse, because the parser was
# deliberately not extended, and a number for it would have to come from an
# engine this probe did not build.
# ---------------------------------------------------------------------------
ARM_A_EMISSIONS = (
    ("per-call >= 3", "derived.episode_count_same_subject >= 3"),
    ("per-call >= 4 (the rule already in force)",
     "derived.episode_count_same_subject >= 4"),
    ("ungrouped episode_sum >= 4",
     "episode_sum(derived.episode_count_same_subject) >= 4"),
)


def _wrap(payload, version):
    return {"envelope_version": 1, "hashed_payload": payload,
            "lineage": {"version": version, "parent_hash": "0" * 16,
                        "lineage_hash": "0" * 16}}


def score(validator, policy):
    from crucible.conductor.real_warden import real_warden

    def line(rep):
        return ("benign %s/%s  near-miss %s/%s  approval-masked %s  failed %s"
                % (rep.get("passed"), rep.get("total"),
                   rep.get("near_miss_passed"), rep.get("near_miss_total"),
                   rep.get("benign_passes_requiring_approval"),
                   rep.get("failed_classes") or []))

    in_force = [r["rule_id"] for r in policy["hashed_payload"]["rules"]
                if str(r.get("origin", "")).startswith("armorer")][0]
    print("policy@v1 armorer rule id: %s" % in_force)
    print("%-46s %s" % ("baseline, policy@v1 unpatched", line(real_warden(policy))))
    for label, clause in ARM_A_EMISSIONS:
        text = ("retract %s\nrule r_new1: cap:CAP_MUTATES_DURABLE_STATE when %s "
                "=> deny origin armorer:3" % (in_force, clause))
        payload = validator.validate_patch(parse_policy(text), policy)
        print("%-46s %s" % (label, line(real_warden(_wrap(payload, 2)))))
        # THE NULL-PATCH CHECK. `retract r_X` followed by a re-add of the same
        # body canonicalises to the same bytes and therefore to the same id, so
        # the rule SET is unchanged and the gate is being handed back the policy
        # it already holds. Printed rather than asserted: it is a finding.
        before = sorted(r["rule_id"] for r in policy["hashed_payload"]["rules"])
        after = sorted(r["rule_id"] for r in payload["rules"])
        if before == after:
            print("%-46s NULL PATCH - rule set unchanged: %s" % ("", after))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--samples", type=int, default=6)
    ap.add_argument("--arms", default="A,B")
    ap.add_argument("--out", default=None)
    ap.add_argument("--scratch", default=os.environ.get("PROBE_SCRATCH") or _HERE)
    args = ap.parse_args()

    autopsy = load_autopsy()
    validator, manifest_a, derived_b = build_validator()
    policy = build_round3_policy(validator)
    objective_set = resolve_objective_set()

    ebnf_b = arm_b_ebnf(args.scratch)

    if args.score:
        score(validator, policy)
        return

    if args.dry_run:
        for name, path in (("A", prompt_mod.POLICY_EBNF), ("B", ebnf_b)):
            projected = project(autopsy, objective_set=objective_set)
            from crucible.armorer.armorer import render_current
            with use_ebnf(path):
                text = prompt_mod.build_user_message(
                    projected_record=projected, manifest_a=manifest_a,
                    derived_schema_b=derived_b,
                    policy_text=render_current(policy), round_index=ROUND)
            out = os.path.join(args.scratch, "prompt.arm%s.txt" % name)
            with open(out, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            print("arm %s prompt -> %s  (%d chars)" % (name, out, len(text)))
        print("\n--- INVARIANT SECTION AS PROJECTED ---")
        print(json.dumps(project(autopsy, objective_set=objective_set)
                         .get("invariant"), indent=2, sort_keys=True))
        return

    if not args.live:
        raise SystemExit("pass --live (and GOOGLE_GENAI_USE_VERTEXAI=1, "
                         "GOOGLE_CLOUD_PROJECT), or --dry-run, or --score.")

    from crucible.armorer.client import make_call_model
    call_model = make_call_model()

    arms = []
    wanted = [a.strip().upper() for a in args.arms.split(",") if a.strip()]
    plan = {
        "A": ("A", prompt_mod.POLICY_EBNF, None),
        "B": ("B", ebnf_b, None),
        "C": ("C", ebnf_b, GUIDANCE_LINE),
    }
    for key in wanted:
        name, ebnf, extra = plan[key]
        print("=== ARM %s ===" % name, flush=True)
        arms.append(run_arm(name, ebnf, args.samples, autopsy, validator,
                            manifest_a, derived_b, policy, objective_set,
                            call_model, extra_rules=extra,
                            jsonl=os.path.join(args.scratch, "samples.jsonl")))

    total_usd = sum(s["usd"] for a in arms for s in a["samples"])
    doc = {
        "probe": "armorer-grouping-probe",
        "captured_at_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "model": ARMORER_MODEL,
        "thinking_level": ARMORER_THINKING_LEVEL,
        "bundle": os.path.relpath(BUNDLE, _REPO),
        "autopsy_id": autopsy["autopsy_id"],
        "round_index": ROUND,
        "samples_per_arm": args.samples,
        "total_usd": round(total_usd, 6),
        "arms": arms,
    }
    out = args.out or os.path.join(args.scratch, "probe-transcript.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=2, sort_keys=False)
        fh.write("\n")
    print("\ntranscript -> %s" % out)
    print("total usd  -> %.6f" % total_usd)
    for a in arms:
        from collections import Counter
        print("arm %s: %s" % (a["arm"],
                              dict(Counter(s["shape"] for s in a["samples"]))))


if __name__ == "__main__":
    main()
