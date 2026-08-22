<!-- Devpost mandatory deliverable: CONTEST.md requirement row 2 ("Text description:
     features, technologies, data sources, findings and learnings"), tracked as
     BUILD-LIST.md T0-5. Separate artifact from project-story.md; does not replace
     it. ADR-0001's word ceiling governs numbered Devpost updates, not this file.

     Nothing has been measured: no attack round has run, no policy has been
     scored, the README results table is all targets with an empty observed
     column. Every claim below is about the build itself, never a measured
     outcome. -->

## Building the checks, not just the system

CRUCIBLE has not measured anything yet. No attack round has run, no policy has
been scored, and the README's results table is still every row a target with an
empty observed column. So this document cannot report what the system found. It
reports what building it found, which turned out to be the more interesting
material: across this eleven-day build, the checks were wrong more often than
the code they were checking.

That is not a complaint about the process. It is the reason the process worked.
Below are the findings worth a stranger's attention, each traceable to a commit
or a file, none of them a result.

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
