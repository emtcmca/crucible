"""view.py - the offline replay viewer's rendering.

Plain text, fixed width, no dependencies, no colour. It is read on a projector
at 1080p during a demo and in a terminal by a stranger who cloned a public repo,
and those two audiences want the same thing: every figure next to the label that
makes it mean something.

THE RULE THIS FILE ENFORCES, FROM `CONVENTIONS.md` SECTION 7
------------------------------------------------------------
The precise claim is the impressive one, and it is the only one that survives a
judge opening the file. So:

  * Every count printed here is a CENSUS OF THE FILE, never a result. This
    viewer does not compute an attack success rate and does not intend to. A
    rate needs a denominator decision (TARGET_FAULT is neither breach nor
    non-breach and leaves the denominator), and that decision belongs to the
    component that owns the measurement, not to the thing that draws it.
  * `k = 1`, so "single-sample, no stability estimate" is printed with the
    census, permanently, rather than attached to figures later.
  * The SEP-BY split prints in the same block, because a suite the
    APPROVAL_ORACLE separates produces IDENTICAL headline numbers to one the
    policy separates and only that ratio tells them apart.
  * The upper bound on unobserved regression is COMPUTED from the rule of
    three, and printed only when the arithmetic actually applies. `docs/lanes/
    L6-evidence.md` section 6: if a number cannot be stated with its label in
    the space available, cut the number, not the label. The same rule going the
    other way says a bound whose precondition does not hold is cut, not fudged.

WHAT IS DELIBERATELY ABSENT
---------------------------
Nothing has been measured on this project as of 2026-08-20, so this file states
no result. What it builds is the machinery that will carry results with their
labels attached when there are results, which is the opposite order from writing
the sentences first and hoping the numbers arrive to fit them.
"""

import argparse
import io
import json
import pathlib
import sys

from .bundle import read_bundle
# CONVENTIONS section 4, as amended by ruling 43: the benign denominator is fixed
# permanently at 26. IMPORTED, NOT RESTATED - this module carried its own copy of
# the value until 2026-08-22, and when ruling 43 moved the number the copy stayed
# at 24, which silently turned `regression_upper_bound` into a function that
# returns None on every real bundle. A gate that stops printing is quieter than a
# gate that prints the wrong number, and it survived a full green suite.
from .integrity import BENIGN_DENOMINATOR, BundleRejected

WIDTH = 96

# Which day each lock freezes on, and the one-line reason a reader needs. Kept
# beside the renderer rather than in the schema's $comment because a viewer that
# prints a hash with no context prints noise.
LOCK_NOTES = (
    ("gate_rule_hash", "D2", "the rule existed before anything was promoted"),
    ("target_agent_hash", "D3", "covers runtime source, not just tool names"),
    ("manifest_hash", "D3", "capability manifest Part A - the tool surface"),
    ("objective_set_hash", "D3", "the definition of breach"),
    ("corpus_hash", "D5", "fifth lock, first half"),
    ("derived_schema_hash", "D5", "second half, gated on label-blindness"),
)


def _out():
    """UTF-8 stdout. The specs carry arrows and section signs, and on Windows
    the default console codec is cp1252 - printing a finding would crash the
    viewer, which makes a real defect look like a broken tool."""
    if hasattr(sys.stdout, "buffer"):
        return io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                errors="replace", line_buffering=True)
    return sys.stdout


def rule(char="-"):
    return char * WIDTH


# Where the note column starts: "  " + 16 + " " + 14 + " " + 6 + " ".
NOTE_COL = 2 + 16 + 1 + 14 + 1 + 6 + 1

# Where the header's value column starts: "  " + 10 + "  ".
HEADER_COL = 2 + 10 + 2


def _wrap_note(text, width):
    """Split a note into a first line and continuation lines.

    The integrity notes are the useful part of the table and some of them are
    long - the policy-chain row has to say what it did NOT verify, which is the
    whole reason that row exists. Truncating it would delete exactly the caveat
    that keeps the row honest, so it wraps instead. `docs/lanes/L6-evidence.md`
    section 6: cut the number, not the label.
    """
    words = []
    for word in str(text).split():
        # HARD-SPLIT a word that cannot fit on a line by itself. Found by
        # running the README's own commands from a fresh clone in a deep
        # temporary directory: the bundle PATH is a single unbreakable token,
        # and this function silently emitted a 130-column line for it. The
        # width test had passed for a hundred runs because the development
        # checkout happens to sit at `C:\dev\crucible-wt-L6`. A check that
        # holds only for the author's directory layout is not measuring the
        # property it names.
        while len(word) > width:
            words.append(word[:width])
            word = word[width:]
        words.append(word)

    lines, current = [], ""
    for word in words:
        candidate = word if not current else current + " " + word
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return (lines[0] if lines else ""), lines[1:]


def regression_upper_bound(failures, denominator):
    """The rule of three, or None when it does not apply.

    With zero failures observed in n trials, the true rate is bounded above by
    roughly 3/n at 95% confidence. At n = 26 that is ~11.5%, and that exact
    number is what gets spoken rather than "no legitimate behavior was lost" -
    which is a claim the data cannot support at any sample size.

    THE FIGURE MOVED WITH THE DENOMINATOR. Ruling 43 took the benign suite from
    24 to 26, so the bound went 12.5% -> ~11.5%. It is COMPUTED here, from
    `BENIGN_DENOMINATOR`, precisely so it cannot be quoted against a corpus it
    was not measured on. `README.md` and `docs/CONVENTIONS.md` section 4 still
    say 12.5%; that is reported to the coordinator rather than rewritten here,
    because which number is spoken on camera is a ruling, not a lane's edit.

    Returns None rather than a softened number when a failure was observed,
    because the rule of three is a bound on an UNOBSERVED rate and simply does
    not apply once something has been observed.
    """
    if denominator != BENIGN_DENOMINATOR or failures != 0:
        return None
    return 3.0 / denominator * 100.0


def _benign_label(bundle):
    results = bundle.get("fixture_results") or []
    if not results:
        return ("benign fixture results are not present in this bundle, so no "
                "bound is stated")
    failures = sum(1 for r in results if r.get("passed") is False)
    bound = regression_upper_bound(failures, len(results))
    if bound is None:
        return ("%d of %d benign fixtures failed. The rule of three bounds an "
                "UNOBSERVED rate and does not apply here."
                % (failures, len(results)))
    return ("0 of %d benign fixtures failed, which bounds the true regression "
            "rate at ~%.1f%%. NEVER 'no legitimate behavior was lost'."
            % (len(results), bound))


def _sep_by_label(bundle):
    split = bundle.get("sep_by_split") or {}
    return ("%s policy-separated / %s APPROVAL_ORACLE-separated"
            % (split.get("policy_separated"), split.get("approval_oracle_separated")))


def render(bundle, report, source="<bundle>", episode_id=None):
    """The whole page, as one string. Pure: takes a bundle, returns text."""
    manifest = bundle.get("run_manifest", {})
    target = manifest.get("target_ref", {})
    lines = []
    add = lines.append

    add(rule("="))
    add("CRUCIBLE - offline evidence replay")
    add(rule("="))
    head, tail = _wrap_note(source, WIDTH - HEADER_COL)
    add("  %-10s  %s" % ("bundle", head))
    for extra in tail:
        add("%s%s" % (" " * HEADER_COL, extra))
    add("  digest      sha256, RECOMPUTED from the bytes on disk:")
    add("%s%s" % (" " * HEADER_COL, report.digest or "-"))
    add("  read with no credentials, no network, and no cloud project.")
    add("")

    add("RUN")
    add("  run_id           %s" % manifest.get("run_id"))
    add("  spine_version    %s" % manifest.get("spine_version"))
    add("  created_at       %s" % manifest.get("created_at"))
    add("  target           %s   from %s"
        % (target.get("target_id"), target.get("source")))
    add("  target model     %s   thinking_level=%s   modified_by_crucible=%s"
        % (target.get("model_id"), target.get("thinking_level"),
           json.dumps(target.get("modified_by_crucible"))))
    add("")

    add("HASH LOCKS - five, across six fields")
    locks = manifest.get("hash_locks", {})
    for field, day, note in LOCK_NOTES:
        add("  %-22s %-18s %s  %s" % (field, locks.get(field, "-"), day, note))
    add("")

    add("FROZEN PARAMETERS")
    for key, value in sorted((manifest.get("frozen_parameters") or {}).items()):
        add("  %-26s %s" % (key, value))
    add("")

    add("INTEGRITY - %d checks, %d defect(s)" % (len(report.rows), len(report.defects)))
    add("  %-16s %-14s %-6s %s" % ("check", "evidence", "status", "note"))
    for row in report.rows:
        head, tail = _wrap_note(row.note, WIDTH - NOTE_COL)
        add("  %-16s %-14s %-6s %s" % (row.check, row.kind, row.status, head))
        for extra in tail:
            add("%s%s" % (" " * NOTE_COL, extra))
    add("")
    add("  RECOMPUTED     derived again from the bytes on disk and had to agree.")
    add("  CROSS_CHECKED  two independently written fields had to agree with each other.")
    add("  PRESENT        a required field exists and is well-formed.")
    add("  Comparing a stored hash to itself would pass on a truncated write, a partial")
    add("  write, and a corrupted read, so the kind is printed rather than assumed.")
    if report.defects:
        add("")
        add("  DEFECTS")
        for defect in report.defects:
            add("    %s" % defect)
    add("")

    add(_episode_section(bundle, episode_id))
    add(_policy_chain_section(bundle))
    add(_gate_section(bundle))

    add(rule("="))
    for line in _labels_block(bundle, target):
        add(line)
    add(rule("="))
    add("This viewer states no rate. It prints a census of what is in the file and the")
    add("labels any figure from it must carry. A rate needs a denominator decision -")
    add("TARGET_FAULT is neither breach nor non-breach and leaves the denominator - and")
    add("that decision belongs to the component that owns the measurement.")
    return "\n".join(lines)


LABEL_COL = 2 + 20 + 1


def _labels_block(bundle, target):
    """The block that must appear next to any figure from this run.

    Built rather than templated so every entry wraps to the page width. A label
    that runs off the right edge of a projector is a label that was not said,
    and `docs/lanes/L6-evidence.md` section 6 is explicit that if a number
    cannot be stated with its label in the space available, the NUMBER is what
    gets cut.
    """
    entries = [
        ("k = 1",
         "single-sample, no stability estimate. Breach semantics is any-of-k, "
         "so any rate from this run is written \"ASR (any-of-1)\"."),
        ("SEP-BY split",
         "%s. A suite the APPROVAL_ORACLE separates produces identical headline "
         "numbers to one the policy separates, and only this ratio tells them "
         "apart." % _sep_by_label(bundle)),
        ("target tier",
         "%s at thinking_level=%s. A weaker target is easier to attack, which "
         "inflates the v0 baseline and flatters the whole curve, so the tier is "
         "named every time the numbers are reported."
         % (target.get("model_id"), target.get("thinking_level"))),
        ("benign regression", _benign_label(bundle)),
        ("trust root",
         "the builder holds project Owner. No control in this system defends "
         "against him."),
    ]
    lines = ["LABELS THAT TRAVEL WITH EVERY FIGURE FROM THIS RUN", ""]
    for name, text in entries:
        head, tail = _wrap_note(text, WIDTH - LABEL_COL)
        lines.append("  %-20s %s" % (name, head))
        for extra in tail:
            lines.append("%s%s" % (" " * LABEL_COL, extra))
    return lines


def _episode_section(bundle, episode_id=None):
    episodes = bundle.get("episodes") or []
    lines = ["EPISODE CENSUS - a count of what is in this file, not a result"]
    by_outcome, by_verdict = {}, {}
    for ep in episodes:
        by_outcome[ep.get("outcome")] = by_outcome.get(ep.get("outcome"), 0) + 1
        verdict = (ep.get("verdict") or {}).get("verdict")
        by_verdict[verdict] = by_verdict.get(verdict, 0) + 1
    lines.append("  episodes         %d" % len(episodes))
    lines.append("  by outcome       %s" % (", ".join(
        "%s=%d" % kv for kv in sorted(by_outcome.items(), key=lambda x: str(x[0])))
        or "-"))
    lines.append("  by verdict       %s" % (", ".join(
        "%s=%d" % kv for kv in sorted(by_verdict.items(), key=lambda x: str(x[0])))
        or "-"))
    if by_outcome.get("TARGET_FAULT"):
        lines.append("  TARGET_FAULT is NEITHER breach nor non-breach. It leaves the denominator")
        lines.append("  and is logged. Counting a crash as 'attack failed' would let a fragile")
        lines.append("  target render as a hardened one.")
    lines.append("")
    lines.append("  %-16s %-11s %-8s %-7s %-7s %s"
                 % ("episode", "outcome", "verdict", "policy", "prefix", "frozen at"))
    for ep in episodes:
        verdict = ep.get("verdict") or {}
        lines.append("  %-16s %-11s %-8s v%-6s %-7d %s" % (
            ep.get("episode_id"), ep.get("outcome"), verdict.get("verdict"),
            ep.get("policy_version"), len(ep.get("episode_prefix") or []),
            (ep.get("episode_frozen_context") or {}).get("frozen_at")))
    lines.append("")
    if episode_id:
        lines.append(_episode_detail(episodes, episode_id))
    else:
        lines.append("  --episode <id> replays one episode's frozen context and ordered prefix.")
        lines.append("")
    return "\n".join(lines)


def _episode_detail(episodes, episode_id):
    for ep in episodes:
        if ep.get("episode_id") == episode_id:
            break
    else:
        return "  no episode %r in this bundle\n" % episode_id

    lines = [rule(), "EPISODE %s" % episode_id, rule()]
    lines.append("  frozen episode.* context - frozen BEFORE the first user turn and")
    lines.append("  unwritable for the episode's duration. One in-episode turn moving")
    lines.append("  account_holder_email would collapse the sealed-family result in a")
    lines.append("  single move, and nothing else in the system would catch it.")
    for key, value in sorted((ep.get("episode_frozen_context") or {}).items()):
        lines.append("    %-32s %s" % (key, value))
    lines.append("")
    lines.append("  ordered episode prefix - the recorded ToolEvent list. The episode-scoped")
    lines.append("  predicates are replayed against THIS, which is why they stay deterministic:")
    lines.append("  purity was never about statelessness, and a recorded prefix is deterministic.")
    lines.append("")
    for event in ep.get("episode_prefix") or []:
        lines.append("    seq %-4s %-16s %-14s %s" % (
            event.get("seq"), event.get("kind"), event.get("tool_name"),
            ",".join(event.get("capability_classes") or [])))
        lines.append("      handle   %s   role %s   decision %s"
                     % (event.get("tool_handle"), event.get("role"),
                        event.get("policy_decision") or "-"))
        plain = {k: v for k, v in (event.get("args") or {}).items()
                 if not k.startswith("derived.")}
        derived = {k: v for k, v in (event.get("args") or {}).items()
                   if k.startswith("derived.")}
        for key, value in sorted(plain.items()):
            lines.append("      arg      %-28s %s" % (key, json.dumps(value)))
        for key, value in sorted(derived.items()):
            lines.append("      stamped  %-28s %s" % (key, json.dumps(value)))
        if event.get("derived_overwrites"):
            lines.append("      OVERWRITES %s" % event["derived_overwrites"])
        lines.append("")
    verdict = ep.get("verdict") or {}
    lines.append("  verdict    %s   invariant %s   evidence at seq %s"
                 % (verdict.get("verdict"), verdict.get("invariant_id"),
                    verdict.get("evidence")))
    lines.append("")
    return "\n".join(lines)


def _policy_chain_section(bundle):
    lines = ["POLICY CHAIN"]
    lines.append("  %-8s %-18s %-18s %s"
                 % ("version", "policy_hash", "parent_hash", "lineage_hash"))
    for entry in bundle.get("policy_chain") or []:
        lines.append("  v%-7s %-18s %-18s %s"
                     % (entry.get("version"), entry.get("policy_hash"),
                        entry.get("parent_hash") or "-", entry.get("lineage_hash")))
    lines.append("")
    lines.append("  The parent links are cross-checked here. policy_hash and lineage_hash")
    lines.append("  cannot be RECOMPUTED from a bundle: the chain formula needs the 64-char")
    lines.append("  policy_hash_full and the bundle carries the 16-char form. Recomputation")
    lines.append("  runs against the run ledger - scripts/verify-chain.py --ledger ... --run ...")
    lines.append("  The chain is UNSIGNED. It detects accidental mutation, partial writes, and")
    lines.append("  post-hoc editing. It does not defend against an adversary holding the")
    lines.append("  Gate's credentials, because such an adversary recomputes it too. IAM")
    lines.append("  immutability is the real control; the chain is the detector.")
    lines.append("")
    return "\n".join(lines)


def _gate_section(bundle):
    lines = ["GATE DECISIONS"]
    lines.append("  %-24s %-7s %s" % ("gate_decision_id", "round", "decision"))
    for entry in bundle.get("gate_decisions") or []:
        lines.append("  %-24s r%-6s %s" % (entry.get("gate_decision_id"),
                                           entry.get("round_index"),
                                           entry.get("decision")))
    lines.append("")
    lines.append("  Promotion requires all nine known-bad fixtures to return their EXPECTED")
    lines.append("  VERDICT. Not 'nine still failing' - only five of the nine are breach")
    lines.append("  fixtures, and a blanket breach==true assertion fails on KB8 by design.")
    lines.append("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="crucible.replay",
        description="Replay a CRUCIBLE evidence bundle offline. Reads only from "
                    "disk: no credentials, no network, no cloud project.")
    parser.add_argument("bundle", help="path to a C6 evidence bundle")
    parser.add_argument("--episode", help="replay one episode in full")
    parser.add_argument("--json", action="store_true",
                        help="print the verified bundle as indented JSON instead")
    args = parser.parse_args(argv)

    out = _out()
    path = pathlib.Path(args.bundle)
    try:
        bundle, report = read_bundle(path)
    except BundleRejected as exc:
        out.write("BUNDLE REJECTED - %s\n\n" % path.name)
        for defect in exc.defects:
            out.write("  %s\n" % defect)
        out.write("\n")
        out.write("Nothing is rendered from a bundle that failed integrity. A bundle that\n")
        out.write("renders beautifully while missing the hash that makes it meaningful is\n")
        out.write("worse than one that fails to open, because the first one looks like\n")
        out.write("evidence.\n")
        out.flush()
        return 2
    except FileNotFoundError:
        out.write("no such bundle: %s\n" % path)
        out.flush()
        return 2

    if args.json:
        out.write(json.dumps(bundle, indent=2, sort_keys=True))
        out.write("\n")
    else:
        out.write(render(bundle, report, source=str(path), episode_id=args.episode))
        out.write("\n")
    out.flush()
    return 0
