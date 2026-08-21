# Day-1 billing questions — evidence, not prose

`execution-spec.md` §Day 1, deliverable 2 requires three questions answered **in
writing** in this file. It was never written. This is it.

**Rule for this file:** every claim carries the command that produced it and that
command's actual output. A tool's success message is not evidence; the
postcondition is. Where the postcondition could not be read, the verdict is
**UNVERIFIED** and the section names exactly what Eric must open.

- Compiled: 2026-08-21
- Active project: `crucible-hack-2026` (project number `752793770087`)
- Billing account: `01857F-ED360B-D82A0D`
- gcloud account: `eric@erictetzlaff.com`
- Every command below is read-only. Nothing in this file created, modified, or
  deleted a cloud resource.

```
$ gcloud config list
[accessibility]
screen_reader = False
[core]
account = eric@erictetzlaff.com
disable_usage_reporting = True
project = crucible-hack-2026

Your active configuration is: [default]
```

```
$ gcloud billing projects describe crucible-hack-2026
billingAccountName: billingAccounts/01857F-ED360B-D82A0D
billingEnabled: true
name: projects/crucible-hack-2026/billingInfo
projectId: crucible-hack-2026
--- exit 0 ---
```

```
$ gcloud billing accounts list
ACCOUNT_ID            NAME                OPEN  MASTER_ACCOUNT_ID
01857F-ED360B-D82A0D  My Billing Account  True
--- exit 0 ---
```

---

## Q1 — Does the $150 hackathon credit stack with an unused $300 trial credit?

### What was tried

`gcloud` has no read surface for billing credits, promotions, or trial state.
The two account-scoped describe/list commands are the whole surface, and neither
returns a credit field:

```
$ gcloud billing accounts describe 01857F-ED360B-D82A0D --format=json
{
  "currencyCode": "USD",
  "displayName": "My Billing Account",
  "masterBillingAccount": "",
  "name": "billingAccounts/01857F-ED360B-D82A0D",
  "open": true,
  "parent": "organizations/74580447849"
}
--- exit 0 ---
```

No `credits`, no `promotions`, no `trial`, no `freeTrialStatus` key. The
`billingEnabled: true` above establishes that a billing account is attached; it
says nothing about which credits fund it or whether they combine.

There is also no billing export to query. A BigQuery billing export would carry
credit line items, and there is none:

```
$ gcloud alpha bq datasets list --project=crucible-hack-2026
Listed 0 items.
--- exit 0 ---
```

### What the repo already says

`docs/build-spec.md:580` carries this as an open item, owned by Eric, still
open:

```
| Does the $150 hackathon credit stack with the $300 trial? Console → Billing → Credits | Eric | UNVERIFIED — **changes the budget 3×** |
```

Nothing anywhere else in `docs/`, `infra/`, or `scripts/` resolves it. The
build-spec's own annotation — *changes the budget 3×* — is why guessing here is
worse than saying nothing.

### What Eric must do

1. Open **console.cloud.google.com/billing/01857F-ED360B-D82A0D/credits** (Billing
   → select `My Billing Account` → **Credits** in the left nav).
2. Read the table. Each row shows a credit's name, amount, **amount remaining**,
   and expiry.
3. Record here: how many credit rows exist, each name and remaining balance, and
   the sum. If both a $150 hackathon credit and a $300 trial credit appear as
   separate rows with separate remaining balances, they stacked. If only one row
   exists, redeeming consumed the other.
4. Also check whether the account left free trial: if the trial credit is still
   listed and the account shows as upgraded, the trial balance may be forfeited
   rather than converted — that is visible on the same page and is a different
   outcome from "consumed."

**Verdict: UNVERIFIED — Eric must confirm.** No gcloud command exposes credit
balances; `gcloud billing accounts describe` returns no credit field and there is
no billing export to query. Settle it at Console → Billing → `01857F-ED360B-D82A0D`
→ Credits, and write the row-by-row balances back into this section.

---

## Q2 — Is the project on paid tier?

The risk the spec names is specific: **free-tier Gemini API traffic is read by
human reviewers and used to improve products, and CRUCIBLE's entire corpus is
attack payloads.** That risk attaches to the free tier of the *Gemini API*
(`generativelanguage.googleapis.com`, the AI Studio key surface). It is worth
splitting the question in two, because the evidence lands differently on each
half.

### Q2a — Is any traffic going through the Gemini API free-tier surface?

The Gemini API service is **not enabled on this project at all**:

```
$ gcloud services list --enabled --project=crucible-hack-2026 --filter="name:generativelanguage.googleapis.com"
Listed 0 items.
```

A disabled service cannot serve traffic. The model surface that *is* enabled is
Vertex:

```
$ gcloud services list --enabled --project=crucible-hack-2026 | grep aiplatform
aiplatform.googleapis.com            Agent Platform API
```

And the code path is hardcoded to Vertex, not to an API key —
`crucible/armorer/client.py:74-79`:

```python
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    if not project:
        raise ModelUnavailable(
            "GOOGLE_CLOUD_PROJECT is unset. This lane does not guess a project.")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "").strip() or "global"
    return genai.Client(vertexai=True, project=project, location=location)
```

`vertexai=True` with a project and location is the Vertex path. There is no
API-key branch in `crucible/`.

The one live model run on record went that way. `docs/lanes/L5-log.md:52`:

```
Model **`gemini-3.7-flash`**, `thinking_level: medium`, Vertex, `global`
endpoint, project `crucible-hack-2026`.
```

**On Q2a the evidence is affirmative and consistent across four independent
places** — service enablement, code, config, and a recorded run. No CRUCIBLE
traffic has gone through the Gemini API free-tier surface, because that service
has never been enabled on this project. See Q3 for the two places that could
still break this.

### Q2b — Is the project actually being billed?

This is the half the spec wrote a postcondition for, and the postcondition is not
readable from the CLI. `execution-spec.md:202`:

> **Tier check by postcondition:** run one trivial generation, then confirm a
> **non-zero charge line** in Billing → Reports within the hour. A paid tier
> bills. **The absence of a charge is your evidence that you are on the tier you
> didn't want.**

Billing → Reports is a console surface. The CLI equivalent would be a BigQuery
billing export, and there is none (`gcloud alpha bq datasets list` → `Listed 0
items.`, above). So the charge line cannot be asserted from here.

What *is* established: billing is attached and enabled on the project
(`billingEnabled: true`), the billing account is open (`OPEN True`), and 21 live
Vertex calls were fired against this project on 2026-08-20 per
`docs/lanes/L5-log.md`. Whether those produced a non-zero charge line is exactly
the thing that was not read.

### What Eric must do

1. Open **console.cloud.google.com/billing/01857F-ED360B-D82A0D/reports**.
2. Filter to project `crucible-hack-2026`, service **Vertex AI**, date range
   covering **2026-08-20** (the L5 live-model run — 21 calls on
   `gemini-3.7-flash`).
3. Confirm a **non-zero** cost line. Paste the figure into this section with the
   date range it covers.
4. If the line is zero, stop and treat it as the spec does: the absence of a
   charge is evidence of the tier we did not want, and it must be resolved before
   any further model traffic.

**Verdict: UNVERIFIED on the spec's own postcondition — Eric must read Billing →
Reports.** The narrower and more important half is answered by evidence:
`generativelanguage.googleapis.com` is not enabled on this project, so no CRUCIBLE
traffic has touched the Gemini API free tier. What remains unread is the non-zero
charge line that proves the Vertex traffic is billing.

---

## Q3 — Gemini API or Vertex AI?

### The decision

**Vertex AI.** Written down here, once, so it stops being re-derived.

### Evidence it is already the de-facto choice

| Evidence | Source |
|---|---|
| `aiplatform.googleapis.com` enabled | `gcloud services list --enabled` (below) |
| `generativelanguage.googleapis.com` **not** enabled | `gcloud services list --enabled --filter=...` → `Listed 0 items.` |
| Client constructed with `vertexai=True` | `crucible/armorer/client.py:79` |
| `global` endpoint, a Vertex-only concept, ruled in CONVENTIONS | `docs/CONVENTIONS.md` §3.3 — *"Use the **`global`** endpoint. Non-global carries a flat 10% premium."* |
| Live run recorded on Vertex | `docs/lanes/L5-log.md:52` |
| Every service account's model permission is `roles/aiplatform.user` | `docs/data-spec.md:1006-1014`, `infra/bind-iam.sh:95` |

The IAM map is the strongest of these. `data-spec.md` §4.1 grants
`aiplatform.user` to the components that may call a model and deliberately
withholds it from the tripwire, warden, and gate. **That boundary is expressed in
Vertex IAM and has no equivalent on an API key.** Switching to the Gemini API
would not just change a client constructor; it would delete the mechanism that
makes *"the judge is code"* structural rather than a claim.

### Two live drift surfaces — both real, both in committed files

1. **`spike/armorer/run_spike.py:243-272` and `spike/armorer/README.md:87-93`
   support both paths.** The spike reads `GOOGLE_API_KEY` / `GEMINI_API_KEY` and
   falls back to them when `GOOGLE_GENAI_USE_VERTEXAI` is unset. `spike/` is
   gitignored and was Day-1 throwaway, so this is low risk — but if anyone reruns
   the spike without setting `GOOGLE_GENAI_USE_VERTEXAI=1`, that run goes over an
   API key. The Armorer prompt carries attack material.

2. **`execution-spec.md:278` instructs the D3 third-party target to run on an AI
   Studio key.** Verbatim:

   > Clone `google/adk-samples`, record the exact commit SHA, run
   > `customer-service` on an **AI Studio key**, **reproduce bypass #1 by hand**

   That is the Gemini API surface, and it is exactly the traffic Q2 says must not
   ride a free tier — the bypass reproduction is an attack payload by
   construction. Either that step moves to Vertex, or the key used must be
   confirmed paid-tier before the step runs. **This is a decision for Eric, not a
   defect I should silently resolve**, because `execution-spec.md` is a frozen
   spec and the D3 step may have been written that way for setup-cost reasons.

**Verdict: ANSWERED — Vertex AI.** Enabled service, `vertexai=True` in
`crucible/armorer/client.py:79`, the `global`-endpoint ruling in CONVENTIONS §3.3,
and the `aiplatform.user` IAM boundary in `data-spec.md` §4.1 all point one way,
and `generativelanguage.googleapis.com` is not enabled. Two committed files still
describe an API-key path (the gitignored spike, and `execution-spec.md:278`'s D3
step) — see Open gaps.

---

## Spend cap — the $160 requirement

### What the spec requires

`CONVENTIONS.md:308` is the ruling and outranks everything downstream:

```
| **Spend cap** | **$160** | A cap, not an alert. Eric holds additional credits beyond this if a run needs them, but the cap stays at $160 so an overrun is a **deliberate decision rather than a discovery**. Supersedes the $60 in `execution-spec.md` D1 and the $120 in `data-spec.md` §8.5 |
```

The documented conflict is real and resolved: **$60** in `execution-spec.md` D1,
**$120** in `data-spec.md` §8.5, and **$160 is the ruling** (also restated at
`architecture-spec.md:1217`, `data-spec.md:1485`, `execution-spec.md:13`,
`build-spec.md:582`).

`execution-spec.md:195` sets the verification: *"`gcloud billing budgets list`
returns JSON with the **cap/enforcement field populated**, not just a threshold
rule. Paste it in."*

### What the command actually returned

```
$ gcloud billing budgets list --billing-account=01857F-ED360B-D82A0D --format=json
API [billingbudgets.googleapis.com] not enabled on project [crucible-hack-2026].
 Would you like to enable and retry (this will take a few minutes)? (y/N)?
ERROR: (gcloud.billing.budgets.list) [eric@erictetzlaff.com] does not have permission
to access billingAccounts instance [01857F-ED360B-D82A0D] (or it may not exist):
Cloud Billing Budget API has not been used in project crucible-hack-2026 before or it
is disabled. Enable it by visiting
https://console.developers.google.com/apis/api/billingbudgets.googleapis.com/overview?project=crucible-hack-2026
then retry.
- '@type': type.googleapis.com/google.rpc.ErrorInfo
  domain: googleapis.com
  metadata:
    activationUrl: https://console.developers.google.com/apis/api/billingbudgets.googleapis.com/overview?project=crucible-hack-2026
    consumer: projects/crucible-hack-2026
    containerInfo: crucible-hack-2026
    service: billingbudgets.googleapis.com
    serviceTitle: Cloud Billing Budget API
  reason: SERVICE_DISABLED
[]
--- exit 1 ---
```

Confirmed independently:

```
$ gcloud services list --enabled --project=crucible-hack-2026 --filter="name:billingbudgets.googleapis.com"
Listed 0 items.
```

The prompt was answered **N** and the API was **not** enabled — enabling a service
is a mutation and outside this task's read-only scope.

### Read this failure precisely

`SERVICE_DISABLED` on `billingbudgets.googleapis.com` means **the budget could not
be read**, not that no budget exists. Budgets are billing-account-scoped
resources; the disabled API is a per-project quota surface for the *call*. A
budget created through the console can exist while this command still fails.
Saying "there is no budget" from this output would be a confident wrong answer.

**But nothing anywhere establishes that a cap exists either.** The only assertion
in the repo is `CONVENTIONS.md:1944`:

> `crucible-hack-2026` live with Firestore and three buckets; **spend cap set.**

That sentence cites nothing. No pasted JSON, no budget ID, no screenshot, no
`docs/proof/` artifact. `execution-spec.md:195` demanded the JSON be pasted in and
it never was — which is precisely why this file was missing. And it does not
distinguish a **cap** from an **alert**, which is the whole question:
`data-spec.md:1485` — *"**Alerts do not stop spending; caps do.**"*

`execution-spec.md:184` also names the fallback if a true cap is unavailable for
these services: *"wire budget → Pub/Sub → Cloud Function calling
`projects.updateBillingInfo` with an empty billing account."* No such Pub/Sub
topic, Cloud Function, or wiring exists anywhere in `infra/` or `scripts/`.

### What Eric must do

1. Open **console.cloud.google.com/billing/01857F-ED360B-D82A0D/budgets**.
2. Confirm a budget exists, and record its **name, amount, and scope** (it must
   cover Vertex AI, Gemini API, and Cloud Run per `build-spec.md:582`).
3. Confirm the amount is **$160**, not $60 and not $120.
4. **Confirm whether it caps or only alerts.** Open the budget and look for
   whether any enforcement action is configured beyond threshold notification. A
   budget with only threshold rules stops nothing.
5. If it only alerts, decide between the console cap control (where offered for
   these services) and the `execution-spec.md:184` Pub/Sub → Cloud Function →
   `updateBillingInfo` fallback, and build it.
6. Then, so this is machine-checkable next time: enable
   `billingbudgets.googleapis.com` on `crucible-hack-2026`, re-run
   `gcloud billing budgets list --billing-account=01857F-ED360B-D82A0D
   --format=json`, and paste the JSON into this section as
   `execution-spec.md:195` required.

**Verdict: UNVERIFIED — Eric must confirm, and this is an open Day-1 gap.** The
required command cannot run because `billingbudgets.googleapis.com` is disabled on
the project, so neither a cap nor an alert can be asserted from here.
`CONVENTIONS.md:1944` claims *"spend cap set"* with no supporting evidence of any
kind, and does not distinguish a cap from an alert. **A plain budget caps
nothing.** The ruling amount is **$160**; the $60 in `execution-spec.md` D1 and
the $120 in `data-spec.md` §8.5 are both superseded and dead.

---

## Services — the twelve the Day-1 list names

`execution-spec.md:185` names twelve services. Actual output:

```
$ gcloud services list --enabled --project=crucible-hack-2026
NAME                                 TITLE
aiplatform.googleapis.com            Agent Platform API
analyticshub.googleapis.com          Analytics Hub API
artifactregistry.googleapis.com      Artifact Registry API
bigquery.googleapis.com              BigQuery API
bigqueryconnection.googleapis.com    BigQuery Connection API
bigquerydatapolicy.googleapis.com    BigQuery Data Policy API
bigquerydatatransfer.googleapis.com  BigQuery Data Transfer API
bigquerymigration.googleapis.com     BigQuery Migration API
bigqueryreservation.googleapis.com   BigQuery Reservation API
bigquerystorage.googleapis.com       BigQuery Storage API
cloudapis.googleapis.com             Google Cloud APIs
cloudbuild.googleapis.com            Cloud Build API
cloudresourcemanager.googleapis.com  Cloud Resource Manager API
cloudtrace.googleapis.com            Cloud Trace API
containerregistry.googleapis.com     Container Registry API
dataform.googleapis.com              Dataform API
dataplex.googleapis.com              Cloud Dataplex API
datastore.googleapis.com             Cloud Datastore API
firebaserules.googleapis.com         Firebase Rules API
firestore.googleapis.com             Cloud Firestore API
iam.googleapis.com                   Identity and Access Management (IAM) API
iamcredentials.googleapis.com        IAM Service Account Credentials API
logging.googleapis.com               Cloud Logging API
modelarmor.googleapis.com            Model Armor API
monitoring.googleapis.com            Cloud Monitoring API
pubsub.googleapis.com                Cloud Pub/Sub API
run.googleapis.com                   Cloud Run Admin API
secretmanager.googleapis.com         Secret Manager API
servicemanagement.googleapis.com     Service Management API
serviceusage.googleapis.com          Service Usage API
sql-component.googleapis.com         Cloud SQL
storage-api.googleapis.com           Google Cloud Storage JSON API
storage-component.googleapis.com     Cloud Storage
storage.googleapis.com               Cloud Storage API
telemetry.googleapis.com             Telemetry API
--- exit 0 ---
```

Checked one by one against the Day-1 list:

| # | Service | Enabled |
|---|---|---|
| 1 | `run.googleapis.com` | yes |
| 2 | `aiplatform.googleapis.com` | yes |
| 3 | `cloudbuild.googleapis.com` | yes |
| 4 | `cloudtrace.googleapis.com` | yes |
| 5 | `modelarmor.googleapis.com` | yes |
| 6 | `storage.googleapis.com` | yes |
| 7 | `firestore.googleapis.com` | yes |
| 8 | `bigquery.googleapis.com` | yes |
| 9 | `artifactregistry.googleapis.com` | yes |
| 10 | `secretmanager.googleapis.com` | yes |
| 11 | `iamcredentials.googleapis.com` | yes |
| 12 | `cloudresourcemanager.googleapis.com` | yes |

**All twelve enabled. Zero missing.** This confirms the `DONE` annotation at
`execution-spec.md:186`.

Two notes on services *not* in the list:

- `billingbudgets.googleapis.com` is **not** enabled, which is what blocks the
  spend-cap verification above. It is not one of the twelve, so this is not a
  deviation from the Day-1 list — it is a gap in the Day-1 list.
- `generativelanguage.googleapis.com` is **not** enabled, and per Q3 that is
  correct and should stay that way.

Also correcting a stale line: `execution-spec.md:196` verification reads *"shows
all **six**."* The deliverable at `:185` names **twelve** and was corrected
2026-08-20; the verification line beneath it was not updated with it. Twelve is
the number.

**Verdict: ANSWERED — all twelve services enabled, none missing.**

---

## ADK version

```
$ python -c "import google.adk; print(google.adk.__version__)"
2.1.0
--- exit 0 ---
```

```
$ pip show google-adk
Name: google-adk
Version: 2.1.0
Summary: Agent Development Kit
Location: C:\Users\tetzl\AppData\Roaming\Python\Python311\site-packages
--- exit 0 ---
```

The installed version matches the required pin, `google-adk==2.1.0`
(`execution-spec.md:187`).

**The pin itself was never written.** `requirements.txt` in full:

```
$ cat requirements.txt
jsonschema==4.26.0
referencing==0.37.0
PyYAML==6.0.3
```

`pyproject.toml` in full:

```
$ cat pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-q"
```

```
$ grep -rn "google-adk" . --include=*.txt --include=*.toml --include=*.cfg
(no hits outside docs/execution-spec.md:187)
```

So `google-adk` is pinned nowhere in the dependency set. It is installed at 2.1.0
on this machine and nothing records that requirement. `execution-spec.md:187`
ends *"**Do not upgrade mid-build.**"* — an unpinned dependency cannot enforce
that, and a clean checkout resolves to whatever is newest.

**Verdict: version ANSWERED (`2.1.0`, matches the required pin) — but the pin is
UNVERIFIED because it does not exist. `google-adk==2.1.0` must be added to
`requirements.txt`.**

---

## Open Day-1 gaps

Everything below came back unverified, missing, or contradictory. Ordered by what
blocks the most.

| # | Gap | Evidence | Owner / next action |
|---|---|---|---|
| 1 | **No verified spend cap.** `gcloud billing budgets list` cannot run — `billingbudgets.googleapis.com` is `SERVICE_DISABLED` on the project. Cannot tell cap from alert, cannot tell $160 from $60 from $120, cannot tell whether a budget exists at all | command output in §Spend cap; `gcloud services list --enabled --filter=billingbudgets` → `Listed 0 items.` | **Eric.** Console → Billing → `01857F-ED360B-D82A0D` → Budgets. Confirm existence, **$160**, scope (Vertex AI + Gemini API + Cloud Run), and cap-vs-alert. Then enable `billingbudgets.googleapis.com` and paste the JSON here |
| 2 | **`CONVENTIONS.md:1944` asserts "spend cap set" with zero supporting evidence** and does not distinguish cap from alert. `execution-spec.md:195` required the JSON pasted in; it never was | `docs/CONVENTIONS.md:1944` | **Coordinator.** Once #1 resolves, either back the claim with the JSON or correct the line. An unevidenced "done" in the spine is the rot this repo already has rulings about |
| 3 | **Credit stacking unknown.** No gcloud surface for credits; no billing export exists. `build-spec.md:580` flags it as *changes the budget 3×* | `gcloud billing accounts describe` returns no credit field; `gcloud alpha bq datasets list` → `Listed 0 items.` | **Eric.** Console → Billing → Credits. Record each row's name and remaining balance |
| 4 | **Paid-tier postcondition never read.** `execution-spec.md:202` requires a non-zero charge line in Billing → Reports; it is a console surface with no CLI equivalent here | no billing export dataset | **Eric.** Billing → Reports, filter project `crucible-hack-2026`, service Vertex AI, date **2026-08-20** (the 21-call L5 run). Confirm non-zero and paste the figure |
| 5 | **`google-adk` is pinned nowhere.** Installed 2.1.0, required 2.1.0, recorded in no dependency file. `execution-spec.md:187` says *"do not upgrade mid-build"* and nothing enforces it | `requirements.txt` has three lines, none `google-adk`; `pyproject.toml` has only pytest config | **Coordinator.** Add `google-adk==2.1.0` to `requirements.txt` |
| 6 | **`execution-spec.md:278` routes the D3 third-party target through an AI Studio key** — the Gemini API surface, running a deliberate bypass reproduction, which is attack material by construction | `docs/execution-spec.md:278` | **Eric's call.** Either move that step to Vertex, or confirm the key is paid-tier before running it. Do not resolve silently — the D3 step may be written that way for setup cost |
| 7 | **`spike/armorer/run_spike.py` falls back to `GOOGLE_API_KEY` / `GEMINI_API_KEY`** when `GOOGLE_GENAI_USE_VERTEXAI` is unset. Low risk (spike is gitignored and finished), but a rerun without that env var sends Armorer prompts over an API key | `spike/armorer/run_spike.py:243-272`, `spike/armorer/README.md:87-93` | **Coordinator.** If the spike is ever rerun, set `GOOGLE_GENAI_USE_VERTEXAI=1` first. Otherwise leave it — the file is not shipped |
| 8 | **`execution-spec.md:196` verification says "shows all six"** where the deliverable at `:185` names twelve. The deliverable was corrected 2026-08-20; the verification line under it was not | `docs/execution-spec.md:196` vs `:185` | **Coordinator.** Downstream-doc defect. Twelve is the number and all twelve are confirmed enabled |

### Not a gap — recorded so it is not re-derived

- All twelve Day-1 services are enabled. Confirmed by name, one at a time.
- The platform decision is **Vertex AI**, and four independent artifacts already
  agree (service enablement, client code, CONVENTIONS §3.3's `global` endpoint
  ruling, and the `aiplatform.user` IAM map). Only the two items above deviate.
- No CRUCIBLE traffic has gone through the Gemini API free tier, because
  `generativelanguage.googleapis.com` has never been enabled on this project.
  That bounds the training-data exposure the spec was worried about — it does not
  prove the Vertex traffic is billing, which is gap #4.

---

## RESOLVED 2026-08-21 — the budget was found. It is an ALERT, not a CAP.

Gaps #1 and #2 above are superseded by this section. `billingbudgets.googleapis.com`
was enabled on the project (that is why the earlier read failed - the API is enabled
per *project*, while the budget itself lives on the *billing account*), and the
budget read back on the first try.

```
$ gcloud billing budgets list --billing-account=01857F-ED360B-D82A0D --format=json
[
  {
    "amount": { "specifiedAmount": { "currencyCode": "USD", "units": "160" } },
    "budgetFilter": {
      "calendarPeriod": "MONTH",
      "creditTypesTreatment": "INCLUDE_ALL_CREDITS",
      "projects": [ "projects/752793770087" ]
    },
    "displayName": "crucible-hack-2026",
    "name": "billingAccounts/01857F-ED360B-D82A0D/budgets/7c074cc2-1f48-4ce5-a9e4-3552bd563c38",
    "notificationsRule": { "enableProjectLevelRecipients": true },
    "thresholdRules": [
      { "spendBasis": "CURRENT_SPEND", "thresholdPercent": 0.5 },
      { "spendBasis": "CURRENT_SPEND", "thresholdPercent": 0.9 },
      { "spendBasis": "CURRENT_SPEND", "thresholdPercent": 1.0 }
    ]
  }
]

$ gcloud projects describe crucible-hack-2026 --format="value(projectNumber,projectId)"
752793770087    crucible-hack-2026
```

**Three of four things are right, and they are the three that were in doubt.**
The amount is **$160**, matching `CONVENTIONS.md:308`. The scope is
`projects/752793770087`, and that number **is** `crucible-hack-2026`, verified
above rather than assumed. `INCLUDE_ALL_CREDITS` means the $160 counts credit
spend, so an unexpectedly generous credit grant cannot silently widen the ceiling.

**The fourth is the one the spec cared about, and it is wrong.**
`notificationsRule` contains only `enableProjectLevelRecipients: true`. There is no
`pubsubTopic`, and there is no enforcement anywhere in the object. The three
threshold rules **send email at 50%, 90% and 100%**. Nothing stops at 100%.

`execution-spec.md:184` predicted this in as many words - *"Plain budgets cap
nothing"* - and named the workaround: budget -> Pub/Sub -> Cloud Function calling
`projects.updateBillingInfo` with an empty billing account. **That kill switch does
not exist.** `grep -rln "updateBillingInfo|pubsub" infra/ scripts/` returns nothing.

**Read the risk honestly, in both directions.**

This is not "no budget" and it is not a live emergency. Spend to date is small, the
runs are bounded by the round cap and the attacks-per-round cap, and Eric gets mail
at $80. What it is: **the Day-1 objective was "make it impossible for this project
to quietly cost money", and what exists makes it impossible for money to be spent
*quietly*. It does not make it impossible for money to be spent.** Those are
different guarantees and the spec asked for the second one.

**Not built unilaterally, deliberately.** A Cloud Function holding permission to
detach billing from the project is a loaded weapon pointed at the demo: if it
misfires mid-run, the project dies and the submission dies with it. That is a
decision the owner makes awake, not one a coordinator makes at 2am on his behalf.

**Owner action.** Choose one:
1. **Accept the alert.** Defensible. Say so in writing here so the spec line is
   settled rather than open, and correct `execution-spec.md:184` and
   `CONVENTIONS.md:1944` to say *alert at $160*, not *cap*.
2. **Build the kill switch**, and test it by firing the Pub/Sub message by hand
   against a throwaway project first. A kill switch nobody has watched fire is a
   check that cannot fail.

**Either way `CONVENTIONS.md:1944` is currently wrong.** It says *"spend cap set"*.
A budget is set. A cap is not.
