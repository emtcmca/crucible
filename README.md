# CRUCIBLE

**A pre-deployment hardening harness for AI agents that hold real permissions.**

A red-team agent attacks a target agent. A pure-code tripwire records what the target
actually *called* — not what it said. A Coroner writes an autopsy of each breach but
cannot propose a fix. An Armorer proposes policy patches in a three-verb DSL but cannot
promote them. A pure-code Warden and gate promote or roll back. Every one of those
boundaries is a component that is deliberately blind to something, because a system that
grades its own work is not measuring anything.

Built for the Google **All Things Agentic** hackathon, track *The Fortified Enterprise
Fleet*.

---

## The judge path — replay the evidence yourself, offline

**This is the point of the repository being public.** A run produces an *evidence bundle*:
the immutable run manifest with its five hash-locks, every episode's frozen context and
ordered tool-call prefix, the policy lineage, the gate's decisions, and the recorded
benign traces. The bundle is a file. Replaying it needs **no credentials, no network, and
no cloud project.**

```bash
git clone https://github.com/emtcmca/crucible
cd crucible
pip install -r requirements.txt

python -m crucible.replay contracts/golden/C6-evidence_bundle.valid.json
```

That command reads a file and prints a page. It opens no socket, reads no credential, and
consults no environment variable — and that is enforced by an AST lint over the package
plus a test that runs the viewer in a subprocess with the environment stripped and the
socket module replaced by something that raises
(`crucible/replay/offline_lint.py`, `tests/test_replay_offline.py`).

Add `--episode <id>` to replay one episode in full: its frozen `episode.*` block, its
ordered tool events with the harness-stamped `derived.*` fields separated from the model's
own arguments, and the verdict with the event sequence numbers it rested on.

### The viewer refuses

A bundle missing a hash is **rejected**, not rendered with a blank field. That is the
whole design. A bundle that renders beautifully while missing the hash that makes it
meaningful is worse than one that fails to open, because the first one looks like
evidence. Exit code 2, the defects named, nothing drawn.

Try it:

```bash
python - <<'PY'
import json, pathlib
b = json.load(open("contracts/golden/C6-evidence_bundle.valid.json"))
b["episodes"][0].pop("derived_schema_hash")
pathlib.Path("damaged.json").write_text(json.dumps(b))
PY

python -m crucible.replay damaged.json      # exits 2, names the field and the episode
```

### What "verified" means on each row, and what it does not

The viewer prints, next to every integrity check, **how** that check was established:

| Kind | Meaning |
|---|---|
| `RECOMPUTED` | derived again from the bytes on disk and had to agree |
| `CROSS_CHECKED` | two independently written fields had to agree with each other |
| `PRESENT` | a required field exists and is well-formed |

The distinction is printed rather than assumed because comparing a stored hash to itself
passes on a truncated write, a partial write, and a corrupted read — in each case a value
is being compared to a copy of itself. Most of what a bundle supports is cross-checking,
and saying so is the difference between a claim that survives a judge opening the file and
one that does not.

Full recomputation of the policy lineage reads the run ledger rather than the bundle:

```bash
python scripts/verify-chain.py --ledger <run.db> --run <run_id>
python scripts/verify-chain.py --selftest      # proves the verifier can fail
```

The lineage chain is **unsigned.** It detects accidental mutation, partial writes, and
post-hoc editing. It does not defend against an adversary holding the Gate's credentials,
because such an adversary recomputes it too. IAM immutability is the real control; the
chain is the detector.

---

## Status

**As of 2026-08-20: no run has been executed and nothing has been measured.** Every number
in this README is a *frozen parameter* — a value decided before measurement so it cannot
be chosen afterwards to fit a result. There are no results to report yet, and this section
is where they will go when there are.

---

## The labels that will travel with every figure

These are pre-registered, before any number exists, because a qualifier added after a
result is a qualifier that was negotiated.

- **`k = 1` — single-sample, no stability estimate.** Every attack-success figure from
  this build is written `ASR (any-of-1)` and carries that phrase, permanently.
- **The SEP-BY split.** Every attack/benign pair is separated either *by the policy* (the
  rule's predicate differs on the two sides) or *by the approval oracle* (the predicate is
  identical and the oracle decides). Target split: **18 policy-separated / 4
  oracle-separated.** A suite the oracle separates produces identical headline numbers to
  one the policy separates, and only this ratio tells them apart. Without it, "the loop
  learned a capability boundary" is unfalsifiable.
- **The benign floor is a bound, not a proof.** The denominator is fixed permanently at 24
  fixtures. A clean 0/24 bounds the true regression rate at roughly **12.5%** by the rule
  of three, and that is the sentence — never a claim that nothing was lost. The viewer
  computes the bound from `3/n` rather than quoting it, and withholds it entirely once a
  failure has been observed, because the rule of three bounds an *unobserved* rate.
- **The target's model tier is named every time.** A weaker target is easier to attack,
  which inflates the baseline and flatters the whole curve.

## What is enforced, and what is convention

Only these are structural — a control that holds because the system cannot do otherwise:

- the Armorer cannot read the sealed attack family: it holds no storage role on that
  bucket at all
- the tripwire and the warden cannot call a model: no `aiplatform.user`, plus an AST
  import lint in the repository
- a promoted policy version cannot be overwritten: the promoting identity holds
  create-only on the policy bucket, plus a retention policy
- the plugin's short-circuit: a denied call does not reach the tool

Everything else is convention plus a code check and is described that way. Firestore IAM
has no per-collection granularity, so "only the Gate writes gate decisions" is a
convention the code observes, not a boundary the platform enforces.

**The trust root is the builder, who holds project Owner.** No control in this system
defends against him. That is stated plainly here and on camera, because implying otherwise
is the overclaim most likely to be caught.

---

## What this is not

- Not a claim that any agent is safe. One held-out family is one held-out family.
- Not a finished product. Eleven days, one person, one target agent.
- Not reviewed, endorsed, or responded to by Google in any way.

---

## Repository layout

```
contracts/        the frozen schemas, the grammar, the gate rule, the canonicalization
                  spec, and MANIFEST.json with each file's hash. Lanes never edit these.
contracts/golden/ one valid and one deliberately-invalid fixture per contract. The
                  invalid ones must FAIL, and a run where they pass is a broken gate.
crucible/canon/   RFC 8785 canonicalization and the content-addressed identifiers
crucible/ledger/  the run ledger and the policy lineage chain
crucible/policy/  the policy engine
crucible/tripwire/ the breach evaluator and its model-import lint
crucible/warden/  the regression warden
crucible/gate/    promotion
crucible/replay/  the offline replay viewer  <- the judge path
docs/             CONVENTIONS.md is the spine; everything else is downstream of it
scripts/          contract-check.py, verify-chain.py, hash-contracts.py
tests/            including the strawmen - deliberately wrong implementations kept in
                  the tree forever, so every suite can be shown to fail
```

## Verifying the repository itself

```bash
python scripts/contract-check.py             # hashes, fixtures, dead values, status, terms
python scripts/contract-check.py --selftest  # proves each of those passes can fail
python -m pytest tests/ -p no:cacheprovider
```

`--selftest` is not ceremony. On 2026-08-20 the contract gate's own first negative test
could not fail: it mutated its input by appending a newline, which is exactly the mutation
the normalization exists to absorb. It looked green for the same reason a disconnected
smoke detector looks quiet. **A check that cannot fail is not measuring anything**, and it
is the standing rule every part of this build is written under.

---

## Reading order

1. `docs/CONVENTIONS.md` — the spine. Identifiers, frozen numbers, the claim vocabulary,
   and the numbered rulings. Where any other document disagrees with it, it wins and the
   other document is the defect.
2. `contracts/` — what crosses each blindness boundary, and what it must look like.
3. `docs/measurement-spec.md` — what is measured and what makes a run invalid.
4. `docs/architecture-spec.md` — the components and the DSL.

`INVALID` is not `FAILED`. `FAILED` means the system under test behaved badly — that is a
measurement, and it gets published. `INVALID` means the instrument is untrustworthy, which
is the *absence* of a measurement, and no number from an invalid run is reported, including
the ones that look good.

---

## License

**Not yet chosen.** Verified 2026-08-20: there is no `LICENSE` file in this repository and
no license is declared anywhere in it. Under default copyright that means a stranger who
clones this repository has no granted right to use it, which sits badly with a public
repository whose entire value proposition is "replay the evidence yourself." Choosing one
is the builder's call, not a lane's, so this line says what is true rather than what would
be convenient.
