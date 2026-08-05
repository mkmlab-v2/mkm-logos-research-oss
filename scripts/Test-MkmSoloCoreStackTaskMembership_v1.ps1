#Requires -Version 5.1
<#
.SYNOPSIS
  Check whether a scheduled task path is listed in solo core stack SSOT tiers.

.DESCRIPTION
  SSOT: docs/final/artifacts/mkm_scheduler_solo_core_stack_v1.json
  Policy: register_task_policy_v1.require_ssot_tier_before_enable_ready

  Exit codes (when run as script):
    0 = member of an allowed tier
    1 = not a member / SSOT missing
    2 = usage error

.PARAMETER TaskName
  Task name without leading backslash (e.g. MKM_AutonomousPatrol_Daily).

.PARAMETER FailClosed
  Throw if not a member (for Register-* -StartReady paths).

.PARAMETER PassThru
  Return a hashtable instead of only bool / exit.

.EXAMPLE
  powershell -File scripts\Test-MkmSoloCoreStackTaskMembership_v1.ps1 -TaskName MKM_AutonomousPatrol_Daily
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TaskName,
    [string]$WorkspaceRoot = "",
    [switch]$FailClosed,
    [switch]$PassThru
)

$ErrorActionPreference = "Stop"

$resolvedRoot = if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot) -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    $WorkspaceRoot.TrimEnd('\', '/')
}
elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
}
else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

$cleanName = $TaskName.Trim().TrimStart('\')
if ([string]::IsNullOrWhiteSpace($cleanName)) {
    if ($FailClosed) { throw "TaskName is empty" }
    if ($PassThru) {
        return [ordered]@{ ok = $false; member = $false; reason = "empty_task_name"; tier_key = $null }
    }
    Write-Host "FAIL: empty TaskName"
    exit 2
}

# JSON stores "\\Task" → parsed single leading backslash path (\TaskName).
$needle = '\' + $cleanName
$ssotPath = Join-Path $resolvedRoot "docs\final\artifacts\mkm_scheduler_solo_core_stack_v1.json"
$result = [ordered]@{
    ok        = $false
    member    = $false
    task_path = $needle
    tier_key  = $null
    ssot      = $ssotPath
    reason    = "not_checked"
}

if (-not (Test-Path -LiteralPath $ssotPath)) {
    $result.reason = "ssot_missing"
    if ($FailClosed) { throw "Solo core stack SSOT missing: $ssotPath" }
    if ($PassThru) { return $result }
    Write-Host "FAIL: SSOT missing ($ssotPath)"
    exit 1
}

$stack = Get-Content -LiteralPath $ssotPath -Raw -Encoding UTF8 | ConvertFrom-Json
$policy = $stack.register_task_policy_v1
$tierKeys = @("tier0_core_daily", "tier1_core_weekly", "tier2_keep_event", "tier3_optional_active", "tier4_solo_intentional_keep")
if ($policy -and $policy.allowed_tier_keys) {
    $tierKeys = @($policy.allowed_tier_keys)
}

foreach ($key in $tierKeys) {
    $list = $stack.$key
    if ($null -eq $list) { continue }
    foreach ($item in @($list)) {
        if ([string]$item -eq $needle) {
            $result.ok = $true
            $result.member = $true
            $result.tier_key = [string]$key
            $result.reason = "listed"
            break
        }
    }
    if ($result.member) { break }
}

if (-not $result.member) {
    $result.reason = "not_in_allowed_tiers"
    if ($FailClosed) {
        throw ("Task {0} not in solo SSOT tiers ({1}). Add to SSOT before Ready (register_task_policy_v1)." -f $needle, ($tierKeys -join ', '))
    }
}

if ($PassThru) { return $result }

if ($result.member) {
    Write-Host ("OK: {0} in {1}" -f $needle, $result.tier_key)
    exit 0
}
Write-Host ("FAIL: {0} not in solo SSOT tiers" -f $needle)
exit 1
