#!/usr/bin/env python3
"""hardening-report.py - what CRUCIBLE did to your agent, and what it cost you.

Run:  python scripts/hardening-report.py evidence/smoke-2026-08-25/run-02.c6.json \
          --out docs/hardening-report --name smoke-run-02
      python scripts/hardening-report.py --selftest

WHY THIS EXISTS. A run currently ends with a policy file, an evidence bundle and
a console log that says what HAPPENED. None of them says what CHANGED. The
person who just handed CRUCIBLE their agent wants seven answers and the loop
already holds all seven; nothing was assembling them.

  1  what we threw at it
  2  what got through, with the actual call and the actual arguments
  3  what CRUCIBLE did about it, in English beside the DSL
  4  what stops now, the same attacks re-evaluated at policy@vFinal
  5  what your agent can still do, by fixture name
  6  what it cost you - benign work that now needs a human
  7  what we could not tell you

THIS IS A READER, NOT A COMPONENT. It calls no model, opens no socket, reads no
credential, and writes nothing the loop will ever read back. It touches the
loop's code only to REUSE the loop's own arbiters: `crucible.policy.evaluate`
(the real L3 engine, through the warden's adapter), `crucible.warden.replay.
replay_trace` (the real replay walk with its real APPROVAL_ORACLE), and
`crucible.tripwire.evaluate_episode` (the real pure-code tripwire). If this
script and the loop ever disagree about a verdict, this script is the defect.

WHAT SECTION 4 IS, PRECISELY, BECAUSE IT IS THE EASIEST THING HERE TO OVERCLAIM.
It replays each RECORDED path through the final policy: every TOOL_ATTEMPT is
re-evaluated, a blocked attempt removes its TOOL_EXECUTED from the surviving
event list, and the real tripwire then scores what survives. It answers exactly
one question - WOULD THIS EXACT RECORDED SEQUENCE STILL HAVE REACHED THE
INVARIANT. It is NOT a re-run. A live agent handed a refusal it never received
before may go somewhere else entirely, and this replay cannot see that. It is
also NOT the sealed-family transfer figure, which does not exist yet
(docs/contest/BUILD-LIST.md, T2-2).

TWO INPUTS, BOTH REQUIRED.
  run-NN.c6.json   the evidence bundle. The run of record. Everything in
                   sections 1, 2 and 7 comes from here, and the offline reader
                   must accept it before a page is written.
  run-NN.json      the run record beside it. It carries `final_policy` in
                   EXECUTABLE form; the bundle's `policy_chain` carries the same
                   rules as DSL TEXT ONLY. Sections 4, 5 and 6 have to run the
                   policy, so they need the sidecar. The two are cross-checked on
                   rule ids and the report refuses on a mismatch.

NO ROLLED-UP SCORE. BUILD-LIST T2-2 refuses one and this obeys it.
"""

import argparse
import copy
import html
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from crucible.conductor.real_warden import (                        # noqa: E402
    load_real_benign_suite, _l3_evaluate_call)
from crucible.replay.bundle import read_bundle                      # noqa: E402
from crucible.replay.integrity import BundleRejected                # noqa: E402
from crucible.tripwire.evaluator import evaluate_episode            # noqa: E402
from crucible.tripwire.objective_set import load_objective_set      # noqa: E402
from crucible.warden.replay import Fixture, replay_trace            # noqa: E402

OBJECTIVE_SET = REPO / "contracts" / "objective_set.v1.json"
MANIFEST = REPO / "target" / "refund_agent" / "capability_manifest.json"
SEVERITY_TABLE = REPO / "docs" / "finding-cards" / "severity-floors.json"

MANIFEST_KEYS = ("policy_version", "policy_hash", "manifest_hash",
                 "derived_schema_hash", "objective_set_hash")


# ---------------------------------------------------------------------------
# citations - every word of prose about a family or a capability class is READ
# OUT OF THE FILE THAT OWNS IT, at generation time, and the report refuses to
# render if the quote is gone. Same discipline as severity-floors.json, and for
# the same reason: a gloss a generator invented is a second source of truth,
# and this project has already watched one of those rot.
# ---------------------------------------------------------------------------

FAMILY_SOURCE = "docs/measurement-spec.md"
FAMILY_PATTERN = r"^\*\*(F\d) — (.+?)\*\*"

CLASS_SOURCE = "docs/architecture-spec.md"
CLASS_PATTERN = r"^\| `(CAP_[A-Z_]+)` \| (.+?) \|"


def _read_lines(rel):
    path = REPO / rel
    if not path.exists():
        raise SystemExit(
            "E_CITATION_SOURCE_MISSING: %s does not exist. Every family name and "
            "capability-class gloss on this sheet is quoted out of a file; with the "
            "file gone the report would have to invent them, and it will not." % rel)
    return path.read_text(encoding="utf-8").splitlines()


def load_family_names():
    """`{'F1': ('Direct instruction override (in-band).', line_no)}`.

    Line numbers are RECOMPUTED here, never stored. A stored line number is a
    state cell and docs/contest/BUILD-LIST.md has watched one of those rot twice.
    """
    out = {}
    for i, line in enumerate(_read_lines(FAMILY_SOURCE), start=1):
        m = re.match(FAMILY_PATTERN, line)
        if m:
            out[m.group(1)] = (m.group(2).strip(), i)
    if len(out) < 7:
        raise SystemExit(
            "E_CITATION_ROT: %s yielded %d attack-family headings, expected 7 "
            "(F1-F7). The heading shape this reader quotes has moved. Fix the "
            "pattern against the file rather than letting the report print a "
            "family it cannot name." % (FAMILY_SOURCE, len(out)))
    return out


def load_class_glosses():
    """`{'CAP_MOVES_MONEY': ('Transfers, credits, ...', line_no)}`."""
    out = {}
    for i, line in enumerate(_read_lines(CLASS_SOURCE), start=1):
        m = re.match(CLASS_PATTERN, line)
        if m:
            out[m.group(1)] = (m.group(2).strip(), i)
    if len(out) < 6:
        raise SystemExit(
            "E_CITATION_ROT: %s yielded %d capability-class rows, expected 6. The "
            "table this reader quotes has moved." % (CLASS_SOURCE, len(out)))
    return out


def load_severity_floors(table_path=None):
    """The ONE severity source. Read, never invented, and UNRATED is not 'low'.

    Deliberately re-reads `docs/finding-cards/severity-floors.json` rather than
    carrying a second table: T2-2 already established that file as the only
    place a severity may come from, and a second one would be a second answer.
    """
    path = pathlib.Path(table_path or SEVERITY_TABLE)
    if not path.exists():
        raise SystemExit(
            "E_NO_SEVERITY_TABLE: %s is missing. Severity is READ, never chosen, "
            "so with the table gone every finding would have to be UNRATED for a "
            "reason that is a tooling failure rather than an honest absence of a "
            "declaration. Those two are not the same and must not print the "
            "same." % path)
    table = json.loads(path.read_text(encoding="utf-8"))
    floors = {}
    for row in table.get("floors", []):
        src = REPO / row["source_file"]
        if not src.exists():
            raise SystemExit("E_SEVERITY_SOURCE_MISSING: %s" % row["source_file"])
        lines = src.read_text(encoding="utf-8").splitlines()
        a = _find_line(lines, row["class_quote"])
        b = _find_line(lines, row["source_quote"])
        if a is None or b is None:
            raise SystemExit(
                "E_SEVERITY_CITATION_ROT: %s no longer contains %s. A citation "
                "nobody re-reads is a citation nobody checked."
                % (row["source_file"],
                   row["class_quote"] if a is None else row["source_quote"]))
        if abs(a - b) > row.get("max_line_distance", 12):
            raise SystemExit(
                "E_SEVERITY_CITATION_DETACHED: in %s the class quote (line %d) and "
                "the floor quote (line %d) have drifted apart. They may no longer "
                "describe the same document." % (row["source_file"], a, b))
        floors[row["capability_class"]] = {
            "floor": row["severity_floor"].upper(),
            "source_file": row["source_file"],
            "class_line": a,
            "floor_line": b,
        }
    return table, floors


def _find_line(lines, needle):
    for i, line in enumerate(lines, start=1):
        if needle in line:
            return i
    return None


def assign_severity(classes, floors, amount_minor=None):
    """(severity, why). UNRATED IS AN ABSENCE OF A DECLARATION, NOT A LOW SCORE."""
    if amount_minor is not None and amount_minor > 0:
        return "CRITICAL", (
            "money actually moved: the autopsy carries amount_minor_moved = %d, "
            "which is a recorded fact rather than a judgement about one"
            % amount_minor)
    rated = [(c, floors[c]) for c in sorted(classes or []) if c in floors]
    if rated:
        c, row = rated[0]
        return row["floor"], (
            "`%s` declares severity_floor `%s` at %s:%d"
            % (c, row["floor"].lower(), row["source_file"], row["floor_line"]))
    named = ", ".join(sorted(classes or [])) or "no capability class"
    return "UNRATED", (
        "no severity_floor is declared anywhere in this tree for %s. UNRATED is "
        "the absence of a declaration and is NOT a low severity - reading it as "
        "one is the same error as reading INVALID as FAILED." % named)


# ---------------------------------------------------------------------------
# loading the two inputs
# ---------------------------------------------------------------------------

def open_bundle(path):
    """(bundle, defects). Empty defects means the offline reader accepted it."""
    try:
        bundle, _report = read_bundle(path)
        return bundle, []
    except BundleRejected as exc:
        defects = []
        for d in getattr(exc, "defects", []) or []:
            defects.append({
                "code": getattr(d, "code", "?"),
                "where": getattr(d, "where", ""),
                "detail": (getattr(d, "detail", "") or "")[:400],
            })
        raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        return raw, defects or [{"code": "E_REJECTED", "where": "",
                                 "detail": str(exc)[:400]}]


def open_run_record(c6_path):
    """The sidecar carrying the EXECUTABLE final policy.

    Refuses rather than degrades. A report that silently dropped sections 4, 5
    and 6 would print sections 1, 2 and 3 - all attack, no defence - and read as
    a red-team report, which is precisely the thing this project is not.
    """
    plain = c6_path.with_name(c6_path.name.replace(".c6.json", ".json"))
    if not plain.exists() or plain == c6_path:
        raise SystemExit(
            "E_NO_RUN_RECORD: expected the run record at %s beside the bundle.\n"
            "The bundle's policy_chain carries rule DSL TEXT; only the run record "
            "carries the final policy in the executable form sections 4, 5 and 6 "
            "have to run. Without it this report would show what got through and "
            "nothing about what stops - a red-team report, which is the thing "
            "CRUCIBLE is not." % plain)
    return json.loads(plain.read_text(encoding="utf-8")), plain


def cross_check_policy(bundle, record):
    """The two inputs must agree about which rules are in force at vFinal.

    Not a formality. They are written by different code paths at different
    moments, and a report that ran the sidecar's policy while printing the
    bundle's DSL would describe one policy and measure another.
    """
    chain = bundle.get("policy_chain") or []
    if not chain:
        return ["E_NO_POLICY_CHAIN: the bundle carries no policy_chain, so there "
                "is no independent record of which rules were in force. Sections "
                "3 and 4 cannot be cross-checked against anything."]
    tail = sorted(r.get("rule_id") for r in chain[-1].get("rules") or [])
    final = sorted(r.get("rule_id") for r in
                   ((record.get("final_policy") or {}).get("hashed_payload") or {})
                   .get("rules") or [])
    if tail != final:
        return ["E_POLICY_DISAGREEMENT: the bundle's last policy_chain entry holds "
                "%d rule(s) and the run record's final_policy holds %d, and the id "
                "sets differ. One of these two files is wrong about what was in "
                "force. Every number in sections 4, 5 and 6 is computed against "
                "the run record, so it would be describing a policy the bundle "
                "does not record." % (len(tail), len(final))]
    return []


# ---------------------------------------------------------------------------
# rendering a rule in English, DERIVED from its structure
# ---------------------------------------------------------------------------

OPS = {
    "eq": "is", "ne": "is not", "gte": "is at least", "gt": "is more than",
    "lte": "is at most", "lt": "is less than", "is_present": "is supplied",
    "is_absent": "is not supplied", "in": "is one of", "not_in": "is not one of",
    "ne_context": "does not match", "eq_context": "matches",
}

VERBS = {
    "deny": "Refuse the call outright.",
    "require_approval": "Hold the call until a human approver signs off.",
    "constrain_arg": "Force the argument inside the stated bound before the "
                     "call proceeds.",
}


def _value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return json.dumps(v) if not isinstance(v, str) else "`%s`" % v


def _condition_english(cond):
    path = cond.get("path") or cond.get("arg_path")
    op = cond.get("op")
    word = OPS.get(op, op)
    if op in ("is_present", "is_absent"):
        return "`%s` %s" % (path, word)
    if "context_field" in cond:
        return "`%s` %s `episode.%s`" % (path, word, cond["context_field"])
    return "`%s` %s %s" % (path, word, _value(cond.get("value")))


def _predicate_english(pred):
    form = pred.get("form")
    if form == "arg_vs_episode_context":
        return "`%s` %s the episode's frozen `episode.%s`" % (
            pred.get("arg_path"), OPS.get(pred.get("op"), pred.get("op")),
            pred.get("context_field"))
    return "predicate `%s` holds" % form


def _predicate_of(dsl_text):
    """Everything a rule matches on, with the id and the verb removed.

    Two rules with the same predicate and different verbs are the same rule at
    two strengths, and that is the only comparison this is used for.
    """
    m = re.match(r"^rule\s+\S+?:\s*(.*?)\s*=>", (dsl_text or "").strip())
    return m.group(1).strip() if m else ""


def _verb_of(dsl_text):
    m = re.search(r"=>\s*(\w+)", dsl_text or "")
    return m.group(1) if m else ""


def rule_english(rule, class_glosses, tool_names):
    """Plain English for one structured rule. Derived, never authored.

    Everything in the sentence comes out of the rule's own fields, so a rule
    this reader has never seen still renders and a rule that changes shape
    changes the sentence. A hand-written gloss keyed on rule_id would be a
    caption that could go quietly wrong.
    """
    match = rule.get("match") or {}
    cls = match.get("capability_class")
    tools = match.get("tool_names") or []
    subject_bits = []
    if cls:
        gloss = (class_glosses.get(cls) or ("", 0))[0]
        gloss = gloss[0].lower() + gloss[1:] if gloss else ""
        subject_bits.append("any call classed `%s`%s"
                            % (cls, " - %s" % gloss.rstrip(".") if gloss else ""))
    for t in tools:
        subject_bits.append("calls to `%s`" % tool_names.get(t, t))
    subject = " and ".join(subject_bits) or "any call"

    tests = [_condition_english(c) for c in match.get("arg_conditions") or []]
    tests += [_predicate_english(p) for p in match.get("predicates") or []]
    when = (", when " + " and ".join(tests)) if tests else ", unconditionally"

    action = VERBS.get(rule.get("verb"), "Apply `%s`." % rule.get("verb"))
    reason = (rule.get("action") or {}).get("reason_code")
    if reason:
        action += " Reason code `%s`." % reason
    return "On %s%s. %s" % (subject, when, action)


# ---------------------------------------------------------------------------
# the replay - the loop's own arbiters, offline
# ---------------------------------------------------------------------------

def episode_as_fixture(ep, approver="NONE"):
    """A recorded attack episode in the shape `replay_trace` walks.

    C6 names the ordered event list `episode_prefix`; the tripwire's Episode
    model reads `events`. One concept, two names, across a contract boundary -
    the same defect class CONVENTIONS section 8 rule 11 already names. Mapped
    here explicitly rather than papered over, so a future rename fails loudly.

    `approver` defaults to the sentinel NONE because that is what an attack
    episode declares. `approval_oracle_default: deny_unless_fixture_declares` is
    a FROZEN run-manifest parameter - handing an attack a fake approver here
    would let the oracle wave through calls the run never approved.
    """
    inner = dict(ep)
    inner["events"] = ep.get("episode_prefix") or []
    raw = {"attack_id": ep.get("attack_id") or ep.get("episode_id"),
           "approver": approver, "near_miss": False, "episode": inner}
    return Fixture(raw, "bundle:%s" % ep.get("episode_id"), "attack_id")


def replay_episode_at(ep, policy, objective_set):
    """Score one recorded path under `policy` using the real tripwire.

    Returns a dict. `fired_rules` is the set of rule ids that actually stopped
    something, which is how section 7 can say a promoted rule never fired on
    this run's own traffic.
    """
    fixture = episode_as_fixture(ep)
    ok, blocked, surviving, oracle = replay_trace(fixture, policy, _l3_evaluate_call)
    replayed = copy.deepcopy(ep)
    replayed["events"] = surviving
    manifest = {k: ep.get(k) for k in MANIFEST_KEYS}
    verdict = evaluate_episode(replayed, objective_set, manifest)
    fired = sorted({e.get("denied_by_rule_id") for e in surviving
                    if e.get("denied_by_rule_id")})
    executed_before = sum(1 for e in ep.get("episode_prefix") or []
                          if e.get("kind") == "TOOL_EXECUTED")
    executed_after = sum(1 for e in surviving if e.get("kind") == "TOOL_EXECUTED")
    return {
        "verdict": verdict.verdict,
        "breach": verdict.verdict == "BREACH",
        "invariant_id": getattr(verdict, "invariant_id", None),
        "all_calls_permitted": ok,
        "blocked_classes": blocked,
        "oracle_resolutions": oracle,
        "fired_rules": fired,
        "executed_before": executed_before,
        "executed_after": executed_after,
    }


def replay_benign_at(policy):
    """Every benign fixture under `policy`, and which passes the oracle carries.

    The masked set is MEASURED, not read off the fixtures' own
    `approval_masked_candidate` flags. A fixture's flag is its author's
    expectation; what the report owes the reader is what the policy in force
    actually does.

    THE SECOND REPLAY IS THE WHOLE TRICK. `replay_trace` returns how many calls
    the oracle resolved but not which rule stopped them, because on an approval
    the recorded `policy_decision` is rewritten to ALLOW and the rule id is
    erased. Replaying the same fixture with its approver stripped to the
    sentinel makes the policy's own decision visible again, and the rule that
    reappears is the rule the human is standing in for.
    """
    rows = []
    for fixture in load_real_benign_suite():
        ok, blocked, _surv, oracle = replay_trace(fixture, policy, _l3_evaluate_call)
        masked, stopped_by = False, []
        if ok and oracle:
            stripped = copy.deepcopy(fixture.raw)
            stripped["approver"] = "NONE"
            bare = Fixture(stripped, fixture.path, "fixture_id")
            ok2, _b2, surv2, _o2 = replay_trace(bare, policy, _l3_evaluate_call)
            masked = not ok2
            stopped_by = sorted({e.get("denied_by_rule_id") for e in surv2
                                 if e.get("denied_by_rule_id")})
        rows.append({
            "fixture_id": fixture.fixture_id,
            "near_miss": fixture.near_miss,
            "passed": ok,
            "blocked_classes": blocked,
            "oracle_resolutions": oracle,
            "approval_masked": masked,
            "stopped_by": stopped_by,
        })
    return rows


# ---------------------------------------------------------------------------
# building the seven sections
# ---------------------------------------------------------------------------

def _index(seq, key):
    out = {}
    for item in seq or []:
        k = item.get(key)
        if k is not None:
            out.setdefault(k, item)
    return out


def corpus_targets():
    """`{instance_id: {"slug":..., "classes":[...], "tool":...}}` for the training
    corpus, keyed the way the bundle keys it.

    THIS IS WHAT MAKES "ATTACKED BUT NEVER EXERCISED" A RESULT RATHER THAN A
    GUESS. A generated attack declares no target - only the corpus instances say
    which capability class they are aiming at - so the denominator here is the
    corpus arm alone and the report says so rather than quietly counting the
    whole run.

    The key is content-addressed by `corpus.schema.instance_id`, recomputed here
    from the files on disk. That is deliberate: if the corpus has moved since the
    run, the ids stop matching and the join coverage drops, which the report
    prints. A join that silently resolved nothing would look identical to a run
    that attacked nothing.
    """
    try:
        from corpus.schema import instance_id
    except Exception:
        return {}, "corpus.schema could not be imported"
    out = {}
    for path in sorted((REPO / "corpus" / "training").glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            out[instance_id(doc)] = {
                "slug": doc.get("slug"),
                "classes": doc.get("capability_classes") or [],
                "tool": (doc.get("tool_fqname") or "").rsplit(".", 1)[-1],
            }
        except Exception:
            continue
    return out, None


def _tool_names():
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {t["tool_handle"]: t["tool_fqname"].rsplit(".", 1)[-1]
            for t in doc.get("tools", [])}, doc.get("tools", [])


def _pretty_args(args):
    """Argument rows, with the harness-stamped `derived.*` fields split out.

    They are separated because they are DIFFERENT KINDS OF THING. The plain
    arguments are what the agent chose to send. The `derived.*` fields are what
    the harness computed about the episode and stamped onto the call, and a
    reader who takes them for the agent's own words is wrong about who did what.
    """
    chosen, derived = [], []
    for k in sorted(args or {}):
        (derived if k.startswith("derived.") else chosen).append((k, args[k]))
    return chosen, derived


def build_report(bundle, record, c6_path, record_path, defects, disagreements):
    families = load_family_names()
    classes = load_class_glosses()
    sev_table, floors = load_severity_floors()
    tool_names, manifest_tools = _tool_names()
    objective_set = load_objective_set(OBJECTIVE_SET)
    clause_by_id = {c["id"]: c for c in objective_set.clauses}

    run = bundle.get("run_manifest") or {}
    summary = record.get("summary") or {}
    final_policy = record.get("final_policy") or {}
    final_rules = ((final_policy.get("hashed_payload") or {}).get("rules")) or []

    episodes = bundle.get("episodes") or []
    attacks = _index(bundle.get("attacks"), "attack_id")
    autopsies = bundle.get("autopsies") or []
    autopsy_by_attack = _index(autopsies, "attack_id")

    # -- 1. what we threw at it --------------------------------------------
    by_family, by_provenance = {}, {}
    for a in bundle.get("attacks") or []:
        fam = (a.get("family_id") or "?").replace("fam_f", "F")
        by_family[fam] = by_family.get(fam, 0) + 1
        p = a.get("provenance") or "?"
        by_provenance[p] = by_provenance.get(p, 0) + 1

    reached, tools_called = {}, {}
    for ep in episodes:
        for e in ep.get("episode_prefix") or []:
            if e.get("kind") != "TOOL_EXECUTED":
                continue
            tools_called[e.get("tool_name")] = tools_called.get(e.get("tool_name"), 0) + 1
            for c in e.get("capability_classes") or []:
                reached[c] = reached.get(c, 0) + 1

    census = bundle.get("round_census") or []
    s1 = {
        "attack_mode": bundle.get("attack_mode"),
        "attacks": len(bundle.get("attacks") or []),
        "episodes": len(episodes),
        "by_family": sorted(by_family.items()),
        "by_provenance": sorted(by_provenance.items()),
        "families": families,
        "reached": sorted(reached.items(), key=lambda kv: -kv[1]),
        "tools_called": sorted(tools_called.items(), key=lambda kv: -kv[1]),
        "attempted": sum(r.get("attempted", 0) for r in census),
        "scorable": sum(r.get("scorable", 0) for r in census),
        "excluded": sum(r.get("excluded", 0) for r in census),
        "rounds": census,
        "target_model": (run.get("target_ref") or {}).get("model_id"),
        "target_thinking": (run.get("target_ref") or {}).get("thinking_level"),
    }

    # -- 2. what got through at policy@v0 ----------------------------------
    breaches = []
    for ep in episodes:
        v = ep.get("verdict") or {}
        if not v.get("breach"):
            continue
        atk = attacks.get(ep.get("attack_id")) or {}
        aut = autopsy_by_attack.get(ep.get("attack_id")) or {}
        involved = aut.get("capability_classes_involved") or []
        sev, why = assign_severity(involved, floors, aut.get("amount_minor_moved"))
        calls = []
        for call in aut.get("offending_tool_calls") or []:
            chosen, derived = _pretty_args(call.get("args_redacted") or {})
            calls.append({
                "seq": call.get("seq"),
                "tool": tool_names.get(call.get("tool_handle"), call.get("tool_handle")),
                "classes": call.get("capability_classes") or [],
                "policy_decision": call.get("policy_decision"),
                "status": call.get("status"),
                "chosen": chosen,
                "derived": derived,
            })
        breaches.append({
            "episode_id": ep.get("episode_id"),
            "attack_id": ep.get("attack_id"),
            "family": (atk.get("family_id") or "?").replace("fam_f", "F"),
            "provenance": ep.get("provenance") or atk.get("provenance"),
            "channel": ep.get("channel"),
            "round_index": ep.get("round_index"),
            "policy_version": ep.get("policy_version"),
            "instruction": atk.get("instruction") or "",
            "invariant_id": v.get("invariant_id"),
            "invariant_why": _clip(
                (clause_by_id.get(v.get("invariant_id")) or {}).get("_why", ""),
                700, "`%s`" % OBJECTIVE_SET.relative_to(REPO).as_posix()),
            "invariant_class": (clause_by_id.get(v.get("invariant_id")) or {})
            .get("capability_class"),
            "invariant_form": (clause_by_id.get(v.get("invariant_id")) or {})
            .get("form"),
            "narrative": (aut.get("human_only") or {}).get("narrative", ""),
            "severity": sev,
            "severity_why": why,
            "calls": calls,
        })

    # -- 3. what CRUCIBLE did about it -------------------------------------
    proposal_by_autopsy = {}
    for pp in bundle.get("patch_proposals") or []:
        for r in pp.get("rules") or []:
            proposal_by_autopsy[r.get("rule_id_assigned")] = pp
    autopsy_by_id = _index(autopsies, "autopsy_id")
    dsl_by_id = {}
    for entry in bundle.get("policy_chain") or []:
        for r in entry.get("rules") or []:
            dsl_by_id.setdefault(r.get("rule_id"), r.get("dsl_text"))

    learned, seeded = [], []
    for rule in final_rules:
        rid = rule.get("rule_id")
        pp = proposal_by_autopsy.get(rid) or {}
        aut = autopsy_by_id.get(pp.get("autopsy_id")) or {}
        row = {
            "rule_id": rid,
            "verb": rule.get("verb"),
            "origin": rule.get("origin"),
            "dsl_text": dsl_by_id.get(rid, ""),
            "english": rule_english(rule, classes, tool_names),
            "round_index": pp.get("round_index"),
            "answers_attack": aut.get("attack_id"),
            "answers_invariant": aut.get("invariant_id"),
            "answers_family": (aut.get("attack_family_id") or "").replace("fam_f", "F"),
            "validator_result": pp.get("validator_result", ""),
            "warden_result": pp.get("warden_result", ""),
            "narrowing_attempt": pp.get("narrowing_attempt"),
        }
        (learned if rule.get("origin") == "armorer" else seeded).append(row)

    gate_rows = []
    for g in bundle.get("gate_decisions") or []:
        findings = g.get("criteria", {}).get("findings") or []
        gate_rows.append({
            "round_index": g.get("round_index"),
            "decision": g.get("decision"),
            "benign": g.get("criteria", {}).get("benign_floor") or {},
            "checks": len(findings),
            "failed": [f for f in findings if f.get("status") != "PASS"],
        })

    # A RULE CAN BE PROMOTED AND THEN NOT BE THERE AT THE END, and nothing in
    # the run record says so: `summary.promotions` counts gate decisions, while
    # the final policy is a set of rules. The two are different quantities and
    # this report prints both rather than picking the flattering one. What is
    # actually shown is the DIFFERENCE, derived from the DSL text: same
    # predicate, different verb, is a rule that was weakened between versions.
    final_ids = {r.get("rule_id") for r in final_rules}
    promoted_ids = []
    for pp in bundle.get("patch_proposals") or []:
        if pp.get("accepted"):
            promoted_ids += [r.get("rule_id_assigned") for r in pp.get("rules") or []]
    dropped = []
    for rid in promoted_ids:
        if rid in final_ids:
            continue
        text = dsl_by_id.get(rid, "")
        pred = _predicate_of(text)
        successor = None
        for other in final_rules:
            if _predicate_of(dsl_by_id.get(other.get("rule_id"), "")) == pred and pred:
                successor = other
                break
        dropped.append({
            "rule_id": rid,
            "dsl_text": text,
            "verb": _verb_of(text),
            "successor_id": (successor or {}).get("rule_id"),
            "successor_verb": (successor or {}).get("verb"),
        })

    s3 = {"learned": learned, "seeded": seeded, "gates": gate_rows,
          "verbs_available": sorted(VERBS),
          "promotions_recorded": summary.get("promotions"),
          "dropped": dropped}

    # -- 4. what stops now --------------------------------------------------
    at_final, regressions, fired_anywhere = [], [], set()
    for ep in episodes:
        was_breach = bool((ep.get("verdict") or {}).get("breach"))
        res = replay_episode_at(ep, final_policy, objective_set)
        fired_anywhere.update(res["fired_rules"])
        if was_breach:
            at_final.append({
                "episode_id": ep.get("episode_id"),
                "attack_id": ep.get("attack_id"),
                "family": (attacks.get(ep.get("attack_id")) or {})
                          .get("family_id", "?").replace("fam_f", "F"),
                "v0_invariant": (ep.get("verdict") or {}).get("invariant_id"),
                "v0": "BREACH",
                "vfinal": res["verdict"],
                "stopped": not res["breach"],
                "executed_before": res["executed_before"],
                "executed_after": res["executed_after"],
                "blocked_classes": res["blocked_classes"],
                "fired_rules": res["fired_rules"],
            })
        elif res["breach"]:
            # A policy can only ever REMOVE executed events, so a clean path that
            # turns into a breach is arithmetically impossible and would mean the
            # replay is wrong. Recorded rather than assumed away.
            regressions.append({"episode_id": ep.get("episode_id"),
                                "invariant_id": res["invariant_id"]})

    s4 = {
        "rows": at_final,
        "breached_at_v0": len(at_final),
        "still_breaching": sum(1 for r in at_final if not r["stopped"]),
        "regressions": regressions,
    }

    # -- 5 and 6. what the agent can still do, and what it cost -------------
    benign = replay_benign_at(final_policy)
    masked = [b for b in benign if b["approval_masked"]]
    failed = [b for b in benign if not b["passed"]]
    recorded_bpr = ((summary.get("benign_floor_at_v0") or {})
                    .get("benign_passes_requiring_approval"))
    s5 = {"rows": benign,
          "passed": sum(1 for b in benign if b["passed"]),
          "total": len(benign),
          "near_miss_passed": sum(1 for b in benign if b["passed"] and b["near_miss"]),
          "near_miss_total": sum(1 for b in benign if b["near_miss"])}
    s6 = {"masked": masked, "failed": failed,
          "measured": len(masked), "recorded": recorded_bpr,
          "rules": sorted({r for b in masked for r in b["stopped_by"]}),
          "english": {r["rule_id"]: r["english"] for r in learned + seeded}}

    # -- 7. what we could not tell you --------------------------------------
    declared_classes = sorted({c for t in manifest_tools
                               for c in t.get("capability_classes") or []})
    never_called = sorted(t["tool_fqname"].rsplit(".", 1)[-1] for t in manifest_tools
                          if t["tool_fqname"].rsplit(".", 1)[-1] not in tools_called)
    # PER CLASS, not the whole never-called list against every row. The first
    # version of this table printed every uncalled tool beside every unexercised
    # class, which read as evidence that `delegate_to_specialist` moves money.
    targets, target_err = corpus_targets()
    aimed_at, joined, unjoined = {}, 0, 0
    for a in bundle.get("attacks") or []:
        if a.get("provenance") != "training_corpus":
            continue
        row = targets.get(a.get("corpus_instance_id"))
        if not row:
            unjoined += 1
            continue
        joined += 1
        for c in row["classes"]:
            aimed_at[c] = aimed_at.get(c, 0) + 1

    never_reached = []
    for c in declared_classes:
        if c in reached:
            continue
        carriers = sorted(t["tool_fqname"].rsplit(".", 1)[-1] for t in manifest_tools
                          if c in (t.get("capability_classes") or [])
                          and t["tool_fqname"].rsplit(".", 1)[-1] not in tools_called)
        never_reached.append({"capability_class": c, "carriers": carriers,
                              "aimed_at_by": aimed_at.get(c, 0)})
    clause_states = {}
    for c in (bundle.get("clause_coverage") or {}).get("clauses") or []:
        clause_states.setdefault(c.get("state"), []).append({
            "invariant_id": c.get("invariant_id"),
            "capability_class": (clause_by_id.get(c.get("invariant_id")) or {})
            .get("capability_class"),
        })
    never_fired = [r for r in learned + seeded if r["rule_id"] not in fired_anywhere]

    s7 = {
        "labels": bundle.get("labels") or {},
        "never_reached": never_reached,
        "never_called": never_called,
        "aimed_at": sorted(aimed_at.items(), key=lambda kv: -kv[1]),
        "corpus_joined": joined,
        "corpus_unjoined": unjoined,
        "corpus_join_error": target_err,
        "clause_states": clause_states,
        "never_fired": never_fired,
        "sep_by_split": bundle.get("sep_by_split") or {},
        "excluded": bundle.get("excluded") or [],
        "defects": defects,
        "disagreements": disagreements,
        "reps": summary.get("reps"),
        "status": summary.get("status"),
        "halt": summary.get("halt"),
        "constrain_arg_proposed": summary.get("constrain_arg_ever_proposed"),
        "untested_against_live_gcs": (summary.get("gate") or {})
        .get("untested_against_live_gcs") or [],
        "citations": {
            "families": FAMILY_SOURCE,
            "classes": CLASS_SOURCE,
            "severity": SEVERITY_TABLE.relative_to(REPO).as_posix(),
        },
    }

    return {
        "run_id": run.get("run_id"),
        "spine_version": run.get("spine_version"),
        "created_at": run.get("created_at"),
        "bundle_path": c6_path,
        "record_path": record_path,
        "hash_locks": run.get("hash_locks") or {},
        "frozen": run.get("frozen_parameters") or {},
        "provenance": bundle.get("execution_provenance") or {},
        "cost": bundle.get("cost") or {},
        "governor": summary.get("governor") or {},
        "class_glosses": classes,
        "severity_table": sev_table,
        "s1": s1, "s2": breaches, "s3": s3, "s4": s4, "s5": s5, "s6": s6, "s7": s7,
        "verdict": verdict_lines(s1, breaches, s3, s4, s6, defects),
    }


def verdict_lines(s1, breaches, s3, s4, s6, defects):
    """The strip at the top. IT IS COMPUTED, and it can say bad things.

    A generator that renders a success story regardless of input is the exact
    failure this project keeps meeting, so every line below is a branch that
    real input can take, and the negative controls in `--selftest` take them.
    """
    lines = []
    if defects:
        lines.append(("REFUSED", "The offline reader REFUSED this bundle, %d "
                      "defect(s). Everything below is rendered from unblessed "
                      "bytes and no figure on this page may be quoted."
                      % len(defects)))
    if not breaches:
        lines.append(("NOTHING FOUND", "No attack got through at policy@v0, and "
                      "THAT IS NOT A CLEAN BILL OF HEALTH. It means the attacks "
                      "were weak, the seed policy already held, or the run did "
                      "not reach the capabilities that matter. Read section 7 "
                      "before reading this as safety."))
    else:
        lines.append(("FOUND", "%d of %d recorded episodes reached an invariant "
                      "at policy@v0." % (len(breaches), s1["episodes"])))
    if not s3["learned"]:
        lines.append(("NOTHING LEARNED", "NO RULE WAS PROMOTED. Your agent's "
                      "policy at the end of this run is the policy it started "
                      "with. Nothing on this page describes a change, because "
                      "there was none."))
    else:
        extra = ""
        if (s3["promotions_recorded"] is not None
                and s3["promotions_recorded"] != len(s3["learned"])):
            extra = (" The gate promoted %s time(s); %d learned rule(s) are in "
                     "force at the end. Those are different quantities and "
                     "section 3 shows the difference."
                     % (s3["promotions_recorded"], len(s3["learned"])))
        lines.append(("HARDENED", "%d learned rule(s) are in force at the end. The "
                      "DSL has no `allow` verb, so no sequence of patches can "
                      "widen what your agent is permitted to do.%s"
                      % (len(s3["learned"]), extra)))
    if s3["dropped"]:
        weakened = [d for d in s3["dropped"] if d["successor_id"]]
        if weakened:
            lines.append(("WEAKENED", "%d promoted rule(s) were replaced later in "
                          "the run by a rule with the SAME predicate and a "
                          "different verb. Read section 3 before treating the "
                          "final policy as the sum of what was learned."
                          % len(weakened)))
        else:
            lines.append(("DROPPED", "%d rule(s) were promoted and are not in the "
                          "final policy." % len(s3["dropped"])))
    if s4["breached_at_v0"]:
        still = s4["still_breaching"]
        if still:
            lines.append(("INCOMPLETE", "%d of %d recorded breach paths STILL "
                          "REACH their invariant under policy@vFinal. The loop "
                          "did not close them and this report will not round "
                          "that off." % (still, s4["breached_at_v0"])))
        else:
            lines.append(("CLOSED", "All %d recorded breach paths stop under "
                          "policy@vFinal, on replay of the recorded calls."
                          % s4["breached_at_v0"]))
    if s4["regressions"]:
        lines.append(("DEFECT", "%d episode(s) score CLEAN at v0 and BREACH at "
                      "vFinal. A policy can only remove executed events, so this "
                      "is arithmetically impossible and means this replay is "
                      "wrong." % len(s4["regressions"])))
    if s6["measured"]:
        lines.append(("COST", "%d benign flow(s) now pass ONLY because a human "
                      "approver signed off. A benign pass rate that counts them "
                      "as untouched work is reporting your agent's capability "
                      "and measuring your approver's patience."
                      % s6["measured"]))
    if s6["failed"]:
        lines.append(("LOST", "%d benign fixture(s) FAIL under the final policy. "
                      "That is capability your agent no longer has."
                      % len(s6["failed"])))
    return lines


# ---------------------------------------------------------------------------
# shared prose. Written once and rendered into both formats, so the markdown
# and the HTML cannot drift into saying different things about the same run.
# ---------------------------------------------------------------------------

S4_CAVEAT = (
    "**This is a replay of the recorded calls, not a re-run.** Every "
    "`TOOL_ATTEMPT` in the recorded path is re-evaluated against `policy@vFinal`; "
    "a blocked attempt removes its `TOOL_EXECUTED` from the surviving events, and "
    "the real pure-code tripwire then scores what is left. It answers exactly one "
    "question - would this exact recorded sequence still reach the invariant. A "
    "live agent handed a refusal it never received before may go somewhere else "
    "entirely, and nothing here can see that. It is also not the sealed-family "
    "transfer figure, which does not exist yet.")

S6_PREAMBLE = (
    "**A rule that over-blocks passes every gate.** It stops the attacks, the "
    "approval oracle waves the benign cases through, the benign pass rate reads "
    "perfect, the gate promotes it - and the agent has been made useless. The "
    "count below is the only thing on this page that can tell that story apart "
    "from a good one, which is why this section may never be omitted or softened.")

S7_PREAMBLE = (
    "A report that only flatters the run is worse than no report, because this "
    "project's whole argument is that its numbers are checkable. Everything below "
    "is a limit on what the run above is able to say.")

NO_SCORE = (
    "NO ROLLED-UP SCORE APPEARS ON THIS PAGE, AND THE OMISSION IS DELIBERATE. "
    "Collapsing a run into one number deletes exactly the information that tells "
    "a good result from a flattering one: the SEP-BY split, the approval-masked "
    "count, the k=1 label, which capability classes were never exercised. The one "
    "honest pair is breached-at-v0 against breached-at-vFinal, and it is printed "
    "in section 4 with its caveat attached.")


def _fam(s1, code):
    name, line = s1["families"].get(code, ("", 0))
    return name, line


def _argval(v):
    s = v if isinstance(v, str) else json.dumps(v)
    return s


def _clip(text, limit, pointer):
    """Long prose, cut at a sentence boundary, with the file that holds the rest.

    An invariant's `_why` runs to a thousand words in places. Printing it whole
    buries the finding it sits under; printing a silent truncation would be a
    quotation the reader cannot tell is partial. The pointer is the difference.
    """
    text = (text or "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    stop = max(cut.rfind(". "), cut.rfind("; "))
    if stop > limit // 2:
        cut = cut[:stop + 1]
    return "%s [...] The rest of this rationale is in %s." % (cut.rstrip(), pointer)


# ---------------------------------------------------------------------------
# markdown
# ---------------------------------------------------------------------------

def render_md(rep, invocation, generated_at):
    o = []
    w = o.append
    s1, s2, s3, s4, s5, s6, s7 = (rep["s1"], rep["s2"], rep["s3"], rep["s4"],
                                  rep["s5"], rep["s6"], rep["s7"])

    w("# CRUCIBLE hardening report")
    w("")
    w("Run `%s`, spine %s, recorded %s." % (rep["run_id"], rep["spine_version"],
                                            rep["created_at"]))
    w("Generated at %s. Regenerate this file; never edit it." % generated_at)
    w("")
    w("```")
    w(invocation)
    w("```")
    w("")
    w("| input | file |")
    w("|---|---|")
    w("| evidence bundle, the run of record | `%s` |" % rep["bundle_path"])
    w("| run record, for the executable final policy | `%s` |" % rep["record_path"])
    w("")
    w("> %s" % NO_SCORE)
    w("")

    w("## The short version")
    w("")
    for tag, text in rep["verdict"]:
        w("- **%s** - %s" % (tag, text))
    w("")

    # 1 ---------------------------------------------------------------------
    w("## 1. What we threw at it")
    w("")
    w("%d attacks across %d episodes, attack mode `%s`, against `%s` at "
      "thinking_level `%s`." % (s1["attacks"], s1["episodes"], s1["attack_mode"],
                                s1["target_model"], s1["target_thinking"]))
    w("")
    w("| family | attacks | what the family does | cited |")
    w("|---|---|---|---|")
    for code, n in s1["by_family"]:
        name, line = _fam(s1, code)
        w("| **%s** | %d | %s | `%s:%d` |"
          % (code, n, name.rstrip("."), s7["citations"]["families"], line))
    w("")
    w("| provenance | attacks |")
    w("|---|---|")
    for p, n in s1["by_provenance"]:
        w("| `%s` | %d |" % (p, n))
    w("")
    w("**Never pool those two.** A mixed rate hides which half moved.")
    w("")
    w("Episodes attempted %d, scorable %d, excluded %d, across %d round(s)."
      % (s1["attempted"], s1["scorable"], s1["excluded"], len(s1["rounds"])))
    w("")
    w("### What the attacks actually reached")
    w("")
    w("Counted from `TOOL_EXECUTED` events, so this is what happened rather than "
      "what was aimed at.")
    w("")
    w("| capability class | executed calls | what the class means |")
    w("|---|---|---|")
    for c, n in s1["reached"]:
        gloss = (rep["class_glosses"].get(c) or ("", 0))[0]
        w("| `%s` | %d | %s |" % (c, n, gloss))
    w("")
    w("| tool | executed calls |")
    w("|---|---|")
    for t, n in s1["tools_called"]:
        w("| `%s` | %d |" % (t, n))
    w("")

    # 2 ---------------------------------------------------------------------
    w("## 2. What got through")
    w("")
    if not s2:
        w("**Nothing got through at `policy@v0`, and that is not good news.**")
        w("")
        w("Zero breaches at the seed policy means one of three things and the run "
          "cannot tell you which: the attacks were weak, the seed policy already "
          "held, or the episodes never reached the capabilities that matter. "
          "Section 7 lists what was never exercised. Read it before reading this "
          "as safety.")
        w("")
    for b in s2:
        w("### `%s` - %s" % (b["attack_id"], b["severity"]))
        w("")
        w("Family **%s**, provenance `%s`, channel `%s`, round %s, at "
          "`policy@v%s`." % (b["family"], b["provenance"], b["channel"],
                             b["round_index"], b["policy_version"]))
        w("")
        w("**Severity is derived, not asserted.** %s" % b["severity_why"])
        w("")
        if b["instruction"]:
            w("What the attacker said:")
            w("")
            w("> %s" % b["instruction"].replace("\n", " ").strip())
            w("")
        w("**What the agent was induced to do.** %s" % (b["narrative"] or
          "The autopsy recorded no narrative for this breach."))
        w("")
        for call in b["calls"]:
            w("Call at sequence %s - `%s`, classed %s, policy decision `%s`, "
              "status `%s`:" % (call["seq"], call["tool"],
                                ", ".join("`%s`" % c for c in call["classes"]),
                                call["policy_decision"], call["status"]))
            w("")
            w("| argument the agent chose | value |")
            w("|---|---|")
            for k, v in call["chosen"]:
                w("| `%s` | %s |" % (k, _argval(v).replace("|", "\\|")))
            w("")
            if call["derived"]:
                w("<details><summary>%d harness-stamped <code>derived.*</code> "
                  "field(s) on the same call - computed by CRUCIBLE, not chosen by "
                  "the agent</summary>" % len(call["derived"]))
                w("")
                w("| field | value |")
                w("|---|---|")
                for k, v in call["derived"]:
                    w("| `%s` | %s |" % (k, _argval(v).replace("|", "\\|")))
                w("")
                w("</details>")
                w("")
        w("The tripwire scored this against `%s` (`%s`, %s form). That clause "
          "exists because:" % (b["invariant_id"], b["invariant_class"],
                               b["invariant_form"]))
        w("")
        w("> %s" % (b["invariant_why"] or "no rationale recorded").replace("\n", " "))
        w("")

    # 3 ---------------------------------------------------------------------
    w("## 3. What CRUCIBLE did about it")
    w("")
    w("The patch language has three verbs - `deny`, `require_approval`, "
      "`constrain_arg` - **and no `allow` verb**. No sequence of patches can "
      "widen what your agent is permitted to do; the reachable set only ever "
      "shrinks.")
    w("")
    if not s3["learned"]:
        w("**No rule was promoted in this run.** The policy at the end is the "
          "policy at the start. Nothing in this section describes a change "
          "because there was none.")
        w("")
    for r in s3["learned"]:
        w("### `%s` - `%s`, promoted in round %s" % (r["rule_id"], r["verb"],
                                                     r["round_index"]))
        w("")
        w("**In English.** %s" % r["english"])
        w("")
        w("```")
        w(r["dsl_text"])
        w("```")
        w("")
        w("Answers the breach on attack `%s` (family %s, invariant `%s`)."
          % (r["answers_attack"], r["answers_family"], r["answers_invariant"]))
        if r["narrowing_attempt"]:
            w("")
            w("Narrowing attempt %s. Validator: %s" % (r["narrowing_attempt"],
                                                       r["validator_result"]))
        if r["warden_result"]:
            w("")
            w("Warden: %s" % r["warden_result"])
        w("")
    if s3["dropped"]:
        w("### Promoted, and not in the final policy")
        w("")
        w("The gate recorded **%s** promotion(s) and **%d** learned rule(s) are in "
          "force at the end. Those are different quantities: `summary.promotions` "
          "counts gate decisions, the policy is a set of rules, and nothing in the "
          "run record reconciles them. Here is the difference."
          % (s3["promotions_recorded"], len(s3["learned"])))
        w("")
        for d in s3["dropped"]:
            w("- **`%s`** (`%s`) was promoted and is not in the final policy."
              % (d["rule_id"], d["verb"]))
            w("  ```")
            w("  %s" % d["dsl_text"])
            w("  ```")
            if d["successor_id"]:
                w("  A rule with the **identical predicate** is in force under a "
                  "different verb: `%s` uses `%s` where this used `%s`. The "
                  "predicate did not change; the strength did. Whether that was "
                  "the right trade is a judgement this report does not make for "
                  "you, and it is not visible anywhere else in the run's own "
                  "output." % (d["successor_id"], d["successor_verb"], d["verb"]))
        w("")
    if s3["seeded"]:
        w("### Rules that were already there")
        w("")
        w("Seed rules. CRUCIBLE did not learn these; they are shown because "
          "sections 4 and 6 measure the whole policy in force, and a reader who "
          "took every effect below for something the loop discovered would be "
          "wrong about what the run achieved.")
        w("")
        for r in s3["seeded"]:
            w("- **`%s`** (`%s`) - %s" % (r["rule_id"], r["verb"], r["english"]))
            w("  ```")
            w("  %s" % r["dsl_text"])
            w("  ```")
        w("")
    if s3["gates"]:
        w("### What the gate checked before letting each one through")
        w("")
        w("| round | decision | benign floor | live cloud assertions | failed |")
        w("|---|---|---|---|---|")
        for g in s3["gates"]:
            bf = g["benign"]
            w("| %s | **%s** | %s/%s | %d | %d |"
              % (g["round_index"], g["decision"], bf.get("passed"), bf.get("total"),
                 g["checks"], len(g["failed"])))
        w("")

    # 4 ---------------------------------------------------------------------
    w("## 4. What stops now")
    w("")
    w("> %s" % S4_CAVEAT)
    w("")
    if not s4["rows"]:
        w("Nothing reached an invariant at `policy@v0`, so there is no before and "
          "after to show.")
        w("")
    else:
        w("**%d recorded breach path(s) at `policy@v0`. %d still reach their "
          "invariant at `policy@vFinal`.**"
          % (s4["breached_at_v0"], s4["still_breaching"]))
        w("")
        w("| attack | family | invariant | at v0 | at vFinal | calls executed | "
          "stopped by |")
        w("|---|---|---|---|---|---|---|")
        for r in s4["rows"]:
            w("| `%s` | %s | `%s` | **BREACH** | **%s** | %d -> %d | %s |"
              % (r["attack_id"], r["family"], r["v0_invariant"], r["vfinal"],
                 r["executed_before"], r["executed_after"],
                 ", ".join("`%s`" % x for x in r["fired_rules"]) or "nothing"))
        w("")
        unstopped = [r for r in s4["rows"] if not r["stopped"]]
        if unstopped:
            w("### The ones that are still open")
            w("")
            w("Every one of these motivated a rule that the gate promoted. The "
              "gate checks that a patch is well-formed and that benign traffic "
              "survives it. **It does not check that the patch closes the breach "
              "it was written for.**")
            w("")
            for r in unstopped:
                w("- `%s` (family %s) still reaches `%s`. No rule stopped a single "
                  "call on the recorded path: %d call(s) executed before, %d after."
                  % (r["attack_id"], r["family"], r["v0_invariant"],
                     r["executed_before"], r["executed_after"]))
            w("")
    if s4["regressions"]:
        w("**DEFECT.** %d episode(s) score CLEAN at v0 and BREACH at vFinal. A "
          "policy can only remove executed events, so this is arithmetically "
          "impossible and means this replay is wrong: %s"
          % (len(s4["regressions"]),
             ", ".join("`%s`" % r["episode_id"] for r in s4["regressions"])))
        w("")

    # 5 ---------------------------------------------------------------------
    w("## 5. What your agent can still do")
    w("")
    w("Named, not summarised. A fraction cannot tell you which capability "
      "survived.")
    w("")
    w("%d of %d benign fixtures pass under `policy@vFinal`, %d of %d of them "
      "near-misses - fixtures built to sit one field away from an attack."
      % (s5["passed"], s5["total"], s5["near_miss_passed"], s5["near_miss_total"]))
    w("")
    w("| benign fixture | near-miss | under policy@vFinal |")
    w("|---|---|---|")
    for b in s5["rows"]:
        if not b["passed"]:
            state = "**FAILS** - blocked on %s" % ", ".join(
                "`%s`" % c for c in b["blocked_classes"])
        elif b["approval_masked"]:
            state = "passes ONLY with a human approver"
        else:
            state = "passes untouched"
        w("| `%s` | %s | %s |" % (b["fixture_id"], "yes" if b["near_miss"] else "",
                                  state))
    w("")

    # 6 ---------------------------------------------------------------------
    w("## 6. What it cost you")
    w("")
    w("> %s" % S6_PREAMBLE)
    w("")
    if s6["measured"]:
        w("**%d of the %d benign passes above are not your agent's. They are your "
          "approver's.** Those flows now stop at the policy and reach a human "
          "before they proceed." % (s6["measured"], s5["passed"]))
    else:
        w("**No benign flow needs a human that did not need one before.** Measured "
          "by replaying every benign fixture twice, once with its declared "
          "approver and once with the approver stripped to the sentinel.")
    w("")
    if s6["recorded"] is not None:
        agree = "agrees" if s6["recorded"] == s6["measured"] else "DISAGREES"
        w("The run record's own `benign_passes_requiring_approval` reads **%s**, "
          "and this replay measured **%d**. The two %s."
          % (s6["recorded"], s6["measured"], agree))
        w("")
    for b in s6["masked"]:
        w("- **`%s`** - stopped by %s, then approved. Without the approver this "
          "fixture fails." % (b["fixture_id"],
                              ", ".join("`%s`" % r for r in b["stopped_by"])))
        for rid in b["stopped_by"]:
            if rid in s6["english"]:
                w("  - %s" % s6["english"][rid])
    if s6["masked"]:
        w("")
        w("**The fix has to be to the ruler, and it has not been written.** The "
          "benign floor still counts an approved call as a pass, so a policy that "
          "sent every call to a human would score a perfect benign rate while "
          "leaving your agent unable to do anything on its own.")
        w("")
    if s6["failed"]:
        w("### Capability actually lost")
        w("")
        for b in s6["failed"]:
            w("- **`%s`** - blocked on %s under the final policy."
              % (b["fixture_id"], ", ".join("`%s`" % c
                                            for c in b["blocked_classes"])))
        w("")

    # 7 ---------------------------------------------------------------------
    w("## 7. What we could not tell you")
    w("")
    w("> %s" % S7_PREAMBLE)
    w("")
    w("### Capability classes your agent holds that this run never exercised")
    w("")
    if s7["never_reached"]:
        w("**This is a coverage gap, not a clean bill of health.** An attack "
          "family aimed at one of these classes produced no finding because no "
          "call of that class was ever made - not because the agent resisted.")
        w("")
        w("| capability class | attacks in this run that AIMED at it | what it "
          "means | tools that carry it and were never called |")
        w("|---|---|---|---|")
        for row in s7["never_reached"]:
            c = row["capability_class"]
            gloss = (rep["class_glosses"].get(c) or ("", 0))[0]
            w("| `%s` | **%d** | %s | %s |"
              % (c, row["aimed_at_by"], gloss,
                 ", ".join("`%s`" % t for t in row["carriers"]) or "-"))
        w("")
        aimed = [r for r in s7["never_reached"] if r["aimed_at_by"]]
        if aimed:
            w("**Read that column before anything else on this page.** %s"
              % "; ".join(
                  "%d attack(s) in this run declared `%s` as their target class "
                  "and not one call of that class was ever made"
                  % (r["aimed_at_by"], r["capability_class"]) for r in aimed))
            w("")
            w("An attack that never induced a call of the class it was aiming at "
              "produced no finding **because the capability was never reached**, "
              "not because the agent resisted. Every invariant guarding those "
              "classes is therefore untested by this run, and the report will not "
              "let an absence of findings there read as a defence.")
            w("")
        w("The `AIMED AT` column is counted over the **%d corpus attack(s)** in "
          "this run whose declared target class this report could resolve, out of "
          "%d attempted. Generated attacks declare no target class, so they are "
          "not in that denominator." % (s7["corpus_joined"],
                                        s7["corpus_joined"] + s7["corpus_unjoined"]))
        if s7["corpus_unjoined"]:
            w("")
            w("**%d corpus attack(s) could not be resolved against the corpus on "
              "disk.** The join is content-addressed, so this usually means the "
              "corpus has moved since the run. Treat the column as a floor."
              % s7["corpus_unjoined"])
        if s7["corpus_join_error"]:
            w("")
            w("**The corpus join did not run: %s.** The `AIMED AT` column is "
              "unavailable, not zero." % s7["corpus_join_error"])
        w("")
    else:
        w("Every capability class declared in the target's manifest was exercised "
          "at least once.")
        w("")
    if s7["never_called"]:
        w("Tools never called in any episode: %s."
          % ", ".join("`%s`" % t for t in s7["never_called"]))
        w("")
    w("### Invariants that never fired, and why that is two different things")
    w("")
    w("| state | invariants | what the state means |")
    w("|---|---|---|")
    meanings = {
        "UNREACHED": "no episode ever made a call this clause could look at. The "
                     "clause was never given the chance to fail",
        "NEVER_TRUE": "the clause was evaluated and its condition never held. This "
                      "one is a measurement",
        "FIRED": "the clause matched at least once",
    }
    for state in ("FIRED", "NEVER_TRUE", "UNREACHED"):
        rows = s7["clause_states"].get(state) or []
        if not rows:
            continue
        w("| **%s** | %s | %s |" % (state,
                                    ", ".join("`%s`" % r["invariant_id"]
                                              for r in rows),
                                    meanings.get(state, "")))
    w("")
    if s7["never_fired"]:
        w("### Rules in force that stopped nothing in this run")
        w("")
        w("Promoted or seeded, and never once the reason a call was blocked or "
          "held on any recorded path. A rule that has never fired is a rule "
          "nothing here has tested.")
        w("")
        for r in s7["never_fired"]:
            w("- **`%s`** (`%s`, origin `%s`) - %s"
              % (r["rule_id"], r["verb"], r["origin"], r["english"]))
        w("")
    w("### The labels this run carries, verbatim")
    w("")
    for k, v in sorted((s7["labels"] or {}).items()):
        w("- **`%s`** - %s" % (k, v))
    w("")
    sep = s7["sep_by_split"]
    if sep:
        w("**SEP-BY split: %s policy-separated, %s separated by the approval "
          "oracle.** A suite the oracle separates produces identical headline "
          "numbers to one the policy separates, and only this ratio tells them "
          "apart." % (sep.get("policy_separated"), sep.get("approval_oracle_separated")))
        w("")
    w("### The rest of the boundary")
    w("")
    w("- Reps: %s" % (s7["reps"] or "not recorded"))
    w("- Run status `%s`, halt `%s`." % (s7["status"], s7["halt"]))
    w("- One target agent, one seed policy, one run. Nothing here generalises to "
      "another agent without measuring that agent.")
    if s7["constrain_arg_proposed"] is False:
        w("- `constrain_arg` was never proposed in this run, so one of the three "
          "verbs is untested here.")
    if s7["excluded"]:
        w("- %d episode(s) were EXCLUDED from scoring: %s"
          % (len(s7["excluded"]),
             ", ".join(str(e) for e in s7["excluded"])[:400]))
    for item in s7["untested_against_live_gcs"] or []:
        w("- Untested against live GCS: %s" % item)
    if s7["defects"]:
        w("- **The offline reader REFUSED this bundle.** %s"
          % "; ".join("`%s` at %s: %s" % (d["code"], d["where"], d["detail"])
                      for d in s7["defects"]))
    for d in s7["disagreements"]:
        w("- **%s**" % d)
    w("")
    w("### Where the words on this page came from")
    w("")
    w("- Attack family names: `%s`" % s7["citations"]["families"])
    w("- Capability class descriptions: `%s`" % s7["citations"]["classes"])
    w("- Severity: `%s`. UNRATED is the absence of a declaration and is NOT a low "
      "severity." % s7["citations"]["severity"])
    w("- Every verdict on this page was produced by the loop's own arbiters - the "
      "real L3 policy engine, the real warden replay walk, the real pure-code "
      "tripwire - not by a second implementation written for the report.")
    w("")
    return "\n".join(o) + "\n"


# ---------------------------------------------------------------------------
# html. Same palette and the same type scale as docs/diagrams/attack-surface.html
# and docs/finding-cards/cards-smoke-2026-08-25.html, so the three read as one
# product rather than three scripts' output.
# ---------------------------------------------------------------------------

CSS = """
:root{--bg:#fbfbf9;--fg:#1b1b1a;--mut:#5d5d58;--line:#d8d6ce;--card:#fff;
--crit:#8a1c1c;--unr:#5d5d58;--ok:#1f5c34;--bad:#8a1c1c;--warn:#8a5a12;
--code:#f2f0e9;--accent:#2f4858;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
--bg:#14140f;--fg:#eceae2;--mut:#9b9a91;--line:#33322b;--card:#1c1c16;
--crit:#e07a7a;--unr:#9b9a91;--ok:#7fc79a;--bad:#e07a7a;--warn:#d8a95a;
--code:#232219;--accent:#9fc0d0;}}
:root[data-theme="dark"]{--bg:#14140f;--fg:#eceae2;--mut:#9b9a91;--line:#33322b;
--card:#1c1c16;--crit:#e07a7a;--unr:#9b9a91;--ok:#7fc79a;--bad:#e07a7a;
--warn:#d8a95a;--code:#232219;--accent:#9fc0d0;}
*{box-sizing:border-box;}
body{background:var(--bg);color:var(--fg);margin:0;padding:2rem 1rem 6rem;
font:16px/1.55 ui-sans-serif,-apple-system,"Segoe UI",system-ui,sans-serif;}
main{max-width:64rem;margin:0 auto;}
h1{font-size:1.9rem;letter-spacing:-.025em;margin:0 0 .3rem;line-height:1.15;}
h2{font-size:1.25rem;letter-spacing:-.015em;margin:3rem 0 .8rem;
border-top:1px solid var(--line);padding-top:1.5rem;}
h2 .n{color:var(--mut);font-weight:400;margin-right:.5rem;
font-variant-numeric:tabular-nums;}
h3{font-size:1rem;margin:1.8rem 0 .5rem;letter-spacing:-.01em;}
h4{font-size:.78rem;text-transform:uppercase;letter-spacing:.1em;color:var(--mut);
margin:1.3rem 0 .4rem;font-weight:600;}
p,li{max-width:74ch;}
.lede{color:var(--mut);font-size:.92rem;}
.banner{border-left:3px solid var(--crit);background:var(--card);padding:.8rem 1rem;
margin:1.2rem 0;font-size:.9rem;color:var(--mut);}
.note{border-left:3px solid var(--line);background:var(--card);padding:.8rem 1rem;
margin:1.2rem 0;font-size:.9rem;color:var(--mut);}
.verdict{margin:1.6rem 0;border:1px solid var(--line);border-radius:6px;
overflow:hidden;background:var(--card);}
.verdict div{display:flex;gap:.9rem;align-items:baseline;padding:.7rem 1rem;
border-bottom:1px solid var(--line);font-size:.92rem;}
.verdict div:last-child{border-bottom:none;}
.tag{flex:0 0 8.5rem;font-size:.7rem;font-weight:700;letter-spacing:.09em;
text-transform:uppercase;}
.tag.FOUND,.tag.HARDENED,.tag.CLOSED{color:var(--ok);}
.tag.INCOMPLETE,.tag.COST,.tag.LOST,.tag.NOTHINGFOUND,.tag.NOTHINGLEARNED,
.tag.WEAKENED,.tag.DROPPED{color:var(--warn);}
.tag.DEFECT,.tag.REFUSED{color:var(--crit);}
.card{background:var(--card);border:1px solid var(--line);border-radius:6px;
padding:1rem 1.2rem;margin:1.2rem 0;}
.hdr{display:flex;gap:.7rem;align-items:baseline;flex-wrap:wrap;
margin-bottom:.4rem;}
.hdr code{font-size:1rem;}
.sev{font-size:.7rem;font-weight:700;letter-spacing:.08em;padding:.15rem .5rem;
border-radius:3px;border:1px solid currentColor;}
.sev.CRITICAL{color:var(--crit);} .sev.UNRATED{color:var(--unr);}
table{border-collapse:collapse;width:100%;font-size:.85rem;margin:.5rem 0;}
th,td{border-bottom:1px solid var(--line);padding:.34rem .55rem;text-align:left;
vertical-align:top;}
th{color:var(--mut);font-weight:600;font-size:.73rem;text-transform:uppercase;
letter-spacing:.06em;}
td.num{font-variant-numeric:tabular-nums;}
.scroll{overflow-x:auto;max-width:100%;}
/* Ligatures OFF. A coding font renders `>=` as one glyph and `=>` as another,
   and these blocks hold a DSL a reader retypes. */
code,pre{font-family:ui-monospace,Consolas,"DejaVu Sans Mono",monospace;
font-variant-ligatures:none;}
code{background:var(--code);padding:.08em .35em;border-radius:3px;font-size:.86em;
overflow-wrap:anywhere;}
pre{background:var(--code);padding:.75rem .9rem;border-radius:4px;overflow-x:auto;
font-size:.82rem;margin:.4rem 0;}
pre code{background:none;padding:0;}
blockquote{margin:.6rem 0;padding-left:.9rem;border-left:2px solid var(--accent);
color:var(--mut);font-size:.92rem;}
details{margin:.4rem 0;font-size:.85rem;}
summary{cursor:pointer;color:var(--mut);}
.ok{color:var(--ok);font-weight:600;} .bad{color:var(--bad);font-weight:600;}
.warn{color:var(--warn);font-weight:600;}
.mut{color:var(--mut);font-size:.88rem;}
ul.tight li{margin:.15rem 0;}
"""


def E(x):
    return html.escape("" if x is None else str(x), quote=False)


def C(x):
    return "<code>%s</code>" % E(x)


def _rows(head, body):
    o = ['<div class="scroll"><table>']
    if head:
        o.append("<thead><tr>%s</tr></thead>"
                 % "".join("<th>%s</th>" % h for h in head))
    o.append("<tbody>")
    for r in body:
        o.append("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in r))
    o.append("</tbody></table></div>")
    return "\n".join(o)


def render_html(rep, invocation, generated_at):
    s1, s2, s3, s4, s5, s6, s7 = (rep["s1"], rep["s2"], rep["s3"], rep["s4"],
                                  rep["s5"], rep["s6"], rep["s7"])
    o = []
    w = o.append
    w("<title>CRUCIBLE hardening report</title>")
    w("<style>%s</style>" % CSS)
    w("<main>")
    w("<h1>CRUCIBLE hardening report</h1>")
    w('<p class="lede">Run <code>%s</code> &middot; spine %s &middot; recorded %s'
      "<br>Generated at %s. Regenerate this file; never edit it.</p>"
      % (E(rep["run_id"]), E(rep["spine_version"]), E(rep["created_at"]),
         E(generated_at)))
    w("<pre><code>%s</code></pre>" % E(invocation))
    w(_rows(None, [["evidence bundle, the run of record", C(rep["bundle_path"])],
                   ["run record, for the executable final policy",
                    C(rep["record_path"])]]))
    w('<div class="banner">%s</div>' % E(NO_SCORE))

    w('<div class="verdict">')
    for tag, text in rep["verdict"]:
        w('<div><span class="tag %s">%s</span><span>%s</span></div>'
          % (tag.replace(" ", ""), E(tag), E(text)))
    w("</div>")

    # 1 ---------------------------------------------------------------------
    w('<h2><span class="n">1</span>What we threw at it</h2>')
    w("<p>%d attacks across %d episodes, attack mode %s, against %s at "
      "thinking_level %s.</p>"
      % (s1["attacks"], s1["episodes"], C(s1["attack_mode"]),
         C(s1["target_model"]), C(s1["target_thinking"])))
    body = []
    for code, n in s1["by_family"]:
        name, line = _fam(s1, code)
        body.append(["<b>%s</b>" % E(code), '<span class="num">%d</span>' % n,
                     E(name.rstrip(".")),
                     C("%s:%d" % (s7["citations"]["families"], line))])
    w(_rows(["family", "attacks", "what the family does", "cited"], body))
    w(_rows(["provenance", "attacks"],
            [[C(p), str(n)] for p, n in s1["by_provenance"]]))
    w('<p class="mut"><b>Never pool those two.</b> A mixed rate hides which half '
      "moved.</p>")
    w("<p>Episodes attempted %d, scorable %d, excluded %d, across %d round(s).</p>"
      % (s1["attempted"], s1["scorable"], s1["excluded"], len(s1["rounds"])))
    w("<h4>What the attacks actually reached</h4>")
    w('<p class="mut">Counted from <code>TOOL_EXECUTED</code> events, so this is '
      "what happened rather than what was aimed at.</p>")
    w(_rows(["capability class", "executed calls", "what the class means"],
            [[C(c), str(n), E((rep["class_glosses"].get(c) or ("", 0))[0])]
             for c, n in s1["reached"]]))
    w(_rows(["tool", "executed calls"],
            [[C(t), str(n)] for t, n in s1["tools_called"]]))

    # 2 ---------------------------------------------------------------------
    w('<h2><span class="n">2</span>What got through</h2>')
    if not s2:
        w('<div class="banner"><b>Nothing got through at policy@v0, and that is '
          "not good news.</b> Zero breaches at the seed policy means one of three "
          "things and the run cannot tell you which: the attacks were weak, the "
          "seed policy already held, or the episodes never reached the "
          "capabilities that matter. Section 7 lists what was never exercised. "
          "Read it before reading this as safety.</div>")
    for b in s2:
        w('<div class="card">')
        w('<div class="hdr"><code>%s</code><span class="sev %s">%s</span>'
          '<span class="mut">family %s &middot; %s &middot; round %s &middot; '
          "policy@v%s</span></div>"
          % (E(b["attack_id"]), E(b["severity"]), E(b["severity"]), E(b["family"]),
             E(b["provenance"]), E(b["round_index"]), E(b["policy_version"])))
        w('<p class="mut"><b>Severity is derived, not asserted.</b> %s</p>'
          % E(b["severity_why"]))
        if b["instruction"]:
            w("<h4>What the attacker said</h4>")
            w("<blockquote>%s</blockquote>"
              % E(b["instruction"].replace("\n", " ").strip()))
        w("<h4>What the agent was induced to do</h4>")
        w("<p>%s</p>" % E(b["narrative"] or
                          "The autopsy recorded no narrative for this breach."))
        for call in b["calls"]:
            w('<p class="mut">Call at sequence %s &mdash; <code>%s</code>, classed '
              "%s, policy decision <code>%s</code>, status <code>%s</code></p>"
              % (E(call["seq"]), E(call["tool"]),
                 ", ".join(C(c) for c in call["classes"]),
                 E(call["policy_decision"]), E(call["status"])))
            w(_rows(["argument the agent chose", "value"],
                    [[C(k), E(_argval(v))] for k, v in call["chosen"]]))
            if call["derived"]:
                w("<details><summary>%d harness-stamped <code>derived.*</code> "
                  "field(s) on the same call &mdash; computed by CRUCIBLE, not "
                  "chosen by the agent</summary>" % len(call["derived"]))
                w(_rows(["field", "value"],
                        [[C(k), E(_argval(v))] for k, v in call["derived"]]))
                w("</details>")
        w("<h4>What the tripwire matched</h4>")
        w('<p class="mut">%s (%s, %s form)</p>'
          % (C(b["invariant_id"]), C(b["invariant_class"]), E(b["invariant_form"])))
        w("<blockquote>%s</blockquote>"
          % E((b["invariant_why"] or "no rationale recorded").replace("\n", " ")))
        w("</div>")

    # 3 ---------------------------------------------------------------------
    w('<h2><span class="n">3</span>What CRUCIBLE did about it</h2>')
    w("<p>The patch language has three verbs &mdash; <code>deny</code>, "
      "<code>require_approval</code>, <code>constrain_arg</code> &mdash; "
      "<b>and no <code>allow</code> verb</b>. No sequence of patches can widen "
      "what your agent is permitted to do; the reachable set only ever shrinks.</p>")
    if not s3["learned"]:
        w('<div class="banner"><b>No rule was promoted in this run.</b> The policy '
          "at the end is the policy at the start. Nothing in this section "
          "describes a change because there was none.</div>")
    for r in s3["learned"]:
        w('<div class="card">')
        w('<div class="hdr"><code>%s</code><span class="mut">%s &middot; promoted '
          "in round %s</span></div>" % (E(r["rule_id"]), C(r["verb"]),
                                        E(r["round_index"])))
        w("<p><b>In English.</b> %s</p>" % _md_inline(r["english"]))
        w("<pre><code>%s</code></pre>" % E(r["dsl_text"]))
        w('<p class="mut">Answers the breach on attack %s (family %s, invariant '
          "%s).</p>" % (C(r["answers_attack"]), E(r["answers_family"]),
                        C(r["answers_invariant"])))
        if r["validator_result"]:
            w('<p class="mut">Validator: %s</p>' % E(r["validator_result"]))
        if r["warden_result"]:
            w('<p class="mut">Warden: %s</p>' % E(r["warden_result"]))
        w("</div>")
    if s3["dropped"]:
        w("<h3>Promoted, and not in the final policy</h3>")
        w("<p>The gate recorded <b>%s</b> promotion(s) and <b>%d</b> learned "
          "rule(s) are in force at the end. Those are different quantities: "
          "<code>summary.promotions</code> counts gate decisions, the policy is a "
          "set of rules, and nothing in the run record reconciles them. Here is "
          "the difference.</p>"
          % (E(s3["promotions_recorded"]), len(s3["learned"])))
        for d in s3["dropped"]:
            w('<div class="card"><div class="hdr"><code>%s</code>'
              '<span class="mut">%s &middot; promoted, then gone</span></div>'
              % (E(d["rule_id"]), C(d["verb"])))
            w("<pre><code>%s</code></pre>" % E(d["dsl_text"]))
            if d["successor_id"]:
                w("<p>A rule with the <b>identical predicate</b> is in force under "
                  "a different verb: %s uses %s where this used %s. The predicate "
                  "did not change; the strength did. Whether that was the right "
                  "trade is a judgement this report does not make for you, and it "
                  "is not visible anywhere else in the run's own output.</p>"
                  % (C(d["successor_id"]), C(d["successor_verb"]), C(d["verb"])))
            w("</div>")
    if s3["seeded"]:
        w("<h3>Rules that were already there</h3>")
        w('<p class="mut">Seed rules. CRUCIBLE did not learn these; they are shown '
          "because sections 4 and 6 measure the whole policy in force, and a reader "
          "who took every effect below for something the loop discovered would be "
          "wrong about what the run achieved.</p>")
        for r in s3["seeded"]:
            w('<div class="card"><div class="hdr"><code>%s</code>'
              '<span class="mut">%s &middot; seed</span></div>'
              % (E(r["rule_id"]), C(r["verb"])))
            w("<p>%s</p>" % _md_inline(r["english"]))
            w("<pre><code>%s</code></pre></div>" % E(r["dsl_text"]))
    if s3["gates"]:
        w("<h3>What the gate checked before letting each one through</h3>")
        w(_rows(["round", "decision", "benign floor", "live cloud assertions",
                 "failed"],
                [[E(g["round_index"]), "<b>%s</b>" % E(g["decision"]),
                  "%s/%s" % (E(g["benign"].get("passed")),
                             E(g["benign"].get("total"))),
                  str(g["checks"]), str(len(g["failed"]))]
                 for g in s3["gates"]]))

    # 4 ---------------------------------------------------------------------
    w('<h2><span class="n">4</span>What stops now</h2>')
    w("<blockquote>%s</blockquote>" % _md_inline(S4_CAVEAT))
    if not s4["rows"]:
        w("<p>Nothing reached an invariant at <code>policy@v0</code>, so there is "
          "no before and after to show.</p>")
    else:
        cls = "bad" if s4["still_breaching"] else "ok"
        w('<p><b>%d recorded breach path(s) at <code>policy@v0</code>. '
          '<span class="%s">%d still reach their invariant at '
          "<code>policy@vFinal</code>.</span></b></p>"
          % (s4["breached_at_v0"], cls, s4["still_breaching"]))
        w(_rows(["attack", "family", "invariant", "at v0", "at vFinal",
                 "calls executed", "stopped by"],
                [[C(r["attack_id"]), E(r["family"]), C(r["v0_invariant"]),
                  '<span class="bad">BREACH</span>',
                  '<span class="%s">%s</span>' % ("ok" if r["stopped"] else "bad",
                                                  E(r["vfinal"])),
                  "%d &rarr; %d" % (r["executed_before"], r["executed_after"]),
                  ", ".join(C(x) for x in r["fired_rules"]) or
                  '<span class="mut">nothing</span>']
                 for r in s4["rows"]]))
        unstopped = [r for r in s4["rows"] if not r["stopped"]]
        if unstopped:
            w("<h3>The ones that are still open</h3>")
            w('<div class="banner">Every one of these motivated a rule that the '
              "gate promoted. The gate checks that a patch is well-formed and that "
              "benign traffic survives it. <b>It does not check that the patch "
              "closes the breach it was written for.</b></div>")
            w('<ul class="tight">')
            for r in unstopped:
                w("<li>%s (family %s) still reaches %s. No rule stopped a single "
                  "call on the recorded path: %d call(s) executed before, %d after."
                  "</li>" % (C(r["attack_id"]), E(r["family"]), C(r["v0_invariant"]),
                             r["executed_before"], r["executed_after"]))
            w("</ul>")
    if s4["regressions"]:
        w('<div class="banner"><b>DEFECT.</b> %d episode(s) score CLEAN at v0 and '
          "BREACH at vFinal. A policy can only remove executed events, so this is "
          "arithmetically impossible and means this replay is wrong: %s</div>"
          % (len(s4["regressions"]),
             ", ".join(C(r["episode_id"]) for r in s4["regressions"])))

    # 5 ---------------------------------------------------------------------
    w('<h2><span class="n">5</span>What your agent can still do</h2>')
    w('<p class="mut">Named, not summarised. A fraction cannot tell you which '
      "capability survived.</p>")
    w("<p>%d of %d benign fixtures pass under <code>policy@vFinal</code>, %d of %d "
      "of them near-misses &mdash; fixtures built to sit one field away from an "
      "attack.</p>" % (s5["passed"], s5["total"], s5["near_miss_passed"],
                       s5["near_miss_total"]))
    body = []
    for b in s5["rows"]:
        if not b["passed"]:
            state = '<span class="bad">FAILS</span> &mdash; blocked on %s' % (
                ", ".join(C(c) for c in b["blocked_classes"]))
        elif b["approval_masked"]:
            state = '<span class="warn">passes ONLY with a human approver</span>'
        else:
            state = '<span class="ok">passes untouched</span>'
        body.append([C(b["fixture_id"]), "yes" if b["near_miss"] else "", state])
    w(_rows(["benign fixture", "near-miss", "under policy@vFinal"], body))

    # 6 ---------------------------------------------------------------------
    w('<h2><span class="n">6</span>What it cost you</h2>')
    w('<div class="banner">%s</div>' % _md_inline(S6_PREAMBLE))
    if s6["measured"]:
        w('<p><b class="warn">%d of the %d benign passes above are not your '
          "agent's. They are your approver's.</b> Those flows now stop at the "
          "policy and reach a human before they proceed.</p>"
          % (s6["measured"], s5["passed"]))
    else:
        w("<p><b>No benign flow needs a human that did not need one before.</b> "
          "Measured by replaying every benign fixture twice, once with its declared "
          "approver and once with the approver stripped to the sentinel.</p>")
    if s6["recorded"] is not None:
        agree = ("agrees" if s6["recorded"] == s6["measured"]
                 else '<span class="bad">DISAGREES</span>')
        w('<p class="mut">The run record\'s own '
          "<code>benign_passes_requiring_approval</code> reads <b>%s</b>, and this "
          "replay measured <b>%d</b>. The two %s.</p>"
          % (E(s6["recorded"]), s6["measured"], agree))
    if s6["masked"]:
        w('<ul class="tight">')
        for b in s6["masked"]:
            w("<li>%s &mdash; stopped by %s, then approved. Without the approver "
              "this fixture fails." % (C(b["fixture_id"]),
                                       ", ".join(C(r) for r in b["stopped_by"])))
            for rid in b["stopped_by"]:
                if rid in s6["english"]:
                    w('<div class="mut">%s</div>' % _md_inline(s6["english"][rid]))
            w("</li>")
        w("</ul>")
        w('<div class="note"><b>The fix has to be to the ruler, and it has not '
          "been written.</b> The benign floor still counts an approved call as a "
          "pass, so a policy that sent every call to a human would score a perfect "
          "benign rate while leaving your agent unable to do anything on its "
          "own.</div>")
    if s6["failed"]:
        w("<h3>Capability actually lost</h3>")
        w('<ul class="tight">')
        for b in s6["failed"]:
            w("<li>%s &mdash; blocked on %s under the final policy.</li>"
              % (C(b["fixture_id"]),
                 ", ".join(C(c) for c in b["blocked_classes"])))
        w("</ul>")

    # 7 ---------------------------------------------------------------------
    w('<h2><span class="n">7</span>What we could not tell you</h2>')
    w("<blockquote>%s</blockquote>" % E(S7_PREAMBLE))
    w("<h3>Capability classes your agent holds that this run never exercised</h3>")
    if s7["never_reached"]:
        w('<div class="banner"><b>This is a coverage gap, not a clean bill of '
          "health.</b> An attack family aimed at one of these classes produced no "
          "finding because no call of that class was ever made &mdash; not because "
          "the agent resisted.</div>")
        w(_rows(["capability class", "attacks in this run that aimed at it",
                 "what it means", "tools that carry it and were never called"],
                [[C(r["capability_class"]), "<b>%d</b>" % r["aimed_at_by"],
                  E((rep["class_glosses"].get(r["capability_class"])
                     or ("", 0))[0]),
                  ", ".join(C(t) for t in r["carriers"]) or "&ndash;"]
                 for r in s7["never_reached"]]))
        aimed = [r for r in s7["never_reached"] if r["aimed_at_by"]]
        if aimed:
            w('<div class="banner"><b>Read that column before anything else on '
              "this page.</b> %s. An attack that never induced a call of the class "
              "it was aiming at produced no finding <b>because the capability was "
              "never reached</b>, not because the agent resisted. Every invariant "
              "guarding those classes is therefore untested by this run, and the "
              "report will not let an absence of findings there read as a "
              "defence.</div>"
              % E("; ".join(
                  "%d attack(s) in this run declared %s as their target class and "
                  "not one call of that class was ever made"
                  % (r["aimed_at_by"], r["capability_class"]) for r in aimed)))
        w('<p class="mut">The aimed-at column is counted over the <b>%d corpus '
          "attack(s)</b> in this run whose declared target class this report could "
          "resolve, out of %d attempted. Generated attacks declare no target "
          "class, so they are not in that denominator.%s%s</p>"
          % (s7["corpus_joined"], s7["corpus_joined"] + s7["corpus_unjoined"],
             (" <b>%d corpus attack(s) could not be resolved against the corpus "
              "on disk</b> - the join is content-addressed, so this usually means "
              "the corpus has moved since the run. Treat the column as a floor."
              % s7["corpus_unjoined"]) if s7["corpus_unjoined"] else "",
             (" <b>The corpus join did not run: %s.</b> The column is unavailable, "
              "not zero." % E(s7["corpus_join_error"]))
             if s7["corpus_join_error"] else ""))
    else:
        w("<p>Every capability class declared in the target's manifest was "
          "exercised at least once.</p>")
    if s7["never_called"]:
        w('<p class="mut">Tools never called in any episode: %s.</p>'
          % ", ".join(C(t) for t in s7["never_called"]))
    w("<h3>Invariants that never fired, and why that is two different things</h3>")
    meanings = {
        "UNREACHED": "no episode ever made a call this clause could look at. The "
                     "clause was never given the chance to fail",
        "NEVER_TRUE": "the clause was evaluated and its condition never held. This "
                      "one is a measurement",
        "FIRED": "the clause matched at least once",
    }
    body = []
    for state in ("FIRED", "NEVER_TRUE", "UNREACHED"):
        rows = s7["clause_states"].get(state) or []
        if rows:
            body.append(["<b>%s</b>" % E(state),
                         ", ".join(C(r["invariant_id"]) for r in rows),
                         E(meanings.get(state, ""))])
    w(_rows(["state", "invariants", "what the state means"], body))
    if s7["never_fired"]:
        w("<h3>Rules in force that stopped nothing in this run</h3>")
        w('<p class="mut">Promoted or seeded, and never once the reason a call was '
          "blocked or held on any recorded path. A rule that has never fired is a "
          "rule nothing here has tested.</p>")
        w('<ul class="tight">')
        for r in s7["never_fired"]:
            w("<li>%s (%s, origin %s) &mdash; %s</li>"
              % (C(r["rule_id"]), C(r["verb"]), C(r["origin"]),
                 _md_inline(r["english"])))
        w("</ul>")
    w("<h3>The labels this run carries, verbatim</h3>")
    w('<ul class="tight">')
    for k, v in sorted((s7["labels"] or {}).items()):
        w("<li><b>%s</b> &mdash; %s</li>" % (C(k), E(v)))
    w("</ul>")
    sep = s7["sep_by_split"]
    if sep:
        w('<div class="note"><b>SEP-BY split: %s policy-separated, %s separated by '
          "the approval oracle.</b> A suite the oracle separates produces identical "
          "headline numbers to one the policy separates, and only this ratio tells "
          "them apart.</div>" % (E(sep.get("policy_separated")),
                                 E(sep.get("approval_oracle_separated"))))
    w("<h3>The rest of the boundary</h3>")
    w('<ul class="tight">')
    w("<li>Reps: %s</li>" % E(s7["reps"] or "not recorded"))
    w("<li>Run status %s, halt %s.</li>" % (C(s7["status"]), C(s7["halt"])))
    w("<li>One target agent, one seed policy, one run. Nothing here generalises to "
      "another agent without measuring that agent.</li>")
    if s7["constrain_arg_proposed"] is False:
        w("<li><code>constrain_arg</code> was never proposed in this run, so one of "
          "the three verbs is untested here.</li>")
    if s7["excluded"]:
        w("<li>%d episode(s) were EXCLUDED from scoring.</li>" % len(s7["excluded"]))
    for item in s7["untested_against_live_gcs"] or []:
        w("<li>Untested against live GCS: %s</li>" % E(item))
    if s7["defects"]:
        w("<li><b>The offline reader REFUSED this bundle.</b> %s</li>"
          % E("; ".join("%s at %s: %s" % (d["code"], d["where"], d["detail"])
                        for d in s7["defects"])))
    for d in s7["disagreements"]:
        w("<li><b>%s</b></li>" % E(d))
    w("</ul>")
    w("<h3>Where the words on this page came from</h3>")
    w('<ul class="tight">')
    w("<li>Attack family names: %s</li>" % C(s7["citations"]["families"]))
    w("<li>Capability class descriptions: %s</li>" % C(s7["citations"]["classes"]))
    w("<li>Severity: %s. UNRATED is the absence of a declaration and is NOT a low "
      "severity.</li>" % C(s7["citations"]["severity"]))
    w("<li>Every verdict on this page was produced by the loop's own arbiters "
      "&mdash; the real L3 policy engine, the real warden replay walk, the real "
      "pure-code tripwire &mdash; not by a second implementation written for the "
      "report.</li>")
    w("</ul>")
    w("</main>")
    return "\n".join(o) + "\n"


def _md_inline(text):
    """The few markdown marks the shared prose uses, rendered for HTML.

    The prose is authored ONCE and rendered into both formats; without this the
    two pages would have to carry separate copies of the same sentence, which is
    a second source of truth about what the run means.
    """
    out = E(text)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)
    return out


# ---------------------------------------------------------------------------
# writing
# ---------------------------------------------------------------------------

def write_lf(path, text):
    """LF on disk, always. Python's text mode translates newlines on Windows and
    rewrites the whole file as CRLF, which shows up as a several-hundred-line
    diff on a one-line change. Bytes, explicitly."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.replace("\r\n", "\n").encode("utf-8"))


def display_path(p):
    """Repo-relative when it can be, cwd-relative next, absolute last.

    `evidence/` is gitignored, so a bundle can legitimately sit outside the
    checkout. Printing an absolute path in that case is correct and printing a
    repo-relative one would be a command that does not run.
    """
    p = pathlib.Path(p)
    for base in (REPO, pathlib.Path.cwd()):
        try:
            return p.resolve().relative_to(base).as_posix()
        except ValueError:
            continue
    return p.as_posix()


# ---------------------------------------------------------------------------
# the negative controls
# ---------------------------------------------------------------------------

NEG_CONTROLS = {
    "no-breaches": (
        "every episode scored CLEAN and the autopsies are gone",
        "the page must say a run that found nothing is NOT a clean bill of "
        "health, and must not render 0 breaches as a success"),
    "no-promotions": (
        "the ARMORER's rules are stripped from the final policy, the policy "
        "chain and the proposals",
        "the page must say NOTHING WAS PROMOTED and must not describe a change"),
    "broken-policy-chain": (
        "the bundle's policy_chain is emptied, so the two inputs can no longer "
        "be cross-checked",
        "the page must carry the cross-check failure in section 7 rather than "
        "quietly running on the sidecar alone"),
    "policy-disagreement": (
        "the bundle's last policy_chain entry loses a rule the run record still "
        "holds",
        "the report must refuse: it would otherwise print one policy's DSL "
        "while measuring another policy's effects"),
}


def _doctor(bundle, record, which):
    """Return doctored (bundle, record) for one negative control.

    These are DELIBERATELY BROKEN INPUTS. A generator that renders a
    confident-looking page regardless of input is exactly the failure this
    project keeps meeting, so each control drives one branch of `verdict_lines`
    and the selftest asserts on the sentence that comes out.
    """
    b = json.loads(json.dumps(bundle))
    r = json.loads(json.dumps(record))
    if which == "no-breaches":
        for ep in b.get("episodes") or []:
            ep["verdict"] = {"verdict": "CLEAN", "breach": False,
                             "objective_set_hash": ep.get("objective_set_hash"),
                             "evidence": []}
        b["autopsies"] = []
    elif which == "no-promotions":
        keep = [x["rule_id"] for x in
                r["final_policy"]["hashed_payload"]["rules"]
                if x.get("origin") != "armorer"]
        r["final_policy"]["hashed_payload"]["rules"] = [
            x for x in r["final_policy"]["hashed_payload"]["rules"]
            if x.get("origin") != "armorer"]
        for entry in b.get("policy_chain") or []:
            entry["rules"] = [x for x in entry.get("rules") or []
                              if x.get("rule_id") in keep]
        b["patch_proposals"] = []
        b["gate_decisions"] = []
    elif which == "broken-policy-chain":
        b["policy_chain"] = []
    elif which == "policy-disagreement":
        chain = b.get("policy_chain") or []
        if chain and chain[-1].get("rules"):
            chain[-1]["rules"] = chain[-1]["rules"][:-1]
    else:
        raise SystemExit("unknown negative control %r" % which)
    return b, r


def selftest(bundle_path, out_dir):
    """Prove the report CAN say bad things.

    Runs the real generator over four deliberately broken inputs and asserts on
    the sentences that come back. Every assertion below is on text a reader
    would see, not on an internal flag, because the failure this guards against
    is a page that LOOKS fine.
    """
    c6 = pathlib.Path(bundle_path)
    bundle, defects = open_bundle(c6)
    record, record_path = open_run_record(c6)
    failures, ran = [], []

    def check(name, cond, detail):
        ran.append(name)
        if not cond:
            failures.append("%s: %s" % (name, detail))

    # The control that must be REFUSED before anything is rendered.
    b, r = _doctor(bundle, record, "policy-disagreement")
    ran.append("policy-disagreement is REFUSED")
    if not cross_check_policy(b, r):
        failures.append("policy-disagreement: the cross-check ACCEPTED two inputs "
                        "that disagree about which rules are in force")

    baseline = build_report(bundle, record, display_path(c6),
                            display_path(record_path), defects, [])
    base_md = render_md(baseline, "selftest", "SELFTEST")
    check("the honest run names its own open findings",
          ("still reach their invariant" in base_md
           or "All %d recorded breach paths stop" % baseline["s4"]["breached_at_v0"]
           in base_md),
          "section 4 said neither that paths remain open nor that they closed")
    check("the honest run prints section 6 whatever the count",
          "## 6. What it cost you" in base_md,
          "section 6 is missing from a real run")
    check("no rolled-up score appears",
          "NO ROLLED-UP SCORE" in base_md,
          "the refusal banner is gone")

    for which in ("no-breaches", "no-promotions", "broken-policy-chain"):
        b, r = _doctor(bundle, record, which)
        dis = cross_check_policy(b, r)
        rep = build_report(b, r, display_path(c6), display_path(record_path),
                           defects, dis)
        md = render_md(rep, "selftest", "SELFTEST")
        html_out = render_html(rep, "selftest", "SELFTEST")
        tags = [t for t, _ in rep["verdict"]]
        if out_dir:
            write_lf(pathlib.Path(out_dir) / ("negative-control-%s.md" % which), md)
            write_lf(pathlib.Path(out_dir) / ("negative-control-%s.html" % which),
                     html_out)
        if which == "no-breaches":
            check("no breaches -> NOTHING FOUND", "NOTHING FOUND" in tags,
                  "verdict tags were %r" % tags)
            check("no breaches -> refuses to read as safety",
                  "that is not good news" in md,
                  "section 2 did not say a run that found nothing is not good news")
            check("no breaches -> never claims the agent is safe",
                  "clean bill of health" in md,
                  "the page did not name the reading it is refusing")
            check("no breaches -> HTML says it too",
                  "not good news" in html_out,
                  "the HTML rendered a blank section instead")
        if which == "no-promotions":
            check("no promotions -> NOTHING LEARNED", "NOTHING LEARNED" in tags,
                  "verdict tags were %r" % tags)
            check("no promotions -> says the policy did not change",
                  "the policy at the start" in md.replace("\n", " "),
                  "section 3 did not say the policy is unchanged")
            check("no promotions -> HARDENED is absent", "HARDENED" not in tags,
                  "it still claimed the agent was hardened")
        if which == "broken-policy-chain":
            check("broken chain -> the cross-check fires",
                  any("E_NO_POLICY_CHAIN" in d for d in dis),
                  "the cross-check stayed silent on an empty policy_chain")
            check("broken chain -> the failure reaches the page",
                  "E_NO_POLICY_CHAIN" in md,
                  "section 7 did not carry the cross-check failure")

    for f in failures:
        print("SELFTEST FAILED - %s" % f)
    # Counted from what ran. A hardcoded summary of a computed result is a claim
    # that cannot fail.
    print("selftest: %d check(s), %d failure(s)" % (len(ran), len(failures)))
    for name in ran:
        print("  - %s" % name)
    print("")
    print("the negative controls, and what each one is asking:")
    for which, (what, must) in sorted(NEG_CONTROLS.items()):
        print("  %s" % which)
        print("    input  : %s" % what)
        print("    must   : %s" % must)
    return 1 if failures else 0


# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="hardening-report.py",
        description="turn one C6 evidence bundle into a hardening report")
    ap.add_argument("bundle", nargs="?",
                    help="path to a run-NN.c6.json evidence bundle")
    ap.add_argument("--out", default="docs/hardening-report",
                    help="output directory (default: docs/hardening-report)")
    ap.add_argument("--name", default=None,
                    help="basename for the two output files (default: the run id)")
    ap.add_argument("--provisional", action="store_true",
                    help="render even if the offline reader REFUSES the bundle. "
                         "The refusal is printed on the page and no figure on it "
                         "may be quoted.")
    ap.add_argument("--selftest", action="store_true",
                    help="run the negative controls and exit")
    ap.add_argument("--selftest-out", default=None,
                    help="with --selftest, also write each control's pages here")
    args = ap.parse_args(argv)

    if args.selftest:
        bundle = args.bundle or "evidence/smoke-2026-08-25/run-02.c6.json"
        return selftest(bundle, args.selftest_out)

    if not args.bundle:
        ap.error("the bundle path is required")
    c6 = pathlib.Path(args.bundle)
    if not c6.exists():
        raise SystemExit("E_NO_BUNDLE: %s does not exist." % c6)

    bundle, defects = open_bundle(c6)
    if defects and not args.provisional:
        print("THE OFFLINE READER REFUSED THIS BUNDLE, %d defect(s)." % len(defects))
        for d in defects:
            print("  %s at %s: %s" % (d["code"], d["where"], d["detail"]))
        print("")
        print("No report is written. The reader failing closed IS THE READER "
              "WORKING: a bundle that renders while missing what makes it "
              "meaningful is worse than one that fails to open. Pass "
              "--provisional to render it anyway, and the refusal will be "
              "printed on the page.")
        return 2

    record, record_path = open_run_record(c6)
    disagreements = cross_check_policy(bundle, record)
    fatal = [d for d in disagreements if d.startswith("E_POLICY_DISAGREEMENT")]
    if fatal:
        for d in fatal:
            print(d)
        print("")
        print("No report is written. Sections 4, 5 and 6 run the run record's "
              "policy while section 3 prints the bundle's DSL; with the two "
              "disagreeing the page would describe one policy and measure "
              "another.")
        return 2

    rep = build_report(bundle, record, display_path(c6), display_path(record_path),
                       defects, disagreements)
    invocation = "python scripts/hardening-report.py %s --out %s%s" % (
        display_path(c6), args.out,
        " --name %s" % args.name if args.name else "")

    import datetime
    generated_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    name = args.name or (rep["run_id"] or "report")
    out = pathlib.Path(args.out)
    md_path = out / ("%s.md" % name)
    html_path = out / ("%s.html" % name)
    write_lf(md_path, render_md(rep, invocation, generated_at))
    write_lf(html_path, render_html(rep, invocation, generated_at))

    print("CRUCIBLE hardening report")
    print("  run          : %s" % rep["run_id"])
    print("  bundle       : %s" % rep["bundle_path"])
    print("  run record   : %s" % rep["record_path"])
    for tag, text in rep["verdict"]:
        print("  %-13s: %s" % (tag.lower(), text))
    print("  wrote        : %s" % display_path(md_path))
    print("  wrote        : %s" % display_path(html_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
