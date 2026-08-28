"""test_sealed_io.py - does the ONLY door to the sealed holdout open exactly
once, on exactly the right objects, and does it compute the SAME number as the
script that owns the algorithm?

WHY THIS FILE EXISTS AT ALL
===========================
`crucible/transfer/sealed_io.py` says so itself, in its own docstring: it is a
SECOND IMPLEMENTATION of a hash whose first implementation is
`scripts/seal-commitment.py:fingerprint`. It exists only because the sealed
bytes never land on disk, so a directory-walking hash cannot be pointed at
them. Two implementations of one number is two answers, and the module's
defence is one sentence - *"the two are asserted equal by the caller."*

Until this file, nothing asserted it. `test_fingerprint_from_bytes_agrees_with
_the_script_that_owns_the_algorithm` below is that assertion, and it is the
most important test here by a wide margin: without it the published commitment
and the unseal-time recomputation could disagree, and the disagreement would
surface exactly once, at the one moment the seal opens and there is no retry.

THE OTHER HALF: G7c COUNTS READS, AND EXACT EQUALITY IS THE CONTRACT
====================================================================
G7c compares granted `storage.objects.get` audit entries against an expected
integer with EXACT equality, and a mismatch sets `invalidates=True` at the END
of a run. One extra read, one duplicate read, or one retried read is a lost
attempt. So `read_sealed_once` is tested for CALL COUNT, not just for output:
the counting fake downloader is the point of tests 3, 4 and 9.

WHAT IS SYNTHETIC HERE, AND IT IS EVERYTHING
============================================
**No test in this file reads a real sealed instance, and none may ever.** The
holdout opens once. Every fixture below is invented in `tmp_path` from
F4-SHAPED nonsense - the name shape is real, the content is not. Nothing here
touches `corpus/sealed`, `gs://crucible-sealed-x7`, or any network: the
downloader is INJECTED precisely so a test needs no client, and every fake in
this file is a plain callable over an in-memory dict.
"""

import hashlib
import importlib.util
import io
import json
import pathlib
import sys

import pytest

from crucible.transfer.sealed_io import (
    SealedReadError,
    expected_object_names,
    fingerprint_from_bytes,
    parse_instances,
    read_sealed_once,
)

REPO = pathlib.Path(__file__).resolve().parent.parent
SEAL_COMMITMENT = REPO / "scripts" / "seal-commitment.py"


# ---------------------------------------------------------------------------
# Loading the script that OWNS the algorithm.
# ---------------------------------------------------------------------------

def _load_seal_commitment():
    """Import `scripts/seal-commitment.py` by path - the filename is hyphenated
    and is not importable as a module name.

    `sys.stdout` is swapped for a `StringIO` across the exec. The script
    rebinds `sys.stdout` to a UTF-8 `TextIOWrapper` over `sys.stdout.buffer` at
    import time, guarded by `hasattr(sys.stdout, "buffer")`. A `StringIO` has
    no `buffer`, so the rebind is skipped entirely - and that matters more than
    it looks: merely restoring `sys.stdout` afterwards leaves the discarded
    wrapper to be garbage-collected, and a `TextIOWrapper` CLOSES the buffer it
    wrapped on the way out. That closed pytest's capture stream and turned
    every test in this file into a teardown error.
    """
    spec = importlib.util.spec_from_file_location("_seal_commitment",
                                                  SEAL_COMMITMENT)
    module = importlib.util.module_from_spec(spec)
    saved_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        spec.loader.exec_module(module)
    finally:
        sys.stdout = saved_stdout
    return module


@pytest.fixture(scope="module")
def seal_commitment():
    return _load_seal_commitment()


# ---------------------------------------------------------------------------
# Synthetic fixtures. F4-SHAPED, entirely invented, never a sealed instance.
# ---------------------------------------------------------------------------

def _instance(index, slug, family="fam_f4"):
    """One synthetic instance body. The SHAPE is what matters - a family
    declaration and a capability-class list, because `seal-commitment.py`'s
    `fingerprint` parses the JSON to tally classes and would raise on garbage.
    """
    return {
        "instance_id": "F4-dest-%02d-%s" % (index, slug),
        "family_id": family,
        "capability_classes": ["CAP_MOVES_MONEY"],
        "note": "SYNTHETIC. Invented for tests. Not a sealed instance.",
    }


def _name(index, slug):
    return "F4-dest-%02d-%s.json" % (index, slug)


def _body(index, slug, family="fam_f4", newline=b"\n"):
    """Serialise an instance to bytes with a chosen line ending, so a test can
    control the exact bytes rather than inherit the platform's."""
    text = json.dumps(_instance(index, slug, family), indent=2) + "\n"
    raw = text.encode("utf-8")
    if newline != b"\n":
        raw = raw.replace(b"\n", newline)
    return raw


def _synthetic_pairs():
    """Three synthetic objects, deliberately NOT in sorted order, and one of
    them CRLF - so a test that gets sorting or normalisation wrong fails."""
    return [
        (_name(3, "wire-detour"), _body(3, "wire-detour")),
        (_name(1, "vendor-swap"), _body(1, "vendor-swap", newline=b"\r\n")),
        (_name(2, "iban-tail"), _body(2, "iban-tail")),
    ]


def _write_dir(tmp_path, pairs):
    """Materialise pairs as a directory `seal-commitment.py:fingerprint` can
    walk. Bytes are written with `write_bytes` so Windows text-mode translation
    cannot silently repair a CRLF fixture into an LF one."""
    directory = tmp_path / "synthetic-sealed"
    directory.mkdir()
    for name, raw in pairs:
        (directory / name).write_bytes(raw)
    return directory


def _counting_downloader(pairs, missing=()):
    """A fake downloader that records every path it was handed.

    Returns `(callable, calls)` where `calls` is the live list of requested
    paths. No client, no network - the injection point exists for this.
    """
    table = {name: raw for name, raw in pairs}
    calls = []

    def download(path):
        calls.append(path)
        name = path.rsplit("/", 1)[-1]
        if name in missing:
            raise FileNotFoundError(path)
        return table[name]

    return download, calls


# ---------------------------------------------------------------------------
# 1. THE CONTROL. The one that matters most.
# ---------------------------------------------------------------------------

def test_fingerprint_from_bytes_agrees_with_the_script_that_owns_the_algorithm(
        tmp_path, seal_commitment):
    """WITHOUT THIS TEST, `sealed_io.fingerprint_from_bytes` is a second
    implementation of a published hash with no proof it agrees with the first
    - which is exactly the defect its own docstring names and then defers to
    "the caller".

    The two implementations differ in how they OBTAIN bytes (a directory glob
    versus injected downloads), and that difference is where a divergence would
    hide: filename encoding, sort order, or CRLF handling. So the same three
    synthetic objects are hashed both ways and the hex digests are compared. If
    they ever disagree, the commitment published before the run and the number
    recomputed at the unseal disagree too, and there is no second attempt at a
    seal.

    The fixture set is deliberately unsorted on input and contains a CRLF file,
    so agreement here is agreement on the parts that could actually drift.
    """
    pairs = _synthetic_pairs()
    directory = _write_dir(tmp_path, pairs)

    script_digest, count, classes = seal_commitment.fingerprint(directory)
    module_digest = fingerprint_from_bytes(sorted(pairs))

    assert count == 3
    assert classes == {"CAP_MOVES_MONEY": 3}
    assert module_digest == script_digest, (
        "sealed_io and seal-commitment.py computed DIFFERENT fingerprints over "
        "identical bytes: %s vs %s" % (module_digest, script_digest))

    # And the agreed value is not some degenerate constant.
    assert len(module_digest) == 64
    assert module_digest != hashlib.sha256(b"").hexdigest()


def test_the_control_above_can_fail_when_the_two_are_fed_different_bytes(
        tmp_path, seal_commitment):
    """NEGATIVE CONTROL for test 1. Without it, the agreement above would pass
    against any pair of functions that both returned a constant, and a check
    that cannot fail is not measuring anything.

    One byte of one instance is changed on the in-memory side only. The two
    implementations must now DISAGREE.
    """
    pairs = _synthetic_pairs()
    directory = _write_dir(tmp_path, pairs)
    script_digest, _count, _classes = seal_commitment.fingerprint(directory)

    tampered = sorted(pairs)
    name, raw = tampered[0]
    tampered[0] = (name, raw.replace(b"CAP_MOVES_MONEY", b"CAP_READS_PII"))

    assert fingerprint_from_bytes(tampered) != script_digest


# ---------------------------------------------------------------------------
# 2. CRLF normalisation, with its own control.
# ---------------------------------------------------------------------------

def test_line_endings_alone_do_not_move_the_fingerprint_but_any_other_byte_does():
    """WITHOUT THIS, a checkout that normalised line endings - a `.gitattributes`
    rule, a Windows editor, a re-upload through a text-mode tool - would break
    the published commitment for a reason that has nothing to do with the
    sealed content, and the seal would read BROKEN on an untouched set.

    The second half is the CONTROL for the first: a normaliser that returned a
    constant, or one that stripped every byte it did not recognise, would pass
    the equality assertion alone. So a one-byte change that is NOT a line
    ending must move the digest.
    """
    lf = [(_name(1, "vendor-swap"), b'{"a": 1,\n "b": 2}\n')]
    crlf = [(_name(1, "vendor-swap"), b'{"a": 1,\r\n "b": 2}\r\n')]
    other = [(_name(1, "vendor-swap"), b'{"a": 1,\n "b": 3}\n')]

    assert fingerprint_from_bytes(lf) == fingerprint_from_bytes(crlf)
    assert fingerprint_from_bytes(lf) != fingerprint_from_bytes(other)

    # The NAME is inside the hash too, so the same bytes under a different
    # object name are a different fingerprint.
    renamed = [(_name(2, "vendor-swap"), lf[0][1])]
    assert fingerprint_from_bytes(lf) != fingerprint_from_bytes(renamed)


# ---------------------------------------------------------------------------
# 3. ONE read per object. This is what G7c's expected count rests on.
# ---------------------------------------------------------------------------

def test_read_sealed_once_calls_the_downloader_exactly_once_per_name():
    """WITHOUT THIS, a second `download_as_bytes`, a retry, or a stray
    `exists()` could creep into the read path and nothing would notice until
    G7c compared audit entries against an expected integer AT THE END OF A RUN
    - after the episodes scored, which the unseal pre-registration treats as
    INVALID with no retry.

    Both halves are asserted, because either alone is weak: the CALL COUNT
    equals the number of names, and the SET of requested paths is exactly the
    expected set. A path requested twice would satisfy a count-only check if
    another were dropped.
    """
    pairs = _synthetic_pairs()
    names = expected_object_names(name for name, _ in pairs)
    download, calls = _counting_downloader(pairs)

    result = read_sealed_once("gs://crucible-sealed-x7", names, download)

    assert len(calls) == len(names) == 3
    assert len(set(calls)) == len(calls), "an object was requested twice: %s" % calls
    assert set(calls) == {
        "gs://crucible-sealed-x7/families/%s" % n for n in names}
    assert [name for name, _ in result] == names


def test_read_sealed_once_returns_one_pair_per_name_sorted_and_never_fewer():
    """WITHOUT THIS, a short read could be returned as a smaller experiment.
    23 of 24 objects is not a smaller experiment; it is a different one with an
    undeclared denominator, and the ASR it produces has no honest name.

    Also pins the sort: the fingerprint is computed over pairs sorted by name,
    so a caller that hashed the return value in arrival order would get a
    different number for the same bytes.
    """
    pairs = _synthetic_pairs()
    names = expected_object_names(name for name, _ in pairs)
    download, _calls = _counting_downloader(pairs)

    result = read_sealed_once("gs://crucible-sealed-x7", names, download)

    assert len(result) == len(names)
    assert [name for name, _ in result] == sorted(names)
    assert all(isinstance(raw, bytes) for _name_, raw in result)
    # Round-trips into the fingerprint the commitment covers.
    assert len(fingerprint_from_bytes(result)) == 64


# ---------------------------------------------------------------------------
# 4-6. The refusals. Each one is a way to lose the single attempt quietly.
# ---------------------------------------------------------------------------

def test_read_sealed_once_refuses_a_duplicate_name_in_the_read_set():
    """WITHOUT THIS, a duplicated name would be downloaded twice and the second
    read would be an audit entry no expected value predicted. Worse, it could
    make G7c's integer RIGHT FOR THE WRONG REASON - two reads of one object and
    zero of another still sums to the expected count.

    The refusal must happen before the second download, so the call count is
    asserted too.
    """
    pairs = _synthetic_pairs()
    dupe = pairs[0][0]
    download, calls = _counting_downloader(pairs)

    with pytest.raises(SealedReadError) as ei:
        read_sealed_once("gs://crucible-sealed-x7", [dupe, dupe], download)

    assert "duplicate read" in str(ei.value)
    assert dupe in str(ei.value)
    assert len(calls) == 1, "the duplicate was fetched before it was refused"


def test_read_sealed_once_refuses_a_downloader_that_returns_str_not_bytes():
    """WITHOUT THIS, a downloader handing back `str` would be hashed after an
    implicit decode, and decoding normalises the exact bytes the published
    commitment covers. The fingerprint would then be computed over a
    re-encoding rather than over what is in the bucket, and the seal would read
    BROKEN against an untouched set - or, worse, INTACT against a changed one.

    `bytearray` is accepted, `str` is not, and the two are asserted together so
    the check is a type check rather than a blanket refusal.
    """
    name = _name(1, "vendor-swap")

    with pytest.raises(SealedReadError) as ei:
        read_sealed_once("gs://b", [name], lambda path: "not bytes")
    assert "expected bytes" in str(ei.value)
    assert "str" in str(ei.value)

    with pytest.raises(SealedReadError):
        read_sealed_once("gs://b", [name], lambda path: None)

    # The accepting arm, so the refusal above is a type check and not a
    # function that rejects everything.
    ok = read_sealed_once("gs://b", [name], lambda path: bytearray(b"{}"))
    assert ok == [(name, b"{}")]


def test_read_sealed_once_raises_rather_than_returning_a_short_read():
    """WITHOUT THIS, an object that never arrived could leave a caller holding
    fewer pairs than it asked for, and a fingerprint over a subset is a
    perfectly valid-looking hex string that matches nothing.

    Three arms, because "short" has three shapes: the downloader RAISES for a
    missing object (the real GCS 404 case) and the error escapes rather than
    being swallowed into a shorter list; the module's own short-read guard
    exists and names the count; and on the success path the returned length
    always equals the requested length.
    """
    pairs = _synthetic_pairs()
    names = expected_object_names(name for name, _ in pairs)
    absent = names[1]
    download, calls = _counting_downloader(pairs, missing={absent})

    with pytest.raises(FileNotFoundError):
        read_sealed_once("gs://crucible-sealed-x7", names, download)

    # It stopped at the missing object. It did not carry on and hand back two.
    assert len(calls) == 2

    # There is no branch that returns a partial result. The module's own guard
    # names the count and raises; asserted on the source because no injected
    # downloader can reach it - which is the point, it is the last line of
    # defence behind the per-object checks.
    import inspect

    from crucible.transfer import sealed_io

    src = inspect.getsource(sealed_io.read_sealed_once)
    assert "short read" in src
    assert "raise SealedReadError(\"short read" in src, (
        "the short-read guard must RAISE, not return a smaller list")

    full, _calls = _counting_downloader(pairs)
    assert len(read_sealed_once("gs://b", names, full)) == len(names)


# ---------------------------------------------------------------------------
# 7. The name shape. The read set is decided before the network is touched.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    "../etc/passwd",
    "../../corpus/sealed/F4-dest-01-x.json",
    "F4-dest-1-x.json",                     # one digit, not two
    "F4-dest-01-x.json/../../secrets",
    "other-family-01-x.json",
    "F4-dest-01-UPPER.json",                # slug is [a-z0-9-]
    "F4-dest-01-x.txt",
    "F4-dest-01-x.json ",                   # trailing space
    "families/F4-dest-01-x.json",           # the prefix is added, not supplied
    "",
])
def test_expected_object_names_rejects_a_malformed_or_traversing_name(bad):
    """WITHOUT THIS, a name arriving from anywhere but the commitment - a
    listing, a config, a string built by concatenation - would be pasted
    straight into an object path. `"%s/families/%s" % (bucket, name)` does no
    escaping, so `../` walks out of `families/` and a wrong-family name reads
    an object no expected count predicted, which is a G7c mismatch and an
    invalid run.

    The commitment decides HOW MANY and WHICH. This regex is the only thing
    standing between that decision and an arbitrary string.
    """
    with pytest.raises(SealedReadError) as ei:
        expected_object_names([bad])
    assert "refusing to read" in str(ei.value)


def test_expected_object_names_accepts_well_formed_names_and_sorts_them():
    """The accepting arm. Without it the test above would pass against a
    function that refused everything, which would fail closed but would also
    make the whole transfer path dead code.

    Sorting is asserted here rather than left to the caller because the
    fingerprint is order-dependent: `expected_object_names` is where the order
    the hash depends on is established.
    """
    good = [_name(9, "iban-tail"), _name(1, "vendor-swap"), _name(12, "a-b-c")]
    names = expected_object_names(good)
    assert names == sorted(good)
    assert names[0] == "F4-dest-01-vendor-swap.json"
    # Digits in a slug are legal; only the instance index is fixed at two.
    assert expected_object_names(["F4-dest-24-b2b-swap.json"]) == \
        ["F4-dest-24-b2b-swap.json"]


# ---------------------------------------------------------------------------
# 8. Family assertion. A non-F4 object here means the read set was wrong.
# ---------------------------------------------------------------------------

def test_parse_instances_rejects_an_instance_declaring_a_non_F4_family():
    """WITHOUT THIS, an object from another family could be scored as a
    transfer result. The headline is about a family SEALED BEFORE the first
    patch was written; a non-F4 instance in this read means the read set was
    wrong before the network was touched, and the number computed from it is
    about something other than transfer.

    This is the assertion the training loader makes in the other direction -
    `corpus_seeds.py` raises `E_SEALED_FAMILY_REACHED` on F4 - and the two
    guards together are why neither path can drift into the other's corpus.
    """
    pairs = [(_name(1, "vendor-swap"), _body(1, "vendor-swap", family="fam_f2"))]
    with pytest.raises(SealedReadError) as ei:
        parse_instances(pairs)
    assert "declares family" in str(ei.value)
    assert "fam_f2" in str(ei.value)

    # A missing family declaration is refused too - absent is not "probably F4".
    silent = [(_name(1, "vendor-swap"),
               json.dumps({"instance_id": "x"}).encode("utf-8"))]
    with pytest.raises(SealedReadError):
        parse_instances(silent)

    # And bytes that are not JSON at all are refused as a read error, not as an
    # empty instance list.
    with pytest.raises(SealedReadError) as ei2:
        parse_instances([(_name(1, "vendor-swap"), b"{not json")])
    assert "not readable JSON" in str(ei2.value)


def test_parse_instances_accepts_fam_f4_and_the_short_F4_spelling():
    """The accepting arm, and it covers BOTH declaration keys. `family_id` and
    `family` are both read by the module, and both spellings - `fam_f4` and
    `F4` - are accepted. Without this the refusal test above would pass against
    a function that refused every instance, and the unseal would read zero
    instances from a full bucket.
    """
    pairs = [
        (_name(1, "vendor-swap"), _body(1, "vendor-swap", family="fam_f4")),
        (_name(2, "iban-tail"), _body(2, "iban-tail", family="F4")),
        (_name(3, "wire-detour"),
         json.dumps({"family": "fam_f4", "instance_id": "z"}).encode("utf-8")),
    ]
    instances = parse_instances(pairs)
    assert len(instances) == 3
    assert instances[0]["instance_id"] == "F4-dest-01-vendor-swap"
    assert [i.get("family_id") or i.get("family") for i in instances] == \
        ["fam_f4", "F4", "fam_f4"]


# ---------------------------------------------------------------------------
# 9. The object path, and the trailing slash that would otherwise double it.
# ---------------------------------------------------------------------------

def test_read_sealed_once_builds_families_paths_and_tolerates_a_trailing_slash():
    """WITHOUT THIS, `gs://crucible-sealed-x7/` (a bucket name copied from a
    console URL, which is how they arrive) would produce
    `gs://crucible-sealed-x7//families/...`. GCS treats that as a DIFFERENT
    object name, so every read 404s - or, if a retry policy hides the 404, the
    run reads nothing and reports an empty set, which is the failure mode
    ruling 61 is about: a check with no input cannot fail.

    Both spellings must produce byte-identical request paths, and the prefix
    must be `families/` - the names come from the commitment WITHOUT a prefix,
    so this module is the only place the prefix is applied.
    """
    pairs = _synthetic_pairs()
    names = expected_object_names(name for name, _ in pairs)

    plain, plain_calls = _counting_downloader(pairs)
    slashed, slashed_calls = _counting_downloader(pairs)

    a = read_sealed_once("gs://crucible-sealed-x7", names, plain)
    b = read_sealed_once("gs://crucible-sealed-x7/", names, slashed)

    assert plain_calls == slashed_calls
    assert a == b
    assert plain_calls[0].startswith("gs://crucible-sealed-x7/families/")
    assert "//families/" not in " ".join(slashed_calls)
    for path, name in zip(sorted(plain_calls), names):
        assert path == "gs://crucible-sealed-x7/families/%s" % name
