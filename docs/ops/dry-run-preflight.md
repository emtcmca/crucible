# Live dry-run preflight

**Built 2026-08-22 by the coordinator, ahead of the first comprehensive `--live` run.**
Every row below was checked, not recalled. Where a row says UNVERIFIED it means exactly that.

The point of this file is that **a precondition checked after six rounds of model spend is a
precondition checked too late** — the campaign's own words, and the reason `--holdout-expected`
is a required flag rather than a default.

---

## 1. Verified now

**Every row below re-checked 2026-08-23 by running it, not by reading it.**

| Check | State | How it was checked |
|---|---|---|
| Application default credentials | **PRESENT** | `%APPDATA%\gcloud\application_default_credentials.json` exists. *(A first check against the Unix path `~/.config/gcloud` said ABSENT — wrong path on Windows. Recorded because it is the shape of a false blocker.)* |
| gcloud account | **`eric@erictetzlaff.com`, active** | `gcloud auth list` |
| `main` | **green** | `pytest` exit 0, `contract-check` exit 0 |
| Six lock fields | **all FROZEN** | printed by the campaign banner every run |
| Offline campaign | **runs clean, $0.0000** | `python -m crucible.conductor.campaign` |
| C6 bundle | **VALIDATES, reader ACCEPTS 17/17** | printed by the run |
| Replay render | **renders** | `python -m crucible.replay <bundle>` exit 0 |
| Attacks resolve to the corpus | **6 of 6** | every `corpus_instance_id` looked up against `corpus/training/` |

---

## 2. The spend question, answered precisely

**There are two caps and only one of them is real. Do not conflate them.**

**The application-layer cap IS real.** `--usd-cap` defaults to **$5.00** and the BUDGET_GOVERNOR
authorizes every model call against it. A refusal degrades that call to a replay and says so
rather than raising, so the run continues on seeds instead of overspending. The banner prints
`spend: $X of $CAP` every run. **This is the cap that binds tonight, and it binds in process.**

**The GCP-layer cap is NOT real.** `docs/ops/billing.md` establishes that the $160 budget is an
**ALERT**: `notificationsRule` carries only email recipients and the three threshold rules SEND
MAIL at 50/90/100%. Nothing stops at $160. `execution-spec.md:184` predicted this — *"plain
budgets cap nothing"* — and named the fallback, a budget → Pub/Sub → Cloud Function calling
`projects.updateBillingInfo`. **No such Pub/Sub wiring exists in `infra/`.**

**The coordinator's read on what that means:**

- **For tonight, exposure is bounded by `--usd-cap`, in process, and it is small.** The observed
  live run cost **$0.0321**. Set the cap deliberately rather than accepting the default, and it
  is the binding constraint.
- **The GCP-layer cap becomes load-bearing when the Cloud Run endpoint opens to `allUsers`**,
  because an open endpoint can be hammered by something that is not our loop and `--usd-cap`
  governs nothing outside the campaign process. That is a **submission-week** requirement
  (Q `c-20260822-1617-c8b2`), not a tonight requirement.
- Building the Pub/Sub kill switch is a mutating GCP change and is **not** being done unsupervised.

**One cost note that is new tonight:** the CORONER now fires **once per breach** rather than
once per round (CONVENTIONS §3.1 conformance, 2026-08-22). On a six-round run that moves the
ceiling from 6 CORONER calls to 36. It is the cheapest model in the roster
(`gemini-3.5-flash-lite`, `minimal`), so the absolute change is small — but the run will cost
more than the last one did, and knowing why beforehand is better than wondering afterwards.

---

## 3. `--holdout-expected` — required, and the value is a decision

`--live` **refuses to start** without it. `contracts/gate_rule.v1.yaml:205` reads
`holdout_touch_count == expected_for_this_phase`, and the campaign will not invent the number
because the phase is not knowable from inside it.

**Recommended value for a hardening dry run: `0`.** The reasoning, checked rather than assumed:

- The loop reads `corpus/training/` from disk. `CorpusSeeds.load()` names the TRAINING layout
  and **raises** on any instance declaring the sealed family, so no code path reaches the
  holdout.
- G7a and G7b use `gcloud storage buckets describe` and `get-iam-policy` — **ADMIN_READ on the
  bucket, not `storage.objects.get` on an object.** `holdout_touch` counts by operation kind and
  counts CONTENT_READ only; enumeration and prefix-gets do not count.

**Therefore a hardening run should touch the holdout zero times, and `0` is the assertion that
this is true.** If it comes back non-zero, that is the instrument working and it is the most
important result of the night. **Not a reason to raise the number.**

An EVALUATION phase is different — it reads 18–24 sealed instances and would pass its own count.
Do not carry tonight's `0` into that run.

---

## 4. Blocked on the lanes, not on you

**RE-CHECKED 2026-08-23. EVERY BLOCKER LISTED HERE HAS LANDED. THIS SECTION NO LONGER BLOCKS
THE RUN.** It is kept rather than deleted because the previous version scheduled four pieces of
work as prerequisites, and a checklist that still lists finished work makes a cleared runway
look like a wall.

| was blocking | state |
|---|---|
| Corpus dialect re-author, 18 instances, then the `corpus_hash` re-freeze | **landed**, ruling 47 |
| Failed-call guard, case-3 exclusion | **landed** |
| Overclaim sweep and the adversarial bundle | **landed** |
| Mutation audit | **landed**, never blocking |

**One blocker was added after this section was written and it has also cleared: the D3 objective
set re-freeze** (ruling 48). Two of the nine clauses named arguments no tool emits and had never
fired. Four training instances flip CLEAN to BREACH; zero of 26 benign move.

**Still running, and neither blocks the run:** the DSL and policy-engine mutation audit, and the
clause-coverage lane. The coverage lane's output governs what may be *said* about the run's
numbers, not whether the run may happen. See section 5.

---

## 5. Known unknowns going in — say these out loud before the run, not after

- **The ARMORER has never promoted anything.** The `require_approval` steer landed today and is
  **unproven against a live model.** If it still emits only `deny`, expect rejections and a
  human-gate halt again. That is a legitimate result, not a failure of the night.
- **The degenerate-success mode to watch for:** if the ARMORER swings to blanket class-level
  `require_approval`, the benign floor reports **26/26 and cannot flag it** — the approval oracle
  approves anything declaring a valid approver. `capability_retained()` and the verb-usage board
  are the only instruments that would catch a policy that looks convergent while having learned
  nothing. **Read those two before celebrating a promotion.**
- **`GcsBlobIO` has never executed** and the policies bucket is empty, because nothing has ever
  been promoted. The first promotion exercises a write path that has never run.
- **8 OF THE 9 OBJECTIVE SET CLAUSES ARE EXERCISED BY A TRACE THE TARGET COULD PRODUCE. ONE IS
  DARK.** *(This bullet said "only 2 of 9" for about an hour on 2026-08-23. That figure came
  from the RETIRED six-shape default script, not the live path, and it was wrong. Corrected
  before the run and before publication; the wrong number is named here rather than erased.)*
  The dark clause is `inv_account_identifier_left_the_boundary`: reached 15 times, every
  argument path present, the comparison never true. It needs a trace, not a repair. **Pooling
  every source including the dead-vocabulary fixtures reports 9 of 9 and hides it**, so read the
  matrix per source, never pooled.
- **The per-clause coverage matrix must be read beside any rate before the rate is quoted.** A
  breach rate published without it invites the assumption that all nine clauses were in play.
- **No transfer number is possible tonight.** F4 is the sealed held-out family and a hardening
  run does not touch it.

---

## 6. The command

Fill the cap deliberately. Do not accept a default on a live run.

```
python -m crucible.conductor.campaign --live \
  --usd-cap <DECIDE> \
  --holdout-expected 0 \
  --out evidence/<run-name>.json
```

Then, and only from the artifact rather than from the banner:

```
python -m crucible.replay evidence/<run-name>.c6.json
```
