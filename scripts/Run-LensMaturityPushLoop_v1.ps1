#Requires -Version 5.1
<#
.SYNOPSIS
  Push lens maturity until composites plateau or max iterations (B-track · no Track A claim).

.DESCRIPTION
  Each round: refresh ops/chain artifacts → Run-LensParallelHardening → compare v2 composites.
  Appends history to reports/lens_maturity_push_history.jsonl.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [int]$MaxIterations = 5,
    [int]$PlateauStop = 2,
    [switch]$SendTelegramOnGain,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

$historyPath = Join-Path $WorkspaceRoot "reports\lens_maturity_push_history.jsonl"
$maturityPath = Join-Path $WorkspaceRoot "reports\lens_maturity_self_score_v1_latest.json"

function Get-Composites([string]$jsonPath) {
    if (-not (Test-Path -LiteralPath $jsonPath)) { return $null }
    $doc = Get-Content -LiteralPath $jsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
    return @{
        myeongni = [double]$doc.lenses.myeongni.composite_10
        logos    = [double]$doc.lenses.logos.composite_10
        sasang   = [double]$doc.lenses.sasang.composite_10
        sum      = [double]$doc.lenses.myeongni.composite_10 + [double]$doc.lenses.logos.composite_10 + [double]$doc.lenses.sasang.composite_10
    }
}

function Test-Improved($before, $after) {
    if ($null -eq $before -or $null -eq $after) { return $true }
    return ($after.sum -gt $before.sum) -or
        ($after.myeongni -gt $before.myeongni) -or
        ($after.logos -gt $before.logos) -or
        ($after.sasang -gt $before.sasang)
}

$beforeAll = Get-Composites $maturityPath
$plateau = 0
$round = 0

$steps = @(
    @{ Name = "myeongni_weekly"; Cmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$WorkspaceRoot\scripts\Run-MyeongniWeeklyOpsSummary_v1.ps1`"" },
    @{ Name = "myeongni_chain"; Cmd = "$py scripts/run_myeongni_lens_chain_from_bot_v1.py --demo-smoke" },
    @{ Name = "hardening"; Cmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$WorkspaceRoot\scripts\Run-LensParallelHardening_v1.ps1`" -SkipTelegram" }
)

while ($round -lt $MaxIterations) {
    $round++
    Write-Host "`n=== maturity push round $round / $MaxIterations ===" -ForegroundColor Cyan
    $before = Get-Composites $maturityPath

    foreach ($s in $steps) {
        if ($WhatIf) {
            Write-Host "[WhatIf] $($s.Name): $($s.Cmd)"
            continue
        }
        Write-Host ">> $($s.Name)" -ForegroundColor DarkGray
        Invoke-Expression $s.Cmd
        if ($LASTEXITCODE -ne 0) {
            if ($s.Name -eq "hardening") {
                Write-Host "[FAIL] hardening exit $LASTEXITCODE" -ForegroundColor Red
                exit $LASTEXITCODE
            }
            Write-Host "[WARN] $($s.Name) exit $LASTEXITCODE (optional)" -ForegroundColor Yellow
        }
    }

    if ($WhatIf) { break }

    $after = Get-Composites $maturityPath
    $row = @{
        round          = $round
        at_utc         = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        before         = $before
        after          = $after
        improved       = (Test-Improved $before $after)
        plateau_rounds = $plateau
    } | ConvertTo-Json -Compress
    Add-Content -LiteralPath $historyPath -Value $row -Encoding UTF8

    Write-Host ("  명리 {0} -> {1} | 성경 {2} -> {3} | 사상 {4} -> {5}" -f `
        $before.myeongni, $after.myeongni, $before.logos, $after.logos, $before.sasang, $after.sasang)

    if (Test-Improved $before $after) {
        $plateau = 0
        if ($SendTelegramOnGain) {
            & $py scripts/send_telegram_four_lens_reports_v1.py --force
        }
    } else {
        $plateau++
        Write-Host "[plateau] no composite gain ($plateau / $PlateauStop)" -ForegroundColor Yellow
        if ($plateau -ge $PlateauStop) {
            Write-Host "[STOP] plateau threshold" -ForegroundColor Green
            break
        }
    }
}

$final = Get-Composites $maturityPath
Write-Host "`n=== push loop done ===" -ForegroundColor Green
if ($beforeAll -and $final) {
    Write-Host ("  start sum={0:F1} -> end sum={1:F1}" -f $beforeAll.sum, $final.sum)
    Write-Host ("  명리 {0} | 성경 {1} | 사상 {2}" -f $final.myeongni, $final.logos, $final.sasang)
}
Write-Host "  history: $historyPath"
