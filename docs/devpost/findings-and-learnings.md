<!-- Devpost mandatory deliverable: CONTEST.md requirement row 2 ("Text description:
     features, technologies, data sources, findings and learnings"), tracked as
     BUILD-LIST.md T0-5. Separate artifact from project-story.md; does not replace
     it. ADR-0001's word ceiling governs numbered Devpost updates, not this file.

     SCOPE WIDENED 2026-08-22. Row 2 asks for four things and this file covered
     one. project-story.md covers "features" and is append-only by its own header,
     and it names no technology and no data source anywhere -- which on a contest
     whose Stage One eligibility turns on naming a Gemini model, a Google agent
     framework, and a Google Cloud service is a gap in the submission text, not a
     stylistic one. The stack and the data provenance are therefore stated here.
     Nothing in that section may be aspirational: it lists what is wired and says
     out loud what is only specified.

     SUPERSEDED 2026-08-30. This paragraph read: "Nothing has been measured: no
     attack round has run, no policy has been scored, the README results table
     is all targets with an empty observed column. Every claim below is about
     the build itself, never a measured outcome." That was true when it was
     written on 2026-08-22 and false by 2026-08-25. Six live batches have since
     run against Vertex, policy has been promoted, and one measurement is the
     most substantive finding in the project. The scope rule that replaces it is
     narrower and still binding: NO RATE may be stated -- no attack-success
     rate, no benign pass rate, no transfer figure, no convergence result -- and
     no figure from RESULTS.md may be quoted at all. What may be stated is the
     gate no-op measurement, with the caveats that travel with it. See the
     README's "what is not defensible today" section, which is maintained by the
     build and is the governing text. -->

## Building the checks, not just the system

**Corrected 2026-08-30.** This section opened, from 2026-08-22 until now, with:

> ~~CRUCIBLE has not measured anything yet. No attack round has run, no policy
> has been scored, and the README's results table is still every row a target
> with an empty observed column.~~

Every clause of that is now false, and leaving it up would have understated the
project to a judge in the one document whose job is to say what was found. Six
live batches have run against Vertex AI, policy has been promoted, and the
project's most substantive measurement exists. What has *not* happened is the
thing that sentence was really guarding against, so the guard is restated
properly rather than dropped:

- **No rate from `RESULTS.md` may be quoted, and none appears below.** Every
  figure in that table came from the sixty-bundle batch of 2026-08-25, and the
  offline reader this repository ships **refuses all sixty of them** — ruling 55
  made `episodes[].target_responded` a required property after they were
  written, and the corpus was re-frozen underneath them when instance F5-05 was
  repaired. A figure that cannot be re-derived from the artifact it came from
  stays out of circulation.
- **One measured result is stateable, and it is negative.** Across the fifteen
  bundles the shipped reader *does* accept, **32 rules were promoted: 13 closed
  the breach they were written for, and 19 were no-ops on it**
  (`docs/design/gate-noop-measurement-2026-08-25.md:8-36`, `AUDIT.md` C13). That
  is a recount, dated 2026-08-27: it read ~~"14 bundles, 31 rules, 18 no-ops"~~
  until `pilot-2026-08-25/run-08` finished writing and the reader began
  accepting it, and the recount moved the finding in the *worse* direction. The
  cause is not the Armorer being careless — the tripwire's aggregate clause
  groups by a key the DSL the Armorer must write in cannot express, so a
  well-formed patch can pass every gate and close nothing.
- **The caveat travels with the number.** Those bundles live in `evidence/`,
  which is gitignored. The finding is reproducible on the builder's machine and
  **not from a clone.** It is stated here anyway, because a negative result
  suppressed for being inconvenient to verify is worse than one published with
  its verification boundary attached.
- **Context for why the no-op count was possible at all.** Every promotion
  published before 2026-08-27 came from a gate that checked a patch was well
  formed and that benign traffic survived it, and never that it closed the
  breach it was written for. The two criteria that ask the missing question —
  **G4 attack reduction** and an originating-breach closure check — landed
  2026-08-26 and have since run `mode=ENFORCING` in all 20 bundles of the
  2026-08-27 measurement batch and in the replication batch at identical
  configuration. **12 rules were promoted under enforcing efficacy gates in the
  measurement batch and 14 in the replication batch.**

That measurement is a finding about the harness, not about the target agent, and
it belongs in the same category as everything else in this document. So the
original framing survives its own correction: this document reports what
building the system found, and across this build the checks were wrong more
often than the code they were checking. The gate no-op count is simply the
largest instance of that pattern, and the only one caught by a measurement
rather than by a test failing.

That is not a complaint about the process. It is the reason the process worked.
Below are the findings worth a stranger's attention, each traceable to a commit
or a file, none of them a result.

### What it runs on, and where the data comes from

Four Gemini models, one per role, so that no single model both attacks and
judges: the red team runs `gemini-3.6-flash`, the target agent under test runs
`gemini-3.5-flash-lite`, the coroner that writes the autopsy runs
`gemini-3.5-flash-lite`, and the armorer that proposes policy patches runs
`gemini-3.7-flash`. The agent framework is Google ADK, pinned at
`google-adk==2.1.0` in `requirements.txt`, with enforcement placed at the plugin
layer: a `before_tool_callback` whose non-None return blocks the call before it
executes (`ADR-0005`). On Google Cloud, the target is deployed to Cloud Run and
serving, and Cloud Storage holds three buckets whose IAM separation is the
security boundary rather than a convention. Firestore is provisioned. The
BigQuery export described in `data-spec.md` is specified and not yet wired, and
this document would rather say so than list it.

Everything downstream of those models is deterministic Python with no model call
in it at all: the tripwire that records what the target actually called, the
evaluator that decides whether a breach occurred, the policy engine, and the
promotion gate.

**Corrected 2026-08-30.** That paragraph used to end: ~~"The only third-party
runtime dependencies are `jsonschema` and `PyYAML`."~~ Read off
`requirements.txt`, which is pinned exactly, there are **five** runtime pins,
not two: `google-adk==2.1.0` (the agent framework the target runs on and the
enforcement plugin attaches to), `jsonschema==4.26.0` and `referencing==0.37.0`
(contract and evidence-bundle validation, `$ref` resolution offline),
`PyYAML==6.0.3` (reads the frozen gate rule `gate_rule.v1.yaml`), and
`google-cloud-storage==3.10.1` (the sealed-holdout reader and the real gate's
bucket access). `pytest==9.0.3` is pinned too and is test-only. The
`google-cloud-storage` pin is itself one of this document's findings in
miniature: it was installed on the build machine and named in no dependency file
until 2026-08-28, so a cold clone resolved without it and every live path
touching GCS would have failed at the import — found by adversarial review, and
confirmed by a clean virtualenv that resolved all the other pins and still had
no `google.cloud`. It is not transitive from `google-adk`. The sentence being
corrected here was written before three of those five pins existed and was never
re-derived from the file it describes, which is the same standing-still failure
this document catalogues elsewhere.

The narrower claim the original sentence was reaching for is true and is worth
stating on its own: **the deterministic core calls no model and needs no
credential.** `python scripts/w2-smoke.py` drives an attack against an empty
policy until the refund executes, applies one hand-written rule, and stops the
same attack with no tool executing while a legitimate episode survives both
policies — exit 0, no model called, no credential, no cloud project.

There is no real customer data in this project and there never was. The order
ledger the target reads and writes is seeded with synthetic orders, and the
in-memory stand-in used while the real one was being built is labelled a fake in
its own docstring. The refund policy the target enforces is modeled from ten
published retailer return policies, read directly from the retailers' own pages
(`docs/refund-policy-research.md`), and that document carries a section
separating what is sourced from what is not: every dollar-authority band in the
model policy is the author's synthesis, because no retailer, support platform, or
job posting publishes a frontline agent's refund limit. The abuse patterns the
attack families are built from are sourced the same way, out of industry
return-fraud reporting and refund-fraud-as-a-service material.

The attack corpus is 50 training instances plus a held-out family sealed before
the first patch is written. It was authored by the build lanes, by hand. An
earlier version of this project claimed it was generated by an open-weights model
pinned by version and seed. That claim was false and is withdrawn in `ADR-0018`,
which is finding two below.

### The checks were checking themselves, and mostly they were the defect

A partial list, each one a real commit rather than a category:

- A blind-input boundary was documented in `measurement-spec.md:987-989` as
  "enforced by the function's arity and by a unit test asserting the Tripwire
  module cannot import the corpus label schema." No such test existed anywhere
  in the repo. The property had stayed true by accident since the sentence was
  written (`c675e29`).
- `contract-check.py`'s STATUS pass, the gate that flags an undated claim that a
  thing exists, had roughly a 90% false-positive rate on its first run. It
  could not tell a durable contract statement ("there is no way to write a rule
  that binds only to a tool") from a claim that goes stale in hours ("there is
  no repository yet") (`b44c8ed`).
- A claim-vocabulary gate over the README and the replay viewer could not tell
  a disclaimer from a claim. When the README grew a section stating, correctly,
  "Not production-ready. Not enterprise-grade," all three sentences tripped the
  same gate built to ban those phrases, because it was matching the words, not
  the assertion (`tests/test_replay_view.py`, found 2026-08-21).
- That same test file's README gate hardcoded "18 policy-separated / 4
  approval-oracle-separated" as the expected split to print, which is the
  target stated in `measurement-spec.md` section 8.1, not the split the corpus
  on disk actually produces. The gate was demanding the README print a target
  as if it were a measurement, on the page a judge reads first.
- Two frozen JSON schemas declare the same enum in two letter cases,
  `tool_event.schema.json` upper, `breach_record.schema.json` lower, both
  correct, both hash-locked, neither editable. The policy engine compared
  against only the uppercase form. All 269 authored trace events are spelled
  lowercase, so every one of them silently dropped out of the evaluation window
  (`baf2ccb`, detailed below).
- The target agent's freeze hash covered tool names and parameter names and not
  one line of tool body (`e1122d1`, detailed below).
- A test built to prove that hash covers tool bodies came one commit from
  corrupting the file it was proving it over, when two lanes ran pytest
  concurrently (`8539824`, detailed below).
- One capability class in the taxonomy, `CAP_INVOKES_AGENT`, was exercised by
  zero corpus episodes even after a tool was added specifically to make it
  reachable, so no coverage check built against "does every class appear
  somewhere" could ever have flagged the gap; the class simply never showed up
  to be counted (`2e459a6`).

None of these were found by review. Every one was found by something failing: a
test that should not have passed, a probe that was finally run instead of
assumed, a gate that got pointed at itself.

### Finding one: a blocked attack was recording itself as a breach

`crucible/tripwire/model.py:56` states the load-bearing rule of the whole
measurement: "TOOL_EXECUTED, and only TOOL_EXECUTED, is what the oracle scores
on." `objective_set.py:285` filters the event log down to executed events and
scores breach clauses against that list alone.

On 2026-08-21, running a real ADK `Runner` against the enforcement plugin for
the first time, rather than calling its callback directly, which is all the
existing test suite did, surfaced that a denied tool call was still being
recorded as `TOOL_EXECUTED`, with the fields that would have identified it as a
denial stripped on the way out. The plugin stored the pending attempt before
checking whether the call was allowed, and ADK runs `after_tool_callback`
unconditionally even after a short-circuit denial. Three places in the code
asserted the opposite property, a comment, a docstring, and the ledger writer,
and all three were true only because nothing had ever driven the enforcement
point through a real `Runner` (`ADR-0012`, fixed in `85ee852`).

Traced to what it would have cost: if a blocked attack always records as
executed, `breached_at_vFinal` never falls no matter how good the learned
policy gets. The promotion gate only advances when attack success drops, so
every correctly working patch would have been rejected, two rejections in a row
would trigger `HALT_HUMAN`, and the run would have reported that the loop
stopped learning while the loop was working and the instrument was lying. A
differential check between the Tripwire and the Warden's reference engine could
not have caught it either. Both engines read the same poisoned ledger and would
have agreed with each other, which is a different thing from agreeing with the
truth.

### Finding two: a false claim survived an ADR, four specs, and a shooting script

`ADR-0009` recorded, as an accepted decision, that the attack corpus is
generated by an open-weights model (Gemma) pinned by version and seed, and
scripted a sentence to be spoken on camera about why that makes the result
pre-registered. On 2026-08-21, checked against the repo for the first time
since it was written: Gemma appears in zero executable code, the module its
architecture depended on was never built, and every training instance's git
history reads "authored by the lane agents," not generated. The claim had never
been true.

It had been edited once, the day before, for how it sounded. A correction note
sits directly beneath the sentence recording that pass. Nobody asked, in that
edit, whether the sentence was true. `ADR-0018` withdraws it and replaces it
with the actual, and stronger, mechanism: the corpus was authored and sealed
before the first patch was written, the commitment is a public timestamped
hash (`sealed-family-commitment.json`), and the identity that writes patches
cannot read the sealed set (`armorer-403.txt`). A commitment does not care how
the corpus was produced; it only cares that nothing moved afterward, which is
the property a skeptical reader actually doubts. Reproducibility was the weaker
argument for the stronger fact.

### Finding three: a target hash that locked the label, not the thing

`target/refund_agent`'s freeze hash was meant to let every measured number cite
the exact agent it was measured against. Its payload covered the capability
manifest and `tool_signatures()`, which is tool names and parameter names, and
nothing else. A statement inserted into a tool's body left the hash unchanged.
A target could be frozen, then silently rewritten to approve everything, and
every result produced afterward would still cite the same hash as evidence of
what was tested (`e1122d1`). Fixed by hashing the actual bytes of every runtime
module, asserted against the file list in both directions so a rename cannot
quietly drop a module out of the lock and a new module cannot quietly sit
outside it.

The fix immediately created its own hazard: a test proving the new hash
responds to a tool-body change works by writing a marker into the live source
file, hashing, and restoring it. Two lanes hit that test at the same moment
under concurrent pytest, both wrote the marker, both restores raced, and the
file was left corrupted, with the day-3 freeze scheduled for the next morning
(`8539824`). Caught by diffing against git before commit, not by the test
itself. The fix was three guards: a lock file so runs cannot interleave, a
pristine check that refuses to "restore" an already-corrupted baseline, and a
verified restore that re-reads from disk and raises rather than trusting a
`finally` block that could fail silently.

### Finding four: the documented fix for a Cloud Run error would have breached our own IAM boundary

Deploying to Cloud Run hit a 403 before the build even started: Cloud Build's
default identity could not read the source bucket. The standard fix documented
for that error is granting `roles/cloudbuild.builds.builder`. Read directly out
of that role's permission list: full read, write, and delete on Cloud Storage at
project scope, which would have handed the build identity the exact access the
sealed-corpus bucket's IAM boundary exists to deny (`deploy/RUNBOOK.md`, gate
`G7`). The narrower fix, `storage.objectViewer` scoped to the source bucket
only, plus two other project-level roles that touch no storage, solved the same
error without widening the boundary the whole project's separability claim
depends on. Two more real defects surfaced in the same deploy: the container
image does not include anything outside the agent folder by default, so the
tool package silently fails with `ModuleNotFoundError` at runtime rather than at
build time, and the generated Dockerfile bakes in a regional endpoint while the
frozen target pins the global one, so the deployed agent would have resolved a
different model than the one every number in this project describes.

### Finding five: the freeze protocol could not be run in the order it was written

`ADR-0017` specifies the day-three freeze of the target agent as eight numbered
steps, and it was written that way precisely so the freeze would not be
improvised at hour seven of the heaviest day in the plan. Step 6 clones the
repository cold and re-checks the hash from a clean checkout, which is the step
that catches a canonicalizer fooled by line endings. Step 7 commits the frozen
record. Executed in that order, on 2026-08-22, the cold clone had no frozen
record to compare against and could only recompute the hash, which is the weaker
of the two assertions the step could make. It recomputed the identical value, so
the line-ending trap was cleared either way, and the record was then committed
and the clone re-run to get the comparison the step was written for
(`docs/proof/d3-target-freeze-2026-08-22.txt`).

The defect is small and the way it survived is not. That ordering was written as
an architecture decision record, reviewed, and cited by three other documents
before anyone executed it. A protocol whose steps cannot be run in the order
written is a protocol nobody has run, and no amount of citation makes it one. The
same shape appears twice more in this list: a documented property with no test
behind it, and a decision record asserting a mechanism that did not exist.

### What generalizes

Ask every check what change it would fail to notice. A hash is only as good as
what it actually covers, and the coverage is never obvious from the field name.
A search that reports clean is sometimes just unable to see what it is looking
for, and that happened three separate ways in one build. A guard enforcing the
wrong number is worse than no guard, because it looks like the number was
checked. None of this is a claim that CRUCIBLE's verification machinery is now
correct. It is a claim that it has been shown to fail loudly at least once,
which is the only property a check can actually earn.

[github.com/emtcmca/crucible](https://github.com/emtcmca/crucible)
