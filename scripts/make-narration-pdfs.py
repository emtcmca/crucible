#!/usr/bin/env python
"""One printable PDF per narration segment, parsed from the locked script.

WHY THIS PARSES RATHER THAN RETYPES. The words Eric reads on camera exist in
exactly one place, `docs/design/narration-LOCKED-2026-08-27.md`. A printable
copy typed out by hand would be a second source of truth for the one artifact
that cannot be re-cut cheaply, and this repository has paid for that shape
repeatedly - most recently on 2026-08-29, when a single corrected line turned
out to exist in six files and five of them were still wrong.

So this reads the locked file, extracts each segment's SPOKEN lines, and fails
loudly if the file's shape has moved. It never edits the words.

WHAT IT REFUSES. If it cannot find all five segments, or a segment has no
spoken lines, it exits non-zero rather than emitting a short deck. A generator
that silently produces four pages out of five is a check that passes while
measuring nothing, and the person holding the paper in a car at midnight is in
no position to notice.

    python scripts/make-narration-pdfs.py
    python scripts/make-narration-pdfs.py --wpm 150
"""

import argparse
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "design" / "narration-LOCKED-2026-08-27.md"
OUTDIR = ROOT / "docs" / "design" / "recording"

# The segments that are recordable. N6 to N9 read figures off a run that has
# not happened, and the locked script's own STOP HERE says so. Emitting a blank
# page for them would invite improvising into it.
EXPECTED = ("N1", "N2", "N3", "N4", "N5")

# Reading pace. 150 is a normal narration pace; the locked script's timings were
# written against a faster one and it says outright that they are targets rather
# than constraints. Both numbers are printed so the gap is visible rather than
# discovered in the edit.
DEFAULT_WPM = 150

_HEAD = re.compile(r"^##\s+(N[1-9])\s*(?:·|\u00b7|-)?\s*(.*)$")
_FENCE = re.compile(r"^```\s*$")


class NarrationError(RuntimeError):
    pass


def parse(text):
    """The locked file -> [{id, heading, scripted, spoken, onscreen}].

    Spoken lines are the fenced blocks under a SAY marker. Everything else in a
    segment is stage direction and is summarised, not printed at reading size:
    a page that mixes what to say with what to do gets read aloud in the car.
    """
    segments = []
    current = None
    in_fence = False
    saying = False

    for line in text.splitlines():
        head = _HEAD.match(line)
        if head and not in_fence:
            if current:
                segments.append(current)
            gid, rest = head.group(1), head.group(2).strip()
            scripted = ""
            m = re.search(r"(\d+:\d{2})\s*[-\u2013\u2014]\s*(\d+:\d{2})", rest)
            if m:
                scripted = "%s to %s" % (m.group(1), m.group(2))
            current = {"id": gid, "heading": rest, "scripted": scripted,
                       "spoken": [], "onscreen": []}
            saying = False
            continue
        if current is None:
            continue

        if _FENCE.match(line):
            in_fence = not in_fence
            # A FENCE BOUNDARY IS A PARAGRAPH BREAK. Each fenced SAY block is
            # its own beat, and the stage direction between two of them is
            # exactly where the reader is meant to pause. Without this the last
            # sentence of one beat ran into the first of the next as a single
            # paragraph, which reads aloud as one breath and lost the pause the
            # direction exists to create.
            if not in_fence and saying:
                current["spoken"].append("")
            continue

        if in_fence:
            if saying:
                current["spoken"].append(line.rstrip())
            else:
                # A fenced block that is not under SAY is something to TYPE on
                # screen, not to read aloud. It belongs in the direction column.
                current["onscreen"].append(line.rstrip())
            continue

        if "**SAY" in line:
            saying = True
            continue
        if line.startswith("**ON SCREEN"):
            saying = False
            current["onscreen"].append(
                re.sub(r"\*\*|`", "", line).replace("ON SCREEN", "").strip(" :-"))
            continue
        if line.strip().startswith("*(") and line.strip().endswith(")*"):
            current["spoken"].append("[[%s]]" % line.strip()[2:-2].strip())

    if current:
        segments.append(current)

    keep = [s for s in segments if s["id"] in EXPECTED]
    found = [s["id"] for s in keep]
    missing = [g for g in EXPECTED if g not in found]
    if missing:
        raise NarrationError(
            "%s has no section for %s. The printable deck is generated from that "
            "file and nowhere else, so a missing segment means the parser and the "
            "script have diverged - fix one of them rather than printing a short "
            "deck." % (SOURCE.name, ", ".join(missing)))
    for s in keep:
        if not [ln for ln in s["spoken"] if ln.strip()]:
            raise NarrationError(
                "%s parsed with no spoken lines. A page with a heading and no "
                "words is worse than no page: it reads as a segment that was "
                "deliberately left silent." % s["id"])
    return keep


def blocks(spoken):
    """Spoken lines -> paragraphs, keeping blank lines as breath breaks."""
    out, cur = [], []
    for line in spoken:
        if line.strip():
            cur.append(line.strip())
        elif cur:
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return out


def words(paras):
    return sum(len(p.split()) for p in paras if not p.startswith("[["))


def mmss(seconds):
    return "%d:%02d" % (int(seconds) // 60, int(seconds) % 60)


CSS = """
@page { size: letter; margin: 0.6in 0.7in; }
* { box-sizing: border-box; }
body { font-family: Georgia, 'Times New Roman', serif; color: #000;
       background: #fff; margin: 0; }
.seg { page-break-after: always; }
.seg:last-child { page-break-after: auto; }
.slate { border: 3px solid #000; padding: 10px 14px; margin-bottom: 16px; }
.slate .id { font-family: Arial, Helvetica, sans-serif; font-size: 34pt;
             font-weight: bold; letter-spacing: 1px; line-height: 1.1; }
.slate .say-this { font-family: Arial, Helvetica, sans-serif; font-size: 13pt;
                   margin-top: 4px; }
.meta { font-family: Arial, Helvetica, sans-serif; font-size: 10.5pt;
        border-bottom: 1.5px solid #000; padding-bottom: 8px; margin-bottom: 18px; }
.meta b { font-weight: bold; }
.direction { font-family: Arial, Helvetica, sans-serif; font-size: 10.5pt;
             background: #eee; border-left: 4px solid #888; padding: 8px 10px;
             margin-bottom: 18px; }
.direction .lbl { font-weight: bold; text-transform: uppercase;
                  letter-spacing: 1px; font-size: 9pt; display: block;
                  margin-bottom: 3px; }
.direction code { font-family: 'Courier New', monospace; font-size: 10pt; }
p.say { font-size: 20pt; line-height: 1.55; margin: 0 0 18pt 0;
        max-width: 34em; }
p.beat { font-family: Arial, Helvetica, sans-serif; font-size: 12pt;
         font-style: italic; color: #444; margin: 0 0 18pt 0; }
/* NOT position:fixed. A fixed footer paints OVER the last paragraph on any
   page that fills, and the first render of N4 lost its closing lines behind
   this element while reporting success. It is a normal trailing block now, so
   long segments simply flow onto a second page. */
.foot { font-family: Arial, Helvetica, sans-serif; font-size: 9pt; color: #555;
        border-top: 1px solid #bbb; padding-top: 4px; margin-top: 22pt; }
p.say { orphans: 3; widows: 3; }
.cover h1 { font-family: Arial, Helvetica, sans-serif; font-size: 26pt; margin: 0 0 4px 0; }
.cover h2 { font-family: Arial, Helvetica, sans-serif; font-size: 12pt;
            font-weight: normal; color: #444; margin: 0 0 22px 0; }
.cover ol { font-size: 13.5pt; line-height: 1.7; padding-left: 22px; }
.cover .warn { border: 2px solid #000; padding: 10px 14px; margin: 18px 0;
               font-family: Arial, Helvetica, sans-serif; font-size: 12pt; }
table.toc { border-collapse: collapse; width: 100%; margin-top: 14px;
            font-family: Arial, Helvetica, sans-serif; font-size: 11pt; }
table.toc th, table.toc td { border-bottom: 1px solid #ccc; padding: 5px 6px;
                             text-align: left; }
"""


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def segment_html(seg, wpm, index, total):
    paras = blocks(seg["spoken"])
    n = words(paras)
    est = n / wpm * 60.0

    body = []
    body.append('<div class="seg">')
    body.append('<div class="slate">')
    body.append('<div class="id">%s &nbsp;of &nbsp;%d</div>' % (seg["id"], total))
    body.append('<div class="say-this">Before you read: say &ldquo;%s, take one&rdquo; '
                'out loud, then wait two seconds.</div>' % seg["id"])
    body.append('</div>')

    body.append('<div class="meta">')
    body.append('<b>%s</b> &nbsp;&bull;&nbsp; %d words &nbsp;&bull;&nbsp; '
                'about <b>%s</b> at %d wpm' % (esc(seg["heading"]), n, mmss(est), wpm))
    if seg["scripted"]:
        body.append(' &nbsp;&bull;&nbsp; script says %s' % esc(seg["scripted"]))
    body.append('</div>')

    if seg["onscreen"]:
        body.append('<div class="direction"><span class="lbl">On screen '
                    '(not read aloud)</span>')
        for d in seg["onscreen"]:
            if d.strip():
                body.append('<div><code>%s</code></div>' % esc(d.strip()))
        body.append('</div>')

    for p in paras:
        if p.startswith("[["):
            body.append('<p class="beat">&mdash; %s &mdash;</p>' % esc(p[2:-2]))
        else:
            body.append('<p class="say">%s</p>' % esc(p))

    body.append('<div class="foot">%s &nbsp;|&nbsp; generated from '
                'docs/design/narration-LOCKED-2026-08-27.md &nbsp;|&nbsp; '
                'page %d of %d</div>' % (seg["id"], index, total))
    body.append('</div>')
    return "\n".join(body)


def cover_html(segs, wpm):
    total_words = sum(words(blocks(s["spoken"])) for s in segs)
    total_secs = total_words / wpm * 60.0
    rows = []
    for s in segs:
        n = words(blocks(s["spoken"]))
        rows.append("<tr><td><b>%s</b></td><td>%s</td><td>%d</td><td>%s</td>"
                    "<td>%s</td></tr>"
                    % (s["id"], esc(s["heading"][:54]), n,
                       mmss(n / wpm * 60.0), esc(s["scripted"] or "-")))
    return """
<div class="seg cover">
<h1>CRUCIBLE &mdash; recording script</h1>
<h2>Segments N1 to N5. One voice note per segment.</h2>
<div class="warn">
<b>Before the first take: record 60 seconds of room tone.</b> Sit still, engine
off, say nothing. It is the single most useful thing on the card and it cannot
be recreated later.
</div>
<ol>
<li>One take per segment. They cut together, so a fluffed line costs one segment
    and not the read.</li>
<li>Slate each take out loud &mdash; &ldquo;N3, take one&rdquo; &mdash; then wait
    two seconds before the first word.</li>
<li>Two seconds of silence at the end too, before you stop recording.</li>
<li>Read at your own pace. <b>The timings below are estimates, not targets.</b>
    The locked script says the same thing: the narration&rsquo;s real length sets
    the cue list, not the other way round.</li>
<li>Grey boxes are what appears on screen. <b>Do not read them aloud.</b></li>
<li>If you stumble, pause, breathe, and start that paragraph again. Do not start
    the segment over.</li>
</ol>
<table class="toc">
<tr><th>Segment</th><th>What it is</th><th>Words</th>
    <th>Estimate at %d wpm</th><th>Script target</th></tr>
%s
<tr><td colspan="2"><b>Total</b></td><td><b>%d</b></td>
    <td><b>%s</b></td><td>-</td></tr>
</table>
<div class="foot">generated from docs/design/narration-LOCKED-2026-08-27.md</div>
</div>
""" % (wpm, "\n".join(rows), total_words, mmss(total_secs))


def page(title, inner):
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            "<title>%s</title><style>%s</style></head><body>%s</body></html>"
            % (esc(title), CSS, inner))


def chrome():
    """A Chromium that can print to PDF, or None.

    Resolved rather than assumed: printing is the last step and discovering
    there is no renderer AFTER writing five HTML files would report success on
    a deck nobody can print.
    """
    for cand in ("chrome", "chrome.exe", "msedge", "msedge.exe"):
        found = shutil.which(cand)
        if found:
            return found
    for p in (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"):
        if pathlib.Path(p).is_file():
            return p
    return None


def to_pdf(exe, html_path, pdf_path):
    subprocess.run(
        [exe, "--headless", "--disable-gpu", "--no-pdf-header-footer",
         "--print-to-pdf=%s" % pdf_path, html_path.as_uri()],
        capture_output=True, timeout=120)
    # ASSERT THE POSTCONDITION, NOT THE EXIT CODE. Headless Chrome exits 0 on
    # several failures that produce no file, and a printed "done" over a missing
    # PDF is the exact shape this repository keeps catching.
    if not pdf_path.is_file() or pdf_path.stat().st_size < 1200:
        raise NarrationError(
            "%s was not produced, or came out too small to contain a page "
            "(%d bytes). The renderer reported nothing useful; do not trust a "
            "silent success here."
            % (pdf_path.name, pdf_path.stat().st_size if pdf_path.is_file() else 0))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wpm", type=int, default=DEFAULT_WPM)
    ap.add_argument("--outdir", default=str(OUTDIR))
    args = ap.parse_args(argv)

    exe = chrome()
    if exe is None:
        print("REFUSED: no Chrome or Edge found to render the PDF. The HTML "
              "would still be written and would look like success.")
        return 2

    segs = parse(SOURCE.read_text(encoding="utf-8"))
    out = pathlib.Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    made = []
    cover = out / "00-COVER.html"
    cover.write_text(page("CRUCIBLE recording script", cover_html(segs, args.wpm)),
                     encoding="utf-8", newline="")
    to_pdf(exe, cover, out / "00-COVER.pdf")
    made.append(out / "00-COVER.pdf")

    for i, seg in enumerate(segs, start=1):
        h = out / ("%02d-%s.html" % (i, seg["id"]))
        h.write_text(page("%s" % seg["id"],
                          segment_html(seg, args.wpm, i, len(segs))),
                     encoding="utf-8", newline="")
        pdf = out / ("%02d-%s.pdf" % (i, seg["id"]))
        to_pdf(exe, h, pdf)
        made.append(pdf)

    allhtml = out / "ALL-SEGMENTS.html"
    inner = cover_html(segs, args.wpm) + "\n".join(
        segment_html(s, args.wpm, i, len(segs)) for i, s in enumerate(segs, 1))
    allhtml.write_text(page("CRUCIBLE recording script - all segments", inner),
                       encoding="utf-8", newline="")
    to_pdf(exe, allhtml, out / "ALL-SEGMENTS.pdf")
    made.append(out / "ALL-SEGMENTS.pdf")

    print("=" * 74)
    print("RECORDING DECK   %d segments, %d wpm" % (len(segs), args.wpm))
    print("=" * 74)
    for p in made:
        print("  %-26s %7d bytes" % (p.name, p.stat().st_size))
    print()
    for s in segs:
        n = words(blocks(s["spoken"]))
        print("  %-3s %4d words   about %s   script target %s"
              % (s["id"], n, mmss(n / args.wpm * 60.0), s["scripted"] or "-"))
    print()
    print("  %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
