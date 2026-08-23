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

THE MODEL ID ENDS `-maas`, AND THAT SUFFIX COST THIS PROJECT AN EVENING.

`docs/proof/vertex-model-reachability-2026-08-22.txt` is the record. Four
separate probes concluded managed Gemma was unavailable in this project. Every
one of them asked for a model id that does not exist:

    google/gemma-4-26b-a4b-it     404   <- missing the -maas suffix
    google/gemma-3-27b-it         404   <- a VERSION name, not a publisher id
    google/gemma-3-12b-it         404   <- same
    google/gemma-2-27b-it         404   <- same

    google/gemma-4-26b-a4b-it-maas  200

**A 404 says nothing about availability until the identifier is known good**,
and the failure was accepted three times because it agreed with what the memo
predicted. The tell was there and nobody read it: with the CORRECT id,
`us-central1` returns `400 FAILED_PRECONDITION` naming the fix in plain text -
*"is only available via global endpoint"* - where a wrong id returns a 404
naming nothing. Two different errors, trivially distinguishable.

Gemma 3 on Vertex remains a **self-deploy** model - Model Garden hands you a
GPU-backed endpoint you stand up and pay for, which is Option A wearing Option
B's name. That was never the question. `gemma-4-26b-a4b-it-maas` is published as
a fully managed serverless endpoint, needs no Model Garden enablement, no
licence acceptance and no GPU, and it answers.

LOCATION IS `global` AND THE HOST HAS NO REGION PREFIX.

Regional Vertex endpoints are `https://<location>-aiplatform.googleapis.com`.
The `global` endpoint is `https://aiplatform.googleapis.com` with no prefix at
all, and `global-aiplatform.googleapis.com` does not resolve. `_host()` below is
the one place that distinction lives.

TEMPERATURE, SEED, AND WHAT NEITHER GUARANTEES.

`temperature=0` and a fixed `seed` are sent, and the endpoint accepts both
(verified 2026-08-22, http 200 with and without `seed`). Neither makes a hosted
model deterministic - batching, kernel selection and server-side version drift
all move the output, and no provider promises otherwise. They are sent because
they narrow the variance and because the seed is the thing a third party needs
in order to attempt the same call. Do not describe the result as deterministic.

TOKEN ACCOUNTING TRAVELS WITH THE CALLABLE, NOT WITH THE RETURN VALUE.

`Cartographer` is built against a `complete(prompt) -> str` seam and every test
drives it with a stub, so widening that return type to carry usage would push a
model concern into a component that is deliberately ignorant of models. Instead
the callable `make_completer` returns exposes two attributes the caller may read
AFTER the call: `last_usage` (the raw `usage` block from the response) and
`calls` (a list of per-call usage dicts). The seam is unchanged; the accounting
is on the object that did the spending.

NOTHING HERE IS EXERCISED BY THE TEST SUITE. Every test in
`tests/test_cartographer_gemma.py` drives `Cartographer` with a stub. This module
is imported by nothing except a caller who has decided to spend money.
"""

import json
import shutil
import subprocess
import urllib.error
import urllib.request

# The one Gemma published as a managed serverless endpoint on Vertex, verified
# reachable from this project 2026-08-22 at http 200. THE `-maas` SUFFIX IS PART
# OF THE ID - see the module docstring on what dropping it cost. A different id
# may not be MaaS at all, in which case the call 404s rather than silently
# costing GPU-hours.
DEFAULT_MODEL_ID = "google/gemma-4-26b-a4b-it-maas"

# Not a region. `us-central1` returns 400 FAILED_PRECONDITION for this model
# with the message "only available via global endpoint".
DEFAULT_LOCATION = "global"

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


def _host(location: str) -> str:
    """The API host for a Vertex location.

    `global` is not a region and does not take the region prefix every real
    region takes. `global-aiplatform.googleapis.com` does not resolve, so
    getting this wrong reads as a network failure rather than as a bad URL.
    """
    if location == "global":
        return "https://aiplatform.googleapis.com"
    return "https://%s-aiplatform.googleapis.com" % location


def endpoint_url(project: str, location: str = DEFAULT_LOCATION) -> str:
    """The Vertex MaaS OpenAI-compatible chat/completions endpoint.

    The project is in the URL path, which is what makes this callable without
    setting an ADC quota project - the quota is attributed from the path.
    """
    return ("%s/v1/projects/%s/locations/%s/endpoints/openapi/chat/completions"
            % (_host(location), project, location))


def generate_content_url(project: str, location: str = DEFAULT_LOCATION,
                         model_id: str = DEFAULT_MODEL_ID) -> str:
    """The native `:generateContent` shape for the same model.

    Not used by `make_completer` - the OpenAPI shape is what the Cartographer
    calls - but both shapes were verified at 200 on 2026-08-22, and a reader
    checking the proof artifact wants the second URL spelled somewhere it can be
    diffed against the first rather than reconstructed from memory.
    """
    bare = model_id.split("/")[-1]
    return ("%s/v1/projects/%s/locations/%s/publishers/google/models/%s"
            ":generateContent" % (_host(location), project, location, bare))


def make_completer(*, project, location=DEFAULT_LOCATION, model_id=DEFAULT_MODEL_ID,
                   seed=DEFAULT_SEED, max_tokens=4096, timeout=180, token=None):
    """Return a `complete(prompt) -> str` callable for `Cartographer`.

    The returned callable is the ONLY thing that touches the network. It is
    built here and injected, so `Cartographer` stays offline-testable and this
    module stays untested-by-design rather than untestable.

    After a call, the callable carries:
        complete.last_usage - the response's raw `usage` block, or None
        complete.calls      - one usage dict per call made, in order

    Read them for cost reporting. They are attributes rather than return values
    so the seam `Cartographer` binds to stays `str`.
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

        # Recorded BEFORE the content is extracted. A response that spent tokens
        # and then came back in an unexpected shape still cost money, and a cost
        # report that omits the malformed call under-reports the spend.
        usage = body.get("usage") if isinstance(body, dict) else None
        complete.last_usage = usage
        # The raw text, kept so a caller can write it out even when the
        # Cartographer's validator rejects the answer and raises. The rejected
        # response is the evidence for the rejection.
        complete.last_raw = _content_or_none(body)
        complete.calls.append({
            "model": model_id,
            "url": url,
            "finish_reason": _finish_reason(body),
            "usage": usage,
        })

        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise VertexUnavailable(
                "unexpected response shape: %s" % json.dumps(body)[:2000]) from exc

    complete.last_usage = None
    complete.last_raw = None
    complete.calls = []
    complete.model_id = model_id
    complete.url = url
    return complete


def _content_or_none(body):
    """The assistant text, or None if the response is not that shape."""
    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None


def _finish_reason(body):
    """The finish reason, or None. A truncated answer is a cost fact worth
    recording next to the token count - `length` and `stop` cost the same and
    mean very different things about whether the answer is complete."""
    try:
        return body["choices"][0]["finish_reason"]
    except (KeyError, IndexError, TypeError):
        return None
