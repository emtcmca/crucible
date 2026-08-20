#!/usr/bin/env python3
"""Generate contracts/MANIFEST.json - the W0 contract freeze.

Normalization before hashing is TEXTUAL AND MINIMAL, and it is a DIFFERENT
OPERATION from the JCS canonicalization used on policy payloads. Three of the
contracts are not JSON at all (policy.ebnf, gate_rule.v1.yaml,
canonicalization.md), so a JSON canonicalizer cannot be the common form.
Conflating the two is how a manifest hash starts disagreeing with a policy hash
for reasons nobody can reproduce. See contracts/canonicalization.md section 4.

    1. line endings -> LF
    2. trailing whitespace stripped from every line
    3. exactly one trailing newline
    4. UTF-8, no BOM

Run:  python scripts/hash-contracts.py           # write MANIFEST.json
      python scripts/hash-contracts.py --check   # verify, exit 1 on drift
"""

import hashlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
CONTRACTS = REPO / "contracts"
MANIFEST = CONTRACTS / "MANIFEST.json"

# Nine contracts. Three of them are two files each - that is existing precedent
# (C4 and C7 were already two-file contracts), and it is why ruling 20's manifest
# split did NOT push the count to ten. NINE STAYS NINE.
CONTRACT_FILES = {
    "C1": ["tool_event.schema.json"],
    "C2": ["decision.schema.json"],
    "C3": ["capability_manifest.schema.json", "derived_schema.schema.json"],
    "C4": ["policy.ebnf", "policy_document.schema.json"],
    "C5": ["breach_record.schema.json"],
    "C6": ["evidence_bundle.schema.json"],
    "C7": ["run_manifest.schema.json", "canonicalization.md"],
    "C8": ["gate_rule.v1.yaml"],
    "C9": ["verdict.schema.json"],
}

OWNERS = {
    "C1": {"produced_by": "L3", "consumed_by": ["L4", "L6"]},
    "C2": {"produced_by": "L3", "consumed_by": ["L3", "L4"]},
    "C3": {"produced_by": "L2", "consumed_by": ["L3", "L4", "L5"]},
    "C4": {"produced_by": "L1/L3", "consumed_by": ["L4", "L5"]},
    "C5": {"produced_by": "L5", "consumed_by": ["L5", "L6"]},
    "C6": {"produced_by": "L1/L4/L5", "consumed_by": ["L6"]},
    "C7": {"produced_by": "L1", "consumed_by": ["ALL"]},
    "C8": {"produced_by": "L1", "consumed_by": ["L4", "L5"]},
    "C9": {"produced_by": "L4", "consumed_by": ["L5", "L6"]},
}

FREEZES = {
    "C3:capability_manifest.schema.json": "D3_with_target",
    "C3:derived_schema.schema.json": "D5_with_corpus_gated_on_blindness_check",
    "C8:gate_rule.v1.yaml": "D2_not_editable_after",
}

# -----------------------------------------------------------------------------
# TERM BINDINGS - CONVENTIONS.md section 8 rule 11.
# One concept, one name. One name, one concept. A contract may not introduce a
# term already bound here. contract-check.py fails on a redefinition.
#
# Every entry below exists because a collision produced a REAL DEFECT on
# 2026-08-20, not because someone wanted a glossary.
# -----------------------------------------------------------------------------
TERM_BINDINGS = {
    "OBJECTIVE_EVALUATOR": {
        "means": "the component that evaluates the Objective Set to produce a breach verdict",
        "not": ["oracle", "the oracle"],
        "why": "'oracle' named TWO components. Grepping for the approval oracle in the hash-locks returned the OBJECTIVE SET's fix, which reads as though the question is already answered. It is a different oracle, and THE COLLISION IS WHY THE GAP SURVIVED.",
    },
    "APPROVAL_ORACLE": {
        "means": "the scripted harness channel that approves or denies a require_approval call",
        "not": ["oracle", "the approval channel"],
        "why": "same collision, other side. Its default behavior is a FROZEN RUN-MANIFEST PARAMETER (approval_oracle_default), not prose.",
    },
    "role": {
        "means": "the invoking agent name, RECORDED on a ToolEvent and NOT EVALUATED",
        "not": ["approver_role", "IAM role", "role-to-model assignment"],
        "why": "'role' named FOUR things across the spec set. It is also the only plain-text product identifier the grammar ever admitted, which is why no rule may bind to it (ruling 25).",
    },
    "approver": {
        "means": "the identity declared BY A FIXTURE and read by the identity layer",
        "not": ["approval_record.verified", "derived.approval_verified", "the verified boolean"],
        "why": "that field carried THREE NAMES across four documents - a field nobody could review, because no single string found it. It is DELETED (ruling 23); its spec was 'attack -> false, benign -> true', a mapping from label to value.",
        "encoding": "REQUIRED on every corpus instance; the sentinel \"NONE\" when none is declared. ABSENT IS A VALIDATION ERROR, NOT A DEFAULT - 'declared none' and 'the author forgot' are otherwise the same bytes. NOT JSON null, which canonicalization rule 5 forbids.",
    },
    "capability_class": {
        "means": "SCALAR. Exactly one of the six, per rule",
        "not": ["capability_classes (on a RULE)", "match_mode"],
        "why": "match_mode:all_of contradicted intersects - TWO POLICIES FOR THE SAME STORED BYTES. Note capability_classes IS still correct on a TOOL, which carries a set; the collision was rule-side only.",
    },
    "UNCLASSIFIED": {
        "means": "we do not know what this tool does",
        "not": ["the empty set", "inert"],
        "why": "the empty set means INERT. These are different facts and must not share an encoding. No rule may select UNCLASSIFIED (C4 V2) - on an unseen target it would report 100% transfer, MANUFACTURED.",
    },
    "hash_locks": {
        "means": "FIVE: gate rule, target agent, manifest_hash, objective_set_hash, corpus+derived_schema_hash",
        "not": ["four hash-locks", "the four hashes", "three hash-locks"],
        "why": "this count has been stated as three, four, and five. Ruling 20's own propagation list named FOUR sites; the real number was FOURTEEN.",
    },
    "INVALID": {
        "means": "the instrument is untrustworthy; there is NO measurement",
        "not": ["FAILED"],
        "why": "FAILED is a measurement - publish it. NO NUMBER FROM AN INVALID RUN MAY BE REPORTED, INCLUDING THE ONES THAT LOOK GOOD.",
    },
    "TARGET_FAULT": {
        "means": "neither breach nor non-breach; removed from the denominator and logged",
        "not": ["attack failed", "CLEAN"],
        "why": "counting a crash as 'attack failed' would let a FRAGILE target render as a HARDENED one.",
    },
}


def normalize(raw: bytes) -> bytes:
    if raw[:3] == b"\xef\xbb\xbf":
        raise SystemExit("BOM found - contracts must be UTF-8 without BOM")
    text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in text.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return ("\n".join(lines) + "\n").encode("utf-8")


def build():
    contracts = {}
    for cid, files in sorted(CONTRACT_FILES.items()):
        entry = {"files": {}, **OWNERS[cid]}
        for fn in files:
            p = CONTRACTS / fn
            if not p.exists():
                raise SystemExit("MISSING CONTRACT FILE: %s" % fn)
            norm = normalize(p.read_bytes())
            rec = {"sha256": hashlib.sha256(norm).hexdigest(), "bytes": len(norm)}
            key = "%s:%s" % (cid, fn)
            if key in FREEZES:
                rec["freezes"] = FREEZES[key]
            entry["files"][fn] = rec
        contracts[cid] = entry
    return {
        "manifest_version": 1,
        "spine_version": 2,
        "frozen_at": "W0",
        "contract_count": len(CONTRACT_FILES),
        "normalization": "LF; trailing whitespace stripped per line; exactly one trailing newline; UTF-8 no BOM. NOT JCS - see contracts/canonicalization.md section 4.",
        "contracts": contracts,
        "term_bindings": TERM_BINDINGS,
    }


def main():
    check = "--check" in sys.argv
    built = build()
    if check:
        if not MANIFEST.exists():
            print("FAIL: MANIFEST.json does not exist")
            return 1
        stored = json.loads(MANIFEST.read_text(encoding="utf-8"))
        drift = []
        for cid, entry in built["contracts"].items():
            for fn, rec in entry["files"].items():
                got = rec["sha256"]
                want = stored.get("contracts", {}).get(cid, {}).get("files", {}).get(fn, {}).get("sha256")
                if want != got:
                    drift.append("%s/%s stored=%s actual=%s" % (cid, fn, want, got))
        if drift:
            print("CONTRACT DRIFT - %d file(s):" % len(drift))
            for d in drift:
                print("  " + d)
            return 1
        print("OK: %d contracts, all hashes match" % built["contract_count"])
        return 0
    MANIFEST.write_text(
        json.dumps(built, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8", newline="\n")
    print("wrote %s" % MANIFEST)
    for cid, entry in built["contracts"].items():
        for fn, rec in entry["files"].items():
            print("  %-4s %-40s %s" % (cid, fn, rec["sha256"][:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
