# Needs Eric

Open items that need the owner's call, newest first. **This file is the only
list.** A decision that lives only in a transcript is gone at the next `/clear`.

Nothing here is blocking the coordinator from other work — everything blocked is
noted as such.

---

## 1. Fire the Cloud Run deploy · **CLOSED 2026-08-21** · was Stage One pass/fail

**Fired on Eric's instruction and serving.** `crucible-00003-t2q`,
`https://crucible-vgp5owkxyq-uc.a.run.app`, authenticated, running as
`crucible-target`. `/list-apps` returns `["refund_agent"]`, and one full episode
ran end to end against it - the agent called `lookup_order("ORD-4471")` and
answered from the seeded record.

Proof: `docs/proof/cloud-run-deploy-2026-08-21.txt`. Full write-up of the three
defects it took to get there: `deploy/RUNBOOK.md`.

**Two of the four postconditions remain, and both are screenshots** - the Trace
Explorer span and the Cloud Run console page. Those are the pass/fail video
requirement. Trace export is UNVERIFIED rather than failed: the legacy v1 trace API
shows nothing, which it may simply be unable to see. The console settles it.

**The Day-2 schedule paid for itself.** ADK bakes `GOOGLE_CLOUD_LOCATION=<region>`
into the image, while the target pins the **global** endpoint and hashes
`"endpoint": "global"` into the D3 freeze - so the deployed agent was resolving its
model through a different endpoint than the measured one. Found 08-21 with nine
days of slack. Found on Day 10, it is the demo.
---

## 2. The corpus counts, and it is now urgent · blocks the D2 freeze

Branch **`corpus/C6-reach`** holds four correct instances that make
`CAP_INVOKES_AGENT` reachable. `delegate_to_specialist` was added to the target
pre-D3 at real cost because that class was uninstantiable — and then no instance
ever called it, so **one sixth of the capability taxonomy is exercised by zero
episodes** and `r_new11` can never fire, be learned, or be falsified.

They are parked, not merged, because they break two frozen counts: **F5 = 10
against a frozen 8**, and **benign = 26 against a permanently-fixed 24**.

Underneath is an older defect: `measurement-spec.md` §1.3 requires **≥3 of F5's 8
to route through `CAP_INVOKES_AGENT`**, and the authored eight route **zero**. The
same is true of F3.

**Three options.** Retire two F5 attacks and two benigns and let these take the
slots (my recommendation — it fixes the §1.3 defect too). Or amend the counts by
ruling. Or discard the branch and accept that a sixth of the taxonomy is untested,
which I would not.

> **This gates item 3.** The D2 gate rule freezes `bpr == "24/24"` with the
> denominator marked *permanently fixed*, and `near_miss_bpr == "12/12"` exactly.
> Merging the branch as-is would make those 26 and 14. **Freezing first forecloses
> the "amend the counts" option**, so the corpus ruling has to come first.

---

## 3. The D2 gate-rule freeze · **held, and here is why it is still held**

Your ruling was "hold until GX5 is completed." GX5 landed (ruling 42,
`SPINE_VERSION 10`, contract C4 re-hashed, suite green).

**I did not fire it, because the reason to hold changed after you gave the
ruling.** The gate rule pins the benign denominator at 24 and near-miss at
exactly 12, so freezing now decides item 2 by side effect rather than by ruling.

Dry run reads `834bc7113a13beea`. One command once item 2 is settled.

---

## 4. Track fit — the honest problem · **Stage One pass/fail**

Fortified Enterprise Fleet asks for *"a scalable network of institutional agents"*
that *"maintain context across weeks of asynchronous operations."*

CRUCIBLE is neither, and **cross-episode state is named as out of scope in our own
specs.** Stage One is pass/fail on "reasonably addresses a Challenge."

The Stage Two sub-criteria for the track are much friendlier — multi-agent
complexity and delegation to specialised sub-agents, both strong here. But the
submission text should meet the track's own language head-on rather than route
around it. This is a writing problem, not a building one. `docs/contest/CONTEST.md`
§3 lays out the options.

---

## 5. The "unlikely hero" · currently scoring zero

A named Stage Two sub-criterion for this track: *"Did they build this for an
'Unlikely Hero' outside of standard corporate roles?"* No persona exists anywhere
in the project.

The honest candidate is not a security engineer — it is the **operations lead who
inherits an agent somebody else built** and has to decide whether it is safe to
give it the company card. Real role, outside standard corporate security, and
genuinely who this serves.

A persona invented to satisfy a rubric reads exactly like a persona invented to
satisfy a rubric, so this is yours rather than mine.

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

## 9. `ORD-13` / `ORD-14` were authored after your review pass

So *"the ordinary benign set was reviewed"* is not true of the set as it stands.
Two fixtures to skim.

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
