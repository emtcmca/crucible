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
