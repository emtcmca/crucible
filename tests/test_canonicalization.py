"""test_canonicalization.py - L1's first work item, and it is the negative check.

Drives `contracts/golden/canonicalization/EXPECTED.json` against three
implementations:

  crucible.canon                  the real one. EVERY vector must pass.
  strawman_canon.naive_dumps      json.dumps(sort_keys=True). Eight vectors
                                  must FAIL it.
  strawman_canon.long_escape      correct except that it escapes controls as
                                  \\u00xx. V09 must FAIL it.

If a strawman vector ever PASSES, that is reported as a test failure - the
suite has stopped measuring. This half is the part that matters. A suite that
only ever runs against the implementation it was written alongside cannot
distinguish "correct" from "agrees with itself."

The second strawman exists because the first run of this file caught a false
claim in the first one: the naive implementation was declared to fail V09, and
it does not - Python's encoder already emits shortest escapes. Rather than
demote V09 to unproven, the escaper that actually gets it wrong was added.

EXPECTED.json carries hand-derived canonical BYTES, not digests emitted by our
own canonicalizer, so `assert canonicalize(x) == expected` compares against an
independent derivation. The hash is computed here, from that string, which is
why no hex literal appears anywhere in the fixtures or in this file.
"""

import hashlib
import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
VECTORS = REPO / "contracts" / "golden" / "canonicalization"
INDEX = json.loads((VECTORS / "EXPECTED.json").read_text(encoding="utf-8"))

from crucible.canon import CanonicalizationError, canonicalize_bytes  # noqa: E402
from tests import strawman_canon  # noqa: E402


def _vec(vid):
    for v in INDEX["vectors"]:
        if v["id"] == vid:
            return v
    raise KeyError(vid)


ALL_IDS = [v["id"] for v in INDEX["vectors"]]
POSITIVE = [v["id"] for v in INDEX["vectors"] if v["expect"] == "canonical"]
NEGATIVE = [v["id"] for v in INDEX["vectors"] if v["expect"] == "reject"]

# Vectors that no strawman in tests/strawman_canon.py fails. Declared, not
# discovered: see test_every_vector_is_killed_by_at_least_one_strawman.
# All six are cases Python's own json module happens to get right - notably V06,
# where arbitrary-precision ints mean a Python strawman CANNOT reproduce the
# 2^53 float trap. A JavaScript implementation would fail it immediately.
UNPROVEN_BY_DESIGN = ["V01", "V04", "V05", "V06", "V07", "V08"]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# --------------------------------------------------------------------------
# The fixture set itself must be intact before it can test anything.
# --------------------------------------------------------------------------

def test_fixture_set_is_intact():
    assert INDEX["vector_count"] == len(INDEX["vectors"]) == 15
    assert len(POSITIVE) == 9, "canonicalization.md sec 3 lists nine positive vectors"
    assert len(NEGATIVE) == 6, "three from the sec 3 table plus three recursion probes"
    for v in INDEX["vectors"]:
        for f in v["inputs"]:
            assert (VECTORS / f).exists(), "%s missing input %s" % (v["id"], f)


def test_v10_input_actually_carries_a_bom():
    """The one fixture an editor round-trip silently destroys.

    If this file loses its BOM, V10 still 'passes' - it just stops testing
    anything, because there is no BOM left to reject.
    """
    raw = (VECTORS / "V10.input.json").read_bytes()
    assert raw[:3] == b"\xef\xbb\xbf", "V10 lost its BOM; the vector is now inert"


def test_v03_inputs_are_actually_different_bytes():
    """NFC and NFD must differ ON DISK or the normalization test is inert."""
    a = (VECTORS / "V03a.input.json").read_bytes()
    b = (VECTORS / "V03b.input.json").read_bytes()
    assert a != b, "V03a and V03b are byte-identical; nothing is being normalized"


# --------------------------------------------------------------------------
# The real implementation. Every vector.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("vid", POSITIVE)
def test_positive_vector(vid):
    v = _vec(vid)
    outs = []
    for i, fname in enumerate(v["inputs"]):
        raw = (VECTORS / fname).read_bytes()
        got = canonicalize_bytes(raw)
        want = (v["canonical"] if "canonical" in v else v["canonicals"][i])
        assert got.decode("utf-8") == want, (
            "%s/%s\n  got  %r\n  want %r" % (vid, fname, got.decode("utf-8"), want))
        outs.append(got)

    if "identical_across_inputs" in v.get("asserts", []):
        assert len({sha(o) for o in outs}) == 1, (
            "%s: inputs must canonicalize to ONE hash, got %s"
            % (vid, [sha(o)[:12] for o in outs]))
    if "distinct_across_inputs" in v.get("asserts", []):
        assert len({sha(o) for o in outs}) == len(outs), (
            "%s: inputs collapsed to the same hash" % vid)


@pytest.mark.parametrize("vid", NEGATIVE)
def test_negative_vector(vid):
    v = _vec(vid)
    for fname in v["inputs"]:
        raw = (VECTORS / fname).read_bytes()
        with pytest.raises(CanonicalizationError) as ei:
            canonicalize_bytes(raw)
        assert ei.value.code == v["reject"], (
            "%s/%s rejected with %s, contract says %s"
            % (vid, fname, ei.value.code, v["reject"]))


def test_canonical_output_never_carries_a_bom_or_newline():
    """Restriction 1 and 3, asserted on the OUTPUT rather than the input."""
    for vid in POSITIVE:
        for fname in _vec(vid)["inputs"]:
            got = canonicalize_bytes((VECTORS / fname).read_bytes())
            assert got[:3] != b"\xef\xbb\xbf", "%s emitted a BOM" % vid
            assert not got.endswith(b"\n"), "%s emitted a trailing newline" % vid
            assert b"\n" not in got and b"  " not in got, "%s emitted whitespace" % vid


def test_idempotent():
    """canonicalize(canonicalize(x)) == canonicalize(x).

    Not in the section 3 table. It is here because a canonicalizer that is not
    idempotent means the canonical form is not a fixed point, and every hash in
    the project then depends on how many times the value happened to be passed
    through - which is unreproducible in exactly the way that looks like a bug
    somewhere else.
    """
    for vid in POSITIVE:
        for fname in _vec(vid)["inputs"]:
            once = canonicalize_bytes((VECTORS / fname).read_bytes())
            assert canonicalize_bytes(once) == once, "%s is not a fixed point" % vid


# --------------------------------------------------------------------------
# THE NEGATIVE CHECK ON THE SUITE ITSELF.
# --------------------------------------------------------------------------

_STRAWMAN_CASES = sorted(
    (name, vid)
    for name, (_fn, must_fail) in strawman_canon.STRAWMEN.items()
    for vid in must_fail
)


@pytest.mark.parametrize("name,vid", _STRAWMAN_CASES,
                         ids=["%s:%s" % (n, v) for n, v in _STRAWMAN_CASES])
def test_strawman_fails_the_vector_it_is_supposed_to_fail(name, vid):
    """If this test fails, the SUITE is broken, not the strawman.

    Each pair below is a vector one wrong implementation gets wrong. A pass here
    means the vector stopped discriminating and would also wave through the real
    bug it was written to catch.
    """
    fn, must_fail = strawman_canon.STRAWMEN[name]
    v = _vec(vid)
    reason = must_fail[vid]
    detected = False
    for i, fname in enumerate(v["inputs"]):
        raw = (VECTORS / fname).read_bytes()
        try:
            got = fn(raw)
        except Exception:
            detected = True          # crashed rather than silently agreeing
            break
        if v["expect"] == "reject":
            detected = True          # it produced output where it owed a rejection
            break
        want = (v["canonical"] if "canonical" in v else v["canonicals"][i])
        if got.decode("utf-8") != want:
            detected = True
            break
    assert detected, (
        "VECTOR {} NO LONGER DISCRIMINATES against strawman {!r}. "
        "It was supposed to fail because: {} "
        "A vector that a known-wrong implementation passes is not testing "
        "the property it claims to test.".format(vid, name, reason))


def test_every_vector_is_killed_by_at_least_one_strawman():
    """The census the single-strawman version could not produce.

    A vector no strawman fails is a vector with no evidence it can detect its own
    violation. That is allowed - some properties only a foreign-language
    implementation gets wrong - but it must be DECLARED, not discovered later.
    """
    killed = {vid for _fn, mf in strawman_canon.STRAWMEN.values() for vid in mf}
    unproven = [v for v in ALL_IDS if v not in killed]
    assert unproven == UNPROVEN_BY_DESIGN, (
        "vector discrimination census changed. "
        "unproven now: {} / declared: {}".format(unproven, UNPROVEN_BY_DESIGN))


def test_every_strawman_claim_names_a_real_vector():
    """Guards the guard. A typo'd vector ID in STRAWMAN_MUST_FAIL would make the
    parametrize above silently skip the case it was added for."""
    for name, (_fn, must_fail) in strawman_canon.STRAWMEN.items():
        for vid in must_fail:
            assert vid in ALL_IDS, "%s names %s, which is not a real vector" % (name, vid)


# --------------------------------------------------------------------------
# Refusals the implementation makes that have NO contract vector yet.
#
# Reported to the coordinator rather than added to contracts/ - lanes never edit
# contracts/ (L1-foundation.md section 6). These tests pin the behaviour so it
# cannot drift while the vector question is open.
# --------------------------------------------------------------------------

def test_unpaired_surrogate_is_refused_not_crashed():
    """Reachable from a `\uD800` escape in a source document. It is not
    representable in UTF-8, so without this the failure surfaces later as a
    UnicodeEncodeError naming the wrong cause."""
    raw = b'{"s":"' + b"\\" + b'ud800"}'
    with pytest.raises(CanonicalizationError) as ei:
        canonicalize_bytes(raw)
    assert ei.value.code == "E_SURROGATE"


def test_excessive_nesting_is_refused_not_recursed():
    """A model authors payloads that reach this function. A RecursionError in a
    hashing path reads as a harness crash, which is TARGET_FAULT-shaped noise in
    a run that is supposed to be measuring something else."""
    raw = (b"[" * 200) + (b"]" * 200)
    with pytest.raises(CanonicalizationError) as ei:
        canonicalize_bytes(raw)
    assert ei.value.code == "E_TOO_DEEP"


def test_str_input_is_a_type_error_not_a_silent_success():
    """By the time a payload is a str the BOM question has already been answered
    by somebody else, which is the one thing restriction 1 asks."""
    with pytest.raises(TypeError):
        canonicalize_bytes('{"a":1}')
