# SHOT LIST — the four-minute demo video

**Written 2026-08-30.** Pairs every narration beat with the footage it needs and
who captures it. Narration: `docs/design/narration-LOCKED-2026-08-27.md` (N1–N5,
locked) and `docs/design/narration-N6-N9-2026-08-30.md` (N6–N9).

**The seal is NOT opened and this video does not depend on it.** Nothing in
N1–N9 claims a sealed result. If the seal is opened later, the video does not
change.

---

## The split: what Playwright captures, and what you record live

| | |
|---|---|
| **Playwright** | title and closing cards, the architecture plate, the animated N4 beat, any static evidence table. All deterministic, all 1920×1080, all re-runnable |
| **You, live** | every terminal beat, and the refund-agent UI |

**The terminal beats are recorded live on purpose.** A browser cannot record a
shell, and rendering fake console output into an HTML card would put invented
text on camera in a project whose entire argument is that it does not do that.
The gcloud output in N6 is also the contest's *"visible proof your backend runs
on Google Cloud"* — it has to be the real thing.

---

## Commands

```powershell
cd C:\dev\crucible\tools\capture
npm install                     # once
npx playwright install chromium # once

node capture.mjs cards                          # every card in cards/
node capture.mjs card cards/01-title.html       # just one
node capture.mjs loop                           # N4 at the cue file's 45 s
node capture.mjs loop --duration 105000         # N4 rescaled to your take
node capture.mjs encode out/loop-frames out/N4.mp4 --fps 30
```

Output lands in `tools/capture/out/`, which is gitignored — it is derived, and
the frame directories are large.

**`--duration` rescales at capture time and edits nothing on disk.** The cue
file records its own conflict: the locked N4 copy is 263 spoken words, which is
about 105 s at a natural 150 wpm, against a `duration_ms` of 45000. Record N4
first, measure the take, then pass its real length here.

---

## The beats

| # | Narration | Footage | Who |
|---|---|---|---|
| — | *(cold)* | `01-title.png`, 3 s hold | Playwright |
| N1 | 0:00–0:12 | refund agent UI; type the cracked-mug claim; trace shows `lookup_order` then `issue_refund(amount_minor=3400)` | live |
| N2 | 0:12–0:25 | terminal: the `sqlite3 ledger.db` select. **The ledger row is the whole beat** | live |
| N3 | 0:25–0:50 | one slide: *find the breach · patch it · prove the patch didn't break the business* | Playwright (card) |
| N4 | 0:50–1:35 | `02-architecture.png` as the hold, then `N4-architecture.mp4` | Playwright |
| N5 | 1:35–1:43 | the five locks, on the plate or as a card | Playwright |
| N6 | ~0:25 | terminal: `gcloud run services list`, then `cat evidence/batch-measure-2026-08-27/BATCH-DONE`; then Cloud Console on the `crucible` service | live |
| N7 | ~0:30 | the three-row pooled table, **all three rows visible at once** | Playwright (card) |
| N8 | ~0:35 | `README.md:95-106`, the 13-closed / 19-no-op finding | Playwright (card) or screen |
| N9 | ~0:20 | the README's *what is not defensible today* section, then `03-close.png` | Playwright |

**Running total ≈ 3:30.** The cap is 4:00 and the cap is hard.

### N7 — do not crop to the pooled row

The pre-registration requires the replication disagreement to travel *with* the
pooled figure rather than sit under it. Three rows on screen, or the shot
contradicts the narration.

---

## The title card, and the alternates

`cards/01-title.html`. The headline is one edit; everything else stays.

**Shipping:** *Break the agent. Ship the policy.*

It beats *"the pen test that writes itself"* on the thing that actually
separates this project: **the output is an enforceable policy, not a report.**
A pen test that writes itself is still a pen test — it ends with findings. The
verb pair says attack *and* remediation in five words, and the sub-headline
carries the third act, which is the refusal.

| alternate | when to prefer it | accuracy note |
|---|---|---|
| *Attack. Autopsy. Patch. Prove.* | if you want the four components stated as the headline | Exactly the four stages. Reads more like a system diagram than a hook |
| *The red team that has to prove its own fix.* | if the judging leans on rigour over capability | True and it is the sharpest single sentence. Longer; loses the "output is a policy" half |
| *A pen test that ships the patch.* | keeps the phrase you liked | "Pen test" undersells the regression and promotion halves, which is what you said |

**Never on a title card:**

- any efficacy rate — the figures rule requires a denominator *and* the reader
  acceptance count beside every rate, and neither fits;
- *"discovers novel attacks"* / *"generates novel attacks"* — RED discovery is a
  **design**, not a shipped capability;
- *"frontier models refuse to author red-team payloads at volume"* — dead
  phrasing, repo-wide. The approved framing is reproducibility.

---

## Before you upload

- **Public, and checked in an incognito window.** The organiser's checklist
  names this specifically.
- **Under 4:00.**
- **Visible proof the backend runs on Google Cloud** — that is N6, and it is why
  N6 is recorded live.
- **Upload early.** YouTube and Vimeo processing runs from minutes to hours, and
  everything locks 2026-08-31 17:00 PT.
- If the foreign-agent probe appears on screen, its `gemini-2.5-flash` string is
  the **sample agent's** pin. Say so in the same breath or a judge reads it as
  CRUCIBLE's.
