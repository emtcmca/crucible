"""test_bundle_reader.py - L6's negative check NC-2, written BEFORE the reader.

    A BUNDLE WITH A MISSING HASH MUST BE REJECTED BY THE VIEWER, NOT RENDERED
    WITH A BLANK.

That is the whole point of the reader. A bundle that renders beautifully while
missing the hash that makes it meaningful is worse than one that fails to open,
because the first one looks like evidence and the second one looks like a bug.

`CONVENTIONS.md` section 8 rule 2: a check that cannot fail is not measuring
anything. So the suite runs against two kinds of implementation:

  crucible.replay          the real reader. Every damaged bundle must be
                           REJECTED and every well-formed one ACCEPTED.
  tests/strawman_replay    three deliberately-wrong readers. A NAMED,
                           PRE-DECLARED bundle must slip past each one. If a
                           strawman ever rejects the bundle it is declared blind
                           to, the SUITE has stopped measuring and that is a
                           failure, not a green run.

THE FIXTURE
-----------
`contracts/golden/C6-evidence_bundle.valid.json`, unmodified, is the accepted
case. Damage is applied by `strawman_replay.mutate`, so the mutation a test
applies and the mutation a strawman is declared blind to are named by the SAME
string. Two lists of mutation names drift apart; one does not.

WHAT THE SCHEMA CANNOT DO, AND WHY THIS FILE EXISTS ANYWAY
----------------------------------------------------------
`contracts/golden/C6-evidence_bundle.KNOWN_BAD.json` declares FOUR reasons it
must fail. The C6 schema catches three of them. The fourth - `sep_by_split`
absent - is not a schema failure, because ruling 17 makes that field a permanent
reporting requirement while the schema does not list it in `required`. Schema
validation therefore accepts a bundle ruling 17 forbids, and `schema_only_read`
is kept here forever to prove it still does.
"""

import copy
import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
GOLDEN = REPO / "contracts" / "golden" / "C6-evidence_bundle.valid.json"

from tests import strawman_replay  # noqa: E402


@pytest.fixture(scope="module")
def valid_bundle():
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def _raw(bundle):
    return json.dumps(bundle).encode("utf-8")


# --------------------------------------------------------------------------
# The fixture itself must be intact before it can test anything.
# --------------------------------------------------------------------------

def test_the_golden_bundle_carries_what_c6_says_a_bundle_carries(valid_bundle):
    """Five hash-locks across six fields, a frozen episode.* block and an
    ordered prefix on every episode, and the recorded v0 benign traces. A
    bundle missing any of them is not a bundle."""
    locks = valid_bundle["run_manifest"]["hash_locks"]
    assert set(locks) == {"gate_rule_hash", "target_agent_hash", "manifest_hash",
                          "objective_set_hash", "corpus_hash", "derived_schema_hash"}
    assert all(len(v) == 16 for v in locks.values())
    for ep in valid_bundle["episodes"]:
        assert ep["episode_frozen_context"]["frozen_at"] == "before_first_user_turn"
        assert isinstance(ep["episode_prefix"], list)
    assert len(valid_bundle["v0_benign_traces"]) >= 24
    assert valid_bundle["sep_by_split"] == {"policy_separated": 18,
                                            "approval_oracle_separated": 4}


# --------------------------------------------------------------------------
# THE REAL READER - every one of these must be REJECTED.
# --------------------------------------------------------------------------

REJECTIONS = [
    ("episode_missing_derived_schema_hash",
     "the episode writer refuses to write it; so does the reader"),
    ("episode_missing_manifest_hash",
     "Part A's half of ruling 20's split - two hashes are two things to forget"),
    ("episode_missing_objective_set_hash",
     "the definition of breach, unstamped on the episode it graded"),
    ("lock_blanked",
     "present and empty. Blank satisfies 'the key exists' and carries nothing"),
    ("lock_missing",
     "a hash-lock absent from the run manifest entirely"),
    ("episode_missing_frozen_context",
     "ruling 16, and nothing else in the build catches it"),
    ("frozen_at_moved",
     "frozen AFTER the first user turn is not frozen"),
    ("episode_missing_prefix",
     "without the ordered prefix the episode-scoped predicates cannot be replayed"),
    ("episode_stamp_disagrees_with_manifest",
     "two arms measuring under two definitions of breach"),
    ("verdict_stamp_disagrees_with_episode",
     "the verdict names a different Objective Set than the episode does"),
    ("sep_by_split_missing",
     "ruling 17 - without it the headline numbers are unfalsifiable"),
    ("sep_by_split_at_parity",
     "ruling 17's authoring gate: parity means stop and re-author"),
    ("benign_traces_short",
     "the benign denominator is fixed permanently at 24"),
    ("float_in_payload",
     "canonicalization restriction 4 - no float may enter a hashed payload"),
    ("null_in_payload",
     "canonicalization restriction 5 - an absent fact is an absent key"),
]


@pytest.mark.parametrize("how,why", REJECTIONS, ids=[r[0] for r in REJECTIONS])
def test_real_reader_rejects(valid_bundle, how, why):
    from crucible.replay import BundleRejected, read_bundle_bytes
    damaged = strawman_replay.mutate(valid_bundle, how)
    with pytest.raises(BundleRejected) as exc:
        read_bundle_bytes(_raw(damaged))
    assert exc.value.defects, "rejected with no defect named: %s" % why


def test_real_reader_accepts_the_untouched_bundle(valid_bundle):
    from crucible.replay import read_bundle_bytes
    bundle, report = read_bundle_bytes(_raw(valid_bundle))
    assert report.ok
    assert bundle["bundle_version"] == 1


def test_a_rejection_names_what_is_missing_not_just_that_something_is(valid_bundle):
    """A reader that refuses without saying why sends the reader to the source.
    The defect text has to be enough to fix the bundle without opening C6."""
    from crucible.replay import BundleRejected, read_bundle_bytes
    damaged = strawman_replay.mutate(valid_bundle, "episode_missing_derived_schema_hash")
    with pytest.raises(BundleRejected) as exc:
        read_bundle_bytes(_raw(damaged))
    text = str(exc.value)
    assert "derived_schema_hash" in text
    assert valid_bundle["episodes"][0]["episode_id"] in text


def test_a_bom_is_refused_rather_than_stripped(valid_bundle):
    """canonicalization.md restriction 1. Stripping a BOM and moving on is the
    trade the contract refuses by name, and on Windows this is a live hazard
    rather than a theoretical one."""
    from crucible.replay import BundleRejected, read_bundle_bytes
    with pytest.raises(BundleRejected):
        read_bundle_bytes(b"\xef\xbb\xbf" + _raw(valid_bundle))


# --------------------------------------------------------------------------
# THE STRAWMEN - each must FAIL to reject the bundle it is declared blind to.
# If one starts rejecting, this suite has stopped measuring.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("how", sorted(strawman_replay.LENIENT_MUST_NOT_REJECT))
def test_lenient_reader_renders_a_blank_where_a_hash_belongs(valid_bundle, how):
    damaged = strawman_replay.mutate(valid_bundle, how)
    out = strawman_replay.lenient_read(_raw(damaged))
    blanks = _blank_fields(out)
    assert blanks, (
        "strawman_replay.lenient_read produced no blank for %r. It is declared "
        "blind to this and it is not - THE SUITE HAS STOPPED MEASURING, because "
        "the real reader's rejection is now unopposed. %s"
        % (how, strawman_replay.LENIENT_MUST_NOT_REJECT[how]))


def _blank_fields(bundle):
    """Every hash-shaped field that came out empty, or a frozen block that came
    out empty. Exactly what "rendered with a blank" looks like on the screen."""
    out = []
    for key, value in bundle.get("run_manifest", {}).get("hash_locks", {}).items():
        if value == "":
            out.append("hash_locks.%s" % key)
    for ep in bundle.get("episodes", []):
        for key in ("objective_set_hash", "manifest_hash", "derived_schema_hash"):
            if ep.get(key) == "":
                out.append("%s.%s" % (ep.get("episode_id"), key))
        if ep.get("episode_frozen_context") == {}:
            out.append("%s.episode_frozen_context" % ep.get("episode_id"))
    return out


@pytest.mark.parametrize("how", sorted(strawman_replay.SELF_COMPARING_MUST_NOT_REJECT))
def test_self_comparing_verifier_finds_nothing(valid_bundle, how):
    """Comparing a stored hash to itself passes on a truncated write, a partial
    write and a corrupted read, because in each case the value is being compared
    to a copy of itself. scripts/verify-chain.py says this in its docstring and
    this is the same claim, held to."""
    damaged = strawman_replay.mutate(valid_bundle, how)
    assert strawman_replay.self_comparing_verify(damaged) == [], (
        "strawman_replay.self_comparing_verify reported a defect. It compares "
        "each field to itself and therefore cannot. THE SUITE IS BROKEN.")


@pytest.mark.parametrize("how", sorted(strawman_replay.SCHEMA_ONLY_MUST_NOT_REJECT))
def test_schema_validation_alone_accepts_a_bundle_ruling_17_forbids(valid_bundle, how):
    """The gap this lane's reader exists to close, pinned so it cannot quietly
    become closed by the schema instead - which would be fine, but would mean
    this file is asserting a property nothing holds any more."""
    from crucible.replay import c6_validator
    damaged = strawman_replay.mutate(valid_bundle, how)
    accepted = strawman_replay.schema_only_read(_raw(damaged), c6_validator())
    assert accepted is not None, (
        "schema_only_read rejected %r. If C6 now REQUIRES sep_by_split then "
        "ruling 17 is enforced by the contract and this strawman is obsolete - "
        "but that is a contract change, and a lane reports it rather than "
        "adjusting the test. %s" % (how, strawman_replay.SCHEMA_ONLY_MUST_NOT_REJECT[how]))


def test_the_real_reader_rejects_exactly_what_the_strawmen_miss(valid_bundle):
    """The meta-check. Every mutation any strawman is declared blind to must be
    on the real reader's rejection list. A strawman blind to something nothing
    else catches is a hole with a comment next to it."""
    from crucible.replay import BundleRejected, read_bundle_bytes
    declared = (set(strawman_replay.LENIENT_MUST_NOT_REJECT)
                | set(strawman_replay.SELF_COMPARING_MUST_NOT_REJECT)
                | set(strawman_replay.SCHEMA_ONLY_MUST_NOT_REJECT))
    listed = {h for h, _ in REJECTIONS}
    assert declared <= listed, (
        "declared blind to %s, which the real reader is not tested to reject"
        % sorted(declared - listed))
    for how in sorted(declared):
        with pytest.raises(BundleRejected):
            read_bundle_bytes(_raw(strawman_replay.mutate(valid_bundle, how)))


def test_every_mutation_name_is_real(valid_bundle):
    """A typo in a mutation name would make `mutate` raise KeyError, which
    pytest.raises(BundleRejected) would report as an error rather than as a
    pass - but only if the name is used. This walks all of them."""
    for how, _ in REJECTIONS:
        assert strawman_replay.mutate(valid_bundle, how) != valid_bundle, how
    with pytest.raises(KeyError):
        strawman_replay.mutate(valid_bundle, "no_such_mutation")


def test_mutate_does_not_touch_its_input(valid_bundle):
    """Every case above shares one module-scoped fixture. If `mutate` damaged
    it in place, case two would run against the wreckage of case one and the
    parametrization would be measuring the wrong thing."""
    before = copy.deepcopy(valid_bundle)
    strawman_replay.mutate(valid_bundle, "lock_blanked")
    assert valid_bundle == before
