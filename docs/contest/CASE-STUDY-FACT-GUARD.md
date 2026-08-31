# Fact guard for an external case study about CRUCIBLE

**Written 2026-08-31.** For a session outside this repository - a portfolio or blog
write-up - that has been pointed at the tree and asked to summarise it.

**Why this file exists.** A summariser reading this repository cold has no way to know
which of its sentences are retired, which figures were withdrawn, and which true
statements stop being true one word wider. Several claims here were false for weeks
before an audit caught them, and one reached a live portfolio page. Read this before
writing, not after review.

---

## 1. The two conditions the bonus actually has

The Devpost bonus field asks for a link to a piece of content, and it has two
conditions, both of which are pass/fail:

1. **Public. Not unlisted, not draft, not password-gated.**
2. **The content must itself say it was created for the purposes of entering this
   hackathon.** Not the submission form saying it - the content.

Wording that satisfies condition 2, adapt freely:

> I wrote this case study for the purposes of entering the Google Cloud **All Things
> Agentic** hackathon, track *The Fortified Enterprise Fleet*.

**An unmet condition on a bonus field is a worse trade than an unclaimed bonus.** If
the piece does not carry that sentence when it goes live, do not paste the link.

## 2. What must be stated, and is true

- Built for the **Google Cloud "All Things Agentic" hackathon**, track **The Fortified
  Enterprise Fleet**.
- Built on the **Google Agent Development Kit**: `google-adk==2.1.0`, pinned, imported
  and load-bearing at `crucible/plugin/adk.py:78`. Enforcement runs at the ADK
  `BasePlugin` `before_tool` callback - **in code, not in an instruction to a model.**
  That is the architectural claim worth making, and it is defensible.
- **Google Cloud services this project actually uses:** Vertex AI (global endpoint),
  Cloud Run, Cloud Storage (three buckets), Cloud IAM, Cloud Logging, Cloud Build,
  Artifact Registry, Cloud Trace.
- **Models, exact ids:** `gemini-3.7-flash` (Armorer), `gemini-3.6-flash` (red
  strategist), `gemini-3.5-flash-lite` (Coroner and target agent),
  `google/gemma-4-26b-a4b-it-maas` (capability cartographer, via Vertex Model Garden).
- **Cloud IAM is the blindness boundary**, not a `.gitignore` entry. The attacking
  identity holds no read on the sealed bucket. That is the strongest single sentence
  in the architecture and it is fully true.

## 3. Do not write these. Every one is retired or false.

| Never write | Why |
|---|---|
| Any `gemini-2.5-*`, `gemini-3.1-*`, or bare `gemini-3-*` id | dead for this project. Litt's Gemini 2.5 Pro is a different project |
| `MONEY_MOVE`, `COMM_EXTERNAL` | dead short forms. The classes are `CAP_MOVES_MONEY`, `CAP_EXTERNAL_COMMS`, `CAP_MUTATES_DURABLE_STATE`, `CAP_READS_PII`, `CAP_ESCALATES_PRIVILEGE`, `CAP_INVOKES_AGENT`, plus `UNCLASSIFIED` |
| Gemma generated the attack corpus | **WITHDRAWN, ADR-0018.** False since written. Gemma classifies capability and does nothing else. The corpus was authored by hand |
| "frontier models refuse to author red-team payloads at volume" | dead phrasing. The approved framing is **reproducibility** |
| CRUCIBLE discovers or autonomously generates novel attacks | **RED discovery is a design, not a shipped capability.** Nothing in the tree authors an attack |
| CRUCIBLE has a spend cap | **There is no cap.** The $160 is an alert with email recipients and it stops nothing |
| The Cloud Run URL, in any public text | never link it |
| BigQuery, Firestore | BigQuery is not created and no client code exists; Firestore is provisioned and nothing holds a client for it. Both were claimed until the 2026-08-30 audit removed them |

**Do not blur CRUCIBLE with Litt.** CRUCIBLE runs on ADK. Litt does not - ADK is a
declared dependency Litt's code never imports.

## 4. Figures

**No rate from the sixty-run batch of 2026-08-25 may be quoted.** `RESULTS.md` is a
record of that batch, not a scoreboard, and it cannot currently be re-derived from the
artifacts it came from.

**Never state a rate without its denominators in the same sentence.** If a figure needs
a denominator to be honest, and the sentence does not have room for it, cut the figure.

**The one result worth leading with is negative, and it should be volunteered:**

> Of 32 rules promoted across the bundles the offline reader accepts, **13 closed the
> breach they were written for and 19 were no-ops on it.** Recounted 2026-08-27.

Say it with its caveat attached: those bundles live in `evidence/`, which is
**gitignored**, so the finding is reproducible on the build machine and **not from a
clone**. The cause is not carelessness - the tripwire's aggregate clause groups by a key
the Armorer's DSL cannot express.

**The most transferable finding, and it is about measurement rather than about an
agent: a rule that over-blocks passes every gate.** It blocks the attacks, the approval
oracle rubber-stamps the benign cases, benign pass rate reads perfect, the gate promotes
it, and the agent has been made useless. That is the paragraph a reader remembers.

**Every count is verify-on-use.** Read it from source at the moment of writing; never
recall one. The test count in `README.md` went stale three times and is marked
verify-on-use for exactly that reason. Take any figure from `README.md` on `main`, which
carries its own "What is not defensible today" section and is fresher than any summary.

## 5. The seal, and the honest version of it

The held-out attack family was **never opened, by decision.** No transfer result exists
and none may be claimed. The reason is stateable and is not a hedge: eleven adversarial
review rounds kept finding defects in the runner, the last closing the morning of
submission, and the family gets exactly one attempt - so spending it against a runner
whose newest defect was hours old would have produced evidence nobody could rule on.

**A sealed instance leaked once, on 2026-08-21**, in a ratification document that was
committed and pushed publicly before being redacted. A public commit is served by SHA
forever and the instance was deliberately not replaced. **If any individual sealed
instance's result is singled out, the leak is stated in the same breath.** Never imply
to a determined reader that the seal is intact.

## 6. The accuracy boundary, which belongs in the piece

Reuse this. It is the repository's own language:

> Eleven days, one person, one target agent. No users, no downloads, no adoption of any
> kind. Every figure is single-sample, k=1, with no stability estimate. The sealed set
> was reviewed by one person, who is also the builder. Not production-ready. Not
> reviewed, endorsed, or responded to by Google in any way.

**Publishing the worst number unprompted is what buys belief in the others.** A case
study that leads with the no-op finding and the accuracy boundary is more persuasive
than one that buries them, and it is the only version that survives a reader who opens
the repository.

## 7. Before the link is pasted

- [ ] The piece **says** it was created for this hackathon
- [ ] Published **public**, verified in an incognito window
- [ ] No dead vocabulary from section 3
- [ ] No rate without its denominators
- [ ] No figure recalled rather than read from `README.md` on `main`
- [ ] Run the voice checker - it is Eric's name on it:
      `node C:\dev\linkedin\knowledge\voice-check.mjs --file <draft>`
- [ ] Published **before** submitting, and **not edited after 17:00 PT** - linked
      material locks with the entry until winners are announced
