<#
.SYNOPSIS
  B-track 실험: Bluesky(ATProto) 샘플 수집 (test_atproto_bluesky_bridge.py).

.NOTES
  - 본선/실매매와 합선 금지. 자격 증명 없으면 스킵하고 exit 0(작업 스케줄 실패 방지).
  - 사전: py -m pip install atproto
  - 비밀 한곳 관리: C:\workspace\.env 에 BSKY_* 저장(커밋 금지) 후
    projects/bitcoin-trading/ops/windows-rehearsal/sync_required_env_to_user.ps1 실행 → User 환경변수 반영
  - 또는 수동으로 User 환경변수에 BSKY_HANDLE, BSKY_APP_PASSWORD
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

# If User/session env is empty, load BSKY_* / BLUESKY_* from C:\workspace\.env (same hub as sync script).
$dotEnv = Join-Path $workspaceRoot ".env"
if (Test-Path -LiteralPath $dotEnv) {
    foreach ($raw in Get-Content -LiteralPath $dotEnv) {
        $line = $raw.Trim()
        if (-not $line -or $line.StartsWith("#") -or $line.IndexOf("=") -lt 1) { continue }
        $idx = $line.IndexOf("=")
        $k = $line.Substring(0, $idx).Trim()
        if ($k -notmatch "^(BSKY_|BLUESKY_)") { continue }
        $v = $line.Substring($idx + 1).Trim()
        if ([string]::IsNullOrWhiteSpace($v)) { continue }
        $cur = [Environment]::GetEnvironmentVariable($k, "Process")
        if ([string]::IsNullOrWhiteSpace($cur)) {
            [Environment]::SetEnvironmentVariable($k, $v, "Process")
        }
    }
}

function Get-BskyIdentifier {
    $candidates = @(
        "BSKY_HANDLE",
        "BLUESKY_HANDLE",
        "BSKY_EMAIL",
        "BSKY_IDENTIFIER",
        "BLUESKY_EMAIL"
    )
    foreach ($name in $candidates) {
        $v = [Environment]::GetEnvironmentVariable($name, "Process")
        if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    }
    return ""
}

$id = Get-BskyIdentifier
$p = [Environment]::GetEnvironmentVariable("BSKY_APP_PASSWORD", "Process")
if ([string]::IsNullOrWhiteSpace($p)) { $p = [Environment]::GetEnvironmentVariable("BLUESKY_APP_PASSWORD", "Process") }

if ([string]::IsNullOrWhiteSpace($id) -or [string]::IsNullOrWhiteSpace($p)) {
    $miss = @()
    if ([string]::IsNullOrWhiteSpace($id)) { $miss += "BSKY_HANDLE_or_BSKY_EMAIL" }
    if ([string]::IsNullOrWhiteSpace($p)) { $miss += "BSKY_APP_PASSWORD" }
    $line = (@{
        ts_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        event    = "skip_missing_bsky_credentials"
        missing  = ($miss -join ",")
        detail   = "Set in C:\workspace\.env or User env; sync: sync_required_env_to_user.ps1"
        script   = "test_atproto_bluesky_bridge.py"
    } | ConvertTo-Json -Compress)
    Add-Content -LiteralPath $skipLog -Value $line -Encoding utf8
    Write-Host "[BTrack Atproto] Skip: missing $($miss -join ', '). Logged to $skipLog"
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
