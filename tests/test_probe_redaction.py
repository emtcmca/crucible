"""The proof file this script writes is TRACKED AND PUBLIC.

Review 9's P2. `render_tally` prints each matched entry's full resource name -
right for an operator at a terminal - and `probe-g7-g8.py` then writes that
text into `docs/proof/`. Sixty lines away in `record-f4-transfer.py` the runner
refuses to publish those same object names, because the commitment's
`_withheld` says they describe each attack's pattern.

The leak has NOT fired: no committed proof file carries a sealed object name,
because no sealed read has happened yet. It fires on the FIRST recovery run
after a terminal failure - the one moment nobody is reviewing a proof file.
"""
import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "probe_g7_g8", ROOT / "scripts" / "probe-g7-g8.py")
probe = importlib.util.module_from_spec(_spec)
sys.modules["probe_g7_g8"] = probe
_spec.loader.exec_module(probe)

ENV = {"CRUCIBLE_SEALED_BUCKET": "gs://crucible-sealed-x7"}

# A REALISTIC LINE, INVENTED. These object names are made up for this test -
# the real ones are in a bucket this process holds no read on, and inventing
# them is the only way to test the redaction without touching the seal.
TALLY = (
    "    READ   2026-08-31T21:00:01Z  crucible-sealed-eval  "
    "projects/_/buckets/crucible-sealed-x7/objects/"
    "F4-dest-07-invented-slug.json\n"
    "    READ   2026-08-31T21:00:02Z  crucible-sealed-eval  "
    "projects/_/buckets/crucible-sealed-x7/objects/"
    "F4-dest-08-invented-slug.json\n"
)


def test_sealed_object_names_do_not_survive_redaction():
    out, hidden = probe._redact_sealed_objects(TALLY, ENV)
    assert "F4-dest-07-invented-slug.json" not in out, (
        "a sealed object name survived into text bound for a public repo")
    assert "F4-dest-08-invented-slug.json" not in out
    assert hidden == 2, hidden


def test_the_audit_record_still_distinguishes_the_objects():
    """Redaction must not destroy what the pre-registration requires.

    The failure record has to be audit-recoverable - what was read, when, by
    which identity. Collapsing every object to the same token would satisfy
    "no names" and destroy "what was read", which is the trade this must not
    make.
    """
    out, _ = probe._redact_sealed_objects(TALLY, ENV)
    digests = [ln.split("sha256-8:")[1].strip() for ln in out.splitlines()
               if "sha256-8:" in ln]
    assert len(digests) == 2, out
    assert digests[0] != digests[1], (
        "two different objects redacted to the same token, so the record no "
        "longer says how many distinct objects were touched")
    assert "2026-08-31T21:00:01Z" in out and "crucible-sealed-eval" in out, (
        "redaction removed the timestamp or the principal, which the "
        "pre-registration requires the failure record to carry")


def test_redaction_is_stable_across_calls():
    """An auditor holding the bucket must be able to match line to object."""
    first, _ = probe._redact_sealed_objects(TALLY, ENV)
    second, _ = probe._redact_sealed_objects(TALLY, ENV)
    assert first == second


def test_a_gs_url_form_is_redacted_too():
    text = "  wrote gs://crucible-sealed-x7/F4-dest-99-invented.json ok"
    out, hidden = probe._redact_sealed_objects(text, ENV)
    assert "F4-dest-99-invented.json" not in out
    assert hidden == 1


def test_nothing_else_is_touched():
    """THE CONTROL. A function that redacted everything would pass the tests
    above and destroy the proof file."""
    text = ("project  : crucible-hack-2026\n"
            "promoter : crucible-gate\n"
            "  wrote gs://crucible-policies-x7/candidate.yaml\n")
    out, hidden = probe._redact_sealed_objects(text, ENV)
    assert out == text, "redaction touched text outside the sealed bucket"
    assert hidden == 0


def test_redaction_is_the_default_in_the_scripts_own_wiring():
    """WIRED, NOT MERELY WRITTEN. Three lifecycle calls in this repository were
    correct, tested and unreachable from the function meant to call them."""
    source = (ROOT / "scripts" / "probe-g7-g8.py").read_text(encoding="utf-8")
    assert "if not args.reveal_sealed_names:" in source, (
        "the redaction helper is not called on the default path, so the "
        "tracked write still carries whatever render_tally produced")
    assert 'action="store_true"' in source, (
        "--reveal-sealed-names must default to OFF; a flag that defaults to "
        "revealing is a redaction nobody applies")
    body = source.split("def _redact_sealed_objects")[0]
    assert body.index("if not args.reveal_sealed_names:") < body.index(
        "out_path.write_text("), (
        "the redaction runs after the file is written, which is not a "
        "redaction")
