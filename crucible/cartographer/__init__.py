"""cartographer - the CAPABILITY_CARTOGRAPHER's deterministic front door.

`architecture-spec.md:138` specifies `CAPABILITY_CARTOGRAPHER` to "propose a
capability class set for each tool the deterministic pre-pass could not
resolve." `docs/decisions-pending/gemma-scope.md` section 6 checked, on
2026-08-21, that the pre-pass did not exist anywhere in `crucible/` or
`target/`. `prepass.py` in this package is task one: pure code, no model, that
resolves what a tool signature can establish and marks the rest
`UNCLASSIFIED` for whatever comes after it (a model, or a human).
"""
