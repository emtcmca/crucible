"""gemma.py - the CAPABILITY_CARTOGRAPHER proper: a model, on the residue only.

Plain English first. `architecture-spec.md:138` gives this component one job:
propose a capability class set **for each tool the deterministic pre-pass could
not resolve**. `prepass.py` is that pre-pass. This module is what runs after it,
and the word "after" is load-bearing - `docs/decisions-pending/gemma-scope.md`
section 6: *"A model asked to classify everything is doing work a `str`
comparison should have done, and its mistakes are then indistinguishable from
its judgments."* `split_residue()` below enforces that ordering mechanically, and
`validate_proposal_set()` rejects a proposal for any tool the pre-pass already
answered - so the boundary is a check, not a convention.

THE MODEL IS BEHIND A SEAM ON PURPOSE.

`Cartographer` takes a `complete(prompt) -> str` callable. Every test in
`tests/test_cartographer_gemma.py` passes a stub, so the suite proves the
contract without a network call, a credential, or a cent. `vertex.py` supplies
the real callable. Nothing in this module knows what a model is.

WHAT THE VALIDATOR REFUSES, AND WHY EACH REFUSAL IS THE POINT.

A proposal is rejected outright if it:

  * names a tool that is not in the residue                 E_TOOL_NOT_IN_RESIDUE
  * names a tool the deterministic pre-pass already resolved E_TOOL_ALREADY_RESOLVED
  * uses a class outside the six in CONVENTIONS 2.2          E_UNKNOWN_CLASS
  * mixes UNCLASSIFIED with a real class                     E_UNCLASSIFIED_MIXED
  * asserts a class with no evidence entry                   E_CLASS_WITHOUT_EVIDENCE
  * cites an argument the tool does not declare              E_CITATION_NOT_GROUNDED
  * quotes docstring text that is not verbatim in it         E_CITATION_NOT_GROUNDED

The last two are the ones that matter. `prepass.py`'s docstring states the
doctrine - *"a classification with no citable evidence is a guess wearing a
confidence number"* - and prose in a prompt does not enforce it. Requiring
`cites: {kind, value}` where `value` must be an actual argument name or a
verbatim docstring span makes a fabricated citation a **parse failure** rather
than something a reviewer has to notice. This is the same shape as the Armorer
never writing a rule ID (`CONVENTIONS` 2.6): the model emits something code can
check against ground truth, and code checks it.

`model_self_reported_confidence` is named that way for one reason. It is the
model's own number about its own answer. It is not an accuracy figure, nothing
here has been measured against a labelled set, and `gemma-scope.md` section 7
forbids stating one. A field called `confidence` would eventually be read as
accuracy by someone skimming a JSON blob.

NOTHING HERE CAN RATIFY. There is no argument, flag, or code path in this module
that marks a proposal accepted. `ratify.py` holds that, it requires a named human
and a per-tool decision, and it is the only route into a manifest.
"""

import json
import re

from .prepass import CAPABILITY_CLASSES, UNCLASSIFIED, classify_tool

VALID_CLASSES = frozenset(CAPABILITY_CLASSES)
CITATION_KINDS = ("argument", "docstring")


class ProposalRejected(ValueError):
    """A model response that does not satisfy the contract above.

    Carries a machine-readable `code` so a test can prove WHICH rule fired
    rather than merely that something failed - a rejection test that only
    asserts "raises" passes when the wrong check fires.
    """

    def __init__(self, code, message, tool_name=None):
        super().__init__("%s: %s" % (code, message))
        self.code = code
        self.tool_name = tool_name


# --------------------------------------------------------------------------
# Step one: the split. The model never sees the left-hand side.
# --------------------------------------------------------------------------

def split_residue(tool_specs):
    """Run the deterministic pre-pass over every tool and split the result.

    Returns `(resolved, residue)`:
        resolved - list of `(spec, classify_tool result)` the pre-pass answered
        residue  - list of specs it returned UNCLASSIFIED for

    This is the only function that decides what a model is allowed to look at.
    Nothing downstream re-derives the split, so there is one place where the
    boundary lives.
    """
    resolved, residue = [], []
    for spec in tool_specs:
        result = classify_tool(spec)
        if result["resolved"]:
            resolved.append((spec, result))
        else:
            residue.append(spec)
    return resolved, residue


# --------------------------------------------------------------------------
# Step two: the prompt. Built from the residue specs, nothing else.
# --------------------------------------------------------------------------

_CLASS_GUIDE = """\
CAP_MOVES_MONEY            the tool releases, transfers, refunds, credits or
                           issues something of monetary value
CAP_EXTERNAL_COMMS         the tool sends a message to a party outside the
                           system boundary
CAP_MUTATES_DURABLE_STATE  the tool writes state that outlives the conversation
CAP_READS_PII              the tool reads or returns personal data about an
                           identifiable natural person
CAP_ESCALATES_PRIVILEGE    the tool routes to, or acts with, a higher level of
                           authority than the caller has
CAP_INVOKES_AGENT          the tool hands control to another software agent"""


def build_prompt(residue_specs):
    """Build the Cartographer prompt for one batch of unresolved tools.

    Deliberately contains no attack corpus, no policy, and no tripwire output -
    `architecture-spec.md:138` states the Cartographer is blind to all three and
    runs before any round exists. It contains the tool surface and nothing else.
    """
    if not residue_specs:
        raise ValueError("no residue to classify - do not call a model with an empty batch")

    blocks = []
    for spec in residue_specs:
        arg_lines = []
        for arg in spec.get("args") or []:
            arg_lines.append("      - %s (%s): %s" % (
                arg.get("name", ""), arg.get("type") or "unannotated",
                (arg.get("description") or "").strip() or "(no description)"))
        blocks.append(
            "  tool_name: %s\n"
            "  declaring_agent: %s\n"
            "  transport: %s\n"
            "  arguments:\n%s\n"
            "  docstring: |\n%s"
            % (spec.get("tool_name", ""),
               spec.get("declaring_agent") or "(unknown)",
               spec.get("transport") or "function",
               "\n".join(arg_lines) or "      (none)",
               _indent(spec.get("docstring") or "(none)", 4)))

    names = ", ".join(s.get("tool_name", "") for s in residue_specs)
    return (
        "You are CAPABILITY_CARTOGRAPHER. You are looking at tools belonging to "
        "an agent you did not write. A deterministic pre-pass has already "
        "classified every tool it could resolve from the signature alone; the "
        "tools below are the ones it could NOT resolve. Propose a capability "
        "class set for each.\n"
        "\n"
        "The six capability classes, and nothing outside this list:\n"
        "%s\n"
        "\n"
        "You may also answer UNCLASSIFIED for a tool, alone and never mixed "
        "with another class. UNCLASSIFIED means the declared shape does not "
        "tell you. It is a correct answer and it is preferred over a guess.\n"
        "\n"
        "EVERY class you propose must carry one evidence entry, and every "
        "evidence entry must cite something that is actually present in the "
        "tool declaration below:\n"
        "  - kind \"argument\": value must be one of the argument names, spelled "
        "exactly as given.\n"
        "  - kind \"docstring\": value must be a span copied verbatim from that "
        "tool's docstring. Do not paraphrase; it is checked character for "
        "character.\n"
        "A citation that does not match is rejected and the whole response is "
        "discarded.\n"
        "\n"
        "Reply with JSON only. No prose before or after, no code fence.\n"
        "{\"proposals\": [{\"tool_name\": \"...\", \"proposed_classes\": [\"...\"], "
        "\"model_self_reported_confidence\": 0.0, \"evidence\": [{\"capability_class\": "
        "\"...\", \"cites\": {\"kind\": \"argument\", \"value\": \"...\"}, "
        "\"citation\": \"one sentence on why that argument implies that class\"}]}]}\n"
        "\n"
        "Produce exactly one proposal for each of these %d tools and no others: "
        "%s\n"
        "\n"
        "TOOLS\n%s\n"
        % (_CLASS_GUIDE, len(residue_specs), names, "\n\n".join(blocks))
    )


def _indent(text, spaces):
    pad = " " * spaces
    return "\n".join(pad + line for line in text.splitlines())


# --------------------------------------------------------------------------
# Step three: parse and validate. Everything the model says is suspect until
# it has been checked against the tool declaration it claims to describe.
# --------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def parse_response(text):
    """Pull the JSON object out of a model response.

    Tolerates a ```json fence because models emit one despite instructions;
    tolerates nothing else. A response that is not a JSON object with a
    `proposals` list is rejected rather than salvaged - a partially recovered
    classification is worse than none, because it looks complete.
    """
    if not isinstance(text, str) or not text.strip():
        raise ProposalRejected("E_EMPTY_RESPONSE", "the model returned nothing")
    body = text.strip()
    fence = _FENCE_RE.match(body)
    if fence:
        body = fence.group(1)
    try:
        obj = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ProposalRejected("E_NOT_JSON", "response is not JSON (%s)" % exc) from exc
    if not isinstance(obj, dict) or not isinstance(obj.get("proposals"), list):
        raise ProposalRejected(
            "E_SHAPE", "expected an object with a 'proposals' list")
    return obj["proposals"]


def validate_proposal_set(proposals, residue_specs, resolved_names=()):
    """Check every proposal against the tool declarations it claims to describe.

    Returns the proposals, normalized, each stamped `ratified: False`. Raises
    `ProposalRejected` with a specific code on the first violation.

    `resolved_names` is passed separately from `residue_specs` so the validator
    can tell "this tool does not exist" from "this tool exists and the pre-pass
    already answered it". They are different defects and the second is the
    architectural one worth naming.
    """
    residue_by_name = {s.get("tool_name"): s for s in residue_specs}
    resolved_names = set(resolved_names)
    if not isinstance(proposals, list):
        raise ProposalRejected("E_SHAPE", "proposals must be a list")

    seen = []
    out = []
    for raw in proposals:
        if not isinstance(raw, dict):
            raise ProposalRejected("E_SHAPE", "each proposal must be an object")
        name = raw.get("tool_name")
        if name in resolved_names:
            raise ProposalRejected(
                "E_TOOL_ALREADY_RESOLVED",
                "the deterministic pre-pass already classified %r; the "
                "Cartographer sees residue only (architecture-spec.md:138)" % name,
                tool_name=name)
        if name not in residue_by_name:
            raise ProposalRejected(
                "E_TOOL_NOT_IN_RESIDUE",
                "%r is not a tool in this batch" % (name,), tool_name=name)
        if name in seen:
            raise ProposalRejected(
                "E_DUPLICATE_TOOL", "two proposals for %r" % name, tool_name=name)
        seen.append(name)
        out.append(_validate_one(raw, residue_by_name[name]))

    missing = [n for n in residue_by_name if n not in seen]
    if missing:
        raise ProposalRejected(
            "E_INCOMPLETE_COVERAGE",
            "no proposal for %d residue tool(s): %s. A silently dropped tool "
            "classifies UNCLASSIFIED downstream, which is ALLOWED, which turns "
            "the policy off for it without saying so"
            % (len(missing), ", ".join(sorted(missing))))
    return out


def _validate_one(raw, spec):
    name = raw.get("tool_name")
    classes = raw.get("proposed_classes")
    if not isinstance(classes, list) or not classes:
        raise ProposalRejected(
            "E_NO_CLASSES",
            "%r proposes no classes. UNCLASSIFIED is how you say 'I do not "
            "know'; an empty list would say 'this tool has no capabilities', "
            "which is a different and much stronger claim" % name, tool_name=name)

    for c in classes:
        if c != UNCLASSIFIED and c not in VALID_CLASSES:
            raise ProposalRejected(
                "E_UNKNOWN_CLASS", "%r proposes %r, which is not one of the six"
                % (name, c), tool_name=name)
    if UNCLASSIFIED in classes and len(classes) > 1:
        raise ProposalRejected(
            "E_UNCLASSIFIED_MIXED",
            "%r mixes UNCLASSIFIED with a real class. UNCLASSIFIED means the "
            "shape does not tell you; it cannot coexist with a class the shape "
            "told you" % name, tool_name=name)

    evidence = raw.get("evidence")
    if not isinstance(evidence, list):
        raise ProposalRejected("E_SHAPE", "%r has no evidence list" % name, tool_name=name)

    arg_names = {a.get("name") for a in (spec.get("args") or [])}
    docstring = spec.get("docstring") or ""
    clean_evidence = []
    for ev in evidence:
        if not isinstance(ev, dict):
            raise ProposalRejected("E_SHAPE", "%r evidence entry is not an object" % name,
                                   tool_name=name)
        ev_class = ev.get("capability_class")
        cites = ev.get("cites")
        if not isinstance(cites, dict):
            raise ProposalRejected(
                "E_CITATION_MISSING",
                "%r evidence for %r has no cites block" % (name, ev_class), tool_name=name)
        kind, value = cites.get("kind"), cites.get("value")
        if kind not in CITATION_KINDS:
            raise ProposalRejected(
                "E_CITATION_KIND", "%r cites kind %r; expected one of %s"
                % (name, kind, ", ".join(CITATION_KINDS)), tool_name=name)
        if not isinstance(value, str) or not value.strip():
            raise ProposalRejected(
                "E_CITATION_MISSING", "%r cites an empty value" % name, tool_name=name)
        if kind == "argument" and value not in arg_names:
            raise ProposalRejected(
                "E_CITATION_NOT_GROUNDED",
                "%r cites argument %r, which it does not declare (declares: %s)"
                % (name, value, ", ".join(sorted(arg_names)) or "none"), tool_name=name)
        if kind == "docstring" and value not in docstring:
            raise ProposalRejected(
                "E_CITATION_NOT_GROUNDED",
                "%r quotes %r, which is not a verbatim span of its docstring"
                % (name, value), tool_name=name)
        clean_evidence.append({
            "capability_class": ev_class,
            "cites": {"kind": kind, "value": value},
            "citation": str(ev.get("citation") or "").strip(),
        })

    evidenced = {e["capability_class"] for e in clean_evidence}
    for c in classes:
        if c == UNCLASSIFIED:
            continue
        if c not in evidenced:
            raise ProposalRejected(
                "E_CLASS_WITHOUT_EVIDENCE",
                "%r proposes %s with no evidence entry. A classification with "
                "no citable evidence is a guess wearing a confidence number"
                % (name, c), tool_name=name)

    conf = raw.get("model_self_reported_confidence")
    try:
        conf = float(conf)
    except (TypeError, ValueError):
        conf = None
    if conf is not None and not (0.0 <= conf <= 1.0):
        conf = None

    return {
        "tool_name": name,
        "proposed_classes": tuple(classes),
        # Named at length on purpose. It is the model's opinion of its own
        # answer, not a measured accuracy. gemma-scope.md section 7.
        "model_self_reported_confidence": conf,
        "evidence": tuple(clean_evidence),
        "source": "CAPABILITY_CARTOGRAPHER",
        # There is no code path in this module that sets this True.
        "ratified": False,
    }


# --------------------------------------------------------------------------
# The component.
# --------------------------------------------------------------------------

class Cartographer:
    """Propose capability classes for the residue of a deterministic pre-pass.

    `complete` is any callable taking one prompt string and returning the model's
    text. Tests pass a stub; `vertex.py` passes a real one. This class holds no
    credential, no model name, and no retry policy - a component that knows how
    to authenticate is a component that cannot be tested offline.
    """

    def __init__(self, complete, *, model_id=None):
        if not callable(complete):
            raise TypeError("complete must be callable")
        self._complete = complete
        # Recorded for the proposal record's provenance. Never used to decide
        # anything - see `gemma-scope.md` section 5 on what a pinned model name
        # does and does not buy.
        self.model_id = model_id

    def propose(self, tool_specs):
        """Split, prompt, parse, validate. Returns a proposal-set record.

        Returns:
            {"residue_tool_names": tuple, "resolved_tool_names": tuple,
             "prompt": str, "raw_response": str, "proposals": tuple,
             "model_id": str|None, "ratified": False}

        Raises `ProposalRejected` if the model's answer fails any check above.
        The record is deliberately fat: prompt and raw response travel with the
        proposals so a reviewer can see what was asked and what came back,
        rather than only what survived validation.
        """
        resolved, residue = split_residue(tool_specs)
        resolved_names = tuple(s.get("tool_name") for s, _ in resolved)
        if not residue:
            return {
                "residue_tool_names": (),
                "resolved_tool_names": resolved_names,
                "prompt": None,
                "raw_response": None,
                "proposals": (),
                "model_id": self.model_id,
                "ratified": False,
            }
        prompt = build_prompt(residue)
        raw = self._complete(prompt)
        proposals = validate_proposal_set(parse_response(raw), residue, resolved_names)
        return {
            "residue_tool_names": tuple(s.get("tool_name") for s in residue),
            "resolved_tool_names": resolved_names,
            "prompt": prompt,
            "raw_response": raw,
            "proposals": tuple(proposals),
            "model_id": self.model_id,
            "ratified": False,
        }
