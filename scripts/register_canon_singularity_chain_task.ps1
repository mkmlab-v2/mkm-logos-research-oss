# Register (or remove) a Windows Scheduled Task for canon singularity chain + vault sync.

param(
    [switch]$Remove,
    [string]$TaskName = "MKM_CanonSingularity_Chain",
    [string]$DailyAt = "06:40",
    [ValidateSet("strict", "balanced", "lenient")]
    [string]$HealthProfile = "strict",
    [Nullable[int]]$HealthMaxFailCount = $null,
    [Nullable[double]]$HealthMinPassRate = $null,
    [switch]$HealthAllowYellow,
    [switch]$PrintOnly
)

$ErrorActionPreference = "Stop"
$workspaceRoot = "C:\workspace"
$runner = Join-Path $workspaceRoot "scripts\run_canon_singularity_chain_and_vault_sync.ps1"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Runner not found: $runner"
}

$profileDefaults = @{
    strict = @{ MaxFail = 0; MinPass = 1.0; AllowYellow = $false }
    balanced = @{ MaxFail = 1; MinPass = 0.9; AllowYellow = $true }
    lenient = @{ MaxFail = 2; MinPass = 0.8; AllowYellow = $true }
}
$selected = $profileDefaults[$HealthProfile]

$maxFail = if ($null -ne $HealthMaxFailCount) { [int]$HealthMaxFailCount } else { [int]$selected.MaxFail }
$minPass = if ($null -ne $HealthMinPassRate) { [double]$HealthMinPassRate } else { [double]$selected.MinPass }
$allowYellow = if ($HealthAllowYellow.IsPresent) { $true } else { [bool]$selected.AllowYellow }

$runnerArgs = @(
    "-NoProfile",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$runner`"",
    "-HealthMaxFailCount", "$maxFail",
    "-HealthMinPassRate", "$minPass"
)
if ($allowYellow) {
    $runnerArgs += "-HealthAllowYellow"
}
$runnerArgString = ($runnerArgs -join " ")

if ($PrintOnly) {
    Write-Host "PrintOnly: no task registration performed."
    Write-Host "TaskName: $TaskName"
    Write-Host "DailyAt: $DailyAt"
    Write-Host "HealthProfile: $HealthProfile"
    Write-Host "RunnerArgs: $runnerArgString"
    exit 0
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument $runnerArgString `
    -WorkingDirectory $workspaceRoot

$parts = $DailyAt -split ":"
if ($parts.Count -lt 2) {
    throw "DailyAt must be HH:mm (e.g. 06:40), got: $DailyAt"
}
$hour = [int]$parts[0]
$minute = [int]$parts[1]
$base = Get-Date
$atToday = Get-Date -Year $base.Year -Month $base.Month -Day $base.Day -Hour $hour -Minute $minute -Second 0
$trigger = New-ScheduledTaskTrigger -Daily -At $atToday

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 60)

$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$description = "Run canon-only singularity chain and mirror outputs to MKM_DATA_VAULT. HealthProfile=$HealthProfile MaxFail=$maxFail MinPass=$minPass AllowYellow=$allowYellow"

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description $description -Force | Out-Null

Write-Host "Registered task: $TaskName (daily at $DailyAt, user=$env:USERNAME)"
Write-Host "Runner: $runner"
