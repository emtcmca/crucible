"""bundle.py - the C6 evidence bundle, assembled from a campaign run.

WHY THIS FILE EXISTS
--------------------
`campaign.py` wrote `{summary, hashes, final_policy, rounds}`.
`contracts/evidence_bundle.schema.json` requires seventeen root keys.
**THE TWO SHAPES HAD ZERO KEYS IN COMMON.** Everything downstream of the loop -
`crucible/replay/view.py`, `crucible/replay/integrity.py`, the judge's
reproduction path, the demo - reads C6, so nothing could render a single run
this project produced. The loop worked and left no record anything could read.

Eric's framing, and it is the design brief for this module: the bundle IS the
product. "What was tested, how it was answered by the test subject, what was
found / addressed / patched. And everything in between."

    what was tested          `attacks[]`, carrying the INSTRUCTION TEXT
    how it was answered      `episodes[].episode_prefix`, the ordered ToolEvents,
                             plus `episodes[].verdict`
    what was found           `autopsies[]`, the CORONER's full C5 records
    what was addressed       `patch_proposals[]`, INCLUDING REJECTED ONES
    what was patched         `policy_chain[].rules[].dsl_text`, the rule as a
                             human reads it
    and everything between   `round_census[]`, `excluded[]`, `clause_coverage`,
                             `execution_provenance`, `cost`, `labels`

THE RULE THIS MODULE IS WRITTEN UNDER
--------------------------------------
**NO FIELD IS EVER INVENTED TO SATISFY A SCHEMA.** A bundle that validates by
fabrication is worse than no bundle, because it looks like evidence. So every
value here is one of exactly three things, and the code says which:

  MEASURED     read off the run (wall clock, token counts, verdicts, events)
  SOURCED      read out of the artifact that owns it (`corpus.model.BENIGN_TOTAL`,
               `docs/CONVENTIONS.md`'s SPINE_VERSION, the frozen target
               descriptor). Never retyped - a second copy of a value is a second
               source of truth.
  RECOMPUTED   derived again, deterministically, from recorded bytes
               (`clause_coverage` re-runs the real `Objective_Set.matches`;
               the placeholder -> assigned rule-id mapping re-parses the
               ARMORER's own accepted patch text)

Anything that is none of those is OMITTED when the schema allows it and REPORTED
as a gap. Four such gaps exist today and each is named at its site:
`channel`, `target_final_text`, `rule_id_as_proposed` in the halt case, and the
target's own token spend on a live run.

VALIDATION HAPPENS AT WRITE TIME, WITH THE READER'S OWN VALIDATOR
------------------------------------------------------------------
`validate_bundle` calls `crucible.replay.integrity.c6_validator()` - the SAME
validator the offline reader builds, with every `$ref` resolved locally so an
offline producer does not become a networked one at the first `$ref`. Building a
second validator here would be a second opinion about what C6 means, and the
producer's opinion is the one that does not matter.

`write_bundle` prints the result. A bundle that failed validation is still
WRITTEN - a rejected bundle is the most useful artifact there is when the thing
being debugged is the producer - but the failure is printed, loudly, and the
caller is told. Silently writing an invalid bundle is how a reader ends up
holding something that is not evidence and cannot tell.
"""

import json
import pathlib
import re
import time

from ..armorer.render import render_rule
from ..canon.hashing import hash_full, policy_hash as compute_policy_hash
from ..dsl import compile_rule, parse_policy

_HERE = pathlib.Path(__file__).resolve().parent
REPO = _HERE.parent.parent

BUNDLE_VERSION = 2

# ---------------------------------------------------------------------------
# The channel gap, stated once, here, rather than papered over.
#
# C6 says `channel` is "A HARNESS fact, stamped - never inferred from the
# transcript", and it is REQUIRED on every episode. NOTHING IN THIS PROJECT
# STAMPS ONE. `crucible/harness/episode.py::seal_episode` writes no `channel`
# key, `tests/golden_traces/T1..T3` carry none either, and
# `crucible.tripwire.model.Episode.channel` therefore returns None - which is
# what every episode in every run so far was actually scored with.
#
# Writing "chat" here would be inferring a channel the scorer never saw, which
# is the one thing the field's own comment forbids. So the sentinel says what
# happened. It is uppercase so it cannot be mistaken for a channel name.
#
# It changed no result: all nine clauses in `contracts/objective_set.v1.json`
# are scoped `channel: ANY`, so `_in_channel` skipped nothing. That is luck
# rather than design, and the moment one clause is channel-scoped it stops being
# luck. REPORTED to the coordinator; the fix belongs in the harness, not here.
# ---------------------------------------------------------------------------
CHANNEL_UNSTAMPED = "UNSTAMPED"

# The one C7 field with no owner in the tree. `target_descriptor()` carries the
# model binding and `FROZEN.json` carries the hashes; neither says where the
# target came from, because for this build the answer is "here". Stated as a
# path so a reader can open it, and deliberately NOT restating the
# `target_agent_hash` that sits ten lines above it in the bundle.
TARGET_SOURCE = ("target/refund_agent, authored in this repository and frozen "
                 "at D3 - see target/refund_agent/FROZEN.json")


class BundleError(RuntimeError):
    """The bundle cannot be built honestly. Raised rather than papered over."""


# ===========================================================================
# RECORDERS - the run facts nothing retains
#
# `RoundRecord` keeps `patch_ok`, `verbs_used` and `new_rule_ids`; it does not
# keep the `PatchResult`, so a REJECTED proposal's rule text exists nowhere once
# the round returns. `BudgetGovernor` keeps a COMBINED token count, so the
# input/output split the C6 `cost` block requires is discarded before it is
# seen. Neither file is this lane's to edit, and neither should be: the fix is
# to OBSERVE the seams `campaign.py` already owns.
#
# Every recorder below wraps a callable `campaign.py` constructs and injects. It
# adds no behaviour, changes no result, and each one is keyed by a value it is
# HANDED rather than by call order - `Armorer.propose` takes `round_index`, and
# the gate is handed the `RoundRecord`. Pairing by position was the alternative
# and it is the one that silently mis-attributes a patch the first time a round
# does not produce one.
# ===========================================================================

class CallMeter:
    """Wraps `call_model` and counts what the governor throws away.

    MEASURED, all of it: every field is read off the response dict
    `crucible/armorer/client.py::make_call_model` already returns
    (`input_tokens`, `output_tokens`, `thinking_tokens`, `status`).

    WHAT THIS CANNOT SEE, AND IT IS NOT A SMALL THING. The TARGET's own model
    turns do not pass through `call_model` at all - ADK owns that call and
    returns no usage metadata to us - so on a `--live` run the token totals here
    cover the RED_STRATEGIST, the CORONER and the ARMORER and NOT the target,
    which is the highest-volume role in the run. `cost.by_role` names the
    unmetered role explicitly rather than leaving the total to read as complete.

    `retries` is the same shape of gap and is handled the same way:
    `make_call_model` retries transient errors INSIDE its own loop and exposes
    no attempt count, so a 429 that was retried and then succeeded is invisible
    from out here. What IS visible is a call that came back ERROR after the
    retries were exhausted, and that is what `transport` counts. `rate_limit_429`
    counts the subset whose error text names a 429. An undercount reads exactly
    like a clean run, so this is REPORTED rather than presented as the retry
    ledger.
    """

    def __init__(self, call_model):
        self._call_model = call_model
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.thinking_tokens = 0
        self.errors = 0
        self.rate_limit_errors = 0
        self.by_role = {}

    def __bool__(self):
        # `campaign.py` passes `call_model or _refuse` in one place and
        # `call_model` (possibly None) in two others, and `None` is the offline
        # signal. A meter wrapping nothing must stay falsey or it would turn an
        # offline run into one that looks configured.
        return self._call_model is not None

    def __call__(self, **kwargs):
        if self._call_model is None:                     # pragma: no cover
            raise BundleError("CallMeter was called with no underlying model")
        response = self._call_model(**kwargs)
        self.calls += 1
        if isinstance(response, dict):
            self.input_tokens += int(response.get("input_tokens", 0) or 0)
            self.output_tokens += int(response.get("output_tokens", 0) or 0)
            self.thinking_tokens += int(response.get("thinking_tokens", 0) or 0)
            if response.get("status") == "ERROR":
                self.errors += 1
                if "429" in str(response.get("error") or ""):
                    self.rate_limit_errors += 1
        return response


class ProposalLog:
    """Wraps `Armorer.propose` and keeps the `PatchResult` per round.

    Keyed by the `round_index` the conductor passes in, so the pairing is exact
    rather than positional. This is the only place a REJECTED candidate's rule
    text survives: `Conductor._round` sets `record._candidate` back to the
    PARENT policy when the gate says REJECT, so by the time the round returns
    the rejected candidate has been dropped on the floor.
    """

    def __init__(self, armorer):
        self._armorer = armorer
        self.by_round = {}

    def propose(self, breach_record, current_policy, round_index,
                rejection_feedback=None):
        patch = self._armorer.propose(breach_record, current_policy, round_index,
                                      rejection_feedback=rejection_feedback)
        self.by_round[int(round_index)] = patch
        return patch


def gate_reports_by_round(gate):
    """`{round_index: [report, ...]}` from `RealGate.reports`.

    NO WRAPPER. A `GateLog` decorator was written here first and then deleted:
    `tests/test_campaign_gate_wiring.py` asserts that the conductor's `promote`
    hook IS a `RealGate` instance and that it exposes `promoted_by`, and that
    guard exists because `promote=lambda c, r: True` sat in `campaign.py` for
    weeks while the banner told the truth about it. A decorator would have had
    to defeat an `isinstance` check to stay green, which is weakening a gate to
    make something pass - CONVENTIONS section 8 rule 3, a stop condition.

    It was also unnecessary, which is the useful half: `RealGate.__call__`
    already stamps `round_index` on every report it appends, so the attribution
    a decorator was being built to supply was in the data all along. Grouping by
    call order would have been the wrong answer regardless - a round whose
    benign floor failed never reaches the gate, so the k-th report is not the
    k-th gate-deciding round.
    """
    out = {}
    for report in getattr(gate, "reports", None) or ():
        index = report.get("round_index")
        if index is None:                                # pragma: no cover
            continue
        out.setdefault(int(index), []).append(report)
    return out


class RoundClock:
    """Wraps `RedStrategist.propose_round` to time each round.

    A round BEGINS when the RED_STRATEGIST is asked for its attacks - that call
    is the first thing `Conductor._round` does - so the interval between one
    round's opening and the next's is exactly that round's wall clock. The last
    round is closed by `stop()` when the loop returns.

    MEASURED, with `time.monotonic_ns`, for the same reason `ts_monotonic` is
    monotonic on a ToolEvent: a wall clock that can step backwards produces a
    negative duration and a reader has no way to tell that from a bug.
    """

    def __init__(self, red):
        self._red = red
        self._marks = []

    def propose_round(self, seeds, feedback=None, n=None):
        self._marks.append(time.monotonic_ns())
        return self._red.propose_round(seeds, feedback, n)

    def stop(self):
        self._marks.append(time.monotonic_ns())

    def per_round_ms(self):
        """`{round_index: ms}` for every round that both opened and closed."""
        out = {}
        for i in range(len(self._marks) - 1):
            out[i + 1] = max(0, (self._marks[i + 1] - self._marks[i]) // 1_000_000)
        return out


# ===========================================================================
# SOURCED values
# ===========================================================================

_SPINE_RE = re.compile(r"^`?SPINE_VERSION`?:?\s*(\d+)", re.MULTILINE)


def spine_version(conventions_path=None):
    """The spine version, READ OUT of `docs/CONVENTIONS.md`.

    CONVENTIONS is the spine and it owns this number - "the coordinator changes
    the value, bumps SPINE_VERSION". There is no Python constant for it, and
    typing one here would create the second source of truth that this repository
    has been bitten by repeatedly. So it is parsed, and a file that does not
    carry it REFUSES rather than defaulting: a bundle stamped with a spine
    version nobody set is a bundle that cannot say which rules it was built
    under.
    """
    path = pathlib.Path(conventions_path or (REPO / "docs" / "CONVENTIONS.md"))
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BundleError(
            "cannot read %s, so the run manifest has no spine_version. "
            "CONVENTIONS owns that number; this module does not get to invent "
            "one. (%s)" % (path, exc))
    match = _SPINE_RE.search(text)
    if not match:
        raise BundleError(
            "%s carries no `SPINE_VERSION: <n>` line. The value is not "
            "defaulted here on purpose - a manifest stamped with a spine "
            "version nobody set cannot say which rulings it was built under."
            % path)
    return int(match.group(1))


def frozen_parameters(governor=None, attacks_per_round=6):
    """C7's `frozen_parameters`, sourced from the constants that own them.

    Every value here has an owner elsewhere in the tree and is read from it:

        round_cap             the governor's own budget
        attacks_per_round     the conductor's own setting
        dry_rounds_required   conductor.CONVERGENCE_DRY_ROUNDS
        benign_floor          corpus.model.BENIGN_TOTAL
        near_miss_floor       corpus.model.NEAR_MISS_FLOOR
        known_bad_count       crucible.tripwire.known_bad.KNOWN_BAD_IDS
        sealed_family_min     corpus.model.SEALED_FLOOR
        approval_oracle_default
                              crucible.plugin.core.APPROVAL_ORACLE_DEFAULT
        token_ceiling         the governor's own budget

    `benign_floor` carried "24/24" in three places for a day after ruling 43
    moved the suite to 26 and every suite stayed green, because nothing compared
    a literal to its owner. Deriving it is the fix.

    TWO VALUES ARE NOT READ FROM THE RUN, AND BOTH ARE SAID OUT LOUD.

    `reps_k` is 1 because THIS harness runs each attack once - `CampaignResult.
    summary()` already reports "k=1, single-sample, no stability estimate" and
    nothing in `Conductor._round` repeats an attack. It is a property of the
    loop, asserted here, not a knob.

    `spend_cap_usd` is 160: the FROZEN PROTOCOL cap from C7, which is a
    different quantity from `campaign.py --usd-cap` (default $5.00), the tighter
    per-invocation guard the governor actually enforced. C6 has no field for the
    second one. REPORTED rather than quietly conflated - a reader of this
    bundle learns the protocol cap and cannot learn this run's governor cap.
    """
    from corpus.model import BENIGN_TOTAL, NEAR_MISS_FLOOR, SEALED_FLOOR
    from ..plugin.core import APPROVAL_ORACLE_DEFAULT
    from ..tripwire.known_bad import KNOWN_BAD_IDS
    from .conductor import CONVERGENCE_DRY_ROUNDS

    budget = getattr(governor, "budget", None)
    return {
        "round_cap": int(getattr(budget, "round_cap", 6)),
        "attacks_per_round": int(attacks_per_round),
        "reps_k": 1,
        "dry_rounds_required": int(CONVERGENCE_DRY_ROUNDS),
        "benign_floor": "%d/%d" % (BENIGN_TOTAL, BENIGN_TOTAL),
        "near_miss_floor": "%d/%d" % (NEAR_MISS_FLOOR, NEAR_MISS_FLOOR),
        "known_bad_count": len(KNOWN_BAD_IDS),
        "sealed_family_min": int(SEALED_FLOOR),
        "approval_oracle_default": APPROVAL_ORACLE_DEFAULT,
        "spend_cap_usd": 160,
        "token_ceiling": int(getattr(budget, "token_cap", 40_000_000)),
    }


def target_ref(source=TARGET_SOURCE):
    """C7's `target_ref`, read off the FROZEN D3 descriptor.

    `modified_by_crucible` is `false` and C7 pins it there. It is true of the
    thing the field is about - CRUCIBLE enforces through a plugin and does not
    edit the agent, its tools or its instruction, which is what
    `target_agent_hash` freezes. It is NOT the whole story on an offline run,
    where `real_target` swaps `agent.model` for a scripted stand-in at runtime.
    That swap is recorded where a reader will actually look for it:
    `execution_provenance.components.target` and every episode's
    `model_provenance.downgraded`.
    """
    from target.refund_agent.agent import target_descriptor
    descriptor = target_descriptor()
    return {
        "target_id": descriptor["target_id"],
        "source": source,
        "modified_by_crucible": False,
        "model_id": descriptor["model"],
        "thinking_level": descriptor["thinking_level"],
    }


def sep_by_split():
    """Ruling 17's permanent split, counted from `corpus/pairs.json`.

    `corpus.sepby.split` REFUSES on an empty pair set and REFUSES at oracle
    parity, and both refusals are load-bearing: an empty set returns a healthy
    ratio computed over nothing, and at parity half the headline is a statement
    about a scripted oracle wearing the policy's name. Neither refusal is caught
    here - a bundle whose SEP-BY split cannot be counted should fail to build,
    not carry a number nobody counted.
    """
    from corpus.load import load_corpus
    from corpus.sepby import split
    counted = split(load_corpus().get("pairs") or [])
    return {"policy_separated": int(counted["policy"]),
            "approval_oracle_separated": int(counted["oracle"])}


def benign_evidence(policy):
    """`(fixture_results, v0_benign_traces)` from the real 26-fixture suite.

    RECOMPUTED, with the real Warden pieces rather than a re-implementation:
    `crucible.conductor.real_warden.load_real_benign_suite` for the converted
    fixtures and `crucible.warden.replay_trace` through L3's real engine for the
    per-fixture pass/fail. `real_warden()` itself returns only the five
    aggregate counts `Conductor` reads, so the PER-FIXTURE row this bundle needs
    does not exist until it is computed - and it is computed by the same call
    the aggregate is, so the two cannot disagree.

    `v0_benign_traces` is each fixture's legitimate tool-call trace. For an
    AUTHORED fixture the trace IS the v0 recording (`real_warden`'s docstring
    says so at length), and the conversion that stamps its seven `derived.*`
    fields happens once per process, not per round - which is exactly ruling
    11's "recorded ONCE at v0".
    """
    from ..warden import replay_trace
    from .real_warden import _l3_evaluate_call, load_real_benign_suite

    results, traces = [], []
    for fixture in load_real_benign_suite():
        ok, blocked, _surviving = replay_trace(fixture, policy, _l3_evaluate_call)
        results.append({
            "fixture_id": fixture.fixture_id,
            "near_miss": bool(fixture.near_miss),
            "passed": bool(ok),
            "blocked_capability_classes": sorted(
                c for c in (blocked or ()) if str(c).startswith("CAP_")),
        })
        traces.append({
            "fixture_id": fixture.fixture_id,
            "near_miss": bool(fixture.near_miss),
            "recorded_at": "v0",
            "events": list(fixture.raw.get("episode", {}).get("events") or ()),
        })
    return results, traces


# ===========================================================================
# The episode half - what was tested and how it was answered
# ===========================================================================

_C9_KEYS = ("verdict", "breach", "invariant_id", "objective_set_hash",
            "evidence", "target_fault")


def _verdict_c9(verdict):
    """The C9 subset of a conductor verdict dict.

    `Conductor._round` decorates the TRIPWIRE's `Verdict.to_dict()` with
    `attack_id`, `family_id` and `_episode` before storing it. C9 is
    `additionalProperties: false`, so those three are stripped here rather than
    at the source - the decoration is the conductor's, it is useful to the
    conductor, and teaching the TRIPWIRE a second output shape to suit a
    consumer is how one contract becomes two.
    """
    return {k: verdict[k] for k in _C9_KEYS if k in verdict}


def _model_provenance(live):
    """Which model produced this episode's target turns.

    C6 made this REQUIRED on 2026-08-22 because a live run reached the WRONG API
    entirely - the target picked its provider from an unhashed environment
    variable while `endpoint` sat inside the D3 freeze, so every hash-lock
    agreed and the calls went somewhere else. Nothing in the bundle could show
    it. Now the episode says who served it.

    OFFLINE, `downgraded` is TRUE and it is not a formality: `requested_model_id`
    is the frozen tier and `model_id` is the scripted stand-in that actually ran,
    so the two fields together say, per episode, that this measurement was not
    produced by the target the freeze names.
    """
    from target.refund_agent.agent import (
        TARGET_ENDPOINT, TARGET_MODEL, TARGET_PROVIDER, TARGET_THINKING_LEVEL,
    )
    if live:
        return {"role": "target", "model_id": TARGET_MODEL,
                "provider": TARGET_PROVIDER, "endpoint": TARGET_ENDPOINT,
                "thinking_level": TARGET_THINKING_LEVEL, "downgraded": False}
    return {
        "role": "target",
        "model_id": "crucible-offline-scripted-target",
        "requested_model_id": TARGET_MODEL,
        "provider": "offline_stand_in",
        "endpoint": "none - no request left this process",
        "thinking_level": TARGET_THINKING_LEVEL,
        "downgraded": True,
    }


def _episodes(rounds, *, live):
    """One C6 episode per verdict, in round then attack order.

    `target_final_text` is OPTIONAL and is OMITTED, because nothing records it:
    `seal_episode` seals EVENTS, and the target's closing prose is discarded
    when `runner.run_async` finishes. It is the human half of "how it was
    answered by the test subject" and its absence is REPORTED rather than filled
    with a summary of the tool log, which would be this module inventing the
    target's words.
    """
    out = []
    provenance = _model_provenance(live)
    for record in rounds:
        for verdict in record.verdicts:
            episode = verdict.get("_episode") or {}
            frozen = dict(episode.get("episode_frozen_context") or {})
            # `frozen_at` is a CONSTANT in C6 and it is a claim about the
            # harness, not a timestamp. It is true here: `real_target._build_core`
            # freezes the block off the seeded order record BEFORE
            # `runner.run_async` delivers the attack, so no in-episode turn can
            # move `account_holder_email`. Ruling 16 is the whole F4 seal.
            frozen["frozen_at"] = "before_first_user_turn"
            row = {
                "episode_id": episode.get("episode_id"),
                "attack_id": verdict.get("attack_id"),
                "outcome": episode.get("outcome"),
                "channel": CHANNEL_UNSTAMPED,
                "round_index": record.round_index,
                "episode_frozen_context": frozen,
                "episode_prefix": list(episode.get("events") or ()),
                "objective_set_hash": episode.get("objective_set_hash"),
                "manifest_hash": episode.get("manifest_hash"),
                "derived_schema_hash": episode.get("derived_schema_hash"),
                "policy_version": episode.get("policy_version"),
                "policy_hash": episode.get("policy_hash"),
                "model_provenance": dict(provenance),
                "verdict": _verdict_c9(verdict),
            }
            out.append(row)
    return out


def _attacks(rounds, *, generator):
    """THE ATTACK CATALOGUE, WITH THE TEXT.

    `campaign.py::_round_json` used to write
    `{k: v for k, v in a.items() if k != "instruction"}` - it stripped the one
    field a reader most wants. Eric: "We absolutely need to record generated
    attacks. The content there is at the crux of what we're doing."

    THERE IS NO LEAK RISK AND IT IS WORTH SAYING WHY, BECAUSE "RECORD THE ATTACK
    TEXT" LOOKS LIKE THE EXACT SHAPE OF A SEAL BREAK. The strings this catalogue
    carries come from `campaign.SEEDS` - six lane-authored literals in
    `campaign.py` - and from the RED_STRATEGIST's rewrite of them. The campaign
    NEVER READS `corpus/sealed/`: no import, no path, no loader, and the real
    boundary is IAM rather than the `.gitignore` entry. A varied attack is a
    surface-form rewrite of a seed that was already committed in plain sight.

    `provenance` decides whether the text is optional, and the two values mean
    genuinely different things:

      training_corpus   reproducible from the corpus at `corpus_hash`, so an id
                        suffices and copying the bytes would create a second
                        source of truth for text the freeze already owns.
      generated         EXISTS NOWHERE ELSE - not in the corpus, not on disk -
                        so if the bundle does not carry the bytes, the attack
                        that broke someone's agent is gone the moment the
                        process exits.

    `RedStrategist.vary` returns a `variation` of "none" / "model" / "fallback" /
    "governor_refused", and that field is what decides which of the two applies.
    "none" is a seed replayed VERBATIM because no model was configured;
    "fallback" and "governor_refused" are the same bytes reached by a different
    road. Only "model" produced text that exists nowhere else.

    THE SEEDS ARE STILL CARRIED WITH THEIR FULL TEXT even though `provenance` is
    `training_corpus`, because `corpus_instance_id` resolves them against
    `corpus_hash` and THEY ARE NOT IN THAT CORPUS - they are `campaign.SEEDS`.
    So the id names the seed and the bytes travel beside it, which is the only
    combination that leaves a reader able to reproduce the round.
    """
    catalogue = {}
    for record in rounds:
        for attack in record.attacks:
            aid = attack.get("attack_id")
            variation = attack.get("variation")
            row = {
                "attack_id": aid,
                "family_id": attack.get("family_id"),
                "instruction": attack.get("instruction"),
            }
            if variation == "model":
                row["provenance"] = "generated"
                row["round_index"] = record.round_index
                row["derived_from_attack_id"] = aid
                row["generator"] = dict(generator)
            else:
                row["provenance"] = "training_corpus"
                # The seed's own id IS its instance id. `campaign.SEEDS` is the
                # instance set for this harness; a corpus-backed run replaces
                # both halves and this line needs no change.
                row["corpus_instance_id"] = aid
            # An attack replayed in two rounds is ONE catalogue entry - a second
            # entry for one id makes "which text ran" a question the bundle
            # answers twice. A generated variant supersedes a seed replay,
            # because the generated bytes are the ones that exist nowhere else.
            existing = catalogue.get(aid)
            if existing is None or (existing.get("provenance") == "training_corpus"
                                    and row["provenance"] == "generated"):
                catalogue[aid] = row
    return [catalogue[k] for k in sorted(catalogue)]


def generator_ref(live, seed):
    """Which model wrote the generated attack text, and through which provider.

    Offline the RED_STRATEGIST has no model and replays its seeds verbatim, so
    nothing is generated and this block is never attached to an entry. It is
    still built - and built from `crucible.red`'s own pinned constants and the
    seed the campaign actually handed the strategist, rather than from literals
    - so a live run cannot reach for it and find prose.
    """
    from ..red.red import RED_MODEL, RED_THINKING_LEVEL
    if not live:
        return {"model_id": "none - offline, seeds replayed verbatim",
                "provider": "offline_stand_in"}
    from target.refund_agent.agent import TARGET_PROVIDER
    return {"model_id": RED_MODEL, "provider": TARGET_PROVIDER,
            "thinking_level": RED_THINKING_LEVEL,
            "seed": int(seed)}


# ===========================================================================
# The finding half - what was found, addressed and patched
# ===========================================================================

def _autopsies(rounds):
    """The CORONER's records, VERBATIM and UNPROJECTED.

    `campaign.py::_round_json` wrote `project(record.autopsy)` - the ARMORER's
    blinded projection, which strips `run_id`, `attack_id`, `objective_set_hash`,
    both manifest hashes and the human narrative. That projection exists so the
    ARMORER cannot see what it must be blind to; it is exactly the wrong thing
    to put in the run of record, where a reader needs the parts the ARMORER may
    not have. C6 `$ref`s the full C5 record, so the full record is what goes in.
    """
    return [dict(r.autopsy) for r in rounds if r.autopsy]


_PLACEHOLDER_RULE = re.compile(r"^\s*rule\s+(r_new\d+)\s*:", re.MULTILINE)


def _proposed_id_map(patch):
    """`{assigned_rule_id: placeholder_id}`, RECOMPUTED from the ARMORER's text.

    CONVENTIONS 2.6: the ARMORER never writes a rule id, because a model cannot
    compute SHA-256. It emits `r_new1` and the validator rewrites it. C6 wants
    BOTH halves recorded, which is what makes that mechanism visible to a reader
    instead of a claim in a doc - and `Validator.validate_patch` returns only
    the rewritten half.

    So the mapping is derived again rather than guessed: re-parse the accepted
    patch text with L3's real parser and run L3's real `compile_rule` over each
    parsed rule. `rule_id` is content-addressed, so this lands on exactly the id
    the validator assigned - it is the same function, not a lookalike. Parsing
    is pure and offline; no model is involved.

    Returns `{}` when the text cannot be re-parsed. That is not expected - the
    text parsed once already, in `Armorer._try` - and an empty map simply means
    `rule_id_as_proposed` is omitted, which is what the OPTIONAL field is for.
    Guessing a pairing by ordinal position was the alternative and it is wrong
    silently.
    """
    text = getattr(patch, "patch_text", "") or ""
    if not _PLACEHOLDER_RULE.search(text):
        return {}
    try:
        parsed = parse_policy(text)
    except Exception:                                    # pragma: no cover
        return {}
    out = {}
    for rule in parsed.rules:
        try:
            out[compile_rule(rule)["rule_id"]] = rule.rule_id
        except Exception:                                # pragma: no cover
            continue
    return out


def _rules_of(policy):
    payload = (policy or {}).get("hashed_payload", policy or {})
    return list(payload.get("rules") or ())


def _patch_proposals(rounds, proposals, run_id):
    """What was addressed - INCLUDING WHAT WAS REFUSED.

    A rejected proposal exists in no other artifact at all. `Conductor._round`
    puts `record._candidate` back to the parent policy on REJECT, so without
    `ProposalLog` the rule the ARMORER wrote and the gate turned down is gone.
    That is the half of the engagement a reader most needs when the question is
    "why did this run not converge".

    `verbs` is `PatchResult.verbs_used` and C6 requires at least one, so a patch
    that parsed to no rule at all produces no proposal row. `rules` is the same:
    a proposal with no rule is not a proposal.

    `autopsy_id` is the provenance citation G6 requires and the only join from
    "here is what was found" to "here is what was done about it". A round with a
    patch always has an autopsy - `Conductor._round` calls the CORONER first and
    only then the ARMORER - so a missing one is a defect, not a shrug, and it
    drops the row rather than emitting a fabricated id.
    """
    out = []
    for record in rounds:
        patch = proposals.get(record.round_index)
        if patch is None or not getattr(patch, "ok", False):
            continue
        autopsy_id = (record.autopsy or {}).get("autopsy_id")
        if not autopsy_id:                               # pragma: no cover
            continue
        assigned_to_placeholder = _proposed_id_map(patch)
        by_id = {r["rule_id"]: r for r in (patch.hashed_payload or {}).get("rules", [])}
        rules = []
        for rule_id in patch.new_rule_ids:
            stored = by_id.get(rule_id)
            if stored is None:                           # pragma: no cover
                continue
            row = {"rule_id_assigned": rule_id,
                   "dsl_text": render_rule(stored)}
            placeholder = assigned_to_placeholder.get(rule_id)
            if placeholder:
                row["rule_id_as_proposed"] = placeholder
            rules.append(row)
        verbs = sorted(set(patch.verbs_used or ()))
        if not rules or not verbs:
            continue
        decision = record.gate_decision
        proposal = {
            "proposal_id": "pp_%s_r%02d" % (_id_slug(run_id), record.round_index),
            "round_index": record.round_index,
            "autopsy_id": autopsy_id,
            "verbs": verbs,
            "rules": rules,
            "accepted": decision == "PROMOTE",
            "repaired": bool(patch.repaired),
            "validator_result": (
                "ACCEPT after %d attempt(s); placeholder rule ids rewritten "
                "from the canonical rule bytes (CONVENTIONS 2.6)"
                % len(patch.attempts or ())),
        }
        if record.benign_total is not None:
            proposal["warden_result"] = (
                "%s/%s benign fixtures replayed clean"
                % (record.benign_passed, record.benign_total))
        if decision == "REJECT":
            proposal["rejected_reason"] = _rejection_reason(record)
        out.append(proposal)
    return out


def _rejection_reason(record):
    feedback = record.rejection_feedback or {}
    failures = feedback.get("benign_failures")
    if failures:
        return ("%d benign fixture(s) lost, in capability class(es) %s. G3 is "
                "`passed == total`; a candidate that scores zero breaches by "
                "removing the capability is the failure the benign floor exists "
                "to catch."
                % (failures, ", ".join(feedback.get("classes") or ()) or "-"))
    return ("the benign floor held and the GATE refused the promotion. Its "
            "per-assertion findings are in gate_decisions[].criteria for this "
            "round.")


def _id_slug(text):
    """A `[a-z0-9_]` slug, for the id patterns C6 pins on proposals and gate
    decisions. Lossy on purpose and never used as a key - the round index is
    what makes these unique."""
    return re.sub(r"[^a-z0-9_]+", "", str(text).lower().replace("-", "_")) or "run"


def _gate_decisions(rounds, gate, run_id):
    """One decision per round that reached a decision, with its per-gate results.

    `criteria` is an OPEN object in C6 and it carries the gate's own findings
    when the gate was reached. A round whose benign floor failed never called
    the gate at all, so there are no findings to carry and the criteria say
    exactly that rather than reporting an empty pass.

    The field is `known_bad_all_expected`, never `known_bad_all_failed`: "9/9
    still failing" is FALSE PHRASING and fails on KB8 by design. It is not
    written at all here, because this campaign does not run the known-bad suite
    (`real_warden`'s docstring says so) and a field claiming a check that never
    ran is worse than its absence.
    """
    out = []
    by_round = gate_reports_by_round(gate)
    for record in rounds:
        if not record.gate_decision:
            continue
        logged = by_round.get(record.round_index)
        criteria = {
            "benign_floor": {"passed": record.benign_passed,
                             "total": record.benign_total,
                             "gate": "G3, `passed == total`"},
            "gate_reached": bool(logged),
        }
        if logged:
            criteria["findings"] = [f for report in logged
                                    for f in report.get("findings", ())]
        else:
            criteria["why_not_reached"] = (
                "the benign floor did not hold, so Conductor._round never "
                "called the gate. No promotion assertion was evaluated.")
        out.append({
            "gate_decision_id": "gd_%s_r%02d" % (_id_slug(run_id),
                                                 record.round_index),
            "round_index": record.round_index,
            "decision": record.gate_decision,
            "criteria": criteria,
        })
    return out


def _policy_chain(run_id, versions):
    """version -> the four hashes and THE RULE TEXT.

    `versions` is `[(version_number, policy_document), ...]` in ascending order,
    starting at the seed at v0.

    THE RULE TEXT IS THE POINT. A chain entry carrying four hashes and a
    `gcs_uri` into a bucket the reader cannot open is not an answer to "what
    does the policy say" - it is a forwarding address, and a customer holding
    this bundle could not read one rule of the policy their own agent runs
    under. `render_rule` is the same renderer the round-trip test parses back,
    so the text a reader sees is the text L3's parser reads.

    `policy_hash_full` is the 64-char digest and it is REQUIRED: the lineage
    step is `SHA256(prev || ':' || policy_hash_full || ':' || uint32_be(n))`
    and it takes the full hash, so a chain carrying only the 16-char truncation
    CANNOT BE RECOMPUTED FROM A BUNDLE AT ALL. That is the difference between a
    judge verifying the lineage and a judge reading it.

    `parent_hash` is the PREVIOUS VERSION'S `policy_hash`, which is what
    `crucible/replay/integrity.py::_check_policy_chain` cross-checks and what
    `crucible/ledger/lineage.py::verify` documents. Note that
    `Conductor._round` writes a candidate's `lineage.parent_hash` from the
    PARENT'S `lineage_hash` instead, and stamps `lineage_hash` as sixteen
    zeroes because the real link is computed at promotion time. Those two
    fields are therefore NOT read off the candidate here; they are computed
    from the actual sequence of policies with `crucible.ledger.lineage`, which
    is the module that owns the formula. The disagreement is REPORTED, not
    silently reconciled.
    """
    from ..ledger import lineage

    entries = []
    full = []
    for _version, document in versions:
        payload = (document or {}).get("hashed_payload", document or {})
        full.append(hash_full(payload))
    links = lineage.build(run_id, full[1:])
    genesis = links[0][2]

    previous_short = None
    for i, (version, document) in enumerate(versions):
        payload = (document or {}).get("hashed_payload", document or {})
        provenance = (document or {}).get("provenance") or {}
        short = compute_policy_hash(payload)
        rules = []
        for stored in _rules_of(document):
            origin = stored.get("origin")
            if origin is None:
                origin = (provenance.get(stored["rule_id"]) or {}).get("origin")
            row = {"rule_id": stored["rule_id"],
                   "verb": stored["verb"],
                   "dsl_text": render_rule(stored, origin)}
            capability = (stored.get("match") or {}).get("capability_class")
            if capability:
                row["capability_class"] = capability
            if origin:
                # RULING 38: the CLASS only - `armorer`, never `armorer:3`.
                # The round lives in `origin_round`.
                row["origin"] = str(origin).split(":", 1)[0]
            entries_round = str(origin or "").split(":", 1)
            if len(entries_round) == 2 and entries_round[1].isdigit():
                row["origin_round"] = int(entries_round[1])
            rules.append(row)
        entries.append({
            "version": int(version),
            "policy_hash": short,
            "parent_hash": previous_short or "0" * 16,
            "lineage_hash": links[i][2] if i < len(links) else genesis,
            "policy_hash_full": full[i],
            "rules": rules,
        })
        previous_short = short
    return entries


# ===========================================================================
# The denominators - the half that decides whether any rate means anything
# ===========================================================================

def _excluded_rows(record):
    """Every episode this round dropped from the denominator, BY INSTANCE ID.

    `measurement-spec.md` 5.1 requires the ids, not the count. A live run on
    2026-08-22 recorded 36 target faults and named NOT ONE OF THEM, which is the
    exact shape by which flakiness turns into apparent hardening: the
    denominator shrinks, the rate improves, and nothing says which instances
    left.

    The two reasons are kept apart because they mean different things.
    TARGET_FAULT is a measurement that belongs outside the denominator - a crash
    is neither a breach nor a repelled attack, and counting it as the latter
    renders a fragile target as a hardened one. INVALID is the ABSENCE of a
    measurement - the instrument could not rule. `RoundRecord.scorable` strips
    both, so both are named.
    """
    rows = []
    for verdict in record.verdicts:
        if verdict.get("target_fault"):
            reason, detail = "target_fault", (
                "the target raised while the episode was being driven. Neither "
                "breach nor non-breach: removed from the denominator by "
                "RoundRecord.scorable and named here.")
        elif verdict.get("verdict") == "INVALID":
            reason, detail = "invalid_verdict", (
                "the TRIPWIRE could not rule on this episode, so it answered no "
                "question. INVALID is the absence of a measurement, not a clean "
                "result.")
        else:
            continue
        episode = verdict.get("_episode") or {}
        row = {"instance_id": verdict.get("attack_id") or "<unattributed>",
               "round_index": record.round_index,
               "reason": reason,
               "detail": detail}
        if episode.get("episode_id"):
            row["episode_id"] = episode["episode_id"]
        rows.append(row)
    return rows


def _round_census(rounds, per_round_ms):
    """THE DENOMINATORS, PER ROUND. `attempted == scorable + excluded`.

    `attempted` is the number of episodes actually RUN, not the number of
    attacks selected - `Conductor._round` runs exactly one episode per selected
    attack, so the two agree today, and reading the verdict list is the one that
    stays true if they ever stop agreeing.

    `outcome` is `RoundRecord.outcome`, carried VERBATIM. It is never rewritten
    to INCOMPLETE here even when exclusions pass the 5% ceiling
    `measurement-spec.md` 5.1 sets, and that is deliberate: the round outcome is
    the conductor's ruling and a bundle that disagrees with the loop it records
    is a second source of truth about what happened. INCOMPLETE is a legal
    `RoundRecord.outcome` that no code path can currently produce, because the
    ceiling has no owner. `crucible/replay/integrity.py::_check_exclusions`
    reports the mismatch, which is the correct place for it to surface.
    REPORTED to the coordinator as an open seam.
    """
    census = []
    for record in rounds:
        attempted = len(record.verdicts)
        scorable = len(record.scorable)
        row = {
            "round_index": record.round_index,
            "attempted": attempted,
            "scorable": scorable,
            "excluded": attempted - scorable,
            "target_faults": record.target_faults,
            "invalid": record.invalid,
            "breaches": len(record.breaches),
            "outcome": record.outcome,
        }
        if record.round_index in per_round_ms:
            row["wall_clock_ms"] = int(per_round_ms[record.round_index])
        census.append(row)
    return census


def _clause_coverage(objective_set, rounds):
    """WHICH CLAUSES OF THE DEFINITION OF BREACH WERE ACTUALLY REACHED.

    The Objective Set IS the definition of breach, so a breach rate measures
    whatever share of it the corpus managed to touch. If three of nine clauses
    never fire, the number measures a third of the definition while being
    reported as the whole, and nothing else in the bundle can say so. The rows
    that matter are the ones reading `episodes_fired: 0`.

    RECOMPUTED, and it has to be. `Verdict.to_dict()` carries ONE
    `invariant_id` - the first clause to fire, in authored order - while
    `Objective_Set.matches` returns ALL of them. Counting from the verdicts
    alone would undercount every clause that fired behind another one. So this
    calls the real `matches()` again over the recorded events, which is pure and
    deterministic and is the same function the TRIPWIRE ruled with. It is
    therefore always a superset of what the verdicts cite, which is what
    `_check_clause_coverage`'s cross-check requires.

    An episode the evaluator refused to score is SKIPPED rather than counted as
    a non-firing one: an unscoreable episode says nothing about coverage, and
    folding it in as a zero would make an instrument failure look like a clause
    the corpus never reached.
    """
    from ..tripwire.model import Episode
    from ..tripwire.objective_set import matches

    fired_counts, first_round = {}, {}
    for clause in objective_set.clauses:
        fired_counts[clause["id"]] = 0

    for record in rounds:
        for verdict in record.verdicts:
            if verdict.get("verdict") == "INVALID":
                continue
            raw = verdict.get("_episode") or {}
            try:
                episode = Episode.from_dict(raw)
                fired, _evidence = matches(objective_set, episode.events,
                                           episode.channel,
                                           episode.episode_context)
            except Exception:                            # pragma: no cover
                continue
            for clause_id in fired:
                fired_counts[clause_id] = fired_counts.get(clause_id, 0) + 1
                first_round.setdefault(clause_id, record.round_index)

    clauses = []
    for clause in objective_set.clauses:
        row = {"invariant_id": clause["id"],
               "form": clause["form"],
               "episodes_fired": fired_counts.get(clause["id"], 0)}
        if clause["id"] in first_round:
            row["first_fired_round"] = first_round[clause["id"]]
        clauses.append(row)
    return {"objective_set_hash": objective_set.hash, "clauses": clauses}


# ===========================================================================
# Cost, provenance, labels
# ===========================================================================

def _cost(meter, wall_clock_ms):
    """In TOKENS, deliberately. Dollars are tokens times a price sheet that
    moves, so a stored dollar figure is a number that goes wrong while sitting
    still - which is why `usd_estimate_minor` is optional and is not written.

    `wall_clock_ms` is MEASURED around the whole loop. "Six rounds" says nothing
    about whether this is a coffee break or an afternoon, and a harness a
    customer is deciding whether to run against their own agent is bought or
    refused on that number.

    `by_role` is an OPEN object in C6 and it is used here to say what the totals
    DO NOT COVER. On a live run the TARGET's own model turns never pass through
    `call_model` - ADK owns that call and hands back no usage - so the totals
    above cover three roles and omit the highest-volume one. A total that reads
    as complete and is not is the failure this whole file is written against, so
    the unmetered role is named in the same object as the metered ones.
    """
    metered = ["red_strategist", "coroner", "armorer"]
    by_role = {
        "_metered_roles": metered,
        "_unmetered_roles": ["target"],
        "_why": ("the target's turns are driven by ADK, which returns no usage "
                 "metadata to this process, so input_tokens/output_tokens above "
                 "cover the three roles that call crucible.armorer.client and "
                 "NOT the target. Reported rather than absorbed."),
        "thinking_tokens": int(meter.thinking_tokens) if meter else 0,
    }
    return {
        "input_tokens": int(meter.input_tokens) if meter else 0,
        "output_tokens": int(meter.output_tokens) if meter else 0,
        "wall_clock_ms": int(wall_clock_ms),
        "retries": {
            # OBSERVABLE ONLY. `make_call_model` retries transient errors inside
            # its own loop and exposes no attempt count, so a 429 that was
            # retried and then SUCCEEDED is invisible from out here. These count
            # calls that came back ERROR after the retries were exhausted. An
            # undercount reads exactly like a clean run, which is why it is said
            # here rather than left to be inferred.
            "rate_limit_429": int(meter.rate_limit_errors) if meter else 0,
            "transport": int(meter.errors - meter.rate_limit_errors) if meter else 0,
            "total": int(meter.errors) if meter else 0,
        },
        "by_role": by_role,
    }


def _execution_provenance(*, live, meter, gate_summary, rounds):
    """WHICH COMPONENTS WERE REAL AND WHICH WERE STAND-INS.

    A BUNDLE FROM AN OFFLINE RUN MUST BE STRUCTURALLY IMPOSSIBLE TO MISTAKE FOR
    A LIVE ONE. Everything else in a stand-in bundle - the hash-locks, the
    frozen parameters, the census, the chain - is byte-identical IN SHAPE to a
    live one, so without this block the two are told apart only by knowing which
    command was typed, and the terminal banner that said so has scrolled away.

    ALL SEVEN COMPONENTS, NAMED, EVERY TIME. A partial list would let the one
    component that was a stand-in be the one nobody mentioned.

    THE TARGET IS `stand_in` OFFLINE AND THAT IS NOT A DEMOTION OF THE WIRING.
    The agent, its eight tools, `CruciblePlugin`, `EnforcementCore`, the policy
    engine, the ledger and the seal are all real and all exercised. What is
    scripted is the MODEL, and a scripted model is not persuadable - so an
    offline run measures ENFORCEMENT and measures NOTHING about susceptibility
    to persuasion. A reader scanning the `implementation` column must not see
    `real` beside a target that could not have been talked into anything, so the
    column says `stand_in` and the `detail` says precisely which half was which.

    `g7_g8_exercised` is taken from `gate_summary`, which derives it from the
    gate's own FINDINGS and never from the `--live` flag - a live run that
    halted before the first candidate exercised them exactly as little as an
    offline one did.
    """
    target_detail = (
        "target/refund_agent driven through ADK on its pinned live binding; "
        "every episode sealed by crucible.harness.episode.seal_episode"
        if live else
        "THE MODEL IS SCRIPTED (campaign.build_offline_target_model): a fixed "
        "per-family tool sequence. The agent, its eight tools, CruciblePlugin, "
        "EnforcementCore, the policy engine, the ledger and the seal are all "
        "real and all exercised - but a scripted model is not persuadable, so "
        "this run measures ENFORCEMENT and measures nothing about persuasion.")
    model_note = ("real models on their pinned bindings" if live else
                  "NO MODEL CONFIGURED. The RED_STRATEGIST replays its seeds "
                  "verbatim, the CORONER writes no narrative, and the ARMORER "
                  "is handed a refusal stub so the run halts on "
                  "ARMORER_EXHAUSTED rather than on a canned patch.")
    exercised = bool(gate_summary.get("g7_g8_exercised"))
    if exercised:
        detail = ("G7 (a/b/b2/c) and G8 were evaluated against live GCP at %d "
                  "candidate(s). Read from the gate's own findings, not from "
                  "the --live flag." % gate_summary.get("calls", 0))
    elif gate_summary.get("cloud_assertions") == "SKIPPED_OFFLINE":
        detail = ("the gate was built with skip_cloud=True (no --live), so it "
                  "made no gcloud call. G7/G8 evaluated nothing and NO G7 OR G8 "
                  "CLAIM MAY BE MADE FROM THIS BUNDLE.")
    else:
        detail = ("no candidate ever reached the gate in this run, so it "
                  "evaluated nothing. A --live flag does not exercise a gate "
                  "the loop never called.")

    return {
        "mode": "live" if live else "offline_stand_in",
        "components": {
            "target": {"implementation": "real" if live else "stand_in",
                       "detail": target_detail},
            "red_strategist": {"implementation": "real" if live else "stand_in",
                               "detail": model_note},
            "tripwire": {"implementation": "real",
                         "detail": "Objective_Set.matches over the ordered "
                                   "TOOL_EXECUTED list. Pure code, no model, "
                                   "never reads a policy verdict."},
            "coroner": {"implementation": "real" if live else "stand_in",
                        "detail": model_note},
            "armorer": {"implementation": "real" if live else "stand_in",
                        "detail": model_note},
            "warden": {"implementation": "real",
                       "detail": "the 26-fixture benign suite with its 14 "
                                 "near-misses, replayed through L3's real "
                                 "policy engine."},
            "gate": {"implementation": "real",
                     "detail": "%s (%s). %s"
                               % (gate_summary.get("implementation"),
                                  gate_summary.get("cloud_assertions"),
                                  gate_summary.get("policy_store"))},
        },
        "g7_g8_exercised": exercised,
        "g7_g8_detail": detail,
        # Metered model calls. On a live run this EXCLUDES the target's own
        # turns, which ADK makes directly - see `_cost`. The contradiction the
        # reader checks (`mode == live` with zero calls) still holds, because
        # three roles firing on a live run cannot total zero.
        "model_calls": int(meter.calls) if meter else 0,
    }


def _labels(*, bundle, live, locks, gate_summary, rounds):
    """THE FIVE SENTENCES THAT TRAVEL WITH EVERY FIGURE FROM THIS RUN.

    Until 2026-08-22 these were string literals inside
    `crucible/replay/view.py`, so a bundle pasted into a slide, mailed to a
    customer or opened in a text editor arrived STRIPPED OF EVERY CAVEAT WHILE
    KEEPING EVERY NUMBER. That is the one failure this project must never allow
    and it was the default.

    Each label that describes a value in this bundle is COMPUTED FROM that
    value - the k from `frozen_parameters.reps_k`, the split from
    `sep_by_split`, the tier from `target_ref.model_id`, the regression bound
    from the benign fixture results - because a label free to disagree with its
    own bundle is worse than a missing one: it is a caveat a reader will
    believe. `crucible/replay/integrity.py::_check_labels` cross-checks all
    four.
    """
    from ..replay.view import regression_upper_bound

    manifest = bundle["run_manifest"]
    reps_k = manifest["frozen_parameters"]["reps_k"]
    split = bundle["sep_by_split"]
    model_id = manifest["target_ref"]["model_id"]
    thinking = manifest["target_ref"]["thinking_level"]

    results = bundle["fixture_results"]
    failures = sum(1 for r in results if r.get("passed") is False)
    bound = regression_upper_bound(failures, len(results))
    if bound is None:
        benign = ("%d of %d benign fixtures failed. The rule of three bounds an "
                  "UNOBSERVED rate and does not apply once something has been "
                  "observed, so no bound is stated."
                  % (failures, len(results)))
    else:
        benign = ("0 of %d benign fixtures failed, which bounds the true "
                  "regression rate at ~%.1f%% at 95%% confidence. It is a bound "
                  "on what was NOT SEEN. NEVER 'no legitimate behavior was "
                  "lost'." % (len(results), bound))

    tier = ("%s at thinking_level=%s, the tier frozen at D3. A weaker target is "
            "easier to attack, which inflates the v0 baseline and flatters the "
            "whole curve, so the tier is named every time the numbers are "
            "reported." % (model_id, thinking))
    if not live:
        tier += (" THIS RUN DID NOT USE IT: the target was driven by a scripted "
                 "offline model, so no rate here measures persuasion.")

    trust = ("the builder holds project Owner, and no control in this system "
             "defends against him. ")
    if gate_summary.get("g7_g8_exercised"):
        trust += ("G7 (seal integrity) and G8 (non-self-approval) were "
                  "evaluated against live IAM in this run; a PASS on an IAM "
                  "document is a snapshot, not a guarantee.")
    else:
        trust += ("G7 and G8 were NOT EXERCISED in this run, so nothing here "
                  "measures seal integrity or non-self-approval and no G7 or "
                  "G8 claim may be made from this bundle.")
    unfrozen = locks.unfrozen
    if unfrozen:
        trust += (" %s carry no dated freeze record, so this run cannot "
                  "evidence that those artifacts were pinned before the first "
                  "measurement." % ", ".join(unfrozen))

    del rounds
    return {
        "k": ("k = %d: single-sample, no stability estimate. Breach semantics "
              "is any-of-k, so any rate from this run is written \"ASR "
              "(any-of-%d)\"." % (reps_k, reps_k)),
        "sep_by_split": (
            "%d policy-separated / %d APPROVAL_ORACLE-separated. A suite the "
            "APPROVAL_ORACLE separates produces IDENTICAL headline numbers to "
            "one the policy separates, and only this ratio tells them apart."
            % (split["policy_separated"], split["approval_oracle_separated"])),
        "target_tier": tier,
        "benign_regression": benign,
        "trust_root": trust,
    }


# ===========================================================================
# The assembly
# ===========================================================================

def build_bundle(result, *, run_id, created_at, locks, objective_set,
                 seed_policy, live, gate_summary, recorders,
                 wall_clock_ms, red_seed, target_source=TARGET_SOURCE):
    """A C6-conformant evidence bundle from one campaign run.

    `result` is a `CampaignResult`, or `None` when the gate raised
    `GateRunInvalid` / `GateHalt` and the loop never returned one. THE HALT PATH
    PRODUCES A C6 BUNDLE TOO, and that is not symmetry for its own sake: a
    bundle that only exists on the happy path is missing exactly when a reader
    most needs it. A RUN INVALID bundle still carries the hash-locks, the benign
    floor, the SEP-BY split, the clause table and every label - it carries no
    episodes, because there were none.
    """
    rounds = list(getattr(result, "rounds", None) or ())
    final_policy = getattr(result, "final_policy", None) or seed_policy
    per_round_ms = recorders.clock.per_round_ms() if recorders.clock else {}

    fixture_results, benign_traces = benign_evidence(final_policy)

    bundle = {
        "bundle_version": BUNDLE_VERSION,
        "run_manifest": {
            "run_id": run_id,
            "spine_version": spine_version(),
            "created_at": created_at,
            "hash_locks": {k: locks.values[k] for k in sorted(locks.values)},
            "frozen_parameters": frozen_parameters(recorders.governor),
            "target_ref": target_ref(target_source),
        },
        "episodes": _episodes(rounds, live=live),
        "policy_chain": _policy_chain(run_id, _versions(seed_policy, rounds)),
        "gate_decisions": _gate_decisions(rounds, recorders.gate, run_id),
        "fixture_results": fixture_results,
        "v0_benign_traces": benign_traces,
        "cost": _cost(recorders.meter, wall_clock_ms),
        "sep_by_split": sep_by_split(),
        "attacks": _attacks(rounds, generator=generator_ref(live, red_seed)),
        "autopsies": _autopsies(rounds),
        "patch_proposals": _patch_proposals(
            rounds,
            recorders.proposals.by_round if recorders.proposals else {},
            run_id),
        "clause_coverage": _clause_coverage(objective_set, rounds),
        "excluded": [row for record in rounds for row in _excluded_rows(record)],
        "round_census": _round_census(rounds, per_round_ms),
        "execution_provenance": _execution_provenance(
            live=live, meter=recorders.meter, gate_summary=gate_summary,
            rounds=rounds),
    }
    bundle["labels"] = _labels(bundle=bundle, live=live, locks=locks,
                               gate_summary=gate_summary, rounds=rounds)
    return bundle


def _versions(seed_policy, rounds):
    """`[(version, document), ...]`, seed first, then every PROMOTED candidate.

    A rejected candidate is NOT a policy version and does not belong in the
    chain - it belongs in `patch_proposals`, which is where a reader looks for
    what was refused. `Conductor._round` leaves `record._candidate` holding the
    promoted document on PROMOTE and the parent policy otherwise, so a round
    with any other gate decision contributes nothing here.
    """
    versions = [((seed_policy or {}).get("lineage", {}).get("version", 0),
                 seed_policy)]
    for record in rounds:
        if record.gate_decision != "PROMOTE":
            continue
        candidate = getattr(record, "_candidate", None)
        if not candidate:                                # pragma: no cover
            continue
        versions.append(((candidate.get("lineage") or {}).get("version"),
                         candidate))
    return versions


class Recorders:
    """The four observers `campaign.py` installs, in one object.

    Grouped so `build_bundle`'s signature does not grow a parameter every time
    the loop learns to record one more thing, and so `campaign.py` has a single
    place that says what is being watched.
    """

    __slots__ = ("meter", "proposals", "gate", "clock", "governor")

    def __init__(self, *, meter=None, proposals=None, gate=None, clock=None,
                 governor=None):
        self.meter = meter
        self.proposals = proposals
        self.gate = gate
        self.clock = clock
        self.governor = governor


# ===========================================================================
# Validation and the write
# ===========================================================================

def validate_bundle(bundle):
    """Errors against the REAL C6 contract, as a list of readable strings.

    Uses `crucible.replay.integrity.c6_validator()` - the same validator the
    offline reader builds, with every `$ref` resolved from `contracts/` rather
    than fetched. Building a second validator here would be a second opinion
    about what C6 means, and the producer's opinion is the one that does not
    count.
    """
    from ..replay.integrity import c6_validator
    validator = c6_validator()
    out = []
    for error in sorted(validator.iter_errors(bundle),
                        key=lambda e: list(e.path)):
        where = "$" + "".join("[%r]" % p for p in error.path)
        out.append("%s: %s" % (where, error.message))
    return out


def write_bundle(bundle, path):
    """Write, then say out loud whether what was written is evidence.

    Returns `(errors, path)`. AN INVALID BUNDLE IS STILL WRITTEN - when the
    thing being debugged is the producer, the rejected document is the only
    useful artifact there is - but the caller is handed the errors and the
    banner is unmissable. A producer that wrote an invalid bundle quietly would
    hand a reader something that is not evidence and cannot say so.

    TWO VERDICTS ARE PRINTED, NOT ONE, AND THE SECOND IS THE ONE THAT DECIDES
    WHETHER THE DEMO CAN RENDER.

      C6 VALIDATION   the schema. Every required field present and well-formed.
      OFFLINE READER  `crucible.replay.integrity.verify_bundle` - the same
                      instrument `python -m crucible.replay` runs before it
                      renders anything, and a much stricter one. It RECOMPUTES
                      the canonical form (proving the document carries no float,
                      no null, no duplicate key - the four ways a payload can be
                      un-hashable while looking like good JSON), cross-checks
                      every episode stamp against the manifest, checks the chain
                      links, and checks each label against the value it
                      describes.

    The reader FAILS CLOSED: one defect and it renders nothing. So a producer
    that printed only the schema verdict would report PASS on a bundle the demo
    cannot open, which is the exact shape of a check that looks green while the
    thing it is checking is broken.
    """
    from ..replay.integrity import verify_bundle

    errors = validate_bundle(bundle)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(bundle, handle, indent=2, default=str, sort_keys=False)
    print("  evidence bundle (C6, THE RUN OF RECORD) -> %s" % path)
    if errors:
        print("  C6 VALIDATION: FAILED, %d error(s). THIS FILE IS NOT EVIDENCE."
              % len(errors))
        for line in errors[:8]:
            print("    %s" % line)
        if len(errors) > 8:
            # CONVENTIONS section 8 rule 9 - log the drop. Silent truncation
            # reads as "that was all of them".
            print("    ... %d further error(s) not listed" % (len(errors) - 8))
        return errors, path

    print("  C6 VALIDATION: PASS. Validates against "
          "contracts/evidence_bundle.schema.json (%d root keys, %d episode(s), "
          "%d attack(s) with text, %d autopsy(ies), %d proposal(s))."
          % (len(bundle), len(bundle["episodes"]), len(bundle["attacks"]),
             len(bundle["autopsies"]), len(bundle["patch_proposals"])))

    report = verify_bundle(bundle)
    passed = sum(1 for row in report.rows if row.status == "OK")
    if report.ok:
        print("  OFFLINE READER: ACCEPTS. %d/%d integrity checks OK; canonical "
              "sha256 %s. `python -m crucible.replay <file>` renders this."
              % (passed, len(report.rows), (report.digest or "-")[:16]))
    else:
        print("  OFFLINE READER: REJECTS, %d defect(s). %d/%d checks OK. THE "
              "SCHEMA IS SATISFIED AND THE VIEWER WILL RENDER NOTHING - it "
              "fails closed, because a bundle that renders while missing what "
              "makes it meaningful is worse than one that fails to open."
              % (len(report.defects), passed, len(report.rows)))
        for defect in report.defects[:6]:
            print("    %s at %s: %s" % (defect.code, defect.where,
                                        str(defect.detail)[:150]))
        if len(report.defects) > 6:
            print("    ... %d further defect(s) not listed"
                  % (len(report.defects) - 6))
    return errors, path
