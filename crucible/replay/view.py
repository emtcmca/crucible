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
    census, permanently, rather than attached to figures later. AS OF
    2026-08-22 THAT SENTENCE IS READ OUT OF THE BUNDLE, not out of this file.
    C6 requires a `labels` block and the reader cross-checks each entry against
    the data it describes, because a bundle mailed to a customer or pasted into
    a slide has to keep its caveats without this program in the room.
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
from .integrity import (
    BENIGN_DENOMINATOR,
    BundleRejected,
    EXCLUSION_CEILING_PCT,
    EXCLUSION_RATE_MIN_N,
    EXCLUSION_SUBFLOOR_ALLOWANCE,
    HASH_LOCK_COUNT,
    HASH_LOCK_FIELDS,
    KNOWN_BAD_BREACH_FIXTURES,
    KNOWN_BAD_CLEAN_FIXTURE,
)

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
    was not measured on. `README.md` and `docs/CONVENTIONS.md` section 4 carried
    12.5% for a day after ruling 43 and were corrected 2026-08-22 at
    SPINE_VERSION 14; this function was right through both days without being
    touched, which is the argument for deriving a number instead of restating it.
    `contracts/run_manifest.schema.json:109` still carries 12.5% in a `$comment`
    and is DELIBERATELY not corrected - editing it re-hashes contract C7, so it
    is a recorded coordinator decision rather than a fix made in passing.

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
    # THE WORD "RECOMPUTED" IS A CLAIM ABOUT A COMPUTATION THAT MAY NOT HAVE
    # HAPPENED. `report.digest` is None when the document did not canonicalize,
    # and the header printed the claim followed by a dash - a provenance
    # sentence with nothing behind it, which is the shape this whole sweep is
    # about. The CLI never reaches it because `read_bundle` refuses first, and
    # "unreachable through one entry point" is not the same as "cannot print".
    if report.digest:
        add("  digest      sha256, RECOMPUTED from the bytes on disk:")
        add("%s%s" % (" " * HEADER_COL, report.digest))
    else:
        add("  digest      NOT RECOMPUTED - this document did not canonicalize,")
        add("%sso there are no bytes to take a digest of." % (" " * HEADER_COL))
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

    # DERIVED, NOT SPELLED OUT. This heading read "five, across six fields" and
    # `integrity._check_hash_locks` carried the same two numbers as a second
    # literal. Both now come from `HASH_LOCK_GROUPS`, which is the fact behind
    # them: corpus_hash and derived_schema_hash freeze together at D5.
    add("HASH LOCKS - %d, across %d fields"
        % (HASH_LOCK_COUNT, len(HASH_LOCK_FIELDS)))
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

    # THE ENGAGEMENT, IN READING ORDER. What was tested, how the target
    # answered, what was excluded, how bad it was, what was found, what was
    # proposed, what the policy now says, whether it held across versions, and
    # what share of the definition of breach was ever reached. A reader with no
    # context has to be able to follow that end to end without opening a source
    # file, which is why every one of these sections prints TEXT and not only
    # ids and hashes.
    add(_provenance_section(bundle))
    add(_attack_section(bundle))
    add(_episode_section(bundle, episode_id))
    add(_round_section(bundle))
    add(_severity_section(bundle))
    add(_autopsy_section(bundle))
    add(_patch_section(bundle))
    add(_policy_chain_section(bundle))
    add(_arc_section(bundle))
    add(_distinctness_section(bundle))
    add(_coverage_section(bundle))
    add(_gate_section(bundle))
    add(_cost_section(bundle))

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

    READ FROM THE BUNDLE, NOT FROM THIS FILE. Until 2026-08-22 these five
    sentences were string literals right here, which meant the caveats existed
    only for a reader who ran this program. A bundle pasted into a slide, mailed
    to a customer, or opened in a text editor arrived stripped of every label
    and kept every number - and that is the one failure this project must never
    allow. C6 now REQUIRES `labels`, `integrity._check_labels` cross-checks each
    one against the data it describes, and this function renders what the file
    says rather than what the viewer remembers.

    Built rather than templated so every entry wraps to the page width. A label
    that runs off the right edge of a projector is a label that was not said,
    and `docs/lanes/L6-evidence.md` section 6 is explicit that if a number
    cannot be stated with its label in the space available, the NUMBER is what
    gets cut.
    """
    carried = bundle.get("labels") or {}
    entries = [
        ("k", carried.get("k")),
        ("SEP-BY split", carried.get("sep_by_split")),
        ("target tier", carried.get("target_tier")),
        ("benign regression", carried.get("benign_regression")),
        ("trust root", carried.get("trust_root")),
    ]
    lines = ["LABELS THAT TRAVEL WITH EVERY FIGURE FROM THIS RUN", ""]
    for line in _wrapped(
            "  ", "read from the bundle's own `labels` block, not from this "
                  "viewer. They travel with the file, so a reader who never "
                  "runs this program still gets them."):
        lines.append(line)
    lines.append("")
    for name, text in entries:
        head, tail = _wrap_note(text or "-", WIDTH - LABEL_COL)
        lines.append("  %-20s %s" % (name, head))
        for extra in tail:
            lines.append("%s%s" % (" " * LABEL_COL, extra))
    lines.append("")
    # DERIVED HERE, AND SAID TO BE. The benign bound is arithmetic over this
    # bundle's own fixture results, so it is recomputed rather than quoted -
    # the carried label above states the METHOD, this line states the RESULT of
    # applying it to these bytes. `regression_upper_bound` withholds the number
    # entirely when its precondition fails, which is why the two are printed
    # separately instead of one standing in for the other.
    for line in _wrapped("  ", "computed from this bundle's own bytes, not "
                               "carried: " + _benign_label(bundle)):
        lines.append(line)
    return lines


# --------------------------------------------------------------------------
# The engagement sections. Each is pure: bundle in, text out.
# --------------------------------------------------------------------------

def _wrapped(indent, text, cont=None):
    """`text` wrapped to the page.

    `indent` prefixes the first line; `cont` prefixes the rest, defaulting to
    `indent`. The two differ for a LABELLED block - "validator: ..." must not
    repeat the word "validator" on every continuation line, which is what a
    single-prefix version printed, while a quoted attack keeps its "| " bar on
    every line precisely so a reader can see where the quotation ends.
    """
    if cont is None:
        cont = indent
    head, tail = _wrap_note(text, WIDTH - max(len(indent), len(cont)))
    return ["%s%s" % (indent, head)] + ["%s%s" % (cont, t) for t in tail]


def _provenance_section(bundle):
    """WHICH PARTS OF THIS RUN WERE REAL. Printed BEFORE any figure, on purpose.

    A stand-in bundle and a live bundle are the same shape: same hash-locks,
    same frozen parameters, same census, same chain. If a reader has to reach
    the end of the page to learn that four components were scripted, the numbers
    in the middle have already been read as though they were not.
    """
    prov = bundle.get("execution_provenance") or {}
    lines = ["EXECUTION PROVENANCE - what actually ran"]
    lines.append("  mode             %s" % prov.get("mode"))
    lines.append("  model calls      %s" % prov.get("model_calls"))
    lines.append("")
    lines.append("  %-18s %-10s %s" % ("component", "impl", "detail"))
    components = prov.get("components") or {}
    # THE TABLE WALKS THE BUNDLE, NOT A LIST IN THIS FILE. The seven names below
    # are a READING ORDER; anything else the bundle declares is appended rather
    # than dropped. `integrity._check_execution_provenance` counts every key in
    # `components`, so a hardcoded seven meant the row could count a stand-in
    # the table underneath it never showed - the row and the table describing
    # the same object and disagreeing, which is how the corpus-provenance defect
    # hid for a day two hundred lines from the docstring that contradicted it.
    ORDER = ("target", "red_strategist", "tripwire", "coroner", "armorer",
             "warden", "gate")
    for name in list(ORDER) + sorted(set(components) - set(ORDER)):
        spec = components.get(name)
        # ABSENT is not blank. A blank impl column reads as "nothing else to
        # say about a component that ran"; the truth is that the bundle never
        # declared it, and only one of those two is a hole in the record.
        impl = "ABSENT" if spec is None else (spec.get("implementation") or "-")
        detail = (spec or {}).get("detail") or ""
        col = 2 + 18 + 1 + 10 + 1
        head, tail = _wrap_note(detail or "-", WIDTH - col)
        lines.append("  %-18s %-10s %s" % (name, impl, head))
        for extra in tail:
            lines.append("%s%s" % (" " * col, extra))
    lines.append("")
    lines.append("  G7/G8 exercised  %s" % json.dumps(prov.get("g7_g8_exercised")))
    lines.extend(_wrapped("    ", str(prov.get("g7_g8_detail") or "-")))
    lines.append("")
    lines.extend(_wrapped(
        "  ", "A stand-in component produces a bundle that LOOKS exactly like a "
             "live one everywhere else in this page. That is why this block is "
             "required, and why the reader refuses a bundle whose mode says "
             "live while a component says stand_in."))
    lines.append("")
    return "\n".join(lines)


def _attack_section(bundle):
    """WHAT WAS TESTED, IN FULL, VERBATIM.

    The RED STRATEGIST puts six attacks into each round, and whether they exist
    anywhere but in this bundle depends on the entry's `provenance` - which is
    exactly why the two branches print different sentences. A `generated` attack
    was rewritten by the model and exists in no corpus and on no disk; a
    `training_corpus` attack is one of `corpus/training/`'s fifty instances and
    resolves against `corpus_hash`. Before 2026-08-22 the bundle carried an id
    for each and nothing else, so the attack that broke someone's agent became
    unrecoverable the moment the process exited. This section is the reason the
    catalogue is required.

    THE `training_corpus` SENTENCE BELOW WAS FALSE UNTIL 2026-08-22 - the seeds
    were hand-authored literals in `campaign.py` and resolved against nothing.
    It is now true and guarded by `tests/test_c6_producer.py::
    test_the_TRAINING_CORPUS_line_the_replay_prints_is_a_true_claim`. Do not
    reword it without checking what that test resolves.
    """
    attacks = bundle.get("attacks") or []
    lines = ["ATTACK CATALOGUE - what was tested"]
    if not attacks:
        lines.append("  none recorded")
        lines.append("")
        return "\n".join(lines)
    for entry in attacks:
        lines.append("")
        lines.append("  %s   %s   family %s   channel %s"
                     % (entry.get("attack_id"),
                        (entry.get("provenance") or "-").upper(),
                        entry.get("family_id"), entry.get("channel") or "-"))
        if entry.get("provenance") == "training_corpus":
            lines.append("    corpus instance %s - resolves against the corpus "
                         "frozen at corpus_hash"
                         % entry.get("corpus_instance_id"))
        else:
            gen = entry.get("generator") or {}
            lines.append("    generated in round %s by %s via %s%s"
                         % (entry.get("round_index"), gen.get("model_id"),
                            gen.get("provider"),
                            (", from seed %s" % entry["derived_from_attack_id"])
                            if entry.get("derived_from_attack_id") else ""))
            lines.append("    THIS TEXT EXISTS NOWHERE ELSE. It was produced in "
                         "memory during the run.")
        text = entry.get("instruction")
        if text:
            lines.append("")
            lines.extend(_wrapped("    | ", str(text)))
    lines.append("")
    return "\n".join(lines)


def _round_section(bundle):
    """THE DENOMINATORS AND THE NAMED EXCLUSIONS.

    `measurement-spec.md` 5.1: exclusions go to a named list WITH INSTANCE IDS,
    the count prints beside every figure, and above 5% of a round the round is
    INCOMPLETE and must be re-run rather than reported. Silent exclusion is how
    flakiness turns into apparent hardening, so the list prints even when it is
    empty - "0 exclusions" is a measurement and a blank space is not.
    """
    census = bundle.get("round_census") or []
    excluded = bundle.get("excluded") or []
    lines = ["ROUND CENSUS AND EXCLUSION LEDGER"]
    lines.append("  %-7s %-10s %-9s %-9s %-8s %-9s %s"
                 % ("round", "attempted", "scorable", "excluded", "faults",
                    "breaches", "outcome"))
    for row in census:
        lines.append("  r%-6s %-10s %-9s %-9s %-8s %-9s %s"
                     % (row.get("round_index"), row.get("attempted"),
                        row.get("scorable"), row.get("excluded"),
                        row.get("target_faults", "-"), row.get("breaches", "-"),
                        row.get("outcome")))
    lines.append("")
    lines.append("  EXCLUDED - %d instance(s), each named" % len(excluded))
    if not excluded:
        lines.append("    none")
    for entry in excluded:
        lines.append("    r%-4s %-22s %s"
                     % (entry.get("round_index"), entry.get("instance_id"),
                        entry.get("reason")))
        if entry.get("detail"):
            lines.extend(_wrapped("           ", str(entry["detail"])))
    lines.append("")
    # DERIVED FROM THE CONSTANTS, NEVER RESTATED. This paragraph said "passes 5%
    # of what it attempted" until 2026-08-22 and would have gone on saying it
    # after the rule became piecewise, printing a contradiction directly beneath
    # a row computed the new way. That is the same defect SPINE_VERSION 14
    # recorded: `regression_upper_bound` derives its figure from
    # BENIGN_DENOMINATOR and stayed correct through a denominator change while
    # four prose documents drifted. Prose that restates a constant is prose that
    # will one day disagree with it.
    lines.extend(_wrapped(
        "  ", "A round is INCOMPLETE and must be RE-RUN, not reported, when its "
             "exclusions pass %d%% of what it attempted - or, below %d "
             "attempted where a rate does not resolve, when it loses more than "
             "%d. The same test runs pooled across the reported rounds, and a "
             "run past it may have no rate quoted from it at all. TARGET_FAULT "
             "and INVALID both leave the denominator, so both are named here - "
             "a denominator that shrinks for an unnamed reason is the silent "
             "exclusion this ledger exists to prevent."
             % (EXCLUSION_CEILING_PCT, EXCLUSION_RATE_MIN_N,
                EXCLUSION_SUBFLOOR_ALLOWANCE)))
    lines.append("")
    return "\n".join(lines)


CAP_ORDER = ("CAP_MOVES_MONEY", "CAP_ESCALATES_PRIVILEGE", "CAP_READS_PII",
             "CAP_EXTERNAL_COMMS", "CAP_MUTATES_DURABLE_STATE",
             "CAP_INVOKES_AGENT", "UNCLASSIFIED")


def _severity_section(bundle):
    """HOW BAD, AND WHAT KIND - not how many.

    "12 breaches" is a number. "Four moved money, three leaked PII" is a
    finding, and a reader's first question is the second one. Every figure here
    is AGGREGATED FROM THE AUTOPSIES rather than stored: C5 already carries
    `capability_classes_involved` and `amount_minor_moved`, authored by the
    component that owns diagnosis, and a stored total would be a second copy of
    a derivable number - which is the drift this repository has already paid for
    more than once.
    """
    autopsies = bundle.get("autopsies") or []
    counts, money, currency = {}, 0, None
    for record in autopsies:
        for cap in record.get("capability_classes_involved") or []:
            counts[cap] = counts.get(cap, 0) + 1
        amount = record.get("amount_minor_moved")
        if isinstance(amount, int):
            money += amount
            currency = record.get("currency") or currency

    lines = ["BREACH SEVERITY BY CAPABILITY CLASS - derived from the autopsies"]
    lines.append("  %d breach(es) with an autopsy" % len(autopsies))
    lines.append("")
    if not counts:
        lines.append("  no capability class was implicated in any recorded breach")
    for cap in CAP_ORDER:
        if cap in counts:
            lines.append("  %-30s %d" % (cap, counts[cap]))
    for cap in sorted(set(counts) - set(CAP_ORDER)):
        lines.append("  %-30s %d" % (cap, counts[cap]))
    if money:
        lines.append("")
        lines.extend(_wrapped(
            "  ", "%d minor units of %s moved across breaches that should not "
                 "have moved any. Minor units, integer - no float ever enters a "
                 "hashed payload." % (money, currency or "?")))
    lines.append("")
    lines.extend(_wrapped(
        "  ", "A class counts once per autopsy, and one autopsy may implicate "
             "several. These are counts of BREACHES BY KIND, never a rate: the "
             "denominator decision belongs to the component that owns the "
             "measurement."))
    lines.append("")
    return "\n".join(lines)


def _autopsy_section(bundle):
    """WHAT WAS FOUND - the CORONER's diagnosis, in its own words.

    The CORONER is structurally barred from proposing a fix: C5 has no fix,
    recommendation or mitigation field and `additionalProperties` is false, so
    one cannot be added without breaking the contract hash. `human_only` is the
    only place free text may live, and it is unreachable by the ARMORER's input
    adapter by construction. It prints here because a diagnosis nobody can read
    is not a diagnosis.
    """
    autopsies = bundle.get("autopsies") or []
    lines = ["AUTOPSIES - what was found"]
    if not autopsies:
        lines.append("  none. A run with no breach has no autopsy.")
        lines.append("")
        return "\n".join(lines)
    for record in autopsies:
        lines.append("")
        lines.append("  %s   round %s   attack %s"
                     % (record.get("autopsy_id"), record.get("round_index"),
                        record.get("attack_id")))
        lines.append("    invariant   %s" % record.get("invariant_id"))
        lines.append("    classes     %s"
                     % ", ".join(record.get("capability_classes_involved") or []))
        if isinstance(record.get("amount_minor_moved"), int):
            lines.append("    moved       %d minor units %s"
                         % (record["amount_minor_moved"],
                            record.get("currency") or ""))
        for call in record.get("offending_tool_calls") or []:
            lines.append("    seq %-4s %-20s %-10s %s"
                         % (call.get("seq"), call.get("tool_handle"),
                            call.get("policy_decision"), call.get("status")))
        for key, value in sorted((record.get("human_only") or {}).items()):
            lines.append("")
            lines.append("    %s:" % key)
            lines.extend(_wrapped("      ", str(value)))
    lines.append("")
    lines.extend(_wrapped(
        "  ", "The CORONER diagnoses and CANNOT propose a fix - C5 carries no "
             "fix, recommendation or mitigation field and forbids adding one. "
             "The prose above is an observation about what happened, and the "
             "ARMORER's input adapter cannot address it at all."))
    lines.append("")
    return "\n".join(lines)


def _patch_section(bundle):
    """WHAT WAS PROPOSED, INCLUDING WHAT WAS REJECTED.

    A rejected proposal exists in no other artifact. It is also the more
    interesting half: the patch that scored zero breaches by deleting the
    capability is the failure the benign floor exists to catch, and a bundle
    that recorded only accepted patches would show a clean sweep with the
    interesting part missing.
    """
    proposals = bundle.get("patch_proposals") or []
    lines = ["PATCH PROPOSALS - what the ARMORER wrote, and what happened to it"]
    if not proposals:
        lines.append("  none")
        lines.append("")
        return "\n".join(lines)
    for entry in proposals:
        lines.append("")
        lines.append("  %s   round %s   %s   cites %s"
                     % (entry.get("proposal_id"), entry.get("round_index"),
                        "ACCEPTED" if entry.get("accepted") else "REJECTED",
                        entry.get("autopsy_id")))
        for rule_entry in entry.get("rules") or []:
            lines.extend(_wrapped("    ", str(rule_entry.get("dsl_text"))))
            proposed = rule_entry.get("rule_id_as_proposed")
            assigned = rule_entry.get("rule_id_assigned")
            if proposed and assigned:
                lines.append("      id %s proposed, rewritten to %s by the "
                             "validator" % (proposed, assigned))
            elif proposed:
                lines.append("      id %s proposed, never assigned" % proposed)
        if entry.get("validator_result"):
            lines.extend(_wrapped("    validator: ",
                                  str(entry["validator_result"]),
                                  cont="               "))
        if entry.get("warden_result"):
            lines.extend(_wrapped("    warden:    ", str(entry["warden_result"]),
                                  cont="               "))
        if entry.get("rejected_reason"):
            lines.extend(_wrapped("    rejected:  ",
                                  str(entry["rejected_reason"]),
                                  cont="               "))
    lines.append("")
    lines.extend(_wrapped(
        "  ", "The ARMORER NEVER WRITES A RULE ID - a model cannot compute "
             "SHA-256. It emits the placeholder r_new1 and the validator "
             "rewrites it from the canonical rule bytes, which is why both "
             "halves are recorded."))
    lines.append("")
    return "\n".join(lines)


def _arc_section(bundle):
    """PER-ATTACK OUTCOME ACROSS POLICY VERSIONS.

    The transfer story told per attack instead of as an aggregate. DERIVED, not
    stored: every episode already carries `attack_id`, `policy_version` and a
    verdict, and C6 now requires all three, so this table is a regrouping of
    required data rather than a second place for the same claim to live.

    It is also the only view that exposes a REGRESSION - an attack blocked at
    one version and breaching again at a later one. No aggregate rate shows
    that, because the two cancel.
    """
    episodes = bundle.get("episodes") or []
    versions, by_attack = set(), {}
    for ep in episodes:
        aid = ep.get("attack_id")
        if not aid:
            continue
        version = ep.get("policy_version")
        versions.add(version)
        by_attack.setdefault(aid, {})[version] = (
            (ep.get("verdict") or {}).get("verdict"))

    lines = ["PER-ATTACK OUTCOME ACROSS POLICY VERSIONS - derived from the episodes"]
    if not by_attack:
        lines.append("  no attack episode in this bundle")
        lines.append("")
        return "\n".join(lines)
    ordered = sorted(v for v in versions if v is not None)
    header = "  %-18s" % "attack"
    for version in ordered:
        header += " %-9s" % ("v%s" % version)
    # rstrip: the last column pads to its width and would leave trailing blanks
    # on every row. Invisible in a terminal, visible in a diff, and the width
    # test measures the padded length rather than the content.
    lines.append(header.rstrip())
    for aid in sorted(by_attack):
        row = "  %-18s" % aid
        for version in ordered:
            row += " %-9s" % (by_attack[aid].get(version) or "-")
        lines.append(row.rstrip())
    lines.append("")
    regressed = sorted(
        aid for aid, arc in by_attack.items()
        if any(arc.get(a) == "CLEAN" and arc.get(b) == "BREACH"
               for i, a in enumerate(ordered) for b in ordered[i + 1:]))
    if regressed:
        lines.extend(_wrapped(
            "  ", "REGRESSED: %s. Blocked at an earlier version and breaching "
                 "again at a later one. An aggregate rate hides this, because "
                 "the two movements cancel." % ", ".join(regressed)))
    elif len(ordered) < 2:
        # THE SENTENCE BELOW IS A FINDING ONLY WHEN THERE ARE TWO VERSIONS TO
        # COMPARE. Under a chain of one it is a statement about the empty set,
        # printed in the exact place a reader looks for the transfer result -
        # and a run that promoted nothing is the ordinary case here, not an
        # exotic one. It is cut, and the reason is printed in its place.
        lines.extend(_wrapped(
            "  ", "ONE POLICY VERSION IN THIS BUNDLE, so there is no "
                 "across-version comparison to make. Regression and transfer "
                 "are both properties of a MOVE between versions; neither is "
                 "absent here, neither was looked for."))
    else:
        lines.extend(_wrapped(
            "  ", "No attack blocked at an earlier version breached again at a "
                 "later one in this bundle. A dash means the attack was not run "
                 "at that version, which is not the same as blocked."))
    lines.append("")
    return "\n".join(lines)


def _distinctness_section(bundle):
    """DID THE ATTACKER KEEP VARYING?

    A loop that stops finding breaches because the attacker stopped varying
    looks identical, in every rate this system produces, to one that stops
    because the policy got good. DERIVED from the catalogue rather than stored:
    the generated attacks carry their own text, so distinctness is arithmetic
    over required fields.
    """
    attacks = bundle.get("attacks") or []
    lines = ["ATTACK DISTINCTNESS - derived from the catalogue"]
    by_round = {}
    for entry in attacks:
        if entry.get("provenance") != "generated":
            continue
        by_round.setdefault(entry.get("round_index"), []).append(
            " ".join(str(entry.get("instruction") or "").split()).lower())
    if not by_round:
        lines.append("  no generated attack in this bundle; nothing to vary")
        lines.append("")
        return "\n".join(lines)
    lines.append("  %-8s %-10s %s" % ("round", "generated", "distinct texts"))
    for index in sorted(by_round, key=lambda x: (x is None, x)):
        texts = by_round[index]
        lines.append("  r%-7s %-10d %d" % (index, len(texts), len(set(texts))))
    every = [t for texts in by_round.values() for t in texts]
    lines.append("")
    lines.append("  across the run   %d generated, %d distinct"
                 % (len(every), len(set(every))))
    lines.append("")
    lines.extend(_wrapped(
        "  ", "Exact-text distinctness only. Two rephrasings of one pretext "
             "count as two, so this is an UPPER BOUND on how much the attacker "
             "actually varied - stated rather than dressed up as a similarity "
             "score this bundle does not carry."))
    lines.append("")
    return "\n".join(lines)


def _coverage_section(bundle):
    """WHICH PART OF THE DEFINITION OF BREACH WAS EVER REACHED.

    The Objective Set is the definition of breach. A breach rate is therefore a
    measurement of whatever share of it the corpus managed to touch, and the
    clauses that NEVER FIRED are the rows that matter: if three of nine never
    fire, the number measures a third of the definition while being reported as
    the whole, and nothing else in the bundle says so.
    """
    coverage = bundle.get("clause_coverage") or {}
    clauses = coverage.get("clauses") or []
    lines = ["OBJECTIVE SET CLAUSE COVERAGE - which clauses were ever reached"]
    lines.append("  objective_set_hash %s" % coverage.get("objective_set_hash"))
    lines.append("")
    lines.append("  %-46s %-11s %-8s %s"
                 % ("invariant", "form", "fired", "first round"))
    for clause in clauses:
        lines.append("  %-46s %-11s %-8s %s"
                     % (clause.get("invariant_id"), clause.get("form"),
                        clause.get("episodes_fired"),
                        clause.get("first_fired_round") or "-"))
    fired = [c for c in clauses if c.get("episodes_fired")]
    lines.append("")
    lines.append("  %d of %d clause(s) fired" % (len(fired), len(clauses)))
    never = [c.get("invariant_id") for c in clauses if not c.get("episodes_fired")]
    if never:
        lines.extend(_wrapped(
            "  ", "%d clause(s) NEVER FIRED. Any breach figure from this run is "
                 "a measurement of the %d that did, and must be read that way."
                 % (len(never), len(fired))))
    # WHOSE CENSUS THIS IS, SAID OUT LOUD. The denominator above is the number
    # of ROWS THE PRODUCER WROTE, and the heading calls the table the Objective
    # Set's. Those are the same number only if the producer wrote a row per
    # clause - which the schema asks for and nothing checks, because the bundle
    # carries the Objective Set's HASH and not the Objective Set. A producer
    # that listed only the clauses that fired would render as full coverage with
    # no row saying otherwise. This is the move `_check_policy_chain` already
    # makes about policy_hash: name what is not recomputable rather than let the
    # printed figure imply it was.
    lines.append("")
    lines.extend(_wrapped(
        "  ", "The denominator is the number of rows in THIS BUNDLE'S table. "
             "Whether that is one row per clause of Objective Set %s is NOT "
             "RECOMPUTABLE FROM A BUNDLE - the bundle carries the hash of that "
             "set and not the set - so a table listing only the clauses that "
             "fired would print as full coverage. Recomputation runs against "
             "the Objective Set at that hash."
             % (coverage.get("objective_set_hash") or "?")))
    lines.append("")
    return "\n".join(lines)


def _cost_section(bundle):
    """WHAT IT COST TO RUN, IN TOKENS AND IN TIME.

    Tokens are the measurement; dollars are tokens times a price sheet that
    moves, which is why a dollar figure is optional here and the token counts
    are not. Wall clock and 429s are here because a harness someone is deciding
    whether to point at their own agent is bought or refused on those numbers,
    and because a run that spent its clock backing off is a run whose attacks
    were thinned by quota.
    """
    cost = bundle.get("cost") or {}
    retries = cost.get("retries") or {}
    lines = ["COST AND TIMING"]
    lines.append("  input tokens     %s" % cost.get("input_tokens"))
    lines.append("  output tokens    %s" % cost.get("output_tokens"))
    lines.append("  wall clock       %s ms" % cost.get("wall_clock_ms"))
    lines.append("  retries          %s total, %s of them rate-limit 429"
                 % (retries.get("total"), retries.get("rate_limit_429")))
    if cost.get("usd_estimate_minor") is not None:
        lines.append("  usd estimate     %d minor units, against the price sheet "
                     "at build time" % cost["usd_estimate_minor"])
    by_role = cost.get("by_role") or {}
    if by_role:
        lines.append("")
        for role in sorted(by_role):
            lines.append("  %-16s %s tokens" % (role, by_role[role]))
    lines.append("")
    return "\n".join(lines)


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
    # HOW THE TARGET ANSWERED, IN ITS OWN WORDS. Optional, and the tool log
    # above is what every verdict is computed over - but an agent that refuses
    # in plain language while calling the tool anyway reads very differently
    # from one that argues back, and the log alone cannot tell those apart.
    if ep.get("target_final_text"):
        lines.append("  the target's closing reply, verbatim:")
        lines.extend(_wrapped("    | ", str(ep["target_final_text"])))
        lines.append("")

    prov = ep.get("model_provenance") or {}
    lines.append("  served by  %s via %s%s   thinking_level=%s"
                 % (prov.get("model_id"), prov.get("provider"),
                    ("/" + prov["endpoint"]) if prov.get("endpoint") else "",
                    prov.get("thinking_level")))
    if prov.get("requested_model_id") and \
            prov.get("requested_model_id") != prov.get("model_id"):
        lines.append("  DOWNGRADED from %s. A result produced by a downgraded "
                     "model means something different." % prov["requested_model_id"])
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
    # THE RULES, AS TEXT. A chain of hashes says a policy changed; it does not
    # say what the policy SAYS. `gcs_uri` points into a bucket the reader cannot
    # open, which is a forwarding address and not an answer, so the DSL text
    # travels in the bundle and prints here.
    for entry in bundle.get("policy_chain") or []:
        lines.append("  POLICY v%s - %d rule(s)"
                     % (entry.get("version"), len(entry.get("rules") or [])))
        for rule_entry in entry.get("rules") or []:
            lines.extend(_wrapped("    ", str(rule_entry.get("dsl_text"))))
            origin = rule_entry.get("origin")
            if origin:
                lines.append("      origin %s%s" % (
                    origin,
                    (", round %s" % rule_entry["origin_round"])
                    if rule_entry.get("origin_round") else ""))
        lines.append("")
    # HOW MANY PARENT LINKS THERE ACTUALLY ARE. "The parent links are
    # cross-checked here" printed unconditionally, including under a chain of
    # one version - which has none - and under an empty chain. A run that
    # promoted nothing is the ordinary case on this project, so the sentence a
    # reader most often saw was the one resting on zero comparisons.
    chain = bundle.get("policy_chain") or []
    if len(chain) >= 2:
        lines.extend(_wrapped(
            "  ", "The %d parent link(s) between these %d versions are "
                 "cross-checked here." % (len(chain) - 1, len(chain))))
    else:
        lines.extend(_wrapped(
            "  ", "%d version(s), and therefore NO PARENT LINK TO CROSS-CHECK: "
                 "nothing here says a promotion chained correctly, because no "
                 "promotion happened." % len(chain)))
    lines.extend(_wrapped(
        "  ", "policy_hash and lineage_hash cannot be RECOMPUTED from a bundle: "
             "the chain formula needs the 64-char policy_hash_full and the "
             "bundle carries the 16-char form. Recomputation runs against the "
             "run ledger - scripts/verify-chain.py --ledger ... --run ..."))
    lines.extend(_wrapped(
        "  ", "The chain is UNSIGNED. It detects accidental mutation, partial "
             "writes, and post-hoc editing. It does not defend against an "
             "adversary holding the Gate's credentials, because such an "
             "adversary recomputes it too. IAM immutability is the real "
             "control; the chain is the detector."))
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
    # THE SUITE SIZE IS READ OUT OF THE RUN BEING DESCRIBED. This paragraph
    # spelled "nine" and "five" and "KB8" as English words, in a viewer whose
    # FROZEN PARAMETERS block two screens up prints this run's own
    # `known_bad_count`. That is the defect that put a hardcoded 5% ceiling
    # above a row computed by the piecewise rule that had replaced it: prose
    # restating a constant is prose that will one day disagree with it.
    #
    # The breach half and the CLEAN fixture's name are in no bundle, so they
    # come from `integrity.py`'s constants, which are pinned to the hash-locked
    # gate rule by a test. When the run froze no count, the sentence that needs
    # one is CUT rather than fudged - the same direction
    # `regression_upper_bound` takes when its precondition fails.
    frozen = ((bundle.get("run_manifest") or {}).get("frozen_parameters") or {})
    count = frozen.get("known_bad_count")
    if isinstance(count, int):
        lines.extend(_wrapped(
            "  ", "Promotion requires all %d known-bad fixtures THIS RUN FROZE "
                 "to return their EXPECTED VERDICT. Not '%d still failing' - "
                 "only %d of the %d are breach fixtures, and a blanket "
                 "breach==true assertion fails on %s by design."
                 % (count, count, KNOWN_BAD_BREACH_FIXTURES, count,
                    KNOWN_BAD_CLEAN_FIXTURE)))
    else:
        lines.extend(_wrapped(
            "  ", "This run's manifest froze no known_bad_count, so the size of "
                 "the calibration suite promotion is gated on is not stated "
                 "here. What holds regardless: the gate asserts a PER-FIXTURE "
                 "EXPECTED VERDICT, never a blanket breach==true, which fails "
                 "on %s by design." % KNOWN_BAD_CLEAN_FIXTURE))
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
