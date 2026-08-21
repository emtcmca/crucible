"""test_corpus_known_bad_home.py - the nine, counted where they are authored.

`corpus.load` read `fixtures/known_bad/*.json` and expected the corpus INSTANCE
shape. `python -m corpus` therefore reported `E_KNOWN_BAD_COUNT: 0 known-bad
fixtures` on a repository that holds all nine, hand-written, in
`tests/golden_traces/known_bad/`.

TWO REASONS THE FIX IS A REPOINT AND NOT AN AUTHORING PASS

1. A second set under `fixtures/` puts KB1-KB9 in the tree twice, in two schemas.
   Two copies of a fixture drift the first time either is corrected, and nothing
   notices: both load, and the count is still nine.

2. **The instance schema cannot express three of them.** `validate_instance`
   demands a non-empty trace carrying exactly one `scored: true` call against a
   Part A tool. KB5 is a policy document the Warden must reject; KB9 is a
   document set plus a product lexicon the linter must reject and then accept;
   neither has an episode. The only way to satisfy the instance validator is to
   invent a tool call that never happened, in an artifact that gets hashed at D5.

Nothing was weakened to reach this. `KNOWN_BAD_TOTAL` is still nine, `must_fail`
is still refused by name, and every fixture still declares its own
`expected_verdict` - because only five of the nine are breach fixtures, and
`known_bad_expected_verdict_rate == 1.0` is what decides whether the RUN is
valid.
"""

import json

import pytest

from corpus.errors import CorpusError
from corpus.load import KNOWN_BAD_DIR, load_known_bads
from corpus.schema import validate_instance, validate_known_bad
from corpus.model import KNOWN_BAD_TOTAL, load_part_a

MANIFEST = load_part_a()


def _kb(kb_id):
    return json.loads((KNOWN_BAD_DIR / ("%s.json" % kb_id)).read_text(encoding="utf-8"))


def test_all_nine_load():
    nine = load_known_bads()
    assert len(nine) == KNOWN_BAD_TOTAL
    assert sorted(d["kb_id"] for d in nine) == ["KB%d" % n for n in range(1, 10)]


def test_they_are_not_all_breach_fixtures():
    """The fact a blanket boolean would erase. Five of nine."""
    verdicts = {d["kb_id"]: d["expected_verdict"] for d in load_known_bads()}
    assert sum(1 for v in verdicts.values() if v == "BREACH") == 5
    assert verdicts["KB5"] == "REJECT"
    assert verdicts["KB6"] == "INVALID"
    assert verdicts["KB8"] == "CLEAN"
    assert verdicts["KB9"].startswith("LINTER_")


@pytest.mark.parametrize("kb_id", ["KB5", "KB9"])
def test_the_instance_validator_cannot_express_the_component_fixtures(kb_id):
    """The load-bearing negative. This is WHY the bucket is not `fixtures/`.

    If this test ever passes silently - if `validate_instance` stops raising -
    someone has given KB5 an invented episode, and the fixture is no longer the
    artifact the Warden and the linter are graded against."""
    doc = dict(_kb(kb_id))
    doc["kind"] = "known_bad"
    doc["slug"] = kb_id
    with pytest.raises(CorpusError):
        validate_instance(doc, manifest=MANIFEST)


def test_a_second_home_is_refused_before_anything_is_read(tmp_path):
    second = tmp_path / "known_bad"
    second.mkdir()
    (second / "KB1.json").write_text("{}", encoding="utf-8")
    with pytest.raises(CorpusError) as e:
        load_known_bads(second_home=second)
    assert e.value.code == "E_KNOWN_BAD_SECOND_HOME"


def test_an_empty_second_home_is_fine():
    """`fixtures/known_bad/` holds a `.gitkeep` and nothing else. The refusal is
    about `*.json`, not about the directory existing."""
    assert len(load_known_bads()) == KNOWN_BAD_TOTAL


def test_a_duplicate_kb_id_is_refused(tmp_path):
    src = _kb("KB1")
    for name in ("a.json", "b.json"):
        (tmp_path / name).write_text(json.dumps(src), encoding="utf-8")
    with pytest.raises(CorpusError) as e:
        load_known_bads(directory=tmp_path, second_home=tmp_path / "nope")
    assert e.value.code == "E_DUPLICATE_KNOWN_BAD_ID"


def test_must_fail_is_still_refused_by_name():
    doc = dict(_kb("KB8"))
    doc["must_fail"] = True
    with pytest.raises(CorpusError) as e:
        validate_known_bad(doc)
    assert e.value.code == "E_MUST_FAIL_BOOLEAN"


def test_a_fixture_with_no_expected_verdict_is_refused():
    doc = dict(_kb("KB1"))
    doc["expected_verdict"] = ""
    with pytest.raises(CorpusError) as e:
        validate_known_bad(doc)
    assert e.value.code == "E_KNOWN_BAD_NO_VERDICT"


def test_a_fixture_aimed_at_no_component_is_refused():
    doc = dict(_kb("KB1"))
    doc["component"] = "AGENT"
    with pytest.raises(CorpusError) as e:
        validate_known_bad(doc)
    assert e.value.code == "E_KNOWN_BAD_COMPONENT"


@pytest.mark.parametrize("field", ["a_wrong_verdict_means",
                                   "not_passable_by_accident_because"])
def test_a_fixture_that_cannot_argue_for_itself_is_refused(field):
    """These two are not commentary. A known-bad exists to prove a checker can
    fail; one that never says what its own wrong verdict would mean is a fixture
    nobody can grade."""
    doc = dict(_kb("KB1"))
    del doc[field]
    with pytest.raises(CorpusError) as e:
        validate_known_bad(doc)
    assert e.value.code == "E_KNOWN_BAD_MISSING_FIELD"
