<#
.SYNOPSIS
  Windows wrapper: MKM System2 self-correction gate MVP (dry-run default).

.DESCRIPTION
  Delegates to py scripts/run_mkm_system2_self_correction_gate_chain_v1.py.
  Default draft uses the pass fixture; no live LLM unless -Live.

.PARAMETER DraftFile
  Draft text path (default: docs/final/artifacts/fixtures/mkm_system2_gate_draft_pass_v1.txt).

.PARAMETER SkipPytest
  Skip gate pytest after chain (faster ops smoke).

.PARAMETER Live
  Pass --live to the Python chain (LLM paths; use with care).

.PARAMETER WorkspaceRoot
  Repo root (default: MKM_WORKSPACE_ROOT or parent of scripts/).
#>
param(
    [string]$DraftFile = "",
    [switch]$SkipPytest,
    [switch]$Live,
    [string]$WorkspaceRoot = ""
)

$ErrorActionPreference = "Stop"

$resolvedRoot = if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot) -and (Test-Path -LiteralPath $WorkspaceRoot)) {
    $WorkspaceRoot.TrimEnd('\', '/')
}
elseif ($env:MKM_WORKSPACE_ROOT -and (Test-Path -LiteralPath $env:MKM_WORKSPACE_ROOT)) {
    $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/')
}
else {
    (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

if (-not $DraftFile) {
    $DraftFile = Join-Path $resolvedRoot "docs\final\artifacts\fixtures\mkm_system2_gate_draft_pass_v1.txt"
}
if (-not (Test-Path -LiteralPath $DraftFile)) {
    throw "Draft file not found: $DraftFile"
}

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

$chainArgs = @(
    "scripts/run_mkm_system2_self_correction_gate_chain_v1.py",
    "--draft-file", $DraftFile
)
if ($SkipPytest) { $chainArgs += "--skip-pytest" }
if ($Live) { $chainArgs += "--live" }

Push-Location $resolvedRoot
try {
    & $py @chainArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
