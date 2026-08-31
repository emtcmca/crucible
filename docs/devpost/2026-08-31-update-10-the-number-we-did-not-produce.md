## Update 10: the number we did not produce

Update 9 ended with a commitment: *"The next update reports that result, with its
single-sample label and its split attached, or reports that it was not run."*

**It was not run. The sealed family is still sealed.**

### Why

The unseal is a one shot. The pre-registration allows a single attempt, and
eleven rounds of independent adversarial review of the runner kept finding
defects in the machinery that would have made the resulting evidence unrulable.
Not defects in the agent. Defects in the thing that records what happened.

The last round closed this morning. Among the findings across those rounds: the
failure record told an auditor to query an audit window it did not carry; the
boundary it did carry was held in memory and would not have survived a
termination that runs no cleanup; and the capability that authorises a sealed
read was mintable by any caller, because it checked an ambient flag bound to no
bucket, no downloader and no invocation.

Every one of those was closed. Every one was found by someone reading the code
adversarially rather than by the test suite, which was green throughout.

Opening the seal with hours left, against a runner whose last defect had been
found that morning, would have spent the single attempt to produce a number
nobody could stand behind. **The number was the point of the project, and it is
still worth less than the ability to say what it means.**

### What exists instead

Two batches at identical configuration, the second pre-registered as a
replication before it fired. The offline reader accepts 20 of 20 bundles in
each.

Attack success, any-of-1, k=1 per episode, TARGET_FAULT episodes excluded:
pooled **13.5 percent at v0 falling to 7.7 percent at the final policy**, over
70 of 520 episodes and 56 of 725. **The two batches do not agree.** The
measurement batch ran 11.8 to 5.7; the replication ran 15.4 to 9.7, about four
points worse at both ends.

A replication that contradicts the first batch does not retire the first batch.
It retires the claim that one batch was enough.

**None of that is a transfer result.** It is measured on the families the loop
could see. Whether a policy learned from those transfers to a family it could
not see is exactly the question with no answer here.

### The correction this update owes

Re-deriving the unresolved-findings count from the completed measurement batch
today gives **21 refused patch attempts across three invariant classes, at 14, 4
and 3**. The design note those figures came from says 18, at 12, 4 and 2. It was
written while the batch was still writing.

**That is the fifth figure this project has had to correct for that one reason.**
The prepared story amendment's own checklist had flagged this slot to re-verify,
which is the only reason it was caught rather than published.

### Correcting Update 8

Update 8 said the transfer number is *"unsealed 2026-08-28 and does not exist
before then."* The first half did not happen. The second half is still true, and
is now true of every date since.

A date stated in the future tense is a prediction, and this one is on the record
as one that did not hold. It is corrected here rather than left to be noticed.

### What is still true

The seal is intact, and `python scripts/pre-read-seal-proof.py` says so rather
than we do. It checks that the sealed set still hashes to its published
commitment, that no tracked file leaks the family, and that the tree is clean,
and it refuses on any of them.

The corpus, the commitment, the runner and eleven rounds of review are all in
the repository. The question is open, and it is open in a way anyone can check.

### The accuracy boundary, unchanged

Eleven days. One person. One target agent. No users. Single-sample k=1 with no
stability estimate. The sealed set was reviewed by one person, who is also the
person who built the thing it was used to test. Not reviewed, endorsed, or
responded to by Google in any way.

[github.com/emtcmca/crucible](https://github.com/emtcmca/crucible)
