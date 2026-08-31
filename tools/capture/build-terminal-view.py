#!/usr/bin/env python3
"""Build `cards/12-gcp-terminal.html` from a REAL captured transcript.

THE TRANSCRIPT IS NOT EDITED. This classifies each line - command, output,
blank, closing note - so the renderer can pace them, and changes nothing else.
No line is dropped, reordered, shortened or reworded, and the generator refuses
if the transcript is missing its capture header, because a transcript that
cannot say when it was taken is not evidence about anything.

Capture one first:

    powershell -NoProfile -ExecutionPolicy Bypass -File tools/capture/gcp-proof.ps1 -Pause 0.05 `
      | Out-File -Encoding utf8 tools/capture/out/gcp-proof-transcript.txt

then:

    python tools/capture/build-terminal-view.py
"""
import argparse
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent

NOTE_PREFIXES = ("Cloud Run -", "Vertex AI -", "Cloud Storage -", "Gemma on")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript",
                    default=str(HERE / "out" / "gcp-proof-transcript.txt"))
    ap.add_argument("--out", default=str(HERE / "cards" / "12-gcp-terminal.html"))
    args = ap.parse_args()

    src = pathlib.Path(args.transcript)
    if not src.exists():
        sys.exit("no transcript at %s - capture one first (see the docstring)"
                 % src)
    # utf-8-sig: PowerShell's Out-File writes a BOM, and a BOM in front of the
    # header makes the regex below miss it. Standing gotcha in this repo.
    raw = src.read_text(encoding="utf-8-sig").splitlines()

    m = re.match(r"#\s*captured\s+(\S+)\s+by\s+(.+)$", raw[0].strip()) if raw else None
    if not m:
        sys.exit("the transcript has no `# captured <iso> by <command>` header. "
                 "A transcript that cannot say when it was taken, and by what, "
                 "is not evidence about anything.")
    captured_at, command = m.group(1), m.group(2)

    lines = []
    for text in raw[1:]:
        t = text.rstrip()
        if not t.strip():
            kind = "blank"
        elif t.lstrip().startswith("PS>"):
            kind = "cmd"
        elif t.startswith(NOTE_PREFIXES):
            kind = "note"
        elif t.startswith("CRUCIBLE -"):
            # The script's own banner. The card has a header saying the same
            # thing, so this would be the sentence twice on one frame.
            continue
        else:
            kind = "out"
        lines.append({"kind": kind, "text": t})

    # Trim leading/trailing blanks so the frame does not open or close on air.
    while lines and lines[0]["kind"] == "blank":
        lines.pop(0)
    while lines and lines[-1]["kind"] == "blank":
        lines.pop()

    payload = {"captured_at": captured_at, "command": command, "lines": lines}
    tpl = (HERE / "terminal-view.template.html").read_text(encoding="utf-8")
    out = pathlib.Path(args.out)
    out.write_text(tpl.replace("/*__DATA__*/null", json.dumps(payload, indent=1)),
                   encoding="utf-8", newline="")

    kinds = {}
    for l in lines:
        kinds[l["kind"]] = kinds.get(l["kind"], 0) + 1
    print("wrote %s" % out)
    print("  captured %s" % captured_at)
    print("  %d lines  %s" % (len(lines), kinds))


if __name__ == "__main__":
    main()
