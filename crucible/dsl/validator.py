"""validator.py - V1-V9 from `contracts/policy.ebnf`, plus N3, N5 and N6.

The parser decides whether the text is IN THE LANGUAGE. This file decides
whether a rule that is in the language is ADMISSIBLE, which needs three things
the parser does not have: capability manifest Part A, derived schema Part B, and
the policy the patch is being applied to.

The checks, and what each one is actually defending:

  V1  cap_selector present and FIRST. There is no way to write a rule that binds
      only to a tool, so EVERY LEARNED RULE GENERALIZES TO EXACTLY ONE
      CAPABILITY CLASS - the mechanism behind headline result #1.
  V2  `cap:UNCLASSIFIED` rejected explicitly (enforced in the parser; re-asserted
      here so the refusal survives someone routing around the parser).
  V3  No plain-text product identifier anywhere in the patch text. Metadata and
      provenance are exempt (KB9).
  V4  Every enum_symbol is a declared member FOR ITS EXACT arg_path.
  V5  Every tool_handle is in the manifest.
  V6  Every retract targets an `armorer:*` rule. SEED RULES ARE IRRETRACTABLE.
  V7  Zero rule bodies contain an >=8-token substring of any corpus payload.
  V8  The resulting rule set evaluates TOTAL on a synthetic call-shape sweep.
  V9  On add_rule, a hash-shaped rule_id is REJECTED.
  N3  A policy DOCUMENT containing `match_mode` at any depth is rejected.
  N6  A rule naming a `derived.*` path Part B does not declare is rejected.

NOT IMPLEMENTED YET - this is the stub the negative checks run RED against.
"""

from .errors import ValidationError  # noqa: F401


def validate_policy_document(doc: dict) -> None:
    """Structural validation of a stored policy document. Raises ValidationError.

    Includes negative check N3: `match_mode` AT ANY DEPTH is a hard reject.
    `match_mode` was DELETED rather than pinned to a constant, because a field
    pinned to a constant sits inside the hashed payload inviting the other value
    at 1am - and the two readings were different policies for the same bytes.
    """
    raise NotImplementedError("L3 WI-3: validator not implemented yet")


class Validator:
    """Holds the manifest halves a rule must be judged against.

    Part A (`capability_manifest`) freezes at D3 with the target agent; Part B
    (`derived_schema`) freezes at D5 with the corpus, gated on the label-
    blindness check. Two artifacts, two hashes, two freeze dates - ruling 20.
    Both are required here because a rule can name a tool handle (Part A) and a
    `derived.*` path (Part B) in the same line.
    """

    def __init__(self, manifest_a: dict, derived_schema_b: dict, *,
                 product_lexicon=(), corpus_payloads=()):
        raise NotImplementedError("L3 WI-3: validator not implemented yet")

    def validate_rule(self, parsed) -> dict:
        """Validate one parsed rule and return its stored form with a real ID."""
        raise NotImplementedError("L3 WI-3: validator not implemented yet")

    def validate_patch(self, parsed_patch, current_policy=None) -> dict:
        """Validate a whole patch against the policy it applies to.

        Returns the new `hashed_payload`. Raises ValidationError on the first
        refusal - the ARMORER gets ONE repair attempt with the error as its sole
        feedback, and a list of twelve simultaneous complaints is not feedback.
        """
        raise NotImplementedError("L3 WI-3: validator not implemented yet")
