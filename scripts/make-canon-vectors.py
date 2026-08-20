#!/usr/bin/env python3
"""make-canon-vectors.py - materialize the C7 canonicalization golden vectors.

COORDINATOR-AUTHORED. `contracts/canonicalization.md` section 3 requires >=12
hand-authored fixtures at `contracts/golden/canonicalization/`, and lanes never
author `contracts/`. L1 develops against these; it does not edit them.

"Hand-authored" is preserved: every payload and every expected canonical string
below was typed literally. This script exists because three of the vectors are
BYTE-level facts that cannot be typed into a text editor reliably on Windows -
a UTF-8 BOM, a non-BMP key, and an NFD combining sequence. Round-tripping those
through an editor is exactly how the fixture stops testing what it claims to.

WHY THE EXPECTED CANONICAL FORM IS A STRING AND NOT A HASH
----------------------------------------------------------
If the expected value were a hex digest produced by our own canonicalizer, the
test would be circular: any bug that changes the output also changes the
expected value, and the vector can never fail. CONVENTIONS.md section 8 rule 2.

So EXPECTED.json carries the exact canonical BYTES, derived by hand from the
RFC 8785 rules plus the seven project restrictions. The test computes SHA-256
from that hand-authored string. There is no magic hex to mistype, and the
assertion is against an independent derivation rather than against ourselves.

Run:  python scripts/make-canon-vectors.py
"""

import hashlib
import json
import pathlib
import sys
import unicodedata

REPO = pathlib.Path(__file__).resolve().parent.parent
OUT = REPO / "contracts" / "golden" / "canonicalization"

# --------------------------------------------------------------------------
# The vectors. Each `raw` is the INPUT FILE'S EXACT BYTES, written as a Python
# str and encoded UTF-8 (except V10, which is bytes because a BOM is a byte
# fact). Each `canonical` is the hand-derived expected output.
# --------------------------------------------------------------------------

NBSP_FF = "ｚ"        # U+FF5A FULLWIDTH LATIN SMALL LETTER Z -> UTF-16 unit FF5A
EMOJI = "\U0001f600"      # U+1F600 GRINNING FACE -> UTF-16 units D83D DE00

VECTORS = [
    {
        "id": "V01",
        "name": "key-order permutation, nested",
        "why": "Two orderings of the same object MUST produce identical bytes. "
               "This is the entire purpose of canonicalization.",
        "inputs": {
            "V01a.input.json": '{"z":1,"a":2,"m":{"y":3,"b":4}}',
            "V01b.input.json": '{"a":2,"m":{"b":4,"y":3},"z":1}',
        },
        "expect": "canonical",
        "canonical": '{"a":2,"m":{"b":4,"y":3},"z":1}',
        "asserts": ["identical_across_inputs"],
    },
    {
        "id": "V02",
        "name": "non-BMP key sorts by UTF-16 code unit",
        "why": "UTF-16 code-unit order and code-point/UTF-8 byte order DISAGREE here "
               "and nowhere else. U+1F600 encodes as surrogate D83D, which is LESS than "
               "U+FF5A; by code point 0x1F600 is GREATER than 0xFF5A. A sorted() on raw "
               "bytes or on code points passes every other vector and fails this one.",
        "inputs": {
            "V02.input.json": '{"a":1,"' + NBSP_FF + '":2,"' + EMOJI + '":3}',
        },
        "expect": "canonical",
        "canonical": '{"a":1,"' + EMOJI + '":3,"' + NBSP_FF + '":2}',
        "asserts": [],
    },
    {
        "id": "V03",
        "name": "NFC and NFD forms normalize to one output",
        "why": "The same visible text typed on two machines must hash the same. "
               "Applies to KEYS as well as values - a key-only normalizer passes a "
               "value-only test and vice versa, so both appear here.",
        "inputs": {
            "V03a.input.json": json.dumps(
                {unicodedata.normalize("NFC", "café"): unicodedata.normalize("NFC", "née")},
                ensure_ascii=False, separators=(",", ":")),
            "V03b.input.json": json.dumps(
                {unicodedata.normalize("NFD", "café"): unicodedata.normalize("NFD", "née")},
                ensure_ascii=False, separators=(",", ":")),
        },
        "expect": "canonical",
        "canonical": '{"café":"née"}',
        "asserts": ["identical_across_inputs"],
    },
    {
        "id": "V04",
        "name": "nested arrays depth 3, order PRESERVED",
        "why": "Restriction 6 sorts arrays AT CONSTRUCTION, never at hash time. A "
               "canonicalizer that sorts arrays is wrong and destroys information. "
               "Every array here is deliberately out of order.",
        "inputs": {
            "V04.input.json": '{"k":[[3,1],[2,[9,7,8]]]}',
        },
        "expect": "canonical",
        "canonical": '{"k":[[3,1],[2,[9,7,8]]]}',
        "asserts": [],
    },
    {
        "id": "V05",
        "name": "empty array and empty object are distinguishable",
        "why": "[] and {} are different facts. An implementation that treats either "
               "as 'empty' collapses them and two different policies hash the same.",
        "inputs": {
            "V05a.input.json": '{"e":[],"o":{}}',
            "V05b.input.json": '{"e":{},"o":[]}',
        },
        "expect": "canonical",
        "canonicals": ['{"e":[],"o":{}}', '{"e":{},"o":[]}'],
        "asserts": ["distinct_across_inputs"],
    },
    {
        "id": "V06",
        "name": "integers beyond 2^53 survive exactly",
        "why": "THE FLOAT TRAP, and it is not hypothetical. Money is INT64 minor units "
               "(CONVENTIONS section 6). ECMAScript numbers - which RFC 8785 otherwise "
               "defers to - are exact only to 2^53-1. Any implementation that routes an "
               "integer through a double corrupts these three values silently. "
               "9007199254740993 is 2^53+1: as a double it becomes 9007199254740992.",
        "inputs": {
            "V06.input.json": '{"a":9007199254740993,"b":9223372036854775807,'
                              '"c":-9223372036854775808}',
        },
        "expect": "canonical",
        "canonical": '{"a":9007199254740993,"b":9223372036854775807,'
                     '"c":-9223372036854775808}',
        "asserts": [],
    },
    {
        "id": "V07",
        "name": "zero and negative integers",
        "why": "0 is falsy in every language this could be written in. A truthiness "
               "check where an is-None check belongs drops it.",
        "inputs": {
            "V07.input.json": '{"neg":-1,"zero":0}',
        },
        "expect": "canonical",
        "canonical": '{"neg":-1,"zero":0}',
        "asserts": [],
    },
    {
        "id": "V08",
        "name": "booleans, both values, lowercase",
        "why": "Restriction 7. Also guards the opposite bug: in Python bool is a "
               "SUBCLASS of int, so an isinstance(x, int) integer check accepts True "
               "and an over-eager type check rejects it. Both directions are live.",
        "inputs": {
            "V08.input.json": '{"f":false,"t":true}',
        },
        "expect": "canonical",
        "canonical": '{"f":false,"t":true}',
        "asserts": [],
    },
    {
        "id": "V09",
        "name": "string escaping, shortest form",
        "why": "RFC 8785 mandates the SHORTEST escape: tab is \\t, never \\u0009. The "
               "input below deliberately uses the long forms so a passthrough "
               "implementation fails. U+0001 has no short form and stays \\u0001.",
        "inputs": {
            "V09.input.json": '{"s":"q\\"b\\\\c\\u0001d\\u0009e\\u000af"}',
        },
        "expect": "canonical",
        "canonical": '{"s":"q\\"b\\\\c\\u0001d\\te\\nf"}',
        "asserts": [],
    },
    # ---------------- the negative half. NOT OPTIONAL. --------------------
    {
        "id": "V10",
        "name": "BOM is REJECTED, not stripped",
        "why": "Restriction 1. A BOM changes the bytes and therefore the hash. Windows "
               "produces them constantly. An implementation that silently strips it "
               "passes all nine positive vectors and is wrong in production, because "
               "the file that arrives at the judge is not the file that was hashed.",
        "inputs": {"V10.input.json": "﻿" + '{"a":1}'},
        "expect": "reject",
        "reject": "E_BOM",
    },
    {
        "id": "V11",
        "name": "float is REJECTED",
        "why": "Restriction 4. Dodging ECMAScript number serialization is the whole "
               "reason floats are banned; accepting one reintroduces every rule the "
               "restriction exists to avoid.",
        "inputs": {"V11.input.json": '{"rate":0.5}'},
        "expect": "reject",
        "reject": "E_FLOAT",
    },
    {
        "id": "V12",
        "name": "null is REJECTED",
        "why": "Restriction 5. An absent fact is an absent key. The approver field's "
               "empty value is the sentinel \"NONE\" - canonicalization.md section 2.",
        "inputs": {"V12.input.json": '{"approver":null}'},
        "expect": "reject",
        "reject": "E_NULL",
    },
    # ------- three more, each killing a specific shallow implementation ----
    {
        "id": "V13",
        "name": "duplicate key is REJECTED",
        "why": "Not in the section 3 table; added because every mainstream JSON parser "
               "silently keeps the LAST duplicate. Two semantically different documents "
               "then canonicalize to the same bytes, which is a hash collision we "
               "manufactured ourselves. Must be caught at parse, not after.",
        "inputs": {"V13.input.json": '{"a":1,"a":2}'},
        "expect": "reject",
        "reject": "E_DUPLICATE_KEY",
    },
    {
        "id": "V14",
        "name": "float at depth 3 is REJECTED",
        "why": "Proves the float check RECURSES. A top-level-only scan passes V11 and "
               "misses every real payload, where numbers live inside arg_conditions.",
        "inputs": {"V14.input.json": '{"a":{"b":[{"c":1.0}]}}'},
        "expect": "reject",
        "reject": "E_FLOAT",
    },
    {
        "id": "V15",
        "name": "null inside an array is REJECTED",
        "why": "Proves the null check recurses INTO ARRAYS specifically. A dict-only "
               "walk passes V12 and misses this.",
        "inputs": {"V15.input.json": '{"a":[1,null,3]}'},
        "expect": "reject",
        "reject": "E_NULL",
    },
    # ---- V16 and V17 added 2026-08-20 on L1's report. Coordinator ruling. ----
    # L1 implemented two refusals the section 3 table does not enumerate and
    # correctly refused to add its own fixtures for them (lanes never edit
    # contracts/). Both accepted. Section 3 says ">=12", so the table is a
    # MINIMUM and adding these does not require editing the frozen contract -
    # which is the only reason this could be done without a SPINE_VERSION bump.
    {
        "id": "V16",
        "name": "unpaired surrogate is REJECTED",
        "why": "Reachable from a \\uD800-style escape in any source document, and "
               "not representable in UTF-8. Without an explicit refusal it surfaces "
               "later as a UnicodeEncodeError NAMING THE WRONG CAUSE, several layers "
               "from where it entered - the failure shape this whole project is "
               "about. Note the input is ASCII: the surrogate arrives as an escape, "
               "which is exactly why a byte-level UTF-8 validity check misses it.",
        "inputs": {"V16.input.json": '{"s":"\\ud800"}'},
        "expect": "reject",
        "reject": "E_SURROGATE",
    },
    {
        "id": "V17",
        "name": "nesting beyond the depth limit is REJECTED",
        "why": "A MODEL authors payloads that reach the canonicalizer. A "
               "RecursionError inside a hashing path reads as a harness crash - "
               "TARGET_FAULT-shaped noise in a run that is supposed to be measuring "
               "whether an attack succeeded. An instrument failure must not be "
               "counted as a measurement (CONVENTIONS section 2.4).",
        "inputs": {"V17.input.json": "[" * 200 + "]" * 200},
        "expect": "reject",
        "reject": "E_TOO_DEEP",
    },
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    index = {
        "_note": "Golden vectors for contracts/canonicalization.md section 3. "
                 "COORDINATOR-AUTHORED, frozen with C7. Lanes read these and do not edit them.",
        "_expected_form": "Each positive vector carries the exact expected canonical "
                          "BYTES, hand-derived from RFC 8785 plus the seven project "
                          "restrictions - NOT a digest emitted by our own canonicalizer. "
                          "A digest would make the vector circular and unable to fail.",
        "_hash": "sha256 of the canonical string, UTF-8 encoded. The test computes it; "
                 "no hex literal appears in this file, so none can be mistyped.",
        "_reject_codes": {
            "E_BOM": "payload begins with a UTF-8 BOM",
            "E_FLOAT": "a non-integer number appears anywhere in the payload",
            "E_NULL": "null appears anywhere in the payload",
            "E_DUPLICATE_KEY": "an object declares the same key twice",
            "E_SURROGATE": "an unpaired surrogate code point, which UTF-8 cannot encode",
            "E_TOO_DEEP": "nesting beyond the implementation's depth limit",
        },
        "vector_count": len(VECTORS),
        "vectors": [],
    }

    for v in VECTORS:
        for fname, body in v["inputs"].items():
            (OUT / fname).write_bytes(body.encode("utf-8"))
        entry = {
            "id": v["id"],
            "name": v["name"],
            "why": v["why"],
            "inputs": sorted(v["inputs"].keys()),
            "expect": v["expect"],
        }
        if v["expect"] == "canonical":
            if "canonical" in v:
                entry["canonical"] = v["canonical"]
            else:
                entry["canonicals"] = v["canonicals"]
            entry["asserts"] = v["asserts"]
        else:
            entry["reject"] = v["reject"]
        index["vectors"].append(entry)

    text = json.dumps(index, ensure_ascii=False, indent=2) + "\n"
    (OUT / "EXPECTED.json").write_text(text, encoding="utf-8", newline="\n")

    # Postcondition, asserted rather than assumed: read every file back off disk
    # and prove the bytes are what was intended.
    print("WROTE %s" % OUT.relative_to(REPO).as_posix())
    ok = True
    for v in VECTORS:
        for fname in v["inputs"]:
            raw = (OUT / fname).read_bytes()
            want = v["inputs"][fname].encode("utf-8")
            mark = "ok " if raw == want else "BAD"
            if raw != want:
                ok = False
            print("  %s %-18s %4d bytes  sha256=%s" % (
                mark, fname, len(raw), hashlib.sha256(raw).hexdigest()[:12]))
    idx = (OUT / "EXPECTED.json").read_bytes()
    print("  ok  %-18s %4d bytes  vectors=%d  BOM=%s" % (
        "EXPECTED.json", len(idx), len(VECTORS), idx[:3] == b"\xef\xbb\xbf"))

    # V10 must actually carry the BOM, and it is the one vector where a
    # well-meaning editor would destroy the thing being tested.
    v10 = (OUT / "V10.input.json").read_bytes()
    print("  V10 first three bytes = %s  (must be efbbbf)" % v10[:3].hex())
    if v10[:3] != b"\xef\xbb\xbf":
        ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
