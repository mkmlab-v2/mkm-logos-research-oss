# One-click: Track C showroom bundle -> validate (no atlas) -> publish ingest -> VPS static sync.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-ShowroomTrackCPublishRoutine_v1.ps1
#   ... -SkipVpsSync
#   ... -ApplyRecommendedNginx

param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipVpsSync,
    [switch]$ApplyRecommendedNginx,
    [switch]$SkipFreshnessInBuild
)

$ErrorActionPreference = "Stop"
$root = $WorkspaceRoot

$verify = Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal\verify_showroom_bundle_chain.ps1"
$publish = Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal\publish_showroom_public_event.ps1"
$sync = Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal\sync_showroom_to_vps.ps1"
$smokePy = Join-Path $root "scripts\check_showroom_trust_viz_public_chain_v1.py"
$c2Py = Join-Path $root "scripts\check_c2_aegis_guardrail.py"

Write-Host "[showroom-routine] (1/4) refresh C2 guardrail status (timestamp anchor)"
& py $c2Py
if ($LASTEXITCODE -ne 0) { throw "check_c2_aegis_guardrail.py failed: $LASTEXITCODE" }

$verifyArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $verify,
    "-WorkspaceRoot", $root,
    "-SkipVisualQualityGate"
)
if ($SkipFreshnessInBuild) { $verifyArgs += "-SkipFreshnessInBuild" }

Write-Host "[showroom-routine] (2/4) build + validate showroom bundle"
& powershell @verifyArgs
if ($LASTEXITCODE -ne 0) { throw "verify_showroom_bundle_chain failed: $LASTEXITCODE" }

$tok = [Environment]::GetEnvironmentVariable("PUBLIC_EVENT_GATEWAY_TOKEN", "User")
if (-not [string]::IsNullOrWhiteSpace($tok)) {
    $env:PUBLIC_EVENT_GATEWAY_TOKEN = $tok
}

Write-Host "[showroom-routine] (3/4) publish public_event_v1 to api.jemaai.cloud"
& powershell -NoProfile -ExecutionPolicy Bypass -File $publish -WorkspaceRoot $root
if ($LASTEXITCODE -ne 0) { throw "publish_showroom_public_event failed: $LASTEXITCODE" }

if (-not $SkipVpsSync) {
    Write-Host "[showroom-routine] (4/4) sync static showroom to VPS"
    $syncArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $sync, "-WorkspaceRoot", $root)
    if ($ApplyRecommendedNginx) { $syncArgs += "-ApplyRecommendedNginx" }
    & powershell @syncArgs
    if ($LASTEXITCODE -ne 0) { throw "sync_showroom_to_vps failed: $LASTEXITCODE" }
} else {
    Write-Host "[showroom-routine] (4/4) skipped (-SkipVpsSync)"
}

Write-Host "[showroom-routine] dual-host smoke"
& py $smokePy
if ($LASTEXITCODE -ne 0) { throw "check_showroom_trust_viz_public_chain_v1 failed: $LASTEXITCODE" }

$logPath = Join-Path $root "reports\showroom_track_c_publish_routine_log.jsonl"
$logDir = Split-Path -Parent $logPath
if (-not (Test-Path -LiteralPath $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}
$logLine = (@{
    schema           = "showroom_track_c_publish_routine_v1"
    completed_at_utc = ([DateTimeOffset]::UtcNow).ToString("yyyy-MM-ddTHH:mm:ssZ")
    ok               = $true
} | ConvertTo-Json -Compress)
Add-Content -LiteralPath $logPath -Value $logLine -Encoding utf8
Write-Host "[showroom-routine] OK (log append: reports/showroom_track_c_publish_routine_log.jsonl)"
