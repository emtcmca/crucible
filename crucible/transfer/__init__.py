"""The F4 transfer phase.

Separate package from `crucible.conductor` on purpose: the conductor's corpus
loader is structurally blind to the sealed family and stays that way. Nothing in
this package is imported by a training run.
"""
