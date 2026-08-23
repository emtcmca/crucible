"""extract.py - turn a FOREIGN agent's source into pre-pass input, with provenance.

Plain English first. The Cartographer's whole point is that it is pointed at an
agent we did not write (`docs/decisions-pending/gemma-scope.md` section 2: all
eight tools in our own `capability_manifest.json` are already hand-classified, so
pointing it at ourselves gives it nothing to do). That means something has to
read a third-party repository and turn its tool functions into the spec shape
`prepass.classify_tool` accepts.

WHY THIS EXISTS RATHER THAN A HAND-TYPED TABLE.

`docs/proof/third-party-target-recon-2026-08-22.md` section 1 records what a
retyped value costs here: `f4c19ab` was a hardcoded fixture literal that looked
like a real upstream SHA, got printed inside a proof file, and was then read back
as an observation. Nothing in this module is typed by a human except the module
path and the tool-name list. Signatures, argument names, types and per-argument
documentation are read out of the foreign source by `inspect`, and the line
number of each `def` is read out of the same file object. If upstream changes a
signature, re-running this changes the fixture and the digest moves.

WHAT IT DOES NOT DO.

It does not classify anything - `prepass.classify_tool` does that, and the model
that reads the residue does the rest. It does not import the foreign package (no
`import customer_service`), because that would pull in `google.adk` and every
other dependency the sample declares; it loads ONE module file by path, which
works exactly when that module has no third-party imports of its own. If a target
does not satisfy that, extraction fails loudly rather than half-succeeding.

It also does not fetch anything. The caller supplies a path to a clone that
already exists on disk, outside this repository, and supplies the commit SHA it
verified. This module records what it was told and what it read; it does not
authenticate the pairing between them. `freeze_target()` is where the two are
written down together so a reviewer can re-check both.
"""

import importlib.util
import inspect
import os
import sys

from ..canon.hashing import hash_full
from .prepass import tool_spec_from_function


class ExtractionError(RuntimeError):
    """Raised when a foreign module cannot be read cleanly.

    Deliberately fatal rather than skip-and-continue. A partially extracted tool
    list becomes a manifest with a missing handle, and a missing handle
    classifies `UNCLASSIFIED`, which is ALLOWED - so the policy is silently off
    for that tool. `third-party-target-recon-2026-08-22.md` section 5 item 3
    makes that exact point about the Day-9 adapter.
    """


def load_module_by_path(module_path: str, module_name: str = "foreign_tools"):
    """Load a single .py file as a module without importing its package.

    The foreign sample's `tools.py` imports only `logging`, `uuid` and
    `datetime`, so it loads standalone. Loading the package instead would
    require `google.adk`, a model credential, and the sample's whole dependency
    tree - none of which a signature read needs.
    """
    if not os.path.isfile(module_path):
        raise ExtractionError("no such module file: %s" % module_path)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ExtractionError("cannot build an import spec for %s" % module_path)
    module = importlib.util.module_from_spec(spec)
    # Registered before exec so a module that inspects sys.modules for itself
    # (dataclasses, some decorators) does not fail in a confusing way.
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - re-raised with the path attached
        raise ExtractionError(
            "%s could not be executed standalone (%s: %s). This module only "
            "supports targets whose tool module has no third-party imports."
            % (module_path, type(exc).__name__, exc)
        ) from exc
    finally:
        sys.modules.pop(module_name, None)
    return module


def extract_tool_specs(module_path, tool_names, *, declaring_agent,
                       source_rel_path=None, transport="function"):
    """Build one `classify_tool` spec per named tool, each carrying provenance.

    Args:
        module_path: absolute path to the foreign module file to read.
        tool_names: the tool names to extract, in the order the foreign agent
            registers them. Supplied by the caller rather than discovered,
            because "every public function in the file" is not the same set as
            "the functions handed to the agent as tools" - the sample's
            `agent.py:58-71` is the registry, and a helper that happens to live
            in `tools.py` is not a tool.
        declaring_agent: the agent name to stamp on each spec.
        source_rel_path: path to record in provenance, relative to the foreign
            repository root. Recorded, not derived, because this module has no
            way to know where that root is.
        transport: transport label per architecture-spec.md:138.

    Returns:
        list[dict] - each a `classify_tool` spec plus a `provenance` key of
        `{"source_file": str|None, "def_line": int}`.

    Raises:
        ExtractionError: a named tool is absent, or is not a function.
    """
    module = load_module_by_path(module_path)
    specs = []
    for name in tool_names:
        fn = getattr(module, name, None)
        if fn is None:
            raise ExtractionError(
                "tool %r is not defined in %s - the registry and the source "
                "disagree, which is exactly the drift this raises on" % (name, module_path))
        if not callable(fn):
            raise ExtractionError("tool %r in %s is not callable" % (name, module_path))
        spec = tool_spec_from_function(fn, declaring_agent=declaring_agent,
                                       transport=transport)
        try:
            def_line = inspect.getsourcelines(fn)[1]
        except (OSError, TypeError):  # pragma: no cover - source is on disk here
            def_line = 0
        spec["provenance"] = {"source_file": source_rel_path, "def_line": def_line}
        specs.append(spec)
    return specs


def freeze_target(*, target_name, repository, commit_sha, specs,
                  extracted_on, notes=None):
    """Assemble the committed fixture: specs plus how to re-derive them.

    `digest` is a SHA-256 over the canonical form of the spec list ALONE -
    not over the wrapper. So the digest answers exactly one question: did the
    foreign agent's tool surface change? It does not move when a note is edited
    or the extraction date is re-stamped, and it does move if upstream renames
    an argument. A digest that also covers prose is a digest nobody can act on.

    `commit_sha` is recorded as given. This function does not verify it - the
    caller does, with `git rev-parse` in the clone, and pastes the output into
    the accompanying decision document. Recording an unverified SHA next to the
    data it supposedly describes is how `f4c19ab` happened; the mitigation is
    that the verification is a separate, human-checkable step, not that this
    function pretends to do it.
    """
    if not isinstance(commit_sha, str) or len(commit_sha) != 40:
        raise ExtractionError(
            "commit_sha must be the full 40-char SHA. A short SHA is ambiguous "
            "and an abbreviation is what got retyped last time.")
    return {
        "target_name": target_name,
        "repository": repository,
        "commit_sha": commit_sha,
        "extracted_on": extracted_on,
        "tool_count": len(specs),
        "digest": hash_full(specs),
        "notes": notes or "",
        "tools": specs,
    }


FROZEN_DIR = os.path.join(os.path.dirname(__file__), "foreign")


def load_frozen_target(name: str = "adk_customer_service") -> dict:
    """Read a committed foreign-target fixture and re-check its own digest.

    The digest is recomputed on load, not trusted. A fixture edited by hand -
    the exact thing `freeze_foreign_target.py` tells people not to do - fails
    here rather than at the point where a classification built on it is being
    defended.
    """
    import json

    path = os.path.join(FROZEN_DIR, "%s.json" % name)
    if not os.path.isfile(path):
        raise ExtractionError("no frozen target %r at %s" % (name, path))
    with open(path, encoding="utf-8") as fh:
        frozen = json.load(fh)
    recomputed = hash_full(frozen.get("tools"))
    if recomputed != frozen.get("digest"):
        raise ExtractionError(
            "%s has been edited: recorded digest %s, recomputed %s. Regenerate "
            "with `python -m crucible.cartographer.freeze_foreign_target`."
            % (path, frozen.get("digest"), recomputed))
    return frozen
