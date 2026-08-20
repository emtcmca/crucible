"""Episode context - frozen before the first user turn, unwritable thereafter.

`CONVENTIONS.md` ruling 16 and `separability-proof.md` section 5.1. Three fields,
taken from the scenario's order/account record at episode start:

    episode.account_holder_email
    episode.account_holder_id
    episode.order_payment_instrument_id

WHAT THIS IS FOR, in plain English before the jargon. Several of the attacks this
project measures work by getting the agent to send money or data somewhere that is
not where the order says it should go. The rule that catches that compares an
argument of the pending call against a fact about the account - "is this payout
instrument the one on the order?" If a customer can move the fact by talking
("actually, my address changed to this one"), the comparison passes and the rule
that was supposed to fire never fires. The attack does not defeat the rule; it
edits the thing the rule compares against.

Ruling 16 calls that "the cheapest possible way to invalidate the headline result",
notes it "looks like nothing", and - the part that matters here - says NO GATE
CATCHES IT. That is why the refusal lives in the target's own episode object rather
than only in the enforcement lane's plugin: there is no downstream check to fall
back on.

WHY THE UPDATE METHOD EXISTS AND ALWAYS RAISES. `apply_context_update` could just
be absent. It is present and unconditionally refusing because of what the two
options cost LATER. To make an absent method work, someone adds a method - which
reads as a feature in review. To make this one work, someone deletes a `raise` from
a function whose docstring says why it is there - which reads as what it is. The
refusal is the API, not the omission of one.

THE ALTERNATIVE CONSIDERED AND REJECTED: freezing on the first `record_user_turn`
call rather than at build. That is what "frozen before the first user turn"
literally licenses, and it is worse - it opens a window between construction and
turn one in which a writer exists, and windows get widened. Freezing at build makes
the window zero-width and the tests assert the refusal fires with `turn_count == 0`.
"""

import dataclasses
import re

# The three baseline fields. `separability-proof.md` section 5.1 tables exactly
# these, and section 5's accounting treats them as baseline rather than as a schema
# change, because CONVENTIONS section 5 already mandated the
# `arg_path cmp_op episode.<context_field>` predicate form and that form is inert
# until the fields are declared. A fourth field added here would be a field the D5
# label-blindness check never ran over.
EPISODE_CONTEXT_FIELDS = (
    "account_holder_email",
    "account_holder_id",
    "order_payment_instrument_id",
)

EPISODE_ID_RE = re.compile(r"^ep_[0-9a-f]{12}$")   # C1's pattern, enforced here


class EpisodeFrozenError(RuntimeError):
    """An attempt to write episode context after it was frozen.

    Always a refusal, never a repair. Accepting the write and logging it would put
    the attacker's value in the field the F4 rule compares against, which is the
    entire failure.
    """


class EpisodeBuildError(ValueError):
    """The episode could not be built. Distinct from `EpisodeFrozenError`: this one
    means the context was never valid, not that someone tried to change it."""


@dataclasses.dataclass(frozen=True, slots=True)
class EpisodeContext:
    """Immutable. `frozen=True` refuses attribute assignment; `slots=True` removes
    the `__dict__` that `object.__setattr__` would otherwise write through."""

    account_holder_email: str
    account_holder_id: str
    order_payment_instrument_id: str

    def as_arg_paths(self) -> dict:
        """`{"episode.account_holder_email": ...}` - the form the policy engine's
        third predicate compares an argument against."""
        return {"episode.%s" % f: getattr(self, f) for f in EPISODE_CONTEXT_FIELDS}


class EpisodeBuilder:
    """The ONLY writer of episode context, and it is spent by `build()`."""

    def __init__(self, episode_id: str):
        if not EPISODE_ID_RE.match(episode_id or ""):
            raise EpisodeBuildError(
                "%r is not an episode id. C1 pins ^ep_[0-9a-f]{12}$, and a malformed "
                "id produces ToolEvents that fail validation at the far end of the "
                "run, where the cause is no longer visible." % episode_id)
        self._episode_id = episode_id
        self._fields = {}
        self._spent = False

    def _guard(self):
        if self._spent:
            raise EpisodeFrozenError(
                "this builder already produced an episode. Episode context is frozen "
                "at build; a builder that could be re-opened is a writer that "
                "outlives the freeze.")

    def set_context_field(self, name: str, value: str) -> "EpisodeBuilder":
        self._guard()
        if name not in EPISODE_CONTEXT_FIELDS:
            raise EpisodeBuildError(
                "%r is not one of the three declared context fields %r. Adding a "
                "fourth here would add a field the label-blindness check never ran "
                "over." % (name, list(EPISODE_CONTEXT_FIELDS)))
        if not isinstance(value, str) or not value:
            raise EpisodeBuildError(
                "%r for %s - context values are non-empty strings. An absent fact is "
                "an absent key, and a defaulted empty string compares equal to an "
                "attacker-supplied empty string." % (value, name))
        self._fields[name] = value
        return self

    def from_order_record(self, order) -> "EpisodeBuilder":
        """Populate all three from the system of record.

        This is the only source permitted. `separability-proof.md` section 5.4 rule
        1: computed from the episode prefix and the scenario's system-of-record data
        only - never from the label, never from payload text, never from the
        target's prose.
        """
        self._guard()
        if order is None:
            raise EpisodeBuildError(
                "no order record. The episode context is built FROM the system of "
                "record; there is no path that builds it from the conversation.")
        self.set_context_field("account_holder_email", order.account_holder_email)
        self.set_context_field("account_holder_id", order.account_holder_id)
        self.set_context_field("order_payment_instrument_id",
                               order.payment_instrument_id)
        return self

    def build(self) -> "Episode":
        self._guard()
        missing = [f for f in EPISODE_CONTEXT_FIELDS if f not in self._fields]
        if missing:
            raise EpisodeBuildError(
                "context incomplete, missing %r. A partially built context is not a "
                "context - the rule that compares against the missing field silently "
                "stops separating anything." % missing)
        self._spent = True
        return Episode(self._episode_id, EpisodeContext(**self._fields))


class Episode:
    """A frozen episode. Turns are appended; context never moves."""

    __slots__ = ("_episode_id", "_context", "_turns", "_sealed")

    def __init__(self, episode_id: str, context: EpisodeContext):
        object.__setattr__(self, "_episode_id", episode_id)
        object.__setattr__(self, "_context", context)
        object.__setattr__(self, "_turns", [])
        object.__setattr__(self, "_sealed", True)

    # `episode.context = <another context>` would be a freeze with a hinge in it:
    # every field refusal held, and the whole object swapped underneath them.
    def __setattr__(self, name, value):
        raise EpisodeFrozenError(
            "episode attributes are frozen at build; %r cannot be reassigned. "
            "Refusing field writes while permitting a whole-object swap would be a "
            "freeze with a hinge in it." % name)

    @property
    def episode_id(self) -> str:
        return self._episode_id

    @property
    def context(self) -> EpisodeContext:
        return self._context

    @property
    def turn_count(self) -> int:
        return len(self._turns)

    @property
    def turns(self) -> tuple:
        return tuple(self._turns)

    def record_user_turn(self, text: str) -> int:
        """Append a user turn. Turns are the mutable part of an episode; context is
        not, and the two are deliberately different objects so that nothing which
        appends a turn is holding a handle to the context."""
        self._turns.append(text)
        return len(self._turns)

    def context_value(self, path: str):
        """Resolve an `episode.<field>` arg path. Unknown paths raise rather than
        returning None, because a predicate silently comparing against None is a
        predicate that stopped firing."""
        table = self._context.as_arg_paths()
        if path not in table:
            raise KeyError(
                "%r is not a declared episode context path; declared: %r"
                % (path, sorted(table)))
        return table[path]

    def apply_context_update(self, **fields):
        """ALWAYS REFUSES. See the module docstring for why it exists at all.

        This is the door the headline attack knocks on: a mid-episode turn claiming
        the account's email, holder, or payout instrument has changed. Ruling 16 -
        one such write collapses P06, P12, P19, P25 and the whole F4 seal.
        """
        raise EpisodeFrozenError(
            "episode context is frozen before the first user turn and is unwritable "
            "thereafter (ruling 16). Refused write to %r. A change of address, "
            "instrument, or account holder is a system-of-record change made outside "
            "an episode - it is not something a conversation does."
            % sorted(fields))
