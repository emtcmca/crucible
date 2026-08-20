"""strawman_policy.py - DELIBERATELY WRONG enforcement implementations, kept in
the tree forever.

Not dead code, not drafts, not leftovers. These are the proof that
`tests/l3_checks.py` CAN FAIL. `CONVENTIONS.md` section 8 rule 2: a check that
cannot fail is not measuring anything. The precedent and its incident are in
`tests/strawman_canon.py` - L1's first strawman claim about WHICH vector it
failed was FALSE, and only running the meta-check caught it. Every reason string
below was written AFTER observing the actual failure, not before.

EACH STRAWMAN IS WRONG IN EXACTLY ONE PLACE. That is what makes it evidence
about one property rather than a general mess that happens to fail everything.
Six of the seven subclass the real implementation and override a single method;
the two that cannot (the permissive parser and the schema-only validator) wrap
it instead.

WHY THESE SEVEN AND NOT SEVEN OTHERS. Each is the implementation a competent
engineer writes from the schema alone, without the ruling that says otherwise:

  set equality           - "the rule names a class, the call has classes, compare them"
  first match wins       - the way nearly every ACL, firewall, and .gitignore works
  whole prefix           - "the episode prefix is the episode prefix"
  sum over the prefix    - "an aggregate over prior events" reads as excluding the current one
  merge on conflict      - dict.update, the single most common way to combine two dicts
  jsonschema and nothing - the entire point of having a schema
  first class of A|B     - be liberal in what you accept

Not one of them is a strawman in the pejorative sense. Every one is what the
code would say today if the corresponding ruling had never been written down.
"""


# The sentinel a reason carries until the real failure has been OBSERVED.
# `test_no_strawman_claim_is_still_a_placeholder` fails while one is present.
UNOBSERVED = "<<UNOBSERVED>>"


# --------------------------------------------------------------------------
# Engine strawmen. Each overrides ONE seam on the real PolicyEngine.
# --------------------------------------------------------------------------

def _equality_engine_factory():
    from crucible.policy.engine import PolicyEngine

    class EqualityMatchEngine(PolicyEngine):
        """Matches when the rule's class EQUALS the call's capability set.

        The reading `architecture-spec.md` section 5.4 step 1 and its own r019
        comment disagreed about, resolved by ruling 22 on the merits because
        precedence could not settle an intra-document conflict.
        """

        def match_rules(self, capability_set, tool_handle):
            out = []
            for r in self._rules:
                m = r.get("match", {})
                if {m.get("capability_class")} != set(capability_set):
                    continue
                names = m.get("tool_names") or []
                if names and tool_handle not in names:
                    continue
                out.append(r)
            return out

    return lambda pol: EqualityMatchEngine(pol)


def _file_order_engine_factory():
    from crucible.policy.engine import PolicyEngine

    class FileOrderEngine(PolicyEngine):
        """First rule in the array that produces an effect wins.

        How an ACL, a firewall chain, and `.gitignore` all work, which is
        exactly why it is the wrong answer here and why it needed a rule of its
        own: file order carries no semantics in C4, so a patch must not be able
        to change behaviour by insertion position.
        """

        def resolve(self, effects):
            from crucible.policy.decision import Decision
            for eff in effects:
                return Decision(eff.outcome, eff.rule_id, eff.reason_code)
            return Decision("ALLOW")

    return lambda pol: FileOrderEngine(pol)


def _unfiltered_prefix_engine_factory():
    from crucible.policy.engine import PolicyEngine

    class UnfilteredPrefixEngine(PolicyEngine):
        """The episode prefix is the episode prefix - all of it.

        Which hands an attacker `preceded_by` for free: make the call you know
        will be denied, and the precondition is satisfied by the denial.
        """

        def visible_prefix(self, episode_prefix):
            return tuple(episode_prefix or ())

    return lambda pol: UnfilteredPrefixEngine(pol)


def _sum_excludes_pending_engine_factory():
    from crucible.policy.engine import PolicyEngine

    class SumExcludesPendingEngine(PolicyEngine):
        """`episode_sum` over the prefix only.

        The natural reading of "aggregate over this episode's prefix", and it
        makes the rule fire exactly one call too late - which for a
        salami-slicing family is the one call that matters.
        """

        def episode_sum(self, arg_path, visible_prefix, pending_args):
            return self._sum_over(arg_path, visible_prefix)

    return lambda pol: SumExcludesPendingEngine(pol)


# --------------------------------------------------------------------------
# Episode strawman.
# --------------------------------------------------------------------------

def _mutable_episode_factory():
    from crucible.policy.episode import EpisodeContext

    class MutableEpisodeContext(EpisodeContext):
        """Accepts a later write and merges it.

        The version somebody writes when `episode.*` looks like ordinary
        session state. It does not raise, so nothing downstream can tell a
        scenario where the account holder's address really is X from one where
        the attacker said so - and every `to == episode.account_holder_email`
        rule is defeated by editing the right-hand side.
        """

        def attempt_write(self, name, value):
            self._fields[self._qualify(name)] = value
            return None

    return lambda facts, schema: MutableEpisodeContext.freeze(
        facts, derived_schema=schema)


# --------------------------------------------------------------------------
# Stamper strawman.
# --------------------------------------------------------------------------

def _merging_stamper_factory():
    from crucible.plugin.stamper import DerivedStamper

    class MergingStamper(DerivedStamper):
        """`dict.update` semantics: the model's value wins where it supplied one.

        The most common way there is to combine two dicts, and it makes the
        agent able to assert that the harness verified something it did not.
        """

        def stamp(self, tool_args, context=None):
            post = dict(tool_args)
            for name in self.declared:
                if name not in post:
                    post[name] = self._compute(name, tool_args, context)
            return post, []

    return lambda schema, compute: MergingStamper(schema, compute=compute)


# --------------------------------------------------------------------------
# Parser strawman. Wraps rather than subclasses - `parse_rule` is a function.
# --------------------------------------------------------------------------

def _permissive_parse_rule(text):
    """Be liberal in what you accept: take the first class of `A|B`, and treat
    `UNCLASSIFIED` as just another class name.

    Both are the Postel's-law instinct applied where it does active harm.
    `cap:A|B` accepted-as-A gives the ARMORER a rule that does something other
    than what it wrote, with no parser error to repair against; and
    `cap:UNCLASSIFIED => deny` on an unseen target blocks everything and reports
    100% transfer, for free.
    """
    import re

    from crucible.dsl.parser import parse_rule as real

    t = re.sub(r"(cap:[A-Z][A-Z0-9_]*)(?:\|[A-Z][A-Z0-9_]*)+", r"\1", text)
    t = t.replace("cap:UNCLASSIFIED", "cap:CAP_MOVES_MONEY")
    return real(t)


# --------------------------------------------------------------------------
# Document-validator strawman.
# --------------------------------------------------------------------------

def _schema_only_validate_policy_document(doc):
    """Run the JSON Schema and nothing else - the whole point of having one.

    It is genuinely close to right. `additionalProperties: false` on `match`
    does catch a `match_mode` sitting in `match`, which is where anybody would
    put it. What a schema cannot reach is `provenance`, which is a free-form
    object by design (it carries per-rule autopsy IDs and proposal IDs), so a
    `match_mode` parked in there is invisible to it - and "at any depth" is not
    decoration.
    """
    import json
    import pathlib

    import jsonschema

    root = pathlib.Path(__file__).resolve().parent.parent
    schema = json.loads(
        (root / "contracts" / "policy_document.schema.json").read_text(
            encoding="utf-8"))
    jsonschema.validate(doc, schema)


def _permissive_validator_factory():
    from crucible.dsl.validator import Validator

    class UndeclaredDerivedOkValidator(Validator):
        """Treats `derived.` as a naming convention rather than a reserved,
        manifest-resolved namespace.

        The rule then compiles AND validates, which is precisely what ruling 24
        says must not happen: `derived.prior_decision_on_this_order` is
        undeclared on purpose, no corpus instance exercises it, and an
        uncheckable field has no business in a hashed artifact.
        """

        def check_derived_paths(self, parsed):
            return None

    return lambda *a, **k: UndeclaredDerivedOkValidator(*a, **k)


# --------------------------------------------------------------------------
# The register. `must_fail` names the checks each strawman MUST fail.
# Reasons are filled in from observed failures - see the module docstring.
# --------------------------------------------------------------------------

def build_strawmen(real):
    """Returns `{name: (Impl, {check_id: reason})}` given the real Impl."""
    return {
        "equality_match": (
            real.replace("equality_match",
                         make_engine=_equality_engine_factory()),
            {"N1": "matches only when the rule's class EQUALS the call's whole "
                   "capability set, so a single-class rule silently stops "
                   "firing on exactly the multi-capability tools it exists for."},
        ),
        "file_order_first_match": (
            real.replace("file_order_first_match",
                         make_engine=_file_order_engine_factory()),
            {"N4": "takes the first rule in array order that produces an "
                   "effect. The fixture places require_approval first, so the "
                   "call returns APPROVAL_REQUIRED where deny must win."},
        ),
        "unfiltered_prefix": (
            real.replace("unfiltered_prefix",
                         make_engine=_unfiltered_prefix_engine_factory()),
            {"S1": "lets a DENIED attempt and an ERRORED call satisfy "
                   "preceded_by and count toward episode_sum. An attacker gets "
                   "the precondition for free from a call he knows will fail."},
        ),
        "sum_excludes_pending": (
            real.replace("sum_excludes_pending",
                         make_engine=_sum_excludes_pending_engine_factory()),
            {"S2": "aggregates the prefix only, so 40000 spent plus a pending "
                   "20000 reads as 40000 and the call that crosses a 50000 "
                   "threshold is the one that executes."},
        ),
        "mutable_episode": (
            real.replace("mutable_episode",
                         freeze_episode=_mutable_episode_factory()),
            {"S3": "accepts a post-start write to episode.account_holder_email "
                   "and merges it, raising nothing."},
        ),
        "merging_stamper": (
            real.replace("merging_stamper",
                         make_stamper=_merging_stamper_factory()),
            {"S4": "keeps the model's derived.subject_verified_in_episode and "
                   "records no overwrite, so a forged verification survives and "
                   "leaves no evidence."},
        ),
        "permissive_parser": (
            real.replace("permissive_parser",
                         parse_rule=_permissive_parse_rule),
            {"N2": "rewrites cap:A|B to cap:A and parses it, so nothing is "
                   "refused and the ARMORER gets a rule that is not the one it "
                   "wrote.",
             "N5": "rewrites cap:UNCLASSIFIED to a real class and parses it."},
        ),
        "schema_only_validator": (
            real.replace("schema_only_validator",
                         validate_policy_document=_schema_only_validate_policy_document),
            {"N3": "OBSERVED 2026-08-20, and the observation is worth more "
                   "than the guess it replaced. It DOES refuse the KNOWN_BAD "
                   "document - but with \"'crucible-armorer@...' does not match "
                   "'^crucible-gate@'\", because that is simply the first "
                   "violation the schema walker reaches. It never mentions "
                   "match_mode, and it carries no error code, so a caller "
                   "cannot tell WHICH deleted field was found or that one was. "
                   "The half that a schema structurally cannot reach is proved "
                   "separately by "
                   "test_schema_only_validator_really_cannot_see_a_nested_"
                   "match_mode: a match_mode parked in `provenance` - a "
                   "free-form object by design - passes it cleanly."},
        ),
        "permissive_derived_validator": (
            real.replace("permissive_derived_validator",
                         make_validator=_permissive_validator_factory()),
            {"N6": "accepts a rule naming an undeclared derived.* path, so the "
                   "rule compiles AND validates - the outcome ruling 24 says "
                   "must not happen."},
        ),
    }
