#Requires -Version 5.1
<#
.SYNOPSIS
  Parallel lens hardening: Logos evidence · Myeongni report · Sasang fusion · predictability + maturity.
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipTelegram,
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = "py" }

$steps = @(
    @{ Name = "logos_lens"; Cmd = "$py scripts/run_lens_logos.py --use-production-evidence" },
    @{ Name = "myeongni_report"; Cmd = "$py scripts/build_myeongni_lens_observation_report_v1.py" },
    @{ Name = "market_myeongni"; Cmd = "$py scripts/run_market_myeongni_lens_v1.py" },
    @{ Name = "market_sasang"; Cmd = "$py scripts/run_market_sasang_lens_v1.py" },
    @{ Name = "sasang_report"; Cmd = "$py scripts/build_sasang_lens_observation_report_v1.py" },
    @{ Name = "per_lens_hit"; Cmd = "$py scripts/build_prophecy_hit_rate_per_lens_bundle_v1.py" },
    @{ Name = "sasang_fusion"; Cmd = "$py scripts/build_sasang_4agent_fusion_gate_v1.py" },
    @{ Name = "sasang_promotion"; Cmd = "$py scripts/build_sasang_4agent_promotion_gate_v1.py" },
    @{ Name = "conflict"; Cmd = "$py scripts/build_lens_conflict_narrative_v1.py" },
    @{ Name = "predictability"; Cmd = "$py scripts/run_btrack_predictability_harness_v1.py" },
    @{ Name = "maturity"; Cmd = "$py scripts/build_lens_maturity_self_score_v1.py" }
)

if ($WhatIf) {
    $steps | ForEach-Object { Write-Host "[WhatIf] $($_.Name): $($_.Cmd)" }
    exit 0
}

$jobs = @()
foreach ($s in $steps) {
    $jobs += Start-Job -Name $s.Name -ScriptBlock {
        param($wd, $cmd)
        Set-Location -LiteralPath $wd
        Invoke-Expression $cmd
        if ($LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE" }
    } -ArgumentList $WorkspaceRoot, $s.Cmd
}

$softOk = @("predictability", "market_myeongni", "market_sasang", "per_lens_hit")
$fail = @()
foreach ($j in $jobs) {
    $null = Wait-Job -Job $j
    $out = Receive-Job -Job $j -ErrorAction SilentlyContinue
    if ($out) { $out | ForEach-Object { Write-Host $_ } }
    if ($j.State -ne "Completed") {
        if ($softOk -contains $j.Name) {
            Write-Host "[WARN] $($j.Name) skipped/failed (optional)" -ForegroundColor Yellow
        } else {
            $fail += $j.Name
        }
    }
    Remove-Job -Job $j -Force -ErrorAction SilentlyContinue
}

if ($fail.Count -gt 0) {
    Write-Host "[FAIL] steps: $($fail -join ', ')" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] parallel hardening complete" -ForegroundColor Green

if (-not $SkipTelegram) {
    & $py scripts/send_telegram_four_lens_reports_v1.py --force
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

exit 0
