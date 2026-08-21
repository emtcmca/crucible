"""errors.py - refusals from the DSL layer, each carrying a stable machine code.

Two reasons the code is a field rather than a prefix on a message string:

  * `policy.ebnf`'s repair loop feeds the ARMORER **the parser error as its sole
    signal**. A message that says "syntax error at line 1" tells a model nothing
    it can repair against; `E_PIPE_DELETED` plus the sentence explaining that
    `cap:A|B` is now two rules does.
  * Tests assert on the code, never on the prose. A test that asserts on a
    message string breaks when the message improves, which trains people to
    stop improving messages.

Nothing here repairs. `crucible/canon/canonical.py` makes the same trade in its
own docstring and for the same reason: a silent repair produces a green
checkmark over a document that is not the document that was hashed.
"""


class DslError(ValueError):
    """Base for every refusal the parser or validator makes."""

    def __init__(self, code: str, detail: str = "", line: int = None):
        self.code = code
        self.detail = detail
        self.line = line
        where = "" if line is None else " (line %d)" % line
        super().__init__("%s%s: %s" % (code, where, detail) if detail
                         else "%s%s" % (code, where))


class ParseError(DslError):
    """The text is not in the language. Feedback to the ARMORER's one repair."""


class ValidationError(DslError):
    """The text parses but the rule is not admissible: V1-V9 in `policy.ebnf`."""


class HaltHuman(Exception):
    """`HALT_HUMAN`. Not a DslError - it is not a bad patch, it is a broken
    invariant, and the difference matters because a DslError gets ONE repair
    attempt and this gets none.

    Raised when `episode.*` is written after episode start (ruling 16). That
    write is the single cheapest way to invalidate the headline result, it looks
    like nothing, and no gate catches it - so it terminates the episode rather
    than being merged, logged, or repaired.
    """

    def __init__(self, reason_code: str, detail: str = ""):
        self.reason_code = reason_code
        self.detail = detail
        super().__init__("HALT_HUMAN(%s): %s" % (reason_code, detail) if detail
                         else "HALT_HUMAN(%s)" % reason_code)
