<!-- DRAFT. DO NOT POST UNTIL THE FREEZE HAS ACTUALLY HAPPENED.
     execution-spec 5a rule 1: THE TRIGGER IS THE ARTIFACT, NEVER THE CALENDAR.
     Post after `python scripts/freeze-d2-gate-rule.py --write` succeeds AND the
     record in docs/proof/ is committed and pushed. A freeze announced before it
     happened is precisely the failure this log exists to disprove, and it would
     sit on a public page forever.

     The hash below is a placeholder marked HASH_PENDING. Fill it from
     docs/proof/d2-gate-rule-freeze.json. Do not type it from memory.
     Format is fixed by docs/adr/ADR-0001-devpost-update-format.md. -->

## Update 3: the promotion rule is frozen before anything has been promoted

The second of five hash-locks landed today. `contracts/gate_rule.v1.yaml` is the rule that decides whether a proposed policy patch is promoted or rolled back, and it is now hash-locked at `HASH_PENDING`, recorded in `docs/proof/d2-gate-rule-freeze.json` with the commit that carries it.

**Nothing has been promoted yet.** That ordering is the entire content of this post.

### Why freeze the referee first

The loop this project runs is: attack the target, autopsy the breach, propose a policy patch, and gate it. The gate is where the temptation lives. When a patch stops the attack but breaks a benign case, the cheapest thing in the world is to decide that the benign case was unrealistic. Freezing the gate rule before any patch exists removes that option from the person who most wants it, which is me.

The rule includes the checks that can reject my own work: a benign suite that must stay at full pass, a rejection limit that halts the loop for a human rather than retrying, and a promotion path where the identity that authors a patch is not the identity that promotes it.

### The freeze script refuses more than it accepts

Writing the hash down is easy and proves nothing. The script refuses to run if the gate rule has uncommitted changes, if the file on disk differs from the file at the last commit, if the hash disagrees with the contract manifest, or if a freeze record already exists naming a different hash.

The first three say the same thing three ways: a freeze of a file that exists only on my laptop is not a freeze. The public commit timestamp is the evidence. The fourth is what "not editable after" means when enforced rather than remembered.

### What went wrong this time

The components were built in parallel, each deliberately blind to the others and each passing its own tests. The first time anything drove one episode through all of them, it failed four ways, and none was visible from inside any single component.

Two were the same shape: a job belonging to nobody because it sat exactly on a boundary. The enforcement layer was built to accept an injected computation, the schema was built to declare which values that computation produces, and no one wrote the arithmetic in between. Separately, the recorder correctly knew nothing about the definition of breach, the scorer correctly refused to score an episode not stamped with it, and nothing existed to do the stamping. That refusal surfaced as an error that read like a scorer bug and was a missing part.

### Still no results

The target agent, the capability manifest and the definition of breach freeze next, together, on the same day. Then the corpus. No attack has been scored, and there is still no number on this project worth quoting.

[github.com/emtcmca/crucible](https://github.com/emtcmca/crucible)
