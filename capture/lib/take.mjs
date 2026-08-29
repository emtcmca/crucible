// lib/take.mjs — the production recording path.
//
// capture-n4.mjs and selftest.mjs both call recordTake(). That is deliberate:
// a selftest that exercises its own private copy of the recording logic proves
// nothing about the code that ships. This project has already been burned by
// tests that "write their own crash record instead of exercising the production
// path", so the fixtures below drive exactly the function the real beat uses.

import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium } from 'playwright';
import { CONTEXT_OPTIONS, INIT_SCRIPT, LAUNCH_ARGS, VIDEO_SIZE } from '../capture.config.mjs';

/** An error that carries a machine-readable reason and an operator-facing fix. */
export class CaptureError extends Error {
  constructor(code, message, fix) {
    super(message);
    this.name = 'CaptureError';
    this.code = code;
    this.fix = fix;
  }
}

/** Sleep until an absolute deadline so pads do not accumulate drift. */
function sleepUntil(deadline) {
  const remaining = deadline - Date.now();
  return new Promise((resolve) => setTimeout(resolve, Math.max(0, remaining)));
}

/** Turn a filesystem path into the file:// URL Chromium needs. */
export function fileUrl(absPath) {
  return pathToFileURL(absPath).href;
}

/**
 * Wait until the page stops changing, then return how long that took.
 *
 * `load` plus `document.fonts.ready` plus two animation frames is NOT enough on
 * its own. The first real N4 take opened on a white unpainted frame -- the
 * verifier caught it as "1 of 100 sampled frames was a flat colour field, mean
 * luma 254 where every other frame was 26" -- because the diagram had not
 * finished painting when the head pad began. So the settle is measured, not
 * assumed: screenshot, hash, repeat until two in a row match.
 *
 * Returns { settled, ms, samples }. `settled: false` is reported, never hidden:
 * a page that never stops changing (an idle animation, a blinking cursor) is a
 * fact the operator needs, not something to swallow.
 */
async function waitForVisualSettle(page, { intervalMs = 150, maxMs = 5000 } = {}) {
  const started = Date.now();
  let previous = null;
  let samples = 0;
  while (Date.now() - started < maxMs) {
    // A low-quality JPEG is plenty: we compare for identity, not for fidelity,
    // and a full-fidelity PNG of a 3840x2160 surface costs real time.
    const shot = await page.screenshot({ type: 'jpeg', quality: 30 });
    const digest = createHash('sha1').update(shot).digest('hex');
    samples += 1;
    if (previous === digest) {
      return { settled: true, ms: Date.now() - started, samples };
    }
    previous = digest;
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return { settled: false, ms: Date.now() - started, samples };
}

/**
 * Record one unbroken take.
 *
 * The take is never paused, never seeked mid-beat, and never stitched. The
 * animation spec requires it: "Each beat is one unbroken take; cuts fall
 * between beats, never inside one."
 *
 * @param {object} opts
 * @param {string} opts.pageFile      absolute path to the HTML file to record
 * @param {string} opts.outFile       absolute path the finished .webm lands at
 * @param {number} opts.beatMs        length of the animated beat itself
 * @param {number} opts.headPadMs     held frame before the beat starts
 * @param {number} opts.tailPadMs     held frame after the beat ends
 * @param {boolean} [opts.requireHook] wait for and drive window.__cuePlayer
 * @param {boolean} [opts.headless]
 * @returns {Promise<object>} an observation record describing what happened
 */
export async function recordTake({
  pageFile,
  outFile,
  beatMs,
  headPadMs,
  tailPadMs,
  requireHook = true,
  headless = true,
}) {
  // ---- preconditions, checked before a browser is launched ---------------
  try {
    const st = await fs.stat(pageFile);
    if (!st.isFile()) throw new Error('not a file');
  } catch {
    throw new CaptureError(
      'TARGET_MISSING',
      `The page to record does not exist: ${pageFile}`,
      'This harness does not create that page. For N4 it is owned by the loop-player work; ' +
        'check that docs/diagrams/loop-player.html has landed on this branch.',
    );
  }

  const tmpDir = path.join(path.dirname(outFile), `.tmp-${path.basename(outFile, '.webm')}`);
  await fs.rm(tmpDir, { recursive: true, force: true });
  await fs.mkdir(tmpDir, { recursive: true });
  await fs.mkdir(path.dirname(outFile), { recursive: true });

  const consoleErrors = [];
  const pageErrors = [];
  const stateSamples = [];

  const browser = await chromium.launch({ headless, args: LAUNCH_ARGS });
  let context;
  let videoWallMs = null;
  const marks = {};

  try {
    context = await browser.newContext({
      ...CONTEXT_OPTIONS,
      recordVideo: { dir: tmpDir, size: VIDEO_SIZE },
    });
    await context.addInitScript(INIT_SCRIPT);

    const recordStart = Date.now();
    const page = await context.newPage();

    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', (err) => pageErrors.push(String(err && err.message ? err.message : err)));

    await page.goto(fileUrl(pageFile), { waitUntil: 'load', timeout: 30000 });

    // Fonts must be settled before the first frame or the take opens on a
    // reflow. document.fonts.ready is the only reliable signal for that.
    await page.evaluate(() => document.fonts.ready).catch(() => {});
    // One more rAF pair so the post-font layout is actually painted.
    await page.evaluate(
      () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))),
    );
    marks.readyMs = Date.now() - recordStart;

    // ---- the cue-player contract ----------------------------------------
    if (requireHook) {
      try {
        await page.waitForFunction(
          () =>
            !!window.__cuePlayer &&
            typeof window.__cuePlayer.play === 'function' &&
            typeof window.__cuePlayer.seek === 'function' &&
            typeof window.__cuePlayer.state === 'function',
          undefined,
          { timeout: 10000 },
        );
      } catch {
        // Report what IS there, so the message is actionable rather than "timed out".
        const found = await page
          .evaluate(() => {
            const v = window.__cuePlayer;
            if (v === undefined) return 'window.__cuePlayer is undefined';
            if (v === null) return 'window.__cuePlayer is null';
            const keys = Object.keys(v);
            const types = keys.map((k) => `${k}:${typeof v[k]}`).join(', ');
            return `window.__cuePlayer exists with { ${types} }`;
          })
          .catch((e) => `could not inspect the page: ${e.message}`);
        throw new CaptureError(
          'HOOK_MISSING',
          `The cue-player hook was not exposed within 10s. ${found}`,
          'The recorded page must expose window.__cuePlayer = { play(), seek(ms), state() } ' +
            'with all three as functions. That interface is owned by the loop-player work, ' +
            'not by this harness.',
        );
      }
      // Park the animation at frame zero before the held head frame.
      await page.evaluate(() => window.__cuePlayer.seek(0));
      await page.evaluate(
        () => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))),
      );
    }

    // Settle AFTER seek(0), not before: seeking is what paints the frame the
    // head pad is supposed to hold, so settling earlier would measure a
    // different picture than the one that ends up on screen.
    const settle = await waitForVisualSettle(page);
    marks.settleMs = settle.ms;
    marks.settled = settle.settled;

    // ---- head pad: a held frame, absolutely still -------------------------
    marks.headPadStartMs = Date.now() - recordStart;
    await sleepUntil(Date.now() + headPadMs);

    // ---- the beat: one unbroken run ---------------------------------------
    marks.beatStartMs = Date.now() - recordStart;
    const beatStartedAt = Date.now();
    if (requireHook) {
      await page.evaluate(() => window.__cuePlayer.play());
    }

    const beatDeadline = beatStartedAt + beatMs;
    // Sample state() as an OBSERVATION only. It never shortens the take: the
    // cue list owns the beat length, and cutting early on a player's say-so is
    // how a take ends mid-sentence. The take is time-boxed by the wall clock,
    // so a wedged player cannot hang the recording -- but a wedged evaluate()
    // could, which is why each sample is raced against a short timeout.
    while (Date.now() < beatDeadline) {
      if (requireHook) {
        const sample = await Promise.race([
          page
            .evaluate(() => {
              try {
                return { state: window.__cuePlayer.state() };
              } catch (e) {
                return { error: String(e && e.message ? e.message : e) };
              }
            })
            .catch((e) => ({ error: e.message })),
          new Promise((r) => setTimeout(() => r({ error: 'state() did not return within 2000 ms' }), 2000)),
        ]);
        stateSamples.push({ tMs: Date.now() - beatStartedAt, ...sample });
      }
      await sleepUntil(Math.min(Date.now() + 1000, beatDeadline));
    }
    marks.beatEndMs = Date.now() - recordStart;

    // ---- tail pad: a held frame again -------------------------------------
    await sleepUntil(Date.now() + tailPadMs);
    marks.tailEndMs = Date.now() - recordStart;

    const video = page.video();
    if (!video) {
      throw new CaptureError(
        'NO_VIDEO_HANDLE',
        'Playwright returned no video handle for the page.',
        'recordVideo was set on the context, so this means the browser build cannot screencast. ' +
          'Re-run `npm run install-browsers`.',
      );
    }

    // Mark the end of the recorded window BEFORE closing. Closing the context
    // is what finalises and flushes the webm, and on a multi-megabyte take that
    // flush costs seconds. Timing the close as if it were recorded footage put
    // a ~1.8s systematic bias into the duration expectation, which was measured
    // on the first real N4 take: it still "passed", with 90% of the tolerance
    // spent on the bias. A check that only passes because its expectation is
    // wrong in the forgiving direction is the defect this repo keeps finding.
    marks.recordingStoppedMs = Date.now() - recordStart;
    await context.close();
    context = null;
    videoWallMs = marks.recordingStoppedMs;
    marks.flushMs = Date.now() - recordStart - marks.recordingStoppedMs;

    const producedPath = await video.path();
    await fs.rm(outFile, { force: true });
    try {
      await fs.rename(producedPath, outFile);
    } catch {
      // rename fails across volumes; copy is the fallback, not the default.
      await fs.copyFile(producedPath, outFile);
      await fs.rm(producedPath, { force: true });
    }
  } finally {
    if (context) await context.close().catch(() => {});
    await browser.close().catch(() => {});
    await fs.rm(tmpDir, { recursive: true, force: true }).catch(() => {});
  }

  return {
    outFile,
    marks,
    videoWallMs,
    plannedMs: headPadMs + beatMs + tailPadMs,
    consoleErrors,
    pageErrors,
    stateSamples,
  };
}
