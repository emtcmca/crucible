"""strawman.py - DELIBERATELY WRONG input adapters, kept in the tree forever.

Not dead code, not drafts. These are the proof that the blindness tests in
`tests/test_armorer_blindness.py` can fail.

CONVENTIONS.md section 8 rule 2: a check that cannot fail is not measuring
anything. On 2026-08-20 the contract gate's own first negative test could not
fail - it appended a trailing newline, which is exactly the mutation the
normalization exists to absorb. It looked green for the same reason a broken
smoke detector looks quiet.

Each entry declares BY NAME the checks it MUST fail. If a strawman ever passes
one of them, THE SUITE IS REPORTED BROKEN - not the strawman - because a check a
known-wrong adapter passes has stopped testing the property it claims to test.

Every one of these is an implementation somebody would actually write:

  passthrough          the adapter nobody wrote. The CORONER's record IS the
                       ARMORER's input, which is the design the C5 contract
                       exists to forbid.
  denylist_projection  "the adapter reads named fields only", written as a
                       DENYLIST. It blocks `recommended_fix` and `mitigation`
                       and lets `generalization_hypothesis` through - WHICH IS
                       EXACTLY THE DEFECT C5's KNOWN_BAD FIXTURE CARRIES. The
                       prose arrived under a name nobody had denied yet.
  lint_only            an allowlist that admits `human_only` and then runs a
                       modal-verb lint over it. THE ONE THE BRIEF NAMES: a
                       hypothesis phrased as a DESCRIPTION carries no modal verb
                       and passes. "Any composition of CAP_INVOKES_AGENT
                       followed by CAP_MOVES_MONEY is reachable" is rule r019,
                       in English, and it contains no `should`.
  raw_args             CORRECT at the top level and wrong one layer down: it
                       copies `args_redacted` verbatim. C5 types that field as a
                       bare object with no value restriction, so a free string in
                       an argument is an open channel that the top-level
                       allowlist does not close. THE SUBTLEST OF THE FOUR, and
                       the only one that looks right on review.
"""

import copy
import re

# --------------------------------------------------------------------------

def passthrough(record):
    """No adapter at all."""
    return copy.deepcopy(record)


PASSTHROUGH_MUST_FAIL = {
    "B1": "the human_only subtree is copied verbatim, prose and all.",
    "B2": "human_only is addressable because everything is addressable.",
    "B3": "args_redacted is copied verbatim.",
}


# --------------------------------------------------------------------------

_DENIED = ("recommended_fix", "fix", "mitigation", "remediation")


def denylist_projection(record):
    """Reads named fields only - as a denylist. The defence C5 says fails."""
    return {k: copy.deepcopy(v) for k, v in record.items() if k not in _DENIED}


DENYLIST_MUST_FAIL = {
    "B1": "`human_only` is not on the denylist because nobody thought of it, "
          "and neither is `generalization_hypothesis`. A denylist is a list of "
          "the names you already regret; the next one has a new name.",
    "B2": "human_only survives untouched.",
    "B3": "args_redacted survives untouched.",
}


# --------------------------------------------------------------------------

_MODAL = re.compile(
    r"\b(should|must|recommend|recommended|ought|suggest|need to|propose)\b",
    re.IGNORECASE)


def lint_only(record):
    """Allowlist plus a prescriptive-language lint over the prose it admits.

    This is the design the brief calls insufficient, and it is insufficient for a
    reason that is easy to miss on review: the lint tests the GRAMMATICAL MOOD of
    the sentence, and a rule can be stated in the indicative.
    """
    out = {}
    for key in ("capability_classes_involved", "offending_tool_calls",
                "invariant_id", "round_index", "autopsy_id", "human_only"):
        if key in record:
            out[key] = copy.deepcopy(record[key])
    prose = " ".join(str(v) for v in (out.get("human_only") or {}).values())
    if _MODAL.search(prose):
        raise ValueError("E_PRESCRIPTIVE_LANGUAGE")
    return out


LINT_ONLY_MUST_FAIL = {
    "B1": "the adversarial record states the fix in the INDICATIVE. No modal "
          "verb, no `recommend`, and the lint has nothing to catch.",
    "B2": "human_only is in the allowlist, so the adapter can address it.",
    "B3": "args_redacted is copied verbatim.",
}


# --------------------------------------------------------------------------

_TOP = ("capability_classes_involved", "offending_tool_calls", "invariant_id",
        "round_index", "autopsy_id")
_CALL = ("tool_handle", "capability_classes", "seq", "args_redacted",
         "policy_decision", "status")


def raw_args(record):
    """The correct allowlist, one layer too shallow."""
    out = {k: copy.deepcopy(record[k]) for k in _TOP if k in record}
    out["offending_tool_calls"] = [
        {k: copy.deepcopy(c[k]) for k in _CALL if k in c}
        for c in record.get("offending_tool_calls", [])
    ]
    return out


RAW_ARGS_MUST_FAIL = {
    "B3": "`args_redacted` is typed in C5 as a bare object. Nothing in the "
          "schema stops a string of any length or content from riding in one, "
          "and this adapter forwards it. B1 and B2 PASS here, which is the "
          "point: an adapter can be right about the field list and still leave "
          "the channel open one level down.",
}


# --------------------------------------------------------------------------
STRAWMEN = {
    "passthrough": (passthrough, PASSTHROUGH_MUST_FAIL),
    "denylist_projection": (denylist_projection, DENYLIST_MUST_FAIL),
    "lint_only": (lint_only, LINT_ONLY_MUST_FAIL),
    "raw_args": (raw_args, RAW_ARGS_MUST_FAIL),
}
