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
      --out "$OUT/run-$n.json" > "$OUT/run-$n.console.txt" 2>&1
  echo $? > "$OUT/run-$n.exitcode"
done
echo "BATCH COMPLETE" > "$OUT/BATCH-DONE"
