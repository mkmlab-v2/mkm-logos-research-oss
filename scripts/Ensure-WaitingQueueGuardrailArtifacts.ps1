param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$StaleLockMinutes = 20
)

$ErrorActionPreference = "Stop"

function Read-JsonObject([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    try {
        $obj = Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($null -eq $obj) { return $null }
        return $obj
    } catch {
        return $null
    }
}

function Copy-IfMissing([string]$Source, [string]$Destination) {
    if (Test-Path -LiteralPath $Destination) { return }
    if (-not (Test-Path -LiteralPath $Source)) { return }
    $destDir = Split-Path -Parent $Destination
    if (-not (Test-Path -LiteralPath $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
}

$artifactsDir = Join-Path $WorkspaceRoot "docs\final\artifacts"
$guardrailPath = Join-Path $artifactsDir "C2_AEGIS_BASELINE_GUARDRAIL_V1.json"
$guardrailArchivePath = Join-Path $artifactsDir "archive\cataloged\20260505T073105Z\docs\final\artifacts\C2_AEGIS_BASELINE_GUARDRAIL_V1.json"
$scoreboardPrimaryPath = Join-Path $artifactsDir "aegis_unified_scoreboard_btc90_k010_latest.json"
$scoreboardFallbackPath = Join-Path $artifactsDir "aegis_unified_scoreboard_latest.json"
$scoreboardAbcdPath = Join-Path $artifactsDir "aegis_unified_scoreboard_abcd_latest.json"
$scoreboardAbcdsPath = Join-Path $artifactsDir "aegis_unified_scoreboard_abcds_latest.json"
$scoreboardCandidates = @($scoreboardPrimaryPath, $scoreboardFallbackPath, $scoreboardAbcdPath, $scoreboardAbcdsPath)
$scoreLockPath = Join-Path $artifactsDir ".btrack_prophecy_score_latest.lock"

Copy-IfMissing -Source $guardrailArchivePath -Destination $guardrailPath

$guardrail = Read-JsonObject -Path $guardrailPath
if ($null -eq $guardrail -or [string]::IsNullOrWhiteSpace([string]$guardrail.schema)) {
    throw "guardrail artifact missing/invalid: $guardrailPath"
}

$scoreboard = Read-JsonObject -Path $scoreboardPrimaryPath
if ($null -eq $scoreboard -or [string]::IsNullOrWhiteSpace([string]$scoreboard.schema)) {
    $recovered = $false
    foreach ($candidate in $scoreboardCandidates) {
        $obj = Read-JsonObject -Path $candidate
        if ($null -ne $obj -and -not [string]::IsNullOrWhiteSpace([string]$obj.schema)) {
            if ($candidate -ne $scoreboardPrimaryPath) {
                Copy-Item -LiteralPath $candidate -Destination $scoreboardPrimaryPath -Force
            }
            $recovered = $true
            break
        }
    }
    if (-not $recovered) {
        throw "scoreboard artifact missing/invalid: $scoreboardPrimaryPath"
    }
}

if (Test-Path -LiteralPath $scoreLockPath) {
    try {
        $lockItem = Get-Item -LiteralPath $scoreLockPath
        $age = (Get-Date) - $lockItem.LastWriteTime
        if ($age.TotalMinutes -ge $StaleLockMinutes) {
            Remove-Item -LiteralPath $scoreLockPath -Force -ErrorAction Stop
        }
    } catch {
        # Non-fatal: lock may be active in another process.
    }
}

Write-Output ("guardrail_ok={0}" -f $guardrailPath)
Write-Output ("scoreboard_ok={0}" -f $scoreboardPrimaryPath)
Write-Output ("lock_checked={0}" -f $scoreLockPath)
