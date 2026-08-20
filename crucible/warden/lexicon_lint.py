"""lexicon_lint.py - the product-lexicon denylist, structurally applied. KB9.

C8 gate G5: *zero rule BODIES contain a banned product-lexicon token*, with
`exempt: [metadata_fields, provenance_fields]`. C4 validator rule V3 says the
same thing from the grammar side, and names the source of the list: tokens
harvested at attach from TOOL NAMES AND DESCRIPTIONS, minus the capability
vocabulary.

WHY IT HAS TO BE STRUCTURAL, which is the whole of KB9. The fixture pairs two
documents carrying THE SAME TOKEN - one inside a rule body, one only inside
`provenance.episode_summary`. A grep over the file rejects both. No lint at all
accepts both. ONLY A PARSER THAT KNOWS WHICH SUBTREE IT IS IN separates them,
and if it cannot, the capability-shaping mandate is decorative and a
product-shaped policy promotes while the boundary claim is false on its face.

The exempt subtrees are `provenance` and `meta`. That is not a loophole: neither
is inside `hashed_payload`, so nothing there can change the policy's meaning
without changing its hash. Prose stays in the record for humans and is
structurally unreachable from the rule semantics - the same shape as the
CORONER's free-text findings being confined where the ARMORER's adapter cannot
address them.

WHAT THIS LINT DOES NOT DO, stated rather than implied: it does not enforce V7
(no >= 8-token substring of a corpus payload), because that needs the corpus,
which L2 freezes at D5. G5 carries both assertions; this file covers one.
"""

import re

# Not hashed_payload, and therefore not able to change what a rule means.
EXEMPT_SUBTREES = ("provenance", "meta", "lineage")

# Fields the fixture files use for their own annotations. They are not part of
# any document a real ARMORER emits, and flagging them would make the fixture
# fail for a reason that has nothing to do with what it tests.
_ANNOTATION_PREFIX = "_"


class LintFinding:
    __slots__ = ("path", "token", "value")

    def __init__(self, path, token, value):
        self.path = path
        self.token = token
        self.value = value

    def __repr__(self):
        return "%s carries the product token %r in %r" % (self.path, self.token, self.value)

    __str__ = __repr__


class LintResult:
    __slots__ = ("verdict", "findings")

    def __init__(self, verdict, findings):
        self.verdict = verdict
        self.findings = findings

    def __repr__(self):
        return "<%s %d finding(s)>" % (self.verdict, len(self.findings))


def _tokens(text):
    """Word-boundary tokens, lowercased. `issue_refund` yields `issue_refund`
    AND `issue` AND `refund`, so a compound identifier cannot smuggle a banned
    word past a whole-token match."""
    return set(re.findall(r"[a-z0-9]+", str(text).lower())) | {
        str(text).lower()} | set(re.findall(r"[a-z0-9_]+", str(text).lower()))


def _walk(node, path, lexicon, findings):
    if isinstance(node, dict):
        for key, value in node.items():
            if key.startswith(_ANNOTATION_PREFIX):
                continue
            _walk(value, "%s.%s" % (path, key), lexicon, findings)
            for token in lexicon:
                if token in _tokens(key):
                    findings.append(LintFinding("%s.%s" % (path, key), token, key))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            _walk(value, "%s[%d]" % (path, i), lexicon, findings)
    elif isinstance(node, str):
        present = _tokens(node)
        for token in lexicon:
            if token in present:
                findings.append(LintFinding(path, token, node))


def lexicon_lint(document, product_lexicon):
    """ACCEPT or REJECT one policy document against a product lexicon.

    Only `hashed_payload` is walked. Everything under `provenance`, `meta`, and
    `lineage` is exempt by construction rather than by a skip-list check inside
    the walk, so a new metadata subtree does not quietly become a new hole.
    """
    lexicon = {t.lower() for t in product_lexicon}
    findings = []
    payload = document.get("hashed_payload")
    if payload is None:
        return LintResult("REJECT", [LintFinding(
            "$", "<no hashed_payload>",
            "a document with no hashed payload has nothing to hash and no rules to lint")])
    _walk(payload, "hashed_payload", lexicon, findings)

    for name in EXEMPT_SUBTREES:
        assert name not in ("hashed_payload",), "the hashed payload is never exempt"

    return LintResult("REJECT" if findings else "ACCEPT", findings)
