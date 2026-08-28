# Cold install, verified 2026-08-28

**This closes the `UNVERIFIED` block at `README.md:401-408`**, which said
`pip install -r requirements.txt` had never been executed into an empty virtualenv and
named the exact command that would settle it. That command was run. It succeeded.

## What was run

```
python -m venv .venv                                  # empty environment, OUTSIDE the repo
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -c "import google.adk, jsonschema, referencing, yaml, pytest"
.venv/Scripts/python -m crucible.replay contracts/golden/C6-evidence_bundle.valid.json
.venv/Scripts/python -m pytest
```

Python 3.11.9. The venv was created in a scratch directory rather than in the tree, so
nothing in the repository was polluted and the result is not an artifact of the build
machine's site-packages.

## Result

| Step | Outcome |
|---|---|
| `pip install -r requirements.txt` | **exit 0.** All five pins resolved AT their pinned versions |
| `import google.adk` + `BasePlugin` | OK |
| `import jsonschema, referencing, yaml, pytest` | OK |
| offline reader vs the tracked golden fixture | **exit 0**, real census output |
| full test suite | **2195 passed, 1 skipped, exit 0**, 60.38s |

Resolved at the pins: `google-adk 2.1.0`, `jsonschema 4.26.0`, `referencing 0.37.0`,
`PyYAML 6.0.3`, `pytest 9.0.3`. The transitive tree resolved without conflict.

**The suite result in the cold environment is identical to the build machine's**, which is
the part that matters: the pins are not merely installable, they reproduce the same result
somewhere the build machine's pre-existing packages cannot be doing the work.

## Why this was worth doing rather than assuming

The prior caveat was written honestly and was right to exist. The packages were present on
the build machine at exactly those versions, so what had been verified was *that the pinned
versions are the ones everything ran against*, **not that a cold resolve succeeds**. Those
are different claims, and the README said so.

`pip` exiting 0 would not have settled it either. An install that resolves but cannot import,
or imports but cannot run the suite, is the same false pass this repository keeps finding.
That is why the check runs the reader and the suite in the cold environment rather than
stopping at the install.

## What this does and does not license

**Licensed:** "a judge can clone this repository into an empty environment, install the
pinned dependencies, and run the test suite and the offline reader." That is the spin-up
path the README describes, and it now has a record behind it.

**Not licensed:** any claim about a non-Windows platform or a different Python minor
version. This was Python 3.11.9 on Windows. A Linux or Colab environment is a *different*
environment and is unverified until it is run there.

**Not licensed:** any claim about the live path. Nothing here called a model, spent anything,
or touched GCS. `--live` remains unexercised by this check.

## Consequence for the README

`README.md:401-408` currently states the cold install is UNVERIFIED. That statement is now
false and understates the project in the section that tells a judge how to start. It should
be replaced with this result and a link here, keeping the platform caveat above.
