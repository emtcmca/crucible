"""parser.py - text of the CRUCIBLE policy DSL to `nodes.ParsedPatch`.

Grammar: `contracts/policy.ebnf`, which is frozen. This file implements it and
never extends it. Three things it must get right and would be easy to get wrong:

  * `cap:A|B` is a PARSE ERROR (ruling 22, negative check N2). `|` was deleted
    from the grammar. Under any-of matching with precedence by verb and file
    order never consulted, `cap:A|B => deny` was identical on every input to two
    separate rules - pure sugar, and ambiguous sugar, because `|` is EBNF
    alternation four lines below its own use as a separator. It must not be
    silently accepted under either reading: R8's repair loop feeds back the
    parser error as its SOLE signal, so a construct that parses wrong gives it
    nothing to repair against.
  * `cap:UNCLASSIFIED` is REJECTED EXPLICITLY, with its own error code, not as
    an accident of the cap_class production (V2, N5).
  * `=>` must be lexed before `>=` and `>`, or `... => deny` lexes as `>` `=`
    and the error names the wrong cause.

NOT IMPLEMENTED YET - this is the stub the negative checks run RED against.
"""

from .errors import ParseError  # noqa: F401  (re-exported for callers)
from .nodes import ParsedPatch, ParsedRule


def parse_policy(text: str) -> ParsedPatch:
    """Parse `{ rule | retraction }` into a ParsedPatch. Raises ParseError."""
    raise NotImplementedError("L3 WI-2: parser not implemented yet")


def parse_rule(text: str) -> ParsedRule:
    """Parse exactly one `rule` statement. Convenience over parse_policy."""
    raise NotImplementedError("L3 WI-2: parser not implemented yet")
