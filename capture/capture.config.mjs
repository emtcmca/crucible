// capture.config.mjs — the single source of truth for every capture setting.
//
// There is deliberately NO playwright.config.ts here. That file is read by the
// `playwright test` runner, and nothing in this directory runs under the test
// runner: a capture is a scripted take, not a test. A config file that nothing
// reads is a setting that cannot fail, which is this project's signature defect
// in a new medium. Every knob below is imported by the scripts that use it.
//
// Frame spec source: docs/design/architecture-animation-spec.md -> "## Frame"
//   1920x1080, 16:9, legible in full at frame one, no text below 16px.
// Take convention source: docs/design/narration-LOCKED-2026-08-27.md -> "How to record"
//   "Two seconds of silence at the head and tail of every take."
//   The video pads match the audio pads so picture and narration cut together.

import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));

/** Absolute path to this capture directory. */
export const CAPTURE_DIR = HERE;

/** Absolute path to the repository root (capture/ sits directly under it). */
export const REPO_ROOT = path.resolve(HERE, '..');

/** Where finished takes land. */
export const OUT_DIR = path.join(HERE, 'out');

/** Exact Playwright version this harness is pinned to (must match package.json). */
export const PINNED_PLAYWRIGHT = '1.60.0';

// ---------------------------------------------------------------------------
// Frame
// ---------------------------------------------------------------------------

export const FRAME = {
  width: 1920,
  height: 1080,
  // deviceScaleFactor 2 renders the page at 3840x2160 and Playwright scales the
  // screencast down into the video size below. That downsample is what makes
  // 16px type legible in a 1080p video instead of aliased.
  deviceScaleFactor: 2,
};

/** Video dimensions. Kept equal to the CSS viewport, not to the device pixels. */
export const VIDEO_SIZE = { width: FRAME.width, height: FRAME.height };

// ---------------------------------------------------------------------------
// Take structure
// ---------------------------------------------------------------------------

/** Held frame before the animation starts, in ms. Matches the audio head pad. */
export const HEAD_PAD_MS = 2000;

/** Held frame after the animation ends, in ms. Matches the audio tail pad. */
export const TAIL_PAD_MS = 2000;

/**
 * Fallback beat length used only when docs/diagrams/loop-cues.json is absent.
 * The cue list owns this number (architecture-animation-spec.md "## Cue list":
 * "Cued to Eric's RECORDED narration ... N4's real duration sets the timeline").
 * If this fallback is ever used, the capture says so out loud in its report.
 */
export const N4_FALLBACK_DURATION_MS = 45000;

// ---------------------------------------------------------------------------
// Verification tolerances (postconditions, not preferences)
// ---------------------------------------------------------------------------

export const VERIFY = {
  /**
   * Duration tolerance. Playwright's screencast starts a beat after
   * context creation and stops a beat after the last frame, so an exact match
   * is not achievable; +/- 2s still distinguishes a real take from a stub.
   */
  durationToleranceMs: 2000,

  /**
   * Minimum plausible file size in bytes. A mostly-static 1080p VP8 take
   * compresses astonishingly hard -- a measured 9-second recording of a blank
   * white page came out at 19,343 bytes -- so this floor is set to catch only
   * zero-byte and header-only stubs. It is NOT evidence the video has content;
   * that is what V6 and V7 are for. Raising it to a number that "feels like a
   * real video" would reject good short takes and still pass blank long ones.
   */
  minBytes: 4096,

  /** Frames per second sampled out of the video for the blankness/motion checks. */
  sampleFps: 2,

  /** Sampled frames are downscaled to this size before pixel analysis. */
  sampleWidth: 64,
  sampleHeight: 36,

  /**
   * A frame counts as "uniform" (a flat colour field) when the spread between
   * its darkest and brightest luma is at or below this, on a 0-255 scale.
   * 2 allows for VP8 quantisation noise on a genuinely flat frame.
   */
  uniformLumaSpread: 2,

  /**
   * Motion is detected when the mean absolute luma difference between two
   * consecutive sampled frames exceeds this, on a 0-255 scale.
   */
  motionMeanAbsDiff: 0.5,
};

// ---------------------------------------------------------------------------
// Browser
// ---------------------------------------------------------------------------

/**
 * Chromium launch flags chosen for determinism, not for speed.
 * Nothing here disables animation: the beat IS the animation.
 */
export const LAUNCH_ARGS = [
  '--force-color-profile=srgb',      // same colours on every machine
  '--font-render-hinting=none',      // same glyph rasterisation on every machine
  '--disable-lcd-text',              // no subpixel colour fringing in the video
  '--hide-scrollbars',               // a scrollbar in frame is a defect
  '--autoplay-policy=no-user-gesture-required',
  '--disable-background-timer-throttling',
  '--disable-renderer-backgrounding',
  '--disable-backgrounding-occluded-windows',
];

/**
 * Context options shared by every take.
 * reducedMotion is pinned to 'no-preference' on purpose. The default inherits
 * the host OS setting, and a machine with "reduce motion" on would silently
 * record a still frame where the spec requires an animation.
 */
export const CONTEXT_OPTIONS = {
  viewport: { width: FRAME.width, height: FRAME.height },
  deviceScaleFactor: FRAME.deviceScaleFactor,
  reducedMotion: 'no-preference',
  forcedColors: 'none',
  colorScheme: 'light',            // palette ground is #F1F3EF, a light surface
  bypassCSP: false,
  serviceWorkers: 'block',
};

/**
 * Injected into every page before its own scripts run.
 * Kills smooth scrolling and the text caret, both of which are non-deterministic
 * frame-to-frame. Also sets a flag the player may read to suppress any debug UI.
 */
export const INIT_SCRIPT = `
  window.__CRUCIBLE_CAPTURE = true;
  document.addEventListener('DOMContentLoaded', () => {
    const style = document.createElement('style');
    style.setAttribute('data-crucible-capture', 'true');
    style.textContent =
      'html, body, * { scroll-behavior: auto !important; }' +
      '* { caret-color: transparent !important; }';
    document.head.appendChild(style);
  });
`;

// ---------------------------------------------------------------------------
// Exit codes. Documented here so the README and the scripts cannot drift.
// ---------------------------------------------------------------------------

export const EXIT = {
  /** Recorded, and every postcondition was observed to PASS. */
  OK: 0,
  /** Recorded, and at least one postcondition FAILED. The take is bad. */
  POSTCONDITION_FAILED: 1,
  /** Never got as far as recording. A precondition was missing. */
  PRECONDITION_FAILED: 2,
  /**
   * Recorded, nothing failed, but at least one property could not be checked.
   * Distinct from OK on purpose: "not measured" must never read as "passed".
   */
  UNVERIFIED: 3,
};
