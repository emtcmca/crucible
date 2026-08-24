"""The primary measure counted every row as a recurrence. JSON did it.

`scripts/cartographer-stability.py::_rows` builds `classes` as a TUPLE.
`json.dump` writes a tuple as an ARRAY and `json.load` returns a LIST. A list
never equals a tuple, so

    classes != ("CAP_MOVES_MONEY",)

was TRUE FOR EVERY ROW, and the primary measure reported **18 of 25** while its
own printout listed six of those rows as `CAP_MOVES_MONEY`. The real figure is
**12 of 25**.

WHY THIS WAS NEARLY UNCATCHABLE AND IS THE MOST DANGEROUS SHAPE HERE.
**The ruling was the same either way.** Section 4 fires on `>= 1`, and both 12
and 18 are `>= 1`, so the decision the pre-registration exists to make would
have been correct while the rate published beside it was inflated by half. A
wrong number pointing at the right decision survives every check that looks at
the decision. It was caught by reading the enumeration under the headline, not
by the headline.

This file pins the comparison against the ROUND-TRIPPED artifact, because the
round trip is the defect. Comparing in-memory tuples proves nothing.
"""

import importlib.util
import json
import pathlib

import pytest

# LOADED BY PATH. `scripts/` is not a package and `cartographer-stability.py` is
# not an importable module name (the hyphen). Importing it by spec is uglier
# than a rename and strictly better than testing a COPY of the function, which
# is what a rewritten helper here would be.
_SPEC = importlib.util.spec_from_file_location(
    "cartographer_stability",
    pathlib.Path(__file__).resolve().parent.parent / "scripts"
    / "cartographer-stability.py")
stability = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(stability)


def _artifact(tmp_path, rows_by_seed):
    """A minimal artifact in the shape `analyse` reads - written and re-read
    through JSON, so `classes` arrives as a list exactly as it does in life."""
    runs = [{"arm": "B", "index": i + 1, "seed": seed, "outcome": "OK",
             "rows": {"generate_qr_code": {"classes": list(classes),
                                           "confidence": 1.0,
                                           "citations": ["c"]}},
             "tokens": 1}
            for i, (seed, classes) in enumerate(sorted(rows_by_seed.items()))]
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps({
        "runs": runs, "executed_runs": len(runs), "planned_runs": len(runs),
        "total_tokens": len(runs)}), encoding="utf-8")
    return path


def test_a_row_that_says_CAP_MOVES_MONEY_is_not_counted_as_a_recurrence(
        tmp_path, capsys):
    """RED before the fix: reported 3 of 3. The three rows all say
    CAP_MOVES_MONEY, so the correct count is ZERO."""
    path = _artifact(tmp_path, {
        20260901: ("CAP_MOVES_MONEY",),
        20260902: ("CAP_MOVES_MONEY",),
        20260903: ("CAP_MOVES_MONEY",)})
    stability.analyse(str(path))
    out = capsys.readouterr().out
    assert "...NOT CAP_MOVES_MONEY     : 0" in out, out


def test_a_row_that_says_something_else_IS_counted(tmp_path, capsys):
    """The positive control. Without it the test above passes on a function
    that counts nothing at all."""
    path = _artifact(tmp_path, {
        20260901: ("CAP_MOVES_MONEY",),
        20260902: ("INERT",),
        20260903: ("INERT",)})
    stability.analyse(str(path))
    out = capsys.readouterr().out
    assert "...NOT CAP_MOVES_MONEY     : 2" in out, out


def test_the_real_artifact_reports_the_measured_twelve(tmp_path, capsys):
    """Against the SHIPPED artifact rather than a fixture, so the published
    number and the code that computes it cannot drift apart."""
    real = (pathlib.Path(__file__).resolve().parent.parent / "docs" / "proof"
            / "cartographer-stability-2026-08-24.json")
    if not real.exists():
        pytest.skip("the 50-run artifact is not in this checkout")
    stability.analyse(str(real))
    out = capsys.readouterr().out
    assert "arm B runs executed        : 25" in out, out
    assert "...NOT CAP_MOVES_MONEY     : 12" in out, out
    assert "BUILD the contradiction check" in out, out
