#!/usr/bin/env node
// selftest.mjs — prove the verifier can still fail.
//
//   node selftest.mjs [--headed]
//
// The whole value of capture/ is the claim "this take is good". That claim is
// worth nothing unless the checks behind it are capable of returning FAIL, so
// this script feeds them artifacts that MUST be rejected and one that MUST be
// accepted, and it fails loudly if either expectation is violated.
//
// Same reasoning as the eval harness shipping deliberate known-bads, and the
// same reasoning as `canon-check --selftest`: a check that cannot fail is not
// measuring anything.
//
// It drives lib/take.mjs -- the production recording path -- not a private copy
// of it. A selftest that exercises its own parallel implementation is the
// eleventh instance of this project's defect, not a defence against it.

import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { CAPTURE_DIR, EXIT } from './capture.config.mjs';
import { recordTake } from './lib/take.mjs';
import { verifyVideo, FAIL, PASS, UNVERIFIED } from './lib/verify-video.mjs';

const SCRATCH = path.join(CAPTURE_DIR, '.selftest');
const FIXTURES = path.join(CAPTURE_DIR, 'fixtures');
const headless = !process.argv.includes('--headed');

// Short beat: the selftest is about the checks, not about the beat length.
const BEAT_MS = 6000;
const PAD_MS = 1000;

const results = [];

function statusOf(result, id) {
  const c = result.checks.find((x) => x.id === id);
  return c ? c.status : 'ABSENT';
}

/** Record one expectation and whether the verifier met it. */
function expect(caseName, what, expected, actual, evidence) {
  const held = expected === actual;
  results.push({ caseName, what, expected, actual, held, evidence });
  const mark = held ? 'ok  ' : 'MISS';
  console.log(`  ${mark} ${what}: expected ${expected}, observed ${actual}`);
  if (evidence) console.log(`       ${evidence}`);
}

async function main() {
  await fs.rm(SCRATCH, { recursive: true, force: true });
  await fs.mkdir(SCRATCH, { recursive: true });

  // ---- A: no artifact at all ---------------------------------------------
  console.log('\nCASE A — the file does not exist');
  {
    const r = await verifyVideo({ file: path.join(SCRATCH, 'does-not-exist.webm') });
    expect('A', 'V1 artifact exists', FAIL, statusOf(r, 'V1'));
  }

  // ---- B: the classic. exit 0, zero bytes on disk -------------------------
  console.log('\nCASE B — a zero-byte file (the "exited 0 and produced nothing" defect)');
  {
    const f = path.join(SCRATCH, 'zero.webm');
    await fs.writeFile(f, Buffer.alloc(0));
    const r = await verifyVideo({ file: f });
    expect('B', 'V1 artifact exists', PASS, statusOf(r, 'V1'));
    expect('B', 'V2 size above floor', FAIL, statusOf(r, 'V2'));
  }

  // ---- C: right size, not a video ----------------------------------------
  console.log('\nCASE C — 64 KB of random bytes: plausible size, not a WebM');
  {
    const f = path.join(SCRATCH, 'garbage.webm');
    await fs.writeFile(f, crypto.randomBytes(64 * 1024));
    const r = await verifyVideo({ file: f });
    expect('C', 'V2 size above floor', PASS, statusOf(r, 'V2'));
    expect('C', 'V3 WebM container header', FAIL, statusOf(r, 'V3'));
  }

  // ---- D: the one that matters. A real video of nothing --------------------
  console.log('\nCASE D — a real, well-formed, correct-length recording of a blank page');
  console.log('         (this is the artifact a naive harness reports as a success)');
  let ffmpegAvailable = true;
  {
    const out = path.join(SCRATCH, 'known-bad-blank.webm');
    const obs = await recordTake({
      pageFile: path.join(FIXTURES, 'known-bad-blank.html'),
      outFile: out,
      beatMs: BEAT_MS,
      headPadMs: PAD_MS,
      tailPadMs: PAD_MS,
      requireHook: true,
      headless,
    });
    const r = await verifyVideo({ file: out, expectedMs: obs.videoWallMs, expectMotion: true });
    const v6 = statusOf(r, 'V6');
    const v7 = statusOf(r, 'V7');
    ffmpegAvailable = v6 !== UNVERIFIED && v7 !== UNVERIFIED;

    const size = (await fs.stat(out)).size;
    expect('D', 'V2 size above floor', PASS, statusOf(r, 'V2'), `the blank take is a real ${size}-byte file`);
    expect('D', 'V3 WebM container header', PASS, statusOf(r, 'V3'), 'and a structurally valid WebM');
    if (ffmpegAvailable) {
      expect('D', 'V6 frames are not uniformly blank', FAIL, v6,
        r.checks.find((c) => c.id === 'V6').observed);
      expect('D', 'V7 frames change over time', FAIL, v7,
        r.checks.find((c) => c.id === 'V7').observed);

      // An independent oracle for the PNG reader itself. The fixture's
      // background is #ffffff, so every sampled frame must come back as a flat
      // near-255 field. If the hand-rolled greyscale decoder were unfiltering
      // rows incorrectly, this number would not land where it is predicted to,
      // and V6/V7 above would be failing for the wrong reason.
      const mean = r.frameStats ? r.frameStats.meanLumaFirst : null;
      const white = mean !== null && mean > 250;
      expect('D', 'PNG reader returns the white field the fixture paints', true, white,
        `mean luma of the first sampled frame = ${mean === null ? 'n/a' : mean.toFixed(2)} (expected > 250 for #ffffff)`);
    } else {
      expect('D', 'V6 frames are not uniformly blank', UNVERIFIED, v6,
        'no ffmpeg: the blankness check could not run, so the selftest cannot clear it');
      expect('D', 'V7 frames change over time', UNVERIFIED, v7, '');
    }
  }

  // ---- E: the positive control -------------------------------------------
  console.log('\nCASE E — a recording of a page that really does render and move');
  console.log('         (a verifier that always fails is as useless as one that always passes)');
  {
    const out = path.join(SCRATCH, 'known-good-motion.webm');
    const obs = await recordTake({
      pageFile: path.join(FIXTURES, 'known-good-motion.html'),
      outFile: out,
      beatMs: BEAT_MS,
      headPadMs: PAD_MS,
      tailPadMs: PAD_MS,
      requireHook: true,
      headless,
    });
    const r = await verifyVideo({
      file: out,
      expectedMs: obs.videoWallMs,
      minMs: obs.plannedMs,
      expectMotion: true,
    });
    const failed = r.checks.filter((c) => c.status === FAIL).map((c) => `${c.id} (${c.observed})`);
    expect('E', 'no check reports FAIL', 'none', failed.length ? failed.join('; ') : 'none');
    if (ffmpegAvailable) {
      expect('E', 'V5 duration within tolerance', PASS, statusOf(r, 'V5'),
        r.checks.find((c) => c.id === 'V5').observed);
      expect('E', 'V6 frames are not uniformly blank', PASS, statusOf(r, 'V6'),
        r.checks.find((c) => c.id === 'V6').observed);
      expect('E', 'V7 frames change over time', PASS, statusOf(r, 'V7'),
        r.checks.find((c) => c.id === 'V7').observed);
      expect('E', 'V8 take covers the planned window', PASS, statusOf(r, 'V8'),
        r.checks.find((c) => c.id === 'V8').observed);

      // ---- F: prove V8 can fail, on the same known-good file --------------
      // Re-verify the identical artifact against a window it cannot possibly
      // cover. A length check that only ever sees takes long enough to pass is
      // not a length check.
      console.log('\nCASE F — the same good file, judged against a longer planned window');
      const tooLong = obs.plannedMs + 60000;
      const r2 = await verifyVideo({ file: out, minMs: tooLong, expectMotion: true });
      expect('F', 'V8 take covers the planned window', FAIL, statusOf(r2, 'V8'),
        r2.checks.find((c) => c.id === 'V8').detail);
    }
  }

  // ---- G/H: the two ways a capture is blocked, and what it says ----------
  // The harness has to fail with an actionable message when the page or the
  // cue hook is absent. "Timeout 10000ms exceeded" is not actionable, so the
  // messages are asserted, not just the fact that something threw.
  console.log('\nCASE G — the page to record does not exist');
  {
    let err = null;
    try {
      await recordTake({
        pageFile: path.join(SCRATCH, 'no-such-page.html'),
        outFile: path.join(SCRATCH, 'g.webm'),
        beatMs: 500, headPadMs: 100, tailPadMs: 100, requireHook: true, headless,
      });
    } catch (e) { err = e; }
    expect('G', 'throws CaptureError with code TARGET_MISSING', 'TARGET_MISSING', err ? err.code : 'no error thrown');
    expect('G', 'the message names who owns the missing page', true,
      !!(err && /loop-player/.test(err.fix)), err ? err.fix : '');
  }

  console.log('\nCASE H — the page loads but never exposes window.__cuePlayer');
  {
    const noHook = path.join(SCRATCH, 'no-hook.html');
    await fs.writeFile(noHook, '<!doctype html><meta charset="utf-8"><title>no hook</title><body>no cue player here</body>', 'utf8');
    let err = null;
    try {
      await recordTake({
        pageFile: noHook,
        outFile: path.join(SCRATCH, 'h.webm'),
        beatMs: 500, headPadMs: 100, tailPadMs: 100, requireHook: true, headless,
      });
    } catch (e) { err = e; }
    expect('H', 'throws CaptureError with code HOOK_MISSING', 'HOOK_MISSING', err ? err.code : 'no error thrown');
    expect('H', 'the message reports what was actually on the page', true,
      !!(err && /window\.__cuePlayer is undefined/.test(err.message)), err ? err.message : '');
    expect('H', 'the message states the required interface', true,
      !!(err && /play\(\), seek\(ms\), state\(\)/.test(err.fix)), err ? err.fix : '');
  }

  // ---- verdict ------------------------------------------------------------
  const missed = results.filter((r) => !r.held);
  console.log('\n' + '='.repeat(72));
  console.log(`SELFTEST — ${results.length} expectations, ${missed.length} not met`);
  console.log('='.repeat(72));
  for (const m of missed) {
    console.log(`  ${m.caseName}: ${m.what} — expected ${m.expected}, observed ${m.actual}`);
  }

  if (missed.length) {
    console.log('\nVERDICT: the verifier does not behave as specified.');
    console.log('Until this is green, treat every "postconditions passed" line from');
    console.log('capture-n4.mjs as unproven.');
    return EXIT.POSTCONDITION_FAILED;
  }
  if (!ffmpegAvailable) {
    console.log('\nVERDICT: UNVERIFIED. Structural checks behave correctly, but with no');
    console.log('ffmpeg present the blankness and motion checks never ran, so the harness');
    console.log('is NOT currently able to detect a well-formed video of nothing.');
    console.log('Run `npm run install-browsers`, then re-run this selftest.');
    return EXIT.UNVERIFIED;
  }
  console.log('\nVERDICT: the verifier rejected every known-bad artifact and accepted the');
  console.log('known-good one. The checks are capable of failing.');
  return EXIT.OK;
}

main()
  .then(async (code) => {
    // Scratch is left on disk when something went wrong, so the artifacts can
    // be inspected. It is cleaned only on a clean run.
    if (code === EXIT.OK) await fs.rm(SCRATCH, { recursive: true, force: true }).catch(() => {});
    else console.log(`\nArtifacts left for inspection in ${SCRATCH}`);
    process.exit(code);
  })
  .catch((err) => {
    console.error('\nSELFTEST COULD NOT RUN');
    console.error(err);
    process.exit(EXIT.PRECONDITION_FAILED);
  });
