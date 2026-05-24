#Requires -Version 5.1
<#
.SYNOPSIS
  Push local trading gate + human approval to VPS destiny tree and rebuild trading_go_no_go.

.DESCRIPTION
  Recurring ops: VPS often shows NO_GO with missing_or_invalid_human_approval while local is GO.
  Copies reports/trading_human_execution_approval_latest.json and
  reports/poc_binance_signal_webhook/conditional_gate_latest.json, then runs
  build_trading_go_nogo_status_v1.py on the server and pulls the result to
  reports/vps_trading_go_no_go_latest.json.

.PARAMETER VpsHost
  SSH config Host (default vps-mkmlife). MKM_VPS_HOST is not required when using config alias.

.PARAMETER DestinyRoot
  Remote monorepo root on VPS (default /opt/mkm-destiny-ai-41e38ec6).

.PARAMETER SkipLocalValidate
  Skip validate_trading_human_execution_approval_v1.py before push.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-VpsTradingGoReadinessSync_v1.ps1
#>
param(
    [string]$WorkspaceRoot = "",
    [string]$VpsHost = $(if ($env:VPS_SSH_HOST) { $env:VPS_SSH_HOST } else { "vps-mkmlife" }),
    [string]$DestinyRoot = "/opt/mkm-destiny-ai-41e38ec6",
    [switch]$SkipLocalValidate,
    [string]$OutJson = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
if ([string]::IsNullOrWhiteSpace($OutJson)) {
    $OutJson = Join-Path $WorkspaceRoot "reports\vps_trading_go_readiness_sync_latest.json"
}

$approvalLocal = Join-Path $WorkspaceRoot "reports\trading_human_execution_approval_latest.json"
$gateLocal = Join-Path $WorkspaceRoot "reports\poc_binance_signal_webhook\conditional_gate_latest.json"
$goLocal = Join-Path $WorkspaceRoot "docs\final\artifacts\trading_go_no_go_latest.json"

foreach ($p in @($approvalLocal, $gateLocal)) {
    if (-not (Test-Path -LiteralPath $p)) {
        throw "Missing local artifact: $p"
    }
}

$ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$payload = [ordered]@{
    schema              = "vps_trading_go_readiness_sync_v1"
    generated_at_utc    = $ts
    workspace_root      = $WorkspaceRoot
    vps_host            = $VpsHost
    destiny_root        = $DestinyRoot
    local_validate_exit = $null
    scp_ok              = $false
    remote_rebuild_exit = $null
    vps_go_no_go        = $null
    vps_reasons         = @()
    local_go_no_go      = $null
    aligned             = $null
    error               = $null
}

try {
    if (-not $SkipLocalValidate) {
        $validate = Join-Path $WorkspaceRoot "scripts\validate_trading_human_execution_approval_v1.py"
        if (-not (Test-Path -LiteralPath $validate)) {
            throw "Missing $validate"
        }
        & py $validate --approval $approvalLocal --workspace-root $WorkspaceRoot
        $payload.local_validate_exit = $LASTEXITCODE
        if ($LASTEXITCODE -ne 0) {
            throw "validate_trading_human_execution_approval_v1.py exit $LASTEXITCODE"
        }
    }

    if (Test-Path -LiteralPath $goLocal) {
        $localGo = Get-Content -LiteralPath $goLocal -Raw -Encoding UTF8 | ConvertFrom-Json
        $payload.local_go_no_go = [string]$localGo.go_no_go
    }

    $remoteReports = "$DestinyRoot/reports"
    $remoteGateDir = "$remoteReports/poc_binance_signal_webhook"
    ssh $VpsHost "mkdir -p '$remoteGateDir'" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "ssh mkdir exit $LASTEXITCODE" }

    scp $approvalLocal "${VpsHost}:${remoteReports}/trading_human_execution_approval_latest.json"
    if ($LASTEXITCODE -ne 0) { throw "scp approval exit $LASTEXITCODE" }
    scp $gateLocal "${VpsHost}:${remoteGateDir}/conditional_gate_latest.json"
    if ($LASTEXITCODE -ne 0) { throw "scp gate exit $LASTEXITCODE" }
    $payload.scp_ok = $true

    $remoteCmd = "cd '$DestinyRoot' && python3 scripts/build_trading_go_nogo_status_v1.py --exit-zero-on-no-go"
    ssh $VpsHost $remoteCmd
    $payload.remote_rebuild_exit = $LASTEXITCODE
    if ($LASTEXITCODE -ne 0) { throw "remote build_trading_go_nogo exit $LASTEXITCODE" }

    $vpsGoLocal = Join-Path $WorkspaceRoot "reports\vps_trading_go_no_go_latest.json"
    scp "${VpsHost}:${DestinyRoot}/docs/final/artifacts/trading_go_no_go_latest.json" $vpsGoLocal
    if ($LASTEXITCODE -ne 0) { throw "scp pull go/nogo exit $LASTEXITCODE" }

    $vpsGo = Get-Content -LiteralPath $vpsGoLocal -Raw -Encoding UTF8 | ConvertFrom-Json
    $payload.vps_go_no_go = [string]$vpsGo.go_no_go
    if ($vpsGo.reasons) {
        $payload.vps_reasons = @($vpsGo.reasons | ForEach-Object { [string]$_ })
    }
    $payload.aligned = ($payload.local_go_no_go -eq $payload.vps_go_no_go)
}
catch {
    $payload.error = $_.Exception.Message
    $payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutJson -Encoding UTF8
    Write-Error $_
    exit 1
}

$payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutJson -Encoding UTF8
Write-Host "vps_trading_go_readiness_sync_written=$OutJson vps_go=$($payload.vps_go_no_go) aligned=$($payload.aligned)"
