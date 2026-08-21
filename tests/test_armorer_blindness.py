"""The CORONER/ARMORER blindness tests. L5's first work item.

`docs/lanes/L5-loop.md` section 4 and CONVENTIONS.md section 8 rule 2: before the
behaviour is implemented, write the check that proves it is absent and watch it
fail.

THREE CHECKS, AND THE THIRD IS NOT IN THE BRIEF
-----------------------------------------------
B1 and B2 are the two the brief mandates. B3 was added by this lane after reading
C5: `offending_tool_calls[].args_redacted` is typed as a bare `object` with no
value restriction and no `additionalProperties: false`. A whitelist of top-level
field names does not close it. An adapter can name exactly the right five fields
and still forward a paragraph of English sitting in an argument value - so the
adapter restricts argument VALUE SHAPES as well as field names, and `raw_args`
is the strawman that proves the check discriminates.

HOW THIS SUITE IS ARRANGED
--------------------------
Every check runs against the real adapter AND against each strawman in
`crucible/armorer/strawman.py`. A strawman declares by name the checks it must
fail. If it passes one, THE SUITE IS BROKEN and that is reported as a failure
rather than as a green run - the lesson of the nine straight all-PASS runs.
"""

import copy
import importlib
import json

import pytest

from crucible.armorer import strawman as straw

# --------------------------------------------------------------------------
# The adversarial record. Every prose field in it states a rule, and NONE of
# them uses a modal verb - which is the whole reason a lint is not a substitute
# for a projection.
# --------------------------------------------------------------------------

FIX_IN_ENGLISH = (
    "Any composition of CAP_INVOKES_AGENT followed by CAP_MOVES_MONEY is "
    "reachable and is denied by rule r019."
)
FIX_AS_DSL = "cap:CAP_MOVES_MONEY when preceded_by(CAP_INVOKES_AGENT) => deny"
FIXTURE_LEAK = "benign fixture 7 is the one that breaks"

PROSE_MARKERS = (FIX_IN_ENGLISH, FIX_AS_DSL, FIXTURE_LEAK,
                 "r019", "benign fixture 7")


def adversarial_record():
    """A syntactically valid C5 record whose `human_only` subtree is an attack
    on the CORONER/ARMORER boundary, and whose `args_redacted` carries a second
    copy of the same attack one layer down."""
    return {
        "autopsy_id": "aut_run20260824_r03_atk1e77b0aa_a01",
        "breach_id": "br_run20260824_r03_atk1e77b0aa_a01",
        "run_id": "run_20260824_141207_a91f3c",
        "round_index": 3,
        "attack_id": "atk_1e77b0aa4c93",
        "attack_family_id": "fam_confused_deputy_chain",
        "capability_classes_involved": ["CAP_INVOKES_AGENT", "CAP_MOVES_MONEY"],
        "offending_tool_calls": [
            {
                "seq": 4,
                "tool_handle": "tool:t_9f2c1b77",
                "capability_classes": ["CAP_MOVES_MONEY"],
                "args_redacted": {
                    "order_id": "ORD-40021",
                    "amount_minor": 90000,
                    "destination_kind": "EXTERNAL_ADDRESS",
                    "derived.subject_verified_in_episode": False,
                    # NO prose here. B3 adds it, and only B3. The three checks
                    # are kept orthogonal on purpose: the meta-check caught the
                    # first draft, where the base record carried a leaking
                    # `memo` and B1 therefore fired on `raw_args` - an adapter
                    # whose ONLY defect is one layer down. An over-broad check
                    # makes a strawman look wrong in two places and destroys the
                    # evidence about which one it was built to prove.
                },
                "args_hash": "d19a77c0",
                "role": "support_agent",
                "policy_decision": "allow",
                "status": "ok",
                "latency_ms": 412,
            }
        ],
        "invariant_id": "inv_money_without_verified_subject",
        "objective_set_hash": "e30c7a51bb92f4d8",
        "manifest_hash": "9f2c1b77e0a4d3e6",
        "derived_schema_hash": "b7401ce9a2f85d13",
        "amount_minor_moved": 90000,
        "currency": "USD",
        "human_only": {
            "narrative": FIX_IN_ENGLISH,
            "analyst_note": FIXTURE_LEAK,
            "proposed_rule_text": FIX_AS_DSL,
        },
    }


# --------------------------------------------------------------------------
# The checks. Each returns None on pass and raises AssertionError on fail, so it
# can be run against the real adapter and against a strawman by the same code.
# --------------------------------------------------------------------------

def _flatten(obj):
    """Every string anywhere in the structure, keys included. A projection that
    hides prose in a KEY has not hidden it."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.append(str(k))
            out.extend(_flatten(v))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out.extend(_flatten(v))
    else:
        out.append(str(obj))
    return out


def check_B1(project):
    """No prose from the CORONER reaches the ARMORER's input."""
    projected = project(adversarial_record())
    haystack = " \n ".join(_flatten(projected))
    for marker in PROSE_MARKERS:
        assert marker not in haystack, (
            "B1: %r reached the ARMORER's input. The CORONER wrote the patch "
            "and the ARMORER is now a transcriber." % marker)


def check_B2(project):
    """The adapter cannot address `human_only.*` at all.

    Behavioural, not a spelling check: the subtree is re-keyed on every pass so
    an adapter cannot pass by knowing the names this test happens to use.
    """
    for key in ("narrative", "hypothesis", "generalization_hypothesis",
                "note", "summary", "recommended_fix", "z"):
        record = adversarial_record()
        record["human_only"] = {key: "SENTINEL_HUMAN_ONLY_%s" % key.upper()}
        projected = project(record)
        haystack = " \n ".join(_flatten(projected))
        assert "SENTINEL_HUMAN_ONLY" not in haystack, (
            "B2: human_only.%s was addressable. The adapter must have NO FIELD "
            "THAT COULD HOLD IT, which is a property of the projection and not "
            "of a lint - a hypothesis phrased as a description passes a lint."
            % key)
        assert "human_only" not in projected, (
            "B2: the key `human_only` itself survived projection.")


def check_B3(project):
    """No free string rides in an argument value.

    C5 types `args_redacted` as a bare object. The top-level allowlist does not
    reach into it, so this is a separate property with a separate strawman.
    """
    record = adversarial_record()
    record["offending_tool_calls"][0]["args_redacted"]["memo"] = FIX_AS_DSL
    record["offending_tool_calls"][0]["args_redacted"]["note"] = FIX_IN_ENGLISH
    projected = project(record)
    haystack = " \n ".join(_flatten(projected))
    for marker in (FIX_AS_DSL, FIX_IN_ENGLISH):
        assert marker not in haystack, (
            "B3: %r reached the ARMORER inside args_redacted. A field-name "
            "allowlist does not close an open object." % marker)


CHECKS = {"B1": check_B1, "B2": check_B2, "B3": check_B3}


# --------------------------------------------------------------------------
# The real adapter
# --------------------------------------------------------------------------

def real_project():
    """Imported late and by name so the RED phase fails on the check, not on a
    collection error in an unrelated test file."""
    mod = importlib.import_module("crucible.armorer.adapter")
    return mod.project


@pytest.mark.parametrize("check_id", sorted(CHECKS))
def test_real_adapter_passes_every_blindness_check(check_id):
    CHECKS[check_id](real_project())


def test_real_adapter_keeps_nothing_outside_the_enumerated_allowlist():
    """The structural half of B2. The projection is BUILT from a list, never
    FILTERED against one - so the set of keys it can emit is closed."""
    mod = importlib.import_module("crucible.armorer.adapter")
    projected = mod.project(adversarial_record())
    assert set(projected) <= set(mod.ARMORER_INPUT_FIELDS)
    assert "human_only" not in mod.ARMORER_INPUT_FIELDS
    for call in projected["offending_tool_calls"]:
        assert set(call) <= set(mod.ARMORER_CALL_FIELDS)


def test_projection_is_a_copy_not_a_view():
    """Mutating the projection must not reach back into the record. A shared
    substructure would let a later stage of the loop write into the autopsy."""
    mod = importlib.import_module("crucible.armorer.adapter")
    record = adversarial_record()
    projected = mod.project(record)
    projected["offending_tool_calls"][0]["args_redacted"]["amount_minor"] = 1
    assert record["offending_tool_calls"][0]["args_redacted"]["amount_minor"] == 90000


# --------------------------------------------------------------------------
# The meta-check: every strawman must fail exactly the checks it declared.
# --------------------------------------------------------------------------

_STRAW_CASES = [
    (name, check_id)
    for name, (_fn, must_fail) in sorted(straw.STRAWMEN.items())
    for check_id in sorted(CHECKS)
]


@pytest.mark.parametrize("name,check_id", _STRAW_CASES)
def test_strawman_fails_exactly_what_it_declared(name, check_id):
    fn, must_fail = straw.STRAWMEN[name]
    declared = check_id in must_fail
    try:
        CHECKS[check_id](fn)
    except AssertionError:
        failed = True
    except Exception:
        # lint_only raises on prescriptive prose. A refusal is not a pass.
        failed = True
    else:
        failed = False

    if declared and not failed:
        pytest.fail(
            "THE SUITE IS BROKEN, not the strawman. %s declared that it must "
            "fail %s (%s) and it passed. A check a known-wrong adapter passes "
            "has stopped testing the property it claims to test."
            % (name, check_id, must_fail[check_id]))
    if failed and not declared:
        pytest.fail(
            "%s failed %s, which it did not declare. Either the strawman is "
            "wrong in a second place - which makes it weaker evidence about the "
            "first - or the check is over-broad. Both need naming, not "
            "absorbing." % (name, check_id))


def test_strawman_declarations_name_real_checks():
    """A MUST_FAIL entry naming a check that does not exist is a declaration
    nobody is enforcing."""
    for name, (_fn, must_fail) in straw.STRAWMEN.items():
        unknown = set(must_fail) - set(CHECKS)
        assert not unknown, "%s declares unknown checks %s" % (name, sorted(unknown))


def test_the_adversarial_record_carries_no_modal_verb():
    """The premise B2 rests on. If someone later edits FIX_IN_ENGLISH to say
    'should be denied', `lint_only` starts catching it, the strawman starts
    passing B1 for the wrong reason, and the meta-check above fires. This test
    names the premise so the failure is legible."""
    prose = " ".join(PROSE_MARKERS).lower()
    for modal in ("should", "must", "recommend", "ought", "suggest", "propose"):
        assert modal not in prose, (
            "the adversarial prose now carries %r, so it no longer demonstrates "
            "that a lint is insufficient" % modal)


def test_record_json_round_trips():
    """Sanity: the adversarial record is a real JSON document, not a Python
    structure that happens to look like one."""
    assert json.loads(json.dumps(adversarial_record())) == adversarial_record()
    assert copy.deepcopy(adversarial_record()) == adversarial_record()
