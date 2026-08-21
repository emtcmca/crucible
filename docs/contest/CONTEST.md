# The contest — rules, scoring, and what CRUCIBLE must produce

**Read this before planning any work that is meant to score.** It is the repo's
single copy of the contest facts. Do not restate any figure below in another
document; link here instead. Verified against
<https://allthingsagentichackathon.devpost.com/rules> on **2026-08-21** and
against the rules text Eric pasted the same day.

> **Verify on use.** A rules page can change. Anything here that decides real work
> — a deadline, a hard requirement, a prize — is re-checked against the live page
> before the submission goes in, not recalled from this file.

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
| 2 | Text description: features, technologies, data sources, **findings and learnings** | Project Story posted; findings section owed |
| 3 | Public code repository URL | `emtcmca/crucible`, public, Apache-2.0 |
| 4 | **Spin-up instructions in `README.md`**, step by step | **NOT WRITTEN** |
| 5 | **Architecture diagram** — a visual of how Gemini connects to backend, database, frontend | **DOES NOT EXIST** |
| 6 | **Demo video, 4 minutes maximum**, public on YouTube or Vimeo, English or English subtitles | script exists, not recorded |
| 7 | Video **must demonstrate the backend running on Google Cloud** | **no Cloud Run deploy yet** |
| 8 | Hosted project URL for judges to test — "highly encouraged", not mandatory | none |

**Three of those eight do not exist**, and two of them (the diagram and the
Cloud-Run-on-camera proof) are pass/fail gates rather than quality points.

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

**What the Stage Two criteria actually ask for this track**, which is friendlier:

> "Is the task complex enough to warrant a multi-agent system? Does the system
> intelligently delegate tasks to specialized sub-agents? Did they build this for
> an 'Unlikely Hero' outside of standard corporate roles?"

Two of three are strong. **"Unlikely Hero" we currently score nothing on** — there
is no named persona anywhere in the project.

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
| Each **additional Google AI model** integrated (Gemma, Veo, Lyria…), max three | **+0.2 each, up to +0.6** | Gemma planned for corpus generation (ADR-0009) = +0.2. Two more unclaimed |

**A full point on a five-point scale is twenty percent of the maximum score, and
none of it requires the loop to work.** The two publishing bonuses are an
afternoon. Eric already writes for LinkedIn.

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
   contracts, seventeen ADRs, a published pre-commitment. This is the closest
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

Three mandatory deliverables do not exist and two of them are pass/fail: the
**architecture diagram** and **visible proof of Google Cloud deployment in the
video**. A full **1.0 bonus point** sits unclaimed and almost none of it depends on
the loop working. The strongest scoring surface is **architectural discipline**,
where the criterion literally asks how the system recovers when a worker agent
returns a hallucination — which is what the tripwire and the gate do. The weakest
is **track fit**, which is a writing problem rather than a building one, and the
**"unlikely hero"** persona, which does not exist at all. Live work items are
tracked in `docs/contest/BUILD-LIST.md`.
