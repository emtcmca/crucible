"""conformance_map.py - which test satisfies which required negative check.

`scripts/conformance-sweep.py` enumerates every negative check declared in a
contract or a lane brief and asks whether a test asserting it exists. It answers
that by grepping `tests/` for the check's token.

THAT MAKES THE CENSUS TRIVIALLY GAMEABLE, and saying so is the point of this
file. Writing `# L1-neg4` in a comment turns the census green with no test
behind it. So the mapping lives here as a RESOLVABLE REFERENCE -- module,
function -- and `test_conformance_map.py` imports each one and fails if it does
not exist. A token in this file is a claim; the test next to it is what makes
the claim checkable.

It still does not prove the referenced test is a GOOD test. Nothing mechanical
can. What it removes is the failure where a check is reported built and no code
by that name exists at all.
"""

# token -> (module, callable name, what it actually asserts)
L1_CONFORMANCE = {
    "L1-neg1": (
        "tests.test_canonicalization", "test_negative_vector",
        "Golden vectors V10 (BOM), V11 (float) and V12 (null) must be REJECTED, "
        "not silently coerced. Parametrized over every NEGATIVE vector, so V13 "
        "(duplicate key), V14 (nested float), V15 (null in array), V16 "
        "(unpaired surrogate) and V17 (depth) ride the same assertion."),
    "L1-neg2": (
        "tests.test_canonicalization", "test_positive_vector",
        "V01 carries assert identical_across_inputs: two key orderings of one "
        "object must produce ONE hash. The assertion is on hash equality between "
        "the two inputs, not against a stored digest, so it cannot pass by "
        "agreeing with itself."),
    "L1-neg3": (
        "tests.test_canonicalization", "test_positive_vector",
        "V02 mixes 'a', U+FF5A and U+1F600. U+1F600 encodes as surrogate D83D "
        "which is LESS than U+FF5A, while by code point it is GREATER -- so a "
        "sorted() on the string or on UTF-8 bytes produces a different order "
        "here and nowhere else. Also killed by the naive_dumps strawman."),
    "L1-neg4": (
        "tests.test_ledger_gate", "test_a_deliberately_corrupted_readback_is_caught",
        "The gate must recompute the policy hash FROM THE READ-BACK BYTES. "
        "Verified red on 2026-08-20 against a naive gate that compared the "
        "stored hash to itself: DID NOT RAISE."),
}
