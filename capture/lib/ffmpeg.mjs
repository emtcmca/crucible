// lib/ffmpeg.mjs — locate and run the ffmpeg binary Playwright ships.
//
// Playwright downloads its own ffmpeg into the browser cache because that is
// what muxes the .webm it records. So if video recording works at all, this
// binary exists. We use the same one to READ the file back, which keeps the
// verifier free of any dependency the recorder does not already have.
//
// If it cannot be found, callers must report UNVERIFIED for anything that
// needed it. They must not skip the check silently.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';

/** The per-platform filename Playwright gives its ffmpeg build. */
function ffmpegBinaryName() {
  if (process.platform === 'win32') return 'ffmpeg-win64.exe';
  if (process.platform === 'darwin') return 'ffmpeg-mac';
  return 'ffmpeg-linux';
}

/** Root of the Playwright browser cache, honouring the standard override. */
export function browsersRoot() {
  if (process.env.PLAYWRIGHT_BROWSERS_PATH && process.env.PLAYWRIGHT_BROWSERS_PATH !== '0') {
    return process.env.PLAYWRIGHT_BROWSERS_PATH;
  }
  const home = os.homedir();
  if (process.platform === 'win32') {
    return process.env.LOCALAPPDATA
      ? path.join(process.env.LOCALAPPDATA, 'ms-playwright')
      : path.join(home, 'AppData', 'Local', 'ms-playwright');
  }
  if (process.platform === 'darwin') {
    return path.join(home, 'Library', 'Caches', 'ms-playwright');
  }
  return path.join(home, '.cache', 'ms-playwright');
}

/**
 * Find the newest ffmpeg-<revision> in the browser cache.
 * Returns an absolute path, or null when there is none. Never throws.
 */
export function findFfmpeg() {
  // An explicit override wins, for a machine with a system ffmpeg on PATH.
  if (process.env.CRUCIBLE_FFMPEG && fs.existsSync(process.env.CRUCIBLE_FFMPEG)) {
    return process.env.CRUCIBLE_FFMPEG;
  }
  const root = browsersRoot();
  let entries;
  try {
    entries = fs.readdirSync(root);
  } catch {
    return null;
  }
  const candidates = entries
    .filter((name) => name.startsWith('ffmpeg-'))
    // Sort by the numeric revision suffix so the newest build wins.
    .sort((a, b) => Number(b.split('-')[1] || 0) - Number(a.split('-')[1] || 0))
    .map((name) => path.join(root, name, ffmpegBinaryName()))
    .filter((p) => fs.existsSync(p));
  return candidates[0] || null;
}

/**
 * Run ffmpeg and collect stdout as a Buffer plus stderr as a string.
 * ffmpeg writes all of its diagnostics to stderr, so a non-empty stderr is
 * normal and is not by itself an error.
 */
export function runFfmpeg(binary, args, { maxStdoutBytes = 256 * 1024 * 1024 } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(binary, args, { windowsHide: true });
    const stdout = [];
    let stdoutBytes = 0;
    let stderr = '';
    child.stdout.on('data', (chunk) => {
      stdoutBytes += chunk.length;
      if (stdoutBytes > maxStdoutBytes) {
        child.kill();
        reject(new Error(`ffmpeg produced more than ${maxStdoutBytes} bytes on stdout`));
        return;
      }
      stdout.push(chunk);
    });
    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString('utf8');
    });
    child.on('error', reject);
    child.on('close', (code) => {
      resolve({ code, stdout: Buffer.concat(stdout), stderr });
    });
  });
}
