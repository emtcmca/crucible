// lib/verify-video.mjs — assert the postconditions of a recorded take.
//
// WHY THIS FILE EXISTS
// This project's signature recurring defect is a check that passes while
// measuring nothing. In this medium that defect looks like: Playwright exits 0,
// the script prints "recorded N4.webm", and the file is zero bytes, or it is a
// perfectly valid 49-second video of a blank page because the target never
// rendered.
//
// So nothing here trusts an exit code. Every check reads the produced artifact
// back off disk and reports what was OBSERVED. A check that cannot be performed
// returns UNVERIFIED and never PASS.

import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { VERIFY } from '../capture.config.mjs';
import { findFfmpeg, runFfmpeg } from './ffmpeg.mjs';
import { readGrayPng } from './png-gray.mjs';

export const PASS = 'PASS';
export const FAIL = 'FAIL';
export const UNVERIFIED = 'UNVERIFIED';

/** EBML magic number that opens every Matroska/WebM file. */
const EBML_MAGIC = Buffer.from([0x1a, 0x45, 0xdf, 0xa3]);
/** Matroska Cluster element id. Encoded video lives inside clusters. */
const CLUSTER_ID = Buffer.from([0x1f, 0x43, 0xb6, 0x75]);

function check(id, name, status, observed, expected, detail) {
  return { id, name, status, observed, expected, detail };
}

/** Parse the last `time=HH:MM:SS.mmm` ffmpeg printed, in ms. Null if absent. */
function lastProgressTimeMs(stderr) {
  const matches = [...stderr.matchAll(/time=\s*(\d+):(\d{2}):(\d{2}(?:\.\d+)?)/g)];
  if (matches.length === 0) return null;
  const m = matches[matches.length - 1];
  return (Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3])) * 1000;
}

/** Parse the container's declared `Duration:` header, in ms. Null if absent. */
function headerDurationMs(stderr) {
  const m = stderr.match(/Duration:\s*(\d+):(\d{2}):(\d{2}(?:\.\d+)?)/);
  if (!m) return null;
  return (Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3])) * 1000;
}

/** Count non-overlapping occurrences of a byte pattern. */
function countPattern(buf, pattern) {
  let count = 0;
  let from = 0;
  for (;;) {
    const at = buf.indexOf(pattern, from);
    if (at === -1) return count;
    count += 1;
    from = at + pattern.length;
  }
}

/**
 * Describe a sequence of greyscale frames.
 *
 * @param {Uint8Array[]} planes one entry per frame, one byte per pixel
 * @returns {{frames:{meanLuma:number,spread:number}[], pairDiffs:number[], frameCount:number}}
 *   `spread` is max-min luma within a frame: a flat colour field scores 0.
 *   `pairDiffs[i]` is the mean absolute luma change from frame i to frame i+1:
 *   a frozen recording scores 0 across the board.
 */
function describeFrames(planes) {
  const frames = planes.map((plane) => {
    let min = 255;
    let max = 0;
    let sum = 0;
    for (let p = 0; p < plane.length; p += 1) {
      const y = plane[p];
      if (y < min) min = y;
      if (y > max) max = y;
      sum += y;
    }
    return { meanLuma: sum / plane.length, spread: max - min };
  });

  const pairDiffs = [];
  for (let f = 1; f < planes.length; f += 1) {
    const a = planes[f - 1];
    const b = planes[f];
    const n = Math.min(a.length, b.length);
    let acc = 0;
    for (let p = 0; p < n; p += 1) acc += Math.abs(a[p] - b[p]);
    pairDiffs.push(n ? acc / n : 0);
  }

  return { frames, pairDiffs, frameCount: planes.length };
}

/**
 * Verify a recorded take.
 *
 * @param {object} opts
 * @param {string} opts.file            absolute path to the .webm
 * @param {number} [opts.expectedMs]    expected duration; omit to skip V5
 * @param {number} [opts.minMs]         the take must be at least this long: the
 *                                      planned head + beat + tail. Omit to skip V8.
 * @param {number} [opts.analyseFromMs] start the pixel checks at this offset, to
 *                                      exclude browser preamble that the edit
 *                                      trims. Duration checks always use the
 *                                      whole file. Defaults to 0.
 * @param {boolean} [opts.expectMotion] false for a take that is legitimately a
 *                                      held still frame. Defaults to true.
 * @returns {Promise<{ok:boolean, hasUnverified:boolean, checks:Array, frameStats:object|null}>}
 */
export async function verifyVideo({ file, expectedMs, minMs, analyseFromMs = 0, expectMotion = true }) {
  const checks = [];

  // ---- V1 the file exists at all -----------------------------------------
  let stat = null;
  try {
    stat = await fs.stat(file);
  } catch {
    stat = null;
  }
  if (!stat || !stat.isFile()) {
    checks.push(check('V1', 'artifact exists', FAIL, 'no file at that path', 'a regular file', file));
    return { ok: false, hasUnverified: false, checks };
  }
  checks.push(check('V1', 'artifact exists', PASS, `regular file, ${stat.size} bytes`, 'a regular file', file));

  // ---- V2 the file is not a stub -----------------------------------------
  checks.push(
    check(
      'V2',
      'artifact size above floor',
      stat.size >= VERIFY.minBytes ? PASS : FAIL,
      `${stat.size} bytes`,
      `>= ${VERIFY.minBytes} bytes`,
      'A floor, not proof of content. The frame checks below are the real test.',
    ),
  );

  // ---- V3/V4 container structure, no decoder required ---------------------
  const head = await fs.readFile(file);
  const magicOk = head.subarray(0, 4).equals(EBML_MAGIC);
  checks.push(
    check(
      'V3',
      'WebM container header',
      magicOk ? PASS : FAIL,
      magicOk ? '1A 45 DF A3 at offset 0' : `${head.subarray(0, 4).toString('hex')} at offset 0`,
      'EBML magic 1A 45 DF A3',
      'Catches a truncated or half-written file that still has a plausible size.',
    ),
  );
  const clusters = countPattern(head, CLUSTER_ID);
  checks.push(
    check(
      'V4',
      'encoded clusters present',
      clusters >= 2 ? PASS : FAIL,
      `${clusters} Cluster element id(s) found`,
      '>= 2',
      'A header-only file with no media payload has zero or one.',
    ),
  );

  // ---- everything past here needs a decoder ------------------------------
  const ffmpeg = findFfmpeg();
  if (!ffmpeg) {
    const why = 'no ffmpeg found in the Playwright browser cache; run `npm run install-browsers`';
    checks.push(check('V5', 'duration within tolerance', UNVERIFIED, why, expectedMs ? `${expectedMs} ms` : 'n/a', ''));
    checks.push(check('V6', 'frames are not uniformly blank', UNVERIFIED, why, 'at least one frame with image content', ''));
    checks.push(check('V7', 'frames change over time', UNVERIFIED, why, 'motion between sampled frames', ''));
    checks.push(check('V8', 'take covers the planned window', UNVERIFIED, why, minMs ? `>= ${minMs} ms` : 'n/a', ''));
    return summarise(checks);
  }

  // ---- V5 duration, measured by decoding the whole file -------------------
  // `-f null -` decodes every frame and discards it. The last `time=` ffmpeg
  // prints is therefore the real playable length, not the container's claim,
  // which for a screencast webm is frequently absent or wrong.
  const durationRun = await runFfmpeg(ffmpeg, ['-hide_banner', '-i', file, '-f', 'null', '-']);
  const decodedMs = lastProgressTimeMs(durationRun.stderr);
  const declaredMs = headerDurationMs(durationRun.stderr);
  const observedMs = decodedMs ?? declaredMs;

  if (observedMs === null) {
    checks.push(
      check('V5', 'duration within tolerance', UNVERIFIED, 'ffmpeg reported no timestamp', expectedMs ? `${expectedMs} ms` : 'n/a',
        `ffmpeg exit ${durationRun.code}`),
    );
  } else if (expectedMs === undefined) {
    checks.push(check('V5', 'duration within tolerance', UNVERIFIED, `${Math.round(observedMs)} ms decoded`, 'no expectation supplied', ''));
  } else {
    const delta = Math.abs(observedMs - expectedMs);
    checks.push(
      check(
        'V5',
        'duration within tolerance',
        delta <= VERIFY.durationToleranceMs ? PASS : FAIL,
        `${Math.round(observedMs)} ms decoded (declared header: ${declaredMs === null ? 'absent' : Math.round(declaredMs) + ' ms'})`,
        `${expectedMs} ms +/- ${VERIFY.durationToleranceMs} ms`,
        `off by ${Math.round(delta)} ms`,
      ),
    );
  }

  // ---- V8 the take actually contains the window that was asked for --------
  // V5 compares the file against the script's own clock, so it catches a
  // recorder that stopped early or ran long. V8 is the different question:
  // does the file contain the head pad, the whole beat, and the tail pad that
  // the cue list and the narration convention require? A take that is short
  // here has cut inside a beat, which the animation spec forbids outright.
  if (minMs === undefined) {
    checks.push(check('V8', 'take covers the planned window', UNVERIFIED, 'no planned length supplied', 'n/a', ''));
  } else if (observedMs === null) {
    checks.push(check('V8', 'take covers the planned window', UNVERIFIED, 'duration could not be measured', `>= ${minMs} ms`, ''));
  } else {
    checks.push(
      check(
        'V8',
        'take covers the planned window',
        observedMs >= minMs ? PASS : FAIL,
        `${Math.round(observedMs)} ms of footage`,
        `>= ${minMs} ms (head pad + beat + tail pad)`,
        observedMs >= minMs
          ? `${Math.round(observedMs - minMs)} ms of margin`
          : `SHORT BY ${Math.round(minMs - observedMs)} ms — part of the beat is missing from the file`,
      ),
    );
  }

  // ---- V6/V7 pixels ------------------------------------------------------
  // Sample frames as small greyscale PNGs and read the pixels back.
  //
  // The obvious approach -- pipe raw RGB out of ffmpeg -- does not work with
  // the binary Playwright ships. That build has no rawvideo muxer and no fps
  // filter (see lib/png-gray.mjs for the full inventory), so the sampling rate
  // comes from the `-r` output option and the pixels come back as PNG.
  // This was found by the selftest, which reported "zero frames decoded" for a
  // recording that plainly had frames in it.
  const { sampleFps, sampleWidth, sampleHeight } = VERIFY;
  const frameDir = await fs.mkdtemp(path.join(os.tmpdir(), 'crucible-frames-'));
  let frames;
  let pairDiffs;
  let frameCount;
  let frameRun;
  try {
    frameRun = await runFfmpeg(ffmpeg, [
      '-hide_banner',
      '-i', file,
      // -ss AFTER -i is an accurate output seek: it decodes and discards rather
      // than jumping to the nearest keyframe, which on VP8 could be seconds off.
      ...(analyseFromMs > 0 ? ['-ss', (analyseFromMs / 1000).toFixed(3)] : []),
      '-r', String(sampleFps),
      '-vf', `scale=${sampleWidth}:${sampleHeight}:flags=bilinear,format=gray`,
      '-f', 'image2',
      path.join(frameDir, 'f%05d.png'),
    ]);
    const files = (await fs.readdir(frameDir)).filter((f) => f.endsWith('.png')).sort();
    const planes = [];
    for (const f of files) {
      const png = readGrayPng(await fs.readFile(path.join(frameDir, f)));
      planes.push(png.pixels);
    }
    ({ frames, pairDiffs, frameCount } = describeFrames(planes));
  } finally {
    await fs.rm(frameDir, { recursive: true, force: true }).catch(() => {});
  }

  if (frameCount === 0) {
    const detail = `ffmpeg exit ${frameRun ? frameRun.code : '?'}; ffmpeg stderr tail: ${(frameRun ? frameRun.stderr : '').trim().split('\n').slice(-2).join(' | ')}`;
    checks.push(check('V6', 'frames are not uniformly blank', FAIL, 'zero frames decoded', '>= 2 frames', detail));
    checks.push(check('V7', 'frames change over time', FAIL, 'zero frames decoded', '>= 2 frames', detail));
    return summarise(checks);
  }

  const uniform = frames.filter((f) => f.spread <= VERIFY.uniformLumaSpread).length;
  const allUniform = uniform === frames.length;
  checks.push(
    check(
      'V6',
      'frames are not uniformly blank',
      allUniform ? FAIL : PASS,
      `${uniform} of ${frames.length} sampled frames were a flat colour field; mean luma first=${frames[0].meanLuma.toFixed(1)} last=${frames[frames.length - 1].meanLuma.toFixed(1)} (0=black, 255=white)${analyseFromMs > 0 ? `; analysed from ${analyseFromMs} ms in` : ''}`,
      'at least one sampled frame with image content',
      `uniform means max-min luma <= ${VERIFY.uniformLumaSpread} across the frame`,
    ),
  );

  const maxDiff = pairDiffs.length ? Math.max(...pairDiffs) : 0;
  const moved = maxDiff > VERIFY.motionMeanAbsDiff;
  if (!expectMotion) {
    checks.push(
      check('V7', 'frames change over time', UNVERIFIED, `max mean abs luma diff ${maxDiff.toFixed(3)}`, 'not applicable: take declared static', 'caller passed expectMotion:false'),
    );
  } else {
    checks.push(
      check(
        'V7',
        'frames change over time',
        moved ? PASS : FAIL,
        `max mean abs luma diff between consecutive sampled frames = ${maxDiff.toFixed(3)} over ${pairDiffs.length} pair(s), sampled at ${sampleFps} fps`,
        `> ${VERIFY.motionMeanAbsDiff}`,
        'A valid-but-frozen recording of a page that never animated fails here.',
      ),
    );
  }

  return summarise(checks, {
    count: frames.length,
    uniformCount: uniform,
    meanLumaFirst: frames[0].meanLuma,
    meanLumaLast: frames[frames.length - 1].meanLuma,
    maxPairDiff: maxDiff,
  });
}

function summarise(checks, frameStats = null) {
  return {
    ok: checks.every((c) => c.status !== FAIL),
    hasUnverified: checks.some((c) => c.status === UNVERIFIED),
    checks,
    // Raw measurements, exposed so a caller can assert against a value it can
    // predict independently -- which is how the selftest checks that the PNG
    // reader itself is not quietly returning nonsense.
    frameStats,
  };
}

/** Print a verification result as a human-readable block. Returns nothing. */
export function printVerification(result, title) {
  const pad = (s, n) => String(s).padEnd(n);
  console.log('');
  console.log(`POSTCONDITIONS — ${title}`);
  console.log('-'.repeat(72));
  for (const c of result.checks) {
    console.log(`${pad(c.id, 4)} ${pad(c.status, 11)} ${c.name}`);
    console.log(`     observed: ${c.observed}`);
    if (c.expected) console.log(`     expected: ${c.expected}`);
    if (c.detail) console.log(`     note:     ${c.detail}`);
  }
  console.log('-'.repeat(72));
  const failed = result.checks.filter((c) => c.status === FAIL).length;
  const unver = result.checks.filter((c) => c.status === UNVERIFIED).length;
  console.log(`${result.checks.length} checks · ${result.checks.length - failed - unver} PASS · ${failed} FAIL · ${unver} UNVERIFIED`);
}
