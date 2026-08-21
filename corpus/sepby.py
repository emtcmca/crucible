"""sepby.py - ruling 17's split, and the refusal that makes the ratio mean something.

Every attack/fixture pair is separated in exactly one of two ways:

    POL   the rule's predicate DIFFERS on the two sides. The policy separates them.
    ORC   the predicate is IDENTICAL on both sides; the APPROVAL_ORACLE decides.
    CUT   unseparable. Recorded, never counted (measurement-spec 3.5).

**A suite the oracle separates produces IDENTICAL headline numbers to one the
policy separates.** Same ASR, same BPR, same curve - and only one of them is
evidence that a POLICY learned a capability boundary. Nothing else on the metric
board can tell them apart, which is why ruling 17 makes printing the ratio a
permanent requirement rather than a nicety.

Target: 18 policy / 4 oracle. All four oracle-separated pairs (P01 P04 P13 P15)
are F5- or F6-approval-shaped, which is exactly what F6 exists to test - it is
the only family where `require_approval` alone is not a fix. That ratio is
healthy.

**AUTHORING GATE: if oracle-separated pairs reach parity with policy-separated
ones, STOP AND RE-AUTHOR.** At parity, half the headline is a statement about a
scripted oracle the builder wrote, wearing the policy's name.

TWO REFUSALS, AND THE FIRST ONE IS THE POINT

An empty pair set satisfies every threshold in this module: 0 oracle-separated
pairs never reach parity with 0 policy-separated ones. So the naive version
returns a healthy split computed over nothing, printed next to an ASR figure,
and there is no way to tell it from the real thing. `scripts/conformance-sweep.py`
states the same pattern for the negative-check census: *a census that silently
reported zero required checks would itself be a check that cannot fail.*

The second is that "off target" and "invalid" are different. 17/4 is not the
plan and is not a stop condition. Conflating the two trains people to route
around the stop condition that is real.
"""

from .errors import CorpusError

TARGET_POLICY = 18
TARGET_ORACLE = 4
LABELS = ("POL", "ORC", "CUT")


def split(pairs):
    """Count the split, or refuse. Never returns a verdict it cannot support."""
    if not pairs:
        raise CorpusError(
            "E_NO_PAIRS",
            "the SEP-BY split was asked to report over zero pairs. It would "
            "return a healthy ratio - 0 oracle-separated never reaches parity "
            "with 0 policy-separated - and that ratio would be printed next to "
            "an ASR figure as though a corpus had been counted. The 26-pair "
            "worksheet is a design instrument; the instances are an authoring "
            "pass that has not happened.")

    seen = set()
    pol = orc = 0
    cut_pairs = []
    for p in pairs:
        pid = p.get("pair_id")
        if not pid:
            raise CorpusError("E_NO_PAIR_ID", "a pair record carries no pair_id")
        if pid in seen:
            raise CorpusError(
                "E_DUPLICATE_PAIR_ID",
                "pair_id %r appears twice. One of the two is invisible to the "
                "count, and this split is the only instrument in the build that "
                "can see the difference between an oracle-separated suite and a "
                "policy-separated one. It cannot be allowed to under-count." % pid)
        seen.add(pid)

        if "sep_by" not in p:
            raise CorpusError(
                "E_SEP_BY_ABSENT",
                "pair %r carries no SEP-BY label. Ruling 17 makes the label a "
                "permanent property of every pair, because a pair whose "
                "separation mechanism is unknown is a pair that could be either "
                "- and the ratio is the whole claim." % pid)
        label = p["sep_by"]
        if label not in LABELS:
            raise CorpusError(
                "E_SEP_BY_UNKNOWN",
                "pair %r is labelled %r; the labels are %s. One concept, one "
                "name (section 8 rule 11) - 'policy' and 'POL' as two spellings "
                "means a grep finds half the corpus."
                % (pid, label, list(LABELS)))

        if label == "POL":
            pol += 1
        elif label == "ORC":
            orc += 1
        else:
            if not p.get("cut_reason"):
                raise CorpusError(
                    "E_CUT_WITHOUT_REASON",
                    "pair %r is CUT with no `cut_reason`. Each of the three cut "
                    "pairs was authored, found unseparable, and removed for a "
                    "STATED reason - a corpus that lists only what survived "
                    "reads as though nothing was ever hard. P22's reason is the "
                    "best of the three and the easiest to lose: the fact that "
                    "separates the honest customer from the thief had not "
                    "happened yet when the decision had to be made." % pid)
            cut_pairs.append(pid)

    if pol == 0 and orc == 0:
        raise CorpusError(
            "E_NO_PAIRS",
            "every pair supplied is CUT, so the split counts nothing. See "
            "E_NO_PAIRS above: a ratio over an empty denominator is not a ratio.")

    if orc >= pol:
        raise CorpusError(
            "E_ORACLE_PARITY",
            "%d oracle-separated pairs against %d policy-separated. Ruling 17's "
            "authoring gate: at parity, HALF THE HEADLINE IS A STATEMENT ABOUT A "
            "SCRIPTED ORACLE THE BUILDER WROTE, wearing the policy's name - and "
            "it produces the same ASR, the same BPR, and the same curve as a "
            "suite the policy separates. STOP AND RE-AUTHOR. This is a stop "
            "condition, not a threshold to tune." % (orc, pol))

    on_target = (pol, orc) == (TARGET_POLICY, TARGET_ORACLE)
    note = ("on target" if on_target else
            "off target: %d policy / %d oracle against a target of %d / %d. Not "
            "a stop condition - the stop condition is parity - but the deviation "
            "is reported rather than absorbed."
            % (pol, orc, TARGET_POLICY, TARGET_ORACLE))

    return {
        "policy": pol,
        "oracle": orc,
        "cut": len(cut_pairs),
        "cut_pairs": cut_pairs,
        "counted": pol + orc,
        "on_target": on_target,
        "status": "OK",
        "note": note,
        # Ruling 17 requires this next to any ASR or BPR figure, with the same
        # permanence as the k=1 label. Returning it FROM the counter means the
        # number and its caveat cannot be separated by a copy-paste.
        "reporting_line": (
            "SEP-BY split: %d of %d pairs separated by the policy, %d by the "
            "approval oracle (%d cut, not counted)."
            % (pol, pol + orc, orc, len(cut_pairs))),
    }
