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
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
GOLDEN = REPO / "contracts" / "golden" / "C6-evidence_bundle.valid.json"

from tests import strawman_replay  # noqa: E402
from crucible.replay.integrity import BENIGN_DENOMINATOR as BENIGN_DEN  # noqa: E402


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
    from crucible.replay.integrity import BENIGN_DENOMINATOR
    assert len(valid_bundle["v0_benign_traces"]) >= BENIGN_DENOMINATOR, (
        "the golden bundle carries %d recorded v0 traces against a denominator "
        "of %d. Read from the constant, never retyped: this assertion said "
        ">= 24 while ruling 43 moved the denominator to 26, so the repo's own "
        "canonical valid bundle was two traces short and this test agreed with "
        "it." % (len(valid_bundle["v0_benign_traces"]), BENIGN_DENOMINATOR))
    assert valid_bundle["sep_by_split"] == {"policy_separated": 18,
                                            "approval_oracle_separated": 4}


def test_the_golden_bundle_can_answer_the_questions_the_product_exists_to_answer(
        valid_bundle):
    """WHAT WAS TESTED, HOW IT WAS ANSWERED, WHAT WAS FOUND, WHAT WAS PATCHED,
    AND WHY THE GATE ACCEPTED IT - from the file, with no source code open.

    This is the acceptance test for the 2026-08-22 extension, written as the
    questions rather than as a field list. A bundle that validates and cannot
    answer these is a scoreboard.
    """
    # what was tested - and a GENERATED attack carries its own bytes, because
    # it exists in no corpus and on no disk.
    catalogue = {a["attack_id"]: a for a in valid_bundle["attacks"]}
    assert catalogue, "no attack catalogue"
    generated = [a for a in catalogue.values() if a["provenance"] == "generated"]
    assert generated, "the fixture exercises no generated attack, so the case "                      "the extension exists for is untested"
    for attack in generated:
        assert attack["instruction"].strip()

    # every episode is traceable to what was tested.
    for ep in valid_bundle["episodes"]:
        assert ("attack_id" in ep) != ("fixture_id" in ep)
        if "attack_id" in ep:
            assert ep["attack_id"] in catalogue
        # which provider actually served it.
        assert ep["model_provenance"]["provider"]

    # what was found - prose, not an id pointing at nothing.
    autopsies = valid_bundle["autopsies"]
    assert autopsies
    assert any(str(v).strip() for a in autopsies
               for v in (a.get("human_only") or {}).values())

    # what was patched - including a REJECTED proposal, which exists in no
    # other artifact and is the more interesting half.
    proposals = valid_bundle["patch_proposals"]
    assert any(p["accepted"] for p in proposals)
    assert any(not p["accepted"] for p in proposals)
    assert all(r["dsl_text"].strip() for p in proposals for r in p["rules"])

    # what the policy now SAYS, readable without fetching a bucket object.
    for entry in valid_bundle["policy_chain"]:
        assert entry["rules"]
        assert all(r["dsl_text"].strip() for r in entry["rules"])

    # which part of the definition of breach was ever reached.
    clauses = valid_bundle["clause_coverage"]["clauses"]
    assert clauses
    assert any(not c["episodes_fired"] for c in clauses), (
        "every clause fired in the fixture, so the NEVER-FIRED row - the row "
        "that matters - is not exercised by anything")

    # what was excluded, by name, and what the denominator was.
    assert isinstance(valid_bundle["excluded"], list)
    assert valid_bundle["round_census"]
    assert any(r["outcome"] == "INCOMPLETE" for r in valid_bundle["round_census"]), (
        "INCOMPLETE has been a legal round outcome that no artifact in this "
        "repository has ever carried. The fixture is where that stops.")

    # and the caveats travel with the file.
    assert set(valid_bundle["labels"]) == {
        "k", "sep_by_split", "target_tier", "benign_regression", "trust_root"}


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
     "the benign denominator is fixed permanently, and 23 is short of it"),
    ("benign_traces_at_the_old_denominator",
     "24 traces was a COMPLETE suite until ruling 43 and is a SHORT one after "
     "it. This is the exact bundle that passed the gate clean for a day"),
    ("float_in_payload",
     "canonicalization restriction 4 - no float may enter a hashed payload"),
    ("null_in_payload",
     "canonicalization restriction 5 - an absent fact is an absent key"),

    # THE 2026-08-22 EXTENSION. Each of these is a way a bundle can be a
    # complete-looking run of record that a reader draws a WRONG CONCLUSION
    # from - which is the bar for a required field, as against a convenient one.
    ("attacks_missing",
     "the bundle records which attacks ran and cannot say what any of them were"),
    ("generated_attack_text_missing",
     "a generated attack recorded as an id. It exists in no corpus and on no "
     "disk, so this record was the only copy there would ever be"),
    ("attack_uncatalogued",
     "an episode's verdict that cannot be traced to what was tested"),
    ("autopsies_missing",
     "the bundle can say a breach happened and cannot say what was found"),
    ("autopsy_missing_for_breach",
     "a breach with no autopsy is a finding nobody wrote down"),
    ("policy_rules_missing",
     "a policy version that is four hashes and a bucket URI. 'Here is the rule "
     "that now stops it' has to be legible from the bundle alone"),
    ("coverage_missing",
     "nothing then says which clauses were ever reached, and a rate over an "
     "unknown fraction of the definition of breach reads as a rate over all of it"),
    ("coverage_hash_disagrees",
     "coverage of a DIFFERENT Objective Set is not coverage of this one"),
    ("coverage_never_fired_for_a_breach",
     "a clause that produced a BREACH recorded as never having fired - two arms "
     "counting the same clause differently"),
    ("labels_missing",
     "every figure in the file would then travel without its caveats, which is "
     "the one failure this project must never allow"),
    ("label_k_disagrees",
     "a label that has stopped being true, which is worse than a missing one"),
    ("label_tier_disagrees",
     "the tier label no longer names the model that was actually attacked"),
    ("provenance_missing",
     "which parts of the run were scripted then lives nowhere in the record"),
    ("provenance_live_with_standin",
     "a stand-in run wearing a live label. Every other field looks the same "
     "either way, which is exactly why this one is required"),
    ("provenance_live_without_model_calls",
     "mode live with zero model calls - the arithmetic shape of the same lie"),
    ("exclusion_ledger_missing",
     "an exclusion count with no denominator cannot be tested against the "
     "5% ceiling; a denominator with no named list cannot be audited"),
    ("exclusion_ledger_short",
     "a round claiming more exclusions than it names. Silent exclusion turns "
     "flakiness into apparent hardening"),
    ("exclusion_ceiling_breached",
     "past the 5% ceiling and still recorded as SCORED. measurement-spec 5.1 "
     "makes that round INCOMPLETE and it must be RE-RUN, not reported"),
    ("census_arithmetic_broken",
     "attempted != scorable + excluded. The denominator does not account for itself"),
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
    # 2 as of 2026-08-22. The bundle stopped being a hash ledger and became
    # the run of record: attack text, autopsies, rule text, clause coverage,
    # the exclusion ledger, execution provenance and the labels all became
    # REQUIRED in one change, so a v1 bundle and a v2 bundle are two
    # different claims about what evidence is.
    assert bundle["bundle_version"] == 2


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
    """Parametrized over an EMPTY set as of 2026-08-20, so it runs zero cases.

    That is the correct state and not a disabled test: the set is empty because
    the single gap it held was closed in the contract. See
    `test_schema_only_gap_is_closed` for the assertion from the other side.
    """
    from crucible.replay import c6_validator
    damaged = strawman_replay.mutate(valid_bundle, how)
    accepted = strawman_replay.schema_only_read(_raw(damaged), c6_validator())
    assert accepted is not None, (
        "schema_only_read rejected %r, and this set is supposed to hold only "
        "mutations the schema CANNOT see. Retire the entry rather than "
        "loosening the schema." % how)


def test_schema_only_gap_is_closed(valid_bundle):
    """C6 now REQUIRES sep_by_split, so schema validation alone rejects a bundle
    ruling 17 forbids. This lane pinned the gap and reported it; the coordinator
    changed the contract; this asserts the change actually took.

    Written from the other side ON PURPOSE. Deleting the pin and adding nothing
    would leave the property untested and the tree looking greener for it.
    """
    from crucible.replay import c6_validator
    damaged = strawman_replay.mutate(valid_bundle, "sep_by_split_missing")
    # schema_only_read signals rejection by RAISING, not by returning None.
    with pytest.raises(ValueError) as ei:
        strawman_replay.schema_only_read(_raw(damaged), c6_validator())
    assert "sep_by_split" in str(ei.value), (
        "C6 rejected the bundle for some OTHER reason, so this test would pass "
        "even if the sep_by_split requirement were removed. Ruling 17 makes the "
        "split a PERMANENT reporting requirement: a suite the APPROVAL_ORACLE "
        "separates produces IDENTICAL headline numbers to one the policy "
        "separates, and only that ratio tells them apart.")
    assert not strawman_replay.SCHEMA_ONLY_MUST_NOT_REJECT, (
        "the schema-only blind set is non-empty again; a new gap needs a new "
        "pin and a report, not a quiet entry")


@pytest.mark.parametrize("how", sorted(strawman_replay.FIELDWISE_MUST_NOT_REJECT),
                         ids=sorted(strawman_replay.FIELDWISE_MUST_NOT_REJECT))
def test_a_fieldwise_reader_cannot_see_a_disagreement(valid_bundle, how):
    """THE NEGATIVE CONTROL FOR THE 2026-08-22 CROSS-FIELD CHECKS.

    Five of the new checks are not expressible in JSON Schema at all: a label
    that contradicts the parameter it describes, coverage of a different
    Objective Set, mode 'live' beside a stand-in component, an exclusion share
    past the 5% ceiling, a census that claims more exclusions than the ledger
    names. Every field involved is individually present, individually typed and
    individually in range.

    `fieldwise_read` is the careful implementation that checks all of that and
    compares nothing, and it must ACCEPT every one of these. If it ever starts
    rejecting one, the case has stopped being a cross-field case and this
    parametrization is no longer measuring what its name says.
    """
    from crucible.replay import c6_validator
    damaged = strawman_replay.mutate(valid_bundle, how)
    accepted = strawman_replay.fieldwise_read(_raw(damaged), c6_validator())
    assert accepted is not None, (
        "fieldwise_read rejected %r. This set holds only defects that exist "
        "BETWEEN two fields; retire the entry rather than loosening the "
        "strawman." % how)


def test_the_real_reader_rejects_exactly_what_the_strawmen_miss(valid_bundle):
    """The meta-check. Every mutation any strawman is declared blind to must be
    on the real reader's rejection list. A strawman blind to something nothing
    else catches is a hole with a comment next to it."""
    from crucible.replay import BundleRejected, read_bundle_bytes
    declared = (set(strawman_replay.LENIENT_MUST_NOT_REJECT)
                | set(strawman_replay.SELF_COMPARING_MUST_NOT_REJECT)
                | set(strawman_replay.SCHEMA_ONLY_MUST_NOT_REJECT)
                | set(strawman_replay.FIELDWISE_MUST_NOT_REJECT))
    listed = {h for h, _ in REJECTIONS}
    assert declared <= listed, (
        "declared blind to %s, which the real reader is not tested to reject"
        % sorted(declared - listed))
    for how in sorted(declared):
        with pytest.raises(BundleRejected):
            read_bundle_bytes(_raw(strawman_replay.mutate(valid_bundle, how)))


def _typed(node):
    """A comparable form that keeps TYPE, not just value.

    Written because this test caught itself: `mutate(b, "float_in_payload")`
    sets `cost.input_tokens` to `412000.0`, and in Python `412000.0 == 412000`,
    so the naive `mutated != original` assertion reported the mutation as a
    no-op. It is not a no-op - it is the single most important mutation in the
    list, because canonicalization restriction 4 forbids a float anywhere in a
    hashed payload and a float that compares equal to its integer is exactly how
    one gets in unnoticed. `crucible/canon/canonical.py` uses `type(node) is
    float` rather than `isinstance` for the same reason, one layer down.
    """
    if isinstance(node, dict):
        return ("dict", tuple(sorted((k, _typed(v)) for k, v in node.items())))
    if isinstance(node, list):
        return ("list", tuple(_typed(v) for v in node))
    return (type(node).__name__, node)


def test_every_mutation_name_is_real(valid_bundle):
    """A typo in a mutation name would make `mutate` raise KeyError, which
    pytest.raises(BundleRejected) would report as an error rather than as a
    pass - but only if the name is used. This walks all of them."""
    baseline = _typed(valid_bundle)
    for how, _ in REJECTIONS:
        assert _typed(strawman_replay.mutate(valid_bundle, how)) != baseline, how
    with pytest.raises(KeyError):
        strawman_replay.mutate(valid_bundle, "no_such_mutation")


def test_mutate_does_not_touch_its_input(valid_bundle):
    """Every case above shares one module-scoped fixture. If `mutate` damaged
    it in place, case two would run against the wreckage of case one and the
    parametrization would be measuring the wrong thing."""
    before = copy.deepcopy(valid_bundle)
    strawman_replay.mutate(valid_bundle, "lock_blanked")
    assert valid_bundle == before


# --------------------------------------------------------------------------
# The KNOWN_BAD fixture must fail for the reasons it names, and no others.
# --------------------------------------------------------------------------

KNOWN_BAD = REPO / "contracts" / "golden" / "C6-evidence_bundle.KNOWN_BAD.json"


def test_the_known_bad_fixture_fails_for_exactly_the_reasons_it_declares():
    """The doctrine `contracts/golden/` runs on: each negative fixture names the
    exact rule it violates, and a fixture that fails for an UNDECLARED reason is
    a defect.

    Nothing enforced that until 2026-08-22. `scripts/contract-check.py` asserts
    only that a KNOWN_BAD fails schema validation, so a fixture could acquire a
    sixth failure its list does not mention - which is precisely the ruling-43
    regression the golden-generator test docstring describes: "a lane fixing all
    five listed reasons would still see red with nothing to tell it why."

    Schema errors are matched by field path rather than by code, because C6
    reports them all as E_SCHEMA; the reader's own defect codes are matched
    exactly. A declared reason that CANNOT fire in this fixture is allowed and
    says so in its own text - the coverage-hash case is exercised against the
    valid bundle instead, and naming it here keeps the check visible.
    """
    from crucible.replay import verify_bundle

    body = json.loads(KNOWN_BAD.read_text(encoding="utf-8"))
    declared = set()
    for reason in body["_must_fail_because"]:
        match = re.match(r"\[(?:replay reader, )?(E_[A-Z0-9_]+)\]", reason)
        if match:
            declared.add(match.group(1))

    body.pop("_must_fail_because")
    report = verify_bundle(body)
    assert not report.ok, (
        "the KNOWN_BAD fixture is accepted by the reader. A negative fixture "
        "that passes is the loudest possible signal that the check under it "
        "stopped measuring anything.")

    fired = {d.code for d in report.defects if d.code != "E_SCHEMA"}
    # The reader codes a bracketed reason does not carry are the ones a plain
    # prose reason describes; they are matched by the second assertion below.
    undeclared = fired - declared - PROSE_DECLARED
    assert not undeclared, (
        "the fixture fails for reason(s) its own list does not name: %s. Add "
        "the reason or remove the cause - a lane fixing every listed reason "
        "would still see red with nothing to tell it why."
        % sorted(undeclared))

    assert len(body.get("v0_benign_traces", [])) < BENIGN_DEN, (
        "the benign-traces reason is declared and no longer true of the file")


# Reader codes whose declared reason is written as prose rather than with a
# bracketed code, because the prose predates the code and reads better in the
# fixture. Listed here so the mapping is a declaration rather than a silence.
PROSE_DECLARED = {
    "E_EPISODE_STAMP_MISSING",       # "missing derived_schema_hash"
    "E_FROZEN_CONTEXT_MISSING",      # "missing episode_frozen_context"
    "E_BENIGN_TRACES_SHORT",         # "v0_benign_traces has 23 entries"
    "E_SEP_BY_MISSING",              # "sep_by_split absent"
    "E_POLICY_TEXT_MISSING",         # "policy_chain[0] carries no rules array"
    "E_COVERAGE_MISSING",            # "clause_coverage is absent entirely"
    "E_GENERATED_ATTACK_TEXT_MISSING",  # "attacks[1] ... carries NO instruction"
}
