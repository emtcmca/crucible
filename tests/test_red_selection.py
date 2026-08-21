"""The RED_STRATEGIST: reproducible selection, declared degradation, blindness.

The split under test is SELECTION IS ARITHMETIC, VARIATION IS THE MODEL. A model
choosing which six attacks run would make round composition unreproducible, and
the ASR curve is a sequence of round compositions - so it would make the curve
unreproducible with it.
"""

import json

from crucible.red import AttackSeed, RedStrategist, RoundFeedback

SEEDS = [AttackSeed("atk_%012x" % i, "fam_f%d" % (i % 6), "instruction %d" % i)
         for i in range(48)]


def test_selection_is_reproducible_from_the_seed():
    """A judge re-running the campaign gets the same six attacks in the same
    order. Without that the ASR curve is not reproducible either."""
    a = RedStrategist(seed=7).select(SEEDS, None, 6)
    b = RedStrategist(seed=7).select(SEEDS, None, 6)
    assert [s.attack_id for s in a] == [s.attack_id for s in b]


def test_a_different_seed_gives_a_different_round():
    a = RedStrategist(seed=1).select(SEEDS, None, 6)
    b = RedStrategist(seed=2).select(SEEDS, None, 6)
    assert [s.attack_id for s in a] != [s.attack_id for s in b]


def test_families_are_cycled_not_sampled():
    """Six attacks over six families must be one each. Uniform sampling at n=6
    would routinely land five of one family and none of another, and the
    per-family verb report the exit criteria require would be noise."""
    chosen = RedStrategist(seed=3).select(SEEDS, None, 6)
    assert len({s.family_id for s in chosen}) == 6


def test_it_does_not_run_out_when_a_family_is_exhausted():
    thin = [AttackSeed("atk_a", "fam_f0", "x"), AttackSeed("atk_b", "fam_f1", "y")]
    assert len(RedStrategist(seed=0).select(thin, None, 6)) == 2


# --------------------------------------------------------------------------

class Stub:
    def __init__(self, text):
        self.text, self.seen = text, []

    def __call__(self, *, system, user, model, thinking_level):
        self.seen.append({"system": system, "user": user, "model": model,
                          "thinking_level": thinking_level})
        return {"text": self.text, "usd": 0.0002, "tokens": 400}


def test_variation_uses_the_pinned_model_and_an_explicit_thinking_level():
    stub = Stub(json.dumps({"instruction": "rewritten"}))
    out = RedStrategist(stub, seed=0).vary(SEEDS[0], None)
    assert out["instruction"] == "rewritten"
    assert out["variation"] == "model"
    assert stub.seen[0]["model"] == "gemini-3.6-flash"
    assert stub.seen[0]["thinking_level"] == "low"


def test_no_model_replays_the_seed_AND_SAYS_SO():
    """Degradation is declared, not silent. Replaying seeds verbatim is a usable
    offline mode and a bad measurement, and the flag is what keeps those two
    facts from being confused in the evidence bundle."""
    out = RedStrategist(None, seed=0).vary(SEEDS[0], None)
    assert out["instruction"] == SEEDS[0].instruction
    assert out["variation"] == "none"


def test_an_unparseable_response_falls_back_and_is_labelled_fallback():
    out = RedStrategist(Stub("sorry, I can't help with that"), seed=0) \
        .vary(SEEDS[0], None)
    assert out["instruction"] == SEEDS[0].instruction
    assert out["variation"] == "fallback", (
        "silently replaying the seed under the label `model` would put a false "
        "claim about the round into the evidence bundle")


def test_the_prompt_carries_counts_and_never_the_policy_or_a_fixture():
    """What an attacker learns by attacking is WHICH OF MY ATTEMPTS WORKED. Not
    which rule stopped me, not what the policy says, not which benign fixture is
    fragile."""
    stub = Stub(json.dumps({"instruction": "z"}))
    fb = RoundFeedback(round_index=2,
                       attempted_by_family={"fam_f0": 3},
                       breached_by_family={"fam_f0": 1})
    RedStrategist(stub, seed=0).vary(SEEDS[0], fb)
    user = stub.seen[0]["user"]
    assert "3" in user and "1" in user
    for forbidden in ("cap:", "=> deny", "require_approval", "rule r_",
                      "fixture", "policy@v", "preceded_by"):
        assert forbidden not in user, "%r reached the RED_STRATEGIST" % forbidden


def test_propose_round_returns_one_entry_per_selected_attack():
    stub = Stub(json.dumps({"instruction": "z"}))
    out = RedStrategist(stub, seed=5).propose_round(SEEDS, None, 6)
    assert len(out) == 6
    assert {k for row in out for k in row} >= {"attack_id", "family_id",
                                               "instruction", "variation"}
