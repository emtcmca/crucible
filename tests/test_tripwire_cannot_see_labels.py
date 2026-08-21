"""test_tripwire_cannot_see_labels.py - the test measurement-spec already claimed.

`measurement-spec.md:987-989` states that the blind-input boundary is enforced
"by the function's arity and by a unit test asserting the Tripwire module cannot
import the corpus label schema."

**That test did not exist.** No match in `tests/`, `crucible/`, or `scripts/`,
and `import_lint.py`'s deny list covered LLM clients only. The property was true
on the day the sentence was written and stayed true by accident. A specification
that describes a check nobody wrote is the exact failure this project keeps
finding in itself: an instrument reporting on its own behalf.

Written 2026-08-21, on ADR-0016's finding. The clause in the spec is now true.

WHY IT MATTERS. The TRIPWIRE answers BREACH or CLEAN from the recorded call log
and the frozen Objective Set. Corpus instances carry the attack family, the
expected verdict, and `near_miss`. An oracle that can reach a label is grading
the answer key, and every number downstream of it measures the corpus's opinion
of itself while looking exactly like a measurement.
"""

import pathlib

import pytest

from crucible.tripwire.import_lint import (
    LABEL_BEARING_MODULES,
    run_import_lint,
    scan_source,
)

REPO = pathlib.Path(__file__).resolve().parent.parent


def test_the_pure_code_components_import_no_label_bearing_module():
    """The live assertion, over `crucible/tripwire` and `crucible/warden`."""
    findings = run_import_lint()
    labelled = [f for f in findings if f.module in LABEL_BEARING_MODULES]
    assert labelled == [], (
        "a pure-code judging component can reach the corpus labels:\n  "
        + "\n  ".join(str(f) for f in labelled))


def test_the_whole_lint_is_clean_not_merely_the_label_half():
    assert run_import_lint() == []


# --------------------------------------------------------------------------
# THE LINT MUST BE ABLE TO FAIL. Same principle as the sealed-family selftest
# and the nine known-bads: a check that has never been seen failing is not
# evidence that the thing it checks is true.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("source,why", [
    ("from corpus.model import Instance", "a plain from-import of the corpus"),
    ("import corpus", "a bare import of the package"),
    ("import corpus.load as loader", "an aliased submodule import"),
    ("from fixtures.benign import something", "the benign suite the floor is computed against"),
    ("import importlib\nm = importlib.import_module('corpus.schema')",
     "string indirection, which a grep would miss"),
    ("m = __import__('corpus')", "the other string-indirection form"),
])
def test_the_lint_catches_every_way_in(source, why):
    findings = scan_source(source, path="<planted:%s>" % why)
    assert findings, "the lint did not catch %s" % why
    assert findings[0].module in LABEL_BEARING_MODULES


def test_the_lint_does_not_fire_on_a_name_that_merely_starts_the_same():
    """Prefix matching is on DOTTED SEGMENTS, never on characters.

    `corpus_synthetic` is a real test helper in this repo. If the lint matched
    substrings it would flag that module, somebody would relax the rule to make
    the suite green, and a relaxed lint is a lint that gets relaxed again.
    """
    assert scan_source("import corpus_synthetic") == []
    assert scan_source("from fixtures_helper import x") == []


def test_a_relative_import_is_not_treated_as_an_escape():
    """`from .known_bad import ...` cannot leave the package, so it is not a
    finding. This is asserted so that tightening the lint later cannot silently
    start flagging the tripwire's own internal wiring."""
    assert scan_source("from .known_bad import KNOWN_BAD_IDS") == []


def test_an_unparseable_module_is_reported_rather_than_skipped():
    """`unparseable` must never read as `clean`."""
    findings = scan_source("def broken(:\n", path="<planted:syntax>")
    assert findings and findings[0].module == "<unparseable>"


def test_the_spec_clause_this_file_exists_to_make_true_is_still_there():
    """If the clause is ever struck from the spec, this test should be deleted
    with it rather than left standing as a check on nothing. Catching the
    removal here is cheaper than discovering an orphan test later."""
    spec = (REPO / "docs" / "measurement-spec.md").read_text(encoding="utf-8")
    assert "cannot import the corpus" in spec
