"""corpus - L2's validators, linters, and the label-blindness harness.

**THIS PACKAGE CONTAINS NO CORPUS INSTANCES AND MUST NEVER CONTAIN ANY.**
`corpus/training/`, `corpus/sealed/`, `fixtures/benign/` and
`fixtures/known_bad/` hold the authored artifacts; everything importable here is
the machinery that checks them.

The split is deliberate and it is L2's brief: *a benign fixture nobody read is
an assumption rather than a fixture*, and the project owner reads all 24
personally. So the lane builds everything AROUND the fixtures first, and every
check that must run on them exists - and has already been shown able to fail -
before the first one is written.

WHAT IS HERE

    errors      one exception type, code + detail, no bare ValueErrors
    model       constants, and the values SOURCED from Part A rather than retyped
    schema      the shape a corpus instance must have, and its content-addressed ID
    lints       the approver lint, the fault-reason_code lint, the sealed-set lints
    sizing      the frozen counts, the sealed floor, and class coverage
    sepby       ruling 17's split, its parity stop condition, and its empty-set refusal
    blindness   ruling 19.3, and it gates the Part B freeze
    part_b      the C3 Part B document, buildable only from a PASSING blindness report
    load        reading the four directories off disk
    check       one command that runs all of the above

RUN IT

    python -m corpus              # validate everything on disk, exit 1 on any finding
"""
