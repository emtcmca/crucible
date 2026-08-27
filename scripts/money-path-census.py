#!/usr/bin/env python3
"""money-path-census.py - READ-ONLY census of the money path in an evidence batch.

WHY THIS EXISTS
---------------
All five `CAP_MOVES_MONEY` invariants in `contracts/objective_set.v1.json` have
never fired. Two explanations are possible and they have opposite consequences:

  (a) the target agent is well defended on money, and the clauses correctly
      never fire, or
  (b) the target agent essentially never REACHES a money tool at all, in which
      case the money dimension of the experiment is unobserved rather than
      clean, and the invariants have never been exercised even once.

This script separates them, by counting - per episode - which corpus instance
was drawn, whether that instance declares `CAP_MOVES_MONEY`, and what the agent
actually called. It reads the C6 bundles and the training corpus and writes
nothing.

IT DOES NOT SCORE ANYTHING AND IT IS NOT A GATE. It is a census. Every number it
prints is a count over files named in its own output header, so the reader can
recount any line by hand.

READ-ONLY BY CONSTRUCTION: it opens files for read and prints. No path here is
opened for write, and nothing under `target/`, `contracts/` or `corpus/` is
touched.

USAGE
-----
    python scripts/money-path-census.py [BATCH_DIR]

Default BATCH_DIR is `evidence/batch-night-2026-08-25`.

The current bundle reader refuses the 08-25 batch bundles on schema, so this
reads them with `json.load` directly and touches only fields whose shape it
checks itself.
"""

import collections
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_BATCH = REPO / "evidence" / "batch-night-2026-08-25"
CORPUS = REPO / "corpus" / "training"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from crucible.replay import verdict as _verdict  # noqa: E402

MONEY_TOOLS = ("issue_refund", "issue_store_credit")


def load_corpus_index():
    """slug/instance-id index over `corpus/training/`.

    `instance_id` is imported from `corpus.schema` rather than recomputed, so
    the mapping from a bundle's `attack_id` to a corpus slug uses the SAME
    content address the conductor used. A second implementation of the hash
    here would be a second source of truth for which instance an episode ran.
    """
    sys.path.insert(0, str(REPO))
    from corpus.schema import instance_id  # noqa: E402

    by_id = {}
    for p in sorted(CORPUS.glob("*.json")):
        doc = json.load(open(p, encoding="utf-8"))
        aid = doc.get("_instance_id") or instance_id(doc)
        by_id[aid] = doc
    return by_id


def declares_money(doc):
    return "CAP_MOVES_MONEY" in (doc.get("capability_classes") or ())


def episode_calls(ep):
    """(attempts, executed) as lists of tool names, from `episode_prefix`."""
    attempts, executed = [], []
    for ev in ep.get("episode_prefix") or ():
        if ev.get("kind") == "TOOL_ATTEMPT":
            attempts.append(ev.get("tool_name"))
        elif ev.get("kind") == "TOOL_EXECUTED":
            executed.append(ev.get("tool_name"))
    return attempts, executed


def main(batch_dir):
    bundles = sorted(pathlib.Path(batch_dir).glob("run-*.c6.json"))
    if not bundles:
        print("no run-*.c6.json under %s" % batch_dir)
        return 1
    corpus = load_corpus_index()

    # Ruling 60 part 3. The acceptance count prints ABOVE the first figure, over
    # exactly the bundles this census aggregates. A figure printed without its
    # acceptance count is the failure mode returning.
    _verdict.print_batch_banner(bundles, label="bundle")
    print()

    print("SOURCE FILES")
    print("  bundles      : %d files, %s .. %s"
          % (len(bundles), bundles[0].name, bundles[-1].name))
    print("  bundle dir   : %s" % batch_dir)
    print("  corpus dir   : %s (%d instances)" % (CORPUS, len(corpus)))
    print()

    corpus_money = [d for d in corpus.values() if declares_money(d)]
    print("CORPUS")
    print("  training instances               : %d" % len(corpus))
    print("  declaring CAP_MOVES_MONEY        : %d" % len(corpus_money))
    tools = collections.Counter(d["tool_fqname"].rsplit(".", 1)[-1]
                                for d in corpus_money)
    print("  their scored tool_fqname         : %s" % dict(tools))
    print()

    # -- per-episode census ------------------------------------------------
    n_eps = 0
    money_eps = 0
    money_eps_with_money_attempt = 0
    money_eps_with_money_executed = 0
    money_attempt_tools = collections.Counter()
    money_exec_tools = collections.Counter()
    tool_attempts_in_money_eps = collections.Counter()
    last_tool_in_money_eps = collections.Counter()
    outcomes_money = collections.Counter()
    verdicts_money = collections.Counter()
    verdicts_nonmoney = collections.Counter()
    calls_per_money_ep = collections.Counter()
    invocations_per_money_ep = collections.Counter()
    unmapped_attacks = collections.Counter()
    prov_money_eps = collections.Counter()
    escalate_eps = 0
    escalate_terminal_eps = 0
    money_ep_rows = []   # (bundle, episode_id, slug, last_tool)

    for b in bundles:
        d = json.load(open(b, encoding="utf-8"))
        by_attack = {a["attack_id"]: a for a in d.get("attacks") or ()}
        for ep in d.get("episodes") or ():
            n_eps += 1
            aid = ep.get("attack_id")
            row = by_attack.get(aid) or {}
            cid = row.get("corpus_instance_id") or aid
            doc = corpus.get(cid)
            if doc is None:
                unmapped_attacks[row.get("provenance", "?")] += 1
                continue
            if not declares_money(doc):
                verdicts_nonmoney[(ep.get("verdict") or {}).get("verdict")] += 1
                continue

            money_eps += 1
            prov_money_eps[row.get("provenance")] += 1
            attempts, executed = episode_calls(ep)
            for t in attempts:
                tool_attempts_in_money_eps[t] += 1
            if attempts:
                last_tool_in_money_eps[attempts[-1]] += 1
                money_ep_rows.append((b.name, ep.get("episode_id"),
                                      doc["slug"], attempts[-1]))
            calls_per_money_ep[len(attempts)] += 1
            invocations_per_money_ep[len(
                {ev.get("invocation_id")
                 for ev in ep.get("episode_prefix") or ()})] += 1
            outcomes_money[ep.get("outcome")] += 1
            verdicts_money[(ep.get("verdict") or {}).get("verdict")] += 1

            m_att = [t for t in attempts if t in MONEY_TOOLS]
            m_exe = [t for t in executed if t in MONEY_TOOLS]
            if m_att:
                money_eps_with_money_attempt += 1
                for t in m_att:
                    money_attempt_tools[t] += 1
            if m_exe:
                money_eps_with_money_executed += 1
                for t in m_exe:
                    money_exec_tools[t] += 1
            if "escalate_to_human" in attempts:
                escalate_eps += 1
                if attempts[-1] == "escalate_to_human":
                    escalate_terminal_eps += 1

    print("EPISODES")
    print("  episodes in batch                          : %d" % n_eps)
    print("  unmapped to a corpus instance (by prov)    : %s"
          % dict(unmapped_attacks))
    if unmapped_attacks:
        print("  ^ AN UNMAPPED EPISODE WAS STILL DRAWN. `corpus_hash` moved after")
        print("    this batch ran, so an instance repaired since is content-")
        print("    addressed to a new id and no longer resolves. It is NOT")
        print("    'never drawn' - see UNMAPPED DRAWS below. Counting it as")
        print("    never-drawn is the exact error this line exists to prevent.")
    print("  drew a CAP_MOVES_MONEY instance            : %d" % money_eps)
    print("    by attack provenance                     : %s"
          % dict(prov_money_eps))
    print("  ... in which a money tool was ATTEMPTED    : %d %s"
          % (money_eps_with_money_attempt, dict(money_attempt_tools)))
    print("  ... in which a money tool EXECUTED         : %d %s"
          % (money_eps_with_money_executed, dict(money_exec_tools)))
    print()
    print("  tool ATTEMPTS inside those episodes (all):")
    for t, c in tool_attempts_in_money_eps.most_common():
        print("      %-24s %6d" % (t, c))
    print()
    print("  LAST tool attempted in those episodes:")
    for t, c in last_tool_in_money_eps.most_common():
        print("      %-24s %6d" % (t, c))
    print()
    print("  episodes containing escalate_to_human      : %d" % escalate_eps)
    print("  ... of which escalate was the LAST call    : %d"
          % escalate_terminal_eps)
    print()
    print("  episode `outcome` field                    : %s"
          % dict(outcomes_money))
    print("  verdict, money-attack episodes             : %s"
          % dict(verdicts_money))
    print("  verdict, non-money-attack episodes         : %s"
          % dict(verdicts_nonmoney))
    print("  tool-call count per money episode          : %s"
          % dict(sorted(calls_per_money_ep.items())))
    print("  distinct invocation_ids per money episode  : %s"
          % dict(sorted(invocations_per_money_ep.items())))
    print()

    # -- the band question -------------------------------------------------
    # `refund_policy.md` section 13: T1 authority is $150 per order and $300
    # per account lifetime. The number is READ FROM THE POLICY FILE, not typed
    # here, so a policy edit cannot leave this script quoting a dead band.
    band = read_t1_band()
    print("T1 BAND, read from target/refund_agent/refund_policy.md")
    print("  per-order cap, minor units                 : %s" % band)
    inside = [d for d in corpus_money
              if (d.get("scored_features") or {}).get("amount_minor") is not None
              and d["scored_features"]["amount_minor"] <= band]
    outside = [d for d in corpus_money
               if (d.get("scored_features") or {}).get("amount_minor") is not None
               and d["scored_features"]["amount_minor"] > band]
    print("  money instances at or under the band       : %d" % len(inside))
    for d in sorted(inside, key=lambda x: x["scored_features"]["amount_minor"]):
        print("      %-52s %8d" % (d["slug"], d["scored_features"]["amount_minor"]))
    print("  money instances ABOVE the band             : %d" % len(outside))
    for d in sorted(outside, key=lambda x: x["scored_features"]["amount_minor"]):
        print("      %-52s %8d" % (d["slug"], d["scored_features"]["amount_minor"]))
    print()

    # -- per-slug drill ----------------------------------------------------
    print("PER-SLUG: money instances, episodes drawn and last tool")
    per_slug = collections.defaultdict(collections.Counter)
    for _b, _e, slug, last in money_ep_rows:
        per_slug[slug][last] += 1
    print("  %-52s %6s  %s" % ("slug", "eps", "last-tool histogram"))
    for slug in sorted(per_slug):
        c = per_slug[slug]
        print("  %-52s %6d  %s" % (slug, sum(c.values()), dict(c.most_common())))
    print()

    # -- COVERAGE: which instances the batch never drew at all -------------
    # This is the half a per-episode rate cannot show. An instance drawn zero
    # times contributes zero episodes to every rate computed over the batch,
    # and its absence is invisible in any denominator.
    drawn = collections.Counter()
    for b in bundles:
        d = json.load(open(b, encoding="utf-8"))
        by_attack = {a["attack_id"]: a for a in d.get("attacks") or ()}
        for ep in d.get("episodes") or ():
            row = by_attack.get(ep.get("attack_id")) or {}
            doc = corpus.get(row.get("corpus_instance_id")
                             or ep.get("attack_id"))
            if doc is not None:
                drawn[doc["slug"]] += 1
    all_slugs = {d["slug"] for d in corpus.values()}
    money_slugs = {d["slug"] for d in corpus_money}
    by_slug = {d["slug"]: d for d in corpus.values()}
    print("CORPUS COVERAGE IN THIS BATCH")
    print("  distinct instances drawn at least once     : %d of %d"
          % (len(drawn), len(all_slugs)))
    print("  money instances drawn at least once        : %d of %d"
          % (len(money_slugs & set(drawn)), len(money_slugs)))
    never_money = sorted(money_slugs - set(drawn))
    print("  MONEY instances NEVER drawn                : %d" % len(never_money))
    for s in never_money:
        amt = by_slug[s]["scored_features"]["amount_minor"]
        print("      %-52s %8d %s" % (s, amt,
                                      "<= T1 band" if amt <= band else ""))
    never_other = sorted((all_slugs - money_slugs) - set(drawn))
    print("  non-money instances NEVER drawn            : %d" % len(never_other))
    for s in never_other:
        print("      %s" % s)
    print()

    # -- UNMAPPED DRAWS ----------------------------------------------------
    # An attack the batch DID draw whose `corpus_instance_id` no longer
    # resolves, because the instance was edited after the batch ran and its
    # id is content-addressed. Without this block such a draw is invisible
    # twice over: absent from `drawn`, and therefore reported as an instance
    # that never ran. Printed with what CAN still be read off the bundle.
    print("UNMAPPED DRAWS (drawn, but the instance has moved since)")
    unm = {}
    for b in bundles:
        d = json.load(open(b, encoding="utf-8"))
        by_attack = {a["attack_id"]: a for a in d.get("attacks") or ()}
        for ep in d.get("episodes") or ():
            row = by_attack.get(ep.get("attack_id")) or {}
            cid = row.get("corpus_instance_id") or ep.get("attack_id")
            if cid in corpus:
                continue
            e = unm.setdefault(cid, {"n": 0, "family": row.get("family_id"),
                                     "prov": row.get("provenance"),
                                     "rounds": collections.Counter(),
                                     "calls": collections.Counter(),
                                     "verdicts": collections.Counter(),
                                     "instruction": row.get("instruction")})
            e["n"] += 1
            e["rounds"][ep.get("round_index")] += 1
            e["calls"][len([v for v in ep.get("episode_prefix") or ()
                            if v.get("kind") == "TOOL_ATTEMPT"])] += 1
            e["verdicts"][(ep.get("verdict") or {}).get("verdict")] += 1
    if not unm:
        print("  none - every drawn attack resolves against the current corpus.")
    for cid, e in unm.items():
        print("  episodes=%d  family=%s  provenance=%s" % (e["n"], e["family"],
                                                           e["prov"]))
        print("    rounds   : %s" % dict(e["rounds"]))
        print("    tool calls per episode : %s" % dict(e["calls"]))
        print("    verdicts : %s" % dict(e["verdicts"]))
        print("    final turn: %s" % (e["instruction"] or "")[:150])
        print("    (the id is content-addressed; find the owning file with")
        print("     `git log -- corpus/training/` and recompute at use time)")
    print()
    print("  money instances at/under the band that RAN : %d of %d"
          % (len([d for d in inside if d["slug"] in drawn]), len(inside)))
    for d in sorted(inside, key=lambda x: x["scored_features"]["amount_minor"]):
        print("      %-52s %8d  episodes=%d"
              % (d["slug"], d["scored_features"]["amount_minor"],
                 drawn.get(d["slug"], 0)))
    print()

    # -- EVERY money call in the batch, regardless of the attack's class ----
    # The census above is scoped to episodes that DREW a CAP_MOVES_MONEY
    # instance, which is the question that was asked. It is the wrong scope
    # for "can this agent be made to move money at all": the agent's tool
    # choice is not bounded by the attack's declared class, and a money call
    # inside an episode whose instance declares CAP_READS_PII still proves the
    # agent reaches the tool.
    print("EVERY MONEY CALL IN THE BATCH, ANY ATTACK CLASS")
    rows = []
    for b in bundles:
        d = json.load(open(b, encoding="utf-8"))
        by_attack = {a["attack_id"]: a for a in d.get("attacks") or ()}
        for ep in d.get("episodes") or ():
            row = by_attack.get(ep.get("attack_id")) or {}
            doc = corpus.get(row.get("corpus_instance_id")
                             or ep.get("attack_id"))
            for ev in ep.get("episode_prefix") or ():
                if ev.get("kind") != "TOOL_ATTEMPT":
                    continue
                if ev.get("tool_name") not in MONEY_TOOLS:
                    continue
                rows.append({
                    "bundle": b.name,
                    "episode_id": ep.get("episode_id"),
                    "slug": doc["slug"] if doc else "UNMAPPED",
                    "money_class": bool(doc and declares_money(doc)),
                    "provenance": row.get("provenance"),
                    "tool": ev.get("tool_name"),
                    "decision": ev.get("policy_decision"),
                    "amount_minor": ev["args"].get("amount_minor"),
                    "reason_code": ev["args"].get("reason_code"),
                    "order_id": ev["args"].get("order_id"),
                    "verdict": (ep.get("verdict") or {}).get("verdict"),
                })
    print("  money TOOL_ATTEMPT events, whole batch     : %d" % len(rows))
    print("  distinct episodes containing one           : %d"
          % len({(r["bundle"], r["episode_id"]) for r in rows}))
    print("  distinct episode_ids                       : %d"
          % len({r["episode_id"] for r in rows}))
    print("  by policy_decision                         : %s"
          % dict(collections.Counter(r["decision"] for r in rows)))
    print("  by tool                                    : %s"
          % dict(collections.Counter(r["tool"] for r in rows)))
    print("  in a CAP_MOVES_MONEY-class episode         : %d"
          % sum(1 for r in rows if r["money_class"]))
    print("  in some other class of episode             : %d"
          % sum(1 for r in rows if not r["money_class"]))
    print("  by originating corpus slug                 :")
    for slug, c in collections.Counter(r["slug"] for r in rows).most_common():
        print("      %-52s %6d" % (slug, c))
    print("  amounts requested (minor units), sorted    :")
    amts = sorted(r["amount_minor"] for r in rows
                  if isinstance(r["amount_minor"], int))
    print("      %s" % amts)
    print("      at/under the T1 band (%d): %d of %d"
          % (band, sum(1 for a in amts if a <= band), len(amts)))
    print("  verdict of episodes containing a money call: %s"
          % dict(collections.Counter(r["verdict"] for r in rows)))
    print()

    # -- IS THE BATCH 60 SAMPLES, OR 60 REPETITIONS OF ONE SAMPLE? ---------
    # `crucible/red/red.py:145` seeds the selector's RNG from `seed=`, and
    # `crucible/conductor/campaign.py:186` passes the module constant
    # `RED_SEED`. A constant seed in every process means every run walks the
    # corpus in the same order. This checks that against the bundles rather
    # than inferring it from the code, because the two could have diverged.
    print("DETERMINISM: round-1 draw sequence across the batch")
    seqs = collections.Counter()
    rounds_per_run = collections.Counter()
    for b in bundles:
        d = json.load(open(b, encoding="utf-8"))
        by_attack = {a["attack_id"]: a for a in d.get("attacks") or ()}
        seq, rounds = [], set()
        for ep in d.get("episodes") or ():
            rounds.add(ep.get("round_index"))
            row = by_attack.get(ep.get("attack_id")) or {}
            doc = corpus.get(row.get("corpus_instance_id")
                             or ep.get("attack_id"))
            seq.append(doc["slug"] if doc else "UNMAPPED")
        rounds_per_run[len(rounds)] += 1
        seqs[tuple(seq[:6])] += 1
    print("  rounds per run                             : %s"
          % dict(sorted(rounds_per_run.items())))
    print("  distinct round-1 sequences over %d runs    : %d"
          % (len(bundles), len(seqs)))
    for s, c in seqs.most_common():
        print("      x%-3d %s" % (c, list(s)))
    print()
    print("  A single distinct sequence means the batch is one corpus walk")
    print("  repeated, not %d independent draws. The reachable ceiling is then"
          % len(bundles))
    print("  (max rounds x attacks-per-round) instances, not the corpus size.")
    return 0


def read_t1_band():
    """Parse the T1 per-order dollar cap out of section 13 of the policy.

    Reading it rather than typing it is the point: the policy file is
    hash-locked, and a number copied into this script would be a second source
    of truth for the agent's own authority. Raises rather than defaulting - a
    default would silently classify every instance against a band nobody set.
    """
    import re
    text = (REPO / "target" / "refund_agent" / "refund_policy.md").read_text(
        encoding="utf-8")
    m = re.search(r"T1 - you\s+per order \.+ \$([\d,]+)", text)
    if not m:
        m = re.search(r"T1 — you\s+per order \.+ \$([\d,]+)", text)
    if not m:
        m = re.search(r"per order \.+ \$([\d,]+)", text)
    if not m:
        raise SystemExit(
            "could not read the T1 per-order cap out of refund_policy.md "
            "section 13. Refusing to assume one.")
    return int(m.group(1).replace(",", "")) * 100


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BATCH))
