#!/usr/bin/env python3
"""check-loop-cues.py - the cue list holds pointers into the diagram, so it needs
a check that can fail.

`docs/design/architecture-animation-spec.md` calls this validator the point,
not a nicety, and names four failure conditions. The reason is on the record:
the cue list is the ARMORER dangling-pointer defect (ruling 51) in a new medium.
A rule that names a clause id nothing defines is a rule that silently does
nothing; a cue that names a node the SVG does not have is an animation beat that
silently does nothing. Same defect, and it has already cost this project one bad
live run.

The four the spec requires:

    R1 DANGLING        a cue id that resolves to no element in the SVG
    R2 UNCUED_NODE     a node in the SVG named by no cue
    R3 BOUNDARY        boundary "resolve" appearing zero times or more than once
    R4 TIMING          any t_ms past duration_ms, or out of order

Two extensions, both of which are the same defect wearing a different hat:

    R5 UNUSED_TARGET   a declared blindness target no cue ever names. Rule 2 in
                       the other direction: a pointer that resolves and is never
                       followed is dead weight that reads as coverage.
    R6 PLAYER_EMBED    the player inlines the cue JSON and the SVG so the page
                       is self-contained with no network fetch. An inlined copy
                       is a second source of truth (ruling 46), so it is checked
                       byte for byte against the files it was copied from rather
                       than trusted. This one is skipped when --cues points at
                       anything other than the shipping cue file, because a
                       fixture is not what the player embeds.

Run:  python scripts/check-loop-cues.py
      python scripts/check-loop-cues.py --selftest
      python scripts/check-loop-cues.py --cues docs/diagrams/loop-cues.KNOWN_BAD.json

Exit 0 clean, 1 on any finding, 2 on a usage or read error.
"""

import argparse
import io
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

def _force_utf8_stdout():
    """Windows consoles default to cp1252 and the findings carry non-ASCII.
    Guarded behind __main__: importing this module (the tests do) must not
    swap the caller's stdout, which detaches pytest's capture buffer."""
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace")

REPO = pathlib.Path(__file__).resolve().parent.parent
DIAGRAMS = REPO / "docs" / "diagrams"

DEFAULT_CUES = DIAGRAMS / "loop-cues.json"
DEFAULT_SVG = DIAGRAMS / "loop.svg"
DEFAULT_PLAYER = DIAGRAMS / "loop-player.html"
KNOWN_BAD = DIAGRAMS / "loop-cues.KNOWN_BAD.json"

# The player marks its two inlined copies so they can be extracted and diffed
# rather than eyeballed. Changing these strings means changing the player too.
CUE_EMBED_OPEN = '<script type="application/json" id="loop-cues">'
CUE_EMBED_CLOSE = "</script>"
SVG_EMBED_OPEN = "<!-- BEGIN loop.svg -->"
SVG_EMBED_CLOSE = "<!-- END loop.svg -->"

RULE_CODES = ("R1_DANGLING", "R2_UNCUED_NODE", "R3_BOUNDARY", "R4_TIMING",
              "R5_UNUSED_TARGET", "R6_PLAYER_EMBED", "R0_SCHEMA")


class Finding(object):
    """One reason the run is not clean. `code` is one of RULE_CODES."""

    def __init__(self, code, where, message):
        self.code = code
        self.where = where
        self.message = message

    def __str__(self):
        return "%-16s %-22s %s" % (self.code, self.where, self.message)


# --------------------------------------------------------------------------
# Reading the SVG. Two sets come out of it: every element that carries an id
# (what a pointer may resolve to) and the subset that are components (what
# rule 2 demands coverage of).
# --------------------------------------------------------------------------

def read_svg(path):
    """Return (all_ids, node_ids). Raises on unparseable XML - a broken SVG is
    not a passing run, it is an unevaluable one, and an unevaluable gate is a
    check that cannot fail (measurement-spec.md:813)."""
    root = ET.parse(str(path)).getroot()
    all_ids = set()
    node_ids = set()
    for elem in root.iter():
        ident = elem.get("id")
        if not ident:
            continue
        all_ids.add(ident)
        classes = (elem.get("class") or "").split()
        if "node" in classes:
            node_ids.add(ident)
    return all_ids, node_ids


# --------------------------------------------------------------------------
# Reading the cue file. Shape problems are reported as R0_SCHEMA and stop the
# rule checks that depend on them, rather than being allowed to raise: a
# validator that crashes on a malformed input tells you less than one that
# names the malformation.
# --------------------------------------------------------------------------

def _as_list(value):
    return value if isinstance(value, list) else []


def check_cues(cue_path, svg_path, player_path=None):
    findings = []

    try:
        raw = cue_path.read_text(encoding="utf-8")
        doc = json.loads(raw)
    except Exception as exc:
        return [Finding("R0_SCHEMA", cue_path.name, "unreadable: %s" % exc)]

    if not isinstance(doc, dict):
        return [Finding("R0_SCHEMA", cue_path.name, "top level is not an object")]

    all_ids, node_ids = read_svg(svg_path)

    duration = doc.get("duration_ms")
    if not isinstance(duration, int) or duration <= 0:
        findings.append(Finding("R0_SCHEMA", "duration_ms",
                                "missing or not a positive integer"))
        duration = None

    targets = doc.get("blindness_targets") or {}
    if not isinstance(targets, dict):
        findings.append(Finding("R0_SCHEMA", "blindness_targets",
                                "present but not an object"))
        targets = {}

    cues = doc.get("cues")
    if not isinstance(cues, list) or not cues:
        findings.append(Finding("R0_SCHEMA", "cues", "missing or empty"))
        cues = []

    # ---- R1, part one: every declared blindness target must anchor to a real
    # element. A target is how something absent from the diagram gets shown
    # going dark, and it can only be drawn next to something the diagram has.
    for name in sorted(targets):
        spec = targets[name]
        if not isinstance(spec, dict):
            findings.append(Finding("R0_SCHEMA", "target:" + name,
                                    "not an object"))
            continue
        anchor = spec.get("anchor")
        if not anchor:
            findings.append(Finding("R0_SCHEMA", "target:" + name,
                                    "no anchor"))
        elif anchor not in all_ids:
            findings.append(Finding(
                "R1_DANGLING", "target:" + name,
                "anchor %r resolves to no element in %s" % (anchor, svg_path.name)))

    # ---- R1, part two, plus R2, R3, R4 and R5 in one pass over the cues.
    named_nodes = set()
    used_targets = set()
    resolves = []
    previous_t = None

    for index, cue in enumerate(cues):
        where = "cues[%d]" % index
        if not isinstance(cue, dict):
            findings.append(Finding("R0_SCHEMA", where, "not an object"))
            continue

        t = cue.get("t_ms")
        if not isinstance(t, int) or isinstance(t, bool):
            findings.append(Finding("R0_SCHEMA", where, "t_ms missing or not an int"))
        else:
            where = "cues[%d]@%d" % (index, t)
            if t < 0:
                findings.append(Finding("R4_TIMING", where, "t_ms is negative"))
            if duration is not None and t > duration:
                findings.append(Finding(
                    "R4_TIMING", where,
                    "t_ms %d is past duration_ms %d" % (t, duration)))
            if previous_t is not None and t <= previous_t:
                findings.append(Finding(
                    "R4_TIMING", where,
                    "t_ms %d does not advance past the previous cue at %d"
                    % (t, previous_t)))
            previous_t = t

        for key in ("spotlight", "dim"):
            value = cue.get(key, [])
            if not isinstance(value, list):
                findings.append(Finding("R0_SCHEMA", where,
                                        "%s is present but not a list" % key))
                continue
            for ident in value:
                if not isinstance(ident, str):
                    findings.append(Finding("R0_SCHEMA", where,
                                            "%s holds a non-string" % key))
                    continue
                if ident in all_ids:
                    # A direct pointer into the diagram. Counts as coverage for
                    # rule 2 whether it was lit or dimmed - either way the beat
                    # names the component.
                    if ident in node_ids:
                        named_nodes.add(ident)
                elif ident in targets:
                    used_targets.add(ident)
                else:
                    findings.append(Finding(
                        "R1_DANGLING", where,
                        "%s id %r is neither an element in %s nor a declared "
                        "blindness target" % (key, ident, svg_path.name)))

        boundary = cue.get("boundary")
        if boundary is not None:
            if boundary != "resolve":
                findings.append(Finding("R0_SCHEMA", where,
                                        "boundary %r is not \"resolve\"" % boundary))
            else:
                resolves.append((index, cue.get("t_ms")))

    # ---- R2. The check the spec wrote this validator for: add a component and
    # forget to narrate it, this fails.
    for missing in sorted(node_ids - named_nodes):
        findings.append(Finding("R2_UNCUED_NODE", missing,
                                "component node is named by no cue"))

    # ---- R3. Exactly once, and last, because it is the closing thesis.
    if len(resolves) == 0:
        findings.append(Finding("R3_BOUNDARY", "cues",
                                'boundary "resolve" never appears'))
    elif len(resolves) > 1:
        findings.append(Finding(
            "R3_BOUNDARY", "cues",
            'boundary "resolve" appears %d times, at %s'
            % (len(resolves), ", ".join(str(t) for _, t in resolves))))
    elif cues and resolves[0][0] != len(cues) - 1:
        findings.append(Finding(
            "R3_BOUNDARY", "cues[%d]" % resolves[0][0],
            'boundary "resolve" is not the last cue'))

    # ---- R5.
    for unused in sorted(set(targets) - used_targets):
        findings.append(Finding("R5_UNUSED_TARGET", "target:" + unused,
                                "declared blindness target is named by no cue"))

    # ---- R6. Only meaningful against the file the player actually embeds.
    if player_path is not None:
        findings.extend(check_player_embed(player_path, cue_path, svg_path))

    return findings


def _between(haystack, open_marker, close_marker):
    start = haystack.find(open_marker)
    if start < 0:
        return None
    start += len(open_marker)
    end = haystack.find(close_marker, start)
    if end < 0:
        return None
    return haystack[start:end]


def check_player_embed(player_path, cue_path, svg_path):
    """The player is self-contained on purpose: file:// pages cannot fetch, and
    a capture run that depends on a web server is a capture run that fails at
    2am. The cost of that choice is two copies, so both are diffed here."""
    findings = []
    try:
        html = player_path.read_text(encoding="utf-8")
    except Exception as exc:
        return [Finding("R6_PLAYER_EMBED", player_path.name,
                        "unreadable: %s" % exc)]

    embedded_cues = _between(html, CUE_EMBED_OPEN, CUE_EMBED_CLOSE)
    if embedded_cues is None:
        findings.append(Finding("R6_PLAYER_EMBED", player_path.name,
                                "no inlined cue block found"))
    elif embedded_cues.strip() != cue_path.read_text(encoding="utf-8").strip():
        findings.append(Finding(
            "R6_PLAYER_EMBED", player_path.name,
            "inlined cue JSON has drifted from %s" % cue_path.name))

    embedded_svg = _between(html, SVG_EMBED_OPEN, SVG_EMBED_CLOSE)
    if embedded_svg is None:
        findings.append(Finding("R6_PLAYER_EMBED", player_path.name,
                                "no inlined SVG block found"))
    elif embedded_svg.strip() != svg_path.read_text(encoding="utf-8").strip():
        findings.append(Finding(
            "R6_PLAYER_EMBED", player_path.name,
            "inlined SVG has drifted from %s" % svg_path.name))

    return findings


# --------------------------------------------------------------------------
# Selftest. Same principle as the eval harness known-bads and canon-check's
# fixtures: a check that cannot fail is not measuring anything, so prove it
# still fails on a file built to break every rule.
# --------------------------------------------------------------------------

def selftest():
    print("selftest: %s must be rejected on every rule" % KNOWN_BAD.name)
    findings = check_cues(KNOWN_BAD, DEFAULT_SVG, player_path=None)
    seen = set(f.code for f in findings)
    expected = {"R1_DANGLING", "R2_UNCUED_NODE", "R3_BOUNDARY", "R4_TIMING",
                "R5_UNUSED_TARGET"}
    for finding in findings:
        print("  " + str(finding))
    missed = expected - seen
    if missed:
        print("\nSELFTEST FAILED: the fixture was not caught on %s"
              % ", ".join(sorted(missed)))
        return 1

    print("\nselftest: %s must pass clean" % DEFAULT_CUES.name)
    clean = check_cues(DEFAULT_CUES, DEFAULT_SVG, player_path=DEFAULT_PLAYER)
    for finding in clean:
        print("  " + str(finding))
    if clean:
        print("\nSELFTEST FAILED: the shipping cue list does not pass")
        return 1

    print("\nselftest OK: %d findings on the known-bad, 0 on the shipping list"
          % len(findings))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cues", default=str(DEFAULT_CUES))
    parser.add_argument("--svg", default=str(DEFAULT_SVG))
    parser.add_argument("--player", default=str(DEFAULT_PLAYER))
    parser.add_argument("--no-player", action="store_true",
                        help="skip R6, the player embed diff")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    cue_path = pathlib.Path(args.cues).resolve()
    svg_path = pathlib.Path(args.svg).resolve()
    for path in (cue_path, svg_path):
        if not path.exists():
            print("cannot read %s" % path)
            return 2

    player_path = None
    if not args.no_player and cue_path == DEFAULT_CUES.resolve():
        candidate = pathlib.Path(args.player).resolve()
        if candidate.exists():
            player_path = candidate
        else:
            print("cannot read %s" % candidate)
            return 2

    findings = check_cues(cue_path, svg_path, player_path)
    if not findings:
        print("OK  %s: every cue resolves, every node is cued, "
              "one boundary resolve, timeline monotonic" % cue_path.name)
        return 0

    print("%s: %d finding(s)" % (cue_path.name, len(findings)))
    for finding in findings:
        print("  " + str(finding))
    return 1


if __name__ == "__main__":
    _force_utf8_stdout()
    sys.exit(main())
