"""python -m crucible.coverage - the matrix, as text and as data.

EXIT CODE IS THE FINDING. 0 only when every clause fired at least once and every
source loaded. A dark clause exits 2, a refused source exits 3. That is
deliberate: the same instrument has to be usable from a shell script and from a
test, and a tool that prints a warning and exits 0 is a check that cannot fail.
"""

import argparse
import json
import pathlib
import sys

from .matrix import build_matrix
from .render import render
from .sources import SourceUnavailable, evidence_bundle


def _provenance():
    import datetime
    import subprocess
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:                                        # pragma: no cover
        head = "UNKNOWN"
    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
                                .replace(microsecond=0).isoformat(),
        "commit": head,
        "command": "python -m crucible.coverage",
        "_reading": (
            "Counters are over EPISODES unless the name says events. Every "
            "authored trace step in an authoring-shape source is taken to have "
            "EXECUTED, so corpus_training / offline_campaign_script / "
            "benign_suite figures are an UPPER BOUND on what a policy-enforced "
            "run would exercise. Sources are never pooled: read "
            "target_vocabulary_sources first."),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m crucible.coverage")
    ap.add_argument("--bundle", help="a C6 evidence bundle to fold in as a "
                                     "live-run source")
    ap.add_argument("--json", dest="json_out",
                    help="write the matrix as JSON to this path")
    ap.add_argument("--text", dest="text_out",
                    help="write the rendered matrix to this path as well as stdout")
    args = ap.parse_args(argv)

    extra = []
    if args.bundle:
        try:
            episodes, skipped = evidence_bundle(args.bundle)
        except SourceUnavailable as exc:
            print("REFUSED: %s" % exc, file=sys.stderr)
            return 3
        extra.append(("evidence_bundle", episodes, skipped))

    matrix = build_matrix(extra=extra)
    text = render(matrix)
    print(text)

    if args.json_out:
        p = pathlib.Path(args.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        # PROVENANCE IN THE ARTIFACT, not only in the memo that cites it. A
        # coverage snapshot with no commit attached cannot be told from a
        # current one, and the fixture arm of this matrix is under active
        # migration in another lane - so "which tree was this" is the first
        # question a reader has and the one a bare table cannot answer.
        payload = dict(_provenance=_provenance(), **matrix.as_dict())
        p.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n",
                     encoding="utf-8")
        print("wrote %s" % p)
    if args.text_out:
        p = pathlib.Path(args.text_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text + "\n", encoding="utf-8")
        print("wrote %s" % p)

    if matrix.refusals:
        return 3
    # SCOPED TO THE SOURCES THAT SPEAK THE TARGET'S TOOL VOCABULARY, which is
    # the same set the gate test uses. Exiting 0 on a pooled count would let a
    # fixture written in a dead vocabulary clear the check for a clause no real
    # trace can reach - the exact inversion this instrument was built to find.
    if matrix.dark_clauses(matrix.target_vocabulary_sources()):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
