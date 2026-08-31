# The contest — rules, scoring, and what CRUCIBLE must produce

**Read this before planning any work that is meant to score.** It is the repo's
single copy of the contest facts. Do not restate any figure below in another
document; link here instead. Verified against
<https://allthingsagentichackathon.devpost.com/rules> on **2026-08-21** and
against the rules text Eric pasted the same day.

> **Verify on use.** A rules page can change. Anything here that decides real work
> — a deadline, a hard requirement, a prize — is re-checked against the live page
> before the submission goes in, not recalled from this file.

## RE-VERIFIED 2026-08-30 against the full Official Rules text and the organiser's one-week checklist email

Eric pasted both. **The dates, the mandatory technology, the Stage One/Two/Three
structure, the weightings and the nine prizes all match what this file already
said.** Four obligations were NOT in this file and one entry in it was wrong.
Participants on the Devpost page that day: **11,842**.

**A. The project must stay AVAILABLE until the Judging Period ends, 2026-10-01.**
Verbatim: *"The Entrant must make the Project available free of charge and
without any restriction, for testing, evaluation and use by the Sponsor,
Administrator and Judges until the Judging Period ends."* Judging runs
2026-09-01 → 2026-10-01; winners on or around 10-08.

**This collides with the planned teardown.** `data-spec.md` §7.3 tears down the
GCS buckets, and the retention-policy reasoning in `CLAUDE.md` is written around
"a hackathon ending 08-31". **The hackathon does not end for the submitter on
08-31 — evaluation runs for another month.** Nothing may be torn down before
2026-10-01.

**B. Everything LOCKS at the deadline.** The organiser's checklist: *"Once the
deadline passes, everything locks — don't touch your repo, video, or linked
materials until after winners are announced."* Anything that must be in the
repository has to land before **2026-08-31 17:00 PT**. This is a wall, not a
preference, and it governs whether the sealed run happens at all.

**C. A private hosted URL requires credentials in the submission.** Verbatim:
*"If Entrant's website is private, Entrant must include login credentials in its
testing instructions."* The Cloud Run service is `--no-allow-unauthenticated`,
and this project has a standing rule never to link that URL publicly. **The two
constraints are in tension and only Eric can resolve it.** A hosted URL remains
*highly encouraged*, not mandatory — so declining to submit one is a legitimate
option and avoids the conflict entirely.

**D. Two submission-form fields this file never listed:** which Google SDK was
used — the official list is **ADK, GenAI SDK, Antigravity SDK, Genkit**, and the
answer here is ADK — and **the date the project was started**, which must fall
inside the Submission Period beginning 2026-08-03. First commit here is
2026-08-20.

**E. Pre-existing code must be disclosed; AI coding assistants need not be.**
Verbatim: *"Participants may use standard development tools, including
frameworks, libraries, starter templates, and AI coding assistants, but must
disclose any other pre-existing code or work incorporated into the Project."*
The disclosure obligation attaches to pre-existing code, not to how the new code
was written.

**F. Startup Excellence needs an incorporated organisation and a corporate email
address.** Solo and unaffiliated is not eligible for that one; do not opt in.
Eligible prizes here are the category prize (Fortified Enterprise Fleet),
Individual/Hobbyist (2 awarded), Best Architectural Design (2 awarded), the Grand
Prize, and Honorable Mentions. **A project may win at most one.**

---

## 1. Dates. All Pacific Time.

| What | When |
|---|---|
| Submission period | **2026-08-03 09:00 PT → 2026-08-31 17:00 PT** |
| **Submission deadline** | **Mon 2026-08-31, 17:00 PT** |
| Google Cloud credit request | **2026-08-28 12:00 PT**, or while supplies last |
| Judging | 2026-09-01 → 2026-10-01 |
| Winners announced | on or around 2026-10-08 |

Internal dates, from `execution-spec.md`: **target freeze Sat 08-22**, **cut line
Tue 08-25**, **code freeze Fri 08-28**, **record Sat 08-29**, **submit Sun 08-30**.
We submit a day early on purpose.

---

## 2. Stage One — pass/fail. Miss one of these and nothing else is scored.

Stage One asks only whether the submission "includes all Submission requirements,
reasonably addresses a Challenge, and reasonably applies the requirements."

**Mandatory technology.**

1. **Gemini 3.5 or newer**, through the Gemini API **or** Vertex AI. *(We are on
   Vertex. Live code pins `gemini-3.7-flash`, `gemini-3.6-flash`,
   `gemini-3.5-flash-lite`, `gemini-3.5-flash`. `agent.py:36` records
   `gemini-2.5-*` and `gemini-3.1-*` as dead vocabulary. Clear.)*
2. **At least one Google Agent Framework.** *(ADK, pinned `google-adk==2.1.0`.)*
3. **At least one Google Cloud infrastructure service.** *(Cloud Run, GCS,
   Firestore, BigQuery.)*

**Mandatory deliverables.**

| # | Requirement | Where it stands |
|---|---|---|
| 1 | One of the three tracks selected | **Fortified Enterprise Fleet** |
| 2 | Text description: features, technologies, data sources, **findings and learnings** | **Findings DONE 2026-08-22.** Features live in `project-story.md`. **Technologies and data sources were covered nowhere in the submission text until 2026-08-22** — `project-story.md` names no Gemini model, no agent framework and no Cloud service. The code always satisfied the *technology* requirement above; this row is the *description*, and it was the half that was short. Now in `docs/devpost/findings-and-learnings.md` |
| 3 | Public code repository URL | `emtcmca/crucible`, public, Apache-2.0 |
| 4 | **Spin-up instructions in `README.md`**, step by step | **DONE 2026-08-21** — every command run, real output pasted |
| 5 | **Architecture diagram** — a visual of how Gemini connects to backend, database, frontend | **DONE 2026-08-21** — `docs/diagrams/architecture.md`, six Mermaid, all rendered |
| 6 | **Demo video, 4 minutes maximum**, public on YouTube or Vimeo, English or English subtitles | script exists, **not recorded as of 2026-08-22** |
| 7 | Video **must demonstrate the backend running on Google Cloud** | **deployed and serving 2026-08-21. Both captures landed the same day** (`b4e060e`): `docs/proof/cloud-run-console-2026-08-21.png` and `docs/proof/trace-explorer-spans-2026-08-21.png`. **Nothing is owed here but the recording.** Narration caveat in `BUILD-LIST.md` T0-3: the captured span names do not include `execute_tool` |
| 8 | Hosted project URL for judges to test — "highly encouraged", not mandatory | `https://crucible-vgp5owkxyq-uc.a.run.app` — **authenticated as of 2026-08-22**, so it is not yet a URL a judge can open. *(The console screenshot shows the same service under its project-number form, `https://crucible-752793770087.us-central1.run.app`. Cloud Run serves both; verify which one you paste before it goes in a submission field.)* |

**Updated 2026-08-21. This table previously read "NOT WRITTEN", "DOES NOT EXIST"
and "no Cloud Run deploy yet" for rows 4, 5 and 7, all three of which had been
done — row 5 for a day.** Every agent reads this file before planning, so a stale
row here does not merely mislead: it schedules work that is already finished, and
it makes a finished deliverable look like a gap in the one document that exists to
say which gaps are fatal.

**As of 2026-08-22, one of those eight does not exist: the video.** *(Re-checked
2026-08-22. On 2026-08-21 this sentence also owed two screenshots under row 7;
both were captured that evening, `b4e060e`.)* Row 8 is one IAM binding away from
being a real judge-testable URL — see the Cost note in `deploy/RUNBOOK.md` for
why it is locked down by default and what opening it would mean, and
`BUILD-LIST.md` **T2-7** for the two ways to give a judge something openable
without opening the service.

> The undated version of that sentence **failed `contract-check`'s STATUS pass**,
> correctly. A bare "one of eight does not exist" is the exact claim that rots:
> it was three yesterday and it will be zero before submission, and a reader who
> cannot see when it was written cannot tell which. The gate caught it on the
> coordinator, in the file whose whole job is saying which gaps are fatal.

---

## 3. The track we are in, and the honest fit question

**Fortified Enterprise Fleet**, as the rules define it:

> "Build a scalable network of institutional agents that hook into official
> enterprise infrastructure… demonstrate how agents are cataloged for
> cross-department use, how they safely maintain context across weeks of
> asynchronous operations, and how they interact with production data without
> violating enterprise compliance, data sovereignty, or security policies."

**Where CRUCIBLE fits cleanly.** *Interacting with production-shaped data without
violating security policy* is the entire product. *Cataloging agents* is the
capability manifest — every tool mapped to a capability class, unmapped tools
**named** rather than hidden, the whole thing hashed before use.

**Where it does not, and we should say so rather than hope nobody reads
carefully.** CRUCIBLE is not a *scalable network of institutional agents*, and it
does not *maintain context across weeks of asynchronous operations* — episode
context is deliberately frozen inside a single episode, and cross-episode state is
named as out of scope in the specs.

**This is an open question for Eric, not a decision the coordinator makes.**
Options: lean the framing toward the fleet the harness *protects*; or argue that
the fleet CRUCIBLE runs (red team, coroner, armorer, tripwire, warden, gate) is
itself the institutional network. Either way the submission text should meet the
track language head-on rather than route around it.

**Full requirement-by-requirement verdict, the honest-fit test on all three framings,
and draft submission text: `docs/contest/track-fit.md`.**

**What the Stage Two criteria actually ask for this track**, which is friendlier:

> "Is the task complex enough to warrant a multi-agent system? Does the system
> intelligently delegate tasks to specialized sub-agents? Did they build this for
> an 'Unlikely Hero' outside of standard corporate roles?"

Two of three are strong. **"Unlikely Hero" had no named persona anywhere in the
project until 2026-08-21.** One now exists — `docs/contest/unlikely-hero.md`, the
operations lead who inherited an agent somebody else built and has to decide
whether to give it the company card. **It is drafted, not ratified**: whether it
is true enough to say out loud is Eric's call, `docs/NEEDS-ERIC.md` item 5.

---

## 4. Stage Two — the weighted score. 1 to 5 per criterion, averaged.

### Innovation & Operational Utility — **40%**

> "Does the system eliminate real-world friction? Is the 'Twist' present? We are
> looking for high-value, autonomous execution over simple chat queries."

### Architectural Discipline & Tech Stack — **30%**

> "We are evaluating your engineering decisions, not just your ability to call an
> API. How well did your team decouple systems, manage state, and design robust,
> failure-tolerant agentic systems?"

The sub-criteria that fit CRUCIBLE best are **The Multi-Agent Nexus**:

> "Is there a clear, strictly enforced separation of concerns between agents? Is
> the inter-agent routing logic failure-tolerant (e.g., how does the system recover
> if a worker agent loops or returns a hallucination)?"

**Read that second sentence twice.** *How does the system recover if a worker agent
returns a hallucination* is what the pure-code tripwire and the promotion gate
exist for. This is the criterion the project was accidentally built to win.

Also relevant, from **The Continuous Action Engine**: "Are the tools properly
isolated and scoped for security?" — that is the capability manifest and the IAM
boundary with the captured 403.

### Demo & Production Readiness — **30%**

> "The clarity of the technical documentation and the undeniable proof of execution
> in the video pitch."

Three named sub-tests:

- **Proof of Action** — "Does the video show an **unedited, live execution**
  of the agent performing its task (via terminal logs, database updates, or UI
  changes)?"
- **The Documentation** — "Does the public GitHub repository feature a **clean
  architecture diagram** and **reproducible setup instructions**?"
- **Visual proof of Google Cloud deployment in the video.**

> **This collides with `ADR-0010`**, which has some demo beats replaying stored
> evidence bundles for quota reasons. "Unedited, live execution" is the phrase the
> judges are given. The replay/live split needs a second look before recording, and
> the beats that replay should be labelled as replay on screen rather than left to
> look live.

---

## 5. Stage Three — bonus points. Cheap, and we are leaving them on the table.

Final score is **1 to 6**: up to 5 from Stage Two, up to **1.0** from bonuses.

| Bonus | Points | Status |
|---|---|---|
| Publish a piece of content (blog, podcast, video) covering how the project was built, public, **stating it was created for this hackathon** | **+0.2** | not done |
| A public social post on X, LinkedIn, Instagram or Facebook with **`#AllThingsAgenticHackathon`** | **+0.2** | not done |
| Each **additional Google AI model** integrated (Gemma, Veo, Lyria…), max three | **+0.2 each, up to +0.6** | **GEMMA IS INTEGRATED AND +0.2 IS CLAIMABLE. Corrected 2026-08-30.** See the note below. Veo and Lyria are not integrated and are not claimable. | |

### The Gemma cell was wrong, and it was wrong in the direction that costs points

**Corrected 2026-08-30, verified from source.** This cell read *"Gemma was never
built and appears in no code."* That is false. Gemma is pinned at
`crucible/cartographer/vertex.py:94` as
`DEFAULT_MODEL_ID = "google/gemma-4-26b-a4b-it-maas"`, the component is
`crucible/cartographer/gemma.py`, and it has **run live against Vertex MaaS** —
`docs/proof/vertex-gemma-maas-probe-2026-08-22.txt`,
`docs/proof/cartographer-live-run-2026-08-22.json` and `-2026-08-23.json`,
`docs/proof/cartographer-stability-2026-08-24.json`, and a ratification record
at `docs/proof/cartographer-adk-ratification-record-2026-08-28.json`.

**How it went wrong is the shape this repository keeps recording.** `ADR-0018`
withdrew a specific claim — that Gemma generated the corpus — and that
withdrawal was correct and stands. Someone then generalised it from *"Gemma did
not do that"* to *"Gemma was never built"*, and the generalisation was written
into the one document that decides what work is worth doing. **Closing an
instance and reporting the class.** The result was a bonus point recorded as
unclaimable while the integration sat in the tree, live-run artifacts and all.

**What may be claimed, and how to word it:** Gemma is used for **capability
classification** — the CAPABILITY_CARTOGRAPHER — and for nothing else. It did
not generate the corpus, and `ADR-0018` says that sentence may not be written or
spoken anywhere.

**A full point on a five-point scale is twenty percent of the maximum score, and
none of it requires the loop to work.** The two publishing bonuses are an
afternoon. Eric already writes for LinkedIn.

**Status 2026-08-30: 0.2 of the 1.0 is already EARNED (Gemma) and needs only to be claimed on the form. The remaining 0.8 — two publishing bonuses at 0.2 each and two further model integrations at 0.2 each — is unclaimed.**

*(The previous line read "the entire 1.0 is still unclaimed", which was true of the two publishing bonuses and false of Gemma.)* Devpost updates 3 and 4
went public that afternoon, but **Devpost is the submission platform** and the
write-up bonus plausibly requires content published off it — **unresolved, and
recorded as unresolved rather than assumed either way** (`BUILD-LIST.md` T1-1).
Nothing carrying `#AllThingsAgenticHackathon` has been posted anywhere.

---

## 6. Prizes. Nine categories, and a project may win exactly one.

| Prize | Cash | Winners |
|---|---|---|
| Grand Prize | **$50,000** + $5,000 credits | 1 |
| The Fortified Enterprise Fleet | **$20,000** + $2,000 credits | 1 |
| The Taskmaster | $20,000 + $2,000 credits | 1 |
| The Collaborative Partner | $20,000 + $2,000 credits | 1 |
| Startup Excellence *(incorporated organizations)* | $20,000 + $5,000 credits | 1 |
| **Individual / Hobbyist — Best Team or Solo Build** | **$10,000** + $1,000 credits | **2** |
| **Best Architectural Design** | **$5,000** + $1,000 credits | **2** |
| Best Multimodal UX | $5,000 + $1,000 credits | 2 |
| Honorable Mention | $2,000 + $500 credits | 5 |

**"Each Project is eligible for up to one (1) Prize."**

**Where CRUCIBLE is disproportionately strong**, in order of odds rather than size:

1. **Best Architectural Design — $5,000, two winners.** Strict separation of
   concerns enforced in IAM and in pure code, five hash-locks, ten frozen
   contracts, **eighteen ADRs** *(recounted 2026-08-22 from `docs/adr/`; this read
   seventeen. Counts here are read from the directory, never recalled)*, a
   published pre-commitment. This is the closest
   match between what the project *is* and what a prize *asks for*.
2. **Individual / Hobbyist — $10,000, two winners.** Eric is solo. Twice the money
   and twice the slots of the architecture prize.
3. **The Fortified Enterprise Fleet — $20,000.** Contingent on the track-fit
   question in §3 being answered convincingly rather than avoided.

---

## 7. Eligibility

No residents of Italy, Quebec, Crimea, Cuba, Iran, Syria, North Korea, Sudan,
Belarus, or Russia; no employees or contractors of Google, Devpost, or connected
organizations; must be at or above the age of majority. **Ohio, solo, unaffiliated
— clear.**

Winners must complete post-competition prize affidavits; nothing is final before
verification.

---

## 8. What this means for the build, in one paragraph

**Rewritten 2026-08-22, because every specific in it had been overtaken.**

**~~One mandatory deliverable does not exist: the video.~~ RECORDED AND UPLOADED 2026-08-31: https://youtu.be/tdro9Fs97mY** — the last mandatory Stage One deliverable, and the eight are now complete. The architecture diagram
landed 2026-08-21; the Cloud Run deploy and both on-camera captures landed the
same day. A full **1.0 bonus point** still sits unclaimed and almost none of it
depends on the loop working. The strongest scoring surface is **architectural
discipline**, where the criterion literally asks how the system recovers when a
worker agent returns a hallucination — which is what the tripwire and the gate do.
The weakest is **track fit**; that and the **"unlikely hero"** persona both now
have drafted answers (`track-fit.md`, `unlikely-hero.md`, both 2026-08-21) waiting
on Eric's ratification rather than on anyone's writing. Live work items are tracked
in `docs/contest/BUILD-LIST.md`.

*(The version of this paragraph before 2026-08-22 said three deliverables did not
exist and named two that did. It is kept in mind rather than in the file for one
reason: §2 above already records why a stale row here is worse than a stale row
anywhere else — this is the document that says which gaps are fatal, so a gap it
invents gets worked on.)*
