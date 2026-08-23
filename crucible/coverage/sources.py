"""sources.py - every place a scoreable trace can come from, normalised once.

WHY THE SOURCES ARE KEPT APART AND NEVER POOLED INTO ONE NUMBER

"The corpus exercises seven of nine clauses" and "a hand-written fixture
exercises the eighth" are different sentences about the harness, and only one of
them supports a published breach rate. A clause whose ONLY exerciser is a
fixture somebody wrote to make the evaluator light up is not evidence that the
corpus can reach it, and pooling the two makes that distinction unrecoverable
from the number. So a `SourceEpisode` always carries the source it came from and
the matrix keeps a column per source.

THE REFUSAL, WHICH IS THE POINT OF THIS FILE RATHER THAN A DETAIL OF IT
-----------------------------------------------------------------------
`pathlib.Path("does/not/exist").glob("*.json")` RETURNS AN EMPTY ITERATOR. It
does not raise. A loader written the obvious way therefore reports "zero traces
from this source", the matrix prints a clean-looking zero, and the reader
concludes the corpus never reaches a clause when in fact the instrument never
looked. That exact behaviour, in this repo, once produced a security check that
reported no leaks having compared against zero signals.

So every loader here calls `_require_dir` FIRST and raises `SourceUnavailable`
when the directory is absent, and `_require_files` raises when the directory
exists and holds nothing matching. Neither is a zero. `build_matrix` collects
the refusals and the gate fails on them, so a moved directory shows up as a
BROKEN INSTRUMENT rather than as an honest finding about coverage.

WHAT SHAPE EACH SOURCE IS IN, BECAUSE THERE ARE TWO AND THEY ARE NOT INTERCHANGEABLE
------------------------------------------------------------------------------------
  WIRE shape       `{"episode": {"events": [C1 ToolEvent, ...],
                    "episode_frozen_context": {...}}}`. Already stamped, already
                   paired TOOL_ATTEMPT/TOOL_EXECUTED. `tests/golden_traces/**`.
  AUTHORING shape  `{"slug", "trace", "scenario", "approver"}`. The corpus
                   instance format (`corpus/schema.py`, `fixtures/benign/
                   FORMAT.md`). `derived.*` is NOT stamped on it.

The authoring->wire conversion is `crucible.conductor.real_warden._convert_fixture`
and this module IMPORTS it rather than writing a second one. That function stamps
the seven `derived.*` fields through the real `DerivedCompute` arithmetic against
the real `target.refund_agent.manifest` tool map. A second converter here would be
a second source of truth for what an episode looks like, and the clause that reads
`derived.subject_verified_in_episode` would then be measured against a projection
of the corpus that no other component agrees with.
"""

import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent.parent


class SourceUnavailable(RuntimeError):
    """A source's directory or artifact is not where the instrument looked.

    RAISED, NEVER RETURNED AS ZERO. Zero traces from a path that does not exist
    is indistinguishable from zero traces from a path that does, and the second
    is a finding while the first is a broken instrument.
    """


class SourceEpisode:
    """One scoreable trace, tagged with where it came from.

    `events` are raw dicts in C1 shape; `episode_context` is the BARE-keyed
    frozen `episode.*` block (`crucible.tripwire.model.Episode.episode_context`
    reads `episode_frozen_context` and the keys inside it are bare).
    """

    __slots__ = ("source", "item_id", "channel", "episode_context", "events", "note")

    def __init__(self, source, item_id, channel, episode_context, events, note=""):
        self.source = source
        self.item_id = item_id
        self.channel = channel
        self.episode_context = dict(episode_context or {})
        self.events = list(events or [])
        self.note = note

    def __repr__(self):                                    # pragma: no cover
        return "<SourceEpisode %s/%s %d events>" % (
            self.source, self.item_id, len(self.events))


# ---------------------------------------------------------------------------
# refusals
# ---------------------------------------------------------------------------

def _require_dir(path, source, why):
    if not path.is_dir():
        raise SourceUnavailable(
            "%s: %s is not a directory. THE INSTRUMENT REFUSES rather than "
            "reporting zero coverage from it - pathlib.glob on a missing "
            "directory returns empty rather than raising, so a zero here would "
            "be indistinguishable from a real finding. %s"
            % (source, path, why))
    return path


def _require_files(paths, path, source):
    paths = sorted(paths)
    if not paths:
        raise SourceUnavailable(
            "%s: %s exists and holds no matching file. Zero traces from a "
            "populated source is a finding; zero from an empty one is a moved "
            "directory. Refusing rather than reporting the first as the second."
            % (source, path))
    return paths


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# wire shape
# ---------------------------------------------------------------------------

def _wire(doc, source, item_id):
    ep = doc.get("episode")
    if not isinstance(ep, dict):
        return None
    return SourceEpisode(
        source=source,
        item_id=item_id,
        channel=ep.get("channel"),
        episode_context=ep.get("episode_frozen_context") or {},
        events=ep.get("events") or [],
        note=str(doc.get("expected_verdict") or ""),
    )


def _wire_dir(directory, source, pattern, why, id_keys):
    """Every wire-shape document in one directory.

    A document with no `episode` block is SKIPPED and named in the note, not
    silently dropped: KB5 (WARDEN) and KB9 (LINTER) are known-bad fixtures for
    OTHER components and carry no trace at all, which is a fact about the suite
    rather than a parse failure.
    """
    d = _require_dir(directory, source, why)
    out, skipped = [], []
    for p in _require_files(d.glob(pattern), d, source):
        doc = _load(p)
        item_id = next((str(doc[k]) for k in id_keys if doc.get(k)), p.stem)
        episode = _wire(doc, source, item_id)
        if episode is None:
            skipped.append("%s (%s, no episode block)"
                           % (item_id, doc.get("component") or "?"))
            continue
        out.append(episode)
    return out, skipped


# ---------------------------------------------------------------------------
# authoring shape
# ---------------------------------------------------------------------------

def _authoring_dir(directory, source, why, exclude=()):
    """Corpus-instance documents, converted through the REAL converter.

    Every authored trace step is taken to have executed, which is what
    `_convert_fixture` does and what the benign suite means by "the trace IS the
    v0 recording". For an ATTACK instance that makes this measurement an UPPER
    BOUND: it answers "which clauses could this corpus reach if the policy
    stopped nothing", which is the right question for coverage and the wrong one
    for a breach rate. The matrix says so on its face.
    """
    from crucible.conductor.real_warden import _convert_fixture
    from target.refund_agent.manifest import build_manifest

    d = _require_dir(directory, source, why)
    tools_by_fqname = {t["tool_fqname"]: t for t in build_manifest()["tools"]}
    out = []
    for p in _require_files(d.glob("*.json"), d, source):
        if p.name in exclude:
            continue
        doc = _load(p)
        if "trace" not in doc:
            continue
        fixture = _convert_fixture(doc, p, tools_by_fqname)
        ep = fixture.raw["episode"]
        out.append(SourceEpisode(
            source=source,
            item_id=doc.get("slug") or p.stem,
            # AUTHORING DOCUMENTS CARRY NO CHANNEL and the frozen Objective Set
            # scopes every clause to the sentinel ANY, so the channel cannot
            # change what fires. Stamped from `kind` so the value is never a
            # silent None that a future channel-scoped clause would skip on.
            channel="ADVERSARIAL" if doc.get("kind") == "attack" else "BENIGN",
            episode_context=ep["episode_frozen_context"],
            events=ep["events"],
            note=doc.get("family") or "",
        ))
    return out


# ---------------------------------------------------------------------------
# the sources
# ---------------------------------------------------------------------------

def corpus_training():
    """The 50 hash-frozen training attack instances."""
    return _authoring_dir(
        REPO / "corpus" / "training", "corpus_training",
        "the training corpus is the population every attack in an offline run "
        "is drawn from; with it absent there is no coverage claim to make.")


def benign_suite():
    """`fixtures/benign/*.json` - the 26-fixture WARDEN suite, 14 near-misses."""
    return _authoring_dir(
        REPO / "fixtures" / "benign", "benign_suite",
        "the benign floor is one half of every claim this harness makes; a "
        "clause that fires on it is a FALSE POSITIVE and that is a finding too.")


def known_bad():
    """`tests/golden_traces/known_bad/*.json` - the calibration fixtures."""
    return _wire_dir(
        REPO / "tests" / "golden_traces" / "known_bad", "known_bad", "KB*.json",
        "the known-bad suite is the only thing proving the evaluator can fail "
        "at all; a missing directory there is not a coverage result.",
        ("kb_id",))


def golden_benign_traces():
    """`tests/golden_traces/benign/*.json` - BF01-BF06, wire shape."""
    return _wire_dir(
        REPO / "tests" / "golden_traces" / "benign", "golden_benign_traces",
        "BF*.json", "the wire-shape benign traces the evaluator's own tests "
        "run against.", ("fixture_id",))


def archived_attacks():
    """`tests/golden_traces/attacks/*.json` - the archived replay set."""
    return _wire_dir(
        REPO / "tests" / "golden_traces" / "attacks", "archived_attacks",
        "AT*.json", "the archived attacks are the replay suite that catches a "
        "retraction silently re-opening a closed hole.", ("attack_id",))


def ruling_traces():
    """`tests/golden_traces/T*.json` - the ruling-6 window trio."""
    d = _require_dir(REPO / "tests" / "golden_traces", "ruling_traces",
                     "T1-T3 are the traces the explicit non-breach clause was "
                     "written against.")
    out = []
    for p in _require_files(d.glob("T*.json"), d, "ruling_traces"):
        episode = _wire(_load(p), "ruling_traces", p.stem.split("-")[0])
        if episode is not None:
            out.append(episode)
    return out, []


def offline_campaign_script():
    """What the campaign's offline target ACTUALLY emits, per attack.

    `crucible.conductor.corpus_seeds.CorpusSeeds.offline_script` - the
    instance's own recorded trace, replayed as the scripted model's call list.
    This is the LIVE offline path as of 2026-08-22, and it is NOT
    `campaign.offline_script_for`, which is the retired six-shape default keyed
    off dead `fam_direct_ask`-style family ids.

    Measured separately from `corpus_training` even though it is derived from
    the same instances, because the two DIVERGE and the divergence is the
    interesting part: `CorpusSeeds.load()` drops instances it cannot present a
    world for, so an instance can be in the corpus and never run.
    """
    from crucible.conductor.corpus_seeds import CorpusSeeds
    from crucible.conductor.real_warden import _convert_fixture
    from target.refund_agent.manifest import build_manifest

    seeds = CorpusSeeds.load()
    manifest = build_manifest()
    tools_by_fqname = {t["tool_fqname"]: t for t in manifest["tools"]}
    by_name = {t["tool_fqname"].rsplit(".", 1)[-1]: t["tool_fqname"]
               for t in manifest["tools"]}
    out, skipped = [], []
    for seed in seeds.attack_seeds():
        rec = seeds.lookup(seed.attack_id)
        if rec.unpresentable:
            # CASE 3, AS A SKIP AND NOT AS A ZERO. An instance the harness
            # cannot build a world for is never driven, so its trace cannot
            # exercise anything - counting it in would credit the run with
            # coverage it does not have.
            skipped.append("%s (unpresentable: %s)" % (
                rec.slug,
                # `CorpusAttack.unpresentable` holds `MissingEntity` objects on
                # the load path and pre-rendered strings on the vary path
                # (`corpus_seeds.py` calls `.describe()` there and not here).
                # Rendering both rather than picking one: this is a NOTE, and a
                # note that raises on the wrong arm turns a skip into a crash.
                "; ".join(m.describe() if hasattr(m, "describe") else str(m)
                          for m in rec.unpresentable)))
            continue
        doc = {
            "slug": rec.slug,
            "approver": {"tier": rec.approval_tier},
            # The instance's OWN scenario block, off `CorpusAttack.doc`, which
            # is the verbatim instance. Not reconstructed: ruling 19 restricts
            # every input to a derived field to the instance's own record.
            "scenario": (rec.doc or {}).get("scenario") or {},
            "trace": [{"tool_fqname": by_name.get(name, name), "args": dict(args)}
                      for name, args in seeds.offline_script(seed.attack_id)],
        }
        fixture = _convert_fixture(doc, rec.slug, tools_by_fqname)
        ep = fixture.raw["episode"]
        out.append(SourceEpisode(
            source="offline_campaign_script",
            item_id=rec.slug,
            channel="ADVERSARIAL",
            episode_context=ep["episode_frozen_context"],
            events=ep["events"],
            note=rec.family_id,
        ))
    return out, skipped


def offline_campaign_default_script():
    """`campaign.offline_script_for` - THE RETIRED DEFAULT, measured on purpose.

    It is no longer on the campaign's path (`campaign.py` passes
    `model_factory=lambda attack: build_offline_target_model(
    CORPUS.offline_script(attack))`), and it is measured here because it is
    still importable, still the fallback inside `build_campaign_target` when no
    `model_factory` is passed, and still the thing a stale coverage figure would
    be describing. A row for it is how the matrix tells a reader which of the
    two offline scripts a number came from.
    """
    from crucible.conductor.campaign import offline_script_for
    from crucible.conductor.real_warden import _convert_fixture
    from target.refund_agent.manifest import build_manifest

    manifest = build_manifest()
    tools_by_fqname = {t["tool_fqname"]: t for t in manifest["tools"]}
    by_name = {t["tool_fqname"].rsplit(".", 1)[-1]: t["tool_fqname"]
               for t in manifest["tools"]}
    families = ("fam_split_ask", "fam_destination_swap", "fam_urgency",
                "fam_delegated_chain", "fam_direct_ask", "fam_authority_claim")
    scenario = _demo_scenario()
    out = []
    for family in families:
        doc = {"slug": family, "approver": {"tier": "NONE"}, "scenario": scenario,
               "trace": [{"tool_fqname": by_name.get(n, n), "args": dict(a)}
                         for n, a in offline_script_for(family)]}
        fixture = _convert_fixture(doc, family, tools_by_fqname)
        ep = fixture.raw["episode"]
        out.append(SourceEpisode(
            source="offline_campaign_default_script", item_id=family,
            channel="ADVERSARIAL",
            episode_context=ep["episode_frozen_context"],
            events=ep["events"], note="retired default"))
    return out


def _demo_scenario():
    from crucible.conductor.campaign import SCENARIO_CUSTOMER_ID, SCENARIO_ORDER_ID
    from target.refund_agent.simulated_system_of_record import (
        DEMO_AS_OF, SimulatedSystemOfRecord, seed_demo_ledger,
    )
    sor = seed_demo_ledger(SimulatedSystemOfRecord(as_of=DEMO_AS_OF))
    order = sor.get_order(SCENARIO_ORDER_ID)
    customer = sor.get_customer(SCENARIO_CUSTOMER_ID)
    days = (sor.as_of - order.delivered_on).days if order.delivered_on else 0
    return {
        "account": {"account_id": order.account_holder_id,
                    "email": order.account_holder_email,
                    "age_days": customer.account_age_days},
        "order": {"payment_instrument_id": order.payment_instrument_id,
                  "delivery_confirmed": order.delivery_confirmed,
                  "days_since_delivery": days},
    }


def evidence_bundle(path):
    """Episodes out of a C6 evidence bundle - THE LIVE-RUN ARM.

    A live model may call a tool the offline script never calls, so live
    coverage is not controllable in advance. It IS measurable afterwards, and
    this is the reader that measures it: `episodes[].episode_prefix` is the
    ordered C1 event list, `episodes[].episode_frozen_context` is the frozen
    block, and both are exactly what the clause forms fold over.

    Episodes whose verdict is INVALID are DROPPED rather than counted as
    non-firing, matching `crucible.conductor.bundle._clause_coverage`: an
    unscoreable episode says nothing about coverage, and folding it in as a zero
    makes an instrument failure look like a clause the run never reached.
    """
    p = pathlib.Path(path)
    if not p.is_file():
        raise SourceUnavailable(
            "evidence_bundle: %s is not a file. Refusing rather than reporting "
            "zero live coverage from a bundle that was never there." % p)
    bundle = _load(p)
    out, skipped = [], []
    for ep in bundle.get("episodes") or []:
        verdict = (ep.get("verdict") or {}).get("verdict")
        if verdict == "INVALID":
            skipped.append("%s (INVALID)" % ep.get("episode_id"))
            continue
        out.append(SourceEpisode(
            source="evidence_bundle", item_id=ep.get("episode_id") or "?",
            channel=ep.get("channel"),
            episode_context=ep.get("episode_frozen_context") or {},
            events=ep.get("episode_prefix") or [],
            note="round %s" % ep.get("round_index"),
        ))
    return out, skipped


# The sources the offline matrix is built from, in report order. Each entry is
# `(name, loader)`; a loader returns either a list of episodes or
# `(episodes, skipped_notes)`.
OFFLINE_SOURCES = (
    ("corpus_training", corpus_training),
    ("offline_campaign_script", offline_campaign_script),
    ("offline_campaign_default_script", offline_campaign_default_script),
    ("known_bad", known_bad),
    ("benign_suite", benign_suite),
    ("golden_benign_traces", golden_benign_traces),
    ("archived_attacks", archived_attacks),
    ("ruling_traces", ruling_traces),
)
