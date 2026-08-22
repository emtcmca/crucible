"""strawman_replay.py - DELIBERATELY WRONG evidence readers and viewers.

Kept in the tree forever. Not drafts, not dead code. These are the proof that
tests/test_replay_offline.py and tests/test_bundle_reader.py CAN FAIL.

`CONVENTIONS.md` section 8 rule 2: a check that cannot fail is not measuring
anything. This repository has already produced two checks that could not - a
dead-value sweep that reported CLEAN on hard-wrapped prose, and a contract-gate
negative test that mutated its input by appending a newline, which is exactly
the mutation the normalization exists to absorb. Both looked green for the same
reason a disconnected smoke detector looks quiet.

So both L6 suites run twice. Once against `crucible.replay`, where every case
must come out right. Then once against a strawman here, where a NAMED,
PRE-DECLARED case must come out WRONG. If a strawman ever behaves correctly,
the SUITE is broken and that is reported as a failure, not as a green run.

WHY THESE FOUR AND NOT SOME OTHER FOUR
--------------------------------------
Each one is a plausible thing to actually write, and each one produces a viewer
that looks like it works:

  lenient_read          fills a missing hash with "" and renders. THE ENTIRE
                        POINT of the reader is that it must not do this - a
                        bundle that renders beautifully while missing the hash
                        that makes it meaningful is worse than one that fails
                        to open, because the first one looks like evidence.

  self_comparing_verify "verifies" each episode's stamp by comparing the field
                        to itself. It passes on a truncated write, a partial
                        write and a corrupted read, because in every case it is
                        comparing a value to a copy of itself. This is the
                        defect scripts/verify-chain.py's docstring names as the
                        reason recomputation is the only step that can disagree
                        with the record.

  schema_only_read      validates against C6 and stops. It is not lazy - it is
                        what a careful engineer writes, and it accepts a bundle
                        with no `sep_by_split`, because ruling 17 makes that
                        field a permanent reporting requirement and the SCHEMA
                        does not list it as required. The C6 known-bad fixture
                        names that absence as one of its four failure reasons
                        and the schema catches only the other three.

  CREDENTIAL_SOURCE     source text, never imported, for the offline lint to
  NETWORK_SOURCE        chew on. A lint aimed only at code that is already
                        clean has never been shown to detect anything.
"""

import copy
import json

# --------------------------------------------------------------------------
# Strawman 1 - the lenient reader. Renders a blank where a hash should be.
# --------------------------------------------------------------------------

LENIENT_MUST_NOT_REJECT = {
    "episode_missing_derived_schema_hash":
        "an episode with no derived_schema_hash. The episode writer REFUSES to "
        "write one - not a warning - and a reader that renders it anyway "
        "silently republishes a row nothing ever wrote.",
    "episode_missing_manifest_hash":
        "same shape, Part A instead of Part B. Two hashes are two things to "
        "forget, which is the risk ruling 20's split introduced and named.",
    "lock_blanked":
        "a hash-lock present but empty. Blank is the single most dangerous "
        "value here: it satisfies 'the key exists' and carries no information.",
    "episode_missing_frozen_context":
        "an episode with no episode_frozen_context. Ruling 16: without the "
        "frozen episode.* block, one in-episode turn moving "
        "account_holder_email collapses the F4 seal, and NOTHING ELSE CATCHES IT.",
}


def lenient_read(raw_bytes):
    """Parse, then paper over every hole with a blank so the view still renders.

    This is what "be permissive in what you accept" turns into when the thing
    being accepted is evidence. Returns a bundle; raises nothing.
    """
    bundle = json.loads(raw_bytes.decode("utf-8-sig"))
    locks = bundle.setdefault("run_manifest", {}).setdefault("hash_locks", {})
    for key in ("gate_rule_hash", "target_agent_hash", "manifest_hash",
                "objective_set_hash", "corpus_hash", "derived_schema_hash"):
        locks.setdefault(key, "")
    for ep in bundle.get("episodes", []):
        for key in ("objective_set_hash", "manifest_hash", "derived_schema_hash"):
            ep.setdefault(key, "")
        ep.setdefault("episode_frozen_context", {})
        ep.setdefault("episode_prefix", [])
    bundle.setdefault("sep_by_split", {"policy_separated": 0,
                                       "approval_oracle_separated": 0})
    return bundle


# --------------------------------------------------------------------------
# Strawman 2 - verification by self-comparison. Always green.
# --------------------------------------------------------------------------

SELF_COMPARING_MUST_NOT_REJECT = {
    "episode_stamp_disagrees_with_manifest":
        "an episode stamped with a DIFFERENT objective_set_hash than the run "
        "manifest carries. That is two arms measuring under two definitions of "
        "breach, which is the single path by which every headline number is "
        "produced while all three claims are false. Comparing each field to "
        "itself cannot see it.",
}


def self_comparing_verify(bundle):
    """Return [] (no defects) by checking every hash against itself.

    Every assertion below is true of any string whatsoever. That is the point:
    the function is shaped exactly like verification and measures nothing.
    """
    defects = []
    locks = bundle.get("run_manifest", {}).get("hash_locks", {})
    for key, value in locks.items():
        if value != locks[key]:                      # pragma: no cover - never
            defects.append("lock %s disagrees with itself" % key)
    for ep in bundle.get("episodes", []):
        for key in ("objective_set_hash", "manifest_hash", "derived_schema_hash"):
            if key in ep and ep[key] != ep[key]:     # pragma: no cover - never
                defects.append("episode %s: %s" % (ep.get("episode_id"), key))
    return defects


# --------------------------------------------------------------------------
# Strawman 3 - schema validation and nothing else.
# --------------------------------------------------------------------------

# CLOSED 2026-08-20 BY THE COORDINATOR, and this set is now EMPTY.
#
# It held exactly one entry: `sep_by_split_missing`. Ruling 17 makes the SEP-BY
# split a permanent reporting requirement, and C6 defined the field without
# listing it in `required` -- so schema validation ACCEPTED a bundle the ruling
# forbids. A suite the APPROVAL_ORACLE separates produces IDENTICAL headline
# numbers to one the policy separates; only that ratio tells them apart, so a
# bundle without it carries numbers that cannot be falsified.
#
# This lane pinned the gap rather than working around it, and wrote the exact
# condition for retiring the pin into its own failure message: "if C6 now
# REQUIRES sep_by_split then ruling 17 is enforced by the contract and this
# strawman is obsolete - but that is a contract change, and a lane reports it
# rather than adjusting the test." It reported. The coordinator changed C6. The
# pin is retired here, by the party allowed to retire it.
#
# LEFT AS AN EMPTY DICT ON PURPOSE. Deleting the name would delete the record
# that the gap existed and how it closed, and `test_schema_only_gap_is_closed`
# below now asserts the schema catches what this set used to excuse -- so the
# property is still tested, from the other side.
SCHEMA_ONLY_MUST_NOT_REJECT = {}


def schema_only_read(raw_bytes, validator):
    """Parse and validate against C6. Nothing further.

    `validator` is injected rather than built here so this strawman shares the
    real reader's schema and cannot pass for a reason the real reader would not.
    """
    bundle = json.loads(raw_bytes.decode("utf-8"))
    errors = sorted(validator.iter_errors(bundle), key=lambda e: list(e.path))
    if errors:
        raise ValueError("schema: %s" % errors[0].message)
    return bundle


# --------------------------------------------------------------------------
# Strawmen 4 and 5 - source text for the offline lint. NEVER IMPORTED.
# --------------------------------------------------------------------------
# Held as strings so that a test can hand them to the lint without this module
# acquiring a network import or an environment read of its own. A lint pointed
# only at code that is already clean has never been shown to detect anything.

CREDENTIAL_SOURCE = '''
import os

def render(bundle):
    key = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "crucible-hack-2026")
    return "%s %s" % (key, project)
'''

NETWORK_SOURCE = '''
import urllib.request
from google.cloud import storage

def fetch(uri):
    return urllib.request.urlopen(uri).read()
'''

SUBPROCESS_SOURCE = '''
import subprocess

def whoami():
    return subprocess.check_output(["gcloud", "auth", "list"])
'''

INDIRECT_IMPORT_SOURCE = '''
import importlib

def late():
    return importlib.import_module("google.cloud.storage")
'''

LINT_MUST_FLAG = {
    "CREDENTIAL_SOURCE": "reads GOOGLE_APPLICATION_CREDENTIALS out of the "
                         "environment. If replay needs a credential the judge "
                         "cannot run it and the reproduction claim is untestable.",
    "NETWORK_SOURCE": "opens a URL and imports a cloud client. Either one turns "
                      "an offline replay into a live fetch that can succeed on "
                      "the author's machine and nowhere else.",
    "SUBPROCESS_SOURCE": "shells out to gcloud. The credential path the import "
                         "deny-list would otherwise miss entirely.",
    "INDIRECT_IMPORT_SOURCE": "importlib.import_module with a string constant. "
                              "A grep for `import google` never sees this line.",
}


def mutate(bundle, how):
    """Produce a named, deliberately-damaged copy of a valid bundle.

    One function, so the damage a test applies and the damage a strawman is
    declared not to notice are described by the SAME string. Two lists of
    mutation names drift; one does not.
    """
    b = copy.deepcopy(bundle)
    if how == "episode_missing_derived_schema_hash":
        b["episodes"][0].pop("derived_schema_hash", None)
    elif how == "episode_missing_manifest_hash":
        b["episodes"][0].pop("manifest_hash", None)
    elif how == "episode_missing_objective_set_hash":
        b["episodes"][0].pop("objective_set_hash", None)
    elif how == "lock_blanked":
        b["run_manifest"]["hash_locks"]["derived_schema_hash"] = ""
    elif how == "lock_missing":
        b["run_manifest"]["hash_locks"].pop("corpus_hash", None)
    elif how == "episode_missing_frozen_context":
        b["episodes"][0].pop("episode_frozen_context", None)
    elif how == "frozen_at_moved":
        b["episodes"][0]["episode_frozen_context"]["frozen_at"] = "after_first_user_turn"
    elif how == "episode_missing_prefix":
        b["episodes"][0].pop("episode_prefix", None)
    elif how == "episode_stamp_disagrees_with_manifest":
        b["episodes"][0]["objective_set_hash"] = "0" * 16
    elif how == "verdict_stamp_disagrees_with_episode":
        b["episodes"][0]["verdict"]["objective_set_hash"] = "1" * 16
    elif how == "sep_by_split_missing":
        b.pop("sep_by_split", None)
    elif how == "sep_by_split_at_parity":
        b["sep_by_split"] = {"policy_separated": 11, "approval_oracle_separated": 11}
    elif how == "benign_traces_short":
        b["v0_benign_traces"] = b["v0_benign_traces"][:23]
    elif how == "benign_traces_at_the_old_denominator":
        # 24 was a COMPLETE benign suite until ruling 43 (2026-08-21) and is a
        # SHORT one after it. Truncating to 23 proves the check fires at all;
        # truncating to exactly 24 proves it fires at the RULER THAT MOVED,
        # which is the case that passed clean while every other test was green.
        b["v0_benign_traces"] = b["v0_benign_traces"][:24]
    elif how == "float_in_payload":
        b["cost"]["input_tokens"] = 412000.0
    elif how == "null_in_payload":
        b["episodes"][0]["policy_hash"] = None
    else:                                             # pragma: no cover
        raise KeyError("no such mutation: %r" % how)
    return b
