#!/usr/bin/env python3
"""probe-g7-g8.py - run G7 and G8 against the live project and write the proof.

READ-ONLY. Every gcloud call this makes is `get-iam-policy`, `describe`, or
`objects list`. It creates nothing, deletes nothing, and binds nothing. It does
not promote a policy version either: it calls `RealGate.preflight()`, which is
the assertion half, and stops there.

WHY THIS EXISTS SEPARATELY FROM `infra/verify_iam.py`
-----------------------------------------------------
`verify_iam.py` asserts the IAM documents. It does not run the G7a impersonation
probe, and it does not evaluate G7c. Those two are the assertions that are not
about what a policy document says but about what an identity can actually do,
and they are where the two live gaps turned out to be. This runs the whole of
G7 and G8 as `crucible.conductor.real_gate` will run them inside a campaign, so
the artifact on disk is the same evaluation the loop performs and not a
second implementation of it.

G7c IS NOW WIRED. IT USED TO BE HARDCODED TO `None`.
-----------------------------------------------------
Until 2026-08-22 this file passed `holdout_touch=None` on line 41, so G7c
reported UNEVALUABLE on every run and `absent_or_unevaluable: RUN_INVALID`
meant no scored run was possible. It now injects a real
`infra.holdout_touch.HoldoutTouchCounter`, which is READ-ONLY (`gcloud logging
read` plus `gcloud projects get-iam-policy`) and so belongs in a probe that
creates nothing.

  python scripts/probe-g7-g8.py
  python scripts/probe-g7-g8.py --holdout-since 2026-08-23T14:00:00Z
  -> docs/proof/L3-real-gate-G7-G8-YYYY-MM-DD.txt

READ THE `--holdout-expected` DEFAULT AS A CONTRACT VALUE, NOT A PREDICTION.
`expected_for_this_phase` is defined by a RUN. This probe is not a run, so
outside one the comparison is not meaningful and G7c will normally read FAIL
here. That is a true statement about a window in which no run happened, and it
is deliberately not massaged into a green line: what this probe demonstrates
about G7c is that the number now EXISTS and is derived from a live log, printed
in full in its own section below.
"""

import argparse
import datetime
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from crucible.conductor import real_gate as rg     # noqa: E402
from infra import holdout_touch as ht              # noqa: E402


def _gate_hook_line():
    """What `campaign.build_gate` actually returns, asked at generation time.

    A dated proof artifact carries its sentences forward forever. The one this
    replaced said the campaign's gate hook "was `lambda c, r: True`" and would
    have kept saying it into every file written after the hook was replaced -
    a false claim, dated, sitting in `docs/proof/`, which is precisely the
    directory whose whole value is that its contents are checkable.

    Failures are REPORTED, never swallowed into a flattering default: if the
    campaign cannot be imported here, the artifact says so rather than
    printing a sentence about a gate nobody looked at.
    """
    try:
        from crucible.conductor import campaign as C
        if getattr(C, "build_real_gate", None) is not rg.build_real_gate:
            return ("NOT the gate probed here - campaign does not build "
                    "crucible.conductor.real_gate. NO G7/G8 RESULT BELOW "
                    "DESCRIBES WHAT THE CAMPAIGN RUNS.")
        return ("campaign builds real_gate.build_real_gate -> RealGate, the "
                "same class probed below. It replaced a "
                "`promote=lambda c, r: True` stand-in on 2026-08-22.")
    except Exception as exc:                      # pragma: no cover - reported
        return "UNREADABLE (%s: %s). State it, do not guess it." % (
            type(exc).__name__, exc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout-since", default=ht.ATTESTATION_FLOOR_UTC,
                    help="RFC3339 UTC window start. Defaults to the attestation "
                         "floor: everything the audit log can speak to.")
    ap.add_argument("--holdout-expected", type=int, default=2,
                    help="expected_for_this_phase. 2 is the contract value; "
                         "outside a run there is no phase.")
    # MEASURED, not guessed. The first wired run of this script queried the log
    # seconds after its own G7a impersonation probes and saw NINE entries where
    # the probes should have added several more - Cloud Logging had not ingested
    # them yet. An undercount reads exactly like a pass, so the settle is on by
    # default and turning it off is the thing you have to ask for.
    ap.add_argument("--holdout-settle", type=float, default=45.0,
                    help="seconds to wait for Cloud Logging ingestion before "
                         "counting. 0 disables it and will UNDERCOUNT reads "
                         "made by this same probe run.")
    ap.add_argument("--reveal-sealed-names", action="store_true",
                    help="write sealed OBJECT NAMES into the proof file "
                         "verbatim. Off by default: this script writes into "
                         "docs/proof/, which is TRACKED and PUBLIC, and the "
                         "sealed object names describe each attack's pattern. "
                         "Use only under an explicit disclosure ruling.")
    args = ap.parse_args()

    day = datetime.date.today().isoformat()
    out_path = REPO / "docs" / "proof" / ("L3-real-gate-G7-G8-%s.txt" % day)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    env = rg.gcp_env(REPO)
    counter = ht.HoldoutTouchCounter(env, since=args.holdout_since,
                                     settle_seconds=args.holdout_settle)

    gate = rg.RealGate(
        ledger=None, run_id="probe", blob_writer=None, blob_reader=None,
        repo_root=REPO, holdout_touch=counter,
        holdout_expected=args.holdout_expected)
    findings = gate.preflight()
    bad = [f for f in findings if f["status"] != rg.PASS]

    lines = [
        "CRUCIBLE - G7 (SEAL INTEGRITY) and G8 (NON-SELF-APPROVAL), evaluated",
        "generated by scripts/probe-g7-g8.py  (READ-ONLY: no gcloud call here",
        "creates, deletes, or binds anything)",
        "project  : %s" % gate.env["CRUCIBLE_PROJECT"],
        "promoter : %s   <- read from scripts/gcp-env.sh, not typed here"
        % gate.promoted_by,
        "date     : %sZ" % datetime.datetime.utcnow().isoformat(timespec="seconds"),
        "gcloud   : %s" % _gcloud_version(),
        "",
        # WHAT THE GATE HOOK IS, READ AT RUN TIME. This block used to state
        # flatly that "until this ran, the campaign's gate hook was
        # `lambda c, r: True`" - true on 2026-08-21, false from 2026-08-22 when
        # RealGate landed, and STAMPED INTO EVERY DATED ARTIFACT THIS SCRIPT
        # WOULD EVER WRITE INTO docs/proof/. A proof file is the last place a
        # sentence should be unable to learn it has stopped being true.
        "gate hook: %s" % _gate_hook_line(),
        "G7 and G8 are the two gates whose failure mode is RUN INVALID, which",
        "is why they are probed separately from any campaign run.",
        "",
        rg.render(findings),
        "",
        "=" * 70,
        "%d assertions, %d PASS, %d not PASS"
        % (len(findings), len(findings) - len(bad), len(bad)),
        "",
    ]
    lines += _holdout_section(counter, args)
    if bad:
        lines += [
            "NOT A CLEAN RESULT, AND THAT IS THE POINT OF RUNNING IT.",
            "An UNEVALUABLE assertion is not a pass. G7's contract",
            "(contracts/gate_rule.v1.yaml) sends `absent_or_unevaluable` to",
            "RUN INVALID precisely so a check that measured nothing cannot be",
            "scored as a check that held.",
            "",
        ]
    lines += [
        "What this does NOT show, stated so the claim stays exactly true:",
        "  * The operator (a human with roles/owner) can read everything here.",
        "    You are the trust root and no control defends against you. What",
        "    changed on 2026-08-22 is only that an operator read of the sealed",
        "    bucket now LEAVES A RECORD, and holdout_touch does not exempt the",
        "    human from its permitted set. A record is not a defence.",
        "  * G7c attests from %s FORWARD and says" % ht.ATTESTATION_FLOOR_UTC,
        "    nothing about the seal's earlier lifetime. Data Access logging was",
        "    enabled 2026-08-22 and Cloud Logging is not retroactive: a G7a",
        "    probe at 18:27:30Z that day left NO entry (denials are logged, so",
        "    that is evidence of absence of coverage) while a read at",
        "    19:31:10Z did. The bucket has existed since 2026-08-20.",
        "  * The sealed BIGQUERY DATASET is not covered. The live auditConfig",
        "    names storage.googleapis.com only, so a read of the sealed dataset",
        "    would be counted as zero touches.",
        "  * Nothing was promoted. This is preflight only; the write path with",
        "    its read-back assertion is exercised by tests/test_real_gate.py",
        "    against a local blob store, and has NEVER run against GCS.",
        "  * A PASS on an IAM document is a snapshot, not a guarantee. The",
        "    whole point of re-asserting every run is that a grant made later",
        "    is invisible to a check that ran earlier.",
    ]
    # REDACTED AT THE BOUNDARY WHERE THE BYTES BECOME PUBLIC.
    #
    # `render_tally` prints each matched entry's full resource name, and that
    # is right for an operator staring at a terminal. This script then writes
    # the same text into `docs/proof/`, which is TRACKED IN A PUBLIC REPO -
    # and sixty lines away in `record-f4-transfer.py` the runner refuses to
    # publish those same names, because the commitment's `_withheld` says they
    # describe each attack's pattern.
    #
    # Two incompatible disclosure claims, one leak path. It has not fired: the
    # committed proof files carry no sealed object names, because no sealed
    # read has happened yet. It would fire on the FIRST recovery run after a
    # terminal failure, which is the one moment nobody will be reviewing a
    # proof file's contents.
    #
    # The redaction is per-object and STABLE, so the audit record still says
    # how many distinct objects were touched and lets an auditor with bucket
    # access match each line to an object. What it does not do is print the
    # slug. Whether the full names should be published after a terminal
    # failure is a real question the pre-registration leaves open, and it is
    # Eric's to rule on - so this defaults to withholding and takes an
    # explicit flag, rather than deciding by omission.
    #
    # TWO THINGS THIS IS NOT, BOTH OF WHICH THE PREVIOUS COMMENT CLAIMED OR
    # IMPLIED, AND A REVIEWER DISPROVED ONE OF THEM BY REPRODUCTION.
    #
    #   * It is NOT a guarantee about "sections added later". It rewrites the
    #     URI shapes the current renderer emits plus bare object names matching
    #     the sealed family's convention. A future section that prints a name
    #     in some other shape is not covered, and saying otherwise is the
    #     widened claim this project keeps catching in itself.
    #   * It is PSEUDONYMISATION, NOT CONCEALMENT. The digest is unsalted and
    #     the object-name format is public, so a determined reader can confirm
    #     a guessed name offline. That is acceptable for a last-line safety
    #     net and it is NOT a substitute for the disclosure ruling.
    #
    # It is defence in depth over one renderer, and the ruling is still owed.
    body = "\n".join(lines) + "\n"
    if not args.reveal_sealed_names:
        body, hidden = _redact_sealed_objects(body, gate.env)
        if hidden:
            body += (
                "\nSEALED OBJECT NAMES REDACTED: %d distinct object(s), shown "
                "as sha256-8 digests above.\nThe digests are stable, so an "
                "auditor holding the bucket can match every line to an "
                "object.\nRe-run with --reveal-sealed-names ONLY under an "
                "explicit disclosure ruling: this file is committed to a "
                "public repository.\n" % hidden)
    out_path.write_text(body, encoding="utf-8")

    # Postcondition, not the exit code: the file on disk is the artifact.
    print(out_path.read_text(encoding="utf-8"))
    print("wrote %s (%d bytes)" % (out_path, out_path.stat().st_size))
    return 1 if bad else 0


def _redact_sealed_objects(text, env):
    """Replace sealed OBJECT names with stable digests. Returns (text, count).

    Operates on the rendered text rather than on the tally structure because
    this is the last point before the bytes are written. That covers every
    section that reaches the file - but only in the SHAPES listed below.

    WHAT IS COVERED:
      * `.../buckets/<sealed-bucket>/objects/<name>`
      * `gs://<sealed-bucket>/<name>`
      * a bare `<name>` matching the sealed family's object convention

    WHAT IS NOT: a name printed in any other shape. An earlier version of this
    docstring claimed it protected "sections added later by someone who never
    read this function". A reviewer reproduced a bare object name surviving
    with `hidden=0`, which is what prompted the third pattern - and the claim
    is now scoped rather than repeated, because a bare name was only the
    instance and the general statement was the defect.

    This is PSEUDONYMISATION. The digest is unsalted and the name format is
    public, so a guessed name can be confirmed offline. It is a safety net
    under a disclosure ruling, not the ruling.
    """
    import hashlib
    import re

    bucket = (env.get("CRUCIBLE_SEALED_BUCKET") or "").replace("gs://", "")
    if not bucket:
        return text, 0

    seen = set()

    def sub(match):
        obj = match.group("obj")
        seen.add(obj)
        digest = hashlib.sha256(obj.encode("utf-8")).hexdigest()[:8]
        return match.group("head") + "sha256-8:" + digest

    # `.../buckets/<bucket>/objects/<name>` and `gs://<bucket>/<name>`.
    pattern = re.compile(
        r"(?P<head>(?:buckets/%s/objects/)|(?:gs://%s/))(?P<obj>[^\s\"']+)"
        % (re.escape(bucket), re.escape(bucket)))
    text = pattern.sub(sub, text)

    # AND A BARE NAME, which a reviewer reproduced surviving untouched.
    #
    # THE PATTERN IS SEALED_IO'S OWN, not one written again here. `_SAFE_NAME`
    # is the regex that validates every name before it is requested, so it is
    # the single definition of what a sealed object is called, and importing it
    # means this cannot drift from the thing it is trying to match.
    #
    # A hand-rolled `F4-.*\.json` was tried first and its own control test
    # caught it redacting `F4-MANIFEST.json` - a PUBLISHED artifact, the one
    # that carries the `atk_` ids on purpose. Over-redaction is not the safe
    # direction here: it corrupts the proof file while looking careful.
    from crucible.transfer.sealed_io import _SAFE_NAME

    def sub_bare(match):
        obj = match.group(0)
        if not _SAFE_NAME.match(obj):
            return obj
        seen.add(obj)
        return "sha256-8:" + hashlib.sha256(obj.encode("utf-8")).hexdigest()[:8]

    bare = re.compile(r"\bF4-dest-\d{2}-[a-z0-9-]+\.json\b")
    text = bare.sub(sub_bare, text)
    return text, len(seen)


def _holdout_section(counter, args):
    """G7c's evidence, printed whatever the finding said.

    The finding above is one line and a verdict. This is the number's
    provenance: the exact read-only command, the window, and every entry that
    filter matched, broken out by kind. A judge who cannot re-derive a number
    has been asked to take the builder's word for it, which is the thing this
    whole project refuses to do.
    """
    head = [
        "-" * 70,
        "G7c EVIDENCE - holdout_touch_count, and how it was derived",
        "-" * 70,
        "Until 2026-08-22 this probe passed holdout_touch=None, so G7c was",
        "UNEVALUABLE on every run and no scored run was possible.",
        "",
    ]
    # REUSE the tally the gate's own G7c call already produced. Recomputing
    # would query the log a second time, sleep the ingestion settle a second
    # time, and - the part that matters - could print a DIFFERENT number beside
    # the finding it is supposed to explain.
    if counter.last_tally is not None:
        return head + _tally_lines(counter.last_tally, args)
    try:
        result = counter.compute()
    except ht.HoldoutTouchInvalid as e:
        return head + [
            "RUN INVALID - THE COUNTER WORKED AND CAUGHT SOMETHING.",
            "  %s" % e,
            "",
        ]
    except Exception as e:                           # noqa: BLE001
        return head + [
            "UNEVALUABLE - the counter declined to guess, which is not zero:",
            "  %s" % e,
            "",
        ]
    return head + _tally_lines(result, args)


def _tally_lines(result, args):
    """The tally, plus the two things a reader would otherwise get wrong."""
    out = [
        ht.render_tally(result),
        "",
        "  expected_for_this_phase used above: %d" % args.holdout_expected,
        "  A probe is not a run, so outside a run this comparison is not",
        "  meaningful. What it shows is that the number now exists.",
        "",
    ]
    if result["count"] == args.holdout_expected:
        out += [
            "  ** THE G7c PASS ABOVE IS A COINCIDENCE. READ IT AS ONE. **",
            "  The count equals %d because ONE `gcloud storage cat` emits two"
            % args.holdout_expected,
            "  granted storage.objects.get entries - a metadata fetch and a",
            "  media download of the same object. It is NOT evidence that the",
            "  expected value is right, and no run has happened. A green line",
            "  produced by an accident is the shape this project keeps killing,",
            "  so it is printed rather than suppressed.",
            "",
            "  The expected value is also contradicted by its own spec. A run",
            "  that evaluates a 24-episode sealed holdout cannot produce 2 by",
            "  any counting rule over this log: 24 objects means at least 24",
            "  granted reads. measurement-spec.md:946's 2 counts EVALUATION",
            "  PASSES (the v0 arm and the vFinal arm), a grouping the audit log",
            "  does not carry. Either the unit or the value needs restating,",
            "  and this module will not pick one for you.",
            "",
        ]
    return out + [
        "  WHY A ZERO HERE WOULD MEAN SOMETHING: before any count is returned,",
        "  the SAME compiled filter - both server-side narrowings included, and",
        "  excluding a sentinel principal that cannot exist - is run over the",
        "  whole attestable window and must match at least one GRANTED CONTENT",
        "  READ. A misspelled bucket, a renamed log, an over-broad exclusion,",
        "  and a seal nobody touched otherwise produce identical output.",
        "",
        "  WHY THE COUNT ABOVE IS NOT ZERO, AND WHY THAT IS NOT AN ALARM: this",
        "  window is the ATTESTATION FLOOR, not a run window, and it contains",
        "  every read since 2026-08-22. Seven of them are operator reads from",
        "  the canary move that day. They are ATTESTED - named one by one, with",
        "  the gcloud invocation that made each - in",
        "  %s," % ht.ATTESTED_READS_RECORD,
        "  and they are COUNTED AND SHOWN above rather than excluded. The",
        "  assertion a reader should look at is the UNATTESTED line: a granted",
        "  read from outside the permitted set that no record explains. That is",
        "  what marks a run INVALID, and it is not softened by anything here.",
        "",
        "  The operator was NOT added to the permitted set and the window was",
        "  NOT moved forward. Either would have made this line green by looking",
        "  away, which is the move this whole project refuses.",
        "",
    ]


def _gcloud_version():
    try:
        exe = rg.verify_iam._gcloud_exe()            # noqa: SLF001
        return subprocess.run([exe, "version"], capture_output=True,
                              text=True).stdout.splitlines()[0]
    except Exception as e:                           # noqa: BLE001
        return "unavailable: %s" % e


if __name__ == "__main__":
    raise SystemExit(main())
