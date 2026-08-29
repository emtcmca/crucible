#!/usr/bin/env node
// verify.mjs — run the postcondition checks against a video file that already
// exists. Same code path capture-n4.mjs uses; this is the standalone entry so a
// take can be re-checked later without re-recording it.
//
//   node verify.mjs out/N4.webm [--expect-ms=N] [--min-ms=N] [--from-ms=N] [--static]
//
// --expect-ms  the duration the recorder observed on its own clock (V5)
// --min-ms     head pad + beat + tail pad; the take must be at least this long (V8)
// --from-ms    start the pixel checks here, to skip browser preamble (V6, V7)
// --static     the take is a deliberately held still frame, so the motion check
//              reports UNVERIFIED rather than a false FAIL
//
// Omitting an expectation does NOT make its check pass. V5 and V8 report
// UNVERIFIED without one, and the process exits 3. The numbers for a take this
// harness recorded are in the matching out/<name>.take.json.

import path from 'node:path';
import { EXIT } from './capture.config.mjs';
import { printVerification, verifyVideo } from './lib/verify-video.mjs';

const positional = process.argv.slice(2).filter((a) => !a.startsWith('--'));
if (positional.length !== 1) {
  console.error('usage: node verify.mjs <file.webm> [--expect-ms=N] [--min-ms=N] [--from-ms=N] [--static]');
  process.exit(EXIT.PRECONDITION_FAILED);
}

const num = (name) => {
  const hit = process.argv.find((a) => a.startsWith(`--${name}=`));
  return hit ? Number(hit.split('=')[1]) : undefined;
};

const file = path.resolve(positional[0]);
const expectedMs = num('expect-ms');
const minMs = num('min-ms');
const analyseFromMs = num('from-ms') ?? 0;
const expectMotion = !process.argv.includes('--static');

const result = await verifyVideo({ file, expectedMs, minMs, analyseFromMs, expectMotion });
printVerification(result, file);

if (!result.ok) process.exit(EXIT.POSTCONDITION_FAILED);
if (result.hasUnverified) {
  console.log('\nAt least one property could not be measured. Not measured is not passed.');
  process.exit(EXIT.UNVERIFIED);
}
process.exit(EXIT.OK);
