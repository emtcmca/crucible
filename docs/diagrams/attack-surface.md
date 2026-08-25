# The attack surface graph — BUILD-LIST T2-1

A **script that renders hashed evidence**, and the render it produced. It is a view over a
frozen input, so it changes no input and writes into no hash-lock. It calls no model, and it
discovers nothing: the graph is read out of artifacts that already exist.

| File | What it is |
|---|---|
| `scripts/render-attack-surface.py` | the deliverable. Takes the bundle directory as a required argument |
| `scripts/render-attack-surface-negcheck.py` | the proof the renderer can fail |
| `docs/diagrams/attack-surface.html` | self-contained page: the figure plus every table behind it. Open it in a browser |
| `docs/diagrams/attack-surface.svg` | the figure alone, for slides and the README |

`evidence/` is gitignored, so the render is committed. A judge with a fresh clone opens the
HTML and sees the picture without running anything.

---

## Regenerate

One command. The bundle directory is a required positional argument — there is no default and
no baked-in path.

```
python scripts/render-attack-surface.py <bundle_dir> \
    --out-svg  docs/diagrams/attack-surface.svg \
    --out-html docs/diagrams/attack-surface.html
```

The render currently committed was produced from `evidence/batch-night-2026-08-25/`.
`--json <path>` additionally dumps the derived graph for a downstream renderer; that dump is
deliberately not committed, because a hash that lives in three files instead of two is three
chances to go stale.

### The committed render is a DEVELOPMENT INPUT and the page says so in red

The batch it was built from measures a corpus that no longer exists. `corpus_hash` moved when
instance F5-05 was repaired and the D5 freeze was re-taken, so those bundles describe a corpus
that is not the current one. **The render that ships must be regenerated from a post-repair
batch.**

That caveat is not typed into the render. It is computed: the renderer reads the corpus hash
out of the bundles, reads the current one out of `docs/proof/d5-corpus-freeze.json`, and prints
the banner when they differ. Point it at a post-repair batch and the banner turns from
`DEVELOPMENT INPUT` to `corpus matches the current freeze record` with no edit to any file.

No hash value is written into this document, into either script, or into any commit message.
Ruling 46 — a frozen hash has exactly one owner, the artifact. The render prints the values it
read at render time; that is a read, not a copy.

---

## What is on the picture, and where each part came from

Nothing is inferred, smoothed, or predicted. `docs/design/T2-8-runtime-visuals-scope.md` §1:
*the visual layer may render only what the event stream carries.* The same rule governs a
static render.

**Nodes** — the frozen capability manifest, read at render time through the manifest's own
loader (`crucible.manifest.load_part_a`), so the manifest hash is read rather than recomputed.

- the tools declared in `target/refund_agent/capability_manifest.json`
- the capability classes at `crucible/manifest/load.py:39-46`
- the `UNCLASSIFIED` sentinel at `crucible/manifest/load.py:47`, drawn because it is part of
  the surface: no rule can select it, so a call landing there is always allowed by the policy

**Edges** — `episodes[].episode_prefix[]` where `kind == TOOL_ATTEMPT`, ordered by `seq`. That
is the tripwire's record of what the target actually **called**, not what it said. The
`episode.*` frozen context is what the rules compare against, and it appears in the rule text
verbatim.

**Colour** — `policy_chain[0]` against `policy_chain[-1]`.

- grey: a class no rule selected, in any run
- blue: governed at `policy@v0` by a seed rule
- **orange: governed for the first time at `policy@vFinal`. The edges that changed are the
  run's result.**

**Approval gates** and **denials** are badged on the tool nodes from
`episode_prefix[].policy_decision` and `denied_by_rule_id`.

### The thing the picture exists to show

That the learned rules are **class-bound rather than string-matched** — the single hardest
thing to convey in four minutes.

The renderer does not assert it. It reads it off the DENY records. A rule carries a
`capability_class` and never a tool name, so the set of tools a rule reaches is a manifest
lookup, and the tripwire shows which tools each rule was actually recorded stopping. Where a
rule denied a tool other than the one the attack used, the figure prints the pair, and the
page's *rules that changed* table adds the column that matters: **every tool the rule reaches
that was never called at all.** A string match would reach exactly one of them.

Two tools in the manifest were never called in the committed development render, and a
class-bound rule still governs both. That is visible in the figure as a dashed hollow node with
a coloured edge running into it.

---

## The negative control

A renderer that draws a plausible picture regardless of its input is a check that cannot fail,
and this project has paid for that shape more than once. The renderer has nine named refusals,
and `render-attack-surface-negcheck.py` fires every one of them.

It copies a slice of a **real** bundle directory into a temp directory, mutates the copy one way
per case, and runs the **shipped** renderer — same file, no test-only mode, no flag that changes
its behaviour. The source directory is never written to.

**Case 0 is the positive control**, and it is the half that is easy to leave out: without it, a
renderer that refused everything would pass every negative case.

```
python scripts/render-attack-surface-negcheck.py <bundle_dir>
```

Real output, 2026-08-25, against `evidence/batch-night-2026-08-25/` (the temp path in the
`empty-dir` case is randomly named per run and is the only line that does not reproduce
verbatim):

```
negative control for scripts/render-attack-surface.py
source: C:\dev\crucible\evidence\batch-night-2026-08-25  (60 bundles available, 4 copied per case)

  intact (POSITIVE CONTROL)    exit 0 (want 0)  PASS
      mutation : nothing mutated
      stdout   : rendered 4 bundles, 114 episodes, 8 tools (2 never called), 28 transitions  [corpus is NOT the current freeze]
      svg      : written
  empty-calls                  exit 2 (want 2)  PASS
      mutation : episode_prefix emptied in every episode of every bundle
      refusal  : REFUSED TO RENDER |   E_NO_CALL_EVENTS |   114 episodes across 4 bundles and not one TOOL_ATTEMPT event - there is no call graph to draw
  unknown-tool                 exit 2 (want 2)  PASS
      mutation : run-01.c6.json: one tool_name renamed to a tool the manifest never declared
      refusal  : REFUSED TO RENDER |   E_UNKNOWN_TOOL |   run-01.c6.json: episode ep_7317dc7d3b15 calls 'wire_funds_offshore', which the frozen manifest does not declare
  cap-drift                    exit 2 (want 2)  PASS
      mutation : run-01.c6.json: one event's capability_classes replaced
      refusal  : REFUSED TO RENDER |   E_EVENT_CAP_DRIFT |   run-01.c6.json: lookup_order recorded as ['CAP_INVOKES_AGENT'], manifest declares ['CAP_READS_PII']
  corpus-split                 exit 2 (want 2)  PASS
      mutation : run-04.c6.json: corpus_hash changed, so the set no longer describes one corpus
      refusal  : REFUSED TO RENDER |   E_CORPUS_HASH_SPLIT |   2 distinct corpus_hash values across 4 bundles; a single render cannot describe two corpora
  unknown-cap                  exit 2 (want 2)  PASS
      mutation : run-01.c6.json: one event carries a capability class outside the frozen set
      refusal  : REFUSED TO RENDER |   E_UNKNOWN_CAP |   run-01.c6.json: lookup_order carries capability class 'CAP_LAUNCHES_MISSILES', not one of the frozen set
  handle-drift                 exit 2 (want 2)  PASS
      mutation : run-01.c6.json: one event's tool_handle no longer matches the manifest
      refusal  : REFUSED TO RENDER |   E_HANDLE_DRIFT |   run-01.c6.json: lookup_order recorded as handle tool:t_00000000, which is not the handle the frozen manifest declares for it (read it from target/refund_agent/capability_manifest.json)
  manifest-drift               exit 2 (want 2)  PASS
      mutation : every bundle's recorded manifest_hash no longer matches the manifest on disk
      refusal  : REFUSED TO RENDER |   E_MANIFEST_DRIFT |   the bundles were measured against a capability manifest that is not the one on disk; the picture would name tools the run never had
  empty-dir                    exit 2 (want 2)  PASS
      mutation : every bundle removed
      refusal  : REFUSED TO RENDER |   E_NO_BUNDLES |   no *.c6.json under C:\Users\tetzl\AppData\Local\Temp\crucible-negcheck-...
  no-policy                    exit 2 (want 2)  PASS
      mutation : run-01.c6.json: policy_chain removed
      refusal  : REFUSED TO RENDER |   E_NO_POLICY_CHAIN |   run-01.c6.json carries no policy_chain

10/10 cases behaved as specified
```

`empty-calls` is the case worth reading twice. Strip every recorded call and a guardless
renderer still draws the manifest half — every tool, every class, every membership edge — and
simply has no arcs. **A graph with no observations in it looks exactly like a graph of a
well-behaved agent.** That is the picture this renderer refuses to draw.

---

## What this render is not

- **It is not a result.** Every number on the page is a count of recorded events over the
  bundles named in its own provenance table. No number on it is a rate. Where a rate is derived
  from this data anywhere else it carries **single-sample, k = 1, no stability estimate**.
- **It is not discovery.** BUILD-LIST T2-1 refuses live or model-driven discovery of the graph.
  There is nothing to discover, deliberately, and swapping a frozen checkable input for a
  probabilistic one in the exact place a silent miss is invisible would trade away the strongest
  thing the project has.
- **It is not an aggregate claim about one run.** The committed development render sums across
  every bundle in the directory. Point it at one bundle to see one run.
