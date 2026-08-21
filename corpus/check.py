"""check.py - one command that runs every corpus check. `python -m corpus`

The point of this file is scheduling, not logic. **The moment the 105 authored
artifacts land on disk, every check that must run on them already exists and has
already been shown able to fail** - so the authoring pass ends with one command
rather than with a list of things somebody has to remember to run.

    1  load + per-instance schema validation      corpus.schema
    2  the approver lint on every instance        corpus.lints
    3  the fault-reason_code lint on every pair   corpus.lints
    4  the sealed-set lints                       corpus.lints
    5  sizing and the sealed floor                corpus.sizing
    6  capability class coverage                  corpus.sizing
    7  the SEP-BY split and its parity gate       corpus.sepby
    8  the label-blindness check                  corpus.blindness
    9  Part B, buildable only if 8 passed         corpus.part_b

**It reports NOT-RUN, never OK, for a check whose input is absent.** A sweep
that prints nine greens on an empty repository is the object every negative
check in this project exists to prevent: `scripts/conformance-sweep.py` says it
for the census, ruling 22 says it for a rule matching an empty class
intersection, and it is true here too. An unevaluable check is not a passing
check.

Exit codes:  0 every runnable check passed   ·   1 a check failed
             2 nothing could be run - the corpus is not authored yet
"""

import io
import sys

from .blindness import run_blindness_check
from .errors import CorpusError, NotRun
from .lints import (
    lint_fault_reason_code,
    lint_sealed_capability_classes,
    lint_sealed_destination,
)
from .load import assert_pairs_resolve, load_corpus
from .model import fault_reason_codes, load_part_a
from .part_b import build_part_b
from .sepby import split
from .sizing import check_class_coverage, check_sizing

def _force_utf8_stdout():
    """Windows consoles default to cp1252 and the error details here are not ASCII.

    Called from `main()`, NOT at import. It was at module scope, which meant
    importing this module for any reason - a test that exercises the Runner, a
    tool that wants `main` without calling it - swapped the process's stdout out
    from under whoever owned it. Under pytest that closes the capture file and
    the ENTIRE suite reports `no tests ran`, which is a red that says nothing
    about any test.
    """
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace")


class Runner:
    def __init__(self):
        self.rows = []

    def run(self, name, fn, *, skip_if_absent=None):
        if skip_if_absent:
            self.rows.append((name, "NOT-RUN", skip_if_absent))
            return None
        try:
            result = fn()
        except NotRun as e:
            # The check looked, and there was nothing there. `skip_if_absent` is
            # decided from the filesystem before a check runs; this is the same
            # verdict reached after the check has computed its own input.
            self.rows.append((name, "NOT-RUN", e.reason))
            return None
        except CorpusError as e:
            self.rows.append((name, "FAIL", "%s: %s" % (e.code, e.detail)))
            return None
        self.rows.append((name, "PASS", _summary(result)))
        return result

    @property
    def failed(self):
        return any(s == "FAIL" for _, s, _ in self.rows)

    @property
    def ran(self):
        return any(s == "PASS" for _, s, _ in self.rows)


def _summary(result):
    if isinstance(result, dict):
        keep = {k: v for k, v in result.items()
                if not k.startswith("_") and not isinstance(v, (dict, list))}
        return ", ".join("%s=%s" % kv for kv in sorted(keep.items())) or "ok"
    return "ok"


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    _force_utf8_stdout()
    r = Runner()

    manifest = load_part_a()
    fault = fault_reason_codes(manifest)

    try:
        corpus = load_corpus(manifest=manifest)
    except CorpusError as e:
        print("LOAD FAILED  %s: %s" % (e.code, e.detail))
        return 1

    counts = {k: len(corpus[k]) for k in
              ("training", "sealed", "benign", "known_bad")}
    total = sum(counts.values())
    r.rows.append(("load", "PASS" if total else "NOT-RUN",
                   "on disk: %s; sealed dir present=%s; pairs file present=%s"
                   % (counts, corpus["_present"].get("sealed"),
                      corpus["_pairs_present"])))

    by_slug = {}
    for bucket in ("training", "sealed", "benign", "known_bad"):
        for d in corpus[bucket]:
            by_slug[d["slug"]] = d

    r.run("pairs resolve", lambda: assert_pairs_resolve(corpus),
          skip_if_absent=None if corpus["pairs"] else "corpus/pairs.json absent")

    def fault_lint():
        checked = 0
        for p in corpus["pairs"]:
            a, b = by_slug.get(p.get("attack")), by_slug.get(p.get("benign"))
            if a and b:
                lint_fault_reason_code(a, b, fault_codes=fault)
                checked += 1
        if checked == 0:
            # This row used to print `PASS pairs_checked=0`. A lint that
            # examined nothing is not a lint that passed, and the same file's
            # own doctrine says NOT-RUN for a check with no input. It matters
            # here more than most: the pair set can be full of CUT records or
            # sealed records that carry no slugs, so a green row over zero pairs
            # is reachable on a corpus that looks complete.
            raise NotRun(
                "no pair resolves to two instances on disk (%d pair records "
                "present). The fault-reason_code lint is the only thing "
                "standing between the corpus and a pair scored on NB-01's "
                "deliberate exemption, and no gate in the build catches a false "
                "positive." % len(corpus["pairs"]))
        return {"pairs_checked": checked}

    r.run("fault reason_code lint", fault_lint,
          skip_if_absent=None if corpus["pairs"] else "no pairs authored")

    def sealed_lints():
        for d in corpus["sealed"]:
            lint_sealed_capability_classes(d)
            lint_sealed_destination(d, manifest=manifest)
        return {"sealed_checked": len(corpus["sealed"])}

    r.run("sealed-set lints", sealed_lints,
          skip_if_absent=None if corpus["sealed"] else "no sealed instances on disk")

    r.run("sizing", lambda: check_sizing(corpus),
          skip_if_absent=None if total else "no instances on disk")
    r.run("class coverage", lambda: check_class_coverage(corpus),
          skip_if_absent=None if (corpus["training"] or corpus["sealed"])
          and corpus["benign"] else "needs both attacks and benign fixtures")
    r.run("SEP-BY split", lambda: split(corpus["pairs"]),
          skip_if_absent=None if corpus["pairs"] else "no pairs authored")

    labelled = corpus["training"] + corpus["sealed"] + corpus["benign"]
    report = r.run("label blindness", lambda: run_blindness_check(labelled),
                   skip_if_absent=None if labelled else "no instances on disk")
    r.run("Part B buildable", lambda: {"fields": len(build_part_b(report)["derived_fields"])},
          skip_if_absent=None if report else "blindness check did not run")

    width = max(len(n) for n, _, _ in r.rows)
    print("CRUCIBLE corpus check")
    print("-" * (width + 60))
    for name, status, detail in r.rows:
        print("%-*s  %-8s %s" % (width, name, status, detail))
    print("-" * (width + 60))

    if r.failed:
        print("RESULT: FAIL")
        return 1
    if not r.ran:
        print("RESULT: NOT-RUN - the corpus is not authored yet. This is not a "
              "pass. An unevaluable check is a check that cannot fail.")
        return 2
    print("RESULT: PASS on every check that had input to run against. Any "
          "NOT-RUN row above is a check with no input, NEVER a check that "
          "passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
