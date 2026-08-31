/**
 * Renders one 3:2 card at 2x, for the Devpost gallery.
 *
 *   node tools/capture/render-3x2.mjs cards/14-thumbnail.html out/submission-media/00-thumbnail-3x2.png
 *
 * SEPARATE FROM capture.mjs ON PURPOSE. That file pins a 1920x1080 viewport
 * because every video beat is 16:9, and the video is built. Widening its
 * viewport to serve one still would change the geometry of thirteen cards that
 * are already recorded, which is a large blast radius for a small need.
 *
 * 3:2 BECAUSE DEVPOST'S GALLERY CROPS TO 3:2. A 16:9 plate letterboxes in the
 * one frame every judge sees before they decide whether to open the project.
 *
 * deviceScaleFactor 2 rather than a 3840px viewport: the card is authored at
 * 1920x1280 so its type scale matches the 16:9 cards it sits beside, and the
 * scale factor supplies the pixels without re-tuning a single font size.
 */
import { chromium } from 'playwright';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));

const src = process.argv[2];
const dest = process.argv[3];
if (!src || !dest) {
  console.error('usage: node render-3x2.mjs <card.html> <out.png>');
  process.exit(2);
}
// Relative paths resolve against this file, not against cwd, so the command
// works from the repository root or from anywhere else.
const srcPath = path.resolve(HERE, src);
const destPath = path.resolve(HERE, dest);

const b = await chromium.launch({
  args: ['--force-color-profile=srgb', '--disable-lcd-text'],
});
const ctx = await b.newContext({
  viewport: { width: 1920, height: 1280 },
  deviceScaleFactor: 2,
  colorScheme: 'light',
  reducedMotion: 'reduce',
});
const p = await ctx.newPage();
await p.goto(pathToFileURL(srcPath).href, { waitUntil: 'load' });
// Fonts before pixels. A screenshot taken mid-swap ships a different typeface
// than the one that was designed. Same rule as captureCard in capture.mjs.
await p.evaluate(() => document.fonts && document.fonts.ready);
await p.waitForTimeout(300);
fs.mkdirSync(path.dirname(destPath), { recursive: true });
await p.screenshot({ path: destPath, animations: 'disabled' });
await b.close();
console.log('wrote %s', path.relative(path.resolve(HERE, '..', '..'), destPath));
