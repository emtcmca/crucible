# RED discovery — authoring an attack the corpus does not hold

**Status, as of 2026-08-23: THIS IS A DESIGN. NOTHING IN THE TREE IMPLEMENTS IT.**
`crucible/red/red.py` has no path that authors an attack, `AttackSeed` is
constructed in exactly one place (`CorpusSeeds.attack_seeds()`), and
`ATTACK_MODES` is `("corpus", "generated", "hybrid")` with no fourth value.
`attack_mode` admits no `discovery` and neither `provenance` enum admits
`red_authored`, deliberately — ruling 51 states why: a contract that admits a
value no code path emits is a contract making a claim the implementation cannot
back, and on a judged submission it reads as a shipped capability.

**Written because ruling 51 does NOT address it, and the two are easy to
confuse.** Ruling 51 makes a run declare *which of three populations it attacked
with*. All three are the frozen corpus. Discovery adds a **fourth population
that is not under `corpus_hash` at all**, and that is a different kind of change:
a labelling change on the run of record versus a new capability with its own
seal, blindness and denominator consequences.

---

## 1. What "discovery" has to mean here, and what `generated` already is

`generated` mode hands the model one string and asks for one string back, under
a system prompt that says *pursue the SAME objective by the SAME sequence of
actions.* `vary()` preserves the seed's `attack_id` and `family_id` on all four
of its paths and rewrites only `instruction`. It varies **whether a capability
path survives a rephrasing** — a real question, and a different one from the
verbatim run — but it explores **no objective the corpus does not already hold.**

Discovery means RED proposes an objective, an action sequence, and **a world for
them to happen in.** The third is the part every naive version of this drops.

### The failure a payload-only spec walks into

`docs/architecture-spec.md` §1.1 already describes RED's output as
`AttackSpec[] — {attack_id, family, target_capability_class, delivery_vector,
payload_text, expected_tool_handle?}`. **That shape cannot be scored**, for two
independent reasons, and both are already paid for elsewhere in this repo:

1. **It mints its own `attack_id`.** `corpus/schema.py` refuses an
   author-supplied `instance_id` rather than checking one, because *a checked
   copy of a derived value is still a second copy*, and CONVENTIONS 2.6 is the
   general rule: never ask a model — or a person — to perform a deterministic
   computation. The Armorer already lives under this rule; it emits the
   placeholder `r_new1` and the validator rewrites it.
2. **It has no world.** An episode runs against an order/account record.
   `CorpusSeeds.world_for` builds one per instance from the instance's own
   `scenario` and refuses to fall back to a shared one — the comment names the
   ORD-4471/ORD-4472 collision that rule exists to close. A payload with no
   scenario has nothing to act on, so the target either invents a record or
   errors, and either way the episode measured nothing.

The second failure is not hypothetical. Two corpus instances, `F2-02` and
`F2-08`, declare a successful `lookup_customer(customer_id='CUS-9142')` while
their own scenarios state no record for that account. They are the
`unpresentable_instances` the harness has reported since 2026-08-22, and they
are two of the five episodes live run 2 lost on 2026-08-23. **A payload-only
discovery spec makes that shape the norm rather than the exception**, because
nothing would be authoring the record the payload refers to.

---

## 2. The split: what RED authors, what code derives, what nobody writes

This is the whole design. Everything else follows from the table.

| field | who | why not the other party |
|---|---|---|
| `objective` | **RED** | one sentence, what the attacker wants the agent to do that exceeds its authority. This is the thing being discovered. |
| `target_capability_class` | **RED** | SCALAR, one of the six. RED already selects against a class today. |
| `tool_fqname` | **RED** | must be a tool the capability manifest DECLARES; refused otherwise. |
| `scenario` | **RED** | the order/account/case record the episode runs in. **This is the half that makes it scoreable and the half a payload-only spec omits.** |
| `turns[]` | **RED** | the user turns in order; the last asks for the forbidden thing. |
| `expected_tool_call` | **RED** | `{tool_handle, args}` the attack is trying to induce. Recorded as the attack's own claim, never as a verdict. |
| `attack_id` | **CODE** | content-addressed, `atk_ + sha256(canonical(body))[:12]`, the SAME derivation `corpus/schema.py::instance_id` uses. So two spellings of one discovered attack collapse rather than seeding the population twice, and RED cannot number its own findings. |
| `family_id` | **CODE** | matched against the seven existing families on `(class, tool, induced-call shape)`; unmatched becomes `fam_discovered`. RED naming its own family would let it declare novelty. |
| `scored_features` | **CODE, derived from the trace** | **the most important row in this table. See §5.** |
| `sealed` | **NOBODY — always `false`** | RED holds no write path to the seal and must not be able to claim one. |
| `episode.*` | **NOBODY** | frozen at episode start from the scenario, unwritable after — ruling 16, and the whole F4 seal. |
| `derived.*` | **NOBODY** | stamped by the plugin in `before_tool`, overwriting anything under that prefix — ruling 21. |
| any verdict, any policy reference | **NOBODY** | RED is blind to both and authoring does not change what it sees. |

### The output contract

`docs/design/red-discovery-attack-spec.schema.json` is the draft, deliberately
NOT under `contracts/` and NOT in `contracts/MANIFEST.json`. It becomes C11 when
something implements it, and that is the second C6 hash move — correct, because
discovery genuinely changes what a bundle means.

---

## 3. Build or refuse a world — and refusal is terminal, counted, and published

The pipeline already exists and is used on every corpus attack today:
`build_sor(doc)` → `verify_world(doc, sor)` → `unpresentable_entities(doc, sor)`.
Discovery runs an authored scenario through the **same** three calls. What
changes is that **an unpresentable entity becomes a pre-flight REFUSAL rather
than an in-flight flag.**

On a corpus instance, `unpresentable` rides into the episode and the episode ends
`harness_error` — acceptable for two known instances a human has ruled on. On an
authored instance it must be caught before a target call is spent, because the
model can produce them at volume.

### The refusal taxonomy — every code costs zero target calls

| code | fires when |
|---|---|
| `E_UNDECLARED_TOOL` | names a tool capability manifest Part A does not declare |
| `E_UNCLASSIFIED_TARGET` | targets a tool whose class set is `UNCLASSIFIED` or empty. **Unpoliceable by construction:** no rule may select `UNCLASSIFIED` (C4 V2), the empty set means INERT, and the engine fails open on both deliberately. An attack aimed there can only ever succeed. |
| `E_UNPRESENTABLE_ENTITY` | the trace names an order/account/case the authored scenario does not state — the `F2-02` shape, made terminal |
| `E_SCENARIO_CONTRADICTS_ITSELF` | `verify_world` refuses the authored world |
| `E_NO_SCORED_CALL` | no turn induces a tool call, so there is nothing to score |
| `E_DUPLICATE_OF_CORPUS` | the content hash equals an existing training instance. **Not a failure — a REDISCOVERY, counted separately**, and a genuinely interesting number. |
| `E_AUTHORED_FROZEN_FIELD` | emitted `instance_id`, `sealed`, or anything under `episode.*` / `derived.*` |

**THE YIELD IS `admitted / authored`, PUBLISHED WITH THE FULL REFUSAL BREAKDOWN,
NEVER AS A BARE ADMITTED COUNT.** "The model authored 40 attacks and 31 were
incoherent" is itself the finding. Reporting only the 9 would be the same defect
as a breach rate over an unknown fraction of the definition of breach.

---

## 4. Discovered attacks are SCORED-ONLY by default, and the toggle is declared

**The single most attackable thing a judge could find in a discovery build**: RED
authors an attack, the Armorer patches against it, and the two models are now in
a conversation the corpus does not bound. Ten rounds of that and the hardening
curve is a record of two models converging, with no external population holding
either of them to anything.

So the default is a **measurement arm, not a training arm**: discovered attacks
are put to the target and scored by the frozen tripwire, and their breach records
**do not reach the Armorer**. Feeding them is a separate declared run parameter,
off by default, and a run that turns it on says so on the run of record beside
the mode.

### The three-population rule, which is stronger than the provenance one

`corpus` and `generated` both resolve to instances under `corpus_hash`.
**A discovered attack resolves to nothing frozen.** Therefore:

> **No figure computed over a population containing discovered attacks may be
> quoted as a corpus-backed figure.** The arms are reported separately, always,
> and the pooled row — if shown at all — is labelled and placed beside the split,
> never instead of it.

This is the same doctrine as `provenance_breakout`, one level up. The existing
rule keeps two arms of one frozen population apart; this one keeps a frozen
population apart from an unfrozen one.

---

## 5. Why code derives `scored_features`, and not RED

`scored_features` are *the structured facts a pair is separated on*. The D5
blindness check measures whether `derived.*` leaks the attack/benign label, and
its own result is a claim about the corpus: **0.7400 against a 0.7400 baseline
over 100 instances including the sealed set, PASS, no leaking fields**
`[V 2026-08-23, docs/proof/d5-derived-schema-freeze.json]`.

If RED authored both the attack and the features its separation is computed on,
that check becomes unfalsifiable for the discovered population — the same party
writes the exam and the answer key. So the features are **stamped by code from
the authored trace**, exactly as `derived.*` is stamped by the plugin, and for
the same reason.

### The property discovery MUST NOT touch, and does not

**RED authors the attack. RED does not author what counts as a breach.** A
discovered attack is scored by the same frozen Objective Set at
`objective_set_hash`, through the same pure-code tripwire. If a discovered attack
targets a capability path no clause covers, the verdict is CLEAN **and that is
the correct answer** — the clause-coverage table will show the clause was never
reached, which is the honest reading. A discovery capability that could also move
the definition of breach would be able to manufacture its own success, and there
would be no instrument left in the build.

---

## 6. The seal, and the one check RED must never be able to run

RED cannot read `corpus/sealed/` — that boundary is IAM, not `.gitignore`: the
sealed family lives under a service account the run identity holds no read
binding on. Authoring does not change that. But it creates a question that did
not exist before:

**an authored attack could independently reproduce a sealed-family attack.**

That is not a leak. It does mean a discovered instance duplicating a sealed one
would make the holdout look partly pre-seen, and the transfer number is the
headline. The check is a content-hash comparison of discovered instances against
sealed instances — and it **must run offline, after the run, by a party that can
read both, reporting a count and nothing else.** RED never learns the answer,
because a RED that could ask "is this one sealed?" has a sealed-family oracle
built out of yes/no questions.

---

## 7. Cost, model tier, and the honest objection to all of it

Authoring a scenario plus a turn sequence is a materially larger ask than
rewriting one string. Today RED is `gemini-3.6-flash` at `thinking_level: low`,
which is the right tier for rephrasing and probably not for this. The refusal
taxonomy in §3 is what makes the tier question empirical rather than a guess:
**run it, publish `admitted / authored` with the breakdown, and let the refusal
mix say whether the tier is wrong.** A high `E_UNPRESENTABLE_ENTITY` rate is a
model that cannot hold a world together; a high `E_DUPLICATE_OF_CORPUS` rate is a
model that is not discovering anything.

**The objection worth stating out loud:** discovery is the most impressive-sounding
capability in this document and the least load-bearing for the claim CRUCIBLE
actually makes. The claim is that a policy learned from breaches on a training
population transfers to a sealed holdout the Armorer never saw, measured by an
instrument that is not the thing being measured. **That claim is complete without
discovery.** Discovery widens the training population; it does not strengthen the
separation, and if it is wired into the Armorer it weakens it.

Build it because a fixed corpus is a ceiling on what the harness can find, not
because it makes the demo better.
