"""Deliberately wrong implementations, kept so N2 and N3 keep the ability to fail.

Same device as `tests/strawman_canon.py`, and for the same reason stated there: a
suite that only ever runs against the implementation it was written alongside
cannot distinguish "correct" from "agrees with itself".

Both of these are the PLAUSIBLE wrong version - what you write if you have not read
`CONVENTIONS.md` section 2.2. Neither is a strawman in the pejorative sense; the
first is a one-line `dict.get` with a default, and the second is the obvious
"filter out the tools with no capabilities" line. They are what this code would
have looked like without the rulings.

NOTHING IMPORTS THESE OUTSIDE `tests/`.
"""

from target.refund_agent.capabilities import UNCLASSIFIED


def defaulting_capability_lookup(manifest, tool_fqname):
    """WRONG: returns the empty set for a tool the manifest never mentions.

    The bug: "we forgot this tool" and "this tool has no capabilities" become the
    same answer. The second is a false statement about a tool that may move money,
    and it is false silently - no rule selects an empty capability set, so the tool
    is allowed, and the coverage report counts it as classified.
    """
    table = {e["tool_fqname"]: tuple(e["capability_classes"])
             for e in manifest.get("tools", ())}
    return table.get(tool_fqname, ())


def collapsing_coverage(manifest, exposed_tool_fqnames):
    """WRONG: treats `UNCLASSIFIED` as "no capabilities".

    The bug: an agent whose tools are all UNKNOWN reports identically to an agent
    whose tools are all INERT. On D9 - an unseen target, where every tool is
    unclassified until the manifest maps it - that is the difference between "no
    capability boundary was needed here" and "no capability boundary was computed
    here". Returns a bare verdict string, which is itself part of the bug: a report
    that cannot name the uncovered tools cannot satisfy CONVENTIONS 2.2.
    """
    table = {e["tool_fqname"]: tuple(e["capability_classes"])
             for e in manifest.get("tools", ())}
    for fqname in exposed_tool_fqnames:
        classes = table.get(fqname, ())
        # "no dangerous classes" - which UNCLASSIFIED is not, but this line cannot
        # tell, because it filtered the sentinel out first.
        classes = tuple(c for c in classes if c != UNCLASSIFIED)
        if classes:
            continue
    return "COVERED"
