"""python -m crucible.replay <bundle.json>

The entry point a stranger types after cloning a PUBLIC repository. It takes a
path and nothing else - no project flag, no credential file, no endpoint - and
that is the shape of the claim, not a convenience.

Exit codes, because something will script this eventually:
  0  the bundle cleared every integrity check and was rendered
  2  the bundle was REJECTED, or the path does not exist

A viewer that printed a defect and exited 0 would be the same failure as one
that rendered a blank, moved one layer out where a CI job cannot see it.
"""

import sys

from .view import main

if __name__ == "__main__":
    sys.exit(main())
