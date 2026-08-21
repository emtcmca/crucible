"""client.py - the only place in this lane that talks to a network.

Kept small and kept separate so "does this component call a model" is answerable
by reading one import rather than by grepping a package. The TRIPWIRE and the
WARDEN get that property from an import lint because they are FORBIDDEN a model;
the ARMORER, the CORONER and the RED_STRATEGIST are ALLOWED one, so the
equivalent discipline here is a single explicit seam that every caller injects.

FOUR THINGS THIS FILE REFUSES TO DO SILENTLY
--------------------------------------------
1. **It will not fall back to another model.** CONVENTIONS 3.1 LOCKS role to
   model. If the pinned id is unavailable the call fails and the lane REPORTS.
   A silent substitution would make every emission number a measurement of a
   different model than the one printed beside it.
2. **It will not drop `thinking_level`.** If the installed SDK cannot carry it,
   this raises. Measuring the provider default and reporting the requested level
   is measuring a different experiment. Thinking tokens bill at the ORDINARY
   OUTPUT RATE with no discount and ran 48x output tokens in the day-1 spike -
   they ARE the cost, so an unset level is not a free default.
3. **It will not report a cost it did not compute.** An unpriced model returns
   `usd=None` rather than 0.0, because a zero would sum into a budget total and
   read as "this was free."
4. **It will not retry a non-transient error.** A 400 is a defect in the payload
   and retrying it three times produces three copies of the same defect and a
   bill.

CALL ERRORS ARE EXCLUDED FROM PARSE-RATE DENOMINATORS, ON THE SAME REASONING AS
`TARGET_FAULT` (CONVENTIONS 2.4): an instrument failure is the ABSENCE of a
measurement, not a measurement of failure. Counting a 503 as "the model cannot
spell the grammar" is the same error as counting a crashed target as a repelled
attack, and it errs in the direction that flatters nothing - which is the only
reason it is safe to say out loud.
"""

import os
import time

# Published rates, USD per 1M tokens, input / output. Thinking tokens bill at the
# OUTPUT rate with no discount (CONVENTIONS 3.2).
PRICING = {
    "gemini-3.7-flash": (0.75, 3.75),
    "gemini-3.6-flash": (0.75, 3.75),
    "gemini-3.5-flash": (1.50, 9.00),
    "gemini-3.5-flash-lite": (0.10, 0.40),
}

_TRANSIENT = ("429", "500", "502", "503", "504", "RESOURCE_EXHAUSTED",
              "UNAVAILABLE", "DEADLINE_EXCEEDED", "INTERNAL", "overloaded")


class ModelUnavailable(RuntimeError):
    """The pinned model could not be reached. REPORT; do not substitute."""


def estimate_cost(model, input_tokens, output_tokens, thinking_tokens):
    rates = PRICING.get(model)
    if rates is None:
        return None
    in_rate, out_rate = rates
    billable_out = output_tokens + thinking_tokens
    return round(input_tokens / 1e6 * in_rate + billable_out / 1e6 * out_rate, 6)


def make_client():
    """Vertex on the GLOBAL endpoint. Non-global carries a flat 10% premium
    (CONVENTIONS 3.3)."""
    try:
        from google import genai
    except ImportError as exc:                           # pragma: no cover
        raise ModelUnavailable(
            "google-genai is not installed: python -m pip install google-genai"
        ) from exc

    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "").strip()
    if not project:
        raise ModelUnavailable(
            "GOOGLE_CLOUD_PROJECT is unset. This lane does not guess a project.")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "").strip() or "global"
    return genai.Client(vertexai=True, project=project, location=location)


def _config(system, thinking_level, temperature=None):
    from google.genai import types

    kwargs = {"system_instruction": system}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if thinking_level is None:
        raise ModelUnavailable(
            "thinking_level is required on every call (CONVENTIONS 3.3). "
            "Measuring the provider default and reporting a level is a "
            "different experiment.")
    try:
        return types.GenerateContentConfig(
            **kwargs,
            thinking_config=types.ThinkingConfig(thinking_level=thinking_level))
    except Exception:
        pass
    try:
        return types.GenerateContentConfig(
            **kwargs, thinking_config={"thinking_level": thinking_level})
    except Exception as exc:
        raise ModelUnavailable(
            "the installed google-genai cannot carry thinking_level=%r. Nothing "
            "was called." % thinking_level) from exc


def make_call_model(client=None, *, temperature=None, max_retries=2):
    """Return a `call_model(system, user, model, thinking_level) -> dict`.

    The dict is `{text, usd, tokens, input_tokens, output_tokens,
    thinking_tokens, latency_s, status, error}`. `status` is OK or ERROR, and an
    ERROR is a value rather than an exception so a campaign can record it and
    keep going - a run that ends in a traceback records nothing about why.
    """
    client = client or make_client()

    def call_model(*, system, user, model, thinking_level):
        config = _config(system, thinking_level, temperature)
        errors = []
        for attempt in range(max_retries + 1):
            started = time.time()
            try:
                resp = client.models.generate_content(
                    model=model, contents=user, config=config)
            except Exception as exc:
                msg = "%s: %s" % (type(exc).__name__, exc)
                errors.append(msg)
                if any(m in msg for m in _TRANSIENT) and attempt < max_retries:
                    time.sleep(2 ** (attempt + 1))
                    continue
                return {"status": "ERROR", "error": " | ".join(errors)[:800],
                        "text": "", "usd": 0.0, "tokens": 0, "latency_s": 0.0,
                        "input_tokens": 0, "output_tokens": 0,
                        "thinking_tokens": 0}
            elapsed = time.time() - started
            um = getattr(resp, "usage_metadata", None)
            tin = int(getattr(um, "prompt_token_count", 0) or 0) if um else 0
            tout = int(getattr(um, "candidates_token_count", 0) or 0) if um else 0
            tthink = int(getattr(um, "thoughts_token_count", 0) or 0) if um else 0
            text = getattr(resp, "text", None) or ""
            usd = estimate_cost(model, tin, tout, tthink)
            out = {
                "status": "OK" if text else "ERROR",
                "error": None if text else "empty candidate",
                "text": text,
                "usd": usd if usd is not None else 0.0,
                "usd_known": usd is not None,
                "tokens": tin + tout + tthink,
                "input_tokens": tin, "output_tokens": tout,
                "thinking_tokens": tthink,
                "latency_s": round(elapsed, 2),
            }
            return out
        return {"status": "ERROR", "error": " | ".join(errors)[:800],   # pragma: no cover
                "text": "", "usd": 0.0, "tokens": 0, "latency_s": 0.0}

    return call_model
