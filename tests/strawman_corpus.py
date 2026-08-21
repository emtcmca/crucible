"""strawman_corpus.py - DELIBERATELY WRONG corpus checks, kept in the tree forever.

Not drafts, not dead code. These are the proof that L2's corpus checks can
fail. `CONVENTIONS.md` section 8 rule 2: a check that cannot fail is not
measuring anything.

Each strawman is the version a competent engineer writes on the first pass -
which is exactly why it is dangerous. Every one of them returns a clean,
confident, green-looking answer on input the real check refuses.

  permissive_approver_lint    `.get("approver")`, so ABSENT and NULL are the
                              same bytes. This is not a hypothetical: in Python
                              `d.get("approver")` returns None for a declared
                              null AND for a key the author forgot, and ruling
                              23.4 exists because those two are different facts.

  substring_free_text_lint    a hardcoded {"memo", "note"} denylist instead of
                              the manifest's declared structured args. Misses
                              `body`, `subject_line`, and every free-text arg a
                              future tool adds - the check keeps passing while
                              its coverage shrinks.

  naive_sepby_split           counts and reports. On zero pairs it reports a
                              healthy split, because 0 oracle-separated pairs
                              never reach parity with 0 policy-separated ones.
                              A ratio computed over nothing looks exactly like a
                              ratio computed over a good corpus.

  blind_view_by_convention    a "blind" view that simply promises not to read
                              the label - a dict copy with a docstring. It
                              cannot fail, because nothing stops a field
                              computer from reading `kind`.

If a strawman ever agrees with the real implementation on its declared vectors,
the SUITE is broken and that is reported as a failure, not as a green run.
"""

FREE_TEXT_GUESS = {"memo", "note"}


def permissive_approver_lint(doc):
    """Returns None (clean) when the approver key is missing entirely."""
    approver = doc.get("approver")
    if approver is None:
        return None                      # "declared none" - it says so itself
    if not isinstance(approver, dict):
        return "E_APPROVER_MALFORMED"
    return None


def substring_free_text_lint(doc):
    """Clean unless the smuggled arg is literally named memo or note."""
    path = doc.get("smuggled_arg_path", "")
    if path in FREE_TEXT_GUESS:
        return "E_FREE_TEXT_IN_SEALED"
    return None


def naive_sepby_split(pairs):
    """Counts, divides, and reports. Never refuses."""
    pol = sum(1 for p in pairs if p.get("sep_by") == "POL")
    orc = sum(1 for p in pairs if p.get("sep_by") == "ORC")
    return {
        "policy": pol,
        "oracle": orc,
        "status": "PARITY" if orc >= pol and (pol or orc) else "OK",
    }


def blind_view_by_convention(doc):
    """A 'blind' view. It is a dict. It is blind because the docstring says so."""
    return dict(doc)
