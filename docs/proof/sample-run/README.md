# One real run, shipped so you can check us

**These three files are a complete, unmodified run from
`evidence/batch-measure-2026-08-27`, the 20-run measurement batch.** They are here because
`evidence/` is gitignored, and a repository that says "every number is checkable by someone
who does not trust us" while shipping nothing to check was making a claim it could not honour.

Nothing here is a fixture. It is what the loop wrote.

## Run it

Two commands, no credentials, no network, no model calls, no cost.

```bash
python -m crucible.replay docs/proof/sample-run/run-01.c6.json
python scripts/hardening-report.py docs/proof/sample-run/run-01.c6.json \
    --out /tmp/report --name sample
```

The first is the **offline reader**. It decides whether this bundle may be quoted at all, and
it prints a census rather than a rate, because a rate needs a denominator decision and that
decision belongs to the component that owns the measurement.

The second is the **hardening report**. It writes Markdown and HTML answering what was thrown
at the agent, what got through, what CRUCIBLE did about it, what stops now, what the agent can
still do, **what it cost you**, and **what we could not tell you**.

## What this particular run says about us

Read the report's own summary before anyone tells you what to think of it:

```
found      : 3 of 30 recorded episodes reached an invariant at policy@v0
hardened   : 1 learned rule in force at the end
incomplete : 2 of 3 recorded breach paths STILL REACH their invariant under
             policy@vFinal. The loop did not close them and this report will
             not round that off.
cost       : 4 benign flows now pass ONLY because a human approver signed off
```

**One rule learned, two of three breaches left open, and four benign flows that now need a
human.** That is a real result and it is not a flattering one. It is shipped because the
alternative is asking you to take the flattering summary on trust.

The `cost` line is the one to read twice. A benign pass rate that counts approver-signed
flows as untouched work is reporting your agent's capability and measuring your approver's
patience. **A rule that over-blocks passes every gate we have**, and that is the most
transferable thing this project found.

## What is NOT here, stated so you do not have to discover it

- **The sealed held-out family, F4.** It is absent from this bundle by construction: the
  families present are f1, f2, f3, f5, f6 and f7. F4 is the transfer test and it opens once.
  Its fingerprint is published in `docs/proof/sealed-family-commitment.json` and you can
  verify the seal without seeing its contents.
- **The other 39 runs.** Two 20-run batches exist. This is one of them, chosen because it
  promoted a rule and therefore exercises every section of the report. It is not the best
  run and it was not selected for looking good; the `incomplete` line above is what a
  representative run looks like here.
- **Any rate computed from this single run.** k=1. One run is one sample.

## Provenance

| file | what it is |
|---|---|
| `run-01.c6.json` | the evidence bundle, C6 schema, exactly as written |
| `run-01.json` | the run record; the report needs it beside the bundle because only it carries the final policy in executable form |
| `run-01.reader.json` | the offline reader's verdict on this bundle |

Copied byte-for-byte, not regenerated. Scanned with `scripts/seal-leak-check.py` before
publication: zero sealed-set signals across all three files.
