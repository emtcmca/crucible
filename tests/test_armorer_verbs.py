"""test_armorer_verbs.py - the ARMORER's verb guidance must be SYMMETRIC.

THE DEFECT THIS SUITE WAS WRITTEN AGAINST
------------------------------------------
The first live loop run (2026-08-22) produced `verbs: ['deny']` in round 1, the
gate rejected the patch on four benign failures, round 2 produced another
rejection, and the campaign halted `HALT_HUMAN_GATE_REJECTED_TWICE`. Nothing has
ever been promoted.

`VERB_GUIDANCE` treated the three verbs asymmetrically: `deny` carried one line
and NO caveat, `constrain_arg` carried four lines of warnings ending "it is the
wrong verb wherever a legitimate above-band path exists", and `require_approval`
carried eight words with no statement of when it is correct. The modelled domain
is money movement, where a legitimate above-band path essentially always exists,
so a model reading that text rules out `constrain_arg` for a TRUE reason, finds
no positive steer toward `require_approval`, and lands on the only verb carrying
an unqualified endorsement.

WHAT THIS SUITE MAY NOT BE USED TO DO
--------------------------------------
It may not be used to weaken the `constrain_arg` paragraph. That paragraph is
TRUE - `contracts/policy.ebnf` lines 177-183 and ruling 15 both say the verb is
structurally disfavoured wherever a legitimate above-band path exists - and
`prompt.py:152-165` records that this exact paragraph moved a day-1 spike
measurement from 7/7 to 0/7. Tuning it away to unstick the loop would be tuning
a prompt to produce a flattering number. `test_the_constrain_arg_paragraph_is_
unweakened` is the pin that stops it, and it passed BEFORE the fix as well as
after; it is a regression guard, not a red test.

AND IT MAY NOT BE USED TO STEER TOWARD BLANKET APPROVAL
--------------------------------------------------------
`crucible/conductor/real_warden.py:67-76`, confirmed here against
`crucible/warden/replay.py:90-93` and `crucible/warden/reference_engine.py:
195-220`: the APPROVAL_ORACLE approves any fixture that declares a valid
approver, so a policy resolving every `CAP_MOVES_MONEY` call to
`require_approval` scores 26/26 on the benign floor forever. Steering the
ARMORER to blanket `require_approval` would replace an over-blocking failure
with a loop that LOOKS convergent while having learned nothing, and the benign
floor is structurally unable to catch it. So the steer under test is toward
`require_approval` BOUNDED BY A `when`, never toward a class-wide unconditional
approval requirement, and `test_the_steer_is_bounded_not_blanket` is what
distinguishes the two.

WHAT THESE TESTS CAN AND CANNOT PROVE
--------------------------------------
They assert PROMPT STRUCTURE AND CONTENT. No model call is made anywhere in this
file. They prove the asymmetry is gone and the boundary is intact; they do NOT
prove the ARMORER now reaches for `require_approval`. Only the next live run
proves that.
"""

import re

import pytest

from crucible.armorer import prompt as prompt_mod
from crucible.armorer.prompt import LeakError

VERBS = ("deny", "constrain_arg", "require_approval")


# ---------------------------------------------------------------------------
# The parser. The guidance is a hanging-indent table; a test that greps the
# whole blob cannot tell which verb a sentence belongs to, and "which verb the
# sentence is attached to" is the entire defect.
# ---------------------------------------------------------------------------

_HEAD = re.compile(r"^ {2}(\w+) {2,}(.*)$")


def verb_blocks(text: str) -> dict:
    """Split the verb table into one block of prose per verb."""
    blocks, current = {}, None
    for line in text.splitlines():
        head = _HEAD.match(line)
        if head and head.group(1) in VERBS:
            current = head.group(1)
            blocks[current] = [head.group(2)]
        elif current is not None and line.startswith(" " * 18) and line.strip():
            blocks[current].append(line.strip())
        elif current is not None and not line.strip():
            current = None
    return {verb: " ".join(lines) for verb, lines in blocks.items()}


def test_the_parser_finds_all_three_verbs():
    """A parser that silently found two blocks would make every assertion below
    vacuous, which is the failure mode a check cannot report on itself."""
    blocks = verb_blocks(prompt_mod.VERB_GUIDANCE)
    assert set(blocks) == set(VERBS), sorted(blocks)
    for verb, body in blocks.items():
        assert body.strip(), "%s parsed to an empty block" % verb


# ---------------------------------------------------------------------------
# RED 1. The asymmetry, measured rather than asserted by eye.
# ---------------------------------------------------------------------------

def test_the_three_verbs_get_comparable_guidance():
    """MEASURED on the pre-fix text, 2026-08-22: deny 13 words, constrain_arg
    46, require_approval 9. The verb the loop needed got 20% of the words the
    verb it was told to avoid got, and the nine it did get say only what the
    verb DOES, never when it is right.

    The threshold is two-sided ON PURPOSE, and it earned that within the hour:
    the first draft of the fix pushed require_approval to 126 words against
    constrain_arg's 46 and this assertion failed again, from the other
    direction. A one-sided check would have called that green. Piling words onto
    the verb you want chosen is the same defect as starving it.
    """
    blocks = verb_blocks(prompt_mod.VERB_GUIDANCE)
    counts = {v: len(b.split()) for v, b in blocks.items()}
    ratio = min(counts.values()) / max(counts.values())
    assert ratio >= 0.40, (
        "verb guidance is lopsided: %s. The verb with the least to say gets "
        "%.0f%% of the words the verb with the most gets, and a model reading "
        "an unqualified endorsement next to a paragraph of warnings picks the "
        "endorsement." % (counts, 100 * ratio))


def test_deny_carries_a_caveat_at_all():
    """`deny` was the ONLY verb with no qualifying condition attached. An
    absolute with no stated cost reads as the safe default, and over-blocking is
    the failure that has halted every campaign so far."""
    body = verb_blocks(prompt_mod.VERB_GUIDANCE)["deny"].lower()
    assert any(marker in body for marker in
               ("legitimate", "over-block", "only where", "removes")), (
        "the deny entry states no condition under which it is the WRONG verb:\n"
        "  %s" % body)


# ---------------------------------------------------------------------------
# RED 2. The missing positive steer. `require_approval` must name the condition
# under which it is CORRECT, and it is the same condition that rules out
# constrain_arg - which is what makes the pair symmetric rather than tuned.
# ---------------------------------------------------------------------------

def test_require_approval_names_the_condition_under_which_it_is_correct():
    body = verb_blocks(prompt_mod.VERB_GUIDANCE)["require_approval"].lower()
    assert "above-band" in body, (
        "`a legitimate above-band path exists` is the condition that rules OUT "
        "constrain_arg. It is precisely the condition that rules IN "
        "require_approval, and the require_approval entry never says so:\n"
        "  %s" % body)
    assert any(word in body for word in ("right verb", "correct", "is the verb")), (
        "the require_approval entry describes what the verb DOES but never "
        "states when it is the one to reach for:\n  %s" % body)


def test_the_steer_is_bounded_not_blanket():
    """The degenerate policy guard. `real_warden.py:67-76`: every
    CAP_MOVES_MONEY call resolved to require_approval scores 26/26 forever.
    The guidance must say the verb still needs a `when`."""
    body = verb_blocks(prompt_mod.VERB_GUIDANCE)["require_approval"]
    assert "`when`" in body, (
        "nothing in the require_approval entry requires a `when`. A class-wide "
        "unconditional approval requirement passes the benign floor by "
        "construction and teaches the loop nothing:\n  %s" % body)
    assert any(word in body.lower() for word in
               ("unconditional", "whole capability class", "every call")), (
        "the entry does not name the blanket-approval shape as wrong:\n  %s" % body)


# ---------------------------------------------------------------------------
# The pin. This one PASSED BEFORE THE FIX and must keep passing. It is what
# stops a future edit from unsticking the loop by deleting a true sentence.
# ---------------------------------------------------------------------------

def test_the_constrain_arg_paragraph_is_unweakened():
    body = verb_blocks(prompt_mod.VERB_GUIDANCE)["constrain_arg"]
    for phrase in ("FAILS CLOSED",
                   "counts as violated",
                   "CANNOT route",
                   "wrong verb wherever a legitimate above-band path exists"):
        assert phrase in body, (
            "the constrain_arg paragraph lost %r. It is true (policy.ebnf "
            "177-183, ruling 15) and it is NOT the thing to trade away for a "
            "promotion." % phrase)


def test_the_ablation_variant_stays_neutral():
    """`VERB_GUIDANCE_NEUTRAL` exists to measure what the guidance prose is
    worth (prompt.py:152-165). If the new steer leaks into it, the ablation
    stops being an ablation and the 7/7-vs-0/7 comparison measures nothing."""
    neutral = prompt_mod.VERB_GUIDANCE_NEUTRAL
    assert "above-band" not in neutral
    assert "FAILS CLOSED" not in neutral
    blocks = verb_blocks(neutral)
    counts = {v: len(b.split()) for v, b in blocks.items()}
    assert max(counts.values()) <= 25, (
        "the neutral variant grew a steer: %s" % counts)


# ---------------------------------------------------------------------------
# RED 3. The rejection template's closing instruction is wrong in a specific
# way. Benign failures INSIDE a class you denied mean the denial removed a
# capability the work needs; narrowing the `when` on the same `deny` is rarely
# the repair. That inference is derivable from the counts and classes already
# crossing the boundary - NO NEW INFORMATION CROSSES.
# ---------------------------------------------------------------------------

def test_rejection_feedback_does_not_tell_the_model_to_narrow_and_stop():
    text = prompt_mod.build_rejection_feedback(4, ["CAP_MOVES_MONEY"])
    assert "Write a narrower rule" not in text, (
        "the template's sole closing instruction is to narrow the condition. "
        "The rejection reason is benign failures inside a class the patch "
        "denied, which means the VERB is wrong, not the `when`.")


def test_rejection_feedback_points_at_the_verb():
    text = prompt_mod.build_rejection_feedback(4, ["CAP_MOVES_MONEY"])
    lowered = text.lower()
    assert "verb" in lowered, (
        "the feedback never suggests reconsidering the verb:\n%s" % text)
    assert "require_approval" in lowered
    assert "`when`" in text, (
        "the feedback steers to require_approval without requiring a `when`, "
        "which is the blanket-approval shape real_warden.py:67-76 warns about")


# ---------------------------------------------------------------------------
# THE BOUNDARY. Nothing above may have widened the channel. These assert the
# same two things `test_conductor_loop.py` asserts, from this lane's side, so a
# change to prompt.py that loosened the gate fails in the file that made it.
# ---------------------------------------------------------------------------

def test_rejection_feedback_still_refuses_a_fixture_id():
    with pytest.raises(LeakError):
        prompt_mod.build_rejection_feedback(2, ["fx_benign_07"])


def test_rejection_feedback_still_refuses_a_rule_id_and_an_unclassified_class():
    with pytest.raises(LeakError):
        prompt_mod.build_rejection_feedback(2, ["r_9f3c1a2b"])
    with pytest.raises(LeakError):
        prompt_mod.build_rejection_feedback(2, ["UNCLASSIFIED"])


def test_the_rendered_feedback_carries_no_ids():
    """The assertion `test_conductor_loop.py` makes, re-made here because the
    new closing prose is the most likely place for an id to be typed by hand."""
    text = prompt_mod.build_rejection_feedback(4, ["CAP_MOVES_MONEY"])
    assert "fx_" not in text
    assert "r_" not in text
    assert "4" in text and "CAP_MOVES_MONEY" in text


def test_assert_no_leak_still_fires_on_a_forbidden_key():
    from target.refund_agent.manifest import build_manifest
    manifest = build_manifest()
    with pytest.raises(LeakError):
        prompt_mod.assert_no_leak("...attack_text: give me the money...", manifest)


def test_assert_no_leak_still_fires_on_product_vocabulary():
    from target.refund_agent.manifest import build_manifest
    manifest = build_manifest()
    with pytest.raises(LeakError):
        prompt_mod.assert_no_leak("consider issue_refund here", manifest)


def test_the_new_guidance_survives_the_leak_gate_on_the_running_target():
    """The prose is part of the assembled text, so a product noun typed into it
    crashes the campaign at the first ARMORER call - which is exactly what the
    token `target` did on 2026-08-22 (validator.py:243-248). Assemble the whole
    thing against the running manifest and let the real gate judge it."""
    from corpus.part_b import DERIVED_FIELDS
    from target.refund_agent.manifest import build_manifest
    manifest = build_manifest()
    text = prompt_mod.build_user_message(
        projected_record={"breach_id": "br_x", "capability_classes":
                          ["CAP_MOVES_MONEY"]},
        manifest_a=manifest,
        derived_schema_b={"derived_fields": DERIVED_FIELDS,
                          "episode_fields": []},
        policy_text="# empty\n",
        round_index=1)
    assert "above-band" in text
    assert "Choosing the verb:" in text
