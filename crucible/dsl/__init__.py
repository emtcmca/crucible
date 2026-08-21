"""crucible.dsl - C4 parser and validator. Owned by L3 ENFORCEMENT.

The grammar is `contracts/policy.ebnf` and it is frozen. Three verbs, six
capability classes, three episode-scoped predicate forms, and NO FREE STRINGS.
That last one is the bar rather than a style choice: a language that cannot
express a string match cannot learn a string filter, so the held-out-family
result is true BY CONSTRUCTION rather than by discipline.
"""

from .errors import DslError, HaltHuman, ParseError, ValidationError
from .nodes import (
    CAP_CLASSES,
    CMP_OPS,
    CONTEXT_FIELDS,
    EPISODE_SCOPED_FORMS,
    UNCLASSIFIED,
    VERBS,
    Action,
    Clause,
    ParsedPatch,
    ParsedRule,
)
from .parser import parse_policy, parse_rule
from .serialize import compile_rule, rule_body, sort_rules
from .validator import Validator, validate_policy_document

__all__ = [
    "DslError", "ParseError", "ValidationError", "HaltHuman",
    "CAP_CLASSES", "UNCLASSIFIED", "VERBS", "CONTEXT_FIELDS", "CMP_OPS",
    "EPISODE_SCOPED_FORMS",
    "Clause", "Action", "ParsedRule", "ParsedPatch",
    "parse_policy", "parse_rule",
    "rule_body", "compile_rule", "sort_rules",
    "Validator", "validate_policy_document",
]
