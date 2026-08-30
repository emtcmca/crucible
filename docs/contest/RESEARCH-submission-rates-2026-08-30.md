# How many people actually submit to a large online hackathon?

**Research date:** 2026-08-30. Every figure below was read off a live page on that date and
carries its source URL. Where I counted something myself versus where a source asserted it is
marked. Nothing here is estimated silently: inferences are labelled `[INFERENCE]`.

**Scope:** the question is what fraction of registrants to the Google Cloud *All Things Agentic*
hackathon (11,844 registered, closes 2026-08-31 17:00 PDT) will file a complete, eligible
submission, and how many of those are real competition.

---

## The short answer

**Between 5% and 10% of registrants file an eligible submission. For this hackathon that is
roughly 600 to 1,200 projects, with a central estimate near 850.**

Confidence: **moderate on the range, low on any single number.** Thirteen comparable
sponsor-run Devpost hackathons produce ratios from **2.8% to 17.2%**, median **6.5%**. The
spread is real, not noise, and it is driven by factors I can name but cannot weight precisely
(see *What drives the spread*). Devpost's own published figure for its whole platform is
**5–33%**, which brackets everything I measured and is wide enough to be nearly useless on its
own.

The narrower claim I have most confidence in: **the four Google Cloud agent-themed hackathons
I found all fall between 2.8% and 9.9%**, and the closest single analogue landed at **4.6%**.

**The single most useful data point:** the *Agent Development Kit Hackathon with Google Cloud*
(May 12 – Jun 23, 2025) had **10,352 participants and 476 gallery projects — 4.60%**. It is the
closest analogue available in every dimension that matters: same sponsor, same platform, same
agent theme, near-identical registrant count (10,352 vs 11,844), and an almost identical
submission requirement list (hosted URL + public repo + architecture diagram + ~3-minute demo
video). Google's own blog post independently confirms the order of magnitude at "477 submitted
projects" from "10,400 participants."

- Devpost page: https://googlecloudmultiagents.devpost.com/ (participant count, read 2026-08-30)
- Gallery count, counted from the pagination header "1 – 24 of 476":
  https://googlecloudmultiagents.devpost.com/project-gallery
- Google Cloud blog: https://cloud.google.com/blog/products/ai-machine-learning/adk-hackathon-results-winners-and-highlights

---

## The data table

Every row: participant count read from the hackathon's own Devpost page; project count read
from the pagination header of its project gallery ("1 – 24 of N"). **I computed every ratio
myself** from those two numbers. Sorted by ratio.

| Hackathon | Sponsor | Dates | Registrants | Gallery projects | Ratio | Source |
|---|---|---|---|---|---|---|
| GKE Turns 10 Hackathon | Google Cloud | Aug 18 – Sep 22, 2025 | 4,708 | 130 | **2.76%** | [page](https://gketurns10.devpost.com/) · [gallery](https://gketurns10.devpost.com/project-gallery) |
| AI in Action: Innovate Together | Google Cloud + MongoDB + GitLab | May 6 – Jun 17, 2025 | 6,689 | 295 | **4.41%** | [page](https://ai-in-action.devpost.com/) · [gallery](https://ai-in-action.devpost.com/project-gallery) |
| **Agent Development Kit Hackathon** | **Google Cloud** | **May 12 – Jun 23, 2025** | **10,352** | **476** | **4.60%** | [page](https://googlecloudmultiagents.devpost.com/) · [gallery](https://googlecloudmultiagents.devpost.com/project-gallery) |
| Azure AI Developer Hackathon | Microsoft | Feb 18 – Mar 28, 2025 | 3,347 | 183 | **5.47%** | [page](https://azureaidev.devpost.com/) · [gallery](https://azureaidev.devpost.com/project-gallery) |
| Code with Kiro Hackathon | AWS | Jul 14 – Sep 15, 2025 | 9,950 | 552 | **5.55%** | [page](https://kiro.devpost.com/) · [gallery](https://kiro.devpost.com/project-gallery) |
| Google AI Hackathon | Google | Mar 18 – May 3, 2024 | 15,476 | 898 | **5.80%** | [page](https://googleai.devpost.com/) · [gallery](https://googleai.devpost.com/project-gallery) |
| AWS AI Agent Global Hackathon | AWS | Sep 8 – Oct 22, 2025 | 9,466 | 613 | **6.48%** | [page](https://aws-agent-hackathon.devpost.com/) · [gallery](https://aws-agent-hackathon.devpost.com/project-gallery) |
| Chrome Built-in AI Challenge | Google | Oct 1 – Dec 3, 2024 | 8,490 | 565 | **6.65%** | [page](https://googlechromeai.devpost.com/) · [gallery](https://googlechromeai.devpost.com/project-gallery) |
| World's Largest Hackathon | Bolt.new | 2025 | 128,339 | 9,573 | **7.46%** | [page](https://worldslargesthackathon.devpost.com/) · [gallery](https://worldslargesthackathon.devpost.com/project-gallery) |
| AWS Lambda Hackathon | AWS | Jun 3 – 30, 2025 | 3,715 | 331 | **8.91%** | [page](https://awslambdahackathon.devpost.com/) · [gallery](https://awslambdahackathon.devpost.com/project-gallery) |
| Google Cloud Rapid Agent Hackathon | Google Cloud | May 5 – Jun 11, 2026 | 14,458 | 1,426 | **9.86%** | [page](https://rapid-agent.devpost.com/) · [gallery](https://rapid-agent.devpost.com/project-gallery) |
| Gemini 3 Hackathon | Google | Dec 17, 2025 – Feb 9, 2026 | 35,528 | 4,499 | **12.66%** | [page](https://gemini3.devpost.com/) · [gallery](https://gemini3.devpost.com/project-gallery) |
| OpenAI Build Week | OpenAI | Jul 13 – 21, 2026 | 46,718 | 8,015 | **17.16%** | [page](https://openai.devpost.com/) · [gallery](https://openai.devpost.com/project-gallery) |

**Aggregates I computed from the table:** median **6.48%**; unweighted mean **7.52%**;
participant-weighted total 27,556 projects / 297,236 registrants = **9.27%** (that last one is
dominated by Bolt and OpenAI Build Week and should not be used as a typical value).

**Google / Google Cloud rows only** (seven rows): 2.76, 4.41, 4.60, 5.80, 6.65, 9.86, 12.66 —
median **5.80%**.

**Google Cloud agent-themed rows only** (four rows, the tightest analogue set): 2.76, 4.41,
4.60, 9.86 — range **2.8% to 9.9%**.

### The one platform-wide figure, and why it is weak

Devpost's own sales page states: *"Devpost hackathons consistently deliver a 5–33% conversion
rate"* from registration to submission — https://info.devpost.com/product/public-hackathons
(read 2026-08-30). It is marketing copy with no methodology, no sample, and no date. It is
consistent with my measurements at the bottom of its range and wildly above them at the top.
Treat it as corroboration that the low single digits are not an error, and nothing more.

Devpost's help centre confirms the platform tracks this metric internally as
*"the registration to submitter conversion rate"* —
https://help.devpost.com/article/96-metrics-and-reports (read 2026-08-30). That report is
organiser-only; the underlying numbers are not public.

### Where the sources disagree

Three disagreements I found, all small, all worth knowing:

1. **ADK Hackathon.** Devpost says **10,352 participants / 476 projects**. Google's own blog
   says **"10,400 participants"** and **"477 submitted projects"**, and a search-surfaced
   summary of the same event reported "10,432 participants." The Devpost page is the live
   count and is the one I used.
2. **Gemini 3 Hackathon.** Devpost's marketing page lists **35,645 participants**; the
   hackathon page itself showed **35,528** on 2026-08-30. I used the hackathon page.
3. **Bolt's World's Largest Hackathon.** The Devpost page shows **128,339 participants**; a
   community write-up analysing the event states *"a total of 131,307 player joined"* —
   https://dev.to/dirsebastian/things-you-did-not-know-about-the-worlds-largest-hackathon-by-boltdotnew-its-not-what-you-51i5

The direction of drift is consistent: **participant counts keep ticking upward after the
deadline** as people continue to register on a closed page, while the gallery count is frozen.
Every ratio in the table is therefore very slightly *understated* — by a fraction of a
percentage point, not by anything material.

### What "participants" and "projects" actually mean here

This matters and Devpost is not fully consistent about it.

- **Participants** = registrants. Anyone who clicked "Join hackathon." It is not a count of
  people who did anything.
- **Gallery projects** = submissions the organiser reviewed and let through. Devpost's help
  centre says a project appears only after *"the hackathon manager turns on the gallery"* and
  *"has reviewed and moderated the project"*
  (https://help.devpost.com/article/80-what-is-the-project-gallery), and instructs organisers
  to mark spam and unrelated submissions **Hidden** so they *"don't show up in your Project
  Gallery"* (https://help.devpost.com/article/102-managing-submissions).

**This cuts in the right direction for the question being asked.** The gallery count is closer
to *complete and eligible* than to *raw submitted*, which is exactly what was asked for. The
raw submission count before moderation is higher than every number in my table, by an unknown
amount. Nobody publishes it.

---

## Credits-for-signup hackathons specifically

**First, a correction to the premise.** *All Things Agentic* does **not** hand credits to
everyone who signs up. Its rules say participants *may request* **"$150 in Google Cloud
credits"** by completing a form **"by August 28th at 12:00 pm PT or while supplies last,"**
reviewed within 72 business hours, and *"credits are not guaranteed"* —
https://allthingsagentichackathon.devpost.com/rules (read 2026-08-30). That is a second
deliberate step with a deadline that has already passed, not a signup bonus. It still lowers
the bar to registering, but less than a no-friction giveaway would.

Splitting the table by whether credits or free tool access were offered:

| Offered credits / free tool access | Ratio | Detail |
|---|---|---|
| Google Cloud Rapid Agent | **9.86%** | *"request $100 in credits… while supplies last"* ([resources](https://rapid-agent.devpost.com/resources)) |
| AWS AI Agent Global | **6.48%** | *"$100 in credit codes for participants on a first come first serve basis"* ([page](https://aws-agent-hackathon.devpost.com/)) |
| OpenAI Build Week | **17.16%** | $100 Codex credits, later *"we've given out all available credits"* ([resources](https://openai.devpost.com/resources)) |
| **No credits offered** | | |
| Chrome Built-in AI Challenge | **6.65%** | Local on-device AI, nothing to fund |
| AWS Lambda Hackathon | **8.91%** | No credits mentioned on the page |
| Gemini 3 Hackathon | **12.66%** | Rules point to *"a no cost trial"*, no hackathon-granted credits ([rules](https://gemini3.devpost.com/rules)) |

**The credits hypothesis is not supported by this data.** Mean of the credits group is 11.2%;
mean of the no-credits group is 9.4%. The credits group is *higher*, not lower. If free credits
were pulling in a wave of registrants who never intended to build, the credits group should
show a visibly depressed ratio. It does not.

Two honest caveats before anyone leans on that:

- **n = 3 per group.** This is a comparison of six numbers. It rules out a large effect; it
  does not rule out a small one, and it certainly does not prove credits *raise* submission
  rates.
- **The groups are not otherwise matched.** OpenAI Build Week is an 8-day sprint on a tool its
  registrants were already using daily. Gemini 3 was a 55-day event on a flagship model launch.
  Those differences are almost certainly larger than the credits effect.

The defensible conclusion: **$100–$150 of cloud credits is too small to be the main thing
driving the registrant-to-submitter gap.** The gap is large everywhere, credits or no credits.
Something else explains it.

### What drives the spread

Ranked by how much support the data gives each factor:

1. **Event length and how far ahead registration opens.** The two highest ratios belong to the
   shortest and the most launch-timed events. OpenAI Build Week ran **8 days** and hit 17.2%.
   The lowest, GKE Turns 10 at 2.76%, ran 35 days on a topic (Kubernetes microservices with
   agents) with a high setup cost. A long open registration window accumulates curious
   registrants who never start. *All Things Agentic* ran **27 days** (Aug 4 – Aug 31,
   https://allthingsagentichackathon.devpost.com/details/dates), which is on the short side of
   this set. `[INFERENCE]` — the correlation is visible in the table but n is too small to
   quantify.
2. **How much infrastructure the submission requires.** The four Google Cloud rows are the four
   that demand deployed cloud infrastructure plus an architecture diagram. They are also four
   of the six lowest ratios. Building an agent that actually runs on Cloud Run is a different
   commitment from shipping a web app.
3. **Whether registrants already use the sponsor's tool.** Codex, Gemini 3 and Bolt registrants
   were largely already users. ADK, GKE and Vertex agent tooling had to be learned first.
4. **Prize size** appears to matter less than expected. The $15,000 AWS Lambda Hackathon (8.91%)
   beat the $50,000 ADK Hackathon (4.60%). Bigger prizes attract more registrants, which is the
   denominator, so the ratio does not obviously improve.

Submission requirements are *not* a clean discriminator on their own: OpenAI Build Week
demanded a working project, a <3-minute video, a repo, a README with setup instructions and a
Codex session ID, and still hit 17.2%.

---

## From submissions to real competition

A gallery entry is not a competitor. Four separate narrowings apply, in order. **The first is
measured. The rest are inference and are labelled as such.**

**1. Moderation already happened.** As established above, the gallery count excludes spam and
projects *"missing a large portion of the hackathon requirements."* So the ratio table is
already net of the worst material. Do not discount it a second time for that.

**2. Submissions are not distinct entrants.** Devpost permits one person or team to submit
multiple projects. In Bolt's hackathon **one participant submitted 159 projects**
(https://dev.to/dirsebastian/things-you-did-not-know-about-the-worlds-largest-hackathon-by-boltdotnew-its-not-what-you-51i5).
That is an outlier, but multi-submission is normal at the top of the distribution, and it
inflates project counts relative to competitor counts. `[INFERENCE]` — I found no published
distinct-entrant figure for any hackathon in the table.

**3. Category split.** *All Things Agentic* has three challenge categories — Taskmaster,
Collaborative Partner, and **Fortified Enterprise Fleet** — and an entrant picks one
(https://allthingsagentichackathon.devpost.com/rules). A submission in another category is not
competing for the same $20,000 track prize. `[INFERENCE]` — an even three-way split is the
naive assumption and is almost certainly wrong. Security- and enterprise-flavoured tracks
typically draw fewer entries than assistant-flavoured ones, but I found no published
per-category counts for any comparable hackathon, so I cannot put a number on the skew or even
prove its direction.

**4. Quality distribution.** This is the number the question is really after, and it is the
weakest-supported thing in this document.

- Devpost's own advice to organisers says the first judging pass is a *"pass/fail whether the
  Idea Submissions meet a baseline level of viability, in that the idea reasonably fits the
  theme and reasonably applied effort to present it"* —
  https://hackdevpost.devpost.com/rules. So sponsors themselves expect a filterable bottom
  layer even after Devpost moderation.
- Devpost's editorial notes *"you'd be surprised how many submissions are disqualified simply
  because they didn't meet the baseline criteria"* —
  https://info.devpost.com/blog/understanding-hackathon-submission-and-judging-criteria. No
  figure attached.
- A judge's write-up (Gaurab Baral, Medium, Nov 2025) is reported to state that roughly **20%
  of projects are worth deep human review**, and that in one 49-project hackathon **41 used the
  same LangChain + Pinecone RAG approach**. **I could not read this article directly — the page
  returned HTTP 403.** Both figures reach me via a search-engine summary of it, not from the
  source. Treat them as a single unverified anecdote, not as data.
  https://medium.com/@gauurab/why-current-ai-models-fail-at-evaluating-hackathons-and-what-we-actually-need-de28cb87b6e5

**5. The prize denominator, which *is* measured.** *All Things Agentic* has **16 winning
slots**: 1 grand prize ($50,000), 3 category winners ($20,000 each), 1 Startup Excellence
($20,000), 2 Individual/Hobbyist ($10,000), 2 Best Architectural Design ($5,000), 2 Best
Multimodal UX ($5,000), and 5 honorable mentions ($2,000) —
https://allthingsagentichackathon.devpost.com/ (read 2026-08-30). The ADK Hackathon awarded
**8 prizes across 476 submissions = 1.68%** (1 grand, 4 regional, 3 honorable mentions —
https://googlecloudmultiagents.devpost.com/updates/35783-and-the-winners-are).

Applying the table to this hackathon:

| Quantity | Estimate | Basis |
|---|---|---|
| Registrants | **11,844** | measured, https://allthingsagentichackathon.devpost.com/participants, 2026-08-30 |
| Eligible submissions | **600 – 1,200** (central ~850) | 5–10% of registrants `[INFERENCE]` |
| — at the ADK rate (4.60%) | 545 | closest analogue |
| — at the Rapid Agent rate (9.86%) | 1,168 | most recent Google Cloud agent event |
| Submissions in the Fortified Enterprise Fleet track | **200 – 400** | even three-way split `[INFERENCE]`, weakly held |
| Any prize | **16 slots** | measured, prize list |
| Odds a submission wins something | **~1.3 – 2.7%** | 16 / 600–1,200 `[INFERENCE]`; ADK's actual was 1.68% |
| Odds a registrant wins something | **~0.14%** | 16 / 11,844 |

The submission gallery for this hackathon is **not yet published** — as of 2026-08-30
https://allthingsagentichackathon.devpost.com/project-gallery returns *"The hackathon managers
haven't published this gallery yet, but hang tight!"* That is normal; galleries open after the
deadline. **There is no live submission count for this event, and there will not be one until
after 2026-08-31 17:00 PDT.**

---

## What this means for a solo entrant with a finished project

- **The 11,844 number is not the field.** The field is most likely 600–1,200 projects, and
  within one category perhaps 200–400. Roughly nine in ten registrants will file nothing.
- **Finishing is the filter.** The measured gap between registering and submitting is enormous
  and every hackathon in the table shows it. A project that is actually done, deployed, and
  demonstrable clears a bar that most registrants never reach.
- **The requirements list is itself a filter, and it is long here.** Hosted project URL, code
  repo, README setup instructions, architecture diagram, and a ≤4-minute video showing live
  execution on Google Cloud. Every one of those is a place a submission dies at 4:55pm on the
  31st. The video is the item most often missing, and this hackathon's video requirement is
  specific: it must show the project running on Google Cloud.
- **One in roughly fifty to eighty submissions wins something**, using the ADK hackathon's
  actual 1.68% and this hackathon's larger prize table. That is the honest scale. It is not a
  coin flip and it is not a lottery ticket.
- **A three-way category split is the only structural advantage available**, and it is real:
  the Fortified Enterprise Fleet prize is contested only by entries that chose that category.
  How much of an advantage depends on a split nobody has published.
- **Neither the registrant count nor the credit giveaway should change any decision.** The
  credits data does not support the theory that 11,000 registrants means 11,000 tourists — but
  it does not need to, because every measured hackathon shows the same collapse between
  registering and submitting whether credits existed or not.

---

## What I could not establish

Named plainly, because these are the load-bearing gaps.

1. **No raw submission count exists publicly for any hackathon.** Every project number in the
   table is post-moderation. The number of people who started a submission and abandoned it,
   or filed one that was hidden as spam, is organiser-only data. Devpost tracks it; nobody
   publishes it.
2. **No per-category submission counts.** I checked several completed multi-track hackathons
   and found no published breakdown. The 200–400 figure for the Fortified Enterprise Fleet
   track rests on an assumption of even distribution that I believe is wrong and cannot
   correct.
3. **No credible quality distribution.** The "20% worth deep human review" figure comes from a
   source I could not open (HTTP 403) via a search summary. I am not treating it as evidence
   and neither should anyone else. I found no judge or organiser post-mortem anywhere that
   published counts of incomplete, video-less, or template submissions. Several guides assert
   the problem exists; none quantify it.
4. **No distinct-entrant counts.** Multi-submission is documented (159 projects from one Bolt
   participant) but its overall prevalence is not.
5. **Selection bias, stated explicitly.** Every row in the table is a hackathon that *published
   a gallery*. A sponsor whose event drew embarrassingly few submissions has an obvious reason
   not to publish, and Devpost lets them choose. The true distribution across all large
   sponsor hackathons is therefore probably **worse** — lower ratios — than this table shows.
   The bias runs in the direction of my numbers being optimistic about the field size.
6. **Devpost's 5–33% platform figure is unmethodologised marketing copy.** It corroborates the
   order of magnitude and nothing else.
7. **The Gemma 3n Impact Challenge is not in the table** because it ran on Kaggle, not Devpost,
   and the two platforms do not report comparable participant definitions.
8. **Participant counts drift upward after the deadline**, so every ratio here is very slightly
   low. The effect is fractions of a percentage point and does not change any conclusion.
9. **I did not find a Microsoft AI Agents Hackathon on Devpost with a published gallery**;
   Microsoft ran several 2025–2026 agent hackathons on its own properties instead, which are
   not comparable. The Microsoft representation in the table is one event, Azure AI Developer
   Hackathon.

---

*All URLs in this document were fetched on 2026-08-30. Ratios were computed by the author from
the two counts cited in each row; no ratio was taken from a source.*
