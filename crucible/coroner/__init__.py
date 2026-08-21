"""crucible.coroner - the CORONER. Owned by L5 LOOP.

Contains a model (`gemini-3.5-flash-lite`, `thinking_level: minimal`,
CONVENTIONS 3.1). One call per breach, structured extraction.

THE CORONER DIAGNOSES. IT IS STRUCTURALLY BARRED FROM PROPOSING THE FIX.
C5 has no `fix`, `recommendation` or `mitigation` field and
`additionalProperties: false`, so one cannot be added without breaking the
contract hash. Detection and remediation are separate roles: if the CORONER can
write the fix, the ARMORER degrades into a transcriber and the producer/verifier
split collapses into one role wearing two names.

BUT THE SCHEMA IS NOT THE ENFORCEMENT, AND SAYING SO IS THE POINT.
The spec's own `generalization_hypothesis` example handed the ARMORER rule `r019`
in English, passed a modal-verb lint, and - being a NAMED TYPED FIELD - sailed
through the "adapter reads named fields only" defence. The enforcement is
`crucible/armorer/adapter.py`: an enumerated projection with no free-text field
at all. This package's contribution is to put the model's ENTIRE output inside
`human_only`, which that projection cannot address.

HONESTY BOUND: the CORONER RETAINS FIRESTORE WRITE. Its inability to propose
fixes is schema plus lint plus the projection - convention and code, NOT IAM -
and it must be described that way (CONVENTIONS section 7).
"""

from .coroner import (
    CORONER_MODEL,
    CORONER_THINKING_LEVEL,
    Coroner,
    CoronerError,
    build_record,
)
from .lint import LintFinding, prescriptive_lint

__all__ = ["Coroner", "CoronerError", "build_record", "CORONER_MODEL",
           "CORONER_THINKING_LEVEL", "prescriptive_lint", "LintFinding"]
