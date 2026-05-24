#Requires -Version 5.1
<#
.SYNOPSIS
  인테이크 JSON → SOAP 초안 + patient_care_bundle_v1 + 근거 사이드카 + (선택) MD 렌더 + 스키마/정책 검증.

.DESCRIPTION
  `scripts/build_patient_intake_fusion_draft_v1.py` 래퍼. SSOT: `docs/final/schemas/patient_intake_fusion_draft_input_v1.schema.json`,
  `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §9 (인테이크 융합 초안 행).

.PARAMETER WorkspaceRoot
  비우면 MKM_WORKSPACE_ROOT, 없으면 스크립트에서 모노레포 루트.

.PARAMETER IntakeJson
  기본: tests\fixtures\patient_intake_fusion_draft_v1.example.json

.EXAMPLE
  pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-PatientIntakeFusionDraft_v1.ps1

.EXAMPLE
  pwsh -File scripts\Invoke-PatientIntakeFusionDraft_v1.ps1 -IntakeJson data\my_encounter.json -BundleOut reports\b.json
#>
param(
  [string]$WorkspaceRoot = "",
  [string]$IntakeJson = "",
  [string]$MyeongniOut = "",
  [string]$BundleOut = "",
  [string]$RationaleOut = "",
  [string]$RenderMdOut = "reports\patient_intake_fusion_bundle_draft_latest.md",
  [switch]$SkipValidateBundleSchema,
  [switch]$SkipValidatePolicy,
  [switch]$ApplySlotTemplatesFillEmptyOnly,
  [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = if ($WorkspaceRoot) { $WorkspaceRoot } elseif ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT } else { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
$intake = if ($IntakeJson) { $IntakeJson } else { Join-Path $root "tests\fixtures\patient_intake_fusion_draft_v1.example.json" }
$mye = if ($MyeongniOut) { $MyeongniOut } else { Join-Path $root "reports\patient_intake_fusion_myeongni_latest.json" }
$bun = if ($BundleOut) { $BundleOut } else { Join-Path $root "reports\patient_intake_fusion_bundle_draft_latest.json" }
$rat = if ($RationaleOut) { $RationaleOut } else { Join-Path $root "reports\patient_intake_fusion_rationale_latest.json" }
$md = if ($null -ne $RenderMdOut -and $RenderMdOut -eq '') { $null } elseif ($RenderMdOut) { if ([System.IO.Path]::IsPathRooted($RenderMdOut)) { $RenderMdOut } else { Join-Path $root $RenderMdOut } } else { $null }

$pyArgs = @(
  (Join-Path $root 'scripts\build_patient_intake_fusion_draft_v1.py'),
  '--intake-json', $intake,
  '--myeongni-out', $mye,
  '--bundle-out', $bun,
  '--rationale-out', $rat
)
if (-not $SkipValidateBundleSchema) { $pyArgs += '--validate-schema' }
if (-not $SkipValidatePolicy) { $pyArgs += '--validate-policy' }
if ($md) { $pyArgs += @('--render-md-out', $md) }

$py = 'py'
if ($DryRun) {
  Write-Host ("$py " + ($pyArgs -join ' '))
  exit 0
}

Push-Location $root
try {
  & $py @pyArgs
  exit $LASTEXITCODE
} finally {
  Pop-Location
}
