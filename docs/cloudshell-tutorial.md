# CRUCIBLE — see it work in five minutes

<walkthrough-tutorial-duration duration="5"/>

You are in a free Google Cloud Shell VM with this repository already cloned. Nothing
here costs you anything, calls a model, or touches a project of yours.

**What CRUCIBLE is.** A red-team agent attacks a target agent that holds real
permissions — it can refund money and email customers. A pure-code tripwire records
what the target actually *called*, not what it said. A Coroner writes the autopsy but
cannot propose a fix. An Armorer proposes policy rules but cannot promote them. A
pure-code gate promotes or rolls back. Every component is deliberately blind to
something, because a system that grades its own work is not measuring anything.

**What this tutorial shows.** The parts that are pure code and therefore need no
credential: the checker that proves it can fail, the policy language that refuses to
learn a string filter — including its refusal to quote an attack back at you — and the
offline evidence reader. Click **Next** to start.

The full attack loop is **not** run here. It needs Vertex AI and a billing account of
your own. Step 6 says exactly what it is and where the proof of it lives.

## Step 1 — the ninety seconds

If you read one step, read this one.

A hardening harness whose checker cannot fail is a harness that reports success no
matter what the agent did. CRUCIBLE ships nine hand-written known-bad fixtures and
seven deliberately broken checkers ("strawmen"), and the boot self-test refuses to
start unless every fixture returns its own expected verdict and every strawman is
caught.

Set up — about twenty seconds. The three packages are read straight out of
`requirements.txt`, so there is no second copy of a version pin:

```bash
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ~/cloudshell_open/crucible)"
python3 -m venv .venv && . .venv/bin/activate
pip install --quiet $(grep -E '^(jsonschema|referencing|PyYAML)' requirements.txt)
```

*(Cloud Shell opens the terminal inside the clone, so the first line is usually a
no-op. It asks git where the repository root is rather than assuming a path, and falls
back to the standard clone location if you opened a plain terminal.)*

Now run the self-test:

```bash
python -m crucible.tripwire --selftest
```

**What to look for in the output — three things:**

1. **The verdict column has five different values, not nine failures.** KB1–KB4 and
   KB7 expect `BREACH`; KB5 expects `REJECT`, KB6 `INVALID`, **KB8 expects `CLEAN`**,
   KB9 a two-stage linter verdict. A blanket "all nine must fail" assertion fails on
   KB8 by design. That is the difference between a suite that tests the checker and a
   suite that tests nothing.
2. **Seven strawmen, all caught.** `blanket_breach` is the checker that calls
   everything a breach. `prose_reader` is the checker that scores what the agent
   *said* instead of what it *called*. `tool_identity_only` is the one that watches
   tool names instead of capabilities. Each is a wrong implementation someone would
   plausibly write, kept in the tree so the suite has something it must fail.
3. **`import lint clean`.** An AST pass over the tripwire package proving it imports
   no model client. The tripwire's blindness is enforced by code, not by a promise.

The last line reads `ALL EXPECTED`. The command exits non-zero if it does not — a
self-test that prints a problem and still exits 0 is a check that cannot fail.

## Step 2 — try to break the policy language yourself

This is the part worth typing.

When the loop learns a fix, it writes a **rule**, in a small language with three verbs
— `deny`, `constrain_arg`, `require_approval` — and no `allow`. Rules bind to
**capability classes** such as `CAP_MOVES_MONEY`, never to a tool name and never to a
string from the attack. That constraint is the whole claim: a language that *cannot*
express a string match cannot learn a string filter, so a rule learned on one tool
transferring to a tool it has never seen is true by construction rather than by
discipline.

Four rules — two the language admits, two it refuses:

```bash
python scripts/try-a-rule.py --demo
```

Both refusals are rules a competent engineer would write on the first try. Now write
one yourself. Anything naming a tool the way a person would is refused:

```bash
python scripts/try-a-rule.py "rule r_new1: cap:CAP_MOVES_MONEY when lookup_order.order_id is present => deny"
```

`E_PRODUCT_IDENTIFIER`. The denylist is not a list someone typed — it is harvested at
run time from the target's own tool names, so you can re-derive it:

```bash
python scripts/try-a-rule.py --lexicon
```

One more, and it is the sharpest one. `UNCLASSIFIED` is the sentinel for a tool whose
capability nobody has mapped yet:

```bash
python scripts/try-a-rule.py "rule r_new1: cap:UNCLASSIFIED => deny"
```

Read that refusal in full. On an unseen target every tool is `UNCLASSIFIED` until the
manifest maps it, so a single rule saying `cap:UNCLASSIFIED => deny` would block
everything on a new target and report **100% transfer, for free**. The validator
refuses it explicitly, and says so in the error, because the alternative is a headline
result that is manufactured rather than measured.

**What to look for:** the accepted rules come back with an `r_`-prefixed `rule_id`. The
model never wrote it. It emits the placeholder `r_new1` and the validator computes the
hash from the canonical rule body — because a model asked to produce a SHA-256 will
produce something that looks like one, and the next guess lands somewhere nobody can
see.

## Step 3 — the same rule, accepted and then refused

One more refusal, and it is the one that decides whether the transfer claim means
anything.

A rule is not allowed to quote the attack it was learned from. The Armorer cannot
invent an attacker's prose — the grammar has no free strings — so the realistic way a
string filter gets into the policy is that an **attack payload quotes DSL-shaped text
and the Armorer parrots it back**. Run the controlled pair:

```bash
python scripts/try-a-rule.py --payload-demo
```

**What to look for: the rule text is byte-identical in both halves.** Judged against an
empty corpus it is `ACCEPTED` and gets a computed `rule_id`. Judged with that one
payload in the corpus it is `REFUSED` with `E_PAYLOAD_SUBSTRING`, and the error names
the exact eight-token run it reproduced. Nothing changed but the corpus.

That is the whole argument in one command. A rule that quotes an attack would score
perfectly against that attack and transfer to nothing, so the headline transfer result
would be an artifact of memorisation. The validator refuses it rather than trusting
whoever wrote the rule to have been disciplined.

## Step 4 — read the evidence with no credentials at all

An evidence bundle is what a run produces. Reading one takes a path and nothing else —
no project flag, no credential file, no endpoint:

```bash
python -m crucible.replay contracts/golden/C6-evidence_bundle.valid.json
```

**Read this label before you read the output.** That file is the golden *contract
fixture* for the bundle schema — a hand-authored instance kept in the tree so the
viewer and the schema can be exercised without a run. Its `run_id` is synthetic.
**It is not a result, and no figure in it is a measurement.** It is here to show you
what the reader checks and what the reader refuses, not to tell you how CRUCIBLE
scored.

**Where the real bundles are, and why they are not in your clone.** Live runs have
happened and they do produce bundles this same command reads. `evidence/` is
gitignored, so those bundles are on the builder's machine and are **not publicly
verifiable** — the repository's own Status section says so, in those words. Do not
take anything in this tutorial as a measured result. The README's `Observed` column is
the only place a measurement is allowed to appear, and it says what it says.

**What to look for:**

- **The `INTEGRITY` table prints the *kind* of each check**, not just a checkmark:
  `RECOMPUTED` (derived again from the bytes on disk and had to agree),
  `CROSS_CHECKED` (two independently written fields had to agree), `PRESENT` (a
  required field exists). Comparing a stored hash to itself would pass on a truncated
  write, a partial write and a corrupted read, so the kind is printed rather than
  assumed.
- **`POLICY_CHAIN` says what it cannot do.** The chain is unsigned; it detects
  accidental mutation and post-hoc editing, not an adversary holding the gate's
  credentials. It names its own limit.
- **The `LABELS THAT TRAVEL WITH EVERY FIGURE` block at the bottom.** `k = 1`,
  single-sample, no stability estimate. The target model tier, named because a weaker
  target flatters every number taken against it. And a trust root that says out loud
  that the builder holds project Owner and no control here defends against him.
- **The viewer states no rate.** It prints a census of what is in the file and the
  labels any figure from it must carry, because a rate needs a denominator decision
  and that decision belongs to the component that owns the measurement.

## Step 5 — the whole thing, if you want it

Everything above ran on three small packages. The full suite additionally needs the
pinned Agent Development Kit and pytest, which take a minute or two to install:

```bash
pip install --quiet -r requirements.txt
python -m pytest
python scripts/contract-check.py
```

`contract-check` is the gate on the contract set: it re-hashes every contract against
its manifest, validates every golden fixture, requires every known-bad fixture to
fail, sweeps the documentation for values that have been corrected, and rejects any
present-tense claim about an artifact that carries no date. It has a `--selftest` of
its own that proves each of the five passes can still fail.

## Step 5b — one live model call, on YOUR project

Everything so far ran without a credential. This step does not: it makes one real
call to Vertex AI, billed to whatever project your Cloud Shell is pointed at.
**Skip it if you would rather not spend anything.** It is a few hundred tokens.

Cloud Shell already has your credentials and a project set, so there is nothing
to configure:

```bash
gcloud config get-value project
python scripts/gemma-live-probe.py --project "$(gcloud config get-value project)"
```

That goes through `crucible/cartographer/vertex.py` — the same
`make_completer` the Cartographer uses in a real run — so the endpoint, the
model id, the seed and the temperature on your screen are the ones the project
runs, not a demo path written to look like them.

It asks Gemma to classify one tool into one capability class. That is the
Cartographer's whole job: **it classifies tools, it does not author attacks.**
`ADR-0018` withdrew the claim that Gemma generated the attack corpus and ruled
that the sentence may not be written or spoken anywhere.

**If it fails**, the two likely reasons are that `aiplatform.googleapis.com` is
not enabled on your project, or that managed Gemma is not offered to it in Model
Garden. Neither is a defect in CRUCIBLE and the probe prints the error rather
than a traceback.

## Step 6 — what was deliberately not run here, and where the rest is

The attack loop itself — red strategist, target agent, Coroner, Armorer — calls Gemini
on Vertex AI. Running it needs a Google Cloud project with billing that belongs to
you, so this tutorial does not ask you for one. A tutorial step that fails on your
machine would be worse than no step at all.

**And billing alone would not be enough, which is worth saying plainly.** `--live`
does more than switch the models on. It points the policy store at a GCS bucket and
wires the holdout counter to this project's Cloud Logging data-access records, and
gates G7 and G8 assert against both. Those are *this* project's buckets and *this*
project's audit log. Running the loop against yours would need three buckets, the
IAM grant direction between them, and data-access logging enabled — which is a
deployment, not a tutorial step.

**The offline mode deliberately refuses to fake it.** Run without `--live` and the
gate is constructed with `skip_cloud=True`, which records G7 and G8 as UNEVALUABLE
rather than as passed, because an unevaluable gate is a check that cannot fail.
Verified 2026-08-31 at `crucible/conductor/campaign.py:766`: the offline branch
passes `holdout_touch=None`, and that argument has no default precisely so that
"nothing computed this" cannot be read as "the count was zero". This step therefore
ends with a limitation instead of a command.

What to read instead:

- **`README.md`** — the claim, the evidence, and a status section that says plainly
  what has and has not been measured.
- **`docs/diagrams/architecture.md`** — how Gemini, Cloud Run, Firestore, GCS and
  BigQuery connect, in rendered diagrams.
- **`docs/proof/`** — transcripts rather than assertions, including
  `armorer-403.txt`: the Armorer being denied write access to the policy bucket, with
  a positive control proving the denial was the boundary and not a broken command.
- **`docs/what-crucible-is.md`** — the long version, in plain English.

Close this tab when you are done. Nothing was created in your project, and Cloud Shell
reclaims the VM on its own.
