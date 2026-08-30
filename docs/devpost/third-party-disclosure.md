# Third-party and pre-existing code — the Devpost disclosure

**Written 2026-08-24 for the submission form's "disclose any pre-existing or
third-party code you used" field.** Every claim below is read off the repository
rather than recalled; the commands that produce each one are given so a judge can
re-derive them.

---

## The short answer

**CRUCIBLE was written entirely during the submission period.** First commit
`fc3a612`, **2026-08-20 11:10 EDT**, in a repository initialized that morning; 340
commits as of this file. No part of the harness — the tripwire, the policy DSL and
its validator, the Warden, the promotion gate, the round conductor, the evidence
bundle, the replay reader, the corpus — existed before that date or came from
anywhere else.

What follows is everything that did.

## 1. Runtime dependencies

Every one is a published package, unmodified, installed from PyPI. Read off
`requirements.txt`, which is pinned exactly:

| Package | Version | Licence | Why it is here |
|---|---|---|---|
| `google-adk` | **2.1.0** | Apache-2.0 | The Google agent framework the target runs on, and the plugin surface enforcement attaches to |
| `jsonschema` | 4.26.0 | MIT | Validates every contract and the evidence bundle |
| `referencing` | 0.37.0 | MIT | `$ref` resolution for the contract set, offline |
| `PyYAML` | 6.0.3 | MIT | Reads the frozen gate rule (`gate_rule.v1.yaml`) |
| `pytest` | 9.0.3 | MIT | The test suite |
| `google-cloud-storage` | **3.10.1** | Apache-2.0 | Reads the sealed holdout and the policies bucket (`crucible/transfer/gcs_reader.py`, `crucible/conductor/real_gate.py:718`) |

**The `google-cloud-storage` row was added 2026-08-30 and the table was wrong
without it.** This file claims each row is read off `requirements.txt` rather
than recalled, and the pin has been in that file since 2026-08-28 — it was added
after an adversarial review found that a clean virtualenv resolving all five
prior pins still had no `google.cloud`, so it is not transitive from
`google-adk` and every live GCS path would have failed at the import. A
disclosure that under-reports a dependency is a smaller sin than one that
over-reports a service, but it is the same defect: the document stopped being
re-derived from the artifact it cites.

**The pins are load-bearing, not hygiene.** `google-adk==2.1.0` is pinned because
three behaviours the enforcement design depends on are true of that version and
not of an unpinned resolve: all 13 `BasePlugin` hooks present with matching
signatures, the plugin manager's `before_tool_callback` firing **before** the
agent's own callbacks, and ADK issue #2809 fixed.

## 2. Third-party code committed into this repository

**One file.**

```
crucible/cartographer/foreign/adk_customer_service.json
```

A frozen descriptor of **Google's own ADK sample agent**, used as the *foreign*
target the Capability Cartographer is pointed at — a tool surface nobody on this
project designed, which is the entire point of that exercise.

| | |
|---|---|
| Source | `https://github.com/google/adk-samples` |
| Path | `python/agents/customer-service` |
| Commit | `629310b7b845398841c814456289a34fbc766acf` |
| Licence | Apache-2.0 |
| Content | 12 tool declarations — names, docstrings, argument schemas |
| Digest | `e9ae52b9ea5920a7e0fc46dc119a8252a96cdff5b01a7099dbde2a50aa34f5e1` |

It carries **no executable code** — it is a descriptor extracted from the sample's
tool declarations, pinned by commit and content-addressed so a third party can
verify it is what it claims to be. Nothing in the sample runs here.

## 3. Models, all served by Google

None is fine-tuned, distilled, or modified. All are called through Vertex AI.

| Role | Model |
|---|---|
| ARMORER | `gemini-3.7-flash` |
| RED_STRATEGIST | `gemini-3.6-flash` |
| CORONER, TARGET | `gemini-3.5-flash-lite` |
| CAPABILITY_CARTOGRAPHER | `google/gemma-4-26b-a4b-it-maas` |

**The Gemma line is the hackathon's "additional Google AI models" bonus** and it is
there for a stated engineering reason rather than to collect the point: an
open-weights model pinned by version and seed was chosen so a third party could
regenerate the classification artifact. *That rationale did not survive contact
with measurement* — 25 same-seed runs on 2026-08-24 produced two different
assignments, so the seed is accepted and not honoured at the serving layer. The
finding is published in `docs/proof/cartographer-stability-2026-08-24.json` rather
than quietly dropped.

## 4. Web assets

`docs/devpost/crucible-explainer.html` loads **Newsreader**, **IBM Plex Mono** and
**IBM Plex Sans** from Google Fonts (SIL Open Font License). No other external
asset, script, stylesheet or CDN is referenced by anything in this repository.

## 5. Google Cloud services used

**Corrected 2026-08-30.** This section previously read, in full:

> ~~Cloud Run, Cloud Storage, Firestore, BigQuery, Cloud Build, Artifact
> Registry, Cloud Trace, Cloud Logging, IAM, Vertex AI.~~

That was a flat list with no distinction between a service this project calls
and a service `data-spec.md` designs for, and three of the ten were on the wrong
side of that line. The list is now tiered, because the tier is the honest part.

**Exercised by code or by a gate in this repository:**

| Service | Where |
|---|---|
| **Vertex AI** | every model call, `global` endpoint |
| **Cloud Run** | the target agent is deployed and serving, `--no-allow-unauthenticated` |
| **Cloud Storage** | three buckets; `google-cloud-storage==3.10.1`, `crucible/transfer/gcs_reader.py`, `crucible/conductor/real_gate.py` |
| **Cloud IAM** | the blindness boundary itself — gates G7/G8 read live IAM policy |
| **Cloud Logging** | `infra/holdout_touch.py` reads `cloudaudit.googleapis.com%2Fdata_access` to prove no sealed object was read |
| **Cloud Build**, **Artifact Registry** | invoked by `gcloud run deploy --source`; the Cloud Build identity's IAM grant is itself a documented finding (`deploy/RUNBOOK.md`) |

**Provisioned or specified, and NOT exercised by any code here. Named so a judge
does not have to discover it:**

| Service | Actual status |
|---|---|
| **Firestore** | the database is provisioned. `data-spec.md` §2 names it as the production store, but the shipped ledger is local SQLite (`crucible/ledger/store.py`) and no module in this repository holds a Firestore client. |
| **Cloud Trace** | the span design in `data-spec.md` §6 is a specification. **As of 2026-08-30** there is no OpenTelemetry dependency in `requirements.txt` and no instrumentation in the tree. |

**Removed from the list entirely: BigQuery.** The dataset is not created and no
client code exists — there is no `google-cloud-bigquery` dependency, no query,
and no dataset. The project's own `docs/devpost/findings-and-learnings.md` has
said so since 2026-08-22: *"The BigQuery export described in `data-spec.md` is
specified and not yet wired."* This section listed it as used for six days after
that sentence was written, which is the ordinary way a document goes stale — by
standing still while the thing it describes moves.

**Scope this correction precisely, because the opposite error is also
available.** `grep -ri bigquery` over this repository is **not** empty. It
returns three things, none of them a use. One: the name inside gate **G7(b)**,
which asserts that the Armorer service account holds **no** project-level
`storage|bigquery` role (`crucible/conductor/real_gate.py:429`,
`infra/verify_iam.py:229,248,435-437,556`). Two: docstrings in
`infra/holdout_touch.py:140-173` and `crucible/red/__init__.py:9` that name the
sealed BigQuery dataset `data-spec.md` designs — and say in the same breath that
this half of the holdout **is not read**. Three: `bq` commands inside the
teardown script in `data-spec.md` §7.3, which has never been run and is now
under an explicit hold until 2026-10-01. A role name inside a deny-check is the
opposite of using the service. The accurate
statement is **"BigQuery is named in an IAM deny-check and is not otherwise
used,"** not "BigQuery does not appear in the repository" — the second is false
and any reader with grep would catch it. This project has twice this week
widened a narrow true correction into a false one; this is the guard against
doing it a third time.

## 6. What this project's own licence is

**Apache-2.0**, in `LICENSE`, public repository `emtcmca/crucible`.

---

## Re-derive any of this

```bash
git log --reverse --format="%cI %h %s" | head -1     # the start date
git rev-list --count HEAD                            # commit count
cat requirements.txt                                 # every pinned dependency
python -c "import json; d=json.load(open('crucible/cartographer/foreign/adk_customer_service.json')); print(d['repository'], d['commit_sha'])"
grep -rn "fonts.googleapis.com" docs/                # the only external host

# Section 5, both directions. The first two return NOTHING -- no BigQuery client,
# no Firestore client. The third returns only IAM deny-check strings and the
# unrun teardown script, which is the whole distinction that section draws.
grep -rn "google-cloud-bigquery\|opentelemetry" requirements.txt
grep -rn "from google.cloud import bigquery\|from google.cloud import firestore" --include=*.py .
grep -rin "bigquery" --include=*.py crucible/ infra/
```
