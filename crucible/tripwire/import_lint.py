"""import_lint.py - the enforcement artifact behind "the TRIPWIRE contains no model".

`CONVENTIONS.md` 2.1 lists `TRIPWIRE`, `REGRESSION_WARDEN`, and `PROMOTION_GATE`
as pure code, and 7 permits only four claims to be called STRUCTURAL rather than
conventional. One of them is the TRIPWIRE's and the WARDEN's inability to call a
model. A comment saying so is a convention. THIS FILE IS WHAT MAKES IT A CLAIM.

WHY IT MATTERS MORE HERE THAN ANYWHERE ELSE. The oracle decides breach. If a
model can be reached from inside it, the oracle grades the attacker's story
instead of the world's state, and the entire improvement metric rests on this
component knowing nothing about WHY a call happened. The same argument runs
through 2.6 (never ask a model to perform a deterministic computation) and
through ruling 19's refusal of any model-computed `derived.*` field: a model on
the pure-code path launders judgment into arithmetic, and the measurement stops
meaning anything while continuing to look exactly like a measurement.

WHY AN AST WALK AND NOT A GREP, which is the second-level question. A grep over
the source flags the word `openai` inside this file's own docstring, and it
misses `importlib.import_module("openai")` because that line contains no import
statement. The AST sees import STATEMENTS and the two string-indirection forms,
and it sees nothing in comments or prose. The cost is that it cannot see a
module name assembled at runtime (`"open" + "ai"`) - stated rather than hidden,
per section 8 rule 9. That gap is not worth closing here: this lint defends
against a well-meaning future edit, not against an adversary with commit access,
and CONVENTIONS 7 already says plainly that the trust root is the builder.

THE COMPANION CONTROL, which is NOT asserted by this file: the run identity for
these components holds no `aiplatform.user` role, so the call fails at IAM even
if the import somehow lands. That half is L1's, and claiming it here would be a
lint reporting on a boundary it cannot see.
"""

import ast
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent.parent

# Roots relative to the repository, so the lint travels with a clean checkout.
DEFAULT_ROOTS = ("crucible/tripwire", "crucible/warden")

# EXACT dotted module names, matched on the module or on any of its prefixes.
# Never a substring match: `googleapiclient` must not be caught by "google", or
# the lint gets relaxed the first time somebody legitimately needs GCS - and a
# lint that is relaxed once is a lint that is relaxed again.
LLM_CLIENT_MODULES = frozenset({
    "google.generativeai",
    "google.genai",
    "google.ai",
    "vertexai",
    "google.cloud.aiplatform",
    "google.cloud.aiplatform_v1",
    "anthropic",
    "openai",
    "cohere",
    "mistralai",
    "litellm",
    "ollama",
    "transformers",
    "llama_cpp",
    "langchain",
    "langchain_core",
    "langchain_google_vertexai",
    "google.adk",
})

# THE SECOND DENY SET, added 2026-08-21, and it closes a FABRICATED CHECK.
#
# `measurement-spec.md:987-989` says the blind-input boundary is "enforced by the
# function's arity AND BY A UNIT TEST asserting the Tripwire module cannot import
# the corpus label schema."
#
# THERE WAS NO SUCH TEST. Not in `tests/`, not in `crucible/`, not in `scripts/`.
# The deny list above covered LLM clients only. The property was true on the day
# it was written and stayed true BY ACCIDENT rather than by anything that could
# fail - which is this project's own worst pattern, stated in its own spec, about
# its own oracle. Found while backfilling ADR-0016.
#
# WHAT THESE MODULES CARRY. `corpus.model` and `corpus.load` read instances whose
# fields include the attack family, the expected verdict, and `near_miss`. The
# TRIPWIRE decides BREACH or CLEAN from the recorded call log and the Objective
# Set. If it could reach a label, the oracle would be scoring the answer key, and
# every transfer number in the project would be measuring the corpus's opinion of
# itself.
#
# `fixtures` is denied for the same reason and one more: the benign suite is what
# the BENIGN FLOOR is computed against, so an oracle that can see it can be tuned
# to it without anyone writing a line of tuning code.
LABEL_BEARING_MODULES = frozenset({
    "corpus",
    "fixtures",
})


class Finding:
    """One offending import. Carries enough to fix it without opening the file."""

    __slots__ = ("path", "lineno", "module", "how")

    def __init__(self, path, lineno, module, how):
        self.path = str(path)
        self.lineno = lineno
        self.module = module
        self.how = how

    def __repr__(self):
        return "%s:%d: %s imports %r (%s)" % (
            self.path, self.lineno, "this pure-code module", self.module, self.how)

    __str__ = __repr__

    def __eq__(self, other):
        return isinstance(other, Finding) and (
            self.path, self.lineno, self.module, self.how) == (
            other.path, other.lineno, other.module, other.how)


def _is_denied(dotted):
    """True if `dotted` is a denied module or a submodule of one.

    `google.genai.types` is denied because `google.genai` is. `googleapiclient`
    is not, because prefix matching here is on DOTTED SEGMENTS, not characters.
    """
    if not dotted:
        return None
    parts = dotted.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in LLM_CLIENT_MODULES or candidate in LABEL_BEARING_MODULES:
            return candidate
    return None


_STRING_IMPORTERS = {"import_module", "__import__"}


def scan_source(source, path="<string>"):
    """Findings for one module's source text. Pure; takes no filesystem."""
    findings = []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        # A module the lint cannot parse is a module the lint cannot clear. It
        # is reported, never skipped - "unparseable" must not read as "clean".
        return [Finding(path, exc.lineno or 0, "<unparseable>", "syntax error: %s" % exc.msg)]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                hit = _is_denied(alias.name)
                if hit:
                    findings.append(Finding(path, node.lineno, hit, "import %s" % alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level:            # a relative import can never leave the package
                continue
            hit = _is_denied(node.module)
            if hit:
                findings.append(Finding(path, node.lineno, hit, "from %s import ..." % node.module))
        elif isinstance(node, ast.Call):
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name in _STRING_IMPORTERS and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    hit = _is_denied(arg.value)
                    if hit:
                        findings.append(
                            Finding(path, node.lineno, hit, "%s(%r)" % (name, arg.value)))
    return findings


def run_import_lint(roots=None):
    """Scan every `.py` under each root. Returns a list of Findings; empty is clean.

    Returning findings rather than raising is deliberate: `--selftest` prints
    them, the test suite asserts on them, and a caller that wants a hard failure
    writes one line. A lint that can only raise cannot be asked "how bad is it".
    """
    roots = DEFAULT_ROOTS if roots is None else roots
    findings = []
    for root in roots:
        base = pathlib.Path(root)
        if not base.is_absolute():
            base = REPO / base
        if not base.exists():
            findings.append(Finding(base, 0, "<missing root>",
                                    "the lint is aimed at a path that does not exist, so it "
                                    "would pass forever"))
            continue
        for py in sorted(base.rglob("*.py")):
            findings.extend(scan_source(py.read_text(encoding="utf-8"), py))
    return findings
