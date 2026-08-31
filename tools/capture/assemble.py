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

# A BEAT, THEN A BREATH.
#
# `prepare-audio` trims each take to 0.25s of padding a side, which is right for
# the take and wrong for the cut: beats landed hard against each other and the
# whole thing read breathless. The fix belongs here rather than in the trim -
# the trim's job is to remove dead air the microphone recorded, and this is an
# editing decision about pace.
#
# Each beat's LAST FRAME is held for GAP_S with silence under it, so the picture
# settles instead of cutting. Cheap: 13 beats at 0.7s is 9.1s against a 240s cap
# the cut clears by 35.
GAP_S = 0.7


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
    fit = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
           "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x14110F")
    if have >= seconds:
        # SPED UP TO FIT, NOT TRUNCATED.
        #
        # Truncation was the first behaviour and it throws away the END of the
        # clip, which on every one of these takes is where the payoff is: the
        # hash locks on the replay, VERDICT PASS on the seal proof, the Gemma
        # http 200 on the cloud beat. A trim to length would have silently cut
        # the frame the beat exists for. Terminal output reads fine a little
        # fast; a missing conclusion does not read at all.
        rate = have / seconds
        vf = "setpts=PTS/%.6f,%s" % (rate, fit)
        if rate > 2.0:
            print("    %s is %.1fs against %.1fs of narration - speeding it "
                  "%.2fx, which is a lot. Consider a longer take or a shorter "
                  "line." % (src.name, have, seconds, rate))
        elif rate > 1.05:
            print("    %s sped %.2fx to fit %.1fs of narration (was %.1fs), so "
                  "the end of the clip survives" % (src.name, rate, seconds, have))
        sh(["ffmpeg", "-y", "-i", str(src), "-vf", vf, "-t", "%.3f" % seconds,
            "-r", "30", "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(dest)], check=False)
    else:
        # tpad clones the final frame for the shortfall.
        pad = seconds - have
        vf = "%s,tpad=stop_mode=clone:stop_duration=%.3f" % (fit, pad)
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
            total += secs + GAP_S
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
    print("                 (includes %.1fs of inter-beat gap at %.2fs each)"
          % (GAP_S * len([r for r in rows if r[3]]), GAP_S))
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

        # EVERY SEGMENT GETS IDENTICAL AUDIO PARAMETERS, AND THAT IS NOT
        # TIDINESS.
        #
        # `concat -c copy` writes the container with the FIRST segment's stream
        # parameters and then streams the rest in unchanged. The title card was
        # stereo (from anullsrc) and every narrated beat was mono (from a mono
        # WAV), so the finished file declared stereo and carried mono packets.
        # ffmpeg decodes each packet by its own header and reported healthy
        # audio at every timestamp; an ordinary player trusts the container and
        # plays nothing. Eric heard silence on a file that measured -13.4 LUFS.
        #
        # The lesson is the one this repository keeps relearning: the check was
        # run with the one tool tolerant enough to hide what it was checking
        # for.
        muxed = WORK / (b["id"] + "-av.mp4")
        total = secs + GAP_S
        # tpad clones the final video frame; apad extends the audio with
        # silence. Both to the SAME length, so the two streams cannot drift -
        # and `-t` rather than `-shortest`, because -shortest would cut the
        # gap back off at the end of the audio, which is the thing being added.
        vpad = "tpad=stop_mode=clone:stop_duration=%.3f" % GAP_S
        if aud is not None:
            sh(["ffmpeg", "-y", "-i", str(dest), "-i", str(aud),
                "-vf", vpad, "-af", "apad=pad_dur=%.3f" % GAP_S,
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                "-t", "%.3f" % total, str(muxed)], check=False)
        else:
            sh(["ffmpeg", "-y", "-i", str(dest), "-f", "lavfi",
                "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-vf", vpad,
                "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                "-t", "%.3f" % total, str(muxed)], check=False)
        clips.append(muxed)

    # ---- REFUSE TO CONCAT MISMATCHED STREAMS ------------------------------
    #
    # The guard the last build did not have. `-c copy` cannot reconcile
    # differing stream parameters and does not try; it takes the first and
    # hopes. Checking here turns a silent wrong answer into a stopped build.
    params = {}
    for c in clips:
        r = sh(["ffprobe", "-v", "error", "-select_streams", "a:0",
                "-show_entries", "stream=codec_name,channels,sample_rate",
                "-of", "csv=p=0", str(c)])
        params.setdefault(r.stdout.strip(), []).append(c.name)
    if len(params) > 1:
        print()
        print("REFUSING TO CONCAT - the segments do not share audio parameters.")
        print("`-c copy` would write the first one's header over all of them,")
        print("and the result plays silence in anything less tolerant than")
        print("ffmpeg itself:")
        for k, names in sorted(params.items()):
            print("  %-28s %s" % (k, ", ".join(sorted(names))))
        sys.exit(1)
    print("  audio parameters identical across %d segments: %s"
          % (len(clips), list(params)[0]))

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
