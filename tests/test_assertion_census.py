"""Every test in this suite must be able to fail, and this counts the ones that cannot.

THE DEFECT THIS REPOSITORY KEEPS PRODUCING IS A CHECK THAT PASSES WHILE
MEASURING NOTHING - seventeen recorded instances, several of them authored while
repairing an earlier one. Every existing control here guards the PRODUCTION
code: the known-bad fixtures, the mutation runs, the coverage census in the
transfer reader. None of them looks at the tests.

A test function whose body contains no `assert`, no `raise`, and no
`pytest.raises` passes unless something it calls throws. That is sometimes a
real property - "this document validates", "this guard has a passing side" - and
it is sometimes a test that was never finished. From the outside the two are
identical, and the suite reports both as a green dot.

WHAT THIS FILE DOES, AND WHAT IT DELIBERATELY DOES NOT DO.

It does NOT require every test to assert. Rewriting thirty-five call-only tests
across files three people are editing, on the day before an unrepeatable run, is
how a repair becomes an outage.

It is a RATCHET. The assertion-free tests that existed when the census was
written are listed below by name. The census fails if a NEW one appears, and it
also fails if a listed one is fixed or renamed without being removed from the
list - a stale exemption is a second source of truth about which tests are debt,
and a list nobody prunes is a list nobody reads.

An open thread had recorded this debt as "my three tests that assert nothing"
for two sessions. The census found THIRTY-FIVE. That gap is the argument for
counting rather than remembering, and it is why the number lives in a scan
instead of in a note.

WHAT THIS MEASURES, AND THE TWO THINGS IT DOES NOT
--------------------------------------------------
Reproduced by an outside reviewer, 2026-08-30, and stated here because a census
whose limits are known only to its author is a number waiting to be misquoted.

**IT MEASURES LOCAL SYNTAX, NOT WHETHER A TEST CAN FAIL.** The scan walks one
function body and looks for `assert`, `raise`, or a `pytest.raises`-family call
written IN IT. That is a lexical property of a single AST, and it is a proxy.

  1. FALSE POSITIVE - THE HELPER. A test that delegates its assertion to a
     helper is reported as assertion-free, because the helper's body is a
     different AST. `test_a_symlink_out_of_a_temp_directory_into_a_repo_is_
     still_refused` calls `_refusal(...)`, which raises on the wrong outcome;
     the census cannot see it and lists it below. Following the call would mean
     resolving names across modules, fixtures and monkeypatching, which is a
     static analyser, not a census.
  2. FALSE NEGATIVE - THE SKIP, now closed. `skip` and `exit` were in
     `_RAISERS` until 2026-08-30, so a test whose only "raiser" was an
     unconditional `pytest.skip()` counted as asserting something. A test that
     always skips cannot fail; counting it as a check is the exact defect this
     file exists to count. Both were removed. The delta was ONE entry - the
     helper-driven test above, whose skip is conditional - so nothing was
     hiding behind them today, and nothing can hide behind them tomorrow.

**THE COUNT IS INTERIM DEBT CONTAINMENT. IT IS NOT EVIDENCE THAT THE LISTED
TESTS ARE MEANINGFUL.** The exemption list is a mixture of three things - real
"must not raise" properties, helper-driven false positives, and tests that were
never finished - and the census cannot tell them apart. EVERY ENTRY ON IT STILL
NEEDS TRIAGE, one at a time, by reading them. No count is written here on
purpose: the list is the artifact, a copy of its length is a second source of
truth about it, and this one moved twice on the day it was written.

So: this file may be cited as "no NEW test that cannot fail may be added
quietly". It may not be cited as closing the test-quality debt. Presenting a
ratchet count as closure is the avoidance the reviewer named when he accepted
the ratchet: it becomes avoidance if the list is never triaged, or if its size
is offered as evidence that the tests on it are sound.
"""

import ast
import pathlib

TESTS = pathlib.Path(__file__).resolve().parent

#: Calls and context managers that ARE an assertion about failure.
#:
#: `skip` and `exit` were here until 2026-08-30 and are deliberately not. A test
#: whose only raiser is `pytest.skip()` cannot fail, so counting it as an
#: assertion is this repository's own defect, committed inside the check that
#: counts it. Removing them added exactly one entry to the list below.
_RAISERS = frozenset(("raises", "warns", "fail", "xfail", "deprecated_call"))

#: The assertion-free tests present when this census was written, 2026-08-30.
#:
#: NOT AN APPROVAL. Several are legitimate - a bare `validate(doc)` that must
#: not raise is a real property, and `test_an_ordinary_off_tree_path_is_allowed`
#: exists precisely because a guard that cannot pass is as broken as one that
#: cannot fail. Some are helper-driven false positives. The rest are unfinished.
#: This list does not distinguish them, because distinguishing them requires
#: reading every one of them - and that is the work this ratchet exists to make
#: visible rather than to pretend it did. UNTRIAGED as of 2026-08-30.
#:
#: TO REMOVE ONE: give the test a real assertion, then delete its line here.
#: Both, in the same change. The census fails either way round.
KNOWN_ASSERTION_FREE = frozenset((
    ("test_adjudication.py", "test_the_outcome_guard_survives_a_self_referencing_structure"),
    ("test_adjudication.py", "test_a_clean_structure_passes_the_guard"),
    ("test_adjudication_inspection.py", "test_the_re_emitted_record_still_answers_the_challenge"),
    ("test_adjudication_inspection.py", "test_the_published_block_validates_against_the_bundle_schema"),
    ("test_adjudication_inspection.py", "test_a_shared_date_does_not_trip_the_firewall"),
    ("test_armorer_blindness.py", "test_real_adapter_passes_every_blindness_check"),
    ("test_compiler_attach.py", "test_a_cycle_does_not_hang_the_walk"),
    ("test_compiler_attach.py", "test_ordinary_tools_without_the_attribute_are_ignored"),
    ("test_coroner_no_fix.py", "test_record_validates_against_the_frozen_c5_schema"),
    ("test_corpus_freeze.py", "test_every_covered_file_on_disk_canonicalizes"),
    ("test_corpus_lints.py", "test_declared_none_is_accepted"),
    ("test_corpus_lints.py", "test_a_declared_approver_is_accepted"),
    ("test_corpus_lints.py", "test_a_fault_code_alongside_another_difference_is_fine"),
    ("test_corpus_lints.py", "test_two_remorse_codes_are_not_this_lint_s_business"),
    ("test_corpus_lints.py", "test_a_structured_destination_arg_is_accepted"),
    ("test_corpus_schema.py", "test_a_minimal_attack_validates"),
    ("test_corpus_schema.py", "test_a_minimal_benign_fixture_validates"),
    ("test_corpus_schema.py", "test_a_minimal_known_bad_validates"),
    ("test_corpus_schema.py", "test_a_known_bad_may_expect_CLEAN"),
    ("test_corpus_trace_vocabulary.py", "test_the_schema_accepts_the_c2_spelling_at_load"),
    ("test_dsl_grouping.py", "test_the_product_lexicon_check_does_not_read_group_by_as_a_product_noun"),
    ("test_dsl_grouping.py", "test_the_stored_form_validates_against_the_C4_schema"),
    ("test_dsl_validator.py", "test_V3_exempts_metadata_and_provenance"),
    ("test_dsl_validator.py", "test_V7_control_the_same_rule_validates_against_an_unrelated_corpus"),
    ("test_dsl_validator.py", "test_V7_control_a_shorter_overlap_is_not_a_violation"),
    ("test_f4_transfer_runner.py", "test_the_invented_sealed_fixture_is_actually_valid"),
    ("test_f4_transfer_runner.py", "test_an_ordinary_off_tree_path_is_allowed"),
    # THE HELPER-DRIVEN FALSE POSITIVE, named in the docstring above. It calls
    # `_refusal(...)`, which raises when the guard does not refuse. Added
    # 2026-08-30 when `skip` left `_RAISERS`; it is the whole delta.
    ("test_f4_transfer_runner.py", "test_a_symlink_out_of_a_temp_directory_into_a_repo_is_still_refused"),
    # Arrived 2026-08-30 from a concurrent session, and it is the sanctioned
    # case rather than debt: its docstring states the property as "must not
    # raise" and its last line says so again. Listed, not exempted silently.
    ("test_f4_transfer_runner.py", "test_release_is_silent_about_a_path_that_is_already_gone"),
    ("test_governor_abort.py", "test_real_governor_passes"),
    ("test_l3_negative_checks.py", "test_negative_check"),
    ("test_l3_strawmen.py", "test_schema_only_validator_really_cannot_see_a_nested_match_mode"),
    ("test_live_corpus_and_worlds.py", "test_c6_accepts_a_generated_row_that_names_its_corpus_instance"),
    ("test_no_events_split.py", "test_every_no_event_verdict_validates_against_c9"),
    ("test_transfer_reader.py", "test_the_contract_is_a_valid_draft_2020_12_schema"),
    ("test_tripwire_verdicts.py", "test_every_verdict_validates_against_c9"),
    ("test_v22_emptiness_escape.py", "test_a_declared_episode_field_is_accepted"),
))


def asserts_something(fn):
    """True if this function body can fail on its own terms.

    `assert` and `raise` are obvious. `pytest.raises` is counted both as a
    context manager and as a bare call, because missing the `with` form would
    report every deliberate-refusal test in the suite as debt - a false positive
    rate that would get the whole census switched off within a day.
    """
    for node in ast.walk(fn):
        if isinstance(node, (ast.Assert, ast.Raise)):
            return True
        if isinstance(node, ast.With):
            for item in node.items:
                call = item.context_expr
                if isinstance(call, ast.Call) and _name_of(call.func) in _RAISERS:
                    return True
        if isinstance(node, ast.Call) and _name_of(node.func) in _RAISERS:
            return True
    return False


def _name_of(func):
    return getattr(func, "attr", None) or getattr(func, "id", None)


def scan(directory):
    """Every (file, test name) in `directory` whose body cannot fail."""
    out = set()
    for path in sorted(pathlib.Path(directory).glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and node.name.startswith("test_") \
                    and not asserts_something(node):
                out.add((path.name, node.name))
    return out


def test_no_new_assertion_free_test_has_been_added():
    """The ratchet. A test that cannot fail may not be introduced quietly."""
    found = scan(TESTS)
    new = sorted(found - KNOWN_ASSERTION_FREE)
    assert not new, (
        "%d test(s) contain no assert, no raise and no pytest.raises, so they "
        "pass unless something they call happens to throw:\n  %s\n\n"
        "If the property really is 'this must not raise', say so in the "
        "docstring and add the pair to KNOWN_ASSERTION_FREE in this file. If "
        "it is an unfinished test, finish it."
        % (len(new), "\n  ".join("%s::%s" % pair for pair in new)))


def test_the_exemption_list_has_no_stale_entries():
    """A list nobody prunes is a list nobody reads.

    Without this, fixing a test leaves its exemption behind, and the next
    person reading the list is told the debt is larger than it is. Worse, a
    RENAMED test drops out of the scan and its old name lingers here - so the
    renamed version is exempt by nothing and the census would not notice it
    coming back as debt.
    """
    found = scan(TESTS)
    stale = sorted(KNOWN_ASSERTION_FREE - found)
    assert not stale, (
        "%d exemption(s) name a test that now asserts something, or that no "
        "longer exists under that name:\n  %s\n\nDelete them from "
        "KNOWN_ASSERTION_FREE."
        % (len(stale), "\n  ".join("%s::%s" % pair for pair in stale)))


def test_the_census_can_actually_fail(tmp_path):
    """THE DELIBERATELY BROKEN FIXTURE, and this file needs one most of all.

    A census of checks that cannot fail, which itself cannot fail, would be the
    eighteenth instance and by some distance the funniest. So the scanner is
    pointed at a directory built here containing one test that asserts and one
    that does not, and it must find exactly the second.
    """
    (tmp_path / "test_fixture.py").write_text(
        "def test_this_one_asserts():\n"
        "    assert 1 == 1\n"
        "\n"
        "def test_this_one_does_not():\n"
        "    ' '.join(['a', 'b'])\n",
        encoding="utf-8")
    assert scan(tmp_path) == {("test_fixture.py", "test_this_one_does_not")}


def test_the_scanner_does_not_report_a_deliberate_refusal_test_as_debt(tmp_path):
    """The false-positive control, and the one that decides whether this survives.

    `with pytest.raises(...)` bodies frequently contain no `assert` at all, and
    they are the STRONGEST tests in this suite - every known-bad fixture is one.
    A census that flagged them would report most of the repository's real checks
    as debt, and the correct response to that census would be to delete it.
    """
    (tmp_path / "test_fixture.py").write_text(
        "import pytest\n"
        "\n"
        "def test_it_refuses():\n"
        "    with pytest.raises(ValueError):\n"
        "        int('not a number')\n"
        "\n"
        "def test_it_refuses_without_the_with_form():\n"
        "    pytest.raises(ValueError, int, 'not a number')\n",
        encoding="utf-8")
    assert scan(tmp_path) == set()
