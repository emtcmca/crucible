"""conftest.py - the shared test helpers, and the one that must not need a shell.

WHY THIS FILE EXISTS
====================
`tests/test_holdout_touch.py` injects every collaborator it has: the log
reader, the project-policy fetch, the clock, the sleep. Not one of its 69 tests
needs a configured machine. It still could not be COLLECTED on a Windows host
without a working Git Bash, because its line 67 called
`infra.verify_iam.load_env`, and that function runs

    bash -c '. <repo>/scripts/gcp-env.sh && env | grep -E "^(CRUCIBLE_|SA_|SUFFIX)"'

at MODULE IMPORT TIME - during pytest collection, before a single test runs.

REPRODUCED 2026-08-29, deterministically. Every PATH directory holding
`bash.exe` was removed and the file was collected:

    pytest tests/test_holdout_touch.py --collect-only -q
    tests\\test_holdout_touch.py:67: in <module>
        ENV = verify_iam.load_env(str(REPO))
    infra\\verify_iam.py:72: in load_env
        out = subprocess.run(
    E   FileNotFoundError: [WinError 2] The system cannot find the file specified

An independent reviewer hit the same line a different way: Git Bash present but
unable to create its signal pipe, so the fork failed rather than the lookup.
Missing bash and broken bash are the same dependency, and a test that injects
its seams has no business having that dependency at all. THE SEAM WAS IN THE
WRONG PLACE: the names were reachable only through a function that shells out.

WHAT THIS DOES INSTEAD, AND WHY IT IS NOT A SECOND SOURCE OF TRUTH
=================================================================
`load_gcp_env` reads `scripts/gcp-env.sh` directly, in pure Python, and expands
its `${VAR}` references itself. **The names still come from that one file.** The
property `scripts/gcp-env.sh` exists to hold - one place for a bucket name, so a
retyped literal cannot produce an unevaluable gate - is untouched: nothing here
types `crucible-sealed-x7`, and `test_the_filter_is_built_from_gcp_env_and_not_
from_retyped_literals` still fails red if anything ever does.

What IS duplicated is the PARSING, and a second parser can disagree with bash
about what the file says. That is guarded, not assumed, and in two directions:

  1. **A partial parse raises.** `require=` names the keys the caller depends on
     and a missing one is a `GcpEnvError`, never a `KeyError` three frames later
     and never a silently absent name that compiles into a filter matching
     nothing. An unexpandable `${VAR}` raises for the same reason: an empty
     expansion would produce `gs://crucible-sealed-` and a query that returns
     zero, and zero is exactly what this repository's signature defect looks
     like.
  2. **A differential test in `tests/test_holdout_touch.py` runs BOTH readers and
     asserts they agree**, wherever bash can actually run. On a host where bash
     is missing or cannot fork, that one test SKIPS with a reason naming bash -
     and it is the only thing that skips. Collection, and the other 69 tests,
     no longer depend on the shell either way.

This does NOT fix the other four test modules that reach `load_env` during
collection (`test_real_gate.py`, `test_campaign_gate_wiring.py`,
`test_closure_gate.py`, `test_g4.py`), nor the production call sites in
`crucible/transfer/gcs_reader.py` and `crucible/conductor/real_gate.py`. The fix
that covers all of them is a shell-free `load_env` in `infra/verify_iam.py`,
which is outside this change's ownership and is reported rather than made.
"""

import os
import re


class GcpEnvError(RuntimeError):
    """`scripts/gcp-env.sh` could not be read into a trustworthy name set.

    Raised rather than returning a partial dict. A missing name does not fail
    loudly downstream: it compiles into a Cloud Logging filter that matches
    nothing, and a filter that matches nothing is indistinguishable from a seal
    nobody touched.
    """


# The prefixes `infra.verify_iam.load_env` keeps (`grep -E "^(CRUCIBLE_|SA_|SUFFIX)"`).
# Same filter, so the two readers return the same key set and the differential
# test below compares like with like.
_KEPT = re.compile(r"^(CRUCIBLE_|SA_|SUFFIX)")

# `export NAME=...`. Deliberately narrow: `export -f sa_email` and the
# `sa_email() { ... }` function definition do not match, and neither carries a
# name any caller reads.
_EXPORT = re.compile(r"^\s*export\s+([A-Za-z_][A-Za-z0-9_]*)=(.*)$")

# `${NAME}` or `$NAME`.
_REF = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")


def repo_root():
    """The repository root, from this file's location. Never from cwd.

    pytest can be invoked from anywhere; `scripts/gcp-env.sh` is always one
    directory above `tests/`.
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _expand(value, known, key, path):
    """Substitute `${VAR}` / `$VAR` from names already parsed. Unknown -> raise."""
    def sub(m):
        name = m.group(1) or m.group(2)
        if name not in known:
            raise GcpEnvError(
                "%s: %s references $%s, which is not defined earlier in the "
                "file. Expanding it to the empty string would silently produce "
                "a truncated resource name, and a filter built on a truncated "
                "bucket name matches nothing - which reads exactly like a "
                "clean seal." % (path, key, name))
        return known[name]
    return _REF.sub(sub, value)


def _unquote(raw):
    """The right-hand side of one assignment -> (text, expandable).

    Single quotes are literal in sh, so `$` inside them is not a reference.
    Bare values stop at whitespace or a comment, which is what sh does for an
    unquoted word.
    """
    raw = raw.strip()
    if raw.startswith('"'):
        end = raw.find('"', 1)
        if end < 0:
            return None, False
        return raw[1:end], True
    if raw.startswith("'"):
        end = raw.find("'", 1)
        if end < 0:
            return None, False
        return raw[1:end], False
    word = raw.split("#", 1)[0].strip().split()
    return (word[0] if word else ""), True


def load_gcp_env(root=None, require=()):
    """`scripts/gcp-env.sh` -> `{NAME: value}`. PURE PYTHON. No subprocess.

    A drop-in for `infra.verify_iam.load_env` for any caller that only needs the
    names, which is every test in `tests/test_holdout_touch.py`.

    `require` names the keys the caller will actually read. A key that is
    absent, or present and empty, raises here rather than surfacing as a
    `KeyError` inside a fixture or - far worse - as an empty string that
    compiles into a working-looking filter.
    """
    path = os.path.join(root or repo_root(), "scripts", "gcp-env.sh")
    if not os.path.exists(path):
        raise GcpEnvError(
            "%s does not exist. It is the single source for every project, "
            "bucket, and service-account name; there is no fallback and a "
            "retyped one would be a second source of truth." % path)
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    # Backslash line continuations, as in CRUCIBLE_ALL_SAS. sh DELETES the
    # backslash-newline pair; it does not replace it with a space. Substituting
    # a space here produced a double space inside CRUCIBLE_ALL_SAS and the
    # differential test in tests/test_holdout_touch.py caught it on its first
    # run - which is the entire reason that test exists.
    text = text.replace("\\\n", "")

    env = {}
    for line in text.splitlines():
        m = _EXPORT.match(line)
        if not m:
            continue
        key, raw = m.group(1), m.group(2)
        value, expandable = _unquote(raw)
        if value is None:
            raise GcpEnvError(
                "%s: the assignment to %s has an unterminated quote, so this "
                "reader cannot say what its value is. Guessing would put a "
                "wrong name into a gate filter." % (path, key))
        if expandable:
            value = _expand(value, env, key, path)
        env[key] = value

    # A parse that produced nothing at all, or lost the anchor name, is a broken
    # reader rather than an empty file.
    if "CRUCIBLE_PROJECT" not in env:
        raise GcpEnvError(
            "%s parsed to %d name(s) and none of them is CRUCIBLE_PROJECT. The "
            "file was read and not understood, which is a broken reader, not an "
            "empty configuration." % (path, len(env)))

    kept = {k: v for k, v in env.items() if _KEPT.match(k)}
    missing = [k for k in require if not kept.get(k)]
    if missing:
        raise GcpEnvError(
            "%s yielded no value for %s. A name that is absent does not fail "
            "loudly downstream; it compiles into a filter that matches nothing."
            % (path, ", ".join(missing)))
    return kept
