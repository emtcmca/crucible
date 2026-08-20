"""python -m crucible.tripwire --selftest

Exits NON-ZERO on failure. A boot self-test that prints a problem and still
exits 0 is a check that cannot fail, because CI and the round conductor read the
exit code and nothing else.
"""

import argparse
import io
import sys

from .selftest import selftest

# The findings carry arrows and section signs. On Windows the console codec is
# cp1252 and printing one CRASHES THE CHECK - which makes a real finding look
# like a broken tool rather than a result.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="crucible.tripwire")
    parser.add_argument("--selftest", action="store_true",
                        help="run the boot self-test (G1a) and exit non-zero on failure")
    parser.add_argument("--traces", default=None,
                        help="directory holding the fixtures (default: tests/golden_traces)")
    parser.add_argument("--gate-rule", default=None,
                        help="path to the hash-locked gate rule carrying the answer key")
    args = parser.parse_args(argv)

    if not args.selftest:
        parser.print_help()
        return 2

    report = selftest(args.traces, args.gate_rule)
    print(report.render())
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
