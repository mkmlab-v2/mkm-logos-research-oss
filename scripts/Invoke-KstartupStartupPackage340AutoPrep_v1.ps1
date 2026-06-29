#Requires -Version 5.1
<#
.SYNOPSIS
  창업패키지 340 — agent 자동 준비 (paste·금지어·ingest·CDP probe·외부 Chrome).
  G0/G3/G5 attest·임시저장·제출완료는 human. autofill fill은 submission_gate 통과 후.
#>
param(
    [switch]$SkipProbe,
    [switch]$SkipOpenExternal,
    [switch]$ProbeOnly
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Invoke-Step($name, [scriptblock]$block) {
    Write-Host "== $name ==" -ForegroundColor Cyan
    & $block
    if ($LASTEXITCODE -ne 0) { throw "$name failed exit=$LASTEXITCODE" }
}

Invoke-Step "ingest_attachments" { py scripts/ingest_kstartup_startup_package_ai_downloads_v1.py }
Invoke-Step "build_paste" { py scripts/build_kstartup_startup_package_ai_paste_ready_v1.py }
Invoke-Step "paste_lint" { py scripts/check_kstartup_startup_package_ai_paste_lint_v1.py }
Invoke-Step "fill_doyak_docx" { py scripts/fill_kstartup_startup_package_ai_doyak_docx_v1.py }
Invoke-Step "verify_filled_plan" { py scripts/verify_kstartup_startup_package_ai_filled_plan_v1.py }
Invoke-Step "body_audit" { py scripts/export_kstartup_startup_package_ai_docx_preview_v1.py }
Invoke-Step "build_assistant" { py scripts/build_kstartup_startup_package_ai_paste_assistant_v1.py }
Invoke-Step "forbidden_scan" { py scripts/check_kstartup_startup_package_ai_forbidden_phrases_v1.py }

Write-Host "== submission_gate (report only) ==" -ForegroundColor Cyan
py scripts/check_kstartup_startup_package_ai_submission_gate_v1.py
$gateRc = $LASTEXITCODE

if (-not $SkipProbe) {
    Write-Host "== pms_cdp_probe ==" -ForegroundColor Cyan
    $cdpUp = $false
    try {
        $null = Invoke-WebRequest -Uri "http://127.0.0.1:9222/json/version" -UseBasicParsing -TimeoutSec 3
        $cdpUp = $true
    } catch { $cdpUp = $false }

    if ($cdpUp) {
        $pmsUrl = "https://pms.k-startup.go.kr/biz/screen/BMO0101M01?pbancId=0661001"
        py scripts/kstartup_startup_package_ai_autofill_v1.py --cdp-url "http://127.0.0.1:9222" --probe-only --pms-url $pmsUrl --wait-for-login-sec 45
        if ($LASTEXITCODE -ne 0) { Write-Host "WARN: probe exit $LASTEXITCODE" -ForegroundColor Yellow }
    } else {
        Write-Host "CDP 9222 down — skip probe (start Chrome CDP or Run-KstartupStartupPackageAiAutofill -UseDefaultProfile)" -ForegroundColor Yellow
    }
}

if (-not $SkipOpenExternal) {
    Write-Host "== open_external_chrome ==" -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Open-KstartupStartupPackage340External_v1.ps1
}

Write-Host ""
Write-Host "340 auto prep DONE" -ForegroundColor Green
Write-Host "  gate_exit: $gateRc (0=human gates ready for autofill fill)" -ForegroundColor $(if ($gateRc -eq 0) { "Green" } else { "Yellow" })
Write-Host "  G0 attest: py scripts/attest_kstartup_startup_package_ai_human_gates_v1.py --gate G0_eligibility --status pass --note `"4항 NO`"" -ForegroundColor Yellow
Write-Host "  autofill:  powershell -File scripts\Run-KstartupStartupPackageAiAutofill_v1.ps1 -UseDefaultProfile" -ForegroundColor Yellow
Write-Host "  boundary:  no 제출완료 without human" -ForegroundColor DarkGray

if ($ProbeOnly) { exit 0 }
exit $(if ($gateRc -eq 0) { 0 } else { 2 })
