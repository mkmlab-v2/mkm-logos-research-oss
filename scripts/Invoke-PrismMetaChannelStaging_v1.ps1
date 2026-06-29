#Requires -Version 5.1
<#
.SYNOPSIS
  B-track Prism meta sidecar staging — session env + readiness verify ([HYPO] research_only).

.DESCRIPTION
  Controls MKM_PRISM_META_CHANNEL_BTRACK for local/staging only (default OFF).
  Not Track A promotion. Rollback: DisableSession or unset User env.

.PARAMETER Action
  Status | EnableSession | DisableSession | Verify

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PrismMetaChannelStaging_v1.ps1 -Action Status

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PrismMetaChannelStaging_v1.ps1 -Action Verify
#>
[CmdletBinding()]
param(
    [ValidateSet('Status', 'EnableSession', 'DisableSession', 'Verify')]
    [string]$Action = 'Status',
    [int]$LiveSmokeMaxCases = 5
)

$ErrorActionPreference = 'Stop'
$EnvName = 'MKM_PRISM_META_CHANNEL_BTRACK'
$Root = Split-Path $PSScriptRoot -Parent

function Get-MkmEnvTruthy([string]$Name, [string]$Scope = 'Process') {
    $raw = [Environment]::GetEnvironmentVariable($Name, $Scope)
    if ($null -eq $raw) { return $false }
    $v = $raw.Trim().ToLowerInvariant()
    return $v -in @('1', 'true', 'yes', 'on')
}

function Show-MkmPrismMetaStagingStatus {
    $proc = Get-MkmEnvTruthy $EnvName 'Process'
    $user = Get-MkmEnvTruthy $EnvName 'User'
    $machine = Get-MkmEnvTruthy $EnvName 'Machine'
    [pscustomobject]@{
        env_flag           = $EnvName
        process_enabled    = $proc
        user_enabled       = $user
        machine_enabled    = $machine
        effective_any      = ($proc -or $user -or $machine)
        rollback_hint      = 'DisableSession or clear User/Machine env; default remains OFF'
        track_wall         = 'not_track_a_promotion'
        research_only      = $true
    } | Format-List
}

switch ($Action) {
    'Status' {
        Show-MkmPrismMetaStagingStatus
        exit 0
    }
    'EnableSession' {
        $env:MKM_PRISM_META_CHANNEL_BTRACK = '1'
        Write-Host "[$EnvName] session(Process)=1 — current PowerShell session only."
        Write-Host "Verify: py scripts/sandbox/run_prism_meta_channel_staging_live_smoke_v1.py --strict --max-cases $LiveSmokeMaxCases"
        Show-MkmPrismMetaStagingStatus
        exit 0
    }
    'DisableSession' {
        if (Test-Path "Env:$EnvName") {
            Remove-Item "Env:$EnvName" -ErrorAction SilentlyContinue
        }
        Write-Host "[$EnvName] removed from Process scope."
        Show-MkmPrismMetaStagingStatus
        exit 0
    }
    'Verify' {
        $bundle = Join-Path (Join-Path $PSScriptRoot 'sandbox') 'run_prism_meta_channel_staging_bundle_v1.py'
        $py = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } else { 'python' }
        & $py $bundle --require-staging-enable --live-smoke --live-smoke-max-cases $LiveSmokeMaxCases
        exit $LASTEXITCODE
    }
    default {
        throw "Unhandled Action: $Action"
    }
}
