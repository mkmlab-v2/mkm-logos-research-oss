#Requires -Version 5.1

<#

.SYNOPSIS

  RQ-031 one-click: A-code governor bundle + promotion RQ readiness [HYPO].

#>

param(

    [string]$WorkspaceRoot = "C:\workspace",

    [string]$SessionDate = "",

    [switch]$SkipGovernorBundle,

    [switch]$RecordCommanderAck,

    [string]$AckReference = "COMMANDER-RQ031-SCOPE-ACK-2026-06-05",

    [switch]$Strict

)



$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $WorkspaceRoot



$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

if (-not $SessionDate) {

    $SessionDate = (Get-Date).ToString("yyyy-MM-dd")

}



if (-not $SkipGovernorBundle) {

    Write-Host "[rq031-bundle] a-code governor research bundle" -ForegroundColor Cyan

    & pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Run-ACodeGovernorResearchBundle_v1.ps1") `

        -WorkspaceRoot $WorkspaceRoot -SessionDate $SessionDate

    if ($LASTEXITCODE -ne 0) { throw "governor bundle exit $LASTEXITCODE" }

}



Write-Host "[rq031-bundle] promotion rq readiness" -ForegroundColor Cyan

$readinessArgs = @("scripts/build_a_code_promotion_rq_readiness_v1.py")

if ($Strict) { $readinessArgs += "--strict" }

& $py @readinessArgs

if ($LASTEXITCODE -ne 0) { throw "promotion rq readiness exit $LASTEXITCODE" }



$ackLocal = Join-Path $WorkspaceRoot "data\personalization\commander_a_code_promotion_rq_ack_v1.local.json"

if (Test-Path -LiteralPath $ackLocal) {

    Write-Host "[rq031-bundle] validate promotion rq ack" -ForegroundColor Cyan

    & $py scripts/validate_commander_a_code_promotion_rq_ack_v1.py

    if ($LASTEXITCODE -ne 0) { throw "promotion rq ack validation exit $LASTEXITCODE" }

}



if ($RecordCommanderAck) {

    Write-Host "[rq031-bundle] record commander scope ack" -ForegroundColor Cyan

    & $py scripts/record_a_code_promotion_rq_commander_ack_v1.py --ack-reference $AckReference

    if ($LASTEXITCODE -ne 0) { throw "record commander ack exit $LASTEXITCODE" }

    & $py scripts/build_a_code_promotion_rq_readiness_v1.py

    if ($LASTEXITCODE -ne 0) { throw "promotion rq readiness refresh exit $LASTEXITCODE" }

}



Write-Host "[rq031-bundle] trackc dashboard refresh" -ForegroundColor Cyan

& $py scripts/build_mkm_trackc_ops_dashboard_v1.py

if ($LASTEXITCODE -ne 0) { throw "trackc dashboard exit $LASTEXITCODE" }



Write-Host "[rq031-bundle] operator-assist lane freeze" -ForegroundColor Cyan

& $py scripts/build_a_code_operator_assist_lane_v1.py

if ($LASTEXITCODE -ne 0) { throw "operator lane build exit $LASTEXITCODE" }



Write-Host "[rq031-bundle] operator-assist lane gate" -ForegroundColor Cyan

$laneGateArgs = @("scripts/check_a_code_operator_assist_lane_gate_v1.py")

if ($Strict) { $laneGateArgs += "--strict" }

& $py @laneGateArgs

if ($LASTEXITCODE -ne 0) { throw "operator lane gate exit $LASTEXITCODE" }



Write-Host "[rq031-bundle] constitution pointer PR draft (human PR only)" -ForegroundColor Cyan

& $py scripts/build_a_code_constitution_pointer_pr_draft_v1.py

if ($LASTEXITCODE -ne 0) { throw "constitution pointer PR draft exit $LASTEXITCODE" }



Write-Host "[rq031-bundle] constitution pointer row check" -ForegroundColor Cyan

& $py scripts/check_a_code_constitution_pointer_row_v1.py --strict

if ($LASTEXITCODE -ne 0) { throw "constitution pointer row check exit $LASTEXITCODE" }



Write-Host "[rq031-bundle] rq close candidate gate (non-closing)" -ForegroundColor Cyan

& $py scripts/check_a_code_rq_close_gate_v1.py

if ($LASTEXITCODE -ne 0) { throw "rq close gate exit $LASTEXITCODE" }



Write-Host "[rq031-bundle] rq close human checklist (commander manual only)" -ForegroundColor Cyan

& $py scripts/build_a_code_rq_close_human_checklist_v1.py

if ($LASTEXITCODE -ne 0) { throw "rq close human checklist exit $LASTEXITCODE" }



Write-Host "[rq031-bundle] done" -ForegroundColor Green

