param(
    [string]$TaskName = "\Bitcoin-Verify-All-Green-SelfHeal-30min",
    [int]$IntervalMinutes = 30,
    [int]$StartDelayMinutes = 1,
    [string]$VerifyOutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\all_green_latest.json",
    [string]$LoopOutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\all_green_self_heal_latest.json",
    [switch]$SlackNotifyLive,
    [string]$WebhookUrl = ""
)

$ErrorActionPreference = "Stop"

function Get-EnvAnyScope([string]$Name) {
    $u = [Environment]::GetEnvironmentVariable($Name, "User")
    if (-not [string]::IsNullOrWhiteSpace($u)) { return $u.Trim() }
    $m = [Environment]::GetEnvironmentVariable($Name, "Machine")
    if (-not [string]::IsNullOrWhiteSpace($m)) { return $m.Trim() }
    $p = [Environment]::GetEnvironmentVariable($Name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($p)) { return $p.Trim() }
    return ""
}

function Resolve-WebhookForTask {
    if (-not [string]::IsNullOrWhiteSpace($WebhookUrl)) {
        return $WebhookUrl.Trim()
    }
    foreach ($name in @("N8N_ALL_GREEN_WEBHOOK_URL", "N8N_WEBHOOK_URL")) {
        $v = Get-EnvAnyScope -Name $name
        if (-not [string]::IsNullOrWhiteSpace($v)) {
            return $v
        }
    }
    return ""
}

$scriptPath = "C:\workspace\projects\bitcoin-trading\ops\windows-rehearsal\run_verify_all_green_self_heal.ps1"
$defaultVerifyOutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\all_green_latest.json"
$defaultLoopOutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\all_green_self_heal_latest.json"
if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Self-heal script not found: $scriptPath"
}

$resolvedWebhook = Resolve-WebhookForTask

$tr = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`""
if ($VerifyOutputPath -ne $defaultVerifyOutputPath) {
    $tr += " -VerifyOutputPath `"$VerifyOutputPath`""
}
if ($LoopOutputPath -ne $defaultLoopOutputPath) {
    $tr += " -LoopOutputPath `"$LoopOutputPath`""
}
if ($SlackNotifyLive) {
    $tr += " -SlackNotifyLive"
}
if (-not [string]::IsNullOrWhiteSpace($resolvedWebhook)) {
    $tr += " -WebhookUrl `"$resolvedWebhook`""
}

$st = (Get-Date).AddMinutes($StartDelayMinutes).ToString("HH:mm")

# Best-effort replace.
schtasks /Delete /TN $TaskName /F | Out-Null 2>&1
if ($tr.Length -gt 261) {
    throw "Task command line too long for schtasks (/TR max 261). Shorten webhook URL or set N8N_ALL_GREEN_WEBHOOK_URL to a shorter path, or omit webhook from TR and rely on User env vars only (not recommended for scheduled tasks)."
}

schtasks /Create /TN $TaskName /SC MINUTE /MO $IntervalMinutes /ST $st /TR $tr /F | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create task ($TaskName). /TR length may exceed Task Scheduler limits."
}

Write-Host "Created task: $TaskName"
Write-Host "Schedule: every $IntervalMinutes minutes; start=$st"
Write-Host "TR: $tr"
if ([string]::IsNullOrWhiteSpace($resolvedWebhook)) {
    Write-Host "Webhook: embedded in TR = none (set User env N8N_ALL_GREEN_WEBHOOK_URL or N8N_WEBHOOK_URL, or pass -WebhookUrl, then re-run this register script)"
} else {
    Write-Host "Webhook: embedded in TR = yes (host/path only; full URL stored in local task definition)"
}

# Seed the latest artifacts immediately.
$runArgs = @("-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-File", $scriptPath)
if ($VerifyOutputPath -ne $defaultVerifyOutputPath) {
    $runArgs += @("-VerifyOutputPath", $VerifyOutputPath)
}
if ($LoopOutputPath -ne $defaultLoopOutputPath) {
    $runArgs += @("-LoopOutputPath", $LoopOutputPath)
}
if ($SlackNotifyLive) {
    $runArgs += "-SlackNotifyLive"
}
if (-not [string]::IsNullOrWhiteSpace($resolvedWebhook)) {
    $runArgs += @("-WebhookUrl", $resolvedWebhook)
}
& powershell @runArgs | Out-Null

exit 0
