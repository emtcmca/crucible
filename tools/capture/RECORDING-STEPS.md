# Screen-recording the live Google Cloud proof (N6a)

**Why bother, when the rendered version already exists.** A screen recording of
a real shell is the least arguable form of the contest's *"visible proof your
backend runs on Google Cloud"*. The rendered transcript at
`cards/12-gcp-terminal.html` is real output and says so on screen, but it is a
rendering. If you have five minutes, shoot this. If you do not, ship the
rendered one and lose nothing that matters.

**Everything below is read-only.** `list` and `describe` create nothing, bind
nothing, delete nothing. No command touches `gs://crucible-sealed-x7`.

---

## 1. Before you start recording

**1.0 — COMMIT OR STASH FIRST.** The seal proof in the second script refuses on
a dirty working tree, on purpose, so one uncommitted file anywhere in the repo
puts a red **VERDICT FAIL** on camera. It happened on this script's very first
run.

```powershell
git status --porcelain     # must print nothing
```

**1.1 — Authenticate off camera**, so no auth prompt can land inside the take:

```powershell
gcloud auth list
```

You should see `eric@erictetzlaff.com` marked active. If not, `gcloud auth login`
and finish it **before** you roll.

**1.2 — Open Windows Terminal and make it big.**

Settings (`Ctrl+,`) → your PowerShell profile → **Appearance**:

| setting | value | why |
|---|---|---|
| Font size | **18–20** | default console text turns to mush after YouTube's compression, and a proof nobody can read is not a proof |
| Color scheme | **One Half Dark** or **Campbell** | dark, so it cuts against the rest of the video without a flash |
| Cursor shape | filled box | reads as a terminal at a glance |

Then maximise the window. If your display is 1080p, maximised is 1920×1080 and
you are done. On a larger display, maximised is fine too — the assembler scales
and pads to 1920×1080 either way.

**1.3 — Get the taskbar and everything else out of the frame.**

| do this | why |
|---|---|
| **`F11`** (or `Alt+Enter`) — full screen | **this is the taskbar answer.** Full screen covers it entirely, no settings change needed |
| **`Ctrl+Shift+P`** → *Toggle focus mode* | hides the tab bar and title bar too, so the frame is nothing but terminal |
| **`Win+N`** → Do Not Disturb **on** | a notification toast landing mid-take costs you the whole take |

If you would rather not go full screen, the settings route is Settings →
Personalization → Taskbar → **Taskbar behaviors → Automatically hide the
taskbar**. Full screen is faster and does not leave your desktop changed
afterwards.

**1.4 — Clear the scrollback** so the take opens on a clean frame:

```powershell
Clear-Host
```

**1.5 — Change into the repo** (do this before recording, so the take does not
open on a `cd`):

```powershell
cd C:\dev\crucible
```

---

## 2. Record

**Xbox Game Bar is already installed on Windows 11 and is the shortest path.**

1. With Windows Terminal focused, press **`Win + G`**.
2. In the **Capture** widget, press the record button — or skip the overlay
   entirely and press **`Win + Alt + R`**, which starts recording the focused
   window directly.
3. A small timer appears. **Wait two seconds** before you type anything: the
   assembler needs a clean head, and a take that opens mid-keystroke cannot be
   trimmed cleanly.
4. Paste and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\capture\gcp-proof.ps1 -Pause 2.0
```

5. Let it finish. It types each command for the camera and prints real output —
   about 30 seconds at `-Pause 2.0`. **Do not touch the keyboard while it runs.**
   The last frame makes a **live Gemma call** and waits ~2s for the response, so
   do not mistake that pause for a hang.
6. **Wait two seconds** after the last line, then press **`Win + Alt + R`** again
   to stop.

Game Bar writes to `C:\Users\tetzl\Videos\Captures\` as an MP4.

**If Game Bar refuses** — it declines to record some window types — use OBS
Studio: Sources → **Window Capture** → the Windows Terminal window; Settings →
Output → Recording Format **mp4**; Start Recording.

---

## 3. Put it in the video

```powershell
copy "C:\Users\tetzl\Videos\Captures\<the file>.mp4" C:\dev\crucible\video\N6a-gcp-terminal.mp4
```

Then point the beat at it — one edit in `tools/capture/beats.json`, the `N6a`
entry:

```json
"visual": "video/N6a-gcp-terminal.mp4",
```

and delete that beat's `"player"` key. Then:

```powershell
python tools\capture\assemble.py --check
```

The clip does not need to match the narration's length. **Longer gets trimmed;
shorter holds on its last frame** rather than cutting your voice off.

---

## 4. What has to be legible on screen

If any of these is unreadable in the recording, re-shoot with a larger font —
this beat exists to be read, and every one of them is the point of a frame:

- `crucible-target@crucible-hack-2026.iam.gserviceaccount.com` — the service
  account. **Not the default compute identity**, which is the design point
- `aiplatform.googleapis.com` — Vertex, where every model call in the loop goes
- `crucible-sealed-x7` — the sealed bucket, present and unread
- `google/gemma-4-26b-a4b-it-maas`, the endpoint URL, and the **live** result:
  `http 200 in <n> ms` with the classification Gemma returned

---

## 5. Two things that are fine, and one that is not

**The Cloud Run URL will be on screen. That is fine.** It is already public in
six tracked files and the service holds zero IAM bindings, so it is not a spend
risk (`docs/contest/AUDIT-stage-one-2026-08-30.md`, Row 8).

**The sealed bucket appears in a bucket listing. That is also fine.** Listing
bucket *names* fetches no object. The seal is intact and
`python scripts/pre-read-seal-proof.py` says so.

**Do not widen what Gemma does.** On screen it is the capability cartographer:
it classifies each tool the target holds into a capability class. `ADR-0018`
withdrew the claim that Gemma generated the attack corpus and says that
sentence *"may not be written or spoken anywhere"*. Classification, never
generation.


---

## 6. The second beat — `verify-proof.ps1`

Two frames, and **neither costs a word of narration**, because both illustrate
lines the script already says:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\captureerify-proof.ps1 -Pause 2.0
```

| frame | the line it proves |
|---|---|
| `python -m crucible.replay evidence/batch-measure-2026-08-27/run-01.c6.json` | **N5** — *"the replay tool needs no credentials to check them."* It recomputes the digest from the bytes on disk and prints **HASH LOCKS — 5, across 6 fields** |
| `python scripts/pre-read-seal-proof.py` | **N9** — *"the held-out family is still sealed."* Makes it a statement about this minute rather than the day it was written |

**Point the replay at a real bundle, not the golden fixture.** The README's copy
of that command uses `contracts/golden/`, which is a hand-authored schema
instance and says so on its own face. A bundle from the 08-27 measurement batch
proves the same property about real evidence.

Use these under N5 and N9 instead of their cards, or cut between the two. A
claim spoken over a card is a claim; the same claim spoken over the command that
checks it is a demonstration.
