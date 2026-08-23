"""V22's emptiness escape, closed. Ruling 49b, Eric 2026-08-23.

`check_context_fields` read:

    if self.declared_episode and qualified not in self.declared_episode:

A Part B declaring no `episode_fields` made `declared_episode` empty, and the
leading truthiness test then switched the whole check off IN SILENCE.

V10, ten lines earlier in the same file, answers the identical question the
opposite way. Its error text handles the empty case explicitly and admits
nothing: *"none - this manifest declares no arg_paths at all, so no argument
name is admissible."* Two checks, one file, opposite answers.

**IT WAS NOT AN OVERSIGHT**, and that is why this carries a ruling rather than a
quiet edit. `test_V10_CANNOT_BE_SWITCHED_OFF_BY_A_MANIFEST_THAT_DECLARES_NOTHING`
says in its own docstring that the skip is "defensible for a backstop and would
be fatal here." Someone drew the line between the two checks deliberately.

**The argument that reversed it.** A rule naming `episode.foo` while Part B
declares nothing gets ADMITTED and can then never fire, because `condition_holds`
returns False on an absent path. That is exactly the defect ruling 48 was written
about on the oracle side of the system, where it cost four episodes their true
verdict. "Defensible for a backstop" and "a check that cannot fail in one
configuration" are one sentence seen from two angles.

Not live-exploitable when found, asserted rather than assumed: the corpus Part B
declares three episode fields, so the check was active on every path that runs.
The empty configuration was one edit away rather than present.

Found by the DSL mutation audit, which reported it instead of changing a
validator it did not own.
"""
import pytest

from crucible.dsl import parse_rule
from crucible.dsl.validator import Validator, ValidationError
import tests.l3_fixtures as fx


RULE = "rule r_new1: cap:CAP_MOVES_MONEY when beneficiary_id != episode.account_holder_id => deny"


def _validator(episode_fields):
    part_b = dict(fx.DERIVED_B)
    part_b["episode_fields"] = episode_fields
    return Validator(fx.MANIFEST_A, part_b)


def test_a_declared_episode_field_is_accepted():
    """POSITIVE CONTROL. Without it the test below could pass because the check
    refuses everything, which is a different defect wearing the same green."""
    v = _validator([{"name": "episode.account_holder_id"}])
    v.check_context_fields(parse_rule(RULE))


def test_an_undeclared_field_is_refused_when_part_b_declares_others():
    """The road that already worked, pinned so closing the escape cannot
    silently break it."""
    v = _validator([{"name": "episode.account_holder_email"}])
    with pytest.raises(ValidationError) as ei:
        v.check_context_fields(parse_rule(RULE))
    assert ei.value.code == "E_UNDECLARED_EPISODE_FIELD"


def test_an_EMPTY_part_b_ADMITS_NOTHING_rather_than_everything():
    """THE ESCAPE ITSELF. Red before the one-word fix, green after.

    A Part B declaring no episode fields declares no episode field, so every
    `episode.*` context field in a rule names something undeclared. V10 answers
    this question by admitting nothing. V22 now agrees with it.
    """
    v = _validator([])
    assert v.declared_episode == frozenset(), (
        "precondition: this test is only meaningful against an EMPTY declared set")
    with pytest.raises(ValidationError) as ei:
        v.check_context_fields(parse_rule(RULE))
    assert ei.value.code == "E_UNDECLARED_EPISODE_FIELD"
