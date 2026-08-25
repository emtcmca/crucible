#!/usr/bin/env python3
"""render-attack-surface-negcheck.py - proof that the attack-surface renderer can fail.

A renderer that draws a plausible picture regardless of its input is a check that cannot
fail, and this project has paid for that failure shape more than once. `CONVENTIONS.md`
sec 8.2: *a check that cannot fail is not measuring anything.*

So this takes a REAL bundle directory, copies a small slice of it into a temp directory,
mutates the copy in one specific way per case, and runs the SHIPPED renderer - the same
`scripts/render-attack-surface.py` a judge would run, with no test-only mode and no flag
that changes its behaviour. Each case asserts an exit code and a named refusal code.

CASE 0 IS THE POSITIVE CONTROL and it is the half that is easy to leave out. Without it,
a renderer that refused every input would pass every negative case. Case 0 renders the
UNMUTATED copy and asserts exit 0, so the guards are proven selective rather than merely
loud.

The mutations are chosen so that each one would, in a renderer without guards, produce a
picture that still looks fine:

  empty-calls     every episode_prefix emptied. A guardless renderer draws the manifest
                  half - eight tools, seven classes, all the class edges - and simply has
                  no arcs. That is the dangerous one: a graph with no observations looks
                  exactly like a graph of a well-behaved agent.
  unknown-tool    one tool_name renamed to something the frozen manifest never declared.
                  A guardless renderer either drops the node silently or invents one.
  cap-drift       one event's capability_classes changed. A guardless renderer would draw
                  the manifest's class edge and never notice the evidence disagrees.
  corpus-split    one bundle's corpus_hash changed. A guardless renderer would average two
                  corpora into one picture and print one hash for both.
  no-policy       one bundle's policy_chain removed. Then v0 versus vFinal - the entire
                  point of the colouring - is undrawable, and the honest move is to refuse
                  rather than colour everything grey.

Run:  python scripts/render-attack-surface-negcheck.py <real_bundle_dir>
      exit 0 = every case behaved as specified; exit 1 = a guard did not fire.
"""

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
RENDERER = REPO / "scripts" / "render-attack-surface.py"

# case name -> (mutator, expected exit code, expected refusal code or None)
CASES = []


def case(name, exit_code, refusal):
    def deco(fn):
        CASES.append((name, fn, exit_code, refusal))
        return fn

    return deco


def _bundles(d):
    return sorted(pathlib.Path(d).glob("*.c6.json"))


def _rewrite(path, obj):
    path.write_bytes((json.dumps(obj) + "\n").encode("utf-8"))


@case("intact (POSITIVE CONTROL)", 0, None)
def m_intact(d):
    return "nothing mutated"


@case("empty-calls", 2, "E_NO_CALL_EVENTS")
def m_empty(d):
    for p in _bundles(d):
        b = json.loads(p.read_text(encoding="utf-8"))
        for ep in b.get("episodes", []):
            ep["episode_prefix"] = []
        _rewrite(p, b)
    return "episode_prefix emptied in every episode of every bundle"


@case("unknown-tool", 2, "E_UNKNOWN_TOOL")
def m_unknown(d):
    p = _bundles(d)[0]
    b = json.loads(p.read_text(encoding="utf-8"))
    for ep in b.get("episodes", []):
        for e in ep.get("episode_prefix", []):
            e["tool_name"] = "wire_funds_offshore"
            _rewrite(p, b)
            return "%s: one tool_name renamed to a tool the manifest never declared" % p.name
    raise SystemExit("negcheck could not mutate: no events in %s" % p.name)


@case("cap-drift", 2, "E_EVENT_CAP_DRIFT")
def m_capdrift(d):
    p = _bundles(d)[0]
    b = json.loads(p.read_text(encoding="utf-8"))
    for ep in b.get("episodes", []):
        for e in ep.get("episode_prefix", []):
            e["capability_classes"] = ["CAP_INVOKES_AGENT"]
            _rewrite(p, b)
            return "%s: one event's capability_classes replaced" % p.name
    raise SystemExit("negcheck could not mutate: no events in %s" % p.name)


@case("corpus-split", 2, "E_CORPUS_HASH_SPLIT")
def m_split(d):
    bs = _bundles(d)
    if len(bs) < 2:
        raise SystemExit("negcheck needs at least 2 bundles for corpus-split")
    p = bs[-1]
    b = json.loads(p.read_text(encoding="utf-8"))
    h = b["run_manifest"]["hash_locks"]["corpus_hash"]
    b["run_manifest"]["hash_locks"]["corpus_hash"] = ("0" * len(h))
    _rewrite(p, b)
    return "%s: corpus_hash changed, so the set no longer describes one corpus" % p.name


@case("unknown-cap", 2, "E_UNKNOWN_CAP")
def m_unknowncap(d):
    p = _bundles(d)[0]
    b = json.loads(p.read_text(encoding="utf-8"))
    for ep in b.get("episodes", []):
        for e in ep.get("episode_prefix", []):
            e["capability_classes"] = ["CAP_LAUNCHES_MISSILES"]
            _rewrite(p, b)
            return "%s: one event carries a capability class outside the frozen set" % p.name
    raise SystemExit("negcheck could not mutate: no events in %s" % p.name)


@case("handle-drift", 2, "E_HANDLE_DRIFT")
def m_handle(d):
    p = _bundles(d)[0]
    b = json.loads(p.read_text(encoding="utf-8"))
    for ep in b.get("episodes", []):
        for e in ep.get("episode_prefix", []):
            e["tool_handle"] = "tool:t_00000000"
            _rewrite(p, b)
            return "%s: one event's tool_handle no longer matches the manifest" % p.name
    raise SystemExit("negcheck could not mutate: no events in %s" % p.name)


@case("manifest-drift", 2, "E_MANIFEST_DRIFT")
def m_manifest(d):
    # Mutated on the BUNDLE side on purpose. The manifest under target/ is loop code and a
    # negative check may not edit it; changing the recorded hash proves the same binding.
    for p in _bundles(d):
        b = json.loads(p.read_text(encoding="utf-8"))
        h = b["run_manifest"]["hash_locks"]["manifest_hash"]
        b["run_manifest"]["hash_locks"]["manifest_hash"] = "f" * len(h)
        _rewrite(p, b)
    return "every bundle's recorded manifest_hash no longer matches the manifest on disk"


@case("empty-dir", 2, "E_NO_BUNDLES")
def m_emptydir(d):
    for p in _bundles(d):
        p.unlink()
    return "every bundle removed"


@case("no-policy", 2, "E_NO_POLICY_CHAIN")
def m_nopolicy(d):
    p = _bundles(d)[0]
    b = json.loads(p.read_text(encoding="utf-8"))
    b["policy_chain"] = []
    _rewrite(p, b)
    return "%s: policy_chain removed" % p.name


def run_case(src, name, mutator, want_exit, want_code, slice_n, keep):
    work = pathlib.Path(tempfile.mkdtemp(prefix="crucible-negcheck-"))
    try:
        for p in _bundles(src)[:slice_n]:
            shutil.copy2(p, work / p.name)
        what = mutator(work)
        proc = subprocess.run(
            [sys.executable, str(RENDERER), str(work), "--out-svg", str(work / "out.svg")],
            capture_output=True,
            text=True,
        )
        err = (proc.stderr or "").strip()
        ok_exit = proc.returncode == want_exit
        ok_code = (want_code is None) or (want_code in err)
        ok = ok_exit and ok_code
        drew = (work / "out.svg").exists()
        if want_exit != 0 and drew:
            ok = False
            err += "  [AND IT STILL WROTE AN SVG]"
        print("  %-28s exit %d (want %d)  %s" % (name, proc.returncode, want_exit,
                                                 "PASS" if ok else "*** FAIL ***"))
        print("      mutation : %s" % what)
        if want_exit == 0:
            print("      stdout   : %s" % ((proc.stdout or "").strip().splitlines() or [""])[-1])
            print("      svg      : %s" % ("written" if drew else "NOT WRITTEN"))
        else:
            print("      refusal  : %s" % (err.replace("\n", " | ") or "(no stderr)"))
        return ok
    finally:
        if keep:
            print("      kept     : %s" % work)
        else:
            shutil.rmtree(work, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bundle_dir", help="a REAL bundle directory; it is copied, never touched")
    ap.add_argument("--slice", type=int, default=4,
                    help="how many bundles to copy per case (default 4; the guards are "
                         "per-bundle, so a slice proves them as well as the full set)")
    ap.add_argument("--keep", action="store_true", help="leave the temp dirs on disk")
    args = ap.parse_args(argv)

    src = pathlib.Path(args.bundle_dir)
    if not _bundles(src):
        sys.stderr.write("no *.c6.json under %s\n" % src)
        return 1

    print("negative control for scripts/render-attack-surface.py")
    print("source: %s  (%d bundles available, %d copied per case)"
          % (src, len(_bundles(src)), args.slice))
    print()
    results = [
        run_case(src, name, fn, want_exit, want_code, args.slice, args.keep)
        for name, fn, want_exit, want_code in CASES
    ]
    print()
    print("%d/%d cases behaved as specified" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
