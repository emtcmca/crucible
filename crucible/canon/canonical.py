"""canonical.py - RFC 8785 (JCS) with the seven CRUCIBLE restrictions.

Contract: `contracts/canonicalization.md`. Vectors: `contracts/golden/canonicalization/`.
This module is the critical path: every hash claim in CRUCIBLE collapses if it is
wrong, and a SUBTLY wrong canonicalizer produces green checkmarks over meaningless
comparisons, which is worse than a red one.

Design notes, each of which is a bug that would otherwise be written here:

  * Sorting is on UTF-16 CODE UNITS, done by encoding each key `utf-16-be` and
    comparing the bytes. Big-endian makes byte order and code-unit order the same
    comparison. `sorted()` on the str, or on its UTF-8 bytes, gives CODE POINT
    order, which agrees everywhere except above the BMP. Vector V02 is the only
    place the two differ and it exists solely to catch this.

  * Arrays are NEVER sorted. Restriction 6 sorts arrays AT CONSTRUCTION, not at
    hash time, precisely so that sorting here would be lossless-looking and
    destructive. Vector V04's arrays are deliberately out of order.

  * Integers are emitted with `str(int)`. Python ints are arbitrary precision, so
    this is exact. Any implementation that routes an integer through a float -
    including any JCS library that follows ECMAScript number serialization
    literally - corrupts values above 2^53. Money is INT64 minor units, so this
    is a live path, not a curiosity. Vector V06.

  * `bool` is a subclass of `int` in Python. Every integer check here tests
    `type(x) is int`, never `isinstance(x, int)`, or `True` serializes as `1`.

  * NFC normalization happens BEFORE the duplicate-key check, because two keys
    that differ only by normalization form are the same key after it, and
    silently keeping one is exactly the self-manufactured hash collision V13
    exists to prevent.
"""

import json
import unicodedata

# A model-authored payload reaches this function. A recursion limit here is
# cheaper than a RecursionError surfacing as a crashed run.
MAX_DEPTH = 64


class CanonicalizationError(ValueError):
    """Refusal to canonicalize. Carries a stable machine-readable `code`.

    Every one of these is a REFUSAL, never a repair. canonicalization.md opens by
    saying a subtly wrong canonicalizer is worse than a red one; silently
    stripping a BOM or coercing a float is precisely that trade, made in the
    wrong direction.
    """

    def __init__(self, code: str, detail: str = "", path: str = "$"):
        self.code = code
        self.detail = detail
        self.path = path
        super().__init__("%s at %s: %s" % (code, path, detail) if detail
                         else "%s at %s" % (code, path))


# --------------------------------------------------------------------------
# Parsing. Rejections that are cheapest to make at parse time are made there.
# --------------------------------------------------------------------------

def _reject_float(literal):
    raise CanonicalizationError(
        "E_FLOAT", "%r - restriction 4, integers only. Money is INT64 minor units "
                   "plus an ISO-4217 currency string; rates and confidences live "
                   "outside the hashed payload." % literal)


def _reject_constant(literal):
    raise CanonicalizationError(
        "E_FLOAT", "%s is not valid JSON and is not a number we can hash" % literal)


def _pairs_hook(pairs):
    """Object construction hook. Catches duplicate keys, which the default dict
    build silently resolves in favour of the last one."""
    seen = {}
    for k, v in pairs:
        nk = unicodedata.normalize("NFC", k)
        if nk in seen:
            raise CanonicalizationError(
                "E_DUPLICATE_KEY",
                "%r appears twice%s" % (
                    nk, "" if nk == k else " (after NFC normalization; the two "
                                           "spellings differ only by Unicode form)"))
        seen[nk] = v
    return seen


def _parse(raw: bytes):
    if raw[:3] == b"\xef\xbb\xbf":
        raise CanonicalizationError(
            "E_BOM", "restriction 1 - a BOM changes the bytes and therefore the "
                     "hash. Stripping it would make the file that arrives differ "
                     "from the file that was hashed.")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise CanonicalizationError("E_NOT_UTF8", str(e)) from None
    try:
        return json.loads(
            text,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
            object_pairs_hook=_pairs_hook,
        )
    except CanonicalizationError:
        raise
    except json.JSONDecodeError as e:
        raise CanonicalizationError("E_MALFORMED", str(e)) from None


# --------------------------------------------------------------------------
# Serialization.
# --------------------------------------------------------------------------

_SHORT = {
    0x08: "\\b", 0x09: "\\t", 0x0A: "\\n", 0x0C: "\\f", 0x0D: "\\r",
    0x22: '\\"', 0x5C: "\\\\",
}


def _string(s: str, path: str) -> str:
    """RFC 8785 section 3.2.2.2 - shortest escape, and nothing else escaped."""
    s = unicodedata.normalize("NFC", s)
    out = ['"']
    for ch in s:
        cp = ord(ch)
        if cp in _SHORT:
            out.append(_SHORT[cp])
        elif cp < 0x20:
            out.append("\\u%04x" % cp)
        elif 0xD800 <= cp <= 0xDFFF:
            # Reachable only via a \uD800-style escape in the source. It is not
            # representable in UTF-8, so it would crash the encode step later,
            # at a point where the error names the wrong cause.
            raise CanonicalizationError(
                "E_SURROGATE", "unpaired surrogate U+%04X" % cp, path)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _key_sort(k: str):
    """JCS sorts by UTF-16 code unit. utf-16-be byte order IS code-unit order."""
    return k.encode("utf-16-be", errors="surrogatepass")


def _emit(node, path: str, depth: int) -> str:
    if depth > MAX_DEPTH:
        raise CanonicalizationError("E_TOO_DEEP", "exceeds %d levels" % MAX_DEPTH, path)

    if node is None:
        raise CanonicalizationError(
            "E_NULL", "restriction 5 - an absent fact is an absent key. The "
                      "approver field's empty value is the sentinel \"NONE\".", path)
    if node is True:
        return "true"
    if node is False:
        return "false"
    if type(node) is int:          # not isinstance: bool is a subclass of int
        return str(node)
    if type(node) is float:        # unreachable via _parse; reachable via a dict
        _reject_float(node)
    if isinstance(node, str):
        return _string(node, path)
    if isinstance(node, dict):
        items = []
        for k in sorted(node, key=_key_sort):
            if not isinstance(k, str):
                raise CanonicalizationError("E_NONSTRING_KEY", repr(k), path)
            items.append("%s:%s" % (_string(k, path),
                                    _emit(node[k], "%s.%s" % (path, k), depth + 1)))
        return "{" + ",".join(items) + "}"
    if isinstance(node, (list, tuple)):
        # NOT sorted. Restriction 6 sorts at construction; order is meaning here.
        return "[" + ",".join(
            _emit(v, "%s[%d]" % (path, i), depth + 1) for i, v in enumerate(node)) + "]"

    raise CanonicalizationError("E_UNSUPPORTED_TYPE", type(node).__name__, path)


# --------------------------------------------------------------------------
# Public surface.
# --------------------------------------------------------------------------

def canonicalize_bytes(raw: bytes) -> bytes:
    """Canonicalize raw JSON bytes. Returns UTF-8, single line, no trailing newline."""
    if isinstance(raw, str):
        raise TypeError("canonicalize_bytes takes bytes; a str has already lost "
                        "the BOM question, which is the one restriction 1 asks")
    return _emit(_parse(raw), "$", 0).encode("utf-8")


def canonicalize(obj) -> bytes:
    """Canonicalize an in-memory Python object.

    Note this path cannot see a BOM or a duplicate key - both were resolved by
    whatever built the object. Prefer `canonicalize_bytes` wherever the payload
    arrived as bytes, which is every case where those two failures are possible.
    """
    return _emit(obj, "$", 0).encode("utf-8")
