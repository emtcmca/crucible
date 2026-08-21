"""store.py - the append-only SQLite run ledger.

The ledger is the record of what actually happened: which policy versions were
promoted, in what order, against which target manifest. `data-spec.md` names
Firestore as the production store and says nothing in the design requires it
beyond append-only semantics. This is the local implementation the harness and
the gate develop against, and it is the one `verify-chain` reads offline.

APPEND-ONLY IS ENFORCED BY TRIGGERS, NOT BY DISCIPLINE
------------------------------------------------------
`policy_versions` carries SQLite triggers that RAISE on UPDATE and on DELETE.
A convention that says "we only ever append" is worth nothing the first time
somebody writes a fix-up script at 2am, and it is worth actively less than
nothing here, because the whole point of the lineage chain is to detect exactly
that edit. A store that permits the edit and a chain that detects it are a
strictly worse pair than a store that refuses it.

This is a DETECTOR and a LOCAL guard. It is not the security boundary. The real
immutability control is IAM on the policies bucket: `crucible-gate` holds
`objectCreator` and nothing that can overwrite or delete. Anyone with the SQLite
file can drop a trigger. Saying so is worth more than implying otherwise.
"""

import pathlib
import sqlite3

SCHEMA = """
-- TWO SQLite facts that both bit here, in order:
--   1. There is NO adjacent-string-literal concatenation. Two quoted strings
--      side by side are a syntax error, not one string.
--   2. RAISE(ABORT, ...) takes a string LITERAL, not an expression -- so the
--      obvious fix for (1), joining with ||, is ALSO a syntax error inside it.
-- Hence the long single-line literals below. Wrapping them breaks the trigger,
-- and a trigger that fails to create leaves the table silently mutable.
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS runs (
    run_id              TEXT PRIMARY KEY,
    created_at          TEXT NOT NULL,
    manifest_hash       TEXT NOT NULL,
    objective_set_hash  TEXT NOT NULL,
    gate_rule_hash      TEXT NOT NULL,
    target_hash         TEXT NOT NULL,
    corpus_hash         TEXT,
    derived_schema_hash TEXT,
    head_lineage_hash   TEXT,
    status              TEXT NOT NULL DEFAULT 'running'
);

CREATE TABLE IF NOT EXISTS policy_versions (
    run_id            TEXT NOT NULL REFERENCES runs(run_id),
    version           INTEGER NOT NULL,
    policy_hash_full  TEXT NOT NULL,
    policy_hash       TEXT NOT NULL,
    parent_hash       TEXT,
    lineage_hash      TEXT NOT NULL,
    manifest_hash     TEXT NOT NULL,
    promoted_by       TEXT NOT NULL,
    promoted_at       TEXT NOT NULL,
    payload_bytes     BLOB NOT NULL,
    PRIMARY KEY (run_id, version)
);

-- Append-only, enforced. See the module docstring for what this is and is not.
CREATE TRIGGER IF NOT EXISTS policy_versions_no_update
BEFORE UPDATE ON policy_versions
BEGIN
    SELECT RAISE(ABORT, 'policy_versions is append-only. An UPDATE here is the exact edit the lineage chain exists to detect; permitting it and then detecting it would be strictly worse than refusing it.');
END;

CREATE TRIGGER IF NOT EXISTS policy_versions_no_delete
BEFORE DELETE ON policy_versions
BEGIN
    SELECT RAISE(ABORT, 'policy_versions is append-only. Deleting a version creates the gap that a silently failed promotion also creates, and makes the two indistinguishable.');
END;
"""


class LedgerError(RuntimeError):
    pass


class Ledger:
    def __init__(self, path):
        self.path = str(path)
        if self.path != ":memory:":
            pathlib.Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.db.commit()

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    # -- runs ---------------------------------------------------------------

    def open_run(self, run_id, created_at, hash_locks):
        """`hash_locks` carries the five locks from CONVENTIONS: gate rule,
        target, manifest, objective set, and (at D5) corpus + derived schema."""
        required = ("manifest_hash", "objective_set_hash", "gate_rule_hash",
                    "target_hash")
        missing = [k for k in required if not hash_locks.get(k)]
        if missing:
            raise LedgerError(
                "a run cannot open without %s. A run manifest with an empty "
                "hash lock is a run that cannot be shown to have measured "
                "anything specific." % ", ".join(missing))
        self.db.execute(
            "INSERT INTO runs (run_id, created_at, manifest_hash, "
            "objective_set_hash, gate_rule_hash, target_hash, corpus_hash, "
            "derived_schema_hash) VALUES (?,?,?,?,?,?,?,?)",
            (run_id, created_at, hash_locks["manifest_hash"],
             hash_locks["objective_set_hash"], hash_locks["gate_rule_hash"],
             hash_locks["target_hash"], hash_locks.get("corpus_hash"),
             hash_locks.get("derived_schema_hash")))
        self.db.commit()

    def get_run(self, run_id):
        r = self.db.execute("SELECT * FROM runs WHERE run_id=?",
                            (run_id,)).fetchone()
        if r is None:
            raise LedgerError("no such run: %s" % run_id)
        return dict(r)

    # -- policy versions ----------------------------------------------------

    def head(self, run_id):
        r = self.db.execute(
            "SELECT * FROM policy_versions WHERE run_id=? "
            "ORDER BY version DESC LIMIT 1", (run_id,)).fetchone()
        return dict(r) if r else None

    def next_version(self, run_id):
        h = self.head(run_id)
        return 1 if h is None else h["version"] + 1

    def append_version(self, run_id, version, policy_hash_full, parent_hash,
                       lineage_hash, manifest_hash, promoted_by, promoted_at,
                       payload_bytes):
        expected = self.next_version(run_id)
        if version != expected:
            raise LedgerError(
                "out-of-order promotion: next version is %d, got %d. Accepting "
                "it would create a chain gap indistinguishable from a silently "
                "failed write." % (expected, version))
        self.db.execute(
            "INSERT INTO policy_versions (run_id, version, policy_hash_full, "
            "policy_hash, parent_hash, lineage_hash, manifest_hash, "
            "promoted_by, promoted_at, payload_bytes) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (run_id, version, policy_hash_full, policy_hash_full[:16],
             parent_hash, lineage_hash, manifest_hash, promoted_by, promoted_at,
             payload_bytes))
        self.db.execute("UPDATE runs SET head_lineage_hash=? WHERE run_id=?",
                        (lineage_hash, run_id))
        self.db.commit()

    def versions(self, run_id):
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM policy_versions WHERE run_id=? ORDER BY version",
            (run_id,))]
