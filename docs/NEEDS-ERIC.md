# Needs Eric

Open items that need the owner's call, newest first. **This file is the only
list.** A decision that lives only in a transcript is gone at the next `/clear`.

Nothing here is blocking the coordinator from other work — everything blocked is
noted as such.

**Swept against the repo 2026-08-22 (Day 3).** Items 1 and 3 closed; items 4 and 5 now have
drafted answers waiting on your ratification rather than open questions waiting on your
writing; item 9 was re-checked and is genuinely still open. **Two new items, 11 and 12, are
above everything else on this list** — item 11 decides whether any run can score at all.

---

## 11. **G7c — CLOSED 2026-08-22, same day it was opened.** No longer gates a run.

**Written while a parallel lane was closing it.** Two lanes ran simultaneously: one swept the
documents and recorded G7c as unevaluable; the other enabled audit logging and built the reader.
Neither could see the other. The text below is what the sweep found; everything after it is
what actually happened, and the sequence is kept rather than overwritten because *the record of
two correct lanes disagreeing about the present tense* is worth more than a clean page.

> ~~The live project has no `auditConfigs` block, so those entries are not being written and
> the number does not exist to be read. `contracts/gate_rule.v1.yaml:170` routes
> `absent_or_unevaluable` to **RUN INVALID**, so as things stand a completed run scores
> nothing.~~

**What was done, in the order it happened.**

1. **Data Access audit logging enabled**, 2026-08-22. `auditConfigs` for
   `storage.googleapis.com`, `logType: DATA_READ`. Applied from a backed-up policy with a
   diff proving only that key was added; **all 18 bindings verified byte-identical afterwards.**
2. **The reader was built** — `infra/holdout_touch.py` — because enabling the log was necessary
   and **not sufficient**: `probe-g7-g8.py` passed `holdout_touch=None`, hardcoded. Nothing read it.
3. **`G7c` now evaluates. 16 assertions, 16 PASS** — the first time G7 has been fully evaluable.

**Option 2 in the original item — accept it as permanently unevaluable — was not taken, and the
defaulted zero was never on the table.**

> **The counter had to learn that an ENTRY IS NOT A TOUCH.** Measured rather than assumed: a
> recursive listing emits **four** log entries including an `objects.get` on the *prefix*; a
> single content read emits **three**, because metadata and media are separate fetches; a
> **denied** read is logged too; and one real entry came back `granted: true` **with status code
> 5** (NOT_FOUND on a prefix). An implementation reading only `authorizationInfo[].granted`
> counts that last one as a read of the holdout. The same log also carries `iamcredentials`
> token-mint entries, one per impersonation — so a filter keyed on log name alone counts a **G7a
> probe** as a seal touch.

> **Five routes to a fabricated zero all RAISE instead**, the load-bearing one being a **canary
> query**: the same filter over the whole attestable window must match at least one entry before
> any count is trusted, so a misspelled bucket or a renamed log surfaces as UNEVALUABLE rather
> than as a clean seal. **Coverage begins 2026-08-22T19:31:10Z** — not when the config was
> applied, but the earliest instant coverage has been *shown*, because a probe at 18:27:30Z left
> no entry and denials are logged, which makes that evidence of absence. G7c attests forward from
> there and says nothing about the seal's lifetime since 08-20.

**Still open and stated rather than covered by silence:** the `auditConfig` names storage only,
so a read of the sealed **BigQuery dataset** counts as zero touches. Closing it is a second
`auditConfigs` entry — a project-IAM write, not made.

**The spec half is settled and needs no ruling.** `measurement-spec.md` said the count was
all-time with a ceiling of 2, against its own `:869`. **The hash-locked contract decides it:**
`contracts/gate_rule.v1.yaml:205` reads `expected_for_this_phase`, contracts outrank
`measurement-spec`, and that file was frozen at `cff9f52929397efb` before anything was measured.
The merits agree independently — the "2" counts the two legitimate measurement *phases*, and one
phase reads 18–24 sealed instances, so an all-time ceiling of 2 would mark the run INVALID **the
first time it was used correctly.** A guard that fires on correct behaviour is not a guard.
`measurement-spec.md` §7 guard 2 is corrected.

---

## 12. **Should the touch counter exclude the canary prefix?** · NEW 2026-08-22

`gs://crucible-sealed-x7/families/_probe/canary.txt` is **not sealed material** —
`infra/prove-armorer-403.sh` wrote it and says so in its own output — and it exists so the
G7a impersonation probe has something to read that is not a sealed instance. But
`real_gate._probe_argv` lists `families/**`, which matches the canary.

**So if the counter counts everything under `families/`, the gate's own positive control
increments the number the gate asserts.** Under the all-time-ceiling reading corrected in
item 11, running the gate probe three times would have invalidated the run before a single
measurement happened.

**Proposed: scope the counter to objects under `families/` and EXCLUDE `families/_probe/`.**
Small, and it is the kind of thing that is obvious once written down and invisible once
shipped. It needs your word because it changes what a gate counts.

*(Related and worth knowing: `python -m corpus` reports **`sealed: 0`**. No sealed instance
exists yet, so nothing has been touched, because there is nothing to touch.)*

---

## 1. Fire the Cloud Run deploy · **CLOSED 2026-08-21** · was Stage One pass/fail

**Fired on Eric's instruction and serving.** `crucible-00003-t2q`,
`https://crucible-vgp5owkxyq-uc.a.run.app`, authenticated, running as
`crucible-target`. `/list-apps` returns `["refund_agent"]`, and one full episode
ran end to end against it - the agent called `lookup_order("ORD-4471")` and
answered from the seeded record.

Proof: `docs/proof/cloud-run-deploy-2026-08-21.txt`. Full write-up of the three
defects it took to get there: `deploy/RUNBOOK.md`.

**ALL FOUR POSTCONDITIONS CLOSED 2026-08-21** (commit `b4e060e`). Both screenshots are
in `docs/proof/`: `cloud-run-console-2026-08-21.png` - service green, `us-central1`, URL
readable, `Scaling: Auto (Min: 0, Max: 20)` - and `trace-explorer-spans-2026-08-21.png`,
36 spans over 12 hours. **Nothing is owed on this item except using them on camera.**

> **A caveat for the narration, not a reopening.** PC3 as written demanded *"an
> `execute_tool` span carrying `gen_ai.agent.name`."* The span names visible in the
> capture are `invocation`, `invoke_agent refund_agent`, `call_llm`,
> `generate_content gemini-*`, `/run` and `/list-apps`. **`execute_tool` is not among
> them** - the facet list is truncated behind "Show more", so it is not proven absent
> either. Say *"the deployed agent's spans are in Cloud Trace"*, which the capture fully
> supports. Do not say *"here is the `execute_tool` span"* unless someone re-opens the
> console and confirms it.

**How it closed is the finding.** Four separate times that day this project concluded "no
traces exist" from an instrument that could not see them - three legacy
`projects.traces.list` v1 queries and one console window that did not contain the episode.
**Repeating a blind check is not a second opinion.** Changing the instrument settled it.
`trace-explorer-1h-empty-window-2026-08-21.png` is kept deliberately as the negative
control.

**The Day-2 schedule paid for itself.** ADK bakes `GOOGLE_CLOUD_LOCATION=<region>`
into the image, while the target pins the **global** endpoint and hashes
`"endpoint": "global"` into the D3 freeze - so the deployed agent was resolving its
model through a different endpoint than the measured one. Found 08-21 with nine
days of slack. Found on Day 10, it is the demo.
---

## 2. The corpus counts · **RESOLVED 2026-08-21 — Eric ruled to AMEND, not retire**

Branch **`corpus/C6-reach`** holds four correct instances that make
`CAP_INVOKES_AGENT` reachable. `delegate_to_specialist` was added to the target
pre-D3 at real cost because that class was uninstantiable — and then no instance
ever called it, so **one sixth of the capability taxonomy is exercised by zero
episodes** and `r_new11` could never fire, be learned, or be falsified.

**Merged.** Eric ruled to amend the frozen counts rather than retire instances,
because all 12 original near-misses are load-bearing for separability pairs. The
counts are now: **F5 = 10** (was 8), **training total = 50** (was 48), **benign =
26** (was 24), **near-miss = 14** (was 12). Every other family is still 8.

Underneath is an older defect that this did **not** close: `measurement-spec.md`
§1.3 requires **≥3 of F5's instances to route through `CAP_INVOKES_AGENT`**, and
only **2 of the 10** do (F5-09, F5-10). This is a known, reported deviation — the
≥3 floor is not lowered to fit the measurement.

> **This gated item 3 below.** Item 2 is now settled, so item 3's blocker is
> cleared — the gate rule freeze should now pin `bpr == "26/26"` (denominator
> permanently fixed) and `near_miss_bpr == "14/14"`, ruling 43, `corpus/C6-reach`,
> not the old 24/24 and 12/12.

---

## 3. The D2 gate-rule freeze · **CLOSED 2026-08-21 — FIRED**

Your ruling was "hold until GX5 is completed." GX5 landed (ruling 42,
`SPINE_VERSION 10`, contract C4 re-hashed, suite green).

**Previously held because the reason to hold changed after you gave the
ruling.** The gate rule as drafted pinned the benign denominator at 24 and near-miss at
exactly 12, so freezing would have decided item 2 by side effect rather than by ruling.
**Item 2 is now resolved by ruling (amend, not retire)**, so that reason no
longer applies — the gate rule should be drafted (or corrected, if already drafted
against the old counts) to pin `bpr == "26/26"` and `near_miss_bpr == "14/14"`
before it is hash-locked.

**Fired 2026-08-21, and it pinned the corrected counts.** `contracts/gate_rule.v1.yaml:90-91`
carries `bpr == "26/26"` and `near_miss_bpr == "14/14"`, so the freeze did **not** decide item 2
by side effect - which was the whole reason it was held. Frozen `gate_rule_hash`
**`cff9f52929397efb`**, recorded with its commit and timestamp in
`docs/proof/d2-gate-rule-freeze.json`. *(The dry run read `834bc7113a13beea`. That value is now
DEAD - it is the pre-correction draft - and it still sits as a synthetic literal in
`scripts/make-golden.py`'s C7 fixture, where it is fixture data rather than a claim.)*

---

## 4. Track fit — the honest problem · **ANSWER DRAFTED 2026-08-21, AWAITING YOUR CALL**

Fortified Enterprise Fleet asks for *"a scalable network of institutional agents"*
that *"maintain context across weeks of asynchronous operations."*

CRUCIBLE is neither, and **cross-episode state is named as out of scope in our own
specs.** Stage One is pass/fail on "reasonably addresses a Challenge."

The Stage Two sub-criteria for the track are much friendlier — multi-agent
complexity and delegation to specialised sub-agents, both strong here. But the
submission text should meet the track's own language head-on rather than route
around it. This is a writing problem, not a building one. `docs/contest/CONTEST.md`
§3 lays out the options.

**The deeper answer now exists and needs ratifying rather than writing.**
`docs/contest/track-fit.md` (2026-08-21) breaks the track language into five separately
checkable requirements, says where CRUCIBLE meets each, partially meets it, or does not,
tests three candidate framings, names what we will explicitly refuse to claim, and carries
draft submission text. **What is still yours: pick the framing.** Nothing in that document
is a result, and it says so on its own first page.

---

## 5. The "unlikely hero" · **PERSONA DRAFTED 2026-08-21, AWAITING YOUR CALL**

A named Stage Two sub-criterion for this track: *"Did they build this for an
'Unlikely Hero' outside of standard corporate roles?"* No persona exists anywhere
in the project.

The honest candidate is not a security engineer — it is the **operations lead who
inherits an agent somebody else built** and has to decide whether it is safe to
give it the company card. Real role, outside standard corporate security, and
genuinely who this serves.

A persona invented to satisfy a rubric reads exactly like a persona invented to
satisfy a rubric, so this is yours rather than mine.

**It has been written down: `docs/contest/unlikely-hero.md` (2026-08-21).** It names exactly
the operations lead described above — someone who did not build the refund agent they now run,
whose question is not "does it work" but "do I give it the company card". It reports no results
and says so in its own header. **Still yours: whether this persona is true enough to say out
loud, or whether it reads as rubric-chasing.** That judgement has not been made for you.

---

## 6. The bonus point nobody is claiming · **+0.4 for an afternoon**

Final scores run 1 to **6**, not 1 to 5. Up to **1.0** comes from Stage Three, and
almost none of it depends on the loop working:

- **+0.2** — publish a build write-up anywhere public, with text saying it was
  created for this hackathon.
- **+0.2** — one public post carrying **`#AllThingsAgenticHackathon`**.
- **+0.2 each, max +0.6** — additional Google AI models. **Corrected 2026-08-21: Gemma was NOT 'nearly free'. It was never built** — see `ADR-0018`. `BUILD-LIST.md` T1-4 holds a live alternative that does real work.

**A full point is twenty percent of the Stage Two maximum.** You already write
publicly.

> One caution: do not bolt Veo or Lyria on to farm 0.2. A decorative integration
> reads as decorative and costs more on the 30% architecture criterion than it
> gains in bonus.

---

## 7. `ADR-0010` versus "unedited, live execution"

The rules say the video should show *"an unedited, live execution of the agent
performing its task."* `ADR-0010` has some demo beats replaying stored evidence
bundles for quota reasons.

Either move more beats live, or label replayed beats as replay on screen. Leaving
a replay looking live is the one version that could actually cost us.

---

## 8. `r_new3` fails validator check V4 — **CLOSED 2026-08-21**

Fixed. It named `RISK_CLEARED, IDENT_CLEARED, FLAG_REMOVED`, none declared in Part A, so V4
refused it — **and it also matched nothing real**, blocking zero calls while being
unpromotable. Rewritten to `status_to in [APPROVED]`, read out of the instances rather than
chosen: `F1-03` writes `APPROVED`, `NM-F1-03` writes `PENDING`.

Eight tests including two negative controls; four fail red on the pre-fix file. Closed at all
three sites — the rule, `corpus/pairs.json`, and `architecture-spec.md`.

> **The prose was wrong too, and differently wrong in each place.** The worksheet row said
> `RISK_CLEARED` vs `RESOLVED`; `pairs.json` said "out-of-enum" vs `CLOSED`; the instances say
> `APPROVED` vs `PENDING`. `RESOLVED` is not declared either, and the broken rule never named
> it, so fixing the rule could not have surfaced it. **Only the rule is machine-checked.** V4
> caught it the moment it ran; nothing checks a sentence, so three descriptions of one pair
> drifted apart unnoticed — in the artifact `BUILD-LIST` T2-3 wants to show judges as the
> hypothesis ledger.
---

## 9. `ORD-13` / `ORD-14` were authored after your review pass · **STILL OPEN 2026-08-22**

So *"the ordinary benign set was reviewed"* is not true of the set as it stands.
Two fixtures to skim.

**Re-checked 2026-08-22: still open.** The two retirements they replaced have a ratification
record (`docs/proof/benign-retirement-ratification.md`) and the sealed family has one; these
two have neither. That file's own closing paragraph asks for exactly this before D5. **It is
two fixtures, and it stands between the corpus and a true sentence about it.**

---

## 10. Gemma provenance — **RULED 2026-08-21. CLOSED.**

**Eric's ruling: supersede now, decide the build later.** Executed the same hour.

- **`ADR-0018`** withdraws the claim and supersedes `ADR-0009`. `ADR-0009` stays on disk,
  unedited below its status line, because the record of a claim made, checked and withdrawn is
  worth more than a document that appears always to have been right.
- **`execution-spec.md:532` — the on-camera line — is corrected.** It now says what is true:
  the corpus was authored, then sealed and committed before the first patch, with a public
  timestamped commitment and an IAM boundary the patch-writing identity cannot cross.
- **Five further sites marked** in `execution-spec`: the Day-7 build item (which would
  otherwise have been built from that line), the regenerate-twice artifact (which proved a
  property we do not have and is **no longer owed**), cut candidate 2, the +0.2 bonus claim,
  and the ADR index row.
- **Whether Gemma gets a real job is deliberately still open**, revisited around D5–D7 when
  the corpus freeze and first loop run give better information. Deferring costs nothing;
  leaving a false statement in a shooting script for five more days did.

**The replacement claim is stronger than the one it replaces, which is the part worth
keeping.** `ADR-0009` argued regenerability is what makes the result pre-registered. It is
not — the commitment is, and a commitment does not care about provenance, only that nothing
moved afterwards. The false line was arguing for a *weaker* property than the one we can
actually demonstrate.
---

## Closed since the last list

- **GX5** ruled and landed. Ruling 42, `SPINE_VERSION 10`.
- **Spend cap** — found. $160, right project, all credits included. **It is an
  alert, not a cap**; nothing stops at $160. `docs/ops/billing.md` has the JSON
  and both options. Building the Pub/Sub kill switch is still yours to decide, and
  I would not build it unwatched: a Cloud Function that can detach billing is a
  loaded weapon pointed at the demo.
- **Two retired benign fixtures** ratified.
- **The sealed family** ratified at 24, commitment published.
- **The D2 gate-rule freeze** fired 2026-08-21 — item 3 above, `cff9f52929397efb`.
- **The Cloud Run screenshots** captured 2026-08-21 — item 1 above. **The video is now the
  only Stage One deliverable that does not exist.**
- **The Objective Set freeze** fired 2026-08-22 — the fourth of five hash-locks,
  `19493e53a6d79d0b`, ruling 44, `SPINE_VERSION 12`. Your ruling that day also corrected C10
  itself: the contract argued its annotations were inside the hash and **won on precedence**,
  then lost anyway, because the value it would have frozen is one no episode can ever carry.
- **The target re-freeze** fired 2026-08-22 after `delegate_to_specialist` was repaired — and
  then re-fired twice more the same day. **Current values: `cat target/refund_agent/FROZEN.json`.**
  Ruling 46 forbids restating them here; this line named the second of four and was stale within
  hours of being written.
  **The finding was not the re-freeze.** A hash-locked package changed, the hash moved, and
  1011 tests stayed green with `contract-check` ALL PASSES OK. A skew detector now catches it.
