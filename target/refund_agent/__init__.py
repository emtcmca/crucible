"""The refund agent - the TARGET AGENT, the subject under test.

Not part of CRUCIBLE. See `target/__init__.py`.

Its policy is `refund_policy.md`: a paragraph of English, sourced from published
merchant policies rather than recalled, loaded verbatim as the system prompt. That
is the whole design. The agent is a good agent - it follows its policy - and its
policy is attackable, which is what the harness measures.
"""
