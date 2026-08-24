"""armorer.py - the ARMORER. One breach record in, one validated patch out.

MODEL: `gemini-3.7-flash`, `thinking_level` medium, escalate to high freely.
CONVENTIONS 3.1 LOCKS this and the lock is not a suggestion: if the model is
unavailable, REPORT - do not substitute. Substituting one silently would make
every emission number in this build a measurement of a different model than the
one named next to it.

THE SHAPE OF THIS COMPONENT
---------------------------
    project -> assemble -> call -> parse -> validate
                            ^                  |
                            |   ONE repair     |
                            +---- on failure --+
                                     |
                            second failure -> HALT_HUMAN(ARMORER_EXHAUSTED)

The repair carries THE VALIDATOR ERROR AND NOTHING ELSE (`policy.ebnf`, foot).
Not the fixture failures, not the benign pass rate, not which fixture broke. Those
are the ARMORER's blind spot by design, and the one place the design is most
likely to be violated is at 11pm when a round keeps getting rejected.

THE MODEL NEVER COMPUTES A rule_id
-----------------------------------
It writes `r_new1`; `Validator.validate_patch` canonicalizes the body, hashes it,
and writes the real id in. A patch in which the model emitted a hash-shaped id on
an add is REJECTED - not because the id would be wrong, which it certainly would
be, but because a model that produced a plausible one has demonstrated it is
guessing at a deterministic computation and the next guess lands somewhere nobody
can see. `crucible.canon.hashing.assert_model_did_not_forge_a_rule_id` is the
check and L3 already wired it into `Validator.check_rule_id`.

WHY THIS MATTERED ON DAY 1: had the spike asked the model for a SHA-256 it would
have read 0/20, concluded the DSL is unemittable, and triggered an architecture
change for a reason that has nothing to do with the DSL.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from ..dsl import ParseError, ValidationError, parse_policy
from . import prompt as prompt_mod
from .adapter import project

# CONVENTIONS 3.1, LOCKED. Do not substitute; report.
ARMORER_MODEL = "gemini-3.7-flash"
ARMORER_THINKING_LEVEL = "medium"          # escalate to `high` freely (~$1/run)

HALT_ARMORER_EXHAUSTED = "ARMORER_EXHAUSTED"

# The spike measured $0.2913 over 20 calls at medium thinking (DECISION.md).
ESTIMATED_USD_PER_CALL = 0.0146


@dataclass
class Attempt:
    """One model call and what became of it. Kept for the evidence bundle: an
    ARMORER that took two tries is a different fact from one that took one, and
    the repair rate is the number the day-1 band was set against."""
    index: int
    kind: str                       # "initial" | "repair"
    raw_text: str = ""
    parsed: bool = False
    validated: bool = False
    error_code: Optional[str] = None
    error_detail: str = ""
    usd: float = 0.0
    tokens: int = 0
    latency_ms: int = 0


@dataclass
class PatchResult:
    """The ARMORER's output. A VALUE, including when it failed.

    `halt` is set instead of an exception being raised for the same reason the
    governor returns rather than raises: ARMORER_EXHAUSTED is a result of the
    round. It belongs in the round outcome and in the evidence bundle, and a
    traceback reaches neither.
    """
    ok: bool
    patch_text: str = ""
    hashed_payload: Optional[dict] = None
    new_rule_ids: List[str] = field(default_factory=list)
    retracted_rule_ids: List[str] = field(default_factory=list)
    verbs_used: List[str] = field(default_factory=list)
    attempts: List[Attempt] = field(default_factory=list)
    halt: Optional[str] = None
    halt_detail: str = ""

    @property
    def repaired(self) -> bool:
        return len(self.attempts) > 1


class Armorer:
    """`call_model` is injected. Two reasons, and the second is the real one:

    1. Every test in this lane runs offline and deterministically.
    2. The model client is the only thing here that can talk to the network, so
       keeping it a constructor argument makes "did this component call a model"
       answerable by reading one line rather than by grepping a package. The
       TRIPWIRE and the WARDEN get the same property from an import lint; this
       component is ALLOWED a model, so the equivalent discipline is making the
       seam explicit.
    """

    def __init__(self, validator, manifest_a, derived_schema_b, call_model,
                 *, model=ARMORER_MODEL, thinking_level=ARMORER_THINKING_LEVEL,
                 governor=None, objective_set=None):
        self.validator = validator
        self.manifest_a = manifest_a
        self.derived_schema_b = derived_schema_b
        # THE OBJECTIVE SET IN FORCE, so `invariant_id` stops being a pointer
        # with nothing on the other end. Frozen at `objective_set_hash` for the
        # whole run, which is why it is a constructor argument rather than a
        # per-call one: an ARMORER that could be handed a different definition
        # of breach between rounds is an ARMORER patching a moving target.
        #
        # OPTIONAL, and the default is the OLD behaviour on purpose. Every
        # offline fixture and every existing test builds one without it, and a
        # required argument would have turned a two-file fix into a sweep. The
        # CONDUCTOR always supplies it.
        self.objective_set = objective_set
        self.call_model = call_model
        self.model = model
        self.thinking_level = thinking_level
        self.governor = governor

    # ----------------------------------------------------------------
    def _fire(self, system_text, user_text, attempts, kind):
        started = time.monotonic()
        attempt = Attempt(index=len(attempts) + 1, kind=kind)
        attempts.append(attempt)
        response = self.call_model(
            system=system_text, user=user_text, model=self.model,
            thinking_level=self.thinking_level)
        attempt.latency_ms = int((time.monotonic() - started) * 1000)
        if isinstance(response, dict):
            attempt.raw_text = response.get("text", "") or ""
            attempt.usd = float(response.get("usd", 0.0))
            attempt.tokens = int(response.get("tokens", 0))
        else:
            attempt.raw_text = str(response)
        if self.governor is not None:
            self.governor.record("ARMORER", usd=attempt.usd,
                                 tokens=attempt.tokens)
        return attempt

    def _try(self, attempt, current_policy):
        """Parse then validate. Returns the hashed payload, or records the first
        refusal on the attempt and returns None.

        ONE error, never a list. `validate_patch` raises on the first refusal on
        purpose: the repair gets the error as its sole feedback, and twelve
        simultaneous complaints is not feedback.
        """
        try:
            parsed = parse_policy(strip_fences(attempt.raw_text))
        except ParseError as exc:
            attempt.error_code, attempt.error_detail = exc.code, str(exc)
            return None
        attempt.parsed = True
        try:
            payload = self.validator.validate_patch(parsed, current_policy)
        except ValidationError as exc:
            attempt.error_code, attempt.error_detail = exc.code, str(exc)
            return None
        attempt.validated = True
        return parsed, payload

    # ----------------------------------------------------------------
    def propose(self, breach_record, current_policy, round_index,
                rejection_feedback=None) -> PatchResult:
        projected = project(breach_record,
                            objective_set=self.objective_set)
        policy_text = render_current(current_policy)
        user_text = prompt_mod.build_user_message(
            projected_record=projected, manifest_a=self.manifest_a,
            derived_schema_b=self.derived_schema_b, policy_text=policy_text,
            round_index=round_index)
        if rejection_feedback is not None:
            # COUNTS AND CLASSES, and the builder rejects anything else. This is
            # the ACROSS-ROUNDS channel; the WITHIN-CALL repair channel below
            # carries the validator error and nothing more. The two must never
            # merge - see build_repair_message.
            user_text += prompt_mod.build_rejection_feedback(
                rejection_feedback.benign_failures, rejection_feedback.classes)
        system_text = prompt_mod.SYSTEM_INSTRUCTION

        attempts: List[Attempt] = []
        if self.governor is not None:
            verdict = self.governor.authorize("ARMORER", ESTIMATED_USD_PER_CALL)
            if not verdict.allowed:
                return PatchResult(ok=False, attempts=attempts,
                                   halt=verdict.code, halt_detail=verdict.detail)

        attempt = self._fire(system_text, user_text, attempts, "initial")
        outcome = self._try(attempt, current_policy)

        if outcome is None:
            # ONE repair, with the validator error as its sole feedback.
            if self.governor is not None:
                verdict = self.governor.authorize("ARMORER",
                                                  ESTIMATED_USD_PER_CALL)
                if not verdict.allowed:
                    return PatchResult(ok=False, attempts=attempts,
                                       halt=verdict.code,
                                       halt_detail=verdict.detail)
            repair_text = user_text + "\n\n" + prompt_mod.build_repair_message(
                attempt.error_code, attempt.error_detail)
            attempt = self._fire(system_text, repair_text, attempts, "repair")
            outcome = self._try(attempt, current_policy)

        if outcome is None:
            return PatchResult(
                ok=False, attempts=attempts, halt=HALT_ARMORER_EXHAUSTED,
                halt_detail="two consecutive invalid patches; last error %s: %s"
                            % (attempt.error_code, attempt.error_detail))

        parsed, payload = outcome
        existing = _rule_ids(current_policy)
        return PatchResult(
            ok=True,
            patch_text=strip_fences(attempt.raw_text),
            hashed_payload=payload,
            new_rule_ids=[r["rule_id"] for r in payload["rules"]
                          if r["rule_id"] not in existing],
            retracted_rule_ids=list(parsed.retractions),
            verbs_used=[r.action.verb for r in parsed.rules],
            attempts=attempts)


# --------------------------------------------------------------------------

def _rule_ids(policy):
    payload = (policy or {}).get("hashed_payload", policy or {})
    return {r["rule_id"] for r in payload.get("rules", [])}


def render_current(policy) -> str:
    from .render import render_policy
    if not policy:
        return "# policy@v0\n# no rules yet."
    return render_policy(policy)


_FENCE_LANGS = ("dsl", "text", "policy", "crucible", "ebnf", "")


def strip_fences(text: str) -> str:
    """Remove a markdown code fence if the model wrapped the patch in one.

    THIS IS A HARNESS REPAIR AND IT IS DECLARED AS ONE. The output contract says
    no fences; a fenced patch is a FRAMING failure, not a GRAMMAR failure, and
    the day-1 decision rule distinguishes them because they have opposite
    remedies - framing is fixed with worked examples, grammar is fixed by
    replacing free-form emission with constrained JSON. Absorbing a fence
    silently would move instances from the second bucket into the first and
    change which remedy the numbers argue for. Every strip is counted.
    """
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    first = lines[0][3:].strip().lower()
    if first not in _FENCE_LANGS:
        return stripped
    body = lines[1:]
    if body and body[-1].strip().startswith("```"):
        body = body[:-1]
    return "\n".join(body).strip()


def was_fenced(text: str) -> bool:
    return text.strip().startswith("```")
