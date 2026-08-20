"""D3 TARGET FREEZE - prepared here, EXECUTED BY THE PROJECT OWNER.

**This lane does not run `--write`.** The freeze is one of the five hash-locks the
whole measurement rests on, it happens on a scheduled date, and it is the owner's
call. What this module does is make running it a single command with nothing left
to decide.

WHAT A FREEZE IS, in plain English. Before any measurement is taken, you write down
exactly what you are measuring and hash it, so that afterwards nobody - including
you - can quietly adjust the thing under test and re-report. Every headline number
in this project is only worth anything because the target, the gate rule, the
capability manifest, the definition of "breach", and the corpus were each pinned
BEFORE the first episode ran. There are FIVE such hash-locks; this module produces
two of them: the target agent and `manifest_hash`.

WHAT GOES IN, and why each piece:

  capability_manifest.json    Part A. What the tools are and what classes they
                              carry. Freezes here, at D3, with the target.
  target_descriptor           the model binding - `gemini-3.5-flash-lite` at
                              `thinking_level: minimal`. IN THE HASH because the
                              target's tier flatters or deflates every number
                              downstream, so it must be recoverable from the
                              frozen record rather than from memory.
  refund_policy.md            the system prompt, by content hash. The policy IS
                              the attack surface; a freeze that did not cover it
                              would let the target's instructions move between the
                              v0 arm and the vFinal arm.
  tool signatures             name and ordered parameter names per tool. A
                              parameter renamed after the freeze breaks every
                              arg-path rule silently.

WHAT IS DELIBERATELY OUT: the fake ledger and the demo transcripts. The ledger is a
stand-in for L1's component and is not part of the target's behaviour under test;
the demos are a rehearsal script. Hashing either would make the target freeze move
whenever a demo line was reworded.

HASHING USES `crucible.canon`. This is the one place the target package reaches
into CRUCIBLE, and it is deliberate: reimplementing canonicalization here would be
a second source of truth for the operation every hash claim in the build depends
on. The freeze is a CRUCIBLE operation performed ON the target, not part of the
target's runtime - `agent.py`, `tools.py`, `episode.py`, `ledger_interface.py` and
`fake_ledger.py` import nothing from `crucible/` and the agent runs without it.

VERIFY, DO NOT TRUST. `--check` recomputes and compares against the committed
`FROZEN.json`. It prints the recomputed hash so the postcondition is asserted from
the artifact rather than from an exit code.
"""

import argparse
import hashlib
import inspect
import json
import pathlib
import sys

from crucible.canon import canonicalize, hash_full

from . import tools
from .agent import POLICY_PATH, target_descriptor
from .manifest import build_manifest

HERE = pathlib.Path(__file__).resolve().parent
FROZEN_PATH = HERE / "FROZEN.json"


def tool_signatures() -> list:
    """Name plus ORDERED parameter names, per tool. Sorted by name at construction
    (arrays are sorted at construction, never at hash time), while each tool's own
    parameter list keeps SOURCE ORDER, because order is meaning there."""
    out = []
    for fn in sorted(tools.TOOL_FUNCTIONS, key=lambda f: f.__name__):
        params = list(inspect.signature(fn).parameters)
        out.append({"tool_name": fn.__name__, "params": params})
    return out


def policy_sha256() -> str:
    """SHA-256 of the policy file AFTER LF NORMALIZATION.

    THIS NORMALIZATION IS NOT COSMETIC AND IT WAS FOUND THE HARD WAY. Verified
    2026-08-20: this repository runs `core.autocrlf=true`, and `.gitattributes`
    covers `contracts/**` and the canonicalization vectors but NOT `target/**`
    (`git check-attr text eol` returns `unspecified` for this file). So the working
    copy holds LF and a fresh clone on Windows gets CRLF - and the raw-bytes hash
    differs: `ae3cb4c93f86ad8a` here against `2060b712f63a6e6c` from a CRLF
    checkout. That silently breaks the exit criterion that the freeze hash
    RECOMPUTES IDENTICALLY FROM A CLEAN CHECKOUT, and it breaks it in the worst
    way - the freeze looks fine on the machine that made it and fails for the judge
    who clones it.

    Normalizing here rather than adding a `.gitattributes` rule is deliberate on
    two counts. It follows the convention this repo already set for the artifacts
    it hashes - `contracts/**` are hashed after LF normalization for the same
    reason. And `.gitattributes` is shared configuration outside this lane's owned
    paths; a lane editing it is a lane changing something five other lanes depend
    on. The gap is reported to the coordinator, who may still want the attribute.

    A BOM is REFUSED rather than stripped, matching `crucible.canon` restriction 1:
    stripping it would make the file that arrives differ from the file that was
    hashed.
    """
    raw = POLICY_PATH.read_bytes()
    if raw[:3] == b"\xef\xbb\xbf":
        raise RuntimeError(
            "refund_policy.md carries a UTF-8 BOM. Refused rather than stripped - "
            "a stripped BOM makes the file that arrives differ from the file that "
            "was hashed.")
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def freeze_payload() -> dict:
    """The exact object that gets hashed. No timestamps, no run id, no paths - a
    payload carrying any of those hashes differently on two machines, and the
    recompute-from-a-clean-checkout exit criterion is the whole point."""
    return {
        "capability_manifest": build_manifest(),
        "target_descriptor": target_descriptor(),
        "policy_sha256": policy_sha256(),
        "tool_signatures": tool_signatures(),
    }


def compute() -> dict:
    payload = freeze_payload()
    return {
        "target_id": payload["target_descriptor"]["target_id"],
        "manifest_hash": hash_full(payload["capability_manifest"])[:16],
        "target_agent_hash": hash_full(payload)[:16],
        "policy_sha256": payload["policy_sha256"],
        "canonical_bytes": len(canonicalize(payload)),
    }


def _emit(result, label):
    print("%s\n  target_id          %s\n  manifest_hash      %s\n"
          "  target_agent_hash  %s\n  policy_sha256      %s\n  canonical bytes    %d"
          % (label, result["target_id"], result["manifest_hash"],
             result["target_agent_hash"], result["policy_sha256"],
             result["canonical_bytes"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true",
                    help="WRITE FROZEN.json. The project owner runs this, on the "
                         "scheduled freeze date. A lane does not.")
    ap.add_argument("--check", action="store_true",
                    help="recompute and compare against the committed FROZEN.json")
    args = ap.parse_args(argv)

    result = compute()

    if args.write:
        # newline="\n" for the same reason manifest.py needs it: pathlib applies
        # the platform's newline translation, and the frozen record must not carry
        # bytes that depend on which machine ran the freeze.
        FROZEN_PATH.write_text(json.dumps(result, indent=2) + "\n",
                               encoding="utf-8", newline="\n")
        readback = json.loads(FROZEN_PATH.read_text(encoding="utf-8"))
        if readback != result:
            print("FROZEN.json did not read back as written", file=sys.stderr)
            return 2
        _emit(result, "FROZEN (written and read back)")
        return 0

    if args.check:
        if not FROZEN_PATH.exists():
            print("no FROZEN.json - the freeze has not been run", file=sys.stderr)
            _emit(result, "RECOMPUTED (nothing to compare against)")
            return 1
        committed = json.loads(FROZEN_PATH.read_text(encoding="utf-8"))
        _emit(result, "RECOMPUTED")
        if committed != result:
            print("\nMISMATCH - the target moved after the freeze.\n  committed %s"
                  "\n  recomputed %s" % (committed.get("target_agent_hash"),
                                         result["target_agent_hash"]), file=sys.stderr)
            return 2
        print("\nMATCHES the committed freeze.")
        return 0

    _emit(result, "RECOMPUTED (dry run; neither --write nor --check given)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
