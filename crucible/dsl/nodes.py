"""nodes.py - the parsed shape of a policy patch.

Named `nodes` and not `ast` on purpose: `ast` is a stdlib module and shadowing
it inside a package that anything else may import is the kind of defect that
surfaces three files away from its cause.

These dataclasses are the boundary between the parser and everything else. They
carry NO semantics - `serialize.py` turns them into the stored C4 form and
`validator.py` decides whether they are admissible. Keeping judgement out of the
node types is what lets the parser stay a pure function of the text, which is
what makes the ARMORER's repair feedback reproducible.

CAP_CLASSES is SIX and there is no seventh. `UNCLASSIFIED` is deliberately not
a member (CONVENTIONS 2.2, policy.ebnf V2): it means WE DO NOT KNOW WHAT THIS
TOOL DOES, and a single `cap:UNCLASSIFIED => deny` on an unseen target would
block everything and report 100% transfer, manufactured.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

# CONVENTIONS 2.2. Six, and the ordering here is the sorted order used wherever
# a capability list is written to a hashed payload (canonicalization rule 6).
CAP_CLASSES = (
    "CAP_ESCALATES_PRIVILEGE",
    "CAP_EXTERNAL_COMMS",
    "CAP_INVOKES_AGENT",
    "CAP_MOVES_MONEY",
    "CAP_MUTATES_DURABLE_STATE",
    "CAP_READS_PII",
)

# The sentinel. DISTINCT FROM THE EMPTY SET: empty means inert, this means we do
# not know. It appears on tools and on ToolEvents; it may never appear in a rule.
UNCLASSIFIED = "UNCLASSIFIED"

# CONVENTIONS 2.3. Three verbs and there is no fourth. Ordered by STRICTNESS
# ascending, which is the order the engine resolves on - never file order.
VERBS = ("constrain_arg", "require_approval", "deny")

# policy.ebnf: context_field. Three, frozen at episode start, unwritable after.
CONTEXT_FIELDS = (
    "account_holder_email",
    "account_holder_id",
    "order_payment_instrument_id",
)

# Text form -> stored form. The stored `op` enum in policy_document.schema.json
# is spelled out because a JSON key of `>=` is legal but miserable to grep for.
CMP_OPS = {"==": "eq", "!=": "ne", "<": "lt", "<=": "lte", ">": "gt", ">=": "gte"}

# Clause discriminants. The last three are the episode-scoped forms.
CLAUSE_ARG_CMP_LITERAL = "arg_cmp_literal"
CLAUSE_ARG_IN_ENUM_LIST = "arg_in_enum_list"
CLAUSE_ARG_IS_ABSENT = "arg_is_absent"
CLAUSE_PRECEDED_BY = "preceded_by"
CLAUSE_EPISODE_SUM = "episode_sum"
CLAUSE_ARG_VS_EPISODE_CONTEXT = "arg_vs_episode_context"

EPISODE_SCOPED_FORMS = (
    CLAUSE_PRECEDED_BY,
    CLAUSE_EPISODE_SUM,
    CLAUSE_ARG_VS_EPISODE_CONTEXT,
)


@dataclass(frozen=True)
class Clause:
    """One conjunct of a `when`. Conjunction only - no disjunction, no negation.

    `form` discriminates; the fields used depend on it. A tagged union rather
    than six classes because the stored C4 form is itself a tagged union keyed
    on `form`, and two different unions over the same six cases is one mapping
    too many.
    """
    form: str
    path: Optional[str] = None          # arg_path, for the four arg-bearing forms
    op: Optional[str] = None            # text cmp_op: "==", ">=", ...
    value: Any = None                   # INTEGER | BOOLEAN | enum_symbol
    value_type: Optional[str] = None    # "int" | "bool" | "enum" | "enum_list"
    values: Optional[Tuple[str, ...]] = None   # enum_list members
    cap_class: Optional[str] = None     # preceded_by
    context_field: Optional[str] = None  # arg_vs_episode_context


@dataclass(frozen=True)
class Action:
    """`deny` | `constrain_arg(path op literal)` | `require_approval(REASON)`."""
    verb: str
    path: Optional[str] = None
    op: Optional[str] = None
    value: Any = None
    value_type: Optional[str] = None
    reason_code: Optional[str] = None


@dataclass
class ParsedRule:
    """One `rule` statement, exactly as written, with nothing resolved.

    `rule_id` here is whatever the text carried - a placeholder (`r_new1`) on an
    add, or a real ID on a document being re-read. The validator is what decides
    which is legal and what the real ID is; the parser does not know and must
    not guess. CONVENTIONS 2.6.
    """
    rule_id: str
    cap_class: str
    tool_handles: List[str] = field(default_factory=list)
    clauses: List[Clause] = field(default_factory=list)
    action: Action = None
    origin: Optional[str] = None
    line: int = 0
    source_text: str = ""
    # The selector-through-action tokens ONLY: no `rule`, no rule_id, no
    # `origin` clause. V3's product-lexicon denylist and V7's payload-substring
    # lint both run over this rather than over `source_text`, because KB9
    # exempts metadata and provenance fields - a rule id is not something the
    # ARMORER chose, and an origin is a fact about the round.
    body_text: str = ""


@dataclass
class ParsedPatch:
    """A whole patch: `{ rule | retraction }`."""
    rules: List[ParsedRule] = field(default_factory=list)
    retractions: List[str] = field(default_factory=list)
    source_text: str = ""
