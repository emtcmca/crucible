#!/usr/bin/env python3
"""Stitch narration audio to visuals and emit the finished video.

THE NARRATION SETS THE TIMING, NOT THE ANIMATION. For every beat this measures
the audio, then makes the visual last exactly that long:

  * a still is held for the audio's duration;
  * a player is RE-CAPTURED at that duration through capture.mjs, so the
    animation stretches to the take. This is what the cue file's own provenance
    says to do - "the recorded take sets the real timestamps: re-cut this file
    against the take, never the animation" - and it is the reason the players
    were built deterministic by seek.

  python tools/capture/assemble.py --check      what is missing, nothing built
  python tools/capture/assemble.py              build tools/capture/out/crucible.mp4

WORKS THE SAME FOR A SYNTHESISED VOICE. A beat's audio is a file; nothing here
cares how it was made. If the recording block is lost, drop the generated
takes in at the same paths and run it again.

RUN --check FIRST AND OFTEN. It is free, it names every gap, and it prints the
running total against the four minute cap - which is a hard cap, not a target.
"""
import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
WORK = OUT / "beats"
CAP_S = 240.0


def sh(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def duration(path):
    """Seconds, from ffprobe. None if it cannot be read."""
    r = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", str(path)])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def build_clip(src, seconds, dest):
    """A screen recording, fitted to its narration.

    LONGER THAN THE TAKE: trimmed. SHORTER: it HOLDS ON ITS LAST FRAME rather
    than the voice being cut off. That direction is deliberate - a beat whose
    audio outlives its footage is a recoverable inconvenience, and a beat whose
    footage outlives its audio silently eats the next line.

    Also normalised to 1920x1080 at 30fps, because a screen recording arrives
    at whatever the capture tool felt like and `concat -c copy` refuses to
    join clips whose parameters differ.
    """
    have = duration(src) or seconds
    if have >= seconds:
        vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
              "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x14110F")
        sh(["ffmpeg", "-y", "-i", str(src), "-t", "%.3f" % seconds,
            "-r", "30", "-vf", vf, "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(dest)], check=False)
    else:
        # tpad clones the final frame for the shortfall.
        pad = seconds - have
        vf = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
              "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x14110F,"
              "tpad=stop_mode=clone:stop_duration=%.3f" % pad)
        sh(["ffmpeg", "-y", "-i", str(src), "-r", "30", "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p", "-an", str(dest)], check=False)
        print("    %s is %.1fs against %.1fs of narration - holding the last "
              "frame for %.1fs" % (src.name, have, seconds, pad))
    return dest


def build_still(png, seconds, dest):
    """A held frame, encoded to match everything else in the timeline."""
    sh(["ffmpeg", "-y", "-loop", "1", "-i", str(png), "-t", "%.3f" % seconds,
        "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-vf", "scale=1920:1080", str(dest)], check=False)
    return dest


def build_player(html, player, seconds, dest, beat_id):
    """Re-capture the player at the take's length. Deterministic by seek."""
    frames = WORK / ("frames-" + beat_id)
    r = sh(["node", str(HERE / "capture.mjs"), "player",
            "--url", str(ROOT / html), "--global", player,
            "--duration", str(int(seconds * 1000)),
            "--frames", str(frames), "--out", str(dest), "--fps", "30"],
           cwd=str(HERE))
    if r.returncode != 0:
        sys.exit("capture failed for %s:\n%s" % (beat_id, r.stdout + r.stderr))
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--beats", default=str(HERE / "beats.json"))
    ap.add_argument("--out", default=str(OUT / "crucible.mp4"))
    args = ap.parse_args()

    spec = json.loads(pathlib.Path(args.beats).read_text(encoding="utf-8"))
    WORK.mkdir(parents=True, exist_ok=True)

    rows, total, missing = [], 0.0, []
    for b in spec["beats"]:
        vis = ROOT / b["visual"]
        aud = ROOT / b["audio"] if b.get("audio") else None

        if aud is not None and not aud.exists():
            missing.append("%-5s audio  %s" % (b["id"], b["audio"]))
            secs = None
        elif aud is not None:
            secs = duration(aud)
            if secs is None:
                missing.append("%-5s audio unreadable  %s" % (b["id"], b["audio"]))
        else:
            secs = (b.get("hold_ms", 3000)) / 1000.0

        if not vis.exists():
            missing.append("%-5s visual %s%s" % (
                b["id"], b["visual"],
                "   <- " + b["live_alternative"] if b.get("live_alternative") else ""))

        if secs:
            total += secs
        rows.append((b, vis, aud, secs))

    print("BEATS")
    for b, vis, aud, secs in rows:
        print("  %-5s %-7s %s" % (
            b["id"],
            ("%.1fs" % secs) if secs else "   ?",
            b["visual"]))
    print()
    print("  running total  %.1fs of %.0fs cap%s"
          % (total, CAP_S, "   OVER THE CAP" if total > CAP_S else ""))
    if missing:
        print()
        print("MISSING - nothing was built:")
        for m in missing:
            print("  " + m)
    if args.check:
        return 1 if missing else 0
    if missing:
        sys.exit("refusing to build with gaps. Run --check.")
    if total > CAP_S:
        sys.exit("refusing to build: %.1fs is over the %.0fs cap. The cap is "
                 "hard - a judge does not watch the overflow, the upload "
                 "rejects it." % (total, CAP_S))

    # ---- per-beat clips ---------------------------------------------------
    clips = []
    for b, vis, aud, secs in rows:
        dest = WORK / (b["id"] + ".mp4")
        print("  building %s (%.1fs)" % (b["id"], secs))
        if vis.suffix == ".html":
            build_player(b["visual"], b.get("player", "__cuePlayer"),
                         secs, dest, b["id"])
        elif vis.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm"):
            build_clip(vis, secs, dest)
        else:
            build_still(vis, secs, dest)

        if aud is not None:
            muxed = WORK / (b["id"] + "-av.mp4")
            # -shortest so a clip cannot outlive its narration, and AAC because
            # it is what every upload path accepts without transcoding again.
            sh(["ffmpeg", "-y", "-i", str(dest), "-i", str(aud),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", str(muxed)], check=False)
            clips.append(muxed)
        else:
            silent = WORK / (b["id"] + "-av.mp4")
            sh(["ffmpeg", "-y", "-i", str(dest), "-f", "lavfi",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-c:v", "copy", "-c:a", "aac", "-shortest", str(silent)],
               check=False)
            clips.append(silent)

    # ---- concat -----------------------------------------------------------
    lst = WORK / "concat.txt"
    lst.write_text("".join("file '%s'\n" % c.as_posix() for c in clips),
                   encoding="utf-8")
    out = pathlib.Path(args.out)
    r = sh(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
            "-c", "copy", str(out)])
    if r.returncode != 0:
        sys.exit("concat failed:\n" + r.stderr[-2000:])

    final = duration(out)
    print()
    print("wrote %s" % out)
    print("  %.1fs  (%.0fs cap)" % (final, CAP_S))
    if final > CAP_S:
        print("  OVER THE CAP - do not upload this cut.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
