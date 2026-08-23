<!-- DRAFT. Not published. Written 2026-08-22 while the D3 re-freeze lane was still
     running, so every figure below is a SLOT rather than a value.

     RULING 46 GOVERNS THIS FILE. No prose document states a current hash. Each
     [SLOT:...] below is filled at publication time by reading the named artifact,
     not by copying a value out of any document -- including this one, including
     CONVENTIONS, including a prior update. An update is published and immutable;
     a hash copied into one is a hash that will be wrong by Thursday and cannot be
     edited afterward. That is how the first freeze value reached the public.

     LENGTH CEILING: 350-500 words (ADR-0001). Register: lead with the unglamorous
     fact. No em-dashes. Update 2 is the upper bound, not the target.

     PUBLISH ONLY AFTER: the repoint lands, the manifest cross-check lands, the
     re-freeze runs green, and the superseded record is archived with its
     _superseded block. -->

## Update 5: the definition of breach is frozen, and two of its nine clauses were dead

[SLOT: objective_set_hash -- read from contracts/objective_set.v1.json + its freeze
proof at docs/proof/d3-objective-set-freeze.json. Do not copy from CONVENTIONS.]

The objective set is the file that says what counts as a breach. Nine clauses, each
naming a tool, an argument path and a condition. Update 4 said it would be the next
thing to freeze. It is frozen now, and the delay was worth the post.

### Two clauses named arguments that no tool emits

Two of the nine keyed on argument paths that do not exist in the target's tool
signatures. [SLOT: name the two repoints -- memo -> body, recipient_email -> to,
confirm against the landed diff.] A clause that names an absent path does not throw.
It evaluates to false, quietly, forever.

So those two clauses had never once fired on the real execution path. [SLOT: N
episodes, from the lane's before/after run] scored CLEAN that should have scored
BREACH. The oracle was not lenient. It was blind, and a blind oracle reports the
number a working one would.

### The same defect class was already a hard rejection on the other side

The policy validator refuses any patch naming an undeclared argument path. It has a
rule id and an error code for exactly this. The oracle that defines breach had no
such check, so the identical mistake was fatal in one direction and silent in the
other.

That is the durable fix and it is why this is a post rather than a commit message:
the objective set is now cross-checked against the capability manifest at load. A
clause naming a path no tool declares refuses to load at all. It cannot become a
number.

### What this invalidates

[SLOT: the ruling text. Say plainly what prior measurement is void and what is not.
Nothing had been promoted, so the honest answer is likely "nothing was published
against the old hash", but assert it from the record rather than from expectation.]

The prior freeze record is archived, not deleted, with its supersession noted in
place. Same handling the corpus lock got when it was deliberately broken and
re-taken.

### Still no results

[SLOT: confirm at publication -- if nothing has been promoted at press time, this
section stays and says so. If the live run has landed by then, this update does NOT
become the results post. Results get their own.]

[github.com/emtcmca/crucible](https://github.com/emtcmca/crucible)
