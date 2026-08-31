#!/usr/bin/env python3
"""Turn raw narration takes into the WAVs `assemble.py` expects.

Four things, in this order, and the order matters:

  1. DENOISE, lightly. The room floor measured -42 dB mean and -28 dB peak,
     which is about 20 dB under the voice. That is audible in the gaps, and it
     is also why step 2 cannot work first: a silence detector set below the
     floor finds no silence at all, which is exactly what N1 did.
  2. TRIM the head and tail to a fixed 0.25 s. The recording rule asks for two
     seconds at each end so takes can be cut cleanly - correct for editing, and
     11 beats x ~4 s is ~44 s of silence against a 237 s budget the script only
     just fits inside. The padding did its job by existing; it does not need to
     survive into the cut.
  3. LOUDNESS NORMALISE to -14 LUFS, -1.5 dBTP, two pass. The takes came in at
     -24.4, -20.1 and -19.7 LUFS, so N1 was audibly quieter than its
     neighbours, and N2 true-peaked at -0.8 dBFS, which is above YouTube's
     recommended headroom and can clip on re-encode.
  4. WRITE 48 kHz mono WAV, which is what the assembler muxes.

NOTHING HERE IS DESTRUCTIVE. Sources are read; `audio/` is written.

    python tools/capture/prepare-audio.py --src "C:/Users/tetzl/Downloads"
    python tools/capture/prepare-audio.py --src <dir> --only N1 N2
    python tools/capture/prepare-audio.py --src <dir> --report      measure only
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEST = ROOT / "audio"

TARGET_LUFS = -14.0      # what YouTube normalises to
TARGET_TP = -1.5         # dBTP, a little under the -1.0 ceiling
PAD = 0.25               # seconds kept at each end
DENOISE = "afftdn=nr=12:nf=-40"


def sh(args):
    return subprocess.run(args, capture_output=True, text=True)


def measure(path):
    """(lufs, true_peak, duration) or None if it cannot be read."""
    r = sh(["ffmpeg", "-hide_banner", "-i", str(path),
            "-af", "ebur128=peak=true", "-f", "null", "-"])
    # THE LAST MATCH, NOT THE FIRST. ebur128 prints a running value as it goes
    # and the integrated summary at the end; `re.search` was returning the
    # opening -70.0 for every file, which made a real measurement look like a
    # constant and would have hidden whether normalisation did anything.
    lufs_all = re.findall(r"I:\s+(-?\d+\.\d+) LUFS", r.stderr)
    peak_all = re.findall(r"Peak:\s+(-?\d+\.\d+) dBFS", r.stderr)
    lufs = lufs_all[-1] if lufs_all else None
    peak = peak_all[-1] if peak_all else None
    d = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", str(path)])
    try:
        dur = float(d.stdout.strip())
    except ValueError:
        return None
    return (float(lufs) if lufs else None,
            float(peak) if peak else None, dur)


def loudnorm_pass1(path, chain):
    """Measured values for the second loudnorm pass. Two-pass because
    single-pass loudnorm is a live estimate and drifts on short files - and
    every one of these is short."""
    r = sh(["ffmpeg", "-hide_banner", "-i", str(path), "-af",
            "%s,loudnorm=I=%s:TP=%s:print_format=json" % (chain, TARGET_LUFS, TARGET_TP),
            "-f", "null", "-"])
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", r.stderr, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


def prepare(src, beat, denoise=True):
    dest = DEST / (beat + ".wav")
    before = measure(src)
    if before is None:
        return "UNREADABLE", None, None

    # Denoise, then trim from BOTH ends against the now-lower floor. The
    # reverse-trim-reverse pair is how silenceremove trims a tail.
    # THE GATE IS RELATIVE TO THIS TAKE'S OWN PEAK, NOT A CONSTANT.
    #
    # A fixed -50 dB gate trimmed N2 and N3 and silently did nothing to N1,
    # whose room floor sits above it. The result shipped: 1.75 s of dead air
    # before the first word, which pushed the line past its beat boundary and
    # ran it over the top of the next one. The trim reported success and
    # changed nothing, which is the shape this repository keeps finding.
    #
    # peak - 30 dB tracks the take instead. A quiet take gets a quiet gate and
    # a loud one a loud gate, and neither depends on the room being as quiet
    # as some number written down in advance. Floored at -55 dB so a
    # pathologically hot take cannot start clipping its own first syllable.
    peak = before[1] if before and before[1] is not None else -3.0
    gate = max(peak - 30.0, -55.0)
    if not denoise:
        gate = max(gate, -40.0)     # the floor is ~15 dB higher without it
    thresh = "%.1fdB" % gate
    trim = ("silenceremove=start_periods=1:start_silence=%s:start_threshold=%s,"
            "areverse,"
            "silenceremove=start_periods=1:start_silence=%s:start_threshold=%s,"
            "areverse" % (PAD, thresh, PAD, thresh))
    chain = "%s,%s" % (DENOISE, trim) if denoise else trim

    stats = loudnorm_pass1(src, chain)
    if stats:
        norm = ("loudnorm=I=%s:TP=%s:measured_I=%s:measured_TP=%s:"
                "measured_LRA=%s:measured_thresh=%s:linear=true"
                % (TARGET_LUFS, TARGET_TP, stats["input_i"], stats["input_tp"],
                   stats["input_lra"], stats["input_thresh"]))
    else:
        # A take too short or too quiet to measure still gets normalised, just
        # in one pass. Saying so beats silently shipping a different treatment.
        norm = "loudnorm=I=%s:TP=%s" % (TARGET_LUFS, TARGET_TP)

    r = sh(["ffmpeg", "-y", "-hide_banner", "-i", str(src),
            "-af", "%s,%s" % (chain, norm),
            "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(dest)])
    if r.returncode != 0:
        return "FFMPEG FAILED", before, None
    return ("OK" if stats else "OK (1-pass)"), before, measure(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True,
                    help="directory holding the raw takes, named <beat>.m4a/.wav/.mp3")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--report", action="store_true",
                    help="measure the sources and write nothing")
    ap.add_argument("--no-denoise", action="store_true",
                    help="skip the noise reduction. USE THIS IF THE VOICE "
                         "SOUNDS THIN, WATERY OR PHASEY - afftdn is judged by "
                         "ear and nothing in this pipeline can hear. Trimming "
                         "and loudness normalisation still run; the silence "
                         "threshold is relaxed to compensate for the higher "
                         "floor.")
    args = ap.parse_args()

    src_dir = pathlib.Path(args.src)
    if not src_dir.is_dir():
        sys.exit("no such directory: %s" % src_dir)

    beats = json.loads((HERE / "beats.json").read_text(encoding="utf-8"))["beats"]
    wanted = [b["id"] for b in beats if b.get("audio")]
    if args.only:
        wanted = [b for b in wanted if b in args.only]

    DEST.mkdir(exist_ok=True)
    found, missing = [], []
    for beat in wanted:
        hit = None
        for ext in (".m4a", ".wav", ".mp3", ".aac", ".mp4"):
            p = src_dir / (beat + ext)
            if p.exists():
                hit = p
                break
        if hit is None:
            missing.append(beat)
        else:
            found.append((beat, hit))

    print("%-5s %-9s %-22s %s" % ("beat", "status", "before", "after"))
    print("-" * 74)
    total = 0.0
    for beat, src in found:
        if args.report:
            b = measure(src)
            print("%-5s %-9s %6.1f LUFS %5.1f dBTP %5.1fs"
                  % (beat, "source", b[0] or 0, b[1] or 0, b[2]))
            total += b[2]
            continue
        status, b, a = prepare(src, beat, denoise=not args.no_denoise)
        if a:
            print("%-5s %-9s %6.1f LUFS %5.1f dBTP %5.1fs  ->  %5.1f LUFS %5.1f dBTP %5.1fs"
                  % (beat, status, b[0] or 0, b[1] or 0, b[2],
                     a[0] or 0, a[1] or 0, a[2]))
            total += a[2]
        else:
            print("%-5s %-9s" % (beat, status))

    print()
    if missing:
        print("NOT YET RECORDED: %s" % ", ".join(missing))
    print("prepared %d of %d beats, %.1fs of audio so far"
          % (len(found) - (0 if args.report else 0), len(wanted), total))
    if found and not args.report:
        print("wrote to %s" % DEST)


if __name__ == "__main__":
    main()
