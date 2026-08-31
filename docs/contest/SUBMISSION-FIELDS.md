# Devpost submission fields — what to paste where

**Written 2026-08-31.** One place for the values that go into the form, so they
are not retyped from memory at 16:50 PT. Every row names where it came from.

**Everything locks 2026-08-31 17:00 PT.** After that: no repo edits, no video
replacement, no material changes, until winners are announced.

---

## The fields

| field | value | source |
|---|---|---|
| **Track** | The Fortified Enterprise Fleet | `docs/contest/CONTEST.md` §3 |
| **Google SDK used** | **ADK** | `google-adk==2.1.0`, imported and load-bearing at `crucible/plugin/adk.py:78` |
| **Project start date** | **2026-08-20** | `git log --reverse`, first commit `fc3a612` at 10:45:12 -0400. Submission period opened 08-03 |
| **Repository** | https://github.com/emtcmca/crucible | public, Apache-2.0. **No `testing@devpost.com` share needed** |
| **Video** | **https://youtu.be/tdro9Fs97mY** | must be **public**, checked in an **incognito window**, **under 4:00** |
| **Architecture diagram** | `docs/diagrams/loop.svg` | upload the rendered PNG from `tools/capture/out/cards/02-architecture.png` |
| **Hosted project URL** | **see the ruling below** | |
| **Startup Excellence opt-in** | **DO NOT OPT IN** | needs an incorporated organisation and a corporate email. Solo and unaffiliated is not eligible |

## "Built with" tags

Paste these. Every one is a thing the build actually uses, verified from source
2026-08-31 - **no aspirational tags**, which is the one field where padding is
free and therefore tempting.

```
python, google-cloud, vertex-ai, google-adk, gemini, gemma, cloud-run,
google-cloud-storage, cloud-iam, cloud-logging, cloud-build, artifact-registry,
cloud-trace, pytest, jsonschema
```

| tag | why it is there |
|---|---|
| `python` | 3.11.9 |
| `google-adk` | `google-adk==2.1.0`, enforcement at the `before_tool` callback |
| `gemini` | 3.7-flash, 3.6-flash, 3.5-flash-lite across four roles |
| `gemma` | `google/gemma-4-26b-a4b-it-maas`, the capability cartographer |
| `vertex-ai` | every model call, global endpoint |
| `cloud-run` | deployed and serving under `crucible-target` |
| `google-cloud-storage` | three buckets: evidence, policies, the sealed holdout |
| `cloud-iam` | the blindness boundary, enforced in IAM rather than in a prompt |
| `cloud-logging` | data-access audit records, which the holdout counter reads |
| `cloud-build`, `artifact-registry` | used by `adk deploy cloud_run` |
| `cloud-trace` | bound to the target service account |
| `pytest`, `jsonschema` | pinned in `requirements.txt` |

**Do NOT tag `bigquery` or `firestore`.** BigQuery is not created and no client
code exists; Firestore is provisioned and nothing in the repository holds a
client for it. Both were claimed in `third-party-disclosure.md` until the
2026-08-30 audit removed them, and a tag list is exactly where an unearned
service name goes unnoticed.

---

## "Try it out" links

Devpost's own hint is *"URL for demo site, app store listing, GitHub repo, etc."*
**This field is the answer to the hosted-URL question**, and it is a better
answer than a hosted URL would have been: it hands a judge a working environment
rather than an endpoint that would return 403.

Two links, in this order:

```
https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https://github.com/emtcmca/crucible&cloudshell_git_branch=main&cloudshell_tutorial=docs/cloudshell-tutorial.md
```

```
https://github.com/emtcmca/crucible
```

Label the first one something like **"Run it in your browser - Cloud Shell, no
credential"** if the field allows a label. It opens the repository in the
judge's own Cloud Shell with the guided tutorial pane: the checker proving it can
fail, the policy language refusing to learn a string filter, and the offline
reader refusing a damaged bundle. Step 5b makes one live Vertex call on their
project if they want it; step 6 says why the full loop is not offered.

---

## Project media

**Ready to upload, in order, at `tools/capture/out/submission-media/`.**
The first image is the gallery thumbnail, so it is the architecture.

Against Devpost's stated limits: **PNG, largest file 0.37 MB against a 5 MB
cap, 8 images against a limit of 15.** Nothing needs resizing or converting.

| # | file | what it is |
|---|---|---|
| 1 | `01-architecture-THUMBNAIL.png` | the hardening loop, **3840x2560, 3:2** - Devpost's gallery ratio, so it is not letterboxed. **This is also the mandatory architecture diagram** |
| 2 | `02-built-with.png` | five models by role, eight Google Cloud services, and what a judge can run themselves |
| 3 | `03-google-cloud-proof.png` | the live terminal: Cloud Run + its own service account, the enabled APIs, the three buckets, Gemma at http 200 |
| 4 | `04-the-figure.png` | pooled 13.5 to 7.7 with all three rows and every denominator |
| 5 | `05-the-negative-finding.png` | 32 rules promoted, 13 closed the breach, 19 no-ops |
| 6 | `06-a-real-run.png` | the run view: a real bundle replayed, LIVE, with project and revision on it |
| 7 | `07-the-target-agent.png` | the refund agent moving money, and the ledger row after |
| 8 | `08-five-locks.png` | the five locks, committed before the first measurement |

The 16:9 cards will letterbox slightly in a 3:2 gallery. That is fine and is why
the architecture is the one supplied at 3:2 - it is the frame anyone actually
studies.

**Everything else a judge might want is in the repository**, not the gallery:
`docs/diagrams/loop.svg` is the same plate as vector, and `docs/proof/` holds
the transcripts rather than assertions.

---

## Additional links

| what | URL |
|---|---|
| LinkedIn post about the build, 2026-08-31 | https://www.linkedin.com/feed/update/urn:li:activity:7500205777584963584/ |

**On the LinkedIn link.** It belongs in an *additional links* or *supporting
material* field, not in the project story and not in a Devpost update. The story
is the record of what was built and when; a link to a post about the build is a
different kind of artifact and mixing them dilutes the thing the story is
evidence for. It is also not a substitute for anything the rules require.

---

## The hosted URL ruling

**Submit no hosted URL.** Name the browser path instead.

The Cloud Run service is `--no-allow-unauthenticated` with **zero IAM bindings**,
so a judge who opens the URL gets a 403. The rules require login credentials in
the testing instructions for a private site, and minting a credential for a
harness whose whole subject is agents holding permissions they should not is the
wrong trade for a field that is *highly encouraged* rather than mandatory.

**What to say instead: the full block is the next section.**

Full reasoning: `docs/contest/AUDIT-stage-one-2026-08-30.md`, Row 8.

---

## Before you submit

- [ ] Video **public**, verified in an **incognito window**, **under 4:00**
- [ ] Video shows the backend on Google Cloud — that is the N6a terminal beat
- [ ] `git status --porcelain` empty, and `origin/main` current
- [ ] `python scripts/pre-read-seal-proof.py` prints **VERDICT PASS**
- [ ] `python scripts/contract-check.py` prints **ALL PASSES OK**
- [ ] Update 10 posted
- [ ] Project story updated — the transfer section says there is no transfer result

**Nothing may be torn down before 2026-10-01.** Availability runs through the
Judging Period, not to the submission deadline.

---

## The "Additional info" page, field by field

Answers verified 2026-08-31. Where a field has a trap, the trap is named.

| field | answer |
|---|---|
| **Sponsor / Special Prizes** | **Leave Startup Excellence UNCHECKED.** It needs an incorporated organisation and a corporate email address. Solo and unaffiliated is not eligible, and ticking it does not make it so |
| **Submitter Type** | Individual |
| **Country of residence** | United States |
| **Category** | **The Fortified Enterprise Fleet** |
| **Organization name** | *blank* — not submitting on behalf of one |
| **Project start date (MM-DD-YY)** | **08-20-26** — first commit `fc3a612`, 2026-08-20 10:45:12 -0400, seventeen days inside a submission period that opened 08-03 |
| **Code repo URL** | `https://github.com/emtcmca/crucible` — **public**, so no share with `testing@devpost.com` or `cloudhackathons@google.com` is needed |
| **Reproducible testing instructions in README?** | **Yes.** `README.md` "Spin it up": requirements, install, run the tests, the enforcement smoke run, the campaign loop — every command executed and its real output shown, verified 2026-08-21. Four more instruments in `MEASUREMENT.md` |
| **Hosted project URL** | *blank* — see the ruling above. Put the reasoning in Testing instructions instead |
| **Google SDK** | **Agent Development Kit (ADK)** only. `google-adk==2.1.0`, imported and load-bearing at `crucible/plugin/adk.py:78`. Do not also tick GenAI SDK: it is a transitive dependency of ADK, not something this project calls |
| **Google Cloud Service(s)** | **Cloud Run only**, from the five offered. **Do NOT tick Firestore** — it is provisioned and nothing in the repository holds a client for it, which the 08-30 audit established. Cloud SQL, GKE and Pub/Sub are not used at all. The services this project actually leans on (Vertex AI, Cloud Storage, IAM, Cloud Logging) are not on that list, so they go in the model and description fields instead |
| **Architecture diagram** | upload `tools/capture/out/submission-media/01-architecture-THUMBNAIL.png` — PNG, 0.37 MB against a 35 MB cap |
| **Startup Prize org / corporate email** | *blank*, both. Not opting in |
| **Google AI Models** | `gemini-3.7-flash` (Armorer) · `gemini-3.6-flash` (Red strategist) · `gemini-3.5-flash-lite` (Coroner and target agent) · `google/gemma-4-26b-a4b-it-maas` (capability cartographer, via Vertex Model Garden). **All Gemini pins are 3.5 or newer, and Gemma is the additional model the bonus asks for** |

### The two optional bonus fields — check before you answer

**Link to a piece of content (blog, podcast, video).** The rule has two
conditions: the content must be **public, not unlisted**, and it **must include
language saying you created it for the purposes of entering this hackathon**.

The demo video is public and is already the required video, but it does not
carry that sentence. **Do not claim this field unless a piece of content
actually says it.** An unmet condition on a bonus field is a worse trade than an
unclaimed bonus.

**Link to a social media post, with `#AllThingsAgentic Hackathon`.** Your
LinkedIn post is at
`https://www.linkedin.com/feed/update/urn:li:activity:7500205777584963584/`.
**Open it and confirm the hashtag is in it before pasting.** I cannot read
LinkedIn from here and will not assume a hashtag is present.


---

## Testing instructions - paste this

**THE FIELD CAPS AT 255 CHARACTERS.** Discovered 2026-08-31 at the form, after a full
block had been written for it. This is the version that fits, at exactly 255:

```
No credential needed. README's Open in Cloud Shell button runs it in your browser. Or clone, pip install -r requirements.txt, python scripts/w2-smoke.py, python -m crucible.conductor.campaign - read the banner. No hosted URL: Cloud Run has 0 IAM bindings.
```

**The Cloud Shell URL is deliberately not in it.** That URL is ~180 of the 255 and it is
already the first "Try it out" link, so spending three quarters of the budget to repeat
it would buy nothing. The README button at `README.md:29` is the same link, one click
further away, and the characters it frees pay for four runnable commands instead.

**The long version below is not dead.** It is what `README.md` "Spin it up" and the
Cloud Shell tutorial already say at length, kept here because it is the source the 255
was cut from - and because if any other field, an update, or a judge's question asks
what a reviewer can run, this is the answer that does not have to be rewritten.

**Written 2026-08-31** against the commands in `README.md` "Spin it up", each of which
is shown there with its real output so a judge can diff what they get against what was
published.

```
No credential is required, and there is no login to hand you. Every path below runs
with no API key, no cloud project and no environment variable.

FASTEST PATH - runs in your browser, about three minutes

Click "Open in Cloud Shell" on the repository's front page, or use this link:

https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https://github.com/emtcmca/crucible&cloudshell_git_branch=main&cloudshell_tutorial=docs/cloudshell-tutorial.md

It opens the repository in your own Cloud Shell with a guided tutorial pane. The
steps are chosen to show instruments FAILING, because a check that cannot fail is
not a check: the contract gate refusing a mutated artifact, the policy compiler
refusing a rule outside its three verbs, and the offline evidence reader refusing a
damaged bundle. Step 5b makes one live Vertex call on your own project if you want
one. Step 6 says plainly why the full attack loop is not offered to a third party.

LOCAL PATH - about five minutes, Python 3.11

  git clone https://github.com/emtcmca/crucible.git
  cd crucible
  python -m pip install -r requirements.txt

  python -m pytest tests/ -p no:cacheprovider
      The suite. tests/ deliberately keeps strawmen - wrong implementations
      retained on purpose - so every check can be shown to fail.

  python scripts/w2-smoke.py
      The enforcement path end to end, no model called. An attack lands against an
      empty policy and the refund executes; one hand-written rule stops it and the
      tool does not execute; a legitimate episode survives both.

  python -m crucible.conductor.campaign
      The loop, offline. READ THE BANNER - it declares which components were real
      and which were not exercised on this path, prints the six hash-locked fields
      with their frozen values, and halts on ARMORER_EXHAUSTED rather than emitting
      a canned patch that would make a degraded run look like a working one.

  python -m crucible.replay contracts/golden/C6-evidence_bundle.valid.json
      The offline evidence reader. It opens no socket and reads no credential,
      which is enforced by an AST lint plus a test that runs the viewer with the
      environment stripped and the socket module replaced by something that raises.

Four more instruments, each pointed at something and shown refusing, are in
MEASUREMENT.md.

WHY THERE IS NO HOSTED URL

The Cloud Run service was deployed and serving as of 2026-08-24, under its own
service account, with --no-allow-unauthenticated and zero IAM bindings, so a URL would return 403 to you.
The rules ask for login credentials when a submitted site is private. Minting a
credential for a harness whose entire subject is agents holding permissions they
should not have is the wrong trade, and the service drives a paid model behind a
budget alert that stops nothing. The demo video shows that service live instead -
the terminal beat is an unedited screen recording of gcloud against the real
project.

WHAT NOT TO EXPECT

The full red-team loop needs Vertex credentials and writes to this project's own
buckets and audit log, BECAUSE the promotion gates assert against them. It is not
runnable by a third party and is not presented as though it were. The README has a
section titled "what is not defensible today" that states every limit of the
measurement, including that a held-out attack family is still sealed and no
transfer result is claimed.

Everything stays up through 2026-10-01.
```

**Two things this field must not do.** It must not claim the full loop is runnable by a
judge, and it must not quote a test count - `README.md` marks that number verify-on-use
because it has gone stale three times. The block above states neither.
