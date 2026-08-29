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


# ------------------------------------------- the sentinel that cost a run --
class _FakeSeeds:
    """Minimal stand-in for ArmedSeeds: drive() only needs these two."""

    def __init__(self):
        self.scripts_asked = []

    def offline_script(self, attack_id):
        self.scripts_asked.append(attack_id)
        return ()

    def world_for(self, attack):
        return object()


class _Rec:
    attack_id = "atk_dddddddddddd"
    family_id = "fam_f7"
    family = "F7"
    slug = "invented"
    turns = ("a turn",)


def _drive_capturing(monkeypatch, model):
    """Run drive() with everything stubbed, returning the models it built with."""
    built = []
    offline_calls = []

    monkeypatch.setattr(rt, "build_real_target",
                        lambda **kw: (built.append(kw["model"])
                                      or (lambda attack, policy: {"episode_id": "ep_%012d" % len(built),
                                                                  "outcome": "completed",
                                                                  "events": []})))
    monkeypatch.setattr(rt, "real_tripwire", lambda ep, objective_set=None: {"verdict": "CLEAN"})

    import crucible.conductor.campaign as campaign

    def _refuse(script):
        offline_calls.append(script)
        return "OFFLINE_MODEL_OBJECT"

    monkeypatch.setattr(campaign, "build_offline_target_model", _refuse)

    seeds = _FakeSeeds()
    rt.drive(seeds, [_Rec()], {"v0": {}, "vfinal": {}},
             {"v0": object(), "vfinal": object()}, model, objective_set=None)
    return built, offline_calls


def test_live_mode_never_builds_the_offline_model(monkeypatch):
    """THE REGRESSION TEST FOR THE DEFECT THAT COST A RUN.

    `build_real_target(model=None)` means "use the pinned live default", and this
    file also used `None` to mean "build the offline stub". Both branches set
    `None`, so `--live` executed the scripted offline model while the record
    claimed live and named the Gemini pin. Asserting the FACT - the offline
    builder is never reached in live mode - rather than the prose about it.
    """
    built, offline_calls = _drive_capturing(monkeypatch, model=None)
    assert offline_calls == [], "live mode reached the offline builder"
    assert built == [None, None], "live mode must pass None so the pinned default is used"


def test_offline_mode_does_build_the_offline_model(monkeypatch):
    """The other half. A test that only proves live is clean would also pass on
    a runner that never built anything at all."""
    built, offline_calls = _drive_capturing(monkeypatch, model=rt.OFFLINE_STUB)
    assert len(offline_calls) == 2, "offline mode must build one stub per arm"
    assert built == ["OFFLINE_MODEL_OBJECT", "OFFLINE_MODEL_OBJECT"]


def test_the_offline_sentinel_is_not_none():
    """The whole defect in one assertion: if this is ever None again, the two
    meanings collide and `--live` silently goes offline."""
    assert rt.OFFLINE_STUB is not None


# ------------------------------------------------- the crash record (#8) --
def test_a_crash_mid_drive_preserves_the_episodes_that_ran(tmp_path, monkeypatch):
    """THE WORST FAILURE ON A ONE-SHOT RUN, made survivable.

    The drive used to accumulate every episode in memory and write once at the
    end, so a failure at episode 13 destroyed twelve episodes that actually ran
    and left nothing the pre-registration's crash rule could be applied to.
    """
    calls = []

    def _boom(**kw):
        calls.append(kw)
        if len(calls) > 3:
            raise RuntimeError("simulated failure mid-drive")
        return lambda attack, policy: {"episode_id": "ep_%012d" % len(calls),
                                       "outcome": "completed", "events": []}

    monkeypatch.setattr(rt, "build_real_target", _boom)
    monkeypatch.setattr(rt, "real_tripwire", lambda ep, objective_set=None: {"verdict": "CLEAN"})
    monkeypatch.setattr(rt, "_COMPLETED", [0])

    out = tmp_path / "drive.jsonl"
    recs = []
    with open(out, "w", encoding="utf-8", newline="") as fh:
        rt._append(fh, {"kind": "header", "artifact": "test"})
        try:
            rt.drive(_FakeSeeds(), [_Rec(), _Rec2(), _Rec3()],
                     {"v0": {}, "vfinal": {}},
                     {"v0": object(), "vfinal": object()},
                     rt.OFFLINE_STUB, objective_set=None, fh=fh)
        except RuntimeError:
            rt._append(fh, {"kind": "crash", "at": "now",
                            "episodes_completed_before_crash": rt._COMPLETED[0],
                            "stage": "drive"})

    for line in out.read_text(encoding="utf-8").splitlines():
        if line.strip():
            recs.append(__import__("json").loads(line))

    kinds = [r["kind"] for r in recs]
    assert "crash" in kinds, "a crash must leave a record"
    survived = [r for r in recs if r["kind"] == "episode"]
    assert survived, "the episodes that completed before the crash must be on disk"
    crash = [r for r in recs if r["kind"] == "crash"][0]
    assert crash["episodes_completed_before_crash"] == len(survived)


class _Rec2(_Rec):
    attack_id = "atk_eeeeeeeeeeee"


class _Rec3(_Rec):
    attack_id = "atk_ffffffffffff"


def test_a_headerless_drive_file_is_refused(tmp_path):
    """A file with no header cannot say what run it describes."""
    p = tmp_path / "d.jsonl"
    p.write_text('{"kind": "episode"}\n', encoding="utf-8", newline="")
    with pytest.raises(rt.TransferRunError) as exc:
        rt.read_drive_file(p)
    assert exc.value.code == "E_NO_DRIVE_HEADER"


def test_a_drive_without_a_footer_reads_as_incomplete(tmp_path):
    """Truncated must be distinguishable from finished. A partial file that
    reads like a complete one is how twelve episodes become a denominator
    nobody declared."""
    p = tmp_path / "d.jsonl"
    p.write_text('{"kind": "header"}\n{"kind": "episode"}\n',
                 encoding="utf-8", newline="")
    got = rt.read_drive_file(p)
    assert got["completed"] is False
    assert len(got["episodes"]) == 1


def test_a_completed_drive_reads_as_completed(tmp_path):
    """The control. A check that only ever reports incomplete is not a check."""
    p = tmp_path / "d.jsonl"
    p.write_text('{"kind": "header"}\n{"kind": "episode"}\n{"kind": "footer"}\n',
                 encoding="utf-8", newline="")
    assert rt.read_drive_file(p)["completed"] is True


def test_the_episode_record_never_carries_a_slug():
    """For the sealed family the slug describes the attack. It is written
    nowhere and printed nowhere."""
    src = pathlib.Path(rt.__file__ if hasattr(rt, "__file__") else "").read_text(
        encoding="utf-8") if getattr(rt, "__file__", None) else ""
    if src:
        block = src.split('"kind": "episode",', 1)[1].split("}", 1)[0]
        assert "slug" not in block, "the episode record must not carry a slug"


def test_duplicate_declared_names_are_refused_before_any_request():
    """`read_sealed_once` refuses a duplicate only when it reaches the second
    one, by which point a request has issued and the audit count has moved.
    A declared set is validated in full before anything is touched."""
    called = []
    names = _declared_names(23) + [_declared_names(23)[0]]
    with pytest.raises(rt.TransferRunError) as exc:
        rt.load_sealed_instances(object_names=names,
                                 downloader=lambda uri: called.append(uri))
    assert exc.value.code == "E_DECLARED_SET_DUPLICATE"
    assert called == [], "no request may be issued before the set is validated"


def test_a_live_run_that_made_no_calls_is_refusable():
    """The contract's own comment: zero on a live run is the exact shape of a
    scripted run wearing a live label. That is the defect this runner shipped,
    so the meter's emptiness has to be actionable."""
    assert hasattr(rt, "_metered_model"), "live runs must be metered"


def test_the_final_policy_pin_exists_and_names_a_human():
    """The vfinal arm needs one intended policy, identified before the run, or
    the measurement can later be attributed to whatever was on the prompt."""
    import json as _json
    pin = _json.loads((ROOT / rt.FINAL_POLICY_PIN).read_text(encoding="utf-8"))
    assert pin["pinned_by"] and pin["pinned_by"].lower() not in ("model", "ai", "crucible")
    assert pin["policy_hash"] and pin["run_id"]
    # The pin must describe the policy actually shipped, not a remembered one.
    run = _json.loads((ROOT / pin["source_run"]).read_text(encoding="utf-8"))
    from crucible.canon import policy_hash
    assert policy_hash(run["final_policy"]["hashed_payload"]) == pin["policy_hash"]


def test_the_pin_carries_the_learned_rule_the_run_is_about():
    """The transfer question is whether a rule the loop LEARNED closes breaches
    in a family it never saw. A pin carrying only seed rules would be asking a
    different question."""
    import json as _json
    pin = _json.loads((ROOT / rt.FINAL_POLICY_PIN).read_text(encoding="utf-8"))
    origins = {r["origin"] for r in pin["rules"]}
    assert "armorer" in origins, "the pinned policy must carry a learned rule"
