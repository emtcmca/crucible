"""run.py - the two things anyone actually wants to do with the Cartographer.

    python -m crucible.cartographer.run --print-prompt
        Offline. Loads the frozen foreign target, runs the deterministic
        pre-pass, prints the split and the exact prompt the residue would
        produce. No credential, no network, no spend.

    python -m crucible.cartographer.run --live --project crucible-hack-2026
        Sends that prompt to the managed Gemma endpoint, validates the answer,
        and writes an UNRATIFIED proposal set to --out. Costs money.

`--live` is a flag rather than the default on purpose. The offline path is the
one to run first, every time: it shows the split, and if the pre-pass resolved
everything there is nothing to ask a model and `--live` refuses to call one.
`gemma-scope.md` section 6 blesses that outcome explicitly - *"It is possible the
pre-pass resolves so much that the Cartographer is not worth building. That is a
real outcome and it should be allowed to happen."*

WHAT `--live` DOES NOT DO. It does not ratify, it does not write a manifest, and
the JSON it emits carries `"ratified": false` on the set and on every proposal
inside it. `ratify.py` is the only route onward and it needs a named human.

As of 2026-08-22 `--live` cannot succeed in `crucible-hack-2026`: the managed
Gemma model is not reachable from this project. See
`docs/proof/vertex-gemma-maas-probe-2026-08-22.txt` for the probe, the control
that proves the endpoint itself is good, and what enabling it would require.
"""

import argparse
import json

from .extract import load_frozen_target
from .gemma import Cartographer, build_prompt, split_residue


def _report_split(frozen, resolved, residue, stream=print):
    stream("target        %s" % frozen["target_name"])
    stream("commit_sha    %s" % frozen["commit_sha"])
    stream("fixture       %s tools, digest %s" % (frozen["tool_count"], frozen["digest"]))
    stream("pre-pass      %d resolved, %d residue" % (len(resolved), len(residue)))
    if resolved:
        stream("  resolved:   %s" % ", ".join(s["tool_name"] for s, _ in resolved))
    if residue:
        stream("  residue:    %s" % ", ".join(s["tool_name"] for s in residue))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", default="adk_customer_service",
                    help="name of a fixture in crucible/cartographer/foreign/")
    ap.add_argument("--print-prompt", action="store_true",
                    help="offline: print the split and the prompt, call nothing")
    ap.add_argument("--live", action="store_true",
                    help="call the managed Gemma endpoint. Costs money.")
    ap.add_argument("--project", help="GCP project for --live")
    ap.add_argument("--location", default=None)
    ap.add_argument("--model-id", default=None)
    ap.add_argument("--out", default=None, help="where to write the proposal set")
    args = ap.parse_args(argv)

    frozen = load_frozen_target(args.target)
    resolved, residue = split_residue(frozen["tools"])
    _report_split(frozen, resolved, residue)

    if not residue:
        print("\nNothing for a model to do. The deterministic pre-pass resolved "
              "every tool, which is a result, not a failure.")
        return 0

    if args.print_prompt or not args.live:
        print("\n" + "=" * 78)
        print(build_prompt(residue))
        if not args.live:
            print("\n(offline. add --live --project <id> to actually call a model)")
        return 0

    if not args.project:
        ap.error("--live needs --project")

    # Imported here, not at module scope, so the offline path never touches a
    # module whose whole job is spending money.
    from .vertex import DEFAULT_LOCATION, DEFAULT_MODEL_ID, make_completer

    model_id = args.model_id or DEFAULT_MODEL_ID
    complete = make_completer(project=args.project,
                              location=args.location or DEFAULT_LOCATION,
                              model_id=model_id)
    proposal_set = Cartographer(complete, model_id=model_id).propose(frozen["tools"])

    payload = json.loads(json.dumps(proposal_set, default=list))
    payload["target"] = {
        "name": frozen["target_name"],
        "repository": frozen["repository"],
        "commit_sha": frozen["commit_sha"],
        "fixture_digest": frozen["digest"],
    }
    out = args.out or "cartographer-proposals.json"
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("\nwrote %s - %d proposals, ratified: %s"
          % (out, len(payload["proposals"]), payload["ratified"]))
    print("Nothing here is in a manifest. ratify.py needs a named human first.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
