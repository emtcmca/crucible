# Eligibility, licensing and IP audit — 2026-08-30

**Scope.** Compliance of `emtcmca/crucible` (public, Apache-2.0) with the All
Things Agentic hackathon's RULES, ELIGIBILITY and INTELLECTUAL PROPERTY terms.
Submission closes **2026-08-31 17:00 PDT**.

**What this audit was checked against.** The official rules text supplied by the
coordinator on 2026-08-30, **not** `docs/contest/CONTEST.md`, wherever the two
differ. `CONTEST.md` was verified against the live rules page on 2026-08-21 and
says on its own face that it must be re-verified before submitting; §7 of it is a
one-paragraph summary that is materially narrower than the official eligibility
text (see NOTE-6). Where a question needs the live page to settle, this document
says so rather than guessing.

**Method, and what was deliberately not done.** Every finding is read off the
repository at `main` on 2026-08-30. **Nothing under `corpus/sealed/` was opened,
`CRUCIBLE_SEALED_DIR` was never set, no `gcloud` command was run, no model was
called, and the test suite was not run.** The secrets sweep was run over the
entire git object store — all 1,981 blobs on all refs, not just `HEAD` — because
a secret removed from the working tree is still served by SHA. No secret value
appears in this document; where something is named, only its file and line are
given.

**This audit changes no other file.** Every item below is a recommendation. A
code review and other agents are live in this repo.

---

## Severity summary

| # | Finding | Severity |
|---|---|---|
| B-1 | The demo video does not exist, and it is Stage One pass/fail | **BLOCKING** |
| B-2 | Submission-facing text describes results the artifact cannot currently produce, and one tracked file asserts an unseal that has not happened | **BLOCKING** |
| B-3 | Redistributed Apache-2.0 content from `google/adk-samples` carries no attribution in `NOTICE` or in the file itself | **BLOCKING** |
| R-1 | The withdrawn Gemma corpus-generation claim survives in nine places, including the top-precedence document and one executable script | RISK |
| R-2 | "Writes new attacks each round" — attack discovery claimed as shipped in the judge-facing explainer | RISK |
| R-3 | `AUDIT.md:57-58` renders two withdrawn figures as live claims | RISK |
| R-4 | The Cloud Run URL appears in nine places across seven tracked files, one of them a judged deliverable | RISK |
| R-5 | No non-affiliation line in `README.md` or `project-story.md`, beneath a Google-branded button | RISK |
| R-6 | The sealed-instance leak is disclosed in the repo and in none of the Devpost or contest documents | RISK |
| R-7 | A sentence `AUDIT.md` rules may not be said is live in three places in a tracked public file | RISK |
| R-8 | `third-party-disclosure.md` — the document that discharges the disclosure obligation — is stale and contains one false statement | RISK |
| R-9 | `MEASUREMENT.md` prints the sealed-family fingerprint 100 lines after announcing its removal | RISK |
| R-10 | Verbatim third-party retailer policy text redistributed under Eric's Apache-2.0 grant | RISK |
| R-11 | Startup Excellence prize — do not opt in | RISK |
| N-1 … N-7 | Clean results and non-obligations, recorded so they are not re-litigated | NOTE |

---

# BLOCKING

## B-1. The demo video does not exist, and Stage One is pass/fail

The rules make Stage One a gate: a submission that misses a mandatory deliverable
is not scored at all. The video is mandatory, capped at four minutes, must be
public on YouTube or Vimeo, and **must demonstrate the backend running on Google
Cloud**.

`README.md:41-45` says it plainly: *"The demo video — not yet recorded, as of
2026-08-26. Link goes here. It is the only Stage One deliverable that does not
exist."* `AUDIT.md:88-90` carries the same in its UNVERIFIED register.
`docs/contest/CONTEST.md:55` has said so since 08-22.

Everything else in Stage One is done and evidenced: the track is selected, the
repository is public, the spin-up instructions landed 2026-08-21 with real pasted
output, the architecture diagram landed 2026-08-21, and the Cloud Run captures
landed the same day (`docs/proof/cloud-run-console-2026-08-21.png`,
`docs/proof/trace-explorer-spans-2026-08-21.png`).

This is out of an auditor's hands, but no other finding in this document matters
if it is not closed. It is listed first for that reason.

One narration constraint that belongs beside it, because it interacts with the
Stage Two "Proof of Action" test — *"does the video show an unedited, live
execution"* — and with B-2: `ADR-0010` has some demo beats replaying stored
evidence bundles for quota reasons. Beats that replay should be labelled as
replay on screen. A beat that looks live and is not is the same warranty problem
as B-2, delivered in video.

## B-2. Submission-facing text describes results the artifact cannot currently produce

The rules require the Project to **"function as depicted in the video and/or
expressed in the text description."** That is a warranty, not a credibility
question, and it is the finding I would fix first after the video.

**Three separate defects converge here.**

**(a) Four mutually contradictory headline efficacy figures are live at once,
across four judge-facing files, and only one is marked superseded — in a file
that does not carry it.**

| File | Line | Figure |
|---|---|---|
| `docs/devpost/the-contribution.md` | 118-122 | attack success fell from **13.3% to 3.2%**; observed v0 **11.3%** |
| `docs/contest/SCOPE-LOCK.md` | 39 | **11.3% to 6.2%** |
| `docs/devpost/story-amendment-2026-08-28-prepared.md` | 107-110 | pooled **13.5% to 7.7%**; measurement batch 11.8 to 5.7; replication 15.4 to 9.7 |
| `RESULTS.md` | 188 | ASR v0 **13/80 = 16.2%**, final round **0/82 = 0.0%**, pooled **20/358 = 5.6%** |

`story-amendment:117` marks the `11.3 to 6.2` figure superseded — but
`SCOPE-LOCK.md:39`, which is the locked submission scope document, still carries
it unmarked. A judge who opens two of these four files finds two different
answers to the same question with nothing telling them which is current.

**(b) `RESULTS.md` says on its own face that its figures cannot be re-derived
from the artifacts they came from, and prints them in a table anyway.** The
disclosure is genuinely strong and appears three times — `RESULTS.md:8-10`
(*"No rate in this document may be quoted"*), `:22-24` and `:133-135` (*"a figure
below cannot currently be re-derived from the artifact it came from"*). The
figures then run from `:82` to `:200`, including at `:188` a complete
attack-success row ending in **0.0%**. A disclaimer above a number does not
remove the number, and `0.0%` is the single most quotable and least defensible
string in the repository.

Note that the repo has quietly re-scoped its own rule. `RESULTS.md:8-10` now
reads *"the ban is on that batch — it is not a blanket prohibition on the
repository,"* and `README.md:613` bans ASR/BPR/transfer/convergence only from the
offline campaign command. **The project brief this audit was written against
states the rule as blanket.** Those are two different rules and, as observed on
2026-08-30, the repository is
currently operating on the narrower one. That needs to be a deliberate decision
of Eric's, made once and applied everywhere, not an inconsistency a judge
discovers.

**(c) `docs/devpost/story-amendment-2026-08-28-prepared.md:126` asserts, in past
tense and declaratively, "The sealed family was opened on 2026-08-28."** It has
not been. `README.md:118-126` says that as of 2026-08-30 no F4 GCS object has
been fetched inside the measurement window. The same file at `:133` instructs
*"Keep exactly one branch below. Delete the other four"* — and all five outcome
branches remain (`:135-170`), several with unfilled `[FILL: …]` slots at `:136`,
`:141-142`, `:147`, `:154`, `:160`.

**The mitigation is real and should be recorded.** The file is titled
`PREPARED`, and `:1-8` states it was written and committed *before* the unseal
precisely so the framing could not be chosen after seeing the number. That is
good pre-registration practice and it is why this is a warranty risk rather than
a fabrication. But it is a **tracked, public** file that reads, out of context,
as a completed result narrated five contradictory ways, and `:33` marks the
replication figures **"NOT YET COMPUTED"** while `:107-110` already prints them.

**Related, and it is the deadline problem underneath all of this.** Eight
judge-facing documents promise the transfer number "on 2026-08-28":
`RESULTS.md:59-61`, updates 6 through 9, `SCORECARD-DRAFT.md:107`,
`SCOPE-LOCK.md:127`, `BUILD-LIST.md:604`. Today is 08-30 and the seal is intact.
`README.md:110-112` carries the same dated promise and is retracted 119 lines
later at `:229-234` without the earlier text being updated.

**Recommendation.** Before anything is pasted into a Devpost field, one person
picks the single set of figures that is defensible, or picks none, and every
other judge-facing file is made to agree or is made silent. `story-amendment` is
a working template and should either be resolved to one branch or moved out of
`docs/devpost/`, which is the directory a judge will read as the submission text.

## B-3. Redistributed `google/adk-samples` content carries no attribution

The rules permit open-source use **"provided the Entrant complies with applicable
open source licenses."** That is a condition, and one part of it is currently
unmet.

`crucible/cartographer/foreign/adk_customer_service.json` is a frozen descriptor
of Google's ADK customer-service sample. It is disclosed properly in
`docs/devpost/third-party-disclosure.md:44-63` — source repository, commit SHA
`629310b7…`, licence Apache-2.0, content digest. That disclosure is exemplary and
satisfies the *disclosure* obligation.

**What it does not satisfy is Apache-2.0 §4 itself.** The descriptor contains
twelve tool declarations including **docstrings and per-argument documentation
read out of Google's source** — that is copied expression, not bare facts. When
that is redistributed, §4(a)–(d) requires the recipient to receive a copy of the
licence, retained copyright and attribution notices, and, where the original
carries a `NOTICE` file, the relevant attribution notices from it.

- The repo's `NOTICE` reads only *"CRUCIBLE / Copyright 2026 Eric Tetzlaff"* and
  names no third-party work.
- The descriptor file itself carries `repository` and `commit_sha` keys and **no
  `license` or `copyright` field** — verified by reading its keys.

This is a two-line fix and it is listed as BLOCKING only because the rules make
licence compliance an express condition of using open source at all, and because
the ownership warranty (below) sits next to it.

**Recommendation.** Add a third-party section to `NOTICE` naming the ADK sample,
its copyright holder, its Apache-2.0 licence and the commit; and add
`"license": "Apache-2.0"` plus the upstream copyright line to the descriptor
JSON. Neither change touches the content digest if the added keys sit outside the
hashed payload — check `crucible/cartographer/freeze_foreign_target` before
editing, because the digest is asserted at `third-party-disclosure.md:59`.

---

# RISK

## R-1. The withdrawn Gemma corpus-generation claim survives in nine places

`docs/adr/ADR-0018` (Accepted, 2026-08-21) supersedes ADR-0009 and rules at `:35`:
*"The Gemma-generation claim is withdrawn. It may not be written or spoken
anywhere."*

The withdrawal is recorded well in eight places —
`docs/devpost/findings-and-learnings.md:66-70,146-166` is a clean public write-up
of it, `CONTEST.md:183` corrects the bonus cell, `BUILD-LIST.md:77` states the
rule, and ADR-0009 carries a superseded banner with its body preserved unedited,
which is correct practice.

**It survives, unmarked, in the document that outranks every ADR.**
`docs/CONVENTIONS.md` is first in the precedence order stated in `CLAUDE.md`, and
§3.1–3.3 carries the claim intact with no withdrawal marker anywhere:

- `:1202` — table row `| Corpus generation | one-time, ~100 artifacts | Bounded | Gemma, pinned | — |`
- `:1220-1227` — headed **"The real reason"**: *"An open-weights model, pinned by version and seed, is the only way corpus generation is reproducible by a third party. A judge can regenerate the corpus and get the same hash."*
- `:1229-1230` — **the exact clause ADR-0018 quotes and forbids**, surviving verbatim as camera direction: *"On camera, one clause: 'the attack corpus is generated by an open-weights model pinned by version and seed, because a corpus you can't regenerate is a corpus you can't pre-register.'"*
- `:1232-1247` — §3.3 in full, including `:1240` "a ~30-minute **corpus-generation** burst costs ~$0.34" and `:1247` "a third party can pull the image by digest and **regenerate the corpus**"

Further survivors: `docs/architecture-spec.md:17`, `:138-141`, `:1327`;
`docs/lanes/L2-target-corpus.md:15`; `docs/execution-spec.md:421` (bounded — `:419`
above it marks WITHDRAWN).

**And it is in executable code.** `scripts/make-lane-briefs.py:177` contains the
string `"Yes — Gemma, pinned by version and seed, for corpus generation only."` —
verified at source. That is the generator that produces the lane briefs, so
re-running it re-emits the withdrawn claim. `ADR-0018:19-20` asserts that a
`grep -rin "gemma"` returns no hits in executable code; that assertion is now
false, and the ADR itself is the only place it is recorded.

Why this is RISK and not NOTE: §1229-1230 is **camera direction**. It is written
to be spoken in the demo video, which does not exist yet. If it is read off
`CONVENTIONS.md` during the shoot, the withdrawn claim goes into the mandatory
video, on Google's own judging surface, about a Google model. That is the exact
failure ADR-0018 was written to prevent.

**Recommendation.** Strike §3.1's `Corpus generation` row, §3.2's "real reason"
paragraph and the on-camera clause, and §3.3 in place with a dated withdrawal
note pointing at ADR-0018, in the manner `execution-spec.md:419` already models.
Fix `scripts/make-lane-briefs.py:177`. Re-run the ADR-0018 grep and append the
corrected result to the ADR.

## R-2. Attack discovery is described as a shipped capability in the judge-facing explainer

The internal rule is stated exactly at
`docs/handoff/claude-design-architecture-plate.md:73-77`: *"Red-team attack
discovery is a DESIGN, not a shipped capability. Nothing in the tree originates
an attack. Selection is deterministic from an authored corpus and the model only
varies the wording, so any phrasing that credits the system with producing
attacks of its own is false."* Confirmed at
`docs/design/paraphrase-invariance-2026-08-25.md:92` and
`docs/contest/SCOPE-LOCK.md:114` ("Free attack discovery | not built").

Two files break it with the same sentence:

- `docs/what-crucible-is.md:49-50` — *"**1. The red-team agent** — a language model that attacks the target. **It writes new attacks each round**, against a target whose defenses are tighter than they were last round."*
- `docs/devpost/crucible-explainer.html:369` — the identical sentence, in the Devpost explainer page. **This one is judge-facing.**

Both verified at source. Neither carries a qualifier that the model re-words
instances drawn from an authored corpus.

Two softer instances read as roadmap and are defensible in context but read as
present capability on a skim: `crucible-explainer.html:460` and
`what-crucible-is.md:158` ("plus fresh generated attacks").

Related exposure the README does not close: `README.md:316` renders the red
strategist as emitting **"6 attack specs per round"** and the README never says
who authored the corpus. `:140-141` and `:414` use the word *"authored"* without
naming the author. The unbuilt-component disclosure is one link away in
`docs/diagrams/architecture.md:363-368`, not in the README.

**Recommendation.** Replace the sentence in both files with the true and equally
good one: the strategist selects deterministically from an authored corpus and
varies the wording, and paraphrase invariance is a measured property rather than
an assumption. Add one clause to `README.md` near `:316` naming the corpus as
hand-authored.

## R-3. `AUDIT.md:57-58` renders two withdrawn figures as live claims

Verified at source with `cat -A`. **`AUDIT.md:57` is a blank line inside the
correction table.** It terminates the C13 table, so the C14 row at `:58` does not
render as a table row on GitHub at all.

Worse, `:58` nests strikethroughs incorrectly:

```
| C14 | ~~"attack success falls from 8 of 50 to a median of 2.5 across ten runs", and the generalization split ~~"44 to 12 on attacks a run drew, 36 to 16 on attacks it never drew"~~ |
```

The first `~~` closes at the second. So *"44 to 12 on attacks a run drew, 36 to
16 on attacks it never drew"* renders **unstruck** and the trailing `~~` renders
literally. C14's whole content is that these figures are *"WITHDRAWN 2026-08-27,
in full, in both directions"* — and on the rendered page two of the four
withdrawn numbers read as standing claims **inside the row that withdraws them.**

`README.md:674-676` sends a judge with five minutes to `AUDIT.md` first. This is
the first thing that judge sees break.

**Recommendation.** Delete the blank line at `:57`; wrap the inner quotation in a
single strikethrough or drop the inner `~~` pair entirely. Then render the file
and look at it, because this defect is invisible in source.

## R-4. The Cloud Run URL is in nine places across seven tracked files

The project's own standing rule is never to link it publicly. It is public, in
files a judge is told to open.

| File | Line | Judge-facing |
|---|---|---|
| `ARCHITECTURE.md` | 250 | **Yes** — the architecture document is a mandatory judged deliverable |
| `docs/contest/CONTEST.md` | 57 | **Yes** — and the only prose carrying the project-number form too |
| `deploy/RUNBOOK.md` | 8, 234 | **Yes** — linked from `ARCHITECTURE.md:255` |
| `docs/NEEDS-ERIC.md` | 385 | tracked and public |
| `docs/proof/cloud-run-deploy-2026-08-21.txt` | 9 | **Yes** — linked from `README.md:181` and `ARCHITECTURE.md:253` |
| `docs/proof/cloud-run-redeploy-2026-08-24.txt` | 30, 42, 43 | **Yes** — linked from `README.md:183` |

`README.md` itself contains no `run.app` hostname — the rule is met in letter and
defeated by the README's own proof links.

Also public in the same files: project number `752793770087`
(`docs/ops/billing.md:12,553,567,572`, `docs/CONVENTIONS.md:2949`,
`docs/build-spec.md:590`, `scripts/gcp-env.sh:11`) and the compute default service
account `752793770087-compute@developer.gserviceaccount.com`
(`deploy/RUNBOOK.md:112`).

**Assessment.** The service runs `--no-allow-unauthenticated` with zero
`allUsers` bindings, so what is exposed is a hostname and an identity mapping,
not access. This is a **policy** violation and an attack-surface disclosure, not
a credential leak. The recorded rules do not cover this — it is CRUCIBLE's own
rule, not the hackathon's, and the hackathon in fact *encourages* a hosted URL
judges can test (`CONTEST.md:57`, row 8, "highly encouraged").

**Recommendation.** Decide deliberately rather than by accident. Either the URL is
public because a judge should be able to reach it — in which case fix
`CONTEST.md`'s note about which form to paste, and close row 8 properly — or it is
not, in which case redact it from `ARCHITECTURE.md:250` and the two proof
transcripts, which is where a judge actually lands. What should not stand is a
rule the repo states and does not follow.

## R-5. No non-affiliation line in the README or the primary Devpost story

The disclaimer exists and is correctly worded — `AUDIT.md:268` and
`docs/devpost/the-contribution.md:168`: *"Not reviewed, endorsed, or responded to
by Google in any way. Not production-ready."* The prohibition on implying
otherwise is enforced in `docs/CONVENTIONS.md:2759`,
`docs/contest/track-fit.md:132` and `docs/execution-spec.md:766`, and there are
passing negative checks for it at
`docs/proof/L6-negative-checks-GREEN-2026-08-20.txt:69,71`. **Nothing in the repo
claims Google endorsement.** That part is clean.

The gap is placement. A grep for `endorse|not reviewed|sponsor|affiliat` across
`README.md` returns zero, and the same is true of
`docs/devpost/project-story.md` — the primary Devpost narrative —
`SCORECARD-DRAFT.md`, and `crucible-explainer.html`.

What a README reader sees above the fold instead: `:11-12` "Built for the Google
All Things Agentic hackathon", and at `:29` a Google-styled **"Open in Cloud
Shell"** button served from `gstatic.com`.

**On the button specifically:** it is Google's own published, sanctioned badge
for exactly this purpose, so it is not a trademark problem and it should stay —
it is a genuinely good judge-experience decision. The finding is that Google
branding sits at line 29 and the disclaimer sits in a different file.

One title worth a second look: `docs/devpost/2026-08-28-update-8-a-google-agent-it-had-never-seen.md`
reads, skimmed, as Google involvement. The body defuses it well at `:26` — *"We
are not claiming a vulnerability in Google's code"* — and `SCORECARD-DRAFT.md:46`
does the same. Leave the body; the title is the exposure.

**Recommendation.** One line, verbatim from `AUDIT.md:268`, in `README.md` near
the top and at the foot of `project-story.md`.

## R-6. The sealed-instance leak is disclosed in the repo and nowhere in the submission

**The repo disclosure is the strongest thing in this audit.**
`README.md:113-117`, inside the "what is not defensible today" block that the
README tells judges to read before any number:

> **The seal has a disclosed leak.** One sealed instance of twenty-four was named
> verbatim in a public commit on 2026-08-21. It is redacted going forward and was
> **deliberately not replaced**. If that instance's result is ever singled out,
> the leak is stated in the same breath.

`AUDIT.md:162-175` carries the full account, including that it was found by a leak
checker on its first run, against a file its own author wrote. `AUDIT.md`'s title
line names "disclosed leaks". Discoverable, prominent, honest.

**`git grep -in "leak" -- docs/devpost docs/contest` returns zero hits.** The leak
appears in none of `project-story.md`, `SCORECARD-DRAFT.md`,
`the-contribution.md` (including §7 "The boundary" at `:165-172`, which lists
every *other* limitation), `findings-and-learnings.md`,
`crucible-explainer.html` (including its "Why believe the number" seal section at
`:397-403`), `SCOPE-LOCK.md`, `CONTEST.md` or `track-fit.md`.

A judge who reads only the Devpost page sees the seal presented as intact —
`crucible-explainer.html:398`: *"It is not in the public repository. It sits in a
cloud bucket the attacking identity cannot read. Its fingerprint was published
before the run"* — and never learns one of the twenty-four is public.

**The standing rule is currently satisfied only by accident.** `AUDIT.md:170-171`
binds: if that instance's result is singled out, the leak is stated in the same
breath. No Devpost document singles out a per-instance result *yet*. All five
transfer branches in `story-amendment:135-170` are written to report per-instance
outcomes and **none of the five carries the leak sentence**, so applying that file
as written breaks the rule at the exact moment the transfer result is published.

**Two smaller omissions in the README version**, measured against
`AUDIT.md:162-175`: it does not say a public commit is served by SHA long after a
rewrite, i.e. that the leak is permanent and still fetchable, and it does not say
the redaction does not undo publication. A reader of `:113-117` alone may infer
redaction closed it. One clause fixes it.

**Recommendation.** Put the leak sentence into `project-story.md` and
`the-contribution.md` §7, and into whichever transfer branch of `story-amendment`
survives. Add "a public commit is served by SHA forever" to `README.md:114`.

## R-7. A sentence `AUDIT.md` rules may not be said is live in a tracked public file

`AUDIT.md:225-228` rules that the flat form *"no F4 object has been read"* may not
be written, because it is false about local reads and the honest claim is a
narrower, three-way split. Every handoff was corrected on 2026-08-30
(`docs/handoff/codex-review-3-2026-08-29.md:15`, `-4-:9`, `-5-:12`) and the repo's
`CLAUDE.md` session block was rewritten to the scoped form.

The pre-registration was not. `docs/proof/f4-unseal-preregistration-2026-08-25.md`
carries *"This amendment is written while the seal is intact and no F4 object has
been read"* at **`:567`, `:642` and `:730`**. That file is tracked, public, and
linked from `README.md:112`.

It is also append-only by its own rule (`:264`, `:709-710`) and by
`AUDIT.md` C13's principle that *"a pre-registration edited after the fact is not
one."* So the remedy is an **appended dated amendment**, not an edit, and no such
amendment exists.

Right now a public document asserts a sentence the project's own correction
ledger names as false. That is an open disclosure obligation, not a stylistic
one.

**Recommendation.** Append a dated amendment to the end of the pre-registration
scoping the sentence, citing `AUDIT.md:225-228`. Do not edit `:567`, `:642` or
`:730` in place.

## R-8. `third-party-disclosure.md` is the file that discharges the disclosure obligation, and it is stale

**First, the good news, because this file is why B-3 is the only licence finding
and not five.** The official rule requires disclosure of *"any other pre-existing
code or work incorporated into the Project."*
`docs/devpost/third-party-disclosure.md` does that properly: it names the one
piece of third-party code committed into the tree, pins it by commit SHA and
content digest, states its licence, names every runtime dependency with its
licence, names the models, names the fonts, and gives five commands so a judge can
re-derive all of it. It is better than most projects manage.

**Three defects.**

1. **It is a repository file. The rule says "as part of the Submission."** A doc
   in `docs/devpost/` is not in the submission unless someone pastes it into the
   Devpost form's disclosure field. Confirm that happens.

2. **The dependency table at `:26-32` is missing one dependency.**
   `requirements.txt` now pins six packages; the table lists five.
   **`google-cloud-storage==3.10.1`** — added 2026-08-28 after adversarial review
   found `real_gate.py:718` importing it with no dependency file naming it — does
   not appear. Neither does `playwright@1.60.0` from `capture/package.json`, which
   is a dev tool rather than a runtime dependency but is the one npm dependency in
   the tree.

3. **`:87-89` contains a false statement.** It says the explainer loads three
   Google Fonts and *"No other external asset, script, stylesheet or CDN is
   referenced by anything in this repository."* `README.md:29` and
   `docs/cloudshell-badge.md:17` reference `https://gstatic.com/cloudssh/images/open-btn.svg`.
   The re-derive command at `:109` (`grep -rn "fonts.googleapis.com" docs/`) is
   scoped so that it cannot catch it.

`:13` also says "340 commits as of this file"; the count is now **529**. That is
correctly framed as an as-of figure, so it is accurate rather than stale — but it
will read as stale to a judge who runs the command at `:106`.

**Recommendation.** Add the two dependency rows, correct `:87-89` to name the
Cloud Shell badge, widen the grep at `:109`, and re-date the commit count.

## R-9. `MEASUREMENT.md` prints the sealed fingerprint 100 lines after announcing its removal

`MEASUREMENT.md:92-100` states that the fingerprint value *"used to be printed
here as a 64-hex literal. **Removed 2026-08-26 under ruling 46**… No prose
document states a current hash value, including this one."*

`MEASUREMENT.md:203-205` then prints it three times, as `fingerprint`, `recorded`
and `recomputed`, inside a fenced banner block.

Verified at source. It is a truncated seal digest rather than a secret, and it is
inside a pasted command banner rather than in prose, which is arguably outside
ruling 46's scope — but it is the sealed family's digest, in the same file that
announces compliance, a hundred lines apart. Ruling 46's stated reason is that a
hash in a document is a string nothing can notice going stale, and that is exactly
the risk here: the seal has not been opened and the artifact may yet move.

**Recommendation.** Either replace the three values in the `:203-205` block with
the artifact path and the command that reads it, or add one line to `:92-100`
carving out pasted command output explicitly. Silent inconsistency is the one
option that costs credibility.

## R-10. Verbatim third-party retailer policy text under Eric's Apache-2.0 grant

The rules' ownership warranty is strict: the Project must *"be your original work
product; be solely owned by you with no other person or entity having any right or
interest in it."*

`docs/refund-policy-research.md` (514 lines, compiled 2026-08-20) quotes published
returns-policy language verbatim from Target, Best Buy, Newegg, Zara, Nordstrom,
Dell, Grainger, Steam, eBay, Amazon and Adobe — including full sentences in
quotation marks at `:31-41`. Retailer names and trademarks are used descriptively
throughout.

**Assessment.** Short, attributed, transformative quotation in a comparative
research document is textbook fair use, and the trademark use is nominative. This
is not a plagiarism finding — the sourcing is meticulous and `:5` even flags which
numbers are synthesis rather than sourced, which is more care than most published
research shows. The exposure is narrower and more technical: **the repository
distributes that text under an Apache-2.0 grant, and the quoted sentences are not
Eric's to license.** Apache-2.0 purports to grant recipients rights in the whole
work.

The recorded rules do not cover how a hackathon reads that warranty against
quoted source material inside a research document. It is very unlikely to be
raised. It is cheap to close.

**Recommendation.** Add a header to `docs/refund-policy-research.md` stating that
quoted policy text remains the property of the named retailers, is reproduced
under fair use for comparison, and is not covered by this repository's Apache-2.0
grant. One paragraph.

## R-11. Do not opt in to Startup Excellence

The Startup Excellence prize requires an **incorporated organization and a
corporate email address**. Eric is solo and unaffiliated. Opting in would be a
self-inflicted eligibility problem — a claimed prize category the entrant does not
qualify for, on a submission whose entire pitch is that it does not overclaim.

He is eligible for **Individual / Hobbyist — Best Team or Solo Build** ($10,000,
two winners) and **Best Architectural Design** ($5,000, two winners), and for the
track prize. **A project may win at most one prize**, so the choice of what to
emphasise matters more than the number of boxes ticked.

`CONTEST.md:213-224` already ranks these correctly by odds rather than by size and
puts Best Architectural Design first. Nothing needs to change except making sure
the form is filled that way.

---

# NOTE

## N-1. Secrets and credentials — clean, and the sweep went past `HEAD`

No credential material was found anywhere, in the working tree or in history.

**What was checked.** Every blob in the object store — **1,981 blobs across all
refs**, enumerated with `git cat-file --batch-all-objects` — scanned for private
key headers, service-account JSON markers, Google API keys, OAuth access tokens,
OpenAI keys, GitHub PATs, Slack tokens and AWS access-key IDs. Zero hits. The scan
mechanism was sanity-checked against a known-present string first, because a grep
that cannot hit is a check that cannot fail.

Separately: **no file matching a secret-shaped name has ever been added on any
ref.** `git log --all --diff-filter=A --name-only` over 850 added paths returns
one match, `infra/create-service-accounts.sh`, which is a creation script and
holds no key material.

`.gitignore:1-8` covers env files, `*service-account*.json`, `*credentials*.json`,
`*.pem` and `*.key`.

## N-2. Personal and customer data — clean, and the fixtures are demonstrably invented

This project models a refund agent, so the question is whether its fixtures are
real customer records. They are not, and the evidence is mechanical rather than
assumed: **every email address in `corpus/`, `fixtures/` and `baseline/` uses an
RFC 2606 reserved domain** — `mailbox.example`, `example.invalid`, `gmail.example`,
`proton.example` and so on, 71 + 28 + 22 + … across the set. Reserved TLDs cannot
resolve and cannot belong to a real person. Order IDs, account IDs and payment
instrument IDs follow the same invented pattern (`CUS-2904`, `ORD-6015`,
`pi_visa_2904_01`).

The only real email in the tree is `eric@erictetzlaff.com` (45 occurrences),
which is Eric's published professional address and is intentional.

**Eric's cell number does not appear anywhere** — not in the working tree and not
in any of the 1,981 historical blobs. That was checked explicitly because the
identity canon flags it as never-publish.

## N-3. Originality — verified from git, and it satisfies the New Projects rule

The rule: *"Projects must be newly created during the Submission Period."* The
Submission Period opened **2026-08-03**.

- **First commit `fc3a612`, 2026-08-20 10:45:12 -0400** — seventeen days into the period.
- **529 commits, one author**, `Eric Tetzlaff <emtcmca@gmail.com>`, on every commit on every ref. No co-author, no bot, no vendored history.
- **No `node_modules`, no vendored library source, no third-party file with a foreign copyright header.** A repo-wide grep for `copyright|(c) 20|SPDX-License-Identifier|All rights reserved` outside `LICENSE`/`NOTICE` returns only two prose mentions in `docs/CONVENTIONS.md:2578` and `docs/lanes/L6-log.md:126`, both discussing *this* repo's licensing.
- The one file that could look imported, `crucible/armorer/experiment.py:188`, says "ported from the spike's three scenarios" — and `spike/` is this project's own gitignored Day-1 work, created 2026-08-20.
- `tests/test_reader_known_bad.py:4` cites "the promptsmith lesson" — that is a **method** carried from another of Eric's projects (deliberately-broken fixtures a suite must fail), not code. No promptsmith code is present. Worth knowing if a judge asks; not a disclosure obligation, since the rule covers code and work incorporated, not ideas an author has had before.

## N-4. AI-assistance disclosure — **not required, and correctly absent**

The official rules text settles this and settles it narrowly:

> *"Participants may use standard development tools, including frameworks,
> libraries, starter templates, and **AI coding assistants**, but must disclose any
> **other pre-existing code or work** incorporated into the Project."*

**AI coding assistants are expressly permitted and require no disclosure.** Much
of this repository was written with AI assistance; nothing in the recorded rules
obliges saying so, and no judge-facing document does. That is compliant.

What *is* obliged is the pre-existing-code disclosure, and that is handled — see
R-8 and B-3.

**One note on optics rather than rules.** `AUDIT.md:313` says "A lane writing this
README first drafted…", where *lane* is the project's internal word for an agent
and is never defined for an outsider. It is not a disclosure failure. It may read
as one to a judge who notices it and cannot decode it. A one-line glossary entry
would cost nothing.

## N-5. Dependency licences — every one compatible with redistribution under Apache-2.0

Read from installed package metadata on this machine, not recalled:

| Package | Pin | Licence | Compatible with Apache-2.0 redistribution |
|---|---|---|---|
| `google-adk` | 2.1.0 | Apache-2.0 *(classifier: Apache Software License)* | Yes — same licence |
| `jsonschema` | 4.26.0 | MIT | Yes — permissive, Apache-2.0-compatible |
| `referencing` | 0.37.0 | MIT | Yes |
| `PyYAML` | 6.0.3 | MIT *(License field and classifier)* | Yes |
| `pytest` | 9.0.3 | MIT | Yes |
| `google-cloud-storage` | 3.10.1 | Apache-2.0 *(License field "Apache 2.0")* | Yes |
| `playwright` (dev, `capture/`) | 1.60.0 | Apache-2.0 | Yes — dev tool, not redistributed |

`jsonschema`, `referencing` and `pytest` expose no `License` field or classifier
in installed metadata (they declare via `License-Expression` in modern packaging
metadata); all three are MIT upstream. If a judge challenges one, the answer is in
each project's own `LICENSE` file, and the claim in
`third-party-disclosure.md:26-32` matches.

**No dependency is copyleft. No dependency is redistributed in this tree** —
`requirements.txt` names them, `pip` fetches them, none is vendored.

Web fonts: Newsreader, IBM Plex Mono and IBM Plex Sans from Google Fonts, **SIL
Open Font License**, loaded by reference in `crucible-explainer.html` and not
redistributed. Compatible.

## N-6. `LICENSE` and `NOTICE` are correct for Eric's own work

`LICENSE` is the canonical, unmodified Apache License 2.0 text, 11,358 bytes,
including the standard appendix with its `[yyyy] [name of copyright owner]`
placeholders. **Leaving those placeholders unfilled is correct** — the appendix is
instructional boilerplate, not the grant, and editing it is a common mistake.

`NOTICE` asserts `CRUCIBLE / Copyright 2026 Eric Tetzlaff` with the standard
Apache-2.0 boilerplate. Correct for Eric's own work. Its only gap is the
third-party attribution in B-3.

## N-7. Eligibility — what I could check and what I could not

**Checked from the repository and from the official text supplied:**

- Sole individual entrant, unaffiliated. 529 commits, one author, one email. No organization named anywhere in the tree.
- No Google or Devpost affiliation is claimed or evidenced anywhere in the repo.
- Ohio, US — not a resident of Italy, Quebec, Crimea, Cuba, Iran, Syria, North Korea, Sudan, Belarus or Russia.

**Cannot be checked from a repository, and is Eric's to confirm:**

- Age of majority. *(Not in doubt; stated for completeness.)*
- Not subject to US export controls or sanctions.
- Not employed by a government agency, and no other real or apparent conflict of interest.
- **Not a member of the household of** a Google or Devpost employee, intern or contractor. This clause is broader than `CONTEST.md:230-233`'s summary, which mentions only employees and contractors and omits households and the government-agency and conflict-of-interest clauses entirely.

**`docs/contest/CONTEST.md` §7 is a summary, and it is narrower than the official
text in three respects** — households, export-controls/sanctions, and the
government-agency conflict clause. Its conclusion ("Ohio, solo, unaffiliated —
clear") still holds on the broader text. But the file's own instruction at `:9-11`
is that anything deciding real work is re-checked against the live page before
submission, and §7 is now demonstrably not a complete restatement.

**This needs the live rules page to close**, not the repository: the official text
supplied here arrived second-hand on 2026-08-30 and `CONTEST.md` was last verified
against the page on 2026-08-21.

---

# What must change before submitting

Numbered shortest first. Items 1 through 5 are under twenty minutes each.

1. **Delete the blank line at `AUDIT.md:57` and fix the nested `~~` at `:58`,** then render the file and look at it. Two withdrawn figures are currently published as live claims inside the row that withdraws them. *(R-3)*

2. **Add the non-affiliation line to `README.md` and to `docs/devpost/project-story.md`** — verbatim from `AUDIT.md:268`: *"Not reviewed, endorsed, or responded to by Google in any way."* *(R-5)*

3. **Add third-party attribution for the ADK sample to `NOTICE`, and a `license` field to `crucible/cartographer/foreign/adk_customer_service.json`.** Check `freeze_foreign_target` first so the asserted digest does not move. This is the one open licence-compliance obligation. *(B-3)*

4. **Fix the two "writes new attacks each round" sentences** — `docs/what-crucible-is.md:49-50` and `docs/devpost/crucible-explainer.html:369`. The explainer is judge-facing. *(R-2)*

5. **Repair `docs/devpost/third-party-disclosure.md`:** add `google-cloud-storage==3.10.1` and `playwright@1.60.0`, correct the false "no other external asset" claim at `:87-89` to name the Cloud Shell badge, and widen the grep at `:109`. Then confirm this document is actually pasted into the Devpost disclosure field, because a repo file is not part of the submission. *(R-8, and the rules' express disclosure obligation)*

6. **Put the seal-leak sentence into `docs/devpost/project-story.md` and `the-contribution.md` §7,** and into whichever transfer branch of `story-amendment` survives. Add "a public commit is served by SHA forever" to `README.md:114`. The repo's disclosure is excellent; the submission's is absent. *(R-6)*

7. **Append a dated scoping amendment to `docs/proof/f4-unseal-preregistration-2026-08-25.md`.** Append — do not edit `:567`, `:642` or `:730`. A public document currently asserts a sentence `AUDIT.md:225-228` rules may not be said. *(R-7)*

8. **Strike the Gemma corpus-generation claim in `docs/CONVENTIONS.md` §3.1–3.3** (`:1202`, `:1220-1227`, `:1229-1230`, `:1232-1247`), in `docs/architecture-spec.md:17,138-141,1327`, in `docs/lanes/L2-target-corpus.md:15`, and in **`scripts/make-lane-briefs.py:177`**. `:1229-1230` is camera direction for a video that has not been shot. *(R-1)*

9. **Decide the Cloud Run URL question deliberately** — publish it properly and close `CONTEST.md` row 8, or redact it from `ARCHITECTURE.md:250` and the two proof transcripts. What must not stand is a rule the repo states and does not follow. *(R-4)*

10. **Settle the figures.** Pick one defensible set or none, make every judge-facing file agree, resolve `story-amendment` to a single branch or move it out of `docs/devpost/`, and delete the past-tense unseal assertion at `:126`. Reconcile the two versions of the project's own "no rate" rule. This is the largest item and it is the one the "functions as expressed in the text description" warranty turns on. *(B-2)*

11. **Record the video.** *(B-1)*

12. **Before submitting, re-verify `docs/contest/CONTEST.md` against the live rules page,** and widen §7's eligibility summary to include households, export controls and the government-agency conflict clause. The file instructs this itself at `:9-11` and was last verified 2026-08-21. *(N-7)*

**Do not opt in to Startup Excellence.** *(R-11)*
