#!/usr/bin/env bash
# Overnight batch runner. Sequential on purpose: Vertex runs on dynamic shared
# quota and the 2026-08-24 batch recorded rate_limit_429 = 0 at this rate.
#
# SINGLE-WRITER LOCK, AND IT IS NOT THEORETICAL. On 2026-08-25 two copies of
# this script ran concurrently against the same output directory: a
# harness-managed background task was REPORTED KILLED and was still alive, and
# a detached relaunch joined it. Both iterated 1..N, both skipped completed
# runs, and both executed the same run number - doubling spend and letting one
# overwrite the other's exit code. Run 10 recorded a RUN_INVALID that a second
# execution then overwrote with a success, erasing the evidence of a real
# failure. No bundle was corrupted and no run_id collided, but that was luck.
#
# A REPORTED STATUS IS NOT EVIDENCE. The lock is held by a live PID, not by the
# existence of a file, so a crashed run does not wedge the directory forever.
OUT="${1:-evidence/batch-night-2026-08-25}"
N="${2:-60}"

# PER-RUN RED SEED, added 2026-08-25, and it is a measurement fix not a tuning.
#
# RED_SEED was a module constant, so every run in a batch drew the same walk.
# Counted over the 60 bundles of evidence/batch-night-2026-08-25/: 26 of the 50
# training instances were EVER drawn and 24 were never attempted once, 15 of
# those being money attacks. Sixty runs was ONE CORPUS WALK REPEATED SIXTY
# TIMES, and every figure computed from it read as sixty samples.
#
# SEED_BASE + run index, deterministically. NOT $RANDOM and not the clock: a
# random seed would trade a coverage defect for a reproducibility defect, and
# this batch has to be re-runnable by a stranger. Each run records its own
# red_seed in the run manifest, so the walk is recoverable per run.
SEED_BASE="${3:-1729}"

# G4 RECORD-ONLY, opt-in via env, added 2026-08-26.
#
# G4 ATTACK REDUCTION defaults to ENFORCING and that default is deliberate: a
# REJECT criterion that is off unless asked for is how G4 sat ABSENT for the
# whole project while contracts/gate_rule.v1.yaml said it was binding.
#
# Set G4_RECORD_ONLY to a REASON STRING to score b and c without enforcing them.
# The reason is required by the flag itself, not by politeness - a suppression
# nobody can name is the thing being guarded against. The banner shouts when it
# is on and the bundle records the mode beside every b/c figure.
G4_FLAG=""
if [ -n "${G4_RECORD_ONLY:-}" ]; then
  G4_FLAG="--g4-record-only"
fi

# G4_SLICE picks the denominator b and c are paired over. Default is the
# campaign's own default (`run`, this run's accumulated episodes). Set it to
# `baseline` to pair against the frozen 50-episode v0 recording, which is the
# only denominator constant across rounds AND across runs - inside a single run
# `n` climbs from 6 to 33, so an early-round candidate and a late one face a
# materially different bar for the same `b >= 3` threshold.
SLICE_FLAG=""
if [ -n "${G4_SLICE:-}" ]; then
  SLICE_FLAG="--g4-slice"
fi
mkdir -p "$OUT"
LOCK="$OUT/RUNNER.lock"

if [ -f "$LOCK" ]; then
  other=$(tr -d '\r\n' < "$LOCK")
  if kill -0 "$other" 2>/dev/null; then
    echo "REFUSING: runner $other is already live on $OUT" >&2
    exit 3
  fi
  echo "stale lock from dead pid $other, taking it" >&2
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT INT TERM

for i in $(seq 1 "$N"); do
  n=$(printf "%02d" "$i")
  [ -f "$OUT/run-$n.exitcode" ] && continue          # resumable
  GOOGLE_GENAI_USE_VERTEXAI=1 GOOGLE_CLOUD_PROJECT=crucible-hack-2026 \
    python -m crucible.conductor.campaign \
      --live --attack-mode hybrid --usd-cap 2.00 --holdout-expected 0 \
      --red-seed "$((SEED_BASE + i))" \
      ${G4_FLAG:+"$G4_FLAG" "$G4_RECORD_ONLY"} \
      ${SLICE_FLAG:+"$SLICE_FLAG" "$G4_SLICE"} \
      --out "$OUT/run-$n.json" > "$OUT/run-$n.console.txt" 2>&1
  echo $? > "$OUT/run-$n.exitcode"
done
echo "BATCH COMPLETE" > "$OUT/BATCH-DONE"
