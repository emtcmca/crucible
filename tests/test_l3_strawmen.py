"""test_l3_strawmen.py - THE NEGATIVE CHECK ON THE CHECKS.

If a test here fails, the SUITE is broken, not the strawman. Each pair below is
a check that one deliberately-wrong implementation must fail. A PASS means the
check stopped discriminating and would also wave through the real bug it exists
to catch.

`tests/strawman_canon.py` records why this exists as a permanent fixture rather
than a one-time exercise: L1's first strawman claim named the wrong vector, the
meta-check caught it, and the comfortable fix - demote the vector to "unproven"
- would have left a vector asserting a property with no evidence it can detect
its own violation.

A `NotImplementedError` is NOT counted as detection. A stub has not disagreed
with anything; treating a stub as evidence is how a suite goes green over an
empty implementation, which is the exact failure the file above was written
about.
"""

import pytest

from . import l3_checks, strawman_policy

_REAL = l3_checks.real_impl()
STRAWMEN = strawman_policy.build_strawmen(_REAL)

_CASES = sorted((name, cid)
                for name, (_impl, must_fail) in STRAWMEN.items()
                for cid in must_fail)


@pytest.mark.parametrize("name,check_id", _CASES,
                         ids=["%s:%s" % (n, c) for n, c in _CASES])
def test_strawman_fails_the_check_it_is_supposed_to_fail(name, check_id):
    impl, must_fail = STRAWMEN[name]
    reason = must_fail[check_id]
    try:
        l3_checks.CHECKS[check_id](impl)
    except NotImplementedError:
        raise
    except AssertionError:
        return
    except Exception as e:                                     # noqa: BLE001
        # A strawman that blows up rather than disagreeing has still been
        # detected, but it is weaker evidence than a wrong ANSWER and it is
        # recorded as such rather than silently counted the same.
        pytest.fail(
            "strawman %r raised %s instead of producing a wrong answer for %s. "
            "That is detection by crash, not by measurement - fix the strawman "
            "so it is wrong in one place rather than broken: %r"
            % (name, type(e).__name__, check_id, e))
    pytest.fail(
        "CHECK {} NO LONGER DISCRIMINATES against strawman {!r}. It was "
        "supposed to fail because: {} A check that a known-wrong implementation "
        "PASSES is not testing the property it claims to test.".format(
            check_id, name, reason))


def test_every_check_is_killed_by_at_least_one_strawman():
    """The census. A check no strawman fails has no evidence it can detect its
    own violation. That state is ALLOWED - some properties only a foreign
    implementation gets wrong, which is why L1 declares six vectors unproven -
    but it must be DECLARED HERE, not discovered by somebody later.

    L3 declares NONE. All ten are killed, because every one of them is about a
    ruling that overrides what the obvious implementation would do, and the
    obvious implementation is exactly what a strawman is.
    """
    killed = {cid for _impl, mf in STRAWMEN.values() for cid in mf}
    unproven = sorted(set(l3_checks.CHECKS) - killed)
    assert unproven == [], (
        "check discrimination census changed. Unproven now: %s. Either add a "
        "strawman that gets it wrong, or declare it here with the reason no "
        "plausible wrong implementation exists." % unproven)


def test_every_strawman_claim_names_a_real_check():
    """Guards the guard. A typo'd check ID in a `must_fail` map would make the
    parametrize above silently skip the case it was added for - the failure
    mode where the suite gets smaller and nobody notices."""
    for name, (_impl, must_fail) in STRAWMEN.items():
        for cid in must_fail:
            assert cid in l3_checks.CHECKS, (
                "strawman %s names %s, which is not a real check" % (name, cid))


def test_no_strawman_claim_is_still_a_placeholder():
    """Every reason string is written AFTER observing the actual failure.

    `strawman_canon.py`'s recorded incident is a claim written from expectation
    that turned out to be false. A placeholder left in the tree is the same
    defect with the tell still visible, so it fails the suite rather than
    sitting there.

    The sentinel is `<<UNOBSERVED>>` and not the word "PENDING". The first
    version of this guard matched "PENDING" case-insensitively and fired on the
    reason string for `sum_excludes_pending`, which contains the phrase "a
    pending 20000" - a guard that flags correct prose gets deleted, and then it
    guards nothing. Logged in `docs/lanes/L3-log.md`.
    """
    for name, (_impl, must_fail) in STRAWMEN.items():
        for cid, reason in must_fail.items():
            assert strawman_policy.UNOBSERVED not in reason, (
                "%s:%s still carries a placeholder reason" % (name, cid))


def test_schema_only_validator_really_cannot_see_a_nested_match_mode():
    """The specific half of N3 that a JSON Schema structurally cannot reach.

    `additionalProperties: false` on `match` DOES catch a `match_mode` sitting
    in `match`, so the schema-only strawman is caught on N3's first assertion
    and that alone would not prove the "at any depth" half discriminates
    against anything. This asserts the gap directly: a `match_mode` parked in
    `provenance` - a free-form object by design, because it carries per-rule
    autopsy and proposal IDs - passes the schema cleanly.
    """
    import copy

    from . import l3_fixtures as fx

    doc = copy.deepcopy(fx.POLICY_DOC_VALID)
    doc["provenance"] = {"r_5f2a91cc0b74": {"notes": [{"match_mode": "all_of"}]}}
    strawman_policy._schema_only_validate_policy_document(doc)   # must NOT raise
