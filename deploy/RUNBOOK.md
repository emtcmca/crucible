# Cloud Run deploy — the Day-2 item, prepared and not fired

**Status: ready to run. Not run.** Everything below was verified except the
deploy itself, which creates a publicly reachable Cloud Run service and spends
money, and is therefore Eric's to fire rather than the coordinator's.

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

So the shim sits outside the freeze boundary at `deploy/refund_agent/agent.py`,
and it calls the same `build_agent()` the harness calls. The deployed agent and
the measured agent are the same object from the same code path. If that ever
stops being true, the Cloud Run demo stops being evidence about the thing we
measured.

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


```bash
cd /c/dev/crucible
source scripts/gcp-env.sh

adk deploy cloud_run \
  --project="$CRUCIBLE_PROJECT" \
  --region="$CRUCIBLE_REGION" \
  --service_name=crucible \
  --with_ui \
  --trace_to_cloud \
  deploy/refund_agent
```

`--trace_to_cloud` is not optional decoration: the Day-2 verification step wants
an `execute_tool` span carrying `gen_ai.agent.name` visible in Trace Explorer,
and that is also the cleanest on-camera proof that the backend is really running
on Google Cloud rather than locally.

## Verification — assert the postcondition, never the exit code

A successful-looking deploy log is not evidence. Four things, in order:

1. `gcloud run services describe crucible --region="$CRUCIBLE_REGION" --format='value(status.url)'` returns a URL.
2. `curl -s "$SERVICE_URL/list-apps"` returns the app name. A 200 with an empty
   body is not a pass.
3. An `execute_tool` span with `gen_ai.agent.name` is visible in **Trace
   Explorer**. Screenshot it into `docs/proof/`.
4. The **Cloud Run console** page, screenshotted into `docs/proof/`.

Both screenshots go in the video. That is the pass/fail requirement, satisfied.

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
