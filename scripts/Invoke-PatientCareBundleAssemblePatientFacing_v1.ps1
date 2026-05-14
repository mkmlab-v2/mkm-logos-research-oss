#Requires -Version 5.1
<#
.SYNOPSIS
  환자 통합 번들 v1 — 만세력 리포트 + JSON 번들 + KO 슬롯 템플릿 + 생성 정책 게이트 + 환자용 단일 Markdown까지 한 번에 실행한다.

.DESCRIPTION
  `scripts/assemble_patient_care_bundle_with_myeongni_v1.py`에 `--validate`·`--apply-slot-templates`
  ·`--validate-policy`·`--render-md-out`를 고정 전달한다. SSOT: `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §9,
  `docs/final/schemas/patient_care_bundle_v1.schema.json`.

.PARAMETER WorkspaceRoot
  비우면 MKM_WORKSPACE_ROOT, 없으면 본 스크립트 상위(모노레포 루트).

.PARAMETER PolicyJson
  비우면 기본 정책(assemble에서 `--policy-json` 생략과 동일). 지정 시 `--policy-json`으로 전달.

.PARAMETER DryRun
  실행할 `py` 인자만 출력하고 종료(exit 0).

.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PatientCareBundleAssemblePatientFacing_v1.ps1 `
    -BirthYear 1994 -BirthMonth 4 -BirthDay 10 -BirthHour 11 -BirthMinute 2 -BirthSecond 0

.EXAMPLE
  pwsh -File scripts\Invoke-PatientCareBundleAssemblePatientFacing_v1.ps1 -BirthYear 1994 -BirthMonth 4 -BirthDay 10 -BirthHour 11 -BirthMinute 2 -BirthSecond 0 `
    -SoapJson tests\fixtures\patient_care_bundle_soap_stub_v1.example.json -RenderMdOut reports\out.md
#>
param(
    [string]$WorkspaceRoot = "",
    [Parameter(Mandatory = $true)][int]$BirthYear,
    [Parameter(Mandatory = $true)][int]$BirthMonth,
    [Parameter(Mandatory = $true)][int]$BirthDay,
    [Parameter(Mandatory = $true)][int]$BirthHour,
    [Parameter(Mandatory = $true)][int]$BirthMinute,
    [Parameter(Mandatory = $true)][int]$BirthSecond,
    [string]$IanaTz = "Asia/Seoul",
    [switch]$IsMale,
    [string]$MyeongniOut = "",
    [string]$BundleOut = "",
    [string]$RenderMdOut = "",
    [string]$SoapJson = "",
    [string]$CdsEnvelopeJson = "",
    [string]$PolicyJson = "",
    [int]$AnnualStartYear = 0,
    [int]$AnnualYears = 5,
    [int]$MonthlyMonthsPerYear = 12,
    [switch]$DryRun
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = if ($WorkspaceRoot -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    (Resolve-Path -LiteralPath $WorkspaceRoot).Path
}
elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    (Resolve-Path -LiteralPath $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')).Path
}
else {
    (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
}

$assemble = Join-Path $root 'scripts\assemble_patient_care_bundle_with_myeongni_v1.py'
if (-not (Test-Path -LiteralPath $assemble)) {
    throw "Missing assemble script: $assemble"
}

$mye = if ($MyeongniOut) { $MyeongniOut } else { Join-Path $root 'reports\patient_care_myeongni_full_for_bundle_latest.json' }
$bundle = if ($BundleOut) { $BundleOut } else { Join-Path $root 'reports\patient_care_bundle_with_myeongni_latest.json' }
$md = if ($RenderMdOut) { $RenderMdOut } else { Join-Path $root 'reports\patient_care_bundle_patient_facing_latest.md' }

$y0 = if ($AnnualStartYear -gt 0) { $AnnualStartYear } else { (Get-Date).Year }

$argList = @(
    $assemble,
    '--local',
    "$BirthYear", "$BirthMonth", "$BirthDay", "$BirthHour", "$BirthMinute", "$BirthSecond",
    '--iana-tz', $IanaTz,
    '--myeongni-out', $mye,
    '--bundle-out', $bundle,
    '--annual-start-year', "$y0",
    '--annual-years', "$AnnualYears",
    '--monthly-months-per-year', "$MonthlyMonthsPerYear",
    '--validate',
    '--apply-slot-templates',
    '--validate-policy',
    '--render-md-out', $md
)
if ($IsMale) { $argList += '--is-male' }
if ($SoapJson) {
    if (-not (Test-Path -LiteralPath $SoapJson)) { throw "SOAP JSON not found: $SoapJson" }
    $argList += @('--soap-json', $SoapJson)
}
if ($CdsEnvelopeJson) {
    if (-not (Test-Path -LiteralPath $CdsEnvelopeJson)) { throw "CDS envelope JSON not found: $CdsEnvelopeJson" }
    $argList += @('--cds-envelope-json', $CdsEnvelopeJson)
}
if ($PolicyJson) {
    if (-not (Test-Path -LiteralPath $PolicyJson)) { throw "Policy JSON not found: $PolicyJson" }
    $argList += @('--policy-json', $PolicyJson)
}

if ($DryRun) {
    Write-Host ('py ' + ($argList -join ' '))
    exit 0
}

Push-Location -LiteralPath $root
try {
    & py @argList
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
