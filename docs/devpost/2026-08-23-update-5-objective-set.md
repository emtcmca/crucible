<!-- DRAFT for Devpost update 5. Filled 2026-08-23 after the re-freeze landed.
     ADR-0001 ceiling: 350-500 words. Register: lead with the unglamorous fact.
     No em-dashes.

     IT STATES NO HASH, DELIBERATELY, AND SAYS SO IN THE BODY. Ruling 46. An
     update is published and immutable, so a hash copied into one cannot be
     corrected afterward. Update 4 carries a target hash that has since moved,
     which is the proof rather than the theory.

     VERIFY BEFORE PUBLISHING: re-read docs/proof/d3-objective-set-freeze.json
     exists and the four named instances are still the four. Do not recall them
     from this file. -->

## Update 5: the definition of breach is frozen, and two of its nine clauses had never fired

The objective set is the file that says what counts as a breach. Nine clauses, each naming a tool, an argument path and a condition. Update 4 said it would be next to freeze. It slipped, and the delay is the post.

### Two clauses named arguments that no tool emits

Two of the nine read `memo` and `recipient_email`. The target's tools carry `body` and `to`.

A clause naming an argument that does not exist does not throw. It evaluates to false, quietly, on every episode it ever sees. So those two clauses had never once fired on the real execution path, and the harness reported the number a working oracle would have reported.

Measured rather than estimated: all 50 training instances and all 26 benign fixtures were scored under both versions. **Four instances change, every one of them from CLEAN to BREACH.** Zero of the 26 benign fixtures move, so the benign floor is untouched. The harness had been under-reporting breaches and nothing indicated it.

### The same mistake was already fatal on the other side of the system

The policy validator has always refused a rule naming an argument path no tool declares. It has an error code for it. The oracle that defines breach had no such check, so the identical defect was a hard rejection in one direction and silent in the other.

That asymmetry is the durable fix. The objective set is now cross-checked against the capability manifest when it loads, and a clause naming an argument no call can carry refuses to load at all. It cannot become a number.

### Why this post contains no hash

Update 4 published a hash. That artifact has since been re-frozen, so a published post now carries a value that is no longer true, and a Devpost update cannot be corrected.

The rule adopted from that: a frozen hash has exactly one owner, which is the artifact plus its freeze record in the repository. No write-up states one. The lock is in `docs/proof/`, dated, in a public commit, where it can be checked against the file it covers.

### Still no results

Nothing has been promoted. The observed column of the results table is a dash on every row, and every figure beside it is a target set before any run.

[github.com/emtcmca/crucible](https://github.com/emtcmca/crucible)
