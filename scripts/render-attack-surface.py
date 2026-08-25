#!/usr/bin/env python3
"""render-attack-surface.py - the attack surface graph, as a view over frozen evidence.

BUILD-LIST T2-1. This is a RENDERER, not a component. It reads a directory of C6
evidence bundles and the frozen capability manifest, and draws one picture. It
changes no input, writes into no hash-lock, and calls no model. A view over a
frozen input does not change the input.

WHAT IS ON THE PICTURE, AND WHERE EVERY PART OF IT COMES FROM
--------------------------------------------------------------
Nothing here is inferred, smoothed, or predicted. `docs/design/T2-8-runtime-visuals-scope.md`
sec 1: *the visual layer may render only what the event stream carries.* The same rule
applies to a static render, so each element names its source field:

  NODES
    tool nodes         target/refund_agent/capability_manifest.json -> tools[].tool_fqname
    capability classes crucible/manifest/load.py::CAPABILITY_CLASSES + UNCLASSIFIED sentinel
                       (the sentinel is drawn because it is part of the surface: no rule can
                       select it, so a tool landing there is always allowed by the policy.)

  EDGES
    tool -> class      manifest tools[].capability_classes.  Structure, not observation.
    tool -> tool       bundle episodes[].episode_prefix[], kind == TOOL_ATTEMPT, ordered by
                       `seq`.  This is the TRIPWIRE's record of what the target actually
                       CALLED.  START/END are the first and last attempt of an episode.

  EDGE COLOUR - and this is the whole point of the figure
    policy@v0          a rule in policy_chain[0].rules selects that capability class
    policy@vFinal      a rule in policy_chain[-1].rules that is NOT in policy_chain[0]
                       selects that class.  THE EDGES THAT CHANGED ARE THE RUN'S RESULT.
    denial markers     episode_prefix[].policy_decision == DENY, with denied_by_rule_id

  The class-bound claim is not asserted by this script.  It is READ OFF the evidence: a
  rule carries `capability_class`, never a tool name, so the set of tools a rule reaches
  is a manifest lookup, and the DENY records show which tools it actually stopped.  Where
  a rule denied a tool other than the one the attack used, that pair is printed.

WHY IT REFUSES TO DRAW
----------------------
A renderer that draws a plausible picture regardless of its input is a check that cannot
fail, and that failure shape has cost this project repeatedly.  Every guard below exits
non-zero with a named code rather than rendering something reasonable-looking:

  E_NO_BUNDLES          the directory holds no *.c6.json
  E_NO_CALL_EVENTS      no TOOL_ATTEMPT event anywhere - there is no graph to draw
  E_UNKNOWN_TOOL        evidence names a tool the frozen manifest does not
  E_UNKNOWN_CAP         evidence names a capability class that is not one of the frozen set
  E_EVENT_CAP_DRIFT     an event's capability_classes disagree with the manifest's
  E_HANDLE_DRIFT        an event's tool_handle disagrees with the manifest's
  E_CORPUS_HASH_SPLIT   the bundles do not all measure the same corpus
  E_MANIFEST_DRIFT      the bundles were not measured against the manifest on disk
  E_NO_POLICY_CHAIN     a bundle carries no policy_chain, so v0 vs vFinal is undrawable

`scripts/render-attack-surface-negcheck.py` proves each of those can fire, and proves the
unmutated directory still renders, so the guards are not simply always-on.

STALENESS IS COMPUTED, NEVER TYPED
-----------------------------------
The render prints the corpus hash it read out of the bundles and compares it to
`docs/proof/d5-corpus-freeze.json`.  If they differ, the header says so in red.  No hash
value is typed into this file or into any document - ruling 46, a frozen hash has exactly
one owner, the artifact.  The renderer reads the value at use time and prints what it read.

Run:
  python scripts/render-attack-surface.py <bundle_dir>
  python scripts/render-attack-surface.py <bundle_dir> --out-html docs/diagrams/attack-surface.html
  python scripts/render-attack-surface.py <bundle_dir> --json -      # derived graph to stdout
"""

import argparse
import collections
import datetime
import html
import json
import math
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from crucible.manifest import CAPABILITY_CLASSES, UNCLASSIFIED, load_part_a  # noqa: E402

DEFAULT_MANIFEST = "target/refund_agent/capability_manifest.json"
DEFAULT_FREEZE = "docs/proof/d5-corpus-freeze.json"


class RenderError(Exception):
    """A refusal to draw. `code` is the machine-checkable half."""

    def __init__(self, code, detail):
        self.code = code
        self.detail = detail
        super().__init__("%s: %s" % (code, detail))


# ---------------------------------------------------------------- loading


def load_manifest(path):
    """Load Part A of the frozen capability manifest and its hash.

    Goes through `crucible.manifest.load_part_a` on purpose: the manifest's own loader
    is the artifact that owns the hash, so the value is read rather than recomputed here.
    """
    manifest, manifest_hash = load_part_a(str(path))
    tools = []
    for t in manifest["tools"]:
        tools.append(
            {
                "name": t["tool_fqname"].rsplit(".", 1)[-1],
                "fqname": t["tool_fqname"],
                "handle": t["tool_handle"],
                "classes": list(t["capability_classes"]),
            }
        )
    return {"tools": tools, "manifest_hash": manifest_hash, "target_id": manifest["target_id"]}


def load_bundles(bundle_dir):
    """Every *.c6.json in the directory, in filename order, each with its path."""
    paths = sorted(pathlib.Path(bundle_dir).glob("*.c6.json"))
    if not paths:
        raise RenderError("E_NO_BUNDLES", "no *.c6.json under %s" % bundle_dir)
    out = []
    for p in paths:
        try:
            out.append((p, json.loads(p.read_text(encoding="utf-8"))))
        except (ValueError, UnicodeDecodeError) as exc:
            raise RenderError("E_NO_BUNDLES", "%s is not readable JSON: %s" % (p.name, exc))
    return out


# ---------------------------------------------------------------- graph


def build_graph(manifest, bundles, freeze_path=None):
    """Turn the manifest plus the bundles into the drawable graph, or refuse."""
    by_name = {t["name"]: t for t in manifest["tools"]}
    frozen_classes = list(CAPABILITY_CLASSES) + [UNCLASSIFIED]

    run_ids = []
    corpus_hashes = collections.Counter()
    manifest_hashes = collections.Counter()
    spine_versions = collections.Counter()
    bundle_versions = collections.Counter()

    calls = collections.Counter()               # tool -> TOOL_ATTEMPT count
    transitions = collections.Counter()         # (from, to) -> count, START/END included
    denials = collections.Counter()             # (rule_id, tool) -> count
    approvals = collections.Counter()           # tool -> APPROVAL_REQUIRED count
    decisions = collections.Counter()
    episodes_seen = 0

    v0_rules = {}                               # rule_id -> rule, union over runs
    final_rules = {}
    v0_runs_by_class = collections.Counter()
    new_runs_by_class = collections.Counter()
    new_rule_runs = collections.Counter()       # dsl body -> run count
    rule_meta = {}                              # rule_id -> {class, verb, origin, text}
    runs_with_growth = 0

    for path, b in bundles:
        rm = b.get("run_manifest") or {}
        run_ids.append(rm.get("run_id") or path.stem)
        locks = rm.get("hash_locks") or {}
        if locks.get("corpus_hash"):
            corpus_hashes[locks["corpus_hash"]] += 1
        if locks.get("manifest_hash"):
            manifest_hashes[locks["manifest_hash"]] += 1
        if rm.get("spine_version") is not None:
            spine_versions[rm["spine_version"]] += 1
        if b.get("bundle_version") is not None:
            bundle_versions[b["bundle_version"]] += 1

        chain = b.get("policy_chain")
        if not chain:
            raise RenderError("E_NO_POLICY_CHAIN", "%s carries no policy_chain" % path.name)
        first, last = chain[0], chain[-1]
        first_ids = {r["rule_id"] for r in first.get("rules", [])}
        if len(chain) > 1:
            runs_with_growth += 1
        for r in first.get("rules", []):
            v0_rules[r["rule_id"]] = r
            rule_meta[r["rule_id"]] = r
        for cls in {r["capability_class"] for r in first.get("rules", [])}:
            v0_runs_by_class[cls] += 1
        added_classes = set()
        for r in last.get("rules", []):
            final_rules[r["rule_id"]] = r
            rule_meta[r["rule_id"]] = r
            if r["rule_id"] not in first_ids:
                added_classes.add(r["capability_class"])
                body = r["dsl_text"].split(": ", 1)[-1]
                new_rule_runs[body] += 1
        for cls in added_classes:
            new_runs_by_class[cls] += 1

        for ep in b.get("episodes", []):
            episodes_seen += 1
            seq = [e for e in ep.get("episode_prefix", []) if e.get("kind") == "TOOL_ATTEMPT"]
            seq.sort(key=lambda e: e.get("seq", 0))
            prev = None
            for e in seq:
                name = e.get("tool_name")
                if name not in by_name:
                    raise RenderError(
                        "E_UNKNOWN_TOOL",
                        "%s: episode %s calls %r, which the frozen manifest does not declare"
                        % (path.name, ep.get("episode_id"), name),
                    )
                ev_classes = list(e.get("capability_classes") or [])
                for c in ev_classes:
                    if c not in frozen_classes:
                        raise RenderError(
                            "E_UNKNOWN_CAP",
                            "%s: %s carries capability class %r, not one of the frozen set"
                            % (path.name, name, c),
                        )
                if sorted(ev_classes) != sorted(by_name[name]["classes"]):
                    raise RenderError(
                        "E_EVENT_CAP_DRIFT",
                        "%s: %s recorded as %s, manifest declares %s"
                        % (path.name, name, sorted(ev_classes), sorted(by_name[name]["classes"])),
                    )
                if e.get("tool_handle") and e["tool_handle"] != by_name[name]["handle"]:
                    # The manifest's own handle is deliberately NOT echoed here. Ruling 46:
                    # a frozen value has one owner, the artifact. The error names where to
                    # read it instead, so this text is safe to paste into a document.
                    raise RenderError(
                        "E_HANDLE_DRIFT",
                        "%s: %s recorded as handle %s, which is not the handle the frozen "
                        "manifest declares for it (read it from %s)"
                        % (path.name, name, e["tool_handle"], DEFAULT_MANIFEST),
                    )
                calls[name] += 1
                dec = e.get("policy_decision")
                if dec is not None:
                    decisions[dec] += 1
                if dec == "DENY":
                    denials[(e.get("denied_by_rule_id"), name)] += 1
                elif dec == "APPROVAL_REQUIRED":
                    approvals[name] += 1
                transitions[(prev or "START", name)] += 1
                prev = name
            if prev is not None:
                transitions[(prev, "END")] += 1

    if not calls:
        raise RenderError(
            "E_NO_CALL_EVENTS",
            "%d episodes across %d bundles and not one TOOL_ATTEMPT event - there is no "
            "call graph to draw" % (episodes_seen, len(bundles)),
        )
    if len(corpus_hashes) != 1:
        raise RenderError(
            "E_CORPUS_HASH_SPLIT",
            "%d distinct corpus_hash values across %d bundles; a single render cannot "
            "describe two corpora" % (len(corpus_hashes), len(bundles)),
        )

    corpus_hash = next(iter(corpus_hashes))
    bundle_manifest_hash = next(iter(manifest_hashes)) if len(manifest_hashes) == 1 else None
    if bundle_manifest_hash is None:
        raise RenderError(
            "E_MANIFEST_DRIFT",
            "bundles disagree on manifest_hash (%d distinct values)" % len(manifest_hashes),
        )
    if not manifest["manifest_hash"].startswith(bundle_manifest_hash):
        raise RenderError(
            "E_MANIFEST_DRIFT",
            "the bundles were measured against a capability manifest that is not the one on "
            "disk; the picture would name tools the run never had",
        )

    # Staleness, computed rather than typed.
    freeze_hash, freeze_file = None, None
    if freeze_path is not None:
        fp = pathlib.Path(freeze_path)
        if fp.exists():
            freeze_file = str(fp.relative_to(REPO)) if fp.is_absolute() else str(fp)
            freeze_hash = json.loads(fp.read_text(encoding="utf-8")).get("corpus_hash")

    # tool -> class membership edges, coloured by governance
    edges = []
    for t in manifest["tools"]:
        for cls in t["classes"]:
            edges.append(
                {
                    "tool": t["name"],
                    "cls": cls,
                    "v0_runs": v0_runs_by_class.get(cls, 0),
                    "new_runs": new_runs_by_class.get(cls, 0),
                    "state": (
                        "new"
                        if new_runs_by_class.get(cls, 0)
                        else "v0"
                        if v0_runs_by_class.get(cls, 0)
                        else "none"
                    ),
                }
            )

    # Which tools a rule REACHES by class, versus which it was actually recorded stopping.
    reach = []
    for rid, r in sorted(final_rules.items()):
        if rid in v0_rules:
            continue
        cls = r["capability_class"]
        reached = [t["name"] for t in manifest["tools"] if cls in t["classes"]]
        stopped = sorted({tool for (rr, tool) in denials if rr == rid})
        reach.append(
            {
                "rule_id": rid,
                "cls": cls,
                "verb": r["verb"],
                "origin": r.get("origin"),
                "text": r["dsl_text"].split(": ", 1)[-1],
                "reaches": reached,
                "reaches_never_called": [t for t in reached if not calls.get(t)],
                "recorded_denials": stopped,
            }
        )

    return {
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "bundle_dir": str(bundle_dir_of(bundles)),
        "bundle_count": len(bundles),
        "run_ids": run_ids,
        "episodes": episodes_seen,
        "corpus_hash": corpus_hash,
        "corpus_freeze_hash": freeze_hash,
        "corpus_freeze_file": freeze_file,
        "corpus_is_current": (freeze_hash is not None and freeze_hash == corpus_hash),
        "manifest_hash": bundle_manifest_hash,
        "target_id": manifest["target_id"],
        "spine_versions": dict(spine_versions),
        "bundle_versions": dict(bundle_versions),
        "tools": [
            dict(t, calls=calls.get(t["name"], 0), observed=bool(calls.get(t["name"])))
            for t in manifest["tools"]
        ],
        "classes": frozen_classes,
        "class_state": {
            c: {"v0_runs": v0_runs_by_class.get(c, 0), "new_runs": new_runs_by_class.get(c, 0)}
            for c in frozen_classes
        },
        "edges": edges,
        "transitions": [
            {"from": a, "to": b, "count": n} for (a, b), n in sorted(transitions.items())
        ],
        "decisions": dict(decisions),
        "denials": [
            {"rule_id": rid, "tool": tool, "count": n}
            for (rid, tool), n in sorted(denials.items(), key=lambda kv: -kv[1])
        ],
        "approvals": dict(approvals),
        "runs_with_growth": runs_with_growth,
        "new_rule_texts": [
            {"text": t, "runs": n} for t, n in new_rule_runs.most_common()
        ],
        "rule_reach": reach,
        "seed_rules": [
            {
                "rule_id": rid,
                "cls": r["capability_class"],
                "verb": r["verb"],
                "text": r["dsl_text"].split(": ", 1)[-1],
            }
            for rid, r in sorted(v0_rules.items())
        ],
    }


def bundle_dir_of(bundles):
    return bundles[0][0].parent


# ---------------------------------------------------------------- svg


BG = "#f7f8fa"
INK = "#161b22"
MUTED = "#5c6672"
GREY = "#aeb6c2"
BLUE = "#1f5fd0"
ORANGE = "#d2481c"
HOLLOW = "#c6ccd6"
RED = "#b3261e"

W, H = 1680, 1330
TOOL_X = 700
TOOL_W = 266
CLASS_X = 1290
CLASS_W = 300
NODE_H = 50


def esc(s):
    return html.escape(str(s), quote=True)


def _tool_y(i, n):
    top, step = 262, 96
    return top + i * step


def _class_y(i, n):
    top, step = 284, 112
    return top + i * step


def _edge_colour(state):
    return {"new": ORANGE, "v0": BLUE}.get(state, GREY)


def render_svg(g):
    tools = g["tools"]
    classes = g["classes"]
    ty = {t["name"]: _tool_y(i, len(tools)) for i, t in enumerate(tools)}
    cy = {c: _class_y(i, len(classes)) for i, c in enumerate(classes)}

    p = []
    a = p.append
    a('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
      'font-family="Inter, Segoe UI, Helvetica, Arial, sans-serif">' % (W, H, W, H))
    a('<rect width="%d" height="%d" fill="%s"/>' % (W, H, BG))
    a("<defs>")
    for name, col in (("g", GREY), ("b", BLUE), ("o", ORANGE)):
        a('<marker id="ah-%s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
          'markerHeight="7" orient="auto-start-reverse">'
          '<path d="M0,0 L10,5 L0,10 z" fill="%s"/></marker>' % (name, col))
    a("</defs>")

    # ---- header -------------------------------------------------------
    a('<text x="60" y="66" font-size="34" font-weight="700" fill="%s">'
      'CRUCIBLE &#183; attack surface</text>' % INK)
    a('<text x="60" y="98" font-size="16" fill="%s">'
      'Nodes are the frozen capability manifest. Edges are the tripwire’s recorded calls. '
      'Colour is policy@v0 versus policy@vFinal.</text>' % MUTED)

    stale = not g["corpus_is_current"]
    banner = (
        "DEVELOPMENT INPUT — these bundles measure a corpus that is not the current freeze"
        if stale
        else "corpus matches the current freeze record"
    )
    a('<rect x="60" y="118" width="%d" height="34" rx="6" fill="%s" opacity="0.12"/>'
      % (W - 120, RED if stale else BLUE))
    a('<text x="76" y="141" font-size="15" font-weight="700" fill="%s">%s</text>'
      % (RED if stale else BLUE, esc(banner)))
    a('<text x="%d" y="141" font-size="13" text-anchor="end" fill="%s">'
      'corpus_hash %s &#183; freeze record %s</text>'
      % (W - 76, MUTED, esc(g["corpus_hash"]),
         esc(g["corpus_freeze_hash"] or "not read")))

    a('<text x="60" y="180" font-size="13" fill="%s">'
      '%d evidence bundles &#183; %d episodes &#183; %s &#8230; %s &#183; manifest_hash %s '
      '&#183; spine %s</text>'
      % (MUTED, g["bundle_count"], g["episodes"], esc(g["run_ids"][0]), esc(g["run_ids"][-1]),
         esc(g["manifest_hash"]),
         esc(", ".join(str(k) for k in sorted(g["spine_versions"])))))

    # ---- column captions ---------------------------------------------
    a('<text x="%d" y="216" font-size="13" font-weight="700" text-anchor="middle" fill="%s">'
      'RECORDED CALL SEQUENCES &#183; tripwire</text>' % (TOOL_X - TOOL_W // 2 - 180, MUTED))
    a('<text x="%d" y="216" font-size="13" font-weight="700" text-anchor="middle" fill="%s">'
      'TOOLS &#183; %d, from the manifest</text>' % (TOOL_X, MUTED, len(tools)))
    a('<text x="%d" y="216" font-size="13" font-weight="700" text-anchor="middle" fill="%s">'
      'CAPABILITY CLASSES &#183; %d + sentinel</text>'
      % (CLASS_X, MUTED, len(classes) - 1))

    # ---- transition arcs, left of the tool column ---------------------
    left = TOOL_X - TOOL_W // 2
    maxn = max((t["count"] for t in g["transitions"]), default=1)
    for tr in sorted(g["transitions"], key=lambda t: t["count"]):
        src, dst, n = tr["from"], tr["to"], tr["count"]
        if src in ("START",) or dst in ("END",):
            continue
        if src not in ty or dst not in ty:
            continue
        wpx = 0.9 + 3.4 * (math.log10(n + 1) / math.log10(maxn + 1))
        op = 0.20 + 0.55 * (math.log10(n + 1) / math.log10(maxn + 1))
        y1, y2 = ty[src], ty[dst]
        if src == dst:
            a('<path d="M %d %d C %d %d, %d %d, %d %d" fill="none" stroke="%s" '
              'stroke-width="%.2f" opacity="%.2f" marker-end="url(#ah-g)"/>'
              % (left, y1 - 13, left - 74, y1 - 34, left - 74, y1 + 34, left, y1 + 13,
                 GREY, wpx, op))
            continue
        d = abs(y2 - y1)
        bulge = 46 + 0.40 * d + (26 if y2 < y1 else 0)
        a('<path d="M %d %d Q %d %d %d %d" fill="none" stroke="%s" stroke-width="%.2f" '
          'opacity="%.2f" marker-end="url(#ah-g)"/>'
          % (left, y1, left - bulge, (y1 + y2) // 2, left, y2, GREY, wpx, op))

    # Entry points: how many episodes OPENED with this tool. Drawn as a badge on the node
    # rather than as another arc, because the arc field is already the densest part of the
    # figure and the exact counts are in the transition matrix on the page.
    starts = {t["to"]: t["count"] for t in g["transitions"] if t["from"] == "START"}

    # ---- tool nodes ---------------------------------------------------
    for t in tools:
        y = ty[t["name"]]
        x = TOOL_X - TOOL_W // 2
        observed = t["observed"]
        a('<rect x="%d" y="%d" width="%d" height="%d" rx="9" fill="%s" stroke="%s" '
          'stroke-width="%s" %s/>'
          % (x, y - NODE_H // 2, TOOL_W, NODE_H, "#ffffff" if observed else BG,
             INK if observed else HOLLOW, "1.8" if observed else "1.4",
             "" if observed else 'stroke-dasharray="5 4"'))
        a('<text x="%d" y="%d" font-size="16" font-weight="%s" fill="%s">%s</text>'
          % (x + 16, y + 1, "600" if observed else "400",
             INK if observed else MUTED, esc(t["name"])))
        label = ("%d calls" % t["calls"]) if observed else "never called"
        if starts.get(t["name"]):
            label += " · opened %d episodes" % starts[t["name"]]
        a('<text x="%d" y="%d" font-size="11" fill="%s">%s</text>'
          % (x + 16, y + 17, MUTED if observed else HOLLOW, esc(label)))
        if t["name"] in g["approvals"]:
            a('<text x="%d" y="%d" font-size="10" text-anchor="end" fill="%s">'
              'approval gate &#215;%d</text>'
              % (x + TOOL_W - 12, y + 17, BLUE, g["approvals"][t["name"]]))
        stopped = sum(d["count"] for d in g["denials"] if d["tool"] == t["name"])
        if stopped:
            a('<text x="%d" y="%d" font-size="10" text-anchor="end" fill="%s">'
              'denied &#215;%d</text>' % (x + TOOL_W - 12, y - 8, ORANGE, stopped))

    # ---- class nodes --------------------------------------------------
    for c in classes:
        y = cy[c]
        x = CLASS_X - CLASS_W // 2
        st = g["class_state"][c]
        col = ORANGE if st["new_runs"] else (BLUE if st["v0_runs"] else GREY)
        a('<rect x="%d" y="%d" width="%d" height="%d" rx="9" fill="#ffffff" stroke="%s" '
          'stroke-width="%s"/>'
          % (x, y - NODE_H // 2 - 3, CLASS_W, NODE_H + 6, col,
             "2.6" if st["new_runs"] else ("2.0" if st["v0_runs"] else "1.2")))
        a('<text x="%d" y="%d" font-size="14" font-weight="600" fill="%s">%s</text>'
          % (x + 14, y - 1, col if (st["new_runs"] or st["v0_runs"]) else MUTED, esc(c)))
        if st["new_runs"]:
            sub = "governed at v0 &#183; NEW RULE at vFinal in %d/%d runs" % (
                st["new_runs"], g["bundle_count"]) if st["v0_runs"] else (
                "NEW RULE at vFinal in %d/%d runs" % (st["new_runs"], g["bundle_count"]))
        elif st["v0_runs"]:
            sub = "governed at v0 in %d/%d runs" % (st["v0_runs"], g["bundle_count"])
        else:
            sub = "ungoverned in every run"
        a('<text x="%d" y="%d" font-size="11" fill="%s">%s</text>' % (x + 14, y + 16, MUTED, sub))

    # ---- membership edges, coloured ------------------------------------
    for e in sorted(g["edges"], key=lambda e: {"none": 0, "v0": 1, "new": 2}[e["state"]]):
        y1 = ty[e["tool"]]
        y2 = cy[e["cls"]]
        x1 = TOOL_X + TOOL_W // 2
        x2 = CLASS_X - CLASS_W // 2
        col = _edge_colour(e["state"])
        mk = {"new": "o", "v0": "b"}.get(e["state"], "g")
        wpx = {"new": 3.0, "v0": 2.0}.get(e["state"], 1.1)
        op = {"new": 0.95, "v0": 0.75}.get(e["state"], 0.45)
        mid = (x1 + x2) // 2
        a('<path d="M %d %d C %d %d, %d %d, %d %d" fill="none" stroke="%s" '
          'stroke-width="%.1f" opacity="%.2f" marker-end="url(#ah-%s)"/>'
          % (x1, y1, mid, y1, mid, y2, x2 - 10, y2, col, wpx, op, mk))

    # ---- legend -------------------------------------------------------
    ly = H - 218
    a('<rect x="60" y="%d" width="%d" height="176" rx="10" fill="#ffffff" stroke="%s" '
      'stroke-width="1"/>' % (ly, W - 120, "#e2e6ec"))
    a('<text x="84" y="%d" font-size="14" font-weight="700" fill="%s">LEGEND</text>'
      % (ly + 28, INK))
    rows = [
        (GREY, 1.1, "class the policy never selected, in any run"),
        (BLUE, 2.0, "governed at policy@v0 — a seed rule selects this class"),
        (ORANGE, 3.0, "GOVERNED FOR THE FIRST TIME AT policy@vFinal — the run’s result"),
    ]
    for i, (col, wpx, txt) in enumerate(rows):
        yy = ly + 56 + i * 26
        a('<line x1="88" y1="%d" x2="150" y2="%d" stroke="%s" stroke-width="%.1f"/>'
          % (yy, yy, col, wpx))
        a('<text x="164" y="%d" font-size="13" fill="%s">%s</text>' % (yy + 4, INK, esc(txt)))
    yy = ly + 56 + 3 * 26
    a('<path d="M 88 %d Q 110 %d 150 %d" fill="none" stroke="%s" stroke-width="2" '
      'opacity="0.55"/>' % (yy, yy - 14, yy, GREY))
    a('<text x="164" y="%d" font-size="13" fill="%s">%s</text>'
      % (yy + 4, INK,
         esc("recorded call transition, tripwire; thickness is log(count) over all bundles")))
    a('<text x="88" y="%d" font-size="13" fill="%s">%s</text>'
      % (ly + 158, MUTED,
         esc("A dashed hollow tool was never called in any bundle. It is still on the surface, "
             "and a class-bound rule still reaches it.")))

    # ---- the point, spelled out --------------------------------------
    cross = [d for d in g["denials"] if d["rule_id"]]
    by_rule = collections.defaultdict(list)
    for d in cross:
        by_rule[d["rule_id"]].append(d["tool"])
    multi = sorted(
        [(r, sorted(set(v))) for r, v in by_rule.items() if len(set(v)) > 1],
        key=lambda rv: (-len(rv[1]), rv[0]),
    )
    a('<text x="60" y="%d" font-size="15" font-weight="700" fill="%s">%s</text>'
      % (ly - 62, INK,
         esc("Class-bound, not string-matched — read off the DENY records, not asserted:")))
    if multi:
        for i, (rid, toolset) in enumerate(multi[:2]):
            cls = next((r["cls"] for r in g["rule_reach"] if r["rule_id"] == rid), "?")
            a('<text x="60" y="%d" font-size="14" fill="%s">%s</text>'
              % (ly - 38 + i * 22, MUTED,
                 esc("rule %s selects cap:%s and denied calls to %d distinct tools — %s. "
                     "The rule text contains no tool name."
                     % (rid, cls, len(toolset), ", ".join(toolset)))))
    else:
        a('<text x="60" y="%d" font-size="14" fill="%s">%s</text>'
          % (ly - 38, MUTED,
             esc("no rule in this bundle set denied more than one distinct tool")))

    a('<text x="60" y="%d" font-size="11" fill="%s">%s</text>'
      % (H - 22, MUTED,
         esc("Rendered %s by scripts/render-attack-surface.py from %s. "
             "Counts are event counts, not rates. No figure here is a rate."
             % (g["generated_at"], g["bundle_dir"]))))
    a("</svg>")
    return "\n".join(p)


# ---------------------------------------------------------------- html


def render_html(g, svg):
    def row(cells, tag="td"):
        return "<tr>" + "".join("<%s>%s</%s>" % (tag, c, tag) for c in cells) + "</tr>"

    reach_rows = []
    for r in g["rule_reach"]:
        never = ", ".join(r["reaches_never_called"]) or "—"
        stopped = ", ".join(r["recorded_denials"]) or "—"
        reach_rows.append(
            row([
                "<code>%s</code>" % esc(r["rule_id"]),
                esc(r["verb"]),
                "<code>%s</code>" % esc(r["cls"]),
                "<code>%s</code>" % esc(r["text"]),
                esc(", ".join(r["reaches"])),
                "<b>%s</b>" % esc(never),
                "<b>%s</b>" % esc(stopped),
            ])
        )

    seed_rows = [
        row([
            "<code>%s</code>" % esc(r["rule_id"]),
            esc(r["verb"]),
            "<code>%s</code>" % esc(r["cls"]),
            "<code>%s</code>" % esc(r["text"]),
        ])
        for r in g["seed_rules"]
    ]

    new_rows = [
        row(["<code>%s</code>" % esc(t["text"]), "%d / %d runs" % (t["runs"], g["bundle_count"])])
        for t in g["new_rule_texts"]
    ]

    tool_names = [t["name"] for t in g["tools"]]
    tmap = {(t["from"], t["to"]): t["count"] for t in g["transitions"]}
    head = row(["from \\ to"] + [esc(n) for n in tool_names] + ["END"], tag="th")
    mrows = []
    for a_ in tool_names:
        cells = ["<b>%s</b>" % esc(a_)]
        for b_ in tool_names + ["END"]:
            n = tmap.get((a_, b_), 0)
            cells.append(
                ('<span class="hot">%d</span>' % n) if n else '<span class="zero">0</span>'
            )
        mrows.append(row(cells))
    start_cells = ["<b>START</b>"] + [
        ('<span class="hot">%d</span>' % tmap.get(("START", b_), 0))
        if tmap.get(("START", b_), 0)
        else '<span class="zero">0</span>'
        for b_ in tool_names
    ] + ['<span class="zero">—</span>']

    den_rows = [
        row(["<code>%s</code>" % esc(d["rule_id"] or "—"), esc(d["tool"]), str(d["count"])])
        for d in g["denials"]
    ]

    stale = not g["corpus_is_current"]
    banner = (
        "DEVELOPMENT INPUT. The corpus hash in these bundles is not the hash in "
        "<code>%s</code>. The render that ships must be regenerated from a batch whose "
        "corpus hash matches the current freeze record." % esc(g["corpus_freeze_file"] or "?")
        if stale
        else "The corpus hash in these bundles matches the current freeze record."
    )

    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CRUCIBLE attack surface</title>
<style>
 :root {{ color-scheme: light; }}
 body {{ margin:0; background:#f7f8fa; color:#161b22;
        font:15px/1.55 Inter, "Segoe UI", Helvetica, Arial, sans-serif; }}
 main {{ max-width:1740px; margin:0 auto; padding:28px 24px 80px; }}
 h1 {{ font-size:30px; margin:0 0 6px; letter-spacing:-.02em; }}
 h2 {{ font-size:19px; margin:40px 0 10px; }}
 p.sub {{ color:#5c6672; margin:0 0 18px; }}
 .banner {{ border-left:5px solid {bar}; background:{bg}; padding:12px 16px;
            border-radius:0 8px 8px 0; margin:16px 0 24px; font-size:14px; }}
 .fig {{ background:#fff; border:1px solid #e2e6ec; border-radius:12px; padding:10px;
         overflow-x:auto; }}
 .fig svg {{ display:block; min-width:1680px; height:auto; }}
 table {{ border-collapse:collapse; width:100%; font-size:13px; background:#fff;
          border:1px solid #e2e6ec; border-radius:10px; overflow:hidden; }}
 th, td {{ text-align:left; padding:7px 10px; border-bottom:1px solid #eef1f5;
           vertical-align:top; }}
 th {{ background:#f0f2f6; font-size:12px; letter-spacing:.03em; text-transform:uppercase;
       color:#5c6672; }}
 code {{ font:12px/1.4 ui-monospace, SFMono-Regular, Consolas, monospace; }}
 .zero {{ color:#c6ccd6; }}
 .hot {{ font-weight:600; }}
 .prov {{ font-size:13px; color:#5c6672; }}
 .prov code {{ color:#161b22; }}
 footer {{ margin-top:44px; font-size:12px; color:#5c6672; }}
</style></head><body><main>

<h1>CRUCIBLE &middot; attack surface</h1>
<p class="sub">A view over frozen evidence. Nodes come from the capability manifest, edges
from the tripwire&rsquo;s recorded calls, colour from the policy chain. Nothing on this page
was inferred; every value was read out of an artifact at render time.</p>

<div class="banner">{banner}</div>

<div class="fig">{svg}</div>

<h2>Provenance &mdash; read from the bundles, not typed</h2>
<table class="prov">
<tr><th>field</th><th>value</th><th>source</th></tr>
{prov}
</table>

<h2>The rules that changed &mdash; and every tool each one reaches</h2>
<p class="sub">A rule carries a <b>capability class</b>, never a tool name. The
&ldquo;reaches&rdquo; column is a manifest lookup, so a rule authored from an attack on one
tool governs every tool in the class &mdash; including tools the red team never called.
&ldquo;Recorded denials&rdquo; is what the tripwire actually observed the rule stopping.</p>
<table>
<tr><th>rule</th><th>verb</th><th>class</th><th>rule text</th><th>reaches (manifest)</th>
<th>reaches, never called</th><th>recorded denials</th></tr>
{reach}
</table>

<h2>policy@v0 &mdash; the seed rules, before any patch</h2>
<table><tr><th>rule</th><th>verb</th><th>class</th><th>rule text</th></tr>{seed}</table>

<h2>Rule bodies added by the ARMORER, and in how many runs</h2>
<table><tr><th>rule body</th><th>runs</th></tr>{new}</table>

<h2>Recorded DENY events, by rule and tool</h2>
<table><tr><th>rule</th><th>tool</th><th>events</th></tr>{den}</table>

<h2>Call transitions &mdash; exact counts behind the arcs</h2>
<table>{head}{start}{matrix}</table>

<footer>
Generated by <code>scripts/render-attack-surface.py</code> at {gen}
from <code>{dir}</code>.<br>
Every number on this page is a count of recorded events over {n} evidence bundles. No number
here is a rate, and none is a result. Where a rate is derived from this data elsewhere it
carries <b>single-sample, k = 1, no stability estimate</b>.<br>
Negative control: <code>python scripts/render-attack-surface-negcheck.py {dir}</code>
</footer>
</main></body></html>
""".format(
        bar="#b3261e" if stale else "#1f5fd0",
        bg="#fdf1ef" if stale else "#eff4fd",
        banner=banner,
        svg=svg,
        prov="\n".join([
            row(["bundle count", str(g["bundle_count"]), "files matched in the bundle directory"]),
            row(["run ids", "<code>%s</code> &hellip; <code>%s</code>"
                 % (esc(g["run_ids"][0]), esc(g["run_ids"][-1])),
                 "<code>run_manifest.run_id</code>"]),
            row(["episodes", str(g["episodes"]), "<code>episodes[]</code>"]),
            row(["corpus_hash", "<code>%s</code>" % esc(g["corpus_hash"]),
                 "<code>run_manifest.hash_locks.corpus_hash</code>"]),
            row(["current freeze corpus_hash",
                 "<code>%s</code>" % esc(g["corpus_freeze_hash"] or "not read"),
                 "<code>%s</code>" % esc(g["corpus_freeze_file"] or "—")]),
            row(["manifest_hash", "<code>%s</code>" % esc(g["manifest_hash"]),
                 "<code>run_manifest.hash_locks.manifest_hash</code>, asserted equal to the "
                 "manifest on disk"]),
            row(["target_id", "<code>%s</code>" % esc(g["target_id"]),
                 "capability manifest"]),
            row(["spine version(s)",
                 esc(", ".join(str(k) for k in sorted(g["spine_versions"]))),
                 "<code>run_manifest.spine_version</code>"]),
            row(["runs whose policy grew past v0",
                 "%d / %d" % (g["runs_with_growth"], g["bundle_count"]),
                 "<code>len(policy_chain) &gt; 1</code>"]),
            row(["policy decisions recorded",
                 esc(json.dumps(g["decisions"], sort_keys=True)),
                 "<code>episode_prefix[].policy_decision</code>"]),
        ]),
        reach="\n".join(reach_rows),
        seed="\n".join(seed_rows),
        new="\n".join(new_rows),
        den="\n".join(den_rows) or "<tr><td colspan=3>none recorded</td></tr>",
        head=head,
        start=row(start_cells),
        matrix="\n".join(mrows),
        gen=esc(g["generated_at"]),
        dir=esc(g["bundle_dir"]),
        n=g["bundle_count"],
    )


# ---------------------------------------------------------------- main


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Render the attack surface graph from a directory of C6 evidence bundles."
    )
    ap.add_argument("bundle_dir", help="directory holding *.c6.json evidence bundles")
    ap.add_argument("--manifest", default=str(REPO / DEFAULT_MANIFEST),
                    help="frozen capability manifest (default: %s)" % DEFAULT_MANIFEST)
    ap.add_argument("--freeze", default=str(REPO / DEFAULT_FREEZE),
                    help="corpus freeze record to compare against (default: %s)" % DEFAULT_FREEZE)
    ap.add_argument("--out-svg", default=None, help="write the SVG here")
    ap.add_argument("--out-html", default=None, help="write the self-contained HTML here")
    ap.add_argument("--json", default=None,
                    help="write the derived graph as JSON here; '-' for stdout")
    args = ap.parse_args(argv)

    try:
        manifest = load_manifest(args.manifest)
        bundles = load_bundles(args.bundle_dir)
        g = build_graph(manifest, bundles, freeze_path=args.freeze)
    except RenderError as exc:
        sys.stderr.write("REFUSED TO RENDER\n  %s\n  %s\n" % (exc.code, exc.detail))
        return 2

    svg = render_svg(g)
    page = render_html(g, svg)

    if args.out_svg:
        pathlib.Path(args.out_svg).write_bytes(svg.encode("utf-8"))
        print("wrote %s (%d bytes)" % (args.out_svg, len(svg.encode("utf-8"))))
    if args.out_html:
        pathlib.Path(args.out_html).write_bytes(page.encode("utf-8"))
        print("wrote %s (%d bytes)" % (args.out_html, len(page.encode("utf-8"))))
    if args.json == "-":
        json.dump(g, sys.stdout, indent=1, sort_keys=True)
        sys.stdout.write("\n")
    elif args.json:
        pathlib.Path(args.json).write_bytes(
            (json.dumps(g, indent=1, sort_keys=True) + "\n").encode("utf-8")
        )
        print("wrote %s" % args.json)
    if not (args.out_svg or args.out_html or args.json):
        sys.stdout.write(svg + "\n")

    stale = "" if g["corpus_is_current"] else "  [corpus is NOT the current freeze]"
    print(
        "rendered %d bundles, %d episodes, %d tools (%d never called), %d transitions%s"
        % (
            g["bundle_count"],
            g["episodes"],
            len(g["tools"]),
            sum(1 for t in g["tools"] if not t["observed"]),
            len(g["transitions"]),
            stale,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
