#!/usr/bin/env node
/**
 * capture.mjs - deterministic 1920x1080 footage for the demo video.
 *
 * WHY SEEK AND NOT SCREEN RECORDING. `docs/diagrams/loop-player.html` was built
 * so that everything it draws is a pure function of one integer t:
 * `window.__cuePlayer.seek(ms)` suppresses transitions, renders, and settles in
 * the same frame. So a headless driver gets the same pixels for the same t
 * every time. Recording `play()` in real time would hand the frame rate to
 * whatever the machine was doing that second, on a deadline, at night.
 *
 * WHY PNG FRAMES AND NOT PLAYWRIGHT VIDEO. Playwright's video capture is WebM
 * at a frame rate it chooses, and it starts when the context opens rather than
 * when the beat does. A numbered PNG sequence is exact, resumable, and ffmpeg
 * turns it into whatever the edit needs.
 *
 * WHAT THIS DOES NOT CAPTURE: the terminal beats. A browser cannot record a
 * shell, and faking one would put invented output on camera in a project whose
 * entire argument is that it does not do that. Record those live - see
 * tools/capture/SHOT-LIST.md.
 *
 * Usage:
 *   node tools/capture/capture.mjs cards                 all cards in cards/
 *   node tools/capture/capture.mjs card <file.html>      one card
 *   node tools/capture/capture.mjs loop                  the N4 animation
 *   node tools/capture/capture.mjs loop --duration 105000 --fps 30
 *   node tools/capture/capture.mjs run                   the run-view beat
 *   node tools/capture/capture.mjs player --url <f.html> --global <name>
 *        --duration <ms> --frames <dir> --out <f.mp4>   generic, for assemble.py
 *   node tools/capture/capture.mjs encode <dir> <out.mp4>
 *
 * Output lands in tools/capture/out/ which is gitignored.
 */
import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..', '..');
const OUT = path.join(HERE, 'out');
const W = 1920, H = 1080;

function ensure(dir) { fs.mkdirSync(dir, { recursive: true }); return dir; }

async function browser() {
  return chromium.launch({ args: ['--force-color-profile=srgb',
                                  '--disable-lcd-text',
                                  '--allow-file-access-from-files'] });
}

async function page(b) {
  const ctx = await b.newContext({
    viewport: { width: W, height: H },
    deviceScaleFactor: 1,
    // The plate is authored light. Pinning it means the capture does not
    // inherit whatever the recording machine's OS theme happens to be.
    colorScheme: 'light',
    reducedMotion: 'reduce',
  });
  return ctx.newPage();
}

/** One static frame from an HTML file. */
async function captureCard(p, file, outDir) {
  const url = pathToFileURL(path.resolve(file)).href;
  await p.goto(url, { waitUntil: 'load' });
  // Fonts before pixels. A screenshot taken mid-swap ships a different
  // typeface than the one that was designed.
  await p.evaluate(() => document.fonts && document.fonts.ready);
  await p.waitForTimeout(250);
  const name = path.basename(file, '.html') + '.png';
  const dest = path.join(ensure(outDir), name);
  await p.screenshot({ path: dest, animations: 'disabled' });
  console.log('  card  %s', path.relative(ROOT, dest));
  return dest;
}

/** The N4 architecture beat, one PNG per frame, driven by seek(). */
async function captureLoop(p, { durationMs, fps, outDir, url: pageUrl, global: g }) {
  const url = pageUrl || pathToFileURL(path.join(ROOT, 'docs', 'diagrams',
                                      'loop-player.html')).href;
  const G = g || '__cuePlayer';
  await p.goto(url, { waitUntil: 'load' });

  // FAIL LOUDLY IF THE PLAYER IS NOT THERE. A capture run that silently
  // screenshots a blank page 3000 times is worse than one that stops.
  await p.waitForFunction((n) => !!window[n], G, { timeout: 15000 });

  const native = await p.evaluate((n) => window[n].duration_ms, G);
  const total = durationMs || native;
  const scale = total / native;
  console.log('  player duration %d ms; capturing %d ms (scale %s) at %d fps',
              native, total, scale.toFixed(3), fps);
  if (scale !== 1) {
    console.log('  NOTE the cue file records that its timings are ESTIMATES and');
    console.log('       are to be rescaled against the recorded take. This run');
    console.log('       rescales at capture time and edits nothing on disk.');
  }

  const frames = Math.round((total / 1000) * fps);
  const dir = ensure(outDir);
  for (let i = 0; i <= frames; i++) {
    const tOut = (i / fps) * 1000;          // position in the OUTPUT timeline
    const tCue = Math.min(native, tOut / scale);   // position in cue time
    await p.evaluate(([n, ms]) => window[n].seek(ms), [G, tCue]);
    const dest = path.join(dir, 'f' + String(i).padStart(5, '0') + '.png');
    await p.screenshot({ path: dest, animations: 'disabled' });
    if (i % 60 === 0) {
      process.stdout.write('    frame ' + i + '/' + frames + '\r');
    }
  }
  console.log('\n  loop  %d frames -> %s', frames + 1, path.relative(ROOT, dir));
  return dir;
}

function encode(dir, out, fps) {
  return new Promise((resolve, reject) => {
    // yuv420p and even dimensions: the combination every editor and every
    // upload path accepts. -crf 16 is visually lossless for flat vector art.
    const args = ['-y', '-framerate', String(fps),
                  '-i', path.join(dir, 'f%05d.png'),
                  '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
                  '-pix_fmt', 'yuv420p', out];
    const ff = spawn('ffmpeg', args, { stdio: ['ignore', 'ignore', 'inherit'] });
    ff.on('error', reject);
    ff.on('close', (c) => c === 0 ? resolve(out)
                                  : reject(new Error('ffmpeg exit ' + c)));
  });
}

function arg(flag, dflt) {
  const i = process.argv.indexOf(flag);
  return i > -1 ? process.argv[i + 1] : dflt;
}

const cmd = process.argv[2] || 'cards';
const fps = Number(arg('--fps', 30));

if (cmd === 'encode') {
  const dir = process.argv[3], out = process.argv[4];
  await encode(dir, out, fps);
  console.log('wrote %s', out);
} else {
  const b = await browser();
  const p = await page(b);
  try {
    if (cmd === 'cards') {
      const dir = path.join(HERE, 'cards');
      const files = fs.readdirSync(dir).filter(f => f.endsWith('.html')).sort();
      if (!files.length) throw new Error('no cards in ' + dir);
      for (const f of files) await captureCard(p, path.join(dir, f),
                                               path.join(OUT, 'cards'));
    } else if (cmd === 'card') {
      await captureCard(p, process.argv[3], path.join(OUT, 'cards'));
    } else if (cmd === 'player') {
      // THE GENERIC PATH, used by assemble.py. Any seek-deterministic player,
      // any duration, explicit frame and output directories - so the stitcher
      // can retime a beat to its narration without this file knowing which
      // beat it is.
      const url = pathToFileURL(path.resolve(arg('--url'))).href;
      const g = arg('--global', '__cuePlayer');
      const frames = arg('--frames', path.join(OUT, 'frames-tmp'));
      const out = arg('--out', path.join(OUT, 'beat.mp4'));
      const durationMs = Number(arg('--duration', 0)) || 0;
      const dir = await captureLoop(p, {
        durationMs, fps, outDir: frames, url, global: g,
      });
      await encode(dir, out, fps);
      console.log('wrote %s', out);
    } else if (cmd === 'run') {
      // THE RUN VIEW - a real bundle replayed. Build it first with
      // `python tools/capture/build-run-view.py --bundle <c6.json>`.
      const card = path.join(HERE, 'cards', '03-run.html');
      if (!fs.existsSync(card)) {
        throw new Error('cards/03-run.html not built - run build-run-view.py');
      }
      const durationMs = Number(arg('--duration', 0)) || 0;
      const dir = await captureLoop(p, {
        durationMs, fps, outDir: path.join(OUT, 'run-frames'),
        url: pathToFileURL(card).href, global: '__runPlayer',
      });
      const mp4 = path.join(ensure(OUT), 'N6-run.mp4');
      await encode(dir, mp4, fps);
      console.log('wrote %s', path.relative(ROOT, mp4));
    } else if (cmd === 'loop') {
      const durationMs = Number(arg('--duration', 0)) || 0;
      const dir = await captureLoop(p, {
        durationMs, fps, outDir: path.join(OUT, 'loop-frames'),
      });
      const mp4 = path.join(ensure(OUT), 'N4-architecture.mp4');
      await encode(dir, mp4, fps);
      console.log('wrote %s', path.relative(ROOT, mp4));
    } else {
      throw new Error('unknown command: ' + cmd);
    }
  } finally {
    await b.close();
  }
}
