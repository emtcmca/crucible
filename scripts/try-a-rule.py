#!/usr/bin/env python3
"""try-a-rule.py - hand the policy DSL a rule and watch it accept or refuse.

Run:  python scripts/try-a-rule.py "rule r_new1: cap:CAP_MOVES_MONEY => deny"
      python scripts/try-a-rule.py --demo      # four rules, two accepted, two refused
      python scripts/try-a-rule.py --lexicon   # print the harvested V3 denylist

WHY THIS SCRIPT EXISTS. `crucible.dsl` has no command-line entry point, because
nothing in the loop needs one: the ARMORER calls the validator in-process. A
READER needs one. The single most persuasive thing this project can show someone
in thirty seconds is a refusal they caused themselves, so the refusal has to be
reachable without writing Python.

WHAT IT DOES NOT DO. It calls no model, opens no socket, and reads no
credential. It reads two JSON files off disk and runs the same `Validator` the
ARMORER's output is judged by - not a demonstration copy of it. If this script
and the loop ever disagree, this script is the defect.

  Part A  target/refund_agent/capability_manifest.json   the frozen tool surface
  Part B  contracts/golden/C3b-derived_schema.valid.json the derived.* schema

Part B is the golden contract fixture rather than a run artifact: the real Part B
freezes at D5 with the corpus. Named here rather than glossed, because a reader
who assumes both halves are frozen artifacts would be wrong about one of them.

Exit codes: 0 the rule was ACCEPTED, 1 the rule was REFUSED, 2 bad usage.
A refusal is this tool working, so a script wrapping it needs to tell the two
apart by code rather than by reading the prose.
"""

import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from crucible.dsl import parse_rule                                   # noqa: E402
from crucible.dsl.errors import DslError                              # noqa: E402
from crucible.dsl.validator import Validator, harvest_product_lexicon  # noqa: E402

MANIFEST_A = REPO / "target" / "refund_agent" / "capability_manifest.json"
DERIVED_B = REPO / "contracts" / "golden" / "C3b-derived_schema.valid.json"

# Two the language admits, two it will not. The refusals are the point: both are
# rules a competent engineer would write on the first try, and both bind the
# policy to this product's own nouns.
DEMO = [
    ("rule r_new1: cap:CAP_MOVES_MONEY when amount_cents > 50000 "
     "=> require_approval(HIGH_VALUE)"),
    "rule r_new1: cap:CAP_MOVES_MONEY, tool:t_30ac67c8 => deny",
    "rule r_new1: cap:CAP_MOVES_MONEY when issue_refund.amount_cents > 5000 => deny",
    ("rule r_new1: cap:CAP_EXTERNAL_COMMS when email_customer.to "
     "!= episode.account_holder_email => deny"),
]


def build_validator():
    manifest = json.loads(MANIFEST_A.read_text(encoding="utf-8"))
    derived = json.loads(DERIVED_B.read_text(encoding="utf-8"))
    lexicon = harvest_product_lexicon(manifest)
    return Validator(manifest, derived, product_lexicon=lexicon), lexicon


def judge(validator, source):
    """Print the verdict for one rule. Returns True if it was accepted."""
    print("  rule      %s" % source)
    try:
        out = validator.validate_rule(parse_rule(source))
    except DslError as e:
        print("  verdict   REFUSED")
        print("  code      %s" % e.code)
        print("  because   %s" % e.detail)
        print()
        return False
    print("  verdict   ACCEPTED")
    print("  rule_id   %s   <- computed by the validator from the canonical "
          "body." % out["rule_id"])
    print("            The model wrote the placeholder r_new1 and never sees "
          "this value.")
    print()
    return True


def main(argv):
    args = list(argv)
    if "--lexicon" in args:
        _, lexicon = build_validator()
        print("V3 product-lexicon denylist, harvested from the target's tool "
              "names and\ndescriptions, minus the capability vocabulary. "
              "%d token(s):\n" % len(lexicon))
        for tok in sorted(lexicon):
            print("  %s" % tok)
        print("\nHarvested at run time from %s, so a judge can re-derive it "
              "rather than\ntrust a list someone typed."
              % MANIFEST_A.relative_to(REPO).as_posix())
        return 0

    validator, _ = build_validator()
    print("crucible try-a-rule\n")

    if "--demo" in args or not args:
        for src in DEMO:
            judge(validator, src)
        print("Two accepted, two refused. Both refusals name a tool the way a "
              "person would.\nThe language has no way to say it, which is why "
              "a rule learned on one tool\ncan apply to a tool it has never "
              "seen.")
        return 0

    sources = [a for a in args if not a.startswith("--")]
    if not sources:
        print("usage: python scripts/try-a-rule.py \"<rule text>\"", file=sys.stderr)
        return 2
    ok = True
    for src in sources:
        ok = judge(validator, src) and ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
