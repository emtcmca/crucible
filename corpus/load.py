"""load.py - reading the four directories off disk.

    corpus/training/*.json      50 training attacks, 8 per family and TEN F5
    corpus/sealed/*.json        24 sealed F4 instances. GITIGNORED.
    corpus/pairs.json           the pair records carrying the SEP-BY labels
    fixtures/benign/*.json      26 benign fixtures, 14 near-misses
    tests/golden_traces/known_bad/*.json
                                the 9 known-bads. NOT under fixtures/ -
                                see the block above load_known_bads()

THE SEALED DIRECTORY IS ABSENT ON A FRESH CLONE, AND THAT MUST NOT READ AS ZERO
-------------------------------------------------------------------------------
`corpus/sealed/` is gitignored, so a judge cloning the public repo gets no
sealed set - correctly, that is the point. But "the directory is not here" and
"the sealed set holds zero instances" are different facts, and collapsing them
would make the sizing check report E_SEALED_BELOW_FLOOR on a clone where nothing
is wrong. The loader reports `sealed_present: False` and the caller decides.

**The .gitignore entry is not the control.** The real boundary is IAM: the
Armorer's service account holds no read on the sealed bucket. The ignore line
only stops an accidental local commit, and a pre-commit hook refusing any staged
path under `corpus/sealed/` is the second layer. Neither is the boundary.

BYTES, NOT TEXT
---------------
Files are read as bytes and decoded strictly. A BOM is REFUSED rather than
stripped, matching canonicalization restriction 1 - the same defect L2 already
paid for once in scope (a), where `freeze.py` hashed raw bytes and the freeze
hash differed between an LF working copy and a CRLF checkout. That failure looks
correct on the machine that produced it and fails for the judge who clones it.
"""

import json
import pathlib

from .errors import CorpusError
from .schema import instance_id, validate_instance, validate_known_bad

REPO = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_LAYOUT = {
    "training": REPO / "corpus" / "training",
    "sealed": REPO / "corpus" / "sealed",
    "benign": REPO / "fixtures" / "benign",
}
DEFAULT_PAIRS = REPO / "corpus" / "pairs.json"

# THE NINE KNOWN-BADS ARE ALREADY AUTHORED, AND NOT WHERE THIS MODULE LOOKED.
# ----------------------------------------------------------------------------
# This loader read `fixtures/known_bad/*.json` and expected the corpus INSTANCE
# shape. Two things were wrong with that, and only one of them was a path.
#
# 1. The nine exist, hand-written, in `tests/golden_traces/known_bad/`. Authoring
#    a second set under `fixtures/` would put KB1-KB9 in the repository twice, in
#    two schemas, and the pair would drift the first time one was corrected.
#    `CLAUDE.md` on the bucket names: *a second copy is a second source of truth.*
#
# 2. THE INSTANCE SCHEMA CANNOT HOLD THREE OF THEM. It requires a non-empty
#    trace carrying exactly one `scored: true` call against a Part A tool. KB5 is
#    a policy DOCUMENT the Warden must reject, KB9 is a document set plus a
#    product lexicon the linter must reject and then accept, and neither has an
#    episode at all. Forcing them in would mean inventing a tool call that never
#    happened, inside an artifact that gets hashed at D5.
#
# So the count is asserted where the nine actually live, against a validator
# shaped like what they are. `KNOWN_BAD_TOTAL` is untouched, `must_fail` is still
# refused by name, and every fixture still declares its own `expected_verdict` -
# the five-of-nine fact that makes "all nine must fail" a FALSE description of
# this suite survives intact.
KNOWN_BAD_DIR = REPO / "tests" / "golden_traces" / "known_bad"
KNOWN_BAD_SECOND_HOME = REPO / "fixtures" / "known_bad"


def _read_json(path):
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise CorpusError(
            "E_BOM",
            "%s starts with a UTF-8 BOM. Refused rather than stripped: the "
            "corpus is hash-locked at D5 and canonicalization restriction 1 "
            "refuses a BOM, so stripping here would move the defect to the "
            "freeze." % path.name)
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise CorpusError("E_MALFORMED_JSON", "%s: %s" % (path.name, e))


def load_corpus(layout=None, pairs_path=None, manifest=None):
    """Load and validate every instance on disk. Returns a corpus dict.

    Every instance is validated as it loads. A corpus that half-loads and then
    reports counts would produce a sizing verdict over instances nobody checked.
    """
    from .model import load_part_a

    manifest = manifest or load_part_a()
    layout = layout or DEFAULT_LAYOUT
    corpus = {"training": [], "sealed": [], "benign": [], "known_bad": []}
    present = {}
    slugs = {}

    for bucket, directory in layout.items():
        directory = pathlib.Path(directory)
        present[bucket] = directory.is_dir()
        if not present[bucket]:
            continue
        for path in sorted(directory.glob("*.json")):
            doc = _read_json(path)
            validate_instance(doc, manifest=manifest)
            slug = doc["slug"]
            if slug in slugs:
                raise CorpusError(
                    "E_DUPLICATE_SLUG",
                    "slug %r appears in %s and %s. Pair records reference "
                    "instances by slug, so a duplicate means a pair points at "
                    "whichever file happened to load second - and the SEP-BY "
                    "split would then describe a pair nobody authored."
                    % (slug, slugs[slug], path.name))
            slugs[slug] = path.name
            doc["_instance_id"] = instance_id(doc)
            doc["_source_file"] = path.name
            corpus[bucket].append(doc)

    corpus["known_bad"] = load_known_bads()
    present["known_bad"] = KNOWN_BAD_DIR.is_dir()

    pairs_path = pathlib.Path(pairs_path or DEFAULT_PAIRS)
    corpus["pairs"] = _read_json(pairs_path)["pairs"] if pairs_path.is_file() else []
    corpus["_present"] = present
    corpus["_pairs_present"] = pairs_path.is_file()
    corpus["_slugs"] = slugs
    return corpus


def load_known_bads(directory=None, second_home=None):
    """The nine, read from the one place they are authored.

    Refuses a second home before reading anything. `fixtures/known_bad/` holding
    a `*.json` would mean KB1-KB9 exist twice, and two copies of a fixture drift
    the first time one is corrected - silently, because both would still load
    and the count would still be nine.
    """
    directory = pathlib.Path(directory or KNOWN_BAD_DIR)
    second_home = pathlib.Path(second_home or KNOWN_BAD_SECOND_HOME)

    if second_home.is_dir():
        stray = sorted(p.name for p in second_home.glob("*.json"))
        if stray:
            raise CorpusError(
                "E_KNOWN_BAD_SECOND_HOME",
                "%s holds %s. The nine known-bads are authored in %s and only "
                "there. Two copies of one fixture drift the first time either is "
                "corrected, and nothing notices - both load, and the count is "
                "still nine."
                % (second_home.name + "/", stray, directory.name + "/"))

    if not directory.is_dir():
        return []

    out = []
    seen = {}
    for path in sorted(directory.glob("*.json")):
        doc = _read_json(path)
        validate_known_bad(doc)
        kb_id = doc["kb_id"]
        if kb_id in seen:
            raise CorpusError(
                "E_DUPLICATE_KNOWN_BAD_ID",
                "%s appears in %s and %s. One of the two is invisible to the "
                "count, and `known_bad_expected_verdict_rate == 1.0` is the "
                "figure that decides whether the whole RUN is valid."
                % (kb_id, seen[kb_id], path.name))
        seen[kb_id] = path.name
        doc["_source_file"] = path.name
        doc["slug"] = kb_id
        doc["kind"] = "known_bad"
        out.append(doc)
    return out


def assert_pairs_resolve(corpus):
    """Every pair must name two instances that actually exist.

    A pair referencing a slug nobody wrote is a pair that is counted in the
    SEP-BY split and evaluated by nothing - it inflates the denominator of the
    one ratio that distinguishes a policy-separated suite from an
    oracle-separated one.
    """
    slugs = set(corpus.get("_slugs") or {})
    missing = []
    for p in corpus.get("pairs") or []:
        for side in ("attack", "benign"):
            if p.get(side) and p[side] not in slugs:
                missing.append("%s.%s -> %s" % (p.get("pair_id"), side, p[side]))
    if missing:
        raise CorpusError(
            "E_PAIR_REFERENCE_MISSING",
            "pair records reference instances that do not exist: %s. Such a "
            "pair is counted in the SEP-BY split and evaluated by nothing."
            % missing)
    return {"pairs": len(corpus.get("pairs") or [])}
