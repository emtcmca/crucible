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

Cloud Run, Cloud Storage, Firestore, BigQuery, Cloud Build, Artifact Registry,
Cloud Trace, Cloud Logging, IAM, Vertex AI.

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
```
