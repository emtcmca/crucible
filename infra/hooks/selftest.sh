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
# Absolute, captured BEFORE the cd into the throwaway repo below.
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
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

# --- case 4: is the hook ARMED IN THIS REPOSITORY, right now? ----------------
# Added 2026-08-20 after a lane inspected `.git/hooks/`, found only `.sample`
# files, and reported the sealed-corpus guard as NOT ARMED. It was armed. The
# lane looked in the right place for a DEFAULT install and this repo sets
# `core.hooksPath`, so git never consults `.git/hooks` at all.
#
# That inference was reasonable and its inverse is the dangerous one: somebody
# unsets core.hooksPath, `.git/hooks` still looks the way it always did, and the
# guard is silently gone. So the armed state is now something a script reports
# rather than something a person infers from a directory listing.
cd "$REPO_ROOT" || exit 1
echo ""
echo "Armed check - is the guard live in THIS working copy?"
HOOKS_DIR="$(git rev-parse --git-path hooks)"
echo "  git resolves hooks to: $HOOKS_DIR"
if [ -x "$HOOKS_DIR/pre-commit" ] || [ -f "$HOOKS_DIR/pre-commit" ]; then
  echo "  ok    a pre-commit hook is present there"
else
  echo "  FAIL  NO pre-commit hook at the path git actually consults."
  echo "        Run: bash infra/hooks/install.sh"
  echo "        Note .git/hooks/ may look untouched and be irrelevant --"
  echo "        core.hooksPath redirects git away from it entirely."
  exit 1
fi
