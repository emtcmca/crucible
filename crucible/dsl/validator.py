"""validator.py - V1-V9 from `contracts/policy.ebnf`, plus N3, N5 and N6.

The parser decides whether the text is IN THE LANGUAGE. This file decides
whether a rule that is in the language is ADMISSIBLE, which needs three things
the parser does not have: capability manifest Part A, derived schema Part B, and
the policy the patch is being applied to.

THE SPLIT IS LOAD-BEARING, NOT TIDY. Ruling 24's exhibit turns on a rule that
COMPILES AS GRAMMAR AND REJECTS AS POLICY -
`derived.prior_decision_on_this_order` parses fine and is deliberately
undeclared, because 19.3's blindness check runs over the corpus, no instance
exercises that field, and AN UNCHECKABLE FIELD HAS NO BUSINESS IN A HASHED
ARTIFACT. If the parser resolved names against the manifest there would be no
such state to demonstrate, and the expressibility claim would read as bluster to
a judge who tested it.

The checks, and what each one is actually defending:

  V1  cap_selector present and FIRST. There is no way to write a rule that binds
      only to a tool, so EVERY LEARNED RULE GENERALIZES TO EXACTLY ONE
      CAPABILITY CLASS - the mechanism behind headline result #1.
  V2  `cap:UNCLASSIFIED` rejected explicitly (raised in the parser; re-asserted
      here so the refusal survives someone building a rule without it).
  V3  No plain-text product identifier anywhere in the rule body. Metadata and
      provenance are exempt (KB9), which is why this runs over `body_text`.
  V4  Every enum_symbol is a declared member FOR ITS EXACT arg_path.
  V5  Every tool_handle is in the manifest.
  V6  Every retract targets an `armorer:*` rule. SEED RULES ARE IRRETRACTABLE.
  V7  Zero rule bodies contain an >=8-token substring of any corpus payload.
  V8  The resulting rule set evaluates TOTAL on a synthetic call-shape sweep.
  V9  On add_rule, a hash-shaped rule_id is REJECTED.
  N3  A policy DOCUMENT containing `match_mode` at any depth is rejected.
  N6  A rule naming a `derived.*` path Part B does not declare is rejected.

ONE REFUSAL AT A TIME, AND THE ORDER MATTERS. `policy.ebnf` gives the ARMORER
exactly one repair attempt with the error as its sole feedback, so a list of
twelve simultaneous complaints is not feedback. The order is chosen so the most
specific diagnosis wins: an undeclared `derived.*` path is reported as such
rather than as "undeclared enum for that path", which is what a naive ordering
would say and which would send the repair after the wrong half of the line.
"""

import json
import pathlib
import re

from ..canon.hashing import assert_model_did_not_forge_a_rule_id
from ..canon.canonical import CanonicalizationError
from .errors import ValidationError
from .nodes import (
    CAP_CLASSES,
    CLAUSE_ARG_CMP_LITERAL,
    CLAUSE_ARG_IN_ENUM_LIST,
    CLAUSE_ARG_VS_EPISODE_CONTEXT,
    UNCLASSIFIED,
)
from .serialize import compile_rule, sort_rules

_CONTRACTS = pathlib.Path(__file__).resolve().parents[2] / "contracts"
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")

DERIVED_PREFIX = "derived."
EPISODE_PREFIX = "episode."

# V7. Eight is from `policy.ebnf` and it is not tunable here.
PAYLOAD_SUBSTRING_TOKENS = 8

# The capability vocabulary is subtracted from a harvested product lexicon: the
# six class names and the DSL's own keywords are ours, not the product's.
_DSL_VOCABULARY = frozenset(CAP_CLASSES) | frozenset({
    "rule", "retract", "cap", "tool", "when", "and", "in", "is", "absent",
    "deny", "constrain_arg", "require_approval", "origin", "seed", "armorer",
    "preceded_by", "episode_sum", "episode", "true", "false", UNCLASSIFIED,
})


# --------------------------------------------------------------------------
# Document-level validation.
# --------------------------------------------------------------------------

def find_match_mode(node, path="$"):
    """Every location of a `match_mode` key, at any depth. Returns paths."""
    hits = []
    if isinstance(node, dict):
        for k, v in node.items():
            here = "%s.%s" % (path, k)
            if k == "match_mode":
                hits.append(here)
            hits.extend(find_match_mode(v, here))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            hits.extend(find_match_mode(v, "%s[%d]" % (path, i)))
    return hits


def _schema():
    return json.loads((_CONTRACTS / "policy_document.schema.json")
                      .read_text(encoding="utf-8"))


def validate_policy_document(doc: dict) -> None:
    """Structural validation of a stored policy document. Raises ValidationError.

    THE DELETED-FIELD SCAN RUNS FIRST, BEFORE THE SCHEMA. That ordering is the
    point, not an optimization. A JSON Schema reports whichever violation its
    walker reaches first, and on the C4 KNOWN_BAD document - which is bad in six
    ways - that turns out to be `promoted_by`. It never looks at `match_mode` at
    all, so a schema-first validator can refuse the right document while
    diagnosing the wrong thing, and the ARMORER's one repair goes to the wrong
    half of the patch.

    "At any depth" is also not decoration. `additionalProperties: false` on
    `match` catches a `match_mode` sitting in `match`, which is where anybody
    would put it - but `provenance` is a free-form object by design, because it
    carries per-rule autopsy IDs and proposal IDs, and a schema cannot reach
    inside it.

    `match_mode` was DELETED rather than pinned to a constant. A field pinned to
    a constant sits inside the hashed payload INVITING THE OTHER VALUE AT 1AM,
    and the two readings were two different policies for the same stored bytes:
    under `all_of` a rule naming an empty class intersection matches NOTHING,
    EVER - the validator passes it, the benign fixtures pass BECAUSE IT NEVER
    FIRES, and the gate promotes a rule that cannot fire into the hashed policy.
    """
    hits = find_match_mode(doc)
    if hits:
        raise ValidationError(
            "E_MATCH_MODE",
            "`match_mode` was DELETED from the schema by ruling 22 and is a "
            "hard reject at any depth. Found at: %s. The stored form is a "
            "SCALAR `capability_class` and matching is MEMBERSHIP of that class "
            "in the call's capability set." % ", ".join(hits))

    try:
        import jsonschema
    except ImportError:                                    # pragma: no cover
        raise ValidationError("E_NO_VALIDATOR",
                              "jsonschema is required to validate C4 documents")
    try:
        jsonschema.validate(doc, _schema())
    except jsonschema.ValidationError as e:
        raise ValidationError(
            "E_SCHEMA",
            "%s at %s" % (e.message, "$" + "".join(
                "[%r]" % p for p in e.absolute_path))) from None

    rules = doc.get("hashed_payload", {}).get("rules", [])
    ids = [r["rule_id"] for r in rules]
    if ids != sorted(ids):
        raise ValidationError(
            "E_RULES_NOT_SORTED",
            "rules are stored PRE-SORTED BY rule_id ASCENDING "
            "(canonicalization restriction 6). Sorting at construction rather "
            "than at hash time is what makes the canonical form unambiguous. "
            "Got: %s" % ids)


def harvest_product_lexicon(manifest_a: dict) -> frozenset:
    """V3's denylist: tokens from tool names and descriptions, minus the
    capability vocabulary.

    L3 does not own this input - it is harvested at attach - so the constructor
    takes it explicitly and defaults to EMPTY rather than silently harvesting.
    A lexicon that appears from nowhere is a lexicon nobody can reproduce, and
    V3's whole value is that a judge can re-run it.
    """
    toks = set()
    for tool in manifest_a.get("tools", []):
        for field in ("tool_fqname", "description"):
            for t in _TOKEN_RE.findall(str(tool.get(field, ""))):
                toks.add(t)
    return frozenset(t for t in toks if t not in _DSL_VOCABULARY)


# --------------------------------------------------------------------------
class Validator:
    """Holds the manifest halves a rule must be judged against.

    Part A (`capability_manifest`) freezes at D3 with the target agent; Part B
    (`derived_schema`) freezes at D5 with the corpus, gated on the label-
    blindness check. Two artifacts, two hashes, two freeze dates - ruling 20.
    Both are required here because a rule can name a tool handle (Part A) and a
    `derived.*` path (Part B) in the same line.

    One field deliberately straddles them: `derived.approval_tier`'s ENUM VALUES
    `{NONE,T0..T4}` are Part A, so this class can validate a rule naming `T2` at
    any point after D3 including before the corpus exists, while its
    COMPUTATION is Part B. VALUES FREEZE EARLY, SEMANTICS FREEZE LATE.
    """

    def __init__(self, manifest_a: dict, derived_schema_b: dict, *,
                 product_lexicon=(), corpus_payloads=()):
        self.manifest = manifest_a
        self.derived_schema = derived_schema_b
        self.tool_handles = frozenset(
            t["tool_handle"] for t in manifest_a.get("tools", []))
        self.arg_enums = manifest_a.get("arg_enums", {}) or {}
        self.declared_derived = frozenset(
            f["name"] for f in derived_schema_b.get("derived_fields", []))
        self.declared_episode = frozenset(
            f["name"] for f in derived_schema_b.get("episode_fields", []))
        self.product_lexicon = frozenset(product_lexicon)
        self.corpus_payloads = tuple(corpus_payloads)
        self._payload_ngrams = self._build_ngrams()

    # -- V7 support -------------------------------------------------------
    def _build_ngrams(self):
        grams = set()
        for payload in self.corpus_payloads:
            toks = _TOKEN_RE.findall(str(payload))
            n = PAYLOAD_SUBSTRING_TOKENS
            for i in range(len(toks) - n + 1):
                grams.add(tuple(toks[i:i + n]))
        return grams

    # -- individual checks, each overridable so a strawman can be wrong in
    #    exactly one place -------------------------------------------------
    def check_rule_id(self, parsed):
        """V9. A patch in which the model emitted a hash-shaped ID on add_rule
        is REJECTED - not because the id would be wrong (it certainly would be)
        but because a model that emitted a plausible one has demonstrated it is
        GUESSING AT A DETERMINISTIC COMPUTATION, and the next guess lands
        somewhere we cannot see."""
        try:
            assert_model_did_not_forge_a_rule_id(parsed.rule_id)
        except CanonicalizationError as e:
            raise ValidationError(e.code, e.detail, parsed.line) from None

    def check_selector(self, parsed):
        """V1 and V2, re-asserted off the parse tree."""
        if parsed.cap_class == UNCLASSIFIED:
            raise ValidationError(
                "E_UNCLASSIFIED_SELECTOR",
                "no rule may select UNCLASSIFIED", parsed.line)
        if parsed.cap_class not in CAP_CLASSES:
            raise ValidationError(
                "E_UNKNOWN_CAP_CLASS",
                "%r is not one of the six classes" % parsed.cap_class,
                parsed.line)

    def check_tool_handles(self, parsed):
        """V5."""
        for h in parsed.tool_handles:
            if h not in self.tool_handles:
                raise ValidationError(
                    "E_UNKNOWN_TOOL_HANDLE",
                    "%s is not in the capability manifest. A rule may not bind "
                    "to a tool the target does not expose." % h, parsed.line)

    def check_derived_paths(self, parsed):
        """N6 and ruling 19. `derived.` is a RESERVED prefix that resolves
        against Part B's declared set.

        Anything else under that prefix is model-authored by definition, and the
        plugin overwrites model-authored derived values before evaluation - so a
        rule reading an undeclared one would be reading a field that is
        guaranteed absent. It would never fire, and section 8 rule 2 says a
        check that cannot fail is not measuring anything.
        """
        for path in self._paths(parsed):
            if path.startswith(DERIVED_PREFIX) and path not in self.declared_derived:
                raise ValidationError(
                    "E_UNDECLARED_DERIVED_PATH",
                    "%r is not one of the seven derived fields Part B declares "
                    "(%s). The rule PARSES - the grammar has no opinion about "
                    "names - and it is refused HERE, which is the discipline "
                    "rather than a gap: 19.3's label-blindness check runs over "
                    "the corpus, so a field no corpus instance exercises cannot "
                    "be checked, and an uncheckable field has no business in a "
                    "hashed artifact."
                    % (path, ", ".join(sorted(self.declared_derived))),
                    parsed.line)
            if path.startswith(EPISODE_PREFIX):
                raise ValidationError(
                    "E_EPISODE_PATH_AS_ARGUMENT",
                    "%r is an episode context fact, not a call argument. The "
                    "grammar's asymmetry is deliberate: an episode fact can "
                    "only ever appear on the RIGHT of a comparison against an "
                    "argument of the pending call, never on the left and never "
                    "against a literal." % path, parsed.line)

    def check_context_fields(self, parsed):
        """The three `episode.*` bindings are Part B's too."""
        for cl in parsed.clauses:
            if cl.form != CLAUSE_ARG_VS_EPISODE_CONTEXT:
                continue
            qualified = EPISODE_PREFIX + cl.context_field
            if self.declared_episode and qualified not in self.declared_episode:
                raise ValidationError(
                    "E_UNDECLARED_EPISODE_FIELD",
                    "%s is not declared in Part B" % qualified, parsed.line)

    def check_enums(self, parsed):
        """V4. An enum symbol is legal only where the manifest declares it FOR
        THAT EXACT PATH. There are NO FREE STRINGS, and that bound is the bar:
        a language that cannot express a string match cannot learn a string
        filter, so the held-out-family result is true BY CONSTRUCTION."""
        for path, symbols in self._enum_uses(parsed):
            declared = self.arg_enums.get(path)
            if declared is None:
                raise ValidationError(
                    "E_UNDECLARED_ENUM_PATH",
                    "the manifest declares no enum for %r, so no symbol is "
                    "legal there" % path, parsed.line)
            for s in symbols:
                if s not in declared:
                    raise ValidationError(
                        "E_UNDECLARED_ENUM_SYMBOL",
                        "%r is not a declared member of %r (%s)"
                        % (s, path, ", ".join(declared)), parsed.line)

    def check_product_lexicon(self, parsed):
        """V3. Runs over `body_text`, not `source_text`: KB9 exempts metadata
        and provenance, and a rule id is not something the ARMORER chose."""
        if not self.product_lexicon:
            return
        for tok in _TOKEN_RE.findall(parsed.body_text):
            if tok in self.product_lexicon:
                raise ValidationError(
                    "E_PRODUCT_IDENTIFIER",
                    "%r is a product identifier harvested from the target's "
                    "tool names. Every terminal in this grammar is abstract or "
                    "manifest-declared - that is what makes headline result #1 "
                    "mean anything." % tok, parsed.line)

    def check_payload_substring(self, parsed):
        """V7. Zero rule bodies contain an >=8-token substring of any corpus
        payload.

        The realistic path to a violation is not that the ARMORER invents an
        attacker's prose - it cannot, there are no free strings - but that an
        attack payload QUOTES DSL-SHAPED TEXT and the ARMORER parrots it back.
        That is the lint's actual job.
        """
        if not self._payload_ngrams:
            return
        toks = _TOKEN_RE.findall(parsed.body_text)
        n = PAYLOAD_SUBSTRING_TOKENS
        for i in range(len(toks) - n + 1):
            gram = tuple(toks[i:i + n])
            if gram in self._payload_ngrams:
                raise ValidationError(
                    "E_PAYLOAD_SUBSTRING",
                    "the rule body reproduces an %d-token run from a corpus "
                    "payload: %r. A policy that quotes the attack is a string "
                    "filter wearing a capability rule's clothes."
                    % (n, " ".join(gram)), parsed.line)

    def check_totality(self, stored_rules):
        """V8. The rule set must evaluate TOTAL on a synthetic call-shape sweep.

        Every shape below is one the corpus can actually produce: a missing
        argument, a string where an integer was expected, an empty prefix, a
        call carrying every class at once (the fail-closed tool), and a call
        carrying none. If any of them raises, the engine is not total and a
        single malformed call would crash an episode - which leaves the run
        with a TARGET_FAULT-shaped hole where a measurement should be.
        """
        from ..policy.engine import PolicyEngine          # lazy: avoids a cycle

        engine = PolicyEngine({"policy_schema_version": 1,
                               "target_manifest_hash": "0" * 16,
                               "rules": list(stored_rules)})
        shapes = [
            ({}, ()),
            ({"amount_minor": 1}, ()),
            ({"amount_minor": "not-a-number"}, ()),
            ({"amount_minor": None}, ()),
            ({"derived.approval_tier": "T2"}, ()),
            ({"to": "someone"}, ()),
        ]
        caps = [set(), {"CAP_MOVES_MONEY"}, set(CAP_CLASSES), {UNCLASSIFIED}]
        for args, prefix in shapes:
            for cs in caps:
                try:
                    engine.evaluate(tool_handle="tool:t_00000000",
                                    capability_set=cs, args=args,
                                    episode_prefix=prefix)
                except Exception as e:                      # noqa: BLE001
                    raise ValidationError(
                        "E_NOT_TOTAL",
                        "evaluation raised %s on capability_set=%s args=%r. "
                        "The evaluator must be TOTAL and TERMINATING or the "
                        "TRIPWIRE stops being a pure function of its inputs."
                        % (type(e).__name__, sorted(cs), args)) from None

    # -- helpers ----------------------------------------------------------
    def _paths(self, parsed):
        for cl in parsed.clauses:
            if cl.path:
                yield cl.path
        if parsed.action.path:
            yield parsed.action.path

    def _enum_uses(self, parsed):
        for cl in parsed.clauses:
            if cl.form == CLAUSE_ARG_CMP_LITERAL and cl.value_type == "enum":
                yield cl.path, (cl.value,)
            elif cl.form == CLAUSE_ARG_IN_ENUM_LIST:
                yield cl.path, tuple(cl.values)
        a = parsed.action
        if a.verb == "constrain_arg" and a.value_type == "enum":
            yield a.path, (a.value,)

    # -- entry points -----------------------------------------------------
    def validate_rule(self, parsed, *, is_add=True) -> dict:
        """Validate one parsed rule and return its stored form with a real ID."""
        if is_add:
            self.check_rule_id(parsed)
        self.check_selector(parsed)
        self.check_tool_handles(parsed)
        self.check_derived_paths(parsed)      # before check_enums, see the
        self.check_context_fields(parsed)     # module docstring on ordering
        self.check_enums(parsed)
        self.check_product_lexicon(parsed)
        self.check_payload_substring(parsed)
        return compile_rule(parsed)

    def validate_patch(self, parsed_patch, current_policy=None) -> dict:
        """Validate a whole patch against the policy it applies to.

        Returns the new `hashed_payload`. Raises ValidationError on the FIRST
        refusal - the ARMORER gets one repair attempt with the error as its sole
        feedback, and a list of twelve simultaneous complaints is not feedback.
        """
        current = current_policy or {}
        if "hashed_payload" in current:
            current = current["hashed_payload"]
        existing = {r["rule_id"]: r for r in current.get("rules", [])}

        for rid in parsed_patch.retractions:
            target = existing.get(rid)
            if target is None:
                raise ValidationError(
                    "E_RETRACT_UNKNOWN_RULE",
                    "%s is not in the policy being patched. On retract_rule the "
                    "model cites the REAL id verbatim, copied from the policy "
                    "document it was handed." % rid)
            if not str(target.get("origin", "")).startswith("armorer:"):
                raise ValidationError(
                    "E_RETRACT_SEED_RULE",
                    "%s has origin %r. SEED RULES ARE IRRETRACTABLE BY THE "
                    "ARMORER (V6) - the seed floor is the one thing no learned "
                    "patch may remove." % (rid, target.get("origin")))
            existing.pop(rid)

        for parsed in parsed_patch.rules:
            stored = self.validate_rule(parsed)
            existing[stored["rule_id"]] = stored

        rules = sort_rules(list(existing.values()))
        self.check_totality(rules)
        return {
            "policy_schema_version": current.get("policy_schema_version", 1),
            "target_manifest_hash": current.get("target_manifest_hash",
                                                "0" * 16),
            "rules": rules,
        }
