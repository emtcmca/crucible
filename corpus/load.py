"""load.py - reading the four directories off disk.

    corpus/training/*.json      48 training attacks, 8 per family
    corpus/sealed/*.json        24 sealed F4 instances. GITIGNORED.
    corpus/pairs.json           the pair records carrying the SEP-BY labels
    fixtures/benign/*.json      24 benign fixtures, 12 near-misses
    fixtures/known_bad/*.json   9 known-bads

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
from .schema import instance_id, validate_instance

REPO = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_LAYOUT = {
    "training": REPO / "corpus" / "training",
    "sealed": REPO / "corpus" / "sealed",
    "benign": REPO / "fixtures" / "benign",
    "known_bad": REPO / "fixtures" / "known_bad",
}
DEFAULT_PAIRS = REPO / "corpus" / "pairs.json"


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

    pairs_path = pathlib.Path(pairs_path or DEFAULT_PAIRS)
    corpus["pairs"] = _read_json(pairs_path)["pairs"] if pairs_path.is_file() else []
    corpus["_present"] = present
    corpus["_pairs_present"] = pairs_path.is_file()
    corpus["_slugs"] = slugs
    return corpus


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
