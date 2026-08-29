"""The transfer runner's guards, exercised without touching the seal.

WHY THESE TESTS EXIST AND WHAT THEY DELIBERATELY DO NOT COVER.

The sealed drive runs exactly once. Every refusal on that path therefore has to
be proven somewhere that is not the run itself, because a guard whose first
execution is the irreplaceable attempt is a guard nobody has tested.

The downloader is injected in every test here, so no network call is made and no
sealed object is read. What stays untested by design is the one thing that cannot
be rehearsed: the real `objects.get` against the real bucket as the attested
identity. That gap is named rather than papered over.

Every fixture below is INVENTED. No sealed instance content appears in this file.
"""

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import importlib.util                                                # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "record_f4_transfer", ROOT / "scripts" / "record-f4-transfer.py")
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)


# --------------------------------------------------------------- the arms --
def test_the_two_arms_get_different_attack_ids():
    """The collision this runner exists to avoid.

    `_episode_id_for` derives the episode id from the attack id alone, so if
    both arms carried one attack id both episodes would carry one episode id.
    """
    a = rt.armed_attack_id("atk_aaaaaaaaaaaa", "v0")
    b = rt.armed_attack_id("atk_aaaaaaaaaaaa", "vfinal")
    assert a != b
    assert a.startswith("atk_") and b.startswith("atk_")
    assert len(a) == len("atk_") + 12


def test_an_armed_id_is_stable_across_calls():
    """It has to be a pure function of (instance, arm): the drive builds the id
    and the record carries it, and a value that moved between them would put the
    episode under an instance that never ran."""
    assert (rt.armed_attack_id("atk_bbbbbbbbbbbb", "v0")
            == rt.armed_attack_id("atk_bbbbbbbbbbbb", "v0"))


def test_an_unknown_arm_is_refused():
    with pytest.raises(rt.TransferRunError) as exc:
        rt.armed_attack_id("atk_cccccccccccc", "vmiddle")
    assert exc.value.code == "E_UNKNOWN_ARM"


# ------------------------------------------------------------- the guards --
def test_sealed_without_authorisation_is_refused():
    with pytest.raises(rt.TransferRunError) as exc:
        rt.load_instances(family="F7", sealed=True, opening_the_seal=False)
    assert exc.value.code == "E_SEAL_NOT_AUTHORISED"


def test_the_sealed_family_cannot_be_reached_through_the_training_door():
    """A filter would drop it silently. This refuses, so the two paths cannot
    quietly become one."""
    with pytest.raises(rt.TransferRunError) as exc:
        rt.load_instances(family="F4", sealed=False, opening_the_seal=False)
    assert exc.value.code == "E_SEALED_FAMILY_VIA_TRAINING"


def test_an_empty_family_is_refused_rather_than_driven():
    with pytest.raises(rt.TransferRunError) as exc:
        rt.load_instances(family="F99", sealed=False, opening_the_seal=False)
    assert exc.value.code == "E_FAMILY_EMPTY"


def test_both_paths_return_three_values():
    """The sealed path also returns the names it declared in advance. A caller
    unpacking two would crash on the one run that cannot be repeated."""
    seeds, picked, names = rt.load_instances(
        family="F7", sealed=False, opening_the_seal=False)
    assert names is None
    assert picked and seeds is not None


# ------------------------------------------------- the sealed read itself --
def _fake_downloader(payload_by_name):
    def download(uri):
        name = uri.rsplit("/", 1)[-1]
        if name not in payload_by_name:
            raise AssertionError("read an object the test did not declare: %s" % name)
        return payload_by_name[name]
    return download


def _sealed_ids():
    m = json.loads((ROOT / rt.F4_MANIFEST).read_text(encoding="utf-8"))
    return m["instance_ids"]


def _declared_names(n=24):
    """INVENTED object names in the shape the seal uses. Not the real names,
    which are withheld from the published manifest on purpose."""
    return ["F4-dest-%02d-invented-placeholder.json" % i for i in range(1, n + 1)]


def test_the_read_set_cannot_be_derived_and_must_be_supplied():
    """The object names are withheld from the published manifest deliberately,
    so a run that was not handed them has no legitimate way to obtain them.
    Listing the bucket would fit the declared set to what came back."""
    with pytest.raises(rt.TransferRunError) as exc:
        rt.load_sealed_instances(object_names=None, downloader=_fake_downloader({}))
    assert exc.value.code == "E_NO_DECLARED_READ_SET"


def test_a_declared_set_of_the_wrong_size_is_refused_before_the_network():
    called = []
    with pytest.raises(rt.TransferRunError) as exc:
        rt.load_sealed_instances(object_names=_declared_names(23),
                                 downloader=lambda uri: called.append(uri))
    assert exc.value.code == "E_DECLARED_SET_SIZE"
    assert called == [], "the size check must fire before any request"


def test_a_fingerprint_that_does_not_match_the_commitment_halts():
    """THE CENTRAL GUARD. If the bytes on the wire do not hash to the published
    commitment, the set being measured is not the set that was sealed, and every
    number derived from it describes a corpus nobody committed to."""
    names = _declared_names()
    payload = {n: b'{"family": "F4", "sealed": true}' for n in names}
    with pytest.raises(rt.TransferRunError) as exc:
        rt.load_sealed_instances(object_names=names,
                                 downloader=_fake_downloader(payload))
    assert exc.value.code == "E_SEAL_FINGERPRINT_MISMATCH"


def test_the_read_set_is_decided_before_the_network_not_after():
    """The downloader is only ever asked for names the manifest declared. A run
    that read whatever the bucket happened to hold could not assert afterwards
    that it read only what it named."""
    asked = []

    def download(uri):
        asked.append(uri.rsplit("/", 1)[-1])
        return b'{"family": "F4", "sealed": true}'

    with pytest.raises(rt.TransferRunError):
        rt.load_sealed_instances(object_names=_declared_names(), downloader=download)
    assert sorted(asked) == sorted(_declared_names())


def test_every_object_is_read_exactly_once():
    """A second read of one object makes the audit count right for the wrong
    reason, so the reader refuses a duplicate rather than tolerating it."""
    seen = []

    def download(uri):
        seen.append(uri)
        return b'{"family": "F4", "sealed": true}'

    with pytest.raises(rt.TransferRunError):
        rt.load_sealed_instances(object_names=_declared_names(), downloader=download)
    assert len(seen) == len(set(seen)) == 24


# ------------------------------------------------------- the sealed adapt --
def _instance(**over):
    doc = {
        "slug": "invented-instance",
        "family": "F4",
        "sealed": True,
        "input_turns": ["a turn"],
        "scenario": {"order": {"order_id": "ORD-0001"},
                     "account": {"account_id": "CUST-0001"}},
    }
    doc.update(over)
    return doc


def test_the_sealed_door_refuses_a_training_family():
    """The mirror image of `_adapt`'s refusal of F4."""
    from crucible.conductor.corpus_seeds import CorpusSeedError
    with pytest.raises(CorpusSeedError) as exc:
        rt._adapt_sealed(_instance(family="F7"))
    assert exc.value.code == "E_NOT_THE_SEALED_FAMILY"


def test_the_sealed_door_refuses_an_instance_not_marked_sealed():
    from crucible.conductor.corpus_seeds import CorpusSeedError
    with pytest.raises(CorpusSeedError) as exc:
        rt._adapt_sealed(_instance(sealed=False))
    assert exc.value.code == "E_SEALED_FLAG_ABSENT"


def test_an_instance_with_no_turns_is_refused():
    """The turns ARE the attack; an instance with none has nothing to drive."""
    from crucible.conductor.corpus_seeds import CorpusSeedError
    with pytest.raises(CorpusSeedError) as exc:
        rt._adapt_sealed(_instance(input_turns=[]))
    assert exc.value.code == "E_INPUT_TURNS"


def test_no_sealed_instance_content_appears_in_this_file():
    """The control on the tests themselves. Every fixture above is invented, and
    this asserts it rather than trusting the author."""
    text = pathlib.Path(__file__).read_text(encoding="utf-8")
    for iid in _sealed_ids():
        assert iid not in text, "a real sealed instance id reached the tests"
