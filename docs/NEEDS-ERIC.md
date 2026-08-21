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
- **+0.2 each, max +0.6** — additional Google AI models. Gemma is already planned
  for corpus generation, so that one is nearly free.

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

## 8. `r_new3` fails validator check V4

It names `status_to` values — `RISK_CLEARED`, `IDENT_CLEARED`, `FLAG_REMOVED` —
that Part A does not declare. Part A declares `OPEN, PENDING, APPROVED, REJECTED,
CLOSED`, and `validator.py:294-310` raises `E_UNDECLARED_ENUM_SYMBOL`.

**Narrowing fact:** both P03 instances are already inside the declared enum
(`F1-03` sets `APPROVED`, `NM-F1-03` sets `PENDING` and names `status_to` as its
differing field). **So the pair is sound and only the rule text is wrong** — a
rule rewrite with no corpus change.

I did not rewrite it because changing a separating rule changes what the pair
claims, and I would want to measure the rewrite against the whole benign suite
before asserting it separates.

---

## 9. `ORD-13` / `ORD-14` were authored after your review pass

So *"the ordinary benign set was reviewed"* is not true of the set as it stands.
Two fixtures to skim.

---

## 10. The corpus was not generated by Gemma, and a scripted on-camera line says it was

`ADR-0009` names one rationale and says it is **the only one that may be written
anywhere**, with a clause to say on camera:

> *"the attack corpus is generated by an open-weights model pinned by version and
> seed, because a corpus you can't regenerate is a corpus you can't pre-register."*

**As things stand that sentence is false.** The corpus was authored by the lane
agents across W2 — `git log` shows *"corpus: author attack families F1 and F2"*
and its siblings. Gemma appears in **no code anywhere in the repo**, and
`CAPABILITY_CARTOGRAPHER`, its other home, has no module. Checked every instance:
there is **no generator, no seed, no model, and no provenance field of any kind**
on any of them.

So the corpus is not regenerable by a third party, and it is not regenerable by
us either.

**What this does NOT break, which is the important half.** The pre-registration
claim does not rest on regenerability. It rests on the **hash**, the **published
commitment** (`2cde0250de00e692`, with a public commit timestamp), and the **IAM
boundary** the Armorer's identity cannot cross. Those are all real and all
independent of how the instances were written. A commitment is the stronger
mechanism precisely because it does not care about provenance — it only cares that
nothing moved afterwards.

**Three options.**

1. **Change the line and keep the corpus.** Say what is true: the corpus was
   authored, then sealed and committed before the first patch. Drop the
   regeneration argument entirely. Cheapest, and it costs nothing real — the
   commitment already does the work the regeneration argument was doing.
2. **Give Gemma its real job.** Wire it as `CAPABILITY_CARTOGRAPHER`, which is
   where `architecture-spec.md:138` puts it anyway. That earns the **+0.2**
   honestly and gives the model an architectural home rather than a bolted-on one
   — which is `ADR-0009`'s own stated standard.
3. **Cut Gemma.** It is already cut candidate 2 (`execution-spec.md:475`). Loses
   0.2 of the bonus ceiling and one on-camera clause.

**My recommendation: 1 and 2.** They are independent, and 1 is required regardless
of what happens to Gemma, because the line is currently scripted and wrong.

> Worth naming plainly: this is a claim that survived being written into an ADR,
> restated in two specs, and scheduled into a demo script, and nothing checked it
> against the repo until tonight. It is the same shape as the fabricated unit test
> in `measurement-spec:989` — a document asserting something true-sounding that
> nobody measured.

### Addendum, 2026-08-21. Four things this item did not have.

Full memo with the ground-truth commands: `docs/decisions-pending/gemma-provenance.md`.

**1. The exact line, and it is worse than "a clause".** It is
`docs/execution-spec.md:532`, inside the timed video script, in the 45-second
ARCHITECTURE beat — the segment the script itself marks as carrying the 40%
criterion. It is spoken aloud to Google judges as "Proof of Action."

**2. That line was already corrected once, and the correction was about tone.**
The callout immediately below it records a 2026-08-20 fix: the Gemma clause "must
not say *because aligned frontier models refuse red-team payloads at volume*",
because in a Google-judged contest that reads as routing around safety refusals.
**So somebody edited that exact sentence one day ago, for how it would sound, and
never asked whether it was true.** A sentence can be revised and still be false;
revising it is not checking it.

**3. The stated justification is independently false.** The line argues *"because
a corpus you can't regenerate is a corpus you can't pre-register."* Pre-registration
here rests on the commitment hash, the public commit timestamp, and the IAM
boundary — none of which care about provenance. **The commitment is the stronger
mechanism, and the script talks past it to make a weaker argument that is also
untrue.** Fixing the fact would improve the sentence even if regenerability were
real.

**4. Where it does and does not leak.** ~10 internal docs repeat it (ADR-0008,
ADR-0009, architecture-spec, CONVENTIONS §3.2-3.3, build-spec, lanes/L2,
NEEDS-ERIC, competitive-analysis). **`README.md` and `docs/devpost/` are clean —
zero mentions.** So nothing false has reached the public artifacts yet. The script
is the only path from here to a judge.

**Recommendation sharpened: do option 1 TODAY and unconditionally, and decouple it
from the decision about option 2.** Option 1 is not a concession, it is removing a
false statement from a script; it should not wait on a build decision that will
have better information in five days, after the corpus freeze and the first loop
run. Supersede rather than edit ADR-0009 — this repo's stated practice — so the
record shows the claim was made, checked, and withdrawn. **That trail is worth
more to an architecture judge than the claim ever was.**

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
