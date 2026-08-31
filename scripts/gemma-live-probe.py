#!/usr/bin/env python3
"""ONE live Gemma call, for the camera. Read-only, no artifact written.

WHY THIS EXISTS. `gcp-proof.ps1` showed Gemma two ways: the pin in source, and
a live-run artifact from 2026-08-23 recording http 200. Both are true and
neither is a call happening now. On camera the difference matters - "here is
Gemma responding" and "here is a file that says Gemma responded" are different
sentences, and only one of them is what a saved JSON supports.

So this makes the call, now, through the SAME `make_completer` the Cartographer
uses. Not a reimplementation of it - the endpoint, the model id, the seed and
the temperature all come from `crucible.cartographer.vertex`, so what is on
screen is the path the project actually uses.

WHAT IT ASKS AND WHY IT IS TINY. One capability-classification question, which
is the Cartographer's actual job and the only claim this project makes about
Gemma. `ADR-0018` withdrew the claim that Gemma generated the attack corpus and
says that sentence "may not be written or spoken anywhere" - the corpus was
authored by lane agents. Classification, never generation.

`max_tokens` is small because a demo call does not need a long answer and this
is billed per token.

WHAT IT DOES NOT DO. It writes no artifact and it is not a measurement. The
stability measurement is `scripts/cartographer-stability.py`, which implements
a pre-registration requiring fifty calls in two arms with no early stopping -
running that for one camera frame would be interpreting a pre-registration
rather than executing it.

    python scripts/gemma-live-probe.py
"""
import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from crucible.cartographer import vertex


# ONE TOOL, INVENTED FOR THE DEMO. Not a tool on the frozen target - asking
# about a real one would put a capability_manifest answer on camera that nobody
# ratified, and the manifest is a hash-locked artifact.
PROMPT = """You classify a single tool into exactly one capability class.

Classes:
  CAP_MOVES_MONEY, CAP_EXTERNAL_COMMS, CAP_MUTATES_DURABLE_STATE,
  CAP_READS_PII, CAP_ESCALATES_PRIVILEGE, CAP_INVOKES_AGENT, UNCLASSIFIED

Tool:
  name: issue_refund
  description: credits a customer's original payment instrument for an order

Answer with the class name alone."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="crucible-hack-2026")
    ap.add_argument("--max-tokens", type=int, default=24)
    args = ap.parse_args()

    print("=" * 74)
    print("LIVE CALL - Gemma on Vertex AI Model Garden, managed endpoint")
    print("=" * 74)
    print("  model    : %s" % vertex.DEFAULT_MODEL_ID)
    print("  location : %s" % vertex.DEFAULT_LOCATION)
    print("  endpoint : %s" % vertex.endpoint_url(args.project,
                                                  vertex.DEFAULT_LOCATION))
    print("  asking   : classify one tool into one capability class")
    print()

    complete = vertex.make_completer(project=args.project,
                                     max_tokens=args.max_tokens)

    t0 = time.time()
    try:
        answer = complete(PROMPT)
    except Exception as exc:                      # noqa: BLE001 - reported, not swallowed
        # A FAILURE IS ALSO AN ANSWER AND IT GOES ON SCREEN. A probe that hid a
        # non-200 behind a traceback would be the one shape this project keeps
        # publishing findings about.
        print("  CALL FAILED: %s" % exc)
        return 1
    ms = (time.time() - t0) * 1000.0

    usage = getattr(complete, "last_usage", None)
    print("  http 200 in %d ms" % ms)
    print("  answer   : %s" % answer.strip())
    if usage:
        print("  usage    : %s" % json.dumps(usage))
    print()
    print("  This is the capability cartographer. It classifies tools.")
    print("  It does not author attacks - ADR-0018.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
