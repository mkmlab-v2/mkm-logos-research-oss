<#
.SYNOPSIS
  Register daily scheduled task for Track C macro fusion chain.

.NOTES
  Use -UnregisterLegacyTasks once when migrating off separate Fragility + Forward daily tasks
  (default legacy names: MKM-Fragility-MacroRisk-Daily, MacroRiskForwardDailyChain).
  Use -DryRun to print planned action and whether legacy/fusion tasks exist (no changes).
  Recommended unattended flags: -SkipGateAlert -SkipExodusSourceFetch (optional -SkipFailureAlert).
  Optional meta-layer gate after fusion: -MetaLayerEnvelopePath <json-or-md> (passed through to Invoke-TrackCMacroDailyFusion_v1.ps1).
  Optional: -SkipRoleRouterShadowAdvisory to omit build_role_router_s1_shadow_advisory_v1.py (default runs; non-gating).
  Optional: -SkipLensMusicHormoneTrend to omit M31 hormone trend + webhook before ops dashboard (default runs when dashboard runs).
  After register: NOTE only if -UnregisterLegacyTasks; else one-line TIP (SSOT pointers).
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$TaskName = "MKM-TrackC-MacroDailyFusion",

    [Parameter(Mandatory = $false)]
    [string]$RunAt = "07:28",

    [switch]$PreferFred,
    [string]$AssetScope = "BTC-USD",
    [ValidateSet("1h", "4h", "24h", "7d")]
    [string]$Horizon = "24h",
    [switch]$SkipGateAlert,
    [switch]$SkipFailureAlert,
    [switch]$SkipExodusSourceFetch,
    [switch]$SkipRoleRouterShadowAdvisory,
    [switch]$SkipLensMusicHormoneTrend,

    # Optional: forwarded to Invoke-TrackCMacroDailyFusion_v1.ps1 (see CONSTITUTION §1.3.1)
    [string]$MetaLayerEnvelopePath = "",

    [switch]$UnregisterLegacyTasks,
    [string]$LegacyFragilityTaskName = "MKM-Fragility-MacroRisk-Daily",
    [string]$LegacyForwardTaskName = "MacroRiskForwardDailyChain",
    [switch]$DryRun,
    [switch]$Remove,
    [switch]$StartNow
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "scheduled_task: REMOVED ($TaskName)"
    exit 0
}

$fusionScript = Join-Path $PSScriptRoot "Invoke-TrackCMacroDailyFusion_v1.ps1"
if (-not (Test-Path -LiteralPath $fusionScript)) {
    throw "Required script not found: $fusionScript"
}

try {
    $runTime = [DateTime]::ParseExact($RunAt, "HH:mm", $null)
}
catch {
    throw "RunAt must be HH:mm format, e.g. 07:28"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$argument = "-NoProfile -ExecutionPolicy Bypass -File `"$fusionScript`""
if ($PreferFred) { $argument += " -PreferFred" }
$argument += " -AssetScope `"$AssetScope`" -Horizon `"$Horizon`""
if ($SkipGateAlert) { $argument += " -SkipGateAlert" }
if ($SkipFailureAlert) { $argument += " -SkipFailureAlert" }
if ($SkipExodusSourceFetch) { $argument += " -SkipExodusSourceFetch" }
if ($SkipRoleRouterShadowAdvisory) { $argument += " -SkipRoleRouterShadowAdvisory" }
if ($SkipLensMusicHormoneTrend) { $argument += " -SkipLensMusicHormoneTrend" }
$metaTrim = if ($null -eq $MetaLayerEnvelopePath) { "" } else { $MetaLayerEnvelopePath.Trim() }
if ($metaTrim -ne "") {
    $argument += " -MetaLayerEnvelopePath `"$metaTrim`""
}

function Test-ScheduledTaskExists {
    param([string]$Name)
    if ([string]::IsNullOrWhiteSpace($Name)) { return $false }
    $t = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
    return ($null -ne $t)
}

if ($DryRun) {
    Write-Output "scheduled_task: DRY_RUN (no Register/Unregister performed)"
    Write-Output "would_register_task_name=$TaskName"
    Write-Output "would_run_daily_at=$RunAt"
    Write-Output ("would_prefer_fred={0}" -f [bool]$PreferFred)
    Write-Output "asset_scope=$AssetScope horizon=$Horizon"
    Write-Output ("skip_gate_alert={0} skip_failure_alert={1} skip_exodus_source_fetch={2} skip_role_router_shadow_advisory={3} skip_lens_music_hormone_trend={4}" -f @(
            [bool]$SkipGateAlert, [bool]$SkipFailureAlert, [bool]$SkipExodusSourceFetch, [bool]$SkipRoleRouterShadowAdvisory, [bool]$SkipLensMusicHormoneTrend))
    Write-Output ("meta_layer_envelope_path_set={0}" -f ($metaTrim -ne ""))
    if ($metaTrim -ne "") { Write-Output "meta_layer_envelope_path=$metaTrim" }
    Write-Output "working_directory=$repoRoot"
    Write-Output "powershell_argument=$argument"
    Write-Output ("would_unregister_legacy_tasks={0}" -f [bool]$UnregisterLegacyTasks)
    foreach ($legacyName in @($LegacyFragilityTaskName, $LegacyForwardTaskName)) {
        if ([string]::IsNullOrWhiteSpace($legacyName)) { continue }
        $ex = Test-ScheduledTaskExists -Name $legacyName
        Write-Output "legacy_task_present name=$legacyName exists=$ex"
    }
    $fex = Test-ScheduledTaskExists -Name $TaskName
    Write-Output "fusion_task_present name=$TaskName exists=$fex"
    if ($StartNow) { Write-Output "would_start_now=true (ignored under DryRun)" }
    exit 0
}

if ($UnregisterLegacyTasks) {
    foreach ($legacyName in @($LegacyFragilityTaskName, $LegacyForwardTaskName)) {
        if ([string]::IsNullOrWhiteSpace($legacyName)) { continue }
        Unregister-ScheduledTask -TaskName $legacyName -Confirm:$false -ErrorAction SilentlyContinue
        Write-Output "legacy_scheduled_task: removed_if_present ($legacyName)"
    }
}

$actionParams = @{
    Execute = "powershell.exe"
    Argument = $argument
}
try {
    $action = New-ScheduledTaskAction @actionParams -WorkingDirectory $repoRoot
}
catch {
    $action = New-ScheduledTaskAction @actionParams
}

$trigger = New-ScheduledTaskTrigger -Daily -At $runTime
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
Write-Output "scheduled_task: REGISTERED ($TaskName)"
Write-Output "run_at=$RunAt"
Write-Output ("prefer_fred={0}" -f [bool]$PreferFred)
Write-Output "asset_scope=$AssetScope horizon=$Horizon"
Write-Output ("skip_gate_alert={0} skip_failure_alert={1} skip_exodus_source_fetch={2} skip_role_router_shadow_advisory={3} skip_lens_music_hormone_trend={4}" -f @(
        [bool]$SkipGateAlert, [bool]$SkipFailureAlert, [bool]$SkipExodusSourceFetch, [bool]$SkipRoleRouterShadowAdvisory, [bool]$SkipLensMusicHormoneTrend))
Write-Output ("meta_layer_envelope_path_set={0}" -f ($metaTrim -ne ""))
if ($metaTrim -ne "") { Write-Output "meta_layer_envelope_path=$metaTrim" }
Write-Output "script=$fusionScript"
if ($UnregisterLegacyTasks) {
    Write-Output "NOTE: Legacy daily task names were unregistered above; confirm no duplicate Fragility schedulers remain."
}
else {
    Write-Output "TIP: Avoid parallel legacy Fragility+Forward daily tasks (see AGENTS.md Track C fusion, CONSTITUTION §1.3.1)."
}

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Output "scheduled_task: STARTED ($TaskName)"
}
