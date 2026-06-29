#Requires -Version 5.1
<#
.SYNOPSIS
  RQ-028 one-click: multiday replay + promotion gate + evening observation [HYPO].
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$SessionDate = "",
    [switch]$StrictGate,
    [switch]$SkipMultiday
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
if (-not $SessionDate) {
    $SessionDate = (Get-Date).ToString("yyyy-MM-dd")
}

Write-Host "[a-code-bundle] validate commander profile" -ForegroundColor Cyan
& $py scripts/validate_commander_profile_v1.py
if ($LASTEXITCODE -ne 0) { throw "commander profile validation exit $LASTEXITCODE" }

if (-not $SkipMultiday) {
    Write-Host "[a-code-bundle] multiday replay" -ForegroundColor Cyan
    & $py scripts/build_a_code_governor_knob_multiday_replay_v1.py
    if ($LASTEXITCODE -ne 0) { throw "multiday replay exit $LASTEXITCODE" }
}

Write-Host "[a-code-bundle] promotion gate" -ForegroundColor Cyan
$gateArgs = @("scripts/check_a_code_governor_promotion_gate_v1.py")
if ($StrictGate) { $gateArgs += "--strict" }
& $py @gateArgs
if ($LASTEXITCODE -ne 0 -and $StrictGate) { throw "promotion gate exit $LASTEXITCODE" }

Write-Host "[a-code-bundle] evening observation ($SessionDate)" -ForegroundColor Cyan
& $py scripts/build_a_code_governor_knob_evening_observation_v1.py --session-date $SessionDate
if ($LASTEXITCODE -ne 0) { throw "evening observation exit $LASTEXITCODE" }

Write-Host "[a-code-bundle] evidence pack" -ForegroundColor Cyan
& $py scripts/build_a_code_governor_evidence_pack_v1.py
if ($LASTEXITCODE -ne 0) { throw "evidence pack exit $LASTEXITCODE" }

Write-Host "[a-code-bundle] commander a-code signoff (optional)" -ForegroundColor Cyan
$signoffLocal = Join-Path $WorkspaceRoot "data\personalization\commander_a_code_signoff_v1.local.json"
if (Test-Path -LiteralPath $signoffLocal) {
    & $py scripts/validate_commander_a_code_signoff_v1.py
    if ($LASTEXITCODE -ne 0) { throw "commander a-code signoff validation exit $LASTEXITCODE" }
} else {
    Write-Host "[a-code-bundle] signoff absent (MANUAL checklist items remain)" -ForegroundColor DarkGray
}

Write-Host "[a-code-bundle] promotion checklist readiness" -ForegroundColor Cyan
& $py scripts/check_a_code_promotion_checklist_readiness_v1.py
if ($LASTEXITCODE -ne 0) { throw "checklist readiness exit $LASTEXITCODE" }

Write-Host "[a-code-bundle] trackc dashboard refresh" -ForegroundColor Cyan
& $py scripts/build_mkm_trackc_ops_dashboard_v1.py
if ($LASTEXITCODE -ne 0) { throw "trackc dashboard exit $LASTEXITCODE" }

Write-Host "[a-code-bundle] promotion discussion hint dispatch (non-gating)" -ForegroundColor Cyan
& $py scripts/dispatch_a_code_promotion_discussion_hint_v1.py
if ($LASTEXITCODE -ne 0) { throw "promotion discussion hint exit $LASTEXITCODE" }

Write-Host "[a-code-bundle] done" -ForegroundColor Green
