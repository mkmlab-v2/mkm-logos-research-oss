param(
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\runtime_self_heal_latest.json"
)

$ErrorActionPreference = "Stop"

$taskNames = @(
    "\Bitcoin-Runtime-Bootstrap-Automation",
    "\Bitcoin-Fused-QuantPixel-SOP-Strict-Check",
    "\Bitcoin-Runtime-Health-Check",
    "\Bitcoin-Runtime-Task-Chain-Check",
    "\Bitcoin-Runtime-Schedule-Integrity-Check",
    "\Bitcoin-Runtime-Alert-Check"
)

function Get-TaskStatus([string]$TaskName) {
    schtasks /Query /TN $TaskName /V /FO LIST > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        return @{ exists = $false; status = "NOT_FOUND" }
    }
    $raw = schtasks /Query /TN $TaskName /V /FO LIST
    $statusLine = ($raw | Select-String "^Status:\s+" | Select-Object -First 1).ToString()
    $status = ($statusLine -replace "^Status:\s+", "").Trim()
    return @{ exists = $true; status = $status }
}

$items = @()
foreach ($task in $taskNames) {
    $before = Get-TaskStatus -TaskName $task
    $action = "none"
    $ok = $false

    if (-not $before.exists) {
        $action = "missing"
        $ok = $false
    } elseif ($before.status -ne "Ready") {
        schtasks /Change /TN $task /ENABLE > $null 2>&1
        $after = Get-TaskStatus -TaskName $task
        $action = "enabled"
        $ok = ($after.exists -and $after.status -eq "Ready")
        $items += @{
            task_name = $task
            before_status = $before.status
            after_status = $after.status
            action = $action
            ok = $ok
        }
        continue
    } else {
        $ok = $true
    }

    $items += @{
        task_name = $task
        before_status = $before.status
        after_status = $before.status
        action = $action
        ok = $ok
    }
}

$allOk = ($items | Where-Object { -not $_.ok }).Count -eq 0
$enabledCount = ($items | Where-Object { $_.action -eq "enabled" }).Count
$result = [ordered]@{
    timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    all_ok = $allOk
    enabled_count = $enabledCount
    items = $items
}

$json = $result | ConvertTo-Json -Depth 6
Write-Host $json

$parent = Split-Path -Parent $OutputPath
if ($parent -and -not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
}
Set-Content -LiteralPath $OutputPath -Value $json -Encoding UTF8
Write-Host ("Saved runtime self-heal report: {0}" -f $OutputPath)

if (-not $allOk) { exit 1 }
exit 0
