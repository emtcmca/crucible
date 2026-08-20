"""serialize.py - ParsedRule to the stored C4 form, and the rule_id assignment.

The stored form is `policy_document.schema.json` `$defs/rule`. Two properties of
it are load-bearing rather than cosmetic:

  * **Arrays are sorted AT CONSTRUCTION** (canonicalization.md restriction 6),
    not at hash time. `rules` by `rule_id`, `arg_conditions` by `path` then
    `op`. Sorting at hash time would look lossless and be destructive; sorting
    here is what makes the canonical form unambiguous.
  * **`rule_id` is assigned by CODE, from the canonical bytes of the body with
    `rule_id` removed.** The ARMORER emits `r_new1` and never sees a hash
    (CONVENTIONS 2.6). A model cannot compute a SHA-256; asked to, it fails
    every attempt, and the day-1 spike would have read 0/20 and triggered an
    architecture change for a reason that has nothing to do with the DSL.

NOT IMPLEMENTED YET - this is the stub the negative checks run RED against.
"""

from .nodes import ParsedRule


def rule_body(parsed: ParsedRule) -> dict:
    """The stored rule WITHOUT `rule_id`. This is what gets hashed."""
    raise NotImplementedError("L3 WI-2: serializer not implemented yet")


def compile_rule(parsed: ParsedRule) -> dict:
    """Stored rule with the real content-addressed `rule_id` written in."""
    raise NotImplementedError("L3 WI-2: serializer not implemented yet")


def sort_rules(rules: list) -> list:
    """`rules` ascending by `rule_id` - restriction 6."""
    raise NotImplementedError("L3 WI-2: serializer not implemented yet")
