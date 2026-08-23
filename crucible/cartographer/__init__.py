"""cartographer - capability classification for an agent, ours or somebody else's.

`architecture-spec.md:138` specifies `CAPABILITY_CARTOGRAPHER` to "propose a
capability class set for each tool the deterministic pre-pass could not
resolve." `docs/decisions-pending/gemma-scope.md` section 6 checked, on
2026-08-21, that the pre-pass did not exist anywhere in `crucible/` or
`target/`. `prepass.py` in this package is task one: pure code, no model, that
resolves what a tool signature can establish and marks the rest
`UNCLASSIFIED` for whatever comes after it (a model, or a human).

The rest of the package is that "after", pointed at an agent we did not write
(`gemma-scope.md` section 2 - our own eight tools are already hand-classified,
so the Cartographer aimed at them has nothing to do):

    extract.py                 read a foreign agent's tool module, with provenance
    freeze_foreign_target.py   regenerate the committed fixture
    foreign/*.json             frozen tool surfaces, digest-checked on load
    gemma.py                   the Cartographer: residue -> prompt -> validated
                               proposals, model behind a stubbable seam
    ratify.py                  the human gate. The ONLY route to a manifest entry
    vertex.py                  Option B hosting, and only Option B
    run.py                     --print-prompt (offline, free) / --live (spends)

TWO PROPERTIES HOLD ACROSS ALL OF IT. The model sees only what the deterministic
pass could not answer, enforced by `gemma.split_residue` rather than by a
sentence in a prompt. And nothing it proposes reaches a manifest without a named
human - `architecture-spec.md:138`, "it cannot approve its own classification".

Measured 2026-08-22 and pinned in `tests/test_cartographer_gemma.py`: on the
foreign target the pre-pass resolves **0 of 12** tools, against 6 of 8 on our
own. The five rules key on our agent's argument vocabulary and none of it
appears in somebody else's agent. Making them portable is open work; adding
rules until that number improves would be tuning to a fixture.
"""
