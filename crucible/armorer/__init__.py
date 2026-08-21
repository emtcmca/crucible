"""crucible.armorer - the ARMORER. Owned by L5 LOOP.

Contains a model (`gemini-3.7-flash`, CONVENTIONS 3.1). It reads a projection of
one BreachRecord and emits a patch in the C4 DSL. It never computes a rule id
(CONVENTIONS 2.6) and it never sees prose.

THE BLINDNESS IS THE SHAPE OF THE INPUT, NOT AN INSTRUCTION IN THE PROMPT.
A prompt that ASKS a model to ignore something it can see is not blindness; it is
a request, and a judge reading the transcript can see the material sitting right
there. `adapter.py` builds a new dict from an enumerated allowlist, so there is no
field a rationale could arrive on.
"""
