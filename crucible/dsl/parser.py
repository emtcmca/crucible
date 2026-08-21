"""parser.py - text of the CRUCIBLE policy DSL to `nodes.ParsedPatch`.

Grammar: `contracts/policy.ebnf`, which is frozen. This file implements it and
never extends it. Four things it must get right and would be easy to get wrong:

  * `cap:A|B` is a PARSE ERROR (ruling 22, negative check N2). `|` was deleted
    from the grammar. Under any-of matching with precedence by verb and file
    order never consulted, `cap:A|B => deny` was identical on every input to two
    separate rules - pure sugar, and ambiguous sugar, because `|` is EBNF
    alternation four lines below its own use as a separator. It must not be
    silently accepted under either reading: R8's repair loop feeds back the
    parser error as its SOLE signal, so a construct that parses wrong gives it
    nothing to repair against.

  * `cap:UNCLASSIFIED` is REJECTED EXPLICITLY, with its own error code, not as
    an accident of the cap_class production (V2, N5). A generic
    "unknown capability class" error would fire today and stop firing the moment
    somebody added UNCLASSIFIED to a list for an unrelated reason.

  * `=>` must be lexed before `>=` and `>`, or `... => deny` lexes as `>` then
    `=` and the error names the wrong cause. The operator table is sorted
    longest-first for exactly this reason.

  * The parser DOES NOT JUDGE. It does not know the manifest, so it cannot tell
    a declared enum symbol from an undeclared one, or a declared `derived.*`
    path from an invented one. That is `validator.py`'s job, and the split is
    load-bearing rather than tidy: ruling 24 turns on a rule that COMPILES AS
    GRAMMAR and REJECTS AS POLICY, and if the parser resolved names against the
    manifest there would be no such state to demonstrate.

Errors carry a `code`. `policy.ebnf` gives the ARMORER exactly ONE repair
attempt with the parser error as its sole feedback, so the error has to be
specific enough to repair against and stable enough to test on.
"""

import re

from .errors import ParseError
from .nodes import (
    CAP_CLASSES,
    CLAUSE_ARG_CMP_LITERAL,
    CLAUSE_ARG_IN_ENUM_LIST,
    CLAUSE_ARG_IS_ABSENT,
    CLAUSE_ARG_IS_PRESENT,
    CLAUSE_ARG_VS_EPISODE_CONTEXT,
    CLAUSE_EPISODE_SUM,
    CLAUSE_PRECEDED_BY,
    CMP_OPS,
    CONTEXT_FIELDS,
    UNCLASSIFIED,
    Action,
    Clause,
    ParsedPatch,
    ParsedRule,
)

# `ident = LOWER { LOWER | DIGIT | "_" }` - lowercase start, so an arg_path can
# never be confused with an enum_symbol.
IDENT_RE = re.compile(r"^[a-z][a-z0-9_]*$")
UPPER_SNAKE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
REAL_RULE_ID_RE = re.compile(r"^r_[0-9a-f]{12}$")
PLACEHOLDER_RULE_ID_RE = re.compile(r"^r_new[0-9]+$")
TOOL_HANDLE_RE = re.compile(r"^t_[0-9a-f]{8}$")

# Longest first. `=>` before `>=` before `>`; `==` before `=` (which is not a
# token at all, and must not silently become one).
_OPERATORS = ("=>", "==", "!=", "<=", ">=", "<", ">")
_PUNCT = (":", ",", "(", ")", "[", "]", ".")

_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_INT_RE = re.compile(r"-?[0-9]+")


class _Token:
    __slots__ = ("kind", "text", "line")

    def __init__(self, kind, text, line):
        self.kind, self.text, self.line = kind, text, line

    def __repr__(self):                                   # pragma: no cover
        return "<%s %r@%d>" % (self.kind, self.text, self.line)


def _lex(text):
    """Text to tokens. NEWLINE is a token because the grammar terminates both
    `rule` and `retraction` with NL, so it is syntax, not whitespace."""
    toks, i, line = [], 0, 1
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            toks.append(_Token("NEWLINE", "\n", line))
            line += 1
            i += 1
            continue
        if ch in " \t\r":
            i += 1
            continue
        if ch == "|":
            # The whole of negative check N2, refused at the lexer so the
            # message can say what the construct MEANT rather than reporting an
            # unexpected token four productions later.
            raise ParseError(
                "E_PIPE_DELETED",
                "`|` was deleted from the grammar (ruling 22). A multi-class "
                "selector `cap:A|B` was pure sugar - identical on every input "
                "to two separate rules, because precedence is by verb and file "
                "order is never consulted - and it was ambiguous sugar, since "
                "`|` is EBNF alternation in the cap_class production. Write the "
                "two rules.", line)
        m = _INT_RE.match(text, i)
        if m and (ch.isdigit() or (ch == "-" and i + 1 < n and text[i + 1].isdigit())):
            toks.append(_Token("INT", m.group(0), line))
            i = m.end()
            continue
        m = _WORD_RE.match(text, i)
        if m:
            toks.append(_Token("WORD", m.group(0), line))
            i = m.end()
            continue
        for op in _OPERATORS:
            if text.startswith(op, i):
                toks.append(_Token("OP", op, line))
                i += len(op)
                break
        else:
            if ch in _PUNCT:
                toks.append(_Token("PUNCT", ch, line))
                i += 1
                continue
            raise ParseError("E_UNEXPECTED_CHAR", "%r is not part of the DSL" % ch,
                             line)
    toks.append(_Token("EOF", "", line))
    return toks


class _Parser:
    def __init__(self, text):
        self.text = text
        self.toks = _lex(text)
        self.i = 0

    # -- token plumbing ---------------------------------------------------
    @property
    def cur(self):
        return self.toks[self.i]

    def peek(self, ahead=0):
        j = min(self.i + ahead, len(self.toks) - 1)
        return self.toks[j]

    def at(self, kind, text=None, ahead=0):
        t = self.peek(ahead)
        return t.kind == kind and (text is None or t.text == text)

    def take(self):
        t = self.cur
        self.i += 1
        return t

    def expect(self, kind, text=None, what=""):
        t = self.cur
        if t.kind != kind or (text is not None and t.text != text):
            raise ParseError(
                "E_UNEXPECTED_TOKEN",
                "expected %s%s but found %r%s"
                % (text or kind, " (%s)" % what if what else "",
                   t.text or "end of input",
                   "" if t.kind != "NEWLINE" else " (end of line)"),
                t.line)
        return self.take()

    def skip_newlines(self):
        while self.at("NEWLINE"):
            self.take()

    def end_of_statement(self):
        if self.at("EOF"):
            return
        self.expect("NEWLINE", what="a statement ends at the end of its line")

    # -- productions ------------------------------------------------------
    def parse_patch(self):
        patch = ParsedPatch(source_text=self.text)
        self.skip_newlines()
        while not self.at("EOF"):
            if self.at("WORD", "retract"):
                patch.retractions.append(self.parse_retraction())
            elif self.at("WORD", "rule"):
                patch.rules.append(self.parse_rule())
            else:
                raise ParseError(
                    "E_UNEXPECTED_TOKEN",
                    "a statement starts with `rule` or `retract`, not %r"
                    % self.cur.text, self.cur.line)
            self.skip_newlines()
        return patch

    def parse_retraction(self):
        self.expect("WORD", "retract")
        rid = self.rule_id()
        self.end_of_statement()
        return rid

    def parse_rule(self):
        start = self.i
        line = self.cur.line
        self.expect("WORD", "rule")
        rid = self.rule_id()
        self.expect("PUNCT", ":")
        body_start = self.i
        cap_class, tool_handles = self.selector()

        clauses = []
        if self.at("WORD", "when"):
            self.take()
            clauses = self.predicate()

        self.expect("OP", "=>", what="the action arrow")
        action = self.action()
        body_end = self.i

        origin = None
        if self.at("WORD", "origin"):
            self.take()
            origin = self.origin()

        end = self.i
        self.end_of_statement()
        return ParsedRule(
            rule_id=rid, cap_class=cap_class, tool_handles=tool_handles,
            clauses=clauses, action=action, origin=origin, line=line,
            source_text=" ".join(t.text for t in self.toks[start:end]),
            body_text=" ".join(t.text for t in self.toks[body_start:body_end]))

    def rule_id(self):
        t = self.expect("WORD", what="a rule id")
        if REAL_RULE_ID_RE.match(t.text) or PLACEHOLDER_RULE_ID_RE.match(t.text):
            return t.text
        raise ParseError(
            "E_BAD_RULE_ID",
            "%r is neither `r_` plus twelve hex nor a placeholder `r_newN`. "
            "On add_rule the ARMORER emits a placeholder and the validator "
            "computes the real id - a model cannot compute a SHA-256, and one "
            "that emits a plausible hash has demonstrated it is guessing at a "
            "deterministic computation." % t.text, t.line)

    def selector(self):
        """`cap_selector { "," qualifier }` - cap is REQUIRED and FIRST.

        There is no way to write a rule that binds only to a tool, which is the
        mechanism behind headline result #1: EVERY LEARNED RULE GENERALIZES TO
        EXACTLY ONE CAPABILITY CLASS.
        """
        self.expect("WORD", "cap", what="cap_selector is required and FIRST")
        self.expect("PUNCT", ":")
        t = self.expect("WORD", what="a capability class")
        if t.text == UNCLASSIFIED:
            raise ParseError(
                "E_UNCLASSIFIED_SELECTOR",
                "`cap:UNCLASSIFIED` is refused explicitly. UNCLASSIFIED means "
                "WE DO NOT KNOW WHAT THIS TOOL DOES and is distinct from the "
                "empty set, which means inert. The damage is not that it papers "
                "over a coverage gap - an unseen target's tools are "
                "UNCLASSIFIED until the manifest maps them, so one such rule "
                "would block everything on a new target and report 100% "
                "transfer, for free. That is the headline transfer result, "
                "manufactured.", t.line)
        if t.text not in CAP_CLASSES:
            raise ParseError(
                "E_UNKNOWN_CAP_CLASS",
                "%r is not one of the six classes: %s"
                % (t.text, ", ".join(CAP_CLASSES)), t.line)
        cap_class = t.text

        handles = []
        while self.at("PUNCT", ","):
            self.take()
            self.expect("WORD", "tool", what="the only qualifier is `tool:`")
            self.expect("PUNCT", ":")
            h = self.expect("WORD", what="a tool handle")
            if not TOOL_HANDLE_RE.match(h.text):
                raise ParseError(
                    "E_BAD_TOOL_HANDLE",
                    "%r is not `t_` plus eight hex. Handles are OPAQUE - the "
                    "ARMORER sees handles, never product tool names."
                    % h.text, h.line)
            handles.append("tool:" + h.text)
        return cap_class, handles

    def predicate(self):
        """`clause { "and" clause }`. CONJUNCTION ONLY.

        No disjunction, no negation, no arithmetic, no user functions, no loops.
        The evaluator must be TOTAL and TERMINATING so the TRIPWIRE is a pure
        function of its inputs, and every one of those constructs makes
        evaluation cost or termination input-dependent.
        """
        clauses = [self.clause()]
        while self.at("WORD", "and"):
            self.take()
            clauses.append(self.clause())
        return clauses

    def clause(self):
        if self.at("WORD", "preceded_by") and self.at("PUNCT", "(", 1):
            line = self.take().line
            self.expect("PUNCT", "(")
            t = self.expect("WORD", what="a capability class")
            if t.text == UNCLASSIFIED:
                raise ParseError(
                    "E_UNCLASSIFIED_SELECTOR",
                    "`preceded_by(UNCLASSIFIED)` is refused for the same reason "
                    "`cap:UNCLASSIFIED` is: it means we do not know, and a rule "
                    "may not bind to not-knowing.", t.line)
            if t.text not in CAP_CLASSES:
                raise ParseError("E_UNKNOWN_CAP_CLASS",
                                 "%r is not one of the six classes" % t.text,
                                 t.line)
            self.expect("PUNCT", ")")
            return Clause(form=CLAUSE_PRECEDED_BY, cap_class=t.text)

        if self.at("WORD", "episode_sum") and self.at("PUNCT", "(", 1):
            self.take()
            self.expect("PUNCT", "(")
            path = self.arg_path()
            self.expect("PUNCT", ")")
            op = self.cmp_op()
            t = self.expect("INT", what="episode_sum compares to an INTEGER")
            return Clause(form=CLAUSE_EPISODE_SUM, path=path, op=op,
                          value=int(t.text), value_type="int")

        path = self.arg_path()

        if self.at("WORD", "in"):
            self.take()
            return Clause(form=CLAUSE_ARG_IN_ENUM_LIST, path=path,
                          values=self.enum_list(), value_type="enum_list")

        if self.at("WORD", "is"):
            self.take()
            # GX5, ruling 42: `is` now takes either polarity, and ONLY these
            # two. Anything else is still a parse error, so the token after
            # `is` remains a closed set of exactly two words.
            if self.at("WORD", "present"):
                self.take()
                return Clause(form=CLAUSE_ARG_IS_PRESENT, path=path)
            self.expect("WORD", "absent",
                        what="`is` takes only `absent` or `present`")
            return Clause(form=CLAUSE_ARG_IS_ABSENT, path=path)

        op = self.cmp_op()

        if self.at("WORD", "episode") and self.at("PUNCT", ".", 1):
            self.take()
            self.take()
            t = self.expect("WORD", what="an episode context field")
            if t.text not in CONTEXT_FIELDS:
                raise ParseError(
                    "E_UNKNOWN_CONTEXT_FIELD",
                    "%r is not one of the three episode context fields: %s"
                    % (t.text, ", ".join(CONTEXT_FIELDS)), t.line)
            return Clause(form=CLAUSE_ARG_VS_EPISODE_CONTEXT, path=path, op=op,
                          context_field=t.text)

        value, value_type = self.literal()
        return Clause(form=CLAUSE_ARG_CMP_LITERAL, path=path, op=op,
                      value=value, value_type=value_type)

    def arg_path(self):
        t = self.expect("WORD", what="an argument path")
        if not IDENT_RE.match(t.text):
            raise ParseError(
                "E_BAD_ARG_PATH",
                "%r is not an identifier. An arg_path is lowercase-initial, so "
                "it can never be confused with an enum symbol." % t.text, t.line)
        parts = [t.text]
        while self.at("PUNCT", ".") and self.at("WORD", None, 1):
            self.take()
            p = self.take()
            if not IDENT_RE.match(p.text):
                raise ParseError("E_BAD_ARG_PATH",
                                 "%r is not an identifier" % p.text, p.line)
            parts.append(p.text)
        return ".".join(parts)

    def cmp_op(self):
        t = self.cur
        if t.kind == "OP" and t.text in CMP_OPS:
            self.take()
            return t.text
        raise ParseError(
            "E_EXPECTED_CMP_OP",
            "expected one of %s but found %r"
            % (" ".join(CMP_OPS), t.text or "end of input"), t.line)

    def literal(self):
        t = self.cur
        if t.kind == "INT":
            self.take()
            return int(t.text), "int"
        if t.kind == "WORD" and t.text in ("true", "false"):
            self.take()
            return t.text == "true", "bool"
        if t.kind == "WORD" and UPPER_SNAKE_RE.match(t.text):
            self.take()
            return t.text, "enum"
        raise ParseError(
            "E_BAD_LITERAL",
            "%r is not a literal. NO FREE STRINGS: a literal is an integer, a "
            "boolean, or an enum symbol the manifest declares for that exact "
            "path. That bound is what makes the held-out-family result true by "
            "construction rather than by discipline - a language that cannot "
            "express a string match cannot learn a string filter."
            % (t.text or "end of input"), t.line)

    def enum_list(self):
        self.expect("PUNCT", "[")
        members = []
        while True:
            t = self.expect("WORD", what="an enum symbol")
            if not UPPER_SNAKE_RE.match(t.text):
                raise ParseError("E_BAD_LITERAL",
                                 "%r is not an enum symbol" % t.text, t.line)
            members.append(t.text)
            if self.at("PUNCT", ","):
                self.take()
                continue
            break
        self.expect("PUNCT", "]")
        return tuple(members)

    def action(self):
        t = self.cur
        if self.at("WORD", "deny"):
            self.take()
            return Action(verb="deny")

        if self.at("WORD", "constrain_arg"):
            self.take()
            self.expect("PUNCT", "(")
            path = self.arg_path()
            op = self.cmp_op()
            value, value_type = self.literal()
            self.expect("PUNCT", ")")
            return Action(verb="constrain_arg", path=path, op=op, value=value,
                          value_type=value_type)

        if self.at("WORD", "require_approval"):
            self.take()
            self.expect("PUNCT", "(")
            rc = self.expect("WORD", what="a reason code")
            if not UPPER_SNAKE_RE.match(rc.text):
                raise ParseError(
                    "E_BAD_REASON_CODE",
                    "%r is not a reason code. An enum symbol, never free text - "
                    "a reason code that could carry prose would be a hole in "
                    "the no-free-strings bar." % rc.text, rc.line)
            self.expect("PUNCT", ")")
            return Action(verb="require_approval", reason_code=rc.text)

        raise ParseError(
            "E_UNKNOWN_VERB",
            "%r is not a verb. THREE VERBS AND THERE IS NO FOURTH: deny, "
            "constrain_arg, require_approval. There is also no `allow` verb - "
            "the policy is SUBTRACTIVE ONLY, so no sequence of patches can "
            "widen the target's blast radius." % (t.text or "end of input"),
            t.line)

    def origin(self):
        if self.at("WORD", "seed"):
            self.take()
            return "seed"
        if self.at("WORD", "armorer"):
            self.take()
            self.expect("PUNCT", ":")
            t = self.expect("INT", what="the round number")
            return "armorer:%d" % int(t.text)
        raise ParseError("E_BAD_ORIGIN",
                         "origin is `seed` or `armorer:<round>`, not %r"
                         % self.cur.text, self.cur.line)


def parse_policy(text: str) -> ParsedPatch:
    """Parse `{ rule | retraction }` into a ParsedPatch. Raises ParseError."""
    return _Parser(text).parse_patch()


def parse_rule(text: str) -> ParsedRule:
    """Parse exactly one `rule` statement. Convenience over parse_policy."""
    patch = parse_policy(text)
    if len(patch.rules) != 1 or patch.retractions:
        raise ParseError(
            "E_NOT_ONE_RULE",
            "expected exactly one rule, found %d rules and %d retractions"
            % (len(patch.rules), len(patch.retractions)))
    return patch.rules[0]
