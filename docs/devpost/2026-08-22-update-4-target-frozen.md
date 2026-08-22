## Update 4: two of the three artifacts promised for today are frozen

The target agent is hash-locked. `target/refund_agent/FROZEN.json` carries `target_agent_hash` `125fe7e9e54a419e` and `manifest_hash` `d2e9f5f435b5acfe`, the second covering the capability manifest that says which tools exist and what class each one belongs to. The hashed payload canonicalizes to 4543 bytes. The protocol is `ADR-0017` and the transcript is `docs/proof/d3-target-freeze-2026-08-22.txt`.

Update 3 said the target agent, the capability manifest and the definition of breach would freeze together on the same day. **Two of the three did.** The objective set, which is the definition of breach, is not frozen. Today's only instance is a hand-written development file that declares itself one in its own first field, and the production artifact is still being authored. It gets its own post when it lands, and the claim stays incomplete until then.

### The lock that locked the label instead of the thing

The first version of this hash covered the capability manifest and the tool signatures, meaning tool names and parameter names. Not one line of any tool body was inside it. A target could be frozen, then rewritten to approve every refund it was ever asked for, and every number produced afterward would still cite the same hash as evidence of what was tested. It now hashes the bytes of every runtime module, asserted against the file list in both directions, so a rename cannot drop a module out of the lock and a new file cannot sit outside it.

### Running the protocol found a defect in the protocol

`ADR-0017` writes the freeze out as eight numbered steps. Step 6 clones the repository cold and re-checks the hash from a clean checkout, which is the step that catches a canonicalizer fooled by line endings. Step 7 commits the frozen record. Run in that order the clone has nothing to compare against and can only recompute, which is the weaker of the two assertions. It recomputed the identical value, so the trap was cleared either way, and the record was then committed and the clone run a second time to get the comparison the step exists for.

That sequence was written as an ADR, reviewed, and cited by three other documents before anyone executed it. A protocol whose steps cannot be run in the order written is a protocol nobody has run. The proof file records the reorder rather than quietly correcting it.

### Still no results

Three of the five hash-locks are down. Nothing has been measured: no attack has been scored, nothing has been promoted, and the results table in the README is every row a design target with an empty observed column. The next post is the objective set, then the corpus with its derived-field schema, and neither may say more than that it happened.

[github.com/emtcmca/crucible](https://github.com/emtcmca/crucible)
