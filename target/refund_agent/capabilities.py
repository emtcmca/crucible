"""Capability classes, the UNCLASSIFIED sentinel, and coverage reporting.

Plain English first. A "capability class" is a label for the KIND of damage a tool
can do - move money, talk to the outside world, write durable state, read personal
data, raise its own privilege, call another agent. There are six, and the whole
project turns on the idea that a policy binding to those six generalizes, where a
policy binding to `issue_refund` does not.

Two things that are easy to conflate and must not be, because they are the reason
this module exists rather than a dict:

    the EMPTY SET   we know what this tool does, and it is nothing dangerous.
                    A pure read of non-personal data. CONVENTIONS section 2.2
                    calls it INERT.
    UNCLASSIFIED    we do not know what this tool does.

They are different facts. An agent whose tools are all inert needs no capability
boundary; an agent whose tools are all UNCLASSIFIED has not had one computed. If
those share an encoding, the second reports as the first - and on D9, where every
tool of an unseen target is unclassified until the manifest maps it, that is the
difference between a real transfer result and a manufactured one.

A THIRD failure sits next to those two and is separate again:

    UNMAPPED        the agent exposes the tool; the manifest never mentions it.

`UNCLASSIFIED` is a declaration. `UNMAPPED` is a disagreement between the manifest
and the agent - a build defect. Reporting the second as the first launders an
omission into a disclosed gap, which is why `capability_classes_for` RAISES rather
than defaulting, and why `CoverageReport` carries two separate tuples.

THE SECOND-LEVEL QUESTION an engineer asks here: "if no rule can select
UNCLASSIFIED, isn't an unclassified tool just allowed?" Yes, and that is deliberate
(ruling 22 item 6). Membership fails open on unclassified tools because the
alternative - letting one rule say `cap:UNCLASSIFIED => deny` - would block
everything on an unseen target and report 100% transfer for free. Detection is not
remediation: the TRIPWIRE scores the Objective Set independently of policy, so an
unclassified tool that moves money is still a recorded breach. The compensating
control is that the gap is COUNTED AND NAMED rather than absorbed.
"""

import enum

# The six, in the canonical order and the canonical spelling (CONVENTIONS 2.2).
# The short forms MONEY_MOVE, COMM_EXTERNAL, STATE_MUTATE, PII_READ,
# PRIV_ESCALATE, AGENT_INVOKE are dead vocabulary and appear nowhere.
CAPABILITY_CLASSES = (
    "CAP_MOVES_MONEY",
    "CAP_EXTERNAL_COMMS",
    "CAP_MUTATES_DURABLE_STATE",
    "CAP_READS_PII",
    "CAP_ESCALATES_PRIVILEGE",
    "CAP_INVOKES_AGENT",
)

# A sentinel, not a seventh class. No rule may select it (C4 V2).
UNCLASSIFIED = "UNCLASSIFIED"

# The empty set, named so that `is_inert(INERT)` reads as a statement rather than
# as a comparison against a literal `()` that could be a typo.
INERT = frozenset()


class Coverage(enum.Enum):
    """Three outcomes, and they are not orderable by severity - INCOMPLETE is a
    build defect, PARTIAL is an honest declaration."""

    FULL = "FULL"
    PARTIAL = "PARTIAL"          # every tool mapped; at least one UNCLASSIFIED
    INCOMPLETE = "INCOMPLETE"    # the manifest does not describe the agent


class ManifestIncompleteError(LookupError):
    """A tool the agent exposes has no entry in Part A."""


class CoverageReport:
    """Two tuples, never merged. See the module docstring."""

    __slots__ = ("status", "unmapped", "uncovered", "classified")

    def __init__(self, status, unmapped, uncovered, classified):
        self.status = status
        self.unmapped = tuple(unmapped)
        self.uncovered = tuple(uncovered)
        self.classified = tuple(classified)

    def __repr__(self):
        return ("CoverageReport(status=%s, unmapped=%r, uncovered=%r)"
                % (self.status.value, self.unmapped, self.uncovered))

    def as_statement(self) -> str:
        """The sentence that goes in the run report. CONVENTIONS 2.2 requires the
        uncovered tools to be NAMED, not counted."""
        if self.status is Coverage.INCOMPLETE:
            return ("MANIFEST INCOMPLETE - the agent exposes tools Part A does not "
                    "map: %s" % ", ".join(self.unmapped))
        if self.status is Coverage.PARTIAL:
            return ("PARTIALLY COVERED - %d of %d tools classified; unclassified: %s"
                    % (len(self.classified), len(self.classified) + len(self.uncovered),
                       ", ".join(self.uncovered)))
        return "FULLY COVERED - %d tools, all classified" % len(self.classified)


def _validate(classes) -> tuple:
    classes = tuple(classes)
    unknown = [c for c in classes if c not in CAPABILITY_CLASSES and c != UNCLASSIFIED]
    if unknown:
        raise ValueError("not capability classes: %r" % unknown)
    if UNCLASSIFIED in classes and len(classes) > 1:
        raise ValueError(
            "UNCLASSIFIED travels alone. %r mixes it with real classes, which means "
            "someone appended the sentinel to a partial classification - that reads "
            "as covered and is not." % (classes,))
    return classes


def is_unclassified(classes) -> bool:
    """True when we do not know what the tool does."""
    return UNCLASSIFIED in _validate(classes)


def is_inert(classes) -> bool:
    """True when we know what the tool does and it is nothing dangerous."""
    return len(_validate(classes)) == 0


def fail_closed_classes() -> tuple:
    """ALL SIX. Fail-closed and UNCLASSIFIED are two different answers to the same
    ignorance: one maximally restricts, the other declares the gap. A "fail-closed"
    tool carrying the sentinel would be the LEAST restricted thing in the manifest,
    because no rule can select it. C3a encodes this as a schema rule; it is repeated
    in code because the manifest builder needs a value, not a validation."""
    return CAPABILITY_CLASSES


def capability_classes_for(manifest: dict, tool_fqname: str) -> tuple:
    """Look up a tool's classes. RAISES on an unmapped tool - never returns ().

    Returning the empty set here would encode "this tool has no capabilities",
    which is a different and false fact about a tool that may well move money.
    """
    for entry in manifest.get("tools", ()):
        if entry["tool_fqname"] == tool_fqname:
            return tuple(entry["capability_classes"])
    raise ManifestIncompleteError(
        "%s is exposed by the agent and absent from the capability manifest. This "
        "is a build defect, not an unclassified tool: an unclassified tool is IN "
        "the manifest and says so. Add it to Part A or the D3 freeze hashes a "
        "manifest that does not describe the agent." % tool_fqname)


def coverage_report(manifest: dict, exposed_tool_fqnames) -> CoverageReport:
    """Compare what the agent exposes against what Part A maps."""
    mapped = {e["tool_fqname"]: tuple(e["capability_classes"])
              for e in manifest.get("tools", ())}
    unmapped, uncovered, classified = [], [], []
    for fqname in exposed_tool_fqnames:
        if fqname not in mapped:
            unmapped.append(fqname)
        elif is_unclassified(mapped[fqname]):
            uncovered.append(fqname)
        else:
            classified.append(fqname)

    if unmapped:
        # INCOMPLETE wins and `uncovered` stays empty: while the manifest and the
        # agent disagree about what the agent IS, a coverage percentage over the
        # rest is a number computed on a denominator that silently shrank.
        return CoverageReport(Coverage.INCOMPLETE, unmapped, (), classified)
    if uncovered:
        return CoverageReport(Coverage.PARTIAL, (), uncovered, classified)
    return CoverageReport(Coverage.FULL, (), (), classified)
