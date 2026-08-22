"""infra - provisioning scripts, and the IAM predicates G7 and G8 are made of.

This file exists so `infra.verify_iam`'s predicates can be IMPORTED rather than
copied. `verify_iam.py` was written as a CLI, and every G7/G8 predicate in the
project lives in it as a pure function over a policy dict, each already driven
to red by its `--selftest`. The alternative to importing them was restating them
inside `crucible/conductor/real_gate.py`, which would create a second source of
truth for the one boundary whose entire claim is that it has exactly one.

Nothing else belongs here. The shell scripts stay shell scripts.
"""
