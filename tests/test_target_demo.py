"""The three demo conversations, replayed against the fake ledger.

THESE ARE SCRIPTED TRANSCRIPTS, NOT CAPTURED ONES. No model call is made here and
none is made anywhere in scope (a). Each file is the rehearsal script for a demo
beat: the turns, the exact tool calls with their exact arguments, and the LEDGER
POSTCONDITION the beat asserts on camera. The live capture against the real model
is a separate, later step and it has not been done.

WHY THEY ARE EXECUTED RATHER THAN JUST WRITTEN. A demo script that has never been
run is a paragraph of intentions. Running the scripted calls against a seeded
ledger proves the tool signatures accept exactly these arguments, that the amounts
and ids are internally consistent, and that the postcondition the demo claims is
the postcondition the ledger actually reaches.

This suite passed on its first run, which is a weak signal and is recorded as one.
It was therefore falsified by hand before being trusted - a postcondition and an
argument were each mutated and the suite was watched going red. That transcript is
in `docs/lanes/L2-log.md`. A green suite that has never been seen red is a suite
nobody has established can fail.

WHAT IT DOES NOT PROVE, and this is the honest limit: that the MODEL will choose
these calls. That is what the live capture is for, and until it runs, these files
are a specification of the beat and not evidence about the agent.
"""

import json
import pathlib

import pytest

from target.refund_agent import tools
from target.refund_agent.fake_ledger import FakeLedger, seed_demo_ledger

DEMO_DIR = pathlib.Path(__file__).resolve().parent.parent / "target" / "refund_agent" / "demo"
DEMOS = sorted(DEMO_DIR.glob("*.json"))


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture
def ledger():
    lg = seed_demo_ledger(FakeLedger())
    tools.bind_backends(lg)
    yield lg
    tools.unbind_backends()


def test_there_are_exactly_three_demo_conversations():
    """`lanes-spec.md` scope (a) names three. Counted from disk, not from the doc."""
    assert len(DEMOS) == 3, [p.name for p in DEMOS]


@pytest.mark.parametrize("path", DEMOS, ids=lambda p: p.stem)
def test_demo_declares_what_it_is_and_what_it_expects(path):
    d = _load(path)
    for key in ("demo_id", "title", "beat", "why_this_one", "episode_id",
                "expected_outcome", "breach_expectation", "turns", "postconditions"):
        assert key in d, "%s is missing %s" % (path.name, key)
    assert d["episode_id"].startswith("ep_") and len(d["episode_id"]) == 15


@pytest.mark.parametrize("path", DEMOS, ids=lambda p: p.stem)
def test_demo_replays_to_its_declared_postconditions(path, ledger):
    """THE ASSERTION THAT MATTERS. Replay every scripted tool call in order and
    check the LEDGER, not the return values."""
    d = _load(path)
    for turn in d["turns"]:
        if turn["speaker"] != "tool_call":
            continue
        fn = getattr(tools, turn["tool"])
        result = fn(**turn["args"])
        assert result["status"] == turn["expect_status"], (
            "%s: %s returned %r" % (path.name, turn["tool"], result))

    post = d["postconditions"]
    assert len(ledger.refunds) == post["refund_count"]
    assert sum(r.amount_minor for r in ledger.refunds) == post["refund_total_minor"]
    assert len(ledger.store_credits) == post["store_credit_count"]
    assert len(ledger.escalations) == post["escalation_count"]
    assert len(ledger.outbox()) == post["outbox_count"]

    order = ledger.get_order(d["scenario_order_id"])
    assert order.refunded_minor == post["order_refunded_minor"]
    assert order.status == post["order_status"]

    if "escalation_queue" in post:
        esc = ledger.escalations[0]
        assert esc.detail["queue"] == post["escalation_queue"]
        assert esc.detail["state"] == post["escalation_state"]
    if "refund_reason_code" in post:
        assert ledger.refunds[0].detail["reason_code"] == post["refund_reason_code"]


@pytest.mark.parametrize("path", DEMOS, ids=lambda p: p.stem)
def test_every_scripted_tool_call_names_a_real_tool(path):
    names = {f.__name__ for f in tools.TOOL_FUNCTIONS}
    for turn in _load(path)["turns"]:
        if turn["speaker"] == "tool_call":
            assert turn["tool"] in names, "%s: no such tool %s" % (path.name, turn["tool"])


@pytest.mark.parametrize("path", DEMOS, ids=lambda p: p.stem)
def test_money_is_minor_units_with_an_explicit_currency(path):
    """CONVENTIONS section 6. `amount_cents` is not used anywhere in this build; the
    two sites in `execution-spec.md`'s demo script that still carry it are reported
    in `docs/lanes/L2-log.md` rather than copied."""
    for turn in _load(path)["turns"]:
        if turn["speaker"] != "tool_call":
            continue
        args = turn["args"]
        assert "amount" not in args and "amount_cents" not in args
        for money_arg in ("amount_minor", "recommended_amount_minor"):
            if money_arg in args:
                assert isinstance(args[money_arg], int)
                assert args["currency"] == "USD"


@pytest.mark.parametrize("path", DEMOS, ids=lambda p: p.stem)
def test_every_outbound_email_goes_to_the_order_email_of_record(path, ledger):
    """A demo that mailed an address supplied in the conversation would be
    demonstrating the F4 destination attack while calling it the happy path."""
    d = _load(path)
    order = ledger.get_order(d["scenario_order_id"])
    for turn in d["turns"]:
        if turn["speaker"] == "tool_call" and turn["tool"] == "email_customer":
            assert turn["args"]["to"] == order.account_holder_email
            assert isinstance(turn["args"]["to"], str), "`to` is scalar, never a list"


def test_D3_declares_itself_an_explicit_non_breach():
    """Ruling 6, made mechanical. If this demo's expectation ever flips to a
    breach, the Objective Set has started manufacturing false positives on the one
    behaviour the research says is structurally unstoppable."""
    d = _load(DEMO_DIR / "D3-reframe-as-defective.json")
    assert d["breach_expectation"].startswith("EXPLICIT NON-BREACH")
    refunds = [t for t in d["turns"]
               if t["speaker"] == "tool_call" and t["tool"] == "issue_refund"]
    assert len(refunds) == 1
    assert refunds[0]["args"]["reason_code"] == "DEFECTIVE"


def test_D2_moves_no_money_at_all():
    """The escalation beat is worthless if money moves anyway. Asserted on the
    script as well as on the ledger, so a later edit to the script cannot quietly
    turn the beat into a refund."""
    d = _load(DEMO_DIR / "D2-escalation.json")
    money_tools = {"issue_refund", "issue_store_credit"}
    assert not [t for t in d["turns"]
                if t["speaker"] == "tool_call" and t["tool"] in money_tools]
    assert d["postconditions"]["refund_total_minor"] == 0
