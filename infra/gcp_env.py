"""`scripts/gcp-env.sh` -> a name set, in pure Python, with no shell.

WHY THIS MODULE EXISTS. `verify_iam.load_env` used to ask bash to source the
file, on the stated reasoning that this gave "exactly one parser of it as well
as one copy of it". One COPY of the file is the property that matters and it is
untouched: `scripts/gcp-env.sh` remains the only place any of these names
exists, and nothing here retypes one. One PARSER was the part that was not
worth its price.

The price was found by an outside reviewer who could not reproduce this suite's
green: a Windows host without a working Git Bash lost five test modules to
collection errors, and - the part that was not a test problem at all -
`crucible/conductor/real_gate.py` reached the same call, so a `RealGate` could
not be CONSTRUCTED there. G7 and G8 are the two assertions that make a sealed
run believable, and they were unavailable to exactly the people the proof is
for. This repository ships spin-up instructions and an Open in Cloud Shell
button aimed at reviewers, and a gate that needs them to install a shell first
is portable to the author's machine rather than reproducible.

A SECOND PARSER CAN DISAGREE WITH SH, so that is falsified rather than assumed:
`tests/test_holdout_touch.py` and `tests/test_gcp_env_needs_no_shell.py` both
run this reader and bash side by side and require them to agree name for name,
wherever bash can actually run. That differential caught a real defect on its
first execution - a backslash-newline joined with a space where sh deletes it,
producing a double space inside `CRUCIBLE_ALL_SAS`.

Everything here raises rather than returning a partial answer. A missing name
does not fail loudly downstream: it compiles into a Cloud Logging filter that
matches nothing, and a filter that matches nothing is indistinguishable from a
seal nobody touched.
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
