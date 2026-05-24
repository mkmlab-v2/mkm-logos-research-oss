#Requires -Version 5.1
<#
.SYNOPSIS
  Enable Bitcoin-OpsKPI scheduled tasks (requires elevated PowerShell / UAC once).

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Enable-BitcoinOpsKpiTasks_v1.ps1
#>
$ErrorActionPreference = 'Stop'
$names = @(
    'Bitcoin-OpsKPI-AlertEval-30min',
    'Bitcoin-OpsKPI-Baseline-30min',
    'Bitcoin-OpsKPI-Response-30min'
)
$results = @()
foreach ($tn in $names) {
    $row = [ordered]@{ TaskName = $tn; Method = ''; Ok = $false; Detail = '' }
    try {
        Enable-ScheduledTask -TaskName $tn -ErrorAction Stop | Out-Null
        $row.Method = 'Enable-ScheduledTask'
        $row.Ok = $true
    }
    catch {
        $row.Detail = $_.Exception.Message
        schtasks /Change /TN $tn /ENABLE 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $row.Method = 'schtasks /CHANGE /ENABLE'
            $row.Ok = $true
            $row.Detail = ''
        }
    }
    $st = (Get-ScheduledTask -TaskName $tn -ErrorAction SilentlyContinue).State
    $row.State = [string]$st
    $results += [pscustomobject]$row
}
$out = Join-Path $PSScriptRoot '..\reports\bitcoin_opskpi_enable_latest.json'
$payload = @{
    schema           = 'bitcoin_opskpi_enable_v1'
    generated_at_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    is_admin         = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    results          = $results
}
$payload | ConvertTo-Json -Depth 5 | Set-Content -Path $out -Encoding UTF8
Write-Host "Wrote: $out"
$results | Format-Table -AutoSize
if ($results | Where-Object { -not $_.Ok }) { exit 1 }
exit 0
