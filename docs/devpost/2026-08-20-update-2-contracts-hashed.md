## Update 2: the interfaces are frozen, and nothing has been measured yet

**CRUCIBLE** is a pre-deployment hardening harness. A red-team agent attacks a target that holds real permissions, a pure-code tripwire records what the target actually called, a coroner writes the autopsy, an armorer proposes a policy patch in a three-verb DSL, and a pure-code gate promotes it or rolls it back.

Today's milestone is deliberately unglamorous: **ten interface contracts are written, canonicalized, hashed, and committed, and no application code existed when they landed.** The manifest is at `contracts/MANIFEST.json`. Each carries a golden fixture pair, one instance that must validate and one known-bad that must fail, and each known-bad names in the file the exact rule it violates.

### Why post about interfaces

The claim this project will eventually make is that a policy learned from one attack family transferred to a family sealed away before the first patch was written. That is only worth anything if the order of operations is verifiable, so the order is published as it happens rather than asserted afterward.

Five things are hashed and committed before any measurement:

1. the gate rule
2. the target agent
3. the capability manifest
4. the objective set, which is the definition of breach
5. the corpus with its derived-field schema

Today covers the interfaces those artifacts must satisfy. Each of the rest gets its own post at the moment it freezes.

### Two things worth reporting from the day

**A decision rule written before the number arrived.** The riskiest assumption in the design was whether a Flash-tier model can spell a bespoke three-verb DSL it has never seen. The ruling for every possible outcome was committed first, then the calls were made. If it had come back under half, the grammar was going to be cut to two verbs and reported as a finding, and that ruling sits in the repo with a timestamp earlier than the result.

The first run scored 20 of 20 and **that number was retired the same day.** Its checker was written before the grammar was frozen, and the grammar then lost a qualifier, so the checker was accepting a syntax the real parser rejects. It measured a language nobody had built. Re-run against the frozen contract and the real validator: **21 of 21 parsed, 21 of 21 valid.** The second number is worth more because something could have failed it.

**The checks keep catching the person who wrote them.** The gate that verifies the contract hashes had a first negative test that *could not fail*: the mutation it made was exactly the whitespace the normalization exists to absorb. It was caught only because the negative test was actually run, and two of the five checks then turned out to have defects of their own.

### No results yet

No attack has been scored and there is no result on this project worth quoting. The next post is the promotion gate rule freezing, and it will say only that.

[github.com/emtcmca/crucible](https://github.com/emtcmca/crucible)
