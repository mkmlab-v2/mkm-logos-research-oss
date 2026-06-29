<#
.SYNOPSIS
  Disable Windows hibernate (hiberfil.sys) to reclaim ~12-13GB on C:.

.NOTES
  Requires elevated (Administrator) PowerShell. Infra lane only.
#>
param(
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$root = "C:\workspace"
$outJson = Join-Path $root "reports\c_workspace_hibernate_off_v1_latest.json"
$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

function Get-CFreeGb {
    [math]::Round((Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace / 1GB, 2)
}

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)

$before = Get-CFreeGb
$hiberBefore = $null
if (Test-Path -LiteralPath "C:\hiberfil.sys") {
    $hiberBefore = [math]::Round((Get-Item -LiteralPath "C:\hiberfil.sys" -Force).Length / 1GB, 2)
}

$exitCode = 0
$note = "skipped"
if (-not $isAdmin) {
    $exitCode = 1
    $note = "requires_admin_run_as_administrator"
} elseif ($WhatIfOnly) {
    $note = "whatif_skipped"
} else {
    & powercfg /h off
    $exitCode = $LASTEXITCODE
    $note = if ($exitCode -eq 0) { "powercfg_h_off_ok" } else { "powercfg_failed" }
}

$after = Get-CFreeGb
$hiberAfter = Test-Path -LiteralPath "C:\hiberfil.sys"

$report = [ordered]@{
    schema           = "c_workspace_hibernate_off_v1"
    generated_at_utc = $utc
    is_admin         = $isAdmin
    exit_code        = $exitCode
    note             = $note
    hiberfil_gb_before = $hiberBefore
    hiberfil_exists_after = $hiberAfter
    c_free_gb_before = $before
    c_free_gb_after  = $after
    c_free_delta_gb  = [math]::Round($after - $before, 2)
}
$report | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $outJson -Encoding UTF8
Write-Host "Report: $outJson"
Write-Host "C: free ${before}GB -> ${after}GB (admin=$isAdmin exit=$exitCode)"
exit $exitCode
