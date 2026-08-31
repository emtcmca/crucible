# Narration takes

One file per beat, named for the beat id in `tools/capture/beats.json`:

    N1.wav  N2.wav  N3.wav  N4.wav  N5.wav
    N6.wav  N7.wav  N8.wav  N9a.wav  N9b.wav

WAV or MP3, either is fine - `assemble.py` measures whatever ffprobe can read.
This directory is gitignored: takes are large binaries, not repo content.

**The narration sets the timing.** Record the beat; the visual is retimed to
your take, not the other way round. A fluffed line costs one beat.

    python tools/capture/assemble.py --check    # free, names every gap
    python tools/capture/assemble.py            # builds out/crucible.mp4

A synthesised voice drops in at the same paths and needs no other change.
