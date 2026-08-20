# Canonicalization — C7, part 2 of 2

**Contract. Frozen at the W0 hash. Lanes read this; no lane edits it.**

Every hash claim in CRUCIBLE collapses if this is wrong, and **a subtly wrong canonicalizer
produces green checkmarks over meaningless comparisons** — which is worse than a red one. This
file is the normative statement; `data-spec.md` §2.2 is its narrative source.

---

## 1. The rules

Follow **RFC 8785 (JCS)** with seven project restrictions, each of which removes a part that is
easy to get wrong rather than adding cleverness.

| # | Rule | Why it is not merely a preference |
|---|---|---|
| 1 | **UTF-8, no BOM.** All strings and keys Unicode **NFC**-normalized before serialization | A BOM changes the bytes and therefore the hash. On Windows this is a live hazard, not a theoretical one |
| 2 | **Key order ascending by UTF-16 code unit** — the JCS rule, *not* byte order | They differ above the BMP. **Use a JCS library; never `sorted()` on raw bytes.** A corpus containing one emoji key would silently diverge |
| 3 | **No whitespace.** Single line, no trailing newline | |
| 4 | **Integers only.** Floats are forbidden anywhere in a hashed payload | Dodges JCS's ECMAScript number-serialization rules entirely. Money is integer **minor units** plus an ISO-4217 `currency` string. Confidences and rates live **outside** the hashed payload |
| 5 | **`null` is forbidden. An absent fact is an absent key** | See §2 — this interacts with a ruled decision and the interaction is resolved there |
| 6 | **Arrays pre-sorted at construction:** `rules` by `rule_id`; `capability_classes` by value; `arg_conditions` by `path` then `op` | Precedence is by **verb**, never by array position, so order carries no semantics and sorting is lossless. Sorting once at construction — not at hash time — is what makes the canonical form unambiguous |
| 7 | **Booleans lowercase** | |

```
policy_hash_full = hex(SHA256(jcs_canonical_utf8(hashed_payload)))   # run_id NOT inside
policy_hash      = policy_hash_full[0:16]
rule_id          = "r_" + hex(SHA256(jcs_canonical_utf8(rule_without_rule_id)))[0:12]
```

`rule_id` is content-derived, so the same semantic rule always gets the same ID and `add_rule` of
an existing rule is **detectably a no-op** — the per-rule half of the convergence detector.

> **The ARMORER never writes a `rule_id`.** A model cannot compute SHA-256. It emits the
> placeholder `r_new1`, `r_new2`, …; the validator canonicalizes the body, computes the hash, and
> rewrites the placeholder. **A patch in which the model emitted a hash-shaped ID on `add_rule` is
> rejected.** `CONVENTIONS.md` §2.6.

---

## 2. `null` vs. the required-approver field — resolved 2026-08-20

**Two ruled decisions collided here, and the collision was found while authoring this contract.**

- Rule 5 above: *"`null` is forbidden. An absent fact is an absent key."*
- `CONVENTIONS.md` §5.7 ruling 23, addition 4: *"the approver field is REQUIRED on every corpus
  instance and must be explicitly `null` when none is declared. Absent is a validation error, not
  a default."*

Both are right about what they are protecting. Ruling 23 is protecting a real failure: **"no
approver declared" and "the corpus author forgot" are otherwise the same bytes**, and a forgotten
approver silently flips a pair from policy-separated to oracle-denied, which makes the SEP-BY
split ruling 17 mandates print a wrong number. Rule 5 is protecting the canonical form, and the
corpus **is** hash-locked at D5, so it canonicalizes through this same canonicalizer.

**Resolution — a sentinel, not `null`:**

```jsonc
"approver": "NONE"                              // declared: this instance has no approver
"approver": { "id": "sup_0413", "tier": "T3" }  // declared: this approver
// key absent                                   // VALIDATION ERROR, not a default
```

**This preserves both intents exactly.** Presence stays mandatory, so the two states ruling 23
cares about remain distinguishable; and `null` never enters a hashed payload, so rule 5 holds
unweakened. It is the same shape as `UNCLASSIFIED` being **distinct from the empty set** in
`CONVENTIONS.md` §2.2 — *we know there is none* and *we do not know* are different facts and must
not share an encoding.

> **Neither rule was weakened to fit the other**, which matters: `CONVENTIONS.md` §8 rule 3 says
> weakening a check is a stop condition, not a repair.

---

## 3. Golden vectors — the highest-leverage test file in the project

**≥12 fixtures, hand-authored, committed at `contracts/golden/canonicalization/`.** L1 writes the
canonicalizer against these and they are frozen with this contract.

Required coverage, each present because it is a way to be subtly wrong:

| # | Fixture | Fails if |
|---|---|---|
| 1 | Key-order permutations of one object | Two orderings must produce **identical** hashes. This is the whole point |
| 2 | Non-BMP key (e.g. an emoji) | Byte-order sorting diverges from UTF-16 code-unit order here and nowhere else |
| 3 | NFC vs. NFD forms of the same string | Must normalize to one hash |
| 4 | Nested arrays, depth ≥3 | |
| 5 | Empty array `[]` and empty object `{}` | Must be distinguishable and stable |
| 6 | Large integer beyond 2^53 | The float trap. Must survive exactly |
| 7 | Integer `0`, negative integer | |
| 8 | Booleans, both values | |
| 9 | A string containing `"`, `\`, and a control character | JCS escaping |
| 10 | A payload with a BOM prepended | Must be **rejected**, not silently stripped |
| 11 | A payload containing a float | Must be **rejected** |
| 12 | A payload containing `null` | Must be **rejected** |

**Fixtures 10, 11, and 12 are the negative half and they are not optional.** §8 rule 2: a check
that cannot fail is not measuring anything. A canonicalizer that silently strips a BOM or coerces
a float will pass all nine positive vectors and be wrong in production.

---

## 4. What canonicalization applies to

| Artifact | Canonicalized before hashing? | Notes |
|---|---|---|
| Policy `hashed_payload` | **Yes**, JCS | `run_id` is deliberately outside it — it made the same policy hash differently in two runs, which breaks convergence-by-hash-equality and the resume key |
| A rule body, for `rule_id` | **Yes**, JCS, with `rule_id` itself removed first | |
| Corpus artifacts | **Yes**, JCS | Which is why §2 above matters |
| Objective Set | **Yes**, JCS | `objective_set_hash`. It is the definition of breach and was the only unfrozen input to the `OBJECTIVE_EVALUATOR` |
| Capability manifest Part A / `derived_schema` Part B | **Yes**, JCS | Two artifacts, two hashes, two freeze dates — ruling 20 |
| **The contract files in this directory** | **No — see below** | |

**Contract files are hashed as bytes, not as JCS.** Three of the nine contracts are not JSON at
all (`policy.ebnf`, `gate_rule.v1.yaml`, this file), so a JSON canonicalizer cannot be the common
form. The normalization applied before hashing a contract file is therefore textual and minimal:

1. Line endings normalized to **LF**
2. Trailing whitespace stripped from every line
3. Exactly one trailing newline at end of file
4. UTF-8, no BOM

`contracts/MANIFEST.json` records the SHA-256 of each contract file **after** that normalization.
**This is a different operation from JCS and the distinction is deliberate** — conflating them is
how a manifest hash starts disagreeing with a policy hash for reasons nobody can reproduce.
