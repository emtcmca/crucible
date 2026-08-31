# Live-shot footage

Screen recordings you capture yourself. Gitignored - large binaries, not repo
content.

    N6a-gcp-terminal.mp4

## N6a - the Google Cloud proof

    powershell -NoProfile -ExecutionPolicy Bypass -File tools\capture\gcp-proof.ps1 -Pause 2.0

Record the terminal while that runs. Four frames, all read-only:

1. Cloud Run serving, its revision, and its own named service account
2. the enabled APIs - aiplatform, run, storage, logging
3. the three buckets, including the sealed one
4. Gemma's pin in source, and a live-run artifact showing http 200 against
   Vertex Model Garden at `locations/global`

**Set the terminal to 1920x1080 and 18-20pt before you roll.** Default console
text is illegible after YouTube's compression, and an unreadable proof is not
proof.

Run `gcloud auth list` first, off camera, so an auth prompt cannot land in the
take.
