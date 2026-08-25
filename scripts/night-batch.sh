#!/usr/bin/env bash
# Overnight batch runner. Sequential on purpose: Vertex runs on dynamic shared
# quota and tonight's 10-run batch recorded rate_limit_429 = 0 at this rate.
# Writes the REAL exit code to a file per run, because exit codes have lied
# five times on this project and a notification is not evidence.
OUT="${1:-evidence/batch-night-2026-08-25}"
N="${2:-60}"
mkdir -p "$OUT"
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
