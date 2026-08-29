# capture/ — Playwright capture harness for the demo video

Records **beat N4, the architecture beat**, as one unbroken take, and then
asserts that the file it produced is actually a usable take.

It records nothing else. Read "What this cannot capture" before planning the
shoot around it.

Spec sources, which own everything this directory merely obeys:

- `docs/design/architecture-animation-spec.md` — the frame, the palette, the
  three rules, and the capture line: *"Playwright drives the page and records.
  Each beat is one unbroken take; cuts fall between beats, never inside one."*
- `docs/design/narration-LOCKED-2026-08-27.md` — the beat list N1–N5 and the
  take convention: *"Two seconds of silence at the head and tail of every take."*
- `docs/diagrams/loop-cues.json` — owns the beat length. This harness reads
  `duration_ms` from it and never hardcodes a beat length.

---

## Quick start

```powershell
cd C:\dev\crucible\capture
npm ci                  # or `npm install` the first time
npm run doctor          # says what is missing, before you are on the clock
npm run selftest        # proves the checks below can actually fail
npm run capture:n4      # records capture/out/N4.webm and verifies it
```

`npm run install-browsers` downloads Chromium and ffmpeg if the doctor says they
are absent. On this machine they were already in the shared Playwright cache, so
nothing was downloaded.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Recorded, and every postcondition was **observed** to pass |
| 1 | Recorded, and a postcondition **failed**. The file is not usable |
| 2 | Never got as far as recording — a precondition was missing |
| 3 | Recorded, nothing failed, but something could **not be measured** |

3 is deliberately not 0. *Not measured* must never read as *passed*.

---

## What is automated

- **Launching and driving the page.** Chromium at 1920x1080, deviceScaleFactor
  2, animations allowed to run, `reducedMotion` pinned to `no-preference` so a
  machine with "reduce motion" enabled cannot silently record a still frame.
- **Determinism before the first frame.** Smooth scrolling and the text caret
  are killed by an init script; `document.fonts.ready` is awaited; then the page
  is screenshotted repeatedly until two consecutive frames are byte-identical.
  That last step is measured, not assumed — see "Things this harness learned the
  hard way" below.
- **The take itself.** `seek(0)`, a 2-second held frame, `play()`, the full beat
  with no pause and no seek, a 2-second held frame, stop. `state()` is polled
  once a second but **only as an observation** — it can never shorten the take,
  because the cue list owns the beat length and cutting on a player's say-so is
  how a take ends mid-sentence.
- **Verification of the artifact.** Eight checks, listed below.
- **Preflight.** `npm run doctor` — nine numbered checks, each reporting what it
  observed, with the fix for anything missing.
- **A selftest that proves the verifier can fail.** `npm run selftest` —
  21 expectations across eight cases.
- **An observation record.** `out/N4.take.json` beside the video: every mark,
  every `state()` sample, every page error, and every check result.

## What is NOT automated

- **Audio.** Nothing here records, times, or syncs narration. The beat length
  comes from `loop-cues.json`, which is supposed to have been cued to Eric's
  recorded take. If that file is absent the capture falls back to the spec's
  45,000 ms estimate and says loudly that it did.
- **Editing.** No trimming, no re-encoding, no concatenation, no titles. The
  file contains browser preamble before the head pad; the script prints the
  exact millisecond offsets to cut at and deliberately does not re-encode the
  file to hide it.
- **The page being correct.** The harness checks that frames are not blank and
  that they change. It has no idea whether the right node lit at the right
  moment, whether the blindness beat fired, or whether the trust boundary
  resolved. **`scripts/check-loop-cues.py` and a human watching the take are
  what cover that.** A green run here means "a real animated 1920x1080 video of
  that page exists", not "the animation is right".
- **Beats N1, N2, N3, and N5.** See below.
- **Uploading, publishing, or naming anything.**

## What a human still has to do

1. Record the narration; `docs/design/narration-LOCKED-2026-08-27.md` is the
   script. 60 seconds of room tone first, one take per chunk, 2 seconds of
   silence head and tail.
2. Cue `docs/diagrams/loop-cues.json` to that recording — real timings, not the
   spec's estimates — and run `scripts/check-loop-cues.py`.
3. Re-verify the three on-camera source claims in N4. The narration script says
   *"Re-verify before recording; do not recall."* This harness does not check
   claims.
4. Run `npm run capture:n4` and **watch the resulting file**. Every check here
   can pass on an animation that is wrong.
5. Screen-record N1, N2, and N3 by hand (below).
6. Cut the beats together, lay the narration under them, and cut only between
   beats.

---

## What this cannot capture, and why

**N1, N2 and N3 are not web pages, and Playwright cannot record them.** This is
the honest answer, not a limitation to be worked around.

| Beat | On screen | Capturable here? |
|---|---|---|
| **N1** | "refund agent UI" with a tool-call trace | **No.** There is no web UI in this repo. The target agent is Python — `target/refund_agent/`. Whatever N1 shows is a console session or a UI that does not exist yet. |
| **N2** | `sqlite3 ledger.db "select order_id, amount_minor, ts ..."` typed live, then a $900 escalation | **No.** That is a native terminal against the sqlite file `target/refund_agent/simulated_system_of_record.py` writes. Playwright drives a browser; it has no access to a terminal window. |
| **N3** | one slide — *find the breach · patch it · prove the patch didn't break the business* | **Not today, but it could be.** No slide file exists. If the slide is authored as an HTML page, this harness can record it: `node capture-n4.mjs --out=N3.webm` is close, but it requires a cue hook, so a static slide would want a small variant that passes `requireHook: false` to `recordTake()`. |
| **N4** | the architecture diagram | **Yes. This is the beat the harness is for.** |
| **N5** | the honesty beat, spoken over the diagram | **Partly.** If it is spoken over the N4 diagram it needs no new capture; if it needs its own visual, that visual does not exist yet. |

**Use a screen recorder (OBS, or Windows Game Bar) for N1 and N2.** Match the
1920x1080 frame and the 2-second head and tail pads so the beats cut together.

**Do not fake the terminal in a browser to make it capturable here.** A web
terminal emulator would technically let Playwright record N1 and N2, and it
would misrepresent a real command against a real ledger as a rendered page.
N2's whole point is *"That's not a mock response. The ledger moved."*

---

## The eight postconditions

Every check reports what it **observed**. This exists because the project's
signature recurring defect — twelve recorded instances — is a check that passes
while measuring nothing, and in this medium that defect is a script exiting 0
after producing a zero-byte or black video.

| ID | Checks | Catches |
|---|---|---|
| V1 | the file exists and is a regular file | nothing was written |
| V2 | size above a 4 KB floor | a zero-byte or header-only stub |
| V3 | EBML magic `1A 45 DF A3` at offset 0 | a truncated or half-written file |
| V4 | at least 2 Matroska Cluster elements | a container with no media payload |
| V5 | decoded duration matches the wall clock the script measured, ±2 s | a recorder that stopped early or ran long |
| V8 | footage ≥ head pad + beat + tail pad | **a cut inside the beat** |
| V6 | not every sampled frame is a flat colour field | **a valid video of a page that never rendered** |
| V7 | consecutive sampled frames differ | **a valid video that is frozen** |

V5 measures duration by decoding the whole file, not by reading the container's
`Duration:` header, because a screencast webm's declared duration is frequently
absent or wrong. V6 and V7 sample frames at 2 fps, downscale to 64x36
greyscale, and read the pixels.

**V6 and V7 analyse from the cut-in point, not from byte zero.** The frames
before the head pad are browser preamble and are trimmed in the edit; judging
the deliverable on footage nobody will ship would be the wrong measurement in
either direction. V5 and V8 always use the whole file.

**Anything that cannot be measured reports UNVERIFIED and exits 3.** With no
ffmpeg present, V5–V8 all report UNVERIFIED, and the selftest refuses to return
a pass because in that state the harness genuinely cannot detect a well-formed
video of nothing.

## The selftest is the point, not a nicety

Same reasoning as the eval harness shipping known-bad fixtures and as
`canon-check --selftest`: a check that cannot fail is not measuring anything.

`npm run selftest` drives **`lib/take.mjs`, the production recording path** —
not a private copy of it — against artifacts whose verdict is known in advance:

- **A** no file → V1 must FAIL
- **B** a zero-byte file → V2 must FAIL
- **C** 64 KB of random bytes → V2 must PASS, V3 must FAIL
- **D** `fixtures/known-bad-blank.html`: a page that loads, exposes a complete
  `__cuePlayer`, records a **valid 19 KB WebM of the correct length**, and
  renders nothing. **V6 and V7 must FAIL.** This is the artifact a naive harness
  reports as a success. It also asserts the first frame's mean luma lands above
  250, which is an independent oracle on the hand-rolled PNG reader.
- **E** `fixtures/known-good-motion.html`: a page that really renders and moves.
  **Every check must PASS.** A verifier that always fails is as useless as one
  that always passes.
- **F** the same good file judged against a 60 s longer window → V8 must FAIL
- **G** a missing page → `TARGET_MISSING`, and the message must name the owner
- **H** a page with no hook → `HOOK_MISSING`, and the message must state both
  what was found and the required interface

Observed on 2026-08-29: **21 expectations, 0 not met.**

---

## The interface this harness expects

The recorded page must expose:

```js
window.__cuePlayer = { play(), seek(ms), state() }
```

All three as functions. `state()` is treated as opaque — it is logged into
`out/N4.take.json` and never branched on — so the player is free to return
whatever it finds useful.

**This harness does not create `docs/diagrams/loop-player.html`.** That page and
its cue list belong to the loop-player work. If either is missing, `npm run
doctor` says so by name and `npm run capture:n4` exits 2 with the required
interface printed.

## Layout

```
capture/
  package.json          pinned playwright 1.60.0, exact, no carets
  capture.config.mjs    every knob: frame, pads, tolerances, launch args, exit codes
  capture-n4.mjs        the N4 beat: record, verify, write the observation record
  verify.mjs            re-check an existing file without re-recording it
  doctor.mjs            preflight, nine numbered checks
  selftest.mjs          proves the verifier can fail
  fixtures/
    known-bad-blank.html    must always be rejected
    known-good-motion.html  must always be accepted
  lib/
    take.mjs           the production recording path
    verify-video.mjs   the eight postconditions
    ffmpeg.mjs         locates the ffmpeg Playwright ships
    png-gray.mjs       zero-dependency 8-bit greyscale PNG reader
  out/                 recorded takes (gitignored)
```

There is **no `playwright.config.ts`**. That file is read by the `playwright
test` runner and nothing here runs under it — a capture is a scripted take, not
a test. A config file that nothing reads is a setting that cannot fail.
`capture.config.mjs` is imported by every script that uses it.

## Things this harness learned the hard way

Kept because each one was a real defect found by running the thing, and each
would come back if the reason were deleted.

1. **The Playwright ffmpeg is a stripped build.** Two muxers (image2, webm), two
   encoders (png, libvpx), and a filter list with no `fps` and no rawvideo
   muxer. The usual "pipe raw RGB out of ffmpeg" approach silently produced zero
   frames — and the first version of the verifier reported "zero frames decoded"
   as a **FAIL on a video that plainly had frames in it**. Sampling now uses the
   `-r` output option and PNG, which is why `lib/png-gray.mjs` exists.
2. **The size floor was wrong in the direction that rejects good takes.** It was
   set at 20 KB by guess; a measured 9-second recording of a **blank white page**
   came out at 19,343 bytes. The floor is now 4 KB and its job is only to catch
   stubs. Size is not evidence of content.
3. **`context.close()` was being counted as footage.** Closing the context is
   what flushes the webm, and on a 3.6 MB take that costs ~1.4 s. Timing the
   close as recording put a systematic ~1.8 s bias into the duration
   expectation. It still "passed" — with 90% of the tolerance spent on the bias.
   The end of the recorded window is now marked before the close, and V5 came in
   at 150 ms off instead of 1,798 ms.
4. **`load` + `fonts.ready` + two animation frames is not "settled".** The first
   real take opened on a white unpainted frame. The verifier caught it as *1 of
   100 sampled frames was a flat colour field, mean luma 254 where every other
   frame was 26*. The settle is now measured by screenshot comparison.

Numbers 2, 3 and 4 were all found by checks in this directory failing or
reporting an odd measurement. That is the intended behaviour, and it is the
reason the selftest exists.
