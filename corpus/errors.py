"""errors.py - one exception, a code, and a detail that says what it cost.

Same shape as `crucible.manifest.ManifestError`. The code is what a test asserts
on; the detail is what a person reads at 1am, and it is expected to name the
consequence rather than restate the rule. "E_SEALED_BELOW_FLOOR: 17 instances"
is a complaint. "17 instances, and transfer is unmeasurable below 12 breaches at
v0, so the headline claim dies" is a reason not to route around it.
"""


class CorpusError(ValueError):
    def __init__(self, code, detail):
        self.code = code
        self.detail = detail
        super().__init__("%s: %s" % (code, detail))


class NotRun(Exception):
    """A check that found, on looking, that it had nothing to run against.

    NOT an error and NOT a pass. `check.py` decides `skip_if_absent` from what is
    on disk BEFORE a check runs, which is fine for a directory that is empty and
    useless for a check whose input only turns out to be empty once it has been
    computed - the fault-reason_code lint examines the pairs that resolve to two
    instances, and that set can be zero while `corpus/pairs.json` is full.

    Reporting PASS there is the exact shape this project refuses everywhere else:
    a check that prints the same green whether the corpus is empty or complete is
    not measuring anything (CONVENTIONS section 8 rule 2). Raising this makes the
    row read NOT-RUN and say what was missing.
    """

    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)
