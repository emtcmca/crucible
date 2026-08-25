# The daily update — README and Devpost, together

**Eric's standing instruction, 2026-08-25: the README is refreshed nightly until
submission, at the same time the Devpost update is drafted.** They are one job, not two.

They pair because they draw on the same thing — what actually changed today and what is
now measurable — and because splitting them is how one of them goes stale. The README is
the artifact a judge opens first; the Devpost update is the one they read on the way in.

**Enforced, not remembered.** `contract-check` has a `FRESH` pass that fails when the
README's `**As of YYYY-MM-DD` anchor is more than **2 days** old. It is the only
time-dependent pass in the file, deliberately: staleness is a function of time, so a
freshness check that fired only when someone edited the file could never catch the case it
exists for — a file nobody touched while the world moved. That is exactly how the README
came to say "nothing has been measured" during judging.

```bash
python scripts/contract-check.py     # FRESH fails if the README has drifted
```

---

## The order that works

**1. Read what actually changed.** `git log --oneline <yesterday's tag or sha>..main`.
The commit messages carry the reasoning; that is what they are for.

**2. Update the README's `## Status` section, and move the `**As of` date.**
The date is the anchor the FRESH pass reads. Moving it without updating the content below
it is worse than leaving it stale, because it converts an obvious gap into a false claim.

**3. Sweep for claims the day's work made false.** This is the step that gets skipped.
Every fix that closes a gap turns some sentence describing that gap into a falsehood.

```bash
python scripts/contract-check.py       # SWEEP + STATUS now cover README.md
python -m pytest tests/test_readme_claims.py -q
```

`tests/test_readme_claims.py` pins README paragraphs to the code that makes them true, in
BOTH directions — it fails if the README claims something unbuilt, and it fails if
something gets built while the README still calls it a gap. It has already fired once, on
2026-08-24, when ruling 37.1's producer landed.

**4. Draft the Devpost update.** Format is `docs/adr/ADR-0001-devpost-update-format.md`.

**5. Check the figures before either goes out.**

- No design target may be presented as a result. If a figure appears as a result and is
  not one, that is a defect — the README says so itself, and it means it.
- Every attack-success or benign figure carries **`single-sample, k=1, no stability
  estimate`** and the **policy / approval-oracle split** beside it (ruling 17).
- **No hash VALUE in prose** (ruling 46). Cite the path; read the value at use time.
- Counts are verify-on-use, on the right ref. Never recalled.

**6. Both go out, or neither.** A Devpost update quoting numbers the README contradicts is
worse than posting nothing.

---

## What the README still owes

**The Results table `Observed` column.** The row shape was published empty and in advance,
so the rows could not be chosen afterwards to suit the outcome — filling it is the payoff
of that discipline. It needs the batch data, the k=1 labelling, and the policy/oracle
split. The held-out rows stay dashed until the **08-28 unseal** and are not guessed.
