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

The second of five hash-locks landed today. `contracts/gate_rule.v1.yaml` decides whether a proposed policy patch is promoted or rolled back. It is hash-locked at `HASH_PENDING`, recorded in `docs/proof/d2-gate-rule-freeze.json` with the commit that carries it.

**Nothing has been promoted yet.** That ordering is the entire content of this post.

### Why freeze the referee first

The loop is: attack the target, autopsy the breach, propose a policy patch, gate it. The gate is where the temptation lives. When a patch stops the attack but breaks a benign case, the cheapest move available is deciding the benign case was unrealistic. Freezing the gate rule before any patch exists removes that option from the person who most wants it, which is me.

It includes the checks that can reject my own work: a benign suite that must stay at full pass, a rejection limit that halts the loop for a human rather than retrying, and a promotion path where the identity that authors a patch is not the identity that promotes it.

### The freeze script refuses more than it accepts

Writing the hash down is easy and proves nothing. The script refuses to run if the gate rule has uncommitted changes, if the file on disk differs from the file at the last commit, if the hash disagrees with the contract manifest, or if a freeze record already exists naming a different hash.

The first three say one thing three ways: a freeze of a file that exists only on my laptop is not a freeze. The public commit timestamp is the evidence. The fourth is what "not editable after" means when enforced rather than remembered.

### A correction to Update 2

Update 2 said the DSL emission experiment scored 20 of 20. **That number is retired and the post carrying it cannot be edited, so the correction goes here.**

It was scored by a throwaway checker written before the grammar was frozen, and the grammar then lost a qualifier. The checker was accepting a syntax the real parser rejects: it had measured a language nobody built. Against the frozen contract and the real validator: **21 of 21 parsed, 21 of 21 valid**.

The corrected number is better than the retired one, which is not the point. The point is that a checker written against a moving target reports on the target it remembers. That failure produced a *flattering* number here. There is no reason it always would.

Separately: the components were built in parallel, each blind to the others and each passing its own tests. The first time one episode ran through all of them, it failed four ways, none visible from inside any single component.

### Still no results

The target agent, the capability manifest and the definition of breach freeze next, together, on the same day. Then the corpus. No attack has been scored, and there is still no number on this project worth quoting.

[github.com/emtcmca/crucible](https://github.com/emtcmca/crucible)
