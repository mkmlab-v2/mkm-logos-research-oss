param(
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\runtime_schedule_integrity_latest.json",
    # Daily stagger shifts Start Time vs nominal HH:mm — exact minute match is too brittle for Task Scheduler.
    # Covers intra-cluster reorder (e.g. Alert 09:10 vs nominal 09:30) without masking whole-hour drift.
    [int]$TimeToleranceMinutes = 25,
    # Ops may intentionally disable bootstrap/self-heal while keeping the chain audited.
    [string[]]$AllowDisabled = @(
        '\Bitcoin-Runtime-Bootstrap-Automation',
        '\Bitcoin-Runtime-Self-Heal'
    )
)

$ErrorActionPreference = "Stop"

$expected = @(
    @{ task = "\Bitcoin-Runtime-Bootstrap-Automation"; time = "09:10" },
    @{ task = "\Bitcoin-Runtime-Self-Heal"; time = "09:12" },
    @{ task = "\Bitcoin-Fused-QuantPixel-SOP-Strict-Check"; time = "09:15" },
    @{ task = "\Bitcoin-Runtime-Health-Check"; time = "09:20" },
    @{ task = "\Bitcoin-Runtime-Task-Chain-Check"; time = "09:25" },
    @{ task = "\Bitcoin-Runtime-Schedule-Integrity-Check"; time = "09:27" },
    @{ task = "\Bitcoin-Runtime-Alert-Check"; time = "09:30" }
)

function Get-TaskStartTime([string]$TaskName) {
    schtasks /Query /TN $TaskName /V /FO LIST > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        return @{ exists = $false; start_time = ""; status = "NOT_FOUND" }
    }
    $raw = schtasks /Query /TN $TaskName /V /FO LIST
    $statusLine = ($raw | Select-String "^Status:\s+" | Select-Object -First 1).ToString()
    $startLine = ($raw | Select-String "^Start Time:\s+" | Select-Object -First 1).ToString()
    $status = ($statusLine -replace "^Status:\s+", "").Trim()
    $startText = ($startLine -replace "^Start Time:\s+", "").Trim()
    return @{ exists = $true; start_time = $startText; status = $status }
}

function Parse-Time([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) { return $null }
    $t = $Text.Trim()
    try {
        $dt = [datetime]::Parse($t)
        return ($dt.Hour * 60 + $dt.Minute)
    } catch {
    }
    if ($t -match "(\d{1,2}):(\d{2})(?::\d{2})?") {
        return ([int]$Matches[1] * 60 + [int]$Matches[2])
    }
    return $null
}

function Test-MinutesWithinTolerance([nullable[int]]$ActualMin, [nullable[int]]$ExpectedMin, [int]$Tol) {
    if ($null -eq $ActualMin -or $null -eq $ExpectedMin) { return $false }
    $diff = [Math]::Abs([int]$ActualMin - [int]$ExpectedMin)
    $circ = [Math]::Min($diff, 1440 - $diff)
    return ($circ -le $Tol)
}

function Test-AcceptableTaskStatus([string]$Status, [string]$TaskName, [string[]]$AllowDisabledList) {
    if ($Status -in @("Ready", "Running")) { return $true }
    if ($Status -eq "Disabled" -and $AllowDisabledList -contains $TaskName) { return $true }
    return $false
}

$items = @()
foreach ($e in $expected) {
    $task = $e.task
    $expectedMin = Parse-Time $e.time
    $snap = Get-TaskStartTime -TaskName $task
    $actualMin = Parse-Time $snap.start_time
    $timeMatch = Test-MinutesWithinTolerance -ActualMin $actualMin -ExpectedMin $expectedMin -Tol $TimeToleranceMinutes
    $items += @{
        task_name = $task
        exists = $snap.exists
        status = $snap.status
        expected_time = $e.time
        actual_start_time = $snap.start_time
        time_match = $timeMatch
    }
}

$allExist = ($items | Where-Object { -not $_.exists }).Count -eq 0
$allTimeMatch = ($items | Where-Object { -not $_.time_match }).Count -eq 0
$allReady = ($items | Where-Object { -not (Test-AcceptableTaskStatus -Status $_.status -TaskName $_.task_name -AllowDisabledList $AllowDisabled) }).Count -eq 0

$integrityOk = $allExist -and $allTimeMatch -and $allReady
$result = [ordered]@{
    timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    integrity_ok = $integrityOk
    all_exist = $allExist
    all_time_match = $allTimeMatch
    all_ready = $allReady
    time_tolerance_minutes = $TimeToleranceMinutes
    allow_disabled_tasks = @($AllowDisabled)
    items = $items
}

$json = $result | ConvertTo-Json -Depth 6
Write-Host $json

$parent = Split-Path -Parent $OutputPath
if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
Write-Host ("Saved runtime schedule integrity report: {0}" -f $OutputPath)

if (-not $integrityOk) { exit 1 }
exit 0
