<#
.SYNOPSIS
  B-track 실험: Bluesky(ATProto) 샘플 수집 (test_atproto_bluesky_bridge.py).

.NOTES
  - 본선/실매매와 합선 금지. 자격 증명 없으면 스킵하고 exit 0(작업 스케줄 실패 방지).
  - 사전: py -m pip install atproto
  - 환경: User 또는 세션에 BSKY_HANDLE, BSKY_APP_PASSWORD
#>
$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$py = Join-Path $workspaceRoot "scripts\test_atproto_bluesky_bridge.py"
$logDir = Join-Path $workspaceRoot "projects\bitcoin-trading\memory\v2\btrack\raw_feeds\atproto"
$skipLog = Join-Path $logDir "probe_env_skip_log.jsonl"

if (-not (Test-Path -LiteralPath $py)) {
    throw "Missing $py"
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$h = $env:BSKY_HANDLE
if (-not $h) { $h = $env:BLUESKY_HANDLE }
$p = $env:BSKY_APP_PASSWORD
if (-not $p) { $p = $env:BLUESKY_APP_PASSWORD }

if ([string]::IsNullOrWhiteSpace($h) -or [string]::IsNullOrWhiteSpace($p)) {
    $line = (@{
        ts_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        event    = "skip_missing_bsky_credentials"
        detail   = "Set BSKY_HANDLE and BSKY_APP_PASSWORD (User env recommended)"
        script   = "test_atproto_bluesky_bridge.py"
    } | ConvertTo-Json -Compress)
    Add-Content -LiteralPath $skipLog -Value $line -Encoding utf8
    Write-Host "[BTrack Atproto] Skip: BSKY_HANDLE / BSKY_APP_PASSWORD not set. Logged to $skipLog"
    exit 0
}

Push-Location $workspaceRoot
try {
    & py $py @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
