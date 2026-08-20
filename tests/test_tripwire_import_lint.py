"""test_tripwire_import_lint.py - L4's FIRST work item, and it is the negative check.

`CONVENTIONS.md` 2.1 marks the TRIPWIRE and the REGRESSION_WARDEN "pure code",
and 7 permits only four claims to be called STRUCTURAL - one of which is "the
TRIPWIRE's and WARDEN's inability to call a model". That claim is structural only
if something enforces it. A docstring saying "contains no model" is a
CONVENTION; a lint that fails the build is an ENFORCEMENT ARTIFACT, and the
difference is exactly the one 7 draws between the two lists.

The lint is proven three ways here, in increasing strength:

  1  a synthetic offending module in a temp directory is flagged
  2  a look-alike module name (googleapiclient) is NOT flagged - a lint that
     flags everything is as useless as one that flags nothing, and prefix
     matching on "google" is the plausible wrong implementation
  3  AN OFFENDING FILE IS WRITTEN INTO THE REAL crucible/tripwire/ PACKAGE AND
     THE LINT MUST FAIL, then it is removed. This is the only one of the three
     that proves the lint is POINTED AT THE RIGHT DIRECTORY. A lint with a
     correct module list and a wrong root passes forever and measures nothing.

The 403 half of the same claim (no aiplatform.user role) belongs to L1's IAM
work and is NOT asserted here - logging the drop rather than implying coverage
(section 8 rule 9).
"""

import pathlib
import textwrap

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent

from crucible.tripwire.import_lint import (  # noqa: E402
    DEFAULT_ROOTS,
    LLM_CLIENT_MODULES,
    run_import_lint,
)


# --------------------------------------------------------------------------
# The lint must be aimed at both owned packages, or half the claim is unbacked.
# --------------------------------------------------------------------------

def test_default_roots_cover_both_owned_packages():
    names = {pathlib.Path(r).name for r in DEFAULT_ROOTS}
    assert "tripwire" in names
    assert "warden" in names, (
        "the WARDEN is listed model-free in CONVENTIONS 2.1 alongside the "
        "TRIPWIRE. A lint over only one of them backs only one of the claims.")
    for r in DEFAULT_ROOTS:
        assert (REPO / r).is_dir(), "%s is not a directory" % r


def test_the_module_list_is_not_empty():
    """A lint whose denylist is empty passes forever. That is the failure shape
    this whole file exists to make impossible, so it is asserted directly."""
    assert len(LLM_CLIENT_MODULES) >= 5
    for expected in ("google.genai", "vertexai", "openai", "anthropic"):
        assert expected in LLM_CLIENT_MODULES


# --------------------------------------------------------------------------
# The real packages, as they stand.
# --------------------------------------------------------------------------

def test_the_real_packages_are_clean():
    findings = run_import_lint()
    assert findings == [], (
        "an LLM client import reached a pure-code package:\n  "
        + "\n  ".join(str(f) for f in findings))


# --------------------------------------------------------------------------
# Proof 1 and 2 - synthetic offenders and one look-alike.
# --------------------------------------------------------------------------

OFFENDERS = [
    ("plain import", "import openai\n"),
    ("dotted import", "import google.genai\n"),
    ("aliased import", "import vertexai as v\n"),
    ("from import", "from vertexai.generative_models import GenerativeModel\n"),
    ("submodule from import", "from google.genai import types\n"),
    ("importlib by string", 'import importlib\nm = importlib.import_module("anthropic")\n'),
    ("dunder import by string", 'm = __import__("openai")\n'),
    ("deferred import inside a function",
     "def score(e):\n    import openai\n    return openai\n"),
]


@pytest.mark.parametrize("label,src", OFFENDERS, ids=[o[0] for o in OFFENDERS])
def test_synthetic_offender_is_flagged(tmp_path, label, src):
    (tmp_path / "offender.py").write_text(src, encoding="utf-8")
    findings = run_import_lint([tmp_path])
    assert findings, "%s was not flagged: %r" % (label, src)


NON_OFFENDERS = [
    ("look-alike prefix", "import googleapiclient\n"),
    ("look-alike prefix, from", "from googleapiclient import discovery\n"),
    ("a word containing a module name in a string",
     'MSG = "this module calls no openai client, deliberately"\n'),
    ("stdlib", "import json\nimport hashlib\n"),
    ("our own package", "from crucible.canon import canonicalize\n"),
]


@pytest.mark.parametrize("label,src", NON_OFFENDERS, ids=[o[0] for o in NON_OFFENDERS])
def test_look_alikes_are_not_flagged(tmp_path, label, src):
    """A lint that flags everything is as useless as one that flags nothing.

    `googleapiclient` is the specific trap: a prefix match on "google" catches
    it, and then the lint gets relaxed the first time somebody needs GCS.
    """
    (tmp_path / "innocent.py").write_text(src, encoding="utf-8")
    findings = run_import_lint([tmp_path])
    assert findings == [], "%s was wrongly flagged: %s" % (label, findings)


# --------------------------------------------------------------------------
# Proof 3 - THE ONE THAT MATTERS. Offend the real tree; the lint must fail.
# --------------------------------------------------------------------------

def test_lint_fails_when_the_real_tripwire_package_is_offended():
    """Writes an offending module into the REAL package, asserts the lint fails,
    and removes it. Proves the lint's ROOTS are right, which proofs 1 and 2
    cannot: a correct module list aimed at an empty directory passes forever.
    """
    planted = REPO / "crucible" / "tripwire" / "_planted_offender_do_not_commit.py"
    assert not planted.exists()
    planted.write_text(textwrap.dedent("""\
        # Planted by tests/test_tripwire_import_lint.py and removed in the same
        # test. If this file is on disk after a test run, the run crashed.
        import google.genai
        """), encoding="utf-8")
    try:
        findings = run_import_lint()
        assert findings, (
            "THE IMPORT LINT DID NOT SEE AN LLM CLIENT IMPORT INSIDE "
            "crucible/tripwire/. The lint is not measuring the package it "
            "claims to measure, and the 'contains no model' claim is a "
            "convention wearing an enforcement label.")
        assert any("google.genai" in str(f) for f in findings)
    finally:
        planted.unlink()
    assert run_import_lint() == [], "the planted file outlived the test"


def test_lint_fails_when_the_real_warden_package_is_offended():
    """Same proof, other package. Both halves of the claim, or neither."""
    planted = REPO / "crucible" / "warden" / "_planted_offender_do_not_commit.py"
    assert not planted.exists()
    planted.write_text("from anthropic import Anthropic\n", encoding="utf-8")
    try:
        findings = run_import_lint()
        assert findings, "the lint does not reach crucible/warden/"
    finally:
        planted.unlink()
    assert run_import_lint() == []
