# gcp-proof.ps1 - the on-camera beat that proves the backend runs on Google Cloud.
#
# WHY A SCRIPT AND NOT TYPING IT LIVE. Four commands typed by hand on a take is
# four chances to fumble a flag, and the beat is twenty seconds. This types them
# FOR the camera - the command appears, then its real output - so what lands on
# screen is the same every take and you are not editing around a typo.
#
# EVERY COMMAND HERE IS READ-ONLY. `list` and `describe` create nothing, bind
# nothing, and delete nothing. Nothing in this file touches gs://crucible-sealed-x7.
#
# BEFORE YOU ROLL:
#   * set the terminal to 1920x1080 and the font to 18-20pt. Default console
#     text is illegible at YouTube's compression - the judge sees mush.
#   * `gcloud auth list` first, off camera, so an auth prompt cannot land mid-take.
#   * the Cloud Run URL appears on screen. That is fine and it is already public
#     in six tracked files; the service holds ZERO IAM bindings, so the URL is
#     not a spend risk. See docs/contest/AUDIT-stage-one-2026-08-30.md Row 8.
#
# Usage (Windows PowerShell 5.1 - there is no pwsh on this machine, and
# reaching for one is how the take opens with a CommandNotFoundException):
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\capture\gcp-proof.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools\capture\gcp-proof.ps1 -Pause 2.5

param(
  [double]$Pause = 1.8,
  [string]$Project = "crucible-hack-2026",
  [string]$Region  = "us-central1"
)

$ErrorActionPreference = "Stop"

function Beat($cmd) {
  Write-Host ""
  Write-Host "PS> " -NoNewline -ForegroundColor DarkGray
  # Typed a character at a time, so the frame reads as a session rather than a
  # paste. Fast enough not to eat the beat.
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
Write-Host "CRUCIBLE - is this actually running on Google Cloud?" -ForegroundColor DarkYellow
Start-Sleep -Seconds $Pause

# 1. THE SERVICE IS DEPLOYED AND SERVING, and it runs under a NAMED identity.
#    The service account is the point: `crucible-target` is not the default
#    compute SA, and the whole design rests on identities that differ.
Beat "gcloud run services describe crucible --project=$Project --region=$Region --format=""table(status.url, status.latestReadyRevisionName, spec.template.spec.serviceAccountName)"""

# 2. VERTEX AND CLOUD RUN ARE ENABLED ON THIS PROJECT. aiplatform is the one
#    that matters - it is where every model call in the loop goes.
Beat "gcloud services list --enabled --project=$Project --format=""value(config.name)"" | Select-String -Pattern 'aiplatform|^run\.|storage-api|logging'"

# 3. THE THREE BUCKETS, INCLUDING THE SEALED ONE. Listing bucket NAMES is not
#    reading the holdout - no object is fetched, and the sealed bucket appearing
#    here is the point: it exists, and the attacking identity cannot read it.
Beat "gcloud storage buckets list --project=$Project --format=""table(name, location)"" | Select-String -Pattern 'crucible-'"

# 4. GEMMA, ON VERTEX MODEL GARDEN AS A MANAGED ENDPOINT.
#    Two frames: the pin in source, and a live-run artifact that recorded the
#    endpoint it actually called. The `-maas` suffix is part of the id - the
#    module docstring records what dropping it cost.
#
#    SAY WHAT GEMMA DOES AND NOTHING MORE. It is the CAPABILITY CARTOGRAPHER:
#    it classifies each tool on the target into a capability class. ADR-0018
#    withdrew the claim that Gemma generated the attack corpus - that sentence
#    "may not be written or spoken anywhere" - and the corpus was authored by
#    lane agents. Classification is the claim; generation is not.
Beat "Select-String -Path crucible/cartographer/vertex.py -Pattern 'DEFAULT_MODEL_ID =|DEFAULT_LOCATION ='"

# AND ONE LIVE CALL, NOW, rather than a saved artifact that says a call
# happened once. The earlier version read
# docs/proof/cartographer-live-run-2026-08-23.json here, which is true and is
# not the same sentence: "here is Gemma responding" and "here is a file saying
# Gemma responded" differ, and only the second is what a saved JSON supports.
#
# It goes through the same make_completer the Cartographer uses, so the
# endpoint, model id, seed and temperature on screen are the ones the project
# actually runs. One question, ~24 tokens out.
Beat "python scripts/gemma-live-probe.py"

Write-Host ""
Write-Host "Cloud Run - serving, own service account." -ForegroundColor DarkYellow
Write-Host "Vertex AI - every model call in the loop." -ForegroundColor DarkYellow
Write-Host "Cloud Storage - evidence, policies, and the sealed holdout." -ForegroundColor DarkYellow
Write-Host "Gemma on Vertex Model Garden - the capability cartographer." -ForegroundColor DarkYellow
Write-Host ""
Start-Sleep -Seconds 2
