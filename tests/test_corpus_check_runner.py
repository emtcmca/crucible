"""test_corpus_check_runner.py - a check with no input must report NOT-RUN.

`check.py` says it in its own docstring: *it reports NOT-RUN, never OK, for a
check whose input is absent.* The fault-reason_code row did not, and printed
`PASS pairs_checked=0`.

**Why the zero case is reachable on a corpus that looks complete.** The row's
`skip_if_absent` asks whether `corpus/pairs.json` exists. That is a different
question from whether any pair RESOLVES to two instances on disk: three of the
worksheet records are CUT and carry no slugs by design, two more are sealed pairs
whose instances live only in a gitignored directory, and on a fresh public clone
`corpus/sealed/` is absent entirely. A pair file full of records can therefore
present zero pairs to the lint, and the row would print the same green it prints
over a fully authored corpus.

`CONVENTIONS.md` section 8 rule 2 - a check that cannot fail is not measuring
anything - and the lint being defended here is the one standing between the
corpus and a pair scored on NB-01's deliberate exemption. **No gate in the build
catches a false positive.** A green row over zero pairs is how one gets in.
"""

import pytest

from corpus.check import Runner
from corpus.errors import CorpusError, NotRun


def _row(runner):
    assert len(runner.rows) == 1
    return runner.rows[0]


def test_a_check_that_finds_no_input_reports_not_run():
    r = Runner()
    r.run("fault reason_code lint",
          lambda: (_ for _ in ()).throw(NotRun("no pair resolves to two instances")))
    name, status, detail = _row(r)
    assert status == "NOT-RUN"
    assert "no pair resolves" in detail


def test_not_run_is_not_counted_as_having_run():
    """`check.py` exits 2 - not 0 - when nothing could be run. A NOT-RUN row
    that satisfied `ran` would turn that exit 2 into an exit 0."""
    r = Runner()
    r.run("fault reason_code lint", lambda: (_ for _ in ()).throw(NotRun("empty")))
    assert r.ran is False
    assert r.failed is False


def test_not_run_is_not_a_failure_either():
    """The two verdicts stay apart. Collapsing NOT-RUN into FAIL would make an
    unauthored corpus indistinguishable from a broken one, and someone would
    weaken the check to clear the red."""
    r = Runner()
    r.run("x", lambda: (_ for _ in ()).throw(NotRun("empty")))
    assert r.failed is False


def test_a_real_defect_still_fails():
    r = Runner()
    r.run("x", lambda: (_ for _ in ()).throw(CorpusError("E_X", "a real defect")))
    name, status, detail = _row(r)
    assert status == "FAIL"
    assert "E_X" in detail


def test_a_check_with_input_still_passes():
    r = Runner()
    r.run("x", lambda: {"pairs_checked": 22})
    name, status, detail = _row(r)
    assert status == "PASS"
    assert "pairs_checked=22" in detail


def test_the_strawman_runner_cannot_tell_the_two_apart():
    """The version this replaced, kept demonstrable rather than described.

    It returns the same green for a lint that examined 22 pairs and one that
    examined none, which is exactly the shape section 8 rule 2 forbids."""
    def permissive_run(fn):
        return ("PASS", "pairs_checked=%d" % fn())

    assert permissive_run(lambda: 22)[0] == permissive_run(lambda: 0)[0] == "PASS"
