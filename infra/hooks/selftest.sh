#!/usr/bin/env bash
# Prove the sealed-corpus pre-commit hook can actually refuse a commit.
#
# CONVENTIONS.md section 8 rule 2: a check that cannot fail is not measuring
# anything. A hook script sitting in a directory is not evidence that a commit
# would be blocked - core.hooksPath could be unset, the file could be
# non-executable, the shell could differ, the path match could be wrong.
#
# So this builds a THROWAWAY repository, installs the real hook file into it,
# and drives a real `git commit` at it. Two cases, and BOTH must hold:
#
#   1. `git add -f corpus/sealed/<file>` then commit  ->  MUST FAIL
#   2. an ordinary file                  then commit  ->  MUST SUCCEED
#
# Case 2 is not padding. A hook that refuses everything also "passes" case 1,
# and would be discovered only when it blocked real work at 2am.
set -uo pipefail

HOOK="$(cd "$(dirname "$0")" && pwd)/pre-commit"
[ -f "$HOOK" ] || { echo "no hook at $HOOK" >&2; exit 2; }

TMP="$(mktemp -d 2>/dev/null || mktemp -d -t crucible-hook)"
trap 'rm -rf "$TMP"' EXIT

cd "$TMP"
git init -q .
git config user.email selftest@crucible.invalid
git config user.name  "hook selftest"
git config commit.gpgsign false
mkdir -p .githooks corpus/sealed
cp "$HOOK" .githooks/pre-commit
chmod +x .githooks/pre-commit
git config core.hooksPath .githooks
printf 'corpus/sealed/\n' > .gitignore

FAILURES=0

# --- case 1: sealed material, force-added past .gitignore --------------------
printf 'SEALED HOLDOUT ATTACK\n' > corpus/sealed/atk_seal_001.json
git add -f corpus/sealed/atk_seal_001.json
if git commit -q -m "should never land" 2>/dev/null; then
  echo "  FAIL  case 1: the commit SUCCEEDED. The hook did not block sealed material."
  FAILURES=$((FAILURES + 1))
else
  echo "  ok    case 1: sealed path refused"
fi
git reset -q

# --- case 2: an ordinary file --------------------------------------------
printf 'ordinary\n' > README.md
git add README.md
if git commit -q -m "ordinary commit" 2>/dev/null; then
  echo "  ok    case 2: ordinary commit allowed"
else
  echo "  FAIL  case 2: the hook blocked an ORDINARY commit. A hook that refuses"
  echo "        everything passes case 1 for the wrong reason."
  FAILURES=$((FAILURES + 1))
fi

# --- case 3: a path with a space, staged under corpus/sealed/ ----------------
# The NUL-delimited read exists for this. A newline-split loop mangles it and
# the file slips through while the hook reports clean.
printf 'SEALED\n' > "corpus/sealed/atk seal 002.json"
git add -f "corpus/sealed/atk seal 002.json"
if git commit -q -m "should never land either" 2>/dev/null; then
  echo "  FAIL  case 3: a sealed path CONTAINING A SPACE got through."
  FAILURES=$((FAILURES + 1))
else
  echo "  ok    case 3: sealed path with a space refused"
fi

if [ "$FAILURES" -ne 0 ]; then
  echo "SELFTEST FAILED: $FAILURES case(s)" >&2
  exit 1
fi
echo "SELFTEST PASSED: 3/3"
