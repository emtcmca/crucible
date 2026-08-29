#!/usr/bin/env python
"""Turn the ratifier's twelve rulings into a ratified foreign capability manifest.

WHAT THIS IS. `docs/proof/cartographer-adk-ratification.md` is the review
contract, and it was UNSIGNED: twelve Cartographer proposals with no human
verdict, so no manifest could be produced from them. On 2026-08-28 Eric Tetzlaff
ruled on all twelve. This script transcribes those rulings, runs them through
`crucible.cartographer.ratify` - the ONE route from a proposal to a manifest
entry - and writes the ratified manifest plus the machine-readable record.

WHY A SCRIPT AND NOT A HAND-EDITED JSON. `ratify.py` refuses a manifest whose
digests do not bind, and hand-writing the output would route around exactly the
gate this artifact exists to pass. The rulings below are DATA transcribed from
the signed sheet; every check is done by the library.

WHAT IT DOES NOT DO. It does not classify anything. Four rows carry a class set
the model never proposed, and each is stamped `classified_by: human` by the
library, not by this file.

    python scripts/ratify-foreign-manifest.py            # write the artifacts
    python scripts/ratify-foreign-manifest.py --check    # verify, write nothing
"""

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from crucible.cartographer.ratify import (            # noqa: E402
    RatificationError,
    build_ratification,
    decisions_digest,
    proposal_set_digest,
    to_manifest_entries,
)
from crucible.manifest import load_part_a             # noqa: E402

LIVE_RUN = "docs/proof/cartographer-live-run-2026-08-23.json"
FROZEN = "crucible/cartographer/foreign/adk_customer_service.json"
SHEET = "docs/proof/cartographer-adk-ratification.md"

RECORD_OUT = "docs/proof/cartographer-adk-ratification-record-2026-08-28.json"
MANIFEST_OUT = "docs/proof/foreign-manifest-adk-customer-service-ratified-2026-08-28.json"

RATIFIED_BY = "Eric Tetzlaff"
RATIFIED_ON = "2026-08-28"

# The digest the UNSIGNED sheet recorded, before any verdict existed. Asserted,
# never trusted: if the proposals moved since the sheet was written, the review
# was of a different document and this script must stop.
SHEET_PROPOSAL_DIGEST = (
    "24a0a3fb354e1c5fc37f53f8fc1a85f701e250f8903aa8283b2c1f1f88f2295c")

# ---------------------------------------------------------------------------
# THE RULINGS. Transcribed from the signed sheet, 2026-08-28. Eight accept,
# four amend, no rejections.
# ---------------------------------------------------------------------------
DECISIONS = {
    # ---- amended: the reviewer supplied a class set the model did not ----
    "access_cart_information": {
        "decision": "amend",
        "classes": ["CAP_READS_PII"],
        "reason": (
            "Proposed UNCLASSIFIED with no evidence, and UNCLASSIFIED cannot be "
            "accepted: manifest/load.py refuses it by name as a sentinel for an "
            "unclassified CALL. An identifier-shaped arg returning a customer's "
            "record is the stated deterministic signal for CAP_READS_PII "
            "(architecture-spec.md 4.1). DISSENT RECORDED: "
            "third-party-target-recon-2026-08-22.md proposed INERT, reasoning "
            "that the mock's returned cart holds product rows and a subtotal "
            "with no personal data. That is an OBSERVED-EFFECT argument, and "
            "this sheet classifies DECLARED CAPABILITY of the tool surface, "
            "under which reading a named customer's cart is a PII read. The "
            "classifier itself reached CAP_READS_PII once in 36 stability runs."),
    },
    "approve_discount": {
        "decision": "amend",
        "classes": ["CAP_MOVES_MONEY", "CAP_ESCALATES_PRIVILEGE"],
        "reason": (
            "CAP_MOVES_MONEY stands and is unanimous at 36/36. Adding "
            "CAP_ESCALATES_PRIVILEGE because the class means 'GRANTS, elevates, "
            "or bypasses an authorization check' and approving a discount is "
            "granting one. The narrower reading of escalation as routing upward "
            "is the pre-pass SIGNAL description, not the class definition."),
    },
    "sync_ask_for_approval": {
        "decision": "amend",
        "classes": ["CAP_MOVES_MONEY", "CAP_ESCALATES_PRIVILEGE"],
        "reason": (
            "CAP_ESCALATES_PRIVILEGE stands, unanimous at 36/36, and it is the "
            "class the portability demo's rule r_00332742f13f binds to. Adding "
            "CAP_MOVES_MONEY: identical signature to approve_discount, same "
            "float value, same domain. The classifier split the two on the "
            "docstring verb rather than on capability. Membership matching "
            "means the added class cannot unbind the existing rule."),
    },
    "generate_qr_code": {
        "decision": "amend",
        "classes": ["CAP_MOVES_MONEY"],
        "reason": (
            "Proposed INERT, a positive claim of no capability, over a tool that "
            "takes a float discount_value and mints an instrument redeeming it. "
            "The 2026-08-22 run and the prior hand reading both said "
            "CAP_MOVES_MONEY. Stability run: INERT 28/36, CAP_MOVES_MONEY 8/36, "
            "so this is a human override of a classifier stable on the wrong "
            "answer, not the correction of a one-off. Under-calling capability "
            "is the dangerous direction: a missing class is a rule that never "
            "binds. Not CAP_EXTERNAL_COMMS - it returns the code to the caller "
            "rather than sending it."),
    },
    # ---- accepted: the proposed class set stands ----
    "send_call_companion_link": {
        "decision": "accept",
        "reason": "Emits a link to a supplied phone number outside the boundary. 36/36.",
    },
    "update_salesforce_crm": {
        "decision": "accept",
        "reason": (
            "Non-idempotent write to external durable state. 36/36. NOT amended "
            "to add CAP_READS_PII: the class means 'RETURNS personal data about "
            "an identified natural person' and this returns a status. FINDING "
            "RECORDED, not resolved here: the six classes have no encoding for "
            "a tool that WRITES a named person's record, so a cross-customer "
            "write is unpoliceable where a cross-customer read is not."),
    },
    "modify_cart": {
        "decision": "accept",
        "reason": "Non-idempotent verb over session-outliving cart state. 36/36.",
    },
    "schedule_planting_service": {
        "decision": "accept",
        "reason": "Creates a durable appointment. 36/36.",
    },
    "send_care_instructions": {
        "decision": "accept",
        "reason": (
            "Email or SMS to a customer, outside the boundary. 36/36. An earlier "
            "draft of this review proposed adding CAP_READS_PII on the strength "
            "of prepass.py pairing an email destination with both classes. "
            "WITHDRAWN: that pairing is a pre-pass signal heuristic, and the "
            "class definition requires the tool RETURN personal data. This "
            "returns a status dictionary."),
    },
    "get_product_recommendations": {
        "decision": "accept",
        "reason": (
            "INERT, resolving to the empty capability set. Flagged during review "
            "as the marginal one of the three inert rows because it accepts a "
            "customer_id, then accepted: it returns catalog rows rather than a "
            "customer record, and the classifier is unanimous at 36/36."),
    },
    "check_product_availability": {
        "decision": "accept",
        "reason": "INERT. Inventory lookup over product and store ids, no personal record. 36/36.",
    },
    "get_available_planting_times": {
        "decision": "accept",
        "reason": "INERT. Takes a date, returns time ranges. No identifier, no mutation. 36/36.",
    },
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify and report, write nothing")
    args = ap.parse_args()

    live = json.loads((ROOT / LIVE_RUN).read_text(encoding="utf-8"))
    frozen = json.loads((ROOT / FROZEN).read_text(encoding="utf-8"))
    proposals = live["proposals"]

    # 1. The proposals must be the ones the sheet was written against.
    got = proposal_set_digest(proposals)
    if got != SHEET_PROPOSAL_DIGEST:
        print("REFUSED E_SHEET_DIGEST_MOVED")
        print("  sheet recorded %s" % SHEET_PROPOSAL_DIGEST)
        print("  proposals hash %s" % got)
        print("  The review on %s was of a different proposal set." % SHEET)
        return 2
    print("proposal set        binds to the sheet")

    # 2. Build the record. The library refuses a component name, an unreviewed
    #    tool, a decision for an unproposed tool, and an out-of-vocabulary class.
    try:
        record = build_ratification(
            ratified_by=RATIFIED_BY, ratified_on=RATIFIED_ON,
            proposals=proposals, decisions=DECISIONS,
            notes=("Twelve rulings, 2026-08-28. Eight accept, four amend, no "
                   "rejections. Full reasoning per tool in the decisions map; "
                   "the accept/amend split and two recorded dissents are in the "
                   "reason fields, not summarised away."))
    except RatificationError as e:
        print("REFUSED %s" % e)
        return 2
    print("ratification        built, %d decisions" % len(record["decisions"]))

    # 3. The one route from proposals to manifest entries.
    try:
        entries = to_manifest_entries({"proposals": proposals,
                                       "model_id": live.get("endpoint", {}).get("model")},
                                      record)
    except RatificationError as e:
        print("REFUSED %s" % e)
        return 2

    # 4. Shape them into Part A. tool_handle/fqname/arg_paths come from the
    #    frozen fixture, never retyped.
    by_name = {t["tool_name"]: t for t in frozen["tools"]}
    tools = []
    for e in entries:
        spec = by_name[e["tool_name"]]
        tools.append({
            "tool_handle": "tool:f_%s" % e["tool_name"],
            "tool_fqname": "customer_service.tools.tools.%s" % e["tool_name"],
            "capability_classes": list(e["capability_classes"]),
            # As produced by the library: `human` where the reviewer supplied
            # the answer, `cartographer` where the proposal stood. Preserved
            # because it records WHO produced the answer that shipped.
            "classified_by": e["classified_by"],
            "human_confirmed": True,
            # No row is fail_closed now: every one carries a precise set, and an
            # empty set is a positive claim of no capability, not an unknown.
            "fail_closed": False,
            "arg_paths": sorted(a["name"] for a in spec.get("args") or ()),
            "ratified_by": e["ratified_by"],
            "ratified_on": e["ratified_on"],
        })

    manifest = {
        "manifest_version": 1,
        "target_id": "tgt_foreign_adk_customer_service",
        "_RATIFIED": (
            "Ratified by %s on %s against proposal-set digest recorded in %s. "
            "Produced ONLY by ratify.to_manifest_entries(); no value here was "
            "hand-written." % (RATIFIED_BY, RATIFIED_ON, SHEET)),
        "_source_commit": frozen["commit_sha"],
        "tools": sorted(tools, key=lambda t: t["tool_handle"]),
    }

    amended = [t["tool_handle"] for t in tools if t["classified_by"] == "human"]
    inert = [t["tool_handle"] for t in tools if not t["capability_classes"]]

    if args.check:
        print("check only, nothing written")
    else:
        # newline="" so Python does not translate \n to \r\n on Windows. The repo
        # stores LF; without this the artifacts land CRLF and every line reads as
        # changed, which buries a real edit in a whole-file rewrite.
        (ROOT / RECORD_OUT).write_text(
            json.dumps(record, indent=1, sort_keys=True) + "\n",
            encoding="utf-8", newline="")
        (ROOT / MANIFEST_OUT).write_text(
            json.dumps(manifest, indent=1) + "\n",
            encoding="utf-8", newline="")

    # 5. Validate through the PRODUCTION loader, and read the hash off the file
    #    that was actually written rather than the object in memory.
    if not args.check:
        m, manifest_hash = load_part_a(ROOT / MANIFEST_OUT)
        print("manifest            validates through load_part_a, %d tools" % len(m["tools"]))
        print("manifest_hash       %s   (computed at use time, never typed)" % manifest_hash)
        print("record              %s" % RECORD_OUT)
        print("manifest            %s" % MANIFEST_OUT)

    print("decisions_digest    %s" % decisions_digest(record["decisions"])[:32])
    print("amended (human)     %d  %s" % (len(amended), ", ".join(amended)))
    print("inert (empty set)   %d  %s" % (len(inert), ", ".join(inert)))
    print("capability-bearing  %d of %d" % (len(tools) - len(inert), len(tools)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
