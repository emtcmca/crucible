"""The ARMORER's patch path: the placeholder id, the one repair, and the halt.

Every model here is a stub returning fixed text. The question is what the ARMORER
does with an answer, not what the model answers - the live measurement of that is
`crucible/armorer/experiment.py`, and it is reported in `docs/lanes/L5-log.md`
with an N and a cost beside it.
"""

import json
import os

import pytest

from crucible.armorer.armorer import (
    HALT_ARMORER_EXHAUSTED,
    Armorer,
    strip_fences,
    was_fenced,
)
from crucible.armorer.experiment import SCENARIOS, build_seed_policy
from crucible.armorer.render import render_policy, render_rule
from crucible.dsl import parse_policy, parse_rule
from crucible.dsl.serialize import compile_rule
from crucible.dsl.validator import Validator, harvest_product_lexicon
from crucible.governor import Budget, BudgetGovernor

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(REPO, "contracts", "golden")


def load(name):
    with open(os.path.join(GOLDEN, name), encoding="utf-8") as fh:
        return json.load(fh)


MANIFEST_A = load("C3a-capability_manifest.valid.json")
DERIVED_B = load("C3b-derived_schema.valid.json")


def validator():
    return Validator(MANIFEST_A, DERIVED_B,
                     product_lexicon=harvest_product_lexicon(MANIFEST_A))


class Stub:
    """Returns each canned answer in turn and records what it was asked."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.seen = []

    def __call__(self, *, system, user, model, thinking_level):
        self.seen.append({"system": system, "user": user, "model": model,
                          "thinking_level": thinking_level})
        text = self.answers[min(len(self.seen) - 1, len(self.answers) - 1)]
        return {"text": text, "usd": 0.0146, "tokens": 5000}


GOOD = ("rule r_new1: cap:CAP_MOVES_MONEY when preceded_by(CAP_INVOKES_AGENT) "
        "=> require_approval(DELEGATION_UNBOUND) origin armorer:1")
FORGED = ("rule r_a1b2c3d4e5f6: cap:CAP_MOVES_MONEY => deny origin armorer:1")
GIBBERISH = "here is your patch:\nplease deny the money tool"


def armorer(stub, governor=None):
    return Armorer(validator(), MANIFEST_A, DERIVED_B, stub, governor=governor)


def seed():
    return build_seed_policy(validator())


# --------------------------------------------------------------------------

def test_a_valid_patch_is_accepted_and_the_id_is_computed_by_code():
    stub = Stub(GOOD)
    result = armorer(stub).propose(SCENARIOS["s01"], seed(), 1)
    assert result.ok
    assert result.verbs_used == ["require_approval"]
    assert len(result.new_rule_ids) == 1
    rid = result.new_rule_ids[0]
    assert rid.startswith("r_") and len(rid) == 14
    assert "r_new1" not in json.dumps(result.hashed_payload), (
        "the placeholder must be gone: the validator canonicalizes the body, "
        "hashes it and REWRITES the id. The model never sees a hash.")
    assert not result.repaired


def test_a_hash_shaped_id_on_an_add_is_rejected():
    """CONVENTIONS 2.6 / V9. Not because the id would be wrong - it certainly
    would be - but because a model that produced a plausible one has demonstrated
    it is GUESSING AT A DETERMINISTIC COMPUTATION, and the next guess lands
    somewhere nobody can see."""
    stub = Stub(FORGED, FORGED)
    result = armorer(stub).propose(SCENARIOS["s01"], seed(), 1)
    assert not result.ok
    assert result.halt == HALT_ARMORER_EXHAUSTED
    assert result.attempts[0].parsed is True, (
        "it PARSES - the grammar admits a real id - and is refused by the "
        "VALIDATOR. That ordering is the check working, not a near miss.")
    assert result.attempts[0].error_code


def test_one_repair_is_offered_and_exactly_one():
    stub = Stub(GIBBERISH, GOOD)
    result = armorer(stub).propose(SCENARIOS["s01"], seed(), 1)
    assert result.ok
    assert result.repaired
    assert len(result.attempts) == 2
    assert [a.kind for a in result.attempts] == ["initial", "repair"]


def test_two_failures_halt_rather_than_looping():
    stub = Stub(GIBBERISH, GIBBERISH, GOOD)
    result = armorer(stub).propose(SCENARIOS["s01"], seed(), 1)
    assert not result.ok
    assert result.halt == HALT_ARMORER_EXHAUSTED
    assert len(stub.seen) == 2, (
        "a third call is the loop tuning its way past a stop condition")


def test_the_repair_carries_the_validator_error_and_nothing_else():
    """The temptation at 11pm is to add "and two benign fixtures failed", which
    would hand the ARMORER the signal it is blind to by design.

    THE SCORE STRING IS DERIVED. This list held the literal `"24/24"` until
    2026-08-22 - a day after ruling 43 moved the floor to 26, so the leak
    detector was watching for a string the loop had stopped producing. A
    detector pinned to a dead value is a check that cannot fail: the same defect
    it exists to prevent, aimed at itself.
    """
    from corpus.model import BENIGN_TOTAL

    stub = Stub(GIBBERISH, GOOD)
    armorer(stub).propose(SCENARIOS["s01"], seed(), 1)
    repair = stub.seen[1]["user"]
    tail = repair.split("That patch was rejected by the validator.")[-1]
    assert "E_" in tail
    for forbidden in ("fixture", "benign",
                      "%d/%d" % (BENIGN_TOTAL, BENIGN_TOTAL),
                      "fx_", "near-miss", "passed", "rolled back"):
        assert forbidden not in tail.lower(), (
            "%r reached the repair message" % forbidden)


def test_rejection_feedback_is_a_separate_channel_and_is_counts_and_classes():
    from crucible.conductor.conductor import RejectionFeedback
    stub = Stub(GOOD)
    armorer(stub).propose(
        SCENARIOS["s01"], seed(), 2,
        rejection_feedback=RejectionFeedback(2, ("CAP_MOVES_MONEY",)))
    user = stub.seen[0]["user"]
    assert "benign_failures: 2" in user
    assert "CAP_MOVES_MONEY" in user
    assert "fx_" not in user
    tail = user.split("=== FEEDBACK FROM THE PREVIOUS ROUND ===")[1]
    assert "fixture" not in tail.lower()


def test_the_model_id_and_thinking_level_are_set_on_every_call():
    """CONVENTIONS 3.1 and 3.3. An unset thinking_level is not a free default -
    thinking tokens bill at the ordinary OUTPUT rate and ran 48x output tokens in
    the day-1 spike."""
    stub = Stub(GIBBERISH, GOOD)
    armorer(stub).propose(SCENARIOS["s01"], seed(), 1)
    for call in stub.seen:
        assert call["model"] == "gemini-3.7-flash"
        assert call["thinking_level"] == "medium"


def test_the_governor_can_refuse_before_the_call_and_it_is_a_result():
    stub = Stub(GOOD)
    gov = BudgetGovernor(Budget(usd_cap=0.0001, token_cap=10 ** 9, round_cap=6,
                                call_cap=10))
    result = armorer(stub, governor=gov).propose(SCENARIOS["s01"], seed(), 1)
    assert not result.ok
    assert result.halt == "BUDGET_EXHAUSTED"
    assert stub.seen == [], "nothing was called and nothing was spent"


def test_the_governor_is_charged_the_actual_cost():
    stub = Stub(GOOD)
    gov = BudgetGovernor(Budget(usd_cap=10.0, token_cap=10 ** 9, round_cap=6,
                                call_cap=10))
    armorer(stub, governor=gov).propose(SCENARIOS["s01"], seed(), 1)
    assert gov.spent_usd == pytest.approx(0.0146)
    assert gov.tokens_used == 5000
    assert gov.calls_made == 1


# --------------------------------------------------------------------------
# Fences
# --------------------------------------------------------------------------

def test_a_fenced_patch_is_stripped_and_the_strip_is_visible():
    """A fenced patch is a FRAMING failure, not a GRAMMAR failure, and the day-1
    decision rule distinguishes them because they have opposite remedies.
    Absorbing a fence silently would move instances from one bucket to the other
    and change which remedy the numbers argue for."""
    fenced = "```dsl\n%s\n```" % GOOD
    assert was_fenced(fenced)
    assert strip_fences(fenced) == GOOD
    result = armorer(Stub(fenced)).propose(SCENARIOS["s01"], seed(), 1)
    assert result.ok


def test_an_unfenced_patch_is_untouched():
    assert strip_fences(GOOD) == GOOD
    assert not was_fenced(GOOD)


# --------------------------------------------------------------------------
# The renderer is a mirror of the parser, so it is checked by round trip
# --------------------------------------------------------------------------

ROUND_TRIP = [
    "rule r_new1: cap:CAP_MOVES_MONEY => deny origin armorer:1",
    "rule r_new1: cap:CAP_MOVES_MONEY when amount_minor >= 50000 "
    "=> require_approval(FLOOR) origin seed",
    "rule r_new1: cap:CAP_MOVES_MONEY "
    "=> constrain_arg(amount_minor <= 50000) origin armorer:2",
    "rule r_new1: cap:CAP_READS_PII when derived.subject_verified_in_episode "
    "== false => deny origin armorer:1",
    "rule r_new1: cap:CAP_MOVES_MONEY when preceded_by(CAP_INVOKES_AGENT) "
    "=> deny origin armorer:3",
    "rule r_new1: cap:CAP_MOVES_MONEY when "
    "episode_sum(amount_minor) >= 50000 => deny origin armorer:1",
    "rule r_new1: cap:CAP_EXTERNAL_COMMS when to == episode.account_holder_email "
    "=> deny origin armorer:1",
    "rule r_new1: cap:CAP_MOVES_MONEY when reason_code in "
    "[CHANGED_MIND, SIZE_FIT] => deny origin armorer:1",
    "rule r_new1: cap:CAP_MOVES_MONEY when beneficiary_id is absent "
    "=> deny origin armorer:1",
    "rule r_new1: cap:CAP_MOVES_MONEY, tool:t_9f2c1b77 "
    "=> deny origin armorer:1",
    "rule r_new1: cap:CAP_MOVES_MONEY when derived.approval_tier == T2 "
    "and amount_minor >= 10000 => deny origin armorer:1",
]


@pytest.mark.parametrize("text", ROUND_TRIP)
def test_render_parse_round_trip_lands_on_the_same_rule_id(text):
    """The renderer and the parser are two implementations of one mapping and
    they will drift. The CONTENT HASH is the instrument that catches it, because
    a renderer that emits something the parser reads DIFFERENTLY produces a
    different id - which inspection would not reveal."""
    original = compile_rule(parse_rule(text))
    rendered = render_rule(original, origin="armorer:1")
    again = compile_rule(parse_rule(rendered))
    assert again["rule_id"] == original["rule_id"], (
        "%r rendered to %r, which the parser reads as a DIFFERENT RULE"
        % (text, rendered))


def test_the_whole_seed_policy_round_trips():
    policy = seed()
    text = render_policy(policy)
    reparsed = parse_policy("\n".join(l for l in text.splitlines()
                                      if not l.startswith("#")))
    got = sorted(compile_rule(r)["rule_id"] for r in reparsed.rules)
    want = sorted(r["rule_id"] for r in policy["hashed_payload"]["rules"])
    assert got == want


def test_a_retraction_cites_an_id_the_model_can_copy_off_the_rendered_policy():
    """CONVENTIONS 2.6: copying an identifier is a different task from computing
    one. That only holds if the id is VISIBLE IN THE TEXT the model was handed."""
    policy = seed()
    text = render_policy(policy)
    for rule in policy["hashed_payload"]["rules"]:
        assert rule["rule_id"] in text
