## Update 9: a human overruled the classifier, and the gate recording it had a hole

### Twelve tools, one at a time

Update 8 described a policy governing a Google ADK sample agent. The capability
classes that policy binds to came from a model reading each tool's description,
and no human had signed them. This week they were reviewed, one row at a time.

Eight were accepted. Four were amended. The one that matters is
`generate_qr_code`, which the classifier proposed as inert, meaning a positive
claim that the tool has no capability worth policing. The tool takes a float
discount value and mints an instrument that redeems it.

A stability run makes that worse rather than better. Across 36 runs the
classifier called it inert 28 times and money-moving 8 times. **This was not an
unlucky sample. It was a human overruling a classifier that was stable on the
wrong answer.**

The reviewer was first handed a summary sheet and refused to sign it, asking to
see all twelve rows. That refusal caught a real defect: the summary showed values
from a downstream fail-closed adapter rather than the classifier's actual
proposals, and it recommended amending the QR code tool to the empty set, which
would have ratified the model's own regression as a human decision.

### The gate had a hole, and an outsider found it

An independent adversarial review of `ratify.py` found that the ratification
digest covered the proposals the reviewer saw and nothing covered the verdicts
the reviewer recorded. An amendment class edited after signature changed the
manifest that shipped, and the digest check stayed green.

We reproduced it, then closed it. **This is the eighth instance in this project
of a check that passes while measuring nothing**, and the first found by someone
outside it rather than by our own test suite.

### Correcting Update 8

Update 8 said the deciding rule came from a policy CRUCIBLE had learned. In the
run that post described, the rule that fired was a seed rule, not a learned one.
That claim was not supported by its own evidence.

Re-running the probe against the ratified manifest, the matched-fact case is now
decided by a rule the loop did learn, and it names no tool. Both facts belong in
the record, and the second does not excuse the first.

### What is still unknown

The held-out attack family remains sealed. No transfer figure exists, and none
may be quoted until that family is opened, which happens once. The next update
reports that result, with its single-sample label and its split attached, or
reports that it was not run.

[github.com/emtcmca/crucible](https://github.com/emtcmca/crucible)
