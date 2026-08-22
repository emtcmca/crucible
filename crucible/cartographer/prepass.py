"""prepass.py - deterministic capability pre-pass for CAPABILITY_CARTOGRAPHER.

Plain English first. `architecture-spec.md:138` specifies the Cartographer's job
as proposing capability classes "for each tool the deterministic pre-pass could
not resolve." That sentence presupposes a pre-pass. `gemma-scope.md` section 6
checked on 2026-08-21 that no such thing existed anywhere in this repository -
the eight tools in `target/refund_agent/capability_manifest.json` were
classified by a human. This module is that missing pre-pass, and it is
deliberately built and evaluated BEFORE any model is wired in, per the memo's
own reasoning: "a model asked to classify everything is doing work a `str`
comparison should have done, and its mistakes are then indistinguishable from
its judgments."

WHAT THIS DOES AND DOES NOT DO.

`classify_tool` is pure code: no model call, no file I/O, no network, no
randomness. It looks at ONE tool's declared shape - its name, its docstring,
and its argument names/types/descriptions - and asks whether that shape alone
is enough to place the tool in one or more of the six capability classes
defined in `target/refund_agent/capabilities.py`. Six classes, one sentinel:

    CAP_MOVES_MONEY, CAP_EXTERNAL_COMMS, CAP_MUTATES_DURABLE_STATE,
    CAP_READS_PII, CAP_ESCALATES_PRIVILEGE, CAP_INVOKES_AGENT      (the six)
    UNCLASSIFIED                                                   (the sentinel)

This module intentionally does NOT import that file. The pre-pass has to
generalize to an agent this project never wrote and whose source may not even
be Python - importing the target's own class tuple would quietly couple a
supposedly foreign-agent-facing tool to our own fixture. The six strings are
repeated here, in the same order and spelling CONVENTIONS.md 2.2 fixes
(`CAP_MOVES_MONEY` first, `CAP_INVOKES_AGENT` last) - a project-wide constant,
not something this module owns or may drift from independently.

WHY EVERY RESOLUTION CARRIES EVIDENCE.

A classification with no citable evidence is a guess wearing a confidence
number. `evidence` on a resolved result is a tuple of
`{"capability_class": ..., "citation": ...}` entries, and the citation always
names the argument (and, where relevant, the exact docstring text) that
produced it - so a human reviewing the proposal can check the claim against
the tool signature directly, without re-running anything.

WHY `UNCLASSIFIED` IS A CORRECT ANSWER, NOT A FAILURE TO ANSWER.

`capabilities.py`'s module docstring draws the line this pass has to respect:
UNCLASSIFIED means "we do not know", the empty set means "we know and it is
nothing". This module never returns the empty set - if no rule fires, the tool
is UNCLASSIFIED, `resolved` is False, and that result is the handoff to
whatever runs next (the Cartographer's model, or a human). A pre-pass that
always finds something is worse than one that admits what a signature alone
cannot tell it - see `docs/decisions-pending/gemma-scope.md` section 6.
"""

import inspect
import re

# The six, in CONVENTIONS.md 2.2's canonical order and spelling. Duplicated
# here on purpose - see the module docstring on why this file does not import
# target/refund_agent/capabilities.py.
CAPABILITY_CLASSES = (
    "CAP_MOVES_MONEY",
    "CAP_EXTERNAL_COMMS",
    "CAP_MUTATES_DURABLE_STATE",
    "CAP_READS_PII",
    "CAP_ESCALATES_PRIVILEGE",
    "CAP_INVOKES_AGENT",
)
UNCLASSIFIED = "UNCLASSIFIED"

_CLASS_RANK = {c: i for i, c in enumerate(CAPABILITY_CLASSES)}

# --------------------------------------------------------------------------
# Rules. Each is a plain function: (arg_names, arg_by_name) -> list of
# (capability_class, citation, rule_confidence) or []. Kept as small,
# independent functions rather than one long body so each rule's evidence
# text lives next to the pattern that produced it, and so a rule can be added
# or removed without touching the others.
#
# Every pattern here keys on something a TOOL SIGNATURE can actually
# establish - an argument's name, or a description string the tool's own
# author wrote for that argument. None of them look at what the tool was
# ever called with, what it returned, or anything about an attack - the
# Cartographer's own "blind to the attack corpus" boundary (architecture-
# spec.md:138) starts here, one layer below it.
# --------------------------------------------------------------------------

_AMOUNT_RE = re.compile(r"(?i:amount)")
_CURRENCY_RE = re.compile(r"(?i:currency)")
_STATUS_TARGET_RE = re.compile(r"(?i:^status_to$|^status$|_status$)")
_AGENT_DEST_RE = re.compile(r"(?i:^specialist_agent$|^agent_name$|_agent$)")
_QUEUE_RE = re.compile(r"(?i:^queue$|^escalation_queue$)")
_EMAIL_DOC_RE = re.compile(r"(?i:email address)")


def _rule_money(arg_names, arg_by_name):
    """An amount-shaped argument alongside a currency argument implies the
    tool moves or references a sum of money (candidate rule, gemma-scope
    prompt: "an argument named like a payment instrument, amount, or
    currency implies money movement")."""
    amount_arg = next((n for n in arg_names if _AMOUNT_RE.search(n)), None)
    currency_arg = next((n for n in arg_names if _CURRENCY_RE.search(n)), None)
    if amount_arg and currency_arg:
        return [(
            "CAP_MOVES_MONEY",
            "argument '%s' is amount-shaped and argument '%s' is a currency "
            "code - together they name a sum of money the tool handles"
            % (amount_arg, currency_arg),
            0.7,
        )]
    return []


def _rule_email_destination(arg_names, arg_by_name):
    """An argument named 'to' whose own description identifies it as an
    email address implies both external communication (the message leaves
    the system) and a PII read (an email address is personal data, and the
    tool's signature says it holds one)."""
    out = []
    arg = arg_by_name.get("to")
    if arg is not None:
        desc = (arg.get("description") or "")
        if _EMAIL_DOC_RE.search(desc):
            citation = "argument 'to', documented as \"%s\"" % desc.strip()
            out.append(("CAP_EXTERNAL_COMMS",
                        citation + " - a destination email address leaving the system",
                        0.85))
            out.append(("CAP_READS_PII",
                        citation + " - an email address is personal data",
                        0.6))
    return out


def _rule_state_mutation(arg_names, arg_by_name):
    """An argument naming a state-transition target ('status_to', or a
    '*_status'/'status' argument) implies the tool writes durable state."""
    for name in arg_names:
        if _STATUS_TARGET_RE.match(name):
            return [(
                "CAP_MUTATES_DURABLE_STATE",
                "argument '%s' names a state-transition target, implying "
                "the tool persists a status change" % name,
                0.75,
            )]
    return []


def _rule_agent_invocation(arg_names, arg_by_name):
    """An argument naming another agent ('specialist_agent', '*_agent',
    'agent_name') implies the tool hands the case to another software agent."""
    for name in arg_names:
        if _AGENT_DEST_RE.match(name):
            return [(
                "CAP_INVOKES_AGENT",
                "argument '%s' names a destination software agent, implying "
                "the tool invokes another agent" % name,
                0.85,
            )]
    return []


def _rule_privileged_queue(arg_names, arg_by_name):
    """An argument named 'queue' (or 'escalation_queue') routes the case to a
    named handling tier, implying privilege escalation."""
    for name in arg_names:
        if _QUEUE_RE.match(name):
            arg = arg_by_name.get(name) or {}
            desc = (arg.get("description") or "").strip()
            suffix = ' ("%s")' % desc if desc else ""
            return [(
                "CAP_ESCALATES_PRIVILEGE",
                "argument '%s'%s routes the case to a named handling tier, "
                "implying escalation to a higher-privilege handler" % (name, suffix),
                0.65,
            )]
    return []


_RULES = (
    _rule_money,
    _rule_email_destination,
    _rule_state_mutation,
    _rule_agent_invocation,
    _rule_privileged_queue,
)


def classify_tool(spec: dict) -> dict:
    """Classify one tool from its declared shape. Pure code - no model, no I/O.

    `spec` mirrors the input architecture-spec.md:148-150 describes for the
    Cartographer proper:
        {
          "tool_name": str,
          "docstring": str,                     # optional, full docstring
          "args": [
              {"name": str, "type": str, "description": str}, ...
          ],
          "declaring_agent": str,                # optional
          "transport": str,                      # optional: function / MCP / ...
          "mcp_annotations": dict,                # optional
        }
    Only `tool_name` and `args` are read by the rules above; the remaining
    fields are accepted so the same spec this pre-pass declines can be handed
    straight to the Cartographer without reshaping it.

    Returns:
        {"tool_name": str, "classes": tuple[str, ...], "confidence": float,
         "evidence": tuple[dict, ...], "resolved": bool}

    `resolved: False` with `classes: (UNCLASSIFIED,)` is a correct, expected
    output when no rule fires - see the module docstring. It is never
    suppressed or padded to look more decisive than the signature supports.
    """
    tool_name = spec.get("tool_name", "")
    args = spec.get("args") or []
    arg_names = [a.get("name", "") for a in args if a.get("name")]
    arg_by_name = {a.get("name", ""): a for a in args if a.get("name")}

    findings = []
    for rule in _RULES:
        findings.extend(rule(arg_names, arg_by_name))

    if not findings:
        return {
            "tool_name": tool_name,
            "classes": (UNCLASSIFIED,),
            "confidence": 0.0,
            "evidence": (),
            "resolved": False,
        }

    classes_seen = sorted({c for c, _citation, _conf in findings},
                          key=lambda c: _CLASS_RANK[c])
    evidence = tuple(
        {"capability_class": c, "citation": citation}
        for c, citation, _conf in findings
    )
    confidence = round(sum(conf for _c, _cit, conf in findings) / len(findings), 2)

    return {
        "tool_name": tool_name,
        "classes": tuple(classes_seen),
        "confidence": confidence,
        "evidence": evidence,
        "resolved": True,
    }


# --------------------------------------------------------------------------
# Spec construction helper. NOT part of classify_tool's contract - a
# convenience for building the input shape from a live bare Python function,
# used by this pre-pass's own agreement check and available to anything else
# that wants to point classify_tool at a plain-function tool. It reads only
# the function's signature and docstring: no capability table, no manifest,
# nothing target-specific.
# --------------------------------------------------------------------------

_ARG_LINE_RE = re.compile(r"^\s{4,8}(\w+)(?:\s*\([^)]*\))?:\s?(.*)$")


def _parse_google_docstring_args(docstring: str) -> dict:
    """Pull {arg_name: description} out of a Google-style 'Args:' block.

    Deliberately simple: takes the first line of each argument's
    description and stops at the next top-level section ('Returns:' etc.)
    or a blank line followed by a non-indented line. Good enough to recover
    the one-line descriptions this module's rules read; not a docstring
    parser for its own sake.
    """
    if not docstring:
        return {}
    lines = docstring.splitlines()
    out = {}
    in_args = False
    for line in lines:
        stripped = line.strip()
        if stripped == "Args:":
            in_args = True
            continue
        if in_args and stripped in ("Returns:", "Raises:", "Yields:"):
            break
        if in_args:
            m = _ARG_LINE_RE.match(line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


def tool_spec_from_function(fn, *, declaring_agent=None, transport="function") -> dict:
    """Build a classify_tool() spec from a live bare Python function.

    Reads `inspect.signature` for argument names/types and the function's
    own docstring for per-argument descriptions - exactly the introspection
    available to anything that turns a Python callable into a tool schema
    for an LLM (ADK, MCP, function calling). Uses no information beyond
    what such a schema builder would already have.
    """
    doc = inspect.getdoc(fn) or ""
    arg_docs = _parse_google_docstring_args(doc)
    sig = inspect.signature(fn)
    args = []
    for name, param in sig.parameters.items():
        ann = param.annotation
        type_name = getattr(ann, "__name__", None) or (
            None if ann is inspect._empty else str(ann)
        )
        args.append({
            "name": name,
            "type": type_name,
            "description": arg_docs.get(name, ""),
        })
    return {
        "tool_name": fn.__name__,
        "docstring": doc,
        "args": args,
        "declaring_agent": declaring_agent,
        "transport": transport,
        "mcp_annotations": {},
    }
