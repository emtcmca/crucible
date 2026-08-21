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

`HaltHuman` and not a `DslError`, deliberately: a `DslError` gets one repair
attempt, and there is nothing here to repair. By the time a write is seen the
invariant is already broken, and a "repaired" write is just a merge that took
two tries.

Note also the grammar's asymmetry, which this class enforces from the other
side: `arg_path cmp_op episode.field` exists and `episode.field cmp_op literal`
DOES NOT. An episode fact can only ever be compared to AN ARGUMENT OF THE
PENDING CALL. That is why the `derived.*` namespace is load-bearing rather than
a convenience, and it is also why there is no reader on this class that returns
the whole frozen mapping to the evaluator.
"""

from ..dsl.errors import HaltHuman

EPISODE_PREFIX = "episode."

# The reason code that reaches the run ledger. One symbol, not prose.
EPISODE_FIELD_WRITE_ATTEMPT = "EPISODE_FIELD_WRITE_ATTEMPT"


class EpisodeContext:
    """The three frozen `episode.*` facts for one episode.

    Constructed exactly once, before the first user turn. There is no setter, no
    `update`, and no `__setitem__`. `attempt_write` exists ONLY so that a write
    attempt has somewhere to land loudly instead of silently succeeding against
    a plain dict - if this class had no such method, the natural implementation
    at the call site would be `ctx[field] = value`, which is the merge.
    """

    __slots__ = ("_fields",)

    def __init__(self, fields):
        object.__setattr__(self, "_fields", dict(fields))

    # -- construction -----------------------------------------------------
    @classmethod
    def freeze(cls, fields: dict, *, derived_schema: dict = None):
        """Freeze the episode context before the first user turn.

        `derived_schema` is Part B; when supplied, the field names are checked
        against its declared `episode_fields`, so an undeclared episode fact
        cannot be smuggled in AT FREEZE TIME EITHER. Guarding only the write
        path would leave the front door open: a fourth `episode.*` fact placed
        at construction is never written to, so it never trips `attempt_write`,
        and a rule comparing against it would be comparing against something no
        blindness check ever saw.
        """
        frozen = {}
        for name, value in (fields or {}).items():
            frozen[cls._qualify(name)] = value

        if derived_schema:
            declared = {f["name"] for f in derived_schema.get("episode_fields", [])}
            if declared:
                unknown = sorted(set(frozen) - declared)
                if unknown:
                    raise HaltHuman(
                        "UNDECLARED_EPISODE_FIELD",
                        "%s is not declared in Part B (%s). An episode fact the "
                        "derived schema does not carry is a fact no "
                        "label-blindness check ever ran over."
                        % (", ".join(unknown), ", ".join(sorted(declared))))
        return cls(frozen)

    @staticmethod
    def _qualify(name):
        return name if name.startswith(EPISODE_PREFIX) else EPISODE_PREFIX + name

    # -- read -------------------------------------------------------------
    def get(self, name: str):
        """Read one frozen field. Accepts `account_holder_id` or the fully
        qualified `episode.account_holder_id` - one field, two spellings, never
        two fields."""
        return self._fields.get(self._qualify(name))

    def __contains__(self, name):
        return self._qualify(name) in self._fields

    def as_dict(self) -> dict:
        """A COPY, for the evidence bundle. Mutating it changes nothing here -
        a live reference would be a second write path that `attempt_write` does
        not guard, which is the same defect wearing a getter's name."""
        return dict(self._fields)

    # -- write, which never happens ---------------------------------------
    def attempt_write(self, name: str, value) -> None:
        """ALWAYS raises HaltHuman. Never merges, never returns.

        The value is not stored, not compared, and not recorded as accepted. The
        ATTEMPT is the evidence; the write is refused.
        """
        raise HaltHuman(
            EPISODE_FIELD_WRITE_ATTEMPT,
            "%s is frozen for the duration of this episode (ruling 16). "
            "Something tried to set it to %r after episode start. Merging the "
            "write would defeat every rule of the form "
            "`arg == episode.<field>` in one move, and it would do so silently: "
            "the run completes, the numbers look excellent, and they are about "
            "nothing." % (self._qualify(name), value))

    # -- close the remaining doors ----------------------------------------
    def __setattr__(self, name, value):                      # pragma: no cover
        raise HaltHuman(EPISODE_FIELD_WRITE_ATTEMPT,
                        "EpisodeContext is immutable; %r was not set" % name)

    def __setitem__(self, name, value):
        # Present so the natural-looking `ctx[field] = value` cannot quietly do
        # nothing on a __slots__ object - it routes to the same refusal.
        self.attempt_write(name, value)

    def __repr__(self):                                      # pragma: no cover
        return "EpisodeContext(frozen=%d)" % len(self._fields)
