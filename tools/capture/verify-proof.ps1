# verify-proof.ps1 - the second on-camera beat: the claims a judge can check.
#
# WHY THIS ONE EARNS ITS PLACE AND COSTS NOTHING. Both frames illustrate lines
# the narration ALREADY says, so neither needs a word of new script against a
# hard 4:00 cap that the copy only just fits inside:
#
#   N5  "the replay tool needs no credentials to check them"  -> frame 1
#   N9  "the held-out family is still sealed"                 -> frame 2
#
# A claim spoken over a card is a claim. The same claim spoken over the command
# that checks it is a demonstration, and this project's whole argument is the
# difference between those two.
#
# BOTH ARE READ-ONLY. The replay opens no socket and reads no credential - that
# is enforced by an AST lint over the package plus a test that runs the viewer
# with the environment stripped and the socket module replaced by something
# that raises. The seal proof reads files and git, and touches no bucket.
#
# COMMIT OR STASH BEFORE YOU ROLL. The seal proof refuses on a dirty working
# tree - deliberately - so an uncommitted file anywhere in the repo puts a red
# VERDICT FAIL on camera. `git status` should be empty before this runs.
#
# Usage (Windows PowerShell 5.1 - there is no pwsh here):
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\capture\verify-proof.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\capture\verify-proof.ps1 -Pause 2.5

param(
  [double]$Pause = 2.0,
  [string]$Bundle = "evidence/batch-measure-2026-08-27/run-01.c6.json",

  # SHOOT THESE AS TWO TAKES. Together they are ~52 lines, which overflows a
  # 1080p terminal at a legible font size and scrolls the head off - and the
  # head is where the digest and the locks are. Each half fits on its own.
  #   -Only replay   the offline reader, ~30 lines
  #   -Only seal     the seal proof, ~18 lines
  [ValidateSet("both", "replay", "seal")]
  [string]$Only = "both"
)

$ErrorActionPreference = "Stop"

function Beat($cmd) {
  Write-Host ""
  Write-Host "PS> " -NoNewline -ForegroundColor DarkGray
  foreach ($ch in $cmd.ToCharArray()) {
    Write-Host $ch -NoNewline -ForegroundColor White
    Start-Sleep -Milliseconds 12
  }
  Write-Host ""
  Start-Sleep -Milliseconds 350
  Invoke-Expression $cmd
  Start-Sleep -Seconds $Pause
}

Clear-Host
$banner = switch ($Only) {
  "replay" { "CRUCIBLE - replay the evidence yourself, offline" }
  "seal"   { "CRUCIBLE - is the held-out family still sealed?" }
  default  { "CRUCIBLE - the two things you can check without asking me" }
}
Write-Host $banner -ForegroundColor DarkYellow
Start-Sleep -Seconds $Pause

# 1. THE OFFLINE REPLAY, ON A REAL BUNDLE - not the golden fixture.
#    The README ships this command pointed at contracts/golden/, which is a
#    hand-authored schema instance and says so. Pointing it at a bundle from
#    the 08-27 measurement batch shows the same thing about REAL evidence: the
#    digest is recomputed from the bytes on disk, and the five locks come back
#    out of the file rather than out of a claim.
# THE FULL REPLAY IS 600+ LINES AND SCROLLS THE FRAME OFF THE TOP INSTANTLY.
# Everything that matters for this beat is in the head: the digest recomputed
# from the bytes on disk, the "no credentials, no network, no cloud project"
# line, the run identity, and the five hash locks. The rest is per-round
# detail nobody can read at speed anyway.
#
# The total is PRINTED, not hidden. Showing 24 of 663 lines without saying so
# would be a frame that implies the output is short.
if ($Only -ne "seal") {
  $replay = python -m crucible.replay $Bundle
  Beat "python -m crucible.replay $Bundle | Select-Object -First 24"
  Write-Host ("      ... {0} more lines: per-round census, gate decisions, and the" -f ($replay.Count - 24)) -ForegroundColor DarkGray
  Write-Host "      full episode ledger. All of it read from the same file." -ForegroundColor DarkGray
  Start-Sleep -Seconds $Pause
}

# 2. THE SEAL, RIGHT NOW. This is what makes N9's "still sealed" a statement
#    about this minute rather than about the day it was written. It refuses on
#    a dirty tree, on a commitment that no longer recomputes, on a leak in a
#    tracked file, and on HEAD moving while its own checks run.
$sealOk = $true
if ($Only -ne "replay") {
  Beat "python scripts/pre-read-seal-proof.py"
  $sealOk = ($LASTEXITCODE -eq 0)
}

Write-Host ""
if ($Only -ne "seal") {
  Write-Host "No credentials. No network. No cloud project." -ForegroundColor DarkYellow
}

# THE CLOSING LINE READS THE VERDICT. IT DOES NOT ASSERT ONE.
#
# The first version printed "the seal is intact and the check says so" no
# matter what the check said - and the very first run proved why that matters:
# the tree was dirty, the proof returned FAIL, and the script cheerfully
# narrated a pass underneath it. That is a check that measures nothing wearing
# a summary line, which is the defect this repository has published seventeen
# instances of. It is not going on camera.
if ($Only -eq "replay") {
  # nothing to say about the seal - this half did not check it
} elseif ($sealOk) {
  Write-Host "The seal is intact and the check says so, not me." -ForegroundColor DarkYellow
} else {
  Write-Host "THE PROOF FAILED. Do not use this take." -ForegroundColor Red
  Write-Host "Most likely the working tree is dirty - commit or stash, then" -ForegroundColor Red
  Write-Host "re-run. The proof refuses on a dirty tree on purpose." -ForegroundColor Red
}
Write-Host ""
Start-Sleep -Seconds 2
if (-not $sealOk) { exit 1 }
