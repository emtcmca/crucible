"""selftest.py - the boot self-test. It runs before every round and it can HALT.

G1a's mechanism, and `HALT_HUMAN` on failure - listed alongside a known-bad leak
and a read-back failure, not advisory.

IT PROVES THREE THINGS, and the third is the one usually missing:

  1  ALL NINE KNOWN-BADS RETURN THEIR EXPECTED VERDICT. Per fixture, against a
     hash-locked answer key, with the fixture's own declaration cross-checked so
     a re-labelled fixture refuses to boot instead of calibrating against a
     moved key.

  2  THE HARNESS CAN REACH EVERY VERDICT, including the rare ones. BREACH and
     CLEAN are easy. A suite that has never emitted INVALID has never
     demonstrated it can stop a run, and INVALID is the verdict that stops one.

  3  THE HARNESS CAN STILL FAIL. Every shipped strawman is run against the same
     nine fixtures and MUST be rejected by them. NINE STRAIGHT ALL-PASS RUNS ARE
     INDISTINGUISHABLE FROM A BROKEN JUDGE, so this claim is re-earned on every
     boot rather than inherited from the day the fixtures were written.

Plus the import lint, because a component reported model-free on the strength of
a docstring is a convention wearing an enforcement label.
"""

import pathlib

from .import_lint import run_import_lint
from .known_bad import (KNOWN_BAD_IDS, MislabelledFixture, load_known_bad_suite,
                        run_known_bad_suite)
from . import strawman

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
DEFAULT_TRACES = REPO / "tests" / "golden_traces"
DEFAULT_GATE_RULE = REPO / "contracts" / "gate_rule.v1.yaml"


class SelfTestReport:
    __slots__ = ("ok", "failures", "outcomes", "verdicts_observed", "strawmen_caught",
                 "import_lint_findings", "import_lint_ran")

    def __init__(self, **kw):
        for slot in self.__slots__:
            setattr(self, slot, kw.get(slot))

    def render(self):
        lines = ["crucible tripwire --selftest", ""]
        for outcome in self.outcomes or []:
            mark = "ok " if outcome.ok else "BAD"
            lines.append("  %s  %-4s %-8s expected %-26s got %s"
                         % (mark, outcome.kb_id, outcome.component,
                            outcome.expected, outcome.verdict))
        lines.append("")
        lines.append("  verdicts reached      %s" % ", ".join(sorted(self.verdicts_observed or [])))
        for name, caught in sorted((self.strawmen_caught or {}).items()):
            lines.append("  strawman %-28s %s" % (name, "caught" if caught else "PASSED - SUITE BROKEN"))
        lines.append("  import lint           %s"
                     % ("clean" if not self.import_lint_findings else "FINDINGS"))
        for finding in self.import_lint_findings or []:
            lines.append("    %s" % finding)
        lines.append("")
        if self.ok:
            lines.append("ALL EXPECTED - nine fixtures, every verdict reached, every strawman caught")
        else:
            lines.append("SELF-TEST FAILED -> HALT_HUMAN")
            for failure in self.failures:
                lines.append("  %s" % failure)
        return "\n".join(lines)


def selftest(traces_dir=None, gate_rule_path=None):
    traces_dir = pathlib.Path(traces_dir or DEFAULT_TRACES)
    gate_rule_path = pathlib.Path(gate_rule_path or DEFAULT_GATE_RULE)
    failures = []

    try:
        suite = load_known_bad_suite(traces_dir, gate_rule_path)
    except MislabelledFixture as exc:
        return SelfTestReport(ok=False, failures=[str(exc)], outcomes=[],
                              verdicts_observed=set(), strawmen_caught={},
                              import_lint_findings=[], import_lint_ran=False)

    result = run_known_bad_suite(suite)
    if not result.all_expected:
        failures.append(
            "known-bad fixtures returned unexpected verdicts: %s. ANY WRONG VERDICT MARKS THE "
            "ENTIRE RUN INVALID - not the round." % result.wrong_verdicts)

    if len(result.outcomes) != len(KNOWN_BAD_IDS):
        failures.append("the suite ran %d fixtures; there are exactly %d and all are never cut"
                        % (len(result.outcomes), len(KNOWN_BAD_IDS)))

    observed = result.verdicts_observed
    required = {"BREACH", "CLEAN", "INVALID", "REJECT", "LINTER_REJECT_THEN_ACCEPT"}
    missing = required - observed
    if missing:
        failures.append(
            "the harness never reached %s. A verdict it has not produced is a verdict it has "
            "not demonstrated it can produce." % sorted(missing))

    caught = {}
    for name, (impl, must_fail) in strawman.STRAWMEN.items():
        wrong = run_known_bad_suite(suite, evaluate=impl)
        caught[name] = all(not wrong.by_id[kb].ok for kb in must_fail)
        if not caught[name]:
            passed = [kb for kb in must_fail if wrong.by_id[kb].ok]
            failures.append(
                "STRAWMAN %r PASSED %s. The suite has stopped measuring: a fixture that a "
                "known-wrong oracle passes is not testing the property it claims to test."
                % (name, passed))

    findings = run_import_lint()
    if findings:
        failures.append("import lint: %s" % [str(f) for f in findings])

    return SelfTestReport(ok=not failures, failures=failures, outcomes=result.outcomes,
                          verdicts_observed=observed, strawmen_caught=caught,
                          import_lint_findings=findings, import_lint_ran=True)
