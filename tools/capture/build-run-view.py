#!/usr/bin/env python3
"""Build `cards/03-run.html` from a REAL run bundle.

WHY A GENERATOR AND NOT A LIVE PAGE. The page has to work over `file://` with no
server and no fetch - the same constraint `loop-player.html` documents and for
the same reason: a capture run that needs a web server is a capture run that
fails at 2am. So the data is inlined at build time.

WHAT IT PUTS ON SCREEN, AND WHERE EVERY FIELD COMES FROM. Nothing here is
composed, styled-up or rounded. Every value is read out of the bundle and the
generator refuses if a field it needs is absent, because a viewer that silently
renders a blank where a fact should be is a viewer that can show a run that did
not happen.

  header      run_manifest.run_id, execution_provenance.mode, the project and
              region from scripts/gcp-env.sh, and the deployed Cloud Run
              revision passed in with --revision
  models      episodes[].model_provenance, deduplicated by role - so the model
              ids on screen are the ones the episodes actually ran on, not a
              roster copied from a document
  stream      one row per episode: round, attack id, the tripwire verdict, and
              the policy version in force
  gate        gate_decisions[]: the decision, the benign floor as passed/total,
              and G4's newly-blocked and newly-breached counts
  locks       run_manifest.hash_locks, shown as names and short values

Usage:
    python tools/capture/build-run-view.py \
        --bundle evidence/batch-measure-2026-08-27/run-01.c6.json \
        --revision crucible-00004-gfk
"""
import argparse
import html
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def need(d, *path):
    """Fetch a nested field or die naming it. A viewer that renders a blank
    where a fact belongs can show a run that did not happen."""
    cur = d
    for k in path:
        if isinstance(cur, list):
            cur = cur[k]
        elif k in cur:
            cur = cur[k]
        else:
            sys.exit("bundle has no %s" % ".".join(str(x) for x in path))
    return cur


def gcp_env():
    """project and region from scripts/gcp-env.sh - the single source. Never
    retyped here; `docs/CLAUDE.md` calls a second copy of these a second source
    of truth and G7/G8 grep the literals."""
    out = subprocess.run(
        ["bash", "-c", "set -a; . scripts/gcp-env.sh; "
                       "echo \"$CRUCIBLE_PROJECT|$CRUCIBLE_REGION\""],
        cwd=str(ROOT), capture_output=True, text=True)
    if out.returncode != 0 or "|" not in out.stdout:
        sys.exit("could not source scripts/gcp-env.sh: %s" % out.stderr.strip())
    project, region = out.stdout.strip().split("|", 1)
    return project, (region or "us-central1")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", required=True)
    ap.add_argument("--revision", default="",
                    help="the serving Cloud Run revision, read from "
                         "`gcloud run services describe`. Left blank if you "
                         "would rather not put one on screen.")
    ap.add_argument("--out", default=str(pathlib.Path(__file__).parent
                                         / "cards" / "03-run.html"))
    args = ap.parse_args()

    b = json.loads(pathlib.Path(args.bundle).read_text(encoding="utf-8"))
    project, region = gcp_env()

    run_id = need(b, "run_manifest", "run_id")
    mode = need(b, "execution_provenance", "mode")
    locks = need(b, "run_manifest", "hash_locks")
    episodes = need(b, "episodes")
    gates = need(b, "gate_decisions")
    chain = need(b, "policy_chain")

    # MODELS AS THE EPISODES RAN THEM. Deduplicated by role, in first-seen
    # order. A roster lifted from a document would be a claim about
    # configuration; this is a record of execution.
    models, seen = [], set()
    for e in episodes:
        mp = e.get("model_provenance") or {}
        role = mp.get("role")
        if role and role not in seen:
            seen.add(role)
            models.append({"role": role, "model_id": mp.get("model_id"),
                           "provider": mp.get("provider"),
                           "endpoint": mp.get("endpoint")})

    stream = []
    for e in episodes:
        v = e.get("verdict") or {}
        stream.append({
            "round": e.get("round_index"),
            "attack": (e.get("attack_id") or "")[:22],
            "breach": bool(v.get("breach")),
            "fault": bool(v.get("target_fault")),
            "verdict": v.get("verdict", "?"),
            "pv": e.get("policy_version"),
        })

    gate_rows = []
    for g in gates:
        c = g.get("criteria") or {}
        bf = c.get("benign_floor") or {}
        ar = c.get("attack_reduction") or {}
        gate_rows.append({
            "round": g.get("round_index"),
            "decision": g.get("decision"),
            "benign": "%s/%s" % (bf.get("passed"), bf.get("total")),
            "b": ar.get("newly_blocked_b"),
            "c": ar.get("newly_breached_c"),
            "mode": ar.get("mode"),
        })

    final = chain[-1]
    payload = {
        "run_id": run_id, "mode": mode, "project": project, "region": region,
        "revision": args.revision, "bundle": pathlib.Path(args.bundle).name,
        "models": models, "stream": stream, "gates": gate_rows,
        "locks": [{"name": k, "value": v} for k, v in sorted(locks.items())],
        "rules": len(final.get("rules") or []),
        "policy_hash": final.get("policy_hash"),
        "sample_rule": next((r.get("dsl_text") for r in (final.get("rules") or [])
                             if r.get("origin") != "seed"),
                            (final.get("rules") or [{}])[0].get("dsl_text", "")),
    }

    tpl = (pathlib.Path(__file__).parent / "run-view.template.html").read_text(
        encoding="utf-8")
    out = tpl.replace("/*__DATA__*/null",
                      json.dumps(payload, indent=1, sort_keys=True))
    pathlib.Path(args.out).write_text(out, encoding="utf-8", newline="")
    print("wrote %s" % args.out)
    print("  run %s  mode=%s  %d episodes  %d gate decisions  %d rules"
          % (run_id, mode, len(stream), len(gate_rows), payload["rules"]))
    if mode != "live":
        print("  NOTE this bundle is NOT a live run. The header will say so.")


if __name__ == "__main__":
    main()
