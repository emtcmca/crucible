"""episode.py - the `episode.*` freeze. Ruling 16, and it is marked CRITICAL.

Three fields, frozen at episode start from the scenario's order/account record,
immutable for the episode's duration, recorded in the evidence bundle.

WHY A WRITE IS `HALT_HUMAN` AND NOT A MERGE, A WARNING, OR A LOG LINE.

If an in-episode turn can move `episode.account_holder_email` - *"actually, my
address changed to this one"* - then P06, P12, P19, P25 and THE ENTIRE F4 SEAL
COLLAPSE IN A SINGLE MOVE. Every rule of the form `to == episode.account_holder_
email` is defeated by editing the right-hand side. It is the cheapest possible
way to invalidate the headline result, IT LOOKS LIKE NOTHING, and no gate
catches it: the run completes, the numbers are excellent, and they are about
nothing.

A merge is the obvious wrong answer and it is wrong in a specific way - it does
not fail, so nothing downstream can tell the difference between a scenario where
the customer's address really is X and one where the attacker said so. Writing a
warning is the same failure with a nicer log. The only response that preserves
the measurement is to stop the episode.

Note also the grammar's asymmetry, which is deliberate and which this class
enforces from the other side: `arg_path cmp_op episode.field` exists and
`episode.field cmp_op literal` DOES NOT. An episode fact can only ever be
compared to an argument of the pending call. That is why the `derived.*`
namespace is load-bearing rather than a convenience.

NOT IMPLEMENTED YET - this is the stub the negative checks run RED against.
"""

from ..dsl.errors import HaltHuman  # noqa: F401

EPISODE_PREFIX = "episode."

# The reason code that reaches the run ledger. One symbol, not prose.
EPISODE_FIELD_WRITE_ATTEMPT = "EPISODE_FIELD_WRITE_ATTEMPT"


class EpisodeContext:
    """The three frozen `episode.*` facts for one episode.

    Constructed exactly once, before the first user turn. There is no setter,
    no `update`, no `__setitem__`, and `attempt_write` exists only so that a
    write ATTEMPT has somewhere to land loudly instead of silently succeeding
    against a plain dict.
    """

    @classmethod
    def freeze(cls, fields: dict, *, derived_schema: dict = None):
        """Freeze the episode context before the first user turn.

        `derived_schema` is Part B; when supplied, the field names are checked
        against its declared `episode_fields` so an undeclared episode fact
        cannot be smuggled in at freeze time either.
        """
        raise NotImplementedError("L3 WI-5: episode freeze not implemented yet")

    def get(self, name: str):
        """Read one frozen field. Accepts `account_holder_id` or the fully
        qualified `episode.account_holder_id`."""
        raise NotImplementedError("L3 WI-5: episode freeze not implemented yet")

    def attempt_write(self, name: str, value) -> None:
        """ALWAYS raises HaltHuman. Never merges, never returns.

        The value is not stored, not compared, and not logged as accepted - the
        attempt is evidence and the write is refused.
        """
        raise NotImplementedError("L3 WI-5: episode freeze not implemented yet")

    def as_dict(self) -> dict:
        """A copy, for the evidence bundle. Mutating it changes nothing."""
        raise NotImplementedError("L3 WI-5: episode freeze not implemented yet")
