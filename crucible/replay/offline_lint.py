"""offline_lint.py - the enforcement artifact behind "replay needs no credentials".

`docs/lanes/L6-evidence.md` section 2: the viewer reads only from disk and needs
no credentials, and that is not a nicety - it is the judge's free reproduction
path on a PUBLIC repository. A README sentence saying so is a convention. THIS
FILE IS WHAT MAKES IT A CLAIM.

WHAT IT REFUSES, AND WHY EACH GROUP IS HERE
-------------------------------------------
1. NETWORK TRANSPORTS - `socket`, `ssl`, `http.client`, `urllib.request`,
   `requests`, and friends. A replay that fetches anything succeeds on the
   author's machine and nowhere else, which is the exact failure mode "clone it
   and run it" is supposed to rule out.
2. CLOUD SDKs - `google.cloud`, `google.auth`, `boto3`. These do not merely
   reach the network; they reach for ambient credentials, so their presence
   turns "works here" into "works where a credential happens to be lying about."
3. `subprocess` - the credential path an import deny-list misses entirely.
   Shelling out to `gcloud` is not an import.
4. ANY READ OF THE PROCESS ENVIRONMENT. This is the one `crucible/tripwire/
   import_lint.py` has no reason to make, and it is the sharpest rule here:
   the viewer has no business knowing what is in the environment, so the bar is
   not "no credential variables" but "no environment at all." A rule with an
   exception list is a rule that acquires exceptions.

WHY AN AST WALK AND NOT A GREP, which is the second-level question and the same
answer `import_lint.py` gives: a grep flags the word `subprocess` inside this
file's own docstring, and it misses `importlib.import_module("google.cloud")`
because that line contains no import statement. The AST sees import STATEMENTS
and the two string-indirection forms, and it sees nothing in prose.

WHAT IT CANNOT SEE, stated rather than hidden (`CONVENTIONS.md` section 8 rule 9):
a module name assembled at runtime (`"soc" + "ket"`), and a branch that only
executes under conditions this repository never creates. The first is not worth
closing - this lint defends against a well-meaning future edit, not against an
adversary with commit access, and CONVENTIONS section 7 already says plainly
that the trust root is the builder. The second is covered by the OTHER half of
NC-1: `tests/test_replay_offline.py` runs the viewer in a subprocess whose
environment has been stripped and whose socket module raises. Neither instrument
covers the other's blind spot, which is why there are two.

RELATIONSHIP TO `crucible/tripwire/import_lint.py`
--------------------------------------------------
Same technique, different question, and deliberately a second file. That module
bakes its deny set and its roots in at module level, so it cannot be pointed at
a different question without editing it - and it belongs to another lane.
Whether the two should become one parameterized lint is a coordinator call;
this note exists so the duplication is a decision rather than an accident.
"""

import ast
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent.parent

# Roots relative to the repository, so the lint travels with a clean checkout.
DEFAULT_ROOTS = ("crucible/replay",)

# EXACT dotted module names, matched on the module or on any of its DOTTED
# PREFIXES - never as a substring. `googleapiclient` must be caught by its own
# entry and not by "google", or the lint gets relaxed the first time somebody
# legitimately imports something whose name merely starts the same way. A lint
# that is relaxed once is a lint that is relaxed again.
#
# Note what is NOT here: `urllib` and `http`. `urllib.parse` and `http.cookies`
# are pure string work and offline. Denying the parent package would have been
# the lazy call and would have made the first legitimate need into an argument
# for widening the whole rule.
OFFLINE_DENIED_MODULES = frozenset({
    # transports
    "socket", "ssl", "select", "selectors", "asyncore", "asynchat",
    "http.client", "http.server", "urllib.request", "urllib.error",
    "ftplib", "smtplib", "poplib", "imaplib", "nntplib", "telnetlib",
    "xmlrpc.client", "xmlrpc.server", "webbrowser", "socketserver",
    # third-party transports
    "requests", "httpx", "urllib3", "aiohttp", "websockets", "websocket",
    "grpc", "grpc_status", "pycurl",
    # cloud SDKs and ambient-credential providers
    "google.cloud", "google.auth", "google.oauth2", "google.api_core",
    "google.adk", "google.genai", "google.generativeai", "googleapiclient",
    "vertexai", "boto3", "botocore", "azure", "keyring",
    # process escape hatches
    "subprocess", "pty", "multiprocessing.connection",
})

# Attributes of `os` that read or mutate the environment, or start a process.
# `os.path` is fine and is not here.
OFFLINE_DENIED_OS_ATTRS = frozenset({
    "environ", "environb", "getenv", "putenv", "unsetenv",
    "system", "popen", "execv", "execve", "execvp", "spawnv", "spawnl",
})

# Whole modules whose only purpose is reading the ambient environment.
OFFLINE_DENIED_ENV_MODULES = frozenset({"getpass", "netrc", "dotenv"})

_STRING_IMPORTERS = {"import_module", "__import__"}


class Finding:
    """One offending construct. Carries enough to fix it without opening the file."""

    __slots__ = ("path", "lineno", "what", "how")

    def __init__(self, path, lineno, what, how):
        self.path = str(path)
        self.lineno = lineno
        self.what = what
        self.how = how

    def __repr__(self):
        return "%s:%d: offline replay reaches %r (%s)" % (
            self.path, self.lineno, self.what, self.how)

    __str__ = __repr__

    def __eq__(self, other):
        return isinstance(other, Finding) and (
            self.path, self.lineno, self.what, self.how) == (
            other.path, other.lineno, other.what, other.how)


def _denied_module(dotted):
    """The denied ancestor of `dotted`, or None.

    `google.cloud.storage` is denied because `google.cloud` is. `google_fonts`
    is not, because matching walks dotted SEGMENTS rather than characters.
    """
    if not dotted:
        return None
    parts = dotted.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in OFFLINE_DENIED_MODULES or candidate in OFFLINE_DENIED_ENV_MODULES:
            return candidate
    return None


def scan_offline_source(source, path="<string>"):
    """Findings for one module's source text. Pure; touches no filesystem."""
    findings = []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        # A module the lint cannot parse is a module the lint cannot clear. It
        # is reported, never skipped - "unparseable" must not read as "clean".
        return [Finding(path, exc.lineno or 0, "<unparseable>",
                        "syntax error: %s" % exc.msg)]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                hit = _denied_module(alias.name)
                if hit:
                    findings.append(Finding(path, node.lineno, hit,
                                            "import %s" % alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level:      # a relative import can never leave the package
                continue
            hit = _denied_module(node.module)
            if hit:
                findings.append(Finding(path, node.lineno, hit,
                                        "from %s import ..." % node.module))
            if node.module == "os":
                for alias in node.names:
                    if alias.name in OFFLINE_DENIED_OS_ATTRS:
                        findings.append(Finding(
                            path, node.lineno, "os.%s" % alias.name,
                            "from os import %s" % alias.name))
        elif isinstance(node, ast.Attribute):
            # `os.environ`, `os.getenv(...)`. Matched on the NAME `os` rather
            # than on any expression, so `self.os.environ` is not caught - said
            # out loud rather than pretended away.
            if (isinstance(node.value, ast.Name) and node.value.id == "os"
                    and node.attr in OFFLINE_DENIED_OS_ATTRS):
                findings.append(Finding(path, node.lineno, "os.%s" % node.attr,
                                        "reads the process environment"))
        elif isinstance(node, ast.Call):
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name in _STRING_IMPORTERS and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    hit = _denied_module(arg.value)
                    if hit:
                        findings.append(Finding(path, node.lineno, hit,
                                                "%s(%r)" % (name, arg.value)))
    return findings


def run_offline_lint(roots=None):
    """Scan every `.py` under each root. Returns a list of Findings; empty is clean.

    Returning findings rather than raising is deliberate: the test suite asserts
    on them and a caller wanting a hard failure writes one line. A lint that can
    only raise cannot be asked "how bad is it".
    """
    roots = DEFAULT_ROOTS if roots is None else roots
    findings = []
    for root in roots:
        base = pathlib.Path(root)
        if not base.is_absolute():
            base = REPO / base
        if not base.exists():
            # A lint aimed at a path that does not exist passes forever, which
            # is the same defect class as a check that cannot fail.
            findings.append(Finding(base, 0, "<missing root>",
                                    "the lint is aimed at a path that does not "
                                    "exist, so it would report clean forever"))
            continue
        for py in sorted(base.rglob("*.py")):
            findings.extend(scan_offline_source(py.read_text(encoding="utf-8"), py))
    return findings
