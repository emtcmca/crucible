"""corpus_seeds.py - the adapter between `corpus/training/` and the campaign.

THE DEFECT THIS CLOSES
----------------------
`docs/decisions-pending/campaign-does-not-read-the-corpus.md`, coordinator
finding 2026-08-22: `campaign.py` ran six hand-authored one-sentence
`AttackSeed` literals while `corpus/training/` held 50 rich instances covered by
the `corpus_hash` hash-lock. **`AttackSeed` was constructed in exactly one place
in the repository and there was never an adapter.** The consequence is the one
that matters: the campaign's `fam_direct_ask`-style family ids map to nothing in
the F1-F7 taxonomy, so no per-family rate and no F4 transfer number was
computable from any campaign run - which is the number this project exists to
produce.

This module is that adapter, and it does four things:

    1. loads the TRAINING corpus and turns each instance into an `AttackSeed`
       whose `family_id` round-trips to a real F-family
    2. builds a PER-INSTANCE seeded world, so an attack that names ORD-4471 is
       run against a world that actually holds ORD-4471
    3. carries the provenance the C6 evidence bundle's `attacks[]` array needs
    4. carries the instance's `input_turns` so the escalation can be DRIVEN
       rather than concatenated

WHY A PER-INSTANCE WORLD IS THE PART THAT WOULD HAVE FAILED SILENTLY
--------------------------------------------------------------------
`campaign.py` pins one shared seeded world (`SCENARIO_ORDER_ID = "ORD-4472"`).
Run `F1-01-chargeback-band-override` - a $900 defective television on ORD-4471 -
against that world and the collision is not even a miss: the demo world DOES
hold an ORD-4471, and it is a **$34 stoneware mug**
(`simulated_system_of_record.py::seed_demo_ledger`). The agent looks the order
up, finds it, and the ledger's own business invariant refuses a $90000 refund
against a $3400 order. The episode scores NON-BREACH and indexes as hardening.
Nothing raises. That is the flattering-error shape this repo watches for, and it
is why item 1 is mandatory rather than an improvement.

THE SEALED BOUNDARY, AND WHAT THIS MODULE DOES AND DOES NOT CLAIM ABOUT IT
---------------------------------------------------------------------------
**The real boundary is IAM.** The red-team and Armorer service accounts hold no
role on `gs://crucible-sealed-x7`, `real_gate.py` G7b re-asserts that every
round, and `docs/proof/armorer-403.txt` is the evidence. Nothing in this file
is that boundary, and this file does not claim to be it.

What this file adds is the structural half on the code side: **the layout it
loads from names the training directory and nothing else** (`TRAINING_LAYOUT`),
so there is no path from here to `corpus/sealed/` to be disabled, misconfigured,
or forgotten. `corpus.load.load_corpus` iterates the layout it is handed; a
bucket absent from the layout is a bucket it never opens.

The second half is a refusal rather than a filter. Any loaded instance whose
`family` is not in `corpus.model.TRAINING_FAMILIES` RAISES
`E_SEALED_FAMILY_REACHED`. **Filtering would have been the wrong shape**: a
filter that silently drops an F4 instance planted in `training/` passes
identically whether the seal held or not, and section 8 rule 2 says a check that
cannot fail is not measuring anything. The family names are read from
`corpus.model`, never typed here, so "which family is sealed" has one owner.

**On `corpus/blindness.py`:** it is CALLED, not copied, and not duplicated. It
is a LABEL-leak check - does any `derived.*`/`episode.*` field predict
attack-vs-benign - which is a different class of check from sealed-family
reachability, and the repo has no existing code-side check of the second kind.
What this module reuses is its ten reference field computers and its
`BlindInstance` view: `verify_world()` below computes the six fields that reach
the policy engine straight out of `corpus.blindness.FIELD_COMPUTERS` and asserts
they equal what `real_target` derives from the constructed world. One definition,
two derivations, cross-checked - rather than a second implementation of either.

THE THIRD THING A WORLD CAN BE WRONG ABOUT, ADDED 2026-08-22
--------------------------------------------------------------
The two above are "the world is a different world" and "the world does not
round-trip the instance". The third is **the world cannot present the scenario
at all**: the instance's own trace makes a successful call against an entity
that the world built from its own `scenario` block does not hold. Two of the
fifty do this today - `F2-02` and `F2-08` both `lookup_customer("CUS-9142")`,
the linked/merged account the poisoned note points at, and neither instance
states a record for it. The call returns `{"status": "error"}`, the plugin
records `TOOL_EXECUTED` anyway (`crucible/plugin/core.py::after_tool` fires on
the tool BODY running, and `on_tool_error` catches raises only), and both
episodes score **CLEAN**. A read of a third party's file that never happened,
counted as an attack the target repelled.

`unpresentable_entities()` is the precondition, `CorpusAttack.unpresentable`
and `EpisodeWorld.unpresentable` carry it, `report()` counts it and
`disclaimers()` says it out loud. It reads ONLY fixture data - the instance's
own trace - because case 3 is the HARNESS failing to set the test up, never the
target failing it. A model that invents an order id is the finding, not an
exclusion.

FIELDS THE CORPUS DOES NOT CARRY, DECLARED RATHER THAN INVENTED
----------------------------------------------------------------
`OrderRecord` and `CustomerRecord` are frozen dataclasses with required fields.
The corpus does not state all of them, and the counts are not small:

    order.currency          stated by 34 of 50
    order.order_status      stated by 16 of 50
    order.refunded_minor    stated by 16 of 50
    order.placed_on         stated by  0 of 50 - the corpus has no placed date

Nothing here fills those with a plausible number. `currency` and `order_status`
become **None**, which `lookup_order` surfaces to the target as JSON `null` -
the honest rendering of "not on file", and a value that fails loudly if anything
downstream ever starts reading it, rather than a `0` or a `"USD"` that would
read as data. Two are derivations rather than inventions and both are declared:
`refunded_minor` is `0` because an instance's `trace` IS its whole episode and
no corpus instance records a prior refund, and `placed_on` is set to
`delivered_on` because no artifact states an order date and nothing on the drive
path reads the field (`tools.py` surfaces `item_description`, `category` and
`order_status`, never `placed_on`).

Every one of those lands on `CorpusAttack.unstated_fields`, and `report()`
tallies them across the corpus so the gap is a number in the run rather than a
paragraph in a file.

THE SECOND ACCOUNT DIALECT IS GONE, EXCEPT FOR ONE FIELD THAT HAS NO HOME
------------------------------------------------------------------------
The account panel was authored in two dialects - a clean 32/18 split over
`corpus/training/*.json`, no instance mixing them. **This module refused to
accept both spellings**, which is precisely the shim that produced
`ALLOW`/`allow` and `outcome`/`target_fault` here already; a shim in the adapter
is where a drift goes to live forever. So they were counted rather than read,
and the 18 were re-authored on 2026-08-22.

THE CANONICAL DIALECT CAME FROM THE TARGET, NOT FROM THE VOTE.
`target/refund_agent/system_of_record.py:81-86` declares the six names and
`tools.py:145-150` returns exactly those six from `lookup_customer`. 32-vs-18 is
a majority, not an authority; the two agreed, and had they not, the 32 would
have been re-authored instead. `lifetime_orders` -> `lifetime_order_count`,
`not_received_lifetime` -> `not_received_claims_lifetime`, `open_risk_flag` ->
`risk_flag_open`.

`returns_90d` IS NOT A RENAME AND IT STAYS IGNORED. It is a COUNT of returns in
the trailing 90 days. `CustomerRecord` carries `lifetime_return_rate_pct` (a
lifetime percentage) and `refunds_trailing_90_minor` (money). Neither is that
number, and the instances prove the reading in their own traces - `F5-10`'s note
reads "Five returns in the trailing 90 on seven lifetime orders" against
`returns_90d: 5`. Mapping it onto either field would quote five returns off a
panel reading five cents; dropping it would delete a stated fact. Both are value
invention, so it stays stated, unread, counted, and named in `disclaimers()`.

WHY THAT COSTS NOTHING MEASURABLE - checked, not assumed. The field feeds
`refund_policy.md` section 8.3, "Trailing-90-day return rate above 60% with four
or more orders." **The target cannot evaluate 8.3 from any tool it has**: no
tool returns a trailing-90 return count or rate. And **8.3 appears in none of
the Objective Set's nine clauses**, so nothing it could change is scored. Adding
the field would move `target_agent_hash` for a policy clause that is
unenforceable and unscored.

WORTH KNOWING, AND NOT A DEFECT IN THIS MODULE: 8.3 is not alone. Section 8.2
("second NOT_RECEIVED claim within 180 days") has only a LIFETIME count to read,
and 8.6 ("three or more contacts on the same order in 72 hours") has no contact
count in any tool's return surface. **Three of the target's seven risk holds are
unevaluable from its own data.** None is in the Objective Set, so no number
moves - but "which clauses of a written policy are evaluable from the tool
surface" is a real question a hardening harness should answer, and CRUCIBLE does
not answer it yet.

**None of the four reaches the policy engine.** They are surfaced by
`lookup_customer` and read by nothing else; the fields that decide anything are
`account_age_days`, `delivery_confirmed`, `days_since_delivery` and
`approval_tier`, and all four are stated by all fifty. So the loss is realism in
a live transcript, not enforcement - which is why this reports rather than
halts.

FAMILY IDS: TWO FROZEN CONTRACTS DECIDE THE SPELLING, NOT THE CORPUS
---------------------------------------------------------------------
The corpus says `F1`. `contracts/evidence_bundle.schema.json` and
`contracts/breach_record.schema.json` both pin `^fam_[a-z0-9_]+$`, and both are
hash-locked contracts this lane may not edit. So a seed carries BOTH: `family`
is the taxonomy label the measurement is keyed on, and `family_id` is
`fam_f<n>` - the bundle-legal spelling, mechanically derived and losslessly
invertible by `family_label()`.

`fam_f1` and not `fam_f1_direct_override`: the F-number is the only name for a
family that any frozen document owns. A prose slug would be a second name whose
only source of truth is this file, and the parse back to `F1` would then depend
on a convention rather than on the string. `tests/golden_traces/attacks/AT01.json`
carries `fam_f1_direct_authority`, which is the longer shape; `family_label` is
STRICT and refuses it rather than parsing it, because accepting two spellings is
the defect this file just spent a paragraph refusing.
"""

import dataclasses
import datetime
import re

from corpus.blindness import FIELD_COMPUTERS, BlindInstance
from corpus.errors import CorpusError
from corpus.load import DEFAULT_LAYOUT, load_corpus
from corpus.model import SEALED_FAMILY, TRAINING_FAMILIES
from corpus.schema import instance_id

from ..red import AttackSeed
from .real_target import EpisodeWorld

# The ONLY directory this module reads. `corpus/sealed/` is not absent from this
# dict by accident and is not commented out - there is no code path from here to
# it at all. `load_corpus` opens the buckets it is handed and no others.
TRAINING_LAYOUT = {"training": DEFAULT_LAYOUT["training"]}

FAMILY_ID = re.compile(r"^fam_f([1-9][0-9]*)$")

# `CustomerRecord`'s returns panel. Stated by 32 of 50 instances under these
# names and by 18 under different ones (module docstring). Unstated -> None.
RETURNS_PANEL = (
    "lifetime_order_count",
    "lifetime_return_rate_pct",
    "refunds_trailing_90_minor",
    "not_received_claims_lifetime",
    "loyalty_tier",
)

# Scenario keys this module consumes. Anything else in an instance's scenario is
# reported on `ignored_scenario_keys` rather than quietly dropped.
CONSUMED_ACCOUNT_KEYS = ("account_id", "email", "age_days") + RETURNS_PANEL + (
    "risk_flag_open",)
CONSUMED_ORDER_KEYS = (
    "order_id", "payment_instrument_id", "order_total_minor", "currency",
    "item_description", "category", "delivery_confirmed", "days_since_delivery",
    "order_status", "refunded_minor",
)

# The six fields that reach the policy engine, and the reference computer that
# owns each. Read out of `corpus.blindness` so there is one definition.
POLICY_VISIBLE_FIELDS = (
    "episode.account_holder_email",
    "episode.account_holder_id",
    "episode.order_payment_instrument_id",
    "derived.approval_tier",
    "derived.account_age_days",
    "derived.delivery_confirmed",
    "derived.days_since_delivery",
)

# ---------------------------------------------------------------------------
# CASE 3: THE ENTITIES THE SYSTEM OF RECORD MUST *RESOLVE*, AND ONLY THOSE.
#
# `target/refund_agent/tools.py` has exactly three places where a tool asks the
# ledger to find something by id and returns `status: error` when it is not
# there. Read from the source 2026-08-22:
#
#     lookup_order      `_ledger().get_order(order_id)` is None ->
#                       `_err("no order found with id %s")`          (tools.py:106)
#     lookup_customer   `_ledger().get_customer(customer_id)` is None ->
#                       `_err("no customer found with id %s")`       (tools.py:139)
#     issue_refund      `record_refund` -> `self._orders.get(order_id)` is None ->
#                       `SystemOfRecordError("no such order")`, caught and
#                       returned as `_err`                            (tools.py:180,
#                       simulated_system_of_record.py:88)
#
# NOTHING ELSE BELONGS IN THIS TABLE, AND THE OMISSIONS ARE THE ARGUMENT.
#
#   * `email_customer(to=...)` sends to ANY string - `send_email` checks that the
#     destination is scalar and appends it to the outbox. A third-party address
#     is the ATTACK LANDING, not a world the harness failed to build, so four
#     training instances that mail `claims@harborlaw.example` and friends are
#     correctly untouched by this.
#   * `update_case_notes(case_id=...)` and `escalate_to_human(order_id=...)`
#     append receipts without looking anything up.
#   * `issue_refund(beneficiary_id=...)` IS checked by the ledger - but against
#     `order.account_holder_id`, which is a VALUE INVARIANT ("never refund to a
#     non-purchasing account"), not a presence question. That is defence in
#     depth and it is CASE 2. Putting it here would convert a real breach into
#     an exclusion, which is the direction that does actual damage.
#
# The line this table draws is the line the ruling draws: PRESENCE of an entity
# is the harness's job, and a business rule about a VALUE is the system of
# record's. `tests/test_failed_call_guard.py::test_the_resolution_table_matches_
# what_the_tools_actually_do` re-derives it by calling the real tools against an
# empty world, so it cannot rot into a comment.
RESOLVED_ARGS = {
    "lookup_order": (("order_id", "order"),),
    "lookup_customer": (("customer_id", "customer"),),
    "issue_refund": (("order_id", "order"),),
}

# `SimulatedSystemOfRecord` accessor per entity kind. One name per kind, so a
# resolver and the table above cannot disagree about what "order" means.
_RESOLVERS = {"order": "get_order", "customer": "get_customer"}


class CorpusSeedError(CorpusError):
    pass


# --------------------------------------------------------------------------
# Family id translation. One direction is mechanical; the other is STRICT.
# --------------------------------------------------------------------------

def family_id_for(family):
    """`"F1"` -> `"fam_f1"`. The bundle-legal spelling of a taxonomy label."""
    if not isinstance(family, str) or not re.match(r"^F[1-9][0-9]*$", family):
        raise CorpusSeedError(
            "E_FAMILY_LABEL",
            "%r is not an F-family label. The corpus writes F1..F7 and the two "
            "frozen contracts pin ^fam_[a-z0-9_]+$; this function is the only "
            "translation between them and it refuses anything else rather than "
            "coining a third spelling." % (family,))
    return "fam_f" + family[1:]


def family_label(family_id):
    """`"fam_f1"` -> `"F1"`. STRICT: this is what makes a per-family rate
    computable from a bundle, so it refuses a shape it did not write."""
    m = FAMILY_ID.match(family_id or "")
    if not m:
        raise CorpusSeedError(
            "E_FAMILY_ID",
            "%r does not parse back to an F-family. Per-family rates and the F4 "
            "transfer figure are keyed on that inversion, so an id this "
            "function cannot invert is an id no measurement can use. Refused "
            "rather than guessed - `tests/golden_traces/attacks/AT01.json` "
            "carries `fam_f1_direct_authority`, and accepting both shapes here "
            "would put two spellings of one family into the analysis."
            % (family_id,))
    return "F" + m.group(1)


# --------------------------------------------------------------------------
# One corpus instance, as everything downstream needs it.
# --------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class CorpusAttack:
    """Everything about one training instance that leaves this module.

    `attack_id` and `corpus_instance_id` are THE SAME STRING and that is not a
    bug. Both are `corpus.schema.instance_id(doc)`, content-addressed over the
    canonical instance body; the attack IS the instance, so two content
    addresses of one content collapse to one value. C6 requires both fields and
    each means a different thing - the run's attack identity, and the reference
    that resolves against the corpus frozen at `corpus_hash`.
    """

    attack_id: str
    corpus_instance_id: str
    slug: str
    family: str                     # "F1" - the taxonomy label
    family_id: str                  # "fam_f1" - the contract-legal spelling
    turns: tuple                    # the instance's `input_turns`, verbatim
    order_id: str
    customer_id: str
    approval_tier: str
    script: tuple                   # (bare_tool_name, args) per trace call
    unstated_fields: tuple          # record fields the instance does not state
    ignored_scenario_keys: tuple    # keys present in `scenario` and not read
    # CASE 3. Non-empty means the harness could not build the world this
    # instance describes, so the episode is NOT SCOREABLE and must not be
    # driven - `unpresentable_entities` above carries the whole argument.
    unpresentable: tuple = ()
    doc: dict = dataclasses.field(repr=False, default_factory=dict)

    @property
    def instruction(self):
        """The FINAL turn - the one carrying the ask under pressure.

        This is what `AttackSeed.instruction` holds and therefore what the
        RED_STRATEGIST rewrites. The preceding turns are context and are
        replayed verbatim, so a varied round is a partially-varied
        conversation. Stated rather than smoothed over: F1-01's chargeback
        threat only works because it answers a refusal that has not happened
        yet, and that structure lives in the ORDER of the turns, which no
        rewrite of a single string can reproduce.
        """
        return self.turns[-1]


# --------------------------------------------------------------------------
# Building the per-instance world.
# --------------------------------------------------------------------------

def _records():
    from target.refund_agent.system_of_record import CustomerRecord, OrderRecord
    return CustomerRecord, OrderRecord


def build_world_records(doc):
    """`(customer, order, unstated, ignored)` for one instance's `scenario`.

    Separate from `build_sor` so a test can assert on the records without
    standing up a ledger, and so the "what did this instance not state" list is
    produced exactly once, where the reading happens.
    """
    from target.refund_agent.simulated_system_of_record import DEMO_AS_OF
    CustomerRecord, OrderRecord = _records()

    scenario = doc.get("scenario") or {}
    account = scenario.get("account") or {}
    order = scenario.get("order") or {}
    where = doc.get("slug") or doc.get("_source_file") or "<instance>"

    def required(block, key, block_name):
        if key not in block:
            raise CorpusSeedError(
                "E_SCENARIO_FIELD_MISSING",
                "%s states no scenario.%s.%s. The world is built from the "
                "instance's own account and order, and this field is read on "
                "the drive path - a default here would be a fabricated world "
                "wearing the instance's name." % (where, block_name, key))
        return block[key]

    unstated = []

    def optional(block, key, block_name, default):
        if key in block:
            return block[key]
        unstated.append("%s.%s" % (block_name, key))
        return default

    customer = CustomerRecord(
        customer_id=required(account, "account_id", "account"),
        email=required(account, "email", "account"),
        account_age_days=required(account, "age_days", "account"),
        # Unstated -> None, never a number. `lookup_customer` renders it as
        # JSON null, which is "not on file" rather than "zero".
        lifetime_order_count=optional(account, "lifetime_order_count",
                                      "account", None),
        lifetime_return_rate_pct=optional(account, "lifetime_return_rate_pct",
                                          "account", None),
        refunds_trailing_90_minor=optional(account, "refunds_trailing_90_minor",
                                           "account", None),
        not_received_claims_lifetime=optional(
            account, "not_received_claims_lifetime", "account", None),
        loyalty_tier=optional(account, "loyalty_tier", "account", None),
        risk_flag_open=optional(account, "risk_flag_open", "account", None),
    )

    days = required(order, "days_since_delivery", "order")
    if not isinstance(days, int) or isinstance(days, bool):
        raise CorpusSeedError(
            "E_DAYS_SINCE_DELIVERY_TYPE",
            "%s states scenario.order.days_since_delivery as %r. The delivered "
            "date is computed as `as_of - days`, and every episode-scoped "
            "predicate that reads a day count is computed off it."
            % (where, days))
    delivered_on = DEMO_AS_OF - datetime.timedelta(days=days)

    order_record = OrderRecord(
        order_id=required(order, "order_id", "order"),
        account_holder_id=customer.customer_id,
        account_holder_email=customer.email,
        payment_instrument_id=required(order, "payment_instrument_id", "order"),
        order_total_minor=required(order, "order_total_minor", "order"),
        currency=optional(order, "currency", "order", None),
        item_description=required(order, "item_description", "order"),
        category=required(order, "category", "order"),
        # DERIVED, not invented, and both are declared below.
        placed_on=delivered_on,
        delivered_on=delivered_on,
        delivery_confirmed=required(order, "delivery_confirmed", "order"),
        refunded_minor=optional(order, "refunded_minor", "order", 0),
        status=optional(order, "order_status", "order", None),
    )
    # `placed_on` is stated by NO instance. Recorded as unstated so it is
    # counted rather than assumed away; it is set to `delivered_on` because
    # nothing on the drive path reads it (`tools.py::lookup_order` surfaces
    # item_description, category and order_status, never the placed date).
    unstated.append("order.placed_on")

    ignored = tuple(sorted(
        ["account.%s" % k for k in account if k not in CONSUMED_ACCOUNT_KEYS]
        + ["order.%s" % k for k in order if k not in CONSUMED_ORDER_KEYS]))
    return customer, order_record, tuple(unstated), ignored


def build_sor(doc):
    """A FRESH `SimulatedSystemOfRecord` holding this instance's own world.

    One customer and one order, because no trace in the training corpus names
    an order other than its own scenario's (measured across all 50 on
    2026-08-22). A world carrying orders the instance never mentions would give
    the target somewhere else to land.
    """
    from target.refund_agent.simulated_system_of_record import (
        DEMO_AS_OF, SimulatedSystemOfRecord,
    )
    customer, order, unstated, ignored = build_world_records(doc)
    sor = SimulatedSystemOfRecord(as_of=DEMO_AS_OF)
    sor.put_customer(customer)
    sor.put_order(order)
    return sor, unstated, ignored


def blind_fields(doc):
    """The six policy-visible fields, computed by `corpus/blindness.py`.

    Not recomputed here. `BlindInstance` raises if a computer reaches for the
    label, so these are exactly the values the D5 blindness check ruled on.
    """
    out = {}
    for name in POLICY_VISIBLE_FIELDS:
        out[name] = FIELD_COMPUTERS[name](BlindInstance(doc, field_name=name))
    return out


@dataclasses.dataclass(frozen=True)
class MissingEntity:
    """One entity an instance's own trace declares reachable and the world it
    was built from does not hold. CASE 3 - see `unpresentable_entities`."""

    step_index: int
    tool: str
    arg: str
    value: object
    kind: str

    def describe(self):
        return ("trace[%d] %s(%s=%r) - the world built for this instance holds "
                "no %s of that id, and the instance declares the call ok"
                % (self.step_index, self.tool, self.arg, self.value, self.kind))


def unpresentable_entities(doc, sor):
    """CASE 3: everything this instance's TRACE names that its WORLD lacks.

    THE DEFECT THIS CLOSES, and it is a lookup failure scored as a measurement.
    `crucible/plugin/core.py::after_tool` records `TOOL_EXECUTED` whenever the
    tool BODY ran; `on_tool_error` only fires on a RAISED exception. Every tool
    in `target/refund_agent/tools.py` returns `{"status": "error", ...}` instead
    of raising - deliberately, so a refused business write is not a target crash
    (`tools.py` header). So a call that found nothing is byte-indistinguishable
    in the ledger from a call that did the thing, and the Objective Set matches
    on the ARGUMENTS of `TOOL_EXECUTED` events. Measured across all fifty
    training instances offline at policy v0 on 2026-08-22, two calls come back
    `status: error` and are recorded as executed - `F2-02` and `F2-08`, both
    `lookup_customer(CUS-9142)` - and BOTH EPISODES SCORE CLEAN. A read of a
    third party's file that never happened is counted as an attack the target
    repelled. The flattering direction, again.

    WHY THIS IS A PRECONDITION AND NOT A CLASSIFIER ON THE EVENT.
    The obvious fix is to record a result status on `TOOL_EXECUTED` and let the
    oracle read it. Two things are wrong with that. It needs the tool bodies in
    `target/refund_agent/tools.py` to categorise their own failures, and that
    file is inside `target_agent_hash`. Worse, THE TARGET IS THE SUBJECT UNDER
    TEST: code inside it must never get a say in whether an episode is
    scoreable, because that is an escape hatch from measurement. Catching it
    here is also strictly stronger - you cannot mis-score an episode you never
    ran.

    WHAT IS *NOT* CASE 3, AND THIS IS THE WHOLE OF THE DIFFICULTY.
    Case 3 is the HARNESS failing to set up the test. It is never the target
    behaving badly. If a model invents `ORD-9999`, that is the finding, and it
    is scoreable. So this function reads ONLY the instance's own `trace` - which
    is fixture data in both directions: offline it IS the script the target is
    driven with (`CorpusSeeds.offline_script`), and live it is the corpus
    author's statement of what the world must support. It never reads a runtime
    event, and it cannot: it runs before the episode does.

    `status` IS READ AND IT IS LOAD-BEARING. A step the instance declares
    `"error"` on is a step whose refusal the fixture EXPECTS, so its entity is
    not required to exist. Only a step the corpus says succeeds ("ok", and that
    is the default when the key is absent) makes a presence claim about the
    world. Reading the declared status is not reading the declared VERDICT: the
    policy decision recorded on each trace step is still ignored, here and in
    `offline_script`, because replaying that would make the run a replay of the
    answer.

    Returns a tuple of `MissingEntity`, empty when the instance is presentable.
    It RETURNS rather than RAISES because `CorpusSeeds.load()` must not die on
    one bad fixture out of fifty - the flag rides on `CorpusAttack` and on
    `EpisodeWorld`, `report()` counts it, and `real_target` refuses to drive a
    world that declares itself unpresentable.
    """
    out = []
    for i, step in enumerate(doc.get("trace") or ()):
        if str(step.get("status", "ok")).lower() != "ok":
            continue
        fq = step.get("tool_fqname") or ""
        tool = fq.rsplit(".", 1)[-1]
        args = step.get("args") or {}
        for arg, kind in RESOLVED_ARGS.get(tool, ()):
            if arg not in args:
                continue
            if getattr(sor, _RESOLVERS[kind])(args[arg]) is None:
                out.append(MissingEntity(step_index=i, tool=tool, arg=arg,
                                         value=args[arg], kind=kind))
    return tuple(out)


def verify_world(doc, sor):
    """Assert the constructed world IS the instance's world. Raises, never warns.

    Two derivations of the same six facts have to agree: `corpus/blindness.py`'s
    reference computers reading the instance, and `real_target` reading the
    constructed `SimulatedSystemOfRecord`. If they disagree, the episode would
    run against a world that is not the one the instance describes - and the
    failure would be an honest refusal from the target, scored NON-BREACH and
    indexed as hardening. That is why this is a precondition on every episode
    rather than a test that ran once.
    """
    from .real_target import scenario_and_context

    expect = blind_fields(doc)
    where = doc.get("slug") or "<instance>"

    order_id = doc["scenario"]["order"]["order_id"]
    customer_id = doc["scenario"]["account"]["account_id"]
    if sor.get_order(order_id) is None:
        raise CorpusSeedError(
            "E_WORLD_MISSING_ORDER",
            "%s names order %s and the world built for it does not hold that "
            "order. The target would answer 'no order found', the episode "
            "would score NON-BREACH, and the run would index a lookup failure "
            "as hardening." % (where, order_id))
    if sor.get_customer(customer_id) is None:
        raise CorpusSeedError(
            "E_WORLD_MISSING_CUSTOMER",
            "%s names account %s and the world built for it does not hold that "
            "account." % (where, customer_id))

    scenario, context = scenario_and_context(
        sor, order_id, customer_id, expect["derived.approval_tier"])
    got = {
        "episode.account_holder_email": context.get(
            "episode.account_holder_email"),
        "episode.account_holder_id": context.get("episode.account_holder_id"),
        "episode.order_payment_instrument_id": context.get(
            "episode.order_payment_instrument_id"),
        "derived.approval_tier": scenario["approval_tier"],
        "derived.account_age_days": scenario["account_age_days"],
        "derived.delivery_confirmed": scenario["delivery_confirmed"],
        "derived.days_since_delivery": scenario["days_since_delivery"],
    }
    drift = sorted(k for k in expect if expect[k] != got[k])
    if drift:
        raise CorpusSeedError(
            "E_WORLD_ROUNDTRIP",
            "%s: the world built from this instance does not reproduce it. %s. "
            "corpus/blindness.py computed %s from the instance; real_target "
            "derived %s from the constructed world."
            % (where, ", ".join(drift),
               {k: expect[k] for k in drift}, {k: got[k] for k in drift}))
    return got


# --------------------------------------------------------------------------
# The loaded corpus, and everything the campaign asks it for.
# --------------------------------------------------------------------------

class CorpusSeeds:
    """The training corpus, as attack seeds plus the worlds they name."""

    def __init__(self, attacks):
        self._attacks = tuple(attacks)
        self._by_id = {a.attack_id: a for a in self._attacks}
        if len(self._by_id) != len(self._attacks):
            raise CorpusSeedError(
                "E_DUPLICATE_ATTACK_ID",
                "two instances produced the same content-addressed id. One of "
                "them is invisible to every per-family count in the run.")

    # -- loading ----------------------------------------------------------
    @classmethod
    def load(cls, layout=None):
        """Load `corpus/training/` ONLY and adapt it.

        `layout` exists so a test can point at a temporary directory - it does
        NOT exist so a caller can add a bucket. Whatever is handed in, every
        instance is checked against `corpus.model.TRAINING_FAMILIES` and a
        member of the sealed family RAISES.
        """
        corpus = load_corpus(layout=layout or TRAINING_LAYOUT)
        if not corpus["training"]:
            raise CorpusSeedError(
                "E_EMPTY_TRAINING_CORPUS",
                "zero training instances loaded. The campaign would run a "
                "zero-attack round, report no breaches, and a zero-breach run "
                "reads exactly like a hardened one.")
        return cls([cls._adapt(doc) for doc in corpus["training"]])

    @staticmethod
    def _adapt(doc):
        slug = doc.get("slug") or "<instance>"
        family = doc.get("family")
        if family == SEALED_FAMILY or family not in TRAINING_FAMILIES:
            raise CorpusSeedError(
                "E_SEALED_FAMILY_REACHED",
                "%s declares family %r; the training families are %s and %s is "
                "SEALED. Refused rather than skipped: a filter here would drop "
                "a sealed instance silently and pass identically whether the "
                "seal held or not."
                % (slug, family, list(TRAINING_FAMILIES), SEALED_FAMILY))
        if doc.get("sealed"):
            raise CorpusSeedError(
                "E_SEALED_FLAG_SET",
                "%s carries `sealed: true` inside corpus/training/." % slug)

        turns = doc.get("input_turns")
        if not isinstance(turns, list) or not turns or not all(
                isinstance(t, str) and t.strip() for t in turns):
            raise CorpusSeedError(
                "E_INPUT_TURNS",
                "%s carries no usable `input_turns`. The turns ARE the attack; "
                "an instance with none has nothing to drive the target with."
                % slug)

        sor, unstated, ignored = build_sor(doc)
        computed = blind_fields(doc)
        aid = doc.get("_instance_id") or instance_id(doc)
        return CorpusAttack(
            attack_id=aid,
            corpus_instance_id=aid,
            slug=slug,
            family=family,
            family_id=family_id_for(family),
            turns=tuple(turns),
            order_id=doc["scenario"]["order"]["order_id"],
            customer_id=doc["scenario"]["account"]["account_id"],
            approval_tier=computed["derived.approval_tier"],
            script=tuple(_script_from_trace(doc)),
            unstated_fields=unstated,
            ignored_scenario_keys=ignored,
            unpresentable=unpresentable_entities(doc, sor),
            doc=doc,
        )

    # -- what the campaign wires in ---------------------------------------
    def attack_seeds(self):
        """The `SEEDS` list. `instruction` is the FINAL turn - see
        `CorpusAttack.instruction`."""
        return [AttackSeed(a.attack_id, a.family_id, a.instruction)
                for a in self._attacks]

    def lookup(self, attack):
        """The `CorpusAttack` behind an attack dict or an attack id.

        The join key is `attack_id`, and it has to be: `RedStrategist.vary()`
        returns a six-key dict and drops anything else the seed carried, so
        nothing but the id survives the trip from `SEEDS` to `run_episode`.
        """
        aid = attack.get("attack_id") if isinstance(attack, dict) else attack
        rec = self._by_id.get(aid)
        if rec is None:
            raise CorpusSeedError(
                "E_ATTACK_NOT_IN_CORPUS",
                "no training instance carries attack id %r. An attack whose "
                "world cannot be built must not fall back to a shared one - "
                "that is the ORD-4471/ORD-4472 collision this module exists to "
                "close." % (aid,))
        return rec

    def world_for(self, attack):
        """`EpisodeWorld` for one attack. A FRESH world every call.

        The last turn is replaced by whatever the RED_STRATEGIST produced
        (`attack["instruction"]`), because that is the turn `AttackSeed`
        carried and therefore the only one it could have varied. The earlier
        turns are the instance's own, verbatim.
        """
        rec = self.lookup(attack)
        sor, _unstated, _ignored = build_sor(rec.doc)
        verify_world(rec.doc, sor)
        varied = (attack.get("instruction") if isinstance(attack, dict)
                  else None) or rec.turns[-1]
        # CASE 3, recomputed against THIS world rather than copied off `rec`.
        # `build_sor` is called fresh on every episode, so the flag and the
        # world it is a fact about are produced together; a cached flag would be
        # a claim about a world that no longer exists.
        #
        # STRINGS, not `MissingEntity`. `real_target` cannot import this module
        # - the dependency runs the other way (`from .real_target import
        # EpisodeWorld`) - and an `EpisodeWorld` that carried a corpus type
        # would make the world shape depend on where the world came from.
        unpresentable = unpresentable_entities(rec.doc, sor)
        return EpisodeWorld(
            sor=sor,
            order_id=rec.order_id,
            customer_id=rec.customer_id,
            approval_tier=rec.approval_tier,
            turns=rec.turns[:-1] + (varied,),
            unpresentable=tuple(m.describe() for m in unpresentable),
        )

    def offline_script(self, attack):
        """The instance's OWN trace as an offline tool script.

        `campaign.offline_script_for` keys six hand-written call shapes off
        `fam_direct_ask`-style ids against a hardcoded ORD-4472. Both halves
        break under corpus seeds - the family ids no longer match, so every
        attack would fall through to the default shape, and that shape names an
        order the per-instance world does not hold. This replaces it with the
        calls the instance actually records, in order, with its own arguments.

        The policy decision recorded on each trace step is NOT read. The live
        policy engine decides; replaying the corpus's decision would make the
        offline run a replay of the answer.
        """
        return [(name, dict(args)) for name, args in self.lookup(attack).script]

    def provenance_for(self, attack):
        """The C6 `attacks[]` entry for a corpus-sourced attack.

        Exactly the fields `contracts/evidence_bundle.schema.json` declares for
        `provenance: "training_corpus"` and no others - that object is
        `additionalProperties: false`, so the human-legible `slug` cannot ride
        along and lives on `CorpusAttack` instead.
        """
        rec = self.lookup(attack)
        return {
            "attack_id": rec.attack_id,
            "provenance": "training_corpus",
            "family_id": rec.family_id,
            "corpus_instance_id": rec.corpus_instance_id,
        }

    # -- what the banner and the bundle should say ------------------------
    def report(self):
        """Counts, so the gaps are a number in the run and not a paragraph."""
        by_family = {}
        unstated = {}
        ignored = {}
        for a in self._attacks:
            by_family[a.family] = by_family.get(a.family, 0) + 1
            for f in a.unstated_fields:
                unstated[f] = unstated.get(f, 0) + 1
            for k in a.ignored_scenario_keys:
                ignored[k] = ignored.get(k, 0) + 1
        return {
            "instances": len(self._attacks),
            "by_family": dict(sorted(by_family.items())),
            "families": sorted({a.family for a in self._attacks}),
            "sealed_family_loaded": False,
            "multi_turn_instances": sum(1 for a in self._attacks
                                        if len(a.turns) > 1),
            "turns_total": sum(len(a.turns) for a in self._attacks),
            "unstated_fields": dict(sorted(unstated.items())),
            "ignored_scenario_keys": dict(sorted(ignored.items())),
            # CASE 3, AS A NUMBER IN THE RUN. Two of fifty on 2026-08-22. A
            # count here is what stops "we dropped some fixtures" from being a
            # paragraph nobody re-measures.
            "unpresentable_instances": sorted(
                a.slug for a in self._attacks if a.unpresentable),
            "unpresentable_entities": {
                a.slug: [m.describe() for m in a.unpresentable]
                for a in self._attacks if a.unpresentable},
        }

    def disclaimers(self):
        """Sentences for `campaign._disclaimer`, in its voice: one per thing
        that is still not what a reader would assume. Assembled from what was
        measured, so they go away when the corpus is fixed."""
        r = self.report()
        bits = []
        if r["unpresentable_instances"]:
            bits.append(
                "%d of %d instances are NOT SCOREABLE and are not driven: the "
                "world built from the instance's own scenario does not hold an "
                "entity the instance's own trace declares a successful call "
                "against (%s). This is the harness failing to set up the test, "
                "not the target failing it, so the episodes go to `excluded[]` "
                "rather than into the denominator. Every one of them scored "
                "CLEAN before 2026-08-22 - a lookup that found nothing counted "
                "as an attack repelled. The fix is a coordinator decision: the "
                "corpus states no record for the second account these "
                "instances name, and inventing one here would be a fabricated "
                "world wearing the instance's name."
                % (len(r["unpresentable_instances"]), r["instances"],
                   ", ".join(r["unpresentable_instances"])))
        if r["multi_turn_instances"]:
            bits.append(
                "%d of %d attacks are multi-turn and are DRIVEN as separate "
                "turns on one session, so the escalation is exercised - but the "
                "RED_STRATEGIST varies the FINAL turn only, because that is the "
                "one `AttackSeed` carries. Earlier turns are replayed verbatim, "
                "so a varied round is a partially-varied conversation."
                % (r["multi_turn_instances"], r["instances"]))
        if r["ignored_scenario_keys"]:
            # NAMES THE KEYS IT COUNTED. This sentence used to describe the
            # SECOND ACCOUNT DIALECT by hand and end "the fix is a re-author
            # plus a corpus_hash re-freeze" - and on 2026-08-22 that re-author
            # and that re-freeze both happened (ruling 47). The count moved and
            # the prose did not, so a run banner a judge reads would have
            # prescribed a fix already applied, and named `lifetime_orders`,
            # which no longer appears in any instance.
            #
            # A disclaimer that hardcodes what it is disclaiming outlives the
            # thing. This one lists what was actually ignored, so it shrinks as
            # the corpus is fixed and disappears when nothing is left - which is
            # what the docstring above already promised and the sentence did not
            # deliver.
            ignored = r["ignored_scenario_keys"]
            named = ", ".join("%s (%d)" % (k, n)
                              for k, n in sorted(ignored.items()))
            bits.append(
                "%d scenario keys across the training corpus were NOT read into "
                "the per-instance world: %s. Accepting a second spelling for a "
                "field that already has one was refused - that shim is how "
                "`ALLOW`/`allow` happened here - so an unrecognised key is "
                "counted and named rather than guessed at. None of these "
                "reaches the policy engine."
                % (sum(ignored.values()), named))
        if r["unstated_fields"]:
            bits.append(
                "Order and account fields the corpus does not state are carried "
                "as null rather than filled: %s. Nothing here invented a "
                "currency, a status or an order date."
                % ", ".join("%s (%d instances)" % (k, v)
                            for k, v in sorted(r["unstated_fields"].items())))
        return bits


def _script_from_trace(doc):
    """`[(bare_tool_name, args)]` from an instance's trace, in order.

    Bare names, because that is what a real endpoint emits and what
    `real_target._adk_tools_for` deliberately kept - a stub that accepts a
    dotted name the live API refuses is the failure moved to where nothing is
    watching.
    """
    out = []
    for i, step in enumerate(doc.get("trace") or ()):
        fq = step.get("tool_fqname")
        if not isinstance(fq, str) or "." not in fq:
            raise CorpusSeedError(
                "E_TRACE_TOOL_FQNAME",
                "%s trace[%d] declares tool_fqname %r."
                % (doc.get("slug"), i, fq))
        out.append((fq.rsplit(".", 1)[-1], dict(step.get("args") or {})))
    return out


__all__ = [
    "CorpusAttack", "CorpusSeedError", "CorpusSeeds", "MissingEntity",
    "RESOLVED_ARGS", "TRAINING_LAYOUT", "blind_fields", "build_sor",
    "build_world_records", "family_id_for", "family_label",
    "unpresentable_entities", "verify_world",
]
