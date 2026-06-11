<#
.SYNOPSIS
  C: workspace Phase2 completion — non-destructive git gc + hygiene report + Nemotron HOLD record.

.DESCRIPTION
  Phase1 (HF+Ollama junction to F:) assumed done per LOCAL_MACHINE_POINTER.
  Phase2: git gc, optional __pycache__/pytest cache cleanup, disk hygiene JSON, Nemotron 106G HOLD SSOT.
  Does NOT move WSL-linked Nemotron paths or delete .venv without explicit -ApproveVenvCleanup.

.NOTES
  [HYPO] infra lane · research_only · no Track A / live coupling.
#>
param(
    [switch]$WhatIfOnly,
    [switch]$ApproveVenvCleanup,
    [int]$GitGcExpireDays = 1
)

$ErrorActionPreference = "Stop"
$root = "C:\workspace"
Set-Location $root

$outJson = Join-Path $root "reports\c_workspace_phase2_completion_v1_latest.json"
$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

$steps = [System.Collections.Generic.List[object]]::new()

function Add-Step($name, $exitCode, $note) {
    $script:steps.Add([ordered]@{
        name      = $name
        exit_code = $exitCode
        note      = $note
    }) | Out-Null
}

# 1) git gc (non-destructive to working tree)
Write-Host "[1/4] git gc --prune=now (expire $GitGcExpireDays d)..." -ForegroundColor Cyan
if ($WhatIfOnly) {
    Add-Step "git_gc" 0 "whatif_skipped"
} else {
    git gc --prune=now --expire="$GitGcExpireDays.days.ago" 2>&1 | Out-Null
    Add-Step "git_gc" $LASTEXITCODE "prune_now"
}

# 2) light workspace cache cleanup (__pycache__, .pytest_cache only)
Write-Host "[2/4] light cache cleanup..." -ForegroundColor Cyan
$removed = 0
if (-not $WhatIfOnly) {
    Get-ChildItem -Path $root -Recurse -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -in @("__pycache__", ".pytest_cache") } |
        ForEach-Object {
            try {
                Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction Stop
                $removed++
            } catch { }
        }
}
Add-Step "cache_cleanup" 0 "removed_dirs=$removed"

# 3) disk hygiene report (no deletes)
Write-Host "[3/4] system disk hygiene report..." -ForegroundColor Cyan
$hygieneScript = Join-Path $root "scripts\Invoke-SystemDiskHygieneReport.ps1"
$hygieneExit = 0
if (Test-Path -LiteralPath $hygieneScript) {
    if ($WhatIfOnly) {
        Add-Step "disk_hygiene" 0 "whatif_skipped"
    } else {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $hygieneScript 2>&1 | Out-Null
        $hygieneExit = $LASTEXITCODE
        Add-Step "disk_hygiene" $hygieneExit "reports/system_disk_hygiene_latest.json"
    }
} else {
    Add-Step "disk_hygiene" 0 "script_missing_skipped"
}

# 4) Nemotron 106G — record HOLD (WSL dependency; no move)
Write-Host "[4/4] Nemotron 106G HOLD record..." -ForegroundColor Cyan
$nemotronPaths = @(
    (Join-Path $root "data\nvidia"),
    (Join-Path $root "storage\hf_cache\nemotron_wsl")
)
$nemotronBytes = 0
foreach ($p in $nemotronPaths) {
    if (Test-Path -LiteralPath $p) {
        $nemotronBytes += (Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction SilentlyContinue |
            Measure-Object -Property Length -Sum).Sum
    }
}
Add-Step "nemotron_hold" 0 "decision=HOLD_wsl_dependency bytes_approx=$nemotronBytes"

$doc = [ordered]@{
    schema             = "c_workspace_phase2_completion_v1"
    generated_at_utc   = $utc
    research_only      = $true
    hypothesis_tag     = "[HYPO]"
    phase1_assumption  = "HF+Ollama junction to F:\workspace_offload (LOCAL_MACHINE_POINTER)"
    phase2_actions     = $steps
    nemotron_106g      = [ordered]@{
        decision = "HOLD"
        reason   = "WSL-linked paths; moving breaks nemotron_wsl training smoke"
        paths    = $nemotronPaths
        bytes_approx = $nemotronBytes
    }
    venv_cleanup       = [ordered]@{
        executed = $false
        reason   = if ($ApproveVenvCleanup) { "not_implemented_use_Invoke-ApprovedUserCacheCleanup" } else { "skipped_default_dual_active_venv" }
    }
    boundary_ack       = "B→A·실매매 자동 합선 없음"
}

$json = $doc | ConvertTo-Json -Depth 6
if (-not $WhatIfOnly) {
    $json | Set-Content -Path $outJson -Encoding utf8
    Write-Host "Wrote $outJson" -ForegroundColor Green
} else {
    Write-Host "WhatIf: would write $outJson" -ForegroundColor Yellow
}

$fail = ($steps | Where-Object { $_.exit_code -ne 0 }).Count
if ($fail -gt 0) { exit 1 }
exit 0
