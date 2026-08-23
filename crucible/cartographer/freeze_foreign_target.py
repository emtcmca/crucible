"""freeze_foreign_target.py - regenerate the committed foreign-target fixture.

Run this, do not hand-edit `foreign/adk_customer_service.json`. The fixture is
the input to every Cartographer test, and a test suite whose fixture was typed by
hand is measuring the typist.

    python -m crucible.cartographer.freeze_foreign_target \\
        --clone C:\\dev\\_sandbox\\adk-samples \\
        --sha   629310b7b845398841c814456289a34fbc766acf

The clone must already exist on disk, OUTSIDE this repository (the L6 lane
contract, `third-party-target-recon-2026-08-22.md` section 7: nothing
third-party is ever staged into ours). This script reads it and writes one file
inside `crucible/cartographer/foreign/`. It fetches nothing and it verifies no
SHA - `git rev-parse` in the clone is the caller's job, and its output belongs in
the decision document beside the fixture.

WHY THE TOOL LIST IS TYPED HERE AND THE SIGNATURES ARE NOT.

`TOOL_NAMES` mirrors the sample's own registry at `customer_service/agent.py`
`tools=[...]`, which is the only place that says which functions are tools. That
list is twelve names and nothing else - no types, no arguments, no docs. Every
piece of data a classification could rest on is read from source. If upstream
adds a thirteenth tool this list goes stale, which is why
`tests/test_cartographer_gemma.py` asserts the count rather than trusting it.
"""

import argparse
import datetime
import json
import os

from .extract import extract_tool_specs, freeze_target

TARGET_NAME = "adk-samples/python/agents/customer-service"
REPOSITORY = "https://github.com/google/adk-samples"
DECLARING_AGENT = "customer_service_agent"
REL_TOOLS_PATH = "python/agents/customer-service/customer_service/tools/tools.py"
REL_AGENT_PATH = "python/agents/customer-service/customer_service/agent.py"

# Mirrors `agent.py` tools=[...] exactly, in registration order.
TOOL_NAMES = (
    "send_call_companion_link",
    "approve_discount",
    "sync_ask_for_approval",
    "update_salesforce_crm",
    "access_cart_information",
    "modify_cart",
    "get_product_recommendations",
    "check_product_availability",
    "schedule_planting_service",
    "get_available_planting_times",
    "send_care_instructions",
    "generate_qr_code",
)

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "foreign",
                            "adk_customer_service.json")

NOTES = (
    "Tool names mirror the registry at %s (tools=[...]). Signatures, argument "
    "names, annotations and per-argument documentation are read from %s by "
    "inspect - none of it is typed. Regenerate with "
    "`python -m crucible.cartographer.freeze_foreign_target`." % (REL_AGENT_PATH, REL_TOOLS_PATH)
)


def build(clone_root: str, commit_sha: str) -> dict:
    module_path = os.path.join(clone_root, *REL_TOOLS_PATH.split("/"))
    specs = extract_tool_specs(
        module_path,
        TOOL_NAMES,
        declaring_agent=DECLARING_AGENT,
        source_rel_path=REL_TOOLS_PATH,
    )
    return freeze_target(
        target_name=TARGET_NAME,
        repository=REPOSITORY,
        commit_sha=commit_sha,
        specs=specs,
        extracted_on=datetime.date.today().isoformat(),
        notes=NOTES,
    )


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--clone", required=True,
                    help="path to an existing google/adk-samples clone, outside this repo")
    ap.add_argument("--sha", required=True,
                    help="full 40-char SHA you verified with `git rev-parse` in that clone")
    ap.add_argument("--out", default=FIXTURE_PATH)
    args = ap.parse_args(argv)

    frozen = build(args.clone, args.sha)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(frozen, fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")
    print("wrote %s" % args.out)
    print("tool_count %d" % frozen["tool_count"])
    print("digest     %s" % frozen["digest"])
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
