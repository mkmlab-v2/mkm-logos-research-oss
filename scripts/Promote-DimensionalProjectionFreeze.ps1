[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "",
    [string]$HoldoutGateJson = "",
    [string]$FreezeDir = "",
    [string]$ActiveDir = "",
    [switch]$AllowPartial
)

$ErrorActionPreference = "Stop"

function Read-Json([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing JSON file: $Path"
    }
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Copy-RequiredFile([string]$Source, [string]$Target, [bool]$IsRequired = $true) {
    if (-not (Test-Path -LiteralPath $Source)) {
        if ($IsRequired) {
            throw "Required source missing: $Source"
        }
        Write-Warning "Optional source missing: $Source"
        return
    }
    Copy-Item -LiteralPath $Source -Destination $Target -Force
}

function Get-FileSha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Cannot hash missing file: $Path"
    }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
if ([string]::IsNullOrWhiteSpace($HoldoutGateJson)) {
    $HoldoutGateJson = Join-Path $WorkspaceRoot "reports\dimensional_projection_bridge\holdout_gate_latest.json"
}
if ([string]::IsNullOrWhiteSpace($FreezeDir)) {
    $FreezeDir = Join-Path $WorkspaceRoot "reports\dimensional_projection_bridge\freeze"
}
if ([string]::IsNullOrWhiteSpace($ActiveDir)) {
    $ActiveDir = Join-Path $WorkspaceRoot "reports\dimensional_projection_bridge"
}

Set-Location $WorkspaceRoot

$gate = Read-Json -Path $HoldoutGateJson
if (-not $gate.overall_pass) {
    throw "Promotion blocked: holdout gate overall_pass=false ($HoldoutGateJson)"
}

$freezeOverrides = Join-Path $FreezeDir "engine_overrides_latest.json"
$freezePolicies = Join-Path $FreezeDir "policies_calibrated_latest.json"
$freezeScorer = Join-Path $FreezeDir "scorer_config_latest.json"

$activeOverrides = Join-Path $ActiveDir "engine_overrides_latest.json"
$activePolicies = Join-Path $ActiveDir "policies_calibrated_latest.json"
$activeScorer = Join-Path $ActiveDir "scorer_config_latest.json"

New-Item -ItemType Directory -Path $ActiveDir -Force | Out-Null

Copy-RequiredFile -Source $freezeOverrides -Target $activeOverrides -IsRequired $true
Copy-RequiredFile -Source $freezePolicies -Target $activePolicies -IsRequired $true
Copy-RequiredFile -Source $freezeScorer -Target $activeScorer -IsRequired (-not $AllowPartial)

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$promotionDir = Join-Path $ActiveDir "promotions"
New-Item -ItemType Directory -Path $promotionDir -Force | Out-Null
$promotionJson = Join-Path $promotionDir "promotion_$ts.json"

$promotion = [ordered]@{
    schema = "dimensional_projection_promotion_v1"
    promoted_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    holdout_gate_path = $HoldoutGateJson
    holdout_overall_pass = [bool]$gate.overall_pass
    sources = @{
        freeze_overrides = $freezeOverrides
        freeze_policies = $freezePolicies
        freeze_scorer = $freezeScorer
    }
    targets = @{
        active_overrides = $activeOverrides
        active_policies = $activePolicies
        active_scorer = $activeScorer
    }
}

$promotion | ConvertTo-Json -Depth 8 | Out-File -LiteralPath $promotionJson -Encoding utf8

$lockManifestPath = Join-Path $FreezeDir "runtime_lock_manifest_latest.json"
$lockManifest = [ordered]@{
    schema = "dimensional_projection_runtime_lock_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    source_promotion_record = $promotionJson
    refs = @{
        active_overrides = $activeOverrides
        active_policies = $activePolicies
        active_scorer = $activeScorer
    }
    checksums = @{
        active_overrides = (Get-FileSha256 -Path $activeOverrides)
        active_policies = (Get-FileSha256 -Path $activePolicies)
        active_scorer = (Get-FileSha256 -Path $activeScorer)
    }
}
$lockManifest | ConvertTo-Json -Depth 8 | Out-File -LiteralPath $lockManifestPath -Encoding utf8

Write-Output "Promotion completed."
Write-Output "promotion_record: $promotionJson"
Write-Output "active_dir: $ActiveDir"
Write-Output "runtime_lock_manifest: $lockManifestPath"

