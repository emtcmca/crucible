"""strawman_canon.py - DELIBERATELY WRONG canonicalizers, kept in the tree forever.

Not dead code, not drafts. These are the proof that
tests/test_canonicalization.py can fail.

CONVENTIONS.md section 8 rule 2: a check that cannot fail is not measuring
anything. On 2026-08-20 the contract gate's own first negative test could not
fail - it appended a trailing newline, which is exactly the mutation the
normalization exists to absorb. It looked green for the same reason a broken
smoke detector looks quiet.

So the suite runs three times. Once against `crucible.canon`, where every vector
must pass. Then once against each strawman here, where a NAMED, PRE-DECLARED set
of vectors must FAIL. If a strawman vector ever passes, the SUITE is broken and
that is reported as a failure, not as a green run.

WHY THERE ARE TWO STRAWMEN
--------------------------
There was one. It was `json.dumps(sort_keys=True)`, and the claim written next to
it said V09 (string escaping) would fail against it. The meta-check caught that
claim as FALSE on the first run: Python's encoder already emits the shortest
escape form, so the strawman passed V09.

That left V09 discriminating against nothing any test could demonstrate - a
vector asserting a property with no evidence it can detect its own violation,
which is the exact object this rule exists to eliminate. Demoting V09 to
"unproven" would have been the comfortable fix. Adding the escaper that actually
gets it wrong is the correct one, because that escaper is the single most common
hand-rolled JSON string writer there is.
"""

import json
import unicodedata

# --------------------------------------------------------------------------
# Strawman 1 - the four-minute answer. What a competent engineer writes when
# asked for "canonical JSON" without having read RFC 8785.
# --------------------------------------------------------------------------

NAIVE_MUST_FAIL = {
    "V02": "sort_keys sorts by code point; JCS sorts by UTF-16 code unit. They "
           "disagree only above the BMP, so V02 is the one vector that catches it.",
    "V03": "no NFC normalization, so the NFD input produces different bytes.",
    "V10": "utf-8-sig silently eats the BOM instead of rejecting it - the exact "
           "'strip it and move on' trade canonicalization.md refuses.",
    "V11": "a float round-trips happily. The restriction-4 hole.",
    "V12": "null round-trips happily. The restriction-5 hole.",
    "V13": "json.loads keeps the LAST duplicate key silently, so two different "
           "documents canonicalize to identical bytes - a hash collision we "
           "manufactured ourselves.",
    "V14": "same hole as V11, and proves nothing recurses.",
    "V15": "same hole as V12, and proves nothing walks into arrays.",
}

# NOT in the list above, and the reason is recorded rather than left implicit:
#   V01, V04, V05, V06, V07, V08 - json.dumps gets these right. Python ints are
#     arbitrary precision, so even V06's 2^53+1 survives. A JS implementation
#     would fail V06; ours cannot, and claiming otherwise would be theatre.
#   V09 - Python's encoder already emits shortest escapes. Strawman 2 exists
#     because of this line.


def naive_canonicalize(raw: bytes) -> bytes:
    obj = json.loads(raw.decode("utf-8-sig"))     # -sig: silently eats a BOM
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


# --------------------------------------------------------------------------
# Strawman 2 - correct everywhere the first one is wrong, and wrong in exactly
# one place: it escapes every control character as \u00xx instead of using the
# short forms RFC 8785 section 3.2.2.2 mandates.
#
# This is not a contrived error. It is what almost every hand-rolled JSON string
# writer does, because \u00xx is uniform and the short-form table is six special
# cases somebody has to remember. It produces valid JSON that parses to the
# identical value - and a different hash.
# --------------------------------------------------------------------------

LONG_ESCAPE_MUST_FAIL = {
    "V09": "escapes tab as \\u0009 and newline as \\u000a rather than \\t and "
           "\\n. Valid JSON, identical parsed value, DIFFERENT BYTES, therefore "
           "a different hash. Nothing but V09 catches it.",
}


def _long_escape_string(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    out = ['"']
    for ch in s:
        cp = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif cp < 0x20:
            out.append("\\u%04x" % cp)      # <-- the whole defect, one branch
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _long_escape_emit(node) -> str:
    if node is None:
        return "null"
    if node is True:
        return "true"
    if node is False:
        return "false"
    if type(node) is int:
        return str(node)
    if isinstance(node, str):
        return _long_escape_string(node)
    if isinstance(node, dict):
        return "{" + ",".join(
            "%s:%s" % (_long_escape_string(unicodedata.normalize("NFC", k)),
                       _long_escape_emit(node[k]))
            for k in sorted(node, key=lambda x: unicodedata.normalize("NFC", x)
                            .encode("utf-16-be", errors="surrogatepass"))) + "}"
    if isinstance(node, (list, tuple)):
        return "[" + ",".join(_long_escape_emit(v) for v in node) + "]"
    raise ValueError(type(node).__name__)


def long_escape_canonicalize(raw: bytes) -> bytes:
    if raw[:3] == b"\xef\xbb\xbf":
        raise ValueError("E_BOM")
    obj = json.loads(raw.decode("utf-8"))
    return _long_escape_emit(obj).encode("utf-8")


# --------------------------------------------------------------------------
STRAWMEN = {
    "naive_dumps": (naive_canonicalize, NAIVE_MUST_FAIL),
    "long_escape": (long_escape_canonicalize, LONG_ESCAPE_MUST_FAIL),
}
