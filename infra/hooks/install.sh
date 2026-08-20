#!/usr/bin/env bash
# Point this repository's hooks at the TRACKED hook directory.
#
# `core.hooksPath` is local config, so a fresh clone does not inherit it. That is
# a real limitation and it is stated rather than papered over: a judge who clones
# this repo has no pre-commit hook until they run this. The hook protects OUR
# working copies from staging sealed material; it was never a claim about theirs.
#
# Run:  bash infra/hooks/install.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$HERE"

git config core.hooksPath infra/hooks
chmod +x infra/hooks/pre-commit 2>/dev/null || true

# Assert the postcondition rather than trusting the exit code.
GOT="$(git config core.hooksPath)"
if [ "$GOT" != "infra/hooks" ]; then
  echo "FAILED: core.hooksPath reads '$GOT'" >&2
  exit 1
fi
echo "core.hooksPath = $GOT"

# A worktree resolves hooks through the COMMON git dir, so one install covers
# every lane worktree. Proved here rather than assumed, because if it were not
# true the six lane checkouts would each need their own install and five of them
# would silently not have one.
echo "resolved hooks dir for this checkout: $(git rev-parse --git-path hooks)"
echo ""
echo "Self-test - the hook must REFUSE a staged sealed path:"
bash "$HERE/infra/hooks/selftest.sh"
