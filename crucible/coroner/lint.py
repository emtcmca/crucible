"""lint.py - the prescriptive-language lint over the CORONER's free text.

WHAT THIS IS FOR, AND WHAT IT IS NOT FOR
-----------------------------------------
It is NOT the enforcement. The enforcement is `crucible/armorer/adapter.py`,
which cannot address `human_only.*` at all. This lint runs one layer earlier and
serves the HUMAN reader: an autopsy whose narrative has drifted into writing
policy is a CORONER that is behaving wrongly even though nothing downstream can
act on it, and the drift is worth seeing before it becomes a habit.

Stating the limit plainly, because the brief and C5 both insist on it:

    A HYPOTHESIS PHRASED AS A DESCRIPTION PASSES THIS LINT.

"Any composition of CAP_INVOKES_AGENT followed by CAP_MOVES_MONEY is reachable"
IS rule r019, in English, in the indicative, with no modal verb anywhere. This
lint cannot catch it and no lint can, because the defect is in the SEMANTICS and
the lint reads the MOOD. That sentence is why the projection exists, and anyone
who reads a green lint result as "the CORONER did not propose a fix" has drawn
exactly the wrong conclusion.

It is reported as findings rather than raised as an error. A record that trips it
is still a valid record - the material is unreachable either way - and refusing
to write an autopsy because its prose was bossy would lose the diagnosis over a
matter of tone.
"""

import re
from dataclasses import dataclass
from typing import List

# Modal and prescriptive constructions. Deliberately short: a long list produces
# false positives on ordinary description and teaches people to ignore the lint.
_PATTERNS = (
    (r"\bshould\b", "modal"),
    (r"\bmust\b", "modal"),
    (r"\bought to\b", "modal"),
    (r"\bneeds? to\b", "modal"),
    (r"\brecommend(?:s|ed|ation)?\b", "prescriptive"),
    (r"\bsuggest(?:s|ed|ion)?\b", "prescriptive"),
    (r"\bpropose[sd]?\b", "prescriptive"),
    (r"\bthe fix is\b", "prescriptive"),
    (r"\bmitigat(?:e|ion)\b", "prescriptive"),
    (r"\bwe advise\b", "prescriptive"),
)

# DSL surface that has no business in prose. Catching a literal rule is easy and
# worth doing; it is the PARAPHRASE that is uncatchable.
_DSL_PATTERNS = (
    (r"\bcap:CAP_[A-Z_]+", "dsl_selector"),
    (r"=>\s*(?:deny|constrain_arg|require_approval)", "dsl_action"),
    (r"\bpreceded_by\s*\(", "dsl_predicate"),
    (r"\bepisode_sum\s*\(", "dsl_predicate"),
    (r"\brule\s+r_(?:new)?[0-9a-f]+\s*:", "dsl_rule_statement"),
)


@dataclass(frozen=True)
class LintFinding:
    kind: str
    match: str
    path: str


def _walk(node, path="human_only"):
    if isinstance(node, dict):
        for key in sorted(node):
            yield from _walk(node[key], "%s.%s" % (path, key))
    elif isinstance(node, (list, tuple)):
        for i, item in enumerate(node):
            yield from _walk(item, "%s[%d]" % (path, i))
    elif isinstance(node, str):
        yield path, node


def prescriptive_lint(human_only) -> List[LintFinding]:
    """Findings, never an exception. Empty means NOTHING KNOWN-BAD WAS SPELLED,
    which is a much weaker statement than "no fix was proposed"."""
    out = []
    for path, text in _walk(human_only or {}):
        for pattern, kind in _PATTERNS + _DSL_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                out.append(LintFinding(kind=kind, match=m.group(0), path=path))
    return out
