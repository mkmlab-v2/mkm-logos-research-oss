#Requires -Version 5.1
<#
.SYNOPSIS
  Open CF API token UI, watch for local secret JSON, then apply rules + autoverify.

.EXAMPLE
  powershell -File scripts\Invoke-JemaaiCfTokenWatchAndApply_v1.ps1 -WatchMinutes 5
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$WatchMinutes = 5,
    [int]$PollSeconds = 5,
    [switch]$SkipOpenBrowser
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$secretPath = Join-Path $WorkspaceRoot "reports\cloudflare_jemaai_solo_edge_token_secret_LOCAL.json"
$logPath = Join-Path $WorkspaceRoot "reports\jemaai_cf_token_watch_apply_v1_latest.json"

if (-not $SkipOpenBrowser) {
    & (Join-Path $WorkspaceRoot "scripts\Open-JemaaiShowroomCfEdgeTokenTemplate_v1.ps1")
}

function Test-TokenReady {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    try {
        $doc = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
        $tok = [string]$doc.CLOUDFLARE_RULESETS_API_TOKEN
        if ([string]::IsNullOrWhiteSpace($tok)) { $tok = [string]$doc.CLOUDFLARE_API_TOKEN }
        if ([string]::IsNullOrWhiteSpace($tok)) { return $false }
        if ($tok -match '^(paste_|<|your_)') { return $false }
        if ($tok.Length -lt 20) { return $false }
        return $true
    } catch {
        return $false
    }
}

$deadline = (Get-Date).AddMinutes($WatchMinutes)
$status = "timeout"
$applyExit = $null

Write-Host "[watch] Waiting for $secretPath ($WatchMinutes min) ..." -ForegroundColor Cyan
Write-Host "  Create token: Zone Read + Zone WAF Edit + Cache Rules Edit (jemaai.cloud only)" -ForegroundColor DarkGray

while ((Get-Date) -lt $deadline) {
    if (Test-TokenReady -Path $secretPath) {
        Write-Host "[watch] Secret detected — applying" -ForegroundColor Green
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-ApplyJemaaiShowroomCfEdgeTokenFromSecret_v1.ps1") -SecretJson $secretPath
        $applyExit = $LASTEXITCODE
        $status = if ($applyExit -eq 0) { "applied_ok" } else { "apply_failed" }
        break
    }
    Start-Sleep -Seconds $PollSeconds
}

$payload = [ordered]@{
    schema           = "jemaai_cf_token_watch_apply_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    secret_path      = $secretPath
    watch_minutes    = $WatchMinutes
    status           = $status
    apply_exit       = $applyExit
}
$payload | ConvertTo-Json | Set-Content -LiteralPath $logPath -Encoding UTF8
Write-Host "WROTE: $logPath status=$status apply_exit=$applyExit"

if ($status -eq "timeout") {
    Write-Host "[watch] No token file yet. Paste into:" -ForegroundColor Yellow
    Write-Host '  reports\cloudflare_jemaai_solo_edge_token_secret_LOCAL.json' -ForegroundColor Yellow
    Write-Host '  { "CLOUDFLARE_RULESETS_API_TOKEN": "<paste once>" }' -ForegroundColor Yellow
    Write-Host "Then: powershell -File scripts\Invoke-ApplyJemaaiShowroomCfEdgeTokenFromSecret_v1.ps1" -ForegroundColor Cyan
    exit 2
}
exit $applyExit
