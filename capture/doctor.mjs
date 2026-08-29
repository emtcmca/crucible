#!/usr/bin/env node
// doctor.mjs — find out what is missing BEFORE anyone tries to record under
// time pressure.
//
//   node doctor.mjs [--no-browser]
//
// Every check states what it observed. Nothing here is inferred from an exit
// code: the chromium check stats the binary on disk, and the cue-hook check
// actually launches a browser, loads the real page, and asks the real object
// whether it is there.

import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { EXIT, OUT_DIR, PINNED_PLAYWRIGHT, REPO_ROOT, CAPTURE_DIR } from './capture.config.mjs';
import { findFfmpeg, browsersRoot } from './lib/ffmpeg.mjs';
import { fileUrl } from './lib/take.mjs';

const require = createRequire(import.meta.url);
const TARGET_PAGE = path.join(REPO_ROOT, 'docs', 'diagrams', 'loop-player.html');
const CUE_LIST = path.join(REPO_ROOT, 'docs', 'diagrams', 'loop-cues.json');
const LOOP_SVG = path.join(REPO_ROOT, 'docs', 'diagrams', 'loop.svg');

const checks = [];
/**
 * @param {string} name
 * @param {'BLOCKS'|'WARNS'} severity  BLOCKS = no capture is possible without it
 */
function record(name, severity, ok, observed, fix) {
  checks.push({ n: checks.length + 1, name, severity, ok, observed, fix });
  return ok;
}

async function exists(p) {
  try {
    await fs.stat(p);
    return true;
  } catch {
    return false;
  }
}

// ---- 1. node ---------------------------------------------------------------
{
  const [major, minor] = process.versions.node.split('.').map(Number);
  const ok = major > 18 || (major === 18 && minor >= 17);
  record('node >= 18.17', 'BLOCKS', ok, `node ${process.version} at ${process.execPath}`,
    'Install Node 18.17 or newer.');
}

// ---- 2. playwright, at the pinned version ----------------------------------
let playwrightOk = false;
{
  let observed;
  try {
    const pkg = require('playwright/package.json');
    playwrightOk = pkg.version === PINNED_PLAYWRIGHT;
    observed = `playwright ${pkg.version} resolved from ${path.relative(CAPTURE_DIR, require.resolve('playwright/package.json'))}`;
    if (!playwrightOk) observed += ` — package.json pins ${PINNED_PLAYWRIGHT}`;
  } catch (e) {
    observed = `cannot resolve the playwright package (${e.code || e.message})`;
  }
  record(`playwright pinned at ${PINNED_PLAYWRIGHT}`, 'BLOCKS', playwrightOk, observed,
    'From capture/: `npm ci` (or `npm install` the first time).');
}

// ---- 3. the chromium build that version wants -------------------------------
let chromiumPath = null;
{
  let observed;
  let ok = false;
  if (playwrightOk) {
    try {
      const { chromium } = await import('playwright');
      chromiumPath = chromium.executablePath();
      ok = await exists(chromiumPath);
      observed = ok ? `chromium present at ${chromiumPath}` : `playwright expects ${chromiumPath}, nothing on disk there`;
    } catch (e) {
      observed = `playwright could not report an executable path: ${e.message}`;
    }
  } else {
    observed = 'not checked — playwright itself is not installed';
  }
  record('chromium browser installed', 'BLOCKS', ok, observed,
    'From capture/: `npm run install-browsers`. This downloads ~150 MB the first time.');
}

// ---- 4. ffmpeg, which is what makes the video verifiable --------------------
{
  const ff = findFfmpeg();
  record('ffmpeg present (Playwright build)', 'BLOCKS', !!ff,
    ff ? `ffmpeg at ${ff}` : `no ffmpeg-* directory under ${browsersRoot()}`,
    'From capture/: `npm run install-browsers`. Without it Playwright cannot mux a video ' +
      'AND the duration/blankness checks report UNVERIFIED, which means a bad take can ship.');
}

// ---- 5. output directory ----------------------------------------------------
{
  let ok = false;
  let observed;
  try {
    await fs.mkdir(OUT_DIR, { recursive: true });
    const probe = path.join(OUT_DIR, '.doctor-write-probe');
    await fs.writeFile(probe, 'probe');
    await fs.rm(probe);
    ok = true;
    observed = `wrote and removed a probe file in ${OUT_DIR}`;
  } catch (e) {
    observed = `cannot write to ${OUT_DIR}: ${e.message}`;
  }
  record('output directory writable', 'BLOCKS', ok, observed, 'Check permissions on capture/out.');
}

// ---- 6. the page to record --------------------------------------------------
const pageThere = await exists(TARGET_PAGE);
record('docs/diagrams/loop-player.html exists', 'BLOCKS', pageThere,
  pageThere ? `present at ${TARGET_PAGE}` : `absent: ${TARGET_PAGE}`,
  'This harness does not create that page — the loop-player work owns it. ' +
    'Until it lands there is nothing for beat N4 to record.');

// ---- 7. the cue list, which owns the beat length ----------------------------
{
  let ok = false;
  let observed;
  if (!(await exists(CUE_LIST))) {
    observed = `absent: ${CUE_LIST}`;
  } else {
    try {
      const cues = JSON.parse(await fs.readFile(CUE_LIST, 'utf8'));
      if (typeof cues.duration_ms === 'number') {
        ok = true;
        observed = `duration_ms = ${cues.duration_ms}, ${Array.isArray(cues.cues) ? cues.cues.length : 0} cue(s)`;
      } else {
        observed = 'parsed, but duration_ms is absent or not a number';
      }
    } catch (e) {
      observed = `present but unreadable: ${e.message}`;
    }
  }
  record('docs/diagrams/loop-cues.json has duration_ms', 'WARNS', ok, observed,
    'Without it the capture falls back to the spec estimate, which is NOT the recorded ' +
      'narration length, so picture and audio will not line up. Cue the list to the recorded take first.');
}

// ---- 8. the diagram the player draws ---------------------------------------
{
  const ok = await exists(LOOP_SVG);
  record('docs/diagrams/loop.svg exists', 'WARNS', ok,
    ok ? `present at ${LOOP_SVG}` : `absent: ${LOOP_SVG}`,
    'The player is expected to draw this. Whether it does is the loop-player work, not this harness.');
}

// ---- 9. the cue hook, asked of the real page --------------------------------
if (!process.argv.includes('--no-browser')) {
  let ok = false;
  let observed;
  if (!playwrightOk || !chromiumPath || !pageThere) {
    observed = 'not checked — playwright, chromium, or the page itself is missing above';
  } else {
    let browser;
    try {
      const { chromium } = await import('playwright');
      browser = await chromium.launch({ headless: true });
      const page = await browser.newPage();
      await page.goto(fileUrl(TARGET_PAGE), { waitUntil: 'load', timeout: 20000 });
      observed = await page.evaluate(() => {
        const v = window.__cuePlayer;
        if (!v) return `window.__cuePlayer is ${v === null ? 'null' : 'undefined'}`;
        const shape = Object.keys(v).map((k) => `${k}:${typeof v[k]}`).join(', ');
        return `window.__cuePlayer = { ${shape} }`;
      });
      ok = await page.evaluate(
        () => !!window.__cuePlayer &&
          typeof window.__cuePlayer.play === 'function' &&
          typeof window.__cuePlayer.seek === 'function' &&
          typeof window.__cuePlayer.state === 'function',
      );
    } catch (e) {
      observed = `could not load the page: ${e.message}`;
    } finally {
      if (browser) await browser.close().catch(() => {});
    }
  }
  record('window.__cuePlayer exposes play/seek/state', 'BLOCKS', ok, observed,
    'The recorded page must expose window.__cuePlayer = { play(), seek(ms), state() }. ' +
      'That contract belongs to the loop-player work.');
}

// ---- report -----------------------------------------------------------------
console.log('CRUCIBLE capture — preflight');
console.log('='.repeat(72));
for (const c of checks) {
  const mark = c.ok ? 'OK    ' : c.severity === 'BLOCKS' ? 'MISSING' : 'WARN  ';
  console.log(`${String(c.n).padStart(2)}. ${mark} ${c.name}`);
  console.log(`      observed: ${c.observed}`);
}

const missing = checks.filter((c) => !c.ok);
const blocking = missing.filter((c) => c.severity === 'BLOCKS');
console.log('='.repeat(72));

if (!missing.length) {
  console.log('Nothing missing. `npm run capture:n4` can run.');
  process.exit(EXIT.OK);
}

console.log(`${missing.length} item(s) need attention — ${blocking.length} of them block a capture:\n`);
missing.forEach((c, i) => {
  console.log(`${i + 1}. [${c.severity === 'BLOCKS' ? 'BLOCKS CAPTURE' : 'DEGRADES TAKE'}] ${c.name}`);
  console.log(`   observed: ${c.observed}`);
  console.log(`   fix:      ${c.fix}\n`);
});

process.exit(blocking.length ? EXIT.PRECONDITION_FAILED : EXIT.UNVERIFIED);
