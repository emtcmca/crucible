# Cloud Run deploy

**Status: RUN, and serving. 2026-08-21.** Fired on Eric's instruction. Proof:
`docs/proof/cloud-run-deploy-2026-08-21.txt`.

```
service   crucible          revision crucible-00003-t2q, 100% traffic
url       https://crucible-vgp5owkxyq-uc.a.run.app
runs as   crucible-target@crucible-hack-2026.iam.gserviceaccount.com
auth      --no-allow-unauthenticated (allUsers bindings: 0)
```

**It took three attempts, and each failure was a real finding rather than a
fumble.** They are written up below because the next person to run this - a judge
reproducing the build, or Eric on Day 10 - will hit all three. Each one produced a
DEPLOY THAT LOOKED HEALTHY at the layer above it, which is the shape this project
exists to distrust: the image built, the revision was created, and the log was
clean, while the thing being deployed did not work.

**Deployed authenticated, which the first draft of this file did not specify.**
The service drives a paid model behind a $160 *alert* that stops nothing (see
Cost), so a world-reachable ADK web UI is an open invitation to spend against it.
If the Day-10 recording needs the UI open in a browser, one
`gcloud run services add-iam-policy-binding ... --member=allUsers
--role=roles/run.invoker` reverses it. Locking down first is the reversible
direction.

## Why it matters more than "a Day 2 item"

`docs/contest/CONTEST.md` §2 makes **"Must demonstrate the backend is running on
Google Cloud"** a Stage One pass/fail requirement on the video. It is not a
quality point. And `execution-spec.md` put the first deploy on **Day 2**
deliberately, to find out eight days early whether ADK's invocation paths break
the enforcement demo. Every day this slips re-arms the risk the schedule moved it
to defuse.

## What was blocking it, and is now fixed

`adk deploy cloud_run` requires a package whose `agent` module exposes a
module-level **`root_agent`**. `target/refund_agent/agent.py` has no such name —
it has `build_agent()`, a function.

Adding `root_agent` there would have been wrong twice over. It constructs an
`LlmAgent` at import time, and three things import that module without wanting an
agent: the D3 freeze, the manifest builder, and the test suite. More importantly
`agent.py` is inside `RUNTIME_MODULES`, so **after the D3 freeze on Sat 08-22 it
cannot be edited without voiding the run** — deployment scaffolding must not live
inside the thing being frozen.

So the shim sits outside the freeze boundary, and it calls the same
`build_agent()` the harness calls. The deployed agent and the measured agent are
the same object from the same code path. If that ever stops being true, the Cloud
Run demo stops being evidence about the thing we measured.

**The shim alone was not enough, and that is defect 1 of 3.**

### Defect 1 - the container does not contain `target/`

`adk deploy cloud_run` does exactly one thing with the source:

```
cli_deploy.py:702   shutil.copytree(agent_folder, <temp>/agents/<basename>)
cli_deploy.py:96    COPY "agents/<name>/" "/app/agents/<name>/"
```

**It copies the agent folder and nothing else.** The shim's
`from target.refund_agent.agent import build_agent` resolves on this machine and
raises `ModuleNotFoundError: No module named 'target'` in the container. The image
would still build and the revision would still be created; `/list-apps` would come
back empty. Postcondition 2 exists to catch exactly that, and it should not have
to.

`deploy/build-stage.py` assembles the real package: it vendors
`target/refund_agent/` into `deploy/.stage/refund_agent/_target/`, **re-reads every
staged byte off disk and compares SHA-256 against the source**, and refuses on any
mismatch. The copy is derived and verified rather than authored, so `target/` stays
the single source of truth. The stage is gitignored and rebuilt every deploy.

### Defect 2 - the tools were unbound

`target/refund_agent/tools.py:48` holds `_LEDGER = None` until `bind_backends()` is
called, and `_ledger()` then raises `BackendsNotBoundError` - deliberately loud, so
an unbound tool cannot produce an episode in which nothing happened and nothing
failed. Nothing bound it. Every tool call in the deployed agent would have raised.

The generated shim now binds `seed_demo_ledger(SimulatedSystemOfRecord())` - the
same seeded world the three demo transcripts use, with `as_of` defaulting to the
frozen `DEMO_AS_OF` rather than the wall clock.

### Defect 3 - `--trace_to_cloud` ships without its dependency

The generated Dockerfile runs `pip install google-adk==2.1.0` and nothing more, and
installs agent dependencies **only** if the agent folder carries a
`requirements.txt` (`cli_deploy.py:703-708`). The Cloud Trace exporter is not a
dependency of base `google-adk`, so the flag is accepted, the build succeeds, the
image pushes, and the revision dies on first import:

```
File "google/adk/cli/fast_api.py", line 563, in get_fast_api_app
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
ModuleNotFoundError: No module named 'opentelemetry.exporter'
```

`build-stage.py` now emits a pinned `requirements.txt`. **Cost of discovering this:
one full container build.**

### The IAM failure, which was the most valuable one

The first attempt died before the build:

```
403: 752793770087-compute@developer.gserviceaccount.com does not have
     storage.objects.get access to .../run-sources-.../objects/....zip
```

Cloud Build's default builder identity is the compute default service account,
which normally carries `roles/editor`. It does not here, **on purpose** - see the
G8 hazard note in `scripts/gcp-env.sh`: any principal holding a project-level BASIC
role silently inherits READ on the sealed bucket through the legacy
`projectEditor:` binding.

**The documented one-line fix for this 403 is `roles/cloudbuild.builds.builder`,
and it would have breached the seal.** Read out of the role itself:

```
storage.objects.get     storage.objects.list
storage.objects.create  storage.objects.delete   storage.objects.update
```

all at **project scope** - full read/write/delete on `crucible-sealed-x7`,
`crucible-policies-x7` and `crucible-evidence-x7`. G7 is the gate that exists to
catch that, and here the standard remedy was the thing it catches.

Granted instead, narrowly:

| Principal | Grant | Scope |
|---|---|---|
| compute default SA | `roles/storage.objectViewer` | **the `run-sources-*` bucket only** |
| compute default SA | `roles/logging.logWriter` | project - build logs, no storage |
| compute default SA | `roles/artifactregistry.writer` | project - push the image, no storage |
| `crucible-target` | `roles/cloudtrace.agent` | project - it held only `aiplatform.user`, so it could not write the span postcondition 3 asks for |

Asserted after: compute SA holds exactly those two project roles, and **zero**
bindings on all three crucible buckets.

The run identity is pinned to `crucible-target` rather than left as the compute
default. Otherwise the deployed agent - the thing under attack - would inherit the
builder's `artifactregistry.writer` and source-bucket read.

### The finding the Day-2 schedule was built to surface

With the container finally starting, the first episode returned a 500:

```
404 NOT_FOUND. Publisher model `projects/crucible-hack-2026/locations/us-central1/
publishers/google/models/gemini-3.5-flash-lite` was not found or your project
does not have access to it.
```

ADK's Dockerfile template bakes `ENV GOOGLE_CLOUD_LOCATION={gcp_region}` (line 85)
into the image. But `target/refund_agent/agent.py` pins the **global** endpoint -
non-global carries a flat 10% premium - and `target_descriptor()` hashes
`"endpoint": "global"` into the D3 freeze.

**So the deployed agent was resolving its model through a different endpoint than
the measured agent.** Left unfixed, the Cloud Run demo would have been a different
agent than the one the numbers describe. That is precisely the failure
`build-stage.py` was written to prevent, arriving through a channel the shim could
not see, because ADK set it in the image rather than in the code.

Fixed on the service: `--update-env-vars=GOOGLE_CLOUD_LOCATION=global`. It is in
the deploy command below so a fresh deploy never regresses to regional.

**This is what putting the first deploy on Day 2 bought.** Found on 08-21, with
nine days of slack. Found while recording on Day 10, it is the demo.

**Verified 2026-08-21:**

```
root_agent constructed: LlmAgent | name: refund_agent
                      | model: gemini-3.5-flash-lite | tools: 8
```

## The deploy

Names come from `scripts/gcp-env.sh`. **Source it; do not retype them** — G7 and
G8 grep for these literal strings, and a typo produces an unevaluable gate rather
than a loud failure.

> **Proved on the first draft of this file.** I wrote `$CRUCIBLE_PROJECT_ID`
> from memory. The variable is `CRUCIBLE_PROJECT`; `CRUCIBLE_PROJECT_ID` does
> not exist, and an undefined shell variable expands to an EMPTY STRING rather
> than erroring, so `--project=""` would have failed with a message about the
> project rather than about the typo. Source the file. Do not type the names.


**Two commands, and the first is not optional.** `build-stage.py` is what makes the
package deployable at all; skipping it deploys the last stage on disk, or nothing.

```bash
cd /c/dev/crucible
source scripts/gcp-env.sh

python deploy/build-stage.py          # verifies every staged byte against target/

adk deploy cloud_run \
  --project="$CRUCIBLE_PROJECT" \
  --region="$CRUCIBLE_REGION" \
  --service_name=crucible \
  --with_ui \
  --trace_to_cloud \
  deploy/.stage/refund_agent \
  -- --no-allow-unauthenticated \
     --service-account="crucible-target@${CRUCIBLE_PROJECT}.iam.gserviceaccount.com" \
     --update-env-vars=GOOGLE_CLOUD_LOCATION=global
```

Everything after the bare `--` is passed through to `gcloud run deploy`. All three
of those flags are load-bearing and each is explained above: authenticated because
the service spends money, a named run identity so the agent under attack does not
carry the builder's authority, and the global endpoint so the deployed agent
resolves the same model as the measured one.

`--trace_to_cloud` is not optional decoration: the Day-2 verification step wants
an `execute_tool` span carrying `gen_ai.agent.name` visible in Trace Explorer,
and that is also the cleanest on-camera proof that the backend is really running
on Google Cloud rather than locally.

## Verification — assert the postcondition, never the exit code

A successful-looking deploy log is not evidence. Four things, in order:

1. **PASS.** `gcloud run services describe crucible --region="$CRUCIBLE_REGION" --format='value(status.url)'`
   returns `https://crucible-vgp5owkxyq-uc.a.run.app`.
2. **PASS.** `/list-apps` returns `["refund_agent"]`, HTTP 200. A 200 with an empty
   body is not a pass. Authenticated now, so it needs a header:
   ```bash
   curl -s -H "Authorization: Bearer $(gcloud auth print-identity-token)" "$SERVICE_URL/list-apps"
   ```
   **Went further than the postcondition asked:** one full episode ran against the
   deployed service - the agent called `lookup_order("ORD-4471")`, got the seeded
   record back, and answered from it. Transcript in the proof file. That is a
   stronger result than `/list-apps`, which only proves the app loaded.
3. **NOT VERIFIED.** The Cloud Trace **v1** list API returned zero traces over a
   45-minute window, with no trace-export error in the live revision's logs. The v1
   `projects.traces.list` API is legacy and does not reliably surface spans written
   through the OpenTelemetry path, which is what `--trace_to_cloud` uses - so the
   negative result came from an instrument that may not be able to see the thing
   being asked about. **UNVERIFIED, not FAILED**, and the difference matters.
   Settle it in the console, which is postcondition 3's literal wording anyway:
   `https://console.cloud.google.com/traces/explorer?project=crucible-hack-2026`
4. **OWED.** The Cloud Run console page, screenshotted into `docs/proof/`:
   `https://console.cloud.google.com/run/detail/us-central1/crucible/metrics?project=crucible-hack-2026`

Both screenshots go in the video. That is the pass/fail requirement, and **3 and 4
are what remain of it.**

## The second thing this deploy is for: ADK #4704

Register a trivial blocking plugin (`before_tool_callback` returning a dict) and
confirm it fires through **both** `/run` and whatever path `--with_ui` uses.

The local half is already answered — `tests/test_plugin_enforcement.py` and
`tests/test_compiler_attach.py` pass, so enforcement works on the non-live path,
and `ADR-0012` already records the decision to use non-live `run_async` only.
What is **not** answered is the streaming/live path, and that can only be
answered against a running service.

**If the plugin does not fire in streaming mode, the demo must avoid the ADK web
UI on camera.** Better to learn that today than while recording on Day 10. Write
the answer into `ADR-0012` either way, with the trace pasted in.

## Cost

Small, and bounded: Cloud Run scales to zero, and the budget on the billing
account is $160/month scoped to this project. **Note it is an alert, not a cap** —
see `docs/ops/billing.md`. Nothing stops at $160; email arrives at $80, $144 and
$160.

## Teardown

`data-spec.md` §7.3 covers teardown. Delete the service after the hackathon:

```bash
gcloud run services delete crucible --region="$CRUCIBLE_REGION"
```
