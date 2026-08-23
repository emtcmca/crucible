"""matrix.py - how much of the definition of breach anything actually touches.

THE DEFECT THIS INSTRUMENT EXISTS TO END

On 2026-08-22 two of the nine frozen Objective Set clauses were found naming
argument paths no tool in the target emits - `memo` and `recipient_email`, where
`target/refund_agent/tools.py` writes `body` and `to`. A clause naming an absent
path DOES NOT RAISE. `resolve()` returns `_ABSENT`, `condition_holds` returns
False, and the clause evaluates to false quietly, forever. Four episodes scored
CLEAN that should have scored BREACH, and nothing noticed across 1,435 tests and
a hash freeze.

The bug was the argument path. THE DEFECT WAS THAT NOTHING WAS POINTED AT THE
QUESTION. A clause could go dark and no check in the build would say so.

WHAT WAS ALREADY HERE, BECAUSE IT IS NOT NOTHING
-------------------------------------------------
`contracts/evidence_bundle.schema.json` declares `clause_coverage`,
`crucible.conductor.bundle._clause_coverage` produces it by re-running the real
`matches()` over a run's episodes, `crucible.replay.integrity._check_clause_
coverage` cross-checks it against the verdicts, and `crucible.replay.view`
renders it. That machinery is real and this module does not replace it.

Three things it does not do, and each of them is why `memo` survived:

  1. IT ONLY EXISTS AFTER A RUN. The corpus, the known-bad suite, the benign
     floor and the offline script are all measurable today, with no credentials
     and no model, and none of them was ever measured.
  2. IT COUNTS ONLY `episodes_fired`. A clause reached a hundred times and never
     true and a clause no trace ever reaches are THE SAME ROW - both read zero.
     They are opposite findings and they have opposite repairs.
  3. NOTHING FAILS ON A ZERO. `_check_clause_coverage` checks the table is
     CONSISTENT (one row per cited invariant, right Objective Set hash). It
     never asserts that any clause was exercised. A run in which eight of nine
     clauses were dark produces a green bundle.

THE FOUR STATES A CLAUSE CAN BE IN, WHICH IS THE WHOLE POINT
-------------------------------------------------------------
  FIRED                the clause returned true on at least one episode.
  NEVER TRUE           some executed event carried the clause's capability
                       class AND every condition path on it resolved, and the
                       comparison still never held. THIS IS HEALTHY. It is what
                       a clause looks like when the traces are clean.
  PATH NEVER PRESENT   events reached the clause's capability gate and a
                       condition's argument path was ABSENT on every one of
                       them. THE `memo` SHAPE. The clause is a check that cannot
                       fail and the row looks identical to a healthy zero unless
                       something separates them.
  UNREACHED            no executed event ever carried the clause's capability
                       class. The corpus has nothing to say about this clause.

A fifth exists and is tracked because it is silent in a different way:
CONTEXT FIELD MISSING - a context operator naming an `episode.*` field the
episode does not carry. The real evaluator raises `MissingContextField` and
rules the episode INVALID, which is loud in a run and invisible in a fixture
directory nobody scores.

THE REAL PRIMITIVES ARE IMPORTED, NEVER REIMPLEMENTED
------------------------------------------------------
`_FORMS`, `_matches_shape`, `condition_holds`, `resolve` and `_in_channel` come
from `crucible.tripwire.objective_set`. A second matcher here would measure
coverage of a definition of breach that no component rules with, and the number
would drift from the oracle exactly when it mattered most. The firing decision
in `probe_episode` IS `_FORMS[form](...)` - the same call the TRIPWIRE makes.
"""

from . import sources
from crucible.tripwire.objective_set import (
    _ABSENT,
    _FORMS,
    _condition_positions,
    _in_channel,
    _matches_shape,
    condition_holds,
    MissingContextField,
    resolve,
)
from crucible.tripwire.model import ToolEvent

UNREACHED = "UNREACHED"
PATH_NEVER_PRESENT = "PATH_NEVER_PRESENT"
CONTEXT_FIELD_MISSING = "CONTEXT_FIELD_MISSING"
NEVER_TRUE = "NEVER_TRUE"
FIRED = "FIRED"

# The four dark states. A clause in any of them fired zero times, and the
# distinction between them is which repair it needs - which is exactly what a
# single `episodes_fired: 0` throws away.
DARK_STATES = (UNREACHED, PATH_NEVER_PRESENT, CONTEXT_FIELD_MISSING, NEVER_TRUE)


class ClauseCounters:
    """Per-clause tallies for one (clause, source) cell.

    Every counter is over EPISODES except the `*_events` ones, which are over
    executed events. Both are kept: "one episode reached this clause" and "four
    hundred events reached it" are different facts about how hard the corpus
    leans on a clause, and only the second distinguishes a clause the corpus
    brushes past from one it hammers.
    """

    __slots__ = ("episodes_in_scope", "episodes_cap_reached",
                 "episodes_paths_resolvable", "episodes_fired",
                 "episodes_exempted", "episodes_context_missing",
                 "events_cap_reached", "conditions")

    def __init__(self):
        self.episodes_in_scope = 0
        self.episodes_cap_reached = 0
        self.episodes_paths_resolvable = 0
        self.episodes_fired = 0
        self.episodes_exempted = 0
        self.episodes_context_missing = 0
        self.events_cap_reached = 0
        # {"conditions[0] amount_minor": {"present": n, "absent": n, "true": n}}
        self.conditions = {}

    def condition_slot(self, key):
        return self.conditions.setdefault(
            key, {"present": 0, "absent": 0, "true": 0, "context_missing": 0})

    def merge(self, other):
        for name in ("episodes_in_scope", "episodes_cap_reached",
                     "episodes_paths_resolvable", "episodes_fired",
                     "episodes_exempted", "episodes_context_missing",
                     "events_cap_reached"):
            setattr(self, name, getattr(self, name) + getattr(other, name))
        for key, slot in other.conditions.items():
            mine = self.condition_slot(key)
            for k, v in slot.items():
                mine[k] = mine.get(k, 0) + v
        return self

    def as_dict(self):
        return {
            "episodes_in_scope": self.episodes_in_scope,
            "episodes_cap_reached": self.episodes_cap_reached,
            "episodes_paths_resolvable": self.episodes_paths_resolvable,
            "episodes_fired": self.episodes_fired,
            "episodes_exempted": self.episodes_exempted,
            "episodes_context_missing": self.episodes_context_missing,
            "events_cap_reached": self.events_cap_reached,
            "conditions": {k: dict(v) for k, v in sorted(self.conditions.items())},
        }

    def state(self):
        """Which of the five states this cell is in. FIRED wins over everything."""
        if self.episodes_fired:
            return FIRED
        if not self.episodes_cap_reached:
            return UNREACHED
        if self.episodes_context_missing and not self.episodes_paths_resolvable:
            return CONTEXT_FIELD_MISSING
        if not self.episodes_paths_resolvable:
            return PATH_NEVER_PRESENT
        return NEVER_TRUE


def _positions(clause):
    """`(where, condition, capability_gate)` for every condition in a clause.

    The capability gate is the shape a condition is only ever evaluated BEHIND.
    For `conditions` and `exempt_when` it is the clause's own
    `capability_class`; for `steps[i].conditions` it is step i's. Getting this
    wrong would count a condition as "path absent" on events the real evaluator
    never shows it, which turns a healthy clause into a false dark row.
    """
    out = []
    for where, cond in _condition_positions(clause):
        if where.startswith("steps["):
            i = int(where[len("steps["):where.index("]")])
            gate = clause["steps"][i]
        else:
            gate = clause
        out.append((where, cond, gate))
    return out


def _gate_events(gate, executed):
    """Executed events past a shape's CAPABILITY gate only.

    Deliberately NOT past its conditions: the question "did anything ever carry
    this argument path" has to be asked of every event the clause could look at,
    not only of the ones that already satisfied the other conditions. Membership
    rather than set equality, because `_matches_shape` uses membership and
    `email_customer` carries CAP_EXTERNAL_COMMS *and* CAP_READS_PII.
    """
    cap = gate.get("capability_class")
    if not cap:
        return list(executed)
    return [e for e in executed if cap in e.capability_classes]


def probe_episode(clause, episode, counters):
    """Instrument one clause against one episode. Mutates `counters`.

    The FIRING decision is the real `_FORMS[...]` call - the same function the
    TRIPWIRE rules with. Everything else here is bookkeeping ABOUT that call and
    never a second opinion on it.
    """
    if not _in_channel(clause, episode.channel):
        return
    counters.episodes_in_scope += 1

    executed = [ToolEvent(e) for e in episode.events
                if e.get("kind") == "TOOL_EXECUTED"]
    ctx = episode.episode_context

    positions = _positions(clause)
    gates = {}
    for where, _cond, gate in positions:
        gates.setdefault(id(gate), (gate, _gate_events(gate, executed)))

    # A clause with NO conditions at all (the aggregate forms) is gated by its
    # own capability class alone, so its gate has to be registered even though
    # `_positions` yields nothing for it.
    if not positions:
        gates.setdefault(id(clause), (clause, _gate_events(clause, executed)))

    reached_events = 0
    reached = False
    for gate, evs in gates.values():
        reached_events += len(evs)
        if evs:
            reached = True
    if reached:
        counters.episodes_cap_reached += 1
    counters.events_cap_reached += reached_events

    # -- per-condition path presence, which is the `memo` detector -----------
    any_context_missing = False
    resolvable_positions = 0
    for where, cond, gate in positions:
        key = "%s %s" % (where, cond.get("path"))
        slot = counters.condition_slot(key)
        _gate, evs = gates[id(gate)]
        present = absent = held = 0
        ctx_missing = False
        for event in evs:
            if resolve(event.args, cond["path"]) is _ABSENT:
                absent += 1
                continue
            present += 1
            try:
                if condition_holds(cond, event, ctx):
                    held += 1
            except MissingContextField:
                ctx_missing = True
        slot["present"] += present
        slot["absent"] += absent
        slot["true"] += held
        if ctx_missing:
            slot["context_missing"] += 1
            any_context_missing = True
        if present:
            resolvable_positions += 1

    if any_context_missing:
        counters.episodes_context_missing += 1
    # "Every condition path on this clause resolved on at least one event past
    # its gate." Written as ALL rather than ANY on purpose: a two-condition
    # clause where one path is real and the other is `memo` is still a clause
    # that can never fire, and an ANY here would score it reachable.
    if positions and resolvable_positions == len(positions):
        counters.episodes_paths_resolvable += 1
    elif not positions and reached:
        counters.episodes_paths_resolvable += 1

    # -- the real firing decision -------------------------------------------
    try:
        seqs = _FORMS[clause["form"]](clause, executed, ctx)
    except MissingContextField:
        return
    if seqs is not None:
        counters.episodes_fired += 1
    elif clause.get("exempt_when") and _would_fire_without_exemption(
            clause, executed, ctx):
        # THE EXEMPTION IS COVERAGE TOO, and it is invisible in `episodes_fired`.
        # `inv_refund_outside_window` is the EXPLICIT NON-BREACH clause: a trace
        # that trips its conditions and is then let through by a fault reason
        # code exercised the whole clause, exemption included, and reporting
        # that as "never reached" would hide the only evidence that ruling 6
        # works.
        counters.episodes_exempted += 1


def _would_fire_without_exemption(clause, executed, ctx):
    stripped = {k: v for k, v in clause.items() if k != "exempt_when"}
    try:
        return _FORMS[clause["form"]](stripped, executed, ctx) is not None
    except MissingContextField:
        return False


class CoverageMatrix:
    """Nine rows by N sources, plus the tool census, plus the refusals."""

    def __init__(self, objective_set, tool_names, handles=None):
        self.objective_set = objective_set
        self.tool_names = tuple(sorted(tool_names))
        # {tool_handle: bare tool name}, from the capability manifest.
        self._by_handle = dict(handles or {})
        self.sources = []
        self.refusals = {}
        # {name: reason} - a source that is KNOWN to be absent and is supposed
        # to be. Kept apart from `refusals`, which are broken instruments, and
        # from a column of zeros, which would be a claim. See `declare_absent`.
        self.declared_absent = {}
        self.skips = {}
        self.episode_counts = {}
        # {clause_id: {source: ClauseCounters}}
        self.cells = {c["id"]: {} for c in objective_set.clauses}
        # {source: {tool_name: executed_event_count}}
        self.tools = {}
        self.unmapped_tools = {}

    # -- building ---------------------------------------------------------
    def add_source(self, name, episodes, skipped=()):
        self.sources.append(name)
        self.episode_counts[name] = len(episodes)
        self.skips[name] = list(skipped)
        tools = self.tools.setdefault(name, {})
        unmapped = self.unmapped_tools.setdefault(name, {})
        for clause in self.objective_set.clauses:
            counters = self.cells[clause["id"]].setdefault(name, ClauseCounters())
            for episode in episodes:
                probe_episode(clause, episode, counters)
        for episode in episodes:
            for raw in episode.events:
                if raw.get("kind") != "TOOL_EXECUTED":
                    continue
                tool = self._tool_name(raw)
                tools[tool] = tools.get(tool, 0) + 1
                if tool not in self.tool_names:
                    unmapped[tool] = unmapped.get(tool, 0) + 1

    def add_refusal(self, name, message):
        self.refusals[name] = message

    def declare_absent(self, name, reason):
        """A source that is absent ON PURPOSE, named rather than omitted.

        The F4 sealed family is 24 instances that all smuggle
        `payout_instrument_id`, and it is the ONLY population that exercises
        `inv_payout_to_instrument_not_on_the_order` as designed. It is not on
        this machine: the boundary is IAM, the red-team service account cannot
        read the holdout bucket, and that is the point of the seal.

        DECLARING IT IS THE WHOLE DIFFERENCE. Omitting it leaves a reader to
        infer that the clause is dark because nobody wrote a trace; a column of
        zeros would assert that the holdout was measured and found empty. Both
        are wrong in the same direction, which is the flattering one - they make
        an unmeasured population look like a measured absence.
        """
        self.declared_absent[name] = reason

    def _tool_name(self, raw):
        """The tool a C1 event names, by HANDLE first and `tool_name` second.

        Handle first because the handle is what the capability manifest keys on
        and what the harness actually writes; `tool_name` is present on the
        hand-written golden traces and carries a vocabulary
        (`transfer_funds`, `send_notification`) that no tool in
        `target/refund_agent` has ever exposed. Reading the handle first means a
        migrated fixture is counted against the real tool the moment it is
        migrated, and an unmigrated one shows up in `unmapped_tools` by its dead
        name rather than being silently binned.
        """
        handle = raw.get("tool_handle")
        if handle in self._by_handle:
            return self._by_handle[handle]
        return raw.get("tool_name") or handle or "<unnamed>"

    # -- reading ----------------------------------------------------------
    def pooled(self, clause_id, sources=None):
        total = ClauseCounters()
        for name in (sources or self.sources):
            cell = self.cells[clause_id].get(name)
            if cell is not None:
                total.merge(cell)
        return total

    def dark_clauses(self, sources=None):
        """Clause ids that fired ZERO times across the given sources, with the
        state each one is dark in. Ordered by the authored clause order, which
        is the order `invariant_id` is assigned in."""
        out = []
        for clause in self.objective_set.clauses:
            pooled = self.pooled(clause["id"], sources)
            if pooled.episodes_fired:
                continue
            out.append((clause["id"], pooled.state(), pooled))
        return out

    def speaks_target_vocabulary(self, source):
        """Does every tool this source calls exist in the target?

        THE DISTINCTION THE WHOLE GATE RESTS ON. `tests/golden_traces/**` calls
        `transfer_funds`, `send_notification`, `lookup_customer_record` and
        `update_shipping_address`. `target/refund_agent` has never exposed any
        of the four. A fixture written in that vocabulary can light up a clause
        - KB4 fires `inv_account_identifier_left_the_boundary` on a `memo`
        argument - WITHOUT THAT BEING EVIDENCE THAT ANY REAL TRACE CAN. It is
        evidence that the fixture and the clause were written together, which is
        the closed loop this project calls a check that cannot fail.

        So a clause is "exercised" only when a source SPEAKING THE TARGET'S
        VOCABULARY exercises it. Pooling the fixture arm in is how nine of nine
        clauses read as covered on a day two of them provably could not fire.

        Self-repairing under the fixture migration: the moment a fixture is
        rewritten to call `email_customer(body=..., to=...)`, its source starts
        speaking the vocabulary and starts counting - and the two broken clauses
        go dark THERE too, rather than the gate needing an edit.
        """
        if not self.tools.get(source):
            return False
        return not self.unmapped_tools.get(source)

    def target_vocabulary_sources(self):
        return [s for s in self.sources if self.speaks_target_vocabulary(s)]

    def tools_never_reached(self, sources=None):
        reached = set()
        for name in (sources or self.sources):
            reached.update(self.tools.get(name, {}))
        return [t for t in self.tool_names if t not in reached]

    def as_dict(self):
        return {
            "objective_set_hash": self.objective_set.hash,
            "sources": list(self.sources),
            "refusals": dict(self.refusals),
            "declared_absent": dict(self.declared_absent),
            "episodes_per_source": dict(self.episode_counts),
            "target_vocabulary_sources": self.target_vocabulary_sources(),
            "dark_clauses_in_target_vocabulary": [
                {"invariant_id": cid, "state": state}
                for cid, state, _ in self.dark_clauses(self.target_vocabulary_sources())],
            "skipped_per_source": {k: v for k, v in self.skips.items() if v},
            "clauses": [
                {
                    "invariant_id": clause["id"],
                    "form": clause["form"],
                    "capability_class": clause.get("capability_class"),
                    "pooled": dict(self.pooled(clause["id"]).as_dict(),
                                   state=self.pooled(clause["id"]).state()),
                    "by_source": {
                        name: dict(cell.as_dict(), state=cell.state())
                        for name, cell in sorted(self.cells[clause["id"]].items())
                    },
                }
                for clause in self.objective_set.clauses
            ],
            "tools": {
                "target_tools": list(self.tool_names),
                "executed_events_by_source": {
                    k: dict(sorted(v.items())) for k, v in sorted(self.tools.items())},
                "never_reached_by_anything": self.tools_never_reached(),
                "unmapped_tool_names_by_source": {
                    k: dict(sorted(v.items()))
                    for k, v in sorted(self.unmapped_tools.items()) if v},
            },
        }


def load_objective_set():
    """THE FROZEN PRODUCTION ARTIFACT, never the development instance.

    `contracts/objective_set.v1.json` is the definition of breach for the run;
    `tests/golden_traces/objective_set.json` is the hand-written development
    instance the nine known-bad fixtures were built against. Measuring coverage
    of the second and reporting it as coverage of the first is the same class of
    error as measuring a breach rate against a different ruler.
    """
    from crucible.tripwire.objective_set import load_objective_set as _load
    return _load(sources.REPO / "contracts" / "objective_set.v1.json")


def target_tool_names():
    from target.refund_agent.manifest import build_manifest
    return [t["tool_fqname"].rsplit(".", 1)[-1] for t in build_manifest()["tools"]]


def _handle_map():
    from target.refund_agent.manifest import build_manifest
    return {t["tool_handle"]: t["tool_fqname"].rsplit(".", 1)[-1]
            for t in build_manifest()["tools"]}


def build_matrix(source_list=None, extra=()):
    """Run every source and return the matrix.

    A source that REFUSES is recorded as a refusal and its column is absent -
    never a column of zeros. `extra` takes `(name, episodes, skipped)` triples
    so a caller can fold in a live run's evidence bundle alongside the offline
    sources without this module knowing where the bundle came from.
    """
    objective_set = load_objective_set()
    matrix = CoverageMatrix(objective_set, target_tool_names(), _handle_map())
    for name, loader in (source_list or sources.OFFLINE_SOURCES):
        try:
            result = loader()
        except sources.SourceUnavailable as exc:
            matrix.add_refusal(name, str(exc))
            continue
        if isinstance(result, tuple):
            episodes, skipped = result
        else:
            episodes, skipped = result, []
        matrix.add_source(name, episodes, skipped)
    for name, episodes, skipped in extra:
        matrix.add_source(name, episodes, skipped)
    _declare_the_seal(matrix)
    return matrix


def _declare_the_seal(matrix):
    """The F4 holdout, named in the matrix rather than left out of it.

    Read from `corpus/F4-MANIFEST.json`, which is a MANIFEST OF COUNTS and
    carries no instance content - that file exists on this side of the boundary
    precisely so the seal can be described without being opened.
    """
    import json
    import pathlib

    path = sources.REPO / "corpus" / "F4-MANIFEST.json"
    if not path.is_file():
        matrix.declare_absent(
            "sealed_holdout",
            "corpus/F4-MANIFEST.json is missing, so this instrument cannot "
            "even say how large the sealed population is.")
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    if (sources.REPO / "corpus" / "sealed").is_dir():
        matrix.declare_absent(
            "sealed_holdout",
            "corpus/sealed EXISTS ON THIS MACHINE. The holdout is supposed to "
            "be unreadable from here; its presence is a seal defect, not a "
            "coverage opportunity, and this instrument does not read it.")
        return
    matrix.declare_absent(
        "sealed_holdout",
        "%d F4 instances, all smuggling %s, are held out behind IAM and are "
        "NOT on this machine. They are the population that exercises the "
        "clause over %s as designed. Any clause dark here whose only intended "
        "exercisers are sealed is dark FOR A DECLARED REASON, and that is a "
        "different sentence from 'nobody wrote a trace'."
        % (doc.get("instances"), ", ".join(doc.get("smuggled_arg_path") or ()),
           doc.get("episode_field_compared_against")))
