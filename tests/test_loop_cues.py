"""test_loop_cues.py - the N4 architecture animation: cue list, validator, player.

READ THIS FIRST. Every test below is written so that deleting the behaviour it
protects turns it RED. That is not a style preference here. This repo's
signature recurring defect is a check that passes while measuring nothing -
twelve recorded instances, three of them authored while repairing the other
eight - and an animation is a soft target for it, because "the page contains
the word seek" looks like a test and is not one.

Three consequences show up in the file:

  * The player's timeline is a DOM-free core, marked off in loop-player.html
    between CRUCIBLE_CUE_CORE_BEGIN and CRUCIBLE_CUE_CORE_END. The tests
    EXTRACT AND EXECUTE that text in node. They are not reading it. Break
    computeFrame and these go red.
  * Nothing asserts that a symbol exists. Every assertion is about a value the
    code produced.
  * The blindness claims are re-read out of docs/architecture-spec.md 1.1 at
    test time, never recalled. The spec names the trap by name: the Objective
    Set is on RED's blind list and NOT on the ARMORER's, and it has been got
    wrong once already.

WHAT IS NOT COVERED, stated rather than hidden. There is no playwright and no
jsdom in the pinned dependencies, so nothing here drives a browser. The DOM
layer of loop-player.html - class assignment, chip placement, the transition
suppression inside seek() - is verified by hand in a real browser and by
scripts/check-loop-cues.py, not by this file. The core it calls is covered.
"""

import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
DIAGRAMS = REPO / "docs" / "diagrams"
CUES_PATH = DIAGRAMS / "loop-cues.json"
KNOWN_BAD_PATH = DIAGRAMS / "loop-cues.KNOWN_BAD.json"
SVG_PATH = DIAGRAMS / "loop.svg"
PLAYER_PATH = DIAGRAMS / "loop-player.html"
CHECKER_PATH = REPO / "scripts" / "check-loop-cues.py"
ARCH_SPEC = REPO / "docs" / "architecture-spec.md"

CORE_BEGIN = "CRUCIBLE_CUE_CORE_BEGIN"
CORE_END = "CRUCIBLE_CUE_CORE_END"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_loop_cues", CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = _load_checker()


# --------------------------------------------------------------------------
# Fixtures and helpers
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def cue_doc():
    return json.loads(CUES_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def svg_ids():
    """(all_ids, node_ids) straight out of loop.svg, by the same rule the
    validator uses: a component is an element whose class carries `node`."""
    return checker.read_svg(SVG_PATH)


def codes_for(doc, tmp_path, player=None):
    """Run the validator over an in-memory cue document and return the set of
    rule codes it raised. Every R-rule test below mutates the real shipping cue
    list and asserts the code appears, so a rule that stops firing goes red."""
    path = tmp_path / "mutated-cues.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    findings = checker.check_cues(path, SVG_PATH, player)
    return set(f.code for f in findings), findings


def mutate(doc):
    return json.loads(json.dumps(doc))


def cue_at(doc, t_ms):
    for cue in doc["cues"]:
        if cue["t_ms"] == t_ms:
            return cue
    raise AssertionError("no cue at %d" % t_ms)


# --------------------------------------------------------------------------
# The shipping artifacts are clean. If this fails nothing else below means
# anything, because every mutation test starts from this document.
# --------------------------------------------------------------------------

def test_shipping_cue_list_and_player_pass_the_validator():
    findings = checker.check_cues(CUES_PATH, SVG_PATH, PLAYER_PATH)
    assert findings == [], "\n".join(str(f) for f in findings)


# --------------------------------------------------------------------------
# R1 DANGLING - the ARMORER dangling-pointer defect in a new medium. Three
# shapes: a bad spotlight id, a bad dim id, and a target anchored to nothing.
# --------------------------------------------------------------------------

def test_r1_catches_a_spotlight_id_that_is_in_no_element(cue_doc, tmp_path):
    doc = mutate(cue_doc)
    cue_at(doc, 20800)["spotlight"] = ["ARMOURER"]
    codes, findings = codes_for(doc, tmp_path)
    assert "R1_DANGLING" in codes
    assert any("ARMOURER" in f.message for f in findings)


def test_r1_catches_a_dim_id_that_is_neither_element_nor_declared_target(cue_doc, tmp_path):
    doc = mutate(cue_doc)
    cue_at(doc, 20800)["dim"].append("SEALED_BUCKET")
    codes, findings = codes_for(doc, tmp_path)
    assert "R1_DANGLING" in codes
    assert any("SEALED_BUCKET" in f.message for f in findings)


def test_r1_catches_a_blindness_target_anchored_to_a_missing_node(cue_doc, tmp_path):
    """FLOOR is the real-world shape of this. It is a node in
    docs/diagrams/_loop.mmd and is NOT a node in loop.svg, so a target that
    anchors to it points at a component the plate does not draw."""
    doc = mutate(cue_doc)
    doc["blindness_targets"]["HELDOUT"]["anchor"] = "FLOOR"
    codes, findings = codes_for(doc, tmp_path)
    assert "R1_DANGLING" in codes
    assert any("FLOOR" in f.message for f in findings)


def test_r1_accepts_an_edge_as_an_anchor(cue_doc):
    """WARDEN_REPORT anchors to the edge the report travels along, not to a
    box. If anchors were silently restricted to nodes this would be a false
    positive and the shipping list would not pass."""
    anchor = cue_doc["blindness_targets"]["WARDEN_REPORT"]["anchor"]
    all_ids, node_ids = checker.read_svg(SVG_PATH)
    assert anchor in all_ids and anchor not in node_ids


# --------------------------------------------------------------------------
# R2 UNCUED_NODE - a component nobody narrates. Add a node to the diagram and
# forget the cue list, this fails.
# --------------------------------------------------------------------------

def test_r2_catches_a_component_no_cue_names(cue_doc, tmp_path):
    doc = mutate(cue_doc)
    cue_at(doc, 1200)["spotlight"] = ["RED"]        # drops GOV, which nothing else names
    codes, findings = codes_for(doc, tmp_path)
    assert "R2_UNCUED_NODE" in codes
    assert any(f.where == "GOV" for f in findings)


def test_r2_counts_every_component_in_the_svg_not_a_hardcoded_list(svg_ids, cue_doc):
    """The node set is read from loop.svg. If it were a literal in the
    validator, adding a component would leave the check silently satisfied,
    which is precisely the failure the spec wrote R2 to prevent."""
    all_ids, node_ids = svg_ids
    named = set()
    for cue in cue_doc["cues"]:
        named.update(cue.get("spotlight", []))
        named.update(cue.get("dim", []))
    assert node_ids and node_ids <= named


# --------------------------------------------------------------------------
# R3 BOUNDARY - rule 3 fires exactly once, and last, because it is the
# closing thesis.
# --------------------------------------------------------------------------

def test_r3_catches_zero_resolves(cue_doc, tmp_path):
    doc = mutate(cue_doc)
    del cue_at(doc, 41000)["boundary"]
    codes, _ = codes_for(doc, tmp_path)
    assert "R3_BOUNDARY" in codes


def test_r3_catches_two_resolves(cue_doc, tmp_path):
    doc = mutate(cue_doc)
    cue_at(doc, 29200)["boundary"] = "resolve"
    codes, findings = codes_for(doc, tmp_path)
    assert "R3_BOUNDARY" in codes
    assert any("2 times" in f.message for f in findings)


def test_r3_catches_a_resolve_that_is_not_last(cue_doc, tmp_path):
    doc = mutate(cue_doc)
    doc["cues"].append({"t_ms": 43000, "spotlight": ["ARM"], "dim": []})
    codes, findings = codes_for(doc, tmp_path)
    assert "R3_BOUNDARY" in codes
    assert any("not the last cue" in f.message for f in findings)


# --------------------------------------------------------------------------
# R4 TIMING
# --------------------------------------------------------------------------

def test_r4_catches_a_cue_past_the_duration(cue_doc, tmp_path):
    doc = mutate(cue_doc)
    doc["cues"][-1]["t_ms"] = 61000
    codes, findings = codes_for(doc, tmp_path)
    assert "R4_TIMING" in codes
    assert any("past duration_ms" in f.message for f in findings)


def test_r4_catches_cues_out_of_order(cue_doc, tmp_path):
    doc = mutate(cue_doc)
    doc["cues"][3]["t_ms"] = 900          # earlier than cues[2] at 2400
    codes, findings = codes_for(doc, tmp_path)
    assert "R4_TIMING" in codes
    assert any("does not advance" in f.message for f in findings)


def test_r4_catches_two_cues_at_the_same_instant(cue_doc, tmp_path):
    """Not merely out of order. Two cues sharing a t_ms means one of them can
    never be the active cue, which is a beat that silently does nothing - the
    same defect class as a dangling pointer."""
    doc = mutate(cue_doc)
    doc["cues"][3]["t_ms"] = doc["cues"][2]["t_ms"]
    codes, _ = codes_for(doc, tmp_path)
    assert "R4_TIMING" in codes


# --------------------------------------------------------------------------
# R5 UNUSED_TARGET
# --------------------------------------------------------------------------

def test_r5_catches_a_declared_target_no_cue_names(cue_doc, tmp_path):
    doc = mutate(cue_doc)
    doc["blindness_targets"]["PHANTOM"] = {
        "label": "a target nothing cues", "anchor": "TW",
        "enforcement": "construction", "source": "test"}
    codes, findings = codes_for(doc, tmp_path)
    assert "R5_UNUSED_TARGET" in codes
    assert any(f.where == "target:PHANTOM" for f in findings)


# --------------------------------------------------------------------------
# R6 PLAYER_EMBED - the player inlines the cue JSON and the SVG so the page is
# self-contained. An inlined copy is a second source of truth (ruling 46), so
# it is diffed, not trusted.
# --------------------------------------------------------------------------

def test_r6_catches_drift_between_the_player_and_the_cue_file(tmp_path):
    html = PLAYER_PATH.read_text(encoding="utf-8")
    drifted = html.replace('"t_ms": 41000', '"t_ms": 40000', 1)
    assert drifted != html
    path = tmp_path / "drifted-player.html"
    path.write_text(drifted, encoding="utf-8")
    findings = checker.check_player_embed(path, CUES_PATH, SVG_PATH)
    assert any(f.code == "R6_PLAYER_EMBED" and "cue JSON" in f.message
               for f in findings), [str(f) for f in findings]


def test_r6_catches_drift_between_the_player_and_the_svg(tmp_path):
    html = PLAYER_PATH.read_text(encoding="utf-8")
    drifted = html.replace('id="ARM"', 'id="ARMORER"', 1)
    assert drifted != html
    path = tmp_path / "drifted-player.html"
    path.write_text(drifted, encoding="utf-8")
    findings = checker.check_player_embed(path, CUES_PATH, SVG_PATH)
    assert any(f.code == "R6_PLAYER_EMBED" and "SVG" in f.message
               for f in findings), [str(f) for f in findings]


def test_r6_catches_a_player_with_the_embed_ripped_out(tmp_path):
    html = PLAYER_PATH.read_text(encoding="utf-8")
    path = tmp_path / "gutted-player.html"
    path.write_text(html.replace(checker.CUE_EMBED_OPEN, "<script>"), encoding="utf-8")
    findings = checker.check_player_embed(path, CUES_PATH, SVG_PATH)
    assert any("no inlined cue block" in f.message for f in findings)


# --------------------------------------------------------------------------
# The known-bad fixture, and the validator's own selftest. Same reason the
# eval harness ships known-bads: a check that cannot fail is not measuring
# anything, so there is a file whose job is to always be rejected.
# --------------------------------------------------------------------------

def test_known_bad_fixture_is_rejected_on_every_rule():
    findings = checker.check_cues(KNOWN_BAD_PATH, SVG_PATH, player_path=None)
    codes = set(f.code for f in findings)
    assert {"R1_DANGLING", "R2_UNCUED_NODE", "R3_BOUNDARY", "R4_TIMING",
            "R5_UNUSED_TARGET"} <= codes, sorted(codes)


def test_known_bad_fixture_documents_the_defect_it_plants():
    """A fixture that is broken for reasons nobody wrote down gets repaired by
    the next person who trips over it."""
    doc = json.loads(KNOWN_BAD_PATH.read_text(encoding="utf-8"))
    planted = doc["_defects_planted"]
    assert {"R1_DANGLING", "R2_UNCUED_NODE", "R3_BOUNDARY", "R4_TIMING",
            "R5_UNUSED_TARGET"} <= set(planted)


def test_validator_cli_exits_zero_on_the_shipping_list():
    proc = subprocess.run([sys.executable, str(CHECKER_PATH)],
                          cwd=str(REPO), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_validator_cli_exits_nonzero_on_the_known_bad():
    proc = subprocess.run([sys.executable, str(CHECKER_PATH),
                           "--cues", str(KNOWN_BAD_PATH)],
                          cwd=str(REPO), capture_output=True, text=True)
    assert proc.returncode != 0, proc.stdout


def test_validator_selftest_passes():
    proc = subprocess.run([sys.executable, str(CHECKER_PATH), "--selftest"],
                          cwd=str(REPO), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


# --------------------------------------------------------------------------
# The cue list against the three rules of the spec.
# --------------------------------------------------------------------------

def test_rule_1_the_first_cue_shows_the_whole_topology(cue_doc):
    """Spotlight, never build-on. A judge sees the whole system at frame one."""
    first = cue_doc["cues"][0]
    assert first["t_ms"] == 0
    assert first["spotlight"] == [] and first["dim"] == []


def test_rule_3_the_boundary_resolve_is_the_final_cue(cue_doc):
    cues = cue_doc["cues"]
    assert cues[-1].get("boundary") == "resolve"
    assert [c for c in cues if c.get("boundary")] == [cues[-1]]


def test_every_component_gets_its_own_moment_in_the_spotlight(cue_doc, svg_ids):
    """Stronger than R2, which accepts a node merely NAMED by a cue. A
    component that only ever appears as a dim target is one the beat never
    actually shows."""
    all_ids, node_ids = svg_ids
    spotlit = set()
    for cue in cue_doc["cues"]:
        spotlit.update(cue.get("spotlight", []))
    assert node_ids - spotlit == set()


def test_the_armorer_beat_darkens_the_four_things_the_spec_names(cue_doc):
    """Rule 2's headline. The spec: 'For the ARMORER that is: the attacker's
    payload text, the benign suite, the Warden report contents, the held-out
    family. Four things going dark in one beat.'"""
    beats = [c for c in cue_doc["cues"] if c.get("spotlight") == ["ARM"]]
    assert len(beats) == 1
    assert set(beats[0]["dim"]) == {
        "RED_PAYLOAD", "FIXTURE_SUITES", "WARDEN_REPORT", "HELDOUT"}


def test_timestamps_fit_the_beat(cue_doc):
    assert cue_doc["beat"] == "N4"
    assert cue_doc["duration_ms"] == 45000
    ts = [c["t_ms"] for c in cue_doc["cues"]]
    assert ts == sorted(set(ts))
    assert ts[-1] <= cue_doc["duration_ms"]


def test_the_cue_file_admits_its_timings_are_estimates(cue_doc):
    """The spec says to narrate first and cue to the recorded audio. There is
    no recording yet. A cue file that presented estimated timestamps as cued
    ones would be the deployment-status defect (ruling 46) in a data file."""
    prov = cue_doc["provenance"]
    assert prov["timings_are"] == "ESTIMATES"


# --------------------------------------------------------------------------
# Blindness, re-read out of architecture-spec.md 1.1. Never recalled.
# --------------------------------------------------------------------------

def _blind_section(component):
    """The 1.1 block for one component, from its heading to the next."""
    text = ARCH_SPEC.read_text(encoding="utf-8")
    start = text.index("### 1.1 Model-bearing components")
    end = text.index("### 1.2 Pure-code components")
    section = text[start:end]
    marker = "#### `%s`" % component
    at = section.index(marker)
    nxt = section.find("\n#### ", at + 1)
    return section[at:] if nxt < 0 else section[at:nxt]


def _blind_row(component):
    for line in _blind_section(component).splitlines():
        if line.startswith("| **Blind to**"):
            return line
    raise AssertionError("no Blind to row for %s" % component)


def test_the_objective_set_is_on_reds_blind_list_and_not_the_armorers():
    """THE TRAP, named in the animation spec because it has been got wrong
    once already. Read from source, both directions, so a cue list that moves
    it onto the Armorer fails and so does one that quietly drops it from Red."""
    assert "Objective Set" in _blind_row("RED_STRATEGIST")
    assert "Objective Set" not in _blind_row("ARMORER")


def test_no_cue_ever_darkens_the_objective_set_while_the_armorer_is_lit(cue_doc):
    for cue in cue_doc["cues"]:
        if "ARM" in cue.get("spotlight", []):
            assert "OBJECTIVE_SET" not in cue.get("dim", []), cue["t_ms"]


def test_the_objective_set_is_actually_used_where_it_belongs(cue_doc):
    """The other half. Asserting only the absence would pass on a cue list
    that never mentions the Objective Set at all."""
    with_red = [c for c in cue_doc["cues"]
                if "RED" in c.get("spotlight", []) and "OBJECTIVE_SET" in c.get("dim", [])]
    assert with_red, "no cue stages Red's blindness to the Objective Set"


def test_the_fixture_suite_chip_does_not_claim_iam(cue_doc):
    """architecture-spec.md 1.1 on the Armorer: the fixture blindness is
    APPLICATION CONVENTION plus a code check, NOT IAM enforcement, and it says
    never to call this one enforced on camera. The chip prints the class it is
    given, so the class in the data file is the thing that can lie."""
    row = _blind_row("ARMORER")
    assert "NOT IAM enforcement" in row
    assert cue_doc["blindness_targets"]["FIXTURE_SUITES"]["enforcement"] == "convention"


def test_the_heldout_chip_does_claim_iam(cue_doc):
    """The same row, the other way: the held-out family IS real IAM, and
    understating it would give away the strongest claim in the beat."""
    row = _blind_row("ARMORER")
    assert "IS real IAM" in row
    assert cue_doc["blindness_targets"]["HELDOUT"]["enforcement"] == "iam"


def test_every_blindness_target_cites_a_component_the_spec_agrees_is_blind(cue_doc):
    """Each target names the components blind to it in its `source`. For every
    component named there, the spec's own Blind to row must be non-empty - a
    citation to a component with no blindness row is a fabricated one."""
    components = ["RED_STRATEGIST", "CORONER", "ARMORER"]
    for name, spec in cue_doc["blindness_targets"].items():
        cited = [c for c in components if c in spec["source"]]
        for component in cited:
            assert len(_blind_row(component)) > 40, (name, component)


# --------------------------------------------------------------------------
# The player. The static half.
# --------------------------------------------------------------------------

def test_the_player_makes_no_network_request():
    """Self-contained is not a nicety: a file:// page cannot fetch, and a
    capture that needs a web server is a capture that fails at 2am."""
    html = PLAYER_PATH.read_text(encoding="utf-8")
    for needle in ("src=\"http", "href=\"http", "@import", "fetch(", "XMLHttpRequest"):
        assert needle not in html, needle


def test_the_player_carries_the_cue_file_verbatim():
    html = PLAYER_PATH.read_text(encoding="utf-8")
    embedded = checker._between(html, checker.CUE_EMBED_OPEN, checker.CUE_EMBED_CLOSE)
    assert embedded.strip() == CUES_PATH.read_text(encoding="utf-8").strip()


def test_the_player_carries_the_svg_verbatim():
    html = PLAYER_PATH.read_text(encoding="utf-8")
    embedded = checker._between(html, checker.SVG_EMBED_OPEN, checker.SVG_EMBED_CLOSE)
    assert embedded.strip() == SVG_PATH.read_text(encoding="utf-8").strip()


# --------------------------------------------------------------------------
# The player. The executed half: the timeline core is pulled out of the page
# and RUN in node, against the real cue list and the real node and edge ids.
# --------------------------------------------------------------------------

NODE = shutil.which("node")

requires_node = pytest.mark.skipif(
    NODE is None,
    reason="node is not on PATH. The player's timeline core is JavaScript and "
           "nothing in requirements.txt can execute it, so these tests are "
           "INERT on this machine - they are not passing, they are absent.")


def _extract_core():
    html = PLAYER_PATH.read_text(encoding="utf-8")
    body = html.split(CORE_BEGIN, 1)[1].split(CORE_END, 1)[0]
    # The split lands inside the opening comment and just inside the closing
    # one, so both fragments are re-balanced rather than trimmed by guesswork.
    return "/*" + body + "*/"


def _svg_class_ids(class_token):
    root = ET.parse(str(SVG_PATH)).getroot()
    return [e.get("id") for e in root.iter()
            if e.get("id") and class_token in (e.get("class") or "").split()]


@pytest.fixture(scope="module")
def probes(tmp_path_factory):
    """One node run. Every timeline test asserts against values this produced,
    so a broken core fails the whole group rather than one case."""
    if NODE is None:
        pytest.skip("node is not on PATH")

    data = json.loads(CUES_PATH.read_text(encoding="utf-8"))
    harness = _extract_core() + """
const tl = globalThis.CrucibleCueTimeline.makeTimeline({
  data: %s, nodeIds: %s, edgeIds: %s });

const sweep = [0, 1200, 3200, 8400, 20800, 20900, 21400, 29200, 41000, 41450, 45000];
const forward  = sweep.map(t => tl.computeFrame(t));
// Same instants, walked backwards and interleaved with other seeks. If any
// state survived between calls the two arrays would differ.
const shuffled = [44000, 100, 30000, 5, 20800, 41000, 12400].map(t => tl.computeFrame(t));
const backward = sweep.slice().reverse().map(t => tl.computeFrame(t)).reverse();

console.log(JSON.stringify({
  frames: Object.fromEntries(sweep.map((t, i) => [String(t), forward[i]])),
  forward: forward,
  backward: backward,
  shuffled_count: shuffled.length,
  clamp: { neg: tl.clampT(-500), zero: tl.clampT(0), max: tl.clampT(45000),
           over: tl.clampT(45001), way_over: tl.clampT(9e9),
           nan: tl.clampT("not a number"), frac: tl.clampT(1234.6) },
  chip_strike: [0, 0.2, 0.34, 0.5, 0.9, 1].map(p => tl.chipStrike(p)),
  chip_opacity: [0, 0.34, 1].map(p => tl.chipOpacity(p)),
  edge_touches: {
    red_lit_on_red_tgt: tl.edgeTouches("e_RED_TGT", {RED: true}),
    red_lit_on_gate_next: tl.edgeTouches("e_GATE_NEXT", {RED: true}),
    gov_lit_on_next_gov_promote: tl.edgeTouches("e_NEXT_GOV_promote", {GOV: true}),
    anything_on_return_bus: tl.edgeTouches("e_return_bus", {GOV: true, RED: true})
  }
}));
""" % (json.dumps(data), json.dumps(_svg_class_ids("node")),
       json.dumps(_svg_class_ids("edge")))

    path = tmp_path_factory.mktemp("cuecore") / "harness.mjs"
    path.write_text(harness, encoding="utf-8")
    proc = subprocess.run([NODE, str(path)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@requires_node
def test_frame_zero_lights_nothing_and_dims_nothing(probes):
    f = probes["frames"]["0"]
    assert f["lit"] == [] and f["dim_nodes"] == [] and f["dim_edges"] == []
    assert f["spotlighting"] is False and f["boundary_resolved"] is False


@requires_node
def test_a_spotlight_dims_every_component_it_did_not_name(probes, svg_ids):
    """Rule 1 is subtractive. At the Armorer beat exactly one node is lit, and
    every other component is either dimmed or darkened as a blind anchor."""
    all_ids, node_ids = svg_ids
    f = probes["frames"]["20800"]
    assert f["lit"] == ["ARM"]
    accounted = set(f["lit"]) | set(f["dim_nodes"]) | set(f["blind"])
    assert node_ids <= accounted
    assert "ARM" not in f["dim_nodes"]


@requires_node
def test_edges_leaving_a_lit_node_stay_lit_and_the_rest_dim(probes):
    f = probes["frames"]["20800"]
    for edge in ("e_ADP_ARM", "e_ARM_VAL", "e_NARROW_ARM"):
        assert edge not in f["dim_edges"], edge
    assert "e_PLG_LED" in f["dim_edges"]


@requires_node
def test_the_armorer_beat_raises_four_chips_at_three_anchors(probes):
    f = probes["frames"]["20800"]
    got = sorted((c["target"], c["anchor"], c["slot"]) for c in f["chips"])
    assert got == [
        ("FIXTURE_SUITES", "WAR", 0),
        ("HELDOUT", "RED", 1),
        ("RED_PAYLOAD", "RED", 0),
        ("WARDEN_REPORT", "e_WAR_NARROW", 0),
    ]
    assert sorted(f["blind"]) == ["RED", "WAR", "e_WAR_NARROW"]


@requires_node
def test_a_chip_arrives_lit_and_then_quenches(probes):
    """Rule 2 says the thing goes visibly dark. A chip that was never lit
    would read as absence rather than as withholding."""
    strikes = probes["chip_strike"]
    assert strikes[0] == 0 and strikes[1] == 0 and strikes[2] == 0
    assert 0 < strikes[3] < 1
    assert strikes[5] == 1
    assert strikes == sorted(strikes)
    opacities = probes["chip_opacity"]
    assert opacities[0] == 1 and opacities[1] == 1 and opacities[2] < 0.5


@requires_node
def test_the_boundary_resolve_owns_the_closing_frames(probes):
    """Rule 3. Once it fires, no spotlight is still burning: a lit component at
    the moment the thesis lands splits the judge's attention."""
    before = probes["frames"]["29200"]
    after = probes["frames"]["41450"]
    assert before["boundary_resolved"] is False
    assert after["boundary_resolved"] is True
    assert after["lit"] == [] and after["dim_nodes"] == [] and after["chips"] == []
    assert after["spotlighting"] is False


@requires_node
def test_the_boundary_wipe_advances_and_then_stops(probes):
    at_start = probes["frames"]["41000"]
    mid = probes["frames"]["41450"]
    at_end = probes["frames"]["45000"]
    assert at_start["wipe_px"] == 0
    assert 0 < mid["wipe_px"] < 1864 and mid["wipe_running"] is True
    assert at_end["wipe_px"] == 1864 and at_end["wipe_running"] is False


@requires_node
def test_seek_clamps_every_input_to_the_beat(probes):
    c = probes["clamp"]
    assert c["neg"] == 0 and c["zero"] == 0
    assert c["max"] == 45000 and c["over"] == 45000 and c["way_over"] == 45000
    assert c["nan"] == 0
    assert c["frac"] == 1235


@requires_node
def test_the_same_t_renders_the_same_frame_regardless_of_how_it_was_reached(probes):
    """Determinism, which is what makes a headless capture reproducible. The
    two arrays are the same instants walked in opposite directions with other
    seeks in between; if any state leaked across calls they would differ."""
    assert probes["forward"] == probes["backward"]
    assert probes["shuffled_count"] == 7


@requires_node
def test_edge_attribution_reads_the_id_tokens(probes):
    e = probes["edge_touches"]
    assert e["red_lit_on_red_tgt"] is True
    assert e["red_lit_on_gate_next"] is False
    assert e["gov_lit_on_next_gov_promote"] is True
    assert e["anything_on_return_bus"] is False


@requires_node
def test_every_cue_in_the_file_becomes_the_active_cue_at_its_own_t(probes, cue_doc):
    """A cue that can never be reached is a beat that silently does nothing.
    The sweep only samples a few instants, so this checks the mapping the
    validator's R4 exists to protect actually holds in the renderer."""
    by_t = probes["frames"]
    for t in ("0", "1200", "3200", "8400", "20800", "29200", "41000"):
        assert by_t[t]["cue_t_ms"] == int(t)
