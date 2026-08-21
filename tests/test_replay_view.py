"""test_replay_view.py - what the viewer must and must not put on a screen.

Three things are checked here and they are different in kind:

  LEGIBILITY   `docs/lanes/L6-evidence.md` section 5 requires the output to be
               legible at 1080p, so no rendered line may run past the page
               width. A label that runs off the right edge of a projector is a
               label that was not said.

  LABELS       every figure carries `k = 1, single-sample, no stability
               estimate`, the SEP-BY split, the target's model tier, and the
               regression bound. Section 6 is explicit about the direction the
               trade runs: if a number cannot be stated with its label in the
               space available, cut THE NUMBER, not the label.

  CLAIM        `CONVENTIONS.md` section 7 lists sentences that must never
  VOCABULARY   appear. This is the only mechanical check on them in the repo,
               and it runs over the viewer's own output and over the README,
               because those are the two surfaces a judge actually reads.

WHY THE CLAIM CHECK IS A TEST AND NOT A REVIEW HABIT
-----------------------------------------------------
The same argument the canon drift gate makes: repetition across documents is
not enforcement. A banned phrase gets into a README the same way a dead value
gets into a spec - by somebody writing the natural sentence. The natural
sentence here is "no legitimate behavior was lost", which is exactly the one
CONVENTIONS forbids and exactly the one 0/24 does not support.
"""

import json
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
GOLDEN = REPO / "contracts" / "golden" / "C6-evidence_bundle.valid.json"
README = REPO / "README.md"

from crucible.replay import read_bundle_bytes, write_bundle  # noqa: E402
from crucible.replay.view import (  # noqa: E402
    WIDTH,
    regression_upper_bound,
    render,
)


@pytest.fixture(scope="module")
def rendered():
    raw = GOLDEN.read_bytes()
    bundle, report = read_bundle_bytes(raw)
    return render(bundle, report, source=str(GOLDEN))


@pytest.fixture(scope="module")
def rendered_with_episode():
    raw = GOLDEN.read_bytes()
    bundle, report = read_bundle_bytes(raw)
    eid = bundle["episodes"][0]["episode_id"]
    return render(bundle, report, source=str(GOLDEN), episode_id=eid)


# --------------------------------------------------------------------------
# Legibility.
# --------------------------------------------------------------------------

def _too_long(page):
    return [(i, len(l), l) for i, l in enumerate(page.split("\n"), 1)
            if len(l) > WIDTH]


def test_no_rendered_line_runs_past_the_page_width(rendered, rendered_with_episode):
    for page in (rendered, rendered_with_episode):
        long_lines = _too_long(page)
        assert not long_lines, "\n".join(
            "line %d is %d chars: %s" % (i, n, l) for i, n, l in long_lines[:6])


def test_the_width_check_does_not_depend_on_where_the_repo_was_cloned():
    """This case exists because the one above passed for the wrong reason.

    Running the README's own commands from a fresh clone in a deep temporary
    directory produced a 130-column line: the bundle PATH is a single
    unbreakable token, and the development checkout happens to sit at
    `C:\\dev\\crucible-wt-L6`, which is short enough to fit. The property being
    claimed is "legible at 1080p for a stranger who cloned this repo", and a
    stranger does not clone it to a path of the author's choosing.

    So the source path is rendered at a length no real one will exceed, and it
    still has to fit.
    """
    raw = GOLDEN.read_bytes()
    bundle, report = read_bundle_bytes(raw)
    deep = ("C:\\Users\\someone\\AppData\\Local\\Temp\\a-very-deeply-nested-"
            "checkout-directory\\crucible\\contracts\\golden\\"
            "C6-evidence_bundle.valid.json")
    assert len(deep) > WIDTH, "the fixture path is not long enough to test anything"
    page = render(bundle, report, source=deep)
    long_lines = _too_long(page)
    assert not long_lines, "\n".join(
        "line %d is %d chars: %s" % (i, n, l) for i, n, l in long_lines[:6])
    assert deep[:40] in page, "the path was wrapped away rather than wrapped"


# --------------------------------------------------------------------------
# Labels.
# --------------------------------------------------------------------------

REQUIRED_LABELS = [
    "single-sample, no stability estimate",
    "any-of-1",
    "policy-separated",
    "APPROVAL_ORACLE-separated",
    "gemini-3.5-flash-lite",
    "trust root",
    "project Owner",
]


@pytest.mark.parametrize("phrase", REQUIRED_LABELS)
def test_every_page_carries_its_labels(rendered, phrase):
    assert phrase in rendered


def test_the_sep_by_split_is_printed_with_both_halves(rendered):
    """Ruling 17. A suite the APPROVAL_ORACLE separates produces identical
    headline numbers to one the policy separates, so printing only the total,
    or only the policy half, loses the one thing that tells them apart."""
    assert re.search(r"18 policy-separated / 4 APPROVAL_ORACLE-separated", rendered)


def test_the_viewer_states_no_rate(rendered):
    """Nothing has been measured on this project as of 2026-08-20, and the
    viewer is not the component that owns a rate anyway. A census of the file
    is a fact about the file; a rate is a claim about the world."""
    assert "a count of what is in this file, not a result" in rendered
    assert "This viewer states no rate." in rendered
    assert not re.search(r"\bASR\s*[:=]\s*\d", rendered)
    assert not re.search(r"\b\d+(\.\d+)?%\s*(ASR|attack success)", rendered, re.I)


# --------------------------------------------------------------------------
# The rule of three, computed rather than recalled.
# --------------------------------------------------------------------------

def test_zero_of_twenty_four_bounds_regression_at_twelve_point_five_percent():
    """The number spoken on camera and printed in the README. It is COMPUTED
    from 3/n so that it cannot drift away from the denominator it belongs to -
    which has happened to other numbers in this project more than once."""
    assert regression_upper_bound(0, 24) == pytest.approx(12.5)


def test_the_bound_is_withheld_when_its_precondition_fails():
    """The rule of three bounds an UNOBSERVED rate. Once a failure has been
    observed it does not apply, and stating a softened bound anyway would be
    the exact shape CONVENTIONS section 7 warns about - a sentence that
    survives because nobody checks the arithmetic behind it."""
    assert regression_upper_bound(1, 24) is None
    assert regression_upper_bound(0, 48) is None, (
        "the benign denominator is fixed PERMANENTLY at 24. A bound quoted "
        "against 48 is a bound against a corpus that was cut on 2026-08-20.")


def test_the_forbidden_phrasing_is_not_what_gets_printed(rendered):
    assert "no legitimate behavior was lost" not in rendered.lower()


# --------------------------------------------------------------------------
# The episode detail view - the part that makes replay mean something.
# --------------------------------------------------------------------------

def test_the_episode_detail_shows_the_frozen_block_and_the_ordered_prefix(
        rendered_with_episode):
    page = rendered_with_episode
    assert "frozen episode.* context" in page
    assert "account_holder_email" in page
    assert "before_first_user_turn" in page
    assert "ordered episode prefix" in page
    assert "seq 4" in page
    assert "issue_refund" in page


def test_stamped_derived_fields_are_labelled_as_stamped_not_as_arguments(
        rendered_with_episode):
    """Ruling 21: args are POST-STAMP, so replay reads the stamped `derived.*`
    values rather than recomputing them from tool returns the bundle
    deliberately does not carry. A viewer that printed them in the same column
    as the model's own arguments would hide which half the model chose."""
    assert "stamped  derived.approval_tier" in rendered_with_episode
    assert "arg      order_id" in rendered_with_episode


def test_asking_for_an_episode_that_is_not_there_says_so(rendered):
    raw = GOLDEN.read_bytes()
    bundle, report = read_bundle_bytes(raw)
    page = render(bundle, report, episode_id="ep_000000000000")
    assert "no episode 'ep_000000000000'" in page


# --------------------------------------------------------------------------
# Write, read back, and tamper.
# --------------------------------------------------------------------------

def test_a_written_bundle_reads_back_and_its_digest_is_recomputed(tmp_path):
    bundle = json.loads(GOLDEN.read_text(encoding="utf-8"))
    path = tmp_path / "bundle.json"
    digest = write_bundle(bundle, path)
    sidecar = path.with_name(path.name + ".sha256")
    assert sidecar.exists()
    assert sidecar.read_text(encoding="utf-8").split()[0] == digest

    from crucible.replay import read_bundle
    back, report = read_bundle(path)
    assert back == bundle
    assert report.digest == digest


def test_a_tampered_bundle_is_caught_by_the_recomputed_digest(tmp_path):
    """The one check in this lane that is a genuine recomputation from bytes.
    A reader that compared the sidecar to a digest stored INSIDE the bundle
    would pass here, because both copies move together."""
    from crucible.replay import BundleRejected, read_bundle
    bundle = json.loads(GOLDEN.read_text(encoding="utf-8"))
    path = tmp_path / "bundle.json"
    write_bundle(bundle, path)

    edited = json.loads(path.read_bytes().decode("utf-8"))
    edited["run_manifest"]["target_ref"]["model_id"] = "gemini-3.6-flash"
    from crucible.canon import canonicalize
    path.write_bytes(canonicalize(edited))

    with pytest.raises(BundleRejected) as exc:
        read_bundle(path)
    assert any(d.code == "E_DIGEST_MISMATCH" for d in exc.value.defects)


def test_writing_a_bundle_that_would_not_read_back_is_refused(tmp_path):
    """A run that wrote unreadable evidence would discover it on demo day."""
    from crucible.replay import BundleRejected
    from tests import strawman_replay
    bundle = json.loads(GOLDEN.read_text(encoding="utf-8"))
    damaged = strawman_replay.mutate(bundle, "sep_by_split_missing")
    with pytest.raises(BundleRejected):
        write_bundle(damaged, tmp_path / "nope.json")
    assert not (tmp_path / "nope.json").exists()


# --------------------------------------------------------------------------
# Claim vocabulary - CONVENTIONS section 7, over the surfaces a judge reads.
# --------------------------------------------------------------------------

# Only the phrasings CONVENTIONS names, plus the two shapes it describes rather
# than quotes. Adoption figures are covered by a narrow pattern rather than a
# clever one; a regex for "any number near the word users" would fire on
# ordinary prose and get relaxed the first time it did. LOGGING THE DROP
# (section 8 rule 9): this catches the SENTENCES, not every possible paraphrase.
FORBIDDEN = {
    r"makes agents safe": "one held-out family is one held-out family",
    r"prevents prompt injection": "same, and it is not what a capability boundary does",
    r"production[- ]ready": "eleven days, solo, one target agent",
    r"enterprise[- ]grade": "same",
    r"no legitimate behaviou?r was lost":
        "0/24 bounds the true regression rate at ~12.5%; it does not show zero",
    r"vulnerability in google": "a defect in a sample application's stubbed tools",
    r"model armor missed": "same data, adversarial framing, and wrong",
    r"google (?:has )?(?:reviewed|endorsed|approved)": "nothing implying Google responded",
    r"endorsed by google": "same",
    r"\b\d+\s+(?:github\s+)?stars\b": "there are none and there will be none",
    r"\b\d+\s+(?:npm\s+)?downloads\b": "same",
}


_AFFIRMATIVE = {
    r"makes agents safe": "CRUCIBLE makes agents safe.",
    r"prevents prompt injection": "It prevents prompt injection.",
    r"production[- ]ready": "This is production-ready.",
    r"enterprise[- ]grade": "An enterprise grade harness.",
    r"no legitimate behaviou?r was lost": "The run showed no legitimate behavior was lost.",
    r"vulnerability in google": "We found a vulnerability in Google's framework.",
    r"model armor missed": "Model Armor missed it.",
    r"google (?:has )?(?:reviewed|endorsed|approved)": "Google reviewed the submission.",
    r"endorsed by google": "This was endorsed by Google.",
    r"\b\d+\s+(?:github\s+)?stars\b": "The repo has 400 GitHub stars.",
    r"\b\d+\s+(?:npm\s+)?downloads\b": "It has 900 npm downloads.",
}

# Both dicts are keyed by the SAME pattern strings, and this asserts it AT
# IMPORT rather than leaving it to a KeyError inside one parametrized case.
# Two of these keys lost their `\b` anchors in transit on 2026-08-21 - they
# arrived as literal backspace bytes - so `_AFFIRMATIVE[pattern]` raised for
# exactly the two patterns nobody would check by hand, and the counter-test
# could not run on them. A lookup that fails loudly at collection beats one
# that fails inside a case whose name looks like the thing being tested.
assert set(_AFFIRMATIVE) == set(FORBIDDEN), (
    "FORBIDDEN and _AFFIRMATIVE have drifted apart: %s"
    % sorted(set(_AFFIRMATIVE) ^ set(FORBIDDEN)))



def _surfaces():
    out = {}
    raw = GOLDEN.read_bytes()
    bundle, report = read_bundle_bytes(raw)
    out["<rendered view>"] = render(bundle, report, source=str(GOLDEN))
    if README.exists():
        out["README.md"] = README.read_text(encoding="utf-8")
    return out


# A DISCLAIMER IS NOT A CLAIM, and the guard could not tell them apart.
#
# Found 2026-08-21, when the README grew a "What this does not prove" section
# that says, correctly, *"Not production-ready. Not enterprise-grade."* and
# *"It is not evidence that no legitimate behaviour was lost."* All three tripped
# the gate. The gate was matching the words rather than the assertion.
#
# THE NARROWING IS DELIBERATELY SMALL: a hit is excused only when an explicit
# negation sits IMMEDIATELY before it, inside a short window. Nothing else is
# excused. A wider rule - "skip if the paragraph contains 'not'" - would make
# this gate unable to fire on any page that also disclaims anything, which is
# every page we write.
#
# The same instinct that had to be beaten out of `scripts/seal-leak-check.py`
# four times: make it broader so it cannot miss anything, and it catches
# everything and therefore means nothing. `test_the_claim_check_can_actually_fire`
# below now also asserts the affirmative form STILL trips for every pattern.
_NEGATIONS = (
    "not", "never", "no", "isn't", "is not", "aren't", "are not",
    "does not", "doesn't", "cannot", "can't", "nothing implying",
)
_NEG_WINDOW = 40


def _is_disclaimed(text, start):
    """True if an explicit negation immediately precedes the hit."""
    before = text[max(0, start - _NEG_WINDOW):start].lower()
    before = before.replace("*", "").replace("_", "").replace("\"", "")
    tail = before.rsplit(".", 1)[-1].rsplit(chr(10), 1)[-1].strip()
    return any(tail == n or tail.endswith(" " + n) or tail.endswith(" " + n + " ")
               or tail.startswith(n + " ") for n in _NEGATIONS)


@pytest.mark.parametrize("pattern", sorted(FORBIDDEN))
def test_no_forbidden_claim_on_any_surface_a_judge_reads(pattern):
    for name, text in _surfaces().items():
        for hit in re.finditer(pattern, text, re.I):
            if _is_disclaimed(text, hit.start()):
                continue
            assert False, "%s says %r - %s" % (name, hit.group(0), FORBIDDEN[pattern])


@pytest.mark.parametrize("pattern", sorted(FORBIDDEN))
def test_the_negation_escape_does_not_swallow_the_affirmative(pattern):
    """The narrowing must not have disarmed the gate.

    Each pattern is planted in an AFFIRMATIVE sentence with no negation in front
    of it, and must still be caught. If this ever passes silently, the disclaimer
    escape has grown into a hole.
    """
    sentence = "CRUCIBLE is the thing. %s Ship it." % _AFFIRMATIVE[pattern]
    hit = re.search(pattern, sentence, re.I)
    assert hit, "pattern %r no longer matches its own affirmative" % pattern
    assert not _is_disclaimed(sentence, hit.start()), (
        "the disclaimer escape swallowed an AFFIRMATIVE use of %r - the gate "
        "has been narrowed into a hole" % pattern)


def test_the_claim_check_can_actually_fire():
    """A vocabulary gate that has only ever been run over clean prose has not
    been shown to detect anything. Every pattern is run against a sentence
    built to trip it."""
    tripwires = {
        r"makes agents safe": "CRUCIBLE makes agents safe.",
        r"prevents prompt injection": "It prevents prompt injection.",
        r"production[- ]ready": "This is production-ready.",
        r"enterprise[- ]grade": "An enterprise grade harness.",
        r"no legitimate behaviou?r was lost": "No legitimate behavior was lost.",
        r"vulnerability in google": "We found a vulnerability in Google's framework.",
        r"model armor missed": "Model Armor missed 40% of our attacks.",
        r"google (?:has )?(?:reviewed|endorsed|approved)": "Google reviewed this.",
        r"endorsed by google": "Endorsed by Google.",
        r"\b\d+\s+(?:github\s+)?stars\b": "It has 42 GitHub stars.",
        r"\b\d+\s+(?:npm\s+)?downloads\b": "It has 500 downloads.",
    }
    assert set(tripwires) == set(FORBIDDEN), (
        "every forbidden pattern needs a sentence proving it fires: missing %s"
        % sorted(set(FORBIDDEN) - set(tripwires)))
    for pattern, sentence in tripwires.items():
        assert re.search(pattern, sentence, re.I), (
            "pattern %r does not match %r - it is guarding nothing"
            % (pattern, sentence))


def test_the_readme_carries_the_labels_it_is_required_to_carry():
    """Section 7 and the lane brief: the exact numbers, next to the exact
    qualifiers, on the surface a judge reads first."""
    assert README.exists(), "README.md is the judge-reproduction path"
    text = README.read_text(encoding="utf-8")
    for phrase in ("single-sample, no stability estimate",
                   "12.5%",
                   "project Owner",
                   "python -m crucible.replay"):
        assert phrase in text, "README.md does not carry %r" % phrase


def test_the_readme_sep_by_split_matches_the_CORPUS_not_a_target():
    """This check hardcoded `18 policy-separated` until 2026-08-21.

    18/4 is the TARGET in `measurement-spec.md` section 8.1. The corpus on disk
    resolves to a different split, and the deviation is reported rather than
    absorbed - that is ruling 17 working. So the gate was demanding that the
    README print a target AS IF IT WERE THE CORPUS, on the surface a judge reads
    first. That is the exact failure this file exists to prevent, inverted: a
    guard enforcing the wrong number is worse than no guard, because it looks
    like the number was checked.

    Computed from `corpus/pairs.json` instead, so it cannot go stale and cannot
    be satisfied by a value nobody recounted.
    """
    pairs = json.loads(
        (REPO / "corpus" / "pairs.json").read_text(encoding="utf-8"))["pairs"]
    pol = sum(1 for p in pairs if p.get("sep_by") == "POL")
    orc = sum(1 for p in pairs if p.get("sep_by") == "ORC")
    assert pol and orc, "a split with an empty half is not a split"
    assert pol != orc, (
        "SEP-BY parity is a STOP CONDITION, not a passing test (ruling 17): at "
        "parity, half the headline is a statement about a scripted oracle "
        "wearing the policy's name.")
    expected = "%d policy-separated / %d APPROVAL_ORACLE-separated" % (pol, orc)
    text = README.read_text(encoding="utf-8")
    assert expected in text, (
        "README.md must print the SEP-BY split the corpus actually resolves to. "
        "Expected %r." % expected)
