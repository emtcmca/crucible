"""render.py - the matrix as something a human cannot skim past.

THE RENDERING IS PART OF THE INSTRUMENT, NOT DECORATION. `episodes_fired: 0` in
a JSON blob is what the C6 bundle already carries and it is what nobody noticed
for four days. So the dark rows are printed with the STATE they are dark in,
they are repeated in a block of their own under a heading that says what a dark
clause does to a published number, and the state names are the ones that carry
a repair inside them: UNREACHED wants a trace, PATH_NEVER_PRESENT wants the
clause fixed, NEVER_TRUE wants nothing at all.
"""

from .matrix import (
    CONTEXT_FIELD_MISSING,
    FIRED,
    NEVER_TRUE,
    PATH_NEVER_PRESENT,
    UNREACHED,
)

_MARK = {
    FIRED: "FIRED",
    NEVER_TRUE: "never-true",
    PATH_NEVER_PRESENT: "PATH ABSENT",
    CONTEXT_FIELD_MISSING: "CTX MISSING",
    UNREACHED: "unreached",
}

_WHAT_IT_MEANS = {
    UNREACHED: ("no executed event in this source ever carried the clause's "
                "capability class. Nothing here can exercise it."),
    PATH_NEVER_PRESENT: ("events DID reach the clause's capability gate and a "
                         "condition's argument path was absent on every one. "
                         "THIS IS THE `memo` SHAPE - a check that cannot fail."),
    CONTEXT_FIELD_MISSING: ("a context operator names an `episode.*` field the "
                            "episodes do not carry. The real evaluator rules "
                            "such an episode INVALID."),
    NEVER_TRUE: ("reached, every argument path present, and the comparison "
                 "never held. This is what a healthy clause looks like against "
                 "traces that do not violate it."),
}


def render(matrix, title="OBJECTIVE SET CLAUSE COVERAGE"):
    lines = ["=" * 100, title, "=" * 100,
             "objective_set  %s  (%d clauses)"
             % (matrix.objective_set.hash, len(matrix.objective_set.clauses)),
             ""]

    if matrix.refusals:
        lines.append("SOURCES THAT REFUSED - these are NOT zeros, they are a broken instrument")
        for name, why in sorted(matrix.refusals.items()):
            lines.append("  %-32s %s" % (name, why.split(". ")[0]))
        lines.append("")

    if matrix.declared_absent:
        lines.append("SOURCES DECLARED ABSENT - named rather than omitted, and not a zero")
        for name, why in sorted(matrix.declared_absent.items()):
            lines.append("  %s" % name)
            lines.extend(_wrap("      ", why))
        lines.append("")

    lines.append("EPISODES PER SOURCE")
    for name in matrix.sources:
        skipped = matrix.skips.get(name) or []
        lines.append("  %-32s %4d episode(s)%s"
                     % (name, matrix.episode_counts[name],
                        "   (%d skipped)" % len(skipped) if skipped else ""))
        for note in skipped:
            lines.append("      skipped: %s" % note)
    lines.append("")

    # -- the matrix ------------------------------------------------------
    width = max(len(c["id"]) for c in matrix.objective_set.clauses)
    header = "  %-*s %-11s" % (width, "invariant", "form")
    for name in matrix.sources:
        header += " %-13s" % _abbrev(name)
    header += " | pooled"
    lines.append("CLAUSE x SOURCE - the cell is `fired/reached` episodes, then the state")
    lines.append(header)
    lines.append("  " + "-" * (len(header) - 2))
    for clause in matrix.objective_set.clauses:
        row = "  %-*s %-11s" % (width, clause["id"], clause["form"])
        for name in matrix.sources:
            cell = matrix.cells[clause["id"]][name]
            row += " %-13s" % ("%d/%d %s" % (cell.episodes_fired,
                                             cell.episodes_cap_reached,
                                             _short(cell.state())))
        pooled = matrix.pooled(clause["id"])
        row += " | %d fired / %d reached / %d evaluated  %s" % (
            pooled.episodes_fired, pooled.episodes_cap_reached,
            pooled.episodes_in_scope, _MARK[pooled.state()])
        lines.append(row)
    lines.append("")
    lines.append("  fired    = the clause returned TRUE on that many episodes")
    lines.append("  reached  = episodes where an executed event carried the clause's capability class")
    lines.append("  evaluated= episodes the clause was in channel scope for, which is every episode")
    lines.append("             while every clause is scoped to the ANY sentinel")
    lines.append("")

    # -- the dark blocks -------------------------------------------------
    total = len(matrix.objective_set.clauses)
    real = matrix.target_vocabulary_sources()
    fake = [s for s in matrix.sources if s not in real]

    lines.append("=" * 100)
    lines.append("WHICH SOURCES SPEAK THE TARGET'S TOOL VOCABULARY")
    lines.append("=" * 100)
    lines.append("  counted   %s" % (", ".join(real) or "NONE"))
    lines.append("  NOT counted (calls tools target/refund_agent does not expose): %s"
                 % (", ".join(fake) or "none"))
    lines.extend(_wrap(
        "  ", "A clause lit only by a fixture written in a vocabulary the target "
             "does not speak is not evidence that any real trace can reach it. It "
             "is evidence that the fixture and the clause were written together. "
             "The headline below counts ONLY the sources above that speak the "
             "target's vocabulary."))
    lines.append("")

    dark = matrix.dark_clauses(real)
    fired = total - len(dark)
    lines.append("=" * 100)
    lines.append("%d of %d CLAUSES EXERCISED BY A TRACE THE TARGET COULD ACTUALLY PRODUCE. %d DARK."
                 % (fired, total, len(dark)))
    lines.append("=" * 100)
    if dark:
        lines.extend(_wrap(
            "", "A breach rate computed over these sources measures %d of the %d "
                "sentences in the definition of breach, and is not honest unless it "
                "says so. Each dark clause, and why it is dark:" % (fired, total)))
        lines.append("")
    _dark_detail(lines, matrix, dark, real)

    pooled_dark = matrix.dark_clauses()
    lines.append("-" * 100)
    lines.append("FOR CONTRAST - pooling EVERY source, including the dead-vocabulary fixtures:")
    lines.append("  %d of %d clauses fire. The %d clause(s) that difference hides: %s"
                 % (total - len(pooled_dark), total, len(dark) - len(pooled_dark),
                    ", ".join(c for c, _, _ in dark
                              if c not in {d for d, _, _ in pooled_dark}) or "none"))
    lines.extend(_wrap(
        "  ", "That is the number a naive pooled count would publish, and it is "
             "the reason this instrument keeps the sources apart."))
    lines.append("")
    if pooled_dark:
        lines.append("  Dark even when everything is pooled:")
        _dark_detail(lines, matrix, pooled_dark, None, indent="  ")

    # -- tools -----------------------------------------------------------
    lines.append("=" * 100)
    lines.append("TOOL COVERAGE - the target exposes %d tools" % len(matrix.tool_names))
    lines.append("=" * 100)
    tw = max(len(t) for t in matrix.tool_names)
    header = "  %-*s" % (tw, "tool")
    for name in matrix.sources:
        header += " %-13s" % _abbrev(name)
    lines.append(header)
    lines.append("  " + "-" * (len(header) - 2))
    for tool in matrix.tool_names:
        row = "  %-*s" % (tw, tool)
        for name in matrix.sources:
            row += " %-13s" % (matrix.tools.get(name, {}).get(tool) or "-")
        lines.append(row)
    never = matrix.tools_never_reached()
    lines.append("")
    lines.append("  %d of %d target tools reached by at least one source"
                 % (len(matrix.tool_names) - len(never), len(matrix.tool_names)))
    if never:
        lines.append("  NEVER REACHED BY ANYTHING: %s" % ", ".join(never))
    unmapped = {k: v for k, v in matrix.unmapped_tools.items() if v}
    if unmapped:
        lines.append("")
        lines.append("  TOOL NAMES NO CAPABILITY MANIFEST MAPS - a trace calling one of these")
        lines.append("  exercises nothing in the real target:")
        for name, tools in sorted(unmapped.items()):
            lines.append("    %-32s %s" % (name, ", ".join(
                "%s x%d" % (t, n) for t, n in sorted(tools.items()))))
    lines.append("")
    return "\n".join(lines)


def _abbrev(name):
    parts = name.split("_")
    if len(name) <= 13:
        return name
    return "".join(p[:4] for p in parts)[:13]


def _short(state):
    return {FIRED: "FIRE", NEVER_TRUE: "n-t", PATH_NEVER_PRESENT: "PATH!",
            CONTEXT_FIELD_MISSING: "CTX!", UNREACHED: "-"}[state]


def _dark_detail(lines, matrix, dark, sources, indent=""):
    for clause_id, state, pooled in dark:
        lines.append("%s  %s" % (indent, clause_id))
        lines.append("%s      state    %s" % (indent, state))
        lines.extend(_wrap("%s               " % indent, _WHAT_IT_MEANS[state]))
        lines.append("%s      reached  %d episode(s), %d executed event(s) past the "
                     "capability gate" % (indent, pooled.episodes_cap_reached,
                                          pooled.events_cap_reached))
        if pooled.episodes_exempted:
            lines.append("%s      exempted %d episode(s) tripped the conditions and were "
                         "let through by exempt_when" % (indent, pooled.episodes_exempted))
        for key, slot in sorted(pooled.conditions.items()):
            lines.append("%s      arg      %-42s present on %d event(s), ABSENT on %d, "
                         "true on %d" % (indent, key, slot["present"], slot["absent"],
                                         slot["true"]))
        if sources is not None:
            per = ", ".join("%s %d/%d" % (s, matrix.cells[clause_id][s].episodes_fired,
                                          matrix.cells[clause_id][s].episodes_cap_reached)
                            for s in sources)
            lines.append("%s      by src   %s" % (indent, per))
        lines.append("")


def _wrap(prefix, text, width=100):
    import textwrap
    return textwrap.wrap(text, width=width, initial_indent=prefix,
                         subsequent_indent=prefix) or [prefix]
