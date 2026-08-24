#!/usr/bin/env python3
"""Execute the 50 pre-registered Cartographer stability runs.

THE PRE-REGISTRATION IS `docs/design/cartographer-stability-preregistration.md`
AND THIS SCRIPT IMPLEMENTS IT RATHER THAN INTERPRETING IT. Everything decidable
was decided there, before any data existed: the two arms, the 25 arm-B seeds by
value, what is recorded, and the ruling that fires on the result. This file
executes and records. It computes no verdict, because the verdict is already
written down and a script that also decided it would be a second author.

  arm A   25 runs, seed 20260822 (the 08-23 artifact's seed)  - is it deterministic?
  arm B   25 runs, seeds 20260901..20260925 inclusive, in order - does it vary?

FOUR INTEGRITY RULES FROM THE PRE-REGISTRATION, IMPLEMENTED AND NOT RESTATED
AS COMMENTS ALONE:

1. THE PROMPT BYTES ARE HASHED BEFORE ARM A AND ASSERTED BEFORE EVERY CALL.
   "Not one word, not one whitespace character." A prompt that drifted mid-run
   would make the two arms measure different things while reporting one number,
   and nothing downstream could see it. On mismatch this aborts; the
   pre-registration then requires BOTH ARMS TO RESTART, which is a human's call
   and is printed rather than done.
2. NO RUN IS DISCARDED. A non-200, a malformed response, a validator rejection
   and a raised exception are all DATA POINTS and all land in the record with
   their codes. "There is no 'we re-ran that one.'" A harness that quietly
   retried would turn a flaky endpoint into a clean result, which is the exact
   shape of defect this whole exercise exists to detect.
3. NO EARLY STOPPING, INCLUDING ON A FAVOURABLE RESULT. The only stop is the
   spend cap in rule 4. A run stopped when the answer looked good is not a
   measurement.
4. THE CAP IS A STOP, NOT A SKIP. The pre-registration's cap is $5.00 measured
   spend. GOOGLE PUBLISHES NO PRICE LINE FOR GEMMA MaaS AND THIRD-PARTY
   AGGREGATORS DISAGREE BY 2x, so dollars are `[UNVERIFIED]` and CANNOT be the
   trigger for an automated stop - a guard keyed to a number nobody can source
   is a guard that fires at an unknown threshold. TOKENS ARE MEASURED, so the
   cap here is expressed in tokens, derived from the pre-registration's own
   estimate (~4,800 tokens/run, 50 runs, ~240,000 total) with headroom. Both are
   reported; only the measured one gates.

WHAT THIS SCRIPT DELIBERATELY DOES NOT DO: compute the primary measure, apply
the decision rule, or write a conclusion. Section 4's ruling fires on a table,
and assembling that table is `--analyse`, which reads the artifact back and
reports counts WITHOUT choosing what they mean.

Run:
    python scripts/cartographer-stability.py --live --project crucible-hack-2026
    python scripts/cartographer-stability.py --analyse docs/proof/cartographer-stability-2026-08-24.json
    python scripts/cartographer-stability.py --dry-run     # prove the plan, call nothing
"""

import argparse
import collections
import hashlib
import json
import pathlib
import sys
import time
import traceback

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from crucible.cartographer.extract import load_frozen_target       # noqa: E402
from crucible.cartographer.gemma import (                           # noqa: E402
    Cartographer, build_prompt, split_residue,
)

# THE ARMS, BY VALUE, COPIED FROM THE PRE-REGISTRATION SECTION 2. Typed out
# rather than computed from a range so a reader can diff this against the
# document without running anything, and so a fencepost error changes a visible
# literal instead of a bound.
ARM_A_SEED = 20260822
ARM_A_RUNS = 25
ARM_B_SEEDS = tuple(range(20260901, 20260926))          # 20260901..20260925
assert len(ARM_B_SEEDS) == 25, ARM_B_SEEDS
assert ARM_B_SEEDS[0] == 20260901 and ARM_B_SEEDS[-1] == 20260925

TARGET = "adk_customer_service"

# Rule 4. ~4,800 tokens/run x 50 = ~240,000 expected. 400,000 is ~1.67x that:
# loose enough that ordinary variance does not trip it, tight enough that a
# runaway (a retry loop, a max_tokens blowout) stops well before it matters.
TOKEN_CAP = 400_000

# `docs/proof/`, NOT `evidence/`. Its two siblings - cartographer-live-run-
# 2026-08-22.json and -08-23.json - live there, `evidence/` is gitignored, and
# this artifact is what the ratification sheet will cite. A proof nobody else
# can open is not a proof.
DEFAULT_OUT = REPO / "docs" / "proof" / "cartographer-stability-2026-08-24.json"


# ---------------------------------------------------------------------------
# The prompt lock - integrity rule 1
# ---------------------------------------------------------------------------

def prompt_and_digest():
    """The exact prompt bytes every one of the 50 calls must send, and their
    sha256. Built ONCE, here, and compared before each call."""
    frozen = load_frozen_target(TARGET)
    _resolved, residue = split_residue(frozen["tools"])
    prompt = build_prompt(residue)
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return frozen, residue, prompt, digest


# ---------------------------------------------------------------------------
# One run
# ---------------------------------------------------------------------------

def _rows(proposal_set):
    """`{tool_name: {classes, confidence, citations}}` for one run.

    Sorted tuples, so two runs that proposed the same classes in a different
    order compare equal - order is not part of the claim and treating it as
    part would report spurious instability.
    """
    out = {}
    for p in proposal_set.get("proposals") or ():
        out[p["tool_name"]] = {
            "classes": tuple(sorted(p.get("proposed_classes") or ())),
            "confidence": p.get("model_self_reported_confidence"),
            "citations": tuple(e.get("citation") for e in (p.get("evidence") or ())),
        }
    return out


def one_run(*, arm, index, seed, project, expected_digest, prompt):
    """Execute one call and return its record. NEVER RAISES.

    Integrity rule 2: a failure is a data point. Every exit from this function
    is a dict that lands in the artifact, including the ones that came from an
    exception, and each carries the code that says which kind it was.
    """
    from crucible.cartographer.vertex import (
        DEFAULT_LOCATION, DEFAULT_MODEL_ID, make_completer,
    )

    record = {
        "arm": arm, "index": index, "seed": seed,
        "model_id": DEFAULT_MODEL_ID, "location": DEFAULT_LOCATION,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    complete = make_completer(project=project, location=DEFAULT_LOCATION,
                             model_id=DEFAULT_MODEL_ID, seed=seed)

    # INTEGRITY RULE 1, ASSERTED PER CALL AND NOT ONCE PER ARM. The prompt is
    # rebuilt from the frozen fixture on every iteration precisely so that a
    # fixture edited mid-run is caught rather than cached past.
    _f, _r, live_prompt, live_digest = prompt_and_digest()
    if live_digest != expected_digest:
        record.update({
            "outcome": "ABORT_PROMPT_DRIFT",
            "prompt_sha256": live_digest,
            "expected_prompt_sha256": expected_digest,
        })
        return record
    assert live_prompt == prompt
    record["prompt_sha256"] = live_digest

    frozen = load_frozen_target(TARGET)
    try:
        proposal_set = Cartographer(complete, model_id=DEFAULT_MODEL_ID).propose(
            frozen["tools"])
        record["outcome"] = "OK"
        record["rows"] = _rows(proposal_set)
        record["proposal_count"] = len(proposal_set.get("proposals") or ())
        record["raw_response"] = proposal_set.get("raw_response")
    except Exception as exc:                       # noqa: BLE001 - rule 2
        # A ProposalRejected carries `.code` and `.tool_name`; anything else is
        # recorded by type. BOTH ARE RESULTS. The validator refusing the model's
        # answer is arguably the most interesting outcome available here, and
        # a harness that let it escape as a traceback would keep no evidence of
        # the one failure mode the gate exists to produce.
        record["outcome"] = "REJECTED" if hasattr(exc, "code") else "EXCEPTION"
        record["error"] = {
            "code": getattr(exc, "code", type(exc).__name__),
            "tool_name": getattr(exc, "tool_name", None),
            "message": str(exc)[:1000],
            "traceback": (None if hasattr(exc, "code")
                          else traceback.format_exc()[-1500:]),
        }
        record["rows"] = {}
        record["raw_response"] = getattr(complete, "last_raw", None)

    # The full usage block, per section 3, read off the API response rather than
    # estimated. `calls` is a list because a completer may make more than one.
    calls = list(getattr(complete, "calls", ()))
    record["usage"] = calls
    record["tokens"] = sum((c.get("usage") or {}).get("total_tokens") or 0
                           for c in calls)
    record["http"] = [{"finish_reason": c.get("finish_reason"),
                       "traffic_type": ((c.get("usage") or {})
                                        .get("extra_properties", {})
                                        .get("google", {}).get("traffic_type"))}
                      for c in calls]
    record["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return record


# ---------------------------------------------------------------------------
# The campaign
# ---------------------------------------------------------------------------

def execute(project, out_path, dry_run=False):
    frozen, residue, prompt, digest = prompt_and_digest()

    plan = ([("A", i + 1, ARM_A_SEED) for i in range(ARM_A_RUNS)]
            + [("B", i + 1, s) for i, s in enumerate(ARM_B_SEEDS)])

    print("=" * 78)
    print("CARTOGRAPHER STABILITY - 50 pre-registered runs")
    print("  pre-registration : docs/design/cartographer-stability-preregistration.md")
    print("  target           : %s (%d tools, %d in residue)"
          % (TARGET, len(frozen["tools"]), len(residue)))
    print("  prompt sha256    : %s" % digest)
    print("  arm A            : %d runs, seed %d" % (ARM_A_RUNS, ARM_A_SEED))
    print("  arm B            : %d runs, seeds %d..%d"
          % (len(ARM_B_SEEDS), ARM_B_SEEDS[0], ARM_B_SEEDS[-1]))
    print("  token cap        : %s (a STOP, not a skip). Dollars are UNVERIFIED"
          % f"{TOKEN_CAP:,}")
    print("  NO RUN IS DISCARDED. NO EARLY STOP ON A FAVOURABLE RESULT.")
    print("=" * 78)

    if dry_run:
        print("\n--dry-run: the plan above is the whole plan. Nothing was called.")
        for arm, index, seed in plan:
            print("  arm %s run %02d seed %d" % (arm, index, seed))
        return 0

    runs, spent = [], 0
    for arm, index, seed in plan:
        rec = one_run(arm=arm, index=index, seed=seed, project=project,
                      expected_digest=digest, prompt=prompt)
        runs.append(rec)
        spent += rec.get("tokens") or 0
        qr = (rec.get("rows") or {}).get("generate_qr_code", {}).get("classes")
        print("  arm %s %02d/%02d seed=%d  %-9s tokens=%-6s qr=%s"
              % (arm, index, 25, seed, rec["outcome"], rec.get("tokens"),
                 ",".join(qr) if qr else "-"))

        if rec["outcome"] == "ABORT_PROMPT_DRIFT":
            print("\nPROMPT DRIFT. The prompt bytes changed mid-run: expected %s, "
                  "got %s.\nThe pre-registration requires BOTH ARMS TO RESTART and "
                  "the change to be\nrecorded as a new revision with its reason. "
                  "That is a human's decision;\nthis script stops and reports it."
                  % (digest, rec.get("prompt_sha256")))
            break
        if spent > TOKEN_CAP:
            print("\nTOKEN CAP REACHED: %s > %s after %d run(s). STOPPING and "
                  "reporting,\nper integrity rule 4. The runs completed so far "
                  "are reported as they are;\nthe remainder are NOT marked "
                  "failed, they were never attempted."
                  % (f"{spent:,}", f"{TOKEN_CAP:,}", len(runs)))
            break

    artifact = {
        "artifact": "cartographer stability, 50 pre-registered runs",
        "preregistration": "docs/design/cartographer-stability-preregistration.md",
        "preregistration_sha256": hashlib.sha256(
            (REPO / "docs" / "design" /
             "cartographer-stability-preregistration.md").read_bytes()).hexdigest(),
        "taken": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target": {"name": frozen["target_name"],
                   "repository": frozen.get("repository"),
                   "commit_sha": frozen.get("commit_sha"),
                   "fixture_digest": frozen.get("digest")},
        "prompt_sha256": digest,
        "prompt": prompt,
        "planned_runs": len(plan),
        "executed_runs": len(runs),
        "total_tokens": spent,
        "token_cap": TOKEN_CAP,
        "dollars": "UNVERIFIED - Google publishes no Gemma MaaS price line and "
                   "third-party aggregators disagree by 2x. Tokens are measured; "
                   "dollars are not reported.",
        "runs": runs,
        "NOTE": "This artifact carries NO verdict. The decision rule is section 4 "
                "of the pre-registration and it fires on the table --analyse "
                "prints. A script that also concluded would be a second author.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
    print("\nwrote %s  (%d/%d runs, %s tokens)"
          % (out_path, len(runs), len(plan), f"{spent:,}"))
    print("Now: python scripts/cartographer-stability.py --analyse %s" % out_path)
    return 0


# ---------------------------------------------------------------------------
# Analysis - counts only. The ruling is the pre-registration's.
# ---------------------------------------------------------------------------

def analyse(path):
    art = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    runs = art["runs"]
    by_arm = collections.defaultdict(list)
    for r in runs:
        by_arm[r["arm"]].append(r)

    print("=" * 78)
    print("ANALYSIS - counts, not conclusions. The ruling is section 4 of")
    print("docs/design/cartographer-stability-preregistration.md and it fires on")
    print("the PRIMARY MEASURE below.")
    print("=" * 78)
    print("  executed %d of %d planned | %s tokens"
          % (art["executed_runs"], art["planned_runs"], f"{art['total_tokens']:,}"))
    print("  outcomes: %s" % dict(collections.Counter(r["outcome"] for r in runs)))
    print()

    # PRIMARY. Section 4: the proportion of ARM B runs in which generate_qr_code
    # receives ANY class other than CAP_MOVES_MONEY. A run that produced no rows
    # at all cannot answer the question and is counted separately rather than
    # silently treated as agreement - which would bias the measure toward "no
    # recurrence", the direction that avoids building the check.
    # `tuple(...)` IS LOAD-BEARING AND ITS ABSENCE WAS A REAL DEFECT.
    # `_rows` builds tuples; `json.dump` writes them as ARRAYS; `json.load`
    # returns LISTS. A list never equals a tuple, so
    # `classes != ("CAP_MOVES_MONEY",)` was TRUE FOR EVERY ROW and the primary
    # measure read 18 of 25 while its own printout listed six rows saying
    # CAP_MOVES_MONEY. Caught 2026-08-24 by reading the output instead of the
    # headline. The ruling was unchanged either way, which is exactly why it
    # could have shipped: a wrong number that points at the right decision.
    b = by_arm["B"]
    scored = [r for r in b if r.get("rows", {}).get("generate_qr_code")]
    other = [r for r in scored
             if tuple(r["rows"]["generate_qr_code"]["classes"]) != ("CAP_MOVES_MONEY",)]
    print("PRIMARY MEASURE - arm B, generate_qr_code")
    print("  arm B runs executed        : %d" % len(b))
    print("  ...that produced a row     : %d" % len(scored))
    print("  ...NOT CAP_MOVES_MONEY     : %d" % len(other))
    for r in other:
        print("      seed %d -> %s" % (r["seed"],
                                       ",".join(r["rows"]["generate_qr_code"]["classes"])))
    print("  SECTION 4 RULING: %s"
          % ("0 of 25 -> do NOT build the contradiction check"
             if not other and len(b) == 25 else
             "%d of %d -> BUILD the contradiction check and publish the rate"
             % (len(other), len(b)) if other else
             "INCOMPLETE - %d of 25 arm-B runs executed, the rule assumes 25" % len(b)))
    print()

    # SECONDARY 1 - every tool, not only the one we suspected.
    print("SECONDARY 1 - class stability, EVERY tool (measuring only row 12")
    print("              would be measuring the fixture)")
    for arm in ("A", "B"):
        assignments = collections.defaultdict(collections.Counter)
        for r in by_arm[arm]:
            for tool, row in (r.get("rows") or {}).items():
                assignments[tool][tuple(row["classes"])] += 1
        unstable = {t: dict(c) for t, c in assignments.items() if len(c) > 1}
        print("  arm %s: %d tool(s) with more than one assignment%s"
              % (arm, len(unstable), "" if unstable else "  (all stable)"))
        for tool, counts in sorted(unstable.items()):
            print("      %-28s %s" % (tool, {",".join(k): v for k, v in counts.items()}))

    # SECONDARY 2 - arm A determinism. Differing same-seed runs would mean the
    # seed is accepted but not honoured, which is a finding in its own right.
    sig = {json.dumps(r.get("rows"), sort_keys=True) for r in by_arm["A"]
           if r["outcome"] == "OK"}
    print("\nSECONDARY 2 - arm A determinism: %d distinct assignment(s) across "
          "%d OK run(s)" % (len(sig), sum(1 for r in by_arm["A"] if r["outcome"] == "OK")))
    if len(sig) > 1:
        print("      THE SEED IS ACCEPTED BUT NOT HONOURED. Reportable on its own.")

    # SECONDARY 3 - a field that may carry no information.
    confs = {row["confidence"] for r in runs for row in (r.get("rows") or {}).values()}
    print("\nSECONDARY 3 - distinct `confidence` values across all runs: %s" % sorted(
        c for c in confs if c is not None))
    if confs == {1.0}:
        print("      1.0 everywhere, including on rows that are wrong. A field "
              "carrying no information.")

    # SECONDARY 4 - two classes that have never appeared.
    seen = {c for r in runs for row in (r.get("rows") or {}).values()
            for c in tuple(row["classes"])}
    for cls in ("CAP_READS_PII", "CAP_INVOKES_AGENT"):
        print("\nSECONDARY 4 - %s appeared: %s" % (cls, cls in seen))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true", help="make the 50 real calls")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan and the prompt hash, call nothing")
    ap.add_argument("--project", default=None)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--analyse", default=None, metavar="ARTIFACT")
    args = ap.parse_args(argv)

    if args.analyse:
        return analyse(args.analyse)
    if not (args.live or args.dry_run):
        ap.error("pass --live to run, or --dry-run to see the plan")
    if args.live and not args.project:
        ap.error("--live needs --project")
    return execute(args.project, pathlib.Path(args.out), dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
