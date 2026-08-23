"""vertex.py - the real model behind the Cartographer's seam. Option B.

Plain English first. `docs/decisions-pending/gemma-scope.md` section 5 puts the
hosting choice at a fork and recommends **Option B, Vertex Model Garden managed
Gemma**, over Option A, a self-deployed Gemma on a Cloud Run L4. This module is
Option B and nothing else. It builds no container, deploys no endpoint, and
creates nothing in the project.

WHAT OPTION B ACTUALLY BUYS, STATED AS THE MEMO REQUIRES.

The memo's own table says it: *"Partial: pinned model name and seed, not the
container."* Concretely, and this is the sentence to reuse rather than
paraphrase:

    A third party can re-issue the same prompt against the same published model
    id with the same seed and temperature. They cannot pin the weights, the
    serving container, or the decoding stack, because Google operates all three
    and may change any of them without changing the model id.

So the reproducibility claim available here is *"same model id, same seed, same
prompt"*, not *"byte-identical regeneration"*. The reason that is acceptable for
this component and was NOT acceptable for the corpus is `gemma-scope.md` section
5: the Cartographer's output is ratified by a human before it enters a manifest,
so **the person is the check**. A corpus that is hash-locked has no such person.

WHY GEMMA 4 26B AND NOT THE GEMMA 3 THE MEMO PROBABLY PICTURED.

Verified against Google's own documentation 2026-08-22: on Vertex, Gemma 3 is a
**self-deploy** model - Model Garden gives you a GPU-backed endpoint you stand up
and pay for, which is Option A wearing Option B's name. The only Gemma published
as a fully managed serverless MaaS endpoint is `gemma-4-26b-a4b-it`. If the
managed listing is not live in this project, Option B is unavailable and the
honest move is to say so rather than quietly fall back to a GPU deploy that
carries the standing `min-instances=0` risk `ADR-0009` names.

TEMPERATURE, SEED, AND WHAT NEITHER GUARANTEES.

`temperature=0` and a fixed `seed` are sent. Neither makes a hosted model
deterministic - batching, kernel selection and server-side version drift all
move the output, and no provider promises otherwise. They are sent because they
narrow the variance and because the seed is the thing a third party needs in
order to attempt the same call. Do not describe the result as deterministic.

NOTHING HERE IS EXERCISED BY THE TEST SUITE. Every test in
`tests/test_cartographer_gemma.py` drives `Cartographer` with a stub. This module
is imported by nothing except a caller who has decided to spend money.
"""

import json
import shutil
import subprocess
import urllib.error
import urllib.request

# The one Gemma published as a managed serverless endpoint on Vertex, per
# Google's MaaS model list. Not a default anyone should change casually - a
# different id may not be MaaS at all, in which case the call 404s rather than
# silently costing GPU-hours.
DEFAULT_MODEL_ID = "google/gemma-4-26b-a4b-it"
DEFAULT_LOCATION = "us-central1"
DEFAULT_SEED = 20260822


class VertexUnavailable(RuntimeError):
    """The managed endpoint could not be reached, or is not enabled here.

    Raised rather than retried or downgraded. `gemma-scope.md` section 5 makes
    Option A a deliberate decision with a cost attached; a client that quietly
    reaches for a GPU because a managed call failed makes that decision by
    accident.
    """


def _gcloud_path() -> str:
    """Resolve the gcloud executable.

    On Windows the thing on PATH is `gcloud.cmd`; the extensionless `gcloud`
    beside it is a bash script that `subprocess` cannot execute, and the failure
    is a bare `WinError 2` that reads as "gcloud is not installed" when it is.
    `shutil.which` with the .cmd/.ps1 candidates spelled out avoids diagnosing
    the wrong problem.
    """
    for candidate in ("gcloud.cmd", "gcloud"):
        found = shutil.which(candidate)
        if found:
            return found
    raise VertexUnavailable("gcloud is not on PATH")


def access_token() -> str:
    """Bearer token from the already-authenticated gcloud, read-only.

    `gcloud auth print-access-token` mints nothing and changes nothing in the
    project. It is the read-only way to authenticate a REST call from a machine
    where a human has already logged in.
    """
    try:
        out = subprocess.run(
            [_gcloud_path(), "auth", "print-access-token"],
            capture_output=True, text=True, timeout=60, check=True, shell=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise VertexUnavailable("could not obtain an access token: %s" % exc) from exc
    token = (out.stdout or "").strip()
    if not token:
        raise VertexUnavailable("gcloud returned an empty access token")
    return token


def endpoint_url(project: str, location: str = DEFAULT_LOCATION) -> str:
    """The Vertex MaaS OpenAI-compatible chat/completions endpoint.

    The project is in the URL path, which is what makes this callable without
    setting an ADC quota project - the quota is attributed from the path.
    """
    return ("https://%s-aiplatform.googleapis.com/v1/projects/%s/locations/%s"
            "/endpoints/openapi/chat/completions" % (location, project, location))


def make_completer(*, project, location=DEFAULT_LOCATION, model_id=DEFAULT_MODEL_ID,
                   seed=DEFAULT_SEED, max_tokens=4096, timeout=180, token=None):
    """Return a `complete(prompt) -> str` callable for `Cartographer`.

    The returned callable is the ONLY thing that touches the network. It is
    built here and injected, so `Cartographer` stays offline-testable and this
    module stays untested-by-design rather than untestable.
    """
    url = endpoint_url(project, location)

    def complete(prompt: str) -> str:
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "seed": seed,
            "max_tokens": max_tokens,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": "Bearer %s" % (token or access_token()),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:2000]
            raise VertexUnavailable(
                "HTTP %s from %s: %s" % (exc.code, url, detail)) from exc
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise VertexUnavailable("%s: %s" % (type(exc).__name__, exc)) from exc

        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise VertexUnavailable(
                "unexpected response shape: %s" % json.dumps(body)[:2000]) from exc

    return complete
