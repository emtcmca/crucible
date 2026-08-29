#!/usr/bin/env node
// capture-n4.mjs — record the N4 architecture beat as one unbroken take.
//
//   node capture-n4.mjs [--headed] [--beat-ms=45000] [--out=out/N4.webm] [--allow-unverified]
//
// Beat source: docs/design/narration-LOCKED-2026-08-27.md
//   "N4 · 0:50–1:35 · architecture · diagram on screen throughout.
//    The animation is cued to this beat. Its real length sets the cue list."
// Take convention: two seconds of held frame head and tail, matching the audio.
//
// This script does NOT create docs/diagrams/loop-player.html and does not know
// how the animation works. It knows the file path, the cue-player interface,
// and the beat length. Everything else belongs to the page.

import fs from 'node:fs/promises';
import path from 'node:path';
import {
  EXIT,
  HEAD_PAD_MS,
  N4_FALLBACK_DURATION_MS,
  OUT_DIR,
  REPO_ROOT,
  TAIL_PAD_MS,
} from './capture.config.mjs';
import { CaptureError, recordTake } from './lib/take.mjs';
import { printVerification, verifyVideo } from './lib/verify-video.mjs';

const TARGET_PAGE = path.join(REPO_ROOT, 'docs', 'diagrams', 'loop-player.html');
const CUE_LIST = path.join(REPO_ROOT, 'docs', 'diagrams', 'loop-cues.json');

function arg(name, fallback) {
  const hit = process.argv.find((a) => a.startsWith(`--${name}=`));
  return hit ? hit.slice(name.length + 3) : fallback;
}
const flag = (name) => process.argv.includes(`--${name}`);

/**
 * The cue list owns the beat length. Read it; do not recall it.
 * Returns { beatMs, source } and says out loud when it fell back.
 */
async function resolveBeatMs() {
  const override = arg('beat-ms', null);
  if (override) return { beatMs: Number(override), source: `--beat-ms=${override} on the command line` };
  try {
    const raw = await fs.readFile(CUE_LIST, 'utf8');
    const cues = JSON.parse(raw);
    if (typeof cues.duration_ms !== 'number') {
      throw new Error('duration_ms is absent or not a number');
    }
    return { beatMs: cues.duration_ms, source: `duration_ms in ${path.relative(REPO_ROOT, CUE_LIST)}` };
  } catch (e) {
    return {
      beatMs: N4_FALLBACK_DURATION_MS,
      source: null,
      warning:
        `Could not read a beat length from ${path.relative(REPO_ROOT, CUE_LIST)} (${e.message}). ` +
        `Falling back to ${N4_FALLBACK_DURATION_MS} ms from capture.config.mjs. ` +
        `That number is the spec's estimate, NOT Eric's recorded narration length, so the ` +
        `take will not match the audio. Record the narration, write the cue list, re-run.`,
    };
  }
}

async function main() {
  const outFile = path.resolve(OUT_DIR, arg('out', 'N4.webm').replace(/^out[\\/]/, ''));
  const { beatMs, source, warning } = await resolveBeatMs();

  console.log('CRUCIBLE capture — beat N4 (architecture)');
  console.log(`  page      ${path.relative(REPO_ROOT, TARGET_PAGE)}`);
  console.log(`  beat      ${beatMs} ms  [${source || 'FALLBACK — see warning below'}]`);
  console.log(`  pads      ${HEAD_PAD_MS} ms head / ${TAIL_PAD_MS} ms tail (held frames)`);
  console.log(`  out       ${outFile}`);
  if (warning) console.log(`\n  WARNING: ${warning}\n`);

  const observation = await recordTake({
    pageFile: TARGET_PAGE,
    outFile,
    beatMs,
    headPadMs: HEAD_PAD_MS,
    tailPadMs: TAIL_PAD_MS,
    requireHook: true,
    headless: !flag('headed'),
  });

  // ---- what the page said while it ran -----------------------------------
  if (observation.pageErrors.length || observation.consoleErrors.length) {
    console.log('\nPAGE ERRORS DURING THE TAKE (the take is suspect even if it verifies):');
    for (const e of observation.pageErrors) console.log(`  pageerror: ${e}`);
    for (const e of observation.consoleErrors) console.log(`  console.error: ${e}`);
  }

  const lastState = observation.stateSamples[observation.stateSamples.length - 1];
  console.log('\nCUE PLAYER');
  console.log(`  ${observation.stateSamples.length} state() samples taken during the beat`);
  console.log(`  last sample at +${lastState ? lastState.tMs : '?'} ms: ${JSON.stringify(lastState ? (lastState.state ?? lastState.error) : null)}`);

  // ---- where the beat sits inside the file, for the editor ---------------
  const m = observation.marks;
  console.log('\nTAKE WINDOW (offsets from the first recorded frame)');
  console.log(`  page ready ......... ${m.readyMs} ms`);
  console.log(`  visually settled ... after ${m.settleMs} ms${m.settled ? '' : '  <- NEVER SETTLED: the page was still changing when the head pad began'}`);
  console.log(`  head pad begins .... ${m.headPadStartMs} ms   <- cut in here`);
  console.log(`  beat begins ........ ${m.beatStartMs} ms`);
  console.log(`  beat ends .......... ${m.beatEndMs} ms`);
  console.log(`  tail pad ends ...... ${m.tailEndMs} ms   <- cut out here`);
  console.log(`  recording stopped .. ${m.recordingStoppedMs} ms  (webm flush then took ${m.flushMs} ms, which is not footage)`);
  console.log(`  Everything before the head pad is browser preamble. Trim it in the edit;`);
  console.log(`  this harness will not re-encode the file to hide it.`);

  // ---- postconditions ----------------------------------------------------
  // The expectation is the wall-clock length THIS script observed between the
  // first recorded frame and the flush, not a number typed into a config.
  // Duration is checked over the whole file. The pixel checks start at the
  // cut-in point, because the frames before it are browser preamble -- an
  // unpainted white frame lives there, and it is trimmed in the edit. Judging
  // the deliverable on footage nobody will ship would be the wrong measurement,
  // in either direction.
  const result = await verifyVideo({
    file: outFile,
    expectedMs: observation.videoWallMs,
    minMs: observation.plannedMs,
    analyseFromMs: observation.marks.headPadStartMs,
    expectMotion: true,
  });
  printVerification(result, path.relative(REPO_ROOT, outFile));

  // ---- an observation record beside the video ----------------------------
  const record = {
    beat: 'N4',
    recorded_at: new Date().toISOString(),
    page: path.relative(REPO_ROOT, TARGET_PAGE),
    beat_ms: beatMs,
    beat_ms_source: source || 'FALLBACK in capture.config.mjs',
    head_pad_ms: HEAD_PAD_MS,
    tail_pad_ms: TAIL_PAD_MS,
    marks: observation.marks,
    video_wall_ms: observation.videoWallMs,
    page_errors: observation.pageErrors,
    console_errors: observation.consoleErrors,
    cue_state_samples: observation.stateSamples,
    verification: result.checks,
  };
  const recordPath = outFile.replace(/\.webm$/, '.take.json');
  await fs.writeFile(recordPath, JSON.stringify(record, null, 2), 'utf8');
  console.log(`\nObservation record: ${recordPath}`);

  if (!result.ok) {
    console.log('\nRESULT: FAILED. At least one postcondition was observed to fail above.');
    console.log('The file on disk is NOT a usable take. Do not put it in the edit.');
    return EXIT.POSTCONDITION_FAILED;
  }
  if (result.hasUnverified && !flag('allow-unverified')) {
    console.log('\nRESULT: RECORDED, BUT NOT FULLY VERIFIED.');
    console.log('Nothing failed, but a property above could not be measured. Not measured is not passed.');
    console.log('Fix the tooling, or re-run with --allow-unverified once you have accepted the gap.');
    return EXIT.UNVERIFIED;
  }
  console.log('\nRESULT: recorded, and every postcondition above was observed to pass.');
  return EXIT.OK;
}

main()
  .then((code) => process.exit(code))
  .catch((err) => {
    if (err instanceof CaptureError) {
      console.error(`\nCAPTURE BLOCKED [${err.code}]`);
      console.error(`  ${err.message}`);
      console.error(`  FIX: ${err.fix}`);
      console.error('\n  Run `npm run doctor` for the full list of what is missing.');
      process.exit(EXIT.PRECONDITION_FAILED);
    }
    console.error('\nUNEXPECTED FAILURE');
    console.error(err);
    process.exit(EXIT.PRECONDITION_FAILED);
  });
