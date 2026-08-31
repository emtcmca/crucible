#!/usr/bin/env python3
"""Build `cards/10-agent.html` - the N1/N2 beat, from the committed demo fixtures.

WHAT THIS IS, STATED PRECISELY, BECAUSE THE DISTINCTION MATTERS ON CAMERA.
`target/refund_agent/demo/D*.json` are SCENARIO FIXTURES: the turns, the tool
calls and the postconditions the target agent is expected to produce, committed
2026-08-20 and frozen with the agent. They are not a transcript of a live
session, and this view labels itself as the scenario rather than implying one.

The card names the fixture id on screen for that reason. If the beat is shot
live instead - which is better, and the shot list says so - this becomes the
fallback rather than the take.

WHY THE LEDGER ROW IS THE PAYOFF. The fixture's own `why_this_one` says it:
"the postcondition asserted on camera is a LEDGER ROW, not an HTTP 200 and not
a transcript line. A tool's success message is not evidence (CONVENTIONS
section 8 rule 1); the row is." So the last thing that lands is the row.

    python tools/capture/build-agent-view.py --fixture D1-cold-open
    python tools/capture/build-agent-view.py --fixture D2-escalation --out cards/11-agent-escalation.html
"""
import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", default="D1-cold-open")
    ap.add_argument("--out", default=str(HERE / "cards" / "10-agent.html"))
    args = ap.parse_args()

    src = ROOT / "target" / "refund_agent" / "demo" / (args.fixture + ".json")
    if not src.exists():
        sys.exit("no such fixture: %s" % src)
    d = json.loads(src.read_text(encoding="utf-8"))

    turns = []
    for t in d["turns"]:
        sp = t.get("speaker")
        if sp == "tool_call":
            turns.append({
                "kind": "tool",
                "tool": t.get("tool"),
                "args": t.get("args") or {},
                "satisfies": t.get("satisfies", ""),
            })
        else:
            turns.append({"kind": sp, "text": t.get("text", "")})

    post = d.get("postconditions") or {}
    payload = {
        "demo_id": d.get("demo_id"),
        "title": d.get("title"),
        "order": d.get("scenario_order_id"),
        "outcome": d.get("expected_outcome"),
        "breach": d.get("breach_expectation"),
        "turns": turns,
        "post": [{"k": k, "v": post[k]} for k in sorted(post)],
        "source": "target/refund_agent/demo/%s.json" % args.fixture,
    }

    tpl = (HERE / "agent-view.template.html").read_text(encoding="utf-8")
    out = pathlib.Path(args.out)
    out.write_text(tpl.replace("/*__DATA__*/null",
                               json.dumps(payload, indent=1)),
                   encoding="utf-8", newline="")
    print("wrote %s" % out)
    print("  %s - %s - %d turns, %d postconditions"
          % (payload["demo_id"], payload["title"], len(turns), len(payload["post"])))


if __name__ == "__main__":
    main()
