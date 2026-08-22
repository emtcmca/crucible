"""test_lane_brief_generator.py - `scripts/make-lane-briefs.py` must reproduce
the six lane briefs that are committed under `docs/lanes/`.

WHY THIS EXISTS
----------------
Same loaded gun as `tests/test_golden_generator.py`, one directory over, and it
was already loaded when this file was written.

A lane brief is the ONLY document a lane reads besides `CONVENTIONS.md` and the
contracts it consumes (`lanes-spec.md` section 6). Lane blindness is
load-bearing, so the brief is the whole of a lane's picture of its own scope,
counts, and exit criteria. Regenerating the set is a documented one-command
operation with no confirmation step.

FOUND 2026-08-22, on this tree, before the fix in the same commit: running
`python scripts/make-lane-briefs.py` would have SILENTLY REVERTED ruling 43 in
`docs/lanes/L2-target-corpus.md` - back to 48 training attacks, 24 benign, 12
near-misses, 24 recorded v0 traces, and an exit criterion of `benign suite
24/24` against a hash-locked gate rule that pins `26/26`. It would also have
reverted L6's F-3 correction, restoring `docs/adr/  the ADRs` to a lane whose
brief must say COORDINATOR ONLY.

Nothing could see it. The suite reads `docs/lanes/*.md` for exactly nothing, and
the generator's staleness is invisible until someone runs the documented command
- which is the one moment nobody is reading the diff.

That is now three generators-versus-hand-edits defects on this project inside
three days (ruling 38 and ruling 43 in `make-golden.py`, ruling 43 again here).
The shape is not a stale script. It is a documented command that reverts a
ruling.

LINE ENDINGS ARE DELIBERATELY NOT PART OF THE QUESTION
-------------------------------------------------------
`main()` writes LF. `.gitattributes` pins `contracts/**`, `target/**`,
`corpus/**` and `fixtures/**` to `eol=lf`, but NOT `docs/**` - and
`core.autocrlf=true` here, so a fresh Windows checkout carries these files with
CRLF. `read_text()` uses universal newlines, so this compares CONTENT and would
not go red on a clone whose only difference is the platform. A byte comparison
would have failed on every judge's machine while passing on the author's, which
is the worst direction for a gate to be wrong in.
"""

import importlib.util
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
LANES_DIR = REPO / "docs" / "lanes"
GENERATOR = REPO / "scripts" / "make-lane-briefs.py"

# Hand-written in `docs/lanes/`, no generator entry, and named here so the hole
# is a declaration rather than a silence: the kickoff note and the six lane logs
# are dated records of what a lane did, not coordinator-issued briefs.
NOT_GENERATED = {"KICKOFF-2026-08-20.md"}


def _load_generator():
    """Import the generator without running `main()`.

    Executing it would WRITE the briefs, and a check that repairs the thing it
    measures is not measuring anything.
    """
    spec = importlib.util.spec_from_file_location("_make_lane_briefs", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generated():
    return _load_generator().briefs()


def test_the_generator_and_the_committed_briefs_are_the_same_text(generated):
    mismatches = []
    for name, body in sorted(generated.items()):
        path = LANES_DIR / name
        if not path.exists():
            mismatches.append("%s: the generator emits it, the repo does not "
                              "carry it" % name)
            continue
        if path.read_text(encoding="utf-8") != body:
            mismatches.append(
                "%s: re-running `python scripts/make-lane-briefs.py` would "
                "CHANGE this committed brief. Whichever is right, the two must "
                "not disagree - the documented regeneration command silently "
                "reverts hand-edits, and a lane cannot see past its brief."
                % name)
    assert not mismatches, "\n".join(mismatches)


def test_every_committed_brief_is_either_generated_or_declared_hand_written(generated):
    """A generator that quietly stopped covering a lane looks exactly like a
    lane that never had one. This makes the difference a declaration."""
    on_disk = {p.name for p in LANES_DIR.glob("*.md")}
    # `L<N>-log.md` is a lane's own dated log, not a coordinator brief.
    logs = {n for n in on_disk if n.endswith("-log.md")}
    uncovered = sorted(on_disk - set(generated) - NOT_GENERATED - logs)
    assert not uncovered, (
        "these lane documents are on disk with no generator entry and are not "
        "on the declared hand-written list: %s. Add them to the generator or "
        "to NOT_GENERATED with the reason." % uncovered)


def test_the_briefs_carry_the_ruling_43_counts(generated):
    """The specific regression, asserted against the corpus rather than against
    a literal.

    L2 is the corpus lane, so its brief states the benign denominator and the
    near-miss floor in three places. `corpus/model.py` owns both numbers; this
    reads them from there, so the next amendment moves this check without an
    edit and cannot leave it asserting a dead value.
    """
    from corpus.model import BENIGN_TOTAL, NEAR_MISS_FLOOR

    l2 = generated["L2-target-corpus.md"]
    for phrase in ("%d fixtures, %d mechanical near-misses"
                   % (BENIGN_TOTAL, NEAR_MISS_FLOOR),
                   "%d benign with %d near-misses" % (BENIGN_TOTAL, NEAR_MISS_FLOOR),
                   "the %d recorded v0 fixture traces" % BENIGN_TOTAL,
                   "benign suite **%d/%d**" % (BENIGN_TOTAL, BENIGN_TOTAL),
                   "every one of the %d benign fixtures" % BENIGN_TOTAL):
        assert phrase in l2, (
            "the L2 brief the generator emits does not carry %r. It is the only "
            "document that lane reads about its own corpus." % phrase)

    assert "24/24" not in l2 and "12 near-misses" not in l2, (
        "the L2 brief still carries a pre-ruling-43 denominator")


def test_the_l6_brief_states_the_bound_the_denominator_implies(generated):
    """L6 owns the README and the camera. Its brief tells that lane which figure
    to speak, so a stale bound here is the one that reaches a judge.

    The expected string is COMPUTED by the same function the replay viewer uses,
    which is why the viewer was right on the day four documents said 12.5%.
    """
    from crucible.replay.integrity import BENIGN_DENOMINATOR
    from crucible.replay.view import regression_upper_bound

    bound = "%.1f%%" % regression_upper_bound(0, BENIGN_DENOMINATOR)
    l6 = generated["L6-evidence.md"]
    assert "upper bound ~%s" % bound in l6, (
        "the L6 brief does not tell the evidence lane to say ~%s" % bound)
    assert "0/%d bounds the true rate" % BENIGN_DENOMINATOR in l6
    # The INSTRUCTIONS, not every mention. The brief may say ≈12.5% while
    # recounting that four documents once did - annotating a dead figure is how
    # this project retires one. What it may never do is tell the lane to speak it.
    assert "upper bound ~12.5%" not in l6, (
        "the L6 brief still instructs the lane to speak the pre-ruling-43 bound")
    assert "bounds the true rate at ≈12.5%" not in l6, (
        "the L6 brief still asserts the pre-ruling-43 bound as current")


def test_the_l6_brief_does_not_hand_the_lane_the_coordinator_s_adrs(generated):
    """F-3, reported by L6 itself on 2026-08-20: the brief's owned-paths block
    listed `docs/adr/` for a lane, contradicting `lanes-spec.md` section 4,
    which reserves ADRs for the coordinator because they record CROSS-lane
    decisions and a blind lane cannot see across. The file was corrected by hand
    and the generator was not, so the correction had a one-command undo.
    """
    l6 = generated["L6-evidence.md"]
    assert "docs/adr/          COORDINATOR ONLY" in l6
