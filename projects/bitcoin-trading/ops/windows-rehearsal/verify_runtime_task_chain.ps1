param(
    [string]$OutputPath = "C:\workspace\projects\bitcoin-trading\memory\v2\ops\runtime_task_chain_latest.json",
    [string[]]$AllowDisabled = @(
        '\Bitcoin-Runtime-Bootstrap-Automation',
        '\Bitcoin-Runtime-Self-Heal'
    )
)

$ErrorActionPreference = "Stop"

$taskNames = @(
    "\Bitcoin-Runtime-Bootstrap-Automation",
    "\Bitcoin-Runtime-Self-Heal",
    "\Bitcoin-Fused-QuantPixel-SOP-Strict-Check",
    "\Bitcoin-Runtime-Health-Check",
    "\Bitcoin-Runtime-Task-Chain-Check",
    "\Bitcoin-Runtime-Schedule-Integrity-Check",
    "\Bitcoin-Runtime-Alert-Check"
)

function Get-TaskSnapshot([string]$TaskName) {
    schtasks /Query /TN $TaskName /V /FO LIST > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        return @{
            task_name = $TaskName
            exists = $false
            status = "NOT_FOUND"
            next_run_time = ""
            last_result = ""
            ok = $false
        }
    }

    $raw = schtasks /Query /TN $TaskName /V /FO LIST
    $statusLine = ($raw | Select-String "^Status:\s+" | Select-Object -First 1).ToString()
    $nextRunLine = ($raw | Select-String "^Next Run Time:\s+" | Select-Object -First 1).ToString()
    $lastResultLine = ($raw | Select-String "^Last Result:\s+" | Select-Object -First 1).ToString()

    $status = ($statusLine -replace "^Status:\s+", "").Trim()
    $nextRun = ($nextRunLine -replace "^Next Run Time:\s+", "").Trim()
    $lastResult = ($lastResultLine -replace "^Last Result:\s+", "").Trim()
    $isReady = ($status -in @("Ready", "Running"))
    $ok = $isReady
    if (-not $ok -and $status -eq "Disabled" -and ($AllowDisabled -contains $TaskName)) {
        $ok = $true
    }

    return @{
        task_name = $TaskName
        exists = $true
        status = $status
        next_run_time = $nextRun
        last_result = $lastResult
        ok = $ok
    }
}

$items = @()
foreach ($t in $taskNames) {
    $items += Get-TaskSnapshot -TaskName $t
}

$allOk = ($items | Where-Object { -not $_.ok }).Count -eq 0
$result = [ordered]@{
    timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    all_ok = $allOk
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
Write-Host ("Saved runtime task chain report: {0}" -f $OutputPath)

if (-not $allOk) {
    exit 1
}
exit 0
